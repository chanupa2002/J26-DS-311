"""Minimal read-only .xlsx reader (standard library only) for the training script.

openpyxl is not in backend/requirements.txt, so combined.xlsx is read directly
from its XML parts. Only what training needs is supported: shared strings,
inline strings, numbers and booleans. Dates come back as Excel serial numbers;
convert them with excel_serial_to_datetime.
"""

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_DOC_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS = {"m": _MAIN}
EXCEL_EPOCH = pd.Timestamp("1899-12-30")


def _column_index(cell_ref: str) -> int:
    letters = re.match(r"[A-Z]+", cell_ref).group(0)
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - 64)
    return index - 1


def _cell_value(cell, shared: list[str]):
    kind = cell.get("t")
    value = cell.find("m:v", _NS)
    if kind == "inlineStr":
        return "".join(t.text or "" for t in cell.iter(f"{{{_MAIN}}}t"))
    if value is None or value.text is None:
        return None
    if kind == "s":
        return shared[int(value.text)]
    if kind == "b":
        return value.text == "1"
    if kind in ("str", "e"):
        return value.text
    number = float(value.text)
    return int(number) if number.is_integer() and re.fullmatch(r"-?\d+", value.text) else number


def read_xlsx(path: str | Path, sheets: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Read worksheets into DataFrames (first row = header)."""
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("m:si", _NS):
                shared.append("".join(t.text or "" for t in item.iter(f"{{{_MAIN}}}t")))

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relations = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target") for r in relations.findall(f"{{{_PKG_REL}}}Relationship")}

        frames: dict[str, pd.DataFrame] = {}
        for sheet in workbook.find("m:sheets", _NS).findall("m:sheet", _NS):
            name = sheet.get("name")
            if sheets is not None and name not in sheets:
                continue
            target = targets[sheet.get(f"{{{_DOC_REL}}}id")].lstrip("/")
            target = target if target.startswith("xl/") else f"xl/{target}"
            root = ET.fromstring(archive.read(target))

            rows = []
            for row in root.iter(f"{{{_MAIN}}}row"):
                rows.append({_column_index(c.get("r")): _cell_value(c, shared) for c in row.findall("m:c", _NS)})
            if not rows:
                frames[name] = pd.DataFrame()
                continue
            width = max((max(r) for r in rows if r), default=-1) + 1
            matrix = [[r.get(i) for i in range(width)] for r in rows]
            header = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(matrix[0])]
            frames[name] = pd.DataFrame(matrix[1:], columns=header)

    if sheets is not None:
        missing = sorted(set(sheets) - set(frames))
        if missing:
            raise ValueError(f"Worksheet(s) not found in {Path(path).name}: {missing}")
    return frames


def excel_serial_to_datetime(values: pd.Series) -> pd.Series:
    """Excel serial day numbers (or date strings) -> pandas datetimes; others -> NaT."""
    numeric = pd.to_numeric(values, errors="coerce")
    from_serial = EXCEL_EPOCH + pd.to_timedelta(numeric, unit="D")
    from_text = pd.to_datetime(values.where(numeric.isna()), errors="coerce")
    return from_serial.where(numeric.notna(), from_text)
