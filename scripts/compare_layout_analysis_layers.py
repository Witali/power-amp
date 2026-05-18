#!/usr/bin/env python3
"""Render comparable OpenCV, frequency, histogram, and balance layout previews."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import detect_page_layout  # noqa: E402
import layout_analysis_thresholds as thresholds  # noqa: E402
import layout_frequency  # noqa: E402


LABEL_COLORS = layout_frequency.LABEL_COLORS


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="Input page image.")
    parser.add_argument("--out-dir", default="study/layout_analysis_comparison", help="Output root.")
    parser.add_argument("--max-analysis-side", type=int, default=1800, help="Largest analysis side.")
    parser.add_argument("--preview-width", type=int, default=1100, help="Preview width.")
    parser.add_argument("--tile-size", type=int, default=layout_frequency.DEFAULT_TILE_SIZE, help="Frequency tile size.")
    parser.add_argument("--stride", type=int, default=layout_frequency.DEFAULT_STRIDE, help="Frequency tile stride.")
    return parser.parse_args(argv)


def preview_image(image, preview_width: int):
    cv2 = layout_frequency.cv2

    height, width = image.shape[:2]
    scale = min(1.0, preview_width / float(width))
    if scale >= 0.999:
        return image.copy(), 1.0
    preview = cv2.resize(image, (int(round(width * scale)), int(round(height * scale))), interpolation=cv2.INTER_AREA)
    return preview, scale


def counts_text(items: list[dict[str, object]]) -> str:
    counts = layout_frequency.label_counts(items)
    return ", ".join(f"{key}={value}" for key, value in counts.items()) or "none"


def histogram_only_label(features: dict[str, float]) -> str:
    ink = float(features.get("ink_density", 0.0))
    gray_std = float(features.get("gray_std", 0.0))
    dark_light = float(features.get("luma_dark_light_ratio", 0.0))
    luma_dark = float(features.get("luma_dark_fraction", 0.0))
    luma_light = float(features.get("luma_light_fraction", 0.0))
    luma_mid = float(features.get("luma_mid_fraction", 0.0))
    luma_entropy = float(features.get("luma_hist_entropy", 0.0))
    luma_bimodal = float(features.get("luma_bimodal_score", 0.0))
    saturation_high = float(features.get("saturation_high_fraction", 0.0))
    color_fraction = float(features.get("color_pixel_fraction", 0.0))

    if ink < thresholds.HISTOGRAM_BACKGROUND_MAX_INK or (
        luma_light > thresholds.HISTOGRAM_BACKGROUND_MIN_LIGHT
        and luma_dark < thresholds.HISTOGRAM_BACKGROUND_MAX_DARK
        and luma_mid < thresholds.HISTOGRAM_BACKGROUND_MAX_MID
    ):
        return "background"
    if (
        ink > thresholds.HISTOGRAM_IMAGE_MIN_INK
        and (
            saturation_high > thresholds.HISTOGRAM_IMAGE_MIN_HIGH_SATURATION
            or (
                color_fraction > thresholds.HISTOGRAM_IMAGE_MIN_COLOR_FRACTION
                and luma_mid > thresholds.HISTOGRAM_IMAGE_MIN_COLOR_MID
            )
            or (
                luma_mid > thresholds.HISTOGRAM_IMAGE_MIN_MID
                and luma_entropy > thresholds.HISTOGRAM_IMAGE_MIN_ENTROPY
            )
        )
    ):
        return "image"
    if (
        ink > thresholds.HISTOGRAM_SCHEMATIC_MIN_INK
        and dark_light <= thresholds.HISTOGRAM_SCHEMATIC_MAX_DARK_LIGHT_RATIO
        and luma_light > thresholds.HISTOGRAM_SCHEMATIC_MIN_LIGHT
        and luma_mid < thresholds.HISTOGRAM_SCHEMATIC_MAX_MID
    ):
        return "schematic/circuit"
    if (
        ink > thresholds.HISTOGRAM_TEXT_MIN_INK
        and thresholds.HISTOGRAM_TEXT_MIN_DARK_LIGHT_RATIO <= dark_light <= thresholds.HISTOGRAM_TEXT_MAX_DARK_LIGHT_RATIO
        and luma_mid < thresholds.HISTOGRAM_TEXT_MAX_MID
        and (
            luma_bimodal > thresholds.HISTOGRAM_TEXT_MIN_BIMODAL
            or luma_entropy > thresholds.HISTOGRAM_TEXT_MIN_ENTROPY
        )
    ):
        return "text"
    return "other"


def balance_only_label(features: dict[str, float]) -> str:
    ink = float(features.get("ink_density", 0.0))
    gray_std = float(features.get("gray_std", 0.0))
    dark_light = float(features.get("luma_dark_light_ratio", 0.0))
    luma_mid = float(features.get("luma_mid_fraction", 0.0))
    luma_light = float(features.get("luma_light_fraction", 0.0))

    if ink < thresholds.BALANCE_BACKGROUND_MAX_INK or (
        luma_light > thresholds.BALANCE_BACKGROUND_MIN_LIGHT
        and dark_light < thresholds.BALANCE_BACKGROUND_MAX_DARK_LIGHT_RATIO
    ):
        return "background"
    if (
        ink > thresholds.BALANCE_SCHEMATIC_MIN_INK
        and dark_light <= thresholds.BALANCE_SCHEMATIC_MAX_DARK_LIGHT_RATIO
        and luma_light > thresholds.BALANCE_SCHEMATIC_MIN_LIGHT
    ):
        return "schematic/circuit"
    if (
        ink > thresholds.BALANCE_TEXT_MIN_INK
        and thresholds.BALANCE_TEXT_MIN_DARK_LIGHT_RATIO < dark_light <= thresholds.BALANCE_TEXT_MAX_DARK_LIGHT_RATIO
        and luma_mid < thresholds.BALANCE_TEXT_MAX_MID
    ):
        return "text"
    if ink > thresholds.BALANCE_IMAGE_MIN_INK and (
        dark_light > thresholds.BALANCE_IMAGE_MIN_DARK_LIGHT_RATIO
        or luma_mid > thresholds.BALANCE_IMAGE_MIN_MID
    ):
        return "image"
    return "other"


def draw_tile_layer(
    original,
    frequency_result: dict[str, object],
    analysis_scale: float,
    preview_width: int,
    classifier,
):
    cv2 = layout_frequency.cv2

    preview, preview_scale = preview_image(original, preview_width)
    overlay = preview.copy()
    classified_tiles: list[dict[str, object]] = []

    for tile in frequency_result.get("tiles", []):
        if not isinstance(tile, dict):
            continue
        features = tile.get("features")
        bbox = tile.get("bbox")
        if not isinstance(features, dict) or not isinstance(bbox, list) or len(bbox) != 4:
            continue
        label = classifier({str(key): float(value) for key, value in features.items()})
        if label == "background":
            continue
        original_bbox = layout_frequency.scale_bbox([int(value) for value in bbox], analysis_scale)
        x, y, w, h = original_bbox
        x1 = int(round(x * preview_scale))
        y1 = int(round(y * preview_scale))
        x2 = int(round((x + w) * preview_scale))
        y2 = int(round((y + h) * preview_scale))
        color = LABEL_COLORS.get(label, LABEL_COLORS["other"])
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
        classified_tiles.append({"label": label, "bbox": original_bbox})

    preview = cv2.addWeighted(overlay, thresholds.TILE_OVERLAY_ALPHA, preview, thresholds.TILE_BASE_ALPHA, 0)
    for tile in classified_tiles:
        x, y, w, h = [int(value) for value in tile["bbox"]]
        x1 = int(round(x * preview_scale))
        y1 = int(round(y * preview_scale))
        x2 = int(round((x + w) * preview_scale))
        y2 = int(round((y + h) * preview_scale))
        color = LABEL_COLORS.get(str(tile["label"]), LABEL_COLORS["other"])
        cv2.rectangle(preview, (x1, y1), (x2, y2), color, 1)

    return preview, classified_tiles


def write_labeled(path: Path, image, title: str, subtitle: str) -> Path:
    labeled = layout_frequency.add_title_header(image, title, subtitle)
    layout_frequency.write_image(path, labeled)
    return path


def build_frequency_result(image_path: Path, max_analysis_side: int, tile_size: int, stride: int) -> tuple[object, float, dict[str, object]]:
    original = layout_frequency.read_image(image_path)
    analysis, scale = layout_frequency.resize_for_analysis(original, max_analysis_side)
    frequency = layout_frequency.analyze_image(analysis, tile_size=tile_size, stride=stride)
    result: dict[str, object] = {
        "source": str(image_path),
        "page": image_path.stem,
        "width": int(original.shape[1]),
        "height": int(original.shape[0]),
        "analysis_scale": scale,
        "tiles": frequency["tiles"],
        "hints": frequency["hints"],
        "cluster_hints": frequency.get("cluster_hints", []),
        "hints_original": layout_frequency.hints_in_original_coordinates(frequency["hints"], scale),
        "cluster_hints_original": layout_frequency.hints_in_original_coordinates(frequency.get("cluster_hints", []), scale),
        "frequency": {
            key: value
            for key, value in frequency.items()
            if key not in {"tiles", "hints", "cluster_hints"}
        },
    }
    return original, scale, result


def write_summary(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def main(argv: list[str]) -> int:
    detect_page_layout.require_dependencies()
    layout_frequency.require_dependencies()
    args = parse_args(argv)

    image_path = Path(args.image)
    page_dir = Path(args.out_dir) / image_path.stem
    raw_dir = page_dir / "_raw"
    page_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    opencv_result = detect_page_layout.detect_page_layout(
        image_path,
        raw_dir / "opencv",
        max_analysis_side=args.max_analysis_side,
        preview_width=args.preview_width,
        frequency_hints="off",
        preview_header=False,
    )
    opencv_preview = layout_frequency.read_image(raw_dir / "opencv" / image_path.stem / opencv_result["preview"])
    opencv_counts = counts_text(list(opencv_result.get("blocks", [])))
    opencv_path = write_labeled(
        page_dir / "01_opencv_layout.png",
        opencv_preview,
        "OpenCV layout detector",
        f"{image_path.name} | blocks: {opencv_counts}",
    )

    original, analysis_scale, frequency_result = build_frequency_result(
        image_path,
        args.max_analysis_side,
        args.tile_size,
        args.stride,
    )
    frequency_raw = raw_dir / "frequency_preview.png"
    layout_frequency.draw_frequency_preview(original, frequency_result, args.preview_width, frequency_raw, add_header=False)
    frequency_preview = layout_frequency.read_image(frequency_raw)
    frequency_path = write_labeled(
        page_dir / "02_frequency_analysis.png",
        frequency_preview,
        "Frequency analysis: FFT + features + clusters",
        f"hints: {counts_text(list(frequency_result['hints']))} | clusters: {counts_text(list(frequency_result['cluster_hints']))}",
    )

    histogram_preview, histogram_tiles = draw_tile_layer(
        original,
        frequency_result,
        analysis_scale,
        args.preview_width,
        histogram_only_label,
    )
    histogram_path = write_labeled(
        page_dir / "03_histogram_only.png",
        histogram_preview,
        "Histogram-only tile recognition",
        f"tiles: {counts_text(histogram_tiles)}",
    )

    balance_preview, balance_tiles = draw_tile_layer(
        original,
        frequency_result,
        analysis_scale,
        args.preview_width,
        balance_only_label,
    )
    balance_path = write_labeled(
        page_dir / "04_dark_light_balance.png",
        balance_preview,
        "Dark/light balance-only recognition",
        f"tiles: {counts_text(balance_tiles)}",
    )

    frequency_json = page_dir / "frequency_layout.json"
    layout_frequency.write_json(frequency_json, frequency_result)
    opencv_json = page_dir / "opencv_layout.json"
    shutil.copyfile(raw_dir / "opencv" / image_path.stem / "layout.json", opencv_json)
    summary = {
        "source": str(image_path),
        "opencv_preview": str(opencv_path),
        "frequency_preview": str(frequency_path),
        "histogram_preview": str(histogram_path),
        "balance_preview": str(balance_path),
        "opencv_counts": layout_frequency.label_counts(list(opencv_result.get("blocks", []))),
        "frequency_hint_counts": layout_frequency.label_counts(list(frequency_result["hints"])),
        "frequency_cluster_counts": layout_frequency.label_counts(list(frequency_result["cluster_hints"])),
        "histogram_tile_counts": layout_frequency.label_counts(histogram_tiles),
        "balance_tile_counts": layout_frequency.label_counts(balance_tiles),
    }
    write_summary(page_dir / "summary.json", summary)

    print(opencv_path)
    print(frequency_path)
    print(histogram_path)
    print(balance_path)
    print(opencv_json)
    print(frequency_json)
    print(page_dir / "summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
