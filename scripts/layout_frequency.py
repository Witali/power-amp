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
DEFAULT_TILE_SIZE = 32
DEFAULT_STRIDE = 32
TEXT_ROW_PERIOD_BAND = (8.0, 44.0)
TEXT_COLUMN_PERIOD_BAND = (4.0, 28.0)

# Calibrated on the locally reviewed archive.radio.ru page set under
# study/layout_detection_marked_pages. The measured p05..p95 text row period
# range was about 19..38 px at the 1800 px analysis scale; the band above keeps
# roughly 15-20% headroom and the rules below prevent line art from becoming
# text purely because circuit labels are also periodic.
BACKGROUND_MAX_INK = 0.010
BACKGROUND_MAX_GRAY_STD = 0.080
STRONG_TEXT_ROW_PERIOD = 0.68
STRONG_TEXT_ROW_ENTROPY_MAX = 0.66
TEXT_ROW_PERIOD = 0.38
TEXT_ROW_ENTROPY_MAX = 0.70
TEXT_MAX_LINE_BALANCE = 0.35
TEXT_MAX_LINE_DENSITY = 0.22
TEXT_MAX_SATURATION = 0.34
LINE_ART_MAX_INK = 0.26
LINE_ART_MIN_ENTROPY = 0.56
LINE_ART_MIN_LINE_DENSITY = 0.045
LINE_ART_MIN_BALANCE = 0.12
LINE_ART_MAX_SATURATION = 0.16
IMAGE_STRONG_SATURATION = 0.24
IMAGE_MEDIUM_SATURATION = 0.15
IMAGE_MIN_GRAY_STD = 0.52
IMAGE_MIN_ENTROPY = 0.34
LUMA_HIST_BINS = 16
SATURATION_HIST_BINS = 8
HUE_HIST_BINS = 12
TEXT_MIN_LUMA_BIMODAL = 0.38
TEXT_MAX_LUMA_MID_FRACTION = 0.42
IMAGE_MIN_LUMA_ENTROPY = 0.52
IMAGE_MIN_LUMA_MID_FRACTION = 0.32
SCHEMATIC_MAX_DARK_LIGHT_RATIO = 0.24
TEXT_MIN_DARK_LIGHT_RATIO = 0.03
TEXT_MAX_DARK_LIGHT_RATIO = 0.34
CLUSTER_FEATURE_KEYS = (
    "ink_density",
    "gray_std",
    "saturation_p80",
    "saturation_high_fraction",
    "color_pixel_fraction",
    "luma_dark_light_ratio",
    "luma_mid_fraction",
    "luma_hist_entropy",
    "row_period_score",
    "column_period_score",
    "row_entropy",
    "column_entropy",
    "hline_density",
    "vline_density",
    "line_balance",
)
CLUSTER_FEATURE_WEIGHTS = {
    "ink_density": 1.10,
    "gray_std": 0.80,
    "saturation_p80": 0.80,
    "saturation_high_fraction": 0.70,
    "color_pixel_fraction": 0.70,
    "luma_dark_light_ratio": 1.15,
    "luma_mid_fraction": 0.95,
    "luma_hist_entropy": 0.85,
    "row_period_score": 1.10,
    "column_period_score": 0.70,
    "row_entropy": 0.90,
    "column_entropy": 0.75,
    "hline_density": 1.10,
    "vline_density": 1.10,
    "line_balance": 0.90,
}
CLUSTER_DISTANCE_THRESHOLDS = {
    "text": 0.46,
    "line_art": 0.58,
    "image": 0.66,
    "other": 0.42,
}


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


def put_fitted_text(image, text: str, origin: tuple[int, int], max_width: int, font_scale: float, color, thickness: int) -> None:
    if not text or max_width <= 0:
        return
    scale = font_scale
    while scale > 0.36 and cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)[0][0] > max_width:
        scale -= 0.04
    while text and cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)[0][0] > max_width:
        text = text[:-4].rstrip() + "..."
    if text:
        cv2.putText(image, text, origin, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def add_title_header(image, title: str, subtitle: str = ""):
    require_dependencies()
    if len(image.shape) == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    header_height = 104
    height, width = image.shape[:2]
    result = np.full((height + header_height, width, 3), 255, dtype=np.uint8)
    result[header_height:, :] = image
    text_width = max(20, width - 48)
    put_fitted_text(result, title, (24, 38), text_width, 1.0, (20, 20, 20), 2)
    if subtitle:
        put_fitted_text(result, subtitle, (24, 76), text_width, 0.58, (70, 70, 70), 1)
    cv2.line(result, (0, header_height - 1), (width, header_height - 1), (215, 215, 215), 1)
    return result


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


def normalized_histogram(values, bins: int, value_range: tuple[float, float]) -> list[float]:
    if values.size == 0:
        return [0.0] * bins
    hist, _ = np.histogram(values.astype(np.float32), bins=bins, range=value_range)
    total = float(hist.sum())
    if total <= 0:
        return [0.0] * bins
    return [float(value) / total for value in hist]


def histogram_entropy(histogram: list[float]) -> float:
    values = np.array(histogram, dtype=np.float32)
    total = float(values.sum())
    if total <= 1e-9:
        return 0.0
    probability = values / total
    entropy = -float((probability * np.log2(probability + 1e-12)).sum())
    return entropy / math.log2(max(2, probability.size))


def prefixed_histogram(prefix: str, histogram: list[float]) -> dict[str, float]:
    return {f"{prefix}_hist_{index:02d}": float(value) for index, value in enumerate(histogram)}


def dominant_period(profile, min_period: float = 3.0, max_period: float = 80.0) -> float:
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
    power[0] = 0.0
    total = float(power.sum())
    if total <= 1e-9:
        return 0.0
    indices = np.arange(power.size, dtype=np.float32)
    periods = np.full(power.size, np.inf, dtype=np.float32)
    periods[1:] = signal.size / indices[1:]
    band = (periods >= min_period) & (periods <= max_period)
    if not bool(band.any()) or float(power[band].sum()) <= 1e-9:
        return 0.0
    band_indices = np.where(band)[0]
    best_index = band_indices[int(power[band].argmax())]
    return float(periods[best_index])


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
    if min(width, height) <= 64:
        h_length = max(18, int(round(width * 0.70)))
        v_length = max(18, int(round(height * 0.70)))
    else:
        h_length = max(10, width // 3)
        v_length = max(10, height // 3)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_length, 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_length))
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
    hue = hsv[:, :, 0].astype(np.float32) / 180.0
    saturation = hsv[:, :, 1].astype(np.float32) / 255.0
    luma = roi_gray.astype(np.float32) / 255.0
    luma_hist = normalized_histogram(luma, LUMA_HIST_BINS, (0.0, 1.0))
    saturation_hist = normalized_histogram(saturation, SATURATION_HIST_BINS, (0.0, 1.0))
    color_mask = saturation > 0.10
    hue_hist = normalized_histogram(hue[color_mask], HUE_HIST_BINS, (0.0, 1.0))
    luma_dark_fraction = float((luma <= 0.25).mean())
    luma_light_fraction = float((luma >= 0.78).mean())
    luma_mid_fraction = max(0.0, 1.0 - luma_dark_fraction - luma_light_fraction)
    luma_dark_light_ratio = luma_dark_fraction / max(luma_light_fraction, 1e-6)
    luma_light_dark_ratio = luma_light_fraction / max(luma_dark_fraction, 1e-6)
    luma_bimodal_score = min(luma_dark_fraction, luma_light_fraction) * (1.0 - luma_mid_fraction)
    saturation_high_fraction = float((saturation >= 0.25).mean())

    row_text_period = max(
        band_energy_ratio(row_profile, *TEXT_ROW_PERIOD_BAND),
        band_energy_ratio(gray_row_profile, *TEXT_ROW_PERIOD_BAND),
    )
    column_text_period = max(
        band_energy_ratio(column_profile, *TEXT_COLUMN_PERIOD_BAND),
        band_energy_ratio(gray_column_profile, *TEXT_COLUMN_PERIOD_BAND),
    )

    features = {
        "ink_density": float(ink.mean()),
        "gray_std": min(float(roi_gray.std()) / 90.0, 1.0),
        "saturation_mean": float(saturation.mean()),
        "saturation_p80": float(np.percentile(saturation, 80)),
        "saturation_high_fraction": saturation_high_fraction,
        "color_pixel_fraction": float(color_mask.mean()),
        "luma_dark_fraction": luma_dark_fraction,
        "luma_light_fraction": luma_light_fraction,
        "luma_mid_fraction": luma_mid_fraction,
        "luma_dark_light_ratio": min(luma_dark_light_ratio, 10.0),
        "luma_light_dark_ratio": min(luma_light_dark_ratio, 100.0),
        "luma_bimodal_score": luma_bimodal_score,
        "luma_hist_entropy": histogram_entropy(luma_hist),
        "saturation_hist_entropy": histogram_entropy(saturation_hist),
        "hue_hist_entropy": histogram_entropy(hue_hist),
        "row_period_score": row_text_period,
        "column_period_score": column_text_period,
        "row_entropy": spectral_entropy(gray_row_profile),
        "column_entropy": spectral_entropy(gray_column_profile),
        "hline_density": min(h_density * 8.0, 1.0),
        "vline_density": min(v_density * 8.0, 1.0),
        "line_balance": line_balance,
        "row_dominant_period": dominant_period(row_profile),
        "column_dominant_period": dominant_period(column_profile),
        "gray_row_dominant_period": dominant_period(gray_row_profile),
        "gray_column_dominant_period": dominant_period(gray_column_profile),
    }
    features.update(prefixed_histogram("luma", luma_hist))
    features.update(prefixed_histogram("saturation", saturation_hist))
    features.update(prefixed_histogram("hue", hue_hist))
    return features


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
    luma_bimodal = features.get("luma_bimodal_score", 0.0)
    luma_mid = features.get("luma_mid_fraction", 0.0)
    dark_light_ratio = features.get("luma_dark_light_ratio", 0.0)
    luma_entropy = features.get("luma_hist_entropy", 0.0)
    saturation_entropy = features.get("saturation_hist_entropy", 0.0)
    hue_entropy = features.get("hue_hist_entropy", 0.0)
    color_fraction = features.get("color_pixel_fraction", 0.0)
    saturation_high_fraction = features.get("saturation_high_fraction", 0.0)
    schematic_light_balance = max(0.0, (SCHEMATIC_MAX_DARK_LIGHT_RATIO - dark_light_ratio) / SCHEMATIC_MAX_DARK_LIGHT_RATIO)

    row_entropy = features["row_entropy"]
    column_entropy = features["column_entropy"]
    min_line = min(hline, vline)
    max_line = max(hline, vline)

    if ink < BACKGROUND_MAX_INK and gray_std < BACKGROUND_MAX_GRAY_STD:
        return "background", min(0.98, 0.72 + (BACKGROUND_MAX_INK - ink) * 12.0)

    strong_text = (
        (row_period > STRONG_TEXT_ROW_PERIOD or luma_bimodal > TEXT_MIN_LUMA_BIMODAL)
        and row_entropy < STRONG_TEXT_ROW_ENTROPY_MAX
        and luma_mid < TEXT_MAX_LUMA_MID_FRACTION
        and TEXT_MIN_DARK_LIGHT_RATIO <= dark_light_ratio <= TEXT_MAX_DARK_LIGHT_RATIO
        and (balance < TEXT_MAX_LINE_BALANCE or max_line < TEXT_MAX_LINE_DENSITY or min_line < LINE_ART_MIN_LINE_DENSITY)
    )
    display_text = (
        row_period > 0.78
        and ink > 0.08
        and saturation < TEXT_MAX_SATURATION
        and luma_mid < 0.50
        and dark_light_ratio <= 0.42
        and max_line < 0.42
        and balance < 0.55
    )
    compact_text = (
        row_period > 0.50
        and row_entropy < 0.58
        and max_line < 0.20
        and (luma_bimodal > 0.18 or luma_mid < 0.50)
        and dark_light_ratio >= TEXT_MIN_DARK_LIGHT_RATIO
    )
    if strong_text or display_text or compact_text:
        confidence = 0.44 + row_period * 0.36 + max(0.0, TEXT_ROW_ENTROPY_MAX - row_entropy) * 0.20
        confidence += min(0.10, luma_bimodal * 0.18)
        confidence -= min(0.16, balance * 0.10 + max_line * 0.06)
        return "text", min(0.92, max(0.42, confidence))

    strong_image = (
        (saturation > IMAGE_STRONG_SATURATION or saturation_high_fraction > 0.18)
        and gray_std > IMAGE_MIN_GRAY_STD
        and (entropy > IMAGE_MIN_ENTROPY or luma_entropy > IMAGE_MIN_LUMA_ENTROPY)
    )
    medium_image = (
        (saturation > IMAGE_MEDIUM_SATURATION or luma_mid > IMAGE_MIN_LUMA_MID_FRACTION)
        and gray_std > 0.64
        and ink > 0.16
        and max_line < 0.65
        and not (min_line > LINE_ART_MIN_LINE_DENSITY and balance > 0.20 and entropy > LINE_ART_MIN_ENTROPY)
    )
    if strong_image and not (row_period > 0.65 and row_entropy < TEXT_ROW_ENTROPY_MAX):
        return "image", min(
            0.92,
            0.36 + saturation * 0.38 + luma_entropy * 0.20 + entropy * 0.18 + gray_std * 0.12 + hue_entropy * 0.06,
        )
    if medium_image:
        return "image", min(
            0.88,
            0.34 + saturation * 0.30 + gray_std * 0.18 + entropy * 0.12 + luma_mid * 0.12 + saturation_entropy * 0.08,
        )

    line_art = (
        ink < LINE_ART_MAX_INK
        and entropy > LINE_ART_MIN_ENTROPY
        and luma_mid < 0.58
        and dark_light_ratio <= SCHEMATIC_MAX_DARK_LIGHT_RATIO
        and (
            (min_line > LINE_ART_MIN_LINE_DENSITY and balance > LINE_ART_MIN_BALANCE)
            or (hline > 0.14 and vline > 0.035)
            or (vline > 0.14 and hline > 0.035)
        )
    )
    loose_line_art = (
        ink < 0.22
        and entropy > 0.62
        and max(row_period, column_period) > 0.42
        and min_line > 0.025
        and saturation < LINE_ART_MAX_SATURATION
        and luma_mid < 0.58
        and dark_light_ratio <= 0.30
    )
    if line_art or loose_line_art:
        label = "table" if min_line > 0.20 and balance > 0.50 and min(row_period, column_period) > 0.12 else "schematic/circuit"
        confidence = 0.40 + (hline + vline) * 0.44 + balance * 0.12 + entropy * 0.12
        confidence -= min(0.14, saturation * 0.20)
        return label, min(0.92, max(0.42, confidence))

    if row_period > TEXT_ROW_PERIOD and row_entropy < TEXT_ROW_ENTROPY_MAX and (
        balance < 0.24 or max_line < 0.16 or min_line < 0.035
    ):
        return "text", min(
            0.88,
            0.40 + row_period * 0.36 + max(0.0, TEXT_ROW_ENTROPY_MAX - row_entropy) * 0.12 + luma_bimodal * 0.08,
        )
    if row_period > 0.55 and ink > 0.09 and saturation < 0.22 and row_entropy < 0.76 and max_line < 0.28:
        return "text", min(0.86, 0.39 + row_period * 0.32 + ink * 0.14 + luma_bimodal * 0.08)

    scores = {
        "text": 2.4 * row_period + 0.30 * column_period + 0.50 * ink + 0.45 * luma_bimodal - 1.0 * balance - 0.70 * entropy - 0.35 * saturation - 0.25 * luma_mid,
        "schematic/circuit": 1.6 * hline + 1.6 * vline + 1.15 * balance + 1.0 * entropy + 0.35 * max(row_period, column_period) + 0.20 * schematic_light_balance - 0.60 * saturation - 0.35 * ink - 0.20 * luma_mid,
        "table": 1.25 * min_line + 1.0 * balance + 0.25 * min(row_period, column_period),
        "image": 1.05 * gray_std + 1.10 * saturation + 0.45 * entropy + 0.50 * luma_entropy + 0.30 * luma_mid + 0.22 * color_fraction - 0.50 * row_period - 0.20 * balance,
        "other": 0.20 + 0.25 * ink + 0.15 * entropy,
    }

    if ink > 0.45 and saturation < 0.08 and row_period > 0.12:
        scores["text"] += 0.35
        scores["image"] *= 0.55

    scores = {label: max(0.001, score) for label, score in scores.items()}
    total = sum(scores.values())
    label = max(scores, key=scores.get)
    confidence = scores[label] / max(total, 1e-6)
    if label == "text" and row_period > TEXT_ROW_PERIOD:
        confidence = max(confidence, min(0.90, 0.40 + row_period * 0.40 - max_line * 0.08))
    if label == "schematic/circuit" and hline > 0.08 and vline > 0.06 and balance > 0.16:
        confidence = max(confidence, min(0.92, 0.44 + (hline + vline) * 0.42 + balance * 0.10))
    if label == "table" and min_line > 0.15 and balance > 0.45:
        confidence = max(confidence, min(0.90, 0.42 + min_line * 0.55 + balance * 0.10))
    if label == "image" and (saturation > IMAGE_MEDIUM_SATURATION or (entropy > 0.45 and gray_std > 0.45)):
        confidence = max(confidence, min(0.92, 0.40 + saturation * 0.45 + entropy * 0.22 + gray_std * 0.15))
    if confidence < 0.32 and label != "other":
        return "other", confidence
    return label, confidence


def cluster_family(label: str) -> str:
    if label in {"schematic/circuit", "diagram", "table"}:
        return "line_art"
    if label in {"text", "image"}:
        return label
    return "other"


def cluster_feature_value(key: str, value: float) -> float:
    if key == "luma_dark_light_ratio":
        return min(1.0, max(0.0, value / 0.50))
    return min(1.0, max(0.0, value))


def cluster_feature_vector(features: dict[str, float]) -> list[float]:
    return [cluster_feature_value(key, float(features.get(key, 0.0))) for key in CLUSTER_FEATURE_KEYS]


def weighted_feature_distance(first: list[float], second: list[float]) -> float:
    if len(first) != len(second) or not first:
        return 1.0
    weighted_sum = 0.0
    weight_total = 0.0
    for index, key in enumerate(CLUSTER_FEATURE_KEYS):
        weight = CLUSTER_FEATURE_WEIGHTS.get(key, 1.0)
        delta = first[index] - second[index]
        weighted_sum += weight * delta * delta
        weight_total += weight
    return math.sqrt(weighted_sum / max(weight_total, 1e-6))


def cluster_distance_threshold(family: str) -> float:
    return CLUSTER_DISTANCE_THRESHOLDS.get(family, CLUSTER_DISTANCE_THRESHOLDS["other"])


def mean_feature_vector(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return [0.0] * len(CLUSTER_FEATURE_KEYS)
    return [sum(vector[index] for vector in vectors) / len(vectors) for index in range(len(CLUSTER_FEATURE_KEYS))]


def dominant_cluster_label(tiles: list[dict[str, object]]) -> str:
    scores: dict[str, float] = {}
    for tile in tiles:
        label = str(tile.get("label", "other"))
        scores[label] = scores.get(label, 0.0) + float(tile.get("confidence", 0.0))
    return max(scores, key=scores.get) if scores else "other"


def cluster_min_tile_count(family: str) -> int:
    if family == "line_art":
        return 4
    return 3 if family in {"text", "image"} else 2


def cluster_min_area_ratio(family: str) -> float:
    if family == "text":
        return 0.0018
    if family == "line_art":
        return 0.0045
    if family == "image":
        return 0.0030
    return 0.0040


def cluster_max_area_ratio(family: str) -> float:
    if family == "text":
        return 0.42
    if family == "line_art":
        return 0.55
    if family == "image":
        return 0.35
    return 0.25


def compatible_cluster_tile(
    candidate: dict[str, object],
    current: dict[str, object],
    centroid: list[float],
    family: str,
) -> bool:
    if cluster_family(str(candidate.get("label", "other"))) != family:
        return False
    threshold = cluster_distance_threshold(family)
    candidate_vector = candidate.get("cluster_vector", [])
    current_vector = current.get("cluster_vector", [])
    if not isinstance(candidate_vector, list) or not isinstance(current_vector, list):
        return False
    if weighted_feature_distance(candidate_vector, current_vector) > threshold:
        return False
    return weighted_feature_distance(candidate_vector, centroid) <= threshold * 1.25


def cluster_tiles_to_hints(
    tiles: list[dict[str, object]],
    width: int,
    height: int,
    min_confidence: float = 0.34,
) -> list[dict[str, object]]:
    page_area = max(1, width * height)
    grid_tiles: dict[tuple[int, int], dict[str, object]] = {}
    for tile in tiles:
        label = str(tile.get("label", "other"))
        if label == "background" or float(tile.get("confidence", 0.0)) < min_confidence:
            continue
        grid = tile.get("grid")
        features = tile.get("features")
        if not isinstance(grid, list) or len(grid) != 2 or not isinstance(features, dict):
            continue
        tile["cluster_vector"] = cluster_feature_vector({str(key): float(value) for key, value in features.items()})
        grid_tiles[(int(grid[0]), int(grid[1]))] = tile

    visited: set[tuple[int, int]] = set()
    clusters: list[dict[str, object]] = []
    for start_grid, start_tile in sorted(grid_tiles.items()):
        if start_grid in visited:
            continue
        family = cluster_family(str(start_tile.get("label", "other")))
        queue = [start_grid]
        visited.add(start_grid)
        cluster_grids: list[tuple[int, int]] = []
        cluster_vectors: list[list[float]] = []
        centroid = list(start_tile.get("cluster_vector", []))

        while queue:
            grid = queue.pop(0)
            tile = grid_tiles[grid]
            cluster_grids.append(grid)
            vector = tile.get("cluster_vector", [])
            if isinstance(vector, list):
                cluster_vectors.append(vector)
                centroid = mean_feature_vector(cluster_vectors)

            row, column = grid
            for row_offset in (-1, 0, 1):
                for column_offset in (-1, 0, 1):
                    if row_offset == 0 and column_offset == 0:
                        continue
                    neighbor_grid = (row + row_offset, column + column_offset)
                    if neighbor_grid in visited or neighbor_grid not in grid_tiles:
                        continue
                    neighbor = grid_tiles[neighbor_grid]
                    if not compatible_cluster_tile(neighbor, tile, centroid, family):
                        continue
                    visited.add(neighbor_grid)
                    queue.append(neighbor_grid)

        cluster_tiles = [grid_tiles[grid] for grid in cluster_grids]
        if len(cluster_tiles) < cluster_min_tile_count(family):
            continue
        left = min(int(tile["bbox"][0]) for tile in cluster_tiles)
        top = min(int(tile["bbox"][1]) for tile in cluster_tiles)
        right = max(int(tile["bbox"][0]) + int(tile["bbox"][2]) for tile in cluster_tiles)
        bottom = max(int(tile["bbox"][1]) + int(tile["bbox"][3]) for tile in cluster_tiles)
        bbox = [left, top, right - left, bottom - top]
        area_ratio = (bbox[2] * bbox[3]) / page_area
        if area_ratio < cluster_min_area_ratio(family) or area_ratio > cluster_max_area_ratio(family):
            continue
        if bbox[2] < 32 or bbox[3] < 32:
            continue
        if family == "text" and bbox[2] > width * 0.86 and bbox[3] > height * 0.60:
            continue
        if family == "line_art" and bbox[2] < width * 0.12 and bbox[3] > height * 0.35:
            continue
        centroid = mean_feature_vector([list(tile.get("cluster_vector", [])) for tile in cluster_tiles])
        distances = [
            weighted_feature_distance(list(tile.get("cluster_vector", [])), centroid)
            for tile in cluster_tiles
            if isinstance(tile.get("cluster_vector", []), list)
        ]
        confidence = sum(float(tile.get("confidence", 0.0)) for tile in cluster_tiles) / len(cluster_tiles)
        if confidence < 0.50 and len(cluster_tiles) < 8:
            continue
        clusters.append(
            {
                "label": dominant_cluster_label(cluster_tiles),
                "family": family,
                "confidence": round(confidence, 5),
                "bbox": [int(value) for value in bbox],
                "area_ratio": round(float(area_ratio), 5),
                "tile_count": len(cluster_tiles),
                "mean_feature_distance": round(float(sum(distances) / len(distances)) if distances else 0.0, 5),
            }
        )
    for tile in grid_tiles.values():
        tile.pop("cluster_vector", None)
    return sorted(clusters, key=lambda item: (int(item["bbox"][1]), int(item["bbox"][0]), str(item["label"])))


def analyze_image(
    image,
    tile_size: int = DEFAULT_TILE_SIZE,
    stride: int = DEFAULT_STRIDE,
    min_hint_confidence: float = 0.42,
) -> dict[str, object]:
    require_dependencies()
    height, width = image.shape[:2]
    tile_size = max(16, min(tile_size, max(width, height)))
    stride = max(8, min(stride, tile_size))
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mask, threshold, bright_foreground = foreground_mask(gray)

    tiles: list[dict[str, object]] = []
    y_positions = tile_positions(height, tile_size, stride)
    x_positions = tile_positions(width, tile_size, stride)
    for row, y in enumerate(y_positions):
        for column, x in enumerate(x_positions):
            features = tile_features(image, gray, mask, x, y, tile_size)
            label, confidence = classify_frequency_features(features)
            tiles.append(
                {
                    "grid": [int(row), int(column)],
                    "bbox": [int(x), int(y), int(min(tile_size, width - x)), int(min(tile_size, height - y))],
                    "label": label,
                    "confidence": round(float(confidence), 5),
                    "features": {key: round(float(value), 5) for key, value in features.items()},
                }
            )

    hints = merge_tiles_to_hints(tiles, width, height, min_hint_confidence)
    cluster_hints = cluster_tiles_to_hints(tiles, width, height)
    for tile in tiles:
        tile.pop("cluster_vector", None)
    return {
        "analysis_width": int(width),
        "analysis_height": int(height),
        "tile_size": int(tile_size),
        "stride": int(stride),
        "threshold": int(threshold),
        "bright_foreground": bool(bright_foreground),
        "tiles": tiles,
        "hints": hints,
        "cluster_hints": cluster_hints,
        "summary": label_counts(hints),
        "cluster_summary": label_counts(cluster_hints),
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
        if label in {"schematic/circuit", "table"}:
            close = max(15, min(width, height) // 45)
        elif label == "text":
            close = max(9, min(width, height) // 80)
        else:
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


def draw_frequency_preview(
    image,
    result: dict[str, object],
    preview_width: int,
    out_path: Path,
    title: str | None = None,
    subtitle: str | None = None,
    add_header: bool = True,
) -> Path:
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

    cluster_hints = result.get("cluster_hints", [])
    if isinstance(cluster_hints, list):
        for index, hint in enumerate(cluster_hints, start=1):
            if not isinstance(hint, dict):
                continue
            bbox = [int(value) for value in hint["bbox"]]
            color = LABEL_COLORS.get(str(hint["label"]), LABEL_COLORS["other"])
            x, y, w, h = scale_bbox(bbox, analysis_scale)
            x1 = int(round(x * scale))
            y1 = int(round(y * scale))
            x2 = int(round((x + w) * scale))
            y2 = int(round((y + h) * scale))
            thickness = max(2, int(round(3 * scale)))
            cv2.rectangle(preview, (x1, y1), (x2, y2), (255, 255, 255), thickness + 2)
            cv2.rectangle(preview, (x1, y1), (x2, y2), color, thickness)
            label = f"C{index:02d} {short_label(str(hint['label']))} {float(hint['confidence']):.2f}"
            (text_w, text_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 1)
            top = min(max(0, y2 + 3), max(0, preview.shape[0] - text_h - baseline - 5))
            cv2.rectangle(preview, (x1, top), (x1 + text_w + 6, top + text_h + baseline + 5), (255, 255, 255), -1)
            cv2.rectangle(preview, (x1, top), (x1 + text_w + 6, top + text_h + baseline + 5), color, 1)
            cv2.putText(preview, label, (x1 + 3, top + text_h + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 1, cv2.LINE_AA)

    if add_header:
        hint_counts = ", ".join(f"{key}={value}" for key, value in label_counts(result.get("hints", [])).items()) or "none"
        cluster_counts = ", ".join(f"{key}={value}" for key, value in label_counts(result.get("cluster_hints", [])).items()) or "none"
        preview_title = title or "Frequency analysis layout hints"
        preview_subtitle = subtitle if subtitle is not None else f"{result.get('page', out_path.parent.name)} | hints: {hint_counts} | clusters: {cluster_counts}"
        preview = add_title_header(preview, preview_title, preview_subtitle)

    write_image(out_path, preview)
    return out_path


def short_label(label: str) -> str:
    return "schematic" if label == "schematic/circuit" else label


def write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
