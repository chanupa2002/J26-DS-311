"""Block 5: last-month comparison and non-critical progress hints."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .blocks import VerificationBlock
from .contracts import BlockResult, CheckResult, ImageInput
from .duplicate import DuplicateBlock, cosine_similarity, difference_hash, perceptual_hash
from .duplicate_index import IndexEntry
from .embedder import Embedder, FakeEmbedder
from .image_loader import ImageContext, load_context
from .monitoring_repository import MonitoringRecord, MonitoringRepository


@dataclass(slots=True)
class ChangePrediction:
    """Optional externally supplied livelihood progress prediction."""

    label: str
    strength: float
    evidence: dict[str, Any]


class ChangeDetector(ABC):
    """Interface for an optional object/change detector."""

    @abstractmethod
    def predict(self, previous: Any, current: Any, category: str) -> ChangePrediction:
        """Predict a progress label and strength."""


class FakeChangeDetector(ChangeDetector):
    """Offline detector used by tests."""

    def __init__(self, label: str = "same", strength: float = 0.0) -> None:
        self.prediction = ChangePrediction(label, strength, {"method": "fake"})

    def predict(self, previous: Any, current: Any, category: str) -> ChangePrediction:
        del previous, current, category
        return self.prediction


class DirectionalProgressScorer(ABC):
    """Optional interface for category-specific CLIP direction scoring."""

    @abstractmethod
    def score(self, previous: Any, current: Any, category: str) -> ChangePrediction:
        """Score progress along a category-specific direction."""


def _ssim(previous: Any, current: Any, config: dict[str, Any]) -> float | None:
    """Compute a dependency-free global SSIM approximation."""
    try:
        size = tuple(config.get("comparison_size", [128, 128]))
        left = list(previous.convert("L").resize(size).getdata())
        right = list(current.convert("L").resize(size).getdata())
        mean_left = sum(left) / len(left)
        mean_right = sum(right) / len(right)
        covariance = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right)) / len(left)
        variance_left = sum((value - mean_left) ** 2 for value in left) / len(left)
        variance_right = sum((value - mean_right) ** 2 for value in right) / len(right)
        c1 = float(config.get("ssim_c1", 6.5025))
        c2 = float(config.get("ssim_c2", 58.5225))
        value = ((2 * mean_left * mean_right + c1) * (2 * covariance + c2)) / ((mean_left**2 + mean_right**2 + c1) * (variance_left + variance_right + c2))
        return max(0.0, min(1.0, value))
    except (AttributeError, TypeError, ValueError, ZeroDivisionError):
        return None


class SimilarityBlock(VerificationBlock):
    """Compare consecutive household photos without making a benefit decision."""

    name = "similarity_change"
    check_codes = ("SIMILARITY_SCORE", "SAME_PLACE", "PROGRESS", "PROGRESS_NOT_DECLINED")

    def __init__(self, embedder: Embedder | None = None, config: dict[str, Any] | None = None, change_detector: ChangeDetector | None = None, directional_scorer: DirectionalProgressScorer | None = None, repository: MonitoringRepository | None = None) -> None:
        self.embedder = embedder or FakeEmbedder()
        self.config = config or {}
        self.settings = self.config.get("similarity_change", {})
        self.change_detector = change_detector
        self.directional_scorer = directional_scorer
        self.repository = repository

    def _null_result(self, reason: str) -> BlockResult:
        return BlockResult(self.name, [
            CheckResult("SIMILARITY_SCORE", None, reason, severity="info"),
            CheckResult("SAME_PLACE", None, reason, severity="info"),
            CheckResult("PROGRESS", None, reason, severity="info"),
            CheckResult("PROGRESS_NOT_DECLINED", None, reason, severity="review"),
        ])

    def _same_place(self, previous: ImageContext, current: ImageContext) -> tuple[float | None, bool | None, dict[str, Any]]:
        previous_embedding = previous.embedding(self.embedder)
        current_embedding = current.embedding(self.embedder)
        score = cosine_similarity(previous_embedding or [], current_embedding or [])
        evidence: dict[str, Any] = {"embedding_similarity": score}
        if score is None:
            return None, None, evidence
        threshold = float(self.settings.get("same_place_embedding_threshold", 0.75))
        embedding_pass = score >= threshold
        if not self.settings.get("feature_matching_enabled", True):
            evidence["local_feature_matching"] = "disabled"
            return score, embedding_pass, evidence

        previous_orb = DuplicateBlock._orb_features(previous.fixed)
        current_orb = DuplicateBlock._orb_features(current.fixed)
        previous_entry = IndexEntry(
            household_id="previous",
            month="previous",
            content_hash="",
            phash=perceptual_hash(previous.fixed),
            dhash=difference_hash(previous.fixed),
            embedding=previous_embedding or [],
            keypoints=previous_orb[0],
            descriptors=previous_orb[1],
            image_size=previous_orb[2],
            feature_metadata=previous_orb[3],
        )
        local_match = DuplicateBlock._feature_match(
            current_orb,
            previous_entry,
            float(self.settings.get("feature_inlier_ratio_threshold", 0.35)),
        )
        if local_match is None:
            evidence["local_feature_matching"] = "unavailable_or_below_threshold"
            return score, embedding_pass, evidence
        evidence["local_feature_matching"] = "orb_ransac"
        evidence["inlier_ratio"] = round(local_match[0], 6)
        evidence["matched_points"] = local_match[1]
        return score, embedding_pass, evidence

    def _previous_source(self, context: ImageContext) -> tuple[Any | None, MonitoringRecord | None, str | None]:
        """Resolve the previous photo from the request or monitoring repository."""
        explicit = context.image_input.previous_image
        if explicit is not None:
            return explicit, None, None
        if self.repository is None:
            return None, None, "no previous photo is available"
        record = self.repository.latest_previous(context.image_input.household_id, context.image_input.month)
        if record is None:
            return None, None, "no previous photo is available for this household"
        image_bytes = self.repository.read_image(record)
        if not image_bytes:
            return None, record, "the previous monitoring record exists but its image could not be read"
        return image_bytes, record, None

    def _progress(self, previous: ImageContext, current: ImageContext, category: str, ssim: float | None) -> ChangePrediction:
        if self.change_detector:
            return self.change_detector.predict(previous.fixed, current.fixed, category)
        if self.directional_scorer:
            return self.directional_scorer.score(previous.fixed, current.fixed, category)
        if ssim is None:
            return ChangePrediction("not_comparable", 0.0, {"method": "ssim_unavailable"})
        same_threshold = float(self.settings.get("ssim_same_threshold", 0.88))
        if ssim >= same_threshold:
            return ChangePrediction("same", max(0.0, min(1.0, ssim)), {"method": "ssim", "ssim": ssim})
        return ChangePrediction("declined", max(0.0, min(1.0, 1.0 - ssim)), {"method": "ssim", "ssim": ssim})

    async def run(self, context: ImageContext) -> BlockResult:
        """Compare with the previous image and emit only information/review hints."""
        previous_source, previous_record, source_error = self._previous_source(context)
        if previous_source is None:
            return self._null_result(source_error or "no previous photo is available")
        previous_input = ImageInput(previous_source, context.image_input.household_id, "previous", context.image_input.registered_category, metadata=context.image_input.metadata)
        previous = load_context(previous_input, int(self.config.get("image", {}).get("fixed_longest_side", 512)))
        if context.load_error or previous.load_error or context.original is None or previous.original is None:
            return self._null_result(context.load_error or previous.load_error or "one photo could not be loaded")
        category = context.image_input.registered_category or ""
        meaningful_categories = set(self.settings.get("visually_meaningful_categories", []))
        score, same_place, gate_evidence = self._same_place(previous, context)
        if category not in meaningful_categories:
            same_place = None
            reason = "progress is not comparable for this livelihood category"
        elif same_place is False:
            reason = "photos appear to show different places"
        else:
            reason = "photos appear to show the same place" if same_place else "same-place signal is unavailable"
        zone_limits = self.settings.get("zone_limits", {})
        if score is None:
            zone = "unknown"
        elif score >= float(zone_limits.get("very_similar", 0.95)):
            zone = "very_similar"
        elif score >= float(zone_limits.get("same_place", 0.75)):
            zone = "same_place"
        else:
            zone = "different_place"
        if previous_record is not None:
            gate_evidence = {**gate_evidence, "matched_month": previous_record.entry.month}
        score_check = CheckResult("SIMILARITY_SCORE", None, f"similarity zone: {zone}", raw_measure=score, threshold=zone_limits, evidence={**gate_evidence, "zone": zone}, severity="info")
        same_check = CheckResult("SAME_PLACE", None if same_place is None else (1 if same_place else 0), reason, raw_measure=score, threshold=self.settings.get("same_place_embedding_threshold"), evidence=gate_evidence, severity="review" if same_place is False else "info")
        if same_place is not True:
            return BlockResult(self.name, [score_check, same_check, CheckResult("PROGRESS", None, "progress is not comparable", evidence={"label": "not_comparable", "strength": 0.0}, severity="info"), CheckResult("PROGRESS_NOT_DECLINED", None, "progress is not comparable", evidence={}, severity="review")])
        ssim = _ssim(previous.fixed, context.fixed, self.settings) if self.settings.get("ssim_enabled", True) else None
        prediction = self._progress(previous, context, category, ssim)
        valid_labels = {"improved", "same", "declined", "not_comparable"}
        label = prediction.label if prediction.label in valid_labels else "not_comparable"
        progress_check = CheckResult("PROGRESS", None, f"progress label: {label}", raw_measure=prediction.strength, evidence={**prediction.evidence, "label": label, "strength": prediction.strength}, severity="review" if label == "declined" else "info")
        not_declined = None if label == "not_comparable" else (0 if label == "declined" else 1)
        not_declined_check = CheckResult("PROGRESS_NOT_DECLINED", not_declined, "decline is a review hint only" if label == "declined" else "progress is same or improved", raw_measure=prediction.strength, evidence={"label": label, "strength": prediction.strength}, severity="review" if label == "declined" else "info")
        return BlockResult(self.name, [score_check, same_check, progress_check, not_declined_check])
