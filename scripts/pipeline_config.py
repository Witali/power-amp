#!/usr/bin/env python3
"""Shared project pipeline configuration helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PARALLELISM_PATH = PROJECT_ROOT / "config" / "pipeline_parallelism.json"
DEFAULT_PIPELINE_PARALLELISM = {
    "max_parallel_opencv_tasks": 1,
    "max_parallel_ocr_tasks": 1,
    "tesseract_threads_per_process": 1,
}


def _positive_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def load_pipeline_parallelism(path: Path = PIPELINE_PARALLELISM_PATH) -> dict[str, int]:
    values = dict(DEFAULT_PIPELINE_PARALLELISM)
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Pipeline parallelism config must be a JSON object: {path}")
        for key, fallback in DEFAULT_PIPELINE_PARALLELISM.items():
            values[key] = _positive_int(raw.get(key), fallback)
    return values


def parallelism_value(key: str, path: Path = PIPELINE_PARALLELISM_PATH) -> int:
    values = load_pipeline_parallelism(path)
    if key not in values:
        raise KeyError(key)
    return values[key]
