from portal_backend.services import pipeline


def test_full_run_uses_excel_steps_when_uploads_are_active(monkeypatch):
    monkeypatch.setattr(pipeline, "active_dataset_pointer", lambda: {"status": "committed"})

    assert pipeline._full_run_steps() == [
        "excel-lakehouse",
        "excel-count-validation",
        "excel-storage-manifest",
        "load-gold-postgres",
        "superset-excel",
        "truth-status",
    ]


def test_full_run_stays_excel_only_without_uploads(monkeypatch):
    monkeypatch.setattr(pipeline, "active_dataset_pointer", lambda: None)

    assert pipeline._full_run_steps()[0] == "excel-lakehouse"


def test_full_run_rejects_nomenklatur_only_dataset(monkeypatch):
    monkeypatch.setattr(pipeline, "read_json", lambda _path: {"status": "committed", "files": [{"jenis_dataset": "nomenklatur"}]})

    result = pipeline.run_full("local-basic")

    assert result["status"] == "failed"
    assert "RAB" in result["message"]
