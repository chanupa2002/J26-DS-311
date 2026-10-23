"""Block 3: livelihood category relevance and calibrated abstention."""

from __future__ import annotations

import math
from typing import Any

from .blocks import VerificationBlock
from .category_embedder import CategoryEmbedder, FakeCategoryEmbedder
from .contracts import BlockResult, CheckResult
from .image_loader import ImageContext


def temperature_scale(logits: dict[str, float], temperature: float) -> dict[str, float]:
    """Convert logits to calibrated probabilities using temperature scaling."""
    if not logits:
        return {}
    temperature = max(float(temperature), 1e-6)
    scaled = {category: value / temperature for category, value in logits.items()}
    maximum = max(scaled.values())
    denominator = sum(math.exp(value - maximum) for value in scaled.values())
    return {category: math.exp(value - maximum) / denominator for category, value in scaled.items()}


def _top_two(probabilities: dict[str, float]) -> list[dict[str, Any]]:
    return [{"category": category, "probability": round(probability, 6)} for category, probability in sorted(probabilities.items(), key=lambda item: item[1], reverse=True)[:2]]


class CategoryMatchBlock(VerificationBlock):
    """Classify livelihood relevance while abstaining when evidence is weak."""

    name = "category_match"
    check_codes = ("CATEGORY_MATCH",)

    def __init__(self, embedder: CategoryEmbedder | None = None, config: dict[str, Any] | None = None) -> None:
        self.embedder = embedder or FakeCategoryEmbedder()
        self.config = config or {}

    def _settings(self) -> dict[str, Any]:
        return self.config.get("category_match", {})

    async def run(self, context: ImageContext) -> BlockResult:
        """Return one category check without denying any benefit."""
        settings = self._settings()
        categories = list(settings.get("categories", []))
        prompts = dict(settings.get("prompts", {}))
        registered = context.image_input.registered_category
        if context.load_error or context.original is None:
            return BlockResult(self.name, [CheckResult("CATEGORY_MATCH", None, context.load_error or "image unavailable", severity="review")])
        if not registered:
            return BlockResult(self.name, [CheckResult("CATEGORY_MATCH", None, "registered livelihood category is missing", severity="review")])
        if registered not in categories:
            return BlockResult(self.name, [CheckResult("CATEGORY_MATCH", None, "registered livelihood category is not configured", severity="review")])
        other = str(settings.get("other_category", "OTHER"))
        if registered == other:
            return BlockResult(self.name, [CheckResult("CATEGORY_MATCH", None, "OTHER is an abstention category; officer manual review is required", evidence={"manual_review_required": True, "registered_category": registered}, severity="review")])
        supported = getattr(self.embedder, "supported_categories", None)
        fallback_used = False
        if supported is not None and registered not in supported:
            if registered != "TRANSPORT & LOGISTICS" or not hasattr(self.embedder, "predict_fallback"):
                return BlockResult(self.name, [CheckResult("CATEGORY_MATCH", None, "registered livelihood category is not present in the trained model mapping", evidence={"supported_categories": list(supported), "registered_category": registered}, severity="review")])
            try:
                prediction = self.embedder.predict_fallback(context.fixed, categories, prompts)
                fallback_used = True
            except Exception:
                return BlockResult(self.name, [CheckResult("CATEGORY_MATCH", None, "Transport fallback model is unavailable; officer manual review is required", evidence={"registered_category": registered, "fallback": "zero_shot_openclip"}, severity="review")])
        else:
            try:
                prediction = self.embedder.predict(context.fixed, categories, prompts)
            except Exception as exc:
                return BlockResult(self.name, [CheckResult("CATEGORY_MATCH", None, "category model unavailable", evidence={"error": str(exc)}, severity="review")], error=str(exc))
        probabilities = prediction.probabilities
        if prediction.logits:
            probabilities = temperature_scale(prediction.logits, float(settings.get("temperature", 1.5)))
        ordered = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
        predicted, confidence = ordered[0]
        second_probability = ordered[1][1] if len(ordered) > 1 else 0.0
        margin = confidence - second_probability
        registered_probability = probabilities.get(registered, 0.0)
        evidence = {"predicted_category": predicted, "top_2": _top_two(probabilities), "calibrated_confidence": round(confidence, 6), "probabilities": probabilities, "method": prediction.method, "registered_category": registered, "fallback": "zero_shot_openclip" if fallback_used else None}
        low_confidence = confidence < float(settings.get("unclear_confidence", 0.55))
        overlapping = margin < float(settings.get("unclear_margin", 0.10))
        if predicted == other:
            evidence["manual_review_required"] = True
            return BlockResult(self.name, [CheckResult("CATEGORY_MATCH", None, "model abstained as OTHER; officer manual review required", raw_measure=confidence, threshold=settings.get("unclear_confidence"), evidence=evidence, severity="review")])
        relevant_threshold = float(settings.get("relevant_probability", 0.55))
        # A matching prediction with sufficient confidence is positive evidence.
        # Evaluate it before the generic ambiguity branch so a valid livelihood
        # match is not turned into a review flag merely because another class is
        # close behind it.
        if predicted == registered and confidence >= relevant_threshold and not low_confidence:
            evidence["accepted_matching_prediction"] = True
            return BlockResult(self.name, [CheckResult("CATEGORY_MATCH", 1, "photo matches the registered livelihood category with sufficient confidence", raw_measure=registered_probability, threshold=relevant_threshold, evidence=evidence)])
        if low_confidence or overlapping:
            return BlockResult(self.name, [CheckResult("CATEGORY_MATCH", None, "category evidence is unclear after calibration", raw_measure=confidence, threshold=settings.get("unclear_confidence"), evidence=evidence, severity="review")])
        unrelated = set(settings.get("unrelated_categories", []))
        if predicted in unrelated and confidence >= float(settings.get("not_relevant_confidence", 0.70)):
            return BlockResult(self.name, [CheckResult("CATEGORY_MATCH", 0, f"photo appears to show {predicted}, not the registered livelihood", raw_measure=registered_probability, threshold=settings.get("relevant_probability"), evidence=evidence, severity="review")])
        if predicted != registered and confidence >= float(settings.get("not_relevant_confidence", 0.70)):
            return BlockResult(self.name, [CheckResult("CATEGORY_MATCH", 0, f"photo appears to show {predicted}, not the registered livelihood", raw_measure=registered_probability, threshold=settings.get("not_relevant_confidence"), evidence=evidence, severity="review")])
        return BlockResult(self.name, [CheckResult("CATEGORY_MATCH", None, "registered category probability is not decisive", raw_measure=registered_probability, threshold=settings.get("relevant_probability"), evidence=evidence, severity="review")])
