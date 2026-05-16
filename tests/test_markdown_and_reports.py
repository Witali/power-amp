from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import generate_result_html
import markdown_html


class MarkdownAndReportTests(unittest.TestCase):
    def test_markdown_to_html_renders_core_constructs(self) -> None:
        html = markdown_html.markdown_to_html(
            """# Title

Text with [link](docs/readme.md) and `code`.

![schematic](schematic.svg)

| A | B |
|---|---|
| 1 | 2 |
"""
        )

        self.assertIn("<h1>Title</h1>", html)
        self.assertIn('<a href="docs/readme.md">link</a>', html)
        self.assertIn("<code>code</code>", html)
        self.assertIn('<img src="schematic.svg" alt="schematic" loading="lazy">', html)
        self.assertIn("<table>", html)

    def test_find_images_prefers_png_for_same_stem(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "plot.svg").write_text("<svg/>", encoding="utf-8")
            (folder / "plot.png").write_bytes(b"png")
            (folder / "source.jpg").write_bytes(b"jpg")
            (folder / "notes.txt").write_text("ignored", encoding="utf-8")

            images = generate_result_html.find_images(folder)

            self.assertEqual([path.name for path in images], ["plot.png", "source.jpg"])

    def test_build_html_uses_readme_and_empty_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = Path(temp) / "001_demo_result"
            result.mkdir()
            (result / "README.md").write_text("# Demo\n\nDescription.", encoding="utf-8")

            html = generate_result_html.build_html(result)

            self.assertIn("<h1>001 demo result</h1>", html)
            self.assertIn("<h1>Demo</h1>", html)
            self.assertIn("No schematic images found.", html)


if __name__ == "__main__":
    unittest.main()
