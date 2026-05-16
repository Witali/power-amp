from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from circuitlib.common import PROJECT_ROOT, write_text_lf
from generate_result_html import build_html


def load_variant(path: Path) -> ModuleType:
    variant_path = path.resolve()
    if not variant_path.exists():
        raise SystemExit(f"Variant file not found: {variant_path}")

    sys.path.insert(0, str(variant_path.parent))
    sys.path.insert(0, str(variant_path.parents[1]))

    module_name = f"circuit_variant_{variant_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, variant_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load variant: {variant_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    if not hasattr(module, "run"):
        raise SystemExit(f"Variant must expose run(): {variant_path}")
    if not hasattr(module, "RESULT_DIR"):
        raise SystemExit(f"Variant must expose RESULT_DIR: {variant_path}")
    return module


def render_pngs(result_dir: Path, scale: float) -> None:
    renderer = PROJECT_ROOT / "tools" / "render_svg_png.js"
    if not renderer.exists():
        raise SystemExit(f"SVG renderer not found: {renderer}")

    for folder_name in ["schematic", "plots"]:
        folder = result_dir / folder_name
        if not folder.exists():
            continue
        for svg_path in sorted(folder.glob("*.svg")):
            png_path = svg_path.with_suffix(".png")
            subprocess.run(
                ["node", str(renderer), str(svg_path), str(png_path), f"{scale:g}"],
                cwd=str(PROJECT_ROOT),
                check=True,
            )


def generate_html(result_dir: Path) -> None:
    write_text_lf(result_dir / "index.html", build_html(result_dir))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a circuit result variant and regenerate its report artifacts.")
    parser.add_argument("variant", type=Path, help="Variant module, for example results/003.../variants/bootstrap.py")
    parser.add_argument("--no-png", action="store_true", help="Skip SVG to PNG rendering.")
    parser.add_argument("--no-html", action="store_true", help="Skip index.html generation.")
    parser.add_argument("--scale", type=float, default=2.0, help="PNG rendering scale, default: 2.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    module = load_variant(args.variant)
    result_dir = Path(module.RESULT_DIR).resolve()

    module.run()
    if not args.no_png:
        render_pngs(result_dir, args.scale)
    if not args.no_html:
        generate_html(result_dir)

    print(result_dir)


if __name__ == "__main__":
    main()
