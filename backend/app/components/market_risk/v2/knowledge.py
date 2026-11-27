"""Knowledge base for recommendations: rule table (FR4) and official circulars (FR5 retrieval).

Files live in artifacts_v2/knowledge/ (git-ignored): guidance_chunks.jsonl (public OCR text of
official documents), doc_registry.csv and risk_actions.csv. They are loaded once, separately
from the model artifacts, so a missing knowledge folder never stops the other v2 endpoints.
Retrieval: TF-IDF over character n-grams (robust to OCR noise and mixed Sinhala/English).
Optional guidance_chunks_en.jsonl holds machine translations of the Sinhala chunks (written by
translate_chunks.py); it is not part of knowledge_version and is re-read when the file changes.
"""

import csv
import hashlib
import json
import logging
import re
import threading
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from app.components.market_risk.v2 import artifacts

logger = logging.getLogger(__name__)

FOLDER = "knowledge"
CHUNKS_FILE = "guidance_chunks.jsonl"
REGISTRY_FILE = "doc_registry.csv"
RULES_FILE = "risk_actions.csv"
FILES = (CHUNKS_FILE, REGISTRY_FILE, RULES_FILE)
TRANSLATIONS_FILE = "guidance_chunks_en.jsonl"  # optional: {chunk_id, text_en, model, created_at}
SINHALA = "si"
TOP_K = 2
EXCERPT_CHARS = 600  # the excerpt is at most this long, plus "…" when it is cut
EXCERPT_MIN_CHARS = 150  # a cut at a sentence end must keep at least this much text
START_SEARCH_CHARS = 200  # how far a cut-off start may be skipped to reach a sentence or point
ELLIPSIS = "…"
VECTORIZER_SETTINGS = {"analyzer": "char_wb", "ngram_range": (2, 4), "sublinear_tf": True}

# Fixed retrieval test set from the component owner: query -> doc_ids that count as a hit.
# Results (hit@1, hit@3) are computed when the knowledge base loads, never typed.
RETRIEVAL_TEST_SET: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("වෙළඳපොළ සමීක්ෂණය ව්‍යාපාර සැලැස්ම business plan market survey", ("SDD_2026_05",)),
    ("මූල්‍ය ප්‍රදානය ලබාදිය හැක්කේ එක් අවස්ථාවක් පමණි", ("SDD_2026_05",)),
    ("වෘත්තීය පුහුණුව NVQ vocational training TVEC",
     ("SDD_2026_03", "SDD_2026_02_MoA", "SDD_2026_02_4thAdd_en", "SDD_2026_02_4thAdd_si", "SDD_2026_02_3rdComp")),
    ("සවිබල ණය යෝජනා ක්‍රමය Savibala loan", ("CBB_2026_06", "CBB_2026_06_1stAdd", "CBB_2026_06_1stAdd_form")),
    ("සවිබල ණය යෝජනා ක්‍රමය Savibala loan",
     ("CBB_2026_06", "CBB_2026_06_1stAdd", "CBB_2026_06_1stAdd_form", "SDD_2026_01_1stAdd_loan",
      "CBB_2020_22", "SDD_page_MicroFinance")),
    ("සවිබලගැන්වීමේ ණය ජීවනෝපාය යටිතල පහසුකම් empowerment loan", ("SDD_2026_01_1stAdd_loan",)),
    ("ඉතුරුම් ප්‍රවර්ධන වැඩසටහන savings", ("CBB_2026_01", "CBB_2026_03")),
    ("නිෂ්පාදන ආදර්ශ ගම්මාන One Village One Product", ("SDD_2026_04_Att04",)),
    ("marketing selling products market island-wide entrepreneurs", ("SDD_page_Entrepreneurship", "SDD_2026_02_3rdComp")),
    ("one-time allowance disaster-affected small and micro enterprises recommencing operations",
     ("MOF_08_2025", "MOF_08_2025_iii", "MOF_08_2025_i")),
    ("only one allowance can be obtained per business unit", ("MOF_08_2025_iii",)),
    ("ජීවනෝපාය සැලැස්ම රැකියා සැලැස්ම කැමැත්ත පුහුණුවීම් රැස්වීම්", ("SDD_2026_01_Annex01",)),
)

# Fallback only: "p.4", "p.3 … and p.4", "p.1–2" in the rule table's citation text.
CITED_PAGE = re.compile(r"\bp\.\s*(\d+)(?:\s*[–-]\s*(\d+))?")

# One page or a range in the cited_pages column: "4", "1-2", "1–2".
PAGE_ITEM = re.compile(r"(\d+)(?:\s*[–-]\s*(\d+))?")

# Excerpt boundaries. A sentence ends with . ? ! or the Sinhala kunddaliya ෴ followed by a space;
# a numbered point starts after a space: "2.", "02.", "2.1", "3)", "(4)", "(iii)", "iv)", "(a)".
SENTENCE_END = re.compile(r"[.?!෴](?=\s|$)")
POINT_START = re.compile(r"(?:(?<=\s)|^)(?:\(?\d{1,2}(?:\.\d{1,2})*[.)]|\((?:[ivxIVX]{1,4}|[a-z])\)|[ivx]{1,4}\))(?=\s)")
# A number right after a sentence end or colon ("… කිරීම. 03. ඉලක්ක", "as follows: 1. Visit") is a
# point marker, so its full stop is not a sentence end; "… to division 8." is a sentence end.
POINT_NUMBER = re.compile(r"(?:^|[.?!෴:]\s)\(?\d{1,2}$")
# Text that cannot begin a word: Sinhala vowel signs and virama, joiners, lower-case Latin,
# or punctuation that closes something.
CUT_START = re.compile(r"^(?:[\u0D81-\u0D83\u0DCA-\u0DDF\u0DF2\u0DF3\u200C\u200D]|[a-z]|[,.;:)\]}’”-])")

SOURCE_FIELDS = ("chunk_id", "doc_id", "issuer", "circular_no", "title_en", "date", "page", "source_url", "status_note")


class KnowledgeUnavailable(RuntimeError):
    """The knowledge base is not installed or cannot be read. The message is safe to show."""


@dataclass(frozen=True)
class Rule:
    rule_id: str
    level: str
    priority: int
    trigger: str
    trigger_fields: tuple[str, ...]
    reason_label: str
    action_category: str
    action_en: str
    doc_filter: tuple[str, ...]
    citation: str
    guardrail: str
    research_basis: str
    timing_days: int | None
    validated_by: str
    status: str
    query_terms: str = ""
    circular_says: str = ""  # plain-English summary of the cited circular (validated with the table)
    doc_pages: tuple[tuple[str, int], ...] = ()  # validated (doc_id, page) pairs from cited_pages

    @property
    def draft(self) -> bool:
        return self.status.strip().lower() != "validated"

    @property
    def query(self) -> str:
        """Retrieval query: circular keywords (mostly Sinhala) + reason + action."""
        return " ".join(part for part in (self.query_terms, self.reason_label, self.action_en) if part)

    @property
    def citation_pages(self) -> set[int]:
        """Pages named in the citation text (fallback when cited_pages is empty)."""
        pages: set[int] = set()
        for start, end in CITED_PAGE.findall(self.citation):
            pages.update(range(int(start), int(end or start) + 1))
        return pages


@dataclass(frozen=True)
class KnowledgeBase:
    version: str
    rules: tuple[Rule, ...]
    documents: dict[str, dict[str, str]]
    chunks: list[dict[str, Any]]
    vectorizer: TfidfVectorizer
    matrix: Any  # sparse TF-IDF rows of the chunks, L2-normalised
    doc_ids: np.ndarray
    retrieval_check: dict[str, int]
    source_page_check: dict[str, Any]
    translations: dict[str, dict[str, str]] = field(default_factory=dict)  # chunk_id -> {text_en, model}

    def scores(self, query: str) -> np.ndarray:
        return (self.matrix @ self.vectorizer.transform([query]).T).toarray().ravel()

    def retrieve(self, query: str, doc_filter: tuple[str, ...], k: int = TOP_K,
                 cited: tuple[tuple[str, int], ...] = ()) -> list[dict[str, Any]]:
        """Top-k chunks, searching only documents in doc_filter. Empty filter -> no sources.

        With `cited` (the rule's validated cited_pages), the best-ranked chunks on those
        (document, page) pairs come first; the rest of doc_filter only fills up to k.
        """
        if not doc_filter:
            return []
        allowed = np.flatnonzero(np.isin(self.doc_ids, list(doc_filter)))
        if allowed.size == 0:
            return []
        scores = self.scores(query)[allowed]
        order = [int(i) for i in allowed[np.argsort(-scores, kind="stable")]]
        if cited:
            pairs = set(cited)
            on_page = [i for i in order if (str(self.doc_ids[i]), self.chunks[i].get("page")) in pairs]
            first = set(on_page)
            order = on_page + [i for i in order if i not in first]
        return [self.source(self.chunks[i]) for i in order[:k]]

    def search_all(self, query: str, k: int) -> list[str]:
        """doc_ids of the top-k chunks over all documents (retrieval check only)."""
        order = np.argsort(-self.scores(query), kind="stable")[:k]
        return [str(self.doc_ids[i]) for i in order]

    def source(self, chunk: dict[str, Any]) -> dict[str, Any]:
        translated = self.translations.get(str(chunk.get("chunk_id")))
        return {**{name: chunk.get(name) for name in SOURCE_FIELDS},
                "excerpt": excerpt(str(chunk.get("text", ""))),
                "excerpt_en": excerpt(translated["text_en"]) if translated else None}

    def translation_summary(self) -> dict[str, Any]:
        sinhala = {str(c["chunk_id"]) for c in self.chunks if c.get("language") == SINHALA}
        done = [t for chunk_id, t in self.translations.items() if chunk_id in sinhala]
        models = Counter(t.get("model") or "" for t in done)
        model = models.most_common(1)[0][0] if models else ""
        return {"translated": len(done), "sinhala_chunks": len(sinhala), "model": model or None}

    def evidence(self) -> dict[str, Any]:
        return {
            "n_rules": len(self.rules),
            "n_rules_validated": sum(not rule.draft for rule in self.rules),
            "n_documents": len(self.documents),
            "n_chunks": len(self.chunks),
            "knowledge_version": self.version,
            "retrieval_check": self.retrieval_check,
            "source_page_check": self.source_page_check,
            "translations": self.translation_summary(),
        }


def _sentence_ends(text: str) -> list[int]:
    """Positions just after each sentence end (bare point numbers such as " 2." excluded)."""
    return [m.end() for m in SENTENCE_END.finditer(text)
            if not (text[m.start()] == "." and POINT_NUMBER.search(text[:m.start()]))]


def _excerpt_start(text: str) -> int:
    """0, unless the chunk begins with a cut-off word or fragment: then the first sentence or
    numbered-point start within START_SEARCH_CHARS, else the first whole word."""
    if not CUT_START.match(text):
        return 0
    starts = [m.start() for m in POINT_START.finditer(text, 0, START_SEARCH_CHARS)]
    starts += [end for end in _sentence_ends(text[:START_SEARCH_CHARS])]
    starts = [s for s in starts if 0 < s < len(text)]
    if starts:
        return min(starts)
    space = text.find(" ")
    return space + 1 if 0 < space < START_SEARCH_CHARS else 0


def excerpt(text: str, limit: int = EXCERPT_CHARS) -> str:
    """Readable passage of a chunk: whole words only, from a sentence or point start, ending at
    the last sentence end within `limit` characters; "…" marks text left out at the end."""
    text = " ".join(text.split())
    text = text[_excerpt_start(text):].lstrip()
    if len(text) <= limit:
        return text
    window = text[:limit + 1]  # +1: a sentence end exactly at the limit still counts
    ends = [end for end in _sentence_ends(window) if EXCERPT_MIN_CHARS <= end <= limit]
    if ends:
        cut = ends[-1]
    else:
        space = window.rfind(" ")
        cut = space if space > 0 else limit
    return text[:cut].rstrip() + ELLIPSIS


def folder() -> Path:
    return artifacts.artifacts_dir() / FOLDER


def read_translations(path: Path, chunk_ids: set[str]) -> dict[str, dict[str, str]]:
    """chunk_id -> {text_en, model} from the optional translations file. Missing file -> {}.
    Lines that are not valid JSON, lack text, or name an unknown chunk are skipped (logged once)."""
    if not path.is_file():
        return {}
    found: dict[str, dict[str, str]] = {}
    skipped = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                chunk_id, text = str(row["chunk_id"]), str(row["text_en"]).strip()
            except (ValueError, KeyError, TypeError):
                skipped += 1
                continue
            if chunk_id not in chunk_ids or not text:
                skipped += 1
                continue
            found[chunk_id] = {"text_en": text, "model": str(row.get("model") or "")}  # last line wins
    if skipped:
        logger.warning("market_risk v2: %d translation lines skipped (invalid or unknown chunk)", skipped)
    return found


def _translations_stamp() -> tuple[int, int] | None:
    try:
        stat = (folder() / TRANSLATIONS_FILE).stat()
    except OSError:
        return None
    return (stat.st_mtime_ns, stat.st_size)


def parse_cited_pages(text: str) -> tuple[list[tuple[str, int]], list[str]]:
    """'DOC_ID:page,page; DOC_ID:page' -> ([(doc_id, page), …], [bad entries]). Ranges like 1-2 are allowed."""
    pairs: list[tuple[str, int]] = []
    bad: list[str] = []
    for entry in (part.strip() for part in (text or "").split(";")):
        if not entry:
            continue
        doc_id, sep, pages = (piece.strip() for piece in entry.partition(":"))
        found: list[int] = []
        try:
            if not sep or not doc_id or not pages:
                raise ValueError(entry)
            for item in (piece.strip() for piece in pages.split(",")):
                match = PAGE_ITEM.fullmatch(item)
                if not match:
                    raise ValueError(entry)
                first, last = int(match[1]), int(match[2] or match[1])
                if first < 1 or last < first:
                    raise ValueError(entry)
                found.extend(range(first, last + 1))
        except ValueError:
            bad.append(entry)
            continue
        for page in found:
            if (doc_id, page) not in pairs:
                pairs.append((doc_id, page))
    return pairs, bad


def _validated_pages(rule: Rule, raw: str, documents: dict[str, dict[str, str]]) -> Rule:
    """Keep cited (doc, page) pairs whose doc is in the registry and the rule's doc_filter; log the rest."""
    pairs, bad = parse_cited_pages(raw)
    for entry in bad:
        logger.warning("market_risk v2: rule %s cited_pages entry skipped – not 'DOC_ID:page,page' (%s)",
                       rule.rule_id, entry)
    kept = []
    for doc_id, page in pairs:
        if doc_id not in documents:
            logger.warning("market_risk v2: rule %s cited_pages skips %s – not in the document registry",
                           rule.rule_id, doc_id)
        elif doc_id not in rule.doc_filter:
            logger.warning("market_risk v2: rule %s cited_pages skips %s – not in its doc_filter",
                           rule.rule_id, doc_id)
        else:
            kept.append((doc_id, page))
    return replace(rule, doc_pages=tuple(kept))


def _split(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in (value or "").split(";") if part.strip())


def _rule(row: dict[str, str]) -> Rule:
    timing = (row.get("timing_days") or "").strip()
    return Rule(
        rule_id=row["rule_id"].strip(),
        level=row["level"].strip(),
        priority=int(row["priority"]),
        trigger=row["trigger"].strip(),
        trigger_fields=_split(row["trigger_fields"]),
        reason_label=row["reason_label"].strip(),
        action_category=row["action_category"].strip(),
        action_en=row["action_en"].strip(),
        doc_filter=_split(row["doc_filter"]),
        citation=(row.get("citation") or "").strip(),
        guardrail=(row.get("guardrail") or "").strip(),
        research_basis=(row.get("research_basis") or "").strip(),
        timing_days=int(float(timing)) if timing else None,
        validated_by=(row.get("validated_by") or "").strip(),
        status=(row.get("status") or "").strip(),
        query_terms=(row.get("query_terms") or "").strip(),
        circular_says=(row.get("circular_says") or "").strip(),
    )


def retrieval_check(base: KnowledgeBase) -> dict[str, int]:
    hit_1 = hit_3 = 0
    for query, expected in RETRIEVAL_TEST_SET:
        top = base.search_all(query, 3)
        hit_1 += top[0] in expected
        hit_3 += any(doc in expected for doc in top)
    return {"queries": len(RETRIEVAL_TEST_SET), "hit_at_1": hit_1, "hit_at_3": hit_3}


def source_page_check(base: KnowledgeBase) -> dict[str, Any]:
    """Is each rule's top retrieved source on a cited (document, page)?

    This is the retrieval evaluation, so it ranks the whole doc_filter without the cited-page
    preference the recommendation items use. Uses the cited_pages column; for a rule without it,
    falls back to page numbers in the citation text.
    """
    rules = []
    for rule in base.rules:
        top = base.retrieve(rule.query, rule.doc_filter, k=1)
        if not top:
            continue
        doc_id, page = top[0]["doc_id"], top[0]["page"]
        if rule.doc_pages:
            cited = [{"doc_id": d, "page": p} for d, p in rule.doc_pages]
            basis, matched = "cited_pages", (doc_id, page) in rule.doc_pages
        elif rule.citation_pages:
            cited = [{"doc_id": None, "page": p} for p in sorted(rule.citation_pages)]
            basis, matched = "citation text (page only)", page in rule.citation_pages
        else:
            continue
        rules.append({"rule_id": rule.rule_id, "basis": basis, "cited_pages": cited,
                      "top_source": top[0]["chunk_id"], "top_doc_id": doc_id, "top_page": page,
                      "matched": matched})
    return {"matched": sum(r["matched"] for r in rules), "total": len(rules), "rules": rules}


def _load() -> KnowledgeBase:
    path = folder()
    missing = [name for name in FILES if not (path / name).is_file()]
    if missing:
        raise KnowledgeUnavailable("Knowledge base not installed (missing: " + ", ".join(missing) + ").")
    digest = hashlib.sha256()
    for name in FILES:
        digest.update((path / name).read_bytes())
    with (path / CHUNKS_FILE).open(encoding="utf-8") as handle:
        chunks = [json.loads(line) for line in handle if line.strip()]
    with (path / REGISTRY_FILE).open(encoding="utf-8-sig", newline="") as handle:
        documents = {row["doc_id"]: row for row in csv.DictReader(handle)}
    with (path / RULES_FILE).open(encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("rule_id")]
    rules = tuple(_validated_pages(_rule(row), row.get("cited_pages") or "", documents) for row in rows)
    if not chunks or not rules:
        raise KnowledgeUnavailable("Knowledge base is empty.")
    vectorizer = TfidfVectorizer(**VECTORIZER_SETTINGS)
    matrix = vectorizer.fit_transform([str(chunk.get("text", "")) for chunk in chunks])
    base = KnowledgeBase(
        version=digest.hexdigest()[:12], rules=rules, documents=documents, chunks=chunks,
        vectorizer=vectorizer, matrix=matrix, doc_ids=np.array([str(chunk["doc_id"]) for chunk in chunks]),
        retrieval_check={}, source_page_check={},
    )
    return KnowledgeBase(**{**base.__dict__, "retrieval_check": retrieval_check(base),
                            "source_page_check": source_page_check(base)})


def _with_translations(base: KnowledgeBase) -> KnowledgeBase:
    try:
        translations = read_translations(folder() / TRANSLATIONS_FILE, {str(c["chunk_id"]) for c in base.chunks})
    except OSError as exc:  # type only
        logger.warning("market_risk v2: translations not readable (%s)", type(exc).__name__)
        translations = {}
    return replace(base, translations=translations)


_lock = threading.RLock()
_base: KnowledgeBase | None = None
_failure: KnowledgeUnavailable | None = None
_stamp: tuple[int, int] | None = None  # translations file (mtime, size) of the loaded base


def load() -> KnowledgeBase:
    """Return the loaded knowledge base, or raise KnowledgeUnavailable with a safe message."""
    global _base, _failure, _stamp
    with _lock:
        if _base is not None:
            stamp = _translations_stamp()
            if stamp != _stamp:  # translations written or removed since loading
                _base, _stamp = _with_translations(_base), stamp
            return _base
        if _failure is not None:
            raise _failure
        try:
            _stamp = _translations_stamp()
            _base = _with_translations(_load())
        except KnowledgeUnavailable as exc:
            _failure = exc
            logger.warning("market_risk v2 recommendations disabled: %s", exc)
            raise
        except Exception as exc:  # type only
            logger.error("market_risk v2 recommendations disabled: knowledge files could not be read (%s)",
                         type(exc).__name__)
            _failure = KnowledgeUnavailable("Knowledge base could not be read.")
            raise _failure from None
        return _base


def check_on_startup() -> None:
    try:
        load()
    except KnowledgeUnavailable:
        pass  # already logged; the recommendations endpoint answers 503


def clear_cache() -> None:
    global _base, _failure, _stamp
    with _lock:
        _base = None
        _failure = None
        _stamp = None
