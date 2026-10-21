"""Block interface and the five foundation placeholders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .contracts import BlockResult, CheckResult
from .image_loader import ImageContext


class VerificationBlock(ABC):
    """One ordered, independently switchable verification block."""

    name: str
    check_codes: tuple[str, ...]

    @abstractmethod
    async def run(self, context: ImageContext) -> BlockResult:
        """Run this block against shared image context."""


class PlaceholderBlock(VerificationBlock):
    """Foundation placeholder that deliberately produces unknown results."""

    def __init__(self, name: str, check_codes: tuple[str, ...]) -> None:
        self.name = name
        self.check_codes = check_codes

    async def run(self, context: ImageContext) -> BlockResult:
        del context
        return BlockResult(
            block_name=self.name,
            checks=[
                CheckResult(code, None, "not implemented", severity="info")
                for code in self.check_codes
            ],
        )


def default_blocks(embedder: Any = None, config: dict[str, Any] | None = None, index: Any = None, category_embedder: Any = None, monitoring_repository: Any = None) -> dict[str, VerificationBlock]:
    """Return the registered foundation blocks by configuration name."""
    from .duplicate import DuplicateBlock
    from .category import CategoryMatchBlock
    from .category_embedder import build_category_embedder
    from .authenticity import AuthenticityBlock
    from .similarity import SimilarityBlock
    from .quality import QualityBlock

    return {
        "quality": QualityBlock(config=config),
        "duplicate": DuplicateBlock(index=index, embedder=embedder, config=config, repository=monitoring_repository),
        "similarity_change": SimilarityBlock(embedder=embedder, config=config, repository=monitoring_repository),
        "category_match": CategoryMatchBlock(embedder=category_embedder or build_category_embedder(config), config=config),
        "authenticity": AuthenticityBlock(config=config),
    }
