from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import DATA_DIR, RAW_DIR, ensure_parent
from src.common.runtime_config import configured_batch_id
from src.common.runtime_paths import active_period_metadata
from src.common.time_utils import utc_now_iso


def copy_raw_to_bronze() -> dict:
    outputs = []
    for source in [*RAW_DIR.glob("pdf/*.pdf"), *RAW_DIR.glob("csv/*.csv"), *RAW_DIR.glob("excel/*.xlsx")]:
        rel = source.relative_to(RAW_DIR)
        target = DATA_DIR / "generated" / "bronze" / rel
        ensure_parent(target)
        shutil.copyfile(source, target)
        row_count = None
        if source.suffix.lower() == ".csv":
            try:
                row_count = max(sum(1 for _ in source.open("r", encoding="utf-8")) - 1, 0)
            except OSError:
                row_count = None
        outputs.append(
            {
                "source_filename": source.name,
                "source_type": source.parent.name,
                "bronze_path": str(target),
                "row_count": row_count,
                "ingested_at": utc_now_iso(),
                "dummy_data": True,
                "contains_real_personal_data": False,
            }
        )
    metadata = {"batch_id": configured_batch_id(), **active_period_metadata(), "files": outputs}
    write_json(DATA_DIR / "generated" / "bronze" / "ingestion_metadata.json", metadata)
    return metadata


def main() -> None:
    print(copy_raw_to_bronze())


if __name__ == "__main__":
    main()
