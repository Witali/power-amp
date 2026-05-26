import csv
import tempfile
import unittest
from pathlib import Path

from scripts import refine_radio_ru_contents_with_issue_toc as refine


def write_contents_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=refine.CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


class RefineRadioRuContentsWithIssueTocTests(unittest.TestCase):
    def test_refines_article_page_from_issue_contents_ocr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [
                {
                    "year": "2000",
                    "article_title": "Импульсный блок питания мощного УМЗЧ",
                    "issue": "2",
                    "journal_page": "36",
                    "archive_image_url": "https://archive.radio.ru/web/img/2000/b.2000-02.036.jpg",
                    "archive_image_page": "36",
                    "section": "ИСТОЧНИКИ ПИТАНИЯ",
                    "source_contents_page": "b.2000-12.063",
                    "needs_review": "",
                }
            ]
            ocr_file = root / "ocr" / "b.2000-02.001" / "layout_text_blocks" / "merged.prose.psm6.corrected.txt"
            ocr_file.parent.mkdir(parents=True)
            ocr_file.write_text(
                "СОДЕРЖАНИЕ\nИмпульсный блок питания мощного УМЗЧ ........ 37\n",
                encoding="utf-8",
            )

            refined, report = refine.refine_rows(
                rows,
                issue_ocr_root=root / "ocr",
                cache_root=root / "cache",
                first_scan_pages=2,
                threshold=0.72,
                ambiguity_margin=0.04,
            )

            self.assertEqual(refined[0]["journal_page"], "37")
            self.assertEqual(refined[0]["archive_image_page"], "37")
            self.assertEqual(
                refined[0]["archive_image_url"],
                "https://archive.radio.ru/web/img/2000/b.2000-02.037.jpg",
            )
            self.assertEqual(report[0]["action"], "updated")
            self.assertEqual(report[0]["matched_title"], "Импульсный блок питания мощного УМЗЧ")

    def test_ambiguous_issue_contents_match_keeps_original_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [
                {
                    "year": "1999",
                    "article_title": "Усилитель с индуктивной коррекцией",
                    "issue": "10",
                    "journal_page": "17",
                    "archive_image_url": "https://archive.radio.ru/web/img/1999/b.1999-10.017.jpg",
                    "archive_image_page": "17",
                    "section": "ЗВУКОТЕХНИКА",
                    "source_contents_page": "b.1999-12.064",
                    "needs_review": "",
                }
            ]
            ocr_file = root / "ocr" / "b.1999-10.001" / "layout_text_blocks" / "merged.prose.psm6.corrected.txt"
            ocr_file.parent.mkdir(parents=True)
            ocr_file.write_text(
                "\n".join(
                    [
                        "Усилитель с индуктивной коррекцией ........ 17",
                        "Усилитель индуктивной коррекции ........ 18",
                    ]
                ),
                encoding="utf-8",
            )

            refined, report = refine.refine_rows(
                rows,
                issue_ocr_root=root / "ocr",
                cache_root=root / "cache",
                first_scan_pages=1,
                threshold=0.72,
                ambiguity_margin=0.08,
            )

            self.assertEqual(refined[0]["journal_page"], "17")
            self.assertEqual(report[0]["action"], "ambiguous")

    def test_writes_missing_first_page_specs_for_issues_without_ocr(self) -> None:
        rows = [
            {"year": "1990", "issue": "1", "journal_page": "1"},
            {"year": "1990", "issue": "1", "journal_page": "2"},
            {"year": "1990", "issue": "2", "journal_page": "3"},
        ]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / "ocr" / "b.1990-01.001" / "layout_text_blocks" / "merged.prose.psm6.txt"
            existing.parent.mkdir(parents=True)
            existing.write_text("Есть OCR", encoding="utf-8")

            missing = refine.missing_ocr_page_specs(rows, root / "ocr", first_scan_pages=2)

        self.assertEqual(missing, ["1990-01-002", "1990-02-001", "1990-02-002"])


if __name__ == "__main__":
    unittest.main()
