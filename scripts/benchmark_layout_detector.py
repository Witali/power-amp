"""Benchmark the OpenCV page layout detector with CPU and OpenCL backends."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import detect_page_layout


def run_once(
    image_path: Path,
    out_dir: Path,
    accelerator: str,
    max_analysis_side: int,
    preview_width: int,
    frequency_hints: str,
) -> float:
    started = time.perf_counter()
    detect_page_layout.detect_page_layout(
        image_path=image_path,
        out_dir=out_dir,
        max_analysis_side=max_analysis_side,
        preview_width=preview_width,
        save_crops=False,
        accelerator=accelerator,
        frequency_hints=frequency_hints,
    )
    return time.perf_counter() - started


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path, help="Page images to benchmark.")
    parser.add_argument("--out-dir", type=Path, default=Path(".tmp/layout_benchmark"), help="Benchmark output root.")
    parser.add_argument("--iterations", type=int, default=3, help="Measured iterations per image and accelerator.")
    parser.add_argument("--warmup", type=int, default=1, help="Warm-up iterations per image and accelerator.")
    parser.add_argument("--max-analysis-side", type=int, default=1800, help="Detector analysis size.")
    parser.add_argument("--preview-width", type=int, default=900, help="Preview width generated during the benchmark.")
    parser.add_argument(
        "--frequency-hints",
        choices=detect_page_layout.FREQUENCY_HINT_CHOICES,
        default="off",
        help="Frequency-analysis mode used during the benchmark. Defaults to off for CPU/OpenCL comparison.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    accelerators = ["cpu", "opencl"]
    results: dict[str, list[float]] = {accelerator: [] for accelerator in accelerators}

    for accelerator in accelerators:
        for image_path in args.images:
            page_out = args.out_dir / accelerator
            for _ in range(max(0, args.warmup)):
                run_once(image_path, page_out, accelerator, args.max_analysis_side, args.preview_width, args.frequency_hints)
            for _ in range(max(1, args.iterations)):
                elapsed = run_once(image_path, page_out, accelerator, args.max_analysis_side, args.preview_width, args.frequency_hints)
                results[accelerator].append(elapsed)
                print(f"{accelerator}\t{image_path.name}\t{elapsed:.4f}s")

    summary = {}
    for accelerator, timings in results.items():
        summary[accelerator] = {
            "runs": len(timings),
            "total_seconds": round(sum(timings), 4),
            "mean_seconds": round(statistics.mean(timings), 4),
            "median_seconds": round(statistics.median(timings), 4),
        }

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
