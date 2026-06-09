from __future__ import annotations

from src.storage import storage_manifest


def _patch_storage(tmp_path, monkeypatch):
    outputs = tmp_path / "outputs"
    reports = outputs / "reports"
    metrics = outputs / "metrics"
    data = tmp_path / "data"
    definitions = {
        "staging": {"local_path": data / "uploads" / "staging", "prefix": "staging", "ready_when": "exists"},
        "raw": {"local_path": data / "raw", "prefix": "raw", "ready_when": "files"},
        "bronze": {"local_path": data / "generated" / "bronze", "prefix": "bronze", "ready_when": "files"},
        "silver": {"local_path": data / "generated" / "silver", "prefix": "silver", "ready_when": "files"},
        "gold": {"local_path": data / "generated" / "gold", "prefix": "gold", "ready_when": "files"},
        "quarantine": {"local_path": data / "quarantine", "prefix": "quarantine", "ready_when": "exists"},
        "manifests": {"local_path": reports, "prefix": "manifests", "ready_when": "exists"},
        "metrics": {"local_path": metrics, "prefix": "metrics", "ready_when": "files"},
        "reports": {"local_path": reports, "prefix": "reports", "ready_when": "exists"},
        "iceberg_warehouse": {"local_path": None, "prefix": "warehouse", "ready_when": "configured"},
    }
    for layer, definition in definitions.items():
        path = definition["local_path"]
        if path is not None:
            path.mkdir(parents=True, exist_ok=True)
            if definition["ready_when"] == "files":
                (path / f"{layer}.txt").write_text(layer, encoding="utf-8")
    monkeypatch.setattr(storage_manifest, "LAYER_DEFINITIONS", definitions)
    monkeypatch.setattr(storage_manifest, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(storage_manifest, "DATA_DIR", data)
    monkeypatch.setattr(storage_manifest, "build_system_truth_status", lambda write_outputs=True: {})


def test_storage_lineage_complete(tmp_path, monkeypatch):
    _patch_storage(tmp_path, monkeypatch)
    monkeypatch.setenv("MINIO_UPLOAD_ENABLED", "false")

    manifest = storage_manifest.generate_storage_manifest()
    transitions = {(item["from_layer"], item["to_layer"]): item["status"] for item in manifest["lineage"]}

    assert transitions == {
        ("staging", "raw"): "complete",
        ("raw", "bronze"): "complete",
        ("bronze", "silver"): "complete",
        ("silver", "gold"): "complete",
    }
    assert (tmp_path / "outputs" / "reports" / "storage_layers_status.json").exists()
