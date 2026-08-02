from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import requests


DAG_ID = "keuangan_prodi_excel_lakehouse_dag"
TERMINAL_STATES = {"success", "failed", "upstream_failed", "skipped"}


def _json(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except (ValueError, requests.JSONDecodeError) as exc:
        raise RuntimeError("Airflow mengembalikan JSON yang tidak valid.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Airflow mengembalikan payload yang tidak valid.")
    return payload


def _base_url() -> str:
    host = os.getenv("AIRFLOW_HOST", "localhost")
    port = os.getenv("AIRFLOW_PORT", "8085")
    scheme = os.getenv("AIRFLOW_SCHEME", "http")
    return f"{scheme}://{host}:{port}".rstrip("/")


def _auth() -> tuple[str, str]:
    username = os.getenv("AIRFLOW_USERNAME", "").strip() or "airflow"
    password = os.getenv("AIRFLOW_PASSWORD", "").strip() or "airflow"
    return username, password

def trigger_dag(
    *,
    dataset_session_id: str,
    pipeline_run_id: str,
    dashboard_mode: str | None = None,
    dashboard_database_id: str | int | None = None,
    dashboard_dashboard_id: str | int | None = None,
) -> dict[str, Any]:
    dag_run_id = f"portal__{pipeline_run_id}"
    url = f"{_base_url()}/api/v1/dags/{quote(DAG_ID, safe='')}/dagRuns"
    conf: dict[str, Any] = {
        "dataset_session_id": dataset_session_id,
        "pipeline_run_id": pipeline_run_id,
    }
    if dashboard_mode:
        conf["dashboard_mode"] = dashboard_mode
    if dashboard_database_id not in {None, "", "auto"}:
        conf["dashboard_database_id"] = str(dashboard_database_id)
    if dashboard_dashboard_id not in {None, "", "auto"}:
        conf["dashboard_dashboard_id"] = str(dashboard_dashboard_id)
    try:
        response = requests.post(
            url,
            auth=_auth(),
            json={
            "dag_run_id": dag_run_id,
            "conf": conf,
            },
            timeout=float(os.getenv("AIRFLOW_REQUEST_TIMEOUT", "15")),
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Airflow tidak dapat dihubungi: {exc}") from exc
    if response.status_code not in {200, 201}:
        detail = response.text[:500].strip() or f"HTTP {response.status_code}"
        raise RuntimeError(f"Airflow menolak trigger DAG: {detail}")
    payload = _json(response)
    return {
        "dag_id": DAG_ID,
        "dag_run_id": payload.get("dag_run_id", dag_run_id),
        "dataset_session_id": dataset_session_id,
        "pipeline_run_id": pipeline_run_id,
        "state": payload.get("state", "queued"),
        "execution_date": payload.get("execution_date"),
    }


def create_pipeline_run_id() -> str:
    return str(uuid4())


def _dag_run_progress(dag_run_id: str) -> dict[str, Any]:
    """Fetch task-instance progress for a DAG run from the Airflow REST API."""
    url = (
        f"{_base_url()}/api/v1/dags/{quote(DAG_ID, safe='')}"
        f"/dagRuns/{quote(dag_run_id, safe='')}/taskInstances"
    )
    try:
        response = requests.get(
            url,
            auth=_auth(),
            params={"limit": 100},
            timeout=float(os.getenv("AIRFLOW_REQUEST_TIMEOUT", "15")),
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Airflow tidak dapat dihubungi: {exc}") from exc
    if not response.ok:
        return {"available": False}
    tasks = _json(response).get("task_instances") or []
    if not tasks:
        return {"available": False}
    active_states = {"running", "queued", "scheduled", "up_for_retry", "up_for_reschedule"}
    total = len(tasks)
    done = sum(1 for task in tasks if task.get("state") in TERMINAL_STATES)
    current = next((task for task in tasks if task.get("state") in active_states), None)
    starts = [task.get("start_date") for task in tasks if task.get("start_date")]
    ends = [task.get("end_date") for task in tasks if task.get("end_date")]
    return {
        "available": True,
        "total_tasks": total,
        "completed_tasks": done,
        "progress_pct": round(done * 100 / total) if total else 0,
        "current_task": current.get("task_id") if current else None,
        "current_state": current.get("state") if current else None,
        "started_at": min(starts) if starts else None,
        "ended_at": max(ends) if ends else None,
    }


def get_dag_run(dag_run_id: str) -> dict[str, Any]:
    url = f"{_base_url()}/api/v1/dags/{quote(DAG_ID, safe='')}/dagRuns/{quote(dag_run_id, safe='')}"
    try:
        response = requests.get(url, auth=_auth(), timeout=float(os.getenv("AIRFLOW_REQUEST_TIMEOUT", "15")))
    except requests.RequestException as exc:
        raise RuntimeError(f"Airflow tidak dapat dihubungi: {exc}") from exc
    if response.status_code == 404:
        raise LookupError(f"Airflow DAG run tidak ditemukan: {dag_run_id}")
    if not response.ok:
        detail = response.text[:500].strip() or f"HTTP {response.status_code}"
        raise RuntimeError(f"Status Airflow tidak dapat dibaca: {detail}")
    payload = _json(response)
    progress: dict[str, Any] = {"available": False}
    try:
        progress = _dag_run_progress(dag_run_id)
    except (RuntimeError, LookupError):
        progress = {"available": False}
    return {
        "dag_id": DAG_ID,
        "dag_run_id": payload.get("dag_run_id", dag_run_id),
        "state": payload.get("state", "unknown"),
        "logical_date": payload.get("logical_date"),
        "start_date": payload.get("start_date"),
        "end_date": payload.get("end_date"),
        "conf": payload.get("conf") or {},
        "terminal": payload.get("state") in TERMINAL_STATES,
        "progress": progress,
    }


def get_active_dag_run(dataset_session_id: str | None = None) -> dict[str, Any] | None:
    url = f"{_base_url()}/api/v1/dags/{quote(DAG_ID, safe='')}/dagRuns"
    try:
        response = requests.get(
            url,
            auth=_auth(),
            params={"limit": 50, "order_by": "-execution_date"},
            timeout=float(os.getenv("AIRFLOW_REQUEST_TIMEOUT", "15")),
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Airflow tidak dapat dihubungi: {exc}") from exc
    if not response.ok:
        detail = response.text[:500].strip() or f"HTTP {response.status_code}"
        raise RuntimeError(f"Daftar run Airflow tidak dapat dibaca: {detail}")
    payload = _json(response)
    for payload in payload.get("dag_runs", []):
        if payload.get("state") not in {"queued", "running", "scheduled"}:
            continue
        conf = payload.get("conf") or {}
        if dataset_session_id and conf.get("dataset_session_id") != dataset_session_id:
            continue
        return {
            "dag_id": DAG_ID,
            "dag_run_id": payload.get("dag_run_id"),
            "state": payload.get("state", "unknown"),
            "logical_date": payload.get("logical_date"),
            "start_date": payload.get("start_date"),
            "conf": conf,
            "terminal": False,
        }
    return None


def get_latest_dag_run(dataset_session_id: str | None = None) -> dict[str, Any] | None:
    url = f"{_base_url()}/api/v1/dags/{quote(DAG_ID, safe='')}/dagRuns"
    try:
        response = requests.get(
            url,
            auth=_auth(),
            params={"limit": 50, "order_by": "-execution_date"},
            timeout=float(os.getenv("AIRFLOW_REQUEST_TIMEOUT", "15")),
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Airflow tidak dapat dihubungi: {exc}") from exc
    if not response.ok:
        detail = response.text[:500].strip() or f"HTTP {response.status_code}"
        raise RuntimeError(f"Daftar run Airflow tidak dapat dibaca: {detail}")
    payload = _json(response)
    for run in payload.get("dag_runs", []):
        conf = run.get("conf") or {}
        if dataset_session_id and conf.get("dataset_session_id") != dataset_session_id:
            continue
        state = run.get("state", "unknown")
        return {
            "dag_id": DAG_ID,
            "dag_run_id": run.get("dag_run_id"),
            "state": state,
            "logical_date": run.get("logical_date") or run.get("execution_date"),
            "start_date": run.get("start_date"),
            "end_date": run.get("end_date"),
            "conf": conf,
            "terminal": state in TERMINAL_STATES,
        }
    return None


def delete_dag_run(dag_run_id: str) -> bool:
    """Delete a DAG run via the REST API.

    Only queued (not yet executed) runs should be deleted. Returns True when the
    run was removed; False when it was not found (already gone).
    """
    url = f"{_base_url()}/api/v1/dags/{quote(DAG_ID, safe='')}/dagRuns/{quote(dag_run_id, safe='')}"
    try:
        response = requests.delete(url, auth=_auth(), timeout=float(os.getenv("AIRFLOW_REQUEST_TIMEOUT", "15")))
    except requests.RequestException as exc:
        raise RuntimeError(f"Airflow tidak dapat dihubungi: {exc}") from exc
    if response.status_code == 404:
        return False
    if response.status_code != 204:
        detail = response.text[:500].strip() or f"HTTP {response.status_code}"
        raise RuntimeError(f"Airflow menolak hapus DAG run {dag_run_id}: {detail}")
    return True


def purge_stale_queued_runs(current_session_id: str) -> list[str]:
    """Remove abandoned queued DAG runs that target an older dataset session.

    Airflow `max_active_runs=1` lets runs pile up in `queued` state when they are
    triggered repeatedly. When the active Excel dataset later changes, those stale
    queued runs execute one by one against the newer dataset and fail the pipeline
    guard. Deleting them here keeps the queue clean so the next trigger actually runs.
    """
    stale: list[str] = []
    try:
        runs = get_all_dag_runs(limit=50)
    except RuntimeError:
        return stale
    for run in runs:
        if run.get("state") != "queued":
            continue
        conf = run.get("conf") or {}
        run_session = str(conf.get("dataset_session_id") or "").strip()
        if run_session and run_session != str(current_session_id).strip():
            dag_run_id = run.get("dag_run_id")
            if dag_run_id and delete_dag_run(dag_run_id):
                stale.append(dag_run_id)
    return stale


def get_all_dag_runs(limit: int = 10) -> list[dict[str, Any]]:
    url = f"{_base_url()}/api/v1/dags/{quote(DAG_ID, safe='')}/dagRuns"
    try:
        response = requests.get(
            url,
            auth=_auth(),
            params={"limit": limit, "order_by": "-execution_date"},
            timeout=float(os.getenv("AIRFLOW_REQUEST_TIMEOUT", "15")),
        )
    except requests.RequestException:
        return []
    if not response.ok:
        return []
    payload = _json(response)
    runs = []
    for run in payload.get("dag_runs", []):
        state = run.get("state", "unknown")
        runs.append({
            "dag_id": DAG_ID,
            "dag_run_id": run.get("dag_run_id"),
            "state": state,
            "logical_date": run.get("logical_date") or run.get("execution_date"),
            "start_date": run.get("start_date"),
            "end_date": run.get("end_date"),
            "conf": run.get("conf") or {},
            "terminal": state in TERMINAL_STATES,
        })
    return runs
