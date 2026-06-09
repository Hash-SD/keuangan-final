from src.sql import setup_superset_dashboard as dashboard


def test_superset_native_filters_include_required_dashboard_filters(monkeypatch):
    monkeypatch.setenv("PORTAL_TARGET_PRODI", "Sains Data")
    monkeypatch.setenv("PORTAL_TARGET_TAHUN_AKADEMIK", "2025/2026")
    monkeypatch.setenv("PORTAL_TARGET_TAHUN_ANGGARAN", "2026")

    defaults = dashboard._runtime_filter_defaults(
        {
            "tahun_akademik": {"2025/2026"},
            "tahun_anggaran": {"2026"},
            "semester": {"Ganjil", "Genap"},
            "nama_prodi": {"Sains Data"},
            "kualitas": {"Lancar"},
        }
    )
    filters = dashboard._native_filter_configuration(dataset_id=42, defaults=defaults)
    by_column = {item["targets"][0]["column"]["name"]: item for item in filters}

    assert set(by_column) == {"nama_prodi", "tahun_akademik", "tahun_anggaran", "semester", "kualitas"}
    assert by_column["nama_prodi"]["defaultDataMask"]["filterState"]["value"] == ["Sains Data"]
    assert by_column["tahun_akademik"]["defaultDataMask"]["filterState"]["value"] == ["2025/2026"]
    assert by_column["tahun_anggaran"]["defaultDataMask"]["filterState"]["value"] == [2026]
    assert by_column["semester"]["defaultDataMask"]["filterState"]["value"] is None
    assert by_column["kualitas"]["defaultDataMask"]["filterState"]["value"] is None
