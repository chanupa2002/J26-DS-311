"""Training utilities for the optional AI-generated-image linear probe.

Manifest CSV columns: ``file, label, generator, source, licence, provenance``.
Labels are ``real`` or ``generated``. Keep field images out of training.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def read_authenticity_manifest(path: str | Path) -> list[dict[str, str]]:
    """Read and validate a local authenticity manifest without loading images."""
    with Path(path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"file", "label", "generator", "source", "licence", "provenance"}
    if rows and not required.issubset(rows[0]):
        raise ValueError(f"manifest must contain columns: {', '.join(sorted(required))}")
    if any(row.get("provenance") == "field" for row in rows):
        raise ValueError("field images are test-only and cannot be used for training")
    if any(row.get("label") not in {"real", "generated"} for row in rows):
        raise ValueError("labels must be real or generated")
    return rows


def train_linear_probe(features: list[list[float]], labels: list[int], **kwargs: Any) -> Any:
    """Train an optional sklearn logistic probe; imports sklearn lazily."""
    try:
        from sklearn.linear_model import LogisticRegression  # type: ignore
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required only for AI detector training") from exc
    model = LogisticRegression(**kwargs)
    model.fit(features, labels)
    return model
