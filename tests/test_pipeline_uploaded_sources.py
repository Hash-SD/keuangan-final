from portal_backend.services import pipeline


def test_full_run_skips_dummy_generation_when_uploads_are_active(monkeypatch):
    monkeypatch.setattr(pipeline, "upload_registry", lambda: {"active": {"pdf": {"path": "data/raw/pdf/uploaded.pdf"}}})

    assert pipeline._full_run_steps() == ["quality-gate", "bronze", "silver", "gold", "metrics"]


def test_full_run_uses_dummy_generation_without_uploads(monkeypatch):
    monkeypatch.setattr(pipeline, "upload_registry", lambda: {"active": {}})

    assert pipeline._full_run_steps()[0] == "generate-data"
