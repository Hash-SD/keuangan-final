import json
from pathlib import Path

from src.storage.storage_manifest import generate_storage_manifest


ROOT = Path(__file__).resolve().parents[1]


def test_storage_manifest_outputs_required_layers(monkeypatch):
    monkeypatch.setenv("MINIO_UPLOAD_ENABLED", "false")
    manifest = generate_storage_manifest()
    mapping = json.loads((ROOT / "outputs" / "reports" / "storage_mapping.json").read_text(encoding="utf-8"))

    expected_layers = {"raw", "bronze", "silver", "gold", "quarantine", "metrics", "reports", "iceberg_warehouse"}
    assert set(mapping["layers"]) == expected_layers
    assert set(manifest["layers"]) == expected_layers
    assert mapping["storage_mode"] == "local_with_minio_mapping"
    assert manifest["upload"]["status"] == "skipped"
    assert mapping["layers"]["iceberg_warehouse"]["status"] == "configured"
    assert mapping["layers"]["bronze"]["s3_prefix"] == "s3://lakehouse/bronze/"
