#!/usr/bin/env python3
"""Shared constants for magazine page layout analysis scripts."""

from __future__ import annotations


LAYOUT_CLASS_NAMES = ["text", "heading", "image", "schematic/circuit", "diagram", "pcb", "table", "other"]
TEXTUAL_LABELS = {"text", "heading"}
FIGURE_LABELS = {"image", "schematic/circuit", "diagram", "pcb"}

# OpenCV uses BGR order when drawing previews.
LABEL_COLORS_BGR = {
    "text": (52, 168, 83),
    "heading": (48, 48, 220),
    "image": (66, 133, 244),
    "schematic/circuit": (234, 67, 53),
    "diagram": (251, 188, 5),
    "pcb": (0, 170, 180),
    "table": (171, 71, 188),
    "other": (128, 128, 128),
    "background": (190, 190, 190),
}
CLASS_COLORS_BGR = {label: LABEL_COLORS_BGR[label] for label in LAYOUT_CLASS_NAMES}

CAPTION_HIGHLIGHT_COLOR_BGR = (0, 255, 255)
CAPTION_HIGHLIGHT_OPACITY = 0.30
CAPTION_HIGHLIGHT_PADDING_PX = 4

ACCELERATOR_CHOICES = ("cpu", "opencl")
FREQUENCY_HINT_CHOICES = ("off", "validate", "hints")

# PCB blocks are expected to contain thick copper traces, round pads, and
# enough horizontal/vertical track structure to avoid confusing bold headings
# with printed circuit boards.
PCB_MIN_TRACE_DENSITY = 0.30
PCB_MIN_SIGNATURE_SCORE = 0.40
PCB_MIN_LINE_BALANCE = 0.16
PCB_MIN_AXIS_LINE_DENSITY = 0.045
PCB_MIN_AREA_RATIO = 0.030
PCB_MIN_HEIGHT_RATIO = 0.110
PCB_MAX_TEXT_SCORE = 0.58
PCB_MAX_INK_DENSITY = 0.34

# Split a short but wide prose block when several text rows are separated by a
# real vertical gutter. This catches two magazine columns that were merged into
# one candidate box without splitting single-line headings at word spaces.
TEXT_COLUMN_SPLIT_MIN_WIDTH_RATIO = 0.35
TEXT_COLUMN_SPLIT_MIN_HEIGHT_RATIO = 0.045
TEXT_COLUMN_SPLIT_MIN_ROW_RUNS = 3
TEXT_COLUMN_SPLIT_MIN_GAP_RATIO = 0.025
TEXT_COLUMN_SPLIT_MIN_GAP_PX = 10
TEXT_COLUMN_SPLIT_MIN_PIECE_WIDTH_RATIO = 0.080
TEXT_COLUMN_SPLIT_MAX_PIECES = 4

# Split tall mixed page regions when a real horizontal whitespace corridor
# separates a figure area from the prose below it. Paragraph gaps are shorter
# and should remain inside one text column.
HORIZONTAL_GAP_SPLIT_MIN_WIDTH_RATIO = 0.16
HORIZONTAL_GAP_SPLIT_MIN_HEIGHT_RATIO = 0.34
HORIZONTAL_GAP_SPLIT_MIN_GAP_RATIO = 0.012
HORIZONTAL_GAP_SPLIT_MIN_GAP_PX = 16
HORIZONTAL_GAP_SPLIT_MIN_PIECE_HEIGHT_RATIO = 0.080
HORIZONTAL_GAP_SPLIT_EDGE_SKIP_RATIO = 0.025
HORIZONTAL_GAP_SPLIT_MAX_PIECES = 3

# Small technical labels attached to figures should not become OCR text
# columns. They are usually thin, low-area fragments touching a PCB or
# schematic outline.
TEXT_ARTIFACT_VISUAL_LABELS = {"pcb", "schematic/circuit", "diagram"}
TEXT_ARTIFACT_MAX_AREA_RATIO = 0.020
TEXT_ARTIFACT_MAX_HEIGHT_PX = 64
TEXT_ARTIFACT_MAX_HEIGHT_RATIO = 0.045
TEXT_ARTIFACT_MAX_WIDTH_RATIO = 0.280
TEXT_ARTIFACT_TOUCH_MARGIN_RATIO = 0.018
TEXT_ARTIFACT_MIN_OVERLAP_RATIO = 0.55

# Very short text fragments are usually contour leftovers, page-number bits,
# leader dots, or tiny labels that should be handled as figure captions instead
# of standalone OCR prose blocks. The glyph-width threshold is evaluated along
# the reading axis: width for horizontal text, height for vertical text.
TEXT_MIN_GLYPH_WIDTHS = 3.5
TEXT_AVERAGE_GLYPH_WIDTH_TO_HEIGHT = 0.55
TEXT_MIN_ABSOLUTE_WIDTH_PX = 28
TEXT_MIN_ABSOLUTE_HEIGHT_PX = 12
TEXT_FRAGMENT_SUPPRESS_INSIDE_VISUALS = True
TEXT_FRAGMENT_INSIDE_VISUAL_MIN_OVERLAP_RATIO = 0.40
TEXT_FRAGMENT_INSIDE_VISUAL_MAX_GLYPH_WIDTHS = 7.0

# Headings are text blocks with display-scale glyphs. They can be saturated
# blue/red in magazine scans, so they must be separated from photo/image rules
# before color-heavy features dominate the classifier.
HEADING_MIN_WIDTH_RATIO = 0.18
HEADING_MAX_HEIGHT_RATIO = 0.165
HEADING_MAX_AREA_RATIO = 0.095
HEADING_MIN_WIDE_ASPECT = 0.36
HEADING_MIN_TEXT_SCORE = 0.16
HEADING_MAX_TEXT_SCORE = 0.62
HEADING_MIN_INK_DENSITY = 0.10
HEADING_MIN_GRAY_STD = 0.36
HEADING_MAX_LINE_BALANCE = 0.18
HEADING_MIN_COMPONENT_DENSITY = 0.18

# Avoid merging confident prose columns into image/diagram groups when text
# happens to trigger component-like signatures.
ILLUSTRATION_TEXT_REJECT_MIN_CONFIDENCE = 0.84
ILLUSTRATION_TEXT_REJECT_MIN_TEXT_SCORE = 0.74
ILLUSTRATION_TEXT_REJECT_MIN_HEIGHT_RATIO = 0.055
ILLUSTRATION_TEXT_REJECT_MAX_LINE_ART = 0.30
ILLUSTRATION_TEXT_REJECT_MAX_HLINE = 0.10
ILLUSTRATION_TEXT_REJECT_MAX_VLINE = 0.06

# Waveform diagrams often appear as stacked strips: each strip can have strong
# vertical transitions while horizontal baselines are too fragmented for the
# generic line-density detector.
STACKED_DIAGRAM_MIN_AXIS_LINE_DENSITY = 0.04
STACKED_DIAGRAM_MIN_SINGLE_AXIS_LINE_DENSITY = 0.18
STACKED_DIAGRAM_MIN_LINE_ART_WITH_SINGLE_AXIS = 0.34

# Low-confidence visual wrappers that mostly sit inside a stronger visual block
# are usually segmentation leftovers and should not cut the stronger block.
VISUAL_WRAPPER_MIN_INNER_OVERLAP = 0.78
VISUAL_WRAPPER_MIN_CONFIDENCE_DELTA = 0.18
VISUAL_WRAPPER_MIN_OUTER_AREA_RATIO = 1.25

# When resolving overlaps, waveform fragments can look textual because each
# row has labels. Dense axis-aligned lines should keep that region with the
# diagram block instead of donating it to adjacent prose.
OVERLAP_DIAGRAM_MIN_LINE_ART = 0.34
OVERLAP_DIAGRAM_MIN_AXIS_DENSITY = 0.18
OVERLAP_DIAGRAM_LINE_ART_BOOST = 2.40
OVERLAP_DIAGRAM_STACKED_MERGE_BOOST = 1.10
OVERLAP_TEXT_LINE_ART_PENALTY = 2.80
STACKED_DIAGRAM_TEXT_CUTOUT_MIN_MERGE_SCORE = 0.50

# Annual contents pages can fragment into one full-width text box per printed
# row because dot leaders connect entries across both magazine columns. Merge
# only longer runs of thin, similarly aligned text strips so normal article
# prose blocks stay separate.
CONTENTS_ROW_MERGE_MIN_RUN = 4
CONTENTS_ROW_MERGE_MAX_HEIGHT_RATIO = 0.085
CONTENTS_ROW_MERGE_MIN_WIDTH_RATIO = 0.50
CONTENTS_ROW_MERGE_MIN_WIDTH_SIMILARITY = 0.74
CONTENTS_ROW_MERGE_MIN_HORIZONTAL_OVERLAP = 0.72
CONTENTS_ROW_MERGE_MAX_VERTICAL_GAP_RATIO = 0.026
CONTENTS_ROW_MERGE_MAX_VERTICAL_GAP_PX = 42
CONTENTS_ROW_MERGE_MIN_TOTAL_HEIGHT_RATIO = 0.10
CONTENTS_ROW_MERGE_MAX_TOTAL_HEIGHT_RATIO = 0.72
CONTENTS_COLUMN_MERGE_MIN_WIDTH_RATIO = 0.20
CONTENTS_COLUMN_MERGE_MAX_WIDTH_RATIO = 0.56
CONTENTS_COLUMN_MERGE_MIN_WIDTH_SIMILARITY = 0.80
CONTENTS_COLUMN_MERGE_MIN_HORIZONTAL_OVERLAP = 0.86
CONTENTS_COLUMN_MERGE_MAX_VERTICAL_GAP_RATIO = 0.016
CONTENTS_COLUMN_MERGE_MAX_VERTICAL_GAP_PX = 28
CONTENTS_HEADING_SPLIT_MIN_WIDTH_RATIO = 0.70
CONTENTS_HEADING_SPLIT_MIN_HEIGHT_RATIO = 0.20
CONTENTS_HEADING_SPLIT_MIN_RATIO = 0.10
CONTENTS_HEADING_SPLIT_MAX_RATIO = 0.32
CONTENTS_HEADING_SPLIT_MIN_GAP_PX = 12
CONTENTS_HEADING_SPLIT_MIN_BODY_ROWS = 3
CONTENTS_TEXT_MIN_SCORE = 0.70
CONTENTS_TEXT_MIN_TEXTLINE_DENSITY = 0.58
CONTENTS_TEXT_MIN_COMPONENT_DENSITY = 0.72
CONTENTS_TEXT_MAX_AXIS_LINE_DENSITY = 0.08
CONTENTS_TEXT_MAX_LINE_BALANCE = 0.14
CONTENTS_TEXT_MAX_SATURATION = 0.10
CONTENTS_TEXT_MIN_WIDTH_RATIO = 0.28
CONTENTS_TEXT_MAX_WIDTH_RATIO = 0.62
CONTENTS_TEXT_MIN_HEIGHT_RATIO = 0.10
CONTENTS_NUMBER_COLUMN_MAX_WIDTH_RATIO = 0.13
CONTENTS_NUMBER_COLUMN_MIN_HEIGHT_RATIO = 0.055
CONTENTS_NUMBER_COLUMN_MAX_GAP_RATIO = 0.055
CONTENTS_NUMBER_COLUMN_MIN_TARGET_OVERLAP = 0.62

# Annual contents scans carry issue/page footer text near the bottom corners.
# Keep those service marks out of OCR layout blocks without touching real
# contents rows above the footer band.
CONTENTS_FOOTER_ARTIFACT_TOP_RATIO = 0.890
CONTENTS_FOOTER_ARTIFACT_MAX_HEIGHT_RATIO = 0.035
CONTENTS_FOOTER_ARTIFACT_MAX_WIDTH_RATIO = 0.175
CONTENTS_FOOTER_ARTIFACT_EDGE_RATIO = 0.220
CONTENTS_FOOTER_ARTIFACT_MAX_AREA_RATIO = 0.006

# Colored magazine side margins can be mistaken for schematic/PCB fragments
# because they contain strong vertical edges and small repeated dots.
PAGE_MARGIN_VISUAL_ARTIFACT_MAX_WIDTH_RATIO = 0.09
PAGE_MARGIN_VISUAL_ARTIFACT_MIN_HEIGHT_RATIO = 0.10
PAGE_MARGIN_VISUAL_ARTIFACT_EDGE_RATIO = 0.025
PAGE_MARGIN_VISUAL_ARTIFACT_MAX_CONFIDENCE = 0.62
PAGE_MARGIN_VISUAL_ARTIFACT_MIN_SATURATION = 0.14

# Component and PCB signature detector thresholds.
MIN_COMPONENT_PIXELS = 4
MIN_SYMBOL_SIDE = 6
MAX_SYMBOL_AREA_RATIO = 0.060
RECT_MIN_ASPECT = 1.25
RECT_MAX_ASPECT = 8.00
RECT_MIN_FILL_RATIO = 0.045
RECT_MAX_FILL_RATIO = 0.950
TRIANGLE_MIN_FILL_RATIO = 0.08
TRIANGLE_MAX_FILL_RATIO = 0.55
CIRCLE_MIN_CIRCULARITY = 0.52
CIRCLE_MAX_ASPECT_SKEW = 0.45
CAPACITOR_MIN_LENGTH = 7
CAPACITOR_MAX_GAP_RATIO = 0.060
CAPACITOR_MAX_PAIR_COUNT = 24
SIGNATURE_AREA_NORMALIZER = 42000.0
PCB_TRACE_DISTANCE_MIN = 2.1
PCB_PAD_MIN_SIDE = 4
PCB_PAD_MAX_SIDE_RATIO = 0.070
PCB_PAD_MIN_CIRCULARITY = 0.28
PCB_BOARD_EDGE_BAND_RATIO = 0.08

# Frequency and histogram page-analysis settings.
DEFAULT_TILE_SIZE = 32
DEFAULT_STRIDE = 32
TEXT_ROW_PERIOD_BAND = (8.0, 44.0)
TEXT_COLUMN_PERIOD_BAND = (4.0, 28.0)
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

# Comparison-layer classifiers used by compare_layout_analysis_layers.py.
HISTOGRAM_BACKGROUND_MAX_INK = 0.018
HISTOGRAM_BACKGROUND_MIN_LIGHT = 0.96
HISTOGRAM_BACKGROUND_MAX_DARK = 0.010
HISTOGRAM_BACKGROUND_MAX_MID = 0.08
HISTOGRAM_IMAGE_MIN_INK = 0.08
HISTOGRAM_IMAGE_MIN_HIGH_SATURATION = 0.20
HISTOGRAM_IMAGE_MIN_COLOR_FRACTION = 0.55
HISTOGRAM_IMAGE_MIN_COLOR_MID = 0.20
HISTOGRAM_IMAGE_MIN_MID = 0.48
HISTOGRAM_IMAGE_MIN_ENTROPY = 0.45
HISTOGRAM_SCHEMATIC_MIN_INK = 0.020
HISTOGRAM_SCHEMATIC_MAX_DARK_LIGHT_RATIO = SCHEMATIC_MAX_DARK_LIGHT_RATIO
HISTOGRAM_SCHEMATIC_MIN_LIGHT = 0.58
HISTOGRAM_SCHEMATIC_MAX_MID = 0.36
HISTOGRAM_TEXT_MIN_INK = 0.035
HISTOGRAM_TEXT_MIN_DARK_LIGHT_RATIO = TEXT_MIN_DARK_LIGHT_RATIO
HISTOGRAM_TEXT_MAX_DARK_LIGHT_RATIO = TEXT_MAX_DARK_LIGHT_RATIO
HISTOGRAM_TEXT_MAX_MID = TEXT_MAX_LUMA_MID_FRACTION
HISTOGRAM_TEXT_MIN_BIMODAL = 0.035
HISTOGRAM_TEXT_MIN_ENTROPY = 0.32
BALANCE_BACKGROUND_MAX_INK = 0.018
BALANCE_BACKGROUND_MIN_LIGHT = 0.96
BALANCE_BACKGROUND_MAX_DARK_LIGHT_RATIO = 0.012
BALANCE_SCHEMATIC_MIN_INK = 0.020
BALANCE_SCHEMATIC_MAX_DARK_LIGHT_RATIO = 0.055
BALANCE_SCHEMATIC_MIN_LIGHT = 0.62
BALANCE_TEXT_MIN_INK = 0.035
BALANCE_TEXT_MIN_DARK_LIGHT_RATIO = 0.055
BALANCE_TEXT_MAX_DARK_LIGHT_RATIO = 0.24
BALANCE_TEXT_MAX_MID = 0.45
BALANCE_IMAGE_MIN_INK = 0.08
BALANCE_IMAGE_MIN_DARK_LIGHT_RATIO = 0.34
BALANCE_IMAGE_MIN_MID = 0.48
TILE_OVERLAY_ALPHA = 0.26
TILE_BASE_ALPHA = 1.0 - TILE_OVERLAY_ALPHA

# HTML report defaults.
LAYOUT_REPORT_LABEL_ORDER = ["heading", "text", "schematic", "pcb", "diagram", "image", "table", "other"]
LAYOUT_REPORT_VISUAL_LABELS = ("schematic", "pcb", "diagram", "image", "table")
LAYOUT_REPORT_DEFAULT_PREVIEW_WIDTH = 1100
LAYOUT_REPORT_DEFAULT_FREQUENCY_HINT_MODE = "validate"
