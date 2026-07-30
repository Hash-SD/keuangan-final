from __future__ import annotations

from pathlib import Path


PORTAL_INDEX = Path(__file__).resolve().parents[1] / "portal" / "index.html"


def _html() -> str:
    return PORTAL_INDEX.read_text(encoding="utf-8")


def test_portal_api_base_supports_local_alt_port_and_external_config():
    html = _html()

    assert "SILARAS_API_BASE_URL" in html
    assert "api_base" in html
    assert 'window.location.port === "8190"' in html
    assert '"http://localhost:8191"' in html


def test_uat_form_keeps_draft_across_background_refresh():
    html = _html()

    assert 'const UAT_DRAFT_KEY = "portal_uat_draft"' in html
    assert "persistUATDraftFromDom" in html
    assert "applyUATDraft();" in html
    assert 'route === "analytics" && hasUATDraft()' in html
    assert 'apiPost("/api/uat/submit", { mode: "local_feedback", ...entry })' in html


def test_upload_and_run_show_inline_status_and_use_full_pipeline():
    html = _html()

    assert "apiUpload(" in html
    assert "upload.onprogress" in html
    assert "setUploadInlineStatus" in html
    assert 'apiPost("/api/pipeline/full-run", { mode: "local-basic" })' in html
    assert "appendRuntimeContext(formData)" in html


def test_upload_is_guarded_by_production_readiness():
    html = _html()

    assert "/api/production/readiness" in html
    assert "Upload dinonaktifkan sampai production release gate lulus" in html


def test_upload_session_is_reloaded_on_every_data_page_render():
    html = _html()

    assert 'apiGet("/api/upload/session/status")' in html
    assert "state.datasetSession = datasetSession" in html
