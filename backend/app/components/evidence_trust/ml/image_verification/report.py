"""JSON, readable and batch report builders."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .contracts import CheckResult, ImageReport


def _check_dict(check: CheckResult) -> dict[str, Any]:
    return asdict(check)


def report_dict(report: ImageReport) -> dict[str, Any]:
    """Convert a report to JSON-safe data without image bytes."""
    return {
        "input_summary": report.input_summary,
        "blocks": [asdict(block) for block in report.blocks],
        "flagged_checks": [_check_dict(check) for check in report.flagged_checks],
        "unknown_checks": [_check_dict(check) for check in report.unknown_checks],
        "summary": report.summary,
        "config_hash": report.config_hash,
        "raised_flag_order": report.raised_flag_order,
        "timestamp": report.timestamp,
    }


def readable_report(report: ImageReport) -> str:
    """Build a human-readable report with flags and unknowns first."""
    lines = [f"# Image verification report\n\n{report.summary}", "", "## Raised flag order"]
    lines += [f"- {item}" for item in report.raised_flag_order] or ["- None"]
    lines += ["", "## Flags"]
    lines += [f"- {item.check_code}: {item.reason}" for item in report.flagged_checks] or ["- None"]
    lines += ["", "## Unknowns"]
    lines += [f"- {item.check_code}: {item.reason}" for item in report.unknown_checks] or ["- None"]
    lines += ["", "## Raw measures"]
    for block in report.blocks:
        for check in block.checks:
            lines.append(f"- {check.check_code}: value={check.value!r}, raw_measure={check.raw_measure!r}, threshold={check.threshold!r}")
    return "\n".join(lines) + "\n"


def write_report(report: ImageReport, output_folder: str | Path, stem: str) -> tuple[Path, Path]:
    """Write JSON and Markdown reports to an output folder."""
    folder = Path(output_folder)
    folder.mkdir(parents=True, exist_ok=True)
    json_path, text_path = folder / f"{stem}.json", folder / f"{stem}.md"
    json_path.write_text(json.dumps(report_dict(report), indent=2), encoding="utf-8")
    text_path.write_text(readable_report(report), encoding="utf-8")
    return json_path, text_path


def batch_summary(reports: list[ImageReport]) -> dict[str, Any]:
    """Summarize flag counts, unknown count and configuration hash."""
    counts = Counter(check.check_code for report in reports for check in report.flagged_checks)
    return {"summary": f"{sum(counts.values())} flags across {len(reports)} images", "flag_counts_per_check": dict(counts), "unknown_count": sum(len(report.unknown_checks) for report in reports), "config_hash": reports[0].config_hash if reports else "", "images": len(reports)}


def write_batch_report(reports: list[ImageReport], output_folder: str | Path) -> tuple[Path, Path]:
    """Write a batch JSON report and readable Markdown summary."""
    folder = Path(output_folder)
    folder.mkdir(parents=True, exist_ok=True)
    summary = batch_summary(reports)
    json_path, markdown_path = folder / "batch_report.json", folder / "batch_report.md"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    markdown_path.write_text("# Image verification batch report\n\n" + "\n".join(f"- {key}: {value}" for key, value in summary.items()), encoding="utf-8")
    return json_path, markdown_path
