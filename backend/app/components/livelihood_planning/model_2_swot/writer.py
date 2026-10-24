"""Rewrite selected fact statements without adding unsupported information."""

import json
import logging
import os
import queue
import re
import threading
import time
from typing import Any

from app.components.livelihood_planning.model_2_swot.gemini_client import (
    _load_project_dotenv,
    create_gemini_client,
    get_gemini_api_key,
    get_gemini_text_model,
)
from app.components.livelihood_planning.model_2_swot.grounding import (
    grounded_or_original,
    numbers_are_grounded,
)

MAX_WORDS = 25
RETRYABLE_STATUS_CODES = {429, 503}
RETRY_DELAYS_SECONDS = (1.0, 2.0, 4.0)
TOTAL_REWRITE_TIMEOUT_SECONDS = 15.0
DEFAULT_FALLBACK_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
)
logger = logging.getLogger(__name__)


def signal_strength(statement: str) -> str:
    """Classify the source fact without relying on Gemini's rewrite."""
    return "weak" if "(weak signal)" in statement.casefold() else "clear"


def _safe_exception_message(exception: Exception) -> str:
    message = str(exception).replace("\r", " ").replace("\n", " ")
    try:
        api_key = get_gemini_api_key(required=False)
    except Exception:
        api_key = None
    for secret in (api_key, os.getenv("GOOGLE_API_KEY")):
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return message


def _response_text(response: Any) -> str:
    text = str(getattr(response, "text", "") or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _status_code(exception: Exception) -> int | None:
    """Return a Gemini HTTP status without depending on one SDK error class."""
    response = getattr(exception, "response", None)
    for value in (
        getattr(exception, "status_code", None),
        getattr(exception, "code", None),
        getattr(response, "status_code", None),
    ):
        try:
            code = int(value)
        except (TypeError, ValueError):
            continue
        if code in {404, 429, 503}:
            return code

    match = re.search(r"(?<!\d)(404|429|503)(?!\d)", str(exception))
    return int(match.group(1)) if match else None


def _model_candidates() -> list[str]:
    """Return the configured primary model followed by unique fallbacks."""
    primary = get_gemini_text_model().strip()
    try:
        _load_project_dotenv()
    except Exception:
        # Environment loading is best-effort; the existing OS environment still works.
        pass
    configured = os.getenv(
        "GEMINI_FALLBACK_MODELS", ",".join(DEFAULT_FALLBACK_MODELS)
    )
    models = [primary, *(item.strip() for item in configured.split(","))]
    return list(dict.fromkeys(model for model in models if model))


def _call_with_deadline(call: Any, deadline: float) -> Any:
    """Run one SDK call without allowing it to exceed the shared deadline."""
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Gemini rewriting exceeded the 15-second limit.")

    outcome: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

    def run() -> None:
        try:
            outcome.put((True, call()))
        except Exception as exception:
            outcome.put((False, exception))

    threading.Thread(target=run, daemon=True).start()
    try:
        succeeded, result = outcome.get(timeout=remaining)
    except queue.Empty as exception:
        raise TimeoutError(
            "Gemini rewriting exceeded the 15-second limit."
        ) from exception
    if succeeded:
        return result
    raise result


def _generate_with_model(
    client: Any,
    model: str,
    prompt: str,
    config: Any,
    deadline: float,
) -> Any:
    """Call one model, retrying only transient 429 and 503 responses."""
    for attempt in range(len(RETRY_DELAYS_SECONDS) + 1):
        if time.monotonic() >= deadline:
            raise TimeoutError("Gemini rewriting exceeded the 15-second limit.")
        try:
            return _call_with_deadline(
                lambda: client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                ),
                deadline,
            )
        except Exception as exception:
            if (
                _status_code(exception) not in RETRYABLE_STATUS_CODES
                or attempt >= len(RETRY_DELAYS_SECONDS)
            ):
                raise

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    "Gemini rewriting exceeded the 15-second limit."
                ) from exception
            time.sleep(min(RETRY_DELAYS_SECONDS[attempt], remaining))

    raise RuntimeError("Gemini rewrite retry loop ended unexpectedly.")


def _generate_rewrites(statements: list[str]) -> list[str]:
    from google.genai import types

    deadline = time.monotonic() + TOTAL_REWRITE_TIMEOUT_SECONDS
    client = create_gemini_client()
    prompt = (
        "Rewrite each source statement as one plain sentence of at most 25 words. "
        "Keep the comparison to its benchmark whenever a statement has one "
        '(for example, "versus a livelihood average of 16%"). Never add any '
        "number or interpretation that is not explicitly in the source fact. "
        "Use only information in that statement. Return only a JSON array of "
        "strings in the same order. Source statements: "
        f"{json.dumps(statements, ensure_ascii=False)}"
    )
    config = types.GenerateContentConfig(temperature=0)
    last_exception: Exception | None = None

    for model in _model_candidates():
        if time.monotonic() >= deadline:
            raise TimeoutError("Gemini rewriting exceeded the 15-second limit.")
        logger.info("Trying Gemini rewrite model: %s", model)
        try:
            response = _generate_with_model(
                client, model, prompt, config, deadline
            )
            payload = json.loads(_response_text(response))
            if (
                not isinstance(payload, list)
                or not all(isinstance(item, str) for item in payload)
                or len(payload) != len(statements)
            ):
                raise ValueError(
                    "Gemini did not return the expected JSON string array."
                )
            logger.info("Gemini rewrite model used: %s", model)
            return payload
        except Exception as exception:
            last_exception = exception
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    "Gemini rewriting exceeded the 15-second limit."
                ) from exception

    if last_exception is not None:
        raise last_exception
    raise RuntimeError("No Gemini rewrite model is configured.")


def rewrite_factors(factors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rewrite selected statements, falling back to the originals on any failure."""
    if not factors:
        return []
    statements = [
        str(
            factor.get("evidence")
            if factor.get("evidence") is not None
            else factor.get("text") or ""
        )
        for factor in factors
    ]
    try:
        rewrites = _generate_rewrites(statements)
        if len(rewrites) != len(statements):
            raise ValueError("Gemini returned the wrong number of rewrites.")
    except Exception as exception:
        logger.warning(
            "Falling back to original fact text: %s: %s",
            type(exception).__name__,
            _safe_exception_message(exception),
        )
        rewrites = statements

    result: list[dict[str, Any]] = []
    for factor, source_statement, rewrite in zip(
        factors, statements, rewrites, strict=True
    ):
        number_check_passed = bool(rewrite.strip()) and numbers_are_grounded(
            rewrite, source_statement
        )
        text = grounded_or_original(rewrite, source_statement)
        if text != source_statement and len(text.split()) > MAX_WORDS:
            logger.warning(
                "Falling back to original fact text: ValueError: rewrite exceeded "
                "%s words.",
                MAX_WORDS,
            )
            text = source_statement
        result.append(
            {
                **factor,
                "text": text,
                "evidence": source_statement,
                "strength": signal_strength(source_statement),
                "_decision_was_reworded": text != source_statement,
                "_decision_number_check_passed": number_check_passed,
            }
        )
    return result
