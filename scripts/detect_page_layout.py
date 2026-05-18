#!/usr/bin/env python3
"""Detect coarse page layout blocks before OCR.

The detector is intentionally small: OpenCV finds candidate blocks, a tiny
OpenCV ANN_MLP classifies each block from visual features, and the script writes
JSON, crops, and a colored preview overlay.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
from dataclasses import asdict, dataclass
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


CLASS_NAMES = ["text", "image", "schematic/circuit", "diagram", "table", "other"]
FIGURE_LABELS = {"image", "schematic/circuit", "diagram"}
CLASS_COLORS = {
    "text": (52, 168, 83),
    "image": (66, 133, 244),
    "schematic/circuit": (234, 67, 53),
    "diagram": (251, 188, 5),
    "table": (171, 71, 188),
    "other": (128, 128, 128),
}
CAPTION_HIGHLIGHT_COLOR = (0, 255, 255)
CAPTION_HIGHLIGHT_OPACITY = 0.30
CAPTION_HIGHLIGHT_PADDING = 4
ACCELERATOR_CHOICES = ("cpu", "opencl")


@dataclass(frozen=True)
class Box:
    x: int
    y: int
    w: int
    h: int

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    @property
    def area(self) -> int:
        return max(0, self.w) * max(0, self.h)

    def clamp(self, width: int, height: int) -> "Box":
        x1 = max(0, min(width - 1, self.x))
        y1 = max(0, min(height - 1, self.y))
        x2 = max(x1 + 1, min(width, self.x2))
        y2 = max(y1 + 1, min(height, self.y2))
        return Box(x1, y1, x2 - x1, y2 - y1)

    def inflate(self, pixels: int, width: int, height: int) -> "Box":
        return Box(self.x - pixels, self.y - pixels, self.w + 2 * pixels, self.h + 2 * pixels).clamp(width, height)

    def to_list(self) -> list[int]:
        return [self.x, self.y, self.w, self.h]


@dataclass
class Block:
    ident: str
    label: str
    orientation: str
    confidence: float
    bbox: list[int]
    outline: list[list[list[int]]] | None
    features: dict[str, float]
    crop_path: str | None = None
    figure_ref: str | None = None
    caption_candidates: list[dict[str, object]] | None = None


def require_dependencies() -> None:
    if OPENCV_AVAILABLE:
        return
    raise SystemExit(
        "OpenCV layout detector dependencies are missing. "
        "Run: python -m pip install --target local_tools\\python_packages "
        "opencv-python-headless numpy pillow"
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


def opencl_is_available() -> bool:
    return bool(hasattr(cv2, "ocl") and cv2.ocl.haveOpenCL())


def normalize_accelerator(accelerator: str | None) -> str:
    requested = (accelerator or "cpu").lower()
    if requested not in ACCELERATOR_CHOICES:
        raise ValueError(f"Unsupported accelerator: {accelerator}")
    if requested == "opencl" and not opencl_is_available():
        return "cpu"
    return requested


def configure_accelerator(accelerator: str | None) -> str:
    selected = normalize_accelerator(accelerator)
    if hasattr(cv2, "ocl"):
        cv2.ocl.setUseOpenCL(selected == "opencl")
    return selected


def resize_for_analysis(image, max_side: int, accelerator: str = "cpu"):
    height, width = image.shape[:2]
    scale = min(1.0, max_side / float(max(width, height)))
    if scale >= 0.999:
        return image.copy(), 1.0
    target = (int(round(width * scale)), int(round(height * scale)))
    if accelerator == "opencl":
        resized = cv2.resize(cv2.UMat(image), target, interpolation=cv2.INTER_AREA).get()
    else:
        resized = cv2.resize(image, target, interpolation=cv2.INTER_AREA)
    return resized, scale


def foreground_mask(gray, accelerator: str = "cpu"):
    if accelerator == "opencl":
        gray_u = cv2.UMat(gray)
        blurred_u = cv2.GaussianBlur(gray_u, (3, 3), 0)
        threshold, _ = cv2.threshold(blurred_u, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        _, light_u = cv2.threshold(gray_u, threshold, 255, cv2.THRESH_BINARY)
        light_count = int(cv2.countNonZero(light_u))
        dark_count = int(gray.size - light_count)
        bright_foreground = light_count < dark_count
        mask_u = light_u if bright_foreground else cv2.bitwise_not(light_u)
        return mask_u.get(), int(threshold), bright_foreground

    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    threshold, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    dark = gray <= threshold
    light = gray > threshold
    dark_count = int(dark.sum())
    light_count = int(light.sum())
    bright_foreground = light_count < dark_count
    mask = light if bright_foreground else dark
    return (mask.astype(np.uint8) * 255), int(threshold), bright_foreground


def make_block_mask(gray, mask, accelerator: str = "cpu"):
    height, width = gray.shape[:2]
    line_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(9, width // 90), max(2, height // 550)))
    block_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, width // 65), max(7, height // 180)))
    edge_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(6, width // 180), max(6, height // 220)))
    if accelerator == "opencl":
        gray_u = cv2.UMat(gray)
        mask_u = cv2.UMat(mask)
        textish_u = cv2.morphologyEx(mask_u, cv2.MORPH_CLOSE, line_kernel, iterations=1)
        textish_u = cv2.dilate(textish_u, block_kernel, iterations=1)
        edges_u = cv2.Canny(gray_u, 60, 160)
        edge_blocks_u = cv2.dilate(edges_u, edge_kernel, iterations=1)
        return cv2.bitwise_or(textish_u, edge_blocks_u).get()

    textish = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, line_kernel, iterations=1)
    textish = cv2.dilate(textish, block_kernel, iterations=1)
    edges = cv2.Canny(gray, 60, 160)
    edge_blocks = cv2.dilate(edges, edge_kernel, iterations=1)
    return cv2.bitwise_or(textish, edge_blocks)


def grayscale_image(image, accelerator: str = "cpu"):
    if accelerator == "opencl":
        return cv2.cvtColor(cv2.UMat(image), cv2.COLOR_BGR2GRAY).get()
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def canny_edges(gray, accelerator: str = "cpu"):
    if accelerator == "opencl":
        return cv2.Canny(cv2.UMat(gray), 60, 160).get()
    return cv2.Canny(gray, 60, 160)


def overlap_area(a: Box, b: Box) -> int:
    x1 = max(a.x, b.x)
    y1 = max(a.y, b.y)
    x2 = min(a.x2, b.x2)
    y2 = min(a.y2, b.y2)
    return max(0, x2 - x1) * max(0, y2 - y1)


def union_box(a: Box, b: Box) -> Box:
    x1 = min(a.x, b.x)
    y1 = min(a.y, b.y)
    x2 = max(a.x2, b.x2)
    y2 = max(a.y2, b.y2)
    return Box(x1, y1, x2 - x1, y2 - y1)


def close_or_overlapping(a: Box, b: Box, margin: int) -> bool:
    expanded = a.inflate(margin, 1_000_000, 1_000_000)
    if overlap_area(expanded, b) <= 0:
        return False
    smaller = max(1, min(a.area, b.area))
    overlap = overlap_area(a, b)
    if overlap / smaller > 0.15:
        return True
    overlap_w = max(0, min(a.x2, b.x2) - max(a.x, b.x))
    overlap_h = max(0, min(a.y2, b.y2) - max(a.y, b.y))
    large_block_area = max(6_000, (margin * 20) ** 2)
    large_layout_blocks = (
        min(a.area, b.area) >= large_block_area
        and min(a.w, b.w) >= margin * 8
        and min(a.h, b.h) >= margin * 8
    )
    thin_touch = overlap > 0 and min(overlap_w, overlap_h) <= margin * 2 and overlap / smaller < 0.04
    if large_layout_blocks and (overlap == 0 or thin_touch):
        return False
    horizontal_gap = max(0, max(a.x, b.x) - min(a.x2, b.x2))
    vertical_overlap = min(a.y2, b.y2) - max(a.y, b.y)
    if horizontal_gap <= margin and vertical_overlap > min(a.h, b.h) * 0.25:
        return True
    vertical_gap = max(0, max(a.y, b.y) - min(a.y2, b.y2))
    horizontal_overlap = min(a.x2, b.x2) - max(a.x, b.x)
    return vertical_gap <= margin and horizontal_overlap > min(a.w, b.w) * 0.25


def merge_boxes(boxes: Iterable[Box], width: int, height: int, margin: int) -> list[Box]:
    merged = [box.clamp(width, height) for box in boxes]
    changed = True
    while changed:
        changed = False
        result: list[Box] = []
        used = [False] * len(merged)
        for index, box in enumerate(merged):
            if used[index]:
                continue
            current = box
            used[index] = True
            for other_index in range(index + 1, len(merged)):
                if used[other_index]:
                    continue
                other = merged[other_index]
                if close_or_overlapping(current, other, margin):
                    current = union_box(current, other).clamp(width, height)
                    used[other_index] = True
                    changed = True
            result.append(current)
        merged = result

    final: list[Box] = []
    for box in sorted(merged, key=lambda item: item.area, reverse=True):
        if any(overlap_area(box, kept) / max(1, box.area) > 0.92 for kept in final):
            continue
        final.append(box)
    return sorted(final, key=lambda item: (item.y, item.x))


def smooth_projection(values, radius: int):
    if len(values) == 0:
        return values
    radius = max(1, radius)
    kernel = np.ones(radius * 2 + 1, dtype=np.float32) / float(radius * 2 + 1)
    return np.convolve(values.astype(np.float32), kernel, mode="same")


def projection_runs(values, threshold: float, min_run: int) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start = -1
    for index, value in enumerate(values):
        active = value > threshold
        if active and start < 0:
            start = index
        elif not active and start >= 0:
            if index - start >= min_run:
                runs.append((start, index - 1))
            start = -1
    if start >= 0 and len(values) - start >= min_run:
        runs.append((start, len(values) - 1))
    return runs


def split_box_by_vertical_gaps(mask, box: Box, page_width: int, page_height: int) -> list[Box]:
    if box.h < page_height * 0.18 or box.w < page_width * 0.20:
        return [box]

    roi = mask[box.y : box.y2, box.x : box.x2]
    if roi.size == 0:
        return [box]

    column_projection = (roi > 0).sum(axis=0)
    smoothed = smooth_projection(column_projection, max(2, box.w // 90))
    low_limit = max(2.0, box.h * 0.022)
    min_gap = max(5, int(box.w * 0.015))
    min_piece = max(22, int(page_width * 0.035))

    runs: list[tuple[int, int, float]] = []
    start = -1
    for index, value in enumerate(smoothed):
        low = value <= low_limit
        if low and start < 0:
            start = index
        elif not low and start >= 0:
            end = index - 1
            if end - start + 1 >= min_gap:
                runs.append((start, end, float(smoothed[start : end + 1].mean())))
            start = -1
    if start >= 0:
        end = len(smoothed) - 1
        if end - start + 1 >= min_gap:
            runs.append((start, end, float(smoothed[start : end + 1].mean())))

    candidates = []
    for start, end, mean_density in runs:
        center = (start + end) // 2
        if center < min_piece or box.w - center < min_piece:
            continue
        width = end - start + 1
        candidates.append((width, -mean_density, center))
    if not candidates:
        return [box]

    _, _, center = max(candidates)
    left = Box(box.x, box.y, center, box.h)
    right = Box(box.x + center, box.y, box.w - center, box.h)
    return [piece for piece in (left, right) if piece.area > 0]


def split_boxes_by_internal_gaps(mask, boxes: list[Box], width: int, height: int) -> list[Box]:
    split: list[Box] = []
    for box in boxes:
        split.extend(split_box_by_vertical_gaps(mask, box, width, height))
    return sorted(split, key=lambda item: (item.y, item.x))


def split_box_by_side_color_strip(image, box: Box, page_width: int, page_height: int) -> list[Box]:
    if box.h < page_height * 0.35 or box.w < page_width * 0.22:
        return [box]

    roi = image[box.y : box.y2, box.x : box.x2]
    if roi.size == 0:
        return [box]

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1].mean(axis=0)
    value = hsv[:, :, 2].mean(axis=0)
    smoothed_saturation = smooth_projection(saturation, max(2, box.w // 120))
    smoothed_value = smooth_projection(value, max(2, box.w // 120))

    median_saturation = float(np.median(smoothed_saturation))
    median_value = float(np.median(smoothed_value))
    color_threshold = max(30.0, median_saturation + 18.0)
    dark_threshold = min(220.0, median_value - 18.0)
    side_candidate = (smoothed_saturation > color_threshold) | (smoothed_value < dark_threshold)

    min_strip = max(18, int(page_width * 0.035))
    max_strip = max(min_strip + 1, int(box.w * 0.38))
    min_main = max(80, int(page_width * 0.16))

    right_start = None
    index = box.w - 1
    while index >= 0 and side_candidate[index]:
        right_start = index
        index -= 1
    if right_start is not None:
        strip_width = box.w - right_start
        if min_strip <= strip_width <= max_strip and right_start >= min_main:
            return [Box(box.x, box.y, right_start, box.h), Box(box.x + right_start, box.y, strip_width, box.h)]

    left_end = None
    index = 0
    while index < box.w and side_candidate[index]:
        left_end = index + 1
        index += 1
    if left_end is not None:
        strip_width = left_end
        if min_strip <= strip_width <= max_strip and box.w - left_end >= min_main:
            return [Box(box.x, box.y, strip_width, box.h), Box(box.x + left_end, box.y, box.w - left_end, box.h)]

    return [box]


def split_boxes_by_side_color_strips(image, boxes: list[Box], width: int, height: int) -> list[Box]:
    split: list[Box] = []
    for box in boxes:
        split.extend(split_box_by_side_color_strip(image, box, width, height))
    return sorted(split, key=lambda item: (item.y, item.x))


def dark_ink_mask(gray):
    threshold = int(np.clip(np.percentile(gray, 8), 55, 115))
    return ((gray < threshold).astype(np.uint8) * 255), threshold


def remove_side_color_strips_from_mask(image, work_mask, box: Box) -> None:
    roi = image[box.y : box.y2, box.x : box.x2]
    if roi.size == 0:
        return

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1].mean(axis=0)
    value = hsv[:, :, 2].mean(axis=0)
    smoothed_saturation = smooth_projection(saturation, max(2, box.w // 120))
    smoothed_value = smooth_projection(value, max(2, box.w // 120))

    median_saturation = float(np.median(smoothed_saturation))
    median_value = float(np.median(smoothed_value))
    side_candidate = (smoothed_saturation > max(30.0, median_saturation + 18.0)) | (
        smoothed_value < min(220.0, median_value - 18.0)
    )

    min_strip = max(18, int(round(box.w * 0.025)))
    max_strip = max(min_strip + 1, int(round(box.w * 0.38)))

    right_start = None
    index = box.w - 1
    while index >= 0 and side_candidate[index]:
        right_start = index
        index -= 1
    if right_start is not None and min_strip <= box.w - right_start <= max_strip:
        work_mask[box.y : box.y2, box.x + right_start : box.x2] = 0

    left_end = None
    index = 0
    while index < box.w and side_candidate[index]:
        left_end = index + 1
        index += 1
    if left_end is not None and min_strip <= left_end <= max_strip:
        work_mask[box.y : box.y2, box.x : box.x + left_end] = 0


def likely_visual_candidate_box(box: Box, page_width: int, page_height: int) -> bool:
    page_area = max(1, page_width * page_height)
    area_ratio = box.area / page_area
    title_like = box.h < page_height * 0.07 and box.w > page_width * 0.20
    return area_ratio > 0.015 and not title_like and (box.h > page_height * 0.08 or area_ratio > 0.08)


def inflate_candidate_box(box: Box, pixels: int, width: int, height: int) -> Box:
    return box.inflate(pixels, width, height)


def split_text_candidate_box(mask, box: Box, page_width: int, page_height: int) -> list[Box]:
    pieces = [box]
    if box.w > page_width * 0.35 and box.h > page_height * 0.12:
        pieces = split_box_by_vertical_gaps(mask, box, page_width, page_height)
    return pieces


def split_text_box_around_visuals(box: Box, visual_boxes: list[Box], width: int, height: int) -> list[Box]:
    fragments = [box]
    pad = max(5, min(width, height) // 260)
    for visual in visual_boxes:
        next_fragments: list[Box] = []
        for fragment in fragments:
            overlap = intersection_box(fragment, visual.inflate(pad, width, height))
            if overlap is None or overlap.area / max(1, fragment.area) < 0.025:
                next_fragments.append(fragment)
                continue
            horizontal_cover = overlap.w / max(1, fragment.w)
            vertical_cover = overlap.h / max(1, fragment.h)
            if horizontal_cover >= 0.45:
                top = Box(fragment.x, fragment.y, fragment.w, max(0, overlap.y - fragment.y))
                bottom = Box(fragment.x, overlap.y2, fragment.w, max(0, fragment.y2 - overlap.y2))
                next_fragments.extend(part for part in (top, bottom) if part.w >= 30 and part.h >= 14)
            elif vertical_cover >= 0.45:
                left = Box(fragment.x, fragment.y, max(0, overlap.x - fragment.x), fragment.h)
                right = Box(overlap.x2, fragment.y, max(0, fragment.x2 - overlap.x2), fragment.h)
                next_fragments.extend(part for part in (left, right) if part.w >= 30 and part.h >= 14)
            else:
                next_fragments.append(fragment)
        fragments = next_fragments
    return fragments


def expand_line_art_box_with_ink(dark_mask, parent: Box, candidate: Box, width: int, height: int) -> Box:
    band_pad = max(8, int(round(candidate.h * 0.035)))
    y1 = max(parent.y, candidate.y - band_pad)
    y2 = min(parent.y2, candidate.y2 + band_pad)
    if y2 <= y1:
        return candidate

    horizontal_roi = dark_mask[y1:y2, parent.x : parent.x2]
    column_projection = (horizontal_roi > 0).sum(axis=0)
    smoothed_columns = smooth_projection(column_projection, max(3, parent.w // 160))
    x_runs = projection_runs(smoothed_columns, max(2.0, (y2 - y1) * 0.008), max(20, parent.w // 45))
    candidate_center_x = candidate.x + candidate.w / 2.0 - parent.x
    expanded_x1 = candidate.x
    expanded_x2 = candidate.x2
    for run_x1, run_x2 in x_runs:
        if run_x1 <= candidate_center_x <= run_x2 or (
            min(parent.x + run_x2, candidate.x2) - max(parent.x + run_x1, candidate.x) > candidate.w * 0.35
        ):
            expanded_x1 = parent.x + run_x1
            expanded_x2 = parent.x + run_x2 + 1
            break

    vertical_roi = dark_mask[parent.y : parent.y2, expanded_x1:expanded_x2]
    row_projection = (vertical_roi > 0).sum(axis=1)
    smoothed_rows = smooth_projection(row_projection, max(3, parent.h // 180))
    y_runs = projection_runs(smoothed_rows, max(2.0, (expanded_x2 - expanded_x1) * 0.008), max(20, parent.h // 85))
    candidate_center_y = candidate.y + candidate.h / 2.0 - parent.y
    expanded_y1 = candidate.y
    expanded_y2 = candidate.y2
    for run_y1, run_y2 in y_runs:
        if run_y1 <= candidate_center_y <= run_y2 or (
            min(parent.y + run_y2, candidate.y2) - max(parent.y + run_y1, candidate.y) > candidate.h * 0.35
        ):
            expanded_y1 = parent.y + run_y1
            expanded_y2 = parent.y + run_y2 + 1
            break

    return Box(expanded_x1, expanded_y1, expanded_x2 - expanded_x1, expanded_y2 - expanded_y1).inflate(
        max(3, min(width, height) // 300), width, height
    )


def line_art_boxes_from_large_regions(
    image,
    foreground,
    gray,
    boxes: list[Box],
    width: int,
    height: int,
) -> list[Box]:
    page_area = max(1, width * height)
    parent_boxes = [
        box
        for box in boxes
        if box.area / page_area > 0.22 and box.w > width * 0.34 and box.h > height * 0.45
    ]
    if not parent_boxes:
        return []

    line_length = max(35, min(width, height) // 45)
    close_size = max(12, min(width, height) // 110)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (line_length, 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, line_length))
    h_lines = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, h_kernel)
    v_lines = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, v_kernel)
    line_mask = cv2.bitwise_or(h_lines, v_lines)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (close_size, close_size))
    line_mask = cv2.dilate(line_mask, close_kernel, iterations=1)

    dark_mask, _ = dark_ink_mask(gray)
    contours, _ = cv2.findContours(line_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[Box] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        candidate = Box(x, y, w, h).inflate(max(3, min(width, height) // 320), width, height)
        if candidate.area / page_area < 0.035 or candidate.w < width * 0.22 or candidate.h < height * 0.10:
            continue
        for parent in parent_boxes:
            if overlap_area(candidate, parent) / max(1, candidate.area) < 0.80:
                continue
            if candidate.area > parent.area * 0.78:
                continue
            expanded = expand_line_art_box_with_ink(dark_mask, parent, candidate, width, height)
            if expanded.area / page_area >= 0.035:
                candidates.append(expanded)

    return deduplicate_candidate_boxes(candidates)


def split_boxes_around_visual_candidates(boxes: list[Box], visual_boxes: list[Box], width: int, height: int) -> list[Box]:
    if not visual_boxes:
        return boxes

    page_area = max(1, width * height)
    result: list[Box] = []
    for box in boxes:
        cutters = [
            visual
            for visual in visual_boxes
            if box.area > visual.area * 1.35
            and box.area / page_area > 0.08
            and overlap_area(box, visual) / max(1, visual.area) > 0.82
        ]
        if cutters:
            result.extend(split_text_box_around_visuals(box, cutters, width, height))
        else:
            result.append(box)
    result.extend(visual_boxes)
    return deduplicate_candidate_boxes(result)


def text_boxes_from_oversized_regions(
    image,
    gray,
    oversized_boxes: list[Box],
    existing_boxes: list[Box],
    width: int,
    height: int,
) -> list[Box]:
    if not oversized_boxes:
        return []

    ink_mask, _ = dark_ink_mask(gray)
    page_area = max(1, width * height)
    result: list[Box] = []
    for oversized in oversized_boxes:
        visual_boxes = [
            box
            for box in existing_boxes
            if likely_visual_candidate_box(box, width, height)
            and not (
                box.area >= oversized.area * 0.65
                and overlap_area(box, oversized) / max(1, oversized.area) > 0.75
            )
        ]
        work_mask = np.zeros_like(ink_mask)
        work_mask[oversized.y : oversized.y2, oversized.x : oversized.x2] = ink_mask[
            oversized.y : oversized.y2, oversized.x : oversized.x2
        ]
        for existing in visual_boxes:
            cleared = inflate_candidate_box(existing, max(6, min(width, height) // 220), width, height)
            work_mask[cleared.y : cleared.y2, cleared.x : cleared.x2] = 0
        remove_side_color_strips_from_mask(image, work_mask, oversized)

        line_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(7, width // 180), 1))
        line_mask = cv2.morphologyEx(work_mask, cv2.MORPH_CLOSE, line_kernel, iterations=1)
        block_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(4, width // 260), max(2, height // 700)))
        line_mask = cv2.dilate(line_mask, block_kernel, iterations=1)

        column_projection = (line_mask > 0).sum(axis=0)
        smoothed_columns = smooth_projection(column_projection, max(3, width // 180))
        x_runs = projection_runs(smoothed_columns, max(5.0, height * 0.012), max(45, width // 30))

        for x1, x2 in x_runs:
            column_width = x2 - x1 + 1
            if column_width < max(45, width // 35):
                continue
            column_mask = line_mask[:, x1 : x2 + 1]
            row_projection = (column_mask > 0).sum(axis=1)
            smoothed_rows = smooth_projection(row_projection, max(2, height // 300))
            y_runs = projection_runs(smoothed_rows, max(3.0, column_width * 0.018), max(14, height // 140))
            for y1, y2 in y_runs:
                candidate = Box(x1, y1, column_width, y2 - y1 + 1).inflate(2, width, height)
                if candidate.area / page_area < 0.00035 or candidate.w < 30 or candidate.h < 14:
                    continue
                for piece in split_text_candidate_box(line_mask, candidate, width, height):
                    for fragment in split_text_box_around_visuals(piece, visual_boxes, width, height):
                        if fragment.area / page_area >= 0.00035 and fragment.w >= 30 and fragment.h >= 14:
                            result.append(fragment)

    return result


def deduplicate_candidate_boxes(boxes: list[Box]) -> list[Box]:
    kept: list[Box] = []
    for box in boxes:
        duplicate = False
        for existing in kept:
            overlap = overlap_area(box, existing)
            if overlap / max(1, box.area) > 0.88:
                duplicate = True
                break
            if overlap / max(1, box.area) > 0.62 and overlap / max(1, existing.area) > 0.62:
                duplicate = True
                break
        if not duplicate:
            kept.append(box)
    return sorted(kept, key=lambda item: (item.y, item.x))


def detect_candidate_boxes(
    image,
    min_area_ratio: float = 0.00035,
    max_area_ratio: float = 0.85,
    accelerator: str = "cpu",
) -> tuple[list[Box], dict[str, object]]:
    accelerator = normalize_accelerator(accelerator)
    gray = grayscale_image(image, accelerator)
    mask, threshold, bright_foreground = foreground_mask(gray, accelerator)
    # Keep the block mask on CPU: OpenCL morphology can change contour topology
    # enough to alter page segmentation, even when it is slightly faster.
    block_mask = make_block_mask(gray, mask, "cpu")
    height, width = gray.shape[:2]
    page_area = width * height
    border_x = max(4, width // 80)
    border_y = max(4, height // 80)
    block_mask[:border_y, :] = 0
    block_mask[height - border_y :, :] = 0
    block_mask[:, :border_x] = 0
    block_mask[:, width - border_x :] = 0

    contours, _ = cv2.findContours(block_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    raw_boxes: list[Box] = []
    boxes: list[Box] = []
    oversized_boxes: list[Box] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        box = Box(x, y, w, h).inflate(max(3, min(width, height) // 250), width, height)
        area_ratio = box.area / page_area
        if area_ratio > max_area_ratio:
            if area_ratio <= 0.98:
                oversized_boxes.append(box)
            continue
        if area_ratio < min_area_ratio:
            continue
        if box.w < 8 or box.h < 8:
            continue
        raw_boxes.append(box)
        boxes.append(box)

    boxes = merge_boxes(boxes, width, height, max(5, min(width, height) // 170))
    boxes = [box for box in boxes if min_area_ratio <= box.area / page_area <= max_area_ratio]
    if not boxes:
        boxes = raw_boxes
    boxes = split_boxes_by_internal_gaps(mask, boxes, width, height)
    boxes = split_boxes_by_side_color_strips(image, boxes, width, height)
    line_art_boxes = line_art_boxes_from_large_regions(image, mask, gray, boxes, width, height)
    large_mixed_boxes = [
        box
        for box in boxes
        if box.area / page_area > 0.22
        and any(overlap_area(box, visual) / max(1, visual.area) > 0.82 for visual in line_art_boxes)
    ]
    if large_mixed_boxes:
        recovered_text_boxes = text_boxes_from_oversized_regions(
            image, gray, large_mixed_boxes, boxes + line_art_boxes, width, height
        )
        if recovered_text_boxes:
            boxes = [box for box in boxes if box not in large_mixed_boxes] + recovered_text_boxes
    boxes = split_boxes_around_visual_candidates(boxes, line_art_boxes, width, height)
    if oversized_boxes:
        boxes = deduplicate_candidate_boxes(
            boxes + text_boxes_from_oversized_regions(image, gray, oversized_boxes, boxes, width, height)
        )
    if not boxes:
        boxes = raw_boxes
    metadata = {
        "threshold": threshold,
        "bright_foreground": bright_foreground,
        "analysis_width": width,
        "analysis_height": height,
        "accelerator": accelerator,
    }
    return boxes, metadata


def count_projection_runs(values, threshold: float) -> int:
    runs = 0
    in_run = False
    for value in values:
        active = value >= threshold
        if active and not in_run:
            runs += 1
        in_run = active
    return runs


def projection_text_score(binary, width: int, height: int) -> float:
    if width <= 0 or height <= 0:
        return 0.0
    row_projection = (binary > 0).sum(axis=1)
    threshold = max(2, width * 0.035)
    runs = count_projection_runs(row_projection, threshold)
    return min(runs / max(1.0, height / 18.0), 1.0)


def rotate_mask_for_orientation(mask, angle: float):
    height, width = mask.shape[:2]
    center = (width / 2.0, height / 2.0)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    cos = abs(matrix[0, 0])
    sin = abs(matrix[0, 1])
    new_width = int((height * sin) + (width * cos))
    new_height = int((height * cos) + (width * sin))
    matrix[0, 2] += (new_width / 2.0) - center[0]
    matrix[1, 2] += (new_height / 2.0) - center[1]
    return cv2.warpAffine(mask, matrix, (new_width, new_height), flags=cv2.INTER_NEAREST, borderValue=0)


def text_orientation_scores(roi_mask) -> dict[str, float]:
    horizontal = projection_text_score(roi_mask, roi_mask.shape[1], roi_mask.shape[0])
    vertical_mask = cv2.rotate(roi_mask, cv2.ROTATE_90_CLOCKWISE)
    vertical = projection_text_score(vertical_mask, vertical_mask.shape[1], vertical_mask.shape[0])

    diagonal_scores = []
    for angle in (-45.0, -30.0, 30.0, 45.0):
        rotated = rotate_mask_for_orientation(roi_mask, angle)
        diagonal_scores.append(projection_text_score(rotated, rotated.shape[1], rotated.shape[0]))
    diagonal = max(diagonal_scores) if diagonal_scores else 0.0
    return {
        "horizontal_text_score": horizontal,
        "vertical_text_score": vertical,
        "diagonal_text_score": diagonal,
        "max_text_score": max(horizontal, vertical, diagonal),
    }


def infer_orientation(features: dict[str, float]) -> str:
    horizontal = features["horizontal_text_score"]
    vertical = features["vertical_text_score"]
    diagonal = features["diagonal_text_score"]
    best = max(horizontal, vertical, diagonal)
    if best < 0.18:
        return "unknown"

    if features["tall_aspect"] > 0.65 and vertical >= max(horizontal, diagonal) * 0.78:
        return "vertical"
    if features["wide_aspect"] > 0.35 and horizontal >= 0.18:
        return "horizontal"
    if diagonal >= best * 0.95 and diagonal > max(horizontal, vertical) + 0.08:
        return "diagonal"
    if vertical >= horizontal + 0.08:
        return "vertical"
    return "horizontal"


def feature_dict(image, mask, edges, box: Box) -> dict[str, float]:
    page_h, page_w = mask.shape[:2]
    roi_gray = cv2.cvtColor(image[box.y : box.y2, box.x : box.x2], cv2.COLOR_BGR2GRAY)
    roi_bgr = image[box.y : box.y2, box.x : box.x2]
    roi_mask = mask[box.y : box.y2, box.x : box.x2]
    roi_edges = edges[box.y : box.y2, box.x : box.x2]
    area = max(1, box.area)

    components, labels, stats, _ = cv2.connectedComponentsWithStats((roi_mask > 0).astype(np.uint8), 8)
    component_count = 0
    for index in range(1, components):
        if stats[index, cv2.CC_STAT_AREA] >= 4:
            component_count += 1

    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(8, box.w // 6), 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(8, box.h // 6)))
    h_lines = cv2.morphologyEx(roi_mask, cv2.MORPH_OPEN, h_kernel)
    v_lines = cv2.morphologyEx(roi_mask, cv2.MORPH_OPEN, v_kernel)
    local_h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(5, box.w // 35), 1))
    local_v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(5, box.h // 35)))
    local_h_lines = cv2.morphologyEx(roi_mask, cv2.MORPH_OPEN, local_h_kernel)
    local_v_lines = cv2.morphologyEx(roi_mask, cv2.MORPH_OPEN, local_v_kernel)

    orientation_scores = text_orientation_scores(roi_mask)

    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1].astype(np.float32) / 255.0
    gray_bins = np.unique((roi_gray // 8).astype(np.uint8)).size
    h_density = float((h_lines > 0).sum()) / area
    v_density = float((v_lines > 0).sum()) / area
    local_line_density = float(((local_h_lines > 0) | (local_v_lines > 0)).sum()) / area
    line_balance = min(h_density, v_density) / max(h_density, v_density, 1e-6)

    return {
        "width_ratio": box.w / max(1, page_w),
        "height_ratio": box.h / max(1, page_h),
        "area_ratio": area / max(1, page_w * page_h),
        "wide_aspect": min((box.w / max(1, box.h)) / 5.0, 1.0),
        "tall_aspect": min((box.h / max(1, box.w)) / 5.0, 1.0),
        "ink_density": float((roi_mask > 0).sum()) / area,
        "edge_density": min(float((roi_edges > 0).sum()) / area * 4.0, 1.0),
        "gray_std": min(float(roi_gray.std()) / 90.0, 1.0),
        "gray_levels": min(float(gray_bins) / 32.0, 1.0),
        "component_density": min(component_count / max(1.0, area / 1000.0), 1.0),
        "hline_density": min(h_density * 9.0, 1.0),
        "vline_density": min(v_density * 9.0, 1.0),
        "line_art_score": min(local_line_density * 6.0, 1.0),
        "line_balance": line_balance,
        "saturation_mean": float(saturation.mean()),
        "saturation_p80": float(np.percentile(saturation, 80)),
        "textline_density": orientation_scores["horizontal_text_score"],
        "horizontal_text_score": orientation_scores["horizontal_text_score"],
        "vertical_text_score": orientation_scores["vertical_text_score"],
        "diagonal_text_score": orientation_scores["diagonal_text_score"],
        "max_text_score": orientation_scores["max_text_score"],
    }


FEATURE_ORDER = [
    "width_ratio",
    "height_ratio",
    "area_ratio",
    "wide_aspect",
    "tall_aspect",
    "ink_density",
    "edge_density",
    "gray_std",
    "gray_levels",
    "component_density",
    "hline_density",
    "vline_density",
    "line_balance",
    "textline_density",
    "horizontal_text_score",
    "vertical_text_score",
    "diagonal_text_score",
    "max_text_score",
]


def vector_from_features(features: dict[str, float]):
    return np.array([features[name] for name in FEATURE_ORDER], dtype=np.float32)


def jittered_samples(prototype: list[float], count: int, rng):
    base = np.array(prototype, dtype=np.float32)
    noise = rng.normal(0.0, 0.07, size=(count, base.size)).astype(np.float32)
    return np.clip(base + noise, 0.0, 1.0)


def train_bootstrap_ann():
    prototypes = {
        "text": [0.42, 0.26, 0.10, 0.55, 0.10, 0.10, 0.10, 0.14, 0.18, 0.78, 0.10, 0.02, 0.12, 0.82, 0.82, 0.18, 0.20, 0.82],
        "image": [0.28, 0.25, 0.08, 0.25, 0.22, 0.43, 0.58, 0.78, 0.95, 0.18, 0.04, 0.04, 0.25, 0.18, 0.18, 0.16, 0.16, 0.18],
        "schematic/circuit": [0.36, 0.30, 0.09, 0.42, 0.18, 0.07, 0.18, 0.20, 0.34, 0.45, 0.42, 0.34, 0.78, 0.38, 0.38, 0.28, 0.32, 0.38],
        "diagram": [0.32, 0.24, 0.08, 0.36, 0.20, 0.13, 0.28, 0.36, 0.55, 0.52, 0.20, 0.14, 0.45, 0.45, 0.45, 0.28, 0.35, 0.45],
        "table": [0.40, 0.24, 0.10, 0.70, 0.08, 0.08, 0.12, 0.16, 0.24, 0.35, 0.58, 0.52, 0.88, 0.68, 0.68, 0.30, 0.22, 0.68],
        "other": [0.08, 0.06, 0.01, 0.18, 0.12, 0.02, 0.04, 0.06, 0.12, 0.08, 0.02, 0.02, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08],
    }
    rng = np.random.default_rng(42)
    rows = []
    labels = []
    for class_index, class_name in enumerate(CLASS_NAMES):
        samples = jittered_samples(prototypes[class_name], 90, rng)
        rows.append(samples)
        response = np.full((samples.shape[0], len(CLASS_NAMES)), -1.0, dtype=np.float32)
        response[:, class_index] = 1.0
        labels.append(response)

    train_data = np.vstack(rows).astype(np.float32)
    responses = np.vstack(labels).astype(np.float32)

    ann = cv2.ml.ANN_MLP_create()
    ann.setLayerSizes(np.array([len(FEATURE_ORDER), 18, len(CLASS_NAMES)], dtype=np.int32))
    ann.setActivationFunction(cv2.ml.ANN_MLP_SIGMOID_SYM, 1.0, 1.0)
    ann.setTrainMethod(cv2.ml.ANN_MLP_BACKPROP, 0.04)
    ann.setTermCriteria((cv2.TERM_CRITERIA_MAX_ITER | cv2.TERM_CRITERIA_EPS, 700, 1e-5))
    ann.train(train_data, cv2.ml.ROW_SAMPLE, responses)
    return ann


def rule_scores(features: dict[str, float]) -> np.ndarray:
    scores = np.zeros(len(CLASS_NAMES), dtype=np.float32)
    ink = features["ink_density"]
    edge = features["edge_density"]
    std = features["gray_std"]
    levels = features["gray_levels"]
    components = features["component_density"]
    hline = features["hline_density"]
    vline = features["vline_density"]
    balance = features["line_balance"]
    textlines = features["textline_density"]
    max_text = features["max_text_score"]
    vertical_text = features["vertical_text_score"]
    diagonal_text = features["diagonal_text_score"]
    area = features["area_ratio"]

    scores[0] = 1.8 * max_text + 1.1 * components + 0.4 * ink + 0.3 * max(vertical_text, diagonal_text) - 0.45 * balance
    scores[1] = 1.6 * std + 1.3 * levels + 0.9 * edge + 0.5 * ink - 0.75 * max_text
    scores[2] = 1.1 * hline + 1.1 * vline + 0.8 * balance + 0.5 * edge - 0.5 * std
    scores[3] = 0.8 * edge + 0.6 * hline + 0.25 * max_text + 0.5 * levels
    scores[4] = 1.4 * hline + 1.4 * vline + 1.2 * balance + 0.25 * max_text - 0.4 * std
    scores[5] = 0.5 + (0.08 > area) * 0.2 - 0.4 * ink - 0.2 * edge
    scores = np.maximum(scores, 0.001)
    return scores / scores.sum()


def classify_features(ann, features: dict[str, float]) -> tuple[str, float]:
    vector = vector_from_features(features)
    _, raw = ann.predict(vector.reshape(1, -1))
    ann_scores = raw[0].astype(np.float32)
    ann_scores = np.exp(ann_scores - ann_scores.max())
    ann_scores = ann_scores / max(float(ann_scores.sum()), 1e-6)
    scores = 0.65 * ann_scores + 0.35 * rule_scores(features)
    max_text = features["max_text_score"]
    line_art = features.get("line_art_score", 0.0)
    saturation_p80 = features.get("saturation_p80", 0.0)

    if features["area_ratio"] < 0.002 and features["textline_density"] < 0.25:
        scores *= 0.65
        scores[CLASS_NAMES.index("other")] += 0.35
    if features["gray_std"] > 0.55 and features["gray_levels"] > 0.75 and features["area_ratio"] > 0.01 and max_text < 0.45:
        scores[CLASS_NAMES.index("image")] += 0.25
    if (
        features["area_ratio"] > 0.035
        and line_art > 0.16
        and saturation_p80 < 0.08
        and features["component_density"] > 0.45
        and features["ink_density"] < 0.32
        and max_text < 0.38
    ):
        scores[CLASS_NAMES.index("schematic/circuit")] += 1.15
        scores[CLASS_NAMES.index("image")] *= 0.30
        scores[CLASS_NAMES.index("diagram")] *= 0.65
    if (
        features["area_ratio"] > 0.10
        and line_art > 0.22
        and saturation_p80 < 0.08
        and features["component_density"] > 0.50
        and features["ink_density"] < 0.22
        and features["line_balance"] > 0.25
        and features["edge_density"] > 0.22
    ):
        scores[CLASS_NAMES.index("schematic/circuit")] += 1.65
        scores[CLASS_NAMES.index("text")] *= 0.32
        scores[CLASS_NAMES.index("image")] *= 0.35
        scores[CLASS_NAMES.index("diagram")] *= 0.70
    if (
        0.004 < features["area_ratio"] < 0.040
        and line_art > 0.30
        and saturation_p80 < 0.08
        and features["component_density"] > 0.30
        and features["edge_density"] > 0.18
        and features["ink_density"] < 0.16
        and 0.20 < features["line_balance"] < 0.70
    ):
        scores[CLASS_NAMES.index("schematic/circuit")] += 1.10
        scores[CLASS_NAMES.index("diagram")] *= 0.35
        scores[CLASS_NAMES.index("table")] *= 0.55
        scores[CLASS_NAMES.index("image")] *= 0.60
    if (
        saturation_p80 > 0.16
        and features["gray_std"] > 0.45
        and features["area_ratio"] > 0.008
        and features["component_density"] > 0.20
        and max_text < 0.45
    ):
        scores[CLASS_NAMES.index("image")] += 1.00
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.35
        scores[CLASS_NAMES.index("table")] *= 0.60
    if (
        features["area_ratio"] > 0.035
        and line_art > 0.22
        and features["ink_density"] < 0.18
        and features["edge_density"] > 0.18
        and features["line_balance"] > 0.45
        and min(features["hline_density"], features["vline_density"]) > 0.07
        and max_text < 0.70
    ):
        scores[CLASS_NAMES.index("schematic/circuit")] += 1.45
        scores[CLASS_NAMES.index("image")] *= 0.35
        scores[CLASS_NAMES.index("diagram")] *= 0.55
        scores[CLASS_NAMES.index("text")] *= 0.70
    if features["hline_density"] > 0.30 and features["vline_density"] > 0.24 and features["line_balance"] > 0.55:
        scores[CLASS_NAMES.index("table")] += 0.15
        scores[CLASS_NAMES.index("schematic/circuit")] += 0.10
    if (
        features["tall_aspect"] > 0.80
        and features["width_ratio"] < 0.12
        and features["ink_density"] > 0.45
        and features["gray_std"] > 0.45
    ):
        scores[CLASS_NAMES.index("image")] += 0.75
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.35
        scores[CLASS_NAMES.index("table")] *= 0.55
    if (
        features["max_text_score"] > 0.50
        and features["component_density"] > 0.60
        and max(features["hline_density"], features["vline_density"]) < 0.18
    ):
        scores[CLASS_NAMES.index("text")] += 1.15
        scores[CLASS_NAMES.index("image")] *= 0.25
    if (
        features["max_text_score"] > 0.22
        and features["component_density"] > 0.45
        and features["line_balance"] < 0.35
        and max(features["hline_density"], features["vline_density"]) < 0.72
    ):
        scores[CLASS_NAMES.index("text")] += 0.45
        scores[CLASS_NAMES.index("table")] *= 0.72
        scores[CLASS_NAMES.index("diagram")] *= 0.72
    if (
        features["height_ratio"] < 0.065
        and features["area_ratio"] < 0.030
        and features["max_text_score"] > 0.30
        and features["component_density"] > 0.25
        and features["ink_density"] > 0.12
        and features["gray_std"] > 0.50
    ):
        scores[CLASS_NAMES.index("text")] += 0.95
        scores[CLASS_NAMES.index("image")] *= 0.35
        scores[CLASS_NAMES.index("diagram")] *= 0.45
        scores[CLASS_NAMES.index("table")] *= 0.45
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.45
    if (
        features["height_ratio"] < 0.090
        and features["wide_aspect"] > 0.80
        and features["area_ratio"] < 0.075
        and features["max_text_score"] > 0.18
        and features["ink_density"] > 0.12
        and features["line_balance"] < 0.12
    ):
        scores[CLASS_NAMES.index("text")] += 1.25
        scores[CLASS_NAMES.index("image")] *= 0.25
        scores[CLASS_NAMES.index("diagram")] *= 0.50
        scores[CLASS_NAMES.index("table")] *= 0.55
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.40
    if features["max_text_score"] > 0.48 and features["line_balance"] < 0.20:
        scores[CLASS_NAMES.index("text")] += 0.70
        scores[CLASS_NAMES.index("diagram")] *= 0.55
        scores[CLASS_NAMES.index("table")] *= 0.65
    scores = scores / max(float(scores.sum()), 1e-6)

    index = int(scores.argmax())
    return CLASS_NAMES[index], float(scores[index])


def safe_label(label: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "_", label.lower()).strip("_") or "block"


def box_from_list(values: list[int]) -> Box:
    return Box(int(values[0]), int(values[1]), int(values[2]), int(values[3]))


def rectangle_polygon(box: Box) -> list[list[list[int]]]:
    return [[[box.x, box.y], [box.x2, box.y], [box.x2, box.y2], [box.x, box.y2]]]


def intersection_box(first: Box, second: Box) -> Box | None:
    left = max(first.x, second.x)
    top = max(first.y, second.y)
    right = min(first.x2, second.x2)
    bottom = min(first.y2, second.y2)
    if right <= left or bottom <= top:
        return None
    return Box(left, top, right - left, bottom - top)


def intersection_area(first: Box, second: Box) -> int:
    intersection = intersection_box(first, second)
    return 0 if intersection is None else intersection.area


def simplify_axis_aligned_polygon(points: list[list[int]]) -> list[list[int]]:
    if len(points) < 3:
        return points

    compact: list[list[int]] = []
    for point in points:
        if not compact or compact[-1] != point:
            compact.append(point)
    if len(compact) > 1 and compact[0] == compact[-1]:
        compact.pop()

    changed = True
    while changed and len(compact) >= 3:
        changed = False
        filtered: list[list[int]] = []
        count = len(compact)
        for index, point in enumerate(compact):
            previous = compact[(index - 1) % count]
            next_point = compact[(index + 1) % count]
            if (previous[0] == point[0] == next_point[0]) or (previous[1] == point[1] == next_point[1]):
                changed = True
                continue
            filtered.append(point)
        compact = filtered

    return compact


def collapse_tiny_stair_steps(points: list[list[int]], tolerance: int = 2) -> list[list[int]]:
    compact = points[:]
    changed = True
    while changed and len(compact) >= 4:
        changed = False
        for index in range(len(compact) - 2):
            first = compact[index]
            middle = compact[index + 1]
            third = compact[index + 2]
            first_step = abs(first[0] - middle[0]) + abs(first[1] - middle[1])
            second_step = abs(middle[0] - third[0]) + abs(middle[1] - third[1])
            if first_step <= tolerance and second_step <= tolerance and first[0] != third[0] and first[1] != third[1]:
                corner = [third[0], first[1]]
                compact = compact[:index] + [corner] + compact[index + 3 :]
                changed = True
                break
    return compact


def orthogonalize_polygon(points: list[list[int]]) -> list[list[int]]:
    if len(points) < 2:
        return points

    result: list[list[int]] = [points[0]]
    for point in points[1:]:
        previous = result[-1]
        if previous[0] != point[0] and previous[1] != point[1]:
            result.append([point[0], previous[1]])
        result.append(point)

    first = result[0]
    last = result[-1]
    if first[0] != last[0] and first[1] != last[1]:
        result.append([first[0], last[1]])

    return simplify_axis_aligned_polygon(collapse_tiny_stair_steps(result))


def text_block_should_cut_visual_outline(visual_box: Box, text_box: Box) -> bool:
    overlap = intersection_box(visual_box, text_box)
    if overlap is None:
        return False

    text_overlap_fraction = overlap.area / max(1, text_box.area)
    visual_overlap_fraction = overlap.area / max(1, visual_box.area)
    if text_overlap_fraction < 0.18 and visual_overlap_fraction < 0.01:
        return False

    edge_margin = max(10, min(60, int(round(min(visual_box.w, visual_box.h) * 0.12))))
    touches_edge = (
        overlap.x <= visual_box.x + edge_margin
        or overlap.x2 >= visual_box.x2 - edge_margin
        or overlap.y <= visual_box.y + edge_margin
        or overlap.y2 >= visual_box.y2 - edge_margin
    )
    if not touches_edge:
        return False

    # Small labels inside a circuit are part of the drawing. Large prose blocks
    # touching a visual block edge are what should carve the preview outline.
    small_internal_label = (
        text_box.area < visual_box.area * 0.012
        and text_box.h < max(42, int(round(visual_box.h * 0.12)))
        and text_box.w < max(180, int(round(visual_box.w * 0.35)))
    )
    return not small_internal_label


def visual_outline_from_text_cutouts(visual_block: Block, text_blocks: list[Block]) -> list[list[list[int]]]:
    visual_box = box_from_list(visual_block.bbox)
    if visual_box.area <= 0:
        return []

    mask = np.full((visual_box.h, visual_box.w), 255, dtype=np.uint8)
    cutouts = 0
    pad = max(3, min(14, int(round(min(visual_box.w, visual_box.h) * 0.025))))
    for text_block in text_blocks:
        text_box = box_from_list(text_block.bbox)
        if not text_block_should_cut_visual_outline(visual_box, text_box):
            continue
        padded = text_box.inflate(pad, visual_box.x2 + pad + 1, visual_box.y2 + pad + 1)
        cutout = intersection_box(visual_box, padded)
        if cutout is None:
            continue
        x1 = max(0, cutout.x - visual_box.x)
        y1 = max(0, cutout.y - visual_box.y)
        x2 = min(visual_box.w, cutout.x2 - visual_box.x)
        y2 = min(visual_box.h, cutout.y2 - visual_box.y)
        if x2 <= x1 or y2 <= y1:
            continue
        mask[y1:y2, x1:x2] = 0
        cutouts += 1

    if cutouts == 0:
        return rectangle_polygon(visual_box)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = max(25.0, visual_box.area * 0.002)
    selected = sorted((contour for contour in contours if cv2.contourArea(contour) >= min_area), key=cv2.contourArea, reverse=True)
    polygons: list[list[list[int]]] = []
    for contour in selected[:8]:
        approx = cv2.approxPolyDP(contour, 4.0, True)
        points = [[visual_box.x + int(point[0]), visual_box.y + int(point[1])] for point in approx.reshape(-1, 2)]
        points = orthogonalize_polygon(points)
        if len(points) >= 3:
            polygons.append(points)

    return polygons or rectangle_polygon(visual_box)


def assign_visual_outlines(blocks: list[Block]) -> None:
    text_blocks = [block for block in blocks if block.label == "text"]
    for block in blocks:
        if block.label in FIGURE_LABELS:
            block.outline = visual_outline_from_text_cutouts(block, text_blocks)


def block_preview_label(block: Block) -> str:
    block_number = block.ident.split("_", 1)[0] if block.ident else "?"
    label = "schematic" if block.label == "schematic/circuit" else block.label
    if block.label == "text" and block.orientation != "unknown":
        label = f"{label} {block.orientation}"
    return f"#{block_number} {label} {block.confidence:.2f}"


def caption_highlight_boxes(blocks: list[Block]) -> list[Box]:
    boxes: list[Box] = []
    seen: set[tuple[int, int, int, int]] = set()
    for block in blocks:
        for candidate in block.caption_candidates or []:
            bbox = candidate.get("bbox") if isinstance(candidate, dict) else None
            if not bbox or len(bbox) != 4:
                continue
            box = box_from_list([int(value) for value in bbox])
            key = (box.x, box.y, box.w, box.h)
            if key in seen:
                continue
            seen.add(key)
            boxes.append(box)
    return boxes


def horizontal_overlap_fraction(first: Box, second: Box) -> float:
    left = max(first.x, second.x)
    right = min(first.x2, second.x2)
    if right <= left:
        return 0.0
    return (right - left) / max(1, first.w)


def point_inside_outline(point: tuple[float, float], outline: list[list[list[int]]] | None) -> bool:
    if not outline:
        return False
    for polygon in outline:
        if len(polygon) < 3:
            continue
        contour = np.array(polygon, dtype=np.float32)
        if cv2.pointPolygonTest(contour, point, False) >= 0:
            return True
    return False


def text_block_inside_schematic(text_block: Block, schematic_block: Block) -> bool:
    text_box = box_from_list(text_block.bbox)
    schematic_box = box_from_list(schematic_block.bbox)
    if text_box.area <= 0 or schematic_box.area <= text_box.area:
        return False

    overlap_fraction = intersection_area(text_box, schematic_box) / max(1, text_box.area)
    top_margin = max(24, int(round(schematic_box.h * 0.055)))
    touches_schematic_top = text_box.y < schematic_box.y and text_box.y2 >= schematic_box.y - top_margin
    small_top_label = (
        touches_schematic_top
        and text_box.area < schematic_box.area * 0.015
        and text_box.h < schematic_box.h * 0.08
        and horizontal_overlap_fraction(text_box, schematic_box) >= 0.60
    )
    if overlap_fraction < 0.35:
        return bool(schematic_block.outline and small_top_label)

    center = (text_box.x + text_box.w / 2.0, text_box.y + text_box.h / 2.0)
    if schematic_block.outline:
        corners = [
            (float(text_box.x), float(text_box.y)),
            (float(text_box.x2), float(text_box.y)),
            (float(text_box.x), float(text_box.y2)),
            (float(text_box.x2), float(text_box.y2)),
        ]
        inside_points = int(point_inside_outline(center, schematic_block.outline))
        inside_points += sum(1 for corner in corners if point_inside_outline(corner, schematic_block.outline))
        if inside_points >= 1 and overlap_fraction >= 0.45:
            return True

        return small_top_label

    return overlap_fraction >= 0.75


def suppress_text_inside_schematics(blocks: list[Block]) -> list[Block]:
    schematic_blocks = [block for block in blocks if block.label == "schematic/circuit"]
    if not schematic_blocks:
        return blocks

    filtered: list[Block] = []
    for block in blocks:
        if block.label == "text" and any(text_block_inside_schematic(block, schematic) for schematic in schematic_blocks):
            continue
        filtered.append(block)
    return filtered


def text_block_inside_text_block(inner_block: Block, outer_block: Block) -> bool:
    if inner_block.ident == outer_block.ident or inner_block.label != "text" or outer_block.label != "text":
        return False

    inner_box = box_from_list(inner_block.bbox)
    outer_box = box_from_list(outer_block.bbox)
    if inner_box.area <= 0 or outer_box.area <= inner_box.area:
        return False

    overlap_fraction = intersection_area(inner_box, outer_box) / max(1, inner_box.area)
    if overlap_fraction < 0.92:
        return False

    much_larger_area = outer_box.area >= inner_box.area * 2.5
    wider_or_equal = outer_box.w >= inner_box.w * 0.95
    much_taller = outer_box.h >= inner_box.h * 2.0
    return much_larger_area and wider_or_equal and much_taller


def suppress_nested_text_blocks(blocks: list[Block]) -> list[Block]:
    text_blocks = [block for block in blocks if block.label == "text"]
    if len(text_blocks) < 2:
        return blocks

    nested_idents = {
        inner.ident
        for inner in text_blocks
        if any(text_block_inside_text_block(inner, outer) for outer in text_blocks)
    }
    if not nested_idents:
        return blocks
    return [block for block in blocks if block.ident not in nested_idents]


def caption_candidate_for_figure(figure_block: Block, text_block: Block) -> dict[str, object] | None:
    figure_box = box_from_list(figure_block.bbox)
    text_box = box_from_list(text_block.bbox)
    if figure_box.area <= 0 or text_box.area <= 0:
        return None
    max_caption_area_fraction = 0.18 if figure_box.h < 140 else 0.055
    if text_box.area > figure_box.area * max_caption_area_fraction:
        return None
    if text_box.h > max(80, int(round(figure_box.h * 0.20))):
        return None

    center_x = text_box.x + text_box.w / 2.0
    center_y = text_box.y + text_box.h / 2.0
    horizontal_touch = horizontal_overlap_fraction(text_box, figure_box)
    extended_left = figure_box.x - max(35, int(round(figure_box.w * 0.08)))
    extended_right = figure_box.x2 + max(35, int(round(figure_box.w * 0.08)))
    center_near_figure_x = extended_left <= center_x <= extended_right
    if horizontal_touch < 0.08 and not center_near_figure_x:
        return None

    margin_y = max(90 if figure_box.h < 140 else 50, int(round(figure_box.h * 0.13)))
    position = ""
    distance = 0
    if 0 <= text_box.y - figure_box.y2 <= margin_y:
        position = "below"
        distance = text_box.y - figure_box.y2
    elif 0 <= figure_box.y - text_box.y2 <= margin_y:
        position = "above"
        distance = figure_box.y - text_box.y2
    elif intersection_area(text_box, figure_box) / max(1, text_box.area) >= 0.40:
        bottom_band = center_y >= figure_box.y + figure_box.h * 0.70
        top_band = center_y <= figure_box.y + figure_box.h * 0.18
        left_band = center_x <= figure_box.x + figure_box.w * 0.40
        if bottom_band and left_band:
            position = "inside-bottom-left"
            distance = int(round(abs(figure_box.y2 - center_y)))
        elif top_band and left_band:
            position = "inside-top-left"
            distance = int(round(abs(center_y - figure_box.y)))
        else:
            return None
    else:
        return None

    score = 1.0 / (1.0 + distance)
    if position.startswith("inside"):
        score += 0.04
    if text_box.w <= figure_box.w * 0.25:
        score += 0.03
    if horizontal_touch >= 0.30:
        score += 0.02

    return {
        "block": text_block.ident,
        "bbox": text_block.bbox,
        "position": position,
        "score": round(score, 5),
    }


def internal_caption_probe_candidate(figure_block: Block) -> dict[str, object] | None:
    if figure_block.label not in {"schematic/circuit", "diagram"}:
        return None

    figure_box = box_from_list(figure_block.bbox)
    if figure_box.w < 80 or figure_box.h < 45:
        return None

    probe_w = min(figure_box.w, max(140, int(round(figure_box.w * 0.32))))
    probe_h = min(figure_box.h, max(36, int(round(figure_box.h * 0.075))))
    pad_x = max(6, int(round(figure_box.w * 0.015)))
    pad_bottom = max(6, int(round(figure_box.h * 0.018)))
    return {
        "block": "internal_caption_probe",
        "bbox": [figure_box.x + pad_x, figure_box.y2 - probe_h - pad_bottom, probe_w, probe_h],
        "position": "inside-bottom-left-probe",
        "score": 0.01,
    }


def attach_caption_candidates(blocks: list[Block], candidate_text_blocks: list[Block]) -> None:
    for figure_block in blocks:
        if figure_block.label not in FIGURE_LABELS:
            continue
        candidates = []
        for text_block in candidate_text_blocks:
            candidate = caption_candidate_for_figure(figure_block, text_block)
            if candidate is not None:
                candidates.append(candidate)
        candidates.sort(key=lambda item: (-float(item["score"]), str(item["block"])))
        if candidates:
            figure_block.caption_candidates = candidates[:4]
        else:
            fallback = internal_caption_probe_candidate(figure_block)
            if fallback is not None:
                figure_block.caption_candidates = [fallback]


def classify_blocks(
    image,
    boxes: list[Box],
    scale: float,
    save_crops: bool,
    page_dir: Path,
    accelerator: str = "cpu",
) -> list[Block]:
    analysis_h, analysis_w = image.shape[:2]
    accelerator = normalize_accelerator(accelerator)
    gray = grayscale_image(image, accelerator)
    mask, _, _ = foreground_mask(gray, accelerator)
    edges = canny_edges(gray, accelerator)
    ann = train_bootstrap_ann()

    classified: list[tuple[Block, Box]] = []
    counters: dict[str, int] = {}
    for index, box in enumerate(boxes, start=1):
        features = feature_dict(image, mask, edges, box)
        label, confidence = classify_features(ann, features)
        orientation = infer_orientation(features) if label == "text" else "unknown"
        counters[label] = counters.get(label, 0) + 1
        ident = f"{index:03d}_{safe_label(label)}"

        original_box = Box(
            int(round(box.x / scale)),
            int(round(box.y / scale)),
            int(round(box.w / scale)),
            int(round(box.h / scale)),
        )
        classified.append(
            (
                Block(
                    ident=ident,
                    label=label,
                    orientation=orientation,
                    confidence=round(confidence, 4),
                    bbox=original_box.to_list(),
                    outline=None,
                    features={key: round(float(value), 5) for key, value in features.items()},
                ),
                box,
            )
        )

    all_blocks = suppress_nested_text_blocks([block for block, _ in classified])
    assign_visual_outlines(all_blocks)
    blocks = suppress_text_inside_schematics(all_blocks)
    attach_caption_candidates(blocks, [block for block in all_blocks if block.label == "text"])
    kept_idents = {block.ident for block in blocks}
    if save_crops:
        blocks_dir = page_dir / "blocks"
        if blocks_dir.exists():
            shutil.rmtree(blocks_dir)
        for block, box in classified:
            if block.ident not in kept_idents:
                continue
            crop_dir = blocks_dir / safe_label(block.label)
            crop_path_obj = crop_dir / f"{block.ident}.png"
            crop = image[box.y : box.y2, box.x : box.x2]
            write_image(crop_path_obj, crop)
            block.crop_path = crop_path_obj.relative_to(page_dir).as_posix()

    return blocks


def draw_preview(image, blocks: list[Block], preview_width: int, page_dir: Path) -> Path:
    height, width = image.shape[:2]
    scale = min(1.0, preview_width / float(width))
    preview = image.copy() if scale >= 0.999 else cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
    preview_h, preview_w = preview.shape[:2]

    caption_boxes = caption_highlight_boxes(blocks)
    if caption_boxes:
        overlay = preview.copy()
        for caption_box in caption_boxes:
            x1 = max(0, int(round((caption_box.x - CAPTION_HIGHLIGHT_PADDING) * scale)))
            y1 = max(0, int(round((caption_box.y - CAPTION_HIGHLIGHT_PADDING) * scale)))
            x2 = min(preview_w, int(round((caption_box.x2 + CAPTION_HIGHLIGHT_PADDING) * scale)))
            y2 = min(preview_h, int(round((caption_box.y2 + CAPTION_HIGHLIGHT_PADDING) * scale)))
            if x2 > x1 and y2 > y1:
                cv2.rectangle(overlay, (x1, y1), (x2, y2), CAPTION_HIGHLIGHT_COLOR, -1)
        preview = cv2.addWeighted(overlay, CAPTION_HIGHLIGHT_OPACITY, preview, 1.0 - CAPTION_HIGHLIGHT_OPACITY, 0)

    for block in blocks:
        x, y, w, h = block.bbox
        x1 = int(round(x * scale))
        y1 = int(round(y * scale))
        x2 = int(round((x + w) * scale))
        y2 = int(round((y + h) * scale))
        color = CLASS_COLORS.get(block.label, CLASS_COLORS["other"])
        thickness = max(2, int(round(2 * scale)))
        if block.outline:
            for polygon in block.outline:
                points = np.array([[int(round(px * scale)), int(round(py * scale))] for px, py in polygon], dtype=np.int32)
                if points.shape[0] >= 3:
                    cv2.polylines(preview, [points], True, color, thickness)
        else:
            cv2.rectangle(preview, (x1, y1), (x2, y2), color, thickness)

        label = block_preview_label(block)
        (text_w, text_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 1)
        top = max(0, y1 - text_h - baseline - 5)
        cv2.rectangle(preview, (x1, top), (x1 + text_w + 6, top + text_h + baseline + 5), color, -1)
        cv2.putText(preview, label, (x1 + 3, top + text_h + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

    path = page_dir / "preview.png"
    write_image(path, preview)
    return path


def detect_page_layout(
    image_path: Path,
    out_dir: Path,
    max_analysis_side: int = 1800,
    preview_width: int = 1400,
    min_area_ratio: float = 0.00035,
    save_crops: bool = True,
    accelerator: str = "cpu",
) -> dict[str, object]:
    accelerator = configure_accelerator(accelerator)
    original = read_image(image_path)
    analysis_image, scale = resize_for_analysis(original, max_analysis_side, accelerator)
    page_name = image_path.stem
    page_dir = out_dir / page_name
    page_dir.mkdir(parents=True, exist_ok=True)

    boxes, metadata = detect_candidate_boxes(analysis_image, min_area_ratio=min_area_ratio, accelerator=accelerator)
    blocks = classify_blocks(analysis_image, boxes, scale=scale, save_crops=save_crops, page_dir=page_dir, accelerator=accelerator)
    preview_path = draw_preview(original, blocks, preview_width=preview_width, page_dir=page_dir)

    result = {
        "source": str(image_path),
        "page": page_name,
        "width": int(original.shape[1]),
        "height": int(original.shape[0]),
        "analysis_scale": scale,
        "classes": CLASS_NAMES,
        "metadata": metadata,
        "accelerator": accelerator,
        "preview": preview_path.relative_to(page_dir).as_posix(),
        "blocks": [asdict(block) for block in blocks],
    }
    (page_dir / "layout.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="Input page image.")
    parser.add_argument("--out-dir", default=".tmp/page_layout", help="Output root for layout JSON, crops and preview.")
    parser.add_argument("--max-analysis-side", type=int, default=1800, help="Largest side used during detection.")
    parser.add_argument("--preview-width", type=int, default=1400, help="Preview overlay width in pixels.")
    parser.add_argument("--min-area-ratio", type=float, default=0.00035, help="Smallest candidate block area relative to page.")
    parser.add_argument(
        "--accelerator",
        choices=ACCELERATOR_CHOICES,
        default="cpu",
        help="OpenCV acceleration backend. OpenCL falls back to CPU when unavailable.",
    )
    parser.add_argument("--no-crops", action="store_true", help="Do not write block crop images.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    require_dependencies()
    args = parse_args(argv)
    result = detect_page_layout(
        image_path=Path(args.image),
        out_dir=Path(args.out_dir),
        max_analysis_side=args.max_analysis_side,
        preview_width=args.preview_width,
        min_area_ratio=args.min_area_ratio,
        save_crops=not args.no_crops,
        accelerator=args.accelerator,
    )
    counts: dict[str, int] = {}
    for block in result["blocks"]:
        counts[block["label"]] = counts.get(block["label"], 0) + 1
    counts_text = ", ".join(f"{key}={value}" for key, value in sorted(counts.items())) or "none"
    print(f"Layout blocks: {len(result['blocks'])} ({counts_text})")
    print(Path(args.out_dir) / result["page"] / "layout.json")
    print(Path(args.out_dir) / result["page"] / result["preview"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
