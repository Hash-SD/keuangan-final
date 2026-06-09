import json

from src.sql import setup_superset_dashboard as dashboard


def test_superset_chart_definitions_are_multi_year_and_unique(monkeypatch):
    monkeypatch.setenv("PORTAL_TARGET_PRODI", "Sains Data")
    monkeypatch.setenv("PORTAL_TARGET_TAHUN_AKADEMIK", "2025/2026")

    definitions = dashboard._chart_definitions(dataset_id=42)
    chart_names = [item["slice_name"] for item in definitions]

    assert len(chart_names) == 6
    assert len(chart_names) == len(set(chart_names))
    assert "Total Piutang UKT" in chart_names
    assert "Jumlah Mahasiswa Penunggak" in chart_names
    assert "Piutang UKT per Prodi" in chart_names
    assert "Distribusi Kualitas Piutang" in chart_names
    assert "Tren Piutang per Semester" in chart_names
    assert "Rincian Piutang Mahasiswa" in chart_names

    query_contexts = [json.loads(item["query_context"]) for item in definitions]
    query_filters = [query.get("filters", []) for ctx in query_contexts for query in ctx["queries"]]
    assert all({"col": "tahun_akademik", "op": "==", "val": "2025/2026"} not in filters for filters in query_filters)


def test_superset_stale_period_charts_are_managed(monkeypatch):
    monkeypatch.setenv("PORTAL_TARGET_PRODI", "Sains Data")
    monkeypatch.setenv("PORTAL_TARGET_TAHUN_AKADEMIK", "2025/2026")

    active_names = {item["slice_name"] for item in dashboard._chart_definitions(dataset_id=42)}

    assert dashboard._is_managed_chart_name("Total Piutang UKT - Sains Data 2023/2024", active_names)
    assert dashboard._is_managed_chart_name("Jumlah Mahasiswa Penunggak - Sains Data 2024/2025", active_names)
    assert dashboard._is_managed_chart_name("Rincian Piutang Mahasiswa", active_names)
    assert not dashboard._is_managed_chart_name("Visual Manual Operator", active_names)


def test_superset_native_filters_cover_multi_year_context():
    filters = dashboard._native_filter_configuration(dataset_id=42, defaults={"nama_prodi": ["Sains Data"]})
    columns = [item["targets"][0]["column"]["name"] for item in filters]

    assert columns == ["tahun_akademik", "tahun_anggaran", "semester", "nama_prodi", "kualitas"]
    prodi_filter = next(item for item in filters if item["id"] == "native_filter_prodi")
    assert prodi_filter["defaultDataMask"]["filterState"]["value"] == ["Sains Data"]
    assert all(item["scope"]["excluded"] == [] for item in filters)
    assert all(item["controlValues"]["enableEmptyFilter"] is True for item in filters)
