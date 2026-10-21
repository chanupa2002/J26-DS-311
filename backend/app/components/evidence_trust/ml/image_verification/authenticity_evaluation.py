"""Offline screen-detector robustness report under compression and resizing."""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Any

from PIL import Image

from .authenticity import AuthenticityBlock
from .contracts import ImageInput
from .image_loader import load_context
from .quality import load_quality_config


def evaluate_screen_robustness(image_path: str | Path, output: str | Path, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Report screen-signal stability for JPEG qualities and resize factors."""
    source = Image.open(image_path).convert("RGB")
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    settings = config or {"authenticity": {"screen_enabled": True, "web_match_enabled": False, "ai_generated_enabled": False}}
    block = AuthenticityBlock(settings)
    rows: list[dict[str, Any]] = []
    for quality in (95, 75, 50, 25):
        for factor in (1.0, 0.75, 0.5):
            width = max(1, int(source.width * factor))
            transformed = source.resize((width, max(1, int(source.height * factor))))
            buffer = io.BytesIO()
            transformed.save(buffer, "JPEG", quality=quality)
            context = load_context(ImageInput(buffer.getvalue(), "robustness", "unknown"), 512)
            result = __import__("asyncio").run(block.run(context))
            check = result.checks[0]
            rows.append({"jpeg_quality": quality, "resize_factor": factor, "value": check.value, "raw_measure": check.raw_measure})
    csv_path = output_path / "screen_robustness.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["jpeg_quality", "resize_factor", "value", "raw_measure"])
        writer.writeheader(); writer.writerows(rows)
    detection_rate = sum(row["value"] == 0 for row in rows) / len(rows) if rows else None
    summary = {"cases": len(rows), "screen_detection_rate": detection_rate, "csv": str(csv_path)}
    (output_path / "screen_robustness.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_path / "screen_robustness.md").write_text(f"# Screen robustness\n\nDetection rate: {detection_rate}\nCases: {len(rows)}\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(evaluate_screen_robustness(args.image, args.output))


if __name__ == "__main__":
    main()
