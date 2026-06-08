from portal_backend.services import pipeline


def test_full_run_skips_dummy_generation_when_uploads_are_active(monkeypatch):
    monkeypatch.setattr(pipeline, "active_dataset_pointer", lambda: {"status": "committed"})

    assert pipeline._full_run_steps() == ["quality-gate", "bronze", "silver", "gold", "metrics"]


def test_full_run_uses_dummy_generation_without_uploads(monkeypatch):
    monkeypatch.setattr(pipeline, "active_dataset_pointer", lambda: None)

    assert pipeline._full_run_steps()[0] == "generate-data"
