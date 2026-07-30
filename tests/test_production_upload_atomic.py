from __future__ import annotations

import io
import json

import pytest
from openpyxl import Workbook
from werkzeug.datastructures import FileMultiDict, FileStorage, MultiDict

from portal_backend.services import excel_upload


def _workbook_bytes() -> bytes:
    book = Workbook()
    book.active.append(["akun", "jumlah"])
    stream = io.BytesIO()
    book.save(stream)
    return stream.getvalue()


def _files(*items: tuple[str, bytes]) -> FileMultiDict:
    result = FileMultiDict()
    for filename, contents in items:
        result.add("file_excel[]", FileStorage(io.BytesIO(contents), filename=filename))
    return result


def test_corrupt_bundle_rolls_back_staging_and_preserves_active_dataset(tmp_path, monkeypatch):
    active_path = tmp_path / "outputs/reports/active_excel_lakehouse_dataset.json"
    active_path.parent.mkdir(parents=True)
    active_path.write_text(json.dumps({"dataset_id": "old", "status": "committed"}), encoding="utf-8")
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", active_path)
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", tmp_path / "outputs/reports/registry.json")
    monkeypatch.setattr(excel_upload, "relative_path", lambda path: str(path))

    with pytest.raises(ValueError, match="dibuka"):
        excel_upload.commit_excel_lakehouse_dataset(
            MultiDict({"tahun_input": "2025"}),
            _files(("valid.xlsx", _workbook_bytes()), ("corrupt.xlsx", b"not an excel workbook")),
        )

    assert json.loads(active_path.read_text(encoding="utf-8"))["dataset_id"] == "old"
    assert not list((tmp_path / "data/uploads/staging").rglob("*"))


def test_committed_upload_records_hashes_and_validation_status(tmp_path, monkeypatch):
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "outputs/reports/active.json")
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", tmp_path / "outputs/reports/registry.json")
    monkeypatch.setattr(excel_upload, "relative_path", lambda path: str(path))

    result = excel_upload.commit_excel_lakehouse_dataset(MultiDict({"tahun_input": "2025"}), _files(("rab.xlsx", _workbook_bytes())))

    assert result["status"] == "committed"
    assert result["validation_status"] == "VALIDATED"
    assert result["files"][0]["sha256"]
    assert result["files"][0]["workbook_openable"] is True


def test_nomenklatur_append_keeps_existing_rab_in_active_session(tmp_path, monkeypatch):
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "outputs/reports/active.json")
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", tmp_path / "outputs/reports/registry.json")
    monkeypatch.setattr(excel_upload, "relative_path", lambda path: str(path))

    first = excel_upload.commit_excel_lakehouse_dataset(MultiDict({"tahun_input": "2025", "jenis_dataset": "rab"}), _files(("rab.xlsx", _workbook_bytes())))
    second = excel_upload.commit_excel_lakehouse_dataset(MultiDict({"tahun_input": "2025", "jenis_dataset": "nomenklatur", "append_to_active": "true"}), _files(("nomenklatur.xlsx", _workbook_bytes())))

    assert second["dataset_session_id"] == first["dataset_session_id"]
    assert {item["jenis_dataset"] for item in second["files"]} == {"rab", "nomenklatur"}
