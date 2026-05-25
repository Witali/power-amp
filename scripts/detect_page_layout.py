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
from typing import Callable, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.local_python_packages import add_local_python_packages  # type: ignore
except ImportError:
    from local_python_packages import add_local_python_packages  # type: ignore

add_local_python_packages(PROJECT_ROOT)

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore

    OPENCV_AVAILABLE = True
except ImportError:
    cv2 = None  # type: ignore
    np = None  # type: ignore
    OPENCV_AVAILABLE = False

try:
    from scripts import layout_frequency  # type: ignore
except ImportError:
    try:
        import layout_frequency  # type: ignore
    except ImportError:
        layout_frequency = None  # type: ignore

try:
    from scripts import layout_component_signatures  # type: ignore
except ImportError:
    try:
        import layout_component_signatures  # type: ignore
    except ImportError:
        layout_component_signatures = None  # type: ignore

try:
    from scripts import layout_config  # type: ignore
except ImportError:
    import layout_config  # type: ignore


CLASS_NAMES = layout_config.LAYOUT_CLASS_NAMES
TEXTUAL_LABELS = layout_config.TEXTUAL_LABELS
FIGURE_LABELS = layout_config.FIGURE_LABELS
CLASS_COLORS = layout_config.CLASS_COLORS_BGR
CAPTION_HIGHLIGHT_COLOR = layout_config.CAPTION_HIGHLIGHT_COLOR_BGR
CAPTION_HIGHLIGHT_OPACITY = layout_config.CAPTION_HIGHLIGHT_OPACITY
CAPTION_HIGHLIGHT_PADDING = layout_config.CAPTION_HIGHLIGHT_PADDING_PX
ACCELERATOR_CHOICES = layout_config.ACCELERATOR_CHOICES
FREQUENCY_HINT_CHOICES = layout_config.FREQUENCY_HINT_CHOICES
PCB_MIN_TRACE_DENSITY = layout_config.PCB_MIN_TRACE_DENSITY
PCB_MIN_SIGNATURE_SCORE = layout_config.PCB_MIN_SIGNATURE_SCORE
PCB_MIN_LINE_BALANCE = layout_config.PCB_MIN_LINE_BALANCE
PCB_MIN_AXIS_LINE_DENSITY = layout_config.PCB_MIN_AXIS_LINE_DENSITY
PCB_MIN_AREA_RATIO = layout_config.PCB_MIN_AREA_RATIO
PCB_MIN_HEIGHT_RATIO = layout_config.PCB_MIN_HEIGHT_RATIO
PCB_MAX_TEXT_SCORE = layout_config.PCB_MAX_TEXT_SCORE
PCB_MAX_INK_DENSITY = layout_config.PCB_MAX_INK_DENSITY
TEXT_COLUMN_SPLIT_MIN_WIDTH_RATIO = layout_config.TEXT_COLUMN_SPLIT_MIN_WIDTH_RATIO
TEXT_COLUMN_SPLIT_MIN_HEIGHT_RATIO = layout_config.TEXT_COLUMN_SPLIT_MIN_HEIGHT_RATIO
TEXT_COLUMN_SPLIT_MIN_ROW_RUNS = layout_config.TEXT_COLUMN_SPLIT_MIN_ROW_RUNS
TEXT_COLUMN_SPLIT_MIN_GAP_RATIO = layout_config.TEXT_COLUMN_SPLIT_MIN_GAP_RATIO
TEXT_COLUMN_SPLIT_MIN_GAP_PX = layout_config.TEXT_COLUMN_SPLIT_MIN_GAP_PX
TEXT_COLUMN_SPLIT_MIN_PIECE_WIDTH_RATIO = layout_config.TEXT_COLUMN_SPLIT_MIN_PIECE_WIDTH_RATIO
TEXT_COLUMN_SPLIT_MAX_PIECES = layout_config.TEXT_COLUMN_SPLIT_MAX_PIECES
TEXT_COLUMN_FALLBACK_MIN_WIDTH_RATIO = layout_config.TEXT_COLUMN_FALLBACK_MIN_WIDTH_RATIO
TEXT_COLUMN_FALLBACK_MIN_HEIGHT_RATIO = layout_config.TEXT_COLUMN_FALLBACK_MIN_HEIGHT_RATIO
TEXT_COLUMN_FALLBACK_MAX_PROJECTION_DENSITY = layout_config.TEXT_COLUMN_FALLBACK_MAX_PROJECTION_DENSITY
TEXT_COLUMN_FALLBACK_MIN_GAP_RATIO = layout_config.TEXT_COLUMN_FALLBACK_MIN_GAP_RATIO
TEXT_COLUMN_FALLBACK_MIN_GAP_PX = layout_config.TEXT_COLUMN_FALLBACK_MIN_GAP_PX
HORIZONTAL_GAP_SPLIT_MIN_WIDTH_RATIO = layout_config.HORIZONTAL_GAP_SPLIT_MIN_WIDTH_RATIO
HORIZONTAL_GAP_SPLIT_MIN_HEIGHT_RATIO = layout_config.HORIZONTAL_GAP_SPLIT_MIN_HEIGHT_RATIO
HORIZONTAL_GAP_SPLIT_MIN_GAP_RATIO = layout_config.HORIZONTAL_GAP_SPLIT_MIN_GAP_RATIO
HORIZONTAL_GAP_SPLIT_MIN_GAP_PX = layout_config.HORIZONTAL_GAP_SPLIT_MIN_GAP_PX
HORIZONTAL_GAP_SPLIT_MIN_PIECE_HEIGHT_RATIO = layout_config.HORIZONTAL_GAP_SPLIT_MIN_PIECE_HEIGHT_RATIO
HORIZONTAL_GAP_SPLIT_EDGE_SKIP_RATIO = layout_config.HORIZONTAL_GAP_SPLIT_EDGE_SKIP_RATIO
HORIZONTAL_GAP_SPLIT_MAX_PIECES = layout_config.HORIZONTAL_GAP_SPLIT_MAX_PIECES
TEXT_ARTIFACT_VISUAL_LABELS = layout_config.TEXT_ARTIFACT_VISUAL_LABELS
TEXT_ARTIFACT_MAX_AREA_RATIO = layout_config.TEXT_ARTIFACT_MAX_AREA_RATIO
TEXT_ARTIFACT_MAX_HEIGHT_PX = layout_config.TEXT_ARTIFACT_MAX_HEIGHT_PX
TEXT_ARTIFACT_MAX_HEIGHT_RATIO = layout_config.TEXT_ARTIFACT_MAX_HEIGHT_RATIO
TEXT_ARTIFACT_MAX_WIDTH_RATIO = layout_config.TEXT_ARTIFACT_MAX_WIDTH_RATIO
TEXT_ARTIFACT_TOUCH_MARGIN_RATIO = layout_config.TEXT_ARTIFACT_TOUCH_MARGIN_RATIO
TEXT_ARTIFACT_MIN_OVERLAP_RATIO = layout_config.TEXT_ARTIFACT_MIN_OVERLAP_RATIO
TEXT_MIN_GLYPH_WIDTHS = layout_config.TEXT_MIN_GLYPH_WIDTHS
TEXT_AVERAGE_GLYPH_WIDTH_TO_HEIGHT = layout_config.TEXT_AVERAGE_GLYPH_WIDTH_TO_HEIGHT
TEXT_MIN_ABSOLUTE_WIDTH_PX = layout_config.TEXT_MIN_ABSOLUTE_WIDTH_PX
TEXT_MIN_ABSOLUTE_HEIGHT_PX = layout_config.TEXT_MIN_ABSOLUTE_HEIGHT_PX
TEXT_FRAGMENT_SUPPRESS_INSIDE_VISUALS = layout_config.TEXT_FRAGMENT_SUPPRESS_INSIDE_VISUALS
TEXT_FRAGMENT_INSIDE_VISUAL_MIN_OVERLAP_RATIO = layout_config.TEXT_FRAGMENT_INSIDE_VISUAL_MIN_OVERLAP_RATIO
TEXT_FRAGMENT_INSIDE_VISUAL_MAX_GLYPH_WIDTHS = layout_config.TEXT_FRAGMENT_INSIDE_VISUAL_MAX_GLYPH_WIDTHS
TEXT_DENSE_MULTILINE_MIN_WIDTH_MULTIPLIER = layout_config.TEXT_DENSE_MULTILINE_MIN_WIDTH_MULTIPLIER
TEXT_DENSE_MULTILINE_MIN_HEIGHT_MULTIPLIER = layout_config.TEXT_DENSE_MULTILINE_MIN_HEIGHT_MULTIPLIER
TEXT_DENSE_MULTILINE_LARGE_WIDTH_MULTIPLIER = layout_config.TEXT_DENSE_MULTILINE_LARGE_WIDTH_MULTIPLIER
TEXT_DENSE_MULTILINE_LARGE_HEIGHT_MULTIPLIER = layout_config.TEXT_DENSE_MULTILINE_LARGE_HEIGHT_MULTIPLIER
TEXT_DENSE_MULTILINE_MIN_INK_DENSITY = layout_config.TEXT_DENSE_MULTILINE_MIN_INK_DENSITY
TEXT_DENSE_MULTILINE_MAX_AXIS_LINE_DENSITY = layout_config.TEXT_DENSE_MULTILINE_MAX_AXIS_LINE_DENSITY
TEXT_DENSE_MULTILINE_MAX_LINE_BALANCE = layout_config.TEXT_DENSE_MULTILINE_MAX_LINE_BALANCE
TEXT_DENSE_MULTILINE_MAX_SATURATION = layout_config.TEXT_DENSE_MULTILINE_MAX_SATURATION
TEXT_DENSE_MULTILINE_MIN_TEXT_SCORE = layout_config.TEXT_DENSE_MULTILINE_MIN_TEXT_SCORE
TEXT_DENSE_MULTILINE_MIN_TEXTLINE_DENSITY = layout_config.TEXT_DENSE_MULTILINE_MIN_TEXTLINE_DENSITY
TEXT_DENSE_MULTILINE_COLOR_MIN_TEXT_SCORE = layout_config.TEXT_DENSE_MULTILINE_COLOR_MIN_TEXT_SCORE
TEXT_DENSE_MULTILINE_COLOR_MIN_TEXTLINE_DENSITY = layout_config.TEXT_DENSE_MULTILINE_COLOR_MIN_TEXTLINE_DENSITY
TEXT_DENSE_MULTILINE_COLOR_MAX_SATURATION = layout_config.TEXT_DENSE_MULTILINE_COLOR_MAX_SATURATION
SCHEMATIC_TEXT_LABEL_MAX_AREA_RATIO = layout_config.SCHEMATIC_TEXT_LABEL_MAX_AREA_RATIO
SCHEMATIC_TEXT_LABEL_MAX_HEIGHT_RATIO = layout_config.SCHEMATIC_TEXT_LABEL_MAX_HEIGHT_RATIO
SCHEMATIC_TEXT_LABEL_MAX_WIDTH_RATIO = layout_config.SCHEMATIC_TEXT_LABEL_MAX_WIDTH_RATIO
SCHEMATIC_TEXT_LABEL_TOUCH_MARGIN_RATIO = layout_config.SCHEMATIC_TEXT_LABEL_TOUCH_MARGIN_RATIO
SCHEMATIC_TEXT_LABEL_TOUCH_OVERLAP_RATIO = layout_config.SCHEMATIC_TEXT_LABEL_TOUCH_OVERLAP_RATIO
SCHEMATIC_TEXT_LABEL_INSIDE_OVERLAP_RATIO = layout_config.SCHEMATIC_TEXT_LABEL_INSIDE_OVERLAP_RATIO
SCHEMATIC_TEXT_LABEL_MIN_VERTICAL_OVERLAP_RATIO = layout_config.SCHEMATIC_TEXT_LABEL_MIN_VERTICAL_OVERLAP_RATIO
SCHEMATIC_TEXT_LABEL_MIN_TEXT_SCORE = layout_config.SCHEMATIC_TEXT_LABEL_MIN_TEXT_SCORE
SCHEMATIC_TEXT_LABEL_MAX_SATURATION = layout_config.SCHEMATIC_TEXT_LABEL_MAX_SATURATION
SCHEMATIC_HEADING_LABEL_MAX_AREA_RATIO = layout_config.SCHEMATIC_HEADING_LABEL_MAX_AREA_RATIO
SCHEMATIC_HEADING_LABEL_MAX_HEIGHT_RATIO = layout_config.SCHEMATIC_HEADING_LABEL_MAX_HEIGHT_RATIO
SCHEMATIC_HEADING_LABEL_MAX_WIDTH_RATIO = layout_config.SCHEMATIC_HEADING_LABEL_MAX_WIDTH_RATIO
SCHEMATIC_HEADING_LABEL_MIN_TEXT_SCORE = layout_config.SCHEMATIC_HEADING_LABEL_MIN_TEXT_SCORE
SCHEMATIC_HEADING_LABEL_MAX_INK_DENSITY = layout_config.SCHEMATIC_HEADING_LABEL_MAX_INK_DENSITY
SCHEMATIC_HEADING_LABEL_MIN_HLINE_DENSITY = layout_config.SCHEMATIC_HEADING_LABEL_MIN_HLINE_DENSITY
SCHEMATIC_HEADING_LABEL_MAX_SATURATION = layout_config.SCHEMATIC_HEADING_LABEL_MAX_SATURATION
SCHEMATIC_HEADING_LABEL_INSIDE_OVERLAP_RATIO = layout_config.SCHEMATIC_HEADING_LABEL_INSIDE_OVERLAP_RATIO
HEADING_MIN_WIDTH_RATIO = layout_config.HEADING_MIN_WIDTH_RATIO
HEADING_MAX_HEIGHT_RATIO = layout_config.HEADING_MAX_HEIGHT_RATIO
HEADING_MAX_AREA_RATIO = layout_config.HEADING_MAX_AREA_RATIO
HEADING_MIN_WIDE_ASPECT = layout_config.HEADING_MIN_WIDE_ASPECT
HEADING_MIN_TEXT_SCORE = layout_config.HEADING_MIN_TEXT_SCORE
HEADING_MAX_TEXT_SCORE = layout_config.HEADING_MAX_TEXT_SCORE
HEADING_MIN_INK_DENSITY = layout_config.HEADING_MIN_INK_DENSITY
HEADING_MIN_GRAY_STD = layout_config.HEADING_MIN_GRAY_STD
HEADING_MAX_LINE_BALANCE = layout_config.HEADING_MAX_LINE_BALANCE
HEADING_MIN_COMPONENT_DENSITY = layout_config.HEADING_MIN_COMPONENT_DENSITY
HORIZONTAL_RULE_MIN_WIDTH_RATIO = layout_config.HORIZONTAL_RULE_MIN_WIDTH_RATIO
HORIZONTAL_RULE_MAX_HEIGHT_RATIO = layout_config.HORIZONTAL_RULE_MAX_HEIGHT_RATIO
HORIZONTAL_RULE_MAX_AREA_RATIO = layout_config.HORIZONTAL_RULE_MAX_AREA_RATIO
HORIZONTAL_RULE_MIN_HLINE_DENSITY = layout_config.HORIZONTAL_RULE_MIN_HLINE_DENSITY
HORIZONTAL_RULE_MAX_VLINE_DENSITY = layout_config.HORIZONTAL_RULE_MAX_VLINE_DENSITY
HORIZONTAL_RULE_MIN_LINE_ART = layout_config.HORIZONTAL_RULE_MIN_LINE_ART
HORIZONTAL_RULE_MAX_COMPONENT_DENSITY = layout_config.HORIZONTAL_RULE_MAX_COMPONENT_DENSITY
HORIZONTAL_RULE_MAX_COMPONENT_SIGNATURE = layout_config.HORIZONTAL_RULE_MAX_COMPONENT_SIGNATURE
WAVEFORM_DIAGRAM_MIN_AREA_RATIO = layout_config.WAVEFORM_DIAGRAM_MIN_AREA_RATIO
WAVEFORM_DIAGRAM_MAX_HEIGHT_RATIO = layout_config.WAVEFORM_DIAGRAM_MAX_HEIGHT_RATIO
WAVEFORM_DIAGRAM_MIN_HLINE_DENSITY = layout_config.WAVEFORM_DIAGRAM_MIN_HLINE_DENSITY
WAVEFORM_DIAGRAM_MAX_VLINE_DENSITY = layout_config.WAVEFORM_DIAGRAM_MAX_VLINE_DENSITY
WAVEFORM_DIAGRAM_MIN_LINE_ART = layout_config.WAVEFORM_DIAGRAM_MIN_LINE_ART
WAVEFORM_DIAGRAM_MIN_TEXT_SCORE = layout_config.WAVEFORM_DIAGRAM_MIN_TEXT_SCORE
WAVEFORM_DIAGRAM_MAX_SATURATION = layout_config.WAVEFORM_DIAGRAM_MAX_SATURATION
WAVEFORM_DIAGRAM_MAX_INK_DENSITY = layout_config.WAVEFORM_DIAGRAM_MAX_INK_DENSITY
WIDE_RULE_HEADING_MIN_WIDTH_RATIO = layout_config.WIDE_RULE_HEADING_MIN_WIDTH_RATIO
WIDE_RULE_HEADING_MAX_HEIGHT_RATIO = layout_config.WIDE_RULE_HEADING_MAX_HEIGHT_RATIO
WIDE_RULE_HEADING_MAX_AREA_RATIO = layout_config.WIDE_RULE_HEADING_MAX_AREA_RATIO
WIDE_RULE_HEADING_MIN_TEXT_SCORE = layout_config.WIDE_RULE_HEADING_MIN_TEXT_SCORE
WIDE_RULE_HEADING_MIN_TEXTLINE_DENSITY = layout_config.WIDE_RULE_HEADING_MIN_TEXTLINE_DENSITY
WIDE_RULE_HEADING_MIN_INK_DENSITY = layout_config.WIDE_RULE_HEADING_MIN_INK_DENSITY
BOLD_DISPLAY_HEADING_MIN_WIDTH_RATIO = layout_config.BOLD_DISPLAY_HEADING_MIN_WIDTH_RATIO
BOLD_DISPLAY_HEADING_MIN_HEIGHT_RATIO = layout_config.BOLD_DISPLAY_HEADING_MIN_HEIGHT_RATIO
BOLD_DISPLAY_HEADING_MAX_HEIGHT_RATIO = layout_config.BOLD_DISPLAY_HEADING_MAX_HEIGHT_RATIO
BOLD_DISPLAY_HEADING_MAX_AREA_RATIO = layout_config.BOLD_DISPLAY_HEADING_MAX_AREA_RATIO
BOLD_DISPLAY_HEADING_MIN_INK_DENSITY = layout_config.BOLD_DISPLAY_HEADING_MIN_INK_DENSITY
BOLD_DISPLAY_HEADING_MIN_GRAY_STD = layout_config.BOLD_DISPLAY_HEADING_MIN_GRAY_STD
BOLD_DISPLAY_HEADING_MAX_TEXT_SCORE = layout_config.BOLD_DISPLAY_HEADING_MAX_TEXT_SCORE
BOLD_DISPLAY_HEADING_MIN_COMPONENT_DENSITY = layout_config.BOLD_DISPLAY_HEADING_MIN_COMPONENT_DENSITY
BOLD_DISPLAY_HEADING_MAX_HLINE_DENSITY = layout_config.BOLD_DISPLAY_HEADING_MAX_HLINE_DENSITY
BOLD_DISPLAY_HEADING_MAX_LINE_BALANCE = layout_config.BOLD_DISPLAY_HEADING_MAX_LINE_BALANCE
BOLD_DISPLAY_HEADING_MAX_SATURATION = layout_config.BOLD_DISPLAY_HEADING_MAX_SATURATION
MONOCHROME_ICON_IMAGE_MIN_AREA_RATIO = layout_config.MONOCHROME_ICON_IMAGE_MIN_AREA_RATIO
MONOCHROME_ICON_IMAGE_MIN_INK_DENSITY = layout_config.MONOCHROME_ICON_IMAGE_MIN_INK_DENSITY
MONOCHROME_ICON_IMAGE_MIN_EDGE_DENSITY = layout_config.MONOCHROME_ICON_IMAGE_MIN_EDGE_DENSITY
MONOCHROME_ICON_IMAGE_MIN_GRAY_STD = layout_config.MONOCHROME_ICON_IMAGE_MIN_GRAY_STD
MONOCHROME_ICON_IMAGE_MAX_COMPONENT_DENSITY = layout_config.MONOCHROME_ICON_IMAGE_MAX_COMPONENT_DENSITY
MONOCHROME_ICON_IMAGE_MAX_COMPONENT_SIGNATURE = layout_config.MONOCHROME_ICON_IMAGE_MAX_COMPONENT_SIGNATURE
MONOCHROME_ICON_IMAGE_MAX_TEXT_SCORE = layout_config.MONOCHROME_ICON_IMAGE_MAX_TEXT_SCORE
CAPTIONED_SCHEMATIC_MIN_AREA_RATIO = layout_config.CAPTIONED_SCHEMATIC_MIN_AREA_RATIO
CAPTIONED_SCHEMATIC_MAX_AREA_RATIO = layout_config.CAPTIONED_SCHEMATIC_MAX_AREA_RATIO
CAPTIONED_SCHEMATIC_MIN_HEIGHT_RATIO = layout_config.CAPTIONED_SCHEMATIC_MIN_HEIGHT_RATIO
CAPTIONED_SCHEMATIC_MAX_INK_DENSITY = layout_config.CAPTIONED_SCHEMATIC_MAX_INK_DENSITY
CAPTIONED_SCHEMATIC_MIN_EDGE_DENSITY = layout_config.CAPTIONED_SCHEMATIC_MIN_EDGE_DENSITY
CAPTIONED_SCHEMATIC_MIN_LINE_ART = layout_config.CAPTIONED_SCHEMATIC_MIN_LINE_ART
CAPTIONED_SCHEMATIC_MIN_VLINE_DENSITY = layout_config.CAPTIONED_SCHEMATIC_MIN_VLINE_DENSITY
CAPTIONED_SCHEMATIC_MAX_TEXT_SCORE = layout_config.CAPTIONED_SCHEMATIC_MAX_TEXT_SCORE
CAPTIONED_SCHEMATIC_MIN_COMPONENT_SIGNATURE = layout_config.CAPTIONED_SCHEMATIC_MIN_COMPONENT_SIGNATURE
CAPTIONED_SCHEMATIC_MAX_SATURATION = layout_config.CAPTIONED_SCHEMATIC_MAX_SATURATION
HEADING_FRAGMENT_MERGE_MAX_HEIGHT_RATIO = layout_config.HEADING_FRAGMENT_MERGE_MAX_HEIGHT_RATIO
HEADING_FRAGMENT_MERGE_MAX_WIDTH_RATIO = layout_config.HEADING_FRAGMENT_MERGE_MAX_WIDTH_RATIO
HEADING_FRAGMENT_MERGE_MIN_TOP_RATIO = layout_config.HEADING_FRAGMENT_MERGE_MIN_TOP_RATIO
HEADING_FRAGMENT_STACKED_MAX_VERTICAL_GAP_PX = layout_config.HEADING_FRAGMENT_STACKED_MAX_VERTICAL_GAP_PX
HEADING_FRAGMENT_STACKED_MAX_VERTICAL_GAP_RATIO = layout_config.HEADING_FRAGMENT_STACKED_MAX_VERTICAL_GAP_RATIO
HEADING_FRAGMENT_STACKED_MIN_HORIZONTAL_OVERLAP = layout_config.HEADING_FRAGMENT_STACKED_MIN_HORIZONTAL_OVERLAP
HEADING_FRAGMENT_STACKED_MAX_X_DRIFT_PX = layout_config.HEADING_FRAGMENT_STACKED_MAX_X_DRIFT_PX
HEADING_FRAGMENT_STACKED_MAX_X_DRIFT_RATIO = layout_config.HEADING_FRAGMENT_STACKED_MAX_X_DRIFT_RATIO
HEADING_FRAGMENT_INLINE_MIN_VERTICAL_OVERLAP = layout_config.HEADING_FRAGMENT_INLINE_MIN_VERTICAL_OVERLAP
HEADING_FRAGMENT_INLINE_MAX_CENTER_DELTA_RATIO = layout_config.HEADING_FRAGMENT_INLINE_MAX_CENTER_DELTA_RATIO
HEADING_FRAGMENT_INLINE_MAX_HORIZONTAL_GAP_PX = layout_config.HEADING_FRAGMENT_INLINE_MAX_HORIZONTAL_GAP_PX
HEADING_FRAGMENT_INLINE_MAX_HORIZONTAL_GAP_RATIO = layout_config.HEADING_FRAGMENT_INLINE_MAX_HORIZONTAL_GAP_RATIO
INTERNAL_DISPLAY_HEADING_MIN_WIDTH_RATIO = layout_config.INTERNAL_DISPLAY_HEADING_MIN_WIDTH_RATIO
INTERNAL_DISPLAY_HEADING_MIN_HEIGHT_RATIO = layout_config.INTERNAL_DISPLAY_HEADING_MIN_HEIGHT_RATIO
INTERNAL_DISPLAY_HEADING_MIN_AREA_RATIO = layout_config.INTERNAL_DISPLAY_HEADING_MIN_AREA_RATIO
INTERNAL_DISPLAY_HEADING_PROJECTION_MIN_PX = layout_config.INTERNAL_DISPLAY_HEADING_PROJECTION_MIN_PX
INTERNAL_DISPLAY_HEADING_PROJECTION_WIDTH_RATIO = layout_config.INTERNAL_DISPLAY_HEADING_PROJECTION_WIDTH_RATIO
INTERNAL_DISPLAY_HEADING_MIN_RUN_PX = layout_config.INTERNAL_DISPLAY_HEADING_MIN_RUN_PX
INTERNAL_DISPLAY_HEADING_MIN_RUN_HEIGHT_RATIO = layout_config.INTERNAL_DISPLAY_HEADING_MIN_RUN_HEIGHT_RATIO
INTERNAL_DISPLAY_HEADING_TOP_SKIP_RATIO = layout_config.INTERNAL_DISPLAY_HEADING_TOP_SKIP_RATIO
INTERNAL_DISPLAY_HEADING_TOP_TEXT_MIN_PX = layout_config.INTERNAL_DISPLAY_HEADING_TOP_TEXT_MIN_PX
INTERNAL_DISPLAY_HEADING_TOP_TEXT_MIN_RATIO = layout_config.INTERNAL_DISPLAY_HEADING_TOP_TEXT_MIN_RATIO
INTERNAL_DISPLAY_HEADING_MIN_TEXT_PX = layout_config.INTERNAL_DISPLAY_HEADING_MIN_TEXT_PX
INTERNAL_DISPLAY_HEADING_MIN_TEXT_HEIGHT_RATIO = layout_config.INTERNAL_DISPLAY_HEADING_MIN_TEXT_HEIGHT_RATIO
INTERNAL_DISPLAY_HEADING_SCORE_GRAY_STD_WEIGHT = layout_config.INTERNAL_DISPLAY_HEADING_SCORE_GRAY_STD_WEIGHT
TOP_DISPLAY_HEADING_MIN_CONTAINER_WIDTH_RATIO = layout_config.TOP_DISPLAY_HEADING_MIN_CONTAINER_WIDTH_RATIO
TOP_DISPLAY_HEADING_MIN_CONTAINER_HEIGHT_RATIO = layout_config.TOP_DISPLAY_HEADING_MIN_CONTAINER_HEIGHT_RATIO
TOP_DISPLAY_HEADING_SCAN_HEIGHT_RATIO = layout_config.TOP_DISPLAY_HEADING_SCAN_HEIGHT_RATIO
TOP_DISPLAY_HEADING_MIN_RUN_PX = layout_config.TOP_DISPLAY_HEADING_MIN_RUN_PX
TOP_DISPLAY_HEADING_MIN_RUN_HEIGHT_RATIO = layout_config.TOP_DISPLAY_HEADING_MIN_RUN_HEIGHT_RATIO
TOP_DISPLAY_HEADING_MAX_TOP_OFFSET_PX = layout_config.TOP_DISPLAY_HEADING_MAX_TOP_OFFSET_PX
TOP_DISPLAY_HEADING_MAX_TOP_OFFSET_RATIO = layout_config.TOP_DISPLAY_HEADING_MAX_TOP_OFFSET_RATIO
TOP_DISPLAY_HEADING_MAX_RUN_GAP_PX = layout_config.TOP_DISPLAY_HEADING_MAX_RUN_GAP_PX
TOP_DISPLAY_HEADING_MAX_RUN_GAP_RATIO = layout_config.TOP_DISPLAY_HEADING_MAX_RUN_GAP_RATIO
TOP_DISPLAY_HEADING_MIN_HEIGHT_RATIO = layout_config.TOP_DISPLAY_HEADING_MIN_HEIGHT_RATIO
TOP_DISPLAY_HEADING_MIN_AREA_RATIO = layout_config.TOP_DISPLAY_HEADING_MIN_AREA_RATIO
TOP_DISPLAY_HEADING_MAX_HLINE_DENSITY = layout_config.TOP_DISPLAY_HEADING_MAX_HLINE_DENSITY
WEAK_HEADING_ARTIFACT_MAX_CONFIDENCE = layout_config.WEAK_HEADING_ARTIFACT_MAX_CONFIDENCE
WEAK_HEADING_ARTIFACT_MIN_WIDTH_RATIO = layout_config.WEAK_HEADING_ARTIFACT_MIN_WIDTH_RATIO
WEAK_HEADING_ARTIFACT_MAX_HEIGHT_RATIO = layout_config.WEAK_HEADING_ARTIFACT_MAX_HEIGHT_RATIO
WEAK_HEADING_ARTIFACT_MAX_INK_DENSITY = layout_config.WEAK_HEADING_ARTIFACT_MAX_INK_DENSITY
WEAK_HEADING_ARTIFACT_MAX_EDGE_DENSITY = layout_config.WEAK_HEADING_ARTIFACT_MAX_EDGE_DENSITY
WEAK_HEADING_ARTIFACT_MAX_LINE_ART = layout_config.WEAK_HEADING_ARTIFACT_MAX_LINE_ART
WEAK_HEADING_ARTIFACT_MAX_TEXT_SCORE = layout_config.WEAK_HEADING_ARTIFACT_MAX_TEXT_SCORE
ILLUSTRATION_TEXT_REJECT_MIN_CONFIDENCE = layout_config.ILLUSTRATION_TEXT_REJECT_MIN_CONFIDENCE
ILLUSTRATION_TEXT_REJECT_MIN_TEXT_SCORE = layout_config.ILLUSTRATION_TEXT_REJECT_MIN_TEXT_SCORE
ILLUSTRATION_TEXT_REJECT_MIN_HEIGHT_RATIO = layout_config.ILLUSTRATION_TEXT_REJECT_MIN_HEIGHT_RATIO
ILLUSTRATION_TEXT_REJECT_MAX_LINE_ART = layout_config.ILLUSTRATION_TEXT_REJECT_MAX_LINE_ART
ILLUSTRATION_TEXT_REJECT_MAX_HLINE = layout_config.ILLUSTRATION_TEXT_REJECT_MAX_HLINE
ILLUSTRATION_TEXT_REJECT_MAX_VLINE = layout_config.ILLUSTRATION_TEXT_REJECT_MAX_VLINE
STACKED_DIAGRAM_MIN_AXIS_LINE_DENSITY = layout_config.STACKED_DIAGRAM_MIN_AXIS_LINE_DENSITY
STACKED_DIAGRAM_MIN_SINGLE_AXIS_LINE_DENSITY = layout_config.STACKED_DIAGRAM_MIN_SINGLE_AXIS_LINE_DENSITY
STACKED_DIAGRAM_MIN_LINE_ART_WITH_SINGLE_AXIS = layout_config.STACKED_DIAGRAM_MIN_LINE_ART_WITH_SINGLE_AXIS
VISUAL_WRAPPER_MIN_INNER_OVERLAP = layout_config.VISUAL_WRAPPER_MIN_INNER_OVERLAP
VISUAL_WRAPPER_MIN_CONFIDENCE_DELTA = layout_config.VISUAL_WRAPPER_MIN_CONFIDENCE_DELTA
VISUAL_WRAPPER_MIN_OUTER_AREA_RATIO = layout_config.VISUAL_WRAPPER_MIN_OUTER_AREA_RATIO
OVERLAP_DIAGRAM_MIN_LINE_ART = layout_config.OVERLAP_DIAGRAM_MIN_LINE_ART
OVERLAP_DIAGRAM_MIN_AXIS_DENSITY = layout_config.OVERLAP_DIAGRAM_MIN_AXIS_DENSITY
OVERLAP_DIAGRAM_LINE_ART_BOOST = layout_config.OVERLAP_DIAGRAM_LINE_ART_BOOST
OVERLAP_DIAGRAM_STACKED_MERGE_BOOST = layout_config.OVERLAP_DIAGRAM_STACKED_MERGE_BOOST
OVERLAP_TEXT_LINE_ART_PENALTY = layout_config.OVERLAP_TEXT_LINE_ART_PENALTY
STACKED_DIAGRAM_TEXT_CUTOUT_MIN_MERGE_SCORE = layout_config.STACKED_DIAGRAM_TEXT_CUTOUT_MIN_MERGE_SCORE
WAVEFORM_IMAGE_PROMOTE_MIN_WIDTH_RATIO = layout_config.WAVEFORM_IMAGE_PROMOTE_MIN_WIDTH_RATIO
WAVEFORM_IMAGE_PROMOTE_MAX_HEIGHT_RATIO = layout_config.WAVEFORM_IMAGE_PROMOTE_MAX_HEIGHT_RATIO
WAVEFORM_IMAGE_PROMOTE_MIN_AREA_RATIO = layout_config.WAVEFORM_IMAGE_PROMOTE_MIN_AREA_RATIO
WAVEFORM_IMAGE_PROMOTE_MAX_AREA_RATIO = layout_config.WAVEFORM_IMAGE_PROMOTE_MAX_AREA_RATIO
WAVEFORM_IMAGE_PROMOTE_MIN_WIDE_ASPECT = layout_config.WAVEFORM_IMAGE_PROMOTE_MIN_WIDE_ASPECT
WAVEFORM_IMAGE_PROMOTE_MIN_LINE_ART = layout_config.WAVEFORM_IMAGE_PROMOTE_MIN_LINE_ART
WAVEFORM_IMAGE_PROMOTE_MIN_AXIS_DENSITY = layout_config.WAVEFORM_IMAGE_PROMOTE_MIN_AXIS_DENSITY
WAVEFORM_IMAGE_PROMOTE_MIN_EDGE_DENSITY = layout_config.WAVEFORM_IMAGE_PROMOTE_MIN_EDGE_DENSITY
WAVEFORM_IMAGE_PROMOTE_MAX_INK_DENSITY = layout_config.WAVEFORM_IMAGE_PROMOTE_MAX_INK_DENSITY
WAVEFORM_IMAGE_PROMOTE_MAX_SATURATION = layout_config.WAVEFORM_IMAGE_PROMOTE_MAX_SATURATION
WAVEFORM_IMAGE_PROMOTE_MIN_COMPONENT_SIGNATURE = layout_config.WAVEFORM_IMAGE_PROMOTE_MIN_COMPONENT_SIGNATURE
CONTENTS_ROW_MERGE_MIN_RUN = layout_config.CONTENTS_ROW_MERGE_MIN_RUN
CONTENTS_ROW_MERGE_MAX_HEIGHT_RATIO = layout_config.CONTENTS_ROW_MERGE_MAX_HEIGHT_RATIO
CONTENTS_ROW_MERGE_MIN_WIDTH_RATIO = layout_config.CONTENTS_ROW_MERGE_MIN_WIDTH_RATIO
CONTENTS_ROW_MERGE_MIN_WIDTH_SIMILARITY = layout_config.CONTENTS_ROW_MERGE_MIN_WIDTH_SIMILARITY
CONTENTS_ROW_MERGE_MIN_HORIZONTAL_OVERLAP = layout_config.CONTENTS_ROW_MERGE_MIN_HORIZONTAL_OVERLAP
CONTENTS_ROW_MERGE_MAX_VERTICAL_GAP_RATIO = layout_config.CONTENTS_ROW_MERGE_MAX_VERTICAL_GAP_RATIO
CONTENTS_ROW_MERGE_MAX_VERTICAL_GAP_PX = layout_config.CONTENTS_ROW_MERGE_MAX_VERTICAL_GAP_PX
CONTENTS_ROW_MERGE_MIN_TOTAL_HEIGHT_RATIO = layout_config.CONTENTS_ROW_MERGE_MIN_TOTAL_HEIGHT_RATIO
CONTENTS_ROW_MERGE_MAX_TOTAL_HEIGHT_RATIO = layout_config.CONTENTS_ROW_MERGE_MAX_TOTAL_HEIGHT_RATIO
CONTENTS_COLUMN_MERGE_MIN_WIDTH_RATIO = layout_config.CONTENTS_COLUMN_MERGE_MIN_WIDTH_RATIO
CONTENTS_COLUMN_MERGE_MAX_WIDTH_RATIO = layout_config.CONTENTS_COLUMN_MERGE_MAX_WIDTH_RATIO
CONTENTS_COLUMN_MERGE_MIN_WIDTH_SIMILARITY = layout_config.CONTENTS_COLUMN_MERGE_MIN_WIDTH_SIMILARITY
CONTENTS_COLUMN_MERGE_MIN_HORIZONTAL_OVERLAP = layout_config.CONTENTS_COLUMN_MERGE_MIN_HORIZONTAL_OVERLAP
CONTENTS_COLUMN_MERGE_MAX_VERTICAL_GAP_RATIO = layout_config.CONTENTS_COLUMN_MERGE_MAX_VERTICAL_GAP_RATIO
CONTENTS_COLUMN_MERGE_MAX_VERTICAL_GAP_PX = layout_config.CONTENTS_COLUMN_MERGE_MAX_VERTICAL_GAP_PX
CONTENTS_COLUMN_SPLIT_MIN_WIDTH_RATIO = layout_config.CONTENTS_COLUMN_SPLIT_MIN_WIDTH_RATIO
CONTENTS_COLUMN_SPLIT_MIN_HEIGHT_RATIO = layout_config.CONTENTS_COLUMN_SPLIT_MIN_HEIGHT_RATIO
CONTENTS_COLUMN_SPLIT_MIN_GAP_RATIO = layout_config.CONTENTS_COLUMN_SPLIT_MIN_GAP_RATIO
CONTENTS_COLUMN_SPLIT_MIN_GAP_PX = layout_config.CONTENTS_COLUMN_SPLIT_MIN_GAP_PX
CONTENTS_COLUMN_SPLIT_MAX_PROJECTION_DENSITY = layout_config.CONTENTS_COLUMN_SPLIT_MAX_PROJECTION_DENSITY
CONTENTS_COLUMN_SPLIT_MIN_PIECE_WIDTH_RATIO = layout_config.CONTENTS_COLUMN_SPLIT_MIN_PIECE_WIDTH_RATIO
CONTENTS_COLUMN_GRID_SNAP_MIN_TOTAL_WIDTH_RATIO = layout_config.CONTENTS_COLUMN_GRID_SNAP_MIN_TOTAL_WIDTH_RATIO
CONTENTS_COLUMN_GRID_SNAP_MIN_HEIGHT_RATIO = layout_config.CONTENTS_COLUMN_GRID_SNAP_MIN_HEIGHT_RATIO
CONTENTS_COLUMN_GRID_SNAP_MAX_COLUMNS = layout_config.CONTENTS_COLUMN_GRID_SNAP_MAX_COLUMNS
CONTENTS_COLUMN_GRID_SNAP_EDGE_TOLERANCE_RATIO = layout_config.CONTENTS_COLUMN_GRID_SNAP_EDGE_TOLERANCE_RATIO
CONTENTS_COLUMN_GRID_SNAP_MAX_WIDTH_DEVIATION_RATIO = layout_config.CONTENTS_COLUMN_GRID_SNAP_MAX_WIDTH_DEVIATION_RATIO
CONTENTS_COLUMN_GRID_SNAP_WIDE_BOUNDS_MIN_WIDTH_RATIO = layout_config.CONTENTS_COLUMN_GRID_SNAP_WIDE_BOUNDS_MIN_WIDTH_RATIO
CONTENTS_COLUMN_GRID_SNAP_MIN_PIECE_WIDTH_RATIO = layout_config.CONTENTS_COLUMN_GRID_SNAP_MIN_PIECE_WIDTH_RATIO
CONTENTS_HEADING_SPLIT_MIN_WIDTH_RATIO = layout_config.CONTENTS_HEADING_SPLIT_MIN_WIDTH_RATIO
CONTENTS_HEADING_SPLIT_MIN_HEIGHT_RATIO = layout_config.CONTENTS_HEADING_SPLIT_MIN_HEIGHT_RATIO
CONTENTS_HEADING_SPLIT_MIN_RATIO = layout_config.CONTENTS_HEADING_SPLIT_MIN_RATIO
CONTENTS_HEADING_SPLIT_MAX_RATIO = layout_config.CONTENTS_HEADING_SPLIT_MAX_RATIO
CONTENTS_HEADING_SPLIT_MIN_GAP_PX = layout_config.CONTENTS_HEADING_SPLIT_MIN_GAP_PX
CONTENTS_HEADING_SPLIT_MIN_BODY_ROWS = layout_config.CONTENTS_HEADING_SPLIT_MIN_BODY_ROWS
CONTENTS_TEXT_MIN_SCORE = layout_config.CONTENTS_TEXT_MIN_SCORE
CONTENTS_TEXT_MIN_TEXTLINE_DENSITY = layout_config.CONTENTS_TEXT_MIN_TEXTLINE_DENSITY
CONTENTS_TEXT_MIN_COMPONENT_DENSITY = layout_config.CONTENTS_TEXT_MIN_COMPONENT_DENSITY
CONTENTS_TEXT_MAX_AXIS_LINE_DENSITY = layout_config.CONTENTS_TEXT_MAX_AXIS_LINE_DENSITY
CONTENTS_TEXT_MAX_LINE_BALANCE = layout_config.CONTENTS_TEXT_MAX_LINE_BALANCE
CONTENTS_TEXT_MAX_SATURATION = layout_config.CONTENTS_TEXT_MAX_SATURATION
CONTENTS_TEXT_MIN_WIDTH_RATIO = layout_config.CONTENTS_TEXT_MIN_WIDTH_RATIO
CONTENTS_TEXT_MAX_WIDTH_RATIO = layout_config.CONTENTS_TEXT_MAX_WIDTH_RATIO
CONTENTS_TEXT_MIN_HEIGHT_RATIO = layout_config.CONTENTS_TEXT_MIN_HEIGHT_RATIO
CONTENTS_NUMBER_COLUMN_MAX_WIDTH_RATIO = layout_config.CONTENTS_NUMBER_COLUMN_MAX_WIDTH_RATIO
CONTENTS_NUMBER_COLUMN_MIN_HEIGHT_RATIO = layout_config.CONTENTS_NUMBER_COLUMN_MIN_HEIGHT_RATIO
CONTENTS_NUMBER_COLUMN_MAX_GAP_RATIO = layout_config.CONTENTS_NUMBER_COLUMN_MAX_GAP_RATIO
CONTENTS_NUMBER_COLUMN_MIN_TARGET_OVERLAP = layout_config.CONTENTS_NUMBER_COLUMN_MIN_TARGET_OVERLAP
CONTENTS_FOOTER_ARTIFACT_TOP_RATIO = layout_config.CONTENTS_FOOTER_ARTIFACT_TOP_RATIO
CONTENTS_FOOTER_ARTIFACT_MAX_HEIGHT_RATIO = layout_config.CONTENTS_FOOTER_ARTIFACT_MAX_HEIGHT_RATIO
CONTENTS_FOOTER_ARTIFACT_MAX_WIDTH_RATIO = layout_config.CONTENTS_FOOTER_ARTIFACT_MAX_WIDTH_RATIO
CONTENTS_FOOTER_ARTIFACT_EDGE_RATIO = layout_config.CONTENTS_FOOTER_ARTIFACT_EDGE_RATIO
CONTENTS_FOOTER_ARTIFACT_MAX_AREA_RATIO = layout_config.CONTENTS_FOOTER_ARTIFACT_MAX_AREA_RATIO
PAGE_MARGIN_VISUAL_ARTIFACT_MAX_WIDTH_RATIO = layout_config.PAGE_MARGIN_VISUAL_ARTIFACT_MAX_WIDTH_RATIO
PAGE_MARGIN_VISUAL_ARTIFACT_MIN_HEIGHT_RATIO = layout_config.PAGE_MARGIN_VISUAL_ARTIFACT_MIN_HEIGHT_RATIO
PAGE_MARGIN_VISUAL_ARTIFACT_EDGE_RATIO = layout_config.PAGE_MARGIN_VISUAL_ARTIFACT_EDGE_RATIO
PAGE_MARGIN_VISUAL_ARTIFACT_MAX_CONFIDENCE = layout_config.PAGE_MARGIN_VISUAL_ARTIFACT_MAX_CONFIDENCE
PAGE_MARGIN_VISUAL_ARTIFACT_MIN_SATURATION = layout_config.PAGE_MARGIN_VISUAL_ARTIFACT_MIN_SATURATION


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
        "Run: .\\init.ps1 or .\\init.ps1 -PythonPath <python.exe>."
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


def low_projection_runs(values, threshold: float, min_run: int) -> list[tuple[int, int, float]]:
    runs: list[tuple[int, int, float]] = []
    start = -1
    for index, value in enumerate(values):
        low = value <= threshold
        if low and start < 0:
            start = index
        elif not low and start >= 0:
            end = index - 1
            if end - start + 1 >= min_run:
                runs.append((start, end, float(values[start : end + 1].mean())))
            start = -1
    if start >= 0:
        end = len(values) - 1
        if end - start + 1 >= min_run:
            runs.append((start, end, float(values[start : end + 1].mean())))
    return runs


def vertical_whitespace_corridor_runs(mask, box: Box, min_gap: int) -> list[tuple[int, int, float]]:
    roi = mask[box.y : box.y2, box.x : box.x2]
    if roi.size == 0:
        return []

    column_projection = (roi > 0).sum(axis=0).astype(np.float32)
    smooth_radius = max(1, box.w // 180)
    smoothed = smooth_projection(column_projection, smooth_radius)
    raw_limit = max(1.0, box.h * 0.006)
    smooth_limit = max(1.5, box.h * 0.010)
    corridor_values = np.where((column_projection <= raw_limit) & (smoothed <= smooth_limit), 0.0, smoothed)
    return low_projection_runs(corridor_values, threshold=0.0, min_run=min_gap)


def horizontal_whitespace_corridor_runs(mask, box: Box, min_gap: int) -> list[tuple[int, int, float]]:
    roi = mask[box.y : box.y2, box.x : box.x2]
    if roi.size == 0:
        return []

    row_projection = (roi > 0).sum(axis=1).astype(np.float32)
    smooth_radius = max(1, box.h // 180)
    smoothed = smooth_projection(row_projection, smooth_radius)
    raw_limit = max(1.0, box.w * 0.006)
    smooth_limit = max(1.5, box.w * 0.010)
    corridor_values = np.where((row_projection <= raw_limit) & (smoothed <= smooth_limit), 0.0, smoothed)
    return low_projection_runs(corridor_values, threshold=0.0, min_run=min_gap)


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

    runs = low_projection_runs(smoothed, low_limit, min_gap)
    runs.extend(vertical_whitespace_corridor_runs(mask, box, min_gap))

    candidates = []
    for start, end, mean_density in runs:
        center = (start + end) // 2
        if center < min_piece or box.w - center < min_piece:
            continue
        width = end - start + 1
        center_balance = 1.0 - abs((center / float(box.w)) - 0.5)
        candidates.append((width, center_balance, -mean_density, center))
    if not candidates:
        return [box]

    _, _, _, center = max(candidates)
    left = Box(box.x, box.y, center, box.h)
    right = Box(box.x + center, box.y, box.w - center, box.h)
    return [piece for piece in (left, right) if piece.area > 0]


def split_box_by_horizontal_gaps(mask, box: Box, page_width: int, page_height: int) -> list[Box]:
    if box.w < page_width * HORIZONTAL_GAP_SPLIT_MIN_WIDTH_RATIO:
        return [box]
    if box.h < page_height * HORIZONTAL_GAP_SPLIT_MIN_HEIGHT_RATIO:
        return [box]

    roi = mask[box.y : box.y2, box.x : box.x2]
    if roi.size == 0:
        return [box]

    row_projection = (roi > 0).sum(axis=1)
    smoothed = smooth_projection(row_projection, max(2, box.h // 120))
    low_limit = max(2.0, box.w * 0.012)
    min_gap = max(HORIZONTAL_GAP_SPLIT_MIN_GAP_PX, int(round(box.h * HORIZONTAL_GAP_SPLIT_MIN_GAP_RATIO)))
    min_piece = max(45, int(round(page_height * HORIZONTAL_GAP_SPLIT_MIN_PIECE_HEIGHT_RATIO)))
    edge_skip = max(8, int(round(box.h * HORIZONTAL_GAP_SPLIT_EDGE_SKIP_RATIO)))

    runs = low_projection_runs(smoothed, low_limit, min_gap)
    runs.extend(horizontal_whitespace_corridor_runs(mask, box, min_gap))

    candidates = []
    for start, end, mean_density in runs:
        if start <= edge_skip or end >= box.h - edge_skip:
            continue
        center = (start + end) // 2
        if center < min_piece or box.h - center < min_piece:
            continue
        gap_height = end - start + 1
        center_balance = 1.0 - abs((center / float(box.h)) - 0.5)
        candidates.append((gap_height, center_balance, -mean_density, center))
    if not candidates:
        return [box]

    _, _, _, center = max(candidates)
    top = Box(box.x, box.y, box.w, center)
    bottom = Box(box.x, box.y + center, box.w, box.h - center)
    return [piece for piece in (top, bottom) if piece.area > 0]


def split_box_by_horizontal_gaps_recursive(mask, box: Box, page_width: int, page_height: int) -> list[Box]:
    pieces = [box]
    for _ in range(HORIZONTAL_GAP_SPLIT_MAX_PIECES - 1):
        changed = False
        next_pieces: list[Box] = []
        for piece in pieces:
            split = split_box_by_horizontal_gaps(mask, piece, page_width, page_height)
            if len(split) > 1:
                changed = True
            next_pieces.extend(split)
        pieces = next_pieces
        if not changed or len(pieces) >= HORIZONTAL_GAP_SPLIT_MAX_PIECES:
            break
    return sorted(pieces[:HORIZONTAL_GAP_SPLIT_MAX_PIECES], key=lambda item: (item.y, item.x))


def text_row_run_count(mask, box: Box) -> int:
    roi = mask[box.y : box.y2, box.x : box.x2]
    if roi.size == 0:
        return 0
    row_projection = (roi > 0).sum(axis=1).astype(np.float32)
    smoothed = smooth_projection(row_projection, max(1, box.h // 80))
    threshold = max(2.0, box.w * 0.010)
    min_run = max(3, box.h // 80)
    return len(projection_runs(smoothed, threshold, min_run))


def split_multiline_text_box_by_column_gaps(mask, box: Box, page_width: int, page_height: int) -> list[Box]:
    if box.w < page_width * TEXT_COLUMN_SPLIT_MIN_WIDTH_RATIO:
        return [box]
    if box.h < page_height * TEXT_COLUMN_SPLIT_MIN_HEIGHT_RATIO:
        return [box]

    min_gap = max(TEXT_COLUMN_SPLIT_MIN_GAP_PX, int(round(box.w * TEXT_COLUMN_SPLIT_MIN_GAP_RATIO)))
    min_piece = max(40, int(round(page_width * TEXT_COLUMN_SPLIT_MIN_PIECE_WIDTH_RATIO)))
    candidates = []
    if text_row_run_count(mask, box) >= TEXT_COLUMN_SPLIT_MIN_ROW_RUNS:
        for start, end, mean_density in vertical_whitespace_corridor_runs(mask, box, min_gap):
            center = (start + end) // 2
            if center < min_piece or box.w - center < min_piece:
                continue
            width = end - start + 1
            center_balance = 1.0 - abs((center / float(box.w)) - 0.5)
            candidates.append((width, center_balance, -mean_density, center))
    if not candidates:
        candidates = low_density_column_gap_candidates(mask, box, page_width, page_height, min_piece)
    if not candidates:
        return [box]

    _, _, _, center = max(candidates)
    left = Box(box.x, box.y, center, box.h)
    right = Box(box.x + center, box.y, box.w - center, box.h)
    return [piece for piece in (left, right) if piece.area > 0]


def low_density_column_gap_candidates(
    mask,
    box: Box,
    page_width: int,
    page_height: int,
    min_piece: int,
) -> list[tuple[int, float, float, int]]:
    if box.w < page_width * TEXT_COLUMN_FALLBACK_MIN_WIDTH_RATIO:
        return []
    if box.h < page_height * TEXT_COLUMN_FALLBACK_MIN_HEIGHT_RATIO:
        return []

    roi = mask[box.y : box.y2, box.x : box.x2]
    if roi.size == 0:
        return []

    column_projection = (roi > 0).sum(axis=0).astype(np.float32)
    smoothed = smooth_projection(column_projection, max(1, box.w // 180))
    low_limit = max(2.0, box.h * TEXT_COLUMN_FALLBACK_MAX_PROJECTION_DENSITY)
    min_gap = max(TEXT_COLUMN_FALLBACK_MIN_GAP_PX, int(round(box.w * TEXT_COLUMN_FALLBACK_MIN_GAP_RATIO)))
    candidates: list[tuple[int, float, float, int]] = []
    for start, end, mean_density in low_projection_runs(smoothed, low_limit, min_gap):
        center = (start + end) // 2
        if center < min_piece or box.w - center < min_piece:
            continue
        width = end - start + 1
        center_balance = 1.0 - abs((center / float(box.w)) - 0.5)
        candidates.append((width, center_balance, -mean_density, center))
    return candidates


def split_contents_row_merged_text_box_by_column_gaps(mask, box: Box, page_width: int, page_height: int) -> list[Box]:
    if box.w < page_width * CONTENTS_COLUMN_SPLIT_MIN_WIDTH_RATIO:
        return [box]
    if box.h < page_height * CONTENTS_COLUMN_SPLIT_MIN_HEIGHT_RATIO:
        return [box]

    roi = mask[box.y : box.y2, box.x : box.x2]
    if roi.size == 0:
        return [box]

    min_piece = max(40, int(round(page_width * CONTENTS_COLUMN_SPLIT_MIN_PIECE_WIDTH_RATIO)))
    min_gap = max(CONTENTS_COLUMN_SPLIT_MIN_GAP_PX, int(round(box.w * CONTENTS_COLUMN_SPLIT_MIN_GAP_RATIO)))
    low_limit = max(2.0, box.h * CONTENTS_COLUMN_SPLIT_MAX_PROJECTION_DENSITY)
    column_projection = (roi > 0).sum(axis=0).astype(np.float32)
    smoothed = smooth_projection(column_projection, max(1, box.w // 180))
    candidates: list[tuple[float, int, float, int]] = []
    for start, end, mean_density in low_projection_runs(smoothed, low_limit, min_gap):
        center = (start + end) // 2
        if center < min_piece or box.w - center < min_piece:
            continue
        width = end - start + 1
        center_balance = 1.0 - abs((center / float(box.w)) - 0.5)
        candidates.append((center_balance, width, -mean_density, center))
    if not candidates:
        return [box]

    _, _, _, center = max(candidates)
    left = Box(box.x, box.y, center, box.h)
    right = Box(box.x + center, box.y, box.w - center, box.h)
    return [piece for piece in (left, right) if piece.area > 0]


def split_multiline_text_box_recursive(mask, box: Box, page_width: int, page_height: int) -> list[Box]:
    pieces = [box]
    for _ in range(TEXT_COLUMN_SPLIT_MAX_PIECES - 1):
        changed = False
        next_pieces: list[Box] = []
        for piece in pieces:
            split = split_multiline_text_box_by_column_gaps(mask, piece, page_width, page_height)
            if len(split) > 1:
                changed = True
            next_pieces.extend(split)
        pieces = next_pieces
        if not changed or len(pieces) >= TEXT_COLUMN_SPLIT_MAX_PIECES:
            break
    return sorted(pieces[:TEXT_COLUMN_SPLIT_MAX_PIECES], key=lambda item: (item.y, item.x))


def split_boxes_by_internal_gaps(mask, boxes: list[Box], width: int, height: int) -> list[Box]:
    split: list[Box] = []
    for box in boxes:
        for vertical_piece in split_box_by_vertical_gaps(mask, box, width, height):
            split.extend(split_box_by_horizontal_gaps_recursive(mask, vertical_piece, width, height))
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


def feature_visual_candidate_for_text_recovery(features: dict[str, float]) -> bool:
    area = features["area_ratio"]
    max_text = features["max_text_score"]
    line_art = features.get("line_art_score", 0.0)
    line_balance = features["line_balance"]
    min_line_density = min(features["hline_density"], features["vline_density"])
    component_signature = features.get("component_signature_score", 0.0)
    saturation = features.get("saturation_p80", 0.0)
    saturated_horizontal_note = (
        saturation > 0.18
        and features["height_ratio"] < 0.075
        and features["wide_aspect"] > 0.45
    )
    line_drawing = (
        area > 0.012
        and line_art > 0.18
        and line_balance > 0.20
        and min_line_density > 0.045
        and max_text < 0.62
    )
    component_visual = (
        area > 0.004
        and line_art > 0.26
        and component_signature > 0.52
        and features["edge_density"] > 0.16
        and features["ink_density"] < 0.20
        and min_line_density > 0.020
        and saturation < 0.12
    )
    grayscale_photo = (
        area > 0.004
        and features["gray_std"] > 0.55
        and features["gray_levels"] > 0.68
        and features["ink_density"] > 0.18
        and max_text < 0.78
        and line_art > 0.24
        and not saturated_horizontal_note
    )
    photo_like = (
        area > 0.006
        and saturation > 0.16
        and features["gray_std"] > 0.45
        and max_text < 0.45
        and not saturated_horizontal_note
    )
    return line_drawing or component_visual or grayscale_photo or photo_like


def nested_visual_boxes_from_large_regions(
    image,
    foreground,
    gray,
    boxes: list[Box],
    width: int,
    height: int,
) -> list[Box]:
    page_area = max(1, width * height)
    large_boxes = [box for box in boxes if box.area / page_area > 0.08 and box.w > width * 0.18 and box.h > height * 0.22]
    if not large_boxes:
        return []

    line_length = max(18, min(width, height) // 70)
    close_size = max(10, min(width, height) // 150)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (line_length, 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, line_length))
    h_lines = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, h_kernel)
    v_lines = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, v_kernel)
    line_mask = cv2.bitwise_or(h_lines, v_lines)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (close_size, close_size))
    line_mask = cv2.dilate(line_mask, close_kernel, iterations=1)
    edges = canny_edges(gray)

    contours, _ = cv2.findContours(line_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[Box] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        candidate = Box(x, y, w, h).inflate(max(3, min(width, height) // 320), width, height)
        area_ratio = candidate.area / page_area
        if area_ratio < 0.004 or area_ratio > 0.16:
            continue
        if candidate.w < width * 0.045 or candidate.h < height * 0.035:
            continue
        if candidate.x < width * 0.08 and candidate.h > height * 0.45:
            continue
        title_like = candidate.h < height * 0.070 and candidate.w > width * 0.20
        if title_like:
            continue
        if not any(overlap_area(candidate, large) / max(1, candidate.area) > 0.78 for large in large_boxes):
            continue

        features = feature_dict(image, foreground, edges, candidate)
        saturation = features.get("saturation_p80", 0.0)
        if saturation > 0.18 and (candidate.h < height * 0.075 or candidate.w / max(1, candidate.h) > 2.8):
            continue
        if not feature_visual_candidate_for_text_recovery(features):
            continue
        candidates.append(candidate)

    return deduplicate_candidate_boxes(candidates)


def visual_boxes_for_text_recovery(image, gray, existing_boxes: list[Box], width: int, height: int) -> list[Box]:
    if not existing_boxes:
        return []

    mask, _, _ = foreground_mask(gray)
    edges = canny_edges(gray)
    visual_boxes: list[Box] = []
    for box in existing_boxes:
        if not likely_visual_candidate_box(box, width, height):
            continue
        features = feature_dict(image, mask, edges, box)
        if feature_visual_candidate_for_text_recovery(features):
            visual_boxes.append(box)
    return deduplicate_candidate_boxes(visual_boxes)


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
            for box in visual_boxes_for_text_recovery(image, gray, existing_boxes, width, height)
            if not (
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


def frequency_hint_boxes(
    frequency_result: dict[str, object] | None,
    labels: set[str],
    width: int,
    height: int,
    min_confidence: float,
    min_area_ratio: float,
) -> list[Box]:
    if not frequency_result:
        return []
    boxes: list[Box] = []
    page_area = max(1, width * height)
    raw_hints = frequency_result.get("hints", [])
    raw_cluster_hints = frequency_result.get("cluster_hints", [])
    all_hints = (raw_hints if isinstance(raw_hints, list) else []) + (
        raw_cluster_hints if isinstance(raw_cluster_hints, list) else []
    )
    for hint in all_hints:
        if not isinstance(hint, dict):
            continue
        label = str(hint.get("label", ""))
        if label not in labels:
            continue
        confidence = float(hint.get("confidence", 0.0))
        if confidence < min_confidence:
            continue
        bbox = hint.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        box = Box(*(int(value) for value in bbox)).clamp(width, height)
        if box.area / page_area < min_area_ratio or box.w < 24 or box.h < 24:
            continue
        if label != "text":
            if box.w < width * 0.16 or box.h < height * 0.10:
                continue
            if box.w > width * 0.88 or box.h > height * 0.78:
                continue
            if box.w < width * 0.20 and box.h > height * 0.42:
                continue
        boxes.append(box)
    return deduplicate_candidate_boxes(boxes)


def add_frequency_text_hints(
    boxes: list[Box],
    text_hints: list[Box],
    width: int,
    height: int,
    min_area_ratio: float,
) -> list[Box]:
    if not text_hints:
        return boxes
    page_area = max(1, width * height)
    result = boxes[:]
    for hint in text_hints:
        if hint.area / page_area < max(0.0025, min_area_ratio * 4.0):
            continue
        if any(overlap_area(hint, box) / max(1, hint.area) > 0.58 for box in result):
            continue
        result.append(hint)
    return deduplicate_candidate_boxes(result)


def scale_frequency_hints_to_original(
    frequency_result: dict[str, object] | None,
    scale: float,
    key: str = "hints",
) -> list[dict[str, object]]:
    if not frequency_result or layout_frequency is None:
        return []
    hints = frequency_result.get(key, [])
    if not isinstance(hints, list):
        return []
    return layout_frequency.hints_in_original_coordinates(hints, scale)


def frequency_validation_warnings(blocks: list[Block], original_frequency_hints: list[dict[str, object]]) -> list[dict[str, object]]:
    if layout_frequency is None or not original_frequency_hints:
        return []
    return layout_frequency.validate_layout_blocks([asdict(block) for block in blocks], original_frequency_hints)


def detect_candidate_boxes(
    image,
    min_area_ratio: float = 0.00035,
    max_area_ratio: float = 0.85,
    accelerator: str = "cpu",
    frequency_result: dict[str, object] | None = None,
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
    line_art_boxes = line_art_boxes_from_large_regions(image, mask, gray, boxes + oversized_boxes, width, height)
    nested_visual_boxes = nested_visual_boxes_from_large_regions(image, mask, gray, boxes + oversized_boxes, width, height)
    frequency_visual_boxes = frequency_hint_boxes(
        frequency_result,
        {"schematic/circuit", "table", "diagram"},
        width,
        height,
        min_confidence=0.70,
        min_area_ratio=0.020,
    )
    line_art_boxes = deduplicate_candidate_boxes(line_art_boxes + nested_visual_boxes + frequency_visual_boxes)
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
        recovered_from_oversized = text_boxes_from_oversized_regions(image, gray, oversized_boxes, boxes, width, height)
        if recovered_from_oversized:
            boxes = deduplicate_candidate_boxes(boxes + recovered_from_oversized)
            second_pass_recovered = text_boxes_from_oversized_regions(image, gray, oversized_boxes, boxes, width, height)
            if second_pass_recovered:
                boxes = deduplicate_candidate_boxes(boxes + second_pass_recovered)
            visual_after_oversized = visual_boxes_for_text_recovery(image, gray, boxes + line_art_boxes, width, height)
            boxes = split_boxes_around_visual_candidates(boxes, visual_after_oversized, width, height)
    frequency_text_boxes: list[Box] = []
    boxes = add_frequency_text_hints(boxes, frequency_text_boxes, width, height, min_area_ratio)
    if not boxes:
        boxes = raw_boxes
    metadata = {
        "threshold": threshold,
        "bright_foreground": bright_foreground,
        "analysis_width": width,
        "analysis_height": height,
        "accelerator": accelerator,
        "frequency_hint_count": len(frequency_result.get("hints", [])) if frequency_result else 0,
        "frequency_cluster_hint_count": len(frequency_result.get("cluster_hints", [])) if frequency_result else 0,
        "frequency_visual_hint_count": len(frequency_visual_boxes),
        "frequency_text_hint_count": len(frequency_text_boxes),
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
    if layout_component_signatures is not None:
        component_signatures = layout_component_signatures.component_signature_features(roi_mask, roi_edges)
    else:
        component_signatures = {
            "component_signature_score": 0.0,
            "resistor_symbol_density": 0.0,
            "capacitor_symbol_density": 0.0,
            "diode_symbol_density": 0.0,
            "transistor_symbol_density": 0.0,
            "pcb_trace_density": 0.0,
            "pcb_pad_density": 0.0,
            "pcb_board_outline_score": 0.0,
            "pcb_signature_score": 0.0,
        }

    features = {
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
    features.update(component_signatures)
    return features


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
        "heading": [0.48, 0.09, 0.045, 0.74, 0.04, 0.24, 0.30, 0.70, 0.78, 0.42, 0.02, 0.03, 0.03, 0.36, 0.36, 0.10, 0.14, 0.36],
        "image": [0.28, 0.25, 0.08, 0.25, 0.22, 0.43, 0.58, 0.78, 0.95, 0.18, 0.04, 0.04, 0.25, 0.18, 0.18, 0.16, 0.16, 0.18],
        "schematic/circuit": [0.36, 0.30, 0.09, 0.42, 0.18, 0.07, 0.18, 0.20, 0.34, 0.45, 0.42, 0.34, 0.78, 0.38, 0.38, 0.28, 0.32, 0.38],
        "diagram": [0.32, 0.24, 0.08, 0.36, 0.20, 0.13, 0.28, 0.36, 0.55, 0.52, 0.20, 0.14, 0.45, 0.45, 0.45, 0.28, 0.35, 0.45],
        "pcb": [0.34, 0.52, 0.16, 0.18, 0.34, 0.16, 0.34, 0.62, 0.72, 0.34, 0.16, 0.18, 0.68, 0.20, 0.20, 0.14, 0.14, 0.20],
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


def heading_candidate_features(features: dict[str, float]) -> bool:
    return (
        features["width_ratio"] >= HEADING_MIN_WIDTH_RATIO
        and features["height_ratio"] <= HEADING_MAX_HEIGHT_RATIO
        and features["area_ratio"] <= HEADING_MAX_AREA_RATIO
        and features["wide_aspect"] >= HEADING_MIN_WIDE_ASPECT
        and features["max_text_score"] >= HEADING_MIN_TEXT_SCORE
        and features["max_text_score"] <= HEADING_MAX_TEXT_SCORE
        and features["ink_density"] >= HEADING_MIN_INK_DENSITY
        and features["gray_std"] >= HEADING_MIN_GRAY_STD
        and features["line_balance"] <= HEADING_MAX_LINE_BALANCE
        and features["component_density"] >= HEADING_MIN_COMPONENT_DENSITY
    )


def top_display_heading_features(features: dict[str, float]) -> bool:
    return (
        features["width_ratio"] >= HEADING_MIN_WIDTH_RATIO
        and features["height_ratio"] <= HEADING_MAX_HEIGHT_RATIO
        and features["area_ratio"] <= HEADING_MAX_AREA_RATIO
        and features["wide_aspect"] >= HEADING_MIN_WIDE_ASPECT
        and features["max_text_score"] >= HEADING_MIN_TEXT_SCORE
        and features["max_text_score"] <= HEADING_MAX_TEXT_SCORE
        and features["ink_density"] >= HEADING_MIN_INK_DENSITY
        and features["gray_std"] >= HEADING_MIN_GRAY_STD
        and features["line_balance"] <= HEADING_MAX_LINE_BALANCE
        and features["component_density"] >= BOLD_DISPLAY_HEADING_MIN_COMPONENT_DENSITY
        and features["hline_density"] <= TOP_DISPLAY_HEADING_MAX_HLINE_DENSITY
    )


def annual_contents_text_features(features: dict[str, float]) -> bool:
    """Recognize dense contents-list text that can look image-like at block scale."""

    return (
        CONTENTS_TEXT_MIN_WIDTH_RATIO <= features.get("width_ratio", 0.0) <= CONTENTS_TEXT_MAX_WIDTH_RATIO
        and features.get("height_ratio", 0.0) >= CONTENTS_TEXT_MIN_HEIGHT_RATIO
        and features.get("max_text_score", 0.0) >= CONTENTS_TEXT_MIN_SCORE
        and features.get("textline_density", 0.0) >= CONTENTS_TEXT_MIN_TEXTLINE_DENSITY
        and features.get("component_density", 0.0) >= CONTENTS_TEXT_MIN_COMPONENT_DENSITY
        and max(features.get("hline_density", 0.0), features.get("vline_density", 0.0)) <= CONTENTS_TEXT_MAX_AXIS_LINE_DENSITY
        and features.get("line_balance", 1.0) <= CONTENTS_TEXT_MAX_LINE_BALANCE
        and features.get("saturation_p80", 0.0) <= CONTENTS_TEXT_MAX_SATURATION
    )


def horizontal_rule_features(features: dict[str, float]) -> bool:
    return (
        features["width_ratio"] >= HORIZONTAL_RULE_MIN_WIDTH_RATIO
        and features["height_ratio"] <= HORIZONTAL_RULE_MAX_HEIGHT_RATIO
        and features["area_ratio"] <= HORIZONTAL_RULE_MAX_AREA_RATIO
        and features["hline_density"] >= HORIZONTAL_RULE_MIN_HLINE_DENSITY
        and features["vline_density"] <= HORIZONTAL_RULE_MAX_VLINE_DENSITY
        and features.get("line_art_score", 0.0) >= HORIZONTAL_RULE_MIN_LINE_ART
        and features["component_density"] <= HORIZONTAL_RULE_MAX_COMPONENT_DENSITY
        and features.get("component_signature_score", 0.0) <= HORIZONTAL_RULE_MAX_COMPONENT_SIGNATURE
    )


def single_axis_waveform_diagram_features(features: dict[str, float]) -> bool:
    return (
        features.get("area_ratio", 0.0) >= WAVEFORM_DIAGRAM_MIN_AREA_RATIO
        and features.get("height_ratio", 1.0) <= WAVEFORM_DIAGRAM_MAX_HEIGHT_RATIO
        and features.get("hline_density", 0.0) >= WAVEFORM_DIAGRAM_MIN_HLINE_DENSITY
        and features.get("vline_density", 1.0) <= WAVEFORM_DIAGRAM_MAX_VLINE_DENSITY
        and features.get("line_art_score", 0.0) >= WAVEFORM_DIAGRAM_MIN_LINE_ART
        and features.get("max_text_score", 0.0) >= WAVEFORM_DIAGRAM_MIN_TEXT_SCORE
        and features.get("saturation_p80", 0.0) <= WAVEFORM_DIAGRAM_MAX_SATURATION
        and features.get("ink_density", 1.0) <= WAVEFORM_DIAGRAM_MAX_INK_DENSITY
    )


def wide_rule_heading_features(features: dict[str, float]) -> bool:
    return (
        not horizontal_rule_features(features)
        and features["width_ratio"] >= WIDE_RULE_HEADING_MIN_WIDTH_RATIO
        and features["height_ratio"] <= WIDE_RULE_HEADING_MAX_HEIGHT_RATIO
        and features["area_ratio"] <= WIDE_RULE_HEADING_MAX_AREA_RATIO
        and features["max_text_score"] >= WIDE_RULE_HEADING_MIN_TEXT_SCORE
        and features["textline_density"] >= WIDE_RULE_HEADING_MIN_TEXTLINE_DENSITY
        and features["ink_density"] >= WIDE_RULE_HEADING_MIN_INK_DENSITY
        and features["component_density"] >= HEADING_MIN_COMPONENT_DENSITY
    )


def bold_display_heading_features(features: dict[str, float]) -> bool:
    height_ratio = features["height_ratio"]
    return (
        features["width_ratio"] >= BOLD_DISPLAY_HEADING_MIN_WIDTH_RATIO
        and BOLD_DISPLAY_HEADING_MIN_HEIGHT_RATIO <= height_ratio <= BOLD_DISPLAY_HEADING_MAX_HEIGHT_RATIO
        and features["area_ratio"] <= BOLD_DISPLAY_HEADING_MAX_AREA_RATIO
        and features["ink_density"] >= BOLD_DISPLAY_HEADING_MIN_INK_DENSITY
        and features["gray_std"] >= BOLD_DISPLAY_HEADING_MIN_GRAY_STD
        and features["max_text_score"] <= BOLD_DISPLAY_HEADING_MAX_TEXT_SCORE
        and features["component_density"] >= BOLD_DISPLAY_HEADING_MIN_COMPONENT_DENSITY
        and features["hline_density"] <= BOLD_DISPLAY_HEADING_MAX_HLINE_DENSITY
        and features["line_balance"] <= BOLD_DISPLAY_HEADING_MAX_LINE_BALANCE
        and features.get("saturation_p80", 0.0) <= BOLD_DISPLAY_HEADING_MAX_SATURATION
    )


def monochrome_icon_image_features(features: dict[str, float]) -> bool:
    return (
        features["area_ratio"] >= MONOCHROME_ICON_IMAGE_MIN_AREA_RATIO
        and features["ink_density"] >= MONOCHROME_ICON_IMAGE_MIN_INK_DENSITY
        and features["edge_density"] >= MONOCHROME_ICON_IMAGE_MIN_EDGE_DENSITY
        and features["gray_std"] >= MONOCHROME_ICON_IMAGE_MIN_GRAY_STD
        and features["component_density"] <= MONOCHROME_ICON_IMAGE_MAX_COMPONENT_DENSITY
        and features.get("component_signature_score", 0.0) <= MONOCHROME_ICON_IMAGE_MAX_COMPONENT_SIGNATURE
        and features["max_text_score"] <= MONOCHROME_ICON_IMAGE_MAX_TEXT_SCORE
    )


def captioned_component_schematic_features(features: dict[str, float]) -> bool:
    return (
        features.get("area_ratio", 0.0) >= CAPTIONED_SCHEMATIC_MIN_AREA_RATIO
        and features.get("area_ratio", 1.0) <= CAPTIONED_SCHEMATIC_MAX_AREA_RATIO
        and features.get("height_ratio", 0.0) >= CAPTIONED_SCHEMATIC_MIN_HEIGHT_RATIO
        and features.get("ink_density", 1.0) <= CAPTIONED_SCHEMATIC_MAX_INK_DENSITY
        and features.get("edge_density", 0.0) >= CAPTIONED_SCHEMATIC_MIN_EDGE_DENSITY
        and features.get("line_art_score", 0.0) >= CAPTIONED_SCHEMATIC_MIN_LINE_ART
        and features.get("vline_density", 0.0) >= CAPTIONED_SCHEMATIC_MIN_VLINE_DENSITY
        and features.get("max_text_score", 1.0) <= CAPTIONED_SCHEMATIC_MAX_TEXT_SCORE
        and features.get("component_signature_score", 0.0) >= CAPTIONED_SCHEMATIC_MIN_COMPONENT_SIGNATURE
        and features.get("saturation_p80", 0.0) <= CAPTIONED_SCHEMATIC_MAX_SATURATION
    )


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
    component_signature = features.get("component_signature_score", 0.0)
    line_art = features.get("line_art_score", 0.0)
    pcb_signature = features.get("pcb_signature_score", 0.0)
    pcb_trace = features.get("pcb_trace_density", 0.0)
    pcb_pad = features.get("pcb_pad_density", 0.0)
    pcb_outline = features.get("pcb_board_outline_score", 0.0)
    component_rule_signal = (
        component_signature
        if max_text < 0.62 and line_art > 0.16 and balance > 0.10
        else 0.0
    )

    text_index = CLASS_NAMES.index("text")
    heading_index = CLASS_NAMES.index("heading")
    image_index = CLASS_NAMES.index("image")
    schematic_index = CLASS_NAMES.index("schematic/circuit")
    diagram_index = CLASS_NAMES.index("diagram")
    pcb_index = CLASS_NAMES.index("pcb")
    table_index = CLASS_NAMES.index("table")
    other_index = CLASS_NAMES.index("other")

    scores[text_index] = 1.8 * max_text + 1.1 * components + 0.4 * ink + 0.3 * max(vertical_text, diagonal_text) - 0.45 * balance
    scores[heading_index] = (
        1.7 * max_text
        + 0.7 * components
        + 0.55 * ink
        + 0.55 * std
        + 0.35 * features.get("saturation_p80", 0.0)
        + 0.40 * features["wide_aspect"]
        - 0.85 * balance
        - 0.40 * max(hline, vline)
    )
    scores[image_index] = 1.6 * std + 1.3 * levels + 0.9 * edge + 0.5 * ink - 0.75 * max_text
    scores[schematic_index] = 1.1 * hline + 1.1 * vline + 0.8 * balance + 0.5 * edge + 1.6 * component_rule_signal - 0.5 * std
    scores[diagram_index] = 0.8 * edge + 0.6 * hline + 0.25 * max_text + 0.5 * levels
    scores[pcb_index] = 1.4 * pcb_signature + 1.2 * pcb_trace + 0.45 * pcb_pad + 0.30 * pcb_outline + 0.35 * line_art - 0.50 * max_text
    scores[table_index] = 1.4 * hline + 1.4 * vline + 1.2 * balance + 0.25 * max_text - 0.4 * std
    scores[other_index] = 0.5 + (0.08 > area) * 0.2 - 0.4 * ink - 0.2 * edge
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
    component_signature = features.get("component_signature_score", 0.0)
    pcb_signature = features.get("pcb_signature_score", 0.0)
    pcb_trace = features.get("pcb_trace_density", 0.0)
    pcb_pad = features.get("pcb_pad_density", 0.0)
    pcb_outline = features.get("pcb_board_outline_score", 0.0)
    pcb_axis_line_density = min(features["hline_density"], features["vline_density"])
    pcb_has_track_grid = features["line_balance"] >= PCB_MIN_LINE_BALANCE and pcb_axis_line_density >= PCB_MIN_AXIS_LINE_DENSITY
    pcb_size_ok = features["area_ratio"] >= PCB_MIN_AREA_RATIO and features["height_ratio"] >= PCB_MIN_HEIGHT_RATIO
    heading_candidate = heading_candidate_features(features)
    contents_text_candidate = annual_contents_text_features(features)
    horizontal_rule_candidate = horizontal_rule_features(features)
    waveform_diagram_candidate = single_axis_waveform_diagram_features(features)
    wide_rule_heading_candidate = wide_rule_heading_features(features)
    bold_display_heading_candidate = bold_display_heading_features(features)
    monochrome_icon_image_candidate = monochrome_icon_image_features(features)
    captioned_component_schematic_candidate = captioned_component_schematic_features(features)
    pcb_candidate = (
        pcb_trace >= PCB_MIN_TRACE_DENSITY
        and pcb_signature >= PCB_MIN_SIGNATURE_SCORE
        and pcb_has_track_grid
        and pcb_size_ok
        and max_text < PCB_MAX_TEXT_SCORE
        and features["ink_density"] < PCB_MAX_INK_DENSITY
    )

    if features["area_ratio"] < 0.002 and features["textline_density"] < 0.25:
        scores *= 0.65
        scores[CLASS_NAMES.index("other")] += 0.35
    if contents_text_candidate:
        scores[CLASS_NAMES.index("text")] += 2.40
        scores[CLASS_NAMES.index("image")] *= 0.08
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.30
        scores[CLASS_NAMES.index("diagram")] *= 0.45
        scores[CLASS_NAMES.index("table")] *= 0.55
        scores[CLASS_NAMES.index("pcb")] *= 0.10
    if horizontal_rule_candidate:
        scores[CLASS_NAMES.index("other")] += 2.80
        scores[CLASS_NAMES.index("heading")] *= 0.04
        scores[CLASS_NAMES.index("text")] *= 0.08
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.08
        scores[CLASS_NAMES.index("diagram")] *= 0.16
        scores[CLASS_NAMES.index("table")] *= 0.16
        scores[CLASS_NAMES.index("image")] *= 0.20
        scores[CLASS_NAMES.index("pcb")] *= 0.04
    if waveform_diagram_candidate:
        scores[CLASS_NAMES.index("diagram")] += 3.40 + 0.45 * line_art
        scores[CLASS_NAMES.index("text")] *= 0.10
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.10
        scores[CLASS_NAMES.index("table")] *= 0.35
        scores[CLASS_NAMES.index("heading")] *= 0.40
        scores[CLASS_NAMES.index("image")] *= 0.55
        scores[CLASS_NAMES.index("pcb")] *= 0.12
    if monochrome_icon_image_candidate:
        scores[CLASS_NAMES.index("image")] += 3.20 + 0.65 * features["gray_std"]
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.06
        scores[CLASS_NAMES.index("diagram")] *= 0.25
        scores[CLASS_NAMES.index("table")] *= 0.18
        scores[CLASS_NAMES.index("pcb")] *= 0.03
        scores[CLASS_NAMES.index("text")] *= 0.25
    if captioned_component_schematic_candidate:
        scores[CLASS_NAMES.index("schematic/circuit")] += 2.90 + 0.45 * component_signature + 0.35 * line_art
        scores[CLASS_NAMES.index("text")] *= 0.18
        scores[CLASS_NAMES.index("image")] *= 0.26
        scores[CLASS_NAMES.index("diagram")] *= 0.42
        scores[CLASS_NAMES.index("table")] *= 0.45
    if wide_rule_heading_candidate:
        scores[CLASS_NAMES.index("heading")] += 1.85
        scores[CLASS_NAMES.index("text")] += 0.30
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.22
        scores[CLASS_NAMES.index("diagram")] *= 0.50
        scores[CLASS_NAMES.index("image")] *= 0.40
    if features["gray_std"] > 0.55 and features["gray_levels"] > 0.75 and features["area_ratio"] > 0.01 and max_text < 0.45:
        scores[CLASS_NAMES.index("image")] += 0.25
    if (
        pcb_candidate
        and features["area_ratio"] > 0.025
        and pcb_trace > 0.32
        and pcb_signature > 0.42
        and line_art > 0.18
        and max_text < 0.52
    ):
        scores[CLASS_NAMES.index("pcb")] += 3.0 + pcb_signature + 0.35 * pcb_pad + 0.20 * pcb_outline
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.24
        scores[CLASS_NAMES.index("diagram")] *= 0.45
        scores[CLASS_NAMES.index("image")] *= 0.62
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
        features["area_ratio"] > 0.045
        and line_art > 0.24
        and saturation_p80 < 0.12
        and component_signature > 0.70
        and features["component_density"] > 0.32
        and features["ink_density"] < 0.24
        and max_text < 0.74
        and max(features["hline_density"], features["vline_density"]) > 0.18
        and min(features["hline_density"], features["vline_density"]) > 0.030
    ):
        scores[CLASS_NAMES.index("schematic/circuit")] += 3.20 + 0.75 * component_signature + 0.45 * line_art
        scores[CLASS_NAMES.index("text")] *= 0.12
        scores[CLASS_NAMES.index("heading")] *= 0.45
        scores[CLASS_NAMES.index("image")] *= 0.45
        scores[CLASS_NAMES.index("diagram")] *= 0.72
        scores[CLASS_NAMES.index("table")] *= 0.55
    if (
        features["area_ratio"] > 0.080
        and line_art > 0.22
        and saturation_p80 < 0.12
        and component_signature > 0.72
        and features["component_density"] > 0.18
        and features["ink_density"] < 0.18
        and features["vline_density"] > 0.10
        and max_text < 0.86
    ):
        scores[CLASS_NAMES.index("schematic/circuit")] += 3.10 + 0.80 * component_signature + 0.35 * line_art
        scores[CLASS_NAMES.index("diagram")] *= 0.24
        scores[CLASS_NAMES.index("text")] *= 0.18
        scores[CLASS_NAMES.index("image")] *= 0.42
        scores[CLASS_NAMES.index("table")] *= 0.55
    if bold_display_heading_candidate:
        scores[CLASS_NAMES.index("heading")] += 3.80 + 0.40 * features["ink_density"]
        scores[CLASS_NAMES.index("text")] *= 0.35
        scores[CLASS_NAMES.index("image")] *= 0.18
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.08
        scores[CLASS_NAMES.index("diagram")] *= 0.22
        scores[CLASS_NAMES.index("table")] *= 0.30
        scores[CLASS_NAMES.index("pcb")] *= 0.04
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
        0.006 < features["area_ratio"] < 0.030
        and line_art > 0.42
        and saturation_p80 < 0.08
        and features["edge_density"] > 0.30
        and features["ink_density"] < 0.18
        and features["hline_density"] > 0.055
        and features["vline_density"] > 0.080
        and 0.18 < features["line_balance"] < 0.78
    ):
        scores[CLASS_NAMES.index("schematic/circuit")] += 2.10
        scores[CLASS_NAMES.index("text")] *= 0.34
        scores[CLASS_NAMES.index("image")] *= 0.45
        scores[CLASS_NAMES.index("diagram")] *= 0.62
        scores[CLASS_NAMES.index("table")] *= 0.72
    if (
        component_signature > 0.18
        and line_art > 0.12
        and max_text < 0.62
        and features["textline_density"] < 0.62
        and features["hline_density"] > 0.04
        and features["vline_density"] > 0.04
        and features["line_balance"] > 0.10
        and saturation_p80 < 0.12
        and features["edge_density"] > 0.12
        and features["ink_density"] < 0.34
    ):
        scores[CLASS_NAMES.index("schematic/circuit")] += 1.35 + component_signature
        scores[CLASS_NAMES.index("diagram")] *= 0.55
        scores[CLASS_NAMES.index("table")] *= 0.62
    if (
        component_signature > 0.34
        and saturation_p80 < 0.08
        and features["ink_density"] < 0.26
        and max_text < 0.65
        and features["line_balance"] > 0.12
    ):
        scores[CLASS_NAMES.index("schematic/circuit")] += 1.15
        scores[CLASS_NAMES.index("diagram")] *= 0.45
    if (
        0.004 < features["area_ratio"] < 0.055
        and component_signature > 0.52
        and line_art > 0.26
        and min(features["hline_density"], features["vline_density"]) > 0.020
        and features["line_balance"] > 0.18
        and features["edge_density"] > 0.16
        and features["ink_density"] < 0.20
        and saturation_p80 < 0.12
    ):
        scores[CLASS_NAMES.index("schematic/circuit")] += 2.00 + component_signature
        scores[CLASS_NAMES.index("text")] *= 0.42
        scores[CLASS_NAMES.index("image")] *= 0.55
        scores[CLASS_NAMES.index("table")] *= 0.55
    if (
        0.003 < features["area_ratio"] < 0.022
        and features["gray_std"] > 0.55
        and features["gray_levels"] > 0.68
        and features["ink_density"] > 0.18
        and max_text < 0.78
        and line_art > 0.24
        and features["height_ratio"] < 0.16
    ):
        scores[CLASS_NAMES.index("image")] += 1.55
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.38
        scores[CLASS_NAMES.index("diagram")] *= 0.55
        scores[CLASS_NAMES.index("text")] *= 0.60
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
    if (
        pcb_candidate
        and pcb_trace > 0.30
        and pcb_signature > 0.40
        and max_text < 0.58
        and features["area_ratio"] > 0.020
    ):
        scores[CLASS_NAMES.index("pcb")] += 2.20 + pcb_signature
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.28
        scores[CLASS_NAMES.index("diagram")] *= 0.55
    if not pcb_candidate or features["width_ratio"] < 0.12:
        scores[CLASS_NAMES.index("pcb")] *= 0.12
    if monochrome_icon_image_candidate:
        scores[CLASS_NAMES.index("image")] += 4.20 + 0.75 * features["gray_std"]
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.04
        scores[CLASS_NAMES.index("diagram")] *= 0.18
        scores[CLASS_NAMES.index("table")] *= 0.15
        scores[CLASS_NAMES.index("pcb")] *= 0.02
        scores[CLASS_NAMES.index("text")] *= 0.18
    if captioned_component_schematic_candidate:
        scores[CLASS_NAMES.index("schematic/circuit")] += 3.80 + 0.60 * component_signature + 0.45 * line_art
        scores[CLASS_NAMES.index("text")] *= 0.12
        scores[CLASS_NAMES.index("image")] *= 0.18
        scores[CLASS_NAMES.index("diagram")] *= 0.32
        scores[CLASS_NAMES.index("table")] *= 0.38
    if waveform_diagram_candidate:
        scores[CLASS_NAMES.index("diagram")] += 4.60 + 0.60 * line_art
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.04
        scores[CLASS_NAMES.index("text")] *= 0.10
        scores[CLASS_NAMES.index("table")] *= 0.28
        scores[CLASS_NAMES.index("heading")] *= 0.35
        scores[CLASS_NAMES.index("image")] *= 0.45
        scores[CLASS_NAMES.index("pcb")] *= 0.05
    if heading_candidate:
        scores[CLASS_NAMES.index("heading")] += 3.20
        scores[CLASS_NAMES.index("text")] += 0.35
        scores[CLASS_NAMES.index("image")] *= 0.10
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.25
        scores[CLASS_NAMES.index("diagram")] *= 0.38
        scores[CLASS_NAMES.index("table")] *= 0.48
        scores[CLASS_NAMES.index("pcb")] *= 0.06
    if bold_display_heading_candidate:
        scores[CLASS_NAMES.index("heading")] += 4.80 + 0.65 * features["ink_density"]
        scores[CLASS_NAMES.index("text")] *= 0.25
        scores[CLASS_NAMES.index("image")] *= 0.12
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.04
        scores[CLASS_NAMES.index("diagram")] *= 0.16
        scores[CLASS_NAMES.index("table")] *= 0.22
        scores[CLASS_NAMES.index("pcb")] *= 0.02
    if wide_rule_heading_candidate:
        scores[CLASS_NAMES.index("heading")] += 4.20
        scores[CLASS_NAMES.index("text")] += 0.40
        scores[CLASS_NAMES.index("image")] *= 0.12
        scores[CLASS_NAMES.index("schematic/circuit")] *= 0.06
        scores[CLASS_NAMES.index("diagram")] *= 0.25
        scores[CLASS_NAMES.index("table")] *= 0.35
        scores[CLASS_NAMES.index("pcb")] *= 0.04
    scores = scores / max(float(scores.sum()), 1e-6)

    index = int(scores.argmax())
    return CLASS_NAMES[index], float(scores[index])


def safe_label(label: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "_", label.lower()).strip("_") or "block"


def box_from_list(values: list[int]) -> Box:
    return Box(int(values[0]), int(values[1]), int(values[2]), int(values[3]))


def rectangle_polygon(box: Box) -> list[list[list[int]]]:
    return [[[box.x, box.y], [box.x2, box.y], [box.x2, box.y2], [box.x, box.y2]]]


def point_inside_block(block: Block, point: tuple[float, float]) -> bool:
    if block.outline:
        return point_inside_outline(point, block.outline)
    box = box_from_list(block.bbox)
    return box.x <= point[0] <= box.x2 and box.y <= point[1] <= box.y2


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


def text_block_should_cut_visual_outline(visual_block: Block, text_block: Block) -> bool:
    visual_box = box_from_list(visual_block.bbox)
    text_box = box_from_list(text_block.bbox)
    overlap = intersection_box(visual_box, text_box)
    if overlap is None:
        return False

    if (
        visual_block.label == "diagram"
        and (
            float(visual_block.features.get("stacked_diagram_merge", 0.0)) >= STACKED_DIAGRAM_TEXT_CUTOUT_MIN_MERGE_SCORE
            or float(visual_block.features.get("waveform_image_promote", 0.0)) >= 0.5
        )
    ):
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

    if visual_block.label in {"schematic/circuit", "diagram"}:
        text_extends_past_visual = (
            text_box.h > visual_box.h * 1.20
            and text_box.y < visual_box.y - edge_margin
            and text_box.y2 >= visual_box.y2 - edge_margin
        )
        if text_extends_past_visual and visual_overlap_fraction < 0.45:
            return False

    # Small labels inside a circuit are part of the drawing. Large prose blocks
    # touching a visual block edge are what should carve the preview outline.
    small_internal_label = (
        text_box.area < visual_box.area * 0.012
        and text_box.h < max(42, int(round(visual_box.h * 0.12)))
        and text_box.w < max(180, int(round(visual_box.w * 0.35)))
    )
    return not small_internal_label


def text_cutout_edge_side(cutout: Box, visual_box: Box, edge_margin: int) -> str | None:
    if cutout.x2 >= visual_box.x2 - edge_margin:
        return "right"
    if cutout.x <= visual_box.x + edge_margin:
        return "left"
    if cutout.y2 >= visual_box.y2 - edge_margin:
        return "bottom"
    if cutout.y <= visual_box.y + edge_margin:
        return "top"
    return None


def bridge_aligned_text_cutout_gaps(cutouts: list[Box], visual_box: Box) -> list[Box]:
    if len(cutouts) < 2:
        return cutouts

    edge_margin = max(10, min(80, int(round(min(visual_box.w, visual_box.h) * 0.050))))
    gap_limit = max(24, min(120, int(round(visual_box.h * 0.070))))
    result = cutouts[:]
    seen = {(box.x, box.y, box.w, box.h) for box in result}

    for first_index, first in enumerate(cutouts):
        first_side = text_cutout_edge_side(first, visual_box, edge_margin)
        if first_side not in {"left", "right"}:
            continue
        for second in cutouts[first_index + 1 :]:
            if text_cutout_edge_side(second, visual_box, edge_margin) != first_side:
                continue

            upper, lower = (first, second) if first.y <= second.y else (second, first)
            vertical_gap = lower.y - upper.y2
            if vertical_gap < 0 or vertical_gap > gap_limit:
                continue
            horizontal_overlap = box_horizontal_overlap_width(first, second)
            if horizontal_overlap < min(first.w, second.w) * 0.62:
                continue

            if first_side == "right":
                x1 = min(first.x, second.x)
                x2 = visual_box.x2
            else:
                x1 = visual_box.x
                x2 = max(first.x2, second.x2)
            bridge = Box(x1, upper.y2, x2 - x1, vertical_gap).clamp(visual_box.x2 + 1, visual_box.y2 + 1)
            key = (bridge.x, bridge.y, bridge.w, bridge.h)
            if bridge.area > 0 and key not in seen:
                result.append(bridge)
                seen.add(key)

    return result


def visual_outline_from_text_cutouts(visual_block: Block, text_blocks: list[Block]) -> list[list[list[int]]]:
    visual_box = box_from_list(visual_block.bbox)
    if visual_box.area <= 0:
        return []

    mask = np.full((visual_box.h, visual_box.w), 255, dtype=np.uint8)
    cutouts: list[Box] = []
    pad = max(3, min(14, int(round(min(visual_box.w, visual_box.h) * 0.025))))
    for text_block in text_blocks:
        text_box = box_from_list(text_block.bbox)
        if not text_block_should_cut_visual_outline(visual_block, text_block):
            continue
        padded = text_box.inflate(pad, visual_box.x2 + pad + 1, visual_box.y2 + pad + 1)
        cutout = intersection_box(visual_box, padded)
        if cutout is None:
            continue
        cutouts.append(cutout)

    cutouts = bridge_aligned_text_cutout_gaps(cutouts, visual_box)
    for cutout in cutouts:
        x1 = max(0, cutout.x - visual_box.x)
        y1 = max(0, cutout.y - visual_box.y)
        x2 = min(visual_box.w, cutout.x2 - visual_box.x)
        y2 = min(visual_box.h, cutout.y2 - visual_box.y)
        if x2 <= x1 or y2 <= y1:
            continue
        mask[y1:y2, x1:x2] = 0

    if not cutouts:
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
    text_blocks = [block for block in blocks if block.label in TEXTUAL_LABELS]
    for block in blocks:
        if block.label in FIGURE_LABELS:
            block.outline = visual_outline_from_text_cutouts(block, text_blocks)


def block_preview_label(block: Block) -> str:
    block_number = block.ident.split("_", 1)[0] if block.ident else "?"
    label = "schematic" if block.label == "schematic/circuit" else block.label
    if block.label in TEXTUAL_LABELS and block.orientation != "unknown":
        label = f"{label} {block.orientation}"
    return f"#{block_number} {label} {block.confidence:.2f}"


def preview_label_anchor(block: Block, default_x: int, default_y: int, scale: float) -> tuple[int, int]:
    if not block.outline:
        return default_x, default_y

    horizontal_segments: list[tuple[int, int, int]] = []
    top_points: list[tuple[int, int]] = []
    for polygon in block.outline:
        if len(polygon) < 2:
            continue
        scaled_points = [(int(round(px * scale)), int(round(py * scale))) for px, py in polygon]
        top_points.extend(scaled_points)
        closed_points = scaled_points + [scaled_points[0]]
        for (x1, y1), (x2, y2) in zip(closed_points, closed_points[1:]):
            if abs(y1 - y2) > 1:
                continue
            left = min(x1, x2)
            right = max(x1, x2)
            if right - left < 8:
                continue
            horizontal_segments.append((min(y1, y2), left, right))

    if horizontal_segments:
        top_y = min(segment[0] for segment in horizontal_segments)
        top_segments = [segment for segment in horizontal_segments if abs(segment[0] - top_y) <= 1]
        _, left, _ = min(top_segments, key=lambda segment: segment[1])
        return left, top_y

    if top_points:
        top_y = min(y for _, y in top_points)
        left = min(x for x, y in top_points if abs(y - top_y) <= 1)
        return left, top_y

    return default_x, default_y


def block_counts_text(blocks: Iterable[Block]) -> str:
    counts: dict[str, int] = {}
    for block in blocks:
        label = "schematic" if block.label == "schematic/circuit" else block.label
        counts[label] = counts.get(label, 0) + 1
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items())) or "none"


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


def small_text_artifact_near_visual(block: Block, visual: Block) -> bool:
    if block.ident == visual.ident or block.label != "text" or visual.label not in TEXT_ARTIFACT_VISUAL_LABELS:
        return False

    block_box = box_from_list(block.bbox)
    visual_box = box_from_list(visual.bbox)
    if block_box.area <= 0 or visual_box.area <= block_box.area:
        return False

    small = block_box.area <= visual_box.area * TEXT_ARTIFACT_MAX_AREA_RATIO
    thin = block_box.h <= max(TEXT_ARTIFACT_MAX_HEIGHT_PX, int(round(visual_box.h * TEXT_ARTIFACT_MAX_HEIGHT_RATIO)))
    narrow = block_box.w <= max(80, int(round(visual_box.w * TEXT_ARTIFACT_MAX_WIDTH_RATIO)))
    if not (small and thin and narrow):
        return False

    margin = max(12, int(round(min(visual_box.w, visual_box.h) * TEXT_ARTIFACT_TOUCH_MARGIN_RATIO)))
    vertical_overlap = box_vertical_overlap_height(block_box, visual_box)
    horizontal_overlap = box_horizontal_overlap_width(block_box, visual_box)
    touches_left_or_right = (
        0 <= block_box.x - visual_box.x2 <= margin or 0 <= visual_box.x - block_box.x2 <= margin
    ) and vertical_overlap >= block_box.h * TEXT_ARTIFACT_MIN_OVERLAP_RATIO
    touches_top_or_bottom = (
        0 <= block_box.y - visual_box.y2 <= margin or 0 <= visual_box.y - block_box.y2 <= margin
    ) and horizontal_overlap >= block_box.w * TEXT_ARTIFACT_MIN_OVERLAP_RATIO
    mostly_inside = intersection_area(block_box, visual_box) / max(1, block_box.area) >= 0.45
    return touches_left_or_right or touches_top_or_bottom or mostly_inside


def suppress_small_text_artifacts_near_visuals(blocks: list[Block]) -> list[Block]:
    visual_blocks = [block for block in blocks if block.label in TEXT_ARTIFACT_VISUAL_LABELS]
    if not visual_blocks:
        return blocks

    suppressed = {
        block.ident
        for block in blocks
        if any(small_text_artifact_near_visual(block, visual) for visual in visual_blocks)
    }
    if not suppressed:
        return blocks
    return [block for block in blocks if block.ident not in suppressed]


def text_fragment_axes(block: Block, box: Box) -> tuple[int, int]:
    if block.orientation == "vertical":
        return box.h, box.w
    if block.orientation == "horizontal":
        return box.w, box.h
    return max(box.w, box.h), min(box.w, box.h)


def minimum_text_reading_length(cross_axis: int, glyph_widths: float) -> int:
    glyph_based = int(round(max(1, cross_axis) * TEXT_AVERAGE_GLYPH_WIDTH_TO_HEIGHT * glyph_widths))
    return max(TEXT_MIN_ABSOLUTE_WIDTH_PX, glyph_based)


def text_fragment_inside_visual(text_box: Box, visual_blocks: list[Block]) -> bool:
    for visual in visual_blocks:
        visual_box = box_from_list(visual.bbox)
        if visual_box.area <= text_box.area:
            continue
        overlap_fraction = intersection_area(text_box, visual_box) / max(1, text_box.area)
        if overlap_fraction >= TEXT_FRAGMENT_INSIDE_VISUAL_MIN_OVERLAP_RATIO:
            return True
    return False


def dense_multiline_text_block(block: Block, box: Box) -> bool:
    if (
        box.w < TEXT_MIN_ABSOLUTE_WIDTH_PX * TEXT_DENSE_MULTILINE_MIN_WIDTH_MULTIPLIER
        or box.h < TEXT_MIN_ABSOLUTE_HEIGHT_PX * TEXT_DENSE_MULTILINE_MIN_HEIGHT_MULTIPLIER
    ):
        return False
    features = block.features
    saturation = float(features.get("saturation_p80", 0.0))
    max_text_score = float(features.get("max_text_score", 0.0))
    textline_density = float(features.get("textline_density", 0.0))
    large_plain_text = (
        box.w >= TEXT_MIN_ABSOLUTE_WIDTH_PX * TEXT_DENSE_MULTILINE_LARGE_WIDTH_MULTIPLIER
        and box.h >= TEXT_MIN_ABSOLUTE_HEIGHT_PX * TEXT_DENSE_MULTILINE_LARGE_HEIGHT_MULTIPLIER
        and float(features.get("ink_density", 0.0)) >= TEXT_DENSE_MULTILINE_MIN_INK_DENSITY
        and max(float(features.get("hline_density", 0.0)), float(features.get("vline_density", 0.0)))
        <= TEXT_DENSE_MULTILINE_MAX_AXIS_LINE_DENSITY
        and float(features.get("line_balance", 0.0)) <= TEXT_DENSE_MULTILINE_MAX_LINE_BALANCE
        and saturation <= TEXT_DENSE_MULTILINE_MAX_SATURATION
    )
    if large_plain_text:
        return True
    colored_background_text = (
        saturation <= TEXT_DENSE_MULTILINE_COLOR_MAX_SATURATION
        and max_text_score >= TEXT_DENSE_MULTILINE_COLOR_MIN_TEXT_SCORE
        and textline_density >= TEXT_DENSE_MULTILINE_COLOR_MIN_TEXTLINE_DENSITY
    )
    return (
        max_text_score >= TEXT_DENSE_MULTILINE_MIN_TEXT_SCORE
        and textline_density >= TEXT_DENSE_MULTILINE_MIN_TEXTLINE_DENSITY
        and (saturation <= TEXT_DENSE_MULTILINE_MAX_SATURATION or colored_background_text)
    )


def tiny_text_fragment(block: Block, visual_blocks: list[Block]) -> bool:
    if block.label != "text":
        return False

    box = box_from_list(block.bbox)
    if box.area <= 0:
        return True
    if dense_multiline_text_block(block, box):
        return False

    reading_axis, cross_axis = text_fragment_axes(block, box)
    if cross_axis < TEXT_MIN_ABSOLUTE_HEIGHT_PX:
        return True

    min_reading = minimum_text_reading_length(cross_axis, TEXT_MIN_GLYPH_WIDTHS)
    if reading_axis < min_reading:
        return True

    if TEXT_FRAGMENT_SUPPRESS_INSIDE_VISUALS and visual_blocks and text_fragment_inside_visual(box, visual_blocks):
        inside_visual_limit = minimum_text_reading_length(cross_axis, TEXT_FRAGMENT_INSIDE_VISUAL_MAX_GLYPH_WIDTHS)
        if reading_axis < inside_visual_limit:
            return True

    return False


def suppress_tiny_text_fragments(blocks: list[Block]) -> list[Block]:
    visual_blocks = [block for block in blocks if block.label in FIGURE_LABELS]
    suppressed = {block.ident for block in blocks if tiny_text_fragment(block, visual_blocks)}
    if not suppressed:
        return blocks
    return [block for block in blocks if block.ident not in suppressed]


def text_block_inside_text_block(inner_block: Block, outer_block: Block) -> bool:
    if inner_block.ident == outer_block.ident or inner_block.label not in TEXTUAL_LABELS or outer_block.label not in TEXTUAL_LABELS:
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
    text_blocks = [block for block in blocks if block.label in TEXTUAL_LABELS]
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


def box_horizontal_overlap_width(first: Box, second: Box) -> int:
    return max(0, min(first.x2, second.x2) - max(first.x, second.x))


def box_vertical_overlap_height(first: Box, second: Box) -> int:
    return max(0, min(first.y2, second.y2) - max(first.y, second.y))


def line_bridge_between_schematic_boxes(line_mask, first: Box, second: Box, width: int, height: int) -> bool:
    margin = max(8, min(width, height) // 140)
    pad = max(3, min(width, height) // 360)

    direct_overlap = overlap_area(first, second)
    if direct_overlap / max(1, min(first.area, second.area)) >= 0.12:
        return True

    vertical_gap = max(0, max(first.y, second.y) - min(first.y2, second.y2))
    horizontal_overlap = box_horizontal_overlap_width(first, second)
    if vertical_gap <= margin and horizontal_overlap >= min(first.w, second.w) * 0.22:
        upper, lower = (first, second) if first.y <= second.y else (second, first)
        x1 = max(0, max(upper.x, lower.x) - pad)
        x2 = min(width, min(upper.x2, lower.x2) + pad)
        top_band = line_mask[max(0, upper.y2 - pad) : min(height, upper.y2 + pad + 1), x1:x2]
        bottom_band = line_mask[max(0, lower.y - pad) : min(height, lower.y + pad + 1), x1:x2]
        if top_band.size > 0 and bottom_band.size > 0:
            top_columns = (top_band > 0).sum(axis=0) >= max(1, int(round(top_band.shape[0] * 0.08)))
            bottom_columns = (bottom_band > 0).sum(axis=0) >= max(1, int(round(bottom_band.shape[0] * 0.08)))
            shared_columns = int(np.logical_and(top_columns, bottom_columns).sum())
            if shared_columns >= max(2, int(round((x2 - x1) * 0.003))):
                return True

        seam = line_mask[max(0, upper.y2) : min(height, lower.y), x1:x2]
        if vertical_gap <= max(3, margin // 2) and seam.size > 0:
            if int((seam > 0).sum()) >= max(4, int(round(seam.size * 0.001))):
                return True

    horizontal_gap = max(0, max(first.x, second.x) - min(first.x2, second.x2))
    vertical_overlap = box_vertical_overlap_height(first, second)
    if horizontal_gap <= margin and vertical_overlap >= min(first.h, second.h) * 0.22:
        left, right = (first, second) if first.x <= second.x else (second, first)
        y1 = max(0, max(left.y, right.y) - pad)
        y2 = min(height, min(left.y2, right.y2) + pad)
        left_band = line_mask[y1:y2, max(0, left.x2 - pad) : min(width, left.x2 + pad + 1)]
        right_band = line_mask[y1:y2, max(0, right.x - pad) : min(width, right.x + pad + 1)]
        if left_band.size > 0 and right_band.size > 0:
            left_rows = (left_band > 0).sum(axis=1) >= max(1, int(round(left_band.shape[1] * 0.08)))
            right_rows = (right_band > 0).sum(axis=1) >= max(1, int(round(right_band.shape[1] * 0.08)))
            shared_rows = int(np.logical_and(left_rows, right_rows).sum())
            if shared_rows >= max(2, int(round((y2 - y1) * 0.003))):
                return True

        seam = line_mask[y1:y2, max(0, left.x2) : min(width, right.x)]
        if horizontal_gap <= max(3, margin // 2) and seam.size > 0:
            if int((seam > 0).sum()) >= max(4, int(round(seam.size * 0.001))):
                return True

    return False


def merged_classified_item(
    items: list[tuple[Block, Box]],
    label: str,
    ident: str,
    image,
    mask,
    edges,
    ann,
    scale: float,
    width: int,
    height: int,
    marker: str,
) -> tuple[Block, Box]:
    merged_box = items[0][1]
    for _, box in items[1:]:
        merged_box = union_box(merged_box, box)
    merged_box = merged_box.clamp(width, height)
    original_box = Box(
        int(round(merged_box.x / scale)),
        int(round(merged_box.y / scale)),
        int(round(merged_box.w / scale)),
        int(round(merged_box.h / scale)),
    )
    features = feature_dict(image, mask, edges, merged_box)
    _, merged_confidence = classify_features(ann, features)
    rounded_features = {key: round(float(value), 5) for key, value in features.items()}
    rounded_features["merged_block_count"] = round(
        sum(float(block.features.get("merged_block_count", 1.0)) for block, _ in items),
        5,
    )
    rounded_features[marker] = 1.0
    block = Block(
        ident=ident,
        label=label,
        orientation="unknown",
        confidence=round(max([block.confidence for block, _ in items] + [merged_confidence]), 4),
        bbox=original_box.to_list(),
        outline=None,
        features=rounded_features,
    )
    return block, merged_box


def split_text_columns_in_classified_blocks(
    classified: list[tuple[Block, Box]],
    image,
    mask,
    edges,
    ann,
    scale: float,
    width: int,
    height: int,
) -> list[tuple[Block, Box]]:
    result: list[tuple[Block, Box]] = []
    for block, box in classified:
        if block.label != "text":
            result.append((block, box))
            continue

        contents_column_split = float(block.features.get("contents_row_merge", 0.0)) >= 0.5
        if contents_column_split:
            pieces = split_contents_row_merged_text_box_by_column_gaps(mask, box, width, height)
        else:
            pieces = split_multiline_text_box_recursive(mask, box, width, height)
        if len(pieces) <= 1:
            result.append((block, box))
            continue

        block_number = block.ident.split("_", 1)[0]
        for index, piece in enumerate(pieces):
            features = feature_dict(image, mask, edges, piece)
            label, confidence = classify_features(ann, features)
            if label != "text":
                label = "text"
                confidence = max(confidence, block.confidence)
            orientation = infer_orientation(features)
            original_box = Box(
                int(round(piece.x / scale)),
                int(round(piece.y / scale)),
                int(round(piece.w / scale)),
                int(round(piece.h / scale)),
            )
            suffix = chr(ord("a") + index) if index < 26 else str(index + 1)
            rounded_features = {key: round(float(value), 5) for key, value in features.items()}
            if contents_column_split:
                rounded_features["contents_column_split"] = 1.0
            result.append(
                (
                    Block(
                        ident=f"{block_number}{suffix}_{safe_label(label)}",
                        label=label,
                        orientation=orientation,
                        confidence=round(confidence, 4),
                        bbox=original_box.to_list(),
                        outline=None,
                        features=rounded_features,
                    ),
                    piece,
                )
            )
    return sorted(result, key=lambda item: (item[1].y, item[1].x))


def contents_text_row_strip_candidate(block: Block, box: Box, width: int, height: int) -> bool:
    if block.label not in TEXTUAL_LABELS:
        return False
    if block.orientation not in {"horizontal", "unknown"}:
        return False
    if box.w < width * CONTENTS_ROW_MERGE_MIN_WIDTH_RATIO:
        return False
    if box.h > height * CONTENTS_ROW_MERGE_MAX_HEIGHT_RATIO:
        return False
    if box.h < max(6, int(round(height * 0.006))):
        return False

    features = block.features
    text_score = float(features.get("max_text_score", 0.0))
    line_art = float(features.get("line_art_score", 0.0))
    saturation = float(features.get("saturation_p80", 0.0))
    if text_score < 0.20:
        return False
    if line_art > 0.62 and saturation > 0.18:
        return False
    return True


def contents_text_rows_are_adjacent(first: Box, second: Box, width: int, height: int) -> bool:
    if second.y < first.y:
        first, second = second, first
    vertical_gap = second.y - first.y2
    max_gap = max(
        CONTENTS_ROW_MERGE_MAX_VERTICAL_GAP_PX,
        int(round(height * CONTENTS_ROW_MERGE_MAX_VERTICAL_GAP_RATIO)),
    )
    if vertical_gap < 0 or vertical_gap > max_gap:
        return False

    overlap = box_horizontal_overlap_width(first, second)
    if overlap < min(first.w, second.w) * CONTENTS_ROW_MERGE_MIN_HORIZONTAL_OVERLAP:
        return False

    width_similarity = min(first.w, second.w) / max(1, max(first.w, second.w))
    if width_similarity < CONTENTS_ROW_MERGE_MIN_WIDTH_SIMILARITY:
        return False

    x_drift = abs(first.x - second.x)
    x2_drift = abs(first.x2 - second.x2)
    drift_limit = max(24, int(round(width * 0.035)))
    return x_drift <= drift_limit and x2_drift <= drift_limit


def merge_fragmented_contents_text_rows(
    classified: list[tuple[Block, Box]],
    image,
    mask,
    edges,
    ann,
    scale: float,
    width: int,
    height: int,
) -> list[tuple[Block, Box]]:
    if len(classified) < CONTENTS_ROW_MERGE_MIN_RUN:
        return classified

    result: list[tuple[Block, Box]] = []
    run: list[tuple[Block, Box]] = []

    def flush_run() -> None:
        nonlocal run
        if len(run) < CONTENTS_ROW_MERGE_MIN_RUN:
            result.extend(run)
            run = []
            return

        merged_box = run[0][1]
        for _, box in run[1:]:
            merged_box = union_box(merged_box, box)
        total_height_ratio = merged_box.h / max(1, height)
        if not (
            CONTENTS_ROW_MERGE_MIN_TOTAL_HEIGHT_RATIO
            <= total_height_ratio
            <= CONTENTS_ROW_MERGE_MAX_TOTAL_HEIGHT_RATIO
        ):
            result.extend(run)
            run = []
            return

        first_number = run[0][0].ident.split("_", 1)[0]
        merged = merged_classified_item(
            run,
            "text",
            f"{first_number}_text",
            image,
            mask,
            edges,
            ann,
            scale,
            width,
            height,
            "contents_row_merge",
        )
        result.append(merged)
        run = []

    for item in sorted(classified, key=lambda entry: (entry[1].y, entry[1].x)):
        block, box = item
        if not contents_text_row_strip_candidate(block, box, width, height):
            flush_run()
            result.append(item)
            continue
        if not run:
            run.append(item)
            continue
        if contents_text_rows_are_adjacent(run[-1][1], box, width, height):
            run.append(item)
        else:
            flush_run()
            run.append(item)
    flush_run()

    return sorted(result, key=lambda item: (item[1].y, item[1].x))


def contents_heading_split_candidate(block: Block, box: Box, width: int, height: int) -> bool:
    if block.label != "text":
        return False
    if float(block.features.get("contents_row_merge", 0.0)) < 0.5:
        return False
    if box.w < width * CONTENTS_HEADING_SPLIT_MIN_WIDTH_RATIO:
        return False
    if box.h < height * CONTENTS_HEADING_SPLIT_MIN_HEIGHT_RATIO:
        return False
    return True


def annual_contents_heading_split(mask, box: Box, page_width: int, page_height: int) -> tuple[int, int] | None:
    min_gap = max(CONTENTS_HEADING_SPLIT_MIN_GAP_PX, int(round(box.h * 0.010)))
    candidates: list[tuple[int, float, int, int]] = []
    for start, end, mean_density in horizontal_whitespace_corridor_runs(mask, box, min_gap):
        center = (start + end) // 2
        ratio = center / max(1, box.h)
        if not (CONTENTS_HEADING_SPLIT_MIN_RATIO <= ratio <= CONTENTS_HEADING_SPLIT_MAX_RATIO):
            continue
        top = Box(box.x, box.y, box.w, start)
        bottom_start = min(box.h, end + 1)
        bottom = Box(box.x, box.y + bottom_start, box.w, box.h - bottom_start)
        if text_row_run_count(mask, top) < 2:
            continue
        if text_row_run_count(mask, bottom) < CONTENTS_HEADING_SPLIT_MIN_BODY_ROWS:
            continue
        gap_height = end - start + 1
        preferred_ratio = 0.18
        ratio_score = 1.0 - abs(ratio - preferred_ratio)
        candidates.append((gap_height, ratio_score - mean_density, start, end))

    if not candidates:
        return None
    _, _, start, end = max(candidates)
    return start, end


def split_annual_contents_heading_blocks(
    classified: list[tuple[Block, Box]],
    image,
    mask,
    edges,
    ann,
    scale: float,
    width: int,
    height: int,
) -> list[tuple[Block, Box]]:
    result: list[tuple[Block, Box]] = []
    for block, box in classified:
        split_gap = None
        if contents_heading_split_candidate(block, box, width, height):
            split_gap = annual_contents_heading_split(mask, box, width, height)
        if split_gap is None:
            result.append((block, box))
            continue

        gap_start, gap_end = split_gap
        bottom_start = min(box.h, gap_end + 1)
        top_box = Box(box.x, box.y, box.w, gap_start).clamp(width, height)
        bottom_box = Box(box.x, box.y + bottom_start, box.w, box.h - bottom_start).clamp(width, height)
        if top_box.area <= 0 or bottom_box.area <= 0:
            result.append((block, box))
            continue

        block_number = block.ident.split("_", 1)[0]
        for label, piece, suffix in (("heading", top_box, ""), ("text", bottom_box, "b")):
            features = feature_dict(image, mask, edges, piece)
            _, confidence = classify_features(ann, features)
            original_box = Box(
                int(round(piece.x / scale)),
                int(round(piece.y / scale)),
                int(round(piece.w / scale)),
                int(round(piece.h / scale)),
            )
            rounded_features = {key: round(float(value), 5) for key, value in features.items()}
            rounded_features["annual_contents_heading_split"] = 1.0
            ident_number = f"{block_number}{suffix}"
            result.append(
                (
                    Block(
                        ident=f"{ident_number}_{label}",
                        label=label,
                        orientation=infer_orientation(features),
                        confidence=round(max(confidence, block.confidence), 4),
                        bbox=original_box.to_list(),
                        outline=None,
                        features=rounded_features,
                    ),
                    piece,
                )
            )

    return sorted(result, key=lambda item: (item[1].y, item[1].x))


def adjacent_heading_fragments(first: tuple[Block, Box], second: tuple[Block, Box], width: int, height: int) -> bool:
    first_block, first_box = first
    second_block, second_box = second
    if first_block.label != "heading" or second_block.label != "heading":
        return False
    if first_box.y > second_box.y:
        first_box, second_box = second_box, first_box

    union = union_box(first_box, second_box)
    if union.h > height * HEADING_FRAGMENT_MERGE_MAX_HEIGHT_RATIO:
        return False
    if union.w > width * HEADING_FRAGMENT_MERGE_MAX_WIDTH_RATIO:
        return False
    if union.y < height * HEADING_FRAGMENT_MERGE_MIN_TOP_RATIO:
        return False

    vertical_overlap = box_vertical_overlap_height(first_box, second_box)
    center_delta = abs((first_box.y + first_box.h / 2.0) - (second_box.y + second_box.h / 2.0))
    horizontal_gap = max(0, max(first_box.x, second_box.x) - min(first_box.x2, second_box.x2))
    vertical_gap = max(0, max(first_box.y, second_box.y) - min(first_box.y2, second_box.y2))
    horizontal_overlap = box_horizontal_overlap_width(first_box, second_box)
    stacked_gap_limit = max(
        HEADING_FRAGMENT_STACKED_MAX_VERTICAL_GAP_PX,
        int(round(height * HEADING_FRAGMENT_STACKED_MAX_VERTICAL_GAP_RATIO)),
    )
    stacked_drift_limit = max(
        HEADING_FRAGMENT_STACKED_MAX_X_DRIFT_PX,
        int(round(width * HEADING_FRAGMENT_STACKED_MAX_X_DRIFT_RATIO)),
    )
    inline_gap_limit = max(
        HEADING_FRAGMENT_INLINE_MAX_HORIZONTAL_GAP_PX,
        int(round(width * HEADING_FRAGMENT_INLINE_MAX_HORIZONTAL_GAP_RATIO)),
    )
    stacked_title_lines = (
        vertical_gap <= stacked_gap_limit
        and horizontal_overlap >= min(first_box.w, second_box.w) * HEADING_FRAGMENT_STACKED_MIN_HORIZONTAL_OVERLAP
        and abs(first_box.x - second_box.x) <= stacked_drift_limit
    )
    if stacked_title_lines:
        return True
    return (
        vertical_overlap >= min(first_box.h, second_box.h) * HEADING_FRAGMENT_INLINE_MIN_VERTICAL_OVERLAP
        and center_delta <= max(first_box.h, second_box.h) * HEADING_FRAGMENT_INLINE_MAX_CENTER_DELTA_RATIO
        and horizontal_gap <= inline_gap_limit
    )


def merge_adjacent_heading_fragments(
    classified: list[tuple[Block, Box]],
    image,
    mask,
    edges,
    ann,
    scale: float,
    width: int,
    height: int,
) -> list[tuple[Block, Box]]:
    if len(classified) < 2:
        return classified

    items = classified[:]
    changed = True
    while changed:
        changed = False
        for first_index, first in enumerate(items):
            for second_index in range(first_index + 1, len(items)):
                second = items[second_index]
                if not adjacent_heading_fragments(first, second, width, height):
                    continue
                first_number = first[0].ident.split("_", 1)[0]
                merged_block, merged_box = merged_classified_item(
                    [first, second],
                    "heading",
                    f"{first_number}_heading",
                    image,
                    mask,
                    edges,
                    ann,
                    scale,
                    width,
                    height,
                    "heading_fragment_merge",
                )
                merged_block.orientation = "horizontal"
                items[first_index] = (merged_block, merged_box)
                del items[second_index]
                changed = True
                break
            if changed:
                break

    return sorted(items, key=lambda item: (item[1].y, item[1].x))


def top_display_heading_band(
    block: Block,
    box: Box,
    image,
    mask,
    edges,
    width: int,
    height: int,
) -> Box | None:
    if block.label != "text":
        return None
    if box.w < width * TOP_DISPLAY_HEADING_MIN_CONTAINER_WIDTH_RATIO:
        return None
    if box.h < height * TOP_DISPLAY_HEADING_MIN_CONTAINER_HEIGHT_RATIO:
        return None

    roi = mask[box.y : box.y2, box.x : box.x2]
    if roi.size == 0:
        return None

    scan_height = min(box.h, max(1, int(round(box.h * TOP_DISPLAY_HEADING_SCAN_HEIGHT_RATIO))))
    projection = (roi[:scan_height] > 0).sum(axis=1)
    smoothed = smooth_projection(projection, max(3, box.h // 120))
    runs = projection_runs(
        smoothed,
        max(
            INTERNAL_DISPLAY_HEADING_PROJECTION_MIN_PX,
            box.w * INTERNAL_DISPLAY_HEADING_PROJECTION_WIDTH_RATIO,
        ),
        max(
            TOP_DISPLAY_HEADING_MIN_RUN_PX,
            int(round(box.h * TOP_DISPLAY_HEADING_MIN_RUN_HEIGHT_RATIO)),
        ),
    )
    if not runs:
        return None

    top_limit = max(
        TOP_DISPLAY_HEADING_MAX_TOP_OFFSET_PX,
        int(round(box.h * TOP_DISPLAY_HEADING_MAX_TOP_OFFSET_RATIO)),
    )
    first_start, band_end = runs[0]
    if first_start > top_limit:
        return None

    gap_limit = max(
        TOP_DISPLAY_HEADING_MAX_RUN_GAP_PX,
        int(round(box.h * TOP_DISPLAY_HEADING_MAX_RUN_GAP_RATIO)),
    )
    for start, end in runs[1:]:
        if start - band_end - 1 > gap_limit:
            break
        band_end = end

    pad = max(3, box.h // 80)
    band = Box(box.x, box.y + first_start, box.w, band_end - first_start + 1).inflate(pad, width, height)
    if band.y <= box.y:
        band = Box(band.x, box.y, band.w, band.y2 - box.y).clamp(width, height)

    bottom_height = box.y2 - band.y2
    min_text_height = max(
        INTERNAL_DISPLAY_HEADING_MIN_TEXT_PX,
        int(round(height * INTERNAL_DISPLAY_HEADING_MIN_TEXT_HEIGHT_RATIO)),
    )
    if bottom_height < min_text_height:
        return None

    features = feature_dict(image, mask, edges, band)
    if not top_display_heading_features(features):
        return None
    if features["height_ratio"] < TOP_DISPLAY_HEADING_MIN_HEIGHT_RATIO:
        return None
    if features["area_ratio"] < TOP_DISPLAY_HEADING_MIN_AREA_RATIO:
        return None
    return band


def internal_display_heading_band(
    block: Block,
    box: Box,
    image,
    mask,
    edges,
    width: int,
    height: int,
) -> Box | None:
    if block.label != "text":
        return None
    if box.w < width * INTERNAL_DISPLAY_HEADING_MIN_WIDTH_RATIO:
        return None
    if box.h < height * INTERNAL_DISPLAY_HEADING_MIN_HEIGHT_RATIO:
        return None
    if box.area / max(1, width * height) < INTERNAL_DISPLAY_HEADING_MIN_AREA_RATIO:
        return None

    roi = mask[box.y : box.y2, box.x : box.x2]
    if roi.size == 0:
        return None
    projection = (roi > 0).sum(axis=1)
    smoothed = smooth_projection(projection, max(3, box.h // 120))
    runs = projection_runs(
        smoothed,
        max(
            INTERNAL_DISPLAY_HEADING_PROJECTION_MIN_PX,
            box.w * INTERNAL_DISPLAY_HEADING_PROJECTION_WIDTH_RATIO,
        ),
        max(
            INTERNAL_DISPLAY_HEADING_MIN_RUN_PX,
            int(round(box.h * INTERNAL_DISPLAY_HEADING_MIN_RUN_HEIGHT_RATIO)),
        ),
    )
    if not runs:
        return None

    candidates: list[tuple[float, Box]] = []
    pad = max(3, box.h // 80)
    for start, end in runs:
        if start < box.h * INTERNAL_DISPLAY_HEADING_TOP_SKIP_RATIO:
            continue
        band = Box(box.x, box.y + start, box.w, end - start + 1).inflate(pad, width, height)
        if band.y <= box.y:
            continue
        top_height = band.y - box.y
        if top_height < max(
            INTERNAL_DISPLAY_HEADING_TOP_TEXT_MIN_PX,
            int(round(height * INTERNAL_DISPLAY_HEADING_TOP_TEXT_MIN_RATIO)),
        ):
            continue
        features = feature_dict(image, mask, edges, band)
        if not bold_display_heading_features(features):
            continue
        score = float(features.get("ink_density", 0.0)) + INTERNAL_DISPLAY_HEADING_SCORE_GRAY_STD_WEIGHT * float(
            features.get("gray_std", 0.0)
        )
        candidates.append((score, band))

    if not candidates:
        return None
    _, best = max(candidates, key=lambda item: item[0])
    return best


def split_internal_display_heading_blocks(
    classified: list[tuple[Block, Box]],
    image,
    mask,
    edges,
    ann,
    scale: float,
    width: int,
    height: int,
) -> list[tuple[Block, Box]]:
    result: list[tuple[Block, Box]] = []
    min_text_height = max(
        INTERNAL_DISPLAY_HEADING_MIN_TEXT_PX,
        int(round(height * INTERNAL_DISPLAY_HEADING_MIN_TEXT_HEIGHT_RATIO)),
    )

    for block, box in classified:
        heading_box = top_display_heading_band(block, box, image, mask, edges, width, height)
        split_marker = "top_display_heading_split"
        if heading_box is None:
            heading_box = internal_display_heading_band(block, box, image, mask, edges, width, height)
            split_marker = "internal_display_heading_split"
        if heading_box is None:
            result.append((block, box))
            continue

        pieces: list[tuple[str, Box, str]] = []
        top_box = Box(box.x, box.y, box.w, max(0, heading_box.y - box.y)).clamp(width, height)
        if top_box.h >= min_text_height:
            pieces.append(("text", top_box, "a"))
        pieces.append(("heading", heading_box, "b" if pieces else ""))

        bottom_y = heading_box.y2
        bottom_box = Box(box.x, bottom_y, box.w, max(0, box.y2 - bottom_y)).clamp(width, height)
        if bottom_box.h >= min_text_height:
            pieces.append(("text", bottom_box, chr(ord("a") + len(pieces))))

        block_number = block.ident.split("_", 1)[0]
        for label, piece, suffix in pieces:
            features = feature_dict(image, mask, edges, piece)
            _, confidence = classify_features(ann, features)
            original_box = Box(
                int(round(piece.x / scale)),
                int(round(piece.y / scale)),
                int(round(piece.w / scale)),
                int(round(piece.h / scale)),
            )
            rounded_features = {key: round(float(value), 5) for key, value in features.items()}
            rounded_features[split_marker] = 1.0
            ident_number = f"{block_number}{suffix}"
            result.append(
                (
                    Block(
                        ident=f"{ident_number}_{label}",
                        label=label,
                        orientation="horizontal" if label == "heading" else infer_orientation(features),
                        confidence=round(max(confidence, block.confidence if label == "text" else 0.0), 4),
                        bbox=original_box.to_list(),
                        outline=None,
                        features=rounded_features,
                    ),
                    piece,
                )
            )

    return sorted(result, key=lambda item: (item[1].y, item[1].x))


def contents_column_fragment_candidate(block: Block, box: Box, width: int) -> bool:
    if block.label not in TEXTUAL_LABELS:
        return False
    if block.orientation not in {"horizontal", "unknown"}:
        return False
    width_ratio = box.w / max(1, width)
    if not (CONTENTS_COLUMN_MERGE_MIN_WIDTH_RATIO <= width_ratio <= CONTENTS_COLUMN_MERGE_MAX_WIDTH_RATIO):
        return False
    if box.h <= 0:
        return False
    features = block.features
    if float(features.get("max_text_score", 0.0)) < 0.20:
        return False
    if float(features.get("saturation_p80", 0.0)) > 0.22 and float(features.get("line_art_score", 0.0)) > 0.55:
        return False
    return True


def contents_column_fragments_are_adjacent(first: Box, second: Box, width: int, height: int) -> bool:
    if second.y < first.y:
        first, second = second, first
    vertical_gap = second.y - first.y2
    max_gap = max(
        CONTENTS_COLUMN_MERGE_MAX_VERTICAL_GAP_PX,
        int(round(height * CONTENTS_COLUMN_MERGE_MAX_VERTICAL_GAP_RATIO)),
    )
    if vertical_gap < 0 or vertical_gap > max_gap:
        return False

    overlap = box_horizontal_overlap_width(first, second)
    if overlap < min(first.w, second.w) * CONTENTS_COLUMN_MERGE_MIN_HORIZONTAL_OVERLAP:
        return False

    width_similarity = min(first.w, second.w) / max(1, max(first.w, second.w))
    if width_similarity < CONTENTS_COLUMN_MERGE_MIN_WIDTH_SIMILARITY:
        return False

    drift_limit = max(18, int(round(width * 0.025)))
    return abs(first.x - second.x) <= drift_limit and abs(first.x2 - second.x2) <= drift_limit


def merge_fragmented_contents_columns(
    classified: list[tuple[Block, Box]],
    image,
    mask,
    edges,
    ann,
    scale: float,
    width: int,
    height: int,
) -> list[tuple[Block, Box]]:
    candidates = [
        item
        for item in classified
        if contents_column_fragment_candidate(item[0], item[1], width)
    ]
    if len(candidates) < 2:
        return classified

    consumed: set[str] = set()
    merged_items: list[tuple[Block, Box]] = []
    for seed_block, seed_box in sorted(candidates, key=lambda item: (item[1].x, item[1].y)):
        if seed_block.ident in consumed:
            continue
        group = [(seed_block, seed_box)]
        consumed.add(seed_block.ident)
        changed = True
        while changed:
            changed = False
            current_box = group[0][1]
            for _, box in group[1:]:
                current_box = union_box(current_box, box)
            for block, box in sorted(candidates, key=lambda item: (item[1].y, item[1].x)):
                if block.ident in consumed:
                    continue
                if contents_column_fragments_are_adjacent(current_box, box, width, height):
                    group.append((block, box))
                    consumed.add(block.ident)
                    changed = True

        if len(group) < 2:
            consumed.remove(seed_block.ident)
            continue

        first_number = sorted(group, key=lambda item: (item[1].y, item[1].x))[0][0].ident.split("_", 1)[0]
        merged_items.append(
            merged_classified_item(
                group,
                "text",
                f"{first_number}_text",
                image,
                mask,
                edges,
                ann,
                scale,
                width,
                height,
                "contents_column_merge",
            )
        )

    if not merged_items:
        return classified

    result = [item for item in classified if item[0].ident not in consumed]
    result.extend(merged_items)
    return sorted(result, key=lambda item: (item[1].y, item[1].x))


def contents_number_column_candidate(block: Block, box: Box, width: int, height: int) -> bool:
    if block.label not in TEXTUAL_LABELS:
        return False
    if box.w > width * CONTENTS_NUMBER_COLUMN_MAX_WIDTH_RATIO:
        return False
    if box.h < height * CONTENTS_NUMBER_COLUMN_MIN_HEIGHT_RATIO:
        return False
    if box.y < height * 0.025 or box.y2 > height * 0.965:
        return False
    features = block.features
    if float(features.get("max_text_score", 0.0)) < 0.45:
        return False
    if float(features.get("saturation_p80", 0.0)) > 0.12:
        return False
    if max(float(features.get("hline_density", 0.0)), float(features.get("vline_density", 0.0))) > 0.16:
        return False
    return block.orientation in {"vertical", "diagonal"} or box.w < width * 0.075


def contents_number_column_target(block: Block, box: Box, number_box: Box, width: int, height: int) -> bool:
    if block.label not in TEXTUAL_LABELS:
        return False
    if block.orientation not in {"horizontal", "unknown"}:
        return False
    if box.area <= 0:
        return False
    if box.h < height * 0.045 or box.w < width * 0.18:
        return False

    horizontal_gap = min(abs(number_box.x - box.x2), abs(box.x - number_box.x2))
    if horizontal_gap > max(8, int(round(width * CONTENTS_NUMBER_COLUMN_MAX_GAP_RATIO))):
        return False

    overlap = box_vertical_overlap_height(box, number_box)
    if overlap <= 0:
        return False
    target_overlap = overlap / max(1, box.h)
    number_overlap = overlap / max(1, number_box.h)
    return (
        target_overlap >= CONTENTS_NUMBER_COLUMN_MIN_TARGET_OVERLAP
        or number_overlap >= CONTENTS_NUMBER_COLUMN_MIN_TARGET_OVERLAP
    )


def contents_number_column_horizontal_gap(box: Box, number_box: Box) -> int:
    if number_box.x >= box.x2:
        return number_box.x - box.x2
    if box.x >= number_box.x2:
        return box.x - number_box.x2
    return 0


def contents_number_column_target_side(box: Box, number_box: Box) -> str:
    if number_box.x >= box.x2:
        return "left"
    if box.x >= number_box.x2:
        return "right"
    if box.x <= number_box.x and box.x2 >= number_box.x2:
        return "contains"
    return "overlap"


def closest_contents_number_column_targets(
    targets: list[tuple[Block, Box]],
    number_box: Box,
    width: int,
) -> list[tuple[Block, Box]]:
    if len(targets) < 2:
        return targets

    min_gap = min(contents_number_column_horizontal_gap(box, number_box) for _, box in targets)
    gap_slack = max(4, int(round(width * 0.006)))
    nearest = [
        item
        for item in targets
        if contents_number_column_horizontal_gap(item[1], number_box) <= min_gap + gap_slack
    ]
    for side in ("left", "contains", "overlap", "right"):
        same_side = [
            item
            for item in nearest
            if contents_number_column_target_side(item[1], number_box) == side
        ]
        if same_side:
            return same_side
    return nearest


def merge_contents_number_columns_once(
    classified: list[tuple[Block, Box]],
    image,
    mask,
    edges,
    ann,
    scale: float,
    width: int,
    height: int,
) -> list[tuple[Block, Box]]:
    number_columns = [
        item
        for item in classified
        if contents_number_column_candidate(item[0], item[1], width, height)
    ]
    if not number_columns:
        return classified

    consumed: set[str] = set()
    merged: list[tuple[Block, Box]] = []
    for number_block, number_box in sorted(number_columns, key=lambda item: (item[1].y, item[1].x)):
        if number_block.ident in consumed:
            continue

        targets = []
        for block, box in classified:
            if block.ident == number_block.ident or block.ident in consumed:
                continue
            if contents_number_column_target(block, box, number_box, width, height):
                targets.append((block, box))

        targets = closest_contents_number_column_targets(targets, number_box, width)
        if not targets:
            continue

        group = [(number_block, number_box), *targets]
        group_box = group[0][1]
        for _, box in group[1:]:
            group_box = union_box(group_box, box)
        target_sides = {contents_number_column_target_side(box, number_box) for _, box in targets}
        if group_box.w > width * CONTENTS_TEXT_MAX_WIDTH_RATIO and target_sides != {"contains"}:
            continue

        consumed.update(block.ident for block, _ in group)
        first_number = sorted(group, key=lambda item: (item[1].y, item[1].x))[0][0].ident.split("_", 1)[0]
        merged.append(
            merged_classified_item(
                group,
                "text",
                f"{first_number}_text",
                image,
                mask,
                edges,
                ann,
                scale,
                width,
                height,
                "contents_number_column_merge",
            )
        )

    if not merged:
        return classified

    result = [item for item in classified if item[0].ident not in consumed]
    result.extend(merged)
    return sorted(result, key=lambda item: (item[1].y, item[1].x))


def merge_contents_number_columns(
    classified: list[tuple[Block, Box]],
    image,
    mask,
    edges,
    ann,
    scale: float,
    width: int,
    height: int,
) -> list[tuple[Block, Box]]:
    result = classified
    for _ in range(3):
        before = [(block.ident, block.label, box.to_list()) for block, box in result]
        merged = merge_contents_number_columns_once(
            result,
            image,
            mask,
            edges,
            ann,
            scale,
            width,
            height,
        )
        after = [(block.ident, block.label, box.to_list()) for block, box in merged]
        if after == before:
            return result
        result = merged
    return result


CONTENTS_COLUMN_GRID_MARKERS = (
    "contents_column_split",
    "contents_column_merge",
    "contents_number_column_merge",
)


def contents_column_grid_snap_candidate(block: Block, box: Box, width: int, height: int) -> bool:
    if block.label != "text":
        return False
    if not any(float(block.features.get(marker, 0.0)) >= 0.5 for marker in CONTENTS_COLUMN_GRID_MARKERS):
        return False
    if box.h < height * CONTENTS_COLUMN_GRID_SNAP_MIN_HEIGHT_RATIO:
        return False
    if box.w < width * CONTENTS_COLUMN_GRID_SNAP_MIN_PIECE_WIDTH_RATIO:
        return False
    return True


def contents_column_grid_bounds(
    group: list[tuple[Block, Box]],
    classified: list[tuple[Block, Box]],
    width: int,
) -> tuple[int, int] | None:
    group_x1 = min(box.x for _, box in group)
    group_x2 = max(box.x2 for _, box in group)
    wide_bounds = [
        box
        for block, box in classified
        if block.label == "image"
        and box.w >= width * CONTENTS_COLUMN_GRID_SNAP_WIDE_BOUNDS_MIN_WIDTH_RATIO
    ]
    if not wide_bounds:
        return None
    return min(group_x1, *(box.x for box in wide_bounds)), max(group_x2, *(box.x2 for box in wide_bounds))


def snap_contents_columns_to_page_grid(
    classified: list[tuple[Block, Box]],
    image,
    mask,
    edges,
    ann,
    scale: float,
    width: int,
    height: int,
) -> list[tuple[Block, Box]]:
    candidates = [
        item
        for item in classified
        if contents_column_grid_snap_candidate(item[0], item[1], width, height)
    ]
    if len(candidates) < 2:
        return classified

    edge_tolerance = max(8, int(round(height * CONTENTS_COLUMN_GRID_SNAP_EDGE_TOLERANCE_RATIO)))
    consumed: set[str] = set()
    replacements: dict[str, tuple[Block, Box]] = {}
    for seed_block, seed_box in sorted(candidates, key=lambda item: (item[1].y, item[1].x)):
        if seed_block.ident in consumed:
            continue
        group = [
            (block, box)
            for block, box in candidates
            if block.ident not in consumed
            and abs(box.y - seed_box.y) <= edge_tolerance
            and abs(box.y2 - seed_box.y2) <= edge_tolerance
        ]
        group = sorted(group, key=lambda item: item[1].x)
        if not (2 <= len(group) <= CONTENTS_COLUMN_GRID_SNAP_MAX_COLUMNS):
            continue

        bounds = contents_column_grid_bounds(group, classified, width)
        if bounds is None:
            continue
        usable_x1, usable_x2 = bounds
        usable_width = usable_x2 - usable_x1
        if usable_width < width * CONTENTS_COLUMN_GRID_SNAP_MIN_TOTAL_WIDTH_RATIO:
            continue

        expected_width = usable_width / float(len(group))
        if expected_width < width * CONTENTS_COLUMN_GRID_SNAP_MIN_PIECE_WIDTH_RATIO:
            continue
        max_deviation = expected_width * CONTENTS_COLUMN_GRID_SNAP_MAX_WIDTH_DEVIATION_RATIO
        if any(abs(box.w - expected_width) > max_deviation for _, box in group):
            continue

        for index, (block, box) in enumerate(group):
            snapped_x1 = int(round(usable_x1 + usable_width * index / len(group)))
            snapped_x2 = int(round(usable_x1 + usable_width * (index + 1) / len(group)))
            snapped = Box(snapped_x1, box.y, max(0, snapped_x2 - snapped_x1), box.h).clamp(width, height)
            if snapped.area <= 0:
                continue

            features = feature_dict(image, mask, edges, snapped)
            label, confidence = classify_features(ann, features)
            if label != "text":
                label = "text"
                confidence = max(confidence, block.confidence)
            rounded_features = {key: round(float(value), 5) for key, value in features.items()}
            for marker in CONTENTS_COLUMN_GRID_MARKERS:
                if float(block.features.get(marker, 0.0)) >= 0.5:
                    rounded_features[marker] = float(block.features[marker])
            rounded_features["contents_column_grid_snap"] = 1.0
            original_box = Box(
                int(round(snapped.x / scale)),
                int(round(snapped.y / scale)),
                int(round(snapped.w / scale)),
                int(round(snapped.h / scale)),
            )
            replacements[block.ident] = (
                Block(
                    ident=block.ident,
                    label="text",
                    orientation=infer_orientation(features),
                    confidence=round(max(confidence, block.confidence), 4),
                    bbox=original_box.to_list(),
                    outline=None,
                    features=rounded_features,
                ),
                snapped,
            )
            consumed.add(block.ident)

    if not replacements:
        return classified
    return sorted((replacements.get(block.ident, (block, box)) for block, box in classified), key=lambda item: (item[1].y, item[1].x))


def merge_connected_schematic_blocks(
    classified: list[tuple[Block, Box]],
    image,
    mask,
    edges,
    ann,
    scale: float,
    width: int,
    height: int,
) -> list[tuple[Block, Box]]:
    if len(classified) < 2:
        return classified

    line_mask = cv2.bitwise_or(mask, edges)
    items = classified[:]
    changed = True
    while changed:
        changed = False
        for first_index in range(len(items)):
            first_block, first_box = items[first_index]
            if first_block.label != "schematic/circuit":
                continue
            for second_index in range(first_index + 1, len(items)):
                second_block, second_box = items[second_index]
                if second_block.label != "schematic/circuit":
                    continue
                if not line_bridge_between_schematic_boxes(line_mask, first_box, second_box, width, height):
                    continue

                merged_block, merged_box = merged_classified_item(
                    [items[first_index], items[second_index]],
                    "schematic/circuit",
                    first_block.ident,
                    image,
                    mask,
                    edges,
                    ann,
                    scale,
                    width,
                    height,
                    "line_bridge_merge",
                )
                items[first_index] = (merged_block, merged_box)
                del items[second_index]
                changed = True
                break
            if changed:
                break

    return sorted(items, key=lambda item: (item[1].y, item[1].x))


def schematic_attachment_candidate(block: Block, box: Box, width: int, height: int) -> bool:
    if block.label == "schematic/circuit":
        return False
    features = block.features
    line_art = float(features.get("line_art_score", 0.0))
    edge = float(features.get("edge_density", 0.0))
    ink = float(features.get("ink_density", 1.0))
    saturation = float(features.get("saturation_p80", 1.0))
    component_signature = float(features.get("component_signature_score", 0.0))
    if single_axis_waveform_diagram_features(features):
        return False
    technical_text_strip = (
        block.label == "text"
        and block.orientation == "horizontal"
        and box.h <= height * 0.055
        and line_art > 0.22
        and edge > 0.12
        and ink < 0.36
        and saturation < 0.10
        and component_signature > 0.45
    )
    low_confidence_text = block.label == "text" and block.confidence < 0.45
    visual_label = block.label in {"diagram", "table", "image", "other"}
    if not (low_confidence_text or technical_text_strip or visual_label):
        return False
    if box.h > height * 0.18:
        return False
    if technical_text_strip:
        return True
    return line_art > 0.24 and edge > 0.16 and ink < 0.22 and saturation < 0.08


def schematic_frame_strip_candidate(block: Block, box: Box, schematic: Box, width: int, height: int) -> bool:
    if block.label not in {"diagram", "image", "other"}:
        return False

    features = block.features
    line_art = float(features.get("line_art_score", 0.0))
    ink = float(features.get("ink_density", 1.0))
    saturation = float(features.get("saturation_p80", 0.0))
    thin_vertical = box.w <= max(40, int(round(schematic.w * 0.075))) and box.h >= schematic.h * 0.72
    thin_horizontal = box.h <= max(40, int(round(schematic.h * 0.075))) and box.w >= schematic.w * 0.72
    if not (thin_vertical or thin_horizontal):
        return False
    if box.area > schematic.area * 0.12:
        return False
    if line_art < 0.10 or ink > 0.12 or saturation > 0.45:
        return False

    margin = max(10, min(width, height) // 100)
    if thin_vertical:
        side_touch = (
            0 <= box.x - schematic.x2 <= margin
            or 0 <= schematic.x - box.x2 <= margin
            or intersection_area(box, schematic) > 0
        )
        vertical_match = box_vertical_overlap_height(box, schematic) >= schematic.h * 0.72
        edge_aligned = abs(box.y - schematic.y) <= margin and abs(box.y2 - schematic.y2) <= margin
        return side_touch and vertical_match and edge_aligned

    top_bottom_touch = (
        0 <= box.y - schematic.y2 <= margin
        or 0 <= schematic.y - box.y2 <= margin
        or intersection_area(box, schematic) > 0
    )
    horizontal_match = box_horizontal_overlap_width(box, schematic) >= schematic.w * 0.72
    edge_aligned = abs(box.x - schematic.x) <= margin and abs(box.x2 - schematic.x2) <= margin
    return top_bottom_touch and horizontal_match and edge_aligned


def schematic_side_caption_panel_candidate(block: Block, box: Box, schematic: Box, width: int, height: int) -> bool:
    if block.label not in {"diagram", "image", "other"}:
        return False
    if schematic.h < height * 0.20:
        return False
    if box.w > max(70, int(round(schematic.w * 0.24))):
        return False
    if box.area > schematic.area * 0.28:
        return False
    if box.h < schematic.h * 0.64:
        return False

    features = block.features
    if float(features.get("ink_density", 1.0)) > 0.08:
        return False
    if float(features.get("edge_density", 0.0)) > 0.14:
        return False
    if float(features.get("saturation_p80", 0.0)) > 0.12:
        return False

    margin = max(10, min(width, height) // 100)
    horizontal_gap = max(0, max(box.x, schematic.x) - min(box.x2, schematic.x2))
    vertical_overlap = box_vertical_overlap_height(box, schematic)
    edge_aligned = abs(box.y - schematic.y) <= margin and abs(box.y2 - schematic.y2) <= margin
    return horizontal_gap <= margin and vertical_overlap >= schematic.h * 0.64 and edge_aligned


def schematic_text_label_candidate(block: Block, box: Box, schematic: Box, width: int, height: int) -> bool:
    if block.label not in {"text", "heading"} or block.orientation not in {"horizontal", "unknown"}:
        return False
    if box.area <= 0 or schematic.area <= box.area:
        return False

    features = block.features
    if block.label == "heading":
        if box.area > schematic.area * SCHEMATIC_HEADING_LABEL_MAX_AREA_RATIO:
            return False
        if box.h > max(36, int(round(schematic.h * SCHEMATIC_HEADING_LABEL_MAX_HEIGHT_RATIO))):
            return False
        if box.w > max(90, int(round(schematic.w * SCHEMATIC_HEADING_LABEL_MAX_WIDTH_RATIO))):
            return False
        if float(features.get("max_text_score", 0.0)) < SCHEMATIC_HEADING_LABEL_MIN_TEXT_SCORE:
            return False
        if float(features.get("ink_density", 1.0)) > SCHEMATIC_HEADING_LABEL_MAX_INK_DENSITY:
            return False
        if float(features.get("hline_density", 0.0)) < SCHEMATIC_HEADING_LABEL_MIN_HLINE_DENSITY:
            return False
        if float(features.get("saturation_p80", 0.0)) > SCHEMATIC_HEADING_LABEL_MAX_SATURATION:
            return False
        inside_overlap = SCHEMATIC_HEADING_LABEL_INSIDE_OVERLAP_RATIO
    else:
        if box.area > schematic.area * SCHEMATIC_TEXT_LABEL_MAX_AREA_RATIO:
            return False
        if box.h > max(28, int(round(schematic.h * SCHEMATIC_TEXT_LABEL_MAX_HEIGHT_RATIO))):
            return False
        if box.w > max(80, int(round(schematic.w * SCHEMATIC_TEXT_LABEL_MAX_WIDTH_RATIO))):
            return False
        if float(features.get("max_text_score", 0.0)) < SCHEMATIC_TEXT_LABEL_MIN_TEXT_SCORE:
            return False
        if float(features.get("saturation_p80", 0.0)) > SCHEMATIC_TEXT_LABEL_MAX_SATURATION:
            return False
        inside_overlap = SCHEMATIC_TEXT_LABEL_INSIDE_OVERLAP_RATIO

    margin = max(8, int(round(min(width, height) * SCHEMATIC_TEXT_LABEL_TOUCH_MARGIN_RATIO)))
    overlap = intersection_area(box, schematic)
    if overlap / max(1, box.area) >= inside_overlap:
        return True

    vertical_gap = max(0, max(box.y, schematic.y) - min(box.y2, schematic.y2))
    horizontal_overlap = box_horizontal_overlap_width(box, schematic)
    if vertical_gap <= margin and horizontal_overlap >= min(box.w, schematic.w) * SCHEMATIC_TEXT_LABEL_TOUCH_OVERLAP_RATIO:
        return True

    horizontal_gap = max(0, max(box.x, schematic.x) - min(box.x2, schematic.x2))
    vertical_overlap = box_vertical_overlap_height(box, schematic)
    return (
        horizontal_gap <= margin
        and vertical_overlap >= box.h * SCHEMATIC_TEXT_LABEL_MIN_VERTICAL_OVERLAP_RATIO
    )


def schematic_attachment_touches(candidate: Box, schematic: Box, width: int, height: int, allow_side_touch: bool = True) -> bool:
    margin = max(8, min(width, height) // 120)
    vertical_gap = max(0, max(candidate.y, schematic.y) - min(candidate.y2, schematic.y2))
    horizontal_overlap = box_horizontal_overlap_width(candidate, schematic)
    if (
        vertical_gap <= margin
        and horizontal_overlap >= min(candidate.w, schematic.w) * 0.58
        and horizontal_overlap >= schematic.w * 0.38
    ):
        return True

    if not allow_side_touch:
        return False

    horizontal_gap = max(0, max(candidate.x, schematic.x) - min(candidate.x2, schematic.x2))
    vertical_overlap = box_vertical_overlap_height(candidate, schematic)
    return (
        horizontal_gap <= margin
        and vertical_overlap >= min(candidate.h, schematic.h) * 0.45
        and vertical_overlap >= schematic.h * 0.18
    )


def merge_line_art_attachments_into_schematics(
    classified: list[tuple[Block, Box]],
    image,
    mask,
    edges,
    ann,
    scale: float,
    width: int,
    height: int,
) -> list[tuple[Block, Box]]:
    if len(classified) < 2:
        return classified

    items = classified[:]
    changed = True
    while changed:
        changed = False
        for schematic_index, (schematic_block, schematic_box) in enumerate(items):
            if schematic_block.label != "schematic/circuit":
                continue
            for other_index, (other_block, other_box) in enumerate(items):
                if other_index == schematic_index:
                    continue
                frame_strip = schematic_frame_strip_candidate(other_block, other_box, schematic_box, width, height)
                side_caption_panel = schematic_side_caption_panel_candidate(
                    other_block, other_box, schematic_box, width, height
                )
                text_label = schematic_text_label_candidate(other_block, other_box, schematic_box, width, height)
                if (
                    not frame_strip
                    and not side_caption_panel
                    and not text_label
                    and not schematic_attachment_candidate(other_block, other_box, width, height)
                ):
                    continue
                high_confidence_text_attachment = other_block.label == "text" and other_block.confidence >= 0.45
                if (
                    high_confidence_text_attachment
                    and not text_label
                    and (schematic_box.w > width * 0.55 or schematic_box.h > height * 0.16)
                ):
                    continue
                allow_side_touch = other_block.label != "text" or text_label
                if (
                    not frame_strip
                    and not side_caption_panel
                    and not text_label
                    and not schematic_attachment_touches(other_box, schematic_box, width, height, allow_side_touch=allow_side_touch)
                ):
                    continue
                merged_block, merged_box = merged_classified_item(
                    [items[schematic_index], items[other_index]],
                    "schematic/circuit",
                    schematic_block.ident,
                    image,
                    mask,
                    edges,
                    ann,
                    scale,
                    width,
                    height,
                    "schematic_text_label_merge" if text_label else "line_art_attachment_merge",
                )
                items[schematic_index] = (merged_block, merged_box)
                del items[other_index]
                changed = True
                break
            if changed:
                break

    return sorted(items, key=lambda item: (item[1].y, item[1].x))


def illustration_fragment_candidate(block: Block, box: Box, width: int, height: int) -> bool:
    if block.label in {"schematic/circuit", "table"}:
        return False

    page_area = max(1, width * height)
    area_ratio = box.area / page_area
    if area_ratio < 0.002 or area_ratio > 0.18:
        return False
    if box.w < width * 0.035 or box.h < height * 0.018:
        return False

    features = block.features
    line_art = float(features.get("line_art_score", 0.0))
    edge = float(features.get("edge_density", 0.0))
    ink = float(features.get("ink_density", 1.0))
    gray_std = float(features.get("gray_std", 0.0))
    saturation = float(features.get("saturation_p80", 0.0))
    text_score = float(features.get("max_text_score", 0.0))
    component_signature = float(features.get("component_signature_score", 0.0))

    if annual_contents_text_features(features):
        return False
    if single_axis_waveform_diagram_features(features):
        return False

    if block.label == "other":
        return (ink < 0.055 and gray_std > 0.12) or (line_art > 0.08 and edge > 0.035)

    if block.label == "image":
        if box.h <= height * 0.035 and box.w / max(1, box.h) > 7.0:
            return False
        return saturation > 0.08 or gray_std > 0.26 or line_art > 0.12

    if block.label == "diagram":
        return ink < 0.22 and (line_art > 0.12 or edge > 0.10 or component_signature > 0.35)

    if block.label != "text":
        return False

    likely_prose = (
        block.orientation == "horizontal"
        and block.confidence >= ILLUSTRATION_TEXT_REJECT_MIN_CONFIDENCE
        and text_score >= ILLUSTRATION_TEXT_REJECT_MIN_TEXT_SCORE
        and box.h >= height * ILLUSTRATION_TEXT_REJECT_MIN_HEIGHT_RATIO
        and line_art <= ILLUSTRATION_TEXT_REJECT_MAX_LINE_ART
        and float(features.get("hline_density", 0.0)) <= ILLUSTRATION_TEXT_REJECT_MAX_HLINE
        and float(features.get("vline_density", 0.0)) <= ILLUSTRATION_TEXT_REJECT_MAX_VLINE
    )
    if likely_prose:
        return False

    line_art_text = (
        ink < 0.20
        and gray_std > 0.24
        and (
            line_art > 0.16
            or edge > 0.14
            or component_signature > 0.50
        )
    )
    return line_art_text and (
        block.orientation != "horizontal"
        or block.confidence < 0.82
        or component_signature > 0.55
        or line_art > 0.26
    )


def illustration_fragment_seed(block: Block, box: Box, width: int, height: int) -> bool:
    if not illustration_fragment_candidate(block, box, width, height):
        return False

    features = block.features
    line_art = float(features.get("line_art_score", 0.0))
    edge = float(features.get("edge_density", 0.0))
    gray_std = float(features.get("gray_std", 0.0))
    component_signature = float(features.get("component_signature_score", 0.0))

    if box.w < width * 0.12 or box.h < height * 0.07:
        return False
    if block.label == "image":
        return True
    return (
        block.orientation in {"diagonal", "vertical"}
        or (component_signature > 0.65 and edge > 0.10 and gray_std > 0.32)
        or (line_art > 0.28 and edge > 0.13)
    )


def illustration_fragment_neighbor(group_box: Box, candidate: Box, width: int, height: int) -> bool:
    margin = max(8, min(width, height) // 100)
    direct_overlap = overlap_area(group_box, candidate)
    if direct_overlap / max(1, min(group_box.area, candidate.area)) >= 0.10:
        return True

    horizontal_gap = max(0, max(group_box.x, candidate.x) - min(group_box.x2, candidate.x2))
    vertical_overlap = box_vertical_overlap_height(group_box, candidate)
    if horizontal_gap <= margin and vertical_overlap >= min(group_box.h, candidate.h) * 0.35:
        return True

    vertical_gap = max(0, max(group_box.y, candidate.y) - min(group_box.y2, candidate.y2))
    horizontal_overlap = box_horizontal_overlap_width(group_box, candidate)
    return vertical_gap <= margin and horizontal_overlap >= min(group_box.w, candidate.w) * 0.45


def merge_illustration_fragments_into_images(
    classified: list[tuple[Block, Box]],
    image,
    mask,
    edges,
    ann,
    scale: float,
    width: int,
    height: int,
) -> list[tuple[Block, Box]]:
    if len(classified) < 2:
        return classified

    page_area = max(1, width * height)
    items = classified[:]
    changed = True
    while changed:
        changed = False
        for seed_index, (seed_block, seed_box) in enumerate(items):
            if not illustration_fragment_seed(seed_block, seed_box, width, height):
                continue

            group = [seed_index]
            group_box = seed_box
            inner_changed = True
            while inner_changed:
                inner_changed = False
                for candidate_index, (candidate_block, candidate_box) in enumerate(items):
                    if candidate_index in group:
                        continue
                    if not illustration_fragment_candidate(candidate_block, candidate_box, width, height):
                        continue
                    if not illustration_fragment_neighbor(group_box, candidate_box, width, height):
                        continue

                    tentative = union_box(group_box, candidate_box)
                    if tentative.area / page_area > 0.24:
                        continue
                    if tentative.w > width * 0.82 or tentative.h > height * 0.34:
                        continue

                    group.append(candidate_index)
                    group_box = tentative
                    inner_changed = True

            if len(group) < 2:
                continue

            first_index = min(group, key=lambda index: (items[index][1].y, items[index][1].x))
            first_number = items[first_index][0].ident.split("_", 1)[0]
            group_items = [items[index] for index in group]
            merged_block, merged_box = merged_classified_item(
                group_items,
                "image",
                f"{first_number}_image",
                image,
                mask,
                edges,
                ann,
                scale,
                width,
                height,
                "illustration_fragment_merge",
            )
            if annual_contents_text_features(merged_block.features):
                merged_block.ident = f"{first_number}_text"
                merged_block.label = "text"
                merged_block.orientation = infer_orientation(merged_block.features)
                merged_block.features.pop("illustration_fragment_merge", None)
                merged_block.features["contents_text_fragment_merge"] = 1.0
            kept = [(block, box) for index, (block, box) in enumerate(items) if index not in group]
            kept.append((merged_block, merged_box))
            items = sorted(kept, key=lambda item: (item[1].y, item[1].x))
            changed = True
            break

    return sorted(items, key=lambda item: (item[1].y, item[1].x))


def stacked_diagram_seed(block: Block, box: Box, width: int, height: int) -> bool:
    features = block.features
    line_art = float(features.get("line_art_score", 0.0))
    if box.w < width * 0.20 or box.h > height * 0.12:
        return False
    if box.w / max(1, box.h) < 1.55:
        return False
    if float(features.get("saturation_p80", 1.0)) > 0.08:
        return False
    if "hline_density" in features and "vline_density" in features and min(
        float(features.get("hline_density", 0.0)),
        float(features.get("vline_density", 0.0)),
    ) < STACKED_DIAGRAM_MIN_AXIS_LINE_DENSITY:
        single_axis_waveform = (
            max(float(features.get("hline_density", 0.0)), float(features.get("vline_density", 0.0)))
            >= STACKED_DIAGRAM_MIN_SINGLE_AXIS_LINE_DENSITY
            and line_art >= STACKED_DIAGRAM_MIN_LINE_ART_WITH_SINGLE_AXIS
        )
        if not single_axis_waveform:
            return False
    return (
        block.label in {"diagram", "table", "schematic/circuit", "image"}
        or line_art > 0.32
    ) and float(features.get("edge_density", 0.0)) > 0.18


def stacked_diagram_neighbor(group_box: Box, candidate: Box, width: int, height: int) -> bool:
    vertical_gap = max(0, max(group_box.y, candidate.y) - min(group_box.y2, candidate.y2))
    horizontal_overlap = box_horizontal_overlap_width(group_box, candidate)
    margin = max(8, min(width, height) // 100)
    centers_close = abs((group_box.x + group_box.w / 2.0) - (candidate.x + candidate.w / 2.0)) <= max(group_box.w, candidate.w) * 0.18
    return (
        vertical_gap <= margin
        and horizontal_overlap >= min(group_box.w, candidate.w) * 0.58
        and centers_close
    )


def caption_touching_diagram(caption: Box, diagram: Box, width: int, height: int) -> bool:
    margin = max(8, min(width, height) // 120)
    if caption.y < diagram.y2 or caption.y - diagram.y2 > margin:
        return False
    if caption.x > diagram.x + diagram.w * 0.35:
        return False
    return caption.w <= diagram.w * 0.35 and caption.h <= max(50, diagram.h * 0.22)


def merge_stacked_diagram_blocks(
    classified: list[tuple[Block, Box]],
    image,
    mask,
    edges,
    ann,
    scale: float,
    width: int,
    height: int,
) -> list[tuple[Block, Box]]:
    seeds = [index for index, (block, box) in enumerate(classified) if stacked_diagram_seed(block, box, width, height)]
    if len(seeds) < 3:
        return classified

    used: set[int] = set()
    groups: list[list[int]] = []
    for seed in seeds:
        if seed in used:
            continue
        group = [seed]
        group_box = classified[seed][1]
        changed = True
        while changed:
            changed = False
            for candidate in seeds:
                if candidate in group:
                    continue
                candidate_box = classified[candidate][1]
                if stacked_diagram_neighbor(group_box, candidate_box, width, height):
                    group.append(candidate)
                    group_box = union_box(group_box, candidate_box)
                    changed = True
        if len(group) >= 3:
            used.update(group)
            groups.append(sorted(group, key=lambda index: (classified[index][1].y, classified[index][1].x)))

    if not groups:
        return classified

    consumed: set[int] = set()
    replacements: dict[int, tuple[Block, Box]] = {}
    for group in groups:
        group_items = [classified[index] for index in group]
        group_box = group_items[0][1]
        for _, box in group_items[1:]:
            group_box = union_box(group_box, box)
        for index, (block, box) in enumerate(classified):
            if index in group or block.label != "text":
                continue
            if caption_touching_diagram(box, group_box, width, height):
                group.append(index)
                group_items.append((block, box))
                group_box = union_box(group_box, box)
        first_index = min(group, key=lambda index: (classified[index][1].y, classified[index][1].x))
        first_number = classified[first_index][0].ident.split("_", 1)[0]
        merged = merged_classified_item(
            group_items,
            "diagram",
            f"{first_number}_diagram",
            image,
            mask,
            edges,
            ann,
            scale,
            width,
            height,
            "stacked_diagram_merge",
        )
        replacements[first_index] = merged
        consumed.update(group)

    result: list[tuple[Block, Box]] = []
    for index, item in enumerate(classified):
        if index in replacements:
            result.append(replacements[index])
        elif index not in consumed:
            result.append(item)
    return sorted(result, key=lambda item: (item[1].y, item[1].x))


def waveform_image_promote_candidate(block: Block, box: Box) -> bool:
    if block.label != "image":
        return False

    features = block.features
    width_ratio = float(features.get("width_ratio", 0.0))
    height_ratio = float(features.get("height_ratio", 1.0))
    area_ratio = float(features.get("area_ratio", 0.0))
    geometric_aspect = box.w / max(1, box.h)
    axis_density = max(float(features.get("hline_density", 0.0)), float(features.get("vline_density", 0.0)))
    return (
        width_ratio >= WAVEFORM_IMAGE_PROMOTE_MIN_WIDTH_RATIO
        and height_ratio <= WAVEFORM_IMAGE_PROMOTE_MAX_HEIGHT_RATIO
        and WAVEFORM_IMAGE_PROMOTE_MIN_AREA_RATIO <= area_ratio <= WAVEFORM_IMAGE_PROMOTE_MAX_AREA_RATIO
        and geometric_aspect >= WAVEFORM_IMAGE_PROMOTE_MIN_WIDE_ASPECT
        and float(features.get("line_art_score", 0.0)) >= WAVEFORM_IMAGE_PROMOTE_MIN_LINE_ART
        and axis_density >= WAVEFORM_IMAGE_PROMOTE_MIN_AXIS_DENSITY
        and float(features.get("edge_density", 0.0)) >= WAVEFORM_IMAGE_PROMOTE_MIN_EDGE_DENSITY
        and float(features.get("ink_density", 1.0)) <= WAVEFORM_IMAGE_PROMOTE_MAX_INK_DENSITY
        and float(features.get("saturation_p80", 1.0)) <= WAVEFORM_IMAGE_PROMOTE_MAX_SATURATION
        and float(features.get("component_signature_score", 0.0)) >= WAVEFORM_IMAGE_PROMOTE_MIN_COMPONENT_SIGNATURE
    )


def promote_waveform_images_to_diagrams(classified: list[tuple[Block, Box]]) -> list[tuple[Block, Box]]:
    promoted: list[tuple[Block, Box]] = []
    for block, box in classified:
        if waveform_image_promote_candidate(block, box):
            features = dict(block.features)
            features["waveform_image_promote"] = 1.0
            block = Block(
                ident=block.ident.replace("_image", "_diagram"),
                label="diagram",
                orientation="unknown",
                confidence=block.confidence,
                bbox=block.bbox,
                outline=block.outline,
                features=features,
                crop_path=block.crop_path,
                figure_ref=block.figure_ref,
                caption_candidates=block.caption_candidates,
            )
        promoted.append((block, box))
    return promoted


def demote_textual_diagram_wrappers(classified: list[tuple[Block, Box]]) -> list[tuple[Block, Box]]:
    result: list[tuple[Block, Box]] = []
    for block, box in classified:
        features = block.features
        looks_like_bold_heading = (
            block.label == "diagram"
            and float(features.get("stacked_diagram_merge", 0.0)) >= 0.5
            and float(features.get("hline_density", 0.0)) < 0.02
            and float(features.get("vline_density", 0.0)) < 0.02
            and float(features.get("textline_density", 0.0)) > 0.25
            and float(features.get("ink_density", 0.0)) > 0.08
            and float(features.get("area_ratio", 1.0)) < 0.12
        )
        if looks_like_bold_heading:
            demoted_features = dict(features)
            demoted_features["textual_diagram_wrapper_demote"] = 1.0
            block = Block(
                ident=block.ident.replace("_diagram", "_heading"),
                label="heading",
                orientation="horizontal",
                confidence=block.confidence,
                bbox=block.bbox,
                outline=None,
                features=demoted_features,
                crop_path=block.crop_path,
                figure_ref=block.figure_ref,
                caption_candidates=block.caption_candidates,
            )
        result.append((block, box))
    return result


def weak_visual_wrapper_inside_stronger_visual(inner_block: Block, inner_box: Box, outer_block: Block, outer_box: Box) -> bool:
    if inner_block.ident == outer_block.ident:
        return False
    if inner_block.label not in FIGURE_LABELS or outer_block.label not in FIGURE_LABELS:
        return False
    if inner_box.area <= 0 or outer_box.area <= 0:
        return False
    if outer_box.area < inner_box.area * VISUAL_WRAPPER_MIN_OUTER_AREA_RATIO:
        return False
    if outer_block.confidence < inner_block.confidence + VISUAL_WRAPPER_MIN_CONFIDENCE_DELTA:
        return False
    inner_overlap = overlap_area(inner_box, outer_box) / max(1, inner_box.area)
    if inner_overlap < VISUAL_WRAPPER_MIN_INNER_OVERLAP:
        return False
    if inner_block.label == "image" and outer_block.label != "image":
        return False
    return True


def suppress_weak_visual_wrappers(classified: list[tuple[Block, Box]]) -> list[tuple[Block, Box]]:
    if len(classified) < 2:
        return classified

    suppressed: set[int] = set()
    for inner_index, (inner_block, inner_box) in enumerate(classified):
        for outer_index, (outer_block, outer_box) in enumerate(classified):
            if inner_index == outer_index:
                continue
            if weak_visual_wrapper_inside_stronger_visual(inner_block, inner_box, outer_block, outer_box):
                suppressed.add(inner_index)
                break

    if not suppressed:
        return classified
    return [item for index, item in enumerate(classified) if index not in suppressed]


OverlapOwnerFn = Callable[[Block, Block, Box], str]


def block_outline_to_mask(block: Block) -> tuple[Box, object]:
    box = box_from_list(block.bbox)
    mask = np.zeros((box.h, box.w), dtype=np.uint8)
    if block.outline:
        polygons = []
        for polygon in block.outline:
            points = np.array(
                [
                    [
                        max(0, min(box.w - 1, int(round(point[0] - box.x)))),
                        max(0, min(box.h - 1, int(round(point[1] - box.y)))),
                    ]
                    for point in polygon
                ],
                dtype=np.int32,
            )
            if points.shape[0] >= 3:
                polygons.append(points)
        if polygons:
            cv2.fillPoly(mask, polygons, 255)
    else:
        mask[:, :] = 255
    return box, mask


def rect_slice_inside_box(rect: Box, box: Box) -> tuple[slice, slice] | None:
    x1 = max(0, rect.x - box.x)
    y1 = max(0, rect.y - box.y)
    x2 = min(box.w, rect.x2 - box.x)
    y2 = min(box.h, rect.y2 - box.y)
    if x2 <= x1 or y2 <= y1:
        return None
    return slice(y1, y2), slice(x1, x2)


def mask_overlap_area(first_mask, first_box: Box, second_mask, second_box: Box, overlap: Box) -> int:
    first_slice = rect_slice_inside_box(overlap, first_box)
    second_slice = rect_slice_inside_box(overlap, second_box)
    if first_slice is None or second_slice is None:
        return 0
    first_region = first_mask[first_slice]
    second_region = second_mask[second_slice]
    if first_region.shape != second_region.shape or first_region.size == 0:
        return 0
    return int(np.logical_and(first_region > 0, second_region > 0).sum())


def set_overlap_in_block_mask(block_mask, block_box: Box, overlap: Box, value: int) -> bool:
    block_slice = rect_slice_inside_box(overlap, block_box)
    if block_slice is None:
        return False
    region = block_mask[block_slice]
    before = int((region > 0).sum())
    region[:, :] = value
    after = int((region > 0).sum())
    return before != after


def mask_to_block_outline(block: Block, box: Box, mask) -> list[list[list[int]]]:
    if mask.size == 0:
        return rectangle_polygon(box)
    if bool(np.all(mask > 0)):
        return rectangle_polygon(box)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = max(16.0, box.area * 0.002)
    selected = sorted((contour for contour in contours if cv2.contourArea(contour) >= min_area), key=cv2.contourArea, reverse=True)
    polygons: list[list[list[int]]] = []
    for contour in selected[:8]:
        approx = cv2.approxPolyDP(contour, 4.0, True)
        points: list[list[int]] = []
        for point in approx.reshape(-1, 2):
            rel_x = int(point[0])
            rel_y = int(point[1])
            abs_x = box.x2 if rel_x >= box.w - 1 else box.x + rel_x
            abs_y = box.y2 if rel_y >= box.h - 1 else box.y + rel_y
            points.append([abs_x, abs_y])
        points = orthogonalize_polygon(points)
        if len(points) >= 3:
            polygons.append(points)
    return polygons or rectangle_polygon(box)


def scaled_overlap_for_analysis(overlap: Box, scale: float, width: int, height: int) -> Box | None:
    x1 = int(round(overlap.x * scale))
    y1 = int(round(overlap.y * scale))
    x2 = int(round(overlap.x2 * scale))
    y2 = int(round(overlap.y2 * scale))
    if x2 <= x1:
        x2 = x1 + 1
    if y2 <= y1:
        y2 = y1 + 1
    if x1 >= width or y1 >= height or x2 <= 0 or y2 <= 0:
        return None
    return Box(x1, y1, x2 - x1, y2 - y1).clamp(width, height)


def labels_are_visual_family(first: str, second: str) -> bool:
    return first in FIGURE_LABELS and second in FIGURE_LABELS


def overlap_owner_score(block: Block, block_box: Box, overlap: Box, overlap_label: str, overlap_features: dict[str, float]) -> float:
    line_art = float(overlap_features.get("line_art_score", 0.0))
    text_score = float(overlap_features.get("max_text_score", 0.0))
    textline = float(overlap_features.get("textline_density", 0.0))
    hline = float(overlap_features.get("hline_density", 0.0))
    vline = float(overlap_features.get("vline_density", 0.0))
    saturation = float(overlap_features.get("saturation_p80", 0.0))
    gray_std = float(overlap_features.get("gray_std", 0.0))
    component_signature = float(overlap_features.get("component_signature_score", 0.0))
    overlap_fraction = overlap.area / max(1, block_box.area)

    score = block.confidence * 0.35 + min(0.80, overlap_fraction * 2.0)
    if block.label == overlap_label:
        score += 3.0
    elif labels_are_visual_family(block.label, overlap_label):
        score += 1.0

    if block.label in TEXTUAL_LABELS:
        score += text_score * 2.2 + textline * 1.4
        if overlap_label in TEXTUAL_LABELS:
            score += 1.2
        if line_art >= OVERLAP_DIAGRAM_MIN_LINE_ART and max(hline, vline) >= OVERLAP_DIAGRAM_MIN_AXIS_DENSITY:
            score -= OVERLAP_TEXT_LINE_ART_PENALTY
        if line_art > 0.45 and (hline > 0.04 or vline > 0.04):
            score -= 0.9
        if block.label == "heading":
            score += 0.4
    elif block.label == "schematic/circuit":
        score += line_art * 2.1 + (hline + vline) * 1.5 + component_signature * 2.4
        if saturation < 0.08:
            score += 0.45
        if overlap_label == "schematic/circuit":
            score += 1.5
        if text_score > 0.75 and hline < 0.03 and vline < 0.03:
            score -= 1.2
    elif block.label == "diagram":
        score += line_art * 1.4 + hline * 1.8 + vline * 0.7
        if line_art >= OVERLAP_DIAGRAM_MIN_LINE_ART and max(hline, vline) >= OVERLAP_DIAGRAM_MIN_AXIS_DENSITY:
            score += OVERLAP_DIAGRAM_LINE_ART_BOOST
        if float(block.features.get("stacked_diagram_merge", 0.0)) >= 0.5:
            score += OVERLAP_DIAGRAM_STACKED_MERGE_BOOST
        if float(block.features.get("waveform_image_promote", 0.0)) >= 0.5:
            score += OVERLAP_DIAGRAM_STACKED_MERGE_BOOST
        if overlap_label == "diagram":
            score += 1.4
    elif block.label == "image":
        score += saturation * 2.0 + gray_std * 0.8
        if overlap_label == "image":
            score += 1.6
    elif block.label == "table":
        score += (hline + vline) * 1.4
        if overlap_label == "table":
            score += 1.4
    return score


def decide_overlap_owner(
    first_block: Block,
    first_box: Box,
    second_block: Block,
    second_box: Box,
    overlap: Box,
    image,
    mask,
    edges,
    ann,
    scale: float,
) -> str:
    height, width = image.shape[:2]
    analysis_overlap = scaled_overlap_for_analysis(overlap, scale, width, height)
    if analysis_overlap is None:
        return first_block.ident if first_block.confidence >= second_block.confidence else second_block.ident

    overlap_features = feature_dict(image, mask, edges, analysis_overlap)
    overlap_label, _ = classify_features(ann, overlap_features)
    first_score = overlap_owner_score(first_block, first_box, overlap, overlap_label, overlap_features)
    second_score = overlap_owner_score(second_block, second_box, overlap, overlap_label, overlap_features)
    if abs(first_score - second_score) <= 0.12:
        if first_block.label == overlap_label and second_block.label != overlap_label:
            return first_block.ident
        if second_block.label == overlap_label and first_block.label != overlap_label:
            return second_block.ident
        return first_block.ident if first_block.confidence >= second_block.confidence else second_block.ident
    return first_block.ident if first_score > second_score else second_block.ident


def resolve_block_overlaps(
    blocks: list[Block],
    image=None,
    mask=None,
    edges=None,
    ann=None,
    scale: float = 1.0,
    owner_fn: OverlapOwnerFn | None = None,
) -> list[Block]:
    if len(blocks) < 2:
        return blocks
    if owner_fn is None and (image is None or mask is None or edges is None or ann is None):
        return blocks

    boxes = {block.ident: box_from_list(block.bbox) for block in blocks}
    masks: dict[str, object] = {}
    changed: set[str] = set()
    pairs: list[tuple[int, int, Box]] = []
    for first_index, first_block in enumerate(blocks):
        first_box = boxes[first_block.ident]
        for second_index in range(first_index + 1, len(blocks)):
            second_block = blocks[second_index]
            second_box = boxes[second_block.ident]
            overlap = intersection_box(first_box, second_box)
            if overlap is None:
                continue
            min_area = min(first_box.area, second_box.area)
            if overlap.area < max(25, int(round(min_area * 0.006))):
                continue
            pairs.append((first_index, second_index, overlap))

    for first_index, second_index, overlap in sorted(pairs, key=lambda item: item[2].area, reverse=True):
        first_block = blocks[first_index]
        second_block = blocks[second_index]
        first_box = boxes[first_block.ident]
        second_box = boxes[second_block.ident]
        if first_block.ident not in masks:
            _, masks[first_block.ident] = block_outline_to_mask(first_block)
        if second_block.ident not in masks:
            _, masks[second_block.ident] = block_outline_to_mask(second_block)

        active_area = mask_overlap_area(masks[first_block.ident], first_box, masks[second_block.ident], second_box, overlap)
        if active_area < max(16, int(round(overlap.area * 0.05))):
            continue

        if owner_fn is not None:
            owner_ident = owner_fn(first_block, second_block, overlap)
        else:
            owner_ident = decide_overlap_owner(first_block, first_box, second_block, second_box, overlap, image, mask, edges, ann, scale)
        if owner_ident not in {first_block.ident, second_block.ident}:
            continue

        loser_block = second_block if owner_ident == first_block.ident else first_block
        loser_box = boxes[loser_block.ident]
        winner_block = first_block if owner_ident == first_block.ident else second_block
        winner_box = boxes[winner_block.ident]
        if set_overlap_in_block_mask(masks[loser_block.ident], loser_box, overlap, 0):
            changed.add(loser_block.ident)
        if set_overlap_in_block_mask(masks[winner_block.ident], winner_box, overlap, 255):
            changed.add(winner_block.ident)

    for block in blocks:
        if block.ident not in changed:
            continue
        box = boxes[block.ident]
        block_mask = masks[block.ident]
        full_rectangle = bool(np.all(block_mask > 0))
        if full_rectangle and block.label not in FIGURE_LABELS:
            block.outline = None
        else:
            block.outline = mask_to_block_outline(block, box, block_mask)
        block.features["overlap_resolution"] = 1.0

    return blocks


def small_artifact_inside_or_touching_schematic(block: Block, schematic: Block) -> bool:
    if block.ident == schematic.ident or block.label in {"text", "schematic/circuit"}:
        return False

    block_box = box_from_list(block.bbox)
    schematic_box = box_from_list(schematic.bbox)
    if block_box.area <= 0 or schematic_box.area <= block_box.area:
        return False

    small = block_box.area <= schematic_box.area * 0.080
    thin = (
        block_box.h <= max(80, int(round(schematic_box.h * 0.050)))
        or block_box.w <= max(80, int(round(schematic_box.w * 0.050)))
    )
    if not small or not thin:
        return False

    overlap_fraction = intersection_area(block_box, schematic_box) / max(1, block_box.area)
    if overlap_fraction >= 0.55:
        return True

    margin = max(14, int(round(min(schematic_box.w, schematic_box.h) * 0.018)))
    horizontal_touch = (
        0 <= block_box.y - schematic_box.y2 <= margin or 0 <= schematic_box.y - block_box.y2 <= margin
    ) and box_horizontal_overlap_width(block_box, schematic_box) >= min(block_box.w, schematic_box.w) * 0.45
    vertical_touch = (
        0 <= block_box.x - schematic_box.x2 <= margin or 0 <= schematic_box.x - block_box.x2 <= margin
    ) and box_vertical_overlap_height(block_box, schematic_box) >= min(block_box.h, schematic_box.h) * 0.45
    return horizontal_touch or vertical_touch


def suppress_small_artifacts_near_schematics(blocks: list[Block]) -> list[Block]:
    schematic_blocks = [block for block in blocks if block.label == "schematic/circuit"]
    if not schematic_blocks:
        return blocks

    suppressed = {
        block.ident
        for block in blocks
        if any(small_artifact_inside_or_touching_schematic(block, schematic) for schematic in schematic_blocks)
    }
    if not suppressed:
        return blocks
    return [block for block in blocks if block.ident not in suppressed]


def page_margin_visual_artifact(block: Block, page_width: int, page_height: int) -> bool:
    if block.label not in FIGURE_LABELS and block.label != "other":
        return False

    box = box_from_list(block.bbox)
    if box.area <= 0:
        return False
    if box.w > page_width * PAGE_MARGIN_VISUAL_ARTIFACT_MAX_WIDTH_RATIO:
        return False
    if box.h < page_height * PAGE_MARGIN_VISUAL_ARTIFACT_MIN_HEIGHT_RATIO:
        return False
    edge_margin = max(8, int(round(page_width * PAGE_MARGIN_VISUAL_ARTIFACT_EDGE_RATIO)))
    touches_page_edge = box.x <= edge_margin or box.x2 >= page_width - edge_margin
    if not touches_page_edge:
        return False

    saturation = float(block.features.get("saturation_p80", 0.0))
    confidence = float(block.confidence)
    line_art = float(block.features.get("line_art_score", 0.0))
    if saturation < PAGE_MARGIN_VISUAL_ARTIFACT_MIN_SATURATION:
        return False
    return confidence <= PAGE_MARGIN_VISUAL_ARTIFACT_MAX_CONFIDENCE or line_art > 0.70


def suppress_page_margin_visual_artifacts(blocks: list[Block], page_width: int, page_height: int) -> list[Block]:
    suppressed = {
        block.ident
        for block in blocks
        if page_margin_visual_artifact(block, page_width, page_height)
    }
    if not suppressed:
        return blocks
    return [block for block in blocks if block.ident not in suppressed]


def annual_contents_footer_artifact(block: Block, page_width: int, page_height: int) -> bool:
    if block.label not in TEXTUAL_LABELS:
        return False
    box = box_from_list(block.bbox)
    if box.area <= 0:
        return False
    page_area = max(1, page_width * page_height)
    if box.y < page_height * CONTENTS_FOOTER_ARTIFACT_TOP_RATIO:
        return False
    if box.h > page_height * CONTENTS_FOOTER_ARTIFACT_MAX_HEIGHT_RATIO:
        return False
    if box.w > page_width * CONTENTS_FOOTER_ARTIFACT_MAX_WIDTH_RATIO:
        return False
    if box.area > page_area * CONTENTS_FOOTER_ARTIFACT_MAX_AREA_RATIO:
        return False

    edge_band = page_width * CONTENTS_FOOTER_ARTIFACT_EDGE_RATIO
    if box.x > edge_band and box.x2 < page_width - edge_band:
        return False

    features = block.features
    return (
        block.orientation in {"horizontal", "vertical", "diagonal", "unknown"}
        and float(features.get("max_text_score", 0.0)) >= 0.45
        and float(features.get("saturation_p80", 0.0)) <= 0.12
    )


def suppress_annual_contents_footer_artifacts(
    blocks: list[Block],
    page_width: int,
    page_height: int,
) -> list[Block]:
    suppressed = {
        block.ident
        for block in blocks
        if annual_contents_footer_artifact(block, page_width, page_height)
    }
    if not suppressed:
        return blocks
    return [block for block in blocks if block.ident not in suppressed]


def horizontal_rule_artifact(block: Block) -> bool:
    return horizontal_rule_features(block.features)


def weak_heading_artifact(block: Block) -> bool:
    if block.label != "heading":
        return False
    features = block.features
    return (
        block.confidence <= WEAK_HEADING_ARTIFACT_MAX_CONFIDENCE
        and features.get("width_ratio", 0.0) >= WEAK_HEADING_ARTIFACT_MIN_WIDTH_RATIO
        and features.get("height_ratio", 1.0) <= WEAK_HEADING_ARTIFACT_MAX_HEIGHT_RATIO
        and features.get("ink_density", 1.0) <= WEAK_HEADING_ARTIFACT_MAX_INK_DENSITY
        and features.get("edge_density", 1.0) <= WEAK_HEADING_ARTIFACT_MAX_EDGE_DENSITY
        and features.get("line_art_score", 1.0) <= WEAK_HEADING_ARTIFACT_MAX_LINE_ART
        and features.get("max_text_score", 1.0) <= WEAK_HEADING_ARTIFACT_MAX_TEXT_SCORE
    )


def suppress_horizontal_rule_artifacts(blocks: list[Block]) -> list[Block]:
    suppressed = {block.ident for block in blocks if horizontal_rule_artifact(block) or weak_heading_artifact(block)}
    if not suppressed:
        return blocks
    return [block for block in blocks if block.ident not in suppressed]


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
    if figure_block.label not in {"schematic/circuit", "diagram", "pcb"}:
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
        orientation = infer_orientation(features) if label in TEXTUAL_LABELS else "unknown"
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

    classified = split_text_columns_in_classified_blocks(
        classified, image, mask, edges, ann, scale=scale, width=analysis_w, height=analysis_h
    )
    classified = split_internal_display_heading_blocks(
        classified, image, mask, edges, ann, scale=scale, width=analysis_w, height=analysis_h
    )
    classified = merge_fragmented_contents_text_rows(
        classified, image, mask, edges, ann, scale=scale, width=analysis_w, height=analysis_h
    )
    classified = split_annual_contents_heading_blocks(
        classified, image, mask, edges, ann, scale=scale, width=analysis_w, height=analysis_h
    )
    classified = merge_adjacent_heading_fragments(
        classified, image, mask, edges, ann, scale=scale, width=analysis_w, height=analysis_h
    )
    classified = split_text_columns_in_classified_blocks(
        classified, image, mask, edges, ann, scale=scale, width=analysis_w, height=analysis_h
    )
    classified = merge_contents_number_columns(
        classified, image, mask, edges, ann, scale=scale, width=analysis_w, height=analysis_h
    )
    classified = merge_fragmented_contents_columns(
        classified, image, mask, edges, ann, scale=scale, width=analysis_w, height=analysis_h
    )
    classified = merge_contents_number_columns(
        classified, image, mask, edges, ann, scale=scale, width=analysis_w, height=analysis_h
    )
    classified = snap_contents_columns_to_page_grid(
        classified, image, mask, edges, ann, scale=scale, width=analysis_w, height=analysis_h
    )
    classified = merge_stacked_diagram_blocks(
        classified, image, mask, edges, ann, scale=scale, width=analysis_w, height=analysis_h
    )
    classified = promote_waveform_images_to_diagrams(classified)
    classified = merge_connected_schematic_blocks(
        classified, image, mask, edges, ann, scale=scale, width=analysis_w, height=analysis_h
    )
    classified = demote_textual_diagram_wrappers(classified)
    classified = merge_line_art_attachments_into_schematics(
        classified, image, mask, edges, ann, scale=scale, width=analysis_w, height=analysis_h
    )
    classified = merge_illustration_fragments_into_images(
        classified, image, mask, edges, ann, scale=scale, width=analysis_w, height=analysis_h
    )
    classified = promote_waveform_images_to_diagrams(classified)
    classified = suppress_weak_visual_wrappers(classified)
    all_blocks = suppress_nested_text_blocks([block for block, _ in classified])
    assign_visual_outlines(all_blocks)
    blocks = suppress_text_inside_schematics(all_blocks)
    blocks = suppress_small_text_artifacts_near_visuals(blocks)
    blocks = suppress_tiny_text_fragments(blocks)
    blocks = suppress_small_artifacts_near_schematics(blocks)
    page_width = int(round(analysis_w / max(scale, 1e-6)))
    page_height = int(round(analysis_h / max(scale, 1e-6)))
    blocks = suppress_page_margin_visual_artifacts(blocks, page_width, page_height)
    blocks = suppress_annual_contents_footer_artifacts(blocks, page_width, page_height)
    blocks = suppress_horizontal_rule_artifacts(blocks)
    blocks = resolve_block_overlaps(blocks, image, mask, edges, ann, scale)
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


def draw_preview(
    image,
    blocks: list[Block],
    preview_width: int,
    page_dir: Path,
    title: str = "OpenCV layout detector",
    subtitle: str | None = None,
    add_header: bool = True,
) -> Path:
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
        label_w = text_w + 6
        label_h = text_h + baseline + 5
        anchor_x, anchor_y = preview_label_anchor(block, x1, y1, scale)
        label_x = max(0, min(preview_w - label_w, anchor_x))
        top = anchor_y - label_h
        if top < 0:
            top = min(preview_h - label_h, anchor_y)
        top = max(0, top)
        cv2.rectangle(preview, (label_x, top), (label_x + label_w, top + label_h), color, -1)
        cv2.putText(preview, label, (label_x + 3, top + text_h + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

    if add_header:
        preview_subtitle = subtitle if subtitle is not None else f"{page_dir.name} | blocks: {block_counts_text(blocks)}"
        preview = add_title_header(preview, title, preview_subtitle)

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
    frequency_hints: str = "validate",
    preview_header: bool = True,
) -> dict[str, object]:
    accelerator = configure_accelerator(accelerator)
    original = read_image(image_path)
    analysis_image, scale = resize_for_analysis(original, max_analysis_side, accelerator)
    page_name = image_path.stem
    page_dir = out_dir / page_name
    page_dir.mkdir(parents=True, exist_ok=True)

    frequency_result = None
    if frequency_hints != "off" and layout_frequency is not None:
        frequency_result = layout_frequency.analyze_image(analysis_image)

    boxes, metadata = detect_candidate_boxes(
        analysis_image,
        min_area_ratio=min_area_ratio,
        accelerator=accelerator,
        frequency_result=frequency_result if frequency_hints == "hints" else None,
    )
    metadata["frequency_mode"] = frequency_hints
    if frequency_result:
        metadata["frequency_hint_count"] = len(frequency_result.get("hints", []))
        metadata["frequency_cluster_hint_count"] = len(frequency_result.get("cluster_hints", []))
    blocks = classify_blocks(analysis_image, boxes, scale=scale, save_crops=save_crops, page_dir=page_dir, accelerator=accelerator)
    original_frequency_hints = scale_frequency_hints_to_original(frequency_result, scale)
    original_frequency_cluster_hints = scale_frequency_hints_to_original(frequency_result, scale, "cluster_hints")
    frequency_warnings = frequency_validation_warnings(blocks, original_frequency_hints)
    frequency_cluster_warnings = frequency_validation_warnings(blocks, original_frequency_cluster_hints)
    preview_path = draw_preview(original, blocks, preview_width=preview_width, page_dir=page_dir, add_header=preview_header)

    result = {
        "source": str(image_path),
        "page": page_name,
        "width": int(original.shape[1]),
        "height": int(original.shape[0]),
        "analysis_scale": scale,
        "classes": CLASS_NAMES,
        "metadata": metadata,
        "accelerator": accelerator,
        "frequency_hints_enabled": frequency_hints != "off",
        "frequency_mode": frequency_hints,
        "preview_header": preview_header,
        "frequency_hints": original_frequency_hints,
        "frequency_cluster_hints": original_frequency_cluster_hints,
        "frequency_warnings": frequency_warnings,
        "frequency_cluster_warnings": frequency_cluster_warnings,
        "preview": preview_path.relative_to(page_dir).as_posix(),
        "blocks": [asdict(block) for block in blocks],
    }
    (page_dir / "layout.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
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
    parser.add_argument(
        "--frequency-hints",
        choices=FREQUENCY_HINT_CHOICES,
        default="validate",
        help="Use 1D frequency analysis: off, validate-only, or hints as extra OpenCV candidate boxes.",
    )
    parser.add_argument("--no-preview-header", action="store_true", help="Write raw annotated preview without the title header.")
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
        frequency_hints=args.frequency_hints,
        preview_header=not args.no_preview_header,
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
