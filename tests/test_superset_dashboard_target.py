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
