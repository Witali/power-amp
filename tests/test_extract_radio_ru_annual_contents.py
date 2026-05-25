import tempfile
import unittest
from pathlib import Path

from scripts import extract_radio_ru_annual_contents as annual_contents


class ExtractRadioRuAnnualContentsTests(unittest.TestCase):
    def test_find_ocr_file_prefers_layout_text_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "b.2000-12.063"
            columns = page / "columns2"
            layout = page / "layout_text_blocks"
            columns.mkdir(parents=True)
            layout.mkdir(parents=True)
            columns_file = columns / "merged.prose.psm6.corrected.txt"
            layout_file = layout / "merged.prose.psm6.corrected.txt"
            columns_file.write_text("columns", encoding="utf-8")
            layout_file.write_text("layout", encoding="utf-8")

            found = annual_contents.find_ocr_file(root, "b.2000-12.063", annual_contents.DEFAULT_OCR_VARIANTS)

            self.assertEqual(found, layout_file)

    def test_find_ocr_file_falls_back_to_fixed_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            columns = root / "b.2000-12.063" / "columns2"
            columns.mkdir(parents=True)
            columns_file = columns / "merged.prose.psm6.txt"
            columns_file.write_text("columns", encoding="utf-8")

            found = annual_contents.find_ocr_file(root, "b.2000-12.063", annual_contents.DEFAULT_OCR_VARIANTS)

            self.assertEqual(found, columns_file)

    def test_parse_page_ranges_builds_page_names(self) -> None:
        pages = annual_contents.parse_page_ranges("1995:059-061,2000:063-064")

        self.assertEqual(
            pages,
            {
                1995: ["b.1995-12.059", "b.1995-12.060", "b.1995-12.061"],
                2000: ["b.2000-12.063", "b.2000-12.064"],
            },
        )
        self.assertEqual(annual_contents.year_span_label(pages), "1995-2000")
        self.assertEqual(annual_contents.default_output_prefix(pages), "radio_annual_contents_1995_2000")

    def test_parse_page_ranges_rejects_reversed_range(self) -> None:
        with self.assertRaises(ValueError):
            annual_contents.parse_page_ranges("1995:061-059")


if __name__ == "__main__":
    unittest.main()
