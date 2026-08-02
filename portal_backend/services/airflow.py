from __future__ import annotations

import os
from datetime import datetime
from math import isfinite
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import requests

DAG_ID = "keuangan_prodi_excel_lakehouse_dag"
TERMINAL_STATES = {"success", "failed", "upstream_failed", "skipped"}
ACTIVE_STATES = {"queued", "running", "scheduled", "up_for_retry", "up_for_reschedule"}

STAGE_TASKS: dict[str, tuple[str, ...]] = {
    "raw": ("start", "validate_upload_context", "extract_excel_to_bronze"),
    "bronze": ("detect_year_and_format", "parse_flexible", "merge_multi_file"),
    "silver": ("normalize_silver", "map_iku_and_nomenklatur", "validate_excel_totals"),
    "gold": ("build_fact_anggaran", "write_minio_storage", "load_gold_to_postgres", "validate_trino_postgres_catalog"),
    "bi": ("refresh_superset_dataset", "refresh_superset_dashboard", "generate_storage_manifest", "generate_system_status", "end"),
}


def _stage_of(task_id: str) -> str:
    lowered = (task_id or "").lower()
    for stage, task_ids in STAGE_TASKS.items():
        if lowered in task_ids:
            return stage
    return "other"


def _airflow_task_duration_seconds(task: dict[str, Any]) -> float | None:
    """Read one task duration from fields returned by Airflow."""
    raw_duration = task.get("duration")
    zero_duration: float | None = None
    if raw_duration is not None:
        try:
            duration = float(raw_duration)
        except (TypeError, ValueError):
            duration = None
        if duration is not None and isfinite(duration) and duration > 0:
            return duration
        if duration == 0:
            zero_duration = 0.0

    start_date = task.get("start_date")
    end_date = task.get("end_date")
    if start_date and end_date:
        try:
            start = datetime.fromisoformat(str(start_date).replace("Z", "+00:00"))
            end = datetime.fromisoformat(str(end_date).replace("Z", "+00:00"))
            duration = (end - start).total_seconds()
        except (TypeError, ValueError):
            duration = None
        if duration is not None and isfinite(duration) and duration >= 0:
            return duration
    return zero_duration


def _airflow_timestamp_span_seconds(starts: list[str], ends: list[str]) -> float | None:
    if not starts or not ends:
        return None
    try:
        start = min(
            datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            for value in starts
        )
        end = max(
            datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            for value in ends
        )
    except (TypeError, ValueError):
        return None
    duration = (end - start).total_seconds()
    return duration if isfinite(duration) and duration >= 0 else None


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
    total = len(tasks)
    done = sum(1 for task in tasks if task.get("state") in TERMINAL_STATES)
    current = next((task for task in tasks if task.get("state") in ACTIVE_STATES), None)
    starts = [task.get("start_date") for task in tasks if task.get("start_date")]
    ends = [task.get("end_date") for task in tasks if task.get("end_date")]
    stage_entries: dict[str, dict[str, Any]] = {}
    for task in tasks:
        stage = _stage_of(str(task.get("task_id") or ""))
        if stage == "other":
            continue
        entry = stage_entries.setdefault(
            stage,
            {"total": 0, "done": 0, "running": 0, "failed": 0, "starts": [], "ends": [], "duration_seconds": 0.0, "measured_durations": 0},
        )
        entry["total"] += 1
        state = task.get("state")
        if state in TERMINAL_STATES:
            entry["done"] += 1
            if state in {"failed", "upstream_failed"}:
                entry["failed"] += 1
        elif state in ACTIVE_STATES:
            entry["running"] += 1
        if task.get("start_date"):
            entry["starts"].append(task["start_date"])
        if task.get("end_date"):
            entry["ends"].append(task["end_date"])
        duration = _airflow_task_duration_seconds(task)
        if duration is not None:
            entry["duration_seconds"] += duration
            entry["measured_durations"] += 1
    stages = {
        stage: {
            "total": entry["total"],
            "done": entry["done"],
            "running": entry["running"],
            "failed": entry["failed"],
            "started_at": min(entry["starts"]) if entry["starts"] else None,
            "ended_at": max(entry["ends"]) if entry["ends"] else None,
            "duration_seconds": round(
                (
                    entry["duration_seconds"]
                    if entry["duration_seconds"] > 0.01
                    else _airflow_timestamp_span_seconds(entry["starts"], entry["ends"])
                )
                or 0.0,
                2,
            ) if entry["measured_durations"] else None,
            "progress_pct": round(entry["done"] * 100 / entry["total"])
            if entry["total"]
            else 0,
        }
        for stage, entry in stage_entries.items()
    }
    return {
        "available": True,
        "total_tasks": total,
        "completed_tasks": done,
        "progress_pct": round(done * 100 / total) if total else 0,
        "current_task": current.get("task_id") if current else None,
        "current_state": current.get("state") if current else None,
        "started_at": min(starts) if starts else None,
        "ended_at": max(ends) if ends else None,
        "stages": stages,
        "task_instances": tasks,
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


def _with_progress(run: dict[str, Any]) -> dict[str, Any]:
    """Attach task-instance progress (with per-stage breakdown) to a run."""
    progress: dict[str, Any] = {"available": False}
    try:
        progress = _dag_run_progress(str(run.get("dag_run_id")))
    except (RuntimeError, LookupError):
        progress = {"available": False}
    return {**run, "progress": progress}


def _list_dag_run_items(limit: int = 50) -> list[dict[str, Any]]:
    url = f"{_base_url()}/api/v1/dags/{quote(DAG_ID, safe='')}/dagRuns"
    try:
        response = requests.get(
            url,
            auth=_auth(),
            params={"limit": limit, "order_by": "-execution_date"},
            timeout=float(os.getenv("AIRFLOW_REQUEST_TIMEOUT", "15")),
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Airflow tidak dapat dihubungi: {exc}") from exc
    if not response.ok:
        detail = response.text[:500].strip() or f"HTTP {response.status_code}"
        raise RuntimeError(f"Daftar run Airflow tidak dapat dibaca: {detail}")
    return _json(response).get("dag_runs") or []


def _summarize_dag_run(run_item: dict[str, Any]) -> dict[str, Any]:
    state = run_item.get("state", "unknown")
    return {
        "dag_id": DAG_ID,
        "dag_run_id": run_item.get("dag_run_id"),
        "state": state,
        "logical_date": run_item.get("logical_date") or run_item.get("execution_date"),
        "start_date": run_item.get("start_date"),
        "end_date": run_item.get("end_date"),
        "conf": run_item.get("conf") or {},
        "terminal": state in TERMINAL_STATES,
    }


def get_runtime_snapshot(dataset_session_id: str | None = None) -> dict[str, Any]:
    """Read one Airflow run list and attach progress only to the runtime source.

    The active run has priority. When there is no active run, the latest matching
    run becomes the source. This keeps the UI's high-frequency refresh to one
    list request plus one task-instance request instead of querying active and
    latest independently.
    """
    run_items = _list_dag_run_items(limit=50)
    matching = []
    for item in run_items:
        conf = item.get("conf") or {}
        if dataset_session_id and conf.get("dataset_session_id") != dataset_session_id:
            continue
        matching.append(item)

    active_item = next(
        (item for item in matching if item.get("state") in ACTIVE_STATES),
        None,
    )
    latest_item = matching[0] if matching else None
    active_run = _summarize_dag_run(active_item) if active_item else None
    latest_run = _summarize_dag_run(latest_item) if latest_item else None
    source = "active" if active_run else "latest" if latest_run else "none"
    runtime_run = active_run or latest_run
    if runtime_run:
        runtime_run = _with_progress(runtime_run)
        if active_run:
            active_run = runtime_run
        else:
            latest_run = runtime_run

    return {
        "status": "ready" if runtime_run else "idle",
        "active": bool(active_run),
        "active_run": active_run,
        "latest_run": latest_run,
        "runtime_run": runtime_run,
        "source": source,
    }


def get_active_dag_run(dataset_session_id: str | None = None) -> dict[str, Any] | None:
    for run_item in _list_dag_run_items(limit=50):
        if run_item.get("state") not in ACTIVE_STATES:
            continue
        conf = run_item.get("conf") or {}
        if dataset_session_id and conf.get("dataset_session_id") != dataset_session_id:
            continue
        return _with_progress(_summarize_dag_run(run_item))
    return None


def get_latest_dag_run(dataset_session_id: str | None = None) -> dict[str, Any] | None:
    for run_item in _list_dag_run_items(limit=50):
        conf = run_item.get("conf") or {}
        if dataset_session_id and conf.get("dataset_session_id") != dataset_session_id:
            continue
        return _with_progress(_summarize_dag_run(run_item))
    return None


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
