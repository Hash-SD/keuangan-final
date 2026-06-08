from src.sql import setup_superset_dashboard as dashboard


def test_superset_chart_definitions_are_unique(monkeypatch):
    monkeypatch.setenv("PORTAL_TARGET_PRODI", "Sains Data")
    monkeypatch.setenv("PORTAL_TARGET_TAHUN_AKADEMIK", "2025/2026")

    definitions = dashboard._chart_definitions(dataset_id=42)
    chart_names = [item["slice_name"] for item in definitions]

    assert len(chart_names) == 6
    assert len(chart_names) == len(set(chart_names))
    assert "Total Piutang UKT - Sains Data 2025/2026" in chart_names
    assert "Jumlah Mahasiswa Penunggak - Sains Data 2025/2026" in chart_names


def test_superset_stale_period_charts_are_managed(monkeypatch):
    monkeypatch.setenv("PORTAL_TARGET_PRODI", "Sains Data")
    monkeypatch.setenv("PORTAL_TARGET_TAHUN_AKADEMIK", "2025/2026")

    active_names = {item["slice_name"] for item in dashboard._chart_definitions(dataset_id=42)}

    assert dashboard._is_managed_chart_name("Total Piutang UKT - Sains Data 2023/2024", active_names)
    assert dashboard._is_managed_chart_name("Jumlah Mahasiswa Penunggak - Sains Data 2024/2025", active_names)
    assert dashboard._is_managed_chart_name("Rincian Piutang Mahasiswa", active_names)
    assert not dashboard._is_managed_chart_name("Visual Manual Operator", active_names)
