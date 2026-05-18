#!/usr/bin/env python3
"""Generate page layout hints from 1D frequency analysis of page tiles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import layout_frequency  # noqa: E402


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="Input page image.")
    parser.add_argument("--out-dir", default=".tmp/page_frequency", help="Output root for frequency JSON and preview.")
    parser.add_argument("--layout", help="Optional OpenCV layout.json to validate against frequency hints.")
    parser.add_argument("--max-analysis-side", type=int, default=1800, help="Largest side used during frequency analysis.")
    parser.add_argument(
        "--tile-size",
        type=int,
        default=layout_frequency.DEFAULT_TILE_SIZE,
        help="Square tile size for local 1D frequency analysis.",
    )
    parser.add_argument("--stride", type=int, default=layout_frequency.DEFAULT_STRIDE, help="Tile stride in pixels.")
    parser.add_argument("--preview-width", type=int, default=1400, help="Preview overlay width in pixels.")
    parser.add_argument("--min-hint-confidence", type=float, default=0.42, help="Lowest tile confidence used when merging hints.")
    return parser.parse_args(argv)


def build_result(args: argparse.Namespace) -> dict[str, object]:
    image_path = Path(args.image)
    original = layout_frequency.read_image(image_path)
    analysis, scale = layout_frequency.resize_for_analysis(original, args.max_analysis_side)
    frequency = layout_frequency.analyze_image(
        analysis,
        tile_size=args.tile_size,
        stride=args.stride,
        min_hint_confidence=args.min_hint_confidence,
    )
    result: dict[str, object] = {
        "source": str(image_path),
        "page": image_path.stem,
        "width": int(original.shape[1]),
        "height": int(original.shape[0]),
        "analysis_scale": scale,
        "frequency": {
            key: value
            for key, value in frequency.items()
            if key not in {"tiles", "hints", "cluster_hints"}
        },
        "tiles": frequency["tiles"],
        "hints": frequency["hints"],
        "cluster_hints": frequency.get("cluster_hints", []),
        "hints_original": layout_frequency.hints_in_original_coordinates(frequency["hints"], scale),
        "cluster_hints_original": layout_frequency.hints_in_original_coordinates(frequency.get("cluster_hints", []), scale),
    }

    if args.layout:
        layout_path = Path(args.layout)
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
        blocks = list(layout.get("blocks", []))
        result["layout"] = str(layout_path)
        result["layout_warnings"] = layout_frequency.validate_layout_blocks(blocks, result["hints_original"])
        result["layout_cluster_warnings"] = layout_frequency.validate_layout_blocks(blocks, result["cluster_hints_original"])

    return result


def main(argv: list[str]) -> int:
    layout_frequency.require_dependencies()
    args = parse_args(argv)
    result = build_result(args)

    page_dir = Path(args.out_dir) / str(result["page"])
    page_dir.mkdir(parents=True, exist_ok=True)
    json_path = page_dir / "frequency_layout.json"
    preview_path = page_dir / "frequency_preview.png"
    layout_frequency.write_json(json_path, result)
    original = layout_frequency.read_image(Path(args.image))
    layout_frequency.draw_frequency_preview(original, result, args.preview_width, preview_path)

    counts = layout_frequency.label_counts(result["hints"])
    counts_text = ", ".join(f"{key}={value}" for key, value in counts.items()) or "none"
    cluster_counts = layout_frequency.label_counts(result["cluster_hints"])
    cluster_counts_text = ", ".join(f"{key}={value}" for key, value in cluster_counts.items()) or "none"
    warnings = len(result.get("layout_warnings", []))
    cluster_warnings = len(result.get("layout_cluster_warnings", []))
    print(f"Frequency hints: {len(result['hints'])} ({counts_text})")
    print(f"Cluster hints: {len(result['cluster_hints'])} ({cluster_counts_text})")
    if args.layout:
        print(f"Layout warnings: {warnings}")
        print(f"Layout cluster warnings: {cluster_warnings}")
    print(json_path)
    print(preview_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
