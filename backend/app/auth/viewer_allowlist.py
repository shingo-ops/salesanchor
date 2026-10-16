"""閲覧者のトークンで呼べるルートの一覧（ADR-1019 段1）。

test_viewer_isolation.py は、これ以外のすべてのルートが閲覧者のトークンで 401 になることを確かめる。
ルートを足すときは、ここと test_viewer_isolation.py の両方を見ること。
"""

from __future__ import annotations

VIEWER_ROUTE_ALLOWLIST: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/api/v1/viewer/signup"),
        ("POST", "/api/v1/viewer/login"),
        ("POST", "/api/v1/viewer/logout"),
        ("GET", "/api/v1/viewer/inventory"),
        ("POST", "/api/v1/viewer/password"),
        ("POST", "/api/v1/viewer/password-reset/request"),
        ("POST", "/api/v1/viewer/password-reset/confirm"),
    }
)
