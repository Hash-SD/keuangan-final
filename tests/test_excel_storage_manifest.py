from __future__ import annotations

from src.storage import excel_storage_manifest


def test_excel_storage_manifest_maps_required_prefixes(tmp_path, monkeypatch):
    data = tmp_path / "data"
    outputs = tmp_path / "outputs"
    (data / "generated" / "gold").mkdir(parents=True)
    (data / "generated" / "gold" / "fact_anggaran.csv").write_text("item_id,jumlah\n1,100\n", encoding="utf-8")
    (outputs / "reports").mkdir(parents=True)
    (outputs / "reports" / "pipeline_run_summary.json").write_text('{"run_id":"run-test"}', encoding="utf-8")

    monkeypatch.setattr(excel_storage_manifest, "DATA_DIR", data)
    monkeypatch.setattr(excel_storage_manifest, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(excel_storage_manifest, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(
        excel_storage_manifest,
        "LAYERS",
        {
            "raw": data / "raw",
            "bronze": data / "generated" / "bronze",
            "silver": data / "generated" / "silver",
            "gold": data / "generated" / "gold",
            "reports": outputs / "reports",
            "logs": outputs / "logs",
        },
    )
    monkeypatch.setattr(excel_storage_manifest, "UPLOAD_ENABLED", False)

    manifest = excel_storage_manifest.build_excel_storage_manifest()

    assert manifest["run_id"] == "run-test"
    assert "s3://lakehouse/gold/" in manifest["required_prefixes"]
    assert any(item["local_path"] == "data/generated/gold/fact_anggaran.csv" for item in manifest["entries"])
    assert {item["upload_status"] for item in manifest["entries"]} == {"mapped_not_uploaded"}
