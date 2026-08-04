from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.validation.dataset_contract import validate_committed_dataset


def _entry(path: Path, kind: str) -> dict[str, str]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"path": str(path), "sha256": digest, "jenis_dataset": kind}


def test_partial_committed_dataset_is_not_canonical(tmp_path):
    nomenklatur = tmp_path / "Nomenklatur.xlsx"
    nomenklatur.write_bytes(b"real-workbook-placeholder")
    result = validate_committed_dataset(
        {
            "status": "committed",
            "upload_state": "COMMITTED",
            "dataset_session_id": "excel-real-1",
            "files": [_entry(nomenklatur, "nomenklatur")],
        },
        tmp_path,
    )
    assert result["valid"] is False
    assert "dataset canonical wajib memiliki workbook RAB" in result["errors"]


def test_committed_dataset_requires_matching_hash_and_both_source_kinds(tmp_path):
    rab = tmp_path / "RAB_2025.xlsx"
    nomenklatur = tmp_path / "Nomenklatur.xlsx"
    rab.write_bytes(b"rab")
    nomenklatur.write_bytes(b"nomenklatur")
    payload = {
        "status": "committed",
        "upload_state": "COMMITTED",
        "dataset_session_id": "excel-real-2",
        "files": [_entry(rab, "rab"), _entry(nomenklatur, "nomenklatur")],
    }
    assert validate_committed_dataset(payload, tmp_path)["valid"] is True
    rab.write_bytes(b"tampered")
    result = validate_committed_dataset(payload, tmp_path)
    assert result["valid"] is False
    assert any("checksum file tidak cocok" in error for error in result["errors"])


def test_committed_dataset_recovers_mixed_bundle_when_category_metadata_is_wrong(tmp_path):
    rab_files = [
        tmp_path / "Rencana_Anggaran_Prodi_Sains_Data_Tahun_2024.xlsx",
        tmp_path / "RAB_2025_SD_RAB_IKU.xlsx",
        tmp_path / "RAB_SD_Usulan_KE_1_Jan-Jun_2023.xlsx",
        tmp_path / "RAB_SD_Usulan_KE_1_jul-des_2023.xlsx",
    ]
    nomenklatur = tmp_path / "Nomenklatur.xlsx"
    for path in [*rab_files, nomenklatur]:
        path.write_bytes(path.name.encode())

    payload = {
        "status": "committed",
        "upload_state": "COMMITTED",
        "dataset_session_id": "excel-mixed-bundle",
        "files": [_entry(path, "nomenklatur") for path in [*rab_files, nomenklatur]],
    }

    result = validate_committed_dataset(payload, tmp_path)

    assert result["valid"] is True
    assert result["kinds"] == ["nomenklatur", "rab"]
    assert [item["jenis_dataset"] for item in result["files"]] == [
        "rab",
        "rab",
        "rab",
        "rab",
        "nomenklatur",
    ]


def test_dataset_contract_result_is_json_serializable(tmp_path):
    rab = tmp_path / "RAB_2025.xlsx"
    nomenklatur = tmp_path / "Nomenklatur.xlsx"
    rab.write_bytes(b"rab")
    nomenklatur.write_bytes(b"nomenklatur")
    result = validate_committed_dataset(
        {
            "status": "committed",
            "upload_state": "COMMITTED",
            "dataset_session_id": "excel-real-3",
            "files": [_entry(rab, "rab"), _entry(nomenklatur, "nomenklatur")],
        },
        tmp_path,
    )
    json.dumps(result)


def test_production_contract_rejects_sources_outside_canonical_raw_root(tmp_path):
    raw_root = tmp_path / "data" / "raw" / "excel_lakehouse"
    raw_root.mkdir(parents=True)
    rab = tmp_path / "outputs" / "RAB_2025.xlsx"
    nomenklatur = tmp_path / "docs" / "Nomenklatur.xlsx"
    rab.parent.mkdir()
    nomenklatur.parent.mkdir()
    rab.write_bytes(b"rab")
    nomenklatur.write_bytes(b"nomenklatur")

    result = validate_committed_dataset(
        {
            "status": "committed",
            "upload_state": "COMMITTED",
            "dataset_session_id": "excel-real-4",
            "files": [_entry(rab, "rab"), _entry(nomenklatur, "nomenklatur")],
        },
        tmp_path,
    )

    assert result["valid"] is False
    assert any("canonical raw" in error for error in result["errors"])
