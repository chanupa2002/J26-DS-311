"""Build the two derived v2 artifacts. Run once after refreshing artifacts_v2/:

    cd backend
    python -m app.components.market_risk.v2.build_artifacts

macro_anomalies_monthly.csv   one row per month: ccpi_anomaly, diesel_anomaly
model_evidence.json           aggregate results from an allow-list of workbook sheets

NDA: the household sheets of SUSTAIN_Model_Results.xlsx are never parsed. Only the
allow-listed sheets are read, and only the shared strings those sheets point to are
kept. The script prints counts only.
"""

import json
import os
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pandas as pd

MODEL_TABLE = "SUSTAIN_Features_Model_Table.csv"
RESULTS_WORKBOOK = "SUSTAIN_Model_Results.xlsx"
MACRO_FILE = "macro_anomalies_monthly.csv"
EVIDENCE_FILE = "model_evidence.json"

ALLOWED_SHEETS = (
    "Test_3M_Classes",
    "Test_3M_EarlyWarning",
    "Rolling_Origin_3M",
    "Rolling_Origin_3M_Pooled",
    "Results_6M_GroupCV",
    "SHAP_Groups_3M",
    "Threshold_Register",
)
FORBIDDEN_COLUMNS = {"uuid", "household_key", "household_id"}
IDENTIFIER = re.compile(r"SIM-HH-|\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)

MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PACKAGE_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def default_artifacts_dir() -> Path:
    configured = os.environ.get("MARKET_RISK_ARTIFACTS_DIR")
    return Path(configured).expanduser() if configured else Path(__file__).parents[1] / "artifacts_v2"


def build_macro(artifacts: Path) -> int:
    """Write one row per month; stop if a month has more than one distinct value."""
    columns = ["monitoring_period", "ccpi_anomaly", "diesel_anomaly"]
    table = pd.read_csv(artifacts / MODEL_TABLE, usecols=columns)[columns]
    distinct = table.groupby("monitoring_period")[["ccpi_anomaly", "diesel_anomaly"]].nunique(dropna=False)
    bad_months = int((distinct > 1).any(axis=1).sum())
    print(f"macro: {len(table)} visits, {len(distinct)} months, {bad_months} months with more than one value")
    if bad_months:
        raise SystemExit("macro: stopped, every month must have exactly one distinct value")
    monthly = (
        table.drop_duplicates("monitoring_period")
        .sort_values("monitoring_period")
        .rename(columns={"monitoring_period": "month"})
    )
    monthly.to_csv(artifacts / MACRO_FILE, index=False)
    return len(monthly)


def _sheet_paths(book: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(book.read("xl/workbook.xml"))
    rels = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
    targets = {rel.get("Id"): rel.get("Target") for rel in rels.iter(f"{PACKAGE_REL_NS}Relationship")}
    paths = {}
    for sheet in workbook.iter(f"{MAIN_NS}sheet"):
        target = targets[sheet.get(f"{REL_NS}id")]
        paths[sheet.get("name")] = target.lstrip("/") if target.startswith("/") else posixpath.join("xl", target)
    return paths


def _column_index(reference: str) -> int:
    index = 0
    for char in re.match(r"[A-Z]+", reference).group():
        index = index * 26 + ord(char) - 64
    return index - 1


def _read_cells(book: zipfile.ZipFile, path: str) -> list[dict[int, tuple[str, str | None]]]:
    """Rows of {column: (cell type, raw value)}; shared strings are resolved later."""
    rows = []
    root = ET.fromstring(book.read(path))
    for row in root.iter(f"{MAIN_NS}row"):
        cells = {}
        for cell in row.iter(f"{MAIN_NS}c"):
            kind = cell.get("t", "n")
            if kind == "inlineStr":
                text = "".join(node.text or "" for node in cell.iter(f"{MAIN_NS}t"))
            else:
                node = cell.find(f"{MAIN_NS}v")
                text = None if node is None else node.text
            cells[_column_index(cell.get("r"))] = (kind, text)
        rows.append(cells)
    return rows


def _shared_strings(book: zipfile.ZipFile, wanted: set[int]) -> dict[int, str]:
    """Return only the requested shared strings; all others are discarded unread."""
    if not wanted or "xl/sharedStrings.xml" not in book.namelist():
        return {}
    found: dict[int, str] = {}
    index = -1
    with book.open("xl/sharedStrings.xml") as stream:
        for _, element in ET.iterparse(stream, events=("end",)):
            if element.tag == f"{MAIN_NS}si":
                index += 1
                if index in wanted:
                    found[index] = "".join(node.text or "" for node in element.iter(f"{MAIN_NS}t"))
                element.clear()
    return found


def _value(kind: str, text: str | None, strings: dict[int, str]):
    if text is None:
        return None
    if kind == "s":
        return strings[int(text)] or None  # pandas writes NaN as an empty string
    if kind in ("str", "inlineStr"):
        return text or None
    if kind == "b":
        return text == "1"
    if kind == "e":
        return None
    number = float(text)
    return int(number) if number.is_integer() else number


def read_allowed_sheets(path: Path) -> dict[str, list[dict]]:
    with zipfile.ZipFile(path) as book:
        paths = _sheet_paths(book)
        missing = [name for name in ALLOWED_SHEETS if name not in paths]
        if missing:
            raise SystemExit(f"evidence: workbook is missing sheets: {', '.join(missing)}")
        raw = {name: _read_cells(book, paths[name]) for name in ALLOWED_SHEETS}
        wanted = {
            int(text)
            for rows in raw.values()
            for row in rows
            for kind, text in row.values()
            if kind == "s" and text is not None
        }
        strings = _shared_strings(book, wanted)

    sheets = {}
    for name, rows in raw.items():
        header = {col: _value(*cell, strings) for col, cell in rows[0].items()}
        columns = {col: (str(title) if title not in (None, "") else "label") for col, title in header.items()}
        sheets[name] = [
            {title: _value(*row[col], strings) if col in row else None for col, title in columns.items()}
            for row in rows[1:]
        ]
    return sheets


def check_no_identifiers(sheets: dict[str, list[dict]]) -> None:
    for name, rows in sheets.items():
        for row in rows:
            if FORBIDDEN_COLUMNS & {key.lower() for key in row}:
                raise SystemExit(f"evidence: stopped, sheet {name} has an identifier column")
            if any(isinstance(value, str) and IDENTIFIER.search(value) for value in row.values()):
                raise SystemExit(f"evidence: stopped, sheet {name} contains an identifier value")


def build_evidence(artifacts: Path) -> dict[str, int]:
    sheets = read_allowed_sheets(artifacts / RESULTS_WORKBOOK)
    check_no_identifiers(sheets)
    payload = {"source": RESULTS_WORKBOOK, "sheets": sheets}
    (artifacts / EVIDENCE_FILE).write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    return {name: len(rows) for name, rows in sheets.items()}


def main() -> int:
    artifacts = default_artifacts_dir()
    months = build_macro(artifacts)
    print(f"macro: wrote {MACRO_FILE} with {months} months")
    counts = build_evidence(artifacts)
    print(f"evidence: wrote {EVIDENCE_FILE}; rows per sheet: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
