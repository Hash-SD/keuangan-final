from __future__ import annotations

import io

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
    assert payload["excel_only"] is True
    assert len(payload["files"]) == 2
    assert payload["upload_scope"] == "single_year"
    assert payload["detected_years"] == ["2025"]
    assert payload["has_nomenklatur"] is False
    assert payload["warnings"]
    assert excel_upload.ACTIVE_EXCEL_DATASET_PATH.exists()
