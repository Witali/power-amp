#!/usr/bin/env python3
"""Run OpenCV page-layout detection and build a thumbnail HTML report."""

from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import detect_page_layout, layout_config  # noqa: E402


DEFAULT_MANIFEST = PROJECT_ROOT / "study" / "opencv_layout_regression_pages" / "manifest.json"
DEFAULT_OUT_DIR = PROJECT_ROOT / "study" / "opencv_layout_reports" / "latest"


def log_progress(stage: str, message: str) -> None:
    print(f"[report {stage}] {message}", flush=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Regression page manifest.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Report output directory.")
    parser.add_argument("--preview-width", type=int, default=0, help="Override detector preview width.")
    parser.add_argument(
        "--frequency-hints",
        choices=detect_page_layout.FREQUENCY_HINT_CHOICES,
        default="",
        help="Override detector frequency hint mode.",
    )
    parser.add_argument("--max-pages", type=int, default=0, help="Process only the first N pages.")
    return parser.parse_args(argv)


def project_path(path: Path | str) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def relative_href(target: Path, from_dir: Path) -> str:
    return os.path.relpath(target.resolve(), from_dir.resolve()).replace("\\", "/")


def safe_label(label: str) -> str:
    return "schematic" if label == "schematic/circuit" else label


def count_blocks(blocks: list[dict[str, Any]]) -> Counter[str]:
    return Counter(safe_label(str(block.get("label", "other"))) for block in blocks)


def counts_text(counts: Counter[str]) -> str:
    if not counts:
        return "no blocks"
    order = layout_config.LAYOUT_REPORT_LABEL_ORDER
    parts = [f"{label}: {counts[label]}" for label in order if counts.get(label)]
    parts.extend(f"{label}: {value}" for label, value in sorted(counts.items()) if label not in order)
    return ", ".join(parts)


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError(f"Manifest has no pages: {path}")
    return manifest


def run_detector(manifest: dict[str, Any], out_dir: Path, max_pages: int) -> list[dict[str, Any]]:
    log_progress("2/5", "checking OpenCV detector dependencies")
    detect_page_layout.require_dependencies()
    layout_dir = out_dir / "detected"
    if layout_dir.exists():
        log_progress("2/5", f"removing previous detected layouts: {layout_dir}")
        shutil.rmtree(layout_dir)
    layout_dir.mkdir(parents=True, exist_ok=True)

    preview_width = int(manifest.get("preview_width", layout_config.LAYOUT_REPORT_DEFAULT_PREVIEW_WIDTH))
    frequency_hints = str(manifest.get("frequency_hints", layout_config.LAYOUT_REPORT_DEFAULT_FREQUENCY_HINT_MODE))
    pages = list(manifest["pages"])
    if max_pages > 0:
        pages = pages[:max_pages]

    entries: list[dict[str, Any]] = []
    total = len(pages)
    log_progress(
        "2/5",
        f"detecting {total} page(s), preview_width={preview_width}, frequency_hints={frequency_hints}",
    )
    for index, page in enumerate(pages, start=1):
        page_id = str(page["id"])
        source = project_path(str(page["source"]))
        print(f"[layout {index:02d}/{total}] start {page_id}: {source}", flush=True)
        if not source.exists():
            raise FileNotFoundError(f"Missing source page: {source}")

        result = detect_page_layout.detect_page_layout(
            source,
            layout_dir,
            preview_width=preview_width,
            frequency_hints=frequency_hints,
            save_crops=False,
        )
        page_dir = layout_dir / source.stem
        layout_path = page_dir / "layout.json"
        preview_path = page_dir / result["preview"]
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
        blocks = list(layout.get("blocks", []))
        counts = count_blocks(blocks)
        warning_count = len(layout.get("frequency_warnings", [])) + len(layout.get("frequency_cluster_warnings", []))
        entries.append(
            {
                "id": page_id,
                "reason": str(page.get("reason", "")),
                "source": source,
                "layout": layout_path,
                "preview": preview_path,
                "block_count": len(blocks),
                "counts": dict(counts),
                "counts_text": counts_text(counts),
                "warning_count": warning_count,
            }
        )
        print(
            f"[layout {index:02d}/{total}] done {page_id}: "
            f"{len(blocks)} block(s), {counts_text(counts)}, warnings={warning_count}",
            flush=True,
        )
    return entries


def report_notes(entries: list[dict[str, Any]]) -> list[str]:
    notes: list[str] = []
    if not entries:
        return ["No pages were processed."]
    high_other = [entry["id"] for entry in entries if int(entry["counts"].get("other", 0)) >= 2]
    warning_pages = [entry["id"] for entry in entries if int(entry["warning_count"]) > 0]
    no_visuals = [
        entry["id"]
        for entry in entries
        if not any(int(entry["counts"].get(label, 0)) for label in layout_config.LAYOUT_REPORT_VISUAL_LABELS)
    ]
    notes.append(f"Processed {len(entries)} page(s).")
    if high_other:
        notes.append("Manual review suggested for pages with several 'other' blocks: " + ", ".join(high_other) + ".")
    if warning_pages:
        notes.append("Frequency validation warnings are present on: " + ", ".join(warning_pages) + ".")
    if no_visuals:
        notes.append("No visual blocks were detected on: " + ", ".join(no_visuals) + ".")
    if len(notes) == 1:
        notes.append("No automatic red flags were found; visual review is still recommended.")
    return notes


def write_html(out_dir: Path, manifest: dict[str, Any], entries: list[dict[str, Any]]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_counts: Counter[str] = Counter()
    for entry in entries:
        summary_counts.update({str(label): int(value) for label, value in entry["counts"].items()})

    rows: list[str] = []
    for entry in entries:
        source_href = html.escape(relative_href(Path(entry["source"]), out_dir))
        preview_href = html.escape(relative_href(Path(entry["preview"]), out_dir))
        layout_href = html.escape(relative_href(Path(entry["layout"]), out_dir))
        page_id = html.escape(str(entry["id"]))
        reason = html.escape(str(entry["reason"]))
        counts = html.escape(str(entry["counts_text"]))
        warnings = int(entry["warning_count"])
        warning_text = f" | warnings: {warnings}" if warnings else ""
        rows.append(
            f"""
    <section class="page-card">
      <header>
        <h2>{page_id}</h2>
        <p>{reason}</p>
        <p class="meta">blocks: {int(entry["block_count"])} | {counts}{html.escape(warning_text)} | <a href="{layout_href}">layout.json</a></p>
      </header>
      <div class="pair">
        <figure>
          <a href="{source_href}" target="_blank"><img src="{source_href}" alt="{page_id} original"></a>
          <figcaption>Original scan</figcaption>
        </figure>
        <figure>
          <a href="{preview_href}" target="_blank"><img src="{preview_href}" alt="{page_id} OpenCV markup"></a>
          <figcaption>OpenCV markup</figcaption>
        </figure>
      </div>
    </section>"""
        )

    notes_html = "\n".join(f"        <li>{html.escape(note)}</li>" for note in report_notes(entries))
    body = "\n".join(rows)
    title = "OpenCV layout regression report"
    index = out_dir / "index.html"
    index.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17202a;
      --muted: #5e6875;
      --line: #d6dbe1;
      --panel: #f7f9fb;
      --accent: #1f6feb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font: 15px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: #ffffff;
    }}
    main {{
      width: min(1280px, calc(100% - 32px));
      margin: 28px auto 48px;
    }}
    h1 {{ margin: 0 0 6px; font-size: 28px; }}
    h2 {{ margin: 0; font-size: 18px; }}
    p {{ margin: 6px 0; }}
    a {{ color: var(--accent); }}
    .summary {{
      padding: 14px 16px;
      margin: 18px 0 22px;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
    }}
    .summary ul {{ margin: 8px 0 0 18px; padding: 0; }}
    .page-card {{
      padding: 16px 0 24px;
      border-top: 1px solid var(--line);
    }}
    .meta {{ color: var(--muted); font-size: 13px; }}
    .pair {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 14px;
      align-items: start;
      margin-top: 10px;
    }}
    figure {{ margin: 0; }}
    img {{
      display: block;
      width: 100%;
      max-height: 420px;
      object-fit: contain;
      border: 1px solid var(--line);
      background: #fff;
    }}
    figcaption {{
      margin-top: 5px;
      color: var(--muted);
      font-size: 13px;
    }}
    @media (max-width: 760px) {{
      .pair {{ grid-template-columns: 1fr; }}
      main {{ width: min(100% - 20px, 1280px); }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>{title}</h1>
    <p class="meta">Manifest: {html.escape(str(manifest.get("name", "unknown")))} | pages: {len(entries)} | total blocks: {sum(summary_counts.values())} | {html.escape(counts_text(summary_counts))}</p>
    <section class="summary">
      <strong>Automatic notes</strong>
      <ul>
{notes_html}
      </ul>
    </section>
{body}
  </main>
</body>
</html>
""",
        encoding="utf-8",
        newline="\n",
    )
    return index


def write_summary(out_dir: Path, entries: list[dict[str, Any]]) -> Path:
    summary_path = out_dir / "summary.json"
    serializable = []
    for entry in entries:
        serializable.append(
            {
                "id": entry["id"],
                "reason": entry["reason"],
                "source": relative_href(Path(entry["source"]), out_dir),
                "layout": relative_href(Path(entry["layout"]), out_dir),
                "preview": relative_href(Path(entry["preview"]), out_dir),
                "block_count": entry["block_count"],
                "counts": entry["counts"],
                "warning_count": entry["warning_count"],
            }
        )
    summary_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return summary_path


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    manifest_path = project_path(args.manifest)
    out_dir = project_path(args.out_dir)
    log_progress("1/5", f"loading manifest: {manifest_path}")
    manifest = load_manifest(manifest_path)
    if args.preview_width > 0:
        manifest["preview_width"] = args.preview_width
    if args.frequency_hints:
        manifest["frequency_hints"] = args.frequency_hints

    log_progress("2/5", f"building page layouts into: {out_dir}")
    entries = run_detector(manifest, out_dir, args.max_pages)
    log_progress("3/5", f"writing HTML report for {len(entries)} page(s)")
    index = write_html(out_dir, manifest, entries)
    log_progress("4/5", "writing JSON summary")
    summary = write_summary(out_dir, entries)
    log_progress("5/5", "done")
    print(index)
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
