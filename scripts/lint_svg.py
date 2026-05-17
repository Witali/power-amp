from __future__ import annotations

import argparse
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".tmp",
    "local_tools",
    "node_cache",
    "node_modules",
    "ocr_tools",
}

NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
LENGTH_RE = re.compile(r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([A-Za-z%]*)\s*$")

NUMERIC_ATTRIBUTES = {
    "cx",
    "cy",
    "dx",
    "dy",
    "height",
    "r",
    "rx",
    "ry",
    "stroke-width",
    "width",
    "x",
    "x1",
    "x2",
    "y",
    "y1",
    "y2",
}

FORBIDDEN_ELEMENTS = {"script", "foreignObject"}


@dataclass
class Issue:
    severity: str
    path: Path
    message: str


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def split_tag(tag: str) -> tuple[str, str]:
    if tag.startswith("{"):
        namespace, _, local = tag[1:].partition("}")
        return namespace, local
    return "", tag


def parse_length(value: str) -> tuple[float | None, str]:
    match = LENGTH_RE.match(value)
    if not match:
        return None, ""
    number = float(match.group(1))
    return number, match.group(2)


def parse_view_box(value: str) -> list[float] | None:
    parts = re.split(r"[\s,]+", value.strip())
    if len(parts) != 4:
        return None
    if not all(NUMBER_RE.match(part) for part in parts):
        return None
    return [float(part) for part in parts]


def numeric_value_is_finite(value: str) -> bool:
    number, _unit = parse_length(value)
    return number is not None and math.isfinite(number)


def element_text_is_empty(element: ET.Element) -> bool:
    if (element.text or "").strip():
        return False
    if (element.tail or "").strip():
        return False
    return len(list(element)) == 0


def collect_svg_files(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        path = target if target.is_absolute() else PROJECT_ROOT / target
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


def lint_svg(path: Path) -> list[Issue]:
    issues: list[Issue] = []
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        return [Issue("error", path, f"XML parse error: {exc}")]
    except OSError as exc:
        return [Issue("error", path, f"Cannot read file: {exc}")]

    root = tree.getroot()
    namespace, local = split_tag(root.tag)
    if local != "svg":
        issues.append(Issue("error", path, f"Root element must be <svg>, got <{local}>."))
        return issues
    if namespace and namespace != SVG_NS:
        issues.append(Issue("error", path, f"Root namespace should be {SVG_NS}, got {namespace}."))
    if not namespace:
        issues.append(Issue("warning", path, "Root <svg> has no SVG namespace."))

    for attr in ("width", "height"):
        value = root.attrib.get(attr)
        if value is None:
            issues.append(Issue("error", path, f"Root <svg> is missing {attr}."))
            continue
        number, unit = parse_length(value)
        if number is None or not math.isfinite(number) or number <= 0:
            issues.append(Issue("error", path, f"Root {attr} must be a positive length, got {value!r}."))
        elif unit and unit != "px":
            issues.append(Issue("warning", path, f"Root {attr} uses non-px unit {unit!r}; generated assets should stay absolute."))

    view_box = root.attrib.get("viewBox")
    if view_box is None:
        issues.append(Issue("error", path, "Root <svg> is missing viewBox."))
    else:
        values = parse_view_box(view_box)
        if values is None:
            issues.append(Issue("error", path, f"viewBox must contain four finite numbers, got {view_box!r}."))
        elif values[2] <= 0 or values[3] <= 0:
            issues.append(Issue("error", path, f"viewBox width and height must be positive, got {view_box!r}."))

    ids: dict[str, int] = {}
    referenced_ids: set[str] = set()

    for element in root.iter():
        element_namespace, element_name = split_tag(element.tag)
        if element_namespace and element_namespace != SVG_NS:
            issues.append(Issue("warning", path, f"Element <{element_name}> uses non-SVG namespace {element_namespace}."))
        if element_name in FORBIDDEN_ELEMENTS:
            issues.append(Issue("error", path, f"Forbidden SVG element <{element_name}> found."))
        if element_name == "g" and element_text_is_empty(element):
            issues.append(Issue("warning", path, "Empty <g> group found."))

        element_id = element.attrib.get("id")
        if element_id:
            ids[element_id] = ids.get(element_id, 0) + 1

        for raw_name, value in element.attrib.items():
            attr_namespace, attr_name = split_tag(raw_name)
            if attr_name.lower().startswith("on"):
                issues.append(Issue("error", path, f"Event handler attribute {attr_name!r} is not allowed."))
            if attr_name in NUMERIC_ATTRIBUTES and not numeric_value_is_finite(value):
                issues.append(Issue("error", path, f"Attribute {attr_name} must be a finite number or length, got {value!r}."))
            if attr_name == "points":
                point_values = re.split(r"[\s,]+", value.strip())
                if not point_values or not all(NUMBER_RE.match(part) for part in point_values):
                    issues.append(Issue("error", path, f"Polyline/polygon points contain a non-numeric token: {value!r}."))
                elif len(point_values) % 2:
                    issues.append(Issue("error", path, f"Polyline/polygon points must contain x/y pairs: {value!r}."))
            if attr_name in {"href", "src"} or (attr_namespace == XLINK_NS and attr_name == "href"):
                if value.startswith("#"):
                    referenced_ids.add(value[1:])
                elif value:
                    issues.append(Issue("warning", path, f"External reference {value!r} found; keep generated SVG self-contained."))

    for element_id, count in sorted(ids.items()):
        if count > 1:
            issues.append(Issue("error", path, f"Duplicate id {element_id!r} appears {count} times."))
    for target_id in sorted(referenced_ids):
        if target_id not in ids:
            issues.append(Issue("error", path, f"Reference points to missing id #{target_id}."))

    return issues


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lint project SVG files for XML validity and reusable generated-asset hygiene.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("part_symbols"), Path("results")],
        help="SVG files or directories to check. Defaults to part_symbols and results.",
    )
    parser.add_argument("--fail-on-warning", action="store_true", help="Return a failing exit code when warnings are present.")
    parser.add_argument("--quiet", action="store_true", help="Print only problems and the final summary.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        files = collect_svg_files(args.paths)
    except FileNotFoundError as exc:
        print(f"error: path not found: {rel(Path(exc.filename or exc.args[0]))}", file=sys.stderr)
        return 2

    if not files:
        print("No SVG files found.")
        return 0

    issues: list[Issue] = []
    for path in files:
        issues.extend(lint_svg(path))

    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warning"]

    for issue in issues:
        print(f"{issue.severity}: {rel(issue.path)}: {issue.message}")

    if not args.quiet or issues:
        print(f"Checked {len(files)} SVG file(s): {len(errors)} error(s), {len(warnings)} warning(s).")

    if errors or (args.fail_on_warning and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
