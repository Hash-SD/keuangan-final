from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import OUTPUTS_DIR
from src.common.runtime_config import get_runtime_config


def main() -> None:
    config = get_runtime_config()
    source_arrival = config.source_event
    gold_ready = datetime.now(timezone.utc)
    write_json(
        OUTPUTS_DIR / "metrics" / "pipeline_latency.json",
        {
            "batch_id": config.batch_id,
            "source_arrival": source_arrival.isoformat(),
            "gold_ready": gold_ready.isoformat(),
            "latency_seconds": int((gold_ready - source_arrival).total_seconds()),
        },
    )


if __name__ == "__main__":
    main()
