
"""Block 4: advisory authenticity signals."""

from __future__ import annotations

import math
import io
import json
import os
import uuid
import asyncio
import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .blocks import VerificationBlock
from .category_embedder import CategoryPrediction
from .contracts import BlockResult, CheckResult
from .duplicate import difference_hash, perceptual_hash, cosine_similarity
from .duplicate_index import DuplicateIndex, IndexEntry
from .embedder import Embedder, FakeEmbedder
from .image_loader import ImageContext


@dataclass(slots=True)
class AIGeneratedPrediction:
    """Probability that an image is AI-generated."""

    generated_probability: float
    method: str


class AIGeneratedDetector(ABC):
    """Interface for an AI-generated-image detector."""

    @abstractmethod
    def predict(self, image: Any) -> AIGeneratedPrediction:
        """Return a generated-image probability."""


class FakeAIGeneratedDetector(AIGeneratedDetector):
    """Deterministic detector used by offline tests."""

    def __init__(self, generated_probability: float | None = None) -> None:
        self.generated_probability = generated_probability

    def predict(self, image: Any) -> AIGeneratedPrediction:
        del image
        if self.generated_probability is None:
            raise RuntimeError("fake AI-generation signal unavailable")
        return AIGeneratedPrediction(float(self.generated_probability), "fake")


class LinearProbeAIGeneratedDetector(AIGeneratedDetector):
    """A frozen-embedding logistic probe supplied with learned weights."""

    def __init__(
        self,
        embedder: Embedder,
        weights: list[float],
        bias: float,
        threshold: float = 0.5,
    ) -> None:
        self.embedder = embedder
        self.weights = weights
        self.bias = bias
        self.threshold = threshold

    def predict(self, image: Any) -> AIGeneratedPrediction:
        vector = self.embedder.embed(image)
        logit = sum(left * right for left, right in zip(self.weights, vector)) + self.bias
        probability = 1.0 / (
            1.0 + math.exp(-max(-60.0, min(60.0, logit)))
        )
        return AIGeneratedPrediction(probability, "linear_probe")


class HuggingFaceAIGeneratedDetector(AIGeneratedDetector):
    """Lazy local Transformers detector for AI-generated images.

    The model and Transformers are loaded only on the first prediction. This
    keeps offline tests independent of PyTorch, Transformers, model downloads,
    and network access. The selected model currently labels class ``fake`` as
    AI-generated and ``real`` as camera/real imagery.
    """

    def __init__(
        self,
        model_id: str = "jacoballessio/ai-image-detect-distilled",
        device: str = "cpu",
        generated_class_index: int = 0,
        local_files_only: bool = False,
    ) -> None:
        self.model_id = model_id
        self.device_name = device
        self.generated_class_index = generated_class_index
        self.local_files_only = local_files_only
        self._processor: Any | None = None
        self._model: Any | None = None
        self._torch: Any | None = None
        self._device: Any | None = None

    def _load(self) -> None:
        """Load the processor and model once, only when inference is needed."""
        if self._model is not None:
            return

        try:
            import torch  # type: ignore
            from transformers import (
                ViTImageProcessor,
                AutoModelForImageClassification,
            )  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "transformers and torch are required for the Hugging Face AI detector"
            ) from exc

        load_kwargs = {"local_files_only": self.local_files_only}

        # This processor successfully loaded the configured model in the
        # standalone inference test. AutoImageProcessor did not recognize
        # this model's processor configuration.
        processor = ViTImageProcessor.from_pretrained(
            self.model_id,
            **load_kwargs,
        )

        model = AutoModelForImageClassification.from_pretrained(
            self.model_id,
            **load_kwargs,
        )

        device = torch.device(self.device_name)
        model.to(device)
        model.eval()

        self._processor = processor
        self._model = model
        self._torch = torch
        self._device = device

    def predict(self, image: Any) -> AIGeneratedPrediction:
        """Return the model probability for the configured generated class."""
        self._load()

        assert self._processor is not None
        assert self._model is not None
        assert self._torch is not None
        assert self._device is not None

        inputs = self._processor(images=image, return_tensors="pt")
        inputs = {
            key: value.to(self._device) if hasattr(value, "to") else value
            for key, value in inputs.items()
        }

        with self._torch.no_grad():
            logits = self._model(**inputs).logits[0]
            probabilities = self._torch.softmax(logits, dim=-1)

        index = int(self.generated_class_index)
        if index < 0 or index >= len(probabilities):
            raise RuntimeError(
                "configured AI-generated class index is outside the model output"
            )

        return AIGeneratedPrediction(
            float(probabilities[index].detach().cpu().item()),
            f"huggingface:{self.model_id}",
        )


class WebImageMatcher:
    """Match against a separate local web-image index, never a live search."""

    def __init__(
        self,
        index: DuplicateIndex | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        self.index = index or DuplicateIndex()
        self.embedder = embedder or FakeEmbedder()

    @property
    def available(self) -> bool:
        """Whether a local web-image corpus is available."""
        return bool(self.index.entries)

    def match(
        self,
        context: ImageContext,
        config: dict[str, Any],
    ) -> dict[str, Any] | None:
        if context.original is None or context.content_hash is None:
            return None
        if not self.index.entries:
            return None

        phash = perceptual_hash(context.fixed)
        dhash = difference_hash(context.fixed)
        embedding = context.embedding(self.embedder) or []
        max_distance = int(config.get("web_hash_hamming_distance", 8))
        minimum_similarity = float(config.get("web_embedding_threshold", 0.92))

        with self.index.lock:
            for entry in self.index.entries:
                if entry.content_hash == context.content_hash:
                    return self._evidence(entry, 1.0, "exact_hash", len(phash))

                distances = max(
                    sum(a != b for a, b in zip(phash, entry.phash)),
                    sum(a != b for a, b in zip(dhash, entry.dhash)),
                )
                if distances <= max_distance:
                    return self._evidence(
                        entry,
                        1.0 - distances / max(1, len(phash)),
                        "phash_dhash",
                        len(phash),
                    )

                similarity = cosine_similarity(embedding, entry.embedding)
                if similarity is not None and similarity >= minimum_similarity:
                    return self._evidence(
                        entry, similarity, "embedding", len(embedding)
                    )

        return None

    @staticmethod
    def _evidence(
        entry: IndexEntry,
        similarity: float,
        layer: str,
        matched_points: int,
    ) -> dict[str, Any]:
        return {
            "matched_household": entry.household_id,
            "matched_month": entry.month,
            "similarity_score": round(similarity, 6),
            "layer": layer,
            "matched_points": matched_points,
        }


class GoogleWebImageMatcher:
    """Optional Google Cloud Vision Web Detection adapter.

    This is an authenticated cloud lookup, not browser scraping of Google
    Lens. The client is imported and created only when this adapter is used.
    """

    @property
    def available(self) -> bool:
        return True

    def match(
        self,
        context: ImageContext,
        config: dict[str, Any],
    ) -> dict[str, Any] | None:
        if context.original is None:
            return None

        try:
            from google.cloud import vision  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "google-cloud-vision is required for Google web detection"
            ) from exc

        buffer = io.BytesIO()
        context.original.save(
            buffer,
            format="JPEG",
            quality=int(config.get("google_upload_quality", 90)),
        )
        client = vision.ImageAnnotatorClient()
        response = client.web_detection(
            image=vision.Image(content=buffer.getvalue())
        )

        detection = response.web_detection
        matches = (
            list(detection.full_matching_images)
            + list(detection.partial_matching_images)
        )
        pages = list(detection.pages_with_matching_images)

        if not matches and not pages:
            return None

        urls = [
            item.url for item in matches if getattr(item, "url", None)
        ]
        page_urls = [
            item.url for item in pages if getattr(item, "url", None)
        ]

        return {
            "provider": "google_cloud_vision_web_detection",
            "layer": "web_detection",
            "similarity_score": None,
            "matched_points": len(matches),
            "matching_urls": urls[:10],
            "matching_pages": page_urls[:10],
            "web_entities": [
                entity.description for entity in detection.web_entities[:10]
            ],
        }


class SerpApiGoogleLensMatcher:
    """Google Lens lookup through SerpApi's upload and image-id APIs.

    The API key is read from an environment variable and is never included in
    evidence, reports, exceptions or logs. The uploaded image ID is temporary
    and only the match metadata is returned to the verification report.
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_key_env: str = "SERPAPI_KEY",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.getenv(api_key_env)
        self.timeout_seconds = timeout_seconds
        self.last_error_code: str | None = None
        self.last_error_detail: str | None = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def _jpeg_bytes(image: Any, max_bytes: int) -> bytes:
        """Encode a small JPEG accepted by SerpApi's 500 KB upload limit."""
        working = image.convert("RGB")

        for quality, scale in (
            (85, 1.0),
            (75, 0.85),
            (65, 0.70),
            (50, 0.55),
        ):
            candidate = working.copy()
            if scale != 1.0:
                candidate.thumbnail(
                    (
                        max(1, int(candidate.width * scale)),
                        max(1, int(candidate.height * scale)),
                    )
                )

            buffer = io.BytesIO()
            candidate.save(
                buffer,
                format="JPEG",
                quality=quality,
                optimize=True,
            )

            if buffer.tell() <= max_bytes:
                return buffer.getvalue()

        raise ValueError(
            "image is too large for the configured SerpApi upload limit"
        )

    def _post_image(self, image_bytes: bytes, boundary: str) -> dict[str, Any]:
        del boundary  # requests generates a valid multipart boundary itself.
        response = requests.post(
            "https://serpapi.com/image",
            files={"image": ("evidence.jpg", image_bytes, "image/jpeg")},
            data={"api_key": self.api_key},
            timeout=self.timeout_seconds,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            response.raise_for_status()
            raise RuntimeError("SerpApi returned invalid JSON for image upload") from exc

        if response.status_code >= 400 or payload.get("error") or not payload.get("image_id"):
            if response.status_code >= 400:
                self.last_error_code = f"http_{response.status_code}"
            self.last_error_detail = str(payload.get("error") or response.text[:500])
            raise RuntimeError("SerpApi image upload failed")

        return payload

    def _search(self, image_id: str) -> dict[str, Any]:
        response = requests.get(
            "https://serpapi.com/search",
            params={
                "engine": "google_lens",
                "image_id": image_id,
                "type": "exact_matches",
                "api_key": self.api_key,
            },
            timeout=self.timeout_seconds,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            response.raise_for_status()
            raise RuntimeError("SerpApi returned invalid JSON for Google Lens") from exc

        if response.status_code >= 400 or payload.get("error"):
            if response.status_code >= 400:
                self.last_error_code = f"http_{response.status_code}"
            self.last_error_detail = str(payload.get("error") or response.text[:500])
            raise RuntimeError("SerpApi Google Lens search failed")

        return payload

    def match(
        self,
        context: ImageContext,
        config: dict[str, Any],
    ) -> dict[str, Any] | None:
        self.last_error_code = None
        self.last_error_detail = None

        if not self.available or context.original is None:
            return None

        max_bytes = int(config.get("serpapi_max_upload_bytes", 500_000))
        image_bytes = self._jpeg_bytes(context.original, max_bytes)

        try:
            upload = self._post_image(
                image_bytes,
                f"evidence-{uuid.uuid4().hex}",
            )
            payload = self._search(str(upload["image_id"]))

        except requests.Timeout as exc:
            self.last_error_code = "timeout"
            self.last_error_detail = str(exc)
            raise RuntimeError("online image lookup timed out") from exc

        except requests.HTTPError as exc:
            self.last_error_code = f"http_{exc.response.status_code if exc.response is not None else 'error'}"
            self.last_error_detail = str(exc)
            raise RuntimeError("online image lookup failed") from exc

        except requests.RequestException as exc:
            self.last_error_code = "network_error"
            self.last_error_detail = str(exc)
            raise RuntimeError("online image lookup failed") from exc

        except (OSError, ValueError, RuntimeError) as exc:
            if self.last_error_code is None:
                self.last_error_code = "service_error"
            self.last_error_detail = str(exc)
            raise RuntimeError("online image lookup failed") from exc

        matches = (
            payload.get("exact_matches")
            or payload.get("visual_matches")
            or []
        )

        if not matches:
            return None

        return {
            "provider": "serpapi_google_lens",
            "layer": (
                "exact_matches"
                if payload.get("exact_matches")
                else "visual_matches"
            ),
            "similarity_score": None,
            "matched_points": len(matches),
            "matching_results": [
                {
                    key: item.get(key)
                    for key in ("title", "source", "link")
                    if item.get(key)
                }
                for item in matches[
                    : int(config.get("serpapi_max_results", 10))
                ]
            ],
        }


class AuthenticityBlock(VerificationBlock):
    """Run advisory screen, local-web and AI-generated checks."""

    name = "authenticity"
    check_codes = (
        "SCREEN_RECAPTURE",
        "AI_GENERATED",
        "WEB_IMAGE_MATCH",
        "AUTHENTICITY_ADVISORY",
    )

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        web_matcher: WebImageMatcher | None = None,
        ai_detector: AIGeneratedDetector | None = None,
    ) -> None:
        self.config = config or {}
        defaults_path = Path(__file__).parent / "config" / "authenticity.yaml"

        try:
            raw_defaults = defaults_path.read_bytes()
            try:
                import yaml  # type: ignore
                defaults = yaml.safe_load(raw_defaults) or {}
            except ImportError:
                defaults = json.loads(raw_defaults.decode("utf-8"))
        except OSError:
            defaults = {"authenticity": {}}

        settings = {
            **defaults.get("authenticity", {}),
            **self.config.get("authenticity", {}),
        }
        self.settings = settings
        self.web_matcher = web_matcher or WebImageMatcher()

        detector_name = str(
            self.settings.get("ai_detector", "huggingface")
        ).lower()

        if ai_detector is not None:
            self.ai_detector = ai_detector
        elif detector_name == "huggingface":
            self.ai_detector = HuggingFaceAIGeneratedDetector(
                model_id=str(
                    self.settings.get(
                        "ai_model_id",
                        "jacoballessio/ai-image-detect-distilled",
                    )
                ),
                device=str(self.settings.get("ai_device", "cpu")),
                generated_class_index=int(
                    self.settings.get("ai_generated_class_index", 0)
                ),
                local_files_only=bool(
                    self.settings.get("ai_local_files_only", False)
                ),
            )
        else:
            self.ai_detector = FakeAIGeneratedDetector()

    def _screen_signal(
        self,
        context: ImageContext,
    ) -> tuple[int | None, dict[str, float] | None, str]:
        if context.fixed is None:
            return None, None, "image unavailable"

        try:
            grayscale = context.fixed.convert("L")
            width, height = grayscale.size
            border = int(self.settings.get("screen_border_width", 4))
            pixels = list(grayscale.getdata())

            interior = [
                pixels[y * width + x]
                for y in range(border, max(border + 1, height - border))
                for x in range(border, max(border + 1, width - border))
            ]

            border_pixels = [
                pixels[y * width + x]
                for y in range(height)
                for x in range(width)
                if (
                    x < border
                    or x >= width - border
                    or y < border
                    or y >= height - border
                )
            ]

            interior_mean = sum(interior) / max(1, len(interior))
            border_mean = sum(border_pixels) / max(1, len(border_pixels))
            border_score = abs(border_mean - interior_mean) / 255.0

            alternating = 0
            comparisons = 0

            for y in range(height):
                for x in range(width - 2):
                    first = (
                        pixels[y * width + x]
                        - pixels[y * width + x + 1]
                    )
                    second = (
                        pixels[y * width + x + 1]
                        - pixels[y * width + x + 2]
                    )

                    if (
                        abs(first) >= 12
                        and abs(second) >= 12
                        and first * second < 0
                    ):
                        alternating += 1

                    comparisons += 1

            moire_score = alternating / max(1, comparisons)
            border_threshold = float(
                self.settings.get("screen_border_score", 0.25)
            )
            moire_threshold = float(
                self.settings.get("screen_moire_score", 0.18)
            )
            moire_enabled = bool(
                self.settings.get("screen_moire_enabled", True)
            )

            suspicious = (
                border_score >= border_threshold
                or moire_enabled and moire_score >= moire_threshold
            )

            raw = {
                "border_score": border_score,
                "moire_score": moire_score,
            }

            return (
                0 if suspicious else 1,
                raw,
                (
                    "screen border or moire score indicates a screen recapture"
                    if suspicious
                    else "no strong screen border or moire signal"
                ),
            )

        except (AttributeError, ValueError, ZeroDivisionError) as exc:
            return None, None, f"screen signal unavailable: {exc}"

    async def run(self, context: ImageContext) -> BlockResult:
        """Return advisory checks; no result is critical."""
        advisory = "advisory"

        if context.load_error or context.original is None:
            return BlockResult(
                self.name,
                [
                    CheckResult(
                        code,
                        None,
                        context.load_error or "image unavailable",
                        severity=(
                            "review"
                            if code == "AUTHENTICITY_ADVISORY"
                            else advisory
                        ),
                    )
                    for code in self.check_codes
                ],
            )

        if self.settings.get("screen_enabled", True):
            screen_value, screen_score, screen_reason = self._screen_signal(
                context
            )
        else:
            screen_value, screen_score, screen_reason = (
                None,
                None,
                "screen signal disabled",
            )

        checks: list[CheckResult] = [
            CheckResult(
                "SCREEN_RECAPTURE",
                screen_value,
                screen_reason,
                raw_measure=screen_score,
                threshold={
                    "border_score": self.settings.get("screen_border_score"),
                    "moire_score": self.settings.get("screen_moire_score"),
                },
                severity=advisory,
            )
        ]

        ai_value: int | None = None
        ai_probability: float | None = None
        ai_reason = "AI-generation signal unavailable"
        ai_error_code: str | None = None

        if self.settings.get("ai_generated_enabled", True):
            try:
                prediction = await asyncio.to_thread(
                    self.ai_detector.predict,
                    context.fixed,
                )
                ai_probability = prediction.generated_probability
                ai_value = (
                    0
                    if ai_probability
                    >= float(self.settings.get("ai_generated_threshold", 0.70))
                    else 1
                )
                ai_reason = (
                    "AI-generation probe found a suspicious score"
                    if ai_value == 0
                    else "AI-generation probe did not find a suspicious score"
                )

            except ImportError:
                ai_error_code = "dependencies_missing"
            except OSError:
                ai_error_code = "model_unavailable"
            except (RuntimeError, ValueError, TypeError):
                ai_error_code = "detector_error"

        if ai_error_code:
            ai_reason = (
                "AI-generation signal unavailable: "
                + {
                    "dependencies_missing": "detector dependencies are not installed",
                    "model_unavailable": "model files could not be loaded",
                    "detector_error": "detector could not complete",
                }.get(ai_error_code, "detector error")
            )

        ai_evidence = {
            "method": getattr(
                self.ai_detector,
                "__class__",
                type(self.ai_detector),
            ).__name__
        }

        if ai_error_code:
            ai_evidence["error_code"] = ai_error_code

        if ai_probability is not None:
            ai_evidence["model"] = (
                getattr(self.ai_detector, "model_id", None)
                or "configured_detector"
            )

        checks.append(
            CheckResult(
                "AI_GENERATED",
                ai_value,
                ai_reason,
                raw_measure=ai_probability,
                threshold=self.settings.get("ai_generated_threshold"),
                evidence=ai_evidence,
                severity=advisory,
            )
        )

        web_match = None
        web_available = bool(
            self.settings.get("web_match_enabled", True)
            and getattr(self.web_matcher, "available", False)
        )
        web_error_code: str | None = None

        if web_available:
            try:
                web_match = await asyncio.to_thread(
                    self.web_matcher.match,
                    context,
                    self.settings,
                )
            except TimeoutError:
                web_error_code = "timeout"
            except (OSError, ValueError, RuntimeError):
                web_error_code = (
                    getattr(self.web_matcher, "last_error_code", None)
                    or "service_error"
                )

        web_provider = getattr(
            self.web_matcher,
            "__class__",
            type(self.web_matcher),
        ).__name__

        if not web_available:
            web_reason = (
                "online image signal unavailable: API key or provider "
                "is not configured"
            )
        elif web_error_code:
            web_reason = (
                "online image lookup unavailable: "
                + {
                    "timeout": "request timed out",
                    "network_error": "network error",
                    "http_401": "authentication failed",
                    "http_403": "access was denied",
                    "http_429": "rate limit reached",
                    "service_error": "provider error",
                }.get(web_error_code, "provider error")
            )
        elif web_match:
            web_reason = "image matches the configured online image search"
        else:
            web_reason = "online image search completed with no match"

        web_evidence = {
            **(web_match or {}),
            "matcher": web_provider,
        }

        if web_error_code:
            web_evidence["error_code"] = web_error_code

        checks.append(
            CheckResult(
                "WEB_IMAGE_MATCH",
                (
                    0
                    if web_match
                    else 1
                    if web_available and not web_error_code
                    else None
                ),
                web_reason,
                evidence=web_evidence,
                severity=advisory,
            )
        )

        available = [check for check in checks if check.value is not None]
        suspicious = [check for check in available if check.value == 0]

        confidence_values = [
            abs(float(check.raw_measure))
            for check in available
            if isinstance(check.raw_measure, (int, float))
        ]

        combined_confidence = (
            sum(confidence_values) / len(confidence_values)
            if confidence_values
            else None
        )

        combined_value = (
            None
            if not available
            else (0 if suspicious else 1)
        )

        checks.append(
            CheckResult(
                "AUTHENTICITY_ADVISORY",
                combined_value,
                (
                    "one or more advisory authenticity signals are suspicious"
                    if suspicious
                    else "available authenticity signals look genuine"
                    if available
                    else "no authenticity signal could run"
                ),
                raw_measure=combined_confidence,
                threshold=None,
                evidence={
                    "available_signals": [
                        check.check_code for check in available
                    ],
                    "missing_signals": [
                        check.check_code
                        for check in checks
                        if check.value is None
                    ],
                    "manual_review_required": bool(suspicious),
                },
                severity=advisory,
            )
        )

        return BlockResult(self.name, checks)
