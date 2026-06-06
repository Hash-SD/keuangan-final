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
    source_event = config.source_event
    dashboard_available = datetime.now(timezone.utc)
    write_json(
        OUTPUTS_DIR / "metrics" / "data_freshness.json",
        {
            "batch_id": config.batch_id,
            "source_event": source_event.isoformat(),
            "dashboard_available": dashboard_available.isoformat(),
            "freshness_seconds": int((dashboard_available - source_event).total_seconds()),
        },
    )


if __name__ == "__main__":
    main()
