from __future__ import annotations

import argparse
from pathlib import Path

from markdown_html import write_html_document


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a standalone HTML file from a Markdown document.")
    parser.add_argument("markdown", type=Path, help="Markdown source file.")
    parser.add_argument("--output", type=Path, default=None, help="Output HTML file. Defaults to <markdown>.html.")
    parser.add_argument("--title", default=None, help="Optional HTML document title.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    markdown_path = args.markdown.resolve()
    if not markdown_path.exists() or not markdown_path.is_file():
        raise SystemExit(f"Markdown file not found: {markdown_path}")

    output_path = args.output.resolve() if args.output else markdown_path.with_suffix(".html")
    write_html_document(markdown_path, output_path, args.title)
    print(output_path)


if __name__ == "__main__":
    main()
