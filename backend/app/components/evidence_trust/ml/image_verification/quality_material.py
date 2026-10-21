"""Generate synthetic quality-defect ladders for local calibration only."""

from __future__ import annotations

import argparse
import csv
import io
import json
import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter


def _variants(image: Image.Image, seed: int) -> list[tuple[str, int, Image.Image, dict[str, Any]]]:
    rng = random.Random(seed)
    variants: list[tuple[str, int, Image.Image, dict[str, Any]]] = []
    for level in range(1, 6):
        variants.append(("blur", level, image.filter(ImageFilter.GaussianBlur(0.8 * level)), {"radius": 0.8 * level}))
        variants.append(("dark", level, ImageEnhance.Brightness(image).enhance(1.0 - 0.12 * level), {"factor": 1.0 - 0.12 * level}))
        bright = ImageEnhance.Brightness(image).enhance(1.0 + 0.16 * level)
        variants.append(("overexposed", level, bright, {"factor": 1.0 + 0.16 * level}))
        scale = max(1, int(max(image.size) * (1.0 - 0.15 * level)))
        variants.append(("downscale", level, image.resize((scale, max(1, int(image.height * scale / image.width)))), {"longest_side": scale}))
        quality = max(10, 95 - 17 * level)
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=quality, optimize=True)
        variants.append(("jpeg", level, Image.open(io.BytesIO(buffer.getvalue())).convert("RGB"), {"quality": quality, "jitter": rng.random()}))
    return variants


def build_ladder(input_folder: str | Path, output_folder: str | Path, seed: int = 7) -> Path:
    """Create a five-level ladder and return its manifest path."""
    source_folder, output = Path(input_folder), Path(output_folder)
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for source in sorted(source_folder.iterdir()):
        if not source.is_file():
            continue
        try:
            image = Image.open(source).convert("RGB")
        except (OSError, ValueError):
            continue
        for defect, level, variant, parameters in _variants(image, seed):
            name = f"{source.stem}_{defect}_{level}.jpg"
            variant.save(output / name, "JPEG", quality=95)
            rows.append({"original_file": str(source), "defect": defect, "level": level, "output_file": name, "parameters": json.dumps(parameters), "random_seed": seed})
    manifest = output / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["original_file", "defect", "level", "output_file", "parameters", "random_seed"])
        writer.writeheader()
        writer.writerows(rows)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_folder", type=Path)
    parser.add_argument("output_folder", type=Path)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    print(build_ladder(args.input_folder, args.output_folder, args.seed))


if __name__ == "__main__":
    main()
