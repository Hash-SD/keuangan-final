from __future__ import annotations

import pandas as pd

from portal_backend.app import create_app
from portal_backend.services import local_dashboard
from portal_backend.services import superset_api


def _superset_fact_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "item_id": "superset-item-1",
                "tahun": "2025",
                "periode": "Tahunan",
                "prodi": "Sains Data",
                "fakultas": "Fakultas Sains",
                "kegiatan": "Kuliah Lapangan",
                "akun": "Perjalanan Dinas",
                "iku": "IK 6.7",
                "jumlah": 1_000_000,
                "jumlah_weighted_iku": 750_000,
                "mapping_status": "mapped",
                "data_quality_flag": "validated",
                "uraian_detail": "Biaya transportasi",
            }
        ]
    )


def test_local_dashboard_prefers_superset_api_when_gold_view_missing(monkeypatch):
    monkeypatch.setattr(local_dashboard, "DASHBOARD_VIEW_PATH", local_dashboard.ROOT_DIR / "missing_vw_dashboard_piutang_ukt.csv")
    monkeypatch.setattr(local_dashboard, "DASHBOARD_VIEW_RELATIVE", "missing_vw_dashboard_piutang_ukt.csv")
    monkeypatch.setattr(local_dashboard, "SUPERSET_GOLD_PATH", local_dashboard.ROOT_DIR / "missing_fact_anggaran.csv")
    monkeypatch.setattr(
        local_dashboard,
        "fetch_superset_fact_rows",
        lambda *args, **kwargs: (_superset_fact_frame(), {"status": "ready", "superset_reference": {"dataset_id": 2}}),
    )

    payload = local_dashboard.build_dashboard_response(section="all")

    assert payload["status"] == "validated"
    assert payload["source_kind"] == "superset_api"
    assert payload["source"] == "superset_api:/api/v1/chart/data"
    assert payload["data"]["summary"]["total_nominal_piutang_rp"] == 750_000
    assert payload["superset_reference"]["dataset_id"] == 2


def test_superset_chart_data_endpoint_returns_proxy_rows(monkeypatch):
    monkeypatch.setattr(
        "portal_backend.app.fetch_superset_fact_rows",
        lambda *args, **kwargs: (_superset_fact_frame(), {"status": "ready", "source_kind": "superset_api", "source_dataset": "fact_anggaran"}),
    )
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.get("/api/superset/chart-data?limit=5")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["source_kind"] == "superset_api"
    assert payload["source_dataset"] == "fact_anggaran"
    assert payload["row_count"] == 1
    assert payload["data"][0]["item_id"] == "superset-item-1"


def test_superset_base_url_uses_compose_host_and_port(monkeypatch):
    monkeypatch.delenv("SUPERSET_BASE_URL", raising=False)
    monkeypatch.setenv("SUPERSET_HOST", "superset")
    monkeypatch.setenv("SUPERSET_PORT", "8088")

    assert superset_api._base_url() == "http://superset:8088"
