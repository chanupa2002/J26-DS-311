"""Placeholder inference for the livelihood recommendation model."""

from app.components.livelihood_planning.ml.loader import ML_DIR, load_model

OFFICIAL_LIVELIHOOD_CATEGORIES = (
    "AGRICULTURE & PLANTATION CROPS",
    "LIVESTOCK & ANIMAL HUSBANDRY",
    "FOOD PROCESSING & PRODUCTION",
    "TRADE",
    "GARMENT TEXTILE, HANDICRAFTS",
    "CONSTRUCTION, BUILDING AND REPAIR",
    "TRANSPORT & LOGISTICS",
    "BEAUTY AND WELLNESS",
    "OTHER",
)

MODEL_FILENAME = "artifacts/model_v1.joblib"


def recommend_top_k(features: dict, k: int = 3) -> list[dict]:
    """Return dummy recommendations until the exported model is available."""
    model_path = ML_DIR / MODEL_FILENAME
    if model_path.exists():
        load_model(MODEL_FILENAME)
        raise NotImplementedError(
            "Model inference is not implemented for model_v1.joblib yet."
        )

    _ = features
    limit = max(0, min(k, len(OFFICIAL_LIVELIHOOD_CATEGORIES)))
    return [
        {"livelihood": livelihood, "score": 0.0}
        for livelihood in OFFICIAL_LIVELIHOOD_CATEGORIES[:limit]
    ]
