"""Foundation tests for image verification."""

from __future__ import annotations

import asyncio
import io
import pytest

from app.components.evidence_trust.ml.image_verification.blocks import VerificationBlock
from app.components.evidence_trust.ml.image_verification.contracts import BlockResult, CheckResult, ImageInput
from app.components.evidence_trust.ml.image_verification.pipeline import ImageVerificationPipeline
from app.components.evidence_trust.ml.image_verification.report import readable_report
from app.components.evidence_trust.ml.image_verification.image_loader import ImageContext
from app.components.evidence_trust.ml.image_verification.image_loader import load_context
from app.components.evidence_trust.ml.image_verification.duplicate import DuplicateBlock
from app.components.evidence_trust.ml.image_verification.duplicate_index import DuplicateIndex
from app.components.evidence_trust.ml.image_verification.category import CategoryMatchBlock, temperature_scale
from app.components.evidence_trust.ml.image_verification.category_embedder import FakeCategoryEmbedder
from app.components.evidence_trust.ml.image_verification.authenticity import AuthenticityBlock, FakeAIGeneratedDetector, HuggingFaceAIGeneratedDetector, WebImageMatcher
from app.components.evidence_trust.ml.image_verification.similarity import SimilarityBlock, FakeChangeDetector
from app.components.evidence_trust.ml.image_verification.quality import QualityBlock, load_quality_config
from app.components.evidence_trust.ml.image_verification.quality import quality_features
from app.components.evidence_trust.ml.image_verification.quality_evaluation import spearman, auroc, compare_logistic_regression
from app.components.evidence_trust.ml.image_verification.monitoring_repository import InMemoryMonitoringRepository


def image_bytes() -> bytes:
    from PIL import Image

    image = Image.new("RGB", (20, 20), (100, 120, 140))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class RecordingBlock(VerificationBlock):
    def __init__(self, name: str, events: list[str], check: CheckResult | None = None, delay: float = 0) -> None:
        self.name, self.events, self.check, self.delay = name, events, check, delay

    async def run(self, context: ImageContext) -> BlockResult:
        del context
        self.events.append(f"start:{self.name}")
        if self.delay:
            await asyncio.sleep(self.delay)
        self.events.append(f"end:{self.name}")
        return BlockResult(self.name, [self.check] if self.check else [])


def config(names: list[str], concurrency: int = 4) -> dict:
    return {"pipeline": {"max_concurrency": concurrency, "blocks": [{"name": name, "enabled": True} for name in names]}, "image": {"fixed_longest_side": 20}}


def test_block_order_and_flag_hook() -> None:
    events: list[str] = []
    hook = lambda image, check, block: events.append(f"flag:{block}")
    blocks = {name: RecordingBlock(name, events, CheckResult("X", 0, "problem")) for name in ("a", "b")}
    pipeline = ImageVerificationPipeline(config(["a", "b"]), blocks=blocks, flag_hook=hook)
    asyncio.run(pipeline.process(ImageInput(image_bytes(), "h", "m")))
    assert events == ["start:a", "end:a", "flag:a", "start:b", "end:b", "flag:b"]


def test_concurrency_limit() -> None:
    active = 0
    maximum = 0

    class Slow(RecordingBlock):
        async def run(self, context: ImageContext) -> BlockResult:
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            await asyncio.sleep(0.01)
            active -= 1
            return BlockResult(self.name)

    pipeline = ImageVerificationPipeline(config(["a"], concurrency=2), blocks={"a": Slow("a", [])})
    asyncio.run(pipeline.process_many([ImageInput(image_bytes(), str(i), "m") for i in range(5)]))
    assert maximum == 2


def test_error_continues_to_next_block() -> None:
    class Broken(RecordingBlock):
        async def run(self, context: ImageContext) -> BlockResult:
            raise ValueError("boom")

    events: list[str] = []
    blocks = {"a": Broken("a", events), "b": RecordingBlock("b", events)}
    pipeline = ImageVerificationPipeline(config(["a", "b"]), blocks=blocks)
    report = asyncio.run(pipeline.process(ImageInput(image_bytes(), "h", "m")))
    assert report.blocks[0].error == "boom"
    assert report.blocks[1].block_name == "b"


def test_unknown_is_not_flagged_and_results_are_deterministic() -> None:
    pipeline = ImageVerificationPipeline(config(["a"]), blocks={"a": RecordingBlock("a", [], CheckResult("X", None, "not applicable"))})
    first = asyncio.run(pipeline.process(ImageInput(image_bytes(), "h", "m")))
    second = asyncio.run(pipeline.process(ImageInput(image_bytes(), "h", "m")))
    assert first.flagged_checks == []
    assert len(first.unknown_checks) == 1
    assert first.summary == second.summary


def test_report_lists_flags_before_unknowns() -> None:
    from app.components.evidence_trust.ml.image_verification.contracts import ImageReport

    flag = CheckResult("BAD", 0, "bad reason", raw_measure=2, threshold=1)
    unknown = CheckResult("UNKNOWN", None, "not implemented")
    report = ImageReport({}, [BlockResult("x", [flag, unknown])], [flag], [unknown], "1 flagged, 1 unknown", "hash")
    text = readable_report(report)
    assert text.index("bad reason") < text.index("not implemented")
    assert "raw_measure=2" in text


def duplicate_config() -> dict:
    return {"pipeline": {"max_concurrency": 2, "blocks": [{"name": "duplicate", "enabled": True}]}, "image": {"fixed_longest_side": 64}, "duplicate": {"layers": {"exact_hash": True, "perceptual_hash": True, "embedding": True, "feature_matching": False}, "hash_hamming_distance": 8, "embedding_duplicate_threshold": 0.92, "same_scene_threshold": 0.80}}


def test_duplicate_self_and_cross_household() -> None:
    raw = image_bytes()
    index = DuplicateIndex()
    block = DuplicateBlock(index=index)
    pipeline = ImageVerificationPipeline(duplicate_config(), blocks={"duplicate": block})
    asyncio.run(pipeline.process(ImageInput(raw, "house-1", "month-1")))
    self_report = asyncio.run(pipeline.process(ImageInput(raw, "house-1", "month-2")))
    cross_report = asyncio.run(pipeline.process(ImageInput(raw, "house-2", "month-2")))
    assert self_report.flagged_checks[0].check_code == "DUPLICATE_SELF"
    assert cross_report.flagged_checks[0].check_code == "DUPLICATE_CROSS"
    assert cross_report.flagged_checks[0].severity == "critical"
    assert cross_report.flagged_checks[0].evidence["matched_household"] == "house-1"


def test_invalid_image_type_is_structured_unknown() -> None:
    pipeline = ImageVerificationPipeline(duplicate_config(), blocks={"duplicate": DuplicateBlock(DuplicateIndex())})
    report = asyncio.run(pipeline.process(ImageInput("photo.gif", "house-1", "month-1")))
    assert report.blocks[0].block_name == "input"
    assert report.blocks[0].checks[0].check_code == "INPUT_ERROR"
    assert report.blocks[0].checks[0].value is None


def category_config() -> dict:
    return {"category_match": {"categories": ["AGRICULTURE", "TRADE", "OTHER"], "other_category": "OTHER", "temperature": 1.5, "relevant_probability": 0.55, "unclear_confidence": 0.55, "unclear_margin": 0.10, "not_relevant_confidence": 0.70, "prompts": {"AGRICULTURE": ["Sri Lankan crop farm"], "TRADE": ["Sri Lankan shop"], "OTHER": ["other livelihood"]}}}


def test_category_relevant_not_relevant_unclear_and_missing() -> None:
    raw = image_bytes()
    context = __import__("app.components.evidence_trust.ml.image_verification.image_loader", fromlist=["load_context"]).load_context(ImageInput(raw, "h", "m", "AGRICULTURE"))
    relevant = asyncio.run(CategoryMatchBlock(FakeCategoryEmbedder({"AGRICULTURE": 0.95, "TRADE": 0.03, "OTHER": 0.02}), category_config()).run(context))
    assert relevant.checks[0].value == 1
    not_relevant = asyncio.run(CategoryMatchBlock(FakeCategoryEmbedder({"AGRICULTURE": 0.02, "TRADE": 0.96, "OTHER": 0.02}), category_config()).run(context))
    assert not_relevant.checks[0].value == 0
    unclear = asyncio.run(CategoryMatchBlock(FakeCategoryEmbedder({"AGRICULTURE": 0.34, "TRADE": 0.33, "OTHER": 0.33}), category_config()).run(context))
    assert unclear.checks[0].value is None
    missing_context = __import__("app.components.evidence_trust.ml.image_verification.image_loader", fromlist=["load_context"]).load_context(ImageInput(raw, "h", "m"))
    missing = asyncio.run(CategoryMatchBlock(FakeCategoryEmbedder({"AGRICULTURE": 1.0}), category_config()).run(missing_context))
    assert missing.checks[0].value is None


def test_temperature_scaling_reduces_confidence() -> None:
    sharp = temperature_scale({"A": 5.0, "B": 0.0}, 1.0)
    calibrated = temperature_scale({"A": 5.0, "B": 0.0}, 2.0)
    assert calibrated["A"] < sharp["A"]


def test_other_requests_manual_review_without_flag() -> None:
    raw = image_bytes()
    events: list[str] = []
    block = CategoryMatchBlock(FakeCategoryEmbedder({"AGRICULTURE": 0.01, "TRADE": 0.01, "OTHER": 0.98}), category_config())
    pipeline_config = {"pipeline": {"max_concurrency": 1, "blocks": [{"name": "category_match", "enabled": True}]}, "image": {"fixed_longest_side": 64}}
    pipeline = ImageVerificationPipeline(pipeline_config, blocks={"category_match": block}, review_hook=lambda image, check, name: events.append(check.check_code))
    report = asyncio.run(pipeline.process(ImageInput(raw, "h", "m", "AGRICULTURE")))
    assert report.flagged_checks == []
    assert events == ["CATEGORY_MATCH"]


def test_authenticity_screen_web_and_missing_signals() -> None:
    from app.components.evidence_trust.ml.image_verification.duplicate import difference_hash, perceptual_hash
    from app.components.evidence_trust.ml.image_verification.duplicate_index import IndexEntry
    from app.components.evidence_trust.ml.image_verification.image_loader import load_context
    import hashlib
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (80, 80), (120, 120, 120))
    ImageDraw.Draw(image).rectangle((0, 0, 79, 79), outline=(0, 0, 0), width=5)
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    raw = buffer.getvalue()
    context = load_context(ImageInput(raw, "h", "m"))
    web_index = DuplicateIndex()
    web_index.add(IndexEntry("web", "source", context.content_hash or "", perceptual_hash(context.fixed), difference_hash(context.fixed), []))
    config = {"authenticity": {"screen_border_score": 0.25, "web_match_enabled": True, "ai_generated_enabled": False}}
    result = asyncio.run(AuthenticityBlock(config, WebImageMatcher(web_index)).run(context))
    assert result.checks[0].value == 0
    assert next(check for check in result.checks if check.check_code == "WEB_IMAGE_MATCH").value == 0
    assert all(check.severity == "advisory" for check in result.checks)
    unknown = asyncio.run(AuthenticityBlock({"authenticity": {"screen_enabled": False, "web_match_enabled": False, "ai_generated_enabled": False}}).run(context))
    assert unknown.checks[-1].value is None


def test_huggingface_ai_detector_is_lazy_and_ai_signal_is_advisory() -> None:
    detector = HuggingFaceAIGeneratedDetector(local_files_only=True)
    assert detector._model is None
    result = asyncio.run(
        AuthenticityBlock(
            {"authenticity": {"screen_enabled": False, "web_match_enabled": False, "ai_generated_enabled": True}},
            ai_detector=FakeAIGeneratedDetector(0.9),
        ).run(load_context(ImageInput(image_bytes(), "h", "m")))
    )
    ai_check = next(check for check in result.checks if check.check_code == "AI_GENERATED")
    assert ai_check.value == 0
    assert ai_check.severity == "advisory"
    assert all(check.severity != "critical" for check in result.checks)


def test_similarity_block_no_previous_brightness_and_decline_are_noncritical() -> None:
    from app.components.evidence_trust.ml.image_verification.image_loader import load_context
    from app.components.evidence_trust.ml.image_verification.embedder import FakeEmbedder
    from PIL import Image

    first = Image.new("RGB", (64, 64), (100, 120, 140))
    brighter = Image.new("RGB", (64, 64), (120, 140, 160))
    first_bytes, brighter_bytes = io.BytesIO(), io.BytesIO()
    first.save(first_bytes, "PNG")
    brighter.save(brighter_bytes, "PNG")
    config = {"similarity_change": {"visually_meaningful_categories": ["AGRICULTURE"], "same_place_embedding_threshold": 0.75, "ssim_enabled": True, "ssim_same_threshold": 0.88, "comparison_size": [32, 32], "zone_limits": {"very_similar": 0.95, "same_place": 0.75}}}
    block = SimilarityBlock(FakeEmbedder(), config)
    no_previous = asyncio.run(block.run(load_context(ImageInput(first_bytes.getvalue(), "h", "m", "AGRICULTURE"))))
    assert all(check.value is None for check in no_previous.checks)
    same = asyncio.run(block.run(load_context(ImageInput(brighter_bytes.getvalue(), "h", "m", "AGRICULTURE", first_bytes.getvalue()))))
    assert same.checks[1].value == 1
    decline = asyncio.run(SimilarityBlock(FakeEmbedder(), config, FakeChangeDetector("declined", 0.8)).run(load_context(ImageInput(first_bytes.getvalue(), "h", "m", "AGRICULTURE", first_bytes.getvalue()))))
    assert decline.checks[-1].value == 0
    assert all(check.severity != "critical" for check in decline.checks)


def test_quality_checks_cover_main_defects() -> None:
    from app.components.evidence_trust.ml.image_verification.image_loader import load_context
    from PIL import Image, ImageEnhance, ImageFilter

    texture = Image.effect_noise((600, 600), 60).convert("RGB")
    sharp_bytes, blur_bytes, dark_bytes, bright_bytes = [], [], [], []
    for image, target in [(texture, sharp_bytes), (texture.filter(ImageFilter.GaussianBlur(8)), blur_bytes), (ImageEnhance.Brightness(texture).enhance(0.15), dark_bytes), (ImageEnhance.Brightness(texture).enhance(2.5), bright_bytes)]:
        buffer = io.BytesIO(); image.save(buffer, "PNG"); target.append(buffer.getvalue())
    block = QualityBlock(load_quality_config())
    sharp = asyncio.run(block.run(load_context(ImageInput(sharp_bytes[0], "h", "m"), 512)))
    blurred = asyncio.run(block.run(load_context(ImageInput(blur_bytes[0], "h", "m"), 512)))
    dark = asyncio.run(block.run(load_context(ImageInput(dark_bytes[0], "h", "m"), 512)))
    bright = asyncio.run(block.run(load_context(ImageInput(bright_bytes[0], "h", "m"), 512)))
    assert sharp.checks[-1].value == 1
    assert blurred.checks[0].value == 0
    assert dark.checks[1].value == 0
    assert bright.checks[2].value == 0
    uniform = Image.new("RGB", (600, 600), (100, 100, 100)); uniform_buffer = io.BytesIO(); uniform.save(uniform_buffer, "PNG")
    uniform_result = asyncio.run(block.run(load_context(ImageInput(uniform_buffer.getvalue(), "h", "m"), 512)))
    assert uniform_result.checks[4].value == 0
    unreadable = asyncio.run(block.run(load_context(ImageInput(b"not-an-image", "h", "m"), 512)))
    assert all(check.value is None for check in unreadable.checks)


def test_quality_blur_is_consistent_across_input_sizes() -> None:
    from app.components.evidence_trust.ml.image_verification.image_loader import load_context
    from PIL import Image
    image = Image.effect_noise((600, 600), 60).convert("RGB")
    small = image.resize((480, 480))
    first, second = io.BytesIO(), io.BytesIO(); image.save(first, "PNG"); small.save(second, "PNG")
    first_features = quality_features(load_context(ImageInput(first.getvalue(), "h", "m"), 512))
    second_features = quality_features(load_context(ImageInput(second.getvalue(), "h", "m"), 512))
    assert first_features is not None and second_features is not None
    assert (first_features["blur_variance"] >= 120.0) == (second_features["blur_variance"] >= 120.0)


def test_quality_calibration_metrics_and_optional_logistic() -> None:
    assert spearman([0.1, 0.2, 0.3], [1, 2, 3]) > 0.99
    assert auroc([0.1, 0.2, 0.9, 0.8], [0, 0, 1, 1]) == 1.0
    result = compare_logistic_regression([[0.0], [1.0]], [0, 1])
    assert result["available"] is False


def test_database_duplicate_parts_and_first_month_unknowns() -> None:
    raw = image_bytes()
    repository = InMemoryMonitoringRepository()
    config = {"pipeline": {"max_concurrency": 1, "blocks": [{"name": "duplicate", "enabled": True}]}, "image": {"fixed_longest_side": 64}, "duplicate": {"layers": {"exact_hash": True, "perceptual_hash": True, "embedding": True, "feature_matching": False}, "hash_hamming_distance": 8, "embedding_duplicate_threshold": 0.92, "same_scene_threshold": 0.80}}
    from app.components.evidence_trust.ml.image_verification.duplicate import DuplicateBlock
    block = DuplicateBlock(repository=repository, config=config)
    pipeline = ImageVerificationPipeline(config, blocks={"duplicate": block})
    first = asyncio.run(pipeline.process(ImageInput(raw, "house-1", "2026-01", "TRADE")))
    assert first.blocks[0].checks[0].value is None
    assert first.blocks[0].checks[1].value is None
    second = asyncio.run(pipeline.process(ImageInput(raw, "house-1", "2026-02", "TRADE")))
    assert second.blocks[0].checks[0].value == 0
    assert len(repository.records) == 2


def test_similarity_runs_after_duplicate_and_reads_latest_repository_photo() -> None:
    raw = image_bytes()
    repository = InMemoryMonitoringRepository()
    config = {
        "pipeline": {"max_concurrency": 1, "blocks": [
            {"name": "quality", "enabled": False},
            {"name": "duplicate", "enabled": True},
            {"name": "category_match", "enabled": False},
            {"name": "authenticity", "enabled": False},
            {"name": "similarity_change", "enabled": True},
        ]},
        "image": {"fixed_longest_side": 64},
        "duplicate": {"layers": {"exact_hash": True, "perceptual_hash": True, "embedding": True, "feature_matching": False}, "hash_hamming_distance": 8, "embedding_duplicate_threshold": 0.92, "same_scene_threshold": 0.80},
        "similarity_change": {"visually_meaningful_categories": ["TRADE"], "same_place_embedding_threshold": 0.75, "feature_matching_enabled": False, "ssim_enabled": True, "ssim_same_threshold": 0.88, "comparison_size": [32, 32], "zone_limits": {"very_similar": 0.95, "same_place": 0.75}},
    }
    pipeline = ImageVerificationPipeline(config, monitoring_repository=repository)
    asyncio.run(pipeline.process(ImageInput(raw, "house-1", "2026-01", "TRADE")))
    report = asyncio.run(pipeline.process(ImageInput(raw, "house-1", "2026-02", "TRADE")))
    assert [block.block_name for block in report.blocks] == ["duplicate", "similarity_change"]
    same_place = next(check for check in report.blocks[1].checks if check.check_code == "SAME_PLACE")
    assert same_place.value == 1
    assert same_place.evidence["matched_month"] == "2026-01"
