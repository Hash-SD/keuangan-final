from __future__ import annotations

from pathlib import Path

from portal_backend.app import create_app


ROOT = Path(__file__).resolve().parents[1]
PORTAL_DIR = ROOT / "portal"
V2_INDEX = PORTAL_DIR / "v2" / "index.html"


def _normalized_html(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_root_serves_v2_portal_index() -> None:
    response = create_app().test_client().get("/")

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert response.get_data(as_text=True).replace("\r\n", "\n") == _normalized_html(V2_INDEX)


def test_legacy_route_aliases_v2_portal_index() -> None:
    response = create_app().test_client().get("/legacy")

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert response.get_data(as_text=True).replace("\r\n", "\n") == _normalized_html(V2_INDEX)


def test_v2_route_remains_directly_accessible() -> None:
    response = create_app().test_client().get("/v2/")

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert response.get_data(as_text=True).replace("\r\n", "\n") == _normalized_html(V2_INDEX)


def test_health_api_still_returns_json_after_static_route_changes() -> None:
    response = create_app().test_client().get("/api/health")

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert response.get_json() == {
        "status": "ok",
        "service": "portal-backend",
        "mode": "local-on-premise",
        "basis": "excel_lakehouse_fact_anggaran",
    }
