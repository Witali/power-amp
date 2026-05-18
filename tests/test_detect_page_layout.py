import json
import tempfile
import unittest
from pathlib import Path

from scripts import detect_page_layout


@unittest.skipUnless(detect_page_layout.OPENCV_AVAILABLE, "OpenCV dependencies are not installed")
class DetectPageLayoutTests(unittest.TestCase):
    def test_normalize_accelerator_accepts_cpu(self) -> None:
        self.assertEqual(detect_page_layout.normalize_accelerator("cpu"), "cpu")

    def test_normalize_accelerator_rejects_unknown_backend(self) -> None:
        with self.assertRaises(ValueError):
            detect_page_layout.normalize_accelerator("quantum")

    def test_feature_classifier_recognizes_large_title_text(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.50,
            "height_ratio": 0.05,
            "area_ratio": 0.025,
            "wide_aspect": 1.00,
            "tall_aspect": 0.02,
            "ink_density": 0.24,
            "edge_density": 0.40,
            "gray_std": 0.78,
            "gray_levels": 0.75,
            "component_density": 0.82,
            "hline_density": 0.04,
            "vline_density": 0.08,
            "line_balance": 0.10,
            "textline_density": 0.42,
            "horizontal_text_score": 0.42,
            "vertical_text_score": 0.14,
            "diagonal_text_score": 0.20,
            "max_text_score": 0.42,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "text")
        self.assertGreater(confidence, 0.25)

    def test_feature_classifier_keeps_bold_display_title_as_text(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.6290,
            "height_ratio": 0.0656,
            "area_ratio": 0.0350,
            "wide_aspect": 1.00,
            "tall_aspect": 0.0324,
            "ink_density": 0.3709,
            "edge_density": 0.3831,
            "gray_std": 0.9372,
            "gray_levels": 0.9375,
            "component_density": 0.4191,
            "hline_density": 0.0,
            "vline_density": 1.0,
            "line_balance": 0.0,
            "textline_density": 0.3051,
            "horizontal_text_score": 0.3051,
            "vertical_text_score": 0.1484,
            "diagonal_text_score": 0.0602,
            "max_text_score": 0.3051,
            "line_art_score": 1.0,
            "saturation_mean": 0.20,
            "saturation_p80": 0.2627,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "text")
        self.assertGreater(confidence, 0.25)

    def test_feature_classifier_recognizes_colored_line_art_as_schematic(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.6290,
            "height_ratio": 0.2761,
            "area_ratio": 0.1737,
            "wide_aspect": 0.3453,
            "tall_aspect": 0.1159,
            "ink_density": 0.0872,
            "edge_density": 0.2715,
            "gray_std": 0.4792,
            "gray_levels": 0.9062,
            "component_density": 0.1759,
            "hline_density": 0.1333,
            "vline_density": 0.1151,
            "line_balance": 0.8635,
            "textline_density": 0.2897,
            "horizontal_text_score": 0.2897,
            "vertical_text_score": 0.6084,
            "diagonal_text_score": 0.2515,
            "max_text_score": 0.6084,
            "line_art_score": 0.3459,
            "saturation_mean": 0.3063,
            "saturation_p80": 0.3176,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "schematic/circuit")
        self.assertGreater(confidence, 0.25)

    def test_feature_classifier_recognizes_vertical_text(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.08,
            "height_ratio": 0.45,
            "area_ratio": 0.036,
            "wide_aspect": 0.04,
            "tall_aspect": 1.00,
            "ink_density": 0.12,
            "edge_density": 0.28,
            "gray_std": 0.35,
            "gray_levels": 0.45,
            "component_density": 0.72,
            "hline_density": 0.06,
            "vline_density": 0.10,
            "line_balance": 0.20,
            "textline_density": 0.12,
            "horizontal_text_score": 0.12,
            "vertical_text_score": 0.78,
            "diagonal_text_score": 0.22,
            "max_text_score": 0.78,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "text")
        self.assertEqual(detect_page_layout.infer_orientation(features), "vertical")
        self.assertGreater(confidence, 0.25)

    def test_feature_classifier_prefers_large_grayscale_line_art_as_schematic(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.91,
            "height_ratio": 0.46,
            "area_ratio": 0.42,
            "wide_aspect": 0.30,
            "tall_aspect": 0.14,
            "ink_density": 0.15,
            "edge_density": 0.40,
            "gray_std": 0.65,
            "gray_levels": 0.97,
            "component_density": 0.94,
            "hline_density": 0.06,
            "vline_density": 0.12,
            "line_balance": 0.54,
            "textline_density": 0.22,
            "horizontal_text_score": 0.22,
            "vertical_text_score": 0.10,
            "diagonal_text_score": 0.20,
            "max_text_score": 0.22,
            "line_art_score": 0.35,
            "saturation_mean": 0.00,
            "saturation_p80": 0.00,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "schematic/circuit")
        self.assertGreater(confidence, 0.35)

    def test_feature_classifier_prefers_labeled_line_art_page_region_as_schematic(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.92,
            "height_ratio": 0.49,
            "area_ratio": 0.45,
            "wide_aspect": 0.28,
            "tall_aspect": 0.14,
            "ink_density": 0.11,
            "edge_density": 0.32,
            "gray_std": 0.54,
            "gray_levels": 0.97,
            "component_density": 0.61,
            "hline_density": 0.03,
            "vline_density": 0.06,
            "line_balance": 0.57,
            "textline_density": 0.57,
            "horizontal_text_score": 0.57,
            "vertical_text_score": 0.38,
            "diagonal_text_score": 0.16,
            "max_text_score": 0.57,
            "line_art_score": 0.25,
            "saturation_mean": 0.00,
            "saturation_p80": 0.00,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "schematic/circuit")
        self.assertGreater(confidence, 0.35)

    def test_feature_classifier_prefers_small_technical_line_art_as_schematic(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.42,
            "height_ratio": 0.03,
            "area_ratio": 0.01,
            "wide_aspect": 1.00,
            "tall_aspect": 0.02,
            "ink_density": 0.08,
            "edge_density": 0.24,
            "gray_std": 0.44,
            "gray_levels": 0.88,
            "component_density": 0.47,
            "hline_density": 0.12,
            "vline_density": 0.25,
            "line_balance": 0.47,
            "textline_density": 0.80,
            "horizontal_text_score": 0.80,
            "vertical_text_score": 0.45,
            "diagonal_text_score": 0.08,
            "max_text_score": 0.80,
            "line_art_score": 0.41,
            "saturation_mean": 0.00,
            "saturation_p80": 0.00,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "schematic/circuit")
        self.assertGreater(confidence, 0.25)

    def test_feature_classifier_prefers_tiny_captioned_circuit_as_schematic(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.30,
            "height_ratio": 0.041,
            "area_ratio": 0.012,
            "wide_aspect": 1.00,
            "tall_aspect": 0.037,
            "ink_density": 0.126,
            "edge_density": 0.389,
            "gray_std": 0.559,
            "gray_levels": 0.91,
            "component_density": 1.0,
            "hline_density": 0.096,
            "vline_density": 0.210,
            "line_balance": 0.458,
            "textline_density": 1.0,
            "horizontal_text_score": 1.0,
            "vertical_text_score": 0.716,
            "diagonal_text_score": 1.0,
            "max_text_score": 1.0,
            "line_art_score": 0.542,
            "saturation_mean": 0.003,
            "saturation_p80": 0.004,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "schematic/circuit")
        self.assertGreater(confidence, 0.35)

    def test_feature_classifier_prefers_color_photo_over_schematic(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.30,
            "height_ratio": 0.17,
            "area_ratio": 0.05,
            "wide_aspect": 0.28,
            "tall_aspect": 0.15,
            "ink_density": 0.51,
            "edge_density": 0.47,
            "gray_std": 0.76,
            "gray_levels": 0.94,
            "component_density": 0.81,
            "hline_density": 1.00,
            "vline_density": 1.00,
            "line_balance": 0.85,
            "textline_density": 0.06,
            "horizontal_text_score": 0.06,
            "vertical_text_score": 0.04,
            "diagonal_text_score": 0.04,
            "max_text_score": 0.06,
            "line_art_score": 1.00,
            "saturation_mean": 0.22,
            "saturation_p80": 0.38,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "image")
        self.assertGreater(confidence, 0.35)

    def test_suppresses_text_inside_schematic_outline(self) -> None:
        schematic = detect_page_layout.Block(
            ident="001_schematic",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.90,
            bbox=[10, 10, 260, 180],
            outline=[[[20, 20], [250, 20], [250, 160], [20, 160]]],
            features={},
        )
        internal_text = detect_page_layout.Block(
            ident="002_text",
            label="text",
            orientation="horizontal",
            confidence=0.91,
            bbox=[70, 55, 70, 18],
            outline=None,
            features={},
        )
        wrapping_text = detect_page_layout.Block(
            ident="003_text",
            label="text",
            orientation="horizontal",
            confidence=0.91,
            bbox=[220, 165, 80, 22],
            outline=None,
            features={},
        )

        filtered = detect_page_layout.suppress_text_inside_schematics([schematic, internal_text, wrapping_text])

        self.assertEqual([block.ident for block in filtered], ["001_schematic", "003_text"])

    def test_suppresses_small_text_touching_schematic_top_edge(self) -> None:
        schematic = detect_page_layout.Block(
            ident="001_schematic",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.90,
            bbox=[50, 100, 500, 360],
            outline=[[[50, 100], [550, 100], [550, 460], [50, 460]]],
            features={},
        )
        top_label = detect_page_layout.Block(
            ident="002_text",
            label="text",
            orientation="horizontal",
            confidence=0.91,
            bbox=[120, 80, 120, 20],
            outline=None,
            features={},
        )
        side_text = detect_page_layout.Block(
            ident="003_text",
            label="text",
            orientation="horizontal",
            confidence=0.91,
            bbox=[570, 80, 120, 20],
            outline=None,
            features={},
        )

        filtered = detect_page_layout.suppress_text_inside_schematics([schematic, top_label, side_text])

        self.assertEqual([block.ident for block in filtered], ["001_schematic", "003_text"])

    def test_suppresses_text_block_nested_inside_larger_text_block(self) -> None:
        parent = detect_page_layout.Block(
            ident="001_text",
            label="text",
            orientation="horizontal",
            confidence=0.90,
            bbox=[1550, 32, 762, 3275],
            outline=None,
            features={},
        )
        nested = detect_page_layout.Block(
            ident="006_text",
            label="text",
            orientation="horizontal",
            confidence=0.86,
            bbox=[1567, 1168, 734, 74],
            outline=None,
            features={},
        )
        sibling = detect_page_layout.Block(
            ident="003_text",
            label="text",
            orientation="horizontal",
            confidence=0.90,
            bbox=[20, 82, 770, 1561],
            outline=None,
            features={},
        )

        filtered = detect_page_layout.suppress_nested_text_blocks([parent, nested, sibling])

        self.assertEqual([block.ident for block in filtered], ["001_text", "003_text"])

    def test_visual_outline_uses_simple_text_cutout(self) -> None:
        figure = detect_page_layout.Block(
            ident="001_schematic",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.90,
            bbox=[10, 10, 200, 100],
            outline=None,
            features={},
        )
        prose = detect_page_layout.Block(
            ident="002_text",
            label="text",
            orientation="horizontal",
            confidence=0.91,
            bbox=[150, 20, 80, 50],
            outline=None,
            features={},
        )

        outline = detect_page_layout.visual_outline_from_text_cutouts(figure, [prose])
        points = outline[0]

        self.assertLessEqual(len(points), 8)
        self.assertFalse(detect_page_layout.point_inside_outline((170, 40), outline))
        self.assertTrue(detect_page_layout.point_inside_outline((40, 40), outline))
        for first, second in zip(points, points[1:] + points[:1]):
            self.assertTrue(first[0] == second[0] or first[1] == second[1])

    def test_visual_outline_keeps_small_internal_labels(self) -> None:
        figure = detect_page_layout.Block(
            ident="001_schematic",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.90,
            bbox=[10, 10, 300, 200],
            outline=None,
            features={},
        )
        component_label = detect_page_layout.Block(
            ident="002_text",
            label="text",
            orientation="horizontal",
            confidence=0.91,
            bbox=[22, 20, 40, 15],
            outline=None,
            features={},
        )

        outline = detect_page_layout.visual_outline_from_text_cutouts(figure, [component_label])

        self.assertEqual(outline, [[[10, 10], [310, 10], [310, 210], [10, 210]]])
        self.assertTrue(detect_page_layout.point_inside_outline((35, 28), outline))

    def test_visual_outline_keeps_line_art_when_tall_text_column_overlaps(self) -> None:
        figure = detect_page_layout.Block(
            ident="001_schematic",
            label="diagram",
            orientation="unknown",
            confidence=0.90,
            bbox=[10, 100, 300, 140],
            outline=None,
            features={},
        )
        page_column = detect_page_layout.Block(
            ident="002_text",
            label="text",
            orientation="horizontal",
            confidence=0.70,
            bbox=[215, 20, 120, 360],
            outline=None,
            features={},
        )

        outline = detect_page_layout.visual_outline_from_text_cutouts(figure, [page_column])

        self.assertEqual(outline, [[[10, 100], [310, 100], [310, 240], [10, 240]]])

    def test_block_preview_label_includes_block_number(self) -> None:
        block = detect_page_layout.Block(
            ident="023_text",
            label="text",
            orientation="vertical",
            confidence=0.876,
            bbox=[0, 0, 10, 10],
            outline=None,
            features={},
        )

        self.assertEqual(detect_page_layout.block_preview_label(block), "#023 text vertical 0.88")

    def test_block_preview_label_shortens_schematic_label(self) -> None:
        block = detect_page_layout.Block(
            ident="007_schematic_circuit",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.89,
            bbox=[0, 0, 10, 10],
            outline=None,
            features={},
        )

        self.assertEqual(detect_page_layout.block_preview_label(block), "#007 schematic 0.89")

    def test_caption_highlight_boxes_deduplicates_candidates(self) -> None:
        first = detect_page_layout.Block(
            ident="001_schematic",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.90,
            bbox=[0, 0, 10, 10],
            outline=None,
            features={},
            caption_candidates=[{"bbox": [10, 20, 30, 12], "block": "010_text"}],
        )
        second = detect_page_layout.Block(
            ident="002_schematic",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.88,
            bbox=[0, 20, 10, 10],
            outline=None,
            features={},
            caption_candidates=[{"bbox": [10, 20, 30, 12], "block": "010_text"}],
        )

        boxes = detect_page_layout.caption_highlight_boxes([first, second])

        self.assertEqual([box.to_list() for box in boxes], [[10, 20, 30, 12]])

    def test_attaches_caption_candidates_to_visual_blocks(self) -> None:
        figure = detect_page_layout.Block(
            ident="001_schematic",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.90,
            bbox=[100, 100, 300, 180],
            outline=None,
            features={},
        )
        caption = detect_page_layout.Block(
            ident="002_text",
            label="text",
            orientation="horizontal",
            confidence=0.91,
            bbox=[110, 286, 70, 24],
            outline=None,
            features={},
        )
        far_text = detect_page_layout.Block(
            ident="003_text",
            label="text",
            orientation="horizontal",
            confidence=0.91,
            bbox=[520, 286, 70, 24],
            outline=None,
            features={},
        )

        detect_page_layout.attach_caption_candidates([figure], [caption, far_text])

        self.assertIsNotNone(figure.caption_candidates)
        self.assertEqual(figure.caption_candidates[0]["block"], "002_text")
        self.assertEqual(figure.caption_candidates[0]["position"], "below")

    def test_attaches_caption_to_short_technical_figure(self) -> None:
        figure = detect_page_layout.Block(
            ident="024_schematic_circuit",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.90,
            bbox=[54, 3028, 1046, 83],
            outline=None,
            features={},
        )
        caption = detect_page_layout.Block(
            ident="026_text",
            label="text",
            orientation="horizontal",
            confidence=0.90,
            bbox=[63, 3182, 184, 69],
            outline=None,
            features={},
        )

        detect_page_layout.attach_caption_candidates([figure], [caption])

        self.assertIsNotNone(figure.caption_candidates)
        self.assertEqual(figure.caption_candidates[0]["block"], "026_text")
        self.assertEqual(figure.caption_candidates[0]["position"], "below")

    def test_adds_internal_caption_probe_for_unmatched_schematic(self) -> None:
        figure = detect_page_layout.Block(
            ident="007_schematic_circuit",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.89,
            bbox=[40, 1700, 1500, 1550],
            outline=None,
            features={},
        )

        detect_page_layout.attach_caption_candidates([figure], [])

        self.assertIsNotNone(figure.caption_candidates)
        self.assertEqual(figure.caption_candidates[0]["block"], "internal_caption_probe")
        self.assertEqual(figure.caption_candidates[0]["position"], "inside-bottom-left-probe")

    def test_synthetic_page_writes_layout_preview_and_crops(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        page = np.full((520, 720, 3), 255, dtype=np.uint8)

        for row in range(40, 210, 18):
            cv2.rectangle(page, (40, row), (310, row + 5), (0, 0, 0), -1)
            cv2.rectangle(page, (40, row + 8), (230, row + 11), (0, 0, 0), -1)

        rng = np.random.default_rng(1)
        photo = rng.integers(40, 220, size=(155, 220, 3), dtype=np.uint8)
        page[45:200, 430:650] = photo

        cv2.rectangle(page, (70, 315), (300, 455), (0, 0, 0), 2)
        cv2.line(page, (90, 385), (280, 385), (0, 0, 0), 2)
        cv2.line(page, (180, 335), (180, 440), (0, 0, 0), 2)
        cv2.circle(page, (180, 385), 34, (0, 0, 0), 2)
        cv2.line(page, (370, 340), (640, 340), (0, 0, 0), 2)
        cv2.line(page, (370, 430), (640, 430), (0, 0, 0), 2)
        cv2.line(page, (430, 305), (430, 465), (0, 0, 0), 2)
        cv2.line(page, (560, 305), (560, 465), (0, 0, 0), 2)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_path = root / "synthetic_page.png"
            detect_page_layout.write_image(image_path, page)

            result = detect_page_layout.detect_page_layout(image_path, root / "layout", max_analysis_side=900)
            page_dir = root / "layout" / "synthetic_page"
            layout_path = page_dir / "layout.json"
            preview_path = page_dir / "preview.png"

            self.assertTrue(layout_path.exists())
            self.assertTrue(preview_path.exists())
            self.assertTrue((page_dir / "blocks").exists())
            self.assertGreaterEqual(len(result["blocks"]), 2)

            saved = json.loads(layout_path.read_text(encoding="utf-8"))
            labels = {block["label"] for block in saved["blocks"]}
            self.assertTrue(labels & {"text", "image", "schematic/circuit", "diagram", "table"})
            self.assertTrue(all("orientation" in block for block in saved["blocks"]))
            self.assertTrue(all("caption_candidates" in block for block in saved["blocks"]))
            self.assertTrue(saved["frequency_hints_enabled"])
            self.assertIn("frequency_hints", saved)
            self.assertIn("frequency_cluster_hints", saved)
            self.assertIn("frequency_warnings", saved)
            self.assertIn("frequency_cluster_warnings", saved)

    def test_split_box_by_vertical_gap_separates_margin_strip(self) -> None:
        np = detect_page_layout.np

        mask = np.zeros((220, 320), dtype=np.uint8)
        mask[10:210, 10:230] = 255
        mask[10:210, 275:315] = 255
        box = detect_page_layout.Box(10, 10, 305, 200)

        pieces = detect_page_layout.split_box_by_vertical_gaps(mask, box, 320, 220)

        self.assertEqual(len(pieces), 2)
        self.assertLess(pieces[0].w, box.w)
        self.assertLess(pieces[1].w, box.w)

    def test_split_box_by_side_color_strip_separates_colored_margin(self) -> None:
        np = detect_page_layout.np

        page = np.full((240, 360, 3), 245, dtype=np.uint8)
        page[20:220, 20:300] = (245, 245, 245)
        page[20:220, 300:345] = (40, 100, 40)
        box = detect_page_layout.Box(20, 20, 325, 200)

        pieces = detect_page_layout.split_box_by_side_color_strip(page, box, 360, 240)

        self.assertEqual(len(pieces), 2)
        self.assertLess(pieces[0].w, box.w)
        self.assertLess(pieces[1].w, box.w)

    def test_projection_runs_finds_active_segments(self) -> None:
        np = detect_page_layout.np

        values = np.array([0, 0, 5, 7, 8, 0, 1, 9, 10, 9, 0], dtype=np.float32)

        self.assertEqual(detect_page_layout.projection_runs(values, threshold=4, min_run=2), [(2, 4), (7, 9)])

    def test_split_text_box_around_visuals_removes_embedded_image(self) -> None:
        text_box = detect_page_layout.Box(10, 20, 220, 300)
        image_box = detect_page_layout.Box(50, 230, 130, 70)

        pieces = detect_page_layout.split_text_box_around_visuals(text_box, [image_box], 260, 360)

        self.assertGreaterEqual(len(pieces), 1)
        self.assertTrue(all(detect_page_layout.overlap_area(piece, image_box) == 0 for piece in pieces))
        self.assertTrue(any(piece.y2 < image_box.y for piece in pieces))

    def test_text_boxes_from_oversized_regions_recovers_column_text(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        page = np.full((620, 520, 3), 245, dtype=np.uint8)
        for row in range(35, 500, 16):
            cv2.rectangle(page, (25, row), (165, row + 10), (0, 0, 0), -1)
        for row in range(40, 210, 16):
            cv2.rectangle(page, (205, row), (330, row + 10), (0, 0, 0), -1)
            cv2.rectangle(page, (360, row), (485, row + 10), (0, 0, 0), -1)

        schematic = detect_page_layout.Box(200, 245, 285, 120)
        cv2.rectangle(page, (schematic.x, schematic.y), (schematic.x2, schematic.y2), (0, 0, 0), 2)
        cv2.line(page, (220, 300), (465, 300), (0, 0, 0), 2)
        cv2.line(page, (330, 260), (330, 345), (0, 0, 0), 2)
        for row in range(390, 540, 16):
            cv2.rectangle(page, (205, row), (330, row + 10), (0, 0, 0), -1)
            cv2.rectangle(page, (360, row), (485, row + 10), (0, 0, 0), -1)

        stamp = detect_page_layout.Box(220, 550, 120, 45)
        cv2.ellipse(page, (280, 572), (58, 20), 0, 0, 360, (50, 95, 50), -1)
        already_found_text_column = detect_page_layout.Box(20, 30, 155, 480)

        gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
        boxes = detect_page_layout.text_boxes_from_oversized_regions(
            page,
            gray,
            [detect_page_layout.Box(10, 10, 500, 590)],
            [already_found_text_column, schematic, stamp],
            520,
            620,
        )

        self.assertTrue(any(box.x < 80 and box.h > 250 for box in boxes))
        self.assertTrue(any(190 <= box.x <= 230 and box.y < schematic.y for box in boxes))
        self.assertTrue(any(box.x > 330 and box.y < schematic.y for box in boxes))
        self.assertTrue(all(detect_page_layout.overlap_area(box, schematic) == 0 for box in boxes))

    def test_line_art_boxes_from_large_regions_finds_embedded_schematic(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        page = np.full((620, 520, 3), 245, dtype=np.uint8)
        for row in range(35, 250, 16):
            cv2.rectangle(page, (25, row), (165, row + 10), (0, 0, 0), -1)
            cv2.rectangle(page, (205, row), (345, row + 10), (0, 0, 0), -1)
        schematic = detect_page_layout.Box(65, 300, 390, 180)
        cv2.rectangle(page, (schematic.x, schematic.y), (schematic.x2, schematic.y2), (0, 0, 0), 2)
        cv2.line(page, (90, 390), (430, 390), (0, 0, 0), 2)
        cv2.line(page, (180, 320), (180, 460), (0, 0, 0), 2)
        cv2.line(page, (320, 320), (320, 460), (0, 0, 0), 2)
        cv2.circle(page, (250, 390), 42, (0, 0, 0), 2)

        gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
        foreground, _, _ = detect_page_layout.foreground_mask(gray)
        boxes = detect_page_layout.line_art_boxes_from_large_regions(
            page,
            foreground,
            gray,
            [detect_page_layout.Box(10, 10, 500, 590)],
            520,
            620,
        )

        self.assertTrue(boxes)
        best = max(boxes, key=lambda box: detect_page_layout.overlap_area(box, schematic))
        self.assertGreaterEqual(detect_page_layout.overlap_area(best, schematic) / schematic.area, 0.65)

    def test_merges_adjacent_schematics_when_lines_bridge_the_gap(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        page = np.full((600, 520, 3), 255, dtype=np.uint8)
        upper = detect_page_layout.Box(70, 40, 360, 110)
        lower = detect_page_layout.Box(55, 158, 390, 120)
        cv2.rectangle(page, (upper.x, upper.y), (upper.x2, upper.y2), (0, 0, 0), 2)
        cv2.rectangle(page, (lower.x, lower.y), (lower.x2, lower.y2), (0, 0, 0), 2)
        cv2.line(page, (180, upper.y2 - 16), (180, lower.y + 16), (0, 0, 0), 2)
        cv2.line(page, (300, upper.y2 - 10), (300, lower.y + 10), (0, 0, 0), 2)

        gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
        mask, _, _ = detect_page_layout.foreground_mask(gray)
        edges = detect_page_layout.canny_edges(gray)
        ann = detect_page_layout.train_bootstrap_ann()
        first = detect_page_layout.Block(
            ident="003_schematic_circuit",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.90,
            bbox=upper.to_list(),
            outline=None,
            features={},
        )
        second = detect_page_layout.Block(
            ident="005_schematic_circuit",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.92,
            bbox=lower.to_list(),
            outline=None,
            features={},
        )

        merged = detect_page_layout.merge_connected_schematic_blocks(
            [(first, upper), (second, lower)], page, mask, edges, ann, scale=1.0, width=520, height=320
        )

        self.assertEqual(len(merged), 1)
        block, box = merged[0]
        self.assertEqual(block.ident, "003_schematic_circuit")
        self.assertEqual(block.label, "schematic/circuit")
        self.assertEqual(box.to_list(), detect_page_layout.union_box(upper, lower).to_list())
        self.assertEqual(block.features["line_bridge_merge"], 1.0)

    def test_merges_low_confidence_line_art_strip_into_schematic(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        page = np.full((320, 520, 3), 255, dtype=np.uint8)
        strip = detect_page_layout.Box(55, 35, 390, 72)
        schematic = detect_page_layout.Box(55, 112, 390, 170)
        cv2.rectangle(page, (strip.x, strip.y), (strip.x2, strip.y2), (0, 0, 0), 2)
        cv2.line(page, (120, strip.y2 - 8), (120, schematic.y + 8), (0, 0, 0), 2)
        cv2.rectangle(page, (schematic.x, schematic.y), (schematic.x2, schematic.y2), (0, 0, 0), 2)

        gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
        mask, _, _ = detect_page_layout.foreground_mask(gray)
        edges = detect_page_layout.canny_edges(gray)
        ann = detect_page_layout.train_bootstrap_ann()
        strip_block = detect_page_layout.Block(
            ident="005_text",
            label="text",
            orientation="horizontal",
            confidence=0.28,
            bbox=strip.to_list(),
            outline=None,
            features={
                "line_art_score": 0.34,
                "edge_density": 0.24,
                "ink_density": 0.08,
                "saturation_p80": 0.0,
            },
        )
        schematic_block = detect_page_layout.Block(
            ident="007_schematic_circuit",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.87,
            bbox=schematic.to_list(),
            outline=None,
            features={},
        )

        merged = detect_page_layout.merge_line_art_attachments_into_schematics(
            [(strip_block, strip), (schematic_block, schematic)],
            page,
            mask,
            edges,
            ann,
            scale=1.0,
            width=520,
            height=600,
        )

        self.assertEqual(len(merged), 1)
        block, box = merged[0]
        self.assertEqual(block.ident, "007_schematic_circuit")
        self.assertEqual(block.label, "schematic/circuit")
        self.assertEqual(box.to_list(), detect_page_layout.union_box(strip, schematic).to_list())
        self.assertEqual(block.features["line_art_attachment_merge"], 1.0)

    def test_merges_stacked_waveform_strips_into_one_diagram(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        page = np.full((900, 520, 3), 255, dtype=np.uint8)
        boxes = [
            detect_page_layout.Box(40, 80, 360, 42),
            detect_page_layout.Box(42, 118, 358, 42),
            detect_page_layout.Box(40, 156, 360, 42),
            detect_page_layout.Box(42, 194, 358, 60),
        ]
        caption = detect_page_layout.Box(42, 256, 80, 30)
        for box in boxes:
            cv2.line(page, (box.x + 12, box.y + box.h // 2), (box.x2 - 12, box.y + box.h // 2), (0, 0, 0), 2)
            cv2.rectangle(page, (box.x + 70, box.y + 8), (box.x + 120, box.y + box.h - 8), (0, 0, 0), 2)
        cv2.putText(page, "Fig. 3", (caption.x + 2, caption.y + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

        gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
        mask, _, _ = detect_page_layout.foreground_mask(gray)
        edges = detect_page_layout.canny_edges(gray)
        ann = detect_page_layout.train_bootstrap_ann()
        seed_features = {
            "line_art_score": 0.42,
            "edge_density": 0.25,
            "saturation_p80": 0.0,
        }
        classified = [
            (
                detect_page_layout.Block(
                    ident=f"{index:03d}_text",
                    label="text",
                    orientation="horizontal",
                    confidence=0.74,
                    bbox=box.to_list(),
                    outline=None,
                    features=dict(seed_features),
                ),
                box,
            )
            for index, box in enumerate(boxes, start=16)
        ]
        classified.append(
            (
                detect_page_layout.Block(
                    ident="025_text",
                    label="text",
                    orientation="horizontal",
                    confidence=0.90,
                    bbox=caption.to_list(),
                    outline=None,
                    features={},
                ),
                caption,
            )
        )

        merged = detect_page_layout.merge_stacked_diagram_blocks(
            classified,
            page,
            mask,
            edges,
            ann,
            scale=1.0,
            width=520,
            height=900,
        )

        self.assertEqual(len(merged), 1)
        block, box = merged[0]
        self.assertEqual(block.label, "diagram")
        self.assertEqual(block.ident, "016_diagram")
        self.assertEqual(box.to_list(), [40, 80, 360, 206])
        self.assertEqual(block.features["stacked_diagram_merge"], 1.0)

    def test_demotes_stacked_bold_heading_wrapper_to_text(self) -> None:
        block = detect_page_layout.Block(
            ident="001_diagram",
            label="diagram",
            orientation="unknown",
            confidence=0.95,
            bbox=[966, 33, 1469, 393],
            outline=None,
            features={
                "stacked_diagram_merge": 1.0,
                "hline_density": 0.0,
                "vline_density": 0.0,
                "textline_density": 0.34,
                "ink_density": 0.15,
                "area_ratio": 0.069,
            },
        )
        box = detect_page_layout.Box(966, 33, 1469, 393)

        demoted = detect_page_layout.demote_textual_diagram_wrappers([(block, box)])

        self.assertEqual(demoted[0][0].label, "text")
        self.assertEqual(demoted[0][0].orientation, "horizontal")
        self.assertEqual(demoted[0][0].ident, "001_text")
        self.assertEqual(demoted[0][0].features["textual_diagram_wrapper_demote"], 1.0)

    def test_keeps_stacked_waveform_wrapper_as_diagram(self) -> None:
        block = detect_page_layout.Block(
            ident="016_diagram",
            label="diagram",
            orientation="unknown",
            confidence=0.90,
            bbox=[52, 2585, 1050, 666],
            outline=None,
            features={
                "stacked_diagram_merge": 1.0,
                "hline_density": 0.078,
                "vline_density": 0.0,
                "textline_density": 0.80,
                "ink_density": 0.089,
                "area_ratio": 0.084,
            },
        )
        box = detect_page_layout.Box(52, 2585, 1050, 666)

        demoted = detect_page_layout.demote_textual_diagram_wrappers([(block, box)])

        self.assertEqual(demoted[0][0].label, "diagram")
        self.assertEqual(demoted[0][0].ident, "016_diagram")

    def test_suppresses_small_artifact_strip_touching_schematic(self) -> None:
        schematic = detect_page_layout.Block(
            ident="003_schematic_circuit",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.93,
            bbox=[50, 50, 420, 300],
            outline=None,
            features={},
        )
        strip = detect_page_layout.Block(
            ident="009_image",
            label="image",
            orientation="unknown",
            confidence=0.51,
            bbox=[55, 354, 400, 24],
            outline=None,
            features={},
        )
        photo = detect_page_layout.Block(
            ident="010_image",
            label="image",
            orientation="unknown",
            confidence=0.80,
            bbox=[520, 50, 120, 100],
            outline=None,
            features={},
        )

        filtered = detect_page_layout.suppress_small_artifacts_near_schematics([schematic, strip, photo])

        self.assertEqual([block.ident for block in filtered], ["003_schematic_circuit", "010_image"])

    def test_close_or_overlapping_keeps_large_layout_blocks_separate(self) -> None:
        upper_text = detect_page_layout.Box(50, 301, 850, 154)
        lower_column = detect_page_layout.Box(473, 454, 426, 327)

        self.assertFalse(detect_page_layout.close_or_overlapping(upper_text, lower_column, margin=8))

    def test_infer_orientation_keeps_wide_display_text_horizontal(self) -> None:
        features = {
            "wide_aspect": 1.00,
            "tall_aspect": 0.03,
            "horizontal_text_score": 0.42,
            "vertical_text_score": 0.58,
            "diagonal_text_score": 0.91,
        }

        self.assertEqual(detect_page_layout.infer_orientation(features), "horizontal")

    def test_feature_classifier_recognizes_text_like_features(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.45,
            "height_ratio": 0.25,
            "area_ratio": 0.10,
            "wide_aspect": 0.55,
            "tall_aspect": 0.10,
            "ink_density": 0.10,
            "edge_density": 0.08,
            "gray_std": 0.12,
            "gray_levels": 0.18,
            "component_density": 0.85,
            "hline_density": 0.10,
            "vline_density": 0.02,
            "line_balance": 0.12,
            "textline_density": 0.90,
            "horizontal_text_score": 0.90,
            "vertical_text_score": 0.12,
            "diagonal_text_score": 0.18,
            "max_text_score": 0.90,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "text")
        self.assertGreater(confidence, 0.25)


if __name__ == "__main__":
    unittest.main()
