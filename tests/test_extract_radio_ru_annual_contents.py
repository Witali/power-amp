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

    def test_find_ocr_file_prefers_tsv_lines_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layout = root / "b.2000-12.063" / "layout_text_blocks"
            layout.mkdir(parents=True)
            psm6 = layout / "merged.prose.psm6.corrected.txt"
            tsv_lines = layout / "merged.prose.psm6.tsv_lines.txt"
            psm6.write_text("psm6", encoding="utf-8")
            tsv_lines.write_text("tsv", encoding="utf-8")

            found = annual_contents.find_ocr_file(root, "b.2000-12.063", annual_contents.DEFAULT_OCR_VARIANTS)

            self.assertEqual(found, tsv_lines)

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

    def test_parse_issue_page_accepts_attached_issue_and_page(self) -> None:
        prefix, issue, page = annual_contents.parse_issue_page("Радиолокация ПРО Н. Айтхожин 401")

        self.assertEqual(prefix, "Радиолокация ПРО Н. Айтхожин")
        self.assertEqual(issue, "4")
        self.assertEqual(page, "1")

    def test_parse_issue_page_accepts_noisy_ocr_page_digits(self) -> None:
        prefix, issue, page = annual_contents.parse_issue_page("Малогабаритные мультиметры. А. Афонский 2 ОЗ")

        self.assertEqual(prefix, "Малогабаритные мультиметры. А. Афонский")
        self.assertEqual(issue, "2")
        self.assertEqual(page, "3")

    def test_is_section_accepts_early_nineties_contents_headings(self) -> None:
        self.assertTrue(annual_contents.is_section("СТАТЬИ, ОЧЕРКИ"))
        self.assertTrue(annual_contents.is_section("ПУТЕШЕСТВИЯ. ЭКСПЕДИЦИИ"))
        self.assertTrue(annual_contents.is_section("РАДИОЛЮБИТЕЛЬСТВО И СПОРТ"))

    def test_find_ocr_file_prefers_psm6_for_structured_extraction_when_no_tsv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layout = root / "b.2000-12.063" / "layout_text_blocks"
            layout.mkdir(parents=True)
            psm6 = layout / "merged.prose.psm6.corrected.txt"
            psm4 = layout / "merged.prose.psm4.corrected.txt"
            psm6.write_text("psm6", encoding="utf-8")
            psm4.write_text("psm4", encoding="utf-8")

            found = annual_contents.find_ocr_file(root, "b.2000-12.063", annual_contents.DEFAULT_OCR_VARIANTS)

            self.assertEqual(found, psm6)


if __name__ == "__main__":
    unittest.main()
