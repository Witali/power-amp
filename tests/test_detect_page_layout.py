import json
import tempfile
import unittest
from pathlib import Path

from scripts import detect_page_layout


@unittest.skipUnless(detect_page_layout.OPENCV_AVAILABLE, "OpenCV dependencies are not installed")
class DetectPageLayoutTests(unittest.TestCase):
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
