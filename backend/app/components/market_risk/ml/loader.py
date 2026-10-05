"""Lazy model loading: the model is loaded on first use, not when the server starts.

Put exported model files (from Google Colab) in this ml/ folder.
Small classical models may be committed. Large files must NOT be committed;
see docs/DATA_AND_MODELS_RULES.md. Keep ml/model_info.json up to date.
"""
from functools import lru_cache
from pathlib import Path

ML_DIR = Path(__file__).parent


@lru_cache(maxsize=None)
def load_model(filename: str):
    path = ML_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")
    # TODO (owner): load the model here using the same library that saved it.
    raise NotImplementedError("Implement model loading for this component.")
