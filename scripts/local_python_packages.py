#!/usr/bin/env python3
"""Add locally installed project Python packages to ``sys.path``."""

from __future__ import annotations

import os
import sys
from pathlib import Path


EXPLICIT_PACKAGE_PATHS_ENV = "POWER_AMP_PYTHON_PACKAGES"
ALLOW_LEGACY_ROOT_ENV = "POWER_AMP_ALLOW_LEGACY_PYTHON_PACKAGES"


def current_python_tag() -> str:
    return f"py{sys.version_info.major}{sys.version_info.minor}"


def env_flag_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def explicit_package_dirs() -> list[Path]:
    raw = os.environ.get(EXPLICIT_PACKAGE_PATHS_ENV, "")
    if not raw.strip():
        return []
    return [Path(part) for part in raw.split(os.pathsep) if part.strip()]


def candidate_package_dirs(project_root: Path | None = None) -> list[Path]:
    explicit = explicit_package_dirs()
    if explicit:
        return explicit

    if project_root is None:
        project_root = Path(__file__).resolve().parents[1]

    root = project_root / "local_tools" / "python_packages"
    versioned = root / current_python_tag()
    candidates = [versioned]
    if env_flag_enabled(ALLOW_LEGACY_ROOT_ENV):
        candidates.append(root)
    return candidates


def add_local_python_packages(project_root: Path | None = None) -> None:
    paths = [path for path in candidate_package_dirs(project_root) if path.exists()]
    for path in reversed(paths):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
