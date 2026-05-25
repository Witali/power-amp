import json
import sys
import tempfile
import unittest
import warnings
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import detect_page_layout  # noqa: E402


REGRESSION_ROOT = PROJECT_ROOT / "study" / "opencv_layout_regression_pages"
BBOX_TOLERANCE_PX = 3
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
    "b.2000-02.036",
    "b.2000-12.063",
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _block_ident(block: dict, index: int) -> str:
    ident = block.get("ident") or block.get("id")
    if ident:
        return str(ident)
    return f"#{index:03d}"


def _bbox_deltas(expected_bbox: list, actual_bbox: list) -> list[int]:
    return [abs(int(expected) - int(actual)) for expected, actual in zip(expected_bbox, actual_bbox)]


def compare_layouts(
    expected_layout: dict,
    actual_layout: dict,
    page_id: str,
    *,
    bbox_tolerance_px: int = BBOX_TOLERANCE_PX,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warning_messages: list[str] = []

    for field in ("width", "height"):
        if expected_layout.get(field) != actual_layout.get(field):
            errors.append(
                f"{page_id}: {field} differs: "
                f"expected {expected_layout.get(field)!r}, got {actual_layout.get(field)!r}"
            )

    expected_blocks = expected_layout.get("blocks", [])
    actual_blocks = actual_layout.get("blocks", [])
    if len(expected_blocks) != len(actual_blocks):
        errors.append(
            f"{page_id}: block count differs: "
            f"expected {len(expected_blocks)}, got {len(actual_blocks)}"
        )
        return errors, warning_messages

    for index, (expected_block, actual_block) in enumerate(zip(expected_blocks, actual_blocks), start=1):
        expected_ident = _block_ident(expected_block, index)
        actual_ident = _block_ident(actual_block, index)
        block_ref = f"{page_id} block {expected_ident}"

        if expected_ident != actual_ident:
            errors.append(
                f"{page_id}: block #{index:03d} ident differs: "
                f"expected {expected_ident!r}, got {actual_ident!r}"
            )
            block_ref = f"{page_id} block #{index:03d}"

        for field in ("label", "orientation"):
            if expected_block.get(field) != actual_block.get(field):
                errors.append(
                    f"{block_ref}: {field} differs: "
                    f"expected {expected_block.get(field)!r}, got {actual_block.get(field)!r}"
                )

        expected_bbox = expected_block.get("bbox")
        actual_bbox = actual_block.get("bbox")
        if (
            not isinstance(expected_bbox, list)
            or not isinstance(actual_bbox, list)
            or len(expected_bbox) != 4
            or len(actual_bbox) != 4
        ):
            errors.append(f"{block_ref}: bbox must be a 4-item list")
            continue

        deltas = _bbox_deltas(expected_bbox, actual_bbox)
        max_delta = max(deltas)
        if max_delta > bbox_tolerance_px:
            errors.append(
                f"{block_ref}: bbox differs by up to {max_delta}px "
                f"(tolerance {bbox_tolerance_px}px): expected {expected_bbox}, got {actual_bbox}"
            )
        elif max_delta > 0:
            warning_messages.append(
                f"{block_ref}: bbox differs within tolerance by up to {max_delta}px: "
                f"expected {expected_bbox}, got {actual_bbox}"
            )

    return errors, warning_messages


class LayoutRegressionPagesTests(unittest.TestCase):
    def test_manifest_has_unique_pages_with_sources_and_baselines(self) -> None:
        manifest_path = REGRESSION_ROOT / "manifest.json"
        self.assertTrue(manifest_path.exists())
        manifest = _read_json(manifest_path)
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

    def test_detected_layouts_match_baselines_with_bbox_tolerance(self) -> None:
        manifest = _read_json(REGRESSION_ROOT / "manifest.json")
        preview_width = int(manifest.get("preview_width", 1100))
        frequency_hints = str(manifest.get("frequency_hints", "validate"))
        save_crops = bool(manifest.get("save_crops", False))

        with tempfile.TemporaryDirectory(prefix="opencv_layout_regression_") as temp_dir:
            output_root = Path(temp_dir)
            for page in manifest["pages"]:
                page_id = page["id"]
                with self.subTest(page=page_id):
                    baseline_path = PROJECT_ROOT / page["baseline_layout"]
                    source_path = PROJECT_ROOT / page["source"]
                    actual_layout = detect_page_layout.detect_page_layout(
                        source_path,
                        output_root,
                        preview_width=preview_width,
                        frequency_hints=frequency_hints,
                        save_crops=save_crops,
                    )

                    errors, warning_messages = compare_layouts(
                        _read_json(baseline_path),
                        actual_layout,
                        page_id,
                    )

                    for message in warning_messages:
                        warnings.warn(message, RuntimeWarning, stacklevel=2)
                    if errors:
                        self.fail("\n".join(errors[:20]))

    def test_bbox_tolerance_reports_warning_without_failure(self) -> None:
        expected = {
            "width": 100,
            "height": 200,
            "blocks": [
                {
                    "ident": "001_text",
                    "label": "text",
                    "orientation": "horizontal",
                    "bbox": [10, 20, 30, 40],
                }
            ],
        }
        actual = {
            "width": 100,
            "height": 200,
            "blocks": [
                {
                    "ident": "001_text",
                    "label": "text",
                    "orientation": "horizontal",
                    "bbox": [12, 20, 30, 43],
                }
            ],
        }

        errors, warning_messages = compare_layouts(expected, actual, "synthetic")

        self.assertEqual(errors, [])
        self.assertEqual(len(warning_messages), 1)
        self.assertIn("within tolerance", warning_messages[0])

    def test_bbox_tolerance_fails_when_coordinates_drift_too_far(self) -> None:
        expected = {
            "width": 100,
            "height": 200,
            "blocks": [
                {
                    "ident": "001_text",
                    "label": "text",
                    "orientation": "horizontal",
                    "bbox": [10, 20, 30, 40],
                }
            ],
        }
        actual = {
            "width": 100,
            "height": 200,
            "blocks": [
                {
                    "ident": "001_text",
                    "label": "text",
                    "orientation": "horizontal",
                    "bbox": [14, 20, 30, 40],
                }
            ],
        }

        errors, warning_messages = compare_layouts(expected, actual, "synthetic")

        self.assertEqual(warning_messages, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("tolerance 3px", errors[0])


if __name__ == "__main__":
    unittest.main()
