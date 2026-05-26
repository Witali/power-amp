#!/usr/bin/env python3
"""Generate a static HTML page from the Radio magazine contents CSV."""

from __future__ import annotations

import argparse
import csv
import html
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "study" / "radio_ru_contents" / "radio_contents_all.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "study" / "radio_ru_contents" / "index.html"
SOURCE_CONTENTS_PAGE_RE = re.compile(r"^b\.(?P<year>\d{4})-(?P<month>\d{2})\.(?P<page>\d{3})$")
CSV_FIELDS = [
    "year",
    "article_title",
    "issue",
    "journal_page",
    "archive_image_url",
    "archive_image_page",
    "section",
    "source_contents_page",
    "needs_review",
]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def project_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def rel_from_output(target: Path, output: Path) -> str:
    try:
        return Path(os.path.relpath(target.resolve(), output.parent.resolve())).as_posix()
    except ValueError:
        return target.as_posix()


def parse_int(value: str, fallback: int = 0) -> int:
    text = str(value or "").strip()
    return int(text) if text.isdigit() else fallback


def source_contents_jpeg_url(page_id: str) -> str:
    match = SOURCE_CONTENTS_PAGE_RE.match(page_id.strip())
    if not match:
        return ""
    year = match.group("year")
    return f"https://archive.radio.ru/web/img/{year}/{page_id}.jpg"


def source_contents_sort_key(page_id: str) -> tuple[int, int, int, str]:
    match = SOURCE_CONTENTS_PAGE_RE.match(page_id.strip())
    if not match:
        return (9999, 99, 999, page_id)
    return (
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("page")),
        page_id,
    )


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [{field: (row.get(field) or "").strip() for field in CSV_FIELDS} for row in reader]
    rows.sort(key=lambda row: (parse_int(row["year"]), parse_int(row["issue"]), parse_int(row["journal_page"]), row["article_title"].casefold()))
    return rows


def group_rows_by_year(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        year = row["year"]
        if year:
            grouped.setdefault(year, []).append(row)
    return dict(sorted(grouped.items(), key=lambda item: parse_int(item[0])))


def option_html(values: list[str]) -> str:
    return "\n".join(f'            <option value="{esc(value)}">{esc(value)}</option>' for value in values)


def source_contents_pages(rows: list[dict[str, str]]) -> list[str]:
    pages = {row["source_contents_page"] for row in rows if row["source_contents_page"]}
    return sorted(pages, key=source_contents_sort_key)


def source_contents_links_html(rows: list[dict[str, str]], compact: bool = False) -> str:
    pages = source_contents_pages(rows)
    if not pages:
        return ""
    links: list[str] = []
    for page_id in pages:
        url = source_contents_jpeg_url(page_id)
        label = page_id.rsplit(".", 1)[-1] if compact and "." in page_id else page_id
        if url:
            links.append(f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>')
        else:
            links.append(f"<span>{esc(label)}</span>")
    prefix = '<span class="source-label">JPG:</span>' if compact else ""
    return f'{prefix}<span class="source-links">{"".join(links)}</span>'


def source_contents_cell_html(page_id: str) -> str:
    if not page_id:
        return ""
    url = source_contents_jpeg_url(page_id)
    if not url:
        return esc(page_id)
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(page_id)}</a>'


def year_nav_html(
    grouped_rows: dict[str, list[dict[str, str]]],
    year_pages: dict[str, Path],
    output: Path,
) -> str:
    cards: list[str] = []
    for year, year_rows in grouped_rows.items():
        year_href = rel_from_output(year_pages[year], output)
        scans = source_contents_links_html(year_rows, compact=True)
        cards.append(
            "        "
            '<li class="year-card">'
            f'<a class="year-link" href="{esc(year_href)}">{esc(year)}</a>'
            f'<span class="year-count">{len(year_rows)} строк</span>'
            f"{scans}"
            "</li>"
        )
    return "\n".join(cards)


def table_rows_html(rows: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for row in rows:
        review = row["needs_review"]
        review_html = f'<span class="flag review">{esc(review)}</span>' if review else '<span class="flag ok">ok</span>'
        archive_link = (
            f'<a href="{esc(row["archive_image_url"])}" target="_blank" rel="noopener">скан</a>'
            if row["archive_image_url"]
            else ""
        )
        searchable = " ".join(
            [
                row["year"],
                row["issue"],
                row["journal_page"],
                row["article_title"],
                row["section"],
                row["source_contents_page"],
                review,
            ]
        ).casefold()
        lines.append(
            "          "
            f'<tr data-year="{esc(row["year"])}" data-issue="{esc(row["issue"])}" '
            f'data-review="{esc("1" if review else "0")}" data-search="{esc(searchable)}">'
            f'<td>{esc(row["year"])}</td>'
            f'<td>{esc(row["issue"])}</td>'
            f'<td>{esc(row["journal_page"])}</td>'
            f'<td class="title-cell">{esc(row["article_title"])}</td>'
            f'<td>{esc(row["section"])}</td>'
            f'<td>{archive_link}</td>'
            f'<td>{source_contents_cell_html(row["source_contents_page"])}</td>'
            f"<td>{review_html}</td>"
            "</tr>"
        )
    return "\n".join(lines)


def build_html(
    rows: list[dict[str, str]],
    input_csv: Path,
    output: Path,
    year_pages: dict[str, Path] | None = None,
    all_output: Path | None = None,
    current_year: str | None = None,
) -> str:
    years = sorted({row["year"] for row in rows if row["year"]}, key=parse_int)
    issues = [str(issue) for issue in range(1, 13)]
    year_counts = Counter(row["year"] for row in rows if row["year"])
    review_count = sum(1 for row in rows if row["needs_review"])
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    csv_link = rel_from_output(input_csv, output)
    project_index_link = rel_from_output(PROJECT_ROOT / "index.html", output) + "#recognition"
    readme_link = rel_from_output(input_csv.parent / "README.md", output)
    year_summary = ", ".join(f"{year}: {year_counts[year]}" for year in years)
    page_title = f"Оглавление журнала Радио за {current_year} год" if current_year else "Оглавления журнала Радио"
    all_link = rel_from_output(all_output or DEFAULT_OUTPUT, output)
    page_intro = (
        f"Статьи за {esc(current_year)} год из общей CSV-выгрузки. "
        if current_year
        else "Статическая HTML-таблица с машинно распознанными строками годовых оглавлений. "
    )
    source_links = source_contents_links_html(rows)
    source_block = (
        f"""
    <section class="source-scans" aria-label="Сканы исходного оглавления">
      <h2>Сканы годового оглавления</h2>
      <p>{source_links}</p>
    </section>"""
        if source_links and current_year
        else ""
    )
    year_nav = ""
    if year_pages and not current_year:
        grouped = group_rows_by_year(rows)
        year_nav = f"""
    <section class="year-nav" aria-label="Подстраницы по годам">
      <h2>Годы</h2>
      <ul>
{year_nav_html(grouped, year_pages, output)}
      </ul>
    </section>"""

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(page_title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #172033;
      --muted: #647083;
      --line: #d8dee8;
      --panel: #f6f8fb;
      --accent: #1769aa;
      --ok: #287d5b;
      --warn: #9a6a00;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font: 15px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: #fff;
    }}
    main {{
      width: min(1380px, calc(100% - 32px));
      margin: 28px auto 54px;
    }}
    header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: end;
      padding-bottom: 18px;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{ margin: 0 0 8px; font-size: 32px; line-height: 1.15; }}
    h2 {{ margin: 0 0 10px; font-size: 18px; line-height: 1.25; }}
    p {{ margin: 0 0 10px; }}
    a {{ color: var(--accent); text-decoration-thickness: 1px; }}
    .subtle {{ color: var(--muted); max-width: 920px; }}
    .links {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }}
    .links a {{
      display: inline-flex;
      align-items: center;
      min-height: 34px;
      padding: 6px 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      color: var(--ink);
      text-decoration: none;
      background: #fff;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin: 18px 0;
    }}
    .stat {{
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .stat strong {{
      display: block;
      font-size: 22px;
      line-height: 1.1;
    }}
    .year-nav,
    .source-scans {{
      margin: 18px 0;
    }}
    .year-nav ul {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
      margin: 0;
      padding: 0;
      list-style: none;
    }}
    .year-card {{
      display: grid;
      gap: 5px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }}
    .year-link {{
      font-size: 18px;
      font-weight: 650;
      text-decoration-thickness: 1px;
    }}
    .year-count,
    .source-label {{
      color: var(--muted);
      font-size: 13px;
    }}
    .source-links {{
      display: inline-flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .source-label + .source-links {{
      margin-left: 6px;
    }}
    .toolbar {{
      position: sticky;
      top: 0;
      z-index: 2;
      display: grid;
      grid-template-columns: minmax(220px, 1fr) 140px 140px auto;
      gap: 10px;
      align-items: end;
      padding: 12px 0;
      background: #fff;
      border-bottom: 1px solid var(--line);
    }}
    label {{
      display: grid;
      gap: 4px;
      color: var(--muted);
      font-size: 13px;
    }}
    input, select {{
      width: 100%;
      min-height: 36px;
      padding: 6px 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      color: var(--ink);
      background: #fff;
      font: inherit;
    }}
    .check-label {{
      display: flex;
      align-items: center;
      gap: 8px;
      min-height: 36px;
      padding: 6px 0;
    }}
    .check-label input {{ width: auto; min-height: 0; }}
    .count-line {{
      margin: 12px 0;
      color: var(--muted);
    }}
    .table-wrap {{
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    table {{
      width: 100%;
      min-width: 1040px;
      border-collapse: collapse;
      background: #fff;
    }}
    th, td {{
      padding: 7px 9px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      text-align: left;
    }}
    th {{
      color: #fff;
      background: #273447;
      font-weight: 600;
    }}
    tbody tr:nth-child(even) {{ background: #fbfcfe; }}
    .title-cell {{ min-width: 360px; }}
    .flag {{
      display: inline-block;
      max-width: 240px;
      padding: 2px 7px;
      border-radius: 999px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      font-size: 12px;
    }}
    .flag.ok {{ color: var(--ok); background: #e9f5ef; }}
    .flag.review {{ color: var(--warn); background: #fff5da; }}
    @media (max-width: 900px) {{
      header,
      .toolbar,
      .stats {{
        grid-template-columns: 1fr;
      }}
      .links {{ justify-content: flex-start; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>{esc(page_title)}</h1>
        <p class="subtle">{page_intro}Источник: <code>{esc(csv_link)}</code>. Ссылки на сканы ведут на <code>archive.radio.ru</code>.</p>
      </div>
      <nav class="links" aria-label="Навигация">
        <a href="{esc(project_index_link)}">Индекс проекта</a>
        <a href="{esc(all_link)}">Все годы</a>
        <a href="{esc(csv_link)}">CSV</a>
        <a href="{esc(readme_link)}">README</a>
      </nav>
    </header>

    <section class="stats" aria-label="Сводка">
      <div class="stat"><strong>{len(rows)}</strong><span>строк статей</span></div>
      <div class="stat"><strong>{esc(years[0] if years else "")}-{esc(years[-1] if years else "")}</strong><span>годы</span></div>
      <div class="stat"><strong>{len(years)}</strong><span>годовых оглавлений</span></div>
      <div class="stat"><strong>{review_count}</strong><span>строк needs_review</span></div>
    </section>
    <p class="subtle">Распределение по годам: {esc(year_summary)}.</p>
{year_nav}
{source_block}

    <section class="toolbar" aria-label="Фильтры">
      <label>Поиск
        <input id="searchInput" type="search" placeholder="Название, раздел, страница">
      </label>
      <label>Год
        <select id="yearFilter">
          <option value="">Все годы</option>
{option_html(years)}
        </select>
      </label>
      <label>Номер
        <select id="issueFilter">
          <option value="">Все номера</option>
{option_html(issues)}
        </select>
      </label>
      <label class="check-label">
        <input id="reviewFilter" type="checkbox">
        Только needs_review
      </label>
    </section>

    <p class="count-line"><span id="visibleCount">{len(rows)}</span> из {len(rows)} строк</p>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Год</th>
            <th>Номер</th>
            <th>Стр.</th>
            <th>Название статьи</th>
            <th>Раздел</th>
            <th>Скан</th>
            <th>Оглавление</th>
            <th>Проверка</th>
          </tr>
        </thead>
        <tbody id="contentsRows">
{table_rows_html(rows)}
        </tbody>
      </table>
    </div>
  </main>

  <script>
    const searchInput = document.getElementById('searchInput');
    const yearFilter = document.getElementById('yearFilter');
    const issueFilter = document.getElementById('issueFilter');
    const reviewFilter = document.getElementById('reviewFilter');
    const visibleCount = document.getElementById('visibleCount');
    const rows = Array.from(document.querySelectorAll('#contentsRows tr'));

    function applyFilters() {{
      const query = searchInput.value.trim().toLowerCase();
      const year = yearFilter.value;
      const issue = issueFilter.value;
      const onlyReview = reviewFilter.checked;
      let visible = 0;

      for (const row of rows) {{
        const matchesQuery = !query || row.dataset.search.includes(query);
        const matchesYear = !year || row.dataset.year === year;
        const matchesIssue = !issue || row.dataset.issue === issue;
        const matchesReview = !onlyReview || row.dataset.review === '1';
        const show = matchesQuery && matchesYear && matchesIssue && matchesReview;
        row.hidden = !show;
        if (show) visible += 1;
      }}

      visibleCount.textContent = String(visible);
    }}

    searchInput.addEventListener('input', applyFilters);
    yearFilter.addEventListener('change', applyFilters);
    issueFilter.addEventListener('change', applyFilters);
    reviewFilter.addEventListener('change', applyFilters);
  </script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Radio contents CSV path.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output HTML path.")
    return parser.parse_args()


def year_page_path(output: Path, year: str) -> Path:
    return output.parent / "years" / f"{year}.html"


def write_html_pages(rows: list[dict[str, str]], input_csv: Path, output: Path) -> list[Path]:
    grouped = group_rows_by_year(rows)
    year_pages = {year: year_page_path(output, year) for year in grouped}
    written: list[Path] = []

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        build_html(rows, input_csv, output, year_pages=year_pages, all_output=output).rstrip() + "\n",
        encoding="utf-8",
        newline="\n",
    )
    written.append(output)

    for year, year_rows in grouped.items():
        page = year_pages[year]
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(
            build_html(
                year_rows,
                input_csv,
                page,
                year_pages=year_pages,
                all_output=output,
                current_year=year,
            ).rstrip()
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        written.append(page)
    return written


def main() -> int:
    args = parse_args()
    input_csv = project_path(args.input)
    output = project_path(args.output)
    rows = load_rows(input_csv)
    written = write_html_pages(rows, input_csv, output)
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
