"""Bill extraction and advisory reconciliation.

The OCR and candidate-selection rules mirror the Bill_Extractor_joblib
notebook. Bill results are advisory evidence only and never feed the model
risk or FINANCIAL_CONSISTENCY signal.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from io import BytesIO
import logging
import math
import os
from pathlib import Path
import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any, Iterable

from .contracts import CheckResult, Visit

LOGGER = logging.getLogger(__name__)

KW = {
    "kw_total": ["total", "amount due", "amount payable", "payable", "nett", "net amount", "මුළු", "එකතුව", "மொத்த"],
    "kw_sub": ["sub total", "subtotal", "sub-total"],
    "kw_cash": ["cash", "tender", "paid", "change", "balance", "refund", "card", "visa", "master"],
    "kw_tax": ["tax", "gst", "vat", "sst", "service"],
    "kw_disc": ["disc", "saving"],
    "kw_round": ["round"],
    "kw_item": ["item", "qty", "quantity"],
}
FEATURES = ["rel_y", "rel_x", "rank", "is_max", "n_same", "n_cands"] + list(KW) + [f"{key}_prev" for key in KW]
AMOUNT_RE = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d{2})?|\d+[.,]\d{2}(?!\d)")
MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
DATE_RE = re.compile(r"\d{4}[/.-]\d{1,2}[/.-]\d{1,2}|\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{1,2}\s?(?:" + MONTHS + r")[a-z]*,?\s?\d{2,4}", re.I)
DATE_TEXT_RE = re.compile(r"(?<!\d)(?:\d{4}\s?[/.-]\s?\d{1,2}\s?[/.-]\s?\d{1,2}|\d{1,2}\s?[/.-]\s?\d{1,2}\s?[/.-]\s?\d{2,4}|\d{1,2}[\s-]?(?:" + MONTHS + r")[a-z]*[\s,-]*\d{2,4})(?!\d)", re.I)


@dataclass(slots=True)
class ExtractedBill:
    total: float | None
    bill_date: date | None
    currency: str | None
    extraction_error: str | None = None


def _to_amount(value: str | None) -> float | None:
    if not value: return None
    cleaned = re.sub(r"[^\d.,]", "", str(value)).strip(".,")
    if not cleaned: return None
    if "," in cleaned and "." in cleaned: cleaned = cleaned.replace(",", "")
    elif "," in cleaned: cleaned = cleaned.replace(",", "") if len(cleaned.rsplit(",", 1)[-1]) == 3 else cleaned.replace(",", ".")
    try: return round(float(cleaned), 2)
    except ValueError: return None


def _to_date(value: str | None) -> date | None:
    if not value: return None
    try:
        from dateutil import parser
        text = str(value).strip()
        year_first = bool(re.match(r"^\d{4}", text))
        parsed = parser.parse(text, dayfirst=not year_first, yearfirst=year_first, fuzzy=True).date()
        return parsed if 2000 <= parsed.year <= 2035 else None
    except (ValueError, OverflowError, TypeError): return None


class BillVerifier(ABC):
    @abstractmethod
    def verify(self, visit: Visit) -> CheckResult: ...


class DisabledBillVerifier(BillVerifier):
    def verify(self, visit: Visit) -> CheckResult:
        return CheckResult("BILL_EVIDENCE", None, "No bill evidence available.")


class BillExtractor:
    """Load bill_model.joblib and extract one bill from image bytes."""

    def __init__(self, model_path: str | Path | None = None, ocr_language: str = "eng+sin+tam") -> None:
        path = Path(model_path or os.getenv("BILL_MODEL_ARTIFACT_PATH", Path(__file__).parent / "model_artifacts" / "bill_model_new.joblib"))
        if not path.exists(): raise FileNotFoundError(f"Bill model artifact not found: {path}")
        import joblib
        bundle = joblib.load(path)
        if not isinstance(bundle, dict) or "model" not in bundle or "features" not in bundle:
            raise ValueError("Bill model artifact must contain 'model' and 'features'")
        self.model = bundle["model"]
        self.features = list(bundle["features"])
        self.views = list(bundle.get("views", [{"binarize": False, "target_w": 1600, "psm": 6}, {"binarize": True, "target_w": 2000, "psm": 6}]))
        self.model_version = bundle.get("version", 3)
        self.ocr_language = ocr_language

    @staticmethod
    def _words_text(words: list[dict[str, Any]]) -> str:
        return " ".join(word["t"] for word in sorted(words, key=lambda item: (round(item["yc"] / 10), item["x"])))

    @staticmethod
    def _configure_tesseract() -> None:
        import pytesseract
        from app.core.config import settings as app_settings
        configured_tesseract = os.getenv("TESSERACT_CMD") or app_settings.tesseract_cmd
        default_windows_tesseract = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if configured_tesseract:
            pytesseract.pytesseract.tesseract_cmd = configured_tesseract
        elif default_windows_tesseract.exists():
            pytesseract.pytesseract.tesseract_cmd = str(default_windows_tesseract)

    @staticmethod
    def _preprocess_gray(image: bytes):
        from PIL import Image, ImageOps
        with Image.open(BytesIO(image)) as original:
            gray = ImageOps.exif_transpose(original).convert("L")
            if gray.width < 1400: gray = gray.resize((gray.width * 3, gray.height * 3))
            elif gray.width > 1800: gray = gray.resize((1600, int(gray.height * 1600 / gray.width)))
            return ImageOps.autocontrast(gray)

    @staticmethod
    def _preprocess_view(image: bytes, binarize: bool, target_w: int):
        import cv2
        import numpy as np
        from PIL import Image, ImageOps
        with Image.open(BytesIO(image)) as original:
            gray = np.array(ImageOps.exif_transpose(original).convert("L"))
        height, width = gray.shape
        gray = cv2.resize(gray, (target_w, max(1, int(height * target_w / width))), interpolation=cv2.INTER_CUBIC if width < target_w else cv2.INTER_AREA)
        gray = cv2.medianBlur(gray, 3)
        if binarize:
            gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
        return Image.fromarray(gray)

    def _ocr_v3_views(self, image: bytes) -> list[tuple[list[dict[str, Any]], int, str]]:
        import pytesseract
        self._configure_tesseract()
        available = set(pytesseract.get_languages(config=""))
        extras = [language for language in ("sin", "tam") if language in available]
        views = []
        for settings in self.views:
            prepared = self._preprocess_view(image, bool(settings.get("binarize", False)), int(settings.get("target_w", 1600)))
            config = f"--psm {int(settings.get('psm', 6))}"
            data = pytesseract.image_to_data(prepared, lang="eng", config=config, output_type=pytesseract.Output.DICT)
            words = [{"t": text.strip(), "x": x, "w": width, "yc": top + height / 2, "h": height} for text, x, top, width, height in zip(data["text"], data["left"], data["top"], data["width"], data["height"]) if text.strip()]
            for language in extras:
                extra = pytesseract.image_to_data(prepared, lang=language, config=config, output_type=pytesseract.Output.DICT)
                words.extend({"t": text.strip(), "x": x, "w": width, "yc": top + height / 2, "h": height} for text, x, top, width, height in zip(extra["text"], extra["left"], extra["top"], extra["width"], extra["height"]) if text.strip() and not any(char.isdigit() for char in text))
            views.append((words, prepared.height, f"{'bin' if settings.get('binarize') else 'gray'}_{settings.get('target_w', 1600)}_psm{settings.get('psm', 6)}"))
        return views

    @staticmethod
    def _keyword_hit(row: str, keywords: list[str]) -> bool:
        tokens = re.findall(r"[^\s:;|]+", row)
        for keyword in keywords:
            if keyword in row:
                return True
            if len(keyword) >= 5 and any(abs(len(token) - len(keyword)) <= 1 and SequenceMatcher(None, token.lower(), keyword.lower()).ratio() >= 0.80 for token in tokens):
                return True
        return False

    def _ocr_words(self, image: bytes) -> tuple[list[dict[str, Any]], int]:
        import pytesseract
        self._configure_tesseract()
        gray = self._preprocess_gray(image)
        data = pytesseract.image_to_data(gray, lang=self.ocr_language, config="--psm 6", output_type=pytesseract.Output.DICT)
        words = [{"t": text.strip(), "x": x, "w": width, "yc": top + height / 2, "h": height} for text, x, top, width, height in zip(data["text"], data["left"], data["top"], data["width"], data["height"]) if text.strip()]
        return words, gray.height

    def _date_ocr_passes(self, image: bytes) -> dict[str, str]:
        import pytesseract
        from PIL import ImageEnhance, ImageFilter, ImageOps
        self._configure_tesseract()
        gray = self._preprocess_gray(image)
        enhanced = ImageEnhance.Contrast(gray).enhance(2.0).filter(ImageFilter.SHARPEN)
        threshold = enhanced.point(lambda pixel: 255 if pixel > 165 else 0)
        outputs: dict[str, str] = {}
        for name, prepared in (("enhanced", enhanced), ("threshold", threshold)):
            for psm in (6, 11, 12):
                outputs[f"{name}_psm_{psm}"] = pytesseract.image_to_string(prepared, lang="eng", config=f"--psm {psm}").strip()
        outputs["numeric_psm_6"] = pytesseract.image_to_string(
            threshold,
            lang="eng",
            config="--psm 6 -c tessedit_char_whitelist=0123456789/-.:",
        ).strip()
        return outputs

    def debug_ocr(self, image: bytes) -> dict[str, Any]:
        """Return OCR variants for diagnosing bill-date recognition."""
        passes = self._date_ocr_passes(image)
        candidates = sorted({match.group(0) for text in passes.values() for match in DATE_RE.finditer(text)})
        parsed = [{"text": candidate, "date": _to_date(candidate).isoformat() if _to_date(candidate) else None} for candidate in candidates]
        return {"ocr_passes": passes, "date_candidates": parsed}

    def debug_full_ocr(self, image: bytes) -> dict[str, Any]:
        """Return full OCR output and every extracted date/amount candidate."""
        import pytesseract
        self._configure_tesseract()
        gray = self._preprocess_gray(image)
        text = pytesseract.image_to_string(
            gray,
            lang=self.ocr_language,
            config="--psm 6",
        ).strip()
        alternate_text = pytesseract.image_to_string(
            gray,
            lang=self.ocr_language,
            config="--psm 11",
        ).strip()
        date_candidates = sorted({
            match.group(0)
            for source in (text, alternate_text)
            for match in DATE_RE.finditer(source)
        })
        amount_candidates = []
        for source_name, source in (("psm_6", text), ("psm_11", alternate_text)):
            for match in AMOUNT_RE.finditer(source):
                amount_candidates.append({
                    "text": match.group(0),
                    "value": _to_amount(match.group(0)),
                    "source": source_name,
                })
        lowered = f"{text} {alternate_text}".lower()
        currency = (
            "LKR" if re.search(r"(?<![a-z])rs(?![a-z])|lkr|à¶»à·”|à®°à¯‚", lowered)
            else "USD" if "usd" in lowered or "$" in lowered
            else "MYR" if re.search(r"(?<![a-z])rm(?![a-z])", lowered)
            else None
        )
        return {
            "ocr_language": self.ocr_language,
            "ocr_text_psm_6": text,
            "ocr_text_psm_11": alternate_text,
            "amount_candidates": amount_candidates,
            "date_candidates": [
                {"text": value, "date": _to_date(value).isoformat() if _to_date(value) else None}
                for value in date_candidates
            ],
            "currency_detected": currency,
        }

    @staticmethod
    def _row_text(words: list[dict[str, Any]], yc: float, height: float, shift: float = 0.0) -> str:
        target = yc + shift * height
        row = [word for word in words if abs(word["yc"] - target) < 0.6 * max(height, word["h"])]
        return " ".join(word["t"] for word in sorted(row, key=lambda item: item["x"])).lower()

    def _candidates(self, words: list[dict[str, Any]], height: int) -> list[dict[str, float]]:
        candidates: list[dict[str, float]] = []
        for word in words:
            if DATE_RE.search(word["t"]): continue
            for match in AMOUNT_RE.findall(word["t"]):
                amount = _to_amount(match)
                if amount and amount > 0: candidates.append({"value": amount, "yc": word["yc"], "h": word["h"], "right": word["x"] + word["w"]})
        if not candidates: return []
        values = [item["value"] for item in candidates]
        cents = {round(value * 100) for value in values}
        width = max(word["x"] + word["w"] for word in words)
        max_value = max(values)
        y_positions = [item["yc"] for item in candidates]
        width = max(word["x"] + word["w"] for word in words)
        rows = []
        for candidate in candidates:
            same = self._row_text(words, candidate["yc"], candidate["h"])
            previous = self._row_text(words, candidate["yc"], candidate["h"], -1.8)
            following = self._row_text(words, candidate["yc"], candidate["h"], 1.8)
            current_cents = round(candidate["value"] * 100)
            same_row = [item for item in candidates if abs(item["yc"] - candidate["yc"]) < 0.6 * max(candidate["h"], item["h"])]
            row = {"value": candidate["value"], "rel_y": candidate["yc"] / height, "rel_x": candidate["right"] / width, "rank": sum(value > candidate["value"] for value in values) / len(values), "is_max": float(candidate["value"] == max_value), "n_same": float(values.count(candidate["value"])), "n_cands": float(len(values)), "log_v": float(__import__("math").log1p(candidate["value"])), "ratio_max": candidate["value"] / max_value, "rank_y": sum(y < candidate["yc"] for y in y_positions) / len(y_positions), "row_n": float(len(same_row)), "rightmost": float(candidate["right"] >= max(item["right"] for item in same_row)), "is_sum_pair": float(any(0 < other < current_cents and current_cents - other in cents for other in cents)), "is_minus_pair": float(any(current_cents + other in cents for other in cents)), "mod5": float(current_cents % 5 == 0)}
            for key, keywords in KW.items():
                row[key] = float(self._keyword_hit(same, keywords))
                row[f"{key}_prev"] = float(self._keyword_hit(previous, keywords))
                row[f"{key}_next"] = float(self._keyword_hit(following, keywords))
            rows.append(row)
        return rows

    def extract(self, image: bytes) -> ExtractedBill:
        try:
            views = self._ocr_v3_views(image)
            total_scores: dict[float, float] = {}
            texts: list[str] = []
            for words, height, _ in views:
                texts.append(self._words_text(words))
                candidates = self._candidates(words, height)
                if candidates:
                    import pandas as pd
                    frame = pd.DataFrame(candidates)
                    probabilities = self.model.predict_proba(frame[self.features])[:, 1]
                    for value, probability in zip(frame["value"], probabilities):
                        total_scores[float(value)] = total_scores.get(float(value), 0.0) + float(probability)
            total = max(total_scores, key=total_scores.get) if total_scores else None
            bill_date = self._vote_date(texts)
            text = " ".join(texts)
            lowered = text.lower()
            currency = "LKR" if re.search(r"(?<![a-z])rs(?![a-z])|lkr|රු|ரூ", lowered) else "USD" if "usd" in lowered or "$" in lowered else "MYR" if re.search(r"(?<![a-z])rm(?![a-z])", lowered) else None
            return ExtractedBill(total, bill_date, currency)
        except Exception as exc:
            LOGGER.warning("Bill extraction failed: %s", exc.__class__.__name__)
            return ExtractedBill(None, None, None, "bill extraction unavailable")

    @staticmethod
    def _vote_date(texts: list[str]) -> date | None:
        hits: list[tuple[date, int, bool]] = []
        for text in texts:
            lowered = text.lower()
            for match in DATE_TEXT_RE.finditer(text):
                raw = re.sub(r"\s*([/.\-])\s*", r"\1", match.group(0))
                parsed = _to_date(raw)
                if parsed and 2000 <= parsed.year <= 2035:
                    hits.append((parsed, match.start(), "date" in lowered[max(0, match.start() - 25):match.start()]))
        if not hits:
            return None
        counts = Counter(item[0] for item in hits)
        return max(hits, key=lambda item: (item[2], counts[item[0]], -item[1]))[0]


class BillEvidenceVerifier:
    """Check all uploaded bills against expenditure and monitoring month."""

    def __init__(self, extractor: Any | None = None, total_tolerance_lkr: float = 0.01, required_currency: str = "LKR") -> None:
        self.extractor = extractor
        self.total_tolerance_lkr = total_tolerance_lkr
        self.required_currency = required_currency

    def verify_many(self, visit: Visit, images: Iterable[bytes]) -> list[CheckResult]:
        image_list = list(images)
        if not image_list: return [CheckResult("BILL_EVIDENCE", None, "No bill evidence available.")]
        if self.extractor is None:
            try: self.extractor = BillExtractor()
            except (FileNotFoundError, ValueError): return [CheckResult("BILL_EVIDENCE", None, "Bill model artifact is unavailable.")]
        extracted = [self.extractor.extract(image) for image in image_list]
        valid_totals = [item.total for item in extracted if item.total is not None]
        total = round(sum(valid_totals), 2) if valid_totals else None
        # New monitoring records compare bills with this month's expenditure.
        # Fall back to grant_spent_lkr for older imported visits that predate
        # the monthly-expenditure field.
        reported_expenditure = visit.monthly_expenditure_lkr
        expenditure_basis = "monthly_expenditure_lkr"
        if reported_expenditure is None:
            reported_expenditure = visit.grant_spent_lkr
            expenditure_basis = "grant_spent_lkr_legacy_fallback"
        amount_value = None if reported_expenditure is None or total is None else int(abs(total - reported_expenditure) <= self.total_tolerance_lkr)
        amount_reason = "Bill total matches monthly expenditure." if amount_value == 1 else "Bill total does not match monthly expenditure." if amount_value == 0 else "Bill total or monthly expenditure is unavailable."
        results = [CheckResult("BILL_TOTAL_MATCH", amount_value, amount_reason, {"bill_count": len(image_list), "extracted_bill_count": len(valid_totals), "bill_total_lkr": total, "reported_expenditure_lkr": reported_expenditure, "expenditure_basis": expenditure_basis, "tolerance_lkr": self.total_tolerance_lkr}, "advisory" if amount_value == 0 else "info")]
        currencies = [item.currency for item in extracted if item.currency is not None]
        currency_value = None if not currencies else int(len(currencies) == len(extracted) and all(item == self.required_currency for item in currencies))
        results.append(CheckResult("BILL_CURRENCY_MATCH", currency_value, "All bills use the expected currency." if currency_value == 1 else "One or more bills use an unexpected currency." if currency_value == 0 else "Bill currency is unavailable.", {"required_currency": self.required_currency, "currencies_found": currencies}, "advisory" if currency_value == 0 else "info"))
        if visit.visit_date is None:
            results.append(CheckResult("BILL_MONTH_MATCH", None, "Monitoring visit date is unavailable.", {"bill_count": len(image_list)}))
        else:
            dates = [item.bill_date for item in extracted]
            known = [item for item in dates if item is not None]
            matching = all(item.year == visit.visit_date.year and item.month == visit.visit_date.month for item in known) if known else None
            value = None if matching is None else int(matching and len(known) == len(dates))
            results.append(CheckResult("BILL_MONTH_MATCH", value, "All bill dates match the monitoring month." if value == 1 else "One or more bill dates do not match the monitoring month." if value == 0 else "Bill dates are unavailable.", {"monitoring_month": visit.visit_date.strftime("%Y-%m"), "bill_dates_found": len(known), "bill_count": len(image_list)}, "advisory" if value == 0 else "info"))
        return results
