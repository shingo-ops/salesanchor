from types import SimpleNamespace

from starlette.datastructures import Headers

from app.security.client_ip import get_trusted_client_ip


class DummyRequest:
    def __init__(self, headers: dict[str, str] | None = None, host: str | None = "127.0.0.1"):
        self.headers = Headers(headers or {})
        self.client = SimpleNamespace(host=host) if host is not None else None


def test_trusted_client_ip_prefers_x_real_ip_over_spoofed_x_forwarded_for():
    request = DummyRequest(
        headers={
            "X-Real-IP": "203.0.113.10",
            "X-Forwarded-For": "1.2.3.4, 203.0.113.10",
        },
        host="172.18.0.5",
    )

    assert get_trusted_client_ip(request) == "203.0.113.10"


def test_trusted_client_ip_ignores_x_forwarded_for_without_x_real_ip():
    request = DummyRequest(
        headers={"X-Forwarded-For": "1.2.3.4"},
        host="172.18.0.5",
    )

    assert get_trusted_client_ip(request) == "172.18.0.5"


def test_trusted_client_ip_returns_unknown_without_proxy_or_client():
    request = DummyRequest(headers={}, host=None)

    assert get_trusted_client_ip(request) == "unknown"
