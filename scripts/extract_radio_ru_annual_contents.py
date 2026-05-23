#!/usr/bin/env python3
"""Extract OCR-derived annual Radio magazine contents tables."""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAGES = {
    1999: ["b.1999-12.064", "b.1999-12.065", "b.1999-12.066", "b.1999-12.067"],
    2000: ["b.2000-12.063", "b.2000-12.064", "b.2000-12.065", "b.2000-12.066"],
}

SECTION_WORDS = {
    "НАУКА",
    "ТЕХНИКА",
    "ВЫСТАВКИ",
    "ВИДЕОТЕХНИКА",
    "СПУТНИКОВОЕ",
    "ТЕЛЕВИДЕНИЕ",
    "ВЕЩАНИЕ",
    "ЗВУКОТЕХНИКА",
    "РАДИОПРИЕМ",
    "РАДИОСВЯЗЬ",
    "ЭЛЕКТРОНИКА",
    "БЫТУ",
    "ИСТОЧНИКИ",
    "ПИТАНИЯ",
    "РАДИОЛЮБИТЕЛЮ",
    "КОНСТРУКТОРУ",
    "РАДИОЛЮБИТЕЛЬСКАЯ",
    "ТЕХНОЛОГИЯ",
    "СПРАВОЧНЫЕ",
    "МАТЕРИАЛЫ",
    "НАЧИНАЮЩИМ",
    "КНИЖНОЙ",
    "ПОЛКЕ",
    "ИЗМЕРЕНИЯ",
    "РАДИОПРИЕМ",
    "СОВЕТЫ",
    "ПОКУПАТЕЛЯМ",
}

NOISE_PATTERNS = [
    re.compile(r"^(?:ПРАДО|ПРАЛИО|PAAMO|PAA|AMO|PRADA|PRA)(?:\b|\W)", re.IGNORECASE),
    re.compile(r"^РАДИО\s*(?:[|/\]\\]|$)", re.IGNORECASE),
    re.compile(r"^\W+$"),
    re.compile(r"^[\d\s.,;:|/\\\-_+=~`'\"<>()[\]{}]+$"),
]

TRAILING_ISSUE_PAGE_RE = re.compile(
    r"(?P<prefix>.*?)(?<!\d)(?P<issue>[1-9]|1[0-2])\s*(?:[—-]\s*)?(?P<page>[1-9]\d{0,2})(?:\D*)$"
)
PAIR_RE = re.compile(r"(?<!\d)(?P<issue>[1-9]|1[0-2])\s*[—-]\s*(?P<page>[1-9]\d{0,2})(?!\d)")
ONLY_NUMBERS_RE = re.compile(r"^(?P<issue>[1-9]|1[0-2])\s+(?P<page>[1-9]\d{0,2})$")


@dataclass
class Record:
    year: int
    section: str
    kind: str
    entry: str
    issue: str = ""
    page: str = ""
    annual_contents_page: str = ""
    column: int = 0
    ocr_source: str = ""
    raw_text: str = ""
    needs_review: str = ""


@dataclass
class ParseState:
    year: int
    section: str = ""
    previous_entry: str = ""
    records: list[Record] = field(default_factory=list)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def normalize_line(line: str) -> str:
    line = line.replace("\u00a0", " ")
    line = line.replace("—", "-").replace("–", "-")
    line = re.sub(r"\s+", " ", line).strip()
    return line


def cyrillic_count(text: str) -> int:
    return len(re.findall(r"[А-Яа-яЁё]", text))


def is_noise(line: str) -> bool:
    if not line:
        return True
    if any(pattern.search(line) for pattern in NOISE_PATTERNS):
        return True
    if cyrillic_count(line) < 3 and not re.search(r"\d", line):
        return True
    letters = re.findall(r"[A-Za-zА-Яа-яЁё]", line)
    if len(line) > 12 and letters:
        cyrillic_ratio = cyrillic_count(line) / max(1, len(letters))
        if cyrillic_ratio < 0.20 and re.search(r"[A-Za-z]{3,}", line):
            return True
    if len(line) <= 2:
        return True
    return False


def clean_section(line: str) -> str:
    line = re.sub(r"[^А-ЯЁA-Z0-9\"'(). -]+", " ", line)
    line = re.sub(r"\s+", " ", line).strip(" .-")
    line = re.sub(r"\s+(?:[ЗБЕ<]|[A-Z])$", "", line)
    return line


def is_section(line: str) -> bool:
    cleaned = clean_section(line)
    if cyrillic_count(cleaned) < 5:
        return False
    words = {word.strip(".").upper() for word in re.findall(r"[А-ЯЁA-Z]{3,}", cleaned)}
    if not words:
        return False
    if words & SECTION_WORDS and len(cleaned) <= 80:
        lowercase = len(re.findall(r"[а-яё]", cleaned))
        uppercase = len(re.findall(r"[А-ЯЁ]", cleaned))
        return uppercase >= max(3, lowercase * 2)
    return False


def clean_entry_text(text: str) -> str:
    text = normalize_line(text)
    text = re.sub(r"[._·•]{2,}", " ", text)
    text = re.sub(r"[-=]{3,}", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .,-;:")


def parse_issue_page(text: str) -> tuple[str, str, str]:
    candidate = re.sub(r"[.,;:|/\\_+=~`'\"<>()[\]{}]+$", "", text).strip()
    match = TRAILING_ISSUE_PAGE_RE.match(candidate)
    if not match:
        return text, "", ""
    issue = int(match.group("issue"))
    page = int(match.group("page"))
    if not (1 <= issue <= 12 and 1 <= page <= 130):
        return text, "", ""
    return match.group("prefix").strip(), str(issue), str(page)


def needs_review(text: str, issue: str, page: str) -> str:
    flags: list[str] = []
    if not issue or not page:
        flags.append("no_issue_page")
    if re.search(r"[A-Za-z]{3,}", text) and cyrillic_count(text) < len(text) // 3:
        flags.append("latin_noise")
    if re.search(r"\b(?:aaa|eee|cece|cere|eos|wee)\b", text, re.IGNORECASE):
        flags.append("ocr_filler")
    if re.search(r"[{}<>|_~=]{2,}", text):
        flags.append("ocr_noise")
    if len(text) < 6:
        flags.append("short")
    return ";".join(flags)


def emit_buffer(
    state: ParseState,
    buffer: list[str],
    year: int,
    page_name: str,
    column_index: int,
    source: Path,
) -> list[str]:
    if not buffer:
        return []

    raw = " ".join(buffer)
    prefix, issue, page = parse_issue_page(raw)
    entry = clean_entry_text(prefix)
    if not entry or not state.section:
        return []

    kind = "article" if issue and page else "unparsed"
    record = Record(
        year=year,
        section=state.section,
        kind=kind,
        entry=entry,
        issue=issue,
        page=page,
        annual_contents_page=page_name,
        column=column_index,
        ocr_source=rel(source),
        raw_text=raw,
        needs_review=needs_review(entry, issue, page),
    )
    state.records.append(record)
    if kind == "article":
        state.previous_entry = entry
    return []


def parse_see_also(
    state: ParseState,
    line: str,
    year: int,
    page_name: str,
    column_index: int,
    source: Path,
) -> bool:
    if not re.match(r"(?i)^(?:см\.?\s*)?также\b|^см\.", line):
        return False
    pairs = list(PAIR_RE.finditer(line))
    if not pairs:
        state.records.append(
            Record(
                year=year,
                section=state.section,
                kind="see_also",
                entry=state.previous_entry,
                annual_contents_page=page_name,
                column=column_index,
                ocr_source=rel(source),
                raw_text=line,
                needs_review="no_pairs",
            )
        )
        return True

    for pair in pairs:
        state.records.append(
            Record(
                year=year,
                section=state.section,
                kind="see_also",
                entry=state.previous_entry,
                issue=pair.group("issue"),
                page=pair.group("page"),
                annual_contents_page=page_name,
                column=column_index,
                ocr_source=rel(source),
                raw_text=line,
            )
        )
    return True


def parse_number_continuation(
    state: ParseState,
    line: str,
    year: int,
    page_name: str,
    column_index: int,
    source: Path,
) -> bool:
    match = ONLY_NUMBERS_RE.match(line)
    if not match or not state.previous_entry:
        return False
    state.records.append(
        Record(
            year=year,
            section=state.section,
            kind="continued",
            entry=state.previous_entry,
            issue=match.group("issue"),
            page=match.group("page"),
            annual_contents_page=page_name,
            column=column_index,
            ocr_source=rel(source),
            raw_text=line,
        )
    )
    return True


def parse_text_file(year: int, page_name: str, source: Path, state: ParseState) -> list[Record]:
    start_count = len(state.records)
    text = source.read_text(encoding="utf-8", errors="replace")
    columns = re.split(r"\n\s*--- column ---\s*\n", text)
    for column_index, column in enumerate(columns, start=1):
        buffer: list[str] = []
        for raw_line in column.splitlines():
            line = normalize_line(raw_line)
            if is_noise(line):
                continue
            if is_section(line):
                buffer = emit_buffer(state, buffer, year, page_name, column_index, source)
                section = clean_section(line)
                state.section = section
                state.records.append(
                    Record(
                        year=year,
                        section=section,
                        kind="section",
                        entry=section,
                        annual_contents_page=page_name,
                        column=column_index,
                        ocr_source=rel(source),
                        raw_text=line,
                    )
                )
                continue
            if re.match(r"(?i)^(?:см\.?\s*)?также\b|^см\.", line):
                buffer = emit_buffer(state, buffer, year, page_name, column_index, source)
                parse_see_also(state, line, year, page_name, column_index, source)
                continue
            if ONLY_NUMBERS_RE.match(line):
                buffer = emit_buffer(state, buffer, year, page_name, column_index, source)
                parse_number_continuation(state, line, year, page_name, column_index, source)
                continue

            buffer.append(line)
            prefix, issue, page = parse_issue_page(" ".join(buffer))
            if issue and page:
                buffer = emit_buffer(state, buffer, year, page_name, column_index, source)
            elif len(buffer) >= 4:
                buffer = emit_buffer(state, buffer, year, page_name, column_index, source)
        emit_buffer(state, buffer, year, page_name, column_index, source)
    return state.records[start_count:]


def find_ocr_file(ocr_root: Path, page_name: str) -> Path:
    base = ocr_root / page_name / "columns2"
    corrected = base / "merged.prose.psm6.corrected.txt"
    raw = base / "merged.prose.psm6.txt"
    if corrected.exists():
        return corrected
    if raw.exists():
        return raw
    raise FileNotFoundError(f"OCR file not found for {page_name} under {ocr_root}")


def write_csv(records: list[Record], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "year",
                "section",
                "kind",
                "entry",
                "issue",
                "page",
                "annual_contents_page",
                "column",
                "ocr_source",
                "raw_text",
                "needs_review",
            ],
        )
        writer.writeheader()
        for record in records:
            writer.writerow(record.__dict__)


def markdown_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def write_markdown(records: list[Record], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    article_count = sum(1 for record in records if record.kind == "article")
    review_count = sum(1 for record in records if record.needs_review)
    lines = [
        "# Годовые оглавления журнала Радио, 1999-2000",
        "",
        "Таблица получена OCR-обработкой декабрьских страниц годовых оглавлений с `archive.radio.ru`.",
        "В CSV сохранены нормализованный текст и сырой OCR-фрагмент, чтобы сомнительные строки можно было сверить со сканом.",
        "",
        f"- Всего записей: {len(records)}",
        f"- Строк статей с номером выпуска и страницей: {article_count}",
        f"- Строк, отмеченных для ручной проверки: {review_count}",
        "",
        "| Год | Раздел | Тип | Номер | Страница | Статья | Страница оглавления | Проверка |",
        "|---:|---|---|---:|---:|---|---|---|",
    ]
    for record in records:
        if record.kind == "section":
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    str(record.year),
                    markdown_escape(record.section),
                    record.kind,
                    record.issue,
                    record.page,
                    markdown_escape(record.entry),
                    record.annual_contents_page,
                    record.needs_review,
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_raw_markdown(records: list[Record], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Сырые OCR-строки для годовых оглавлений Радио",
        "",
    ]
    current = None
    for record in records:
        key = (record.year, record.annual_contents_page, record.column)
        if key != current:
            current = key
            lines.extend(["", f"## {record.annual_contents_page}, column {record.column}", ""])
        lines.append(f"- `{record.kind}` [{record.section or 'no section'}] {record.raw_text}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ocr-root", type=Path, default=Path(".tmp/annual_contents_1999_2000/column_ocr_wide"))
    parser.add_argument("--out-dir", type=Path, default=Path("study/radio_ru_annual_contents"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records: list[Record] = []
    for year in sorted(DEFAULT_PAGES):
        state = ParseState(year=year)
        for page_name in DEFAULT_PAGES[year]:
            source = find_ocr_file(args.ocr_root, page_name)
            records.extend(parse_text_file(year, page_name, source, state))

    write_csv(records, args.out_dir / "radio_annual_contents_1999_2000.csv")
    write_markdown(records, args.out_dir / "radio_annual_contents_1999_2000.md")
    write_raw_markdown(records, args.out_dir / "radio_annual_contents_1999_2000_raw_ocr.md")
    print(f"Wrote {len(records)} records to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
