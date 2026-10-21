"""Create explicitly authenticated Gemini clients from project configuration."""

import os
from pathlib import Path
from typing import Any

from app.core.config import settings

DEFAULT_TEXT_MODEL = "gemini-2.5-flash-lite"
BACKEND_ENV_PATH = Path(__file__).resolve().parents[4] / ".env"


def _settings_value(name: str) -> str | None:
    value = getattr(settings, name.lower(), None)
    if value is None:
        value = getattr(settings, name, None)
    cleaned = str(value).strip() if value is not None else ""
    return cleaned or None


def _load_project_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError as exception:
        raise RuntimeError(
            "python-dotenv is required to load Gemini settings from backend/.env."
        ) from exception
    load_dotenv(dotenv_path=BACKEND_ENV_PATH, override=False)


def get_gemini_api_key(required: bool = True) -> str | None:
    value = _settings_value("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not value:
        _load_project_dotenv()
        value = os.getenv("GEMINI_API_KEY")
    if required and not value:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    return value


def get_gemini_text_model() -> str:
    value = _settings_value("GEMINI_TEXT_MODEL") or os.getenv(
        "GEMINI_TEXT_MODEL"
    )
    if not value:
        _load_project_dotenv()
        value = os.getenv("GEMINI_TEXT_MODEL")
    return value or DEFAULT_TEXT_MODEL


def create_gemini_client() -> Any:
    from google import genai

    api_key = get_gemini_api_key()
    return genai.Client(api_key=api_key)
