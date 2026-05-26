import tempfile
import unittest
from pathlib import Path

from scripts import rebuild_annual_contents_tsv_text as tsv_text


class RebuildAnnualContentsTsvTextTests(unittest.TestCase):
    def word(self, text: str, left: int, width: int = 20) -> tsv_text.Word:
        return tsv_text.Word(
            text=text,
            left=left,
            top=10,
            width=width,
            height=12,
            conf=90.0,
            block_num=1,
            par_num=1,
            line_num=1,
            word_num=left,
        )

    def test_rebuild_line_splits_attached_numeric_tail(self) -> None:
        line = tsv_text.rebuild_line(
            [
                self.word("Радиолокация", 10, 120),
                self.word("ПРО", 150, 40),
                self.word("401", 1080, 30),
            ],
            image_width=1146,
        )

        self.assertEqual(line, "Радиолокация ПРО 4 1")

    def test_rebuild_line_drops_dot_leaders_before_tail(self) -> None:
        line = tsv_text.rebuild_line(
            [
                self.word("Селектор", 10, 90),
                self.word("........", 730, 140),
                self.word("12", 990, 25),
                self.word("11", 1075, 30),
            ],
            image_width=1146,
        )

        self.assertEqual(line, "Селектор 12 11")

    def test_digitlike_text_ignores_unreasonably_long_artifacts(self) -> None:
        self.assertEqual(tsv_text.digitlike_text("1" * 100), "")

    def test_parse_tsv_words_ignores_unescaped_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "words.tsv"
            path.write_text(
                "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
                "5\t1\t1\t1\t1\t1\t10\t20\t30\t12\t90.0\t\"Радио\n"
                "5\t1\t1\t1\t1\t2\t50\t20\t30\t12\t91.0\tтекст\n",
                encoding="utf-8",
            )

            words = tsv_text.parse_tsv_words(path)

        self.assertEqual([word.text for word in words], ['"Радио', "текст"])


if __name__ == "__main__":
    unittest.main()
