"""Rule and model score calculation."""

from __future__ import annotations

from bisect import bisect_right
from typing import Any, Callable


def rule_hits(features: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return configured rules that fire."""
    tests: dict[str, bool] = {
        "total_changed": bool(features["has_history"] and features["total_change"] != 0),
        "remaining_up": features["remaining_up"] == 1,
        "spent_but_stopped": features["spent_pct"] >= 0.5 and features["business_running"] == 0,
        "not_per_plan": features["not_per_plan"] == 1,
        "bills_unsettled": features["bills_streak"] >= 2,
        "slow_use": features["slow_use"] == 1,
    }
    definitions = {x["name"]: x for x in config.get("rules", [])}
    return [dict(definitions[name], name=name) for name, fired in tests.items() if fired and name in definitions]


def percentile(score: float, train_scores: list[float]) -> float:
    """Percentile using right-sided searchsorted, as specified."""
    if not train_scores: return 0.0
    return bisect_right(sorted(train_scores), score) / len(train_scores)


def calculate_scores(features: dict[str, Any], artifact: dict[str, Any] | None, config: dict[str, Any], score_samples: Callable[[Any], Any] | None = None) -> dict[str, Any]:
    """Calculate rule score, model percentile, blended risk, and level."""
    hits = rule_hits(features, config)
    max_points = float(artifact.get("max_points", sum(x["points"] for x in config.get("rules", []))) if artifact else sum(x["points"] for x in config.get("rules", [])))
    rule_score = sum(float(x["points"]) for x in hits) / max_points if max_points else 0.0
    model_score = None
    if artifact is not None and score_samples is not None:
        # Preserve the feature names used when the sklearn imputer was fitted.
        # Passing a named frame avoids sklearn's feature-name warning.
        import pandas as pd
        frame = pd.DataFrame([[features[name] for name in artifact["features"]]], columns=artifact["features"])
        sample = score_samples(frame)[0]
        model_score = percentile(float(-sample), [float(x) for x in artifact.get("train_scores", [])])
    risk = None if model_score is None else float(config.get("rule_weight", artifact.get("rule_weight", 0.5))) * rule_score + (1 - float(config.get("rule_weight", artifact.get("rule_weight", 0.5)))) * model_score
    if risk is None: level = None
    elif risk >= config["thresholds"]["high"]: level = "High"
    elif risk >= config["thresholds"]["medium"]: level = "Medium"
    else: level = "Low"
    return {"hits": hits, "rule_score": rule_score, "model_score": model_score, "risk": risk, "level": level}
