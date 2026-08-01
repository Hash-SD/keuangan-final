from portal_backend.app import create_app


def test_mutating_api_requires_configured_token_when_auth_is_enabled(monkeypatch):
    monkeypatch.setenv("PORTAL_AUTH_REQUIRED", "true")
    monkeypatch.setenv("PORTAL_API_TOKEN", "test-token")

    response = create_app().test_client().post("/api/uat/submit", json={})

    assert response.status_code == 401
    assert response.get_json()["status"] == "failed"


def test_mutating_api_accepts_bearer_token_when_auth_is_enabled(monkeypatch, tmp_path):
    from portal_backend import app as app_module

    monkeypatch.setenv("PORTAL_AUTH_REQUIRED", "true")
    monkeypatch.setenv("PORTAL_API_TOKEN", "test-token")
    monkeypatch.setattr(app_module, "OUTPUTS_DIR", tmp_path / "outputs")

    response = create_app().test_client().post(
        "/api/uat/submit",
        headers={"Authorization": "Bearer test-token"},
        json={},
    )

    assert response.status_code == 200


def test_auth_enabled_without_deployment_token_fails_closed(monkeypatch, tmp_path):
    from portal_backend import app as app_module

    monkeypatch.setenv("PORTAL_AUTH_REQUIRED", "true")
    monkeypatch.delenv("PORTAL_API_TOKEN", raising=False)
    monkeypatch.setattr(app_module, "OUTPUTS_DIR", tmp_path / "outputs")

    client = create_app().test_client()
    upload = client.post("/api/uat/submit", json={})

    assert upload.status_code == 503
    assert "PORTAL_API_TOKEN" in upload.get_json()["message"]


def test_airflow_auth_uses_defaults_for_blank_environment(monkeypatch):
    from portal_backend.services import airflow

    monkeypatch.setenv("AIRFLOW_USERNAME", " ")
    monkeypatch.setenv("AIRFLOW_PASSWORD", "")

    assert airflow._auth() == ("airflow", "airflow")
