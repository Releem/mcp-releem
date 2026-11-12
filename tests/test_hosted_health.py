"""Probe a real loopback server; never contact Releem."""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from test_foundation import module


@pytest.mark.parametrize(
    "status,body,expected",
    [
        (200, b'{"status":"alive"}', 0),
        (503, b'{"status":"alive"}', 1),
        (200, b"not-json", 1),
        (200, b'{"status":"ready"}', 1),
        (302, b"", 1),
        (200, b"x" * 1024, 1),
    ],
)
def test_probe_uses_public_host_and_validates_liveness(status, body, expected):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append((self.path, self.headers.get("Host"), self.headers.get("Authorization")))
            self.send_response(status)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    try:
        settings = module("hosted.config").HostedSettings.from_env(
            {
                "RELEEM_MCP_PROFILE": "hosted",
                "RELEEM_MCP_PUBLIC_URL": "https://mcp.example.invalid/mcp",
                "RELEEM_MCP_PORT": str(server.server_port),
            }
        )
        assert module("hosted.health").check(settings) == expected
        assert calls == [("/healthz", "mcp.example.invalid", None)]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_probe_failure_is_sanitized(monkeypatch, capsys):
    monkeypatch.setenv("RELEEM_MCP_PROFILE", "hosted")
    monkeypatch.setenv("RELEEM_MCP_PUBLIC_URL", "https://synthetic-sensitive.invalid/mcp")
    monkeypatch.setenv("RELEEM_SECRET_KEY", "synthetic-never-log")
    assert module("hosted.health").main() == 1
    captured = capsys.readouterr()
    assert "synthetic" not in captured.out + captured.err
