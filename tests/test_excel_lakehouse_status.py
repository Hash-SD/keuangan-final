from __future__ import annotations

import json

from portal_backend.services import excel_lakehouse


def test_status_does_not_report_stale_counts_when_canonical_artifacts_are_missing(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    (data_dir / "generated").mkdir(parents=True)
    (data_dir / "generated" / "excel_lakehouse_metadata.json").write_text(
        json.dumps({"bronze_cells": 55340, "silver_rab_items": 393, "silver_nomenklatur_detail": 248, "fact_anggaran_rows": 607}),
        encoding="utf-8",
    )
    monkeypatch.setattr(excel_lakehouse, "DATA_DIR", data_dir)
    monkeypatch.setattr(excel_lakehouse, "OUTPUTS_DIR", outputs_dir)
    monkeypatch.setattr(excel_lakehouse, "ROOT_DIR", tmp_path)

    result = excel_lakehouse.excel_lakehouse_status()

    assert result["status"] == "missing"
    assert result["counts"] == {"bronze_cells": None, "silver_rab_items": None, "nomenklatur_detail": None, "fact_anggaran_rows": None}


def test_status_falls_back_to_gold_csv_for_fact_totals(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    generated = data_dir / "generated"
    gold = generated / "gold"
    gold.mkdir(parents=True)
    (generated / "excel_lakehouse_metadata.json").write_text(
        json.dumps({"fact_anggaran_rows": 2}), encoding="utf-8"
    )
    for name in ("bronze_excel_cells", "silver_rab_items_flexible", "silver_nomenklatur_detail", "silver_mapping", "silver_validation"):
        path = generated / ("bronze" if name.startswith("bronze") else "silver") / f"{name}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"placeholder")
    (gold / "fact_anggaran.parquet").write_bytes(b"placeholder")
    (gold / "fact_anggaran.csv").write_text(
        "jumlah,jumlah_weighted_iku\n100,40\n200,60\n", encoding="utf-8"
    )
    monkeypatch.setattr(excel_lakehouse, "DATA_DIR", data_dir)
    monkeypatch.setattr(excel_lakehouse, "OUTPUTS_DIR", outputs_dir)
    monkeypatch.setattr(excel_lakehouse, "ROOT_DIR", tmp_path)

    result = excel_lakehouse.excel_lakehouse_status()

    assert result["fact_anggaran"] == {"total_anggaran": 100.0, "jumlah_item": 2, "jumlah_iku": 0, "jumlah_kegiatan": 0, "status_rekonsiliasi": "CHECK"}


def test_status_summarizes_active_dataset_session_only(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    generated = data_dir / "generated"
    gold = generated / "gold"
    gold.mkdir(parents=True)
    (generated / "excel_lakehouse_metadata.json").write_text(
        json.dumps(
            {
                "dataset_session_id": "current-session",
                "run_id": "current-run",
                "fact_anggaran_rows": 1,
            }
        ),
        encoding="utf-8",
    )
    for name in (
        "bronze_excel_cells",
        "silver_rab_items_flexible",
        "silver_nomenklatur_detail",
        "silver_mapping",
        "silver_validation",
    ):
        path = generated / ("bronze" if name.startswith("bronze") else "silver") / f"{name}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"placeholder")
    (gold / "fact_anggaran.parquet").write_bytes(b"placeholder")
    (gold / "fact_anggaran.csv").write_text(
        "item_id,jumlah,jumlah_weighted_iku,dataset_session_id,run_id\n"
        "old-item,100,100,old-session,old-run\n"
        "current-item,200,200,current-session,current-run\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(excel_lakehouse, "DATA_DIR", data_dir)
    monkeypatch.setattr(excel_lakehouse, "OUTPUTS_DIR", outputs_dir)
    monkeypatch.setattr(excel_lakehouse, "ROOT_DIR", tmp_path)

    result = excel_lakehouse.excel_lakehouse_status()

    assert result["fact_anggaran"] == {"total_anggaran": 200.0, "jumlah_item": 1, "jumlah_iku": 0, "jumlah_kegiatan": 0, "status_rekonsiliasi": "OK"}


def test_status_reads_gold_csv_when_parquet_is_absent(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    generated = data_dir / "generated"
    gold = generated / "gold"
    gold.mkdir(parents=True)
    (generated / "excel_lakehouse_metadata.json").write_text(json.dumps({"fact_anggaran_rows": 1}), encoding="utf-8")
    for name in ("bronze_excel_cells", "silver_rab_items_flexible", "silver_nomenklatur_detail", "silver_mapping", "silver_validation"):
        path = generated / ("bronze" if name.startswith("bronze") else "silver") / f"{name}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"placeholder")
    (gold / "fact_anggaran.csv").write_text("jumlah,jumlah_weighted_iku\n75,25\n", encoding="utf-8")
    monkeypatch.setattr(excel_lakehouse, "DATA_DIR", data_dir)
    monkeypatch.setattr(excel_lakehouse, "OUTPUTS_DIR", outputs_dir)
    monkeypatch.setattr(excel_lakehouse, "ROOT_DIR", tmp_path)

    result = excel_lakehouse.excel_lakehouse_status()

    assert result["fact_anggaran"] == {"total_anggaran": 25.0, "jumlah_item": 1, "jumlah_iku": 0, "jumlah_kegiatan": 0, "status_rekonsiliasi": "CHECK"}
