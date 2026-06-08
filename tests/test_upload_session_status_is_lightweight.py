from __future__ import annotations

import io
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
            path.write_bytes(content)


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _sources() -> dict[str, Path]:
    base = ROOT / "data" / "raw_lama"
    return {
        "pdf": base / "pdf" / "ITERA_LKTA2024Audited.pdf",
        "csv": base / "csv" / "transaksi_ganjil.csv",
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
        },
    )


def _upload_all(client):
    sources = _sources()
    return client.post(
        "/api/upload/session",
        data={
            "target_tahun_akademik": "2025/2026",
            "target_tahun_anggaran": "2026",
            "pdf": (io.BytesIO(sources["pdf"].read_bytes()), "laporan.pdf"),
            "csv": (io.BytesIO(sources["csv"].read_bytes()), "transaksi_ganjil.csv"),
            "excel": (io.BytesIO(sources["excel"].read_bytes()), "rab.xlsx"),
        },
        content_type="multipart/form-data",
    )


def test_upload_session_status_is_lightweight(client, monkeypatch):
    reset_session()
    response = _upload_all(client)
    assert response.status_code == 200

    def fail(*_args, **_kwargs):
        raise AssertionError("GET status must not run heavy file validation")

    monkeypatch.setattr("portal_backend.services.upload_session.PdfReader", fail)
    monkeypatch.setattr("portal_backend.services.upload_session.pd.read_csv", fail)
    monkeypatch.setattr("portal_backend.services.upload_session.load_workbook", fail)

    status = client.get("/api/upload/session/status")
    payload = status.get_json()

    assert status.status_code == 200
    assert payload["readiness"]["can_commit"] is True


def test_upload_file_validates_once_then_status_reads_cache(client, monkeypatch):
    reset_session()
    _post_context(client)
    sources = _sources()
    calls = {"pdf": 0}

    class FakePdfReader:
        def __init__(self, *_args, **_kwargs):
            calls["pdf"] += 1

    monkeypatch.setattr("portal_backend.services.upload_session.PdfReader", FakePdfReader)
    response = client.post(
        "/api/upload/session/file",
        data={"upload_type": "pdf", "file": (io.BytesIO(sources["pdf"].read_bytes()), "laporan.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert calls["pdf"] == 1

    status = client.get("/api/upload/session/status")
    assert status.status_code == 200
    assert calls["pdf"] == 1


def test_commit_runs_final_validation_and_blocks_invalid_file(client, monkeypatch):
    reset_session()
    response = _upload_all(client)
    assert response.status_code == 200
    calls = {"pdf": 0}

    def failing_pdf_reader(*_args, **_kwargs):
        calls["pdf"] += 1
        raise RuntimeError("broken pdf")

    monkeypatch.setattr("portal_backend.services.upload_session.PdfReader", failing_pdf_reader)

    status = client.get("/api/upload/session/status")
    assert status.status_code == 200
    assert calls["pdf"] == 0

    commit = client.post("/api/upload/session/commit", json={})
    payload = commit.get_json()
    assert commit.status_code == 400
    assert payload["status"] == "commit_failed"
    assert calls["pdf"] == 1
