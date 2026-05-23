#!/usr/bin/env python3
"""Add locally installed project Python packages to ``sys.path``."""

from __future__ import annotations

import sys
from pathlib import Path


def candidate_package_dirs(project_root: Path | None = None) -> list[Path]:
    if project_root is None:
        project_root = Path(__file__).resolve().parents[1]

    root = project_root / "local_tools" / "python_packages"
    versioned = root / f"py{sys.version_info.major}{sys.version_info.minor}"
    return [versioned, root]


def add_local_python_packages(project_root: Path | None = None) -> None:
    paths = [path for path in candidate_package_dirs(project_root) if path.exists()]
    for path in reversed(paths):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
