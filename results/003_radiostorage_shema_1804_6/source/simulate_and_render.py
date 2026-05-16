from __future__ import annotations

import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve()
RESULT_DIR = SCRIPT.parents[1]
PROJECT_ROOT = SCRIPT.parents[3]

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(RESULT_DIR))

from circuitlib.common import write_text_lf  # noqa: E402
from variants.bootstrap import SCHEMATIC, bootstrap_schematic_svg  # noqa: E402


def main() -> None:
    SCHEMATIC.mkdir(parents=True, exist_ok=True)
    write_text_lf(SCHEMATIC / "reconstructed_amplifier_bootstrap.svg", bootstrap_schematic_svg())


if __name__ == "__main__":
    main()
