#!/usr/bin/env python3
"""Rebuild annual contents OCR text from Tesseract TSV word coordinates."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import extract_radio_ru_annual_contents as annual_contents

DEFAULT_TESSERACT = PROJECT_ROOT / "local_tools" / "Tesseract-extracted" / "tesseract.exe"
DEFAULT_TESSDATA = PROJECT_ROOT / "local_tools" / "Tesseract-extracted" / "tessdata"
DIGITLIKE_TRANSLATION = str.maketrans(
    {
        "O": "0",
        "o": "0",
        "О": "0",
        "о": "0",
        "З": "3",
        "з": "3",
        "S": "5",
        "$": "5",
        "Б": "6",
        "б": "6",
        "В": "8",
        "B": "8",
        "I": "1",
        "l": "1",
        "|": "1",
    }
)


@dataclass(frozen=True)
class Word:
    text: str
    left: int
    top: int
    width: int
    height: int
    conf: float
    block_num: int
    par_num: int
    line_num: int
    word_num: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def center_x(self) -> float:
        return self.left + self.width / 2.0


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def column_number(path: Path) -> int:
    match = re.search(r"column(\d+)", path.stem)
    return int(match.group(1)) if match else 0


def run_tesseract_tsv(
    image_path: Path,
    out_base: Path,
    tesseract: Path,
    tessdata_dir: Path,
    psm: int,
    languages: str,
    refresh: bool,
) -> Path:
    tsv_path = Path(str(out_base) + ".tsv")
    if tsv_path.exists() and not refresh:
        return tsv_path
    out_base.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(tesseract),
        str(image_path),
        str(out_base),
        "-l",
        languages,
        "--psm",
        str(psm),
        "--tessdata-dir",
        str(tessdata_dir),
        "tsv",
    ]
    subprocess.run(command, check=True, cwd=PROJECT_ROOT)
    return tsv_path


def parse_tsv_words(tsv_path: Path) -> list[Word]:
    words: list[Word] = []
    with tsv_path.open("r", encoding="utf-8", errors="replace") as handle:
        header = handle.readline().rstrip("\n").split("\t")
        index = {name: position for position, name in enumerate(header)}
        for raw_line in handle:
            cells = raw_line.rstrip("\n").split("\t")
            if len(cells) < len(header):
                continue
            if cells[index["level"]] != "5":
                continue
            text = "\t".join(cells[index["text"] :]).strip()
            if not text:
                continue
            words.append(
                Word(
                    text=text,
                    left=int(cells[index["left"]]),
                    top=int(cells[index["top"]]),
                    width=int(cells[index["width"]]),
                    height=int(cells[index["height"]]),
                    conf=float(cells[index["conf"]] or -1),
                    block_num=int(cells[index["block_num"]]),
                    par_num=int(cells[index["par_num"]]),
                    line_num=int(cells[index["line_num"]]),
                    word_num=int(cells[index["word_num"]]),
                )
            )
    return words


def grouped_lines(words: list[Word]) -> list[list[Word]]:
    groups: dict[tuple[int, int, int], list[Word]] = {}
    for word in words:
        key = (word.block_num, word.par_num, word.line_num)
        groups.setdefault(key, []).append(word)
    return [
        sorted(line_words, key=lambda word: (word.left, word.word_num))
        for _, line_words in sorted(
            groups.items(),
            key=lambda item: (
                min(word.top for word in item[1]),
                item[0],
                min(word.left for word in item[1]),
            ),
        )
    ]


def looks_like_leader(text: str) -> bool:
    return bool(re.fullmatch(r"[\s._·•,\-—–=~`'\"<>:;]+", text))


def digitlike_text(text: str) -> str:
    digits = re.sub(r"\D", "", text.translate(DIGITLIKE_TRANSLATION))
    if len(digits) > 5:
        return ""
    return digits


def rebuild_numeric_tail(words: list[Word], image_width: int) -> tuple[list[Word], str]:
    candidates: list[Word] = []
    for word in reversed(words):
        near_right = word.center_x >= image_width * 0.62
        if near_right and (digitlike_text(word.text) or looks_like_leader(word.text)):
            candidates.append(word)
            continue
        if candidates:
            break
    if not candidates:
        return words, ""

    candidates.reverse()
    number_tokens = [digitlike_text(word.text) for word in candidates if digitlike_text(word.text)]
    if not number_tokens:
        return words, ""

    issue = ""
    page = ""
    if len(number_tokens) >= 2:
        issue_candidate = number_tokens[-2]
        page_candidate = number_tokens[-1]
        if issue_candidate.isdigit() and page_candidate.isdigit():
            issue_number = int(issue_candidate)
            page_number = int(page_candidate)
            if 1 <= issue_number <= 12 and 1 <= page_number <= 130:
                issue = str(issue_number)
                page = str(page_number)
    if not issue:
        parsed = annual_contents.split_attached_issue_page(number_tokens[-1])
        if parsed:
            issue, page = str(parsed[0]), str(parsed[1])

    if not issue:
        return words, ""

    candidate_ids = {id(word) for word in candidates}
    kept = [word for word in words if id(word) not in candidate_ids]
    return kept, f"{issue} {page}"


def rebuild_line(words: list[Word], image_width: int) -> str:
    words, numeric_tail = rebuild_numeric_tail(words, image_width)
    parts: list[str] = []
    for word in words:
        if looks_like_leader(word.text):
            continue
        parts.append(word.text)
    if numeric_tail:
        parts.append(numeric_tail)
    return annual_contents.normalize_line(" ".join(parts))


def rebuild_column_text(image_path: Path, tsv_path: Path) -> list[str]:
    words = parse_tsv_words(tsv_path)
    lines: list[str] = []
    width = image_width_from_tsv(tsv_path) or image_width_from_png_header(image_path)
    for line_words in grouped_lines(words):
        line = rebuild_line(line_words, width)
        if line:
            lines.append(line)
    return lines


def image_width_from_tsv(tsv_path: Path) -> int:
    with tsv_path.open("r", encoding="utf-8", errors="replace") as handle:
        header = handle.readline().rstrip("\n").split("\t")
        index = {name: position for position, name in enumerate(header)}
        for raw_line in handle:
            cells = raw_line.rstrip("\n").split("\t")
            if len(cells) >= len(header) and cells[index["level"]] == "1":
                return int(cells[index["width"]])
    return 0


def image_width_from_png_header(image_path: Path) -> int:
    data = image_path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return 0
    return int.from_bytes(data[16:20], "big")


def rebuild_page(
    page_dir: Path,
    tesseract: Path,
    tessdata_dir: Path,
    psm: int,
    languages: str,
    output_name: str,
    refresh: bool,
) -> Path:
    columns = sorted(page_dir.glob("column*.png"), key=column_number)
    if not columns:
        raise FileNotFoundError(f"No column*.png crops found in {rel(page_dir)}")

    column_texts: list[str] = []
    for image_path in columns:
        out_base = image_path.with_name(f"{image_path.stem}.prose.psm{psm}.word_boxes")
        tsv_path = run_tesseract_tsv(image_path, out_base, tesseract, tessdata_dir, psm, languages, refresh)
        lines = rebuild_column_text(image_path, tsv_path)
        column_texts.append("\n".join(lines))

    merged_path = page_dir / output_name
    merged_path.write_text("\n\n--- column ---\n\n".join(column_texts) + "\n", encoding="utf-8", newline="\n")
    return merged_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ocr-root", type=Path, default=Path(".tmp/annual_contents_1995_2000/layout_ocr"))
    parser.add_argument("--page-ranges", required=True)
    parser.add_argument("--variant", default="layout_text_blocks")
    parser.add_argument("--psm", type=int, default=6)
    parser.add_argument("--languages", default="rus+eng")
    parser.add_argument("--output-name", default="merged.prose.psm6.tsv_lines.txt")
    parser.add_argument("--tesseract", type=Path, default=DEFAULT_TESSERACT)
    parser.add_argument("--tessdata-dir", type=Path, default=DEFAULT_TESSDATA)
    parser.add_argument("--refresh", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pages = annual_contents.parse_page_ranges(args.page_ranges)
    rebuilt = 0
    for year in sorted(pages):
        for page_name in pages[year]:
            page_dir = args.ocr_root / page_name / args.variant
            merged_path = rebuild_page(
                page_dir=page_dir,
                tesseract=args.tesseract,
                tessdata_dir=args.tessdata_dir,
                psm=args.psm,
                languages=args.languages,
                output_name=args.output_name,
                refresh=args.refresh,
            )
            rebuilt += 1
            print(rel(merged_path))
    print(f"Rebuilt TSV text for {rebuilt} page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
