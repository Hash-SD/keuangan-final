from __future__ import annotations

import json
from pathlib import Path

from src.status import system_truth_status


def _write_read_only(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o444)


def test_system_truth_replaces_read_only_status_outputs(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(system_truth_status, "_service_statuses", lambda base_dir: {})

    output_files = {
        tmp_path / "outputs" / "metrics" / "pipeline_latency.json": "{}",
        tmp_path / "outputs" / "reports" / "system_truth_status.json": "{}",
        tmp_path / "outputs" / "reports" / "bab4_evidence_summary.json": "{}",
        tmp_path / "outputs" / "reports" / "system_truth_status.csv": "old,status\n",
    }
    for path, content in output_files.items():
        _write_read_only(path, content)

    truth = system_truth_status.build_system_truth_status(
        base_dir=tmp_path,
        write_outputs=True,
    )

    assert truth["dataset_mode"] == "uploaded_excel"
    assert json.loads(
        (tmp_path / "outputs" / "metrics" / "pipeline_latency.json").read_text(encoding="utf-8")
    )["status"] == "not_available"
    assert json.loads(
        (tmp_path / "outputs" / "reports" / "system_truth_status.json").read_text(encoding="utf-8")
    )["dataset_mode"] == "uploaded_excel"
    assert json.loads(
        (tmp_path / "outputs" / "reports" / "bab4_evidence_summary.json").read_text(encoding="utf-8")
    )["status"] == "not_available"
    assert "component,status,source,message" in (
        tmp_path / "outputs" / "reports" / "system_truth_status.csv"
    ).read_text(encoding="utf-8")
