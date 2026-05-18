#!/usr/bin/env python3
"""Build a local regression set for OpenCV page-layout detection."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import detect_page_layout  # noqa: E402


OUTPUT_ROOT = PROJECT_ROOT / "study" / "opencv_layout_regression_pages"
SOURCES_DIR = OUTPUT_ROOT / "sources"
BASELINES_DIR = OUTPUT_ROOT / "baselines"


REGRESSION_PAGES = [
    {
        "id": "b.1997-04.018",
        "source": ".tmp/layout_candidate_pages/b.1997-04.018.jpg",
        "reason": "compact amplifier article with mostly prose and a small technical figure-like area",
    },
    {
        "id": "b.1997-12.015",
        "source": ".tmp/layout_candidate_pages/b.1997-12.015.jpg",
        "reason": "large bold title, dense multi-column Russian text, side material, and mixed scale text",
    },
    {
        "id": "b.1997-12.016",
        "source": ".tmp/layout_candidate_pages/b.1997-12.016.jpg",
        "reason": "continuation page with dense columns and non-standard text flow",
    },
    {
        "id": "b.1998-12.018",
        "source": ".tmp/layout_candidate_pages/b.1998-12.018.jpg",
        "reason": "known difficult negative/edge case for separating text from embedded figure regions",
    },
    {
        "id": "b.1999-10.014",
        "source": ".tmp/b.1999-10.014.jpg",
        "reason": "extra cached page outside the main candidate folder, useful for path and layout diversity",
    },
    {
        "id": "b.1999-10.017",
        "source": ".tmp/layout_candidate_pages/b.1999-10.017.jpg",
        "reason": "article start with title, normal prose columns, and schematic content",
    },
    {
        "id": "b.1999-10.018",
        "source": ".tmp/layout_candidate_pages/b.1999-10.018.jpg",
        "reason": "mixed page with text, visual material, and side labels",
    },
    {
        "id": "b.2000-02.036",
        "source": ".tmp/layout_candidate_pages/b.2000-02.036.jpg",
        "reason": "large schematic, stacked waveform diagram, captions, and text columns",
    },
    {
        "id": "b.2000-02.037",
        "source": ".tmp/layout_candidate_pages/b.2000-02.037.jpg",
        "reason": "large title, technical characteristics table, small schematic Fig. 4, and prose columns",
    },
    {
        "id": "b.2000-09.011",
        "source": ".tmp/layout_candidate_pages/b.2000-09.011.jpg",
        "reason": "bridge amplifier article start with dense title text and figure/table region",
    },
    {
        "id": "b.2000-09.012",
        "source": ".tmp/layout_candidate_pages/b.2000-09.012.jpg",
        "reason": "continuation with amplifier schematic material and multi-column text",
    },
    {
        "id": "b.2000-10.014",
        "source": ".tmp/layout_candidate_pages/b.2000-10.014.jpg",
        "reason": "text-heavy amplifier page with a large schematic near the bottom",
    },
    {
        "id": "b.2000-10.015",
        "source": ".tmp/layout_candidate_pages/b.2000-10.015.jpg",
        "reason": "continuation page with circuit-related visual regions and dense text",
    },
    {
        "id": "b.2000-11.011",
        "source": ".tmp/layout_candidate_pages/b.2000-11.011.jpg",
        "reason": "title page with illustration-like material, prose columns, and side labels",
    },
    {
        "id": "b.2000-11.012",
        "source": ".tmp/layout_candidate_pages/b.2000-11.012.jpg",
        "reason": "large connected schematic fragments and text; useful for schematic merge regression",
    },
    {
        "id": "b.2000-11.013",
        "source": ".tmp/layout_candidate_pages/b.2000-11.013.jpg",
        "reason": "mixed page with image/table/schematic/text and vertical margin labels",
    },
    {
        "id": "b.2000-01.042",
        "source": ".tmp/radio_ru_2000_power_pages/b.2000-01.042.jpg",
        "reason": "power-supply article page with simple stabilizer schematic and technical blocks",
    },
    {
        "id": "b.2000-01.043",
        "source": ".tmp/radio_ru_2000_power_pages/b.2000-01.043.jpg",
        "reason": "page with several small schematics/diagrams and repeated figure blocks",
    },
    {
        "id": "b.2000-11.043",
        "source": ".tmp/radio_ru_2000_power_pages/b.2000-11.043.jpg",
        "reason": "impulse stabilizer article with photo-like and schematic-like content",
    },
    {
        "id": "b.2000-11.044",
        "source": ".tmp/radio_ru_2000_power_pages/b.2000-11.044.jpg",
        "reason": "continuation with schematic block and dense technical prose",
    },
]


README_TEXT = """# OpenCV Layout Regression Pages

This folder preserves a fixed local set of processed Radio magazine pages for
layout-detector regression work.

Contents:

- `sources/` - copied source page scans. These are kept outside `.tmp` so the
  regression set survives cache cleanup.
- `baselines/` - current detector output for each page: `layout.json` and
  `preview.png`.
- `manifest.json` - selected page ids, source paths, baseline paths, and the
  reason each page is interesting.

Regenerate with:

```text
python scripts/build_layout_regression_set.py
```

The baseline intentionally stores no block crops to keep the set compact; crops
can be regenerated from the source scans when needed.
"""


def project_path(relative: str) -> Path:
    return (PROJECT_ROOT / relative).resolve()


def copy_sources() -> list[dict[str, object]]:
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    manifest_pages: list[dict[str, object]] = []
    seen: set[str] = set()
    total = len(REGRESSION_PAGES)
    for index, page in enumerate(REGRESSION_PAGES, start=1):
        page_id = str(page["id"])
        if page_id in seen:
            raise ValueError(f"Duplicate regression page id: {page_id}")
        seen.add(page_id)
        source = project_path(str(page["source"]))
        if not source.exists():
            raise FileNotFoundError(f"Missing regression source: {source}")
        target = SOURCES_DIR / f"{page_id}{source.suffix.lower()}"
        print(f"[copy {index:02d}/{total}] {page_id}: {source}", flush=True)
        shutil.copy2(source, target)
        manifest_pages.append(
            {
                "id": page_id,
                "reason": page["reason"],
                "source": target.relative_to(PROJECT_ROOT).as_posix(),
                "original_cached_source": str(page["source"]),
                "baseline_layout": (BASELINES_DIR / page_id / "layout.json").relative_to(PROJECT_ROOT).as_posix(),
                "baseline_preview": (BASELINES_DIR / page_id / "preview.png").relative_to(PROJECT_ROOT).as_posix(),
            }
        )
    return manifest_pages


def build_baselines(pages: list[dict[str, object]]) -> None:
    if BASELINES_DIR.exists():
        shutil.rmtree(BASELINES_DIR)
    BASELINES_DIR.mkdir(parents=True, exist_ok=True)
    total = len(pages)
    for index, page in enumerate(pages, start=1):
        source = PROJECT_ROOT / str(page["source"])
        print(f"[layout {index:02d}/{total}] {page['id']}: {source}", flush=True)
        detect_page_layout.detect_page_layout(
            source,
            BASELINES_DIR,
            preview_width=1100,
            frequency_hints="validate",
            save_crops=False,
        )


def write_manifest(pages: list[dict[str, object]]) -> None:
    manifest = {
        "name": "OpenCV layout regression pages",
        "page_count": len(pages),
        "detector": "scripts/detect_page_layout.py",
        "preview_width": 1100,
        "frequency_hints": "validate",
        "save_crops": False,
        "pages": pages,
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (OUTPUT_ROOT / "README.md").write_text(README_TEXT, encoding="utf-8", newline="\n")


def main() -> int:
    print(f"Building OpenCV layout regression set: {len(REGRESSION_PAGES)} page(s)", flush=True)
    pages = copy_sources()
    build_baselines(pages)
    write_manifest(pages)
    print(OUTPUT_ROOT / "manifest.json")
    print(f"Saved {len(pages)} regression page(s) in {OUTPUT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
