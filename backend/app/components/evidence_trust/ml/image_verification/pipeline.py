"""Asynchronous ordered pipeline runner."""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import time
from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from .blocks import VerificationBlock, default_blocks
from .config_loader import load_config
from .contracts import BlockResult, CheckResult, ImageInput, ImageReport
from .embedder import Embedder, FakeEmbedder
from .category_embedder import CategoryEmbedder
from .authenticity import AIGeneratedDetector
from .image_loader import ImageContext, load_context
from .duplicate_index import DuplicateIndex
from .monitoring_repository import MonitoringRepository

logger = logging.getLogger(__name__)
FlagHook = Callable[[ImageInput, CheckResult, str], Awaitable[None] | None]
ReviewHook = Callable[[ImageInput, CheckResult, str], Awaitable[None] | None]


class ImageVerificationPipeline:
    """Run enabled blocks in order while bounding concurrent images."""

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        config_hash: str | None = None,
        blocks: dict[str, VerificationBlock] | None = None,
        embedder: Embedder | None = None,
        category_embedder: CategoryEmbedder | None = None,
        authenticity_detector: AIGeneratedDetector | None = None,
        flag_hook: FlagHook | None = None,
        review_hook: ReviewHook | None = None,
        monitoring_repository: MonitoringRepository | None = None,
    ) -> None:
        if config is None:
            config, config_hash = load_config()
        self.config = config
        self.config_hash = config_hash or ""
        self.embedder = embedder or FakeEmbedder()
        duplicate_config = config.get("duplicate", {}) if config else {}
        index_path = duplicate_config.get("index_path")
        web_index_path = config.get("authenticity", {}).get("web_index_path") if config else None
        self.monitoring_repository = monitoring_repository
        self.blocks = blocks or default_blocks(self.embedder, config, DuplicateIndex(index_path) if index_path else None, category_embedder, monitoring_repository)
        if not blocks:
            from .authenticity import AuthenticityBlock, GoogleWebImageMatcher, SerpApiGoogleLensMatcher, WebImageMatcher
            from app.core.config import settings as app_settings
            auth_settings = config.get("authenticity", {}) if config else {}
            provider = auth_settings.get("web_provider", "local")
            serpapi_enabled = os.getenv(
                "SERPAPI_ENABLED",
                str(app_settings.serpapi_enabled).lower(),
            ).lower() == "true"
            if provider == "local" and serpapi_enabled:
                provider = "serpapi"
            if provider == "serpapi":
                web_matcher = SerpApiGoogleLensMatcher(
                    api_key=app_settings.serpapi_key or None,
                    api_key_env=str(auth_settings.get("serpapi_api_key_env", "SERPAPI_KEY")),
                    timeout_seconds=float(auth_settings.get("serpapi_timeout_seconds", 30.0)),
                )
            elif provider == "google_cloud_vision":
                web_matcher = GoogleWebImageMatcher()
            else:
                web_matcher = WebImageMatcher(DuplicateIndex(web_index_path) if web_index_path else None, self.embedder)
            self.blocks["authenticity"] = AuthenticityBlock(config=config, web_matcher=web_matcher, ai_detector=authenticity_detector)
        self.flag_hook = flag_hook
        self.review_hook = review_hook
        pipeline_config = config.get("pipeline", {})
        self.max_concurrency = max(1, int(pipeline_config.get("max_concurrency", 4)))
        self.stop_on_unusable = bool(pipeline_config.get("stop_on_unusable", False))

    async def _raise_flag(self, image: ImageInput, result: CheckResult, block_name: str) -> None:
        if result.value != 0:
            return
        logger.warning("image verification flag: %s (%s): %s", block_name, result.check_code, result.reason)
        if self.flag_hook:
            outcome = self.flag_hook(image, result, block_name)
            if inspect.isawaitable(outcome):
                await outcome

    async def _raise_review(self, image: ImageInput, result: CheckResult, block_name: str) -> None:
        """Notify an officer workflow for review-only unknown results."""
        if result.value is not None or result.severity != "review" or not self.review_hook:
            return
        outcome = self.review_hook(image, result, block_name)
        if inspect.isawaitable(outcome):
            await outcome

    async def process(self, image: ImageInput) -> ImageReport:
        """Process one image and return a report."""
        fixed_side = int(self.config.get("image", {}).get("fixed_longest_side", 512))
        context: ImageContext = await asyncio.to_thread(load_context, image, fixed_side)
        # The cache is primed once here; blocks can reuse it through context.
        if context.original is not None:
            context.embedding(self.embedder)
        results: list[BlockResult] = []
        raised_flag_order: list[str] = []
        if context.load_error:
            results.append(BlockResult("input", [CheckResult("INPUT_ERROR", None, context.load_error, evidence={"input_type": type(image.image).__name__}, severity="review"),], error=context.load_error))
        configured = list(self.config.get("pipeline", {}).get("blocks", []))
        # Block 5 is intentionally a post-duplicate comparison.  Normalize the
        # production order here so older config files cannot place it later.
        required_order = {name: position for position, name in enumerate(("quality", "duplicate", "similarity_change", "authenticity", "category_match"))}
        if any(item.get("name") in required_order for item in configured):
            configured = sorted(configured, key=lambda item: required_order.get(item.get("name"), len(required_order)))
        for item in configured:
            name = item.get("name")
            if not item.get("enabled", True):
                continue
            block = self.blocks.get(name)
            if block is None:
                results.append(BlockResult(name, [CheckResult(f"{str(name).upper()}_NOT_RUN", None, "block not run: implementation is unavailable")], error="not run"))
                continue
            started = time.perf_counter()
            try:
                block_result = await block.run(context)
            except Exception as exc:  # A block must not stop later blocks.
                block_result = BlockResult(
                    block_name=name,
                    checks=[CheckResult(
                        f"{name.upper()}_ERROR",
                        None,
                        "block error",
                        evidence={"error": str(exc)},
                        severity="advisory" if name == "similarity_change" else "critical",
                    )],
                    error=str(exc),
                )
                await self._raise_flag(
                    image,
                    CheckResult(
                        f"{name.upper()}_ERROR",
                        0,
                        "block error",
                        evidence={"error": str(exc)},
                        severity="advisory" if name == "similarity_change" else "critical",
                    ),
                    name,
                )
            block_result.duration_seconds = time.perf_counter() - started
            results.append(block_result)
            for check in block_result.checks:
                await self._raise_flag(image, check, name)
                await self._raise_review(image, check, name)
            if self.stop_on_unusable and any(check.check_code == "QUALITY_USABLE" and check.value == 0 for check in block_result.checks):
                break
        flagged = [check for block in results for check in block.checks if check.value == 0]
        unknown = [check for block in results for check in block.checks if check.value is None]
        for block in results:
            for check in block.checks:
                if check.value == 0 and f"{block.block_name}:{check.check_code}" not in raised_flag_order:
                    raised_flag_order.append(f"{block.block_name}:{check.check_code}")
        return ImageReport(
            input_summary={"household_id": image.household_id, "month": image.month, "registered_category": image.registered_category, "image_path": image.image_path},
            blocks=results,
            flagged_checks=flagged,
            unknown_checks=unknown,
            summary=f"{len(flagged)} flagged, {len(unknown)} unknown",
            config_hash=self.config_hash,
            raised_flag_order=raised_flag_order,
        )

    async def process_many(self, images: Iterable[ImageInput]) -> list[ImageReport]:
        """Process many images concurrently, preserving input order."""
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def limited(image: ImageInput) -> ImageReport:
            async with semaphore:
                return await self.process(image)

        return await asyncio.gather(*(limited(image) for image in images))
