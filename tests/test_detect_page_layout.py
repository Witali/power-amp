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

    def test_feature_classifier_recognizes_large_title_as_heading(self) -> None:
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

        self.assertEqual(label, "heading")
        self.assertGreater(confidence, 0.25)

    def test_feature_classifier_keeps_bold_display_title_as_heading(self) -> None:
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

        self.assertEqual(label, "heading")
        self.assertGreater(confidence, 0.25)

    def test_feature_classifier_recognizes_saturated_article_title_as_heading(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.47654,
            "height_ratio": 0.12611,
            "area_ratio": 0.06010,
            "wide_aspect": 0.57269,
            "tall_aspect": 0.06985,
            "ink_density": 0.21544,
            "edge_density": 0.26142,
            "gray_std": 0.69475,
            "gray_levels": 0.81250,
            "component_density": 0.36598,
            "hline_density": 0.0,
            "vline_density": 0.02342,
            "line_balance": 0.0,
            "textline_density": 0.31718,
            "horizontal_text_score": 0.31718,
            "vertical_text_score": 0.05538,
            "diagonal_text_score": 0.11613,
            "max_text_score": 0.31718,
            "line_art_score": 1.0,
            "saturation_mean": 0.20863,
            "saturation_p80": 0.47451,
            "component_signature_score": 0.79371,
            "resistor_symbol_density": 1.0,
            "capacitor_symbol_density": 1.0,
            "diode_symbol_density": 0.0,
            "transistor_symbol_density": 0.85395,
            "pcb_trace_density": 1.0,
            "pcb_pad_density": 1.0,
            "pcb_board_outline_score": 1.0,
            "pcb_signature_score": 1.0,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "heading")
        self.assertGreater(confidence, 0.25)

    def test_feature_classifier_does_not_promote_horizontal_rule_to_heading(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.86182,
            "height_ratio": 0.01389,
            "area_ratio": 0.01197,
            "wide_aspect": 1.0,
            "tall_aspect": 0.00278,
            "ink_density": 0.17025,
            "edge_density": 0.31591,
            "gray_std": 0.70651,
            "gray_levels": 1.0,
            "component_density": 0.06612,
            "hline_density": 1.0,
            "vline_density": 0.0,
            "line_balance": 0.0,
            "textline_density": 0.72,
            "horizontal_text_score": 0.72,
            "vertical_text_score": 0.0,
            "diagonal_text_score": 0.0,
            "max_text_score": 0.72,
            "line_art_score": 0.99332,
            "saturation_p80": 0.0,
            "component_signature_score": 0.0,
        }

        label, _ = detect_page_layout.classify_features(ann, features)
        block = detect_page_layout.Block("001_heading", label, "horizontal", 0.70, [132, 150, 2154, 45], None, features)

        self.assertTrue(detect_page_layout.horizontal_rule_features(features))
        self.assertNotEqual(label, "heading")
        self.assertEqual(detect_page_layout.suppress_horizontal_rule_artifacts([block]), [])

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

    def test_feature_classifier_recovers_large_component_line_art_as_schematic(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.57550,
            "height_ratio": 0.31111,
            "area_ratio": 0.17904,
            "wide_aspect": 0.28857,
            "tall_aspect": 0.13861,
            "ink_density": 0.10222,
            "edge_density": 0.29231,
            "gray_std": 0.68966,
            "gray_levels": 1.0,
            "component_density": 0.43980,
            "hline_density": 0.03986,
            "vline_density": 0.21871,
            "line_balance": 0.18225,
            "textline_density": 0.22500,
            "horizontal_text_score": 0.22500,
            "vertical_text_score": 0.69059,
            "diagonal_text_score": 0.28378,
            "max_text_score": 0.69059,
            "line_art_score": 0.34894,
            "saturation_p80": 0.0,
            "component_signature_score": 0.97696,
            "resistor_symbol_density": 1.0,
            "capacitor_symbol_density": 1.0,
            "diode_symbol_density": 1.0,
            "transistor_symbol_density": 0.64975,
            "pcb_trace_density": 0.14299,
            "pcb_pad_density": 1.0,
            "pcb_board_outline_score": 1.0,
            "pcb_signature_score": 0.54296,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "schematic/circuit")
        self.assertGreater(confidence, 0.55)

    def test_feature_classifier_recognizes_single_axis_waveform_as_diagram(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.28977,
            "height_ratio": 0.12500,
            "area_ratio": 0.03622,
            "wide_aspect": 0.46382,
            "tall_aspect": 0.08627,
            "ink_density": 0.09171,
            "edge_density": 0.23686,
            "gray_std": 0.68339,
            "gray_levels": 1.0,
            "component_density": 0.19608,
            "hline_density": 0.42569,
            "vline_density": 0.03686,
            "line_balance": 0.08660,
            "textline_density": 1.0,
            "horizontal_text_score": 1.0,
            "vertical_text_score": 0.17647,
            "diagonal_text_score": 0.06977,
            "max_text_score": 1.0,
            "line_art_score": 0.48157,
            "saturation_p80": 0.0,
            "component_signature_score": 0.82301,
            "pcb_signature_score": 0.44845,
            "pcb_trace_density": 0.01174,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertTrue(detect_page_layout.single_axis_waveform_diagram_features(features))
        self.assertEqual(label, "diagram")
        self.assertGreater(confidence, 0.60)

    def test_feature_classifier_keeps_short_labeled_waveform_as_diagram(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.28977,
            "height_ratio": 0.06611,
            "area_ratio": 0.01916,
            "wide_aspect": 0.87664,
            "tall_aspect": 0.04563,
            "ink_density": 0.12228,
            "edge_density": 0.30854,
            "gray_std": 0.76661,
            "gray_levels": 1.0,
            "component_density": 0.32954,
            "hline_density": 0.27305,
            "vline_density": 0.16887,
            "line_balance": 0.61847,
            "textline_density": 0.75630,
            "horizontal_text_score": 0.75630,
            "vertical_text_score": 0.13235,
            "diagonal_text_score": 0.18000,
            "max_text_score": 0.75630,
            "line_art_score": 0.62790,
            "saturation_p80": 0.0,
            "component_signature_score": 0.82000,
            "pcb_signature_score": 0.30130,
            "pcb_trace_density": 0.05302,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertTrue(detect_page_layout.single_axis_waveform_diagram_features(features))
        self.assertEqual(label, "diagram")
        self.assertGreater(confidence, 0.60)

    def test_feature_classifier_recovers_large_vertical_label_schematic(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.48864,
            "height_ratio": 0.43667,
            "area_ratio": 0.21337,
            "wide_aspect": 0.22375,
            "tall_aspect": 0.17860,
            "ink_density": 0.08665,
            "edge_density": 0.24410,
            "gray_std": 0.64827,
            "gray_levels": 1.0,
            "component_density": 0.25519,
            "hline_density": 0.04482,
            "vline_density": 0.18460,
            "line_balance": 0.24279,
            "textline_density": 0.29771,
            "horizontal_text_score": 0.29771,
            "vertical_text_score": 0.78488,
            "diagonal_text_score": 0.09100,
            "max_text_score": 0.78488,
            "line_art_score": 0.30753,
            "saturation_p80": 0.0,
            "component_signature_score": 0.92271,
            "pcb_signature_score": 0.46446,
            "pcb_trace_density": 0.03397,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "schematic/circuit")
        self.assertGreater(confidence, 0.55)

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

    def test_component_signature_boosts_schematic_over_diagram(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.36,
            "height_ratio": 0.18,
            "area_ratio": 0.06,
            "wide_aspect": 0.40,
            "tall_aspect": 0.10,
            "ink_density": 0.12,
            "edge_density": 0.34,
            "gray_std": 0.34,
            "gray_levels": 0.55,
            "component_density": 0.42,
            "hline_density": 0.20,
            "vline_density": 0.18,
            "line_balance": 0.55,
            "textline_density": 0.42,
            "horizontal_text_score": 0.42,
            "vertical_text_score": 0.24,
            "diagonal_text_score": 0.18,
            "max_text_score": 0.42,
            "line_art_score": 0.32,
            "saturation_mean": 0.0,
            "saturation_p80": 0.0,
            "component_signature_score": 0.42,
            "resistor_symbol_density": 0.45,
            "capacitor_symbol_density": 0.35,
            "diode_symbol_density": 0.18,
            "transistor_symbol_density": 0.10,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "schematic/circuit")
        self.assertGreater(confidence, 0.35)

    def test_pcb_signature_boosts_pcb_over_schematic(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.43,
            "height_ratio": 0.52,
            "area_ratio": 0.18,
            "wide_aspect": 0.36,
            "tall_aspect": 0.24,
            "ink_density": 0.15,
            "edge_density": 0.31,
            "gray_std": 0.70,
            "gray_levels": 0.94,
            "component_density": 0.45,
            "hline_density": 0.12,
            "vline_density": 0.17,
            "line_balance": 0.72,
            "textline_density": 0.12,
            "horizontal_text_score": 0.12,
            "vertical_text_score": 0.10,
            "diagonal_text_score": 0.14,
            "max_text_score": 0.16,
            "line_art_score": 0.46,
            "saturation_mean": 0.0,
            "saturation_p80": 0.0,
            "component_signature_score": 0.98,
            "pcb_trace_density": 0.82,
            "pcb_pad_density": 0.65,
            "pcb_board_outline_score": 0.30,
            "pcb_signature_score": 0.86,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "pcb")
        self.assertGreater(confidence, 0.35)

    def test_pcb_signature_classifies_bold_heading_as_heading(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.48,
            "height_ratio": 0.10,
            "area_ratio": 0.047,
            "wide_aspect": 0.74,
            "tall_aspect": 0.05,
            "ink_density": 0.26,
            "edge_density": 0.29,
            "gray_std": 0.74,
            "gray_levels": 0.78,
            "component_density": 0.33,
            "hline_density": 0.00,
            "vline_density": 0.66,
            "line_balance": 0.00,
            "textline_density": 0.31,
            "horizontal_text_score": 0.31,
            "vertical_text_score": 0.22,
            "diagonal_text_score": 0.12,
            "max_text_score": 0.31,
            "line_art_score": 1.00,
            "saturation_mean": 0.0,
            "saturation_p80": 0.0,
            "component_signature_score": 0.34,
            "pcb_trace_density": 1.00,
            "pcb_pad_density": 0.00,
            "pcb_board_outline_score": 1.00,
            "pcb_signature_score": 0.90,
        }

        label, _ = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "heading")

    def test_splits_multiline_text_block_at_column_gutter(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        mask = np.zeros((260, 700), dtype=np.uint8)
        for row in range(5):
            y = 28 + row * 34
            cv2.rectangle(mask, (40, y), (275, y + 12), 255, -1)
            cv2.rectangle(mask, (430, y), (650, y + 12), 255, -1)
        box = detect_page_layout.Box(20, 12, 660, 190)

        pieces = detect_page_layout.split_multiline_text_box_recursive(mask, box, page_width=1000, page_height=1000)

        self.assertEqual(len(pieces), 2)
        self.assertLessEqual(pieces[0].x2, pieces[1].x)
        self.assertGreaterEqual(pieces[0].w, 250)
        self.assertGreaterEqual(pieces[1].w, 250)

    def test_does_not_split_single_line_heading_at_word_gap(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        mask = np.zeros((180, 700), dtype=np.uint8)
        cv2.rectangle(mask, (35, 70), (280, 94), 255, -1)
        cv2.rectangle(mask, (420, 70), (650, 94), 255, -1)
        box = detect_page_layout.Box(20, 40, 660, 90)

        pieces = detect_page_layout.split_multiline_text_box_recursive(mask, box, page_width=1000, page_height=1000)

        self.assertEqual(pieces, [box])

    def test_merges_fragmented_annual_contents_rows_then_splits_columns(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        image = np.full((1000, 1000, 3), 255, dtype=np.uint8)
        mask = np.zeros((1000, 1000), dtype=np.uint8)
        for row in range(5):
            y = 100 + row * 60
            cv2.rectangle(mask, (40, y + 4), (390, y + 22), 255, -1)
            cv2.rectangle(mask, (540, y + 4), (900, y + 22), 255, -1)
        edges = mask.copy()
        ann = detect_page_layout.train_bootstrap_ann()
        classified = []
        features = {
            "max_text_score": 0.72,
            "line_art_score": 0.12,
            "saturation_p80": 0.0,
        }
        for index, row in enumerate(range(5), start=1):
            box = detect_page_layout.Box(30, 96 + row * 60, 900, 28)
            classified.append(
                (
                    detect_page_layout.Block(
                        ident=f"{index:03d}_text",
                        label="text",
                        orientation="horizontal",
                        confidence=0.88,
                        bbox=box.to_list(),
                        outline=None,
                        features=features,
                    ),
                    box,
                )
            )

        merged = detect_page_layout.merge_fragmented_contents_text_rows(
            classified,
            image,
            mask,
            edges,
            ann,
            scale=1.0,
            width=1000,
            height=1000,
        )
        split = detect_page_layout.split_text_columns_in_classified_blocks(
            merged,
            image,
            mask,
            edges,
            ann,
            scale=1.0,
            width=1000,
            height=1000,
        )

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0][0].features["contents_row_merge"], 1.0)
        self.assertEqual(len(split), 2)
        self.assertLessEqual(split[0][1].x2, split[1][1].x)

    def test_merges_adjacent_annual_contents_column_fragments(self) -> None:
        np = detect_page_layout.np

        image = np.full((1400, 1000, 3), 255, dtype=np.uint8)
        mask = np.zeros((1400, 1000), dtype=np.uint8)
        edges = mask.copy()
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "max_text_score": 0.74,
            "line_art_score": 0.10,
            "saturation_p80": 0.0,
        }
        upper_box = detect_page_layout.Box(42, 360, 420, 260)
        lower_box = detect_page_layout.Box(42, 620, 420, 510)
        right_box = detect_page_layout.Box(510, 360, 430, 770)
        classified = [
            (
                detect_page_layout.Block("003_text", "text", "horizontal", 0.85, upper_box.to_list(), None, features),
                upper_box,
            ),
            (
                detect_page_layout.Block("005_text", "text", "horizontal", 0.87, lower_box.to_list(), None, features),
                lower_box,
            ),
            (
                detect_page_layout.Block("004_text", "text", "horizontal", 0.87, right_box.to_list(), None, features),
                right_box,
            ),
        ]

        merged = detect_page_layout.merge_fragmented_contents_columns(
            classified,
            image,
            mask,
            edges,
            ann,
            scale=1.0,
            width=1000,
            height=1400,
        )

        self.assertEqual(len(merged), 2)
        merged_boxes = {item[0].ident: item[1].to_list() for item in merged}
        self.assertEqual(merged_boxes["003_text"], [42, 360, 420, 770])
        self.assertEqual(merged_boxes["004_text"], right_box.to_list())
        self.assertEqual(merged[0][0].features["contents_column_merge"], 1.0)

    def test_merges_annual_contents_number_columns_into_text_blocks(self) -> None:
        np = detect_page_layout.np

        image = np.full((1400, 1000, 3), 255, dtype=np.uint8)
        mask = np.zeros((1400, 1000), dtype=np.uint8)
        edges = mask.copy()
        ann = detect_page_layout.train_bootstrap_ann()
        text_box = detect_page_layout.Box(80, 220, 390, 740)
        numbers_box = detect_page_layout.Box(470, 220, 64, 740)
        text_features = {"max_text_score": 0.82, "saturation_p80": 0.0}
        numbers_features = {
            "max_text_score": 0.92,
            "saturation_p80": 0.0,
            "hline_density": 0.0,
            "vline_density": 0.0,
        }
        classified = [
            (
                detect_page_layout.Block("008_text", "text", "horizontal", 0.87, text_box.to_list(), None, text_features),
                text_box,
            ),
            (
                detect_page_layout.Block("009_text", "text", "vertical", 0.85, numbers_box.to_list(), None, numbers_features),
                numbers_box,
            ),
        ]

        merged = detect_page_layout.merge_contents_number_columns(
            classified,
            image,
            mask,
            edges,
            ann,
            scale=1.0,
            width=1000,
            height=1400,
        )

        self.assertEqual(len(merged), 1)
        block, box = merged[0]
        self.assertEqual(block.label, "text")
        self.assertEqual(box.to_list(), [80, 220, 454, 740])
        self.assertEqual(block.features["contents_number_column_merge"], 1.0)

    def test_repeats_annual_contents_number_column_merge_for_shared_targets(self) -> None:
        np = detect_page_layout.np

        image = np.full((1400, 1000, 3), 255, dtype=np.uint8)
        mask = np.zeros((1400, 1000), dtype=np.uint8)
        edges = mask.copy()
        ann = detect_page_layout.train_bootstrap_ann()
        text_box = detect_page_layout.Box(80, 220, 390, 740)
        first_numbers = detect_page_layout.Box(470, 220, 64, 740)
        second_numbers = detect_page_layout.Box(536, 300, 50, 500)
        text_features = {"max_text_score": 0.82, "saturation_p80": 0.0}
        numbers_features = {
            "max_text_score": 0.92,
            "saturation_p80": 0.0,
            "hline_density": 0.0,
            "vline_density": 0.0,
        }
        classified = [
            (
                detect_page_layout.Block("008_text", "text", "horizontal", 0.87, text_box.to_list(), None, text_features),
                text_box,
            ),
            (
                detect_page_layout.Block("009_text", "text", "vertical", 0.85, first_numbers.to_list(), None, numbers_features),
                first_numbers,
            ),
            (
                detect_page_layout.Block("010_text", "text", "vertical", 0.85, second_numbers.to_list(), None, numbers_features),
                second_numbers,
            ),
        ]

        merged = detect_page_layout.merge_contents_number_columns(
            classified,
            image,
            mask,
            edges,
            ann,
            scale=1.0,
            width=1000,
            height=1400,
        )

        self.assertEqual(len(merged), 1)
        block, box = merged[0]
        self.assertEqual(block.label, "text")
        self.assertEqual(box.to_list(), [80, 220, 506, 740])
        self.assertEqual(block.features["contents_number_column_merge"], 1.0)

    def test_number_column_merge_prefers_nearest_printed_column(self) -> None:
        np = detect_page_layout.np

        image = np.full((1400, 1000, 3), 255, dtype=np.uint8)
        mask = np.zeros((1400, 1000), dtype=np.uint8)
        edges = mask.copy()
        ann = detect_page_layout.train_bootstrap_ann()
        left_box = detect_page_layout.Box(80, 220, 390, 740)
        numbers_box = detect_page_layout.Box(470, 220, 64, 740)
        right_box = detect_page_layout.Box(540, 220, 390, 740)
        text_features = {"max_text_score": 0.82, "saturation_p80": 0.0}
        numbers_features = {
            "max_text_score": 0.92,
            "saturation_p80": 0.0,
            "hline_density": 0.0,
            "vline_density": 0.0,
        }
        classified = [
            (
                detect_page_layout.Block("008_text", "text", "horizontal", 0.87, left_box.to_list(), None, text_features),
                left_box,
            ),
            (
                detect_page_layout.Block("009_text", "text", "vertical", 0.85, numbers_box.to_list(), None, numbers_features),
                numbers_box,
            ),
            (
                detect_page_layout.Block("010_text", "text", "horizontal", 0.87, right_box.to_list(), None, text_features),
                right_box,
            ),
        ]

        merged = detect_page_layout.merge_contents_number_columns(
            classified,
            image,
            mask,
            edges,
            ann,
            scale=1.0,
            width=1000,
            height=1400,
        )

        merged_boxes = {block.ident: box.to_list() for block, box in merged}
        self.assertEqual(len(merged), 2)
        self.assertIn("008_text", merged_boxes)
        self.assertIn("010_text", merged_boxes)
        self.assertEqual(merged_boxes["008_text"], [80, 220, 454, 740])
        self.assertEqual(merged_boxes["010_text"], right_box.to_list())

    def test_splits_annual_contents_heading_at_whitespace_corridor(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        image = np.full((1000, 1000, 3), 255, dtype=np.uint8)
        mask = np.zeros((1000, 1000), dtype=np.uint8)
        cv2.rectangle(mask, (180, 120), (820, 150), 255, -1)
        cv2.rectangle(mask, (80, 190), (910, 205), 255, -1)
        cv2.rectangle(mask, (80, 215), (620, 230), 255, -1)
        for row in range(8):
            y = 310 + row * 45
            cv2.rectangle(mask, (60, y), (420, y + 14), 255, -1)
            cv2.rectangle(mask, (555, y), (930, y + 14), 255, -1)
        edges = mask.copy()
        ann = detect_page_layout.train_bootstrap_ann()
        box = detect_page_layout.Box(40, 100, 920, 620)
        block = detect_page_layout.Block(
            ident="002_text",
            label="text",
            orientation="unknown",
            confidence=0.89,
            bbox=box.to_list(),
            outline=None,
            features={
                "contents_row_merge": 1.0,
                "max_text_score": 0.74,
                "line_art_score": 0.10,
                "saturation_p80": 0.0,
            },
        )

        split = detect_page_layout.split_annual_contents_heading_blocks(
            [(block, box)],
            image,
            mask,
            edges,
            ann,
            scale=1.0,
            width=1000,
            height=1000,
        )

        self.assertEqual([item[0].label for item in split], ["heading", "text"])
        self.assertLess(split[0][1].y2, 310)
        self.assertGreater(split[1][1].y, split[0][1].y2)
        self.assertGreaterEqual(split[1][1].y, 250)
        self.assertEqual(split[0][0].features["annual_contents_heading_split"], 1.0)

    def test_suppresses_small_text_artifact_touching_pcb(self) -> None:
        pcb = detect_page_layout.Block(
            ident="004_pcb",
            label="pcb",
            orientation="unknown",
            confidence=0.83,
            bbox=[250, 90, 1080, 1740],
            outline=None,
            features={},
        )
        artifact = detect_page_layout.Block(
            ident="005_text",
            label="text",
            orientation="horizontal",
            confidence=0.77,
            bbox=[1340, 860, 220, 35],
            outline=None,
            features={},
        )
        prose = detect_page_layout.Block(
            ident="006_text",
            label="text",
            orientation="horizontal",
            confidence=0.93,
            bbox=[1595, 860, 740, 700],
            outline=None,
            features={},
        )

        filtered = detect_page_layout.suppress_small_text_artifacts_near_visuals([pcb, artifact, prose])

        self.assertEqual([block.ident for block in filtered], ["004_pcb", "006_text"])

    def test_suppresses_colored_margin_visual_artifact(self) -> None:
        margin_artifact = detect_page_layout.Block(
            ident="017_schematic",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.38,
            bbox=[0, 2759, 174, 579],
            outline=None,
            features={
                "saturation_p80": 0.38,
                "line_art_score": 1.0,
            },
        )
        real_schematic = detect_page_layout.Block(
            ident="012_schematic",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.89,
            bbox=[161, 2038, 745, 239],
            outline=None,
            features={
                "saturation_p80": 0.0,
                "line_art_score": 0.39,
            },
        )

        filtered = detect_page_layout.suppress_page_margin_visual_artifacts(
            [margin_artifact, real_schematic],
            page_width=2500,
            page_height=3339,
        )

        self.assertEqual([block.ident for block in filtered], ["012_schematic"])

    def test_suppresses_annual_contents_footer_text_artifacts(self) -> None:
        footer_page_text = detect_page_layout.Block(
            ident="022_text",
            label="text",
            orientation="horizontal",
            confidence=0.91,
            bbox=[125, 2897, 379, 59],
            outline=None,
            features={"max_text_score": 0.92, "saturation_p80": 0.0},
        )
        footer_page_number = detect_page_layout.Block(
            ident="021_text",
            label="text",
            orientation="vertical",
            confidence=0.71,
            bbox=[2178, 2881, 103, 73],
            outline=None,
            features={"max_text_score": 0.62, "saturation_p80": 0.0},
        )
        real_contents_row = detect_page_layout.Block(
            ident="012_text",
            label="text",
            orientation="horizontal",
            confidence=0.92,
            bbox=[1236, 2746, 817, 191],
            outline=None,
            features={"max_text_score": 0.88, "saturation_p80": 0.0},
        )

        filtered = detect_page_layout.suppress_annual_contents_footer_artifacts(
            [footer_page_text, footer_page_number, real_contents_row],
            page_width=2500,
            page_height=3200,
        )

        self.assertEqual([block.ident for block in filtered], ["012_text"])

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

    def test_resolve_block_overlaps_cuts_overlap_from_visual_loser(self) -> None:
        schematic = detect_page_layout.Block(
            ident="001_schematic",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.90,
            bbox=[10, 10, 120, 90],
            outline=[[[10, 10], [130, 10], [130, 100], [10, 100]]],
            features={},
        )
        text = detect_page_layout.Block(
            ident="002_text",
            label="text",
            orientation="horizontal",
            confidence=0.91,
            bbox=[90, 35, 90, 42],
            outline=None,
            features={},
        )

        resolved = detect_page_layout.resolve_block_overlaps(
            [schematic, text],
            owner_fn=lambda first, second, overlap: text.ident,
        )

        self.assertFalse(detect_page_layout.point_inside_block(resolved[0], (100, 50)))
        self.assertTrue(detect_page_layout.point_inside_block(resolved[1], (100, 50)))
        self.assertEqual(resolved[0].features["overlap_resolution"], 1.0)

    def test_resolve_block_overlaps_cuts_overlap_from_text_loser(self) -> None:
        schematic = detect_page_layout.Block(
            ident="001_schematic",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.90,
            bbox=[10, 10, 120, 90],
            outline=[[[10, 10], [130, 10], [130, 100], [10, 100]]],
            features={},
        )
        text = detect_page_layout.Block(
            ident="002_text",
            label="text",
            orientation="horizontal",
            confidence=0.91,
            bbox=[90, 35, 90, 42],
            outline=None,
            features={},
        )

        resolved = detect_page_layout.resolve_block_overlaps(
            [schematic, text],
            owner_fn=lambda first, second, overlap: schematic.ident,
        )

        self.assertTrue(detect_page_layout.point_inside_block(resolved[0], (100, 50)))
        self.assertFalse(detect_page_layout.point_inside_block(resolved[1], (100, 50)))
        self.assertIsNotNone(resolved[1].outline)
        self.assertEqual(resolved[1].features["overlap_resolution"], 1.0)

    def test_overlap_owner_score_prefers_text_for_textual_overlap(self) -> None:
        text = detect_page_layout.Block(
            ident="001_text",
            label="text",
            orientation="horizontal",
            confidence=0.90,
            bbox=[90, 35, 90, 42],
            outline=None,
            features={},
        )
        schematic = detect_page_layout.Block(
            ident="002_schematic",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.90,
            bbox=[10, 10, 120, 90],
            outline=None,
            features={},
        )
        overlap = detect_page_layout.Box(90, 35, 40, 42)
        features = {
            "max_text_score": 0.91,
            "textline_density": 0.88,
            "line_art_score": 0.10,
            "hline_density": 0.0,
            "vline_density": 0.0,
            "saturation_p80": 0.0,
            "gray_std": 0.6,
        }

        text_score = detect_page_layout.overlap_owner_score(text, detect_page_layout.box_from_list(text.bbox), overlap, "text", features)
        schematic_score = detect_page_layout.overlap_owner_score(
            schematic,
            detect_page_layout.box_from_list(schematic.bbox),
            overlap,
            "text",
            features,
        )

        self.assertGreater(text_score, schematic_score)

    def test_overlap_owner_score_prefers_stacked_diagram_for_line_art_overlap(self) -> None:
        text = detect_page_layout.Block(
            ident="017_text",
            label="text",
            orientation="horizontal",
            confidence=0.87,
            bbox=[812, 2390, 770, 868],
            outline=None,
            features={},
        )
        diagram = detect_page_layout.Block(
            ident="018_diagram",
            label="diagram",
            orientation="unknown",
            confidence=0.89,
            bbox=[52, 2585, 1050, 666],
            outline=None,
            features={"stacked_diagram_merge": 1.0},
        )
        overlap = detect_page_layout.Box(812, 2585, 290, 666)
        features = {
            "max_text_score": 0.75,
            "textline_density": 0.75,
            "line_art_score": 0.42,
            "hline_density": 0.36,
            "vline_density": 0.0,
            "saturation_p80": 0.0,
            "gray_std": 0.5,
            "component_signature_score": 0.82,
        }

        text_score = detect_page_layout.overlap_owner_score(text, detect_page_layout.box_from_list(text.bbox), overlap, "text", features)
        diagram_score = detect_page_layout.overlap_owner_score(
            diagram,
            detect_page_layout.box_from_list(diagram.bbox),
            overlap,
            "text",
            features,
        )

        self.assertGreater(diagram_score, text_score)

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

    def test_preview_label_anchor_uses_visible_outline_top_edge(self) -> None:
        block = detect_page_layout.Block(
            ident="005_schematic_circuit",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.98,
            bbox=[65, 846, 2264, 2418],
            outline=[[[836, 846], [836, 1589], [65, 1589], [65, 3263], [2328, 3263], [2328, 846]]],
            features={},
        )

        self.assertEqual(detect_page_layout.preview_label_anchor(block, 29, 379, 0.45), (376, 381))

    def test_preview_label_anchor_keeps_rectangle_default(self) -> None:
        block = detect_page_layout.Block(
            ident="002_text",
            label="text",
            orientation="horizontal",
            confidence=0.90,
            bbox=[65, 300, 300, 120],
            outline=None,
            features={},
        )

        self.assertEqual(detect_page_layout.preview_label_anchor(block, 29, 135, 0.45), (29, 135))

    def test_bridges_stacked_text_cutout_gap_at_visual_edge(self) -> None:
        visual = detect_page_layout.Box(152, 108, 2275, 1537)
        upper_text_cutout = detect_page_layout.Box(1659, 1128, 768, 137)
        lower_text_cutout = detect_page_layout.Box(1655, 1329, 772, 316)

        cutouts = detect_page_layout.bridge_aligned_text_cutout_gaps(
            [upper_text_cutout, lower_text_cutout],
            visual,
        )

        self.assertIn(detect_page_layout.Box(1655, 1265, 772, 64), cutouts)

    def test_does_not_bridge_distant_text_cutouts(self) -> None:
        visual = detect_page_layout.Box(152, 108, 2275, 1537)
        upper_text_cutout = detect_page_layout.Box(1659, 1128, 768, 137)
        lower_text_cutout = detect_page_layout.Box(1655, 1510, 772, 120)

        cutouts = detect_page_layout.bridge_aligned_text_cutout_gaps(
            [upper_text_cutout, lower_text_cutout],
            visual,
        )

        self.assertEqual(cutouts, [upper_text_cutout, lower_text_cutout])

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

    def test_vertical_whitespace_corridor_finds_column_gutter(self) -> None:
        np = detect_page_layout.np

        mask = np.zeros((220, 340), dtype=np.uint8)
        for row in range(20, 195, 17):
            mask[row : row + 8, 20:140] = 255
            mask[row : row + 8, 180:320] = 255
        mask[55, 158] = 255
        mask[141, 164] = 255
        box = detect_page_layout.Box(20, 20, 300, 180)

        corridors = detect_page_layout.vertical_whitespace_corridor_runs(mask, box, min_gap=12)
        pieces = detect_page_layout.split_box_by_vertical_gaps(mask, box, 340, 220)

        self.assertTrue(any(118 <= start <= 124 and 155 <= end <= 162 for start, end, _ in corridors))
        self.assertEqual(len(pieces), 2)
        self.assertLessEqual(pieces[0].x2, 180)
        self.assertGreaterEqual(pieces[1].x, 150)

    def test_split_box_by_horizontal_gap_separates_stacked_mixed_regions(self) -> None:
        np = detect_page_layout.np

        mask = np.zeros((520, 320), dtype=np.uint8)
        mask[30:190, 30:270] = 255
        mask[265:500, 30:270] = 255
        box = detect_page_layout.Box(20, 20, 270, 490)

        pieces = detect_page_layout.split_box_by_horizontal_gaps(mask, box, 320, 520)

        self.assertEqual(len(pieces), 2)
        self.assertLess(pieces[0].h, box.h)
        self.assertGreaterEqual(pieces[1].y, 210)

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

    def test_merges_overlapping_schematic_fragments(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        page = np.full((340, 520, 3), 255, dtype=np.uint8)
        left_fragment = detect_page_layout.Box(70, 70, 330, 120)
        right_fragment = detect_page_layout.Box(250, 88, 210, 130)
        cv2.rectangle(page, (left_fragment.x, left_fragment.y), (left_fragment.x2, left_fragment.y2), (0, 0, 0), 2)
        cv2.rectangle(page, (right_fragment.x, right_fragment.y), (right_fragment.x2, right_fragment.y2), (0, 0, 0), 2)

        gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
        mask, _, _ = detect_page_layout.foreground_mask(gray)
        edges = detect_page_layout.canny_edges(gray)
        ann = detect_page_layout.train_bootstrap_ann()
        first = detect_page_layout.Block(
            ident="012_schematic_circuit",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.90,
            bbox=left_fragment.to_list(),
            outline=None,
            features={},
        )
        second = detect_page_layout.Block(
            ident="015_schematic_circuit",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.71,
            bbox=right_fragment.to_list(),
            outline=None,
            features={},
        )

        merged = detect_page_layout.merge_connected_schematic_blocks(
            [(first, left_fragment), (second, right_fragment)], page, mask, edges, ann, scale=1.0, width=520, height=340
        )

        self.assertEqual(len(merged), 1)
        block, box = merged[0]
        self.assertEqual(block.ident, "012_schematic_circuit")
        self.assertEqual(block.label, "schematic/circuit")
        self.assertEqual(box.to_list(), detect_page_layout.union_box(left_fragment, right_fragment).to_list())
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

    def test_merges_technical_text_strip_into_compact_schematic(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        page = np.full((900, 620, 3), 255, dtype=np.uint8)
        strip = detect_page_layout.Box(70, 92, 300, 34)
        schematic = detect_page_layout.Box(70, 126, 300, 92)
        cv2.line(page, (strip.x + 20, strip.y + 18), (strip.x2 - 20, strip.y + 18), (0, 0, 0), 2)
        cv2.putText(page, "C1 0.01 uF", (strip.x + 150, strip.y + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)
        cv2.rectangle(page, (schematic.x + 120, schematic.y + 10), (schematic.x + 130, schematic.y + 80), (0, 0, 0), 2)
        cv2.line(page, (schematic.x + 40, schematic.y + 42), (schematic.x2 - 40, schematic.y + 42), (0, 0, 0), 2)

        gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
        mask, _, _ = detect_page_layout.foreground_mask(gray)
        edges = detect_page_layout.canny_edges(gray)
        ann = detect_page_layout.train_bootstrap_ann()
        strip_block = detect_page_layout.Block(
            ident="014_text",
            label="text",
            orientation="horizontal",
            confidence=0.78,
            bbox=strip.to_list(),
            outline=None,
            features={
                "line_art_score": 0.31,
                "edge_density": 0.20,
                "ink_density": 0.28,
                "saturation_p80": 0.0,
                "component_signature_score": 0.82,
            },
        )
        schematic_block = detect_page_layout.Block(
            ident="015_schematic_circuit",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.71,
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
            width=620,
            height=900,
        )

        self.assertEqual(len(merged), 1)
        block, box = merged[0]
        self.assertEqual(block.ident, "015_schematic_circuit")
        self.assertEqual(block.label, "schematic/circuit")
        self.assertEqual(box.to_list(), detect_page_layout.union_box(strip, schematic).to_list())
        self.assertEqual(block.features["line_art_attachment_merge"], 1.0)

    def test_does_not_merge_technical_text_strip_by_side_touch(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        page = np.full((900, 620, 3), 255, dtype=np.uint8)
        side_strip = detect_page_layout.Box(10, 100, 48, 360)
        text_strip = detect_page_layout.Box(55, 260, 420, 40)
        cv2.rectangle(page, (side_strip.x, side_strip.y), (side_strip.x2, side_strip.y2), (0, 0, 0), 2)
        cv2.line(page, (text_strip.x, text_strip.y + 20), (text_strip.x2, text_strip.y + 20), (0, 0, 0), 2)

        gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
        mask, _, _ = detect_page_layout.foreground_mask(gray)
        edges = detect_page_layout.canny_edges(gray)
        ann = detect_page_layout.train_bootstrap_ann()
        side_block = detect_page_layout.Block(
            ident="017_schematic_circuit",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.95,
            bbox=side_strip.to_list(),
            outline=None,
            features={},
        )
        text_block = detect_page_layout.Block(
            ident="018_text",
            label="text",
            orientation="horizontal",
            confidence=0.75,
            bbox=text_strip.to_list(),
            outline=None,
            features={
                "line_art_score": 0.31,
                "edge_density": 0.20,
                "ink_density": 0.28,
                "saturation_p80": 0.0,
                "component_signature_score": 0.82,
            },
        )

        merged = detect_page_layout.merge_line_art_attachments_into_schematics(
            [(side_block, side_strip), (text_block, text_strip)],
            page,
            mask,
            edges,
            ann,
            scale=1.0,
            width=620,
            height=900,
        )

        self.assertEqual(len(merged), 2)
        self.assertEqual([block.ident for block, _ in merged], ["017_schematic_circuit", "018_text"])

    def test_does_not_merge_technical_text_strip_into_large_schematic(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        page = np.full((900, 620, 3), 255, dtype=np.uint8)
        schematic = detect_page_layout.Box(20, 40, 560, 360)
        text_strip = detect_page_layout.Box(30, 405, 520, 40)
        cv2.rectangle(page, (schematic.x, schematic.y), (schematic.x2, schematic.y2), (0, 0, 0), 2)
        cv2.line(page, (text_strip.x, text_strip.y + 20), (text_strip.x2, text_strip.y + 20), (0, 0, 0), 2)

        gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
        mask, _, _ = detect_page_layout.foreground_mask(gray)
        edges = detect_page_layout.canny_edges(gray)
        ann = detect_page_layout.train_bootstrap_ann()
        schematic_block = detect_page_layout.Block(
            ident="001_schematic_circuit",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.95,
            bbox=schematic.to_list(),
            outline=None,
            features={},
        )
        text_block = detect_page_layout.Block(
            ident="020_text",
            label="text",
            orientation="horizontal",
            confidence=0.78,
            bbox=text_strip.to_list(),
            outline=None,
            features={
                "line_art_score": 0.31,
                "edge_density": 0.20,
                "ink_density": 0.28,
                "saturation_p80": 0.0,
                "component_signature_score": 0.82,
            },
        )

        merged = detect_page_layout.merge_line_art_attachments_into_schematics(
            [(schematic_block, schematic), (text_block, text_strip)],
            page,
            mask,
            edges,
            ann,
            scale=1.0,
            width=620,
            height=900,
        )

        self.assertEqual(len(merged), 2)
        self.assertEqual([block.ident for block, _ in merged], ["001_schematic_circuit", "020_text"])

    def test_merges_tall_frame_strip_into_schematic(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        page = np.full((900, 620, 3), 255, dtype=np.uint8)
        schematic = detect_page_layout.Box(60, 250, 430, 260)
        frame_strip = detect_page_layout.Box(490, 250, 40, 260)
        cv2.rectangle(page, (schematic.x, schematic.y), (schematic.x2, schematic.y2), (0, 0, 0), 2)
        cv2.line(page, (frame_strip.x + 20, frame_strip.y), (frame_strip.x + 20, frame_strip.y2), (0, 0, 0), 2)
        cv2.line(page, (frame_strip.x, frame_strip.y), (frame_strip.x2, frame_strip.y), (0, 0, 0), 2)
        cv2.line(page, (frame_strip.x, frame_strip.y2), (frame_strip.x2, frame_strip.y2), (0, 0, 0), 2)

        gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
        mask, _, _ = detect_page_layout.foreground_mask(gray)
        edges = detect_page_layout.canny_edges(gray)
        ann = detect_page_layout.train_bootstrap_ann()
        schematic_block = detect_page_layout.Block(
            ident="005_schematic_circuit",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.78,
            bbox=schematic.to_list(),
            outline=None,
            features={},
        )
        strip_block = detect_page_layout.Block(
            ident="006_diagram",
            label="diagram",
            orientation="unknown",
            confidence=0.29,
            bbox=frame_strip.to_list(),
            outline=None,
            features={
                "line_art_score": 0.24,
                "edge_density": 0.12,
                "ink_density": 0.04,
                "saturation_p80": 0.0,
            },
        )

        merged = detect_page_layout.merge_line_art_attachments_into_schematics(
            [(schematic_block, schematic), (strip_block, frame_strip)],
            page,
            mask,
            edges,
            ann,
            scale=1.0,
            width=620,
            height=900,
        )

        self.assertEqual(len(merged), 1)
        block, box = merged[0]
        self.assertEqual(block.ident, "005_schematic_circuit")
        self.assertEqual(block.label, "schematic/circuit")
        self.assertEqual(box.to_list(), [60, 250, 470, 260])
        self.assertEqual(block.features["line_art_attachment_merge"], 1.0)

    def test_merges_labeled_line_art_fragments_into_image(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        page = np.full((900, 620, 3), 255, dtype=np.uint8)
        drawing = detect_page_layout.Box(80, 70, 360, 260)
        side_piece = detect_page_layout.Box(440, 70, 90, 260)
        caption_band = detect_page_layout.Box(90, 260, 420, 82)
        cv2.line(page, (drawing.x + 20, drawing.y + 220), (drawing.x + 280, drawing.y + 20), (0, 0, 0), 2)
        cv2.line(page, (drawing.x + 80, drawing.y + 10), (drawing.x + 300, drawing.y + 180), (0, 0, 0), 2)
        cv2.line(page, (side_piece.x + 6, side_piece.y + 130), (side_piece.x2 - 8, side_piece.y + 130), (0, 0, 0), 2)
        cv2.putText(page, "Fig. 2", (caption_band.x + 4, caption_band.y + 52), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

        gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
        mask, _, _ = detect_page_layout.foreground_mask(gray)
        edges = detect_page_layout.canny_edges(gray)
        ann = detect_page_layout.train_bootstrap_ann()
        classified = [
            (
                detect_page_layout.Block(
                    ident="003_text",
                    label="text",
                    orientation="diagonal",
                    confidence=0.72,
                    bbox=drawing.to_list(),
                    outline=None,
                    features={
                        "line_art_score": 0.24,
                        "edge_density": 0.29,
                        "ink_density": 0.09,
                        "gray_std": 0.52,
                        "max_text_score": 0.66,
                        "component_signature_score": 0.97,
                    },
                ),
                drawing,
            ),
            (
                detect_page_layout.Block(
                    ident="004_other",
                    label="other",
                    orientation="unknown",
                    confidence=0.39,
                    bbox=side_piece.to_list(),
                    outline=None,
                    features={
                        "line_art_score": 0.08,
                        "edge_density": 0.04,
                        "ink_density": 0.01,
                        "gray_std": 0.21,
                        "max_text_score": 0.09,
                        "component_signature_score": 0.0,
                    },
                ),
                side_piece,
            ),
            (
                detect_page_layout.Block(
                    ident="009_text",
                    label="text",
                    orientation="horizontal",
                    confidence=0.73,
                    bbox=caption_band.to_list(),
                    outline=None,
                    features={
                        "line_art_score": 0.29,
                        "edge_density": 0.17,
                        "ink_density": 0.06,
                        "gray_std": 0.43,
                        "max_text_score": 0.64,
                        "component_signature_score": 1.0,
                    },
                ),
                caption_band,
            ),
        ]

        merged = detect_page_layout.merge_illustration_fragments_into_images(
            classified,
            page,
            mask,
            edges,
            ann,
            scale=1.0,
            width=620,
            height=900,
        )

        self.assertEqual(len(merged), 1)
        block, box = merged[0]
        self.assertEqual(block.ident, "003_image")
        self.assertEqual(block.label, "image")
        self.assertEqual(box.to_list(), [80, 70, 450, 272])
        self.assertEqual(block.features["illustration_fragment_merge"], 1.0)

    def test_does_not_merge_below_prose_into_illustration_image(self) -> None:
        cv2 = detect_page_layout.cv2
        np = detect_page_layout.np

        page = np.full((900, 620, 3), 255, dtype=np.uint8)
        drawing = detect_page_layout.Box(80, 70, 360, 260)
        caption_band = detect_page_layout.Box(90, 260, 420, 82)
        prose = detect_page_layout.Box(90, 390, 420, 260)
        cv2.line(page, (drawing.x + 20, drawing.y + 220), (drawing.x + 280, drawing.y + 20), (0, 0, 0), 2)
        cv2.putText(page, "Fig. 2", (caption_band.x + 4, caption_band.y + 52), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        for row in range(10):
            y = prose.y + 18 + row * 22
            cv2.line(page, (prose.x + 12, y), (prose.x2 - 12, y), (0, 0, 0), 2)

        gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
        mask, _, _ = detect_page_layout.foreground_mask(gray)
        edges = detect_page_layout.canny_edges(gray)
        ann = detect_page_layout.train_bootstrap_ann()
        classified = [
            (
                detect_page_layout.Block(
                    ident="003_text",
                    label="text",
                    orientation="diagonal",
                    confidence=0.72,
                    bbox=drawing.to_list(),
                    outline=None,
                    features={
                        "line_art_score": 0.24,
                        "edge_density": 0.29,
                        "ink_density": 0.09,
                        "gray_std": 0.52,
                        "max_text_score": 0.66,
                        "component_signature_score": 0.97,
                    },
                ),
                drawing,
            ),
            (
                detect_page_layout.Block(
                    ident="009_text",
                    label="text",
                    orientation="horizontal",
                    confidence=0.73,
                    bbox=caption_band.to_list(),
                    outline=None,
                    features={
                        "line_art_score": 0.29,
                        "edge_density": 0.17,
                        "ink_density": 0.06,
                        "gray_std": 0.43,
                        "max_text_score": 0.64,
                        "component_signature_score": 1.0,
                    },
                ),
                caption_band,
            ),
            (
                detect_page_layout.Block(
                    ident="012_text",
                    label="text",
                    orientation="horizontal",
                    confidence=0.91,
                    bbox=prose.to_list(),
                    outline=None,
                    features={
                        "line_art_score": 0.10,
                        "edge_density": 0.12,
                        "ink_density": 0.27,
                        "gray_std": 0.80,
                        "max_text_score": 0.87,
                        "component_signature_score": 0.08,
                    },
                ),
                prose,
            ),
        ]

        merged = detect_page_layout.merge_illustration_fragments_into_images(
            classified,
            page,
            mask,
            edges,
            ann,
            scale=1.0,
            width=620,
            height=900,
        )

        self.assertEqual([block.ident for block, _ in merged], ["003_image", "012_text"])
        self.assertEqual(merged[0][1].to_list(), [80, 70, 430, 272])

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

    def test_demotes_stacked_bold_heading_wrapper_to_heading(self) -> None:
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

        self.assertEqual(demoted[0][0].label, "heading")
        self.assertEqual(demoted[0][0].orientation, "horizontal")
        self.assertEqual(demoted[0][0].ident, "001_heading")
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

    def test_stacked_diagram_seed_accepts_single_axis_waveform_strip(self) -> None:
        block = detect_page_layout.Block(
            ident="018_text",
            label="text",
            orientation="horizontal",
            confidence=0.69,
            bbox=[20, 200, 500, 70],
            outline=None,
            features={
                "saturation_p80": 0.0,
                "hline_density": 0.0,
                "vline_density": 0.32,
                "line_art_score": 0.45,
                "edge_density": 0.30,
            },
        )

        self.assertTrue(detect_page_layout.stacked_diagram_seed(block, detect_page_layout.Box(20, 200, 500, 70), 900, 1000))

    def test_schematic_side_caption_panel_can_merge_with_large_schematic(self) -> None:
        panel = detect_page_layout.Block(
            ident="008_image",
            label="image",
            orientation="unknown",
            confidence=0.21,
            bbox=[178, 1413, 208, 1396],
            outline=None,
            features={
                "ink_density": 0.01566,
                "edge_density": 0.04184,
                "saturation_p80": 0.0,
                "line_art_score": 0.05004,
            },
        )

        self.assertTrue(
            detect_page_layout.schematic_side_caption_panel_candidate(
                panel,
                detect_page_layout.Box(178, 1413, 208, 1396),
                detect_page_layout.Box(385, 1413, 1222, 1396),
                width=2500,
                height=3200,
            )
        )

    def test_illustration_fragment_rejects_waveform_diagram(self) -> None:
        block = detect_page_layout.Block(
            ident="005_diagram",
            label="diagram",
            orientation="unknown",
            confidence=0.97,
            bbox=[181, 485, 724, 400],
            outline=None,
            features={
                "area_ratio": 0.03622,
                "height_ratio": 0.12500,
                "ink_density": 0.09171,
                "edge_density": 0.23686,
                "saturation_p80": 0.0,
                "hline_density": 0.42569,
                "vline_density": 0.03686,
                "line_art_score": 0.48157,
                "max_text_score": 1.0,
            },
        )

        self.assertFalse(
            detect_page_layout.illustration_fragment_candidate(
                block,
                detect_page_layout.Box(181, 485, 724, 400),
                width=2500,
                height=3200,
            )
        )

    def test_illustration_fragment_rejects_confident_prose_with_false_component_signature(self) -> None:
        block = detect_page_layout.Block(
            ident="017_text",
            label="text",
            orientation="horizontal",
            confidence=0.87,
            bbox=[420, 1200, 420, 250],
            outline=None,
            features={
                "ink_density": 0.12,
                "gray_std": 0.42,
                "saturation_p80": 0.0,
                "max_text_score": 0.86,
                "line_art_score": 0.22,
                "hline_density": 0.06,
                "vline_density": 0.0,
                "edge_density": 0.20,
                "component_signature_score": 1.0,
            },
        )

        self.assertFalse(
            detect_page_layout.illustration_fragment_candidate(block, detect_page_layout.Box(420, 1200, 420, 250), 900, 1600)
        )

    def test_suppresses_weak_visual_wrapper_inside_stronger_visual(self) -> None:
        wrapper = detect_page_layout.Block(
            ident="001_diagram",
            label="diagram",
            orientation="unknown",
            confidence=0.39,
            bbox=[500, 20, 300, 420],
            outline=None,
            features={},
        )
        schematic = detect_page_layout.Block(
            ident="005_schematic",
            label="schematic/circuit",
            orientation="unknown",
            confidence=0.94,
            bbox=[20, 0, 900, 520],
            outline=None,
            features={},
        )

        filtered = detect_page_layout.suppress_weak_visual_wrappers(
            [
                (wrapper, detect_page_layout.Box(500, 20, 300, 420)),
                (schematic, detect_page_layout.Box(20, 0, 900, 520)),
            ]
        )

        self.assertEqual([item[0].ident for item in filtered], ["005_schematic"])

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

    def test_suppresses_tiny_text_fragment_by_configured_glyph_width(self) -> None:
        tiny = detect_page_layout.Block(
            ident="001_text",
            label="text",
            orientation="horizontal",
            confidence=0.72,
            bbox=[10, 10, 18, 20],
            outline=None,
            features={},
        )
        normal = detect_page_layout.Block(
            ident="002_text",
            label="text",
            orientation="horizontal",
            confidence=0.90,
            bbox=[45, 10, 120, 20],
            outline=None,
            features={},
        )
        heading = detect_page_layout.Block(
            ident="003_heading",
            label="heading",
            orientation="horizontal",
            confidence=0.91,
            bbox=[10, 45, 18, 20],
            outline=None,
            features={},
        )

        filtered = detect_page_layout.suppress_tiny_text_fragments([tiny, normal, heading])

        self.assertEqual([block.ident for block in filtered], ["002_text", "003_heading"])

    def test_keeps_dense_multiline_contents_text_when_suppressing_tiny_fragments(self) -> None:
        contents_block = detect_page_layout.Block(
            ident="002_text",
            label="text",
            orientation="horizontal",
            confidence=0.94,
            bbox=[192, 276, 2163, 2583],
            outline=None,
            features={
                "max_text_score": 0.29752,
                "textline_density": 0.29752,
                "ink_density": 0.17495,
                "hline_density": 0.0,
                "vline_density": 0.0,
                "line_balance": 0.0,
                "saturation_p80": 0.0,
            },
        )
        tiny = detect_page_layout.Block(
            ident="003_text",
            label="text",
            orientation="horizontal",
            confidence=0.72,
            bbox=[10, 10, 18, 20],
            outline=None,
            features={},
        )

        filtered = detect_page_layout.suppress_tiny_text_fragments([contents_block, tiny])

        self.assertEqual([block.ident for block in filtered], ["002_text"])

    def test_suppresses_short_text_fragment_inside_visual_block(self) -> None:
        visual = detect_page_layout.Block(
            ident="010_image",
            label="image",
            orientation="unknown",
            confidence=0.82,
            bbox=[100, 100, 240, 140],
            outline=None,
            features={},
        )
        inner_label = detect_page_layout.Block(
            ident="011_text",
            label="text",
            orientation="horizontal",
            confidence=0.75,
            bbox=[130, 145, 62, 18],
            outline=None,
            features={},
        )
        outside_text = detect_page_layout.Block(
            ident="012_text",
            label="text",
            orientation="horizontal",
            confidence=0.90,
            bbox=[100, 265, 220, 42],
            outline=None,
            features={},
        )

        filtered = detect_page_layout.suppress_tiny_text_fragments([visual, inner_label, outside_text])

        self.assertEqual([block.ident for block in filtered], ["010_image", "012_text"])

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

    def test_feature_classifier_recognizes_annual_contents_list_as_text(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.41963,
            "height_ratio": 0.18222,
            "area_ratio": 0.07647,
            "wide_aspect": 0.69684,
            "tall_aspect": 0.07997,
            "ink_density": 0.15170,
            "edge_density": 0.52766,
            "gray_std": 0.70861,
            "gray_levels": 1.0,
            "component_density": 1.0,
            "hline_density": 0.0,
            "vline_density": 0.0,
            "line_balance": 0.0,
            "textline_density": 0.93293,
            "horizontal_text_score": 0.93293,
            "vertical_text_score": 0.15254,
            "diagonal_text_score": 0.30508,
            "max_text_score": 0.93293,
            "line_art_score": 0.35382,
            "saturation_p80": 0.0,
            "component_signature_score": 1.0,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "text")
        self.assertGreater(confidence, 0.60)

    def test_feature_classifier_keeps_lower_annual_contents_group_as_text(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.41952,
            "height_ratio": 0.24,
            "area_ratio": 0.10068,
            "wide_aspect": 0.27269,
            "tall_aspect": 0.14669,
            "ink_density": 0.07278,
            "edge_density": 0.31277,
            "gray_std": 0.47910,
            "gray_levels": 1.0,
            "component_density": 1.0,
            "hline_density": 0.0,
            "vline_density": 0.0,
            "line_art_score": 0.07301,
            "line_balance": 0.0,
            "saturation_mean": 0.00972,
            "saturation_p80": 0.0,
            "textline_density": 0.70833,
            "horizontal_text_score": 0.70833,
            "vertical_text_score": 0.64177,
            "diagonal_text_score": 0.69903,
            "max_text_score": 0.70833,
            "component_signature_score": 1.0,
            "pcb_trace_density": 0.00458,
            "pcb_pad_density": 1.0,
            "pcb_board_outline_score": 0.0,
            "pcb_signature_score": 0.26330,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "text")
        self.assertGreater(confidence, 0.55)

    def test_annual_contents_text_is_not_merged_as_illustration(self) -> None:
        block = detect_page_layout.Block(
            ident="012_text",
            label="text",
            orientation="horizontal",
            confidence=0.95,
            bbox=[1234, 2057, 1059, 794],
            outline=None,
            features={
                "width_ratio": 0.4236,
                "height_ratio": 0.2481,
                "area_ratio": 0.1051,
                "max_text_score": 0.92825,
                "textline_density": 0.92825,
                "component_density": 1.0,
                "hline_density": 0.0,
                "vline_density": 0.0,
                "line_balance": 0.0,
                "line_art_score": 0.09774,
                "edge_density": 0.38,
                "ink_density": 0.10,
                "gray_std": 0.56,
                "saturation_p80": 0.0,
                "component_signature_score": 1.0,
            },
        )

        self.assertFalse(
            detect_page_layout.illustration_fragment_candidate(
                block,
                detect_page_layout.Box(1234, 2057, 1059, 794),
                width=2500,
                height=3200,
            )
        )

    def test_feature_classifier_recognizes_wide_rule_heading(self) -> None:
        ann = detect_page_layout.train_bootstrap_ann()
        features = {
            "width_ratio": 0.86192,
            "height_ratio": 0.02278,
            "area_ratio": 0.01963,
            "wide_aspect": 1.0,
            "tall_aspect": 0.006,
            "ink_density": 0.10604,
            "edge_density": 0.29429,
            "gray_std": 0.44959,
            "gray_levels": 0.65625,
            "component_density": 0.62436,
            "hline_density": 0.28658,
            "vline_density": 0.27752,
            "line_balance": 0.96837,
            "textline_density": 0.43902,
            "horizontal_text_score": 0.43902,
            "vertical_text_score": 0.47564,
            "diagonal_text_score": 0.0,
            "max_text_score": 0.47564,
            "line_art_score": 0.48990,
            "saturation_p80": 0.01961,
            "component_signature_score": 1.0,
        }

        label, confidence = detect_page_layout.classify_features(ann, features)

        self.assertEqual(label, "heading")
        self.assertGreater(confidence, 0.35)


if __name__ == "__main__":
    unittest.main()
