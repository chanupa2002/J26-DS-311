"""Score livelihood facts against household features."""


def score_factors(factors: list[dict], features: dict) -> list[dict]:
    """Attach a dummy score to each fact until scoring rules are implemented."""
    _ = features
    return [{**factor, "score": 0.0} for factor in factors]
