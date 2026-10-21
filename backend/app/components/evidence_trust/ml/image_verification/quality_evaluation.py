"""Calibration, logistic comparison and real-photo quality reporting."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .contracts import ImageInput
from .image_loader import load_context
from .quality import QualityBlock, load_quality_config


def _rank(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        average = (index + 1 + end) / 2.0
        for position in range(index, end):
            ranks[ordered[position][0]] = average
        index = end
    return ranks


def spearman(values: Iterable[float], targets: Iterable[float]) -> float | None:
    """Return rank correlation without requiring SciPy."""
    left, right = list(values), list(targets)
    if len(left) != len(right) or len(left) < 2:
        return None
    left, right = _rank(left), _rank(right)
    mean_left, mean_right = sum(left) / len(left), sum(right) / len(right)
    numerator = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right))
    denominator = math.sqrt(sum((a - mean_left) ** 2 for a in left) * sum((b - mean_right) ** 2 for b in right))
    return numerator / denominator if denominator else 0.0


def auroc(scores: Iterable[float], labels: Iterable[int]) -> float | None:
    """Return rank-based AUROC, or ``None`` when only one class exists."""
    pairs = sorted(zip(scores, labels), key=lambda item: item[0])
    positives = sum(label == 1 for _, label in pairs)
    negatives = sum(label == 0 for _, label in pairs)
    if not positives or not negatives:
        return None
    rank_sum = sum(index for index, (_, label) in enumerate(pairs, 1) if label == 1)
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def _bad_score(checks: dict[str, Any]) -> float:
    return 1.0 - float(checks.get("QUALITY_USABLE", 1) or 0)


def evaluate_manifest(manifest: str | Path, output: str | Path) -> Path:
    """Evaluate a ladder and write row-level CSV plus Spearman/AUROC metrics."""
    manifest_path, output_path = Path(manifest), Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    block = QualityBlock(load_quality_config())
    rows: list[dict[str, Any]] = []
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            image_path = manifest_path.parent / row["output_file"]
            context = load_context(ImageInput(str(image_path), "ladder", "unknown"), int(block.settings["fixed_longest_side"]))
            result = asyncio.run(block.run(context))
            values = {check.check_code: check.value for check in result.checks}
            rows.append({"defect": row["defect"], "level": int(row["level"]), "bad_score": _bad_score(values), **values})
    csv_path = output_path / "quality_results.csv"
    fields = list(rows[0]) if rows else ["defect", "level", "bad_score"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    metrics: dict[str, Any] = {}
    for defect in sorted({row["defect"] for row in rows}):
        subset = [row for row in rows if row["defect"] == defect]
        metrics[defect] = {"spearman": spearman([row["bad_score"] for row in subset], [row["level"] for row in subset]), "auroc": auroc([row["bad_score"] for row in rows], [int(row["defect"] == defect and row["level"] > 0) for row in rows])}
    (output_path / "quality_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (output_path / "quality_results.md").write_text("# Quality calibration\n\n" + "\n".join(f"- {defect}: Spearman={values['spearman']}, AUROC={values['auroc']}" for defect, values in metrics.items()), encoding="utf-8")
    return csv_path


def compare_logistic_regression(features: list[list[float]], labels: list[int]) -> dict[str, Any]:
    """Train an optional comparison-only logistic model."""
    try:
        from sklearn.linear_model import LogisticRegression  # type: ignore
        from sklearn.model_selection import train_test_split  # type: ignore
        from sklearn.metrics import roc_auc_score  # type: ignore
    except ImportError:
        return {"available": False, "reason": "scikit-learn is not installed"}
    if len(set(labels)) < 2 or len(labels) < 4:
        return {"available": False, "reason": "at least two classes and four rows are required"}
    train_x, test_x, train_y, test_y = train_test_split(features, labels, test_size=0.25, random_state=7, stratify=labels)
    model = LogisticRegression(max_iter=1000).fit(train_x, train_y)
    probabilities = model.predict_proba(test_x)[:, 1]
    return {"available": True, "test_auroc": float(roc_auc_score(test_y, probabilities)), "coefficients": model.coef_.tolist(), "intercept": model.intercept_.tolist()}


def real_photo_report(folder: str | Path, output: str | Path) -> dict[str, Any]:
    """Run checks on real photos and write aggregate counts only."""
    folder, output = Path(folder), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter(); total = 0
    block = QualityBlock(load_quality_config())
    for image_path in sorted(folder.iterdir()):
        if not image_path.is_file():
            continue
        total += 1
        context = load_context(ImageInput(str(image_path), "real", "unknown"), int(block.settings["fixed_longest_side"]))
        result = asyncio.run(block.run(context))
        counts.update(check.check_code for check in result.checks if check.value == 0)
    summary = {"images": total, "flag_counts": dict(counts)}
    (output / "real_photo_quality_report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def propose_thresholds(results_csv: str | Path, output_yaml: str | Path) -> None:
    """Write a review-only proposal without modifying runtime config."""
    Path(output_yaml).write_text(json.dumps({"quality": {"proposal_source": str(results_csv), "review_required": True}}, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path, nargs="?")
    parser.add_argument("output", type=Path)
    parser.add_argument("--real-folder", type=Path)
    args = parser.parse_args()
    if args.real_folder:
        print(real_photo_report(args.real_folder, args.output))
    elif args.manifest:
        print(evaluate_manifest(args.manifest, args.output))
    else:
        parser.error("provide a manifest or --real-folder")


if __name__ == "__main__":
    main()
