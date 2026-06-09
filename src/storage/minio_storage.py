from __future__ import annotations

from src.storage.storage_manifest import (
    LAYER_DEFINITIONS,
    StorageConfig,
    generate_storage_manifest,
)


def minio_layer_prefixes(bucket: str = "lakehouse") -> dict[str, str]:
    return {
        layer: f"s3://{bucket}/{definition['prefix']}/"
        for layer, definition in LAYER_DEFINITIONS.items()
    }
