"""書き込みルートと topic 対応表の整合（ADR-1016）。新しい書き込みルートは表に載せるまで赤になる。"""
from __future__ import annotations

import re
from pathlib import Path

from app.main import app
from app.realtime.topics import NO_SIGNAL_ROUTES, SCOPE_GLOBAL, WRITE_ROUTE_TOPICS

_WRITE = {"POST", "PUT", "PATCH", "DELETE"}


def _write_routes():
    out = {}
    for r in app.routes:
        methods = getattr(r, "methods", None)
        if not methods:
            continue
        for m in methods & _WRITE:
            out[(m, r.path)] = r
    return out


def test_every_write_route_is_in_exactly_one_table():
    routes = _write_routes()
    both = set(WRITE_ROUTE_TOPICS) & set(NO_SIGNAL_ROUTES)
    assert not both, f"両方の表に載っている: {sorted(both)}"
    missing = sorted(set(routes) - set(WRITE_ROUTE_TOPICS) - set(NO_SIGNAL_ROUTES))
    assert not missing, f"どちらの表にも無い書き込みルート: {missing}"


def test_tables_have_no_nonexistent_routes():
    routes = set(_write_routes())
    ghost = sorted((set(WRITE_ROUTE_TOPICS) | set(NO_SIGNAL_ROUTES)) - routes)
    assert not ghost, f"存在しないルートが表にある: {ghost}"


def test_super_admin_write_routes_in_signal_table_are_global():
    from app.auth.dependencies import require_super_admin

    def _deps(dep):
        yield dep.call
        for sub in dep.dependencies:
            yield from _deps(sub)

    routes = _write_routes()
    for key, (_topic, scope) in WRITE_ROUTE_TOPICS.items():
        calls = list(_deps(routes[key].dependant))
        if require_super_admin in calls:
            assert scope == SCOPE_GLOBAL, f"super admin 専用なのに global でない: {key}"


def test_frontend_topic_names_match_backend():
    backend = {t for t, _s in WRITE_ROUTE_TOPICS.values()}
    ts = Path(__file__).resolve().parents[2] / "frontend/src/lib/realtime/topics.ts"
    frontend = set(re.findall(r':\s*"([a-z0-9_.]+)"', ts.read_text(encoding="utf-8")))
    assert frontend == backend
