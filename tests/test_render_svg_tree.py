from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import render_svg_tree


class RenderSvgTreeTests(unittest.TestCase):
    def test_collect_svg_files_returns_sorted_svg_files_and_skips_node_modules(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "b").mkdir()
            (root / "node_modules").mkdir()
            (root / "b" / "second.svg").write_text("<svg/>", encoding="utf-8")
            (root / "first.svg").write_text("<svg/>", encoding="utf-8")
            (root / "node_modules" / "ignored.svg").write_text("<svg/>", encoding="utf-8")
            (root / "note.txt").write_text("nope", encoding="utf-8")

            files = render_svg_tree.collect_svg_files([root])

            self.assertEqual(sorted(path.name for path in files), ["first.svg", "second.svg"])

    def test_render_skips_when_png_is_newer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            svg = root / "symbol.svg"
            png = root / "symbol.png"
            svg.write_text("<svg/>", encoding="utf-8")
            png.write_bytes(b"preview")
            future_time = svg.stat().st_mtime + 10
            png.touch()
            import os

            os.utime(png, (future_time, future_time))

            with mock.patch("render_svg_tree.subprocess.run") as run_mock:
                rendered = render_svg_tree.render(svg, scale=2.0, force=False, verbose=False)

            self.assertFalse(rendered)
            run_mock.assert_not_called()

    def test_render_invokes_renderer_when_forced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            svg = Path(temp) / "symbol.svg"
            svg.write_text("<svg/>", encoding="utf-8")

            with mock.patch("render_svg_tree.subprocess.run") as run_mock:
                rendered = render_svg_tree.render(svg, scale=1.5, force=True, verbose=False)

            self.assertTrue(rendered)
            run_mock.assert_called_once()
            command = run_mock.call_args.args[0]
            self.assertEqual(command[-1], "1.5")
            self.assertEqual(Path(command[3]).suffix, ".png")


if __name__ == "__main__":
    unittest.main()
