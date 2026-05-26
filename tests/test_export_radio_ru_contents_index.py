import csv
import tempfile
import unittest
from pathlib import Path

from scripts import export_radio_ru_contents_index as contents_index


class ExportRadioRuContentsIndexTests(unittest.TestCase):
    def test_archive_image_url_uses_zero_padded_issue_and_page(self) -> None:
        self.assertEqual(
            contents_index.archive_image_url(2000, 2, 36),
            "https://archive.radio.ru/web/img/2000/b.2000-02.036.jpg",
        )

    def test_choose_archive_scan_page_prefers_cached_nearby_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_root = Path(tmp)
            cached = cache_root / "1998" / "12" / "b.1998-12.018.jpg"
            cached.parent.mkdir(parents=True)
            cached.write_bytes(b"jpg")

            self.assertEqual(contents_index.choose_archive_scan_page(cache_root, 1998, 12, 19), 18)

    def test_export_filters_article_rows_and_writes_requested_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "radio_annual_contents_2000_2000.csv"
            source.write_text(
                "\n".join(
                    [
                        "year,section,kind,entry,issue,page,annual_contents_page,column,ocr_source,raw_text,needs_review",
                        "2000,ЗВУКОТЕХНИКА,section,ЗВУКОТЕХНИКА,,,,,,,",
                        "2000,ЗВУКОТЕХНИКА,article,Импульсный блок питания мощного УМЗЧ,2,36,b.2000-12.063,1,ocr.txt,raw,",
                        "2000,ЗВУКОТЕХНИКА,article,Строка без страницы,2,,b.2000-12.063,1,ocr.txt,raw,missing_page",
                    ]
                ),
                encoding="utf-8",
            )

            counts = contents_index.export_contents([source], root / "out", root / "cache")

            self.assertEqual(counts[root / "out" / "radio_contents_2000_2000.csv"], 1)
            with (root / "out" / "radio_contents_all.csv").open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(list(rows[0].keys()), contents_index.CSV_FIELDS)
            self.assertEqual(rows[0]["article_title"], "Импульсный блок питания мощного УМЗЧ")
            self.assertEqual(rows[0]["issue"], "2")
            self.assertEqual(rows[0]["journal_page"], "36")
            self.assertEqual(
                rows[0]["archive_image_url"],
                "https://archive.radio.ru/web/img/2000/b.2000-02.036.jpg",
            )


if __name__ == "__main__":
    unittest.main()
