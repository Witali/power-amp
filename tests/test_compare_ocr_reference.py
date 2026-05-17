import tempfile
import unittest
from pathlib import Path

from scripts import compare_ocr_reference


class CompareOcrReferenceTests(unittest.TestCase):
    def test_html_reference_is_decoded_and_compared(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reference = root / "reference.html"
            candidate = root / "candidate.txt"
            reference.write_text(
                "<html><body><h1>УМЗЧ</h1><p>Транзисторный усилитель мощности звуковой частоты.</p></body></html>",
                encoding="utf-8",
            )
            candidate.write_text("транзисторный усилитель мощности звуковой частоты", encoding="utf-8")

            scores = compare_ocr_reference.compare([reference], [candidate])

            self.assertEqual(len(scores), 1)
            self.assertGreater(scores[0].candidate_token_match, 0.8)

    def test_collect_candidates_recurses_by_glob(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a").mkdir()
            (root / "a" / "merged.prose.psm4.txt").write_text("one", encoding="utf-8")
            (root / "a" / "column1.txt").write_text("two", encoding="utf-8")

            candidates = compare_ocr_reference.collect_candidates(root, "merged*.txt")

            self.assertEqual([path.name for path in candidates], ["merged.prose.psm4.txt"])

    def test_cp1251_reference_can_be_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "reference.htm"
            path.write_bytes("<p>Усилитель на транзисторах</p>".encode("cp1251"))

            tokens, encoding = compare_ocr_reference.load_normalized(path)

            self.assertIn("усилитель", tokens)
            self.assertEqual(encoding, "cp1251")


if __name__ == "__main__":
    unittest.main()
