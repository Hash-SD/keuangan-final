from __future__ import annotations

from pathlib import Path

import pandas as pd

from portal_backend.app import create_app
from portal_backend.services import local_dashboard


def _client_for(path: Path, monkeypatch):
    monkeypatch.setattr(local_dashboard, "DASHBOARD_VIEW_PATH", path)
    monkeypatch.setattr(local_dashboard, "SUPERSET_GOLD_PATH", path.parent / "missing_fact_anggaran.csv")
    monkeypatch.setattr(local_dashboard, "fetch_superset_fact_rows", lambda: (None, {"status": "not_available"}))
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _write_gold_view(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        [
            {
                "item_id": "item-001",
                "dataset_session_id": "dataset-1",
                "run_id": "run-1",
                "tahun": "2024",
                "prodi": "Sains Data",
                "fakultas": "Fakultas Sains",
                "iku": "IKU-1",
                "kode_iku": "IKU-1",
                "kegiatan": "Kegiatan A",
                "akun": "Belanja Bahan",
                "uraian_detail": "Detail A",
                "jumlah": 1000000,
                "allocation_weight": 1,
                "jumlah_weighted_iku": 1000000,
                "mapping_status": "VALID",
                "source_file": "rab-2024.xlsx",
            },
            {
                "item_id": "item-002",
                "dataset_session_id": "dataset-1",
                "run_id": "run-1",
                "tahun": "2025",
                "prodi": "Sains Data",
                "fakultas": "Fakultas Sains",
                "iku": "IKU-2",
                "kode_iku": "IKU-2",
                "kegiatan": "Kegiatan B",
                "akun": "Belanja Jasa",
                "uraian_detail": "Detail B",
                "jumlah": 2500000,
                "allocation_weight": 1,
                "jumlah_weighted_iku": 2500000,
                "mapping_status": "VALID",
                "source_file": "rab-2025.xlsx",
            },
            {
                "item_id": "item-003",
                "dataset_session_id": "dataset-1",
                "run_id": "run-1",
                "tahun": "2025",
                "prodi": "Teknik Informatika",
                "fakultas": "Fakultas Teknologi",
                "iku": "IKU-3",
                "kode_iku": "IKU-3",
                "kegiatan": "Kegiatan C",
                "akun": "Belanja Modal",
                "uraian_detail": "Detail C",
                "jumlah": 500000,
                "allocation_weight": 1,
                "jumlah_weighted_iku": 500000,
                "mapping_status": "VALID",
                "source_file": "rab-2025.xlsx",
            },
        ]
    )
    frame.to_csv(path, index=False)


def test_local_dashboard_status_without_gold(tmp_path, monkeypatch):
    client = _client_for(tmp_path / "missing.csv", monkeypatch)

    response = client.get("/api/local-dashboard/status")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "not_available"
    assert payload["source"] is None
    assert payload["data"] is None


def test_local_dashboard_falls_back_to_local_gold_fact_anggaran(tmp_path, monkeypatch):
    view_path = tmp_path / "missing_view.csv"
    fact_path = tmp_path / "data/generated/gold/fact_anggaran.csv"
    _write_gold_view(fact_path)
    monkeypatch.setattr(local_dashboard, "DASHBOARD_VIEW_PATH", view_path)
    monkeypatch.setattr(local_dashboard, "SUPERSET_GOLD_PATH", fact_path)
    monkeypatch.setattr(local_dashboard, "fetch_superset_fact_rows", lambda: (None, {"status": "unreachable"}))
    app = create_app()
    app.config["TESTING"] = True

    payload = app.test_client().get("/api/local-dashboard/all").get_json()

    assert payload["status"] == "validated"
    assert payload["source_kind"] == "gold_fact_anggaran"
    assert payload["source_dataset"] == "fact_anggaran"
    assert payload["data"]["labels"]["title"] == "Dashboard Anggaran RAB/IKU"
    assert payload["data"]["summary"]["total_anggaran"] == 4000000


def test_local_dashboard_filters(tmp_path, monkeypatch):
    path = tmp_path / "fact_anggaran.csv"
    _write_gold_view(path)
    client = _client_for(path, monkeypatch)

    payload = client.get("/api/local-dashboard/filters").get_json()

    assert payload["status"] == "validated"
    assert payload["data"]["prodi"] == ["Sains Data", "Teknik Informatika"]
    assert payload["data"]["tahun"] == ["2024", "2025"]
    assert set(payload["data"]) == {"tahun", "prodi", "iku", "kegiatan", "akun"}


def test_local_dashboard_summary(tmp_path, monkeypatch):
    path = tmp_path / "fact_anggaran.csv"
    _write_gold_view(path)
    client = _client_for(path, monkeypatch)

    payload = client.get("/api/local-dashboard/summary?prodi=Sains%20Data").get_json()

    assert payload["status"] == "validated"
    assert payload["filters"] == {"prodi": ["Sains Data"]}
    assert payload["data"]["total_anggaran"] == 3500000
    assert payload["data"]["jumlah_item"] == 2
    assert payload["data"]["status_rekonsiliasi"] == "OK"


def test_local_dashboard_charts(tmp_path, monkeypatch):
    path = tmp_path / "fact_anggaran.csv"
    _write_gold_view(path)
    client = _client_for(path, monkeypatch)

    payload = client.get("/api/local-dashboard/charts?tahun=2025").get_json()

    assert payload["status"] == "validated"
    charts = payload["data"]
    assert charts["komposisi_akun"]["filter_column"] == "akun"
    assert {item["label"] for item in charts["komposisi_akun"]["items"]} == {"Belanja Jasa", "Belanja Modal"}


def test_local_dashboard_annual_chart_is_chronological(tmp_path, monkeypatch):
    path = tmp_path / "fact_anggaran.csv"
    _write_gold_view(path)
    client = _client_for(path, monkeypatch)

    payload = client.get("/api/local-dashboard/charts").get_json()

    assert [item["label"] for item in payload["data"]["anggaran_per_tahun"]["items"]] == ["2024", "2025"]


def test_local_dashboard_table(tmp_path, monkeypatch):
    path = tmp_path / "fact_anggaran.csv"
    _write_gold_view(path)
    client = _client_for(path, monkeypatch)

    payload = client.get("/api/local-dashboard/table?akun=Belanja%20Jasa").get_json()

    assert payload["status"] == "validated"
    assert payload["data"]["total_rows"] == 1
    assert payload["data"]["rows"][0]["item_id"] == "item-002"


def test_local_dashboard_rejects_legacy_time_column(tmp_path, monkeypatch):
    path = tmp_path / "fact_anggaran.csv"
    _write_gold_view(path)
    frame = pd.read_csv(path)
    frame["periode"] = "Jan-Jun"
    frame.to_csv(path, index=False)
    client = _client_for(path, monkeypatch)

    payload = client.get("/api/local-dashboard/all").get_json()

    assert payload["status"] == "forbidden_columns"
