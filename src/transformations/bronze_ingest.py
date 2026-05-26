from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import DATA_DIR, RAW_DIR, ensure_parent
from src.common.time_utils import utc_now_iso


def copy_raw_to_bronze() -> dict:
    outputs = []
    for source in [*RAW_DIR.glob("pdf/*.pdf"), *RAW_DIR.glob("csv/*.csv"), *RAW_DIR.glob("excel/*.xlsx")]:
        rel = source.relative_to(RAW_DIR)
        target = DATA_DIR / "generated" / "bronze" / rel
        ensure_parent(target)
        shutil.copy2(source, target)
        outputs.append({"source_filename": source.name, "bronze_path": str(target), "ingested_at": utc_now_iso()})
    metadata = {"batch_id": "batch-dummy-20260526", "files": outputs}
    write_json(DATA_DIR / "generated" / "bronze" / "ingestion_metadata.json", metadata)
    return metadata


def main() -> None:
    print(copy_raw_to_bronze())


if __name__ == "__main__":
    main()

