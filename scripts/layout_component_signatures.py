#!/usr/bin/env python3
"""Detect schematic component signatures in binarized page blocks."""

from __future__ import annotations

import sys
from pathlib import Path


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

try:
    from scripts import layout_config  # type: ignore
except ImportError:
    import layout_config  # type: ignore


MIN_COMPONENT_PIXELS = layout_config.MIN_COMPONENT_PIXELS
MIN_SYMBOL_SIDE = layout_config.MIN_SYMBOL_SIDE
MAX_SYMBOL_AREA_RATIO = layout_config.MAX_SYMBOL_AREA_RATIO
RECT_MIN_ASPECT = layout_config.RECT_MIN_ASPECT
RECT_MAX_ASPECT = layout_config.RECT_MAX_ASPECT
RECT_MIN_FILL_RATIO = layout_config.RECT_MIN_FILL_RATIO
RECT_MAX_FILL_RATIO = layout_config.RECT_MAX_FILL_RATIO
TRIANGLE_MIN_FILL_RATIO = layout_config.TRIANGLE_MIN_FILL_RATIO
TRIANGLE_MAX_FILL_RATIO = layout_config.TRIANGLE_MAX_FILL_RATIO
CIRCLE_MIN_CIRCULARITY = layout_config.CIRCLE_MIN_CIRCULARITY
CIRCLE_MAX_ASPECT_SKEW = layout_config.CIRCLE_MAX_ASPECT_SKEW
CAPACITOR_MIN_LENGTH = layout_config.CAPACITOR_MIN_LENGTH
CAPACITOR_MAX_GAP_RATIO = layout_config.CAPACITOR_MAX_GAP_RATIO
CAPACITOR_MAX_PAIR_COUNT = layout_config.CAPACITOR_MAX_PAIR_COUNT
SIGNATURE_AREA_NORMALIZER = layout_config.SIGNATURE_AREA_NORMALIZER
PCB_TRACE_DISTANCE_MIN = layout_config.PCB_TRACE_DISTANCE_MIN
PCB_PAD_MIN_SIDE = layout_config.PCB_PAD_MIN_SIDE
PCB_PAD_MAX_SIDE_RATIO = layout_config.PCB_PAD_MAX_SIDE_RATIO
PCB_PAD_MIN_CIRCULARITY = layout_config.PCB_PAD_MIN_CIRCULARITY
PCB_BOARD_EDGE_BAND_RATIO = layout_config.PCB_BOARD_EDGE_BAND_RATIO


def require_dependencies() -> None:
    if OPENCV_AVAILABLE:
        return
    raise RuntimeError("OpenCV component signature detection dependencies are missing.")


def line_segments_from_mask(line_mask, orientation: str) -> list[tuple[int, int, int, int]]:
    require_dependencies()
    contours, _ = cv2.findContours((line_mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    height, width = line_mask.shape[:2]
    min_length = max(CAPACITOR_MIN_LENGTH, min(width, height) // 80)
    max_thickness = max(4, min(width, height) // 45)
    segments: list[tuple[int, int, int, int]] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if orientation == "vertical":
            if h >= min_length and w <= max_thickness and h / max(1, w) >= 2.2:
                segments.append((x, y, w, h))
        else:
            if w >= min_length and h <= max_thickness and w / max(1, h) >= 2.2:
                segments.append((x, y, w, h))
    return segments


def overlap_length(first_start: int, first_end: int, second_start: int, second_end: int) -> int:
    return max(0, min(first_end, second_end) - max(first_start, second_start))


def count_parallel_plate_pairs(segments: list[tuple[int, int, int, int]], orientation: str, width: int, height: int) -> int:
    count = 0
    max_gap = max(5, int(round(min(width, height) * CAPACITOR_MAX_GAP_RATIO)))
    used: set[tuple[int, int]] = set()
    for first_index, first in enumerate(segments):
        fx, fy, fw, fh = first
        for second_index in range(first_index + 1, len(segments)):
            if (first_index, second_index) in used:
                continue
            sx, sy, sw, sh = segments[second_index]
            if orientation == "vertical":
                gap = max(0, max(fx, sx) - min(fx + fw, sx + sw))
                length_overlap = overlap_length(fy, fy + fh, sy, sy + sh)
                similar_length = min(fh, sh) / max(fh, sh, 1) >= 0.55
                close_centers = abs((fy + fh / 2.0) - (sy + sh / 2.0)) <= max(fh, sh) * 0.35
            else:
                gap = max(0, max(fy, sy) - min(fy + fh, sy + sh))
                length_overlap = overlap_length(fx, fx + fw, sx, sx + sw)
                similar_length = min(fw, sw) / max(fw, sw, 1) >= 0.55
                close_centers = abs((fx + fw / 2.0) - (sx + sw / 2.0)) <= max(fw, sw) * 0.35
            if 1 <= gap <= max_gap and length_overlap >= CAPACITOR_MIN_LENGTH and similar_length and close_centers:
                count += 1
                used.add((first_index, second_index))
                break
        if count >= CAPACITOR_MAX_PAIR_COUNT:
            break
    return count


def contour_symbol_counts(mask) -> dict[str, int]:
    require_dependencies()
    contours, _ = cv2.findContours((mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    height, width = mask.shape[:2]
    area = max(1, width * height)
    counts = {"resistor_like": 0, "diode_triangle_like": 0, "transistor_circle_like": 0}
    for contour in contours:
        contour_area = float(cv2.contourArea(contour))
        if contour_area < MIN_COMPONENT_PIXELS:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        rect_area = max(1, w * h)
        if min(w, h) < MIN_SYMBOL_SIDE or rect_area > area * MAX_SYMBOL_AREA_RATIO:
            continue
        aspect = max(w, h) / max(1, min(w, h))
        fill = contour_area / rect_area
        perimeter = float(cv2.arcLength(contour, True))
        approx = cv2.approxPolyDP(contour, max(1.5, perimeter * 0.035), True)
        vertex_count = len(approx)

        if RECT_MIN_ASPECT <= aspect <= RECT_MAX_ASPECT and RECT_MIN_FILL_RATIO <= fill <= RECT_MAX_FILL_RATIO and vertex_count >= 4:
            counts["resistor_like"] += 1

        if 3 <= vertex_count <= 4 and TRIANGLE_MIN_FILL_RATIO <= fill <= TRIANGLE_MAX_FILL_RATIO and aspect <= 2.6:
            counts["diode_triangle_like"] += 1

        if perimeter > 0.0 and aspect <= 1.0 + CIRCLE_MAX_ASPECT_SKEW:
            circularity = 4.0 * np.pi * contour_area / max(perimeter * perimeter, 1e-6)
            if circularity >= CIRCLE_MIN_CIRCULARITY and TRIANGLE_MIN_FILL_RATIO <= fill <= 0.72:
                counts["transistor_circle_like"] += 1
    return counts


def pcb_signature_features(mask) -> dict[str, float]:
    require_dependencies()
    binary = (mask > 0).astype(np.uint8)
    height, width = binary.shape[:2]
    area = max(1, width * height)

    distance = cv2.distanceTransform(binary, cv2.DIST_L2, 3)
    thick_trace = distance >= PCB_TRACE_DISTANCE_MIN
    thick_trace_density = min(float(thick_trace.sum()) / area * 22.0, 1.0)

    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    pad_count = 0
    max_pad_side = max(PCB_PAD_MIN_SIDE + 2, int(round(min(width, height) * PCB_PAD_MAX_SIDE_RATIO)))
    for contour in contours:
        contour_area = float(cv2.contourArea(contour))
        if contour_area < 4.0:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if min(w, h) < PCB_PAD_MIN_SIDE or max(w, h) > max_pad_side:
            continue
        aspect = max(w, h) / max(1, min(w, h))
        if aspect > 1.8:
            continue
        perimeter = float(cv2.arcLength(contour, True))
        if perimeter <= 0.0:
            continue
        circularity = 4.0 * np.pi * contour_area / max(perimeter * perimeter, 1e-6)
        if circularity >= PCB_PAD_MIN_CIRCULARITY:
            pad_count += 1

    normalizer = max(1.0, area / SIGNATURE_AREA_NORMALIZER)
    pad_density = min(pad_count / normalizer / 5.0, 1.0)

    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(12, width // 12), 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(12, height // 12)))
    h_lines = cv2.morphologyEx(mask, cv2.MORPH_OPEN, h_kernel)
    v_lines = cv2.morphologyEx(mask, cv2.MORPH_OPEN, v_kernel)
    band_x = max(3, int(round(width * PCB_BOARD_EDGE_BAND_RATIO)))
    band_y = max(3, int(round(height * PCB_BOARD_EDGE_BAND_RATIO)))
    top_bottom = float((h_lines[:band_y, :] > 0).sum() + (h_lines[max(0, height - band_y) :, :] > 0).sum())
    left_right = float((v_lines[:, :band_x] > 0).sum() + (v_lines[:, max(0, width - band_x) :] > 0).sum())
    board_outline_score = min((top_bottom / max(1.0, width * 2.0) + left_right / max(1.0, height * 2.0)) * 2.0, 1.0)

    score = min(0.72 * thick_trace_density + 0.26 * pad_density + 0.18 * board_outline_score, 1.0)
    return {
        "pcb_trace_density": float(thick_trace_density),
        "pcb_pad_density": float(pad_density),
        "pcb_board_outline_score": float(board_outline_score),
        "pcb_signature_score": float(score),
    }


def component_signature_features(mask, edges) -> dict[str, float]:
    require_dependencies()
    height, width = mask.shape[:2]
    area = max(1, width * height)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(5, width // 80), 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(5, height // 80)))
    h_lines = cv2.morphologyEx(mask, cv2.MORPH_OPEN, h_kernel)
    v_lines = cv2.morphologyEx(mask, cv2.MORPH_OPEN, v_kernel)

    h_segments = line_segments_from_mask(h_lines, "horizontal")
    v_segments = line_segments_from_mask(v_lines, "vertical")
    capacitor_pairs = count_parallel_plate_pairs(v_segments, "vertical", width, height)
    capacitor_pairs += count_parallel_plate_pairs(h_segments, "horizontal", width, height)
    symbol_counts = contour_symbol_counts(mask)

    normalizer = max(1.0, area / SIGNATURE_AREA_NORMALIZER)
    resistor_density = min(symbol_counts["resistor_like"] / normalizer, 1.0)
    capacitor_density = min(capacitor_pairs / normalizer, 1.0)
    diode_density = min(symbol_counts["diode_triangle_like"] / normalizer, 1.0)
    transistor_density = min(symbol_counts["transistor_circle_like"] / normalizer, 1.0)
    score = min(
        0.34 * resistor_density
        + 0.30 * capacitor_density
        + 0.22 * diode_density
        + 0.18 * transistor_density,
        1.0,
    )
    pcb_features = pcb_signature_features(mask)

    features = {
        "component_signature_score": float(score),
        "resistor_symbol_density": float(resistor_density),
        "capacitor_symbol_density": float(capacitor_density),
        "diode_symbol_density": float(diode_density),
        "transistor_symbol_density": float(transistor_density),
    }
    features.update(pcb_features)
    return features
