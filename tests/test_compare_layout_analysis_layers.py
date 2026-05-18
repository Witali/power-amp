import unittest

from scripts import compare_layout_analysis_layers
from scripts import layout_analysis_thresholds


class CompareLayoutAnalysisLayersTests(unittest.TestCase):
    def test_histogram_only_label_uses_shared_thresholds_for_text(self) -> None:
        features = {
            "ink_density": layout_analysis_thresholds.HISTOGRAM_TEXT_MIN_INK + 0.02,
            "gray_std": 0.62,
            "luma_dark_light_ratio": layout_analysis_thresholds.HISTOGRAM_SCHEMATIC_MAX_DARK_LIGHT_RATIO + 0.04,
            "luma_dark_fraction": 0.06,
            "luma_light_fraction": layout_analysis_thresholds.HISTOGRAM_SCHEMATIC_MIN_LIGHT - 0.03,
            "luma_mid_fraction": layout_analysis_thresholds.HISTOGRAM_TEXT_MAX_MID - 0.03,
            "luma_hist_entropy": layout_analysis_thresholds.HISTOGRAM_TEXT_MIN_ENTROPY + 0.10,
            "luma_bimodal_score": 0.02,
            "saturation_high_fraction": 0.0,
            "color_pixel_fraction": 0.0,
        }

        label = compare_layout_analysis_layers.histogram_only_label(features)

        self.assertEqual(label, "text")

    def test_histogram_only_label_uses_shared_thresholds_for_schematic(self) -> None:
        features = {
            "ink_density": layout_analysis_thresholds.HISTOGRAM_SCHEMATIC_MIN_INK + 0.03,
            "gray_std": 0.55,
            "luma_dark_light_ratio": layout_analysis_thresholds.HISTOGRAM_SCHEMATIC_MAX_DARK_LIGHT_RATIO * 0.5,
            "luma_dark_fraction": 0.03,
            "luma_light_fraction": layout_analysis_thresholds.HISTOGRAM_SCHEMATIC_MIN_LIGHT + 0.18,
            "luma_mid_fraction": layout_analysis_thresholds.HISTOGRAM_SCHEMATIC_MAX_MID * 0.5,
            "luma_hist_entropy": 0.20,
            "luma_bimodal_score": 0.02,
            "saturation_high_fraction": 0.0,
            "color_pixel_fraction": 0.0,
        }

        label = compare_layout_analysis_layers.histogram_only_label(features)

        self.assertEqual(label, "schematic/circuit")

    def test_balance_only_label_uses_shared_thresholds_for_image(self) -> None:
        features = {
            "ink_density": layout_analysis_thresholds.BALANCE_IMAGE_MIN_INK + 0.05,
            "gray_std": 0.72,
            "luma_dark_light_ratio": layout_analysis_thresholds.BALANCE_IMAGE_MIN_DARK_LIGHT_RATIO + 0.10,
            "luma_mid_fraction": 0.32,
            "luma_light_fraction": 0.34,
        }

        label = compare_layout_analysis_layers.balance_only_label(features)

        self.assertEqual(label, "image")


if __name__ == "__main__":
    unittest.main()
