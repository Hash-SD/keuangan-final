from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import DATA_DIR, OUTPUTS_DIR


def main() -> None:
    summary = json.loads((DATA_DIR / "quarantine" / "logs" / "quality_gate_summary.json").read_text(encoding="utf-8"))
    write_json(OUTPUTS_DIR / "metrics" / "dropout_rate.json", summary)


if __name__ == "__main__":
    main()

