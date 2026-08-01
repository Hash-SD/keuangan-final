from __future__ import annotations

import threading
import urllib.request
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Iterator

from portal.server import PortalHandler


ROOT = Path(__file__).resolve().parents[1]
PORTAL_DIR = ROOT / "portal"
V2_INDEX = PORTAL_DIR / "v2" / "index.html"
COMPOSE = ROOT / "docker-compose.yml"


@contextmanager
def _portal_server() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), PortalHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _get(path: str) -> str:
    with _portal_server() as base_url:
        with urllib.request.urlopen(f"{base_url}{path}", timeout=5) as response:
            assert response.status == 200
            assert response.headers.get_content_type() == "text/html"
            return response.read().decode("utf-8").replace("\r\n", "\n")


def _html(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_static_root_serves_v2_index() -> None:
    assert _get("/") == _html(V2_INDEX)


def test_static_legacy_aliases_v2_index() -> None:
    assert _get("/legacy") == _html(V2_INDEX)


def test_static_v2_route_serves_v2_index() -> None:
    assert _get("/v2/") == _html(V2_INDEX)


def test_compose_frontend_uses_portal_static_server() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")

    assert "command: -m portal.server" in compose
    assert "--directory portal" not in compose
