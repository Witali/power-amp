#!/usr/bin/env python3
"""Compatibility aliases for layout comparison preview thresholds."""

from __future__ import annotations

try:
    from scripts.layout_config import *  # type: ignore  # noqa: F401,F403
except ImportError:
    from layout_config import *  # type: ignore  # noqa: F401,F403
