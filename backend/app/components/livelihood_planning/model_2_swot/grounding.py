"""Validate that Gemini did not introduce unsupported numbers."""

import logging
import re

NUMBER_PATTERN = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")
ROUNDING_TOLERANCE = 0.5
logger = logging.getLogger(__name__)


def extract_numbers(text: str) -> list[float]:
    return [
        float(match.replace(",", "")) for match in NUMBER_PATTERN.findall(text)
    ]


def numbers_are_grounded(rewritten: str, source_statement: str) -> bool:
    """Return true when every rewritten number is supported by the source."""
    return not _ungrounded_numbers(rewritten, source_statement)


def _ungrounded_numbers(rewritten: str, source_statement: str) -> list[float]:
    source_numbers = extract_numbers(source_statement)
    return [
        number
        for number in extract_numbers(rewritten)
        if not any(
            abs(number - source_number) <= ROUNDING_TOLERANCE
            for source_number in source_numbers
        )
    ]


def grounded_or_original(rewritten: str, source_statement: str) -> str:
    cleaned = rewritten.strip()
    if not cleaned:
        logger.warning(
            "Falling back to original fact text: ValueError: rewrite was empty."
        )
        return source_statement

    ungrounded_numbers = _ungrounded_numbers(cleaned, source_statement)
    if ungrounded_numbers:
        logger.warning(
            "Falling back to original fact text: ungrounded number: %s.",
            f"{ungrounded_numbers[0]:g}",
        )
        return source_statement
    return cleaned
