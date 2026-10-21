"""Run the full image-verification pipeline and write aggregate slide tables."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from collections import Counter
from pathlib import Path

from .cli import _inputs
from .pipeline import ImageVerificationPipeline
from .report import write_batch_report, write_report


async def run(folder: Path, output: Path, csv_path: Path | None = None) -> dict[str, object]:
    """Run all configured blocks, including explicit not-run entries."""
    events: list[dict[str, str]] = []

    def on_flag(image, check, block):
        events.append({"household_id": image.household_id, "block": block, "check_code": check.check_code, "reason": check.reason})

    reports = await ImageVerificationPipeline(flag_hook=on_flag).process_many(_inputs(folder, csv_path))
    output.mkdir(parents=True, exist_ok=True)
    for index, report in enumerate(reports):
        write_report(report, output, f"{index:04d}_{report.input_summary['household_id']}")
    write_batch_report(reports, output)
    counts = Counter(event["check_code"] for event in events)
    (output / "flag_log.json").write_text(json.dumps(events, indent=2), encoding="utf-8")
    with (output / "block_flag_counts.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(["check_code", "flag_count"]); writer.writerows(sorted(counts.items()))
    (output / "block_flag_counts.md").write_text("# Flag counts\n\n" + "\n".join(f"- {key}: {value}" for key, value in sorted(counts.items())), encoding="utf-8")
    return {"images": len(reports), "flag_counts": dict(counts), "flag_events": len(events)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    print(asyncio.run(run(args.folder, args.output, args.csv)))


if __name__ == "__main__":
    main()
