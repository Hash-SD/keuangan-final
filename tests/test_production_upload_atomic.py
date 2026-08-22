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
    assert result["validation_status"] == "NEEDS_REVIEW"
    assert result["validation_errors"]
    assert result["files"][0]["sha256"]
    assert result["files"][0]["workbook_openable"] is True


def test_complete_rab_nomenklatur_bundle_is_validated_at_commit_boundary(tmp_path, monkeypatch):
    monkeypatch.setattr(excel_upload, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "outputs/reports/active.json")
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", tmp_path / "outputs/reports/registry.json")
    monkeypatch.setattr(excel_upload, "relative_path", lambda path: str(path.relative_to(tmp_path)).replace("\\", "/"))

    result = excel_upload.commit_excel_lakehouse_dataset(
        MultiDict({"tahun_input": "2025", "upload_mode": "multi"}),
        _files(("RAB_2025.xlsx", _workbook_bytes()), ("Nomenklatur.xlsx", _workbook_bytes())),
    )

    assert result["validation_status"] == "VALIDATED"
    assert result["validation_errors"] == []


def test_committed_upload_records_dashboard_target_choice(tmp_path, monkeypatch):
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "outputs/reports/active.json")
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", tmp_path / "outputs/reports/registry.json")
    monkeypatch.setattr(excel_upload, "relative_path", lambda path: str(path))

    result = excel_upload.commit_excel_lakehouse_dataset(
        MultiDict({"tahun_input": "2025", "dashboard_mode": "update", "dashboard_database_id": "3", "dashboard_dashboard_id": "2"}),
        _files(("rab.xlsx", _workbook_bytes())),
    )

    assert result["dashboard_mode"] == "update"
    assert result["dashboard_database_id"] == "3"
    assert result["dashboard_dashboard_id"] == "2"
    stored = json.loads((tmp_path / "outputs/reports/active.json").read_text(encoding="utf-8"))
    assert stored["dashboard_dashboard_id"] == "2"


def test_committed_upload_rejects_invalid_dashboard_target(tmp_path, monkeypatch):
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "OUTPUTS_DIR", tmp_path / "outputs")

    with pytest.raises(ValueError, match="Dashboard target Superset tidak valid"):
        excel_upload.commit_excel_lakehouse_dataset(
            MultiDict({"tahun_input": "2025", "dashboard_dashboard_id": "abc"}),
            _files(("rab.xlsx", _workbook_bytes())),
        )


def test_append_inherits_existing_dashboard_target_when_form_omits_it(tmp_path, monkeypatch):
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "outputs/reports/active.json")
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", tmp_path / "outputs/reports/registry.json")
    monkeypatch.setattr(excel_upload, "relative_path", lambda path: str(path))

    first = excel_upload.commit_excel_lakehouse_dataset(
        MultiDict(
            {
                "tahun_input": "2025",
                "dashboard_mode": "update",
                "dashboard_database_id": "3",
                "dashboard_dashboard_id": "2",
            }
        ),
        _files(("rab.xlsx", _workbook_bytes())),
    )
    second = excel_upload.commit_excel_lakehouse_dataset(
        MultiDict({"tahun_input": "2026", "append_to_active": "true"}),
        _files(("rab-2026.xlsx", _workbook_bytes())),
    )

    assert first["dashboard_database_id"] == "3"
    assert first["dashboard_dashboard_id"] == "2"
    assert second["dashboard_mode"] == "update"
    assert second["dashboard_database_id"] == "3"
    assert second["dashboard_dashboard_id"] == "2"


def test_new_dashboard_upload_clears_explicit_target_ids(tmp_path, monkeypatch):
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "outputs/reports/active.json")
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", tmp_path / "outputs/reports/registry.json")
    monkeypatch.setattr(excel_upload, "relative_path", lambda path: str(path))

    result = excel_upload.commit_excel_lakehouse_dataset(
        MultiDict(
            {
                "tahun_input": "2025",
                "dashboard_mode": "new",
                "dashboard_database_id": "3",
                "dashboard_dashboard_id": "2",
            }
        ),
        _files(("rab.xlsx", _workbook_bytes())),
    )

    assert result["dashboard_mode"] == "new"
    assert result["dashboard_database_id"] == "3"
    assert result["dashboard_dashboard_id"] is None


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


def test_same_kind_append_keeps_previous_files_when_uploading_one_by_one(tmp_path, monkeypatch):
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "outputs/reports/active.json")
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", tmp_path / "outputs/reports/registry.json")
    monkeypatch.setattr(excel_upload, "relative_path", lambda path: str(path))

    first = excel_upload.commit_excel_lakehouse_dataset(
        MultiDict({"tahun_input": "2026", "append_to_active": "true"}),
        _files(("RAB-Anggaran-2026.xlsx", _workbook_bytes())),
    )
    second = excel_upload.commit_excel_lakehouse_dataset(
        MultiDict({"tahun_input": "2027", "append_to_active": "true"}),
        _files(("RAB-Anggaran-2027.xlsx", _workbook_bytes())),
    )

    assert second["dataset_session_id"] == first["dataset_session_id"]
    assert [item["filename"] for item in second["files"]] == ["RAB-Anggaran-2026.xlsx", "RAB-Anggaran-2027.xlsx"]
    assert second["detected_years"] == ["2026", "2027"]
    assert second["upload_scope"] == "multi_year_bundle"


def test_same_kind_append_rejects_duplicate_filename(tmp_path, monkeypatch):
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "outputs/reports/active.json")
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", tmp_path / "outputs/reports/registry.json")
    monkeypatch.setattr(excel_upload, "relative_path", lambda path: str(path))

    excel_upload.commit_excel_lakehouse_dataset(
        MultiDict({"tahun_input": "2026", "append_to_active": "true"}),
        _files(("rab.xlsx", _workbook_bytes())),
    )
    with pytest.raises(ValueError, match="sudah ada pada dataset aktif"):
        excel_upload.commit_excel_lakehouse_dataset(
            MultiDict({"tahun_input": "2027", "append_to_active": "true"}),
            _files(("rab.xlsx", _workbook_bytes())),
        )
