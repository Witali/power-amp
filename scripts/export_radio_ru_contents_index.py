#!/usr/bin/env python3
"""Export article-level Radio magazine contents CSV files."""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "study" / "radio_ru_contents"
DEFAULT_CACHE_ROOT = PROJECT_ROOT / ".tmp" / "archive_radio_ru"
PRIMARY_SOURCES = [
    PROJECT_ROOT / "study" / "radio_ru_annual_contents_1986_1995" / "radio_annual_contents_1986_1995.csv",
    PROJECT_ROOT / "study" / "radio_ru_annual_contents_1995_2000" / "radio_annual_contents_1995_2000.csv",
]
LEGACY_FALLBACK_SOURCE = (
    PROJECT_ROOT / "study" / "radio_ru_annual_contents" / "radio_annual_contents_1999_2000.csv"
)
ARCHIVE_IMAGE_URL = "https://archive.radio.ru/web/img/{year}/b.{year}-{issue:02d}.{scan_page:03d}.jpg"
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


@dataclass(frozen=True)
class ArticleRecord:
    year: int
    article_title: str
    issue: int
    journal_page: int
    archive_image_url: str
    archive_image_page: int
    section: str
    source_contents_page: str
    needs_review: str
    source_csv: Path

    def csv_row(self) -> dict[str, str | int]:
        return {
            "year": self.year,
            "article_title": self.article_title,
            "issue": self.issue,
            "journal_page": self.journal_page,
            "archive_image_url": self.archive_image_url,
            "archive_image_page": self.archive_image_page,
            "section": self.section,
            "source_contents_page": self.source_contents_page,
            "needs_review": self.needs_review,
        }


def project_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_int(value: str, minimum: int, maximum: int) -> int | None:
    text = str(value or "").strip()
    if not text.isdigit():
        return None
    number = int(text)
    if minimum <= number <= maximum:
        return number
    return None


def cached_scan_path(cache_root: Path, year: int, issue: int, scan_page: int) -> Path:
    return cache_root / str(year) / f"{issue:02d}" / f"b.{year}-{issue:02d}.{scan_page:03d}.jpg"


def choose_archive_scan_page(cache_root: Path, year: int, issue: int, journal_page: int) -> int:
    """Choose a best-effort archive scan id for a printed journal page.

    archive.radio.ru JPG ids are scan ids, not guaranteed printed page numbers.
    If nearby scans are already cached, prefer the first available close match;
    otherwise keep the printed page as a stable reproducible guess.
    """

    candidates = [
        journal_page,
        journal_page - 1,
        journal_page + 1,
        journal_page - 2,
        journal_page + 2,
    ]
    for candidate in candidates:
        if candidate > 0 and cached_scan_path(cache_root, year, issue, candidate).exists():
            return candidate
    return journal_page


def archive_image_url(year: int, issue: int, scan_page: int) -> str:
    return ARCHIVE_IMAGE_URL.format(year=year, issue=issue, scan_page=scan_page)


def read_articles(source_csv: Path, cache_root: Path) -> list[ArticleRecord]:
    records: list[ArticleRecord] = []
    with source_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if (row.get("kind") or "").strip() != "article":
                continue
            year = parse_int(row.get("year", ""), 1900, 2100)
            issue = parse_int(row.get("issue", ""), 1, 12)
            page = parse_int(row.get("page", ""), 1, 999)
            title = normalize_space(row.get("entry", ""))
            if year is None or issue is None or page is None or not title:
                continue
            scan_page = choose_archive_scan_page(cache_root, year, issue, page)
            records.append(
                ArticleRecord(
                    year=year,
                    article_title=title,
                    issue=issue,
                    journal_page=page,
                    archive_image_url=archive_image_url(year, issue, scan_page),
                    archive_image_page=scan_page,
                    section=normalize_space(row.get("section", "")),
                    source_contents_page=normalize_space(row.get("annual_contents_page", "")),
                    needs_review=normalize_space(row.get("needs_review", "")),
                    source_csv=source_csv,
                )
            )
    return records


def source_output_name(source_csv: Path) -> str:
    stem = source_csv.stem
    if stem.startswith("radio_annual_contents_"):
        return "radio_contents_" + stem.removeprefix("radio_annual_contents_") + ".csv"
    return "radio_contents_" + stem + ".csv"


def default_sources() -> list[Path]:
    sources = [path for path in PRIMARY_SOURCES if path.exists()]
    if not sources and LEGACY_FALLBACK_SOURCE.exists():
        sources.append(LEGACY_FALLBACK_SOURCE)
    return sources


def deduplicate(records: Iterable[ArticleRecord]) -> list[ArticleRecord]:
    unique: dict[tuple[int, int, int, str], ArticleRecord] = {}
    for record in records:
        key = (record.year, record.issue, record.journal_page, record.article_title.casefold())
        unique.setdefault(key, record)
    return sorted(unique.values(), key=lambda item: (item.year, item.issue, item.journal_page, item.article_title))


def write_csv(path: Path, records: Iterable[ArticleRecord]) -> int:
    rows = [record.csv_row() for record in records]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def export_contents(sources: Iterable[Path], output_dir: Path, cache_root: Path) -> dict[Path, int]:
    output_counts: dict[Path, int] = {}
    all_records: list[ArticleRecord] = []

    for source in sources:
        records = deduplicate(read_articles(source, cache_root))
        all_records.extend(records)
        output_counts[output_dir / source_output_name(source)] = write_csv(
            output_dir / source_output_name(source),
            records,
        )

    all_path = output_dir / "radio_contents_all.csv"
    output_counts[all_path] = write_csv(all_path, deduplicate(all_records))
    return output_counts


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        action="append",
        dest="inputs",
        help="Annual contents CSV to export. Can be passed multiple times.",
    )
    parser.add_argument(
        "--out-dir",
        default=rel(DEFAULT_OUTPUT_DIR),
        help="Directory for exported article contents CSV files.",
    )
    parser.add_argument(
        "--cache-root",
        default=rel(DEFAULT_CACHE_ROOT),
        help="Local archive.radio.ru image cache root used for nearby scan-id guesses.",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    sources = [project_path(path) for path in args.inputs] if args.inputs else default_sources()
    if not sources:
        raise SystemExit("No annual contents CSV sources found.")
    missing = [source for source in sources if not source.exists()]
    if missing:
        formatted = ", ".join(rel(path) for path in missing)
        raise SystemExit(f"Missing annual contents CSV source(s): {formatted}")

    output_counts = export_contents(
        sources=sources,
        output_dir=project_path(args.out_dir),
        cache_root=project_path(args.cache_root),
    )
    for path, count in output_counts.items():
        print(f"{rel(path)}: {count} article rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
