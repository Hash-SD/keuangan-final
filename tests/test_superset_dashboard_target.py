from __future__ import annotations

import json
from unittest.mock import Mock

import pytest

import src.sql.setup_superset_excel_assets as assets


def _put_response(dashboard_id: int) -> Mock:
    return Mock(ok=True, status_code=200, json=lambda: {"id": dashboard_id, "result": {"id": dashboard_id}})


def _session_with_dashboards(dashboard_ids: list[int]) -> Mock:
    session = Mock()
    session.put.return_value = _put_response(dashboard_ids[-1])
    return session


def test_explicit_target_dashboard_id_returns_only_existing_id(monkeypatch):
    monkeypatch.setattr(assets, "TARGET_DASHBOARD_ID", "2")
    session = Mock()
    monkeypatch.setattr(
        assets,
        "_get_items",
        lambda session, resource: [{"id": 1}, {"id": 2}, {"id": 4}] if resource == "dashboard" else [],
    )
    assert assets._target_dashboard_id(session) == 2


def test_explicit_target_missing_dashboard_falls_back(monkeypatch):
    monkeypatch.setattr(assets, "TARGET_DASHBOARD_ID", "99")
    session = Mock()
    monkeypatch.setattr(
        assets,
        "_get_items",
        lambda session, resource: [{"id": 1}, {"id": 2}, {"id": 4}] if resource == "dashboard" else [],
    )
    assert assets._target_dashboard_id(session) is None


def test_no_explicit_target_returns_none(monkeypatch):
    monkeypatch.setattr(assets, "TARGET_DASHBOARD_ID", "")
    assert assets._target_dashboard_id(Mock()) is None


def test_new_dashboard_mode_ignores_explicit_target(monkeypatch):
    monkeypatch.setattr(assets, "DASHBOARD_MODE", "new")
    monkeypatch.setattr(assets, "TARGET_DASHBOARD_ID", "2")
    session = Mock()

    assert assets._target_dashboard_id(session) is None
    session.get.assert_not_called()


def test_new_dashboard_mode_creates_chart_instead_of_updating_old_registry_chart(monkeypatch):
    monkeypatch.setattr(assets, "DASHBOARD_MODE", "new")
    monkeypatch.setattr(assets, "DASHBOARD_INSTANCE_NUMBER", 2)
    old_chart = {
        "id": 7,
        "description": f"{assets.MANAGED_CHART_MARKER}kpi_total_anggaran",
        "slice_name": assets.CHART_DISPLAY_NAMES["kpi_total_anggaran"],
    }
    monkeypatch.setattr(assets, "_get_items", lambda _session, resource: [old_chart] if resource == "chart" else [])
    session = Mock()
    session.post.return_value = _put_response(99)

    payload = assets._chart_payload(
        dataset_id=5,
        name=assets._chart_name("KPI total anggaran"),
        viz_type="big_number_total",
        form_data={},
        query={},
        registry_key="kpi_total_anggaran",
    )

    chart_id = assets._upsert_chart(session, payload)

    assert chart_id == 99
    assert session.post.call_count == 1
    assert session.put.call_count == 0
    assert payload["description"] == f"{assets.NEW_MANAGED_CHART_MARKER}2:kpi_total_anggaran"


def test_new_dashboard_uses_one_stable_suffix_for_title_slug_and_charts(monkeypatch):
    monkeypatch.setattr(assets, "DASHBOARD_MODE", "new")
    monkeypatch.setattr(assets, "DASHBOARD_INSTANCE_NUMBER", 3)

    assert assets._dashboard_title() == "SILARAS SD - Dashboard Anggaran IKU 3"
    assert assets._dashboard_slug() == "dashboard-anggaran-iku-prodi-3"
    assert assets._chart_name("Detail Item Biaya") == "Detail Item Biaya 3"


def test_new_dashboard_uses_next_numeric_instance_without_pipeline_uuid(monkeypatch):
    monkeypatch.setattr(assets, "DASHBOARD_MODE", "new")
    monkeypatch.setattr(assets, "DASHBOARD_INSTANCE_NUMBER", None)
    session = Mock()
    monkeypatch.setattr(
        assets,
        "_get_items",
        lambda _session, resource: (
            [
                {"id": 1, "dashboard_title": assets.DASHBOARD_TITLE},
                {"id": 2, "dashboard_title": f"{assets.DASHBOARD_TITLE} 1"},
                {"id": 3, "dashboard_title": f"{assets.DASHBOARD_TITLE} 3"},
                {"id": 4, "dashboard_title": f"{assets.DASHBOARD_TITLE} old-run"},
            ]
            if resource == "dashboard"
            else []
        ),
    )

    assets._prepare_new_dashboard_instance(session)

    assert assets.DASHBOARD_INSTANCE_NUMBER == 4
    assert "old-run" not in assets._dashboard_title()
    assert assets._dashboard_title().endswith(" 4")
    assert assets._dashboard_slug().endswith("-4")
    assert assets._chart_name("Validasi Rekap").endswith(" 4")


def test_superset_table_payloads_use_business_labels_and_thousands_format(monkeypatch):
    monkeypatch.setattr(assets, "DASHBOARD_MODE", "update")

    detail = json.loads(assets._registry_chart_payload("detail_item_biaya", 10, 20)["params"])
    validation = json.loads(assets._registry_chart_payload("validasi_rekap", 10, 20)["params"])

    assert detail["column_config"]["harga_satuan"]["d3NumberFormat"] == ",.0f"
    assert detail["column_config"]["jumlah"]["d3NumberFormat"] == ",.0f"
    for column in ("total_detail", "total_rekap", "selisih"):
        assert validation["column_config"][column]["d3NumberFormat"] == ",.0f"
    assert assets.COLUMN_LABELS["total_detail"] == "Detail Total"
    assert assets.COLUMN_LABELS["total_rekap"] == "Total Rekap"
    assert assets.COLUMN_LABELS["selisih"] == "Selisih"
    assert assets.COLUMN_LABELS["status"] == "Status"


def test_year_summary_disables_show_cell_bars():
    params = json.loads(assets._registry_chart_payload("ringkasan_per_tahun", 10, 20)["params"])

    assert params["show_cell_bars"] is False


def test_superset_identity_resolves_from_published_active_gold_run(tmp_path, monkeypatch):
    reports = tmp_path / "outputs" / "reports"
    reports.mkdir(parents=True)
    (reports / "active_gold_run.json").write_text(
        json.dumps(
            {
                "status": "PUBLISHED",
                "dataset_session_id": "dataset-1",
                "pipeline_run_id": "run-1",
            }
        ),
        encoding="utf-8",
    )
    (reports / "active_excel_lakehouse_dataset.json").write_text(
        json.dumps(
            {
                "status": "committed",
                "dataset_session_id": "dataset-1",
                "files": [{"filename": "RAB_2025.xlsx"}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(assets, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.delenv("DATASET_SESSION_ID", raising=False)
    monkeypatch.delenv("PIPELINE_RUN_ID", raising=False)

    assert assets._resolve_pipeline_identity() == ("dataset-1", "run-1")


def test_superset_identity_rejects_published_gold_for_different_active_dataset(tmp_path, monkeypatch):
    reports = tmp_path / "outputs" / "reports"
    reports.mkdir(parents=True)
    (reports / "active_excel_lakehouse_dataset.json").write_text(
        json.dumps({"status": "committed", "dataset_session_id": "new-dataset", "files": [{"filename": "RAB.xlsx"}]}),
        encoding="utf-8",
    )
    (reports / "active_gold_run.json").write_text(
        json.dumps({"status": "PUBLISHED", "dataset_session_id": "old-dataset", "pipeline_run_id": "old-run"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(assets, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.delenv("DATASET_SESSION_ID", raising=False)
    monkeypatch.delenv("PIPELINE_RUN_ID", raising=False)

    with pytest.raises(RuntimeError, match="berbeda dari dataset aktif"):
        assets._resolve_pipeline_identity()


def test_upsert_dashboard_targets_explicit_id_without_slug_match(monkeypatch):
    monkeypatch.setattr(assets, "TARGET_DASHBOARD_ID", "2")
    session = _session_with_dashboards([1, 2, 4])
    monkeypatch.setattr(
        assets,
        "_get_items",
        lambda session, resource: [{"id": 1}, {"id": 2}, {"id": 4}] if resource == "dashboard" else [],
    )
    dashboard_id = assets._upsert_dashboard(session, dataset_id=2, chart_ids=[32, 33])

    assert dashboard_id == 2
    assert session.put.call_count == 3  # dashboard PUT + 2 chart attaches
    put_url = session.put.call_args_list[0][0][0]
    assert put_url.endswith("/api/v1/dashboard/2")


def test_hidden_columns_excluded_from_table_charts():
    assert assets.HIDDEN_COLUMNS == frozenset({"mapping_status", "data_quality_flag", "source_sheet", "source_row"})
    assert assets.HIDDEN_COLUMNS.isdisjoint(assets.DETAIL_TABLE_COLUMNS)
    assert assets.HIDDEN_COLUMNS.isdisjoint(assets.VALIDASI_TABLE_COLUMNS)
    assert "source_file" in assets.DETAIL_TABLE_COLUMNS


def test_superset_display_labels_use_business_friendly_names():
    assert assets.COLUMN_LABELS["source_file"] == "Sumber Data"
    assert assets.COLUMN_LABELS["uraian_detail"] == "Detail"
    assert assets.COLUMN_LABELS["harga_satuan"] == "Harga Satuan"
    assert assets.COLUMN_LABELS["jumlah_weighted_iku"] == "Alokasi Anggaran IKU"


def test_dataset_column_payload_keeps_physical_name_and_adds_display_label():
    payload = assets._dataset_column_payload(
        {"id": 7, "column_name": "source_file", "is_active": True}
    )

    assert payload == {
        "id": 7,
        "column_name": "source_file",
        "verbose_name": "Sumber Data",
        "is_active": True,
    }


def test_deactivate_hidden_columns_marks_inactive():
    session = Mock()
    session.get.return_value = Mock(
        ok=True,
        status_code=200,
        json=lambda: {
            "result": {
                "columns": [
                    {"id": 1, "column_name": "tahun"},
                    {"id": 2, "column_name": "mapping_status"},
                    {"id": 3, "column_name": "source_row"},
                ]
            }
        },
    )
    session.put.return_value = Mock(ok=True, status_code=200, json=lambda: {"result": {"id": 5}})

    deactivated = assets._deactivate_hidden_columns(session, dataset_id=5)

    assert deactivated == ["mapping_status", "source_row"]
    put_payload = session.put.call_args[1]["json"]
    by_name = {column["column_name"]: column for column in put_payload["columns"]}
    assert by_name["tahun"]["is_active"] is True
    assert by_name["mapping_status"]["is_active"] is False
    assert by_name["source_row"]["is_active"] is False


def test_detail_saved_query_sql_excludes_hidden_columns():
    for hidden in assets.HIDDEN_COLUMNS:
        assert hidden not in assets.SAVED_QUERY_DETAIL_SQL
