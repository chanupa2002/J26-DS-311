"""Duplicate and near-duplicate detection cascade."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .blocks import VerificationBlock
from .contracts import BlockResult, CheckResult
from .duplicate_index import DuplicateIndex, IndexEntry
from .image_loader import ImageContext
from .embedder import Embedder, FakeEmbedder
from .monitoring_repository import MonitoringRecord, MonitoringRepository


def _bits(value: str) -> list[int]:
    return [int(bit) for bit in value]


def _hamming(left: str, right: str) -> int:
    length = min(len(left), len(right))
    return sum(a != b for a, b in zip(_bits(left[:length]), _bits(right[:length]))) + abs(len(left) - len(right))


def _gray_pixels(image: Any, size: tuple[int, int]) -> list[int]:
    return list(image.convert("L").resize(size).getdata())


def perceptual_hash(image: Any, size: int = 8) -> str:
    """Return a compact average hash used as the pHash foundation."""
    pixels = _gray_pixels(image, (size, size))
    average = sum(pixels) / max(1, len(pixels))
    return "".join("1" if pixel >= average else "0" for pixel in pixels)


def difference_hash(image: Any, size: int = 8) -> str:
    """Return a horizontal gradient hash."""
    pixels = _gray_pixels(image, (size + 1, size))
    return "".join("1" if pixels[row * (size + 1) + col] >= pixels[row * (size + 1) + col + 1] else "0" for row in range(size) for col in range(size))


def cosine_similarity(left: list[float], right: list[float]) -> float | None:
    """Calculate cosine similarity, returning unknown for invalid vectors."""
    if not left or not right or len(left) != len(right):
        return None
    denominator = math.sqrt(sum(value * value for value in left) * sum(value * value for value in right))
    if denominator == 0:
        return 1.0 if left == right else 0.0
    return max(0.0, min(1.0, sum(a * b for a, b in zip(left, right)) / denominator))


@dataclass(slots=True)
class Match:
    entry: IndexEntry
    similarity: float
    layer: str
    matched_points: int
    zone: str


class DuplicateBlock(VerificationBlock):
    """Compare an image against earlier indexed images using configurable layers."""

    name = "duplicate"
    check_codes = ("DUPLICATE_SELF", "DUPLICATE_CROSS", "SAME_SCENE_SELF", "SAME_SCENE_CROSS")

    def __init__(self, index: DuplicateIndex | None = None, embedder: Embedder | None = None, config: dict[str, Any] | None = None, repository: MonitoringRepository | None = None) -> None:
        self.index = index or DuplicateIndex()
        self.embedder = embedder or FakeEmbedder()
        self.config = config or {}
        self.repository = repository

    def _settings(self) -> dict[str, Any]:
        return self.config.get("duplicate", {})

    def _features(self, context: ImageContext) -> tuple[str, str, list[float]] | None:
        if context.original is None or context.content_hash is None:
            return None
        return perceptual_hash(context.fixed), difference_hash(context.fixed), context.embedding(self.embedder) or []

    @staticmethod
    def _orb_features(image: Any) -> tuple[list[dict[str, Any]], list[list[int]], tuple[int, int], dict[str, Any]]:
        """Extract JSON-safe ORB features for persistence and matching."""
        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore
        except ImportError:
            return [], [], (int(image.width), int(image.height)), {"algorithm": "ORB", "available": False}
        try:
            detector = cv2.ORB_create(nfeatures=500)
            gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
            keypoints, descriptors = detector.detectAndCompute(gray, None)
            serialized_keypoints = [
                {"x": float(point.pt[0]), "y": float(point.pt[1]), "size": float(point.size), "angle": float(point.angle), "response": float(point.response), "octave": int(point.octave), "class_id": int(point.class_id)}
                for point in (keypoints or [])
            ]
            serialized_descriptors = descriptors.tolist() if descriptors is not None else []
            return serialized_keypoints, serialized_descriptors, (int(image.width), int(image.height)), {"algorithm": "ORB", "available": True, "keypoint_count": len(serialized_keypoints), "descriptor_length": int(descriptors.shape[1]) if descriptors is not None else 0}
        except (AttributeError, TypeError, ValueError):
            return [], [], (int(image.width), int(image.height)), {"algorithm": "ORB", "available": False}

    def _match(self, context: ImageContext, entry: IndexEntry, current_orb: tuple[list[dict[str, Any]], list[list[int]], tuple[int, int], dict[str, Any]] | None = None) -> Match | None:
        settings = self._settings()
        features = self._features(context)
        if not features:
            return None
        phash, dhash, embedding = features
        layers = settings.get("layers", {})
        best: Match | None = None
        if layers.get("exact_hash", True) and context.content_hash == entry.content_hash:
            best = Match(entry, 1.0, "exact_hash", len(phash), "duplicate")
        phash_distance = _hamming(phash, entry.phash)
        dhash_distance = _hamming(dhash, entry.dhash)
        hash_threshold = int(settings.get("hash_hamming_distance", 8))
        if layers.get("perceptual_hash", True) and max(phash_distance, dhash_distance) <= hash_threshold:
            score = 1.0 - max(phash_distance, dhash_distance) / max(1, len(phash))
            candidate = Match(entry, score, "phash_dhash", len(phash), "duplicate")
            if best is None or candidate.similarity > best.similarity:
                best = candidate
        embedding_score = cosine_similarity(embedding, entry.embedding)
        if layers.get("embedding", True) and embedding_score is not None and embedding_score >= float(settings.get("embedding_duplicate_threshold", 0.92)):
            candidate = Match(entry, embedding_score, "embedding", len(embedding), "duplicate")
            if best is None or candidate.similarity > best.similarity:
                best = candidate
        if layers.get("feature_matching", False):
            feature_match = self._feature_match(current_orb, entry, float(settings.get("feature_inlier_ratio_threshold", 0.35)))
            if feature_match is not None:
                candidate = Match(entry, feature_match[0], "orb_ransac", feature_match[1], "duplicate")
                if best is None or candidate.similarity > best.similarity:
                    best = candidate
        if best:
            return best
        same_scene_threshold = float(settings.get("same_scene_threshold", 0.80))
        if embedding_score is not None and embedding_score >= same_scene_threshold:
            return Match(entry, embedding_score, "embedding", len(embedding), "same_place")
        return None

    @staticmethod
    def _feature_match(current_orb: tuple[list[dict[str, Any]], list[list[int]], tuple[int, int], dict[str, Any]] | None, entry: IndexEntry, threshold: float) -> tuple[float, int] | None:
        """Optionally confirm a candidate with ORB and RANSAC.

        OpenCV is deliberately optional. If it is unavailable, this layer is
        skipped without turning a valid image into an error.
        """
        if not current_orb or not current_orb[1] or not entry.descriptors or not entry.keypoints:
            return None
        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore
        except ImportError:
            return None
        current_keypoints, current_descriptors, _, _ = current_orb
        try:
            left = np.asarray(current_descriptors, dtype=np.uint8)
            right = np.asarray(entry.descriptors, dtype=np.uint8)
            matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            pairs = matcher.knnMatch(left, right, k=2)
            good = [first for first, second in pairs if first.distance < 0.75 * second.distance]
            if len(good) < 4:
                return None
            source = np.float32([[current_keypoints[item.queryIdx]["x"], current_keypoints[item.queryIdx]["y"]] for item in good]).reshape(-1, 1, 2)
            target = np.float32([[entry.keypoints[item.trainIdx]["x"], entry.keypoints[item.trainIdx]["y"]] for item in good]).reshape(-1, 1, 2)
            _, mask = cv2.findHomography(source, target, cv2.RANSAC, 5.0)
            if mask is None:
                return None
            inliers = int(mask.ravel().sum())
            ratio = inliers / len(good)
            return (ratio, inliers) if ratio >= threshold else None
        except (cv2.error, IndexError, ValueError, TypeError):
            return None

    @staticmethod
    def _evidence(match: Match) -> dict[str, Any]:
        return {"matched_household": match.entry.household_id, "matched_month": match.entry.month, "similarity_score": round(match.similarity, 6), "layer": match.layer, "matched_points": match.matched_points, "zone": match.zone}

    async def run(self, context: ImageContext) -> BlockResult:
        """Run the cascade and add this image to the index after comparison."""
        if context.load_error or context.original is None or context.content_hash is None:
            reason = context.load_error or "image unavailable"
            return BlockResult(self.name, [CheckResult(code, None, reason, severity="review") for code in self.check_codes])
        features = self._features(context)
        if features is None:
            return BlockResult(self.name, [CheckResult(code, None, "duplicate features unavailable", severity="review") for code in self.check_codes])
        current_orb = self._orb_features(context.fixed)
        if self.repository:
            household_records = self.repository.same_household(context.image_input.household_id, context.image_input.month)
            all_records = self.repository.all_records(context.image_input.month)
            cross_household_records = [
                record
                for record in all_records
                if record.entry.household_id != context.image_input.household_id
            ]
            candidates = [record.entry for record in household_records + cross_household_records]
            matches = [match for entry in candidates if (match := self._match(context, entry, current_orb)) is not None]
            current = IndexEntry(context.image_input.household_id, context.image_input.month, context.content_hash, features[0], features[1], features[2], current_orb[0], current_orb[1], current_orb[2], current_orb[3])
            self.repository.save(MonitoringRecord(current, context.image_input.metadata.get("division"), context.image_input.registered_category, context.image_input.image_path, context.image_input.image if isinstance(context.image_input.image, bytes) else None))
            self_history_available = bool(household_records)
            cross_household_history_available = bool(cross_household_records)
        else:
            with self.index.lock:
                matches = [match for entry in self.index.entries if (match := self._match(context, entry, current_orb)) is not None]
                current = IndexEntry(
                    context.image_input.household_id,
                    context.image_input.month,
                    context.content_hash,
                    features[0],
                    features[1],
                    features[2],
                    current_orb[0],
                    current_orb[1],
                    current_orb[2],
                    current_orb[3],
                )
                self.index.add(current)
            self_history_available = True
            cross_household_history_available = True
        best_duplicate = max((match for match in matches if match.zone == "duplicate"), key=lambda item: item.similarity, default=None)
        best_scene = max((match for match in matches if match.zone == "same_place"), key=lambda item: item.similarity, default=None)
        self_match = best_duplicate if best_duplicate and best_duplicate.entry.household_id == context.image_input.household_id else None
        cross_match = best_duplicate if best_duplicate and best_duplicate.entry.household_id != context.image_input.household_id else None
        # A duplicate is the same underlying file/photo; it is not a new
        # same-place re-photograph.  Keep the informational scene signal
        # separate from duplicate matches.
        self_scene_match = best_scene if best_scene and best_scene.entry.household_id == context.image_input.household_id else None
        cross_scene_match = best_scene if best_scene and best_scene.entry.household_id != context.image_input.household_id else None
        checks = [
            CheckResult("DUPLICATE_SELF", 0 if self_match else 1 if self_history_available else None, "same-household duplicate detected" if self_match else "no same-household duplicate found" if self_history_available else "no previous household monitoring image is available", evidence={**(self._evidence(self_match) if self_match else {}), "comparison_scope": "same_household_history"}, severity="critical" if self_match else "info"),
            CheckResult("DUPLICATE_CROSS", 0 if cross_match else 1 if cross_household_history_available else None, "cross-household duplicate detected; human review required" if cross_match else "no cross-household duplicate found" if cross_household_history_available else "no cross-household monitoring image is available", evidence={**(self._evidence(cross_match) if cross_match else {}), "comparison_scope": "all_cross_household_history"}, severity="critical" if cross_match else "info"),
            CheckResult("SAME_SCENE_SELF", 1 if self_scene_match else None, "same place, different photo is informational" if self_scene_match else "no same-place match found", evidence=self._evidence(self_scene_match) if self_scene_match else {}, severity="info"),
            CheckResult("SAME_SCENE_CROSS", None, "same place across households; human review advised" if cross_scene_match else "no cross-household same-place match found", evidence=self._evidence(cross_scene_match) if cross_scene_match else {}, severity="review" if cross_scene_match else "info"),
        ]
        return BlockResult(self.name, checks)
