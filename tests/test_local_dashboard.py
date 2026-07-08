from __future__ import annotations

from pathlib import Path

import pandas as pd

from portal_backend.app import create_app
from portal_backend.services import local_dashboard


def _client_for(path: Path, monkeypatch):
    monkeypatch.setattr(local_dashboard, "DASHBOARD_VIEW_PATH", path)
    monkeypatch.setattr(local_dashboard, "SUPERSET_GOLD_PATH", path.parent / "missing_fact_anggaran.csv")
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _write_gold_view(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        [
            {
                "tahun_akademik": "2023/2024",
                "tahun_anggaran": "2024",
                "semester": "Ganjil",
                "nama_prodi": "Sains Data",
                "nama_fakultas": "Fakultas Sains",
                "kualitas": "Lancar",
                "nominal_piutang_rp": 1000000,
                "jumlah_mhs_penunggak": 1,
                "nim": "120450001",
                "nama_debitur": "Debitur A",
            },
            {
                "tahun_akademik": "2024/2025",
                "tahun_anggaran": "2025",
                "semester": "Genap",
                "nama_prodi": "Sains Data",
                "nama_fakultas": "Fakultas Sains",
                "kualitas": "Macet",
                "nominal_piutang_rp": 2500000,
                "jumlah_mhs_penunggak": 1,
                "nim": "120450002",
                "nama_debitur": "Debitur B",
            },
            {
                "tahun_akademik": "2024/2025",
                "tahun_anggaran": "2025",
                "semester": "Genap",
                "nama_prodi": "Teknik Informatika",
                "nama_fakultas": "Fakultas Teknologi",
                "kualitas": "Diragukan",
                "nominal_piutang_rp": 500000,
                "jumlah_mhs_penunggak": 1,
                "nim": "120450003",
                "nama_debitur": "Debitur C",
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


def test_local_dashboard_falls_back_to_superset_gold_fact_anggaran(tmp_path, monkeypatch):
    piutang_path = tmp_path / "data/generated/gold/vw_dashboard_piutang_ukt.csv"
    fact_path = tmp_path / "data/generated/gold/fact_anggaran.csv"
    fact_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "tahun": 2025,
                "periode": "Tahunan",
                "prodi": "Sains Data",
                "fakultas": "Fakultas Sains",
                "item_id": "item-1",
                "kegiatan": "Kuliah Lapangan",
                "jumlah": 1000000,
                "jumlah_weighted_iku": 750000,
                "data_quality_flag": "VALIDATED",
            }
        ]
    ).to_csv(fact_path, index=False)
    monkeypatch.setattr(local_dashboard, "DASHBOARD_VIEW_PATH", piutang_path)
    monkeypatch.setattr(local_dashboard, "SUPERSET_GOLD_PATH", fact_path)
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    payload = client.get("/api/local-dashboard/all").get_json()

    assert payload["status"] == "validated"
    assert payload["source_kind"] == "gold_fact_anggaran"
    assert payload["source_dataset"] == "fact_anggaran"
    assert "superset_reference" in payload
    assert payload["data"]["labels"]["title"] == "Dashboard Anggaran IKU Sains Data"
    assert payload["data"]["summary"]["total_nominal_piutang_rp"] == 750000


def test_local_dashboard_filters(tmp_path, monkeypatch):
    path = tmp_path / "data/generated/gold/vw_dashboard_piutang_ukt.csv"
    _write_gold_view(path)
    client = _client_for(path, monkeypatch)

    payload = client.get("/api/local-dashboard/filters").get_json()

    assert payload["status"] == "validated"
    assert payload["data"]["nama_prodi"] == ["Sains Data", "Teknik Informatika"]
    assert payload["data"]["tahun_anggaran"] == ["2024", "2025"]


def test_local_dashboard_summary(tmp_path, monkeypatch):
    path = tmp_path / "data/generated/gold/vw_dashboard_piutang_ukt.csv"
    _write_gold_view(path)
    client = _client_for(path, monkeypatch)

    payload = client.get("/api/local-dashboard/summary?nama_prodi=Sains%20Data").get_json()

    assert payload["status"] == "validated"
    assert payload["filters"] == {"nama_prodi": ["Sains Data"]}
    assert payload["data"]["total_nominal_piutang_rp"] == 3500000
    assert payload["data"]["total_debitur_unik"] == 2


def test_local_dashboard_charts(tmp_path, monkeypatch):
    path = tmp_path / "data/generated/gold/vw_dashboard_piutang_ukt.csv"
    _write_gold_view(path)
    client = _client_for(path, monkeypatch)

    payload = client.get("/api/local-dashboard/charts?tahun_anggaran=2025").get_json()

    assert payload["status"] == "validated"
    charts = payload["data"]
    assert charts["donut_by_kualitas"]["filter_column"] == "kualitas"
    assert {item["label"] for item in charts["donut_by_kualitas"]["items"]} == {"Macet", "Diragukan"}


def test_local_dashboard_table(tmp_path, monkeypatch):
    path = tmp_path / "data/generated/gold/vw_dashboard_piutang_ukt.csv"
    _write_gold_view(path)
    client = _client_for(path, monkeypatch)

    payload = client.get("/api/local-dashboard/table?kualitas=Macet").get_json()

    assert payload["status"] == "validated"
    assert payload["data"]["total_rows"] == 1
    assert payload["data"]["rows"][0]["nama_debitur"] == "Debitur B"
