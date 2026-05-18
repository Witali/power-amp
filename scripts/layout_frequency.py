#!/usr/bin/env python3
"""Frequency-domain page layout hints for OCR page segmentation."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_PACKAGES = PROJECT_ROOT / "local_tools" / "python_packages"
if LOCAL_PACKAGES.exists():
    sys.path.insert(0, str(LOCAL_PACKAGES))

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore

    OPENCV_AVAILABLE = True
except ImportError:
    cv2 = None  # type: ignore
    np = None  # type: ignore
    OPENCV_AVAILABLE = False


LABEL_COLORS = {
    "text": (52, 168, 83),
    "image": (66, 133, 244),
    "schematic/circuit": (234, 67, 53),
    "diagram": (251, 188, 5),
    "table": (171, 71, 188),
    "other": (128, 128, 128),
    "background": (190, 190, 190),
}
HINT_LABELS = {"text", "image", "schematic/circuit", "diagram", "table", "other"}


def require_dependencies() -> None:
    if OPENCV_AVAILABLE:
        return
    raise SystemExit(
        "OpenCV frequency analysis dependencies are missing. "
        "Run: python -m pip install --target local_tools\\python_packages "
        "opencv-python-headless numpy"
    )


def read_image(path: Path):
    require_dependencies()
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return image


def write_image(path: Path, image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower() or ".png"
    ok, encoded = cv2.imencode(suffix, image)
    if not ok:
        raise ValueError(f"Could not encode image as {suffix}: {path}")
    encoded.tofile(str(path))


def resize_for_analysis(image, max_side: int):
    height, width = image.shape[:2]
    scale = min(1.0, max_side / float(max(width, height)))
    if scale >= 0.999:
        return image.copy(), 1.0
    target = (int(round(width * scale)), int(round(height * scale)))
    return cv2.resize(image, target, interpolation=cv2.INTER_AREA), scale


def tile_positions(length: int, tile_size: int, stride: int) -> list[int]:
    if length <= tile_size:
        return [0]
    positions = list(range(0, length - tile_size + 1, stride))
    last = length - tile_size
    if not positions or positions[-1] != last:
        positions.append(last)
    return positions


def band_energy_ratio(profile, min_period: float, max_period: float) -> float:
    signal = profile.astype(np.float32)
    if signal.size < 8:
        return 0.0
    signal = signal - float(signal.mean())
    std = float(signal.std())
    if std < 1e-6:
        return 0.0
    window = np.hanning(signal.size).astype(np.float32)
    spectrum = np.fft.rfft(signal * window)
    power = (spectrum.real * spectrum.real) + (spectrum.imag * spectrum.imag)
    if power.size <= 1:
        return 0.0
    power[0] = 0.0
    total = float(power.sum())
    if total <= 1e-9:
        return 0.0
    indices = np.arange(power.size, dtype=np.float32)
    periods = np.full(power.size, np.inf, dtype=np.float32)
    periods[1:] = signal.size / indices[1:]
    band = (periods >= min_period) & (periods <= max_period)
    return float(power[band].sum() / total)


def spectral_entropy(profile) -> float:
    signal = profile.astype(np.float32)
    if signal.size < 8:
        return 0.0
    signal = signal - float(signal.mean())
    if float(signal.std()) < 1e-6:
        return 0.0
    spectrum = np.fft.rfft(signal * np.hanning(signal.size).astype(np.float32))
    power = (spectrum.real * spectrum.real) + (spectrum.imag * spectrum.imag)
    if power.size <= 1:
        return 0.0
    power = power[1:]
    total = float(power.sum())
    if total <= 1e-9:
        return 0.0
    probability = power / total
    entropy = -float((probability * np.log2(probability + 1e-12)).sum())
    return entropy / math.log2(max(2, probability.size))


def foreground_mask(gray):
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    threshold, _ = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    dark = gray <= threshold
    light = gray > threshold
    bright_foreground = int(light.sum()) < int(dark.sum())
    mask = light if bright_foreground else dark
    return (mask.astype(np.uint8) * 255), int(threshold), bright_foreground


def line_densities(mask) -> tuple[float, float, float]:
    height, width = mask.shape[:2]
    area = max(1, width * height)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(10, width // 3), 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(10, height // 3)))
    h_lines = cv2.morphologyEx(mask, cv2.MORPH_OPEN, h_kernel)
    v_lines = cv2.morphologyEx(mask, cv2.MORPH_OPEN, v_kernel)
    h_density = float((h_lines > 0).sum()) / area
    v_density = float((v_lines > 0).sum()) / area
    balance = min(h_density, v_density) / max(h_density, v_density, 1e-6)
    return h_density, v_density, balance


def tile_features(image, gray, mask, x: int, y: int, tile_size: int) -> dict[str, float]:
    roi_gray = gray[y : y + tile_size, x : x + tile_size]
    roi_image = image[y : y + tile_size, x : x + tile_size]
    roi_mask = mask[y : y + tile_size, x : x + tile_size]
    if roi_gray.size == 0:
        return {}

    darkness = 1.0 - (roi_gray.astype(np.float32) / 255.0)
    ink = (roi_mask > 0).astype(np.float32)
    row_profile = ink.mean(axis=1)
    column_profile = ink.mean(axis=0)
    gray_row_profile = darkness.mean(axis=1)
    gray_column_profile = darkness.mean(axis=0)

    h_density, v_density, line_balance = line_densities(roi_mask)
    hsv = cv2.cvtColor(roi_image, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1].astype(np.float32) / 255.0

    row_text_period = max(
        band_energy_ratio(row_profile, 7.0, 34.0),
        band_energy_ratio(gray_row_profile, 7.0, 34.0),
    )
    column_text_period = max(
        band_energy_ratio(column_profile, 4.0, 24.0),
        band_energy_ratio(gray_column_profile, 4.0, 24.0),
    )

    return {
        "ink_density": float(ink.mean()),
        "gray_std": min(float(roi_gray.std()) / 90.0, 1.0),
        "saturation_mean": float(saturation.mean()),
        "saturation_p80": float(np.percentile(saturation, 80)),
        "row_period_score": row_text_period,
        "column_period_score": column_text_period,
        "row_entropy": spectral_entropy(gray_row_profile),
        "column_entropy": spectral_entropy(gray_column_profile),
        "hline_density": min(h_density * 8.0, 1.0),
        "vline_density": min(v_density * 8.0, 1.0),
        "line_balance": line_balance,
    }


def classify_frequency_features(features: dict[str, float]) -> tuple[str, float]:
    if not features:
        return "background", 0.0
    ink = features["ink_density"]
    row_period = features["row_period_score"]
    column_period = features["column_period_score"]
    hline = features["hline_density"]
    vline = features["vline_density"]
    balance = features["line_balance"]
    entropy = (features["row_entropy"] + features["column_entropy"]) / 2.0
    saturation = features["saturation_p80"]
    gray_std = features["gray_std"]

    if ink < 0.010 and gray_std < 0.08:
        return "background", min(0.98, 0.72 + (0.010 - ink) * 12.0)

    scores = {
        "text": 1.8 * row_period + 0.6 * column_period + 0.7 * ink - 0.7 * balance - 0.35 * saturation,
        "schematic/circuit": 1.3 * hline + 1.3 * vline + 1.1 * balance + 0.45 * entropy - 0.55 * saturation,
        "table": 1.2 * min(hline, vline) + 1.1 * balance + 0.45 * min(row_period, column_period),
        "image": 1.0 * entropy + 0.9 * gray_std + 0.9 * saturation + 0.4 * ink - 0.35 * row_period,
        "other": 0.20 + 0.25 * ink + 0.15 * entropy,
    }

    if row_period > 0.20 and hline < 0.35 and vline < 0.35:
        scores["text"] += 0.70
    if hline > 0.18 and vline > 0.12 and balance > 0.25:
        scores["schematic/circuit"] += 0.75
    if min(hline, vline) > 0.20 and balance > 0.50 and min(row_period, column_period) > 0.12:
        scores["table"] += 0.65
    if saturation > 0.16 and gray_std > 0.30 and entropy > 0.45:
        scores["image"] += 0.85
    if ink > 0.45 and saturation < 0.08 and row_period > 0.12:
        scores["text"] += 0.35
        scores["image"] *= 0.55

    scores = {label: max(0.001, score) for label, score in scores.items()}
    total = sum(scores.values())
    label = max(scores, key=scores.get)
    confidence = scores[label] / max(total, 1e-6)
    if label == "text" and row_period > 0.22:
        confidence = max(confidence, min(0.92, 0.42 + row_period * 0.45 - max(hline, vline) * 0.08))
    if label == "schematic/circuit" and hline > 0.10 and vline > 0.08 and balance > 0.20:
        confidence = max(confidence, min(0.92, 0.44 + (hline + vline) * 0.42 + balance * 0.10))
    if label == "table" and min(hline, vline) > 0.15 and balance > 0.45:
        confidence = max(confidence, min(0.90, 0.42 + min(hline, vline) * 0.55 + balance * 0.10))
    if label == "image" and (saturation > 0.16 or (entropy > 0.45 and gray_std > 0.45)):
        confidence = max(confidence, min(0.92, 0.40 + saturation * 0.45 + entropy * 0.22 + gray_std * 0.15))
    if confidence < 0.32 and label != "other":
        return "other", confidence
    return label, confidence


def analyze_image(image, tile_size: int = 192, stride: int = 96, min_hint_confidence: float = 0.42) -> dict[str, object]:
    require_dependencies()
    height, width = image.shape[:2]
    tile_size = max(48, min(tile_size, max(width, height)))
    stride = max(24, min(stride, tile_size))
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mask, threshold, bright_foreground = foreground_mask(gray)

    tiles: list[dict[str, object]] = []
    for y in tile_positions(height, tile_size, stride):
        for x in tile_positions(width, tile_size, stride):
            features = tile_features(image, gray, mask, x, y, tile_size)
            label, confidence = classify_frequency_features(features)
            tiles.append(
                {
                    "bbox": [int(x), int(y), int(min(tile_size, width - x)), int(min(tile_size, height - y))],
                    "label": label,
                    "confidence": round(float(confidence), 5),
                    "features": {key: round(float(value), 5) for key, value in features.items()},
                }
            )

    hints = merge_tiles_to_hints(tiles, width, height, min_hint_confidence)
    return {
        "analysis_width": int(width),
        "analysis_height": int(height),
        "tile_size": int(tile_size),
        "stride": int(stride),
        "threshold": int(threshold),
        "bright_foreground": bool(bright_foreground),
        "tiles": tiles,
        "hints": hints,
        "summary": label_counts(hints),
    }


def label_counts(items: Iterable[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        label = str(item.get("label", "other"))
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))


def merge_tiles_to_hints(tiles: list[dict[str, object]], width: int, height: int, min_confidence: float) -> list[dict[str, object]]:
    hints: list[dict[str, object]] = []
    page_area = max(1, width * height)
    for label in sorted(HINT_LABELS):
        label_mask = np.zeros((height, width), dtype=np.uint8)
        confidence_map = np.zeros((height, width), dtype=np.float32)
        for tile in tiles:
            if tile["label"] != label or float(tile["confidence"]) < min_confidence:
                continue
            x, y, w, h = [int(value) for value in tile["bbox"]]
            label_mask[y : y + h, x : x + w] = 255
            confidence_map[y : y + h, x : x + w] = np.maximum(confidence_map[y : y + h, x : x + w], float(tile["confidence"]))

        if int((label_mask > 0).sum()) == 0:
            continue
        close = max(7, min(width, height) // 90)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (close, close))
        label_mask = cv2.morphologyEx(label_mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(label_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area_ratio = (w * h) / page_area
            min_area = 0.003 if label == "text" else 0.006
            if area_ratio < min_area or w < 35 or h < 35:
                continue
            roi_conf = confidence_map[y : y + h, x : x + w]
            active_conf = roi_conf[roi_conf > 0]
            confidence = float(active_conf.mean()) if active_conf.size else min_confidence
            hints.append(
                {
                    "label": label,
                    "confidence": round(confidence, 5),
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "area_ratio": round(float(area_ratio), 5),
                }
            )
    return sorted(hints, key=lambda item: (int(item["bbox"][1]), int(item["bbox"][0]), str(item["label"])))


def scale_bbox(bbox: list[int], scale: float) -> list[int]:
    if scale <= 0:
        return [int(value) for value in bbox]
    return [
        int(round(bbox[0] / scale)),
        int(round(bbox[1] / scale)),
        int(round(bbox[2] / scale)),
        int(round(bbox[3] / scale)),
    ]


def hints_in_original_coordinates(hints: list[dict[str, object]], scale: float) -> list[dict[str, object]]:
    original_hints = []
    for hint in hints:
        converted = dict(hint)
        converted["bbox"] = scale_bbox([int(value) for value in hint["bbox"]], scale)
        original_hints.append(converted)
    return original_hints


def overlap_area(first: list[int], second: list[int]) -> int:
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    left = max(ax, bx)
    top = max(ay, by)
    right = min(ax + aw, bx + bw)
    bottom = min(ay + ah, by + bh)
    return max(0, right - left) * max(0, bottom - top)


def normalize_label(label: str) -> str:
    if label in {"schematic", "schematic/circuit", "diagram", "table"}:
        return "line_art"
    if label == "image":
        return "image"
    if label == "text":
        return "text"
    return "other"


def validate_layout_blocks(blocks: list[dict[str, object]], hints: list[dict[str, object]]) -> list[dict[str, object]]:
    warnings: list[dict[str, object]] = []
    for block in blocks:
        block_bbox = [int(value) for value in block.get("bbox", [])]
        if len(block_bbox) != 4:
            continue
        block_area = max(1, block_bbox[2] * block_bbox[3])
        block_label = str(block.get("label", "other"))
        for hint in hints:
            hint_bbox = [int(value) for value in hint.get("bbox", [])]
            if len(hint_bbox) != 4:
                continue
            overlap = overlap_area(block_bbox, hint_bbox)
            if overlap <= 0:
                continue
            hint_area = max(1, hint_bbox[2] * hint_bbox[3])
            block_overlap = overlap / block_area
            hint_overlap = overlap / hint_area
            if block_overlap < 0.30 and hint_overlap < 0.45:
                continue
            hint_label = str(hint.get("label", "other"))
            if normalize_label(block_label) == normalize_label(hint_label):
                continue
            warnings.append(
                {
                    "block": block.get("ident", ""),
                    "block_label": block_label,
                    "hint_label": hint_label,
                    "hint_confidence": round(float(hint.get("confidence", 0.0)), 5),
                    "block_overlap": round(float(block_overlap), 5),
                    "hint_overlap": round(float(hint_overlap), 5),
                    "bbox": block_bbox,
                    "hint_bbox": hint_bbox,
                }
            )
    return warnings


def draw_frequency_preview(image, result: dict[str, object], preview_width: int, out_path: Path) -> Path:
    height, width = image.shape[:2]
    scale = min(1.0, preview_width / float(width))
    preview = image.copy() if scale >= 0.999 else cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
    overlay = preview.copy()

    analysis_scale = float(result.get("analysis_scale", 1.0))
    hints = result.get("hints", [])
    for hint in hints:
        bbox = [int(value) for value in hint["bbox"]]
        color = LABEL_COLORS.get(str(hint["label"]), LABEL_COLORS["other"])
        x, y, w, h = scale_bbox(bbox, analysis_scale)
        x1 = int(round(x * scale))
        y1 = int(round(y * scale))
        x2 = int(round((x + w) * scale))
        y2 = int(round((y + h) * scale))
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    preview = cv2.addWeighted(overlay, 0.18, preview, 0.82, 0)

    for index, hint in enumerate(hints, start=1):
        bbox = [int(value) for value in hint["bbox"]]
        color = LABEL_COLORS.get(str(hint["label"]), LABEL_COLORS["other"])
        x, y, w, h = scale_bbox(bbox, analysis_scale)
        x1 = int(round(x * scale))
        y1 = int(round(y * scale))
        x2 = int(round((x + w) * scale))
        y2 = int(round((y + h) * scale))
        cv2.rectangle(preview, (x1, y1), (x2, y2), color, max(2, int(round(2 * scale))))
        label = f"F{index:02d} {short_label(str(hint['label']))} {float(hint['confidence']):.2f}"
        (text_w, text_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 1)
        top = max(0, y1 - text_h - baseline - 5)
        cv2.rectangle(preview, (x1, top), (x1 + text_w + 6, top + text_h + baseline + 5), color, -1)
        cv2.putText(preview, label, (x1 + 3, top + text_h + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

    write_image(out_path, preview)
    return out_path


def short_label(label: str) -> str:
    return "schematic" if label == "schematic/circuit" else label


def write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
