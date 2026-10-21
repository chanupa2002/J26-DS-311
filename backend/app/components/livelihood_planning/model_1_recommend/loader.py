"""Load and cache the exported livelihood-recommendation artifacts."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "model_v1.joblib"
INFO_PATH = ARTIFACTS_DIR / "model_v1_info.json"
AREA_INDEX_PATH = ARTIFACTS_DIR / "area_index.csv"
AREA_COLUMNS = ("food_insecurity_score", "debt_pct", "land_pct")


@lru_cache(maxsize=1)
def load_model() -> tuple[Any, dict[str, Any], dict[str, dict[str, float]]]:
    """Load the model, metadata, and district index once on first use."""
    for path in (MODEL_PATH, INFO_PATH, AREA_INDEX_PATH):
        if not path.is_file():
            raise FileNotFoundError(
                f"Required Model 1 artifact is missing: {path.name}"
            )

    import joblib
    import pandas as pd
    import sklearn

    with INFO_PATH.open(encoding="utf-8") as info_file:
        info = json.load(info_file)

    required_version = str(info.get("sklearn_version", "")).strip()
    if sklearn.__version__ != required_version:
        raise RuntimeError(
            "Model 1 requires scikit-learn "
            f"{required_version}, but {sklearn.__version__} is installed. "
            "Install the pinned version or retrain the model with the installed "
            "version."
        )

    model = joblib.load(MODEL_PATH)
    area_table = pd.read_csv(AREA_INDEX_PATH)
    required_area_columns = {"district", *AREA_COLUMNS}
    missing_columns = required_area_columns.difference(area_table.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Area index is missing required columns: {missing}")

    area_index: dict[str, dict[str, float]] = {}
    for record in area_table.to_dict(orient="records"):
        district = str(record["district"]).strip().lower()
        if district:
            area_index[district] = {
                column: record[column] for column in AREA_COLUMNS
            }

    return model, info, area_index
