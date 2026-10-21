"""In-memory and JSON-persisted index for earlier evidence photos."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class IndexEntry:
    """Features retained for one previously processed image."""

    household_id: str
    month: str
    content_hash: str
    phash: str
    dhash: str
    embedding: list[float] = field(default_factory=list)
    keypoints: list[dict[str, Any]] = field(default_factory=list)
    descriptors: list[list[int]] = field(default_factory=list)
    image_size: tuple[int, int] | None = None
    feature_metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "IndexEntry":
        return cls(
            household_id=str(value["household_id"]),
            month=str(value["month"]),
            content_hash=str(value["content_hash"]),
            phash=str(value["phash"]),
            dhash=str(value["dhash"]),
            embedding=[float(item) for item in value.get("embedding", [])],
            keypoints=list(value.get("keypoints", [])),
            descriptors=[[int(item) for item in row] for row in value.get("descriptors", [])],
            image_size=tuple(value["image_size"]) if value.get("image_size") else None,
            feature_metadata=dict(value.get("feature_metadata", {})),
        )


class DuplicateIndex:
    """Thread-safe index with optional JSON persistence."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self.entries: list[IndexEntry] = []
        self.lock = threading.RLock()
        self.load()

    def load(self) -> None:
        """Load an existing index; malformed state is ignored safely."""
        if not self.path or not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            entries = payload.get("entries", [])
            self.entries = [IndexEntry.from_dict(item) for item in entries]
        except (OSError, ValueError, TypeError, KeyError):
            self.entries = []

    def add(self, entry: IndexEntry) -> None:
        """Append an entry and persist it atomically enough for local use."""
        with self.lock:
            self.entries.append(entry)
            if self.path:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(
                    json.dumps({"entries": [asdict(item) for item in self.entries]}, indent=2),
                    encoding="utf-8",
                )
