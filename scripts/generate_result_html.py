from __future__ import annotations

import argparse
import html
from datetime import datetime
from pathlib import Path


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def inline_markdown(text: str) -> str:
    parts = text.split("`")
    for index in range(1, len(parts), 2):
        parts[index] = f"<code>{esc(parts[index])}</code>"
    for index in range(0, len(parts), 2):
        parts[index] = esc(parts[index])
    return "".join(parts)


def markdown_to_html(markdown: str) -> str:
    html_lines: list[str] = []
    paragraph: list[str] = []
    in_list = False
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            html_lines.append(f"<p>{inline_markdown(' '.join(paragraph))}</p>")
            paragraph = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            html_lines.append("</ul>")
            in_list = False

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()

        if line.startswith("```"):
            flush_paragraph()
            close_list()
            if in_code:
                html_lines.append(f"<pre><code>{esc(chr(10).join(code_lines))}</code></pre>")
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(raw_line)
            continue

        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            close_list()
            continue

        if stripped.startswith("#"):
            flush_paragraph()
            close_list()
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped[level:].strip()
            level = min(max(level, 1), 3)
            html_lines.append(f"<h{level}>{inline_markdown(title)}</h{level}>")
            continue

        if stripped.startswith("- "):
            flush_paragraph()
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{inline_markdown(stripped[2:].strip())}</li>")
            continue

        close_list()
        paragraph.append(stripped)

    flush_paragraph()
    close_list()
    if in_code:
        html_lines.append(f"<pre><code>{esc(chr(10).join(code_lines))}</code></pre>")

    return "\n".join(html_lines)


def find_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    by_stem: dict[str, Path] = {}
    format_rank = {".png": 0, ".jpg": 1, ".jpeg": 1, ".webp": 2, ".svg": 3, ".gif": 4}
    for path in folder.iterdir():
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        current = by_stem.get(path.stem)
        if current is None or format_rank[path.suffix.lower()] < format_rank[current.suffix.lower()]:
            by_stem[path.stem] = path
    return sorted(by_stem.values(), key=lambda path: path.name.lower())


def image_card(result_dir: Path, image: Path) -> str:
    rel = image.relative_to(result_dir).as_posix()
    caption = image.stem.replace("_", " ").replace("-", " ")
    return "\n".join(
        [
            '<figure class="image-card">',
            f'  <a href="{esc(rel)}"><img src="{esc(rel)}" alt="{esc(caption)}" loading="lazy"></a>',
            f"  <figcaption>{esc(caption)}</figcaption>",
            "</figure>",
        ]
    )


def section(result_dir: Path, title: str, images: list[Path], empty_text: str) -> str:
    if not images:
        return f"<section><h2>{esc(title)}</h2><p class=\"muted\">{esc(empty_text)}</p></section>"
    cards = "\n".join(image_card(result_dir, image) for image in images)
    return f"<section><h2>{esc(title)}</h2><div class=\"image-grid\">{cards}</div></section>"


def build_html(result_dir: Path) -> str:
    readme = result_dir / "README.md"
    title = result_dir.name.replace("_", " ")
    description = markdown_to_html(readme.read_text(encoding="utf-8")) if readme.exists() else "<p>No README.md found.</p>"
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    source_images = find_images(result_dir / "source")
    schematic_images = find_images(result_dir / "schematic")
    plot_images = find_images(result_dir / "plots")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #172033;
      --muted: #647083;
      --line: #d8dee8;
      --panel: #f6f8fb;
      --accent: #1665d8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--ink);
      background: #ffffff;
      line-height: 1.5;
    }}
    header {{
      padding: 32px 28px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px 28px 42px;
    }}
    h1, h2, h3 {{
      margin: 0 0 12px;
      line-height: 1.18;
    }}
    h1 {{ font-size: 30px; }}
    h2 {{
      margin-top: 28px;
      padding-top: 8px;
      font-size: 22px;
    }}
    h3 {{ font-size: 18px; }}
    p, ul {{ margin: 0 0 12px; }}
    code {{
      padding: 1px 5px;
      border-radius: 4px;
      background: #edf1f7;
      font-family: Consolas, "Courier New", monospace;
      font-size: 0.95em;
    }}
    pre {{
      overflow: auto;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #101827;
      color: #f7fafc;
    }}
    pre code {{
      padding: 0;
      background: transparent;
      color: inherit;
    }}
    a {{ color: var(--accent); }}
    .muted {{ color: var(--muted); }}
    .description {{
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    .image-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
    }}
    .image-card {{
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
    }}
    .image-card img {{
      display: block;
      width: 100%;
      height: auto;
      background: #fff;
    }}
    .image-card figcaption {{
      padding: 10px 12px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 14px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>{esc(title)}</h1>
    <p class="muted">Generated {esc(generated_at)} from local result files.</p>
  </header>
  <main>
    {section(result_dir, "Source Image", source_images, "No source images found.")}
    <section>
      <h2>Description</h2>
      <article class="description">
        {description}
      </article>
    </section>
    {section(result_dir, "Reconstructed Schematic", schematic_images, "No schematic images found.")}
    {section(result_dir, "Plots", plot_images, "No plot images found.")}
  </main>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a simple HTML report for a result folder.")
    parser.add_argument("result_dir", type=Path, help="Result folder, for example results/003_radiostorage_shema_1804_6")
    parser.add_argument("--output", type=Path, default=None, help="Optional output HTML path. Defaults to result_dir/index.html.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result_dir = args.result_dir.resolve()
    if not result_dir.exists() or not result_dir.is_dir():
        raise SystemExit(f"Result folder not found: {result_dir}")

    output = args.output.resolve() if args.output else result_dir / "index.html"
    output.write_text(build_html(result_dir), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
