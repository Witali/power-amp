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
            "luma_dark_fraction": 0.07,
            "luma_light_fraction": 0.76,
            "luma_mid_fraction": 0.17,
            "luma_dark_light_ratio": 0.09,
            "luma_light_dark_ratio": 10.9,
            "luma_bimodal_score": 0.06,
            "luma_hist_entropy": 0.56,
            "saturation_hist_entropy": 0.0,
            "hue_hist_entropy": 0.0,
            "color_pixel_fraction": 0.0,
            "saturation_high_fraction": 0.0,
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
            "luma_dark_fraction": 0.03,
            "luma_light_fraction": 0.88,
            "luma_mid_fraction": 0.09,
            "luma_dark_light_ratio": 0.034,
            "luma_light_dark_ratio": 29.33,
            "luma_bimodal_score": 0.03,
            "luma_hist_entropy": 0.35,
            "saturation_hist_entropy": 0.0,
            "hue_hist_entropy": 0.0,
            "color_pixel_fraction": 0.0,
            "saturation_high_fraction": 0.0,
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
            "luma_dark_fraction": 0.08,
            "luma_light_fraction": 0.20,
            "luma_mid_fraction": 0.72,
            "luma_dark_light_ratio": 0.40,
            "luma_light_dark_ratio": 2.50,
            "luma_bimodal_score": 0.02,
            "luma_hist_entropy": 0.62,
            "saturation_hist_entropy": 0.45,
            "hue_hist_entropy": 0.16,
            "color_pixel_fraction": 0.70,
            "saturation_high_fraction": 0.55,
        }

        self.assertEqual(layout_frequency.classify_frequency_features(text_features)[0], "text")
        self.assertEqual(layout_frequency.classify_frequency_features(schematic_features)[0], "schematic/circuit")
        self.assertEqual(layout_frequency.classify_frequency_features(image_features)[0], "image")

    def test_tile_features_include_luminance_and_color_histograms(self) -> None:
        cv2 = layout_frequency.cv2
        np = layout_frequency.np

        tile = np.full((32, 32, 3), 245, dtype=np.uint8)
        cv2.rectangle(tile, (4, 8), (27, 15), (0, 0, 0), -1)
        gray = cv2.cvtColor(tile, cv2.COLOR_BGR2GRAY)
        mask, _, _ = layout_frequency.foreground_mask(gray)

        features = layout_frequency.tile_features(tile, gray, mask, 0, 0, 32)

        self.assertIn("luma_hist_00", features)
        self.assertIn("saturation_hist_00", features)
        self.assertIn("hue_hist_00", features)
        self.assertGreater(features["luma_dark_fraction"], 0.10)
        self.assertGreater(features["luma_light_fraction"], 0.50)
        self.assertLess(features["luma_mid_fraction"], 0.30)
        self.assertGreater(features["luma_dark_light_ratio"], 0.10)
        self.assertGreater(features["luma_bimodal_score"], 0.05)

    def test_cluster_tiles_groups_adjacent_similar_regions(self) -> None:
        text_features = {
            "ink_density": 0.22,
            "gray_std": 0.72,
            "saturation_p80": 0.0,
            "saturation_high_fraction": 0.0,
            "color_pixel_fraction": 0.0,
            "luma_dark_light_ratio": 0.09,
            "luma_mid_fraction": 0.17,
            "luma_hist_entropy": 0.56,
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
            "saturation_high_fraction": 0.0,
            "color_pixel_fraction": 0.0,
            "luma_dark_light_ratio": 0.034,
            "luma_mid_fraction": 0.09,
            "luma_hist_entropy": 0.35,
            "row_period_score": 0.56,
            "column_period_score": 0.70,
            "row_entropy": 0.74,
            "column_entropy": 0.76,
            "hline_density": 0.11,
            "vline_density": 0.12,
            "line_balance": 0.40,
        }
        tiles = []
        for column in range(3):
            tiles.append(
                {
                    "grid": [0, column],
                    "bbox": [column * 32, 0, 32, 32],
                    "label": "text",
                    "confidence": 0.82,
                    "features": dict(text_features),
                }
            )
        for row in range(2):
            for column in range(2):
                tiles.append(
                    {
                        "grid": [2 + row, column],
                        "bbox": [column * 32, 64 + row * 32, 32, 32],
                        "label": "schematic/circuit",
                        "confidence": 0.78,
                        "features": dict(schematic_features),
                    }
                )

        clusters = layout_frequency.cluster_tiles_to_hints(tiles, 128, 128)
        labels = {cluster["label"] for cluster in clusters}

        self.assertIn("text", labels)
        self.assertIn("schematic/circuit", labels)
        text_cluster = next(cluster for cluster in clusters if cluster["label"] == "text")
        self.assertEqual(text_cluster["tile_count"], 3)
        self.assertEqual(text_cluster["bbox"], [0, 0, 96, 32])

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
        self.assertIn("cluster_hints", result)
        self.assertTrue(result["cluster_hints"])

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
            saved = (root / "frequency" / "page" / "frequency_layout.json").read_text(encoding="utf-8")
            self.assertIn("cluster_hints", saved)

    def test_default_grid_uses_32_pixel_tiles(self) -> None:
        np = layout_frequency.np

        page = np.full((96, 96, 3), 245, dtype=np.uint8)

        result = layout_frequency.analyze_image(page)

        self.assertEqual(result["tile_size"], 32)
        self.assertEqual(result["stride"], 32)


if __name__ == "__main__":
    unittest.main()
