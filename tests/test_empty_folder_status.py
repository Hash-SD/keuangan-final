from __future__ import annotations

from pathlib import Path

from src.status.system_truth_status import build_system_truth_status
from src.storage.storage_manifest import _layer_status


def test_storage_manifest_empty_folder_is_empty(tmp_path: Path):
    empty_layer = tmp_path / "bronze"
    empty_layer.mkdir()

    assert _layer_status(empty_layer, "files", 0) == "empty"


def test_system_truth_source_empty_folder_is_empty(tmp_path: Path, monkeypatch):
    raw_pdf = tmp_path / "data" / "raw" / "pdf"
    raw_pdf.mkdir(parents=True)
    (tmp_path / "data" / "raw" / "csv").mkdir(parents=True)
    (tmp_path / "data" / "raw" / "excel").mkdir(parents=True)

    monkeypatch.chdir(tmp_path)
    truth = build_system_truth_status(base_dir=tmp_path, write_outputs=False)

    assert truth["sources"]["excel_lakehouse"]["status"] == "empty"
    assert truth["sources"]["legacy_pdf_csv"]["status"] == "not_available"


def test_system_truth_includes_staging_layer(tmp_path: Path, monkeypatch):
    staging = tmp_path / "data" / "uploads" / "staging" / "session-001"
    staging.mkdir(parents=True)
    (staging / "context.json").write_text("{}", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    truth = build_system_truth_status(base_dir=tmp_path, write_outputs=False)

    assert truth["layers"]["staging"]["status"] == "ready"
