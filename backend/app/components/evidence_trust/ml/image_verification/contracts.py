"""Data contracts shared by the image-verification pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

CheckValue = Literal[0, 1] | None
Severity = Literal["info", "review", "advisory", "critical"]
SUPPORTED_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"})


@dataclass(slots=True)
class ImageInput:
    """An evidence image reference and the metadata needed by checks."""

    image: str | Path | bytes
    household_id: str
    month: str
    registered_category: str | None = None
    previous_image: str | Path | bytes | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validation_error(self) -> str | None:
        """Return a user-safe validation message, or ``None`` when valid."""
        if not isinstance(self.household_id, str) or not self.household_id.strip():
            return "household_id is required"
        if not isinstance(self.month, str) or not self.month.strip():
            return "month is required"
        if isinstance(self.image, bytes):
            if not self.image:
                return "image bytes must not be empty"
            return None
        if not isinstance(self.image, (str, Path)):
            return "image must be a path or bytes"
        suffix = Path(self.image).suffix.lower()
        if suffix not in SUPPORTED_IMAGE_EXTENSIONS:
            return f"unsupported image type '{suffix or 'none'}'; supported types are JPEG, PNG, WebP, BMP and TIFF"
        return None

    @property
    def image_path(self) -> str | None:
        return str(self.image) if isinstance(self.image, (str, Path)) else None


@dataclass(slots=True)
class CheckResult:
    """The result of one check; ``None`` means unknown/not applicable."""

    check_code: str
    value: CheckValue
    reason: str
    raw_measure: Any = None
    threshold: Any = None
    evidence: dict[str, Any] = field(default_factory=dict)
    severity: Severity = "info"

    @property
    def is_flag(self) -> bool:
        return self.value == 0


@dataclass(slots=True)
class BlockResult:
    """Results emitted by one pipeline block."""

    block_name: str
    checks: list[CheckResult] = field(default_factory=list)
    duration_seconds: float = 0.0
    error: str | None = None


@dataclass(slots=True)
class ImageReport:
    """Serializable report for one image without image content."""

    input_summary: dict[str, Any]
    blocks: list[BlockResult]
    flagged_checks: list[CheckResult]
    unknown_checks: list[CheckResult]
    summary: str
    config_hash: str
    raised_flag_order: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
