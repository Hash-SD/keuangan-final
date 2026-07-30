"""Runs an isolated non-research Gold fixture through PostgreSQL and Superset."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REPORT = ROOT / "outputs" / "reports" / "release_fixture_smoke.json"
SESSION = "fixture-release-session"
RUN = "fixture-release-run"


def write_csv(name: str, rows: list[dict]) -> str:
    path = ROOT / "data" / "generated" / "gold" / SESSION / RUN / name
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    return str(path)


def main() -> None:
    now = datetime.now(timezone.utc).isoformat()
    fact = {
        "item_id": "fixture-item-001", "dataset_session_id": SESSION, "run_id": RUN,
        "tahun": "2099", "periode": "Tahunan", "prodi": "Fixture", "fakultas": "Fixture",
        "kegiatan": "Smoke test", "cluster_kegiatan": "Smoke test", "akun": "Belanja", "kode_akun": "000001",
        "nama_akun": "Fixture", "iku": "IKU Fixture", "kode_iku": "IKU-F", "nama_iku": "IKU Fixture",
        "nomenklatur_path": "Fixture", "uraian_detail": "Baris fixture rilis", "qty": 1,
        "satuan": "paket", "harga_satuan": 1000, "jumlah": 1000, "jumlah_weighted_iku": 1000,
        "allocation_weight": 1, "mapping_status": "mapped", "data_quality_flag": "valid",
        "source_file": "fixture.xlsx", "source_sheet": "RAB", "source_row": 2,
        "source_role": "main_rab", "row_type": "leaf_item", "quality_flags": "[]", "created_at": now,
    }
    outputs = {
        "fact_anggaran.csv": {"csv": write_csv("fact_anggaran.csv", [fact])},
        "vw_dashboard_iku_anggaran.csv": {"csv": write_csv("vw_dashboard_iku_anggaran.csv", [{key: fact[key] for key in ("dataset_session_id", "run_id", "tahun", "periode", "prodi", "fakultas", "iku")} | {"jumlah_weighted_iku": 1000}])},
        "vw_dashboard_mapping_quality.csv": {"csv": write_csv("vw_dashboard_mapping_quality.csv", [{"dataset_session_id": SESSION, "run_id": RUN, "mapping_status": "mapped", "data_quality_flag": "valid", "item_count": 1}])},
        "vw_dashboard_reconciliation.csv": {"csv": write_csv("vw_dashboard_reconciliation.csv", [{"source_file": "fixture.xlsx", "total_detail": 1000, "total_rekap": 1000, "selisih": 0, "validation_status": "validated", "dataset_session_id": SESSION}])},
        "vw_dashboard_detail_item.csv": {"csv": write_csv("vw_dashboard_detail_item.csv", [fact])},
    }
    reports = ROOT / "outputs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "active_gold_run.json").write_text(json.dumps({"status": "PUBLISHED", "dataset_session_id": SESSION, "pipeline_run_id": RUN, "outputs": outputs}), encoding="utf-8")
    (reports / "pipeline_runs" / f"{RUN}.json").parent.mkdir(parents=True, exist_ok=True)
    (reports / "pipeline_runs" / f"{RUN}.json").write_text(json.dumps({"status": "PUBLISHED", "dataset_session_id": SESSION, "pipeline_run_id": RUN, "upload_committed_at": now, "pipeline_started_at": now, "gold_finished_at": now, "fact_anggaran_rows": 1}), encoding="utf-8")
    os.environ.update({"PIPELINE_RUN_ID": RUN, "DATASET_SESSION_ID": SESSION, "POSTGRES_HOST": "localhost", "SUPERSET_BASE_URL": "http://localhost:8089", "SUPERSET_PUBLIC_URL": "http://localhost:8089"})
    from src.sql.load_gold_to_postgres import main as load_postgres
    from src.sql.setup_superset_excel_assets import main as setup_superset
    load_postgres()
    setup_superset()
    manifest = json.loads((reports / "pipeline_runs" / f"{RUN}.json").read_text(encoding="utf-8"))
    result = {"status": "PASSED" if manifest.get("dashboard_verified_at") else "FAILED", "dataset_session_id": SESSION, "pipeline_run_id": RUN, "manifest": manifest}
    REPORT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
