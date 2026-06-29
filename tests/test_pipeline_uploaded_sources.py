from portal_backend.services import pipeline


def test_full_run_uses_excel_steps_when_uploads_are_active(monkeypatch):
    monkeypatch.setattr(pipeline, "active_dataset_pointer", lambda: {"status": "committed"})

    assert pipeline._full_run_steps() == ["excel-lakehouse", "excel-count-validation", "excel-storage-manifest", "superset-excel", "truth-status"]


def test_full_run_stays_excel_only_without_uploads(monkeypatch):
    monkeypatch.setattr(pipeline, "active_dataset_pointer", lambda: None)

    assert pipeline._full_run_steps()[0] == "excel-lakehouse"
