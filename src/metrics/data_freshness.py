from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import OUTPUTS_DIR


def main() -> None:
    source_event = datetime(2026, 5, 26, 10, 0, tzinfo=timezone.utc)
    dashboard_available = datetime.now(timezone.utc)
    write_json(
        OUTPUTS_DIR / "metrics" / "data_freshness.json",
        {
            "batch_id": "batch-dummy-20260526",
            "source_event": source_event.isoformat(),
            "dashboard_available": dashboard_available.isoformat(),
            "freshness_seconds": int((dashboard_available - source_event).total_seconds()),
        },
    )


if __name__ == "__main__":
    main()

