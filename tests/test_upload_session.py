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
            path.write_bytes(content)


def _client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _bytes(path: Path) -> bytes:
    return path.read_bytes()


def _valid_sources() -> dict[str, Path]:
    return {
        "pdf": ROOT / "data" / "raw" / "pdf" / "ITERA_LKTA2024Audited.pdf",
        "csv_ganjil": ROOT / "data" / "raw" / "csv" / "transaksi_ganjil.csv",
        "csv_genap": ROOT / "data" / "raw" / "csv" / "transaksi_genap.csv",
        "excel": ROOT / "data" / "raw" / "excel" / "rab_prodi_sains_data.xlsx",
    }


def _reset():
    reset_session()


def test_upload_session_empty_can_not_commit():
    _reset()
    response = _client().get("/api/upload/session/status")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["status"] == "draft"
    assert payload["readiness"]["can_commit"] is False
    assert payload["files"]["pdf"]["status"] == "missing"


def test_upload_session_partial_pdf_only_keeps_staging():
    _reset()
    sources = _valid_sources()
    response = _client().post(
        "/api/upload/session",
        data={
            "target_tahun_akademik": "2025/2026",
            "target_tahun_anggaran": "2026",
            "pdf": (io.BytesIO(_bytes(sources["pdf"])), "laporan_audited_2026.pdf"),
        },
        content_type="multipart/form-data",
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["files"]["pdf"]["available"] is True
    assert payload["readiness"]["pdf_ready"] is True
    assert payload["readiness"]["csv_ready"] is False
    assert payload["readiness"]["excel_ready"] is False
    assert payload["readiness"]["can_commit"] is False


def test_upload_session_pdf_then_csv_then_excel_keeps_previous_files():
    _reset()
    client = _client()
    sources = _valid_sources()
    first = client.post(
        "/api/upload/session",
        data={"target_tahun_akademik": "2025/2026", "target_tahun_anggaran": "2026", "pdf": (io.BytesIO(_bytes(sources["pdf"])), "laporan.pdf")},
        content_type="multipart/form-data",
    ).get_json()
    second = client.post(
        "/api/upload/session",
        data={"csv": [(io.BytesIO(_bytes(sources["csv_ganjil"])), "transaksi_ganjil.csv"), (io.BytesIO(_bytes(sources["csv_genap"])), "transaksi_genap.csv")]},
        content_type="multipart/form-data",
    ).get_json()
    third = client.post(
        "/api/upload/session",
        data={"excel": (io.BytesIO(_bytes(sources["excel"])), "rab.xlsx")},
        content_type="multipart/form-data",
    ).get_json()

    assert first["files"]["pdf"]["filename"] == "laporan.pdf"
    assert second["files"]["pdf"]["filename"] == "laporan.pdf"
    assert second["files"]["csv"]["count"] == 2
    assert third["files"]["pdf"]["filename"] == "laporan.pdf"
    assert third["files"]["csv"]["count"] == 2
    assert third["files"]["excel"]["filename"] == "rab.xlsx"
    assert third["readiness"]["can_commit"] is True


def test_upload_session_commit_atomic_blocks_invalid_excel():
    _reset()
    client = _client()
    sources = _valid_sources()
    client.post(
        "/api/upload/session",
        data={
            "target_tahun_akademik": "2025/2026",
            "target_tahun_anggaran": "2026",
            "pdf": (io.BytesIO(_bytes(sources["pdf"])), "laporan.pdf"),
            "csv": [(io.BytesIO(_bytes(sources["csv_ganjil"])), "transaksi_ganjil.csv"), (io.BytesIO(_bytes(sources["csv_genap"])), "transaksi_genap.csv")],
            "excel": (io.BytesIO(b"not xlsx"), "bad.xlsx"),
        },
        content_type="multipart/form-data",
    )
    response = client.post("/api/upload/session/commit", json={})
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["status"] == "commit_failed"
    assert not any((ROOT / "data" / "raw" / "excel" / "2026").glob("*bad.xlsx"))


def test_upload_session_commit_success_writes_pointer_and_truth_status():
    _reset()
    client = _client()
    sources = _valid_sources()
    client.post(
        "/api/upload/session",
        data={
            "target_tahun_akademik": "2025/2026",
            "target_tahun_anggaran": "2026",
            "pdf": (io.BytesIO(_bytes(sources["pdf"])), "laporan.pdf"),
            "csv": [(io.BytesIO(_bytes(sources["csv_ganjil"])), "transaksi_ganjil.csv"), (io.BytesIO(_bytes(sources["csv_genap"])), "transaksi_genap.csv")],
            "excel": (io.BytesIO(_bytes(sources["excel"])), "rab.xlsx"),
        },
        content_type="multipart/form-data",
    )
    response = client.post("/api/upload/session/commit", json={})
    payload = response.get_json()
    pointer = json.loads(ACTIVE_DATASET_POINTER_PATH.read_text(encoding="utf-8"))
    truth = json.loads((ROOT / "outputs" / "reports" / "system_truth_status.json").read_text(encoding="utf-8"))

    assert response.status_code == 200
    assert payload["status"] == "committed"
    assert pointer["dataset_mode"] == "uploaded"
    assert pointer["status"] == "committed"
    assert len(pointer["active_csv_files"]) == 2
    assert json.loads(DATASET_REGISTRY_PATH.read_text(encoding="utf-8"))["active_session_id"] == payload["session_id"]
    assert json.loads(AVAILABLE_PERIODS_PATH.read_text(encoding="utf-8"))["periods"][0]["tahun_akademik"] == "2025/2026"
    assert truth["layers"]["raw"]["status"] == "ready"
    assert truth["layers"]["bronze"]["status"] == "not_started"
    assert truth["uat"]["status"] == "manual_input_required"


def test_uploaded_mode_no_dummy_overwrite(monkeypatch):
    from portal_backend.services import pipeline

    monkeypatch.setattr(pipeline, "dataset_mode", lambda: "uploaded")
    result = pipeline.run_command_group("generate-data")

    assert result["status"] == "success"
    assert result["skipped"] is True
