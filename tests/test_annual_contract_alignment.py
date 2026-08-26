from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def _load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def _load_contract_module():
    path = ROOT / "src" / "gold" / "contract.py"
    assert path.exists(), "src/gold/contract.py harus menjadi kontrak Gold kanonik"
    spec = importlib.util.spec_from_file_location("gold_contract", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_canonical_contract_defines_annual_gold_and_final_dashboard_metrics():
    contract = _load_contract_module()

    assert "periode" not in contract.FACT_COLUMNS
    assert "dataset_session_id" in contract.FACT_COLUMNS
    assert contract.DASHBOARD_FILTERS == ("tahun", "prodi", "iku", "kegiatan", "akun")
    assert [metric["label"] for metric in contract.GOLD_METRICS] == [
        "Total Anggaran",
        "Jumlah Item",
        "Jumlah IKU",
        "Jumlah Kegiatan",
        "Status Rekonsiliasi",
    ]
    assert contract.GOLD_SQL_TYPES["created_at"] == "TIMESTAMPTZ"


def test_fact_anggaran_drops_source_period_and_keeps_dataset_identity():
    from src.gold.fact_anggaran import build_fact_anggaran

    silver = pd.DataFrame(
        [
            {
                "item_id": "item-1",
                "dataset_session_id": "dataset-1",
                "run_id": "run-1",
                "tahun": "2023",
                "periode": "Jan-Jun",
                "prodi": "Sains Data",
                "kegiatan": "Kegiatan A",
                "akun": "Belanja Bahan",
                "jumlah": 100,
                "iku": "IKU-1; IKU-2",
                "source_file": "rab.xlsx",
                "source_sheet": "RAB",
                "source_row": 2,
                "source_role": "main_rab",
                "row_type": "leaf_item",
                "include_in_gold": True,
            }
        ]
    )

    fact = build_fact_anggaran(silver)

    assert "periode" not in fact.columns
    assert fact["dataset_session_id"].tolist() == ["dataset-1", "dataset-1"]
    assert fact["allocation_weight"].sum() == 1
    assert fact["jumlah_weighted_iku"].sum() == 100


def test_reconciliation_view_aggregates_multi_iku_at_item_grain():
    from src.transformations.excel_lakehouse_pipeline import _build_reconciliation_view

    fact = pd.DataFrame(
        [
            {
                "item_id": "item-1",
                "dataset_session_id": "dataset-1",
                "run_id": "run-1",
                "tahun": "2023",
                "source_file": "rab.xlsx",
                "jumlah": 100.0,
                "allocation_weight": 0.5,
                "jumlah_weighted_iku": 50.0,
            },
            {
                "item_id": "item-1",
                "dataset_session_id": "dataset-1",
                "run_id": "run-1",
                "tahun": "2023",
                "source_file": "rab.xlsx",
                "jumlah": 100.0,
                "allocation_weight": 0.5,
                "jumlah_weighted_iku": 50.0,
            },
        ]
    )

    result = _build_reconciliation_view(fact)

    assert result.loc[0, "total_detail"] == 100.0
    assert result.loc[0, "total_rekap"] == 100.0
    assert result.loc[0, "status"] == "OK"


def test_superset_assets_use_annual_filters_final_metrics_and_thirteen_charts():
    dataset = _load_json("superset_assets/dataset_definition.json")
    charts = _load_json("superset_assets/charts_definition.json")
    contract = _load_contract_module()

    assert dataset["columns"] == contract.FACT_COLUMNS
    assert "periode" not in dataset["columns"]
    assert [metric["label"] for metric in dataset["metrics"]] == [
        "Total Anggaran",
        "Jumlah Item",
        "Jumlah IKU",
        "Jumlah Kegiatan",
        "Status Rekonsiliasi",
    ]
    assert len(charts["charts"]) == 13
    assert [chart["key"] for chart in charts["charts"]] == [
        "kpi_total_anggaran",
        "kpi_jumlah_item",
        "kpi_jumlah_iku",
        "kpi_jumlah_kegiatan",
        "kpi_status_rekonsiliasi",
        "ringkasan_per_tahun",
        "anggaran_per_tahun",
        "anggaran_per_iku",
        "cluster_kegiatan",
        "komposisi_akun",
        "anggaran_per_akun",
        "detail_item_biaya",
        "validasi_rekap",
    ]
    assert all("periode" not in json.dumps(chart) for chart in charts["charts"])
    assert all("Total Weighted IKU" not in json.dumps(chart) for chart in charts["charts"])


def test_superset_runtime_exposes_single_registry_and_five_filters():
    import src.sql.setup_superset_excel_assets as assets

    assert assets.CHART_SPECS == [
        "kpi_total_anggaran",
        "kpi_jumlah_item",
        "kpi_jumlah_iku",
        "kpi_jumlah_kegiatan",
        "kpi_status_rekonsiliasi",
        "ringkasan_per_tahun",
        "anggaran_per_tahun",
        "anggaran_per_iku",
        "cluster_kegiatan",
        "komposisi_akun",
        "anggaran_per_akun",
        "detail_item_biaya",
        "validasi_rekap",
    ]
    assert assets.DASHBOARD_FILTERS == ("tahun", "prodi", "iku", "kegiatan", "akun")
    assert "periode" not in assets.COLUMN_LABELS
    assert "Total Weighted IKU" not in assets.COLUMN_LABELS.values()
    assert list(assets.CHART_REGISTRY) == assets.CHART_SPECS
    status_payload = assets._registry_chart_payload("kpi_status_rekonsiliasi", 10, 20)
    assert status_payload["datasource_id"] == 20
    assert '"status"' in status_payload["params"]

    detail_payload = assets._registry_chart_payload("detail_item_biaya", 10, 20)
    validation_payload = assets._registry_chart_payload("validasi_rekap", 10, 20)
    assert detail_payload["slice_name"] == "Detail Item Biaya"
    assert validation_payload["slice_name"] == "Validasi Rekap"
    assert not detail_payload["slice_name"].startswith("SILARAS |")
    assert not validation_payload["slice_name"].startswith("SILARAS |")


def test_superset_runtime_removes_dataset_columns_outside_canonical_contract():
    source = (ROOT / "src" / "sql" / "setup_superset_excel_assets.py").read_text(encoding="utf-8")

    assert "def _remove_stale_dataset_columns" in source
    assert "FACT_COLUMNS" in source
    assert "/column/{column_id}" in source


def test_superset_runtime_uses_database_for_create_and_database_id_for_update():
    source = (ROOT / "src" / "sql" / "setup_superset_excel_assets.py").read_text(encoding="utf-8")

    assert '"database": database_id' in source
    assert '"database_id": database_id' in source


def test_superset_runtime_adopts_legacy_managed_chart_markers():
    source = (ROOT / "src" / "sql" / "setup_superset_excel_assets.py").read_text(encoding="utf-8")

    assert "LEGACY_MANAGED_CHART_MARKER" in source
    assert "silaras-managed:" in source
    assert "/api/v1/chart/{candidate['id']}" in source


def test_superset_runtime_requests_all_registry_items():
    source = (ROOT / "src" / "sql" / "setup_superset_excel_assets.py").read_text(encoding="utf-8")

    assert "q=(page:0,page_size:500)" in source


def test_sql_loader_and_ddl_use_the_canonical_gold_schema():
    contract = _load_contract_module()
    ddl = (ROOT / "src" / "sql" / "create_gold_tables.sql").read_text(encoding="utf-8")
    loader_source = (ROOT / "src" / "sql" / "load_gold_to_postgres.py").read_text(encoding="utf-8")

    fact_block = ddl.split("CREATE TABLE IF NOT EXISTS gold.fact_anggaran", 1)[1].split(");", 1)[0]
    assert "periode" not in fact_block
    assert "created_at TIMESTAMPTZ" in fact_block
    assert "pipeline_run_id" not in fact_block
    assert "FACT_COLUMNS" in loader_source
    assert all(column in fact_block for column in contract.FACT_COLUMNS)


def test_local_dashboard_source_has_no_legacy_piutang_domain():
    source = (ROOT / "portal_backend" / "services" / "local_dashboard.py").read_text(encoding="utf-8")
    frontend = (ROOT / "portal" / "local-dashboard" / "app.js").read_text(encoding="utf-8")
    forbidden = (
        "nominal_piutang_rp",
        "tahun_akademik",
        "nama_debitur",
        "vw_dashboard_piutang_ukt",
        "nim",
        "kualitas piutang",
    )
    for value in forbidden:
        assert value not in source
        assert value not in frontend


def test_current_docs_describe_annual_dashboard_contract():
    dashboard_spec = (ROOT / "superset_assets" / "dashboard_spec.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs" / "AI-CODEBASE-GUIDE.md").read_text(encoding="utf-8")

    assert "periode" not in dashboard_spec.lower()
    assert "13 chart" in dashboard_spec.lower()
    assert "laporan tahunan" in architecture.lower()
    assert "periode" not in guide.lower().split("### gold dan grain", 1)[1].split("### identitas output", 1)[0]


def test_trino_validation_uses_weighted_annual_metric_only():
    sql = (ROOT / "src" / "sql" / "trino_validation_queries.sql").read_text(encoding="utf-8")

    assert "SUM(jumlah) AS total_anggaran" not in sql
    assert "SUM(jumlah_weighted_iku) AS total_anggaran" in sql
    assert "COUNT(DISTINCT item_id) AS jumlah_item" in sql
