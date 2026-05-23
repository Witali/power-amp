import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGRESSION_ROOT = PROJECT_ROOT / "study" / "opencv_layout_regression_pages"


class LayoutRegressionPagesTests(unittest.TestCase):
    def test_manifest_has_unique_pages_with_sources_and_baselines(self) -> None:
        manifest_path = REGRESSION_ROOT / "manifest.json"
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        pages = manifest["pages"]

        self.assertEqual(manifest["page_count"], 22)
        self.assertEqual(len(pages), manifest["page_count"])
        self.assertEqual(len({page["id"] for page in pages}), manifest["page_count"])

        for page in pages:
            self.assertTrue((PROJECT_ROOT / page["source"]).exists(), page["source"])
            self.assertTrue((PROJECT_ROOT / page["baseline_layout"]).exists(), page["baseline_layout"])
            self.assertTrue((PROJECT_ROOT / page["baseline_preview"]).exists(), page["baseline_preview"])
            self.assertTrue(page["reason"])


if __name__ == "__main__":
    unittest.main()
