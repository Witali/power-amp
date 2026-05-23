import tempfile
import unittest
from pathlib import Path

from scripts import build_radio_ru_annual_contents_corpus as corpus


class BuildRadioRuAnnualContentsCorpusTests(unittest.TestCase):
    def test_build_page_specs_expands_in_order(self) -> None:
        specs = corpus.build_page_specs({1987: (64, 65), 1986: (63, 63)})

        self.assertEqual(
            [spec.page_name for spec in specs],
            ["b.1986-12.063", "b.1987-12.064", "b.1987-12.065"],
        )

    def test_find_topic_hits_keeps_context(self) -> None:
        page = corpus.PageOcr(
            spec=corpus.PageSpec(year=1986, page_id="067", page_name="b.1986-12.067"),
            source=Path("ocr.1986-12.067.txt"),
            text="\n".join(
                [
                    "Персональный радиолюбительский компьютер «Pa-",
                    "дио-86РК». Горшков, Зеленко, Озеров",
                    "Архитектура компьютера. 4 24",
                ]
            ),
        )

        hits = corpus.find_topic_hits([page])

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].line_number, 2)
        self.assertIn("Персональный радиолюбительский компьютер", hits[0].context)

    def test_read_ocr_pages_reports_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec = corpus.PageSpec(year=1986, page_id="063", page_name="b.1986-12.063")

            with self.assertRaises(FileNotFoundError):
                corpus.read_ocr_pages(Path(tmp), [spec])


if __name__ == "__main__":
    unittest.main()
