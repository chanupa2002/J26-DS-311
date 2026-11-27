"""One-off: machine-translate the Sinhala circular chunks to English (Gemini).

    cd backend && .venv/bin/python -m app.components.market_risk.v2.translate_chunks [--batch-size 6] [--limit N]

Reads artifacts_v2/knowledge/guidance_chunks.jsonl and appends one line per translated chunk to
guidance_chunks_en.jsonl: {chunk_id, text_en, model, created_at}. Resumable: chunks already in the
output file are skipped. Only public circular text and chunk ids go into the prompt – never
household data. Same key lookup, model and settings as the summary (temperature 0, JSON answer);
the timeout is longer because batches are long and nobody waits on a page.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.components.market_risk.v2 import knowledge, summary

logger = logging.getLogger(__name__)

BATCH_SIZE = 6
TIMEOUT_MS = 60000
ATTEMPTS = 2  # one retry per batch, then the batch is reported as failed


def build_prompt(batch: list[tuple[str, str]]) -> str:
    """Prompt for one batch of (chunk_id, Sinhala OCR text). Nothing else goes in."""
    passages = "\n\n".join(f"[{chunk_id}]\n{text}" for chunk_id, text in batch)
    return (
        "Translate each passage below from Sinhala to plain English. The passages are OCR text from "
        "official Sri Lankan Samurdhi circulars and may contain reading errors and English words.\n"
        "Rules: translate faithfully and completely; do not summarise, explain or add anything. Keep "
        "all numbers, dates, amounts, percentages, circular numbers and references (for example 2026/05, "
        "Rs. 25,000, 01.01.2026) exactly as written. Keep English words as they are. If part of a "
        "passage is unreadable, translate what can be read.\n\n"
        f"{passages}\n\n"
        "Answer only with JSON: "
        '{"translations": [{"chunk_id": "...", "text_en": "..."}]} with one entry per passage, same chunk ids.'
    )


def parse_translations(answer: str, expected: list[str]) -> dict[str, str] | None:
    """chunk_id -> English text, or None unless every expected id comes back with non-empty text."""
    try:
        data = json.loads(answer)
    except (TypeError, ValueError):
        return None
    rows = data.get("translations") if isinstance(data, dict) else data  # a bare list is accepted too
    if not isinstance(rows, list):
        return None
    found: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            return None
        chunk_id, text = row.get("chunk_id"), row.get("text_en")
        if not isinstance(chunk_id, str) or not isinstance(text, str) or not text.strip():
            return None
        found[chunk_id] = " ".join(text.split())
    if set(found) != set(expected):
        return None
    return found


def call_llm(prompt: str, key: str, model: str) -> str:
    """One Gemini call. Tests replace this function; they never call the API."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=TIMEOUT_MS))
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"),
    )
    return response.text or ""


def done_ids(path: Path) -> set[str]:
    """chunk_ids already translated (valid lines with text)."""
    if not path.is_file():
        return set()
    done = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict) and str(row.get("text_en") or "").strip():
                done.add(str(row.get("chunk_id")))
    return done


def sinhala_chunks(chunks: list[dict[str, Any]]) -> list[tuple[str, str]]:
    return [(str(c["chunk_id"]), " ".join(str(c.get("text", "")).split()))
            for c in chunks if c.get("language") == knowledge.SINHALA]


def run(chunks: list[dict[str, Any]], out_path: Path, key: str, model: str, *, batch_size: int = BATCH_SIZE,
        limit: int | None = None, llm: Callable[[str, str, str], str] | None = None) -> dict[str, int]:
    """Translate the Sinhala chunks not yet in out_path. Returns {translated, skipped, failed}."""
    llm = llm or call_llm
    todo_all = sinhala_chunks(chunks)
    done = done_ids(out_path)
    todo = [item for item in todo_all if item[0] not in done]
    skipped = len(todo_all) - len(todo)
    if limit is not None:
        todo = todo[:limit]
    translated = failed = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(todo), batch_size):
        batch = todo[start:start + batch_size]
        ids = [chunk_id for chunk_id, _ in batch]
        result = None
        for attempt in range(1, ATTEMPTS + 1):
            try:
                result = parse_translations(llm(build_prompt(batch), key, model), ids)
            except Exception as exc:  # type only: messages may echo request details
                logger.warning("batch %s… attempt %d failed (%s)", ids[0], attempt, type(exc).__name__)
                continue
            if result is not None:
                break
            logger.warning("batch %s… attempt %d: answer invalid or incomplete", ids[0], attempt)
        if result is None:
            failed += len(batch)
            continue
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with out_path.open("a", encoding="utf-8") as handle:  # append per batch: safe to stop and resume
            for chunk_id in ids:
                handle.write(json.dumps({"chunk_id": chunk_id, "text_en": result[chunk_id], "model": model,
                                         "created_at": created}, ensure_ascii=False) + "\n")
        translated += len(batch)
        print(f"  {translated + failed}/{len(todo)} done", file=sys.stderr, flush=True)
    return {"translated": translated, "skipped": skipped, "failed": failed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--limit", type=int, default=None, help="translate at most N chunks (testing)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    key = summary._env("GEMINI_API_KEY")  # read at runtime; never printed
    if not key:
        print("No GEMINI_API_KEY configured – nothing translated.", file=sys.stderr)
        return 1
    path = knowledge.folder()
    with (path / knowledge.CHUNKS_FILE).open(encoding="utf-8") as handle:
        chunks = [json.loads(line) for line in handle if line.strip()]
    model = summary.model_name()
    counts = run(chunks, path / knowledge.TRANSLATIONS_FILE, key, model,
                 batch_size=max(1, args.batch_size), limit=args.limit)
    print(f"model {model}: translated {counts['translated']}, skipped (already done) {counts['skipped']}, "
          f"failed {counts['failed']}")
    return 0 if counts["failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
