from __future__ import annotations

import sys
import time
import os
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import OUTPUTS_DIR


BASE_URL = os.getenv("SUPERSET_BASE_URL", "http://localhost:8089")


def _request_with_wait(session: requests.Session, method: str, url: str, attempts: int = 30, **kwargs) -> requests.Response:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            response = session.request(method, url, timeout=kwargs.pop("timeout", 30), **kwargs)
            return response
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(3)
    raise RuntimeError(f"Superset API is not reachable after {attempts} attempts: {last_error}")


def main() -> None:
    session = requests.Session()
    login = _request_with_wait(
        session,
        "POST",
        f"{BASE_URL}/api/v1/security/login",
        json={"username": "admin", "password": "admin", "provider": "db", "refresh": True},
        timeout=30,
    )
    login.raise_for_status()
    token = login.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    csrf = _request_with_wait(session, "GET", f"{BASE_URL}/api/v1/security/csrf_token/", timeout=30)
    csrf.raise_for_status()
    session.headers.update({"X-CSRFToken": csrf.json()["result"]})

    uri = "trino://trino@trino:8080/iceberg/gold"
    db_payload = {
        "database_name": "Trino Iceberg Gold Keuangan",
        "sqlalchemy_uri": uri,
        "expose_in_sqllab": True,
        "allow_ctas": True,
        "allow_cvas": True,
        "allow_dml": False,
    }
    db_response = session.post(f"{BASE_URL}/api/v1/database/", json=db_payload, timeout=60)
    if db_response.status_code == 422:
        databases = session.get(f"{BASE_URL}/api/v1/database/", timeout=30).json()["result"]
        database_id = next(item["id"] for item in databases if item["database_name"] == db_payload["database_name"])
    else:
        db_response.raise_for_status()
        result = db_response.json().get("result", {})
        database_id = result.get("id")
        if database_id is None:
            databases = session.get(f"{BASE_URL}/api/v1/database/", timeout=30).json()["result"]
            database_id = next(item["id"] for item in databases if item["database_name"] == db_payload["database_name"])

    dataset_payload = {
        "database": database_id,
        "catalog": "iceberg",
        "schema": "gold",
        "table_name": "vw_dashboard_piutang_ukt",
    }
    dataset_response = session.post(f"{BASE_URL}/api/v1/dataset/", json=dataset_payload, timeout=60)
    if dataset_response.status_code == 422:
        datasets = session.get(f"{BASE_URL}/api/v1/dataset/?q=(filters:!((col:table_name,opr:eq,value:vw_dashboard_piutang_ukt)))", timeout=30).json()["result"]
        dataset_id = datasets[0]["id"] if datasets else None
        if dataset_id is not None:
            update_payload = {
                "database_id": database_id,
                "catalog": "iceberg",
                "schema": "gold",
                "table_name": "vw_dashboard_piutang_ukt",
            }
            update_response = session.put(f"{BASE_URL}/api/v1/dataset/{dataset_id}", json=update_payload, timeout=60)
            update_response.raise_for_status()
    else:
        dataset_response.raise_for_status()
        result = dataset_response.json().get("result", {})
        dataset_id = result.get("id")
        if dataset_id is None:
            datasets = session.get(f"{BASE_URL}/api/v1/dataset/?q=(filters:!((col:table_name,opr:eq,value:vw_dashboard_piutang_ukt)))", timeout=30).json()["result"]
            dataset_id = datasets[0]["id"] if datasets else None

    result = {"database_id": database_id, "dataset_id": dataset_id, "database_name": db_payload["database_name"], "table_name": "vw_dashboard_piutang_ukt"}
    write_json(OUTPUTS_DIR / "reports" / "superset_assets.json", result)
    print(result)


if __name__ == "__main__":
    main()
