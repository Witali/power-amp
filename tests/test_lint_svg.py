from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import lint_svg


VALID_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="80" viewBox="0 0 100 80">
<line x1="10" y1="10" x2="90" y2="70"/>
</svg>
"""


class LintSvgTests(unittest.TestCase):
    def test_valid_svg_has_no_issues(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "valid.svg"
            path.write_text(VALID_SVG, encoding="utf-8")

            self.assertEqual(lint_svg.lint_svg(path), [])

    def test_missing_viewbox_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "missing_viewbox.svg"
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="80"></svg>', encoding="utf-8")

            issues = lint_svg.lint_svg(path)

            self.assertTrue(any(issue.severity == "error" and "viewBox" in issue.message for issue in issues))

    def test_duplicate_id_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "duplicate_id.svg"
            path.write_text(
                """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="80" viewBox="0 0 100 80">
<g id="same"></g>
<g id="same"></g>
</svg>
""",
                encoding="utf-8",
            )

            issues = lint_svg.lint_svg(path)

            self.assertTrue(any(issue.severity == "error" and "Duplicate id" in issue.message for issue in issues))

    def test_collect_svg_files_skips_heavy_generated_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "keep").mkdir()
            (root / "node_modules").mkdir()
            (root / "keep" / "symbol.svg").write_text(VALID_SVG, encoding="utf-8")
            (root / "node_modules" / "ignored.svg").write_text("<not-svg/>", encoding="utf-8")

            files = lint_svg.collect_svg_files([root])

            self.assertEqual([path.name for path in files], ["symbol.svg"])


if __name__ == "__main__":
    unittest.main()
