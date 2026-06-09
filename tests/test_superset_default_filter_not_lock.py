from src.sql import setup_superset_dashboard as dashboard


def test_superset_default_filter_is_native_not_static_lock():
    defaults = {"nama_prodi": ["Sains Data"], "tahun_akademik": ["2025/2026"]}
    filters = dashboard._native_filter_configuration(dataset_id=42, defaults=defaults)
    definitions = dashboard._chart_definitions(dataset_id=42)

    assert dashboard._chart_static_locks(definitions) == []
    assert any(item["defaultDataMask"]["filterState"]["value"] == ["Sains Data"] for item in filters)
    assert all(item["controlValues"]["enableEmptyFilter"] is True for item in filters)
