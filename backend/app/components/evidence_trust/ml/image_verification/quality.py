"""Block 1: deterministic photo-quality checks."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .blocks import VerificationBlock
from .contracts import BlockResult, CheckResult
from .image_loader import ImageContext


def load_quality_config() -> dict[str, Any]:
    """Load quality thresholds from the dedicated YAML-compatible config."""
    path = Path(__file__).parent / "config" / "quality.yaml"
    raw = path.read_bytes()
    try:
        import yaml  # type: ignore
        return yaml.safe_load(raw) or {}
    except ImportError:
        return json.loads(raw.decode("utf-8"))


def _luminance(image: Any) -> list[int]:
    return list(image.convert("L").getdata())


def _laplacian_variance(image: Any) -> float:
    pixels = _luminance(image)
    width, height = image.size
    values: list[float] = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            index = y * width + x
            laplacian = pixels[index - width] + pixels[index - 1] - 4 * pixels[index] + pixels[index + 1] + pixels[index + width]
            values.append(float(laplacian))
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def _edge_density(image: Any) -> float:
    pixels = _luminance(image)
    width, height = image.size
    if width < 2 or height < 2:
        return 0.0
    edges = 0
    total = 0
    for y in range(height - 1):
        for x in range(width - 1):
            index = y * width + x
            if abs(pixels[index] - pixels[index + 1]) + abs(pixels[index] - pixels[index + width]) >= 40:
                edges += 1
            total += 1
    return edges / max(1, total)


def _content_coverage(image: Any, grid_size: int, edge_contrast_threshold: float, low_cell_edge_density: float, low_cell_stddev: float) -> tuple[float, float]:
    """Measure how much of the image contains local visual content."""
    pixels = _luminance(image)
    width, height = image.size
    content_cells = 0
    low_content_cells = 0
    total_cells = max(1, grid_size * grid_size)
    for row in range(grid_size):
        y0, y1 = row * height // grid_size, (row + 1) * height // grid_size
        for column in range(grid_size):
            x0, x1 = column * width // grid_size, (column + 1) * width // grid_size
            values = [pixels[y * width + x] for y in range(y0, max(y0 + 1, y1)) for x in range(x0, max(x0 + 1, x1))]
            mean = sum(values) / max(1, len(values))
            stddev = math.sqrt(sum((value - mean) ** 2 for value in values) / max(1, len(values)))
            edges = 0
            comparisons = 0
            for y in range(y0, max(y0, y1 - 1)):
                for x in range(x0, max(x0, x1 - 1)):
                    index = y * width + x
                    if abs(pixels[index] - pixels[index + 1]) + abs(pixels[index] - pixels[index + width]) >= edge_contrast_threshold:
                        edges += 1
                    comparisons += 1
            density = edges / max(1, comparisons)
            if density < low_cell_edge_density and stddev < low_cell_stddev:
                low_content_cells += 1
            else:
                content_cells += 1
    return content_cells / total_cells, low_content_cells / total_cells


def quality_features(context: ImageContext, settings: dict[str, Any] | None = None) -> dict[str, float] | None:
    """Compute raw quality measures on the fixed-size image."""
    if context.original is None or context.fixed is None:
        return None
    settings = settings or load_quality_config().get("quality", {})
    values = _luminance(context.fixed)
    mean = sum(values) / max(1, len(values))
    content_share, low_content_share = _content_coverage(
        context.fixed,
        int(settings.get("content_grid_size", 8)),
        float(settings.get("edge_contrast_threshold", 40.0)),
        float(settings.get("low_cell_edge_density", 0.01)),
        float(settings.get("low_cell_stddev", 3.0)),
    )
    blur_variance = _laplacian_variance(context.fixed)
    normalized_blur = blur_variance / max(float(settings.get("blur_normalization_floor", 1.0)), math.sqrt(sum((value - mean) ** 2 for value in values) / max(1, len(values))))
    return {
        "blur_variance": blur_variance,
        "normalized_blur": normalized_blur,
        "mean_luminance": mean,
        "near_black_share": sum(value <= float(settings.get("near_black_luminance", 20.0)) for value in values) / max(1, len(values)),
        "near_white_share": sum(value >= float(settings.get("near_white_luminance", 235.0)) for value in values) / max(1, len(values)),
        "edge_density": _edge_density(context.fixed),
        "luminance_stddev": math.sqrt(sum((value - mean) ** 2 for value in values) / max(1, len(values))),
        "content_share": content_share,
        "low_content_share": low_content_share,
        "original_width": float(context.original.width),
        "original_height": float(context.original.height),
    }


def optional_quality_comparisons(context: ImageContext, settings: dict[str, Any]) -> dict[str, Any]:
    """Run optional BRISQUE/NIQE adapters when installed; never affect checks."""
    if not settings.get("optional_comparisons_enabled", False) or context.fixed is None:
        return {"enabled": False}
    result: dict[str, Any] = {"enabled": True, "brisque": None, "niqe": None, "unavailable": []}
    try:
        from imquality import brisque  # type: ignore
        result["brisque"] = float(brisque.score(context.fixed))
    except (ImportError, AttributeError, OSError, ValueError):
        result["unavailable"].append("BRISQUE")
    try:
        from skimage.metrics import niqe  # type: ignore
        result["niqe"] = float(niqe(context.fixed.convert("L")))
    except (ImportError, AttributeError, OSError, ValueError):
        result["unavailable"].append("NIQE")
    return result


class QualityBlock(VerificationBlock):
    """Evaluate image quality using configurable, explainable thresholds."""

    name = "quality"
    check_codes = ("BLUR", "DARK", "OVEREXPOSED", "LOW_RES", "CROPPED_OR_EMPTY", "QUALITY_USABLE")

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        loaded = config if config and "quality" in config else load_quality_config()
        self.settings = loaded.get("quality", loaded)

    def _result(self, code: str, value: int | None, reason: str, raw: Any, threshold: Any, evidence: dict[str, Any] | None = None) -> CheckResult:
        return CheckResult(code, value, reason, raw_measure=raw, threshold=threshold, evidence=evidence or {})

    async def run(self, context: ImageContext) -> BlockResult:
        """Run quality checks in a fixed-size copy and preserve unknowns."""
        if context.load_error or context.original is None or context.fixed is None:
            return BlockResult(self.name, [self._result(code, None, context.load_error or "image unavailable", None, None) for code in self.check_codes])
        features = quality_features(context, self.settings)
        if features is None:
            return BlockResult(self.name, [self._result(code, None, "quality features unavailable", None, None) for code in self.check_codes])
        s = self.settings
        blur_threshold = float(s["blur_variance_threshold"])
        normalized_blur_threshold = float(s.get("normalized_blur_threshold", 2.0))
        dark_mean_threshold = float(s["dark_mean_luminance_threshold"])
        dark_share_threshold = float(s["dark_near_black_share_threshold"])
        bright_mean_threshold = float(s["overexposed_mean_luminance_threshold"])
        bright_share_threshold = float(s["overexposed_near_white_share_threshold"])
        low_width = float(s["low_res_min_width"])
        low_height = float(s["low_res_min_height"])
        edge_threshold = float(s["edge_density_min"])
        content_threshold = float(s["low_content_share_max"])
        uniform_threshold = float(s["uniform_stddev_min"])
        blur = features["blur_variance"] >= blur_threshold or features["normalized_blur"] >= normalized_blur_threshold
        dark = not (features["mean_luminance"] <= dark_mean_threshold or features["near_black_share"] >= dark_share_threshold)
        bright = not (features["mean_luminance"] >= bright_mean_threshold or features["near_white_share"] >= bright_share_threshold)
        low_res = features["original_width"] >= low_width and features["original_height"] >= low_height
        empty = features["edge_density"] < edge_threshold or features["luminance_stddev"] < uniform_threshold or features["low_content_share"] > content_threshold
        results = [
            self._result("BLUR", int(blur), f"blur variance {features['blur_variance']:.3f} and normalized blur {features['normalized_blur']:.3f} {'meet' if blur else 'do not meet'} thresholds", {"variance": features["blur_variance"], "normalized": features["normalized_blur"]}, {"variance": blur_threshold, "normalized": normalized_blur_threshold}),
            self._result("DARK", int(dark), f"mean luminance {features['mean_luminance']:.3f} or near-black share {features['near_black_share']:.3f} {'meets' if dark else 'exceeds'} configured dark thresholds", {"mean_luminance": features["mean_luminance"], "near_black_share": features["near_black_share"]}, {"mean_luminance": dark_mean_threshold, "near_black_share": dark_share_threshold}),
            self._result("OVEREXPOSED", int(bright), f"mean luminance {features['mean_luminance']:.3f} or near-white share {features['near_white_share']:.3f} {'is within' if bright else 'exceeds'} configured exposure thresholds", {"mean_luminance": features["mean_luminance"], "near_white_share": features["near_white_share"]}, {"mean_luminance": bright_mean_threshold, "near_white_share": bright_share_threshold}),
            self._result("LOW_RES", int(low_res), f"original dimensions {int(features['original_width'])}x{int(features['original_height'])} {'meet' if low_res else 'are below'} minimum {int(low_width)}x{int(low_height)}", {"width": features["original_width"], "height": features["original_height"]}, {"width": low_width, "height": low_height}),
            self._result("CROPPED_OR_EMPTY", int(not empty), f"edge density {features['edge_density']:.3f}, low-content share {features['low_content_share']:.3f} and luminance standard deviation {features['luminance_stddev']:.3f} {'show content' if not empty else 'indicate mostly empty, uniform or poorly covered content'}", {"edge_density": features["edge_density"], "low_content_share": features["low_content_share"], "luminance_stddev": features["luminance_stddev"]}, {"edge_density_min": edge_threshold, "low_content_share_max": content_threshold, "uniform_stddev_min": uniform_threshold}),
        ]
        passed = all(result.value == 1 for result in results)
        failed = [result.check_code for result in results if result.value == 0]
        score = round(100.0 * sum(result.value == 1 for result in results) / len(results), 2)
        results.append(self._result("QUALITY_USABLE", int(passed), "all quality checks passed" if passed else f"quality checks failed: {', '.join(failed)}", score, 100.0, {"quality_score": score, "failed_checks": failed}))
        results[-1].evidence["optional_comparisons"] = optional_quality_comparisons(context, self.settings)
        return BlockResult(self.name, results)
