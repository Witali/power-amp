import tempfile
import unittest
from pathlib import Path

from scripts import layout_frequency


@unittest.skipUnless(layout_frequency.OPENCV_AVAILABLE, "OpenCV dependencies are not installed")
class LayoutFrequencyTests(unittest.TestCase):
    def test_band_energy_ratio_detects_periodic_profile(self) -> None:
        np = layout_frequency.np

        values = np.zeros(128, dtype=np.float32)
        values[::12] = 1.0

        ratio = layout_frequency.band_energy_ratio(values, 8.0, 16.0)

        self.assertGreater(ratio, 0.15)

    def test_dominant_period_reports_main_profile_period(self) -> None:
        np = layout_frequency.np

        x = np.arange(192, dtype=np.float32)
        values = np.sin(2.0 * np.pi * x / 24.0).astype(np.float32)

        period = layout_frequency.dominant_period(values, 8.0, 44.0)

        self.assertAlmostEqual(period, 24.0, delta=1.0)

    def test_calibrated_classifier_separates_reviewed_feature_profiles(self) -> None:
        text_features = {
            "ink_density": 0.22,
            "gray_std": 0.72,
            "saturation_p80": 0.0,
            "row_period_score": 0.83,
            "column_period_score": 0.67,
            "row_entropy": 0.42,
            "column_entropy": 0.73,
            "hline_density": 0.0,
            "vline_density": 0.0,
            "line_balance": 0.0,
        }
        schematic_features = {
            "ink_density": 0.13,
            "gray_std": 0.60,
            "saturation_p80": 0.0,
            "row_period_score": 0.56,
            "column_period_score": 0.70,
            "row_entropy": 0.74,
            "column_entropy": 0.76,
            "hline_density": 0.11,
            "vline_density": 0.12,
            "line_balance": 0.40,
        }
        image_features = {
            "ink_density": 0.52,
            "gray_std": 0.75,
            "saturation_p80": 0.38,
            "row_period_score": 0.23,
            "column_period_score": 0.22,
            "row_entropy": 0.43,
            "column_entropy": 0.46,
            "hline_density": 1.0,
            "vline_density": 1.0,
            "line_balance": 0.78,
        }

        self.assertEqual(layout_frequency.classify_frequency_features(text_features)[0], "text")
        self.assertEqual(layout_frequency.classify_frequency_features(schematic_features)[0], "schematic/circuit")
        self.assertEqual(layout_frequency.classify_frequency_features(image_features)[0], "image")

    def test_frequency_analysis_finds_text_and_schematic_hints(self) -> None:
        cv2 = layout_frequency.cv2
        np = layout_frequency.np

        page = np.full((420, 520, 3), 245, dtype=np.uint8)
        for row in range(35, 205, 16):
            for x in (28, 76, 132, 184):
                cv2.rectangle(page, (x, row), (x + 34, row + 7), (0, 0, 0), -1)
            for x in (28, 92, 150):
                cv2.rectangle(page, (x, row + 10), (x + 28, row + 13), (0, 0, 0), -1)

        cv2.rectangle(page, (280, 62), (485, 210), (0, 0, 0), 2)
        cv2.line(page, (300, 140), (465, 140), (0, 0, 0), 2)
        cv2.line(page, (370, 82), (370, 192), (0, 0, 0), 2)
        cv2.circle(page, (370, 140), 34, (0, 0, 0), 2)

        rng = np.random.default_rng(3)
        page[250:385, 285:485] = rng.integers(30, 220, size=(135, 200, 3), dtype=np.uint8)

        result = layout_frequency.analyze_image(page, tile_size=128, stride=64)
        labels = {hint["label"] for hint in result["hints"]}

        self.assertIn("text", labels)
        self.assertTrue(labels & {"schematic/circuit", "table", "diagram"})
        self.assertIn("image", labels)

    def test_validate_layout_blocks_reports_mismatch(self) -> None:
        blocks = [
            {
                "ident": "001_text",
                "label": "text",
                "bbox": [10, 10, 200, 120],
            }
        ]
        hints = [
            {
                "label": "image",
                "confidence": 0.80,
                "bbox": [20, 20, 180, 100],
            }
        ]

        warnings = layout_frequency.validate_layout_blocks(blocks, hints)

        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["block"], "001_text")
        self.assertEqual(warnings[0]["hint_label"], "image")

    def test_frequency_cli_writes_json_and_preview(self) -> None:
        cv2 = layout_frequency.cv2
        np = layout_frequency.np
        from scripts import analyze_page_frequency

        page = np.full((240, 300, 3), 245, dtype=np.uint8)
        for row in range(40, 160, 16):
            for x in (30, 78, 132):
                cv2.rectangle(page, (x, row), (x + 30, row + 8), (0, 0, 0), -1)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_path = root / "page.png"
            layout_frequency.write_image(image_path, page)

            code = analyze_page_frequency.main(
                [
                    "--image",
                    str(image_path),
                    "--out-dir",
                    str(root / "frequency"),
                    "--preview-width",
                    "300",
                ]
            )

            self.assertEqual(code, 0)
            self.assertTrue((root / "frequency" / "page" / "frequency_layout.json").exists())
            self.assertTrue((root / "frequency" / "page" / "frequency_preview.png").exists())


if __name__ == "__main__":
    unittest.main()
