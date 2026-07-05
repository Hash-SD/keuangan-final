from __future__ import annotations

import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class PortalHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).resolve().parent), **kwargs)

    def end_headers(self) -> None:
        request_path = self.path.split("?", 1)[0]
        if request_path.startswith("/local-dashboard/") or request_path in {"/", "/index.html"}:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()


def main() -> None:
    host = os.getenv("PORTAL_BIND_HOST", "127.0.0.1")
    port = int(os.getenv("PORTAL_PORT", "8090"))
    server = ThreadingHTTPServer((host, port), PortalHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
