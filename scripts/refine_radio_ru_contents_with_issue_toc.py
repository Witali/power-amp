#!/usr/bin/env python3
"""Refine Radio contents links by matching articles against issue contents pages."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

try:
    import export_radio_ru_contents_index as contents_index
except ModuleNotFoundError:  # pragma: no cover - used when imported as scripts.<module>
    from scripts import export_radio_ru_contents_index as contents_index


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "study" / "radio_ru_contents" / "radio_contents_all.csv"
DEFAULT_ISSUE_OCR_ROOT = PROJECT_ROOT / ".tmp" / "radio_ru_issue_contents_ocr"
DEFAULT_CACHE_ROOT = PROJECT_ROOT / ".tmp" / "archive_radio_ru"
DEFAULT_REPORT = PROJECT_ROOT / "study" / "radio_ru_contents" / "issue_toc_refinement_report.csv"
DEFAULT_FIRST_SCAN_PAGES = 4
DEFAULT_MATCH_THRESHOLD = 0.72
DEFAULT_AMBIGUITY_MARGIN = 0.04
CSV_FIELDS = contents_index.CSV_FIELDS
REPORT_FIELDS = [
    "year",
    "issue",
    "article_title",
    "old_page",
    "new_page",
    "score",
    "action",
    "matched_title",
    "issue_toc_scan_page",
    "issue_toc_source",
]
OCR_FILENAMES = [
    "merged.prose.psm6.corrected.txt",
    "merged.prose.psm6.txt",
    "merged.prose.psm4.corrected.txt",
    "merged.prose.psm4.txt",
    "merged.technical.psm6.corrected.txt",
    "merged.technical.psm6.txt",
]
STOP_WORDS = {
    "для",
    "как",
    "или",
    "при",
    "без",
    "под",
    "над",
    "еще",
    "раз",
    "что",
    "это",
    "его",
    "она",
    "они",
    "радио",
    "журнал",
    "статья",
    "ответы",
    "вопросы",
}
PAGE_DIR_RE = re.compile(r"^b\.(?P<year>\d{4})-(?P<issue>\d{2})\.(?P<scan>\d{3})$")
TRAILING_PAGE_RE = re.compile(r"(?<!\d)(?P<page>[1-9]\d{0,2})\s*$")


@dataclass(frozen=True)
class TocEntry:
    year: int
    issue: int
    scan_page: int
    page: int
    title: str
    source: Path


@dataclass(frozen=True)
class MatchResult:
    entry: TocEntry | None
    score: float
    action: str


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


def normalize_for_match(text: str) -> str:
    text = text.casefold().replace("ё", "е")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"(?<=[а-яa-z])-\s+(?=[а-яa-z])", "", text)
    text = re.sub(r"[^0-9a-zа-я]+", " ", text)
    return normalize_space(text)


def title_tokens(text: str) -> set[str]:
    tokens = set()
    for token in normalize_for_match(text).split():
        if len(token) < 3:
            continue
        if token.isdigit() or token in STOP_WORDS:
            continue
        tokens.add(token)
    return tokens


def title_score(article_title: str, toc_title: str) -> float:
    article_norm = normalize_for_match(article_title)
    toc_norm = normalize_for_match(toc_title)
    if not article_norm or not toc_norm:
        return 0.0

    ratio = SequenceMatcher(None, article_norm, toc_norm).ratio()
    article_tokens = title_tokens(article_title)
    toc_tokens = title_tokens(toc_title)
    if not article_tokens or not toc_tokens:
        return ratio * 0.75

    overlap = len(article_tokens & toc_tokens)
    article_coverage = overlap / len(article_tokens)
    toc_coverage = overlap / len(toc_tokens)
    containment = min(1.0, toc_coverage * 0.82 + article_coverage * 0.18)
    return max(ratio, containment)


def parse_int(value: str, minimum: int, maximum: int) -> int | None:
    text = str(value or "").strip()
    if not text.isdigit():
        return None
    number = int(text)
    if minimum <= number <= maximum:
        return number
    return None


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [field for field in CSV_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{rel(path)} is missing CSV field(s): {', '.join(missing)}")
        return [{field: row.get(field, "") for field in CSV_FIELDS} for row in reader]


def write_rows(path: Path, rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def page_dir_name(year: int, issue: int, scan_page: int) -> str:
    return f"b.{year}-{issue:02d}.{scan_page:03d}"


def issue_page_spec(year: int, issue: int, scan_page: int) -> str:
    return f"{year}-{issue:02d}-{scan_page:03d}"


def required_page_specs(rows: Iterable[dict[str, str]], first_scan_pages: int) -> list[str]:
    issues: set[tuple[int, int]] = set()
    for row in rows:
        year = parse_int(row.get("year", ""), 1900, 2100)
        issue = parse_int(row.get("issue", ""), 1, 12)
        if year is not None and issue is not None:
            issues.add((year, issue))
    specs = [
        issue_page_spec(year, issue, scan_page)
        for year, issue in sorted(issues)
        for scan_page in range(1, first_scan_pages + 1)
    ]
    return specs


def page_has_ocr(issue_ocr_root: Path, year: int, issue: int, scan_page: int) -> bool:
    page_dir = issue_ocr_root / page_dir_name(year, issue, scan_page)
    if not page_dir.exists():
        return False
    return any(page_dir.rglob(filename) for filename in OCR_FILENAMES)


def missing_ocr_page_specs(rows: Iterable[dict[str, str]], issue_ocr_root: Path, first_scan_pages: int) -> list[str]:
    missing: list[str] = []
    for spec in required_page_specs(rows, first_scan_pages):
        year_text, issue_text, scan_text = spec.split("-")
        year = int(year_text)
        issue = int(issue_text)
        scan_page = int(scan_text)
        if not page_has_ocr(issue_ocr_root, year, issue, scan_page):
            missing.append(spec)
    return missing


def write_missing_pages(path: Path, specs: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(specs) + "\n", encoding="utf-8")


def preferred_ocr_file(page_dir: Path) -> Path | None:
    for filename in OCR_FILENAMES:
        candidates = sorted(
            page_dir.rglob(filename),
            key=lambda path: (0 if "layout_text_blocks" in path.parts else 1, len(path.parts), path.as_posix()),
        )
        if candidates:
            return candidates[0]
    return None


def parse_page_dir(path: Path) -> tuple[int, int, int] | None:
    for part in [path.name, *[parent.name for parent in path.parents]]:
        match = PAGE_DIR_RE.match(part)
        if match:
            return int(match.group("year")), int(match.group("issue")), int(match.group("scan"))
    return None


def parse_toc_line(line: str) -> tuple[str, int] | None:
    line = normalize_space(line.replace("\u00a0", " "))
    if not line or "--- column ---" in line or "--- figures ---" in line:
        return None
    match = TRAILING_PAGE_RE.search(line)
    if not match:
        return None
    page = int(match.group("page"))
    if page > 160:
        return None
    title = line[: match.start()].strip(" .,:;—-–·•…")
    title = re.sub(r"[.·•…]{2,}", " ", title)
    title = normalize_space(title)
    if len(normalize_for_match(title)) < 8 or len(title_tokens(title)) < 1:
        return None
    return title, page


def parse_issue_toc_entries(text: str, source: Path, year: int, issue: int, scan_page: int) -> list[TocEntry]:
    entries: list[TocEntry] = []
    seen: set[tuple[str, int]] = set()
    previous = ""
    for raw_line in text.splitlines():
        line = normalize_space(raw_line)
        candidates = [line]
        if previous and line:
            candidates.append(normalize_space(previous + " " + line))
        for candidate in candidates:
            parsed = parse_toc_line(candidate)
            if parsed is None:
                continue
            title, page = parsed
            key = (normalize_for_match(title), page)
            if key in seen:
                continue
            seen.add(key)
            entries.append(TocEntry(year, issue, scan_page, page, title, source))
        previous = line if line else ""
    return entries


def load_issue_toc_entries(issue_ocr_root: Path, year: int, issue: int, first_scan_pages: int) -> list[TocEntry]:
    entries: list[TocEntry] = []
    for scan_page in range(1, first_scan_pages + 1):
        page_dir = issue_ocr_root / page_dir_name(year, issue, scan_page)
        ocr_file = preferred_ocr_file(page_dir)
        if ocr_file is None:
            continue
        parsed_page = parse_page_dir(ocr_file)
        if parsed_page is None:
            parsed_page = (year, issue, scan_page)
        page_year, page_issue, page_scan = parsed_page
        text = ocr_file.read_text(encoding="utf-8", errors="replace")
        entries.extend(parse_issue_toc_entries(text, ocr_file, page_year, page_issue, page_scan))
    return entries


def best_match(article_title: str, entries: list[TocEntry], threshold: float, ambiguity_margin: float) -> MatchResult:
    if not entries:
        return MatchResult(None, 0.0, "no_ocr")
    scored = sorted(
        ((title_score(article_title, entry.title), entry) for entry in entries),
        key=lambda item: item[0],
        reverse=True,
    )
    best_score, best_entry = scored[0]
    if best_score < threshold:
        return MatchResult(best_entry, best_score, "no_match")
    if len(scored) > 1:
        second_score, second_entry = scored[1]
        if second_entry.page != best_entry.page and second_score >= best_score - ambiguity_margin:
            return MatchResult(best_entry, best_score, "ambiguous")
    return MatchResult(best_entry, best_score, "matched")


def update_row_from_match(row: dict[str, str], match: MatchResult, cache_root: Path) -> dict[str, str]:
    if match.entry is None or match.action != "matched":
        return row
    year = int(row["year"])
    issue = int(row["issue"])
    scan_page = contents_index.choose_archive_scan_page(cache_root, year, issue, match.entry.page)
    updated = dict(row)
    updated["journal_page"] = str(match.entry.page)
    updated["archive_image_page"] = str(scan_page)
    updated["archive_image_url"] = contents_index.archive_image_url(year, issue, scan_page)
    return updated


def refine_rows(
    rows: list[dict[str, str]],
    issue_ocr_root: Path,
    cache_root: Path,
    first_scan_pages: int,
    threshold: float,
    ambiguity_margin: float,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    issue_entries: dict[tuple[int, int], list[TocEntry]] = {}
    refined: list[dict[str, str]] = []
    report: list[dict[str, str]] = []

    for row in rows:
        year = parse_int(row.get("year", ""), 1900, 2100)
        issue = parse_int(row.get("issue", ""), 1, 12)
        old_page = parse_int(row.get("journal_page", ""), 1, 999)
        if year is None or issue is None or old_page is None:
            refined.append(row)
            continue

        key = (year, issue)
        if key not in issue_entries:
            issue_entries[key] = load_issue_toc_entries(issue_ocr_root, year, issue, first_scan_pages)
        match = best_match(row.get("article_title", ""), issue_entries[key], threshold, ambiguity_margin)
        new_row = update_row_from_match(row, match, cache_root)
        action = match.action
        if match.action == "matched":
            new_page = parse_int(new_row.get("journal_page", ""), 1, 999)
            action = "updated" if new_page != old_page else "same_page"
        refined.append(new_row)
        report.append(
            {
                "year": str(year),
                "issue": str(issue),
                "article_title": row.get("article_title", ""),
                "old_page": str(old_page),
                "new_page": new_row.get("journal_page", row.get("journal_page", "")),
                "score": f"{match.score:.3f}" if match.score else "",
                "action": action,
                "matched_title": match.entry.title if match.entry else "",
                "issue_toc_scan_page": str(match.entry.scan_page) if match.entry else "",
                "issue_toc_source": rel(match.entry.source) if match.entry else "",
            }
        )
    return refined, report


def run_command(command: list[str]) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=str(PROJECT_ROOT), check=True)


def chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def prepare_issue_toc_ocr(
    rows: list[dict[str, str]],
    cache_root: Path,
    issue_ocr_root: Path,
    first_scan_pages: int,
    prepare_limit: int,
    powershell: str,
) -> None:
    specs = missing_ocr_page_specs(rows, issue_ocr_root, first_scan_pages)
    if prepare_limit > 0:
        specs = specs[:prepare_limit]
    if not specs:
        return

    for batch in chunks(specs, 80):
        run_command(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "scripts/download_radio_ru_pages.ps1",
                "-Pages",
                ",".join(batch),
            ]
        )
    for spec in specs:
        year_text, issue_text, scan_text = spec.split("-")
        year = int(year_text)
        issue = int(issue_text)
        scan_page = int(scan_text)
        image = contents_index.cached_scan_path(cache_root, year, issue, scan_page)
        run_command(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "scripts/ocr_radio_ru_page_columns.ps1",
                "-InputPath",
                rel(image),
                "-OutDir",
                rel(issue_ocr_root),
                "-LayoutTextBlocks",
                "-LayoutOnly",
                "-OcrProfiles",
                "prose",
                "-PsmModes",
                "6",
                "-NoProgress",
            ]
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=rel(DEFAULT_INPUT), help="Radio contents CSV to refine.")
    parser.add_argument(
        "--output",
        help="Refined CSV output path. Defaults to overwriting --input after reading it.",
    )
    parser.add_argument(
        "--issue-ocr-root",
        default=rel(DEFAULT_ISSUE_OCR_ROOT),
        help="OCR output root for first pages of individual issues.",
    )
    parser.add_argument(
        "--cache-root",
        default=rel(DEFAULT_CACHE_ROOT),
        help="archive.radio.ru scan cache root.",
    )
    parser.add_argument("--report", default=rel(DEFAULT_REPORT), help="CSV report for match decisions.")
    parser.add_argument("--first-scan-pages", type=int, default=DEFAULT_FIRST_SCAN_PAGES)
    parser.add_argument("--threshold", type=float, default=DEFAULT_MATCH_THRESHOLD)
    parser.add_argument("--ambiguity-margin", type=float, default=DEFAULT_AMBIGUITY_MARGIN)
    parser.add_argument(
        "--write-missing-pages",
        type=Path,
        help="Write required issue first-page specs that do not have OCR yet.",
    )
    parser.add_argument(
        "--prepare-ocr",
        action="store_true",
        help="Download missing first-page scans and OCR them with existing project scripts before refining.",
    )
    parser.add_argument(
        "--prepare-limit",
        type=int,
        default=0,
        help="When --prepare-ocr is used, limit the number of missing page scans processed. 0 means all.",
    )
    parser.add_argument("--powershell", default="pwsh", help="PowerShell executable for --prepare-ocr.")
    parser.add_argument("--dry-run", action="store_true", help="Build report and missing-page list without writing CSV.")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    input_path = project_path(args.input)
    output_path = project_path(args.output) if args.output else input_path
    issue_ocr_root = project_path(args.issue_ocr_root)
    cache_root = project_path(args.cache_root)
    report_path = project_path(args.report)
    rows = read_rows(input_path)

    if args.write_missing_pages:
        missing = missing_ocr_page_specs(rows, issue_ocr_root, args.first_scan_pages)
        write_missing_pages(project_path(args.write_missing_pages), missing)
        print(f"{rel(project_path(args.write_missing_pages))}: {len(missing)} missing issue TOC OCR page(s)")

    if args.prepare_ocr:
        prepare_issue_toc_ocr(
            rows,
            cache_root=cache_root,
            issue_ocr_root=issue_ocr_root,
            first_scan_pages=args.first_scan_pages,
            prepare_limit=args.prepare_limit,
            powershell=args.powershell,
        )

    refined, report = refine_rows(
        rows,
        issue_ocr_root=issue_ocr_root,
        cache_root=cache_root,
        first_scan_pages=args.first_scan_pages,
        threshold=args.threshold,
        ambiguity_margin=args.ambiguity_margin,
    )

    if not args.dry_run:
        write_rows(output_path, refined)
    write_report(report_path, report)

    actions: dict[str, int] = {}
    for item in report:
        actions[item["action"]] = actions.get(item["action"], 0) + 1
    summary = ", ".join(f"{action}={count}" for action, count in sorted(actions.items()))
    print(f"{rel(output_path)}: {len(refined)} row(s), {summary}")
    print(f"{rel(report_path)}: {len(report)} match decision(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
