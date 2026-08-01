from scripts.production_release_gate import credential_errors


def test_release_gate_rejects_default_credentials(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "lakehouse")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "minioadmin")
    monkeypatch.setenv("AIRFLOW_ADMIN_PASSWORD", "airflow")
    monkeypatch.setenv("SUPERSET_SECRET_KEY", "change_this_secret")

    errors = credential_errors()

    assert "default_credential:POSTGRES_PASSWORD" in errors
    assert "default_credential:MINIO_ROOT_PASSWORD" in errors
    assert "default_credential:AIRFLOW_ADMIN_PASSWORD" in errors
    assert "default_credential:SUPERSET_SECRET_KEY" in errors


def test_release_gate_accepts_non_default_credentials(monkeypatch):
    for name, value in {
        "POSTGRES_PASSWORD": "a-long-random-postgres-secret",
        "MINIO_ROOT_PASSWORD": "a-long-random-minio-secret",
        "AIRFLOW_ADMIN_PASSWORD": "a-long-random-airflow-secret",
        "SUPERSET_ADMIN_PASSWORD": "a-long-random-admin-secret",
        "SUPERSET_SECRET_KEY": "a-long-random-superset-secret",
    }.items():
        monkeypatch.setenv(name, value)

    assert credential_errors() == []
