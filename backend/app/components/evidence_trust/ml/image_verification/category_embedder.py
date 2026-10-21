
"""Embedding-backed category classifiers for livelihood relevance."""

from __future__ import annotations

import json
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class CategoryPrediction:
    """Raw category probabilities and optional embedding evidence."""

    probabilities: dict[str, float]
    logits: dict[str, float] | None = None
    method: str = "unknown"


class CategoryEmbedder(ABC):
    """Interface hiding zero-shot/probe/prototype model choices from blocks."""

    @abstractmethod
    def predict(
        self,
        image: Any,
        categories: list[str],
        prompts: dict[str, list[str]],
    ) -> CategoryPrediction:
        """Predict category scores for one image."""


class FakeCategoryEmbedder(CategoryEmbedder):
    """Deterministic classifier for tests without models or network access."""

    def __init__(
        self,
        scores: dict[str, float] | None = None,
        method: str = "fake",
    ) -> None:
        self.scores = dict(scores or {})
        self.method = method
        self.calls = 0

    def predict(
        self,
        image: Any,
        categories: list[str],
        prompts: dict[str, list[str]],
    ) -> CategoryPrediction:
        del image, prompts
        self.calls += 1

        values = {
            category: float(self.scores.get(category, 0.0))
            for category in categories
        }

        if not any(values.values()):
            values = {
                category: 1.0 / len(categories)
                for category in categories
            }

        total = sum(max(0.0, value) for value in values.values()) or 1.0
        probabilities = {
            category: max(0.0, value) / total
            for category, value in values.items()
        }
        logits = {
            category: math.log(max(probability, 1e-12))
            for category, probability in probabilities.items()
        }

        return CategoryPrediction(probabilities, logits, self.method)


class LinearProbeCategoryEmbedder(CategoryEmbedder):
    """Classify frozen embeddings with supplied linear-probe weights."""

    def __init__(
        self,
        embedder: Any,
        weights: dict[str, list[float]],
        biases: dict[str, float] | None = None,
    ) -> None:
        self.embedder = embedder
        self.weights = weights
        self.biases = biases or {}

    def predict(
        self,
        image: Any,
        categories: list[str],
        prompts: dict[str, list[str]],
    ) -> CategoryPrediction:
        del prompts
        vector = self.embedder.embed(image)

        logits = {
            category: (
                sum(
                    a * b
                    for a, b in zip(
                        vector,
                        self.weights.get(category, []),
                    )
                )
                + self.biases.get(category, 0.0)
            )
            for category in categories
        }

        maximum = max(logits.values()) if logits else 0.0
        denominator = sum(
            math.exp(value - maximum)
            for value in logits.values()
        ) or 1.0

        probabilities = {
            category: math.exp(value - maximum) / denominator
            for category, value in logits.items()
        }

        return CategoryPrediction(
            probabilities=probabilities,
            logits=logits,
            method="linear_probe",
        )


class PrototypeCategoryEmbedder(CategoryEmbedder):
    """Classify frozen embeddings by cosine similarity to prototypes."""

    def __init__(
        self,
        embedder: Any,
        prototypes: dict[str, list[float]],
    ) -> None:
        self.embedder = embedder
        self.prototypes = prototypes

    def predict(
        self,
        image: Any,
        categories: list[str],
        prompts: dict[str, list[str]],
    ) -> CategoryPrediction:
        del prompts
        vector = self.embedder.embed(image)
        vector_norm = math.sqrt(sum(value * value for value in vector)) or 1.0

        logits: dict[str, float] = {}

        for category in categories:
            prototype = self.prototypes.get(category, [])
            prototype_norm = (
                math.sqrt(sum(value * value for value in prototype)) or 1.0
            )
            logits[category] = sum(
                left * right
                for left, right in zip(vector, prototype)
            ) / (vector_norm * prototype_norm)

        maximum = max(logits.values()) if logits else 0.0
        denominator = sum(
            math.exp(value - maximum)
            for value in logits.values()
        ) or 1.0

        probabilities = {
            category: math.exp(value - maximum) / denominator
            for category, value in logits.items()
        }

        return CategoryPrediction(
            probabilities=probabilities,
            logits=logits,
            method="prototype",
        )


class OpenClipCategoryEmbedder(CategoryEmbedder):
    """Lazy OpenCLIP adapter; importing this class does not load a model."""

    def __init__(
        self,
        model_name: str = "ViT-B-32",
        pretrained: str = "laion2b_s34b_b79k",
    ) -> None:
        self.model_name = model_name
        self.pretrained = pretrained
        self._model: Any = None
        self._tokenizer: Any = None
        self._preprocess: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return

        try:
            import open_clip
        except ImportError as exc:
            raise RuntimeError(
                "OpenCLIP is optional; install open_clip_torch "
                "to use the real category embedder"
            ) from exc

        self._model, _, self._preprocess = (
            open_clip.create_model_and_transforms(
                self.model_name,
                pretrained=self.pretrained,
            )
        )
        self._tokenizer = open_clip.get_tokenizer(self.model_name)
        self._model.eval()

    def predict(
        self,
        image: Any,
        categories: list[str],
        prompts: dict[str, list[str]],
    ) -> CategoryPrediction:
        self._load()
        import torch

        prompt_text = [
            prompt
            for category in categories
            for prompt in prompts.get(
                category,
                [f"a photo of {category}"],
            )
        ]

        with torch.no_grad():
            image_features = self._model.encode_image(
                self._preprocess(image).unsqueeze(0)
            )
            text_features = self._model.encode_text(
                self._tokenizer(prompt_text)
            )

            image_features = image_features / image_features.norm(
                dim=-1,
                keepdim=True,
            ).clamp_min(1e-12)
            text_features = text_features / text_features.norm(
                dim=-1,
                keepdim=True,
            ).clamp_min(1e-12)

            similarities = (
                100.0 * image_features @ text_features.T
            ).squeeze(0).tolist()

        raw: dict[str, list[float]] = {
            category: [] for category in categories
        }
        cursor = 0

        for category in categories:
            prompt_count = len(
                prompts.get(category, [f"a photo of {category}"])
            )
            raw[category] = similarities[
                cursor:cursor + prompt_count
            ]
            cursor += prompt_count

        logits = {
            category: sum(values) / max(1, len(values))
            for category, values in raw.items()
        }

        maximum = max(logits.values()) if logits else 0.0
        denominator = sum(
            math.exp(value - maximum)
            for value in logits.values()
        ) or 1.0

        probabilities = {
            category: math.exp(value - maximum) / denominator
            for category, value in logits.items()
        }

        return CategoryPrediction(
            probabilities,
            logits,
            "openclip_zero_shot",
        )


class FineTunedCategoryEmbedder(CategoryEmbedder):
    """Lazy loader for the locally trained CLIP + LoRA classifier."""

    def __init__(
        self,
        artifact_path: str | Path,
        device: str = "cpu",
        normalize_embeddings: bool = False,
        fallback: CategoryEmbedder | None = None,
        fallback_categories: set[str] | None = None,
    ) -> None:
        self.artifact_path = Path(artifact_path)
        self.device_name = device
        self.normalize_embeddings = normalize_embeddings
        self.fallback = fallback
        self.fallback_categories = fallback_categories or set()

        self._processor: Any | None = None
        self._model: Any | None = None
        self._weight: Any | None = None
        self._bias: Any | None = None
        self._torch: Any | None = None
        self._device: Any | None = None

        self.class_mapping = self._read_class_mapping()
        self.supported_categories = tuple(self.class_mapping.values())

        if sorted(self.class_mapping) != list(range(len(self.class_mapping))):
            raise RuntimeError(
                "Category class mapping must use contiguous IDs starting at 0"
            )

    def _read_class_mapping(self) -> dict[int, str]:
        path = self.artifact_path / "class_mapping.json"

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))

            if not isinstance(payload, dict):
                raise ValueError("Class mapping must be a JSON object")

            mapping = {
                int(index): str(category)
                for index, category in payload.items()
            }

            if len(set(mapping.values())) != len(mapping):
                raise ValueError("Class mapping contains duplicate categories")

            return mapping

        except (OSError, ValueError, TypeError, AttributeError) as exc:
            raise RuntimeError(
                "Category model class mapping is unavailable or invalid"
            ) from exc

    @staticmethod
    def _classifier_state(checkpoint: Any) -> tuple[Any, Any]:
        state = (
            checkpoint.get("state_dict", checkpoint)
            if isinstance(checkpoint, dict)
            else checkpoint
        )

        if not isinstance(state, dict):
            raise RuntimeError(
                "Category classifier artifact has an unsupported format"
            )

        weight = next(
            (
                value
                for key, value in state.items()
                if str(key).lower().endswith("weight")
                and getattr(value, "ndim", 0) == 2
            ),
            None,
        )
        bias = next(
            (
                value
                for key, value in state.items()
                if str(key).lower().endswith("bias")
                and getattr(value, "ndim", 0) == 1
            ),
            None,
        )

        if weight is None or bias is None:
            raise RuntimeError(
                "Category classifier weight or bias is missing"
            )

        return weight, bias

    def _load(self) -> None:
        if self._model is not None:
            return

        try:
            import torch
            from peft import LoraConfig, get_peft_model
            from safetensors.torch import load_file
            from transformers import (
                CLIPConfig,
                CLIPImageProcessor,
                CLIPModel,
                CLIPProcessor,
                CLIPTokenizer,
            )
        except ImportError as exc:
            raise RuntimeError(
                "torch, transformers, peft, and safetensors are required "
                "for the fine-tuned category model"
            ) from exc

        model_path = self.artifact_path / "lora_adapter"
        processor_path = self.artifact_path / "processor"
        checkpoint_path = model_path / "model.safetensors"
        classifier_path = self.artifact_path / "classifier.pt"

        required_paths = [
            model_path / "config.json",
            checkpoint_path,
            processor_path / "processor_config.json",
            classifier_path,
        ]

        missing_paths = [
            str(path)
            for path in required_paths
            if not path.is_file()
        ]
        if missing_paths:
            raise RuntimeError(
                f"Fine-tuned category model artifacts are missing: "
                f"{missing_paths}"
            )

        # Reconstruct the CLIP architecture from the saved configuration.
        config = CLIPConfig.from_pretrained(
            model_path,
            local_files_only=True,
        )
        model = CLIPModel(config)

        # Training attached LoRA to the vision encoder only.
        model.vision_model = get_peft_model(
            model.vision_model,
            LoraConfig(
                r=8,
                lora_alpha=16,
                target_modules=["q_proj", "v_proj"],
                lora_dropout=0.1,
                bias="none",
            ),
        )

        # Restore the complete CLIP + LoRA state.
        state = load_file(
            str(checkpoint_path),
            device="cpu",
        )
        result = model.load_state_dict(state, strict=True)

        if result.missing_keys or result.unexpected_keys:
            raise RuntimeError(
                "Saved CLIP + LoRA weights do not match the model. "
                f"Missing: {result.missing_keys}; "
                f"unexpected: {result.unexpected_keys}"
            )

        # Restore the matching processor, including compatibility fallback.
        try:
            processor = CLIPProcessor.from_pretrained(
                processor_path,
                local_files_only=True,
            )
        except (OSError, ValueError, KeyError):
            processor_config = json.loads(
                (processor_path / "processor_config.json").read_text(
                    encoding="utf-8"
                )
            )
            processor = CLIPProcessor(
                image_processor=CLIPImageProcessor(
                    **processor_config["image_processor"]
                ),
                tokenizer=CLIPTokenizer.from_pretrained(
                    processor_path,
                    local_files_only=True,
                ),
            )

        # Load the separate seven-class linear head.
        try:
            checkpoint = torch.load(
                classifier_path,
                map_location="cpu",
                weights_only=True,
            )
        except TypeError:
            checkpoint = torch.load(
                classifier_path,
                map_location="cpu",
            )

        weight, bias = self._classifier_state(checkpoint)

        if int(weight.shape[0]) != len(self.class_mapping):
            raise RuntimeError(
                "Classifier output dimension does not match class mapping"
            )

        if int(weight.shape[1]) != int(config.projection_dim):
            raise RuntimeError(
                "Classifier input dimension does not match CLIP projection "
                "dimension"
            )

        if int(bias.shape[0]) != int(weight.shape[0]):
            raise RuntimeError(
                "Classifier bias dimension does not match classifier weight"
            )

        device = torch.device(self.device_name)
        model.to(device)
        model.eval()

        self._model = model
        self._processor = processor
        self._weight = weight.to(device)
        self._bias = bias.to(device)
        self._torch = torch
        self._device = device

    def predict(
        self,
        image: Any,
        categories: list[str],
        prompts: dict[str, list[str]],
    ) -> CategoryPrediction:
        """Predict using the trained image encoder and linear head."""
        del prompts
        self._load()

        assert self._processor is not None
        assert self._model is not None
        assert self._weight is not None
        assert self._bias is not None
        assert self._torch is not None
        assert self._device is not None

        inputs = self._processor(
            images=image,
            return_tensors="pt",
        )
        pixel_values = inputs["pixel_values"].to(self._device)

        with self._torch.no_grad():
            # Match the notebook's training-time embedding extraction.
            vision_output = self._model.vision_model(
                pixel_values=pixel_values
            )
            pooled_output = vision_output.pooler_output
            features = self._model.visual_projection(pooled_output)

            # Training used unnormalized embeddings by default.
            if self.normalize_embeddings:
                features = features / features.norm(
                    dim=-1,
                    keepdim=True,
                ).clamp_min(1e-12)

            logits_tensor = features @ self._weight.T + self._bias
            logits_values = logits_tensor[0]
            probabilities_tensor = self._torch.softmax(
                logits_values,
                dim=-1,
            )

        logits = {
            self.class_mapping[index]: float(
                logits_values[index].detach().cpu().item()
            )
            for index in range(len(self.class_mapping))
            if self.class_mapping[index] in categories
        }

        probabilities = {
            self.class_mapping[index]: float(
                probabilities_tensor[index].detach().cpu().item()
            )
            for index in range(len(self.class_mapping))
            if self.class_mapping[index] in categories
        }

        return CategoryPrediction(
            probabilities=probabilities,
            logits=logits,
            method="fine_tuned_clip_artifact",
        )

    def predict_fallback(
        self,
        image: Any,
        categories: list[str],
        prompts: dict[str, list[str]],
    ) -> CategoryPrediction:
        """Use the configured zero-shot fallback for unsupported categories."""
        if self.fallback is None:
            raise RuntimeError("No category fallback is configured")

        return self.fallback.predict(image, categories, prompts)


def build_category_embedder(
    config: dict[str, Any] | None = None,
) -> CategoryEmbedder:
    """Build the configured embedder without loading model weights."""
    settings = (config or {}).get("category_match", {})
    provider = str(
        settings.get("provider", "fine_tuned_artifact")
    ).lower()

    if provider == "openclip":
        return OpenClipCategoryEmbedder(
            str(settings.get("model_name", "ViT-B-32")),
            str(settings.get("pretrained", "laion2b_s34b_b79k")),
        )

    if provider == "fine_tuned_artifact":
        default_path = (
            Path(__file__).parent
            / "model_artifacts"
            / "category_relevance_model"
        )

        fallback = None
        if bool(settings.get("transport_zero_shot_enabled", True)):
            fallback = OpenClipCategoryEmbedder(
                str(settings.get("fallback_model_name", "ViT-B-32")),
                str(
                    settings.get(
                        "fallback_pretrained",
                        "laion2b_s34b_b79k",
                    )
                ),
            )

        return FineTunedCategoryEmbedder(
            settings.get("artifact_path", str(default_path)),
            str(settings.get("device", "cpu")),
            bool(settings.get("normalize_embeddings", False)),
            fallback=fallback,
            fallback_categories={"TRANSPORT & LOGISTICS"},
        )

    return FakeCategoryEmbedder()
