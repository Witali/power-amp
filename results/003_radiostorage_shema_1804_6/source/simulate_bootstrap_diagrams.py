from __future__ import annotations

import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve()
RESULT_DIR = SCRIPT.parents[1]
PROJECT_ROOT = SCRIPT.parents[3]

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(RESULT_DIR))

from variants.bootstrap import run  # noqa: E402


if __name__ == "__main__":
    run()
