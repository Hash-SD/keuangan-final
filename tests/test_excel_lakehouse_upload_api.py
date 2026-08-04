from __future__ import annotations

import io
import json

from openpyxl import Workbook

from portal_backend.app import create_app
from portal_backend.services import excel_upload


def _xlsx_bytes() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "RAB"
    ws.append(["kode_akun", "nama_kegiatan", "kategori", "total_pagu"])
    ws.append(["521211", "Kegiatan Test", "Belanja Bahan", 1000])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def test_excel_lakehouse_upload_accepts_multi_file_excel_only(tmp_path, monkeypatch):
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "outputs" / "reports" / "active_excel_lakehouse_dataset.json")
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", tmp_path / "outputs" / "reports" / "excel_dataset_registry.json")
    monkeypatch.setattr(excel_upload, "relative_path", lambda path: str(path))
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/upload/excel-lakehouse",
        data={
            "tahun_input": "2025",
            "periode": "Tahunan",
            "prodi": "Sains Data",
            "fakultas": "Fakultas Sains",
            "jenis_dataset": "rab",
            "file_excel[]": [(io.BytesIO(_xlsx_bytes()), "rab_test.xlsx"), (io.BytesIO(_xlsx_bytes()), "rab_test_2.xlsx")],
        },
        content_type="multipart/form-data",
    )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["status"] == "committed"
    assert payload["dataset_session_id"] == payload["dataset_id"]
    assert payload["upload_started_at"] <= payload["upload_committed_at"]
    assert payload["excel_only"] is True
    assert len(payload["files"]) == 2
    assert payload["upload_scope"] == "single_year"
    assert payload["detected_years"] == ["2025"]
    assert payload["has_nomenklatur"] is False
    assert payload["warnings"]
    assert excel_upload.ACTIVE_EXCEL_DATASET_PATH.exists()


def test_single_file_uploads_append_and_preserve_metadata_per_file(tmp_path, monkeypatch):
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "outputs" / "reports" / "active_excel_lakehouse_dataset.json")
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", tmp_path / "outputs" / "reports" / "excel_dataset_registry.json")
    monkeypatch.setattr(excel_upload, "relative_path", lambda path: str(path))
    client = create_app().test_client()

    first = client.post(
        "/api/upload/excel-lakehouse",
        data={
            "upload_mode": "single",
            "append_to_active": "false",
            "tahun_input": "2025",
            "periode": "Tahunan",
            "prodi": "Sains Data",
            "fakultas": "Fakultas Sains",
            "jenis_dataset": "rab",
            "file_excel[]": [(io.BytesIO(_xlsx_bytes()), "rab_2025.xlsx")],
        },
        content_type="multipart/form-data",
    )
    second = client.post(
        "/api/upload/excel-lakehouse",
        data={
            "upload_mode": "single",
            "append_to_active": "true",
            "tahun_input": "2026",
            "periode": "Semester / Parsial",
            "prodi": "Teknik Informatika",
            "fakultas": "Fakultas Teknologi",
            "jenis_dataset": "rab",
            "file_excel[]": [(io.BytesIO(_xlsx_bytes()), "rab_2026.xlsx")],
        },
        content_type="multipart/form-data",
    )

    assert first.status_code == 200
    assert second.status_code == 200
    payload = second.get_json()
    assert len(payload["files"]) == 2
    assert [(item["filename"], item["tahun_input"], item["prodi"], item["fakultas"]) for item in payload["files"]] == [
        ("rab_2025.xlsx", "2025", "Sains Data", "Fakultas Sains"),
        ("rab_2026.xlsx", "2026", "Teknik Informatika", "Fakultas Teknologi"),
    ]
    assert [item["periode"] for item in payload["files"]] == ["Tahunan", "Semester / Parsial"]


def test_single_batch_preserves_metadata_snapshot_for_each_file(tmp_path, monkeypatch):
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "outputs" / "reports" / "active_excel_lakehouse_dataset.json")
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", tmp_path / "outputs" / "reports" / "excel_dataset_registry.json")
    monkeypatch.setattr(excel_upload, "relative_path", lambda path: str(path))

    response = create_app().test_client().post(
        "/api/upload/excel-lakehouse",
        data={
            "upload_mode": "single",
            "append_to_active": "false",
            "file_excel[]": [
                (io.BytesIO(_xlsx_bytes()), "rab_2025.xlsx"),
                (io.BytesIO(_xlsx_bytes()), "rab_2026.xlsx"),
            ],
            "file_metadata": json.dumps([
                {
                    "upload_mode": "single",
                    "jenis_dataset": "rab",
                    "tahun_input": "2025",
                    "periode": "Tahunan",
                    "prodi": "Sains Data",
                    "fakultas": "Fakultas Sains",
                },
                {
                    "upload_mode": "single",
                    "jenis_dataset": "rab",
                    "tahun_input": "2026",
                    "periode": "Semester / Parsial",
                    "prodi": "Teknik Informatika",
                    "fakultas": "Fakultas Teknologi",
                },
            ]),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert [(item["filename"], item["tahun_input"], item["prodi"], item["fakultas"]) for item in payload["files"]] == [
        ("rab_2025.xlsx", "2025", "Sains Data", "Fakultas Sains"),
        ("rab_2026.xlsx", "2026", "Teknik Informatika", "Fakultas Teknologi"),
    ]


def test_multi_file_bundle_does_not_require_single_file_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "outputs" / "reports" / "active_excel_lakehouse_dataset.json")
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", tmp_path / "outputs" / "reports" / "excel_dataset_registry.json")
    monkeypatch.setattr(excel_upload, "relative_path", lambda path: str(path))
    response = create_app().test_client().post(
        "/api/upload/excel-lakehouse",
        data={
            "upload_mode": "multi",
            "append_to_active": "false",
            "file_excel[]": [(io.BytesIO(_xlsx_bytes()), "RPD_bundle_2026.xlsx")],
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["upload_mode"] == "multi"
    assert payload["tahun_input"] is None
    assert payload["periode"] is None
    assert payload["prodi"] is None
    assert payload["fakultas"] is None
    assert payload["files"][0]["tahun_input"] is None
    assert payload["files"][0]["prodi"] is None


def test_upload_infers_mixed_workbook_kinds_from_filenames(tmp_path, monkeypatch):
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "outputs" / "reports" / "active_excel_lakehouse_dataset.json")
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", tmp_path / "outputs" / "reports" / "excel_dataset_registry.json")
    monkeypatch.setattr(excel_upload, "relative_path", lambda path: str(path))

    response = create_app().test_client().post(
        "/api/upload/excel-lakehouse",
        data={
            "upload_mode": "single",
            "append_to_active": "false",
            "tahun_input": "2023",
            "periode": "Semester / Parsial",
            "prodi": "Sains Data",
            "fakultas": "Fakultas Sains",
            "jenis_dataset": "nomenklatur",
            "file_excel[]": [
                (io.BytesIO(_xlsx_bytes()), "RAB_2025_SD_RAB_IKU.xlsx"),
                (io.BytesIO(_xlsx_bytes()), "Nomenklatur.xlsx"),
            ],
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert [item["jenis_dataset"] for item in response.get_json()["files"]] == [
        "rab",
        "nomenklatur",
    ]


def test_single_file_upload_rejects_missing_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "outputs" / "reports" / "active_excel_lakehouse_dataset.json")
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", tmp_path / "outputs" / "reports" / "excel_dataset_registry.json")
    monkeypatch.setattr(excel_upload, "relative_path", lambda path: str(path))
    response = create_app().test_client().post(
        "/api/upload/excel-lakehouse",
        data={
            "upload_mode": "single",
            "file_excel[]": [(io.BytesIO(_xlsx_bytes()), "rab_missing_metadata.xlsx")],
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "Tahun Input" in response.get_json()["message"]
