"""書き込みルートと topic 対応表の整合（ADR-1016）。新しい書き込みルートは表に載せるまで赤になる。"""
from __future__ import annotations

import re
from pathlib import Path

from app.realtime.topics import (
    NO_SIGNAL_ROUTES,
    SCOPE_GLOBAL,
    SCOPE_SHARED,
    TASK_TOPICS,
    TOPIC_TCG_INVENTORY,
    WRITE_ROUTE_TOPICS,
)

_WRITE = {"POST", "PUT", "PATCH", "DELETE"}


def _write_routes():
    # 遅延 import: 収集時に app.main を読むと、全権限モック(conftest bypass_permissions)の前に
    # inventory_search が本物の load_user_permissions を束縛し、他の試験が 403 になる
    from app.main import app

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
    backend = {t for t, _s in WRITE_ROUTE_TOPICS.values()} | set(TASK_TOPICS)
    ts = Path(__file__).resolve().parents[2] / "frontend/src/lib/realtime/topics.ts"
    frontend = set(re.findall(r':\s*"([a-z0-9_.]+)"', ts.read_text(encoding="utf-8")))
    assert frontend == backend


def test_task_topics_are_shared_or_global():
    # 会社 ID の無い裏の処理から tenant 範囲の合図は出せない
    for topic, scope in TASK_TOPICS.items():
        assert scope in (SCOPE_SHARED, SCOPE_GLOBAL), f"{topic}: {scope}"


def test_write_routes_have_no_shared_scope():
    # shared は TASK_TOPICS に明記した topic だけ
    bad = {k: v for k, v in WRITE_ROUTE_TOPICS.items() if v[1] == SCOPE_SHARED}
    assert not bad, f"書き込みルートに shared がある: {sorted(bad)}"


def test_channel_for_shared():
    from app.realtime.publisher import CHANNEL_SHARED, _channel_for

    assert CHANNEL_SHARED == "rt:shared"
    assert _channel_for("shared", None) == "rt:shared"


def test_publish_review_changed_emits_review_and_inventory(monkeypatch):
    import app.realtime.publisher as pub
    from app.tasks.tcg_extraction import _publish_review_changed

    sent = []
    monkeypatch.setattr(pub, "publish_change_sync", lambda *a, **k: sent.append(a))
    _publish_review_changed()
    assert sent == [("tcg.review", "global"), (TOPIC_TCG_INVENTORY, "shared")]
