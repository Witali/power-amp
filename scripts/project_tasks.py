from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def run(command: list[str]) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=str(PROJECT_ROOT), check=True)


def generate_symbols(scale: float, force_png: bool) -> None:
    run([sys.executable, "part_symbols/generate_part_symbols.py"])
    render_command = [sys.executable, "scripts/render_svg_tree.py", "part_symbols", "--scale", f"{scale:g}"]
    if force_png:
        render_command.append("--force")
    run(render_command)
    run([sys.executable, "scripts/lint_svg.py", "--fail-on-warning", "part_symbols"])


def lint_project() -> None:
    run([sys.executable, "scripts/lint_svg.py", "--fail-on-warning"])


def test_project() -> None:
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests"])


def check_project() -> None:
    test_project()
    lint_project()
    run(["git", "diff", "--check"])


def render_paths(paths: list[Path], scale: float, force_png: bool) -> None:
    command = [sys.executable, "scripts/render_svg_tree.py", *[rel(path) for path in paths], "--scale", f"{scale:g}"]
    if force_png:
        command.append("--force")
    run(command)


def run_result(variant: Path, scale: float, no_png: bool, no_html: bool) -> None:
    command = [sys.executable, "scripts/run_circuit_result.py", rel(variant), "--scale", f"{scale:g}"]
    if no_png:
        command.append("--no-png")
    if no_html:
        command.append("--no-html")
    run(command)


def spellcheck_text(paths: list[Path], backend: str, out: Path | None, fail_on_issues: bool) -> None:
    command = [sys.executable, "scripts/spellcheck_text.py", *[rel(path) for path in paths], "--backend", backend]
    if out is not None:
        command.extend(["--out", rel(out)])
    if fail_on_issues:
        command.append("--fail-on-issues")
    run(command)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reproducible project task runner.")
    subparsers = parser.add_subparsers(dest="task", required=True)

    symbols = subparsers.add_parser("symbols", help="Regenerate part symbols, render PNG previews, and lint SVG files.")
    symbols.add_argument("--scale", type=float, default=2.0, help="PNG render scale. Default: 2.")
    symbols.add_argument("--force-png", action="store_true", help="Render every PNG preview even if it is up to date.")

    render = subparsers.add_parser("render", help="Render SVG files under selected paths to PNG previews.")
    render.add_argument("paths", nargs="*", type=Path, default=[Path("part_symbols")], help="SVG file or folder paths.")
    render.add_argument("--scale", type=float, default=2.0, help="PNG render scale. Default: 2.")
    render.add_argument("--force-png", action="store_true", help="Render every PNG preview even if it is up to date.")

    subparsers.add_parser("lint", help="Run the SVG linter with warnings treated as failures.")
    subparsers.add_parser("test", help="Run the Python unittest suite.")
    subparsers.add_parser("check", help="Run SVG lint and git whitespace checks.")

    all_task = subparsers.add_parser("all", help="Regenerate symbols and run project checks.")
    all_task.add_argument("--scale", type=float, default=2.0, help="PNG render scale. Default: 2.")
    all_task.add_argument("--force-png", action="store_true", help="Render every PNG preview even if it is up to date.")

    result = subparsers.add_parser("result", help="Run one circuit result variant through the shared result runner.")
    result.add_argument("variant", type=Path, help="Variant module, for example results/003.../variants/bootstrap.py")
    result.add_argument("--scale", type=float, default=2.0, help="PNG render scale. Default: 2.")
    result.add_argument("--no-png", action="store_true", help="Skip SVG to PNG rendering.")
    result.add_argument("--no-html", action="store_true", help="Skip index.html generation.")

    spellcheck = subparsers.add_parser("spellcheck", help="Run OCR text spell/OCR-quality checks.")
    spellcheck.add_argument("paths", nargs="*", type=Path, default=[Path("_tmp_radio_ru")], help="Text files or folders.")
    spellcheck.add_argument("--backend", choices=["auto", "hunspell", "heuristic"], default="auto")
    spellcheck.add_argument("--out", type=Path, help="Optional TSV report path.")
    spellcheck.add_argument("--fail-on-issues", action="store_true", help="Exit non-zero if issues are found.")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.task == "symbols":
            generate_symbols(args.scale, args.force_png)
        elif args.task == "render":
            render_paths(args.paths, args.scale, args.force_png)
        elif args.task == "lint":
            lint_project()
        elif args.task == "test":
            test_project()
        elif args.task == "check":
            check_project()
        elif args.task == "all":
            generate_symbols(args.scale, args.force_png)
            check_project()
        elif args.task == "result":
            run_result(args.variant, args.scale, args.no_png, args.no_html)
        elif args.task == "spellcheck":
            spellcheck_text(args.paths, args.backend, args.out, args.fail_on_issues)
        else:
            raise AssertionError(args.task)
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
