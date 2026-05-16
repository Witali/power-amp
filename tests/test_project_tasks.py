from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import project_tasks


class ProjectTasksTests(unittest.TestCase):
    def test_generate_symbols_runs_generation_render_and_lint(self) -> None:
        calls: list[list[str]] = []

        with mock.patch("project_tasks.run", side_effect=lambda command: calls.append(command)):
            project_tasks.generate_symbols(scale=2.0, force_png=True)

        self.assertEqual(calls[0], [sys.executable, "part_symbols/generate_part_symbols.py"])
        self.assertEqual(calls[1], [sys.executable, "scripts/render_svg_tree.py", "part_symbols", "--scale", "2", "--force"])
        self.assertEqual(calls[2], [sys.executable, "scripts/lint_svg.py", "--fail-on-warning", "part_symbols"])

    def test_check_project_runs_tests_lint_and_git_diff_check(self) -> None:
        calls: list[list[str]] = []

        with mock.patch("project_tasks.run", side_effect=lambda command: calls.append(command)):
            project_tasks.check_project()

        self.assertEqual(calls[0], [sys.executable, "-m", "unittest", "discover", "-s", "tests"])
        self.assertEqual(calls[1], [sys.executable, "scripts/lint_svg.py", "--fail-on-warning"])
        self.assertEqual(calls[2], ["git", "diff", "--check"])

    def test_result_task_builds_shared_runner_command(self) -> None:
        variant = PROJECT_ROOT / "results" / "003_radiostorage_shema_1804_6" / "variants" / "bootstrap.py"
        calls: list[list[str]] = []

        with mock.patch("project_tasks.run", side_effect=lambda command: calls.append(command)):
            project_tasks.run_result(variant, scale=2.5, no_png=True, no_html=False)

        self.assertEqual(
            calls[0],
            [
                sys.executable,
                "scripts/run_circuit_result.py",
                "results/003_radiostorage_shema_1804_6/variants/bootstrap.py",
                "--scale",
                "2.5",
                "--no-png",
            ],
        )

    def test_spellcheck_task_builds_text_checker_command(self) -> None:
        calls: list[list[str]] = []

        with mock.patch("project_tasks.run", side_effect=lambda command: calls.append(command)):
            project_tasks.spellcheck_text([PROJECT_ROOT / "_tmp_radio_ru"], "heuristic", PROJECT_ROOT / "spell.tsv", True)

        self.assertEqual(
            calls[0],
            [
                sys.executable,
                "scripts/spellcheck_text.py",
                "_tmp_radio_ru",
                "--backend",
                "heuristic",
                "--out",
                "spell.tsv",
                "--fail-on-issues",
            ],
        )


if __name__ == "__main__":
    unittest.main()
