from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RENDERER = PROJECT_ROOT / "tools" / "render_svg_png.js"

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".tmp",
    "local_tools",
    "node_cache",
    "node_modules",
    "ocr_tools",
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def collect_svg_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for item in paths:
        path = item if item.is_absolute() else PROJECT_ROOT / item
        if path.is_file():
            if path.suffix.lower() == ".svg":
                files.append(path)
            continue
        if not path.exists():
            raise FileNotFoundError(path)
        for root, dirs, names in os.walk(path):
            dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
            for name in names:
                if name.lower().endswith(".svg"):
                    files.append(Path(root) / name)
    return sorted(set(files))


def render(svg_path: Path, scale: float, force: bool, verbose: bool) -> bool:
    png_path = svg_path.with_suffix(".png")
    if not force and png_path.exists() and png_path.stat().st_mtime >= svg_path.stat().st_mtime:
        return False

    subprocess.run(
        ["node", str(RENDERER), str(svg_path), str(png_path), f"{scale:g}"],
        cwd=str(PROJECT_ROOT),
        check=True,
        stdout=None if verbose else subprocess.DEVNULL,
    )
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render SVG files under one or more project folders to PNG previews.")
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("part_symbols")], help="SVG file or folder paths.")
    parser.add_argument("--scale", type=float, default=2.0, help="PNG render scale. Default: 2.")
    parser.add_argument("--force", action="store_true", help="Render even when the PNG preview is newer than the SVG.")
    parser.add_argument("--verbose", action="store_true", help="Print renderer details for every file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not RENDERER.exists():
        print(f"error: SVG renderer not found: {rel(RENDERER)}", file=sys.stderr)
        return 2
    if args.scale <= 0:
        print("error: --scale must be positive", file=sys.stderr)
        return 2

    try:
        svg_files = collect_svg_files(args.paths)
    except FileNotFoundError as exc:
        missing = Path(exc.filename or exc.args[0])
        print(f"error: path not found: {rel(missing)}", file=sys.stderr)
        return 2

    rendered = 0
    for svg_path in svg_files:
        if render(svg_path, args.scale, args.force, args.verbose):
            rendered += 1

    print(f"Rendered {rendered} of {len(svg_files)} SVG file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
