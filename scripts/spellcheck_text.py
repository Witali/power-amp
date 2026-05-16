from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALLOWLIST = PROJECT_ROOT / "ocr_tools" / "radio_ru_user_words.txt"
DEFAULT_SUFFIXES = (".txt", ".md")
SKIP_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "local_tools",
    "node_modules",
}

WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9][A-Za-zА-Яа-яЁё0-9'’.-]*")
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
LATIN_RE = re.compile(r"[A-Za-z]")
DIGIT_RE = re.compile(r"\d")
PART_CODE_RE = re.compile(
    r"^(?:[rvctdq][a-z]?\d+[a-z]?|[a-z]{1,4}\d+[a-z]?|[кk][тt]\d+[a-zа-я]?|"
    r"[кk][трдспн]\d[\da-zа-я-]*|[кk]\d{2,3}-\d+[a-zа-я]?|[a-zа-я]{1,4}-?\d[\da-zа-я-]*)$",
    re.IGNORECASE,
)
PAGE_REF_RE = re.compile(r"^\d+\.?[сc](?:\.?\d+)?$", re.IGNORECASE)
LEADER_TAIL_RE = re.compile(r"[.-]{2,}\d*$")


@dataclass(frozen=True)
class Issue:
    path: Path
    line: int
    column: int
    word: str
    reason: str


@dataclass(frozen=True)
class Occurrence:
    path: Path
    line: int
    column: int
    word: str


def normalize_word(word: str) -> str:
    return word.casefold().replace("ё", "е")


def clean_word(word: str) -> str:
    clean = word.strip("'’.-")
    clean = LEADER_TAIL_RE.sub("", clean)
    return clean.strip("'’.-")


def has_cyrillic(word: str) -> bool:
    return CYRILLIC_RE.search(word) is not None


def has_latin(word: str) -> bool:
    return LATIN_RE.search(word) is not None


def load_allowlist(paths: list[Path]) -> set[str]:
    words: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        for line_text in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            clean = line_text.strip()
            if clean and not clean.startswith("#"):
                words.add(normalize_word(clean))
    return words


def is_ignored_word(word: str, allowlist: set[str]) -> bool:
    clean = clean_word(word)
    normalized = normalize_word(clean)
    if not clean or normalized in allowlist:
        return True
    if len(clean) <= 1:
        return True
    if PART_CODE_RE.match(clean):
        return True
    if PAGE_REF_RE.match(clean):
        return True
    if clean.replace(".", "", 1).isdigit():
        return True
    if has_latin(clean) and not has_cyrillic(clean):
        return True
    return False


def heuristic_reason(word: str, allowlist: set[str]) -> str | None:
    clean = clean_word(word)
    if is_ignored_word(clean, allowlist):
        return None
    if has_cyrillic(clean) and has_latin(clean):
        return "mixed Cyrillic/Latin letters"
    if has_cyrillic(clean) and DIGIT_RE.search(clean) and not PART_CODE_RE.match(clean):
        return "digit inside Cyrillic word"
    if has_cyrillic(clean) and len(clean) > 35:
        return "very long Cyrillic token, possible column merge"
    return None


def collect_text_files(paths: list[Path], suffixes: tuple[str, ...] = DEFAULT_SUFFIXES) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix.lower() in suffixes:
            files.append(path)
        elif path.is_dir():
            files.extend(iter_text_files(path, suffixes))
    return sorted(set(files))


def iter_text_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for child in root.iterdir():
        if child.name in SKIP_DIRS:
            continue
        if child.is_dir():
            files.extend(iter_text_files(child, suffixes))
        elif child.is_file() and child.suffix.lower() in suffixes:
            files.append(child)
    return files


def scan_file(path: Path, allowlist: set[str]) -> tuple[list[Issue], dict[str, list[Occurrence]]]:
    issues: list[Issue] = []
    candidates: dict[str, list[Occurrence]] = {}
    for line_number, line_text in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        for match in WORD_RE.finditer(line_text):
            word = match.group(0).strip("'’.-")
            word = clean_word(word)
            if not word:
                continue
            reason = heuristic_reason(word, allowlist)
            if reason:
                issues.append(Issue(path, line_number, match.start() + 1, word, reason))
                continue
            if is_ignored_word(word, allowlist):
                continue
            if has_cyrillic(word):
                key = normalize_word(word)
                occurrences = candidates.setdefault(key, [])
                if len(occurrences) < 20:
                    occurrences.append(Occurrence(path, line_number, match.start() + 1, word))
    return issues, candidates


def find_hunspell(executable: str | None) -> str | None:
    if executable:
        return executable
    return shutil.which("hunspell")


def run_hunspell(words: list[str], dictionary: str, executable: str) -> set[str]:
    if not words:
        return set()
    result = subprocess.run(
        [executable, "-d", dictionary, "-l"],
        input="\n".join(words) + "\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"hunspell failed with exit code {result.returncode}")
    return {normalize_word(line.strip()) for line in result.stdout.splitlines() if line.strip()}


def write_report(path: Path, issues: list[Issue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(["file", "line", "column", "word", "reason"])
        for issue in issues:
            writer.writerow(
                [
                    issue.path.as_posix(),
                    issue.line,
                    issue.column,
                    issue.word,
                    issue.reason,
                ]
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Spell-check and OCR-quality check for generated text files.")
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("_tmp_radio_ru")], help="Text files or folders.")
    parser.add_argument("--backend", choices=["auto", "hunspell", "heuristic"], default="auto")
    parser.add_argument("--hunspell", help="Path to hunspell executable. Defaults to PATH lookup.")
    parser.add_argument("--dictionary", default="ru_RU", help="Hunspell dictionary name. Default: ru_RU.")
    parser.add_argument(
        "--allowlist",
        action="append",
        type=Path,
        default=[DEFAULT_ALLOWLIST],
        help="Additional newline-separated allowed words. Can be repeated.",
    )
    parser.add_argument("--out", type=Path, help="Write TSV report to this path.")
    parser.add_argument("--max-output", type=int, default=80, help="Maximum issues printed to stdout.")
    parser.add_argument("--fail-on-issues", action="store_true", help="Exit with code 1 if issues are found.")
    return parser.parse_args()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()
    allowlist = load_allowlist(args.allowlist)
    files = collect_text_files(args.paths)
    if not files:
        print("No text files found.")
        return 0

    issues: list[Issue] = []
    candidates: dict[str, list[Occurrence]] = {}
    for path in files:
        file_issues, file_candidates = scan_file(path, allowlist)
        issues.extend(file_issues)
        for word, occurrences in file_candidates.items():
            candidates.setdefault(word, []).extend(occurrences)

    backend_used = "heuristic"
    if args.backend in {"auto", "hunspell"}:
        hunspell = find_hunspell(args.hunspell)
        if hunspell:
            backend_used = "hunspell"
            try:
                misspelled = run_hunspell(sorted(candidates), args.dictionary, hunspell)
            except RuntimeError as exc:
                if args.backend == "hunspell":
                    raise SystemExit(str(exc)) from exc
                print(f"Hunspell unavailable for this run: {exc}", file=sys.stderr)
                misspelled = set()
                backend_used = "heuristic"
            for word in sorted(misspelled):
                for occurrence in candidates.get(word, []):
                    issues.append(
                        Issue(
                            occurrence.path,
                            occurrence.line,
                            occurrence.column,
                            occurrence.word,
                            f"hunspell:{args.dictionary}",
                        )
                    )
        elif args.backend == "hunspell":
            raise SystemExit("hunspell executable not found")

    issues.sort(key=lambda issue: (issue.path.as_posix(), issue.line, issue.column, issue.reason))
    if args.out:
        write_report(args.out, issues)

    print(f"Checked {len(files)} text file(s) with {backend_used}; {len(issues)} issue(s).")
    for issue in issues[: args.max_output]:
        print(f"{issue.path}:{issue.line}:{issue.column}: {issue.word}: {issue.reason}")
    if len(issues) > args.max_output:
        print(f"... {len(issues) - args.max_output} more issue(s)")
    if args.out:
        print(f"Report: {args.out}")
    return 1 if issues and args.fail_on_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
