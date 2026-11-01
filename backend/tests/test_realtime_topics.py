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


def test_inventory_signal_routes_exist_and_are_writes():
    from app.realtime.topics import INVENTORY_SIGNAL_ROUTES

    routes = set(_write_routes())
    ghost = sorted(INVENTORY_SIGNAL_ROUTES - routes)
    assert not ghost, f"存在しない書き込みルートが在庫の表にある: {ghost}"
    assert all(m in _WRITE for m, _ in INVENTORY_SIGNAL_ROUTES)


_EXPECTED_INVENTORY_SIGNAL_ROUTES = {
    ("POST", "/api/v1/conditions"),
    ("POST", "/api/v1/conditions/import/commit"),
    ("DELETE", "/api/v1/conditions/{condition_id}"),
    ("PATCH", "/api/v1/conditions/{condition_id}"),
    ("POST", "/api/v1/products"),
    ("DELETE", "/api/v1/products/{product_id}"),
    ("PATCH", "/api/v1/products/{product_id}"),
    ("POST", "/api/v1/units"),
    ("POST", "/api/v1/units/import/commit"),
    ("DELETE", "/api/v1/units/{unit_id}"),
    ("PATCH", "/api/v1/units/{unit_id}"),
    ("POST", "/api/v1/super-admin/conditions"),
    ("POST", "/api/v1/super-admin/conditions/import/commit"),
    ("DELETE", "/api/v1/super-admin/conditions/{condition_id}"),
    ("PATCH", "/api/v1/super-admin/conditions/{condition_id}"),
    ("POST", "/api/v1/super-admin/suppliers"),
    ("POST", "/api/v1/super-admin/suppliers/import/commit"),
    ("DELETE", "/api/v1/super-admin/suppliers/{supplier_id}"),
    ("PATCH", "/api/v1/super-admin/suppliers/{supplier_id}"),
    ("POST", "/api/v1/super-admin/tcg/types"),
    ("DELETE", "/api/v1/super-admin/tcg/types/{type_id}"),
    ("PATCH", "/api/v1/super-admin/tcg/types/{type_id}"),
    ("POST", "/api/v1/super-admin/units"),
    ("POST", "/api/v1/super-admin/units/import/commit"),
    ("DELETE", "/api/v1/super-admin/units/{unit_id}"),
    ("PATCH", "/api/v1/super-admin/units/{unit_id}"),
    ("PUT", "/api/v1/tcg/distribution/settings/{key}"),
    ("POST", "/api/v1/tcg/extraction-jobs/{extraction_job_id}/reanalyze"),
    ("POST", "/api/v1/tcg/items/{extraction_item_id}/corrections"),
    ("POST", "/api/v1/tcg/items/{extraction_item_id}/review-ack"),
    ("POST", "/api/v1/tcg/items/{extraction_item_id}/review-ack/revoke"),
    ("POST", "/api/v1/tcg/items/{extraction_item_id}/value-override"),
    ("POST", "/api/v1/tcg/line-devices/import"),
    ("POST", "/api/v1/tcg/line-import"),
    ("POST", "/api/v1/tcg/line-import/android"),
    ("POST", "/api/v1/tcg/line-import/{import_job_id}/commit"),
    ("POST", "/api/v1/tcg/line-import/{import_job_id}/resolve"),
    ("POST", "/api/v1/tcg/products"),
    ("POST", "/api/v1/tcg/products/create"),
    ("DELETE", "/api/v1/tcg/products/detail/{product_id}"),
    ("PUT", "/api/v1/tcg/products/detail/{product_id}"),
    ("POST", "/api/v1/tcg/products/import/commit"),
    ("POST", "/api/v1/tcg/products/{product_id}/search-keywords"),
    ("POST", "/api/v1/tcg/review/csv/commit"),
    ("PUT", "/api/v1/tcg/v102/posts/{job_id}/items"),
}


def test_inventory_signal_routes_count():
    from app.realtime.topics import INVENTORY_SIGNAL_ROUTES

    assert len(_EXPECTED_INVENTORY_SIGNAL_ROUTES) == 45
    # 増減は設計（ADR-1016 改訂 2026-10-19）の改訂を通す
    assert set(INVENTORY_SIGNAL_ROUTES) == _EXPECTED_INVENTORY_SIGNAL_ROUTES


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
    from app.realtime.topics import USER_TOPICS

    backend = {t for t, _s in WRITE_ROUTE_TOPICS.values()} | set(TASK_TOPICS) | set(USER_TOPICS)
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
