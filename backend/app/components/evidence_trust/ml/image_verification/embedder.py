"""Embedding interfaces and a deterministic test implementation."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from typing import Any


class Embedder(ABC):
    """Interface for a future production image embedding model."""

    @abstractmethod
    def embed(self, image: Any) -> list[float]:
        """Return an embedding for an image."""


class FakeEmbedder(Embedder):
    """Deterministic, dependency-free embedder for tests and local plumbing."""

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions
        self.calls = 0

    def embed(self, image: Any) -> list[float]:
        self.calls += 1
        if hasattr(image, "convert") and hasattr(image, "resize"):
            # A small deterministic luminance thumbnail gives tests useful
            # perceptual behavior without pretending to be a real model.
            sample = image.convert("L").resize((self.dimensions, self.dimensions))
            values = list(sample.getdata())
            mean = sum(values) / max(1, len(values))
            vector = [((value - mean) / 255.0) for value in values]
            return vector[: self.dimensions]
        digest = hashlib.sha256(repr(image).encode("utf-8")).digest()
        return [digest[index] / 255.0 for index in range(self.dimensions)]
