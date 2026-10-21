"""Evaluation metrics for category relevance predictions."""

from __future__ import annotations

import math
import random
from collections import Counter
from typing import Any


def category_metrics(rows: list[dict[str, Any]], bins: int = 10) -> dict[str, Any]:
    """Calculate accuracy, macro-F1, confusion, abstention, Brier and ECE."""
    labels = [row["true_category"] for row in rows]
    predictions = [row.get("predicted_category") for row in rows]
    categories = sorted(set(labels) | {prediction for prediction in predictions if prediction})
    confusion = {actual: {predicted: 0 for predicted in categories} for actual in categories}
    for actual, predicted in zip(labels, predictions):
        if predicted in confusion[actual]:
            confusion[actual][predicted] += 1
    f1_values = []
    for category in categories:
        tp = confusion[category][category]
        fp = sum(confusion[actual][category] for actual in categories if actual != category)
        fn = sum(confusion[category][predicted] for predicted in categories if predicted != category)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1_values.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    confidences = [float(row.get("confidence", 0.0)) for row in rows]
    correct = [int(actual == predicted) for actual, predicted in zip(labels, predictions)]
    brier = sum((confidence - correctness) ** 2 for confidence, correctness in zip(confidences, correct)) / len(rows) if rows else None
    ece = 0.0
    for index in range(bins):
        lower, upper = index / bins, (index + 1) / bins
        selected = [position for position, confidence in enumerate(confidences) if lower <= confidence < upper or index == bins - 1 and confidence == upper]
        if selected:
            ece += len(selected) / max(1, len(rows)) * abs(sum(confidences[position] for position in selected) / len(selected) - sum(correct[position] for position in selected) / len(selected))
    return {"accuracy": sum(correct) / len(rows) if rows else None, "macro_f1": sum(f1_values) / len(f1_values) if f1_values else None, "confusion_matrix": confusion, "abstention_rate": sum(prediction is None or prediction == "OTHER" for prediction in predictions) / len(rows) if rows else None, "brier_score": brier, "ece": ece if rows else None}


def mismatch_auroc(rows: list[dict[str, Any]]) -> float | None:
    """Calculate rank AUROC for true-category versus random-wrong-category pairs."""
    pairs = [(float(row.get("registered_probability", 0.0)), 1 if row.get("predicted_category") == row.get("true_category") else 0) for row in rows]
    positives, negatives = sum(label for _, label in pairs), sum(1 - label for _, label in pairs)
    if not positives or not negatives:
        return None
    rank_sum = sum(index for index, (_, label) in enumerate(sorted(pairs), 1) if label)
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def bootstrap_accuracy(rows: list[dict[str, Any]], repetitions: int = 1000, seed: int = 7) -> tuple[float, float] | None:
    """Return a percentile bootstrap interval for accuracy."""
    if not rows:
        return None
    rng = random.Random(seed)
    samples = []
    for _ in range(repetitions):
        sample = [rng.choice(rows) for _ in rows]
        samples.append(sum(row.get("true_category") == row.get("predicted_category") for row in sample) / len(sample))
    samples.sort()
    return samples[int(0.025 * len(samples))], samples[int(0.975 * len(samples))]
