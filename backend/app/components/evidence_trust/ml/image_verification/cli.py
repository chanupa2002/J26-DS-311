"""Command-line entry point for folder-based foundation runs."""

from __future__ import annotations

import argparse
import asyncio
import csv
from pathlib import Path

from .contracts import ImageInput
from .pipeline import ImageVerificationPipeline
from .report import write_batch_report, write_report


def _inputs(folder: Path, csv_path: Path | None) -> list[ImageInput]:
    if csv_path:
        with csv_path.open(newline="", encoding="utf-8") as handle:
            rows = csv.DictReader(handle)
            return [ImageInput(folder / row["file_name"], row["household_id"], row["month"], row.get("registered_category") or None) for row in rows]
    return [ImageInput(path, path.stem, "unknown") for path in sorted(folder.iterdir()) if path.is_file()]


async def run(args: argparse.Namespace) -> None:
    images = _inputs(args.folder, args.csv)
    pipeline = ImageVerificationPipeline()
    reports = await pipeline.process_many(images)
    for index, report in enumerate(reports):
        write_report(report, args.output, f"{index:04d}_{report.input_summary['household_id']}")
    write_batch_report(reports, args.output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run evidence image verification foundation")
    parser.add_argument("folder", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--csv", type=Path, default=None, help="Optional photo list CSV")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
