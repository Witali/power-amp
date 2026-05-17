from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import spellcheck_text


class SpellcheckTextTests(unittest.TestCase):
    def test_heuristic_flags_mixed_cyrillic_latin_word(self) -> None:
        # The second letter is Latin "c", a common OCR lookalike for Cyrillic "с".
        reason = spellcheck_text.heuristic_reason("уcилитель", set())

        self.assertEqual(reason, "mixed Cyrillic/Latin letters")

    def test_heuristic_flags_digit_inside_cyrillic_word(self) -> None:
        reason = spellcheck_text.heuristic_reason("усилите1ь", set())

        self.assertEqual(reason, "digit inside Cyrillic word")

    def test_allowlist_suppresses_technical_terms(self) -> None:
        allowlist = {spellcheck_text.normalize_word("УМЗЧ")}

        self.assertIsNone(spellcheck_text.heuristic_reason("УМЗЧ", allowlist))

    def test_technical_part_codes_are_ignored(self) -> None:
        for word in ["КР1182ПМ1", "КД247А", "К73-14М", "VT1", "R12"]:
            with self.subTest(word=word):
                self.assertTrue(spellcheck_text.is_ignored_word(word, set()))

    def test_page_references_are_ignored(self) -> None:
        self.assertTrue(spellcheck_text.is_ignored_word("7.с.35", set()))
        self.assertTrue(spellcheck_text.is_ignored_word("7.с.35..-.---..-...--.-.-.6", set()))

    def test_dotted_leader_tail_is_removed_before_checks(self) -> None:
        self.assertEqual(spellcheck_text.clean_word("Елимов...1"), "Елимов")
        self.assertIsNone(spellcheck_text.heuristic_reason("Елимов...1", set()))

    def test_scan_file_reports_line_and_column(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ocr.txt"
            path.write_text("Это уcилитель НЧ\n", encoding="utf-8")

            issues, candidates = spellcheck_text.scan_file(path, set())

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].line, 1)
        self.assertEqual(issues[0].column, 5)
        self.assertEqual(issues[0].word, "уcилитель")
        self.assertIn(spellcheck_text.normalize_word("Это"), candidates)

    def test_collect_text_files_skips_generated_tool_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "keep").mkdir()
            (root / "node_modules").mkdir()
            (root / "keep" / "ocr.txt").write_text("текст", encoding="utf-8")
            (root / "node_modules" / "ignored.txt").write_text("текст", encoding="utf-8")

            files = spellcheck_text.collect_text_files([root])

        self.assertEqual([path.name for path in files], ["ocr.txt"])

    def test_run_hunspell_returns_normalized_words(self) -> None:
        completed = subprocess_result(stdout="Искаженне\n")
        with mock.patch("spellcheck_text.subprocess.run", return_value=completed) as run:
            words = spellcheck_text.run_hunspell(["искаженне"], "ru_RU", "hunspell")

        self.assertEqual(words, {spellcheck_text.normalize_word("Искаженне")})
        self.assertEqual(run.call_args.args[0], ["hunspell", "-d", "ru_RU", "-l"])

    def test_resolve_dictionary_prefers_local_dictionary_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            dictionary_dir = Path(temp)
            (dictionary_dir / "ru_RU.aff").write_text("SET UTF-8\n", encoding="utf-8")
            (dictionary_dir / "ru_RU.dic").write_text("1\nтест\n", encoding="utf-8")

            with mock.patch("spellcheck_text.LOCAL_DICTIONARY_DIR", dictionary_dir):
                resolved = spellcheck_text.resolve_dictionary("ru_RU")

        self.assertEqual(resolved, str(dictionary_dir / "ru_RU"))

    def test_find_hunspell_prefers_local_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            local_dir = Path(temp)
            exe = local_dir / "hunspell.exe"
            exe.write_text("", encoding="utf-8")

            with mock.patch("spellcheck_text.LOCAL_HUNSPELL_DIRS", (local_dir,)):
                with mock.patch("spellcheck_text.shutil.which", return_value="system-hunspell"):
                    found = spellcheck_text.find_hunspell(None)

        self.assertEqual(found, str(exe))


def subprocess_result(stdout: str = "", stderr: str = "", returncode: int = 0):
    return type("Completed", (), {"stdout": stdout, "stderr": stderr, "returncode": returncode})()


if __name__ == "__main__":
    unittest.main()
