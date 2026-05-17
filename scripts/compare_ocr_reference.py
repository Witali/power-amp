#!/usr/bin/env python3
"""Compare OCR candidates against reference text files.

The tool is intended for calibration only. Keep downloaded reference articles in
.tmp/ or another ignored directory; commit only the source URLs and metrics.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path


TOKEN_RE = re.compile(r"[0-9a-zа-яё]+", re.IGNORECASE)
CHARSET_RE = re.compile(br"charset=[\"']?([A-Za-z0-9._-]+)")


class TextExtractor(HTMLParser):
    BLOCK_TAGS = {
        "article",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "p",
        "section",
        "table",
        "td",
        "th",
        "tr",
    }
    SKIP_TAGS = {"script", "style", "noscript"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return html.unescape("".join(self.parts))


@dataclass(frozen=True)
class Score:
    reference: Path
    candidate: Path
    composite: float
    candidate_token_match: float
    sequence_ratio: float
    ngram_jaccard: float
    matched_tokens: int
    reference_tokens: int
    candidate_tokens: int
    reference_encoding: str
    candidate_encoding: str


def detect_encoding(raw: bytes) -> list[str]:
    encodings: list[str] = []
    match = CHARSET_RE.search(raw[:4096])
    if match:
        encodings.append(match.group(1).decode("ascii", errors="ignore"))
    encodings.extend(["utf-8-sig", "utf-8", "cp1251", "koi8-r"])
    unique: list[str] = []
    for encoding in encodings:
        normalized = encoding.lower()
        if normalized not in unique:
            unique.append(normalized)
    return unique


def read_text(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    last_error: UnicodeDecodeError | None = None
    for encoding in detect_encoding(raw):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError as error:
            last_error = error
    if last_error is not None:
        raise last_error
    return raw.decode("utf-8", errors="replace"), "utf-8-replace"


def html_to_text(text: str) -> str:
    parser = TextExtractor()
    parser.feed(text)
    return parser.text()


def should_strip_html(path: Path, text: str) -> bool:
    suffix = path.suffix.lower()
    return suffix in {".htm", ".html", ".shtml"} or bool(re.search(r"<html|<body|<p\b|<br\b", text, re.I))


def normalize_tokens(text: str) -> list[str]:
    text = html.unescape(text).lower().replace("ё", "е")
    return TOKEN_RE.findall(text)


def ngram_set(tokens: list[str], n: int = 5) -> set[str]:
    normalized = " ".join(tokens)
    if len(normalized) < n:
        return {normalized} if normalized else set()
    return {normalized[index : index + n] for index in range(len(normalized) - n + 1)}


def score_tokens(reference_tokens: list[str], candidate_tokens: list[str]) -> tuple[float, float, float, int]:
    if not reference_tokens or not candidate_tokens:
        return 0.0, 0.0, 0.0, 0

    matcher = SequenceMatcher(None, reference_tokens, candidate_tokens, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    candidate_match = matched / len(candidate_tokens)
    sequence_ratio = matcher.ratio()

    reference_ngrams = ngram_set(reference_tokens)
    candidate_ngrams = ngram_set(candidate_tokens)
    if reference_ngrams or candidate_ngrams:
        ngram_jaccard = len(reference_ngrams & candidate_ngrams) / len(reference_ngrams | candidate_ngrams)
    else:
        ngram_jaccard = 0.0

    return candidate_match, sequence_ratio, ngram_jaccard, matched


def load_normalized(path: Path) -> tuple[list[str], str]:
    text, encoding = read_text(path)
    if should_strip_html(path, text):
        text = html_to_text(text)
    return normalize_tokens(text), encoding


def compare(reference_paths: list[Path], candidate_paths: list[Path]) -> list[Score]:
    references = [(path, *load_normalized(path)) for path in reference_paths]
    candidates = [(path, *load_normalized(path)) for path in candidate_paths]

    scores: list[Score] = []
    for reference_path, reference_tokens, reference_encoding in references:
        for candidate_path, candidate_tokens, candidate_encoding in candidates:
            candidate_match, sequence_ratio, ngram_jaccard, matched = score_tokens(reference_tokens, candidate_tokens)
            composite = 0.70 * candidate_match + 0.20 * sequence_ratio + 0.10 * ngram_jaccard
            scores.append(
                Score(
                    reference=reference_path,
                    candidate=candidate_path,
                    composite=composite,
                    candidate_token_match=candidate_match,
                    sequence_ratio=sequence_ratio,
                    ngram_jaccard=ngram_jaccard,
                    matched_tokens=matched,
                    reference_tokens=len(reference_tokens),
                    candidate_tokens=len(candidate_tokens),
                    reference_encoding=reference_encoding,
                    candidate_encoding=candidate_encoding,
                )
            )

    return sorted(scores, key=lambda item: item.composite, reverse=True)


def collect_candidates(root: Path, pattern: str) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(path for path in root.rglob(pattern) if path.is_file())


def write_tsv(path: Path, scores: list[Score]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(
            [
                "composite",
                "candidate_token_match",
                "sequence_ratio",
                "ngram_jaccard",
                "matched_tokens",
                "candidate_tokens",
                "reference_tokens",
                "candidate",
                "reference",
                "candidate_encoding",
                "reference_encoding",
            ]
        )
        for score in scores:
            writer.writerow(
                [
                    f"{score.composite:.6f}",
                    f"{score.candidate_token_match:.6f}",
                    f"{score.sequence_ratio:.6f}",
                    f"{score.ngram_jaccard:.6f}",
                    score.matched_tokens,
                    score.candidate_tokens,
                    score.reference_tokens,
                    score.candidate.as_posix(),
                    score.reference.as_posix(),
                    score.candidate_encoding,
                    score.reference_encoding,
                ]
            )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", action="append", required=True, help="Reference text/html file. Can be repeated.")
    parser.add_argument("--candidate-root", required=True, help="OCR candidate file or directory.")
    parser.add_argument("--glob", default="merged*.txt", help="Candidate glob under candidate root.")
    parser.add_argument("--out", default="", help="Optional TSV report path.")
    parser.add_argument("--top", type=int, default=10, help="Number of top matches to print.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    reference_paths = [Path(value) for value in args.reference]
    candidate_paths = collect_candidates(Path(args.candidate_root), args.glob)

    missing = [path for path in reference_paths if not path.exists()]
    if missing:
        for path in missing:
            print(f"Missing reference: {path}", file=sys.stderr)
        return 2
    if not candidate_paths:
        print(f"No candidates found under {args.candidate_root} with glob {args.glob}", file=sys.stderr)
        return 2

    scores = compare(reference_paths, candidate_paths)
    if args.out:
        write_tsv(Path(args.out), scores)

    for score in scores[: args.top]:
        print(
            f"{score.composite:.3f}\t"
            f"candidate_match={score.candidate_token_match:.3f}\t"
            f"tokens={score.matched_tokens}/{score.candidate_tokens}\t"
            f"{score.candidate}\t{score.reference}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
