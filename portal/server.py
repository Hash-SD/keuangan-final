from __future__ import annotations

import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class PortalHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, directory=str(Path(__file__).resolve().parent), **kwargs
        )

    def end_headers(self) -> None:
        request_path = self.path.split("?", 1)[0]
        if request_path.startswith("/local-dashboard/") or request_path in {
            "/",
            "/index.html",
            "/v2",
            "/v2/",
            "/v2/index.html",
        }:
            self.send_header(
                "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
            )
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        elif self._is_static_asset(request_path):
            self.send_header("Cache-Control", "public, max-age=86400")
            self.send_header("Pragma", "no-cache")
        super().end_headers()

    @staticmethod
    def _is_static_asset(path: str) -> bool:
        return path.lower().endswith(
            (
                ".css",
                ".js",
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".svg",
                ".ico",
                ".woff",
                ".woff2",
                ".ttf",
                ".eot",
                ".webp",
                ".avif",
            )
        )

    def do_GET(self) -> None:
        request_path = self.path.split("?", 1)[0]
        if request_path in {"/", "/index.html", "/legacy", "/legacy/", "/legacy/index.html"}:
            self.path = "/v2/index.html"
        super().do_GET()


def main() -> None:
    host = os.getenv("PORTAL_BIND_HOST") or os.getenv("PORTAL_HOST") or "0.0.0.0"
    port = int(os.getenv("PORTAL_PORT", "8090"))
    server = ThreadingHTTPServer((host, port), PortalHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
