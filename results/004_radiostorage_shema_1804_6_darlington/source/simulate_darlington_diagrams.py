from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
VARIANTS_DIR = Path(__file__).resolve().parents[1] / "variants"
sys.path.insert(0, str(VARIANTS_DIR))

from darlington import run  # noqa: E402


if __name__ == "__main__":
    run()
