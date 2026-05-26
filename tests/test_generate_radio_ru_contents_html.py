import csv
import tempfile
import unittest
from pathlib import Path

from scripts import generate_radio_ru_contents_html as contents_html


class GenerateRadioRuContentsHtmlTests(unittest.TestCase):
    def test_load_rows_sorts_by_year_issue_page_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "contents.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=contents_html.CSV_FIELDS)
                writer.writeheader()
                writer.writerow({"year": "1995", "issue": "2", "journal_page": "10", "article_title": "B"})
                writer.writerow({"year": "1990", "issue": "1", "journal_page": "2", "article_title": "A"})

            rows = contents_html.load_rows(csv_path)

        self.assertEqual([row["article_title"] for row in rows], ["A", "B"])

    def test_build_html_contains_filters_and_archive_link(self) -> None:
        rows = [
            {
                "year": "2000",
                "article_title": "Импульсный блок питания мощного УМЗЧ",
                "issue": "2",
                "journal_page": "36",
                "archive_image_url": "https://archive.radio.ru/web/img/2000/b.2000-02.036.jpg",
                "archive_image_page": "36",
                "section": "ЗВУКОТЕХНИКА",
                "source_contents_page": "b.2000-12.063",
                "needs_review": "ocr_noise",
            }
        ]

        html = contents_html.build_html(rows, Path("study/radio_ru_contents/radio_contents_all.csv"), Path("study/radio_ru_contents/index.html"))

        self.assertIn("searchInput", html)
        self.assertIn("Импульсный блок питания мощного УМЗЧ", html)
        self.assertIn("https://archive.radio.ru/web/img/2000/b.2000-02.036.jpg", html)
        self.assertIn("ocr_noise", html)


if __name__ == "__main__":
    unittest.main()
