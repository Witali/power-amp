#!/usr/bin/env python3
"""Generate the project-level static index.html dashboard."""

from __future__ import annotations

import html
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def read_title(readme: Path, fallback: str) -> str:
    if not readme.exists():
        return fallback.replace("_", " ").title()
    for line in readme.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return fallback.replace("_", " ").title()


def read_summary(readme: Path) -> str:
    if not readme.exists():
        return ""
    paragraphs: list[str] = []
    current: list[str] = []
    for raw_line in readme.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("- ") or line.startswith("```"):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if line.startswith("!["):
            continue
        current.append(line)
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs[0] if paragraphs else ""


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def result_cards() -> str:
    results_dir = PROJECT_ROOT / "results"
    cards: list[str] = []
    for folder in sorted(path for path in results_dir.iterdir() if path.is_dir()):
        readme = folder / "README.md"
        title = read_title(readme, folder.name)
        summary = read_summary(readme)
        preview = first_existing(sorted((folder / "schematic").glob("*.png")))
        primary_link = folder / "index.html" if (folder / "index.html").exists() else readme
        plot_count = len(list((folder / "plots").glob("*.png"))) if (folder / "plots").exists() else 0
        netlist_count = len(list((folder / "netlists").glob("*"))) if (folder / "netlists").exists() else 0
        data_count = len(list((folder / "data").rglob("*.*"))) if (folder / "data").exists() else 0
        preview_html = (
            f'<a class="thumb-link" href="{html.escape(rel(primary_link))}"><img src="{html.escape(rel(preview))}" alt="{html.escape(title)} schematic"></a>'
            if preview
            else '<div class="thumb-placeholder">No schematic preview</div>'
        )
        cards.append(
            f"""
        <article class="card result-card">
          {preview_html}
          <div class="card-body">
            <h3>{html.escape(title)}</h3>
            <p>{html.escape(summary)}</p>
            <p class="meta">plots: {plot_count} · netlists: {netlist_count} · data files: {data_count}</p>
            <div class="links">
              <a href="{html.escape(rel(primary_link))}">Open result</a>
              <a href="{html.escape(rel(readme))}">README</a>
            </div>
          </div>
        </article>"""
        )
    return "\n".join(cards)


def write_symbols_index() -> Path:
    symbols_dir = PROJECT_ROOT / "part_symbols"
    symbols_preview = symbols_dir / "part_symbols.png"
    symbols_index = symbols_dir / "index.html"
    symbols_index.write_text(
        f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Part Symbols Library</title>
  <style>
    body {{
      margin: 0;
      font: 15px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #18202a;
      background: #fff;
    }}
    main {{
      width: min(1180px, calc(100% - 32px));
      margin: 28px auto 48px;
    }}
    h1 {{ margin: 0 0 10px; font-size: 30px; }}
    p {{ margin: 0 0 12px; max-width: 860px; }}
    a {{ color: #1769aa; }}
    .links {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 16px 0 22px;
    }}
    .links a {{
      display: inline-flex;
      min-height: 34px;
      align-items: center;
      padding: 6px 10px;
      border: 1px solid #d7dde5;
      border-radius: 6px;
      text-decoration: none;
      color: #18202a;
    }}
    img {{
      display: block;
      max-width: 100%;
      height: auto;
      border: 1px solid #d7dde5;
      border-radius: 8px;
      background: #fff;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Part Symbols Library</h1>
    <p>Локальная библиотека условных графических обозначений для GOST/ESKD, IEC, ANSI и общих элементов. Каждый символ хранится отдельным SVG-файлом и проверяется SVG-линтером.</p>
    <div class="links">
      <a href="../index.html#symbols">Project index</a>
      <a href="README.md">README</a>
      <a href="symbol_sources.md">Symbol sources</a>
      <a href="gost/part_symbols_gost.svg">GOST sheet</a>
      <a href="iec/part_symbols_iec.svg">IEC sheet</a>
      <a href="ansi/part_symbols_ansi.svg">ANSI sheet</a>
    </div>
    <a href="{html.escape(symbols_preview.name)}"><img src="{html.escape(symbols_preview.name)}" alt="Part symbols overview"></a>
  </main>
</body>
</html>
""",
        encoding="utf-8",
        newline="\n",
    )
    return symbols_index


def write_index() -> Path:
    opencv_preview = PROJECT_ROOT / "study" / "opencv_layout_reports" / "latest" / "detected" / "b.2000-02.037" / "preview.png"
    opencv_report = PROJECT_ROOT / "study" / "opencv_layout_reports" / "latest" / "index.html"
    symbols_preview = PROJECT_ROOT / "part_symbols" / "part_symbols.png"
    symbols_index = write_symbols_index()
    symbols_readme = PROJECT_ROOT / "part_symbols" / "README.md"

    index = PROJECT_ROOT / "index.html"
    index.write_text(
        f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Power Amp Project Index</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #18202a;
      --muted: #5d6978;
      --line: #d7dde5;
      --panel: #f7f9fb;
      --accent: #1769aa;
      --accent-2: #287d5b;
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
      width: min(1240px, calc(100% - 32px));
      margin: 28px auto 56px;
    }}
    header.project-header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: end;
      padding-bottom: 18px;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{ margin: 0 0 8px; font-size: 32px; line-height: 1.15; }}
    h2 {{ margin: 32px 0 10px; font-size: 22px; }}
    h3 {{ margin: 0 0 6px; font-size: 17px; }}
    p {{ margin: 0 0 10px; }}
    a {{ color: var(--accent); text-decoration-thickness: 1px; }}
    .subtle {{ color: var(--muted); max-width: 820px; }}
    .quick-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }}
    .quick-links a {{
      display: inline-flex;
      align-items: center;
      min-height: 34px;
      padding: 6px 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      text-decoration: none;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
    }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
    }}
    .card-body {{ padding: 14px; }}
    .thumb-link {{
      display: block;
      aspect-ratio: 16 / 10;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }}
    .thumb-link img {{
      display: block;
      width: 100%;
      height: 100%;
      object-fit: contain;
    }}
    .thumb-placeholder {{
      display: grid;
      place-items: center;
      aspect-ratio: 16 / 10;
      color: var(--muted);
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }}
    .meta {{
      color: var(--muted);
      font-size: 13px;
    }}
    .links {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 8px;
    }}
    .feature {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(280px, 420px);
      gap: 18px;
      align-items: start;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .feature img {{
      display: block;
      width: 100%;
      max-height: 360px;
      object-fit: contain;
      border: 1px solid var(--line);
      background: #fff;
    }}
    .tag-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }}
    .tag {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 3px 8px;
      background: #fff;
      color: var(--muted);
      font-size: 13px;
    }}
    .two-col {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }}
    .compact-list {{
      margin: 8px 0 0 18px;
      padding: 0;
    }}
    @media (max-width: 920px) {{
      header.project-header,
      .feature,
      .two-col {{
        grid-template-columns: 1fr;
      }}
      .quick-links {{ justify-content: flex-start; }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <header class="project-header">
      <div>
        <h1>Power Amp Project Index</h1>
        <p class="subtle">Локальная рабочая карта проекта: схемы и SPICE-результаты, распознавание страниц журналов, библиотека условных графических обозначений.</p>
      </div>
      <nav class="quick-links" aria-label="Quick links">
        <a href="#results">Схемы</a>
        <a href="#recognition">Распознавание</a>
        <a href="#symbols">УГО</a>
        <a href="README.md">README</a>
      </nav>
    </header>

    <section id="results">
      <h2>Индивидуальные схемы и результаты</h2>
      <p class="subtle">Каждая папка в <code>results/</code> хранит схему, графики, данные моделирования, netlist и описание для одного эксперимента или схемы.</p>
      <p class="subtle">Данные схемы были распознаны и заново отрисованы с помощью ИИ. Сгенерированы их SPICE-модели и просимулированы с помощью ngspice.</p>
      <div class="grid">
{result_cards()}
      </div>
    </section>

    <section id="recognition">
      <h2>Распознавание страниц</h2>
      <div class="feature">
        <div>
          <h3>OpenCV layout detector</h3>
          <p>Пайплайн разбивает сканы страниц на текст, изображения, схемы, диаграммы, таблицы и служебные области. Отчет ниже показывает контрольные страницы парами: оригинал и разметка.</p>
          <div class="links">
            <a href="{html.escape(rel(opencv_report))}">Открыть HTML-отчет</a>
            <a href="study/opencv_layout_regression_pages/manifest.json">Regression manifest</a>
            <a href="study/layout_frequency_calibration.md">Frequency calibration</a>
          </div>
          <div class="tag-row">
            <span class="tag">OpenCV</span>
            <span class="tag">Tesseract prep</span>
            <span class="tag">frequency hints</span>
            <span class="tag">20 regression pages</span>
          </div>
        </div>
        <a class="thumb-link" href="{html.escape(rel(opencv_report))}">
          <img src="{html.escape(rel(opencv_preview))}" alt="OpenCV page layout preview">
        </a>
      </div>
    </section>

    <section id="symbols">
      <h2>Библиотека УГО</h2>
      <div class="feature">
        <div>
          <h3>Part symbols</h3>
          <p>Локальная библиотека SVG/PNG символов для GOST/ESKD, IEC, ANSI и общих элементов. Используется как визуальный источник для генераторов схем и правил отрисовки.</p>
          <div class="links">
            <a href="{html.escape(rel(symbols_readme))}">Описание библиотеки</a>
            <a href="part_symbols/gost/part_symbols_gost.svg">GOST sheet</a>
            <a href="part_symbols/iec/part_symbols_iec.svg">IEC sheet</a>
            <a href="part_symbols/ansi/part_symbols_ansi.svg">ANSI sheet</a>
          </div>
          <ul class="compact-list">
            <li>Individual SVG symbols are stored in <code>part_symbols/*/symbols/</code>.</li>
            <li>SVG validity is checked by <code>python scripts/lint_svg.py part_symbols</code>.</li>
            <li>Drawing priorities: preserve symbol proportions, avoid overlaps, then reduce wire length.</li>
          </ul>
        </div>
        <a class="thumb-link" href="{html.escape(rel(symbols_index))}">
          <img src="{html.escape(rel(symbols_preview))}" alt="Part symbols overview">
        </a>
      </div>
    </section>

    <section>
      <h2>Automation</h2>
      <div class="two-col">
        <article class="card">
          <div class="card-body">
            <h3>Useful commands</h3>
            <p><code>npm run check</code> runs unit tests, SVG lint and whitespace checks.</p>
            <p><code>npm run layout:report</code> regenerates the OpenCV page-recognition report.</p>
            <p><code>npm run project:index</code> regenerates this page.</p>
          </div>
        </article>
        <article class="card">
          <div class="card-body">
            <h3>Project notes</h3>
            <p>Work history is recorded in <a href="docs/work_journal.md">docs/work_journal.md</a>. Drawing rules live in <a href="docs/schematic_drawing_rules.md">docs/schematic_drawing_rules.md</a>.</p>
            <p>Local tool inventory is kept in <a href="docs/downloaded_tools.md">docs/downloaded_tools.md</a>.</p>
          </div>
        </article>
      </div>
    </section>
  </main>
</body>
</html>
""",
        encoding="utf-8",
        newline="\n",
    )
    return index


def main() -> int:
    index = write_index()
    print(index)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
