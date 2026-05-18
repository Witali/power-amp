#!/usr/bin/env python3
"""Measure frequency features on reviewed page-layout blocks."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import layout_frequency  # noqa: E402


FEATURE_KEYS = [
    "ink_density",
    "gray_std",
    "saturation_p80",
    "row_period_score",
    "column_period_score",
    "row_entropy",
    "column_entropy",
    "hline_density",
    "vline_density",
    "line_balance",
    "row_dominant_period",
    "column_dominant_period",
    "gray_row_dominant_period",
    "gray_column_dominant_period",
]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images-dir", default=".tmp/layout_candidate_pages", help="Directory with original checked page scans.")
    parser.add_argument(
        "--layouts-dir",
        default=".tmp/layout_frequency_calibration_layouts",
        help="Directory with layout.json files for checked pages.",
    )
    parser.add_argument("--out-md", default="study/layout_frequency_calibration.md", help="Markdown report path.")
    parser.add_argument("--out-json", default="study/layout_frequency_calibration.json", help="Machine-readable report path.")
    parser.add_argument("--max-analysis-side", type=int, default=1800)
    parser.add_argument("--tile-size", type=int, default=192)
    parser.add_argument("--stride", type=int, default=96)
    parser.add_argument("--min-overlap", type=float, default=0.58)
    return parser.parse_args(argv)


def overlap_area(first: list[int], second: list[int]) -> int:
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    left = max(ax, bx)
    top = max(ay, by)
    right = min(ax + aw, bx + bw)
    bottom = min(ay + ah, by + bh)
    return max(0, right - left) * max(0, bottom - top)


def source_image_for_layout(layout_path: Path, images_dir: Path) -> Path:
    page_name = layout_path.parent.name
    candidates = [
        images_dir / f"{page_name}.jpg",
        images_dir / f"{page_name}.png",
        images_dir / f"{page_name}.jpeg",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No source image for layout page {page_name} in {images_dir}")


def percentiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(float(value) for value in values)

    def pick(percent: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        index = (len(ordered) - 1) * percent / 100.0
        lower = int(index)
        upper = min(len(ordered) - 1, lower + 1)
        ratio = index - lower
        return ordered[lower] * (1.0 - ratio) + ordered[upper] * ratio

    return {
        "min": ordered[0],
        "p05": pick(5.0),
        "p25": pick(25.0),
        "median": pick(50.0),
        "p75": pick(75.0),
        "p95": pick(95.0),
        "max": ordered[-1],
        "mean": statistics.fmean(ordered),
        "stdev": statistics.pstdev(ordered),
    }


def rounded_stats(values: list[float]) -> dict[str, float]:
    return {key: round(value, 5) for key, value in percentiles(values).items()}


def normalize_truth_label(label: str) -> str:
    return "schematic/circuit" if label == "schematic" else label


def collect_samples(args: argparse.Namespace) -> tuple[list[dict[str, object]], dict[str, int]]:
    images_dir = Path(args.images_dir)
    layouts_dir = Path(args.layouts_dir)
    samples: list[dict[str, object]] = []
    pages: dict[str, int] = {}

    for layout_path in sorted(layouts_dir.glob("*/layout.json")):
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
        source_image = source_image_for_layout(layout_path, images_dir)
        original = layout_frequency.read_image(source_image)
        analysis, scale = layout_frequency.resize_for_analysis(original, args.max_analysis_side)
        height, width = analysis.shape[:2]
        gray = layout_frequency.cv2.cvtColor(analysis, layout_frequency.cv2.COLOR_BGR2GRAY)
        mask, _, _ = layout_frequency.foreground_mask(gray)

        blocks: list[tuple[str, str, list[int]]] = []
        for block in layout.get("blocks", []):
            label = normalize_truth_label(str(block.get("label", "other")))
            if label == "other":
                continue
            bbox = [int(round(float(value) * scale)) for value in block.get("bbox", [])]
            if len(bbox) != 4:
                continue
            blocks.append((str(block.get("ident", "")), label, bbox))
        pages[layout_path.parent.name] = len(blocks)

        for y in layout_frequency.tile_positions(height, args.tile_size, args.stride):
            for x in layout_frequency.tile_positions(width, args.tile_size, args.stride):
                tile = [x, y, min(args.tile_size, width - x), min(args.tile_size, height - y)]
                tile_area = max(1, tile[2] * tile[3])
                best_block: tuple[str, str, list[int]] | None = None
                best_overlap = 0
                for block in blocks:
                    overlap = overlap_area(tile, block[2])
                    if overlap > best_overlap:
                        best_block = block
                        best_overlap = overlap
                if best_block is None or best_overlap / tile_area < args.min_overlap:
                    continue

                features = layout_frequency.tile_features(analysis, gray, mask, x, y, args.tile_size)
                predicted_label, confidence = layout_frequency.classify_frequency_features(features)
                samples.append(
                    {
                        "page": layout_path.parent.name,
                        "block": best_block[0],
                        "truth": best_block[1],
                        "predicted": predicted_label,
                        "confidence": round(float(confidence), 5),
                        "features": {key: round(float(features.get(key, 0.0)), 5) for key in FEATURE_KEYS},
                    }
                )
    return samples, pages


def summarize(samples: list[dict[str, object]], pages: dict[str, int]) -> dict[str, object]:
    by_label: dict[str, list[dict[str, object]]] = defaultdict(list)
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    for sample in samples:
        truth = str(sample["truth"])
        predicted = str(sample["predicted"])
        by_label[truth].append(sample)
        confusion[truth][predicted] += 1

    label_stats: dict[str, object] = {}
    for label, rows in sorted(by_label.items()):
        feature_stats = {}
        for key in FEATURE_KEYS:
            values = [float(row["features"][key]) for row in rows]  # type: ignore[index]
            feature_stats[key] = rounded_stats(values)
        blocks = {(str(row["page"]), str(row["block"])) for row in rows}
        label_stats[label] = {
            "tiles": len(rows),
            "pages": len({str(row["page"]) for row in rows}),
            "blocks": len(blocks),
            "features": feature_stats,
        }

    confusion_dict = {truth: dict(counter) for truth, counter in sorted(confusion.items())}
    total = sum(sum(counter.values()) for counter in confusion.values())
    correct = sum(counter.get(truth, 0) for truth, counter in confusion.items())
    return {
        "pages": dict(sorted(pages.items())),
        "tile_count": len(samples),
        "overall_accuracy": round(correct / total, 5) if total else 0.0,
        "confusion": confusion_dict,
        "labels": label_stats,
        "constants": {
            "TEXT_ROW_PERIOD_BAND": layout_frequency.TEXT_ROW_PERIOD_BAND,
            "TEXT_COLUMN_PERIOD_BAND": layout_frequency.TEXT_COLUMN_PERIOD_BAND,
            "BACKGROUND_MAX_INK": layout_frequency.BACKGROUND_MAX_INK,
            "BACKGROUND_MAX_GRAY_STD": layout_frequency.BACKGROUND_MAX_GRAY_STD,
            "STRONG_TEXT_ROW_PERIOD": layout_frequency.STRONG_TEXT_ROW_PERIOD,
            "STRONG_TEXT_ROW_ENTROPY_MAX": layout_frequency.STRONG_TEXT_ROW_ENTROPY_MAX,
            "LINE_ART_MAX_INK": layout_frequency.LINE_ART_MAX_INK,
            "LINE_ART_MIN_ENTROPY": layout_frequency.LINE_ART_MIN_ENTROPY,
            "LINE_ART_MIN_LINE_DENSITY": layout_frequency.LINE_ART_MIN_LINE_DENSITY,
            "LINE_ART_MIN_BALANCE": layout_frequency.LINE_ART_MIN_BALANCE,
            "IMAGE_STRONG_SATURATION": layout_frequency.IMAGE_STRONG_SATURATION,
        },
    }


def format_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Layout Frequency Calibration",
        "",
        "Калибровка построена по исходным сканам страниц, которые проверялись через PNG-превью в `study/layout_detection_marked_pages/`.",
        "Цветные рамки превью не используются для измерений, чтобы не вносить искусственные частоты.",
        "",
        f"- Pages: {len(summary['pages'])}",
        f"- Calibrated tiles: {summary['tile_count']}",
        f"- Tile classifier accuracy against reviewed blocks: {summary['overall_accuracy']}",
        "",
        "## Constants",
        "",
    ]
    constants = summary["constants"]
    for key, value in constants.items():  # type: ignore[union-attr]
        lines.append(f"- `{key}` = `{value}`")

    lines.extend(["", "## Confusion Matrix", ""])
    confusion = summary["confusion"]
    for truth, row in confusion.items():  # type: ignore[union-attr]
        lines.append(f"- `{truth}`: {row}")

    lines.extend(["", "## Feature Ranges", ""])
    labels = summary["labels"]
    for label, info in labels.items():  # type: ignore[union-attr]
        lines.append(f"### {label}")
        lines.append("")
        lines.append(f"- tiles: {info['tiles']}, pages: {info['pages']}, blocks: {info['blocks']}")
        lines.append("")
        lines.append("| Feature | p05 | median | p95 | mean | stdev |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for feature in FEATURE_KEYS:
            stats = info["features"][feature]
            lines.append(
                f"| `{feature}` | {stats['p05']:.5f} | {stats['median']:.5f} | "
                f"{stats['p95']:.5f} | {stats['mean']:.5f} | {stats['stdev']:.5f} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    layout_frequency.require_dependencies()
    samples, pages = collect_samples(args)
    summary = summarize(samples, pages)

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(format_markdown(summary), encoding="utf-8")

    print(f"Calibrated {summary['tile_count']} tile(s) from {len(summary['pages'])} page(s).")
    print(f"Accuracy: {summary['overall_accuracy']}")
    print(out_json)
    print(out_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
