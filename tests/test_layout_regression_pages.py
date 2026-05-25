import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGRESSION_ROOT = PROJECT_ROOT / "study" / "opencv_layout_regression_pages"
MANUAL_FEEDBACK_PAGE_IDS = {
    "b.1986-12.047",
    "b.1986-12.048",
    "b.1986-12.049",
    "b.1986-12.051",
    "b.1986-12.054",
    "b.1986-12.055",
    "b.1986-12.057",
    "b.1998-12.018",
    "b.1999-10.017",
    "b.1999-10.018",
    "b.1999-12.064",
}


class LayoutRegressionPagesTests(unittest.TestCase):
    def test_manifest_has_unique_pages_with_sources_and_baselines(self) -> None:
        manifest_path = REGRESSION_ROOT / "manifest.json"
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        pages = manifest["pages"]

        page_ids = {page["id"] for page in pages}

        self.assertEqual(len(pages), manifest["page_count"])
        self.assertEqual(len(page_ids), manifest["page_count"])
        self.assertTrue(MANUAL_FEEDBACK_PAGE_IDS.issubset(page_ids))

        for page in pages:
            self.assertTrue((PROJECT_ROOT / page["source"]).exists(), page["source"])
            self.assertTrue((PROJECT_ROOT / page["baseline_layout"]).exists(), page["baseline_layout"])
            self.assertTrue((PROJECT_ROOT / page["baseline_preview"]).exists(), page["baseline_preview"])
            self.assertTrue(page["reason"])


if __name__ == "__main__":
    unittest.main()
