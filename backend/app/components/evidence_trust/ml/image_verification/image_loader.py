"""Safe image loading and shared per-image context."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field
from typing import Any

from .contracts import ImageInput
from .embedder import Embedder


@dataclass(slots=True)
class ImageContext:
    """Loaded image data shared by all blocks for one input."""

    image_input: ImageInput
    original: Any = None
    fixed: Any = None
    content_hash: str | None = None
    load_error: str | None = None
    _embedding: list[float] | None = field(default=None, init=False, repr=False)

    def embedding(self, embedder: Embedder) -> list[float] | None:
        """Compute the embedding once and reuse it across blocks."""
        if self.original is None:
            return None
        if self._embedding is None:
            self._embedding = embedder.embed(self.fixed)
        return self._embedding


def _read_image(source: str | bytes, fixed_longest_side: int) -> tuple[Any, Any, str]:
    try:
        from PIL import Image, ImageOps  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Pillow is required to load verification images") from exc
    if isinstance(source, str):
        with open(source, "rb") as handle:
            raw = handle.read()
    else:
        raw = source
    content_hash = hashlib.sha256(raw).hexdigest()
    with Image.open(io.BytesIO(raw)) as image:
        original = ImageOps.exif_transpose(image).convert("RGB")
        fixed = original.copy()
        fixed.thumbnail((fixed_longest_side, fixed_longest_side))
        return original.copy(), fixed, content_hash


def load_context(image_input: ImageInput, fixed_longest_side: int = 512) -> ImageContext:
    """Load, orient, convert, resize and hash an image without raising."""
    context = ImageContext(image_input=image_input)
    validation_error = image_input.validation_error()
    if validation_error:
        context.load_error = validation_error
        return context
    try:
        source = image_input.image
        if isinstance(source, bytes):
            context.original, context.fixed, context.content_hash = _read_image(source, fixed_longest_side)
        else:
            context.original, context.fixed, context.content_hash = _read_image(str(source), fixed_longest_side)
    except (OSError, ValueError, RuntimeError) as exc:
        context.load_error = str(exc)
    return context
