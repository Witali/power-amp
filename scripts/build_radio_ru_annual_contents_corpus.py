#!/usr/bin/env python3
"""Build a searchable OCR corpus for Radio annual contents pages."""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OCR_ROOT = Path(".tmp/radio_ru_annual_contents_1986_1995/search")
DEFAULT_OUT_DIR = Path("study/radio_ru_annual_contents_1986_1995")
DEFAULT_CONTENTS_PAGE_RANGES: dict[int, tuple[int, int]] = {
    1986: (63, 68),
    1987: (64, 69),
    1988: (62, 67),
    1989: (88, 95),
    1990: (84, 91),
    1991: (83, 89),
    1992: (54, 58),
    1993: (43, 46),
    1994: (47, 48),
    1995: (59, 61),
}
RADIO86RK_RE = re.compile(
    r"(?iu)(?:"
    r"(?:радио|радно|ралио|дио|panno|paguo|padio|pa)\s*[-—\"“”«»]*\s*(?:86|в6|b6)\s*[-—\"“”«»]*\s*(?:рк|pk)"
    r"|(?:86|в6|b6)\s*[-—\"“”«»]*\s*(?:рк|pk)"
    r")"
)


@dataclass(frozen=True)
class PageSpec:
    year: int
    page_id: str
    page_name: str


@dataclass(frozen=True)
class PageOcr:
    spec: PageSpec
    source: Path
    text: str


@dataclass(frozen=True)
class TopicHit:
    year: int
    page_id: str
    page_name: str
    line_number: int
    hit_line: str
    context: str
    ocr_source: Path


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def archive_url(year: int, page_id: str) -> str:
    return f"http://archive.radio.ru/web/{year}/12/{page_id}/"


def archive_image_path(year: int, page_id: str) -> Path:
    return Path(".tmp/archive_radio_ru") / str(year) / "12" / f"b.{year}-12.{page_id}.jpg"


def build_page_specs(page_ranges: dict[int, tuple[int, int]]) -> list[PageSpec]:
    specs: list[PageSpec] = []
    for year in sorted(page_ranges):
        first, last = page_ranges[year]
        for page in range(first, last + 1):
            page_id = f"{page:03d}"
            specs.append(PageSpec(year=year, page_id=page_id, page_name=f"b.{year}-12.{page_id}"))
    return specs


def read_ocr_pages(ocr_root: Path, specs: list[PageSpec]) -> list[PageOcr]:
    pages: list[PageOcr] = []
    missing: list[Path] = []
    for spec in specs:
        source = ocr_root / f"{spec.year}-12" / f"ocr.{spec.year}-12.{spec.page_id}.txt"
        if not source.exists():
            missing.append(source)
            continue
        pages.append(PageOcr(spec=spec, source=source, text=source.read_text(encoding="utf-8", errors="replace")))
    if missing:
        missing_list = "\n  ".join(rel(path) for path in missing)
        raise FileNotFoundError(f"OCR page file(s) not found:\n  {missing_list}")
    return pages


def find_topic_hits(pages: list[PageOcr]) -> list[TopicHit]:
    hits: list[TopicHit] = []
    for page in pages:
        lines = page.text.splitlines()
        for index, line in enumerate(lines):
            if not RADIO86RK_RE.search(line):
                continue
            context_lines = lines[max(0, index - 2) : min(len(lines), index + 3)]
            hits.append(
                TopicHit(
                    year=page.spec.year,
                    page_id=page.spec.page_id,
                    page_name=page.spec.page_name,
                    line_number=index + 1,
                    hit_line=line.strip(),
                    context="\n".join(context_lines).strip(),
                    ocr_source=page.source,
                )
            )
    return hits


def markdown_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def write_pages_csv(pages: list[PageOcr], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "year",
                "page_id",
                "page_name",
                "archive_url",
                "image_path",
                "ocr_source",
            ],
        )
        writer.writeheader()
        for page in pages:
            writer.writerow(
                {
                    "year": page.spec.year,
                    "page_id": page.spec.page_id,
                    "page_name": page.spec.page_name,
                    "archive_url": archive_url(page.spec.year, page.spec.page_id),
                    "image_path": rel(archive_image_path(page.spec.year, page.spec.page_id)),
                    "ocr_source": rel(page.source),
                }
            )


def write_raw_ocr_markdown(pages: list[PageOcr], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Годовые оглавления журнала Радио, 1986-1995",
        "",
        "Сырой OCR выбранных страниц годовых оглавлений из декабрьских номеров.",
        "Текст получен пайплайном `scripts/search_radio_ru_annual_contents.ps1` и не является ручной вычиткой.",
        "",
    ]
    for page in pages:
        lines.extend(
            [
                f"## {page.spec.page_name}",
                "",
                f"- Архив: {archive_url(page.spec.year, page.spec.page_id)}",
                f"- Скан: `{rel(archive_image_path(page.spec.year, page.spec.page_id))}`",
                f"- OCR: `{rel(page.source)}`",
                "",
                "```text",
                page.text.rstrip(),
                "```",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def write_hits_csv(hits: list[TopicHit], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "year",
                "page_id",
                "page_name",
                "line_number",
                "hit_line",
                "context",
                "archive_url",
                "image_path",
                "ocr_source",
            ],
        )
        writer.writeheader()
        for hit in hits:
            writer.writerow(
                {
                    "year": hit.year,
                    "page_id": hit.page_id,
                    "page_name": hit.page_name,
                    "line_number": hit.line_number,
                    "hit_line": hit.hit_line,
                    "context": hit.context,
                    "archive_url": archive_url(hit.year, hit.page_id),
                    "image_path": rel(archive_image_path(hit.year, hit.page_id)),
                    "ocr_source": rel(hit.ocr_source),
                }
            )


def write_hits_markdown(hits: list[TopicHit], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Радио-86РК в годовых оглавлениях Радио, 1986-1995",
        "",
        f"Найдено OCR-совпадений: {len(hits)}.",
        "Это машинный индекс по строкам оглавлений; для сомнительных строк рядом сохранен контекст.",
        "",
        "| Год | Страница оглавления | Строка | OCR-строка |",
        "|---:|---|---:|---|",
    ]
    for hit in hits:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(hit.year),
                    f"[{hit.page_name}]({archive_url(hit.year, hit.page_id)})",
                    str(hit.line_number),
                    markdown_escape(hit.hit_line),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Контекст", ""])
    for hit in hits:
        lines.extend(
            [
                f"### {hit.page_name}, строка {hit.line_number}",
                "",
                f"- Архив: {archive_url(hit.year, hit.page_id)}",
                f"- Скан: `{rel(archive_image_path(hit.year, hit.page_id))}`",
                f"- OCR: `{rel(hit.ocr_source)}`",
                "",
                "```text",
                hit.context,
                "```",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def write_readme(pages: list[PageOcr], hits: list[TopicHit], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ranges = ", ".join(
        f"{year}: {first:03d}-{last:03d}" for year, (first, last) in sorted(DEFAULT_CONTENTS_PAGE_RANGES.items())
    )
    lines = [
        "# Годовые оглавления Радио, 1986-1995",
        "",
        "Папка хранит распознанные страницы годовых оглавлений из декабрьских номеров журнала `Радио`.",
        "",
        f"- Страниц оглавлений в корпусе: {len(pages)}",
        f"- OCR-совпадений по Радио-86РК: {len(hits)}",
        f"- Диапазоны страниц: {ranges}",
        "",
        "Файлы:",
        "",
        "- `contents_pages.csv` - список страниц, URL архива, локальные пути сканов и OCR.",
        "- `radio_annual_contents_1986_1995_raw_ocr.md` - сырой OCR выбранных страниц.",
        "- `radio86rk_hits.csv` - машинный CSV-индекс строк с Радио-86РК.",
        "- `radio86rk_hits.md` - читаемый индекс совпадений с контекстом.",
        "- `radio86rk_articles.md` - вычитанный черновой список статей по Радио-86РК.",
        "",
        "Сканы лежат вне Git под `.tmp/archive_radio_ru/<year>/12/`, OCR-времянка - под `.tmp/radio_ru_annual_contents_1986_1995/search/`.",
        "",
        "Перегенерировать сохраненные файлы можно так:",
        "",
        "```powershell",
        "python scripts/build_radio_ru_annual_contents_corpus.py `",
        "  --ocr-root .tmp\\radio_ru_annual_contents_1986_1995\\search `",
        "  --out-dir study\\radio_ru_annual_contents_1986_1995",
        "```",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ocr-root", type=Path, default=DEFAULT_OCR_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    specs = build_page_specs(DEFAULT_CONTENTS_PAGE_RANGES)
    pages = read_ocr_pages(args.ocr_root, specs)
    hits = find_topic_hits(pages)

    write_pages_csv(pages, args.out_dir / "contents_pages.csv")
    write_raw_ocr_markdown(pages, args.out_dir / "radio_annual_contents_1986_1995_raw_ocr.md")
    write_hits_csv(hits, args.out_dir / "radio86rk_hits.csv")
    write_hits_markdown(hits, args.out_dir / "radio86rk_hits.md")
    write_readme(pages, hits, args.out_dir / "README.md")

    print(f"Wrote {len(pages)} OCR page(s) and {len(hits)} Radio-86RK hit(s) to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
