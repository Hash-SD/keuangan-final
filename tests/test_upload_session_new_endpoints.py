from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from portal_backend.app import create_app
from portal_backend.services.upload_session import (
    ACTIVE_DATASET_POINTER_PATH,
    ACTIVE_SESSION_PATH,
    AVAILABLE_PERIODS_PATH,
    DATASET_REGISTRY_PATH,
    LATEST_UPLOAD_METADATA_PATH,
    UPLOAD_REGISTRY_PATH,
    reset_session,
)


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_CONTEXT_PATH = ROOT / "outputs" / "reports" / "active_runtime_context.json"
SYSTEM_TRUTH_PATH = ROOT / "outputs" / "reports" / "system_truth_status.json"


@pytest.fixture(autouse=True)
def restore_upload_state():
    snapshots = {}
    for path in [ACTIVE_DATASET_POINTER_PATH, ACTIVE_SESSION_PATH, ACTIVE_CONTEXT_PATH, SYSTEM_TRUTH_PATH, UPLOAD_REGISTRY_PATH, LATEST_UPLOAD_METADATA_PATH, DATASET_REGISTRY_PATH, AVAILABLE_PERIODS_PATH]:
        snapshots[path] = path.read_bytes() if path.exists() else None
    yield
    for path, content in snapshots.items():
        if content is None:
            if path.exists():
                path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            restore_path = path.with_name(f"{path.name}.restore.tmp")
            restore_path.write_bytes(content)
            restore_path.replace(path)


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _sources() -> dict[str, Path]:
    legacy = ROOT / "data" / "raw_lama"
    base = legacy if legacy.exists() else ROOT / "data" / "raw"
    return {
        "pdf": base / "pdf" / "ITERA_LKTA2024Audited.pdf",
        "csv_ganjil": base / "csv" / "transaksi_ganjil.csv",
        "csv_genap": base / "csv" / "transaksi_genap.csv",
        "excel": base / "excel" / "rab_prodi_sains_data.xlsx",
    }


def _post_context(client):
    return client.post(
        "/api/upload/session/context",
        json={
            "target_prodi": "Sains Data",
            "target_fakultas": "Fakultas Sains",
            "target_tahun_akademik": "2025/2026",
            "target_tahun_anggaran": "2026",
            "source_event": "2026-06-08T00:00:00Z",
        },
    )


def _post_file(client, upload_type: str, source: Path, name: str):
    return client.post(
        "/api/upload/session/file",
        data={"upload_type": upload_type, "file": (io.BytesIO(source.read_bytes()), name)},
        content_type="multipart/form-data",
    )


def test_upload_session_status_empty():
    reset_session()
    test_client = create_app().test_client()
    payload = test_client.get("/api/upload/session/status").get_json()
    assert payload["status"] == "draft"
    assert payload["readiness"]["can_commit"] is False


def test_upload_session_context_autosave(client):
    reset_session()
    response = _post_context(client)
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["readiness"]["context_ready"] is True
    assert payload["context"]["status"] == "draft_saved"


def test_upload_session_pdf_csv_excel_persist(client):
    reset_session()
    sources = _sources()
    _post_context(client)
    pdf = _post_file(client, "pdf", sources["pdf"], "laporan.pdf").get_json()
    csv = client.post(
        "/api/upload/session/file",
        data={
            "upload_type": "csv",
            "file": [
                (io.BytesIO(sources["csv_ganjil"].read_bytes()), "transaksi_ganjil.csv"),
                (io.BytesIO(sources["csv_genap"].read_bytes()), "transaksi_genap.csv"),
            ],
        },
        content_type="multipart/form-data",
    ).get_json()
    excel = _post_file(client, "excel", sources["excel"], "rab.xlsx").get_json()
    assert pdf["files"]["pdf"]["filename"] == "laporan.pdf"
    assert csv["files"]["pdf"]["filename"] == "laporan.pdf"
    assert csv["files"]["csv"]["count"] == 2
    assert excel["files"]["pdf"]["filename"] == "laporan.pdf"
    assert excel["files"]["csv"]["count"] == 2
    assert excel["files"]["excel"]["filename"] == "rab.xlsx"
    assert excel["readiness"]["can_commit"] is True


def test_upload_session_remove_file(client):
    reset_session()
    sources = _sources()
    _post_context(client)
    _post_file(client, "pdf", sources["pdf"], "laporan.pdf")
    _post_file(client, "csv", sources["csv_ganjil"], "transaksi_ganjil.csv")
    _post_file(client, "excel", sources["excel"], "rab.xlsx")
    response = client.delete("/api/upload/session/file", json={"upload_type": "csv", "filename": "transaksi_ganjil.csv"})
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["files"]["csv"]["count"] == 0
    assert payload["files"]["pdf"]["filename"] == "laporan.pdf"
    assert payload["files"]["excel"]["filename"] == "rab.xlsx"
    assert payload["readiness"]["can_commit"] is False


def test_upload_session_commit_requires_complete(client):
    reset_session()
    _post_context(client)
    response = client.post("/api/upload/session/commit", json={})
    payload = response.get_json()
    assert response.status_code == 400
    assert payload["status"] == "commit_failed"
    assert payload["readiness"]["can_commit"] is False


def test_upload_session_commit_success(client):
    reset_session()
    sources = _sources()
    _post_context(client)
    _post_file(client, "pdf", sources["pdf"], "laporan.pdf")
    client.post(
        "/api/upload/session/file",
        data={
            "upload_type": "csv",
            "file": [
                (io.BytesIO(sources["csv_ganjil"].read_bytes()), "transaksi_ganjil.csv"),
                (io.BytesIO(sources["csv_genap"].read_bytes()), "transaksi_genap.csv"),
            ],
        },
        content_type="multipart/form-data",
    )
    _post_file(client, "excel", sources["excel"], "rab.xlsx")
    response = client.post("/api/upload/session/commit", json={})
    payload = response.get_json()
    pointer = json.loads(ACTIVE_DATASET_POINTER_PATH.read_text(encoding="utf-8"))
    assert response.status_code == 200
    assert payload["status"] == "committed"
    assert payload["raw_layer"]["status"] == "ready"
    assert payload["pipeline_state"]["quality_gate"] == "not_started"
    assert pointer["dataset_mode"] == "uploaded"
