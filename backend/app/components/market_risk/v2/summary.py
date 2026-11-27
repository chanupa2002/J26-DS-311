"""Optional LLM summary of a recommendation (FR5 generation), grounded in the retrieved chunks.

Runs only when a Gemini API key is configured (environment, or backend/.env read by code at
runtime as in the project's existing pattern). No key, a timeout or any error -> no summary,
and the response is rules + retrieval only. The prompt carries only the risk class, the 3-month
alert, reason labels, the action, the guardrail and public circular text with chunk ids –
never a household key, name, district, ids or answers. Every step must cite given chunk ids.
"""

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TEXT_MODEL = "gemini-2.5-flash-lite"  # same default as the project's livelihood text model
TIMEOUT_MS = 10000  # the Gemini API rejects deadlines under 10 s (400 INVALID_ARGUMENT)
FAILURE_COOLDOWN_S = 300  # after a failed call, skip the LLM for 5 minutes (no wait on every page)
MIN_STEPS, MAX_STEPS = 1, 3
PROMPT_VERSION = "officer-steps-2"  # part of the cache key: a new prompt never reuses old answers
BACKEND_ENV_PATH = Path(__file__).resolve().parents[4] / ".env"

_cache: dict[tuple, list[dict[str, Any]] | None] = {}
_lock = threading.Lock()
_failed_at: float | None = None  # monotonic time of the last failed call


def _mark_failed() -> None:
    global _failed_at
    with _lock:
        _failed_at = time.monotonic()


def _cooling_down() -> bool:
    with _lock:
        return _failed_at is not None and time.monotonic() - _failed_at < FAILURE_COOLDOWN_S


def _env(name: str) -> str | None:
    value = (os.getenv(name) or "").strip()
    if value:
        return value
    try:  # project pattern: backend/.env, read at runtime without changing the environment
        from dotenv import dotenv_values

        value = (dotenv_values(BACKEND_ENV_PATH).get(name) or "").strip()
    except Exception:
        return None
    return value or None


def api_key() -> str | None:
    if (_env("MARKET_RISK_LLM_SUMMARY") or "").lower() == "off":
        return None
    return _env("GEMINI_API_KEY")


def model_name() -> str:
    return _env("MARKET_RISK_LLM_MODEL") or _env("GEMINI_TEXT_MODEL") or DEFAULT_TEXT_MODEL


def build_prompt(*, risk_class: str, alert_3m: bool | None, reason_labels: list[str], action_en: str,
                 guardrail: str, chunks: list[tuple[str, str]]) -> str:
    """The only inputs allowed into the prompt (keyword-only, so nothing else can slip in)."""
    alert = "yes" if alert_3m else "no"
    sources = "\n\n".join(f"[{chunk_id}]\n{text}" for chunk_id, text in chunks)
    reasons = "; ".join(reason_labels) or "none"
    return (
        "You help a Samurdhi Development Officer plan a follow-up for one livelihood household.\n"
        f"Risk this month: {risk_class}. Needs attention in 3 months: {alert}.\n"
        f"Reasons: {reasons}.\n"
        f"Suggested action from the rule table: {action_en}\n"
        f"Guardrail (must be respected): {guardrail or 'none'}\n\n"
        "Official circular extracts (OCR text, may be noisy):\n"
        f"{sources}\n\n"
        f"Write {MIN_STEPS} to {MAX_STEPS} short, concrete steps in plain English that the Samurdhi "
        "Development Officer can take for THIS household. Use only the extracts above. "
        "Skip extracts about other officials' duties, agreements, forms between offices or administration. "
        "Every step must cite the chunk id(s) it relies on. Never suggest a second livelihood grant. "
        'If the extracts give no such step, answer {"steps": []}. '
        'Answer only with JSON: {"steps": [{"text": "...", "chunk_ids": ["..."]}]}'
    )


def parse_steps(answer: str, allowed: set[str]) -> list[dict[str, Any]] | None:
    """Validated steps; [] when the model found no step for the officer; None if the answer breaks
    any rule (then the caller falls back)."""
    try:
        data = json.loads(answer)
    except (TypeError, ValueError):
        return None
    steps = data.get("steps") if isinstance(data, dict) else None
    if steps == []:
        return []
    if not isinstance(steps, list) or not MIN_STEPS <= len(steps) <= MAX_STEPS:
        return None
    clean = []
    for step in steps:
        if not isinstance(step, dict):
            return None
        text, ids = step.get("text"), step.get("chunk_ids")
        if not isinstance(text, str) or not text.strip() or not isinstance(ids, list) or not ids:
            return None
        if not all(isinstance(i, str) and i in allowed for i in ids):
            return None
        clean.append({"text": text.strip(), "chunk_ids": list(dict.fromkeys(ids))})
    return clean


def call_llm(prompt: str, key: str) -> str:
    """One Gemini call. Tests replace this function; they never call the API."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=TIMEOUT_MS))
    response = client.models.generate_content(
        model=model_name(),
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"),
    )
    return response.text or ""


class Summariser:
    """One per request: stops calling the LLM after the first failure in that request, and for
    FAILURE_COOLDOWN_S after it in later requests."""

    def __init__(self, knowledge_version: str):
        self.key = api_key()
        self.version = knowledge_version
        self.failed = _cooling_down()

    @property
    def enabled(self) -> bool:
        return self.key is not None and not self.failed

    def steps(self, item: dict[str, Any], *, risk_class: str, alert_3m: bool | None,
              reason_labels: list[str], chunk_texts: dict[str, str]) -> list[dict[str, Any]] | None:
        if not self.enabled or not item["sources"]:
            return None
        cache_key = (PROMPT_VERSION, item["rule_id"], tuple(sorted(reason_labels)), risk_class, alert_3m,
                     self.version)
        with _lock:
            if cache_key in _cache:
                return _cache[cache_key]
        chunks = [(source["chunk_id"], chunk_texts[source["chunk_id"]]) for source in item["sources"]]
        prompt = build_prompt(risk_class=risk_class, alert_3m=alert_3m, reason_labels=reason_labels,
                              action_en=item["action_en"], guardrail=item["guardrail"], chunks=chunks)
        try:
            answer = call_llm(prompt, self.key)
        except Exception as exc:  # timeout, network, quota, SDK errors: fall back, type only in the log
            logger.warning("market_risk v2: LLM summary unavailable (%s); retry after %d s",
                           type(exc).__name__, FAILURE_COOLDOWN_S)
            self.failed = True
            _mark_failed()
            return None
        steps = parse_steps(answer, {chunk_id for chunk_id, _ in chunks})
        if steps is None:
            logger.warning("market_risk v2: LLM summary for rule %s discarded (invalid or uncited)", item["rule_id"])
        elif not steps:
            logger.info("market_risk v2: LLM found no officer step for rule %s", item["rule_id"])
            steps = None  # no step for this household -> summary_steps null
        with _lock:
            _cache[cache_key] = steps
        return steps


def clear_cache() -> None:
    global _failed_at
    with _lock:
        _cache.clear()
        _failed_at = None
