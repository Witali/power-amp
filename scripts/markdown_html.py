from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path


INLINE_LINK_RE = re.compile(r"(!)?\[([^\]]*)\]\(([^)]+)\)")
ORDERED_LIST_RE = re.compile(r"^\d+\.\s+(.*)$")
UNORDERED_LIST_RE = re.compile(r"^[-*]\s+(.*)$")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_inline(text: str) -> str:
    parts = text.split("`")
    for index in range(1, len(parts), 2):
        parts[index] = f"<code>{esc(parts[index])}</code>"
    for index in range(0, len(parts), 2):
        parts[index] = render_links_and_images(parts[index])
    return "".join(parts)


def render_links_and_images(text: str) -> str:
    output: list[str] = []
    position = 0
    for match in INLINE_LINK_RE.finditer(text):
        output.append(esc(text[position : match.start()]))
        is_image, label, target = match.groups()
        if is_image:
            output.append(f'<img src="{esc(target)}" alt="{esc(label)}" loading="lazy">')
        else:
            output.append(f'<a href="{esc(target)}">{render_inline(label)}</a>')
        position = match.end()
    output.append(esc(text[position:]))
    return "".join(output)


def split_table_cells(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def is_table_separator(line: str) -> bool:
    cells = split_table_cells(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def render_table(header: list[str], rows: list[list[str]]) -> str:
    head_cells = "".join(f"<th>{render_inline(cell)}</th>" for cell in header)
    body_rows = []
    for row in rows:
        cells = row + [""] * max(0, len(header) - len(row))
        body_rows.append("<tr>" + "".join(f"<td>{render_inline(cell)}</td>" for cell in cells[: len(header)]) + "</tr>")
    return "\n".join(
        [
            "<table>",
            f"<thead><tr>{head_cells}</tr></thead>",
            "<tbody>",
            *body_rows,
            "</tbody>",
            "</table>",
        ]
    )


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    html_lines: list[str] = []
    paragraph: list[str] = []
    list_tag: str | None = None
    in_code = False
    code_lang = ""
    code_lines: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            html_lines.append(f"<p>{render_inline(' '.join(paragraph))}</p>")
            paragraph = []

    def close_list() -> None:
        nonlocal list_tag
        if list_tag:
            html_lines.append(f"</{list_tag}>")
            list_tag = None

    def open_list(tag: str) -> None:
        nonlocal list_tag
        if list_tag != tag:
            close_list()
            html_lines.append(f"<{tag}>")
            list_tag = tag

    while index < len(lines):
        raw_line = lines[index]
        line = raw_line.rstrip()

        if line.startswith("```"):
            flush_paragraph()
            close_list()
            if in_code:
                lang_attr = f' class="language-{esc(code_lang)}"' if code_lang else ""
                html_lines.append(f"<pre><code{lang_attr}>{esc(chr(10).join(code_lines))}</code></pre>")
                code_lines = []
                code_lang = ""
                in_code = False
            else:
                code_lang = line[3:].strip()
                in_code = True
            index += 1
            continue

        if in_code:
            code_lines.append(raw_line)
            index += 1
            continue

        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            close_list()
            index += 1
            continue

        if stripped.startswith("|") and index + 1 < len(lines) and is_table_separator(lines[index + 1].strip()):
            flush_paragraph()
            close_list()
            header = split_table_cells(stripped)
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(split_table_cells(lines[index]))
                index += 1
            html_lines.append(render_table(header, rows))
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            html_lines.append(f"<h{level}>{render_inline(heading.group(2).strip())}</h{level}>")
            index += 1
            continue

        unordered = UNORDERED_LIST_RE.match(stripped)
        if unordered:
            flush_paragraph()
            open_list("ul")
            html_lines.append(f"<li>{render_inline(unordered.group(1).strip())}</li>")
            index += 1
            continue

        ordered = ORDERED_LIST_RE.match(stripped)
        if ordered:
            flush_paragraph()
            open_list("ol")
            html_lines.append(f"<li>{render_inline(ordered.group(1).strip())}</li>")
            index += 1
            continue

        close_list()
        paragraph.append(stripped)
        index += 1

    flush_paragraph()
    close_list()
    if in_code:
        lang_attr = f' class="language-{esc(code_lang)}"' if code_lang else ""
        html_lines.append(f"<pre><code{lang_attr}>{esc(chr(10).join(code_lines))}</code></pre>")

    return "\n".join(html_lines)


def build_html_document(markdown: str, title: str, source_name: str | None = None) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source_text = f" from {source_name}" if source_name else ""
    body = markdown_to_html(markdown)
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
      --code-bg: #edf1f7;
      --accent: #1665d8;
      --image-max-width: 920px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--ink);
      background: #fff;
      line-height: 1.55;
    }}
    header {{
      padding: 32px 28px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    main {{
      max-width: 1040px;
      margin: 0 auto;
      padding: 24px 28px 44px;
    }}
    h1, h2, h3, h4, h5, h6 {{
      margin: 24px 0 12px;
      line-height: 1.18;
    }}
    h1 {{ font-size: 30px; margin-top: 0; }}
    h2 {{ font-size: 23px; padding-top: 8px; }}
    h3 {{ font-size: 18px; }}
    p, ul, ol, table, pre {{ margin: 0 0 14px; }}
    ul, ol {{ padding-left: 24px; }}
    a {{ color: var(--accent); }}
    code {{
      padding: 1px 5px;
      border-radius: 4px;
      background: var(--code-bg);
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
    img {{
      display: block;
      width: auto;
      max-width: min(100%, var(--image-max-width));
      height: auto;
      margin: 12px auto 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      display: block;
      overflow-x: auto;
    }}
    th, td {{
      padding: 8px 10px;
      border: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: var(--panel); }}
    .muted {{ color: var(--muted); }}
  </style>
</head>
<body>
  <header>
    <h1>{esc(title)}</h1>
    <p class="muted">Generated {esc(generated_at)}{esc(source_text)}.</p>
  </header>
  <main>
    {body}
  </main>
</body>
</html>
"""


def write_html_document(markdown_path: Path, output_path: Path, title: str | None = None) -> None:
    markdown = markdown_path.read_text(encoding="utf-8")
    resolved_title = title or markdown_path.stem.replace("_", " ").replace("-", " ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        build_html_document(markdown, resolved_title, markdown_path.name).rstrip() + "\n",
        encoding="utf-8",
        newline="\n",
    )
