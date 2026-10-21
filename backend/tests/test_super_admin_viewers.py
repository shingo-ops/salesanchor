"""閲覧者管理（API・サービス・専用スクリプト）の試験（ADR-1019 段4a-2）。

非 PG: 権限（403）と入力検証（422）。
PG（CI の使い捨て DB。pg fixture）: 状態遷移・履歴・目印・ログイン記録・CLI。SQLite・mock は使わない。
テストデータはすべて架空。
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app import cache
from app.database import get_db
from app.discord_gateway import viewer_bot_texts
from app.services import viewer_admin
from app.services import viewer_message_templates as vmt
from app.services.viewer_admin import ViewerAdminError
from tests.rls_bootstrap import _ensure_public_users
from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture
from tests.test_viewer_api import SECRET, FakeRedis, _bearer
from tests.viewer_template_fixtures import DEFAULT_BODIES, make_load_body

needs_ci_pg = pytest.mark.skipif(
    os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required"
)

ROUTES = [
    ("GET", "/api/v1/super-admin/viewers", None),
    ("GET", "/api/v1/super-admin/viewers/1/logins", None),
    ("POST", "/api/v1/super-admin/viewers/1/activate", {}),
    ("POST", "/api/v1/super-admin/viewers/1/suspend", {}),
    ("POST", "/api/v1/super-admin/viewers/1/unsuspend", {}),
    ("POST", "/api/v1/super-admin/viewers/1/extend", {"days": 7}),
    ("POST", "/api/v1/super-admin/viewers/1/reissue-signup-code", {}),
    ("GET", "/api/v1/super-admin/viewers/signup-request", None),
    ("GET", "/api/v1/super-admin/viewers/1/template-text?key=signup_request", None),
    ("GET", "/api/v1/super-admin/viewer-templates", None),
    ("PUT", "/api/v1/super-admin/viewer-templates/signup_request", {"body": "x", "expected_updated_at": None}),
]


def _make_user(*, is_super_admin: bool):
    from app.models import User

    user = User()
    user.id = 999
    user.tenant_id = 999
    user.username = "testuser"
    user.email = "test@example.com"
    user.role = "admin"
    user.is_active = True
    user.is_super_admin = is_super_admin
    return user


@pytest.fixture
def override_user():
    from app.auth.dependencies import get_current_tenant, get_current_user
    from app.main import app

    def _apply(user):
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_current_tenant] = lambda: 999

    yield _apply
    app.dependency_overrides.clear()


async def _call(method, path, body):
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, path, json=body)


# ── 非 PG ─────────────────────────────────────────────────────


async def test_signup_request_returns_text_for_super_admin(override_user):
    from app.main import app

    async def _no_db():
        yield None

    override_user(_make_user(is_super_admin=True))
    app.dependency_overrides[get_db] = _no_db
    with patch.object(vmt, "load_body", new=make_load_body()):
        resp = await _call("GET", "/api/v1/super-admin/viewers/signup-request", None)
    assert resp.status_code == 200
    assert resp.json() == {
        "text": DEFAULT_BODIES["signup_request"].format(signup_url=viewer_bot_texts.SIGNUP_URL)
    }
    assert "?openExternalBrowser=1#signup" in resp.json()["text"]


async def test_signup_request_uses_edited_body(override_user):
    """T5: 画面で直した本文がそのまま出る。"""
    from app.main import app

    async def _no_db():
        yield None

    override_user(_make_user(is_super_admin=True))
    app.dependency_overrides[get_db] = _no_db
    with patch.object(vmt, "load_body", new=make_load_body({"signup_request": "直した文 {signup_url}"})):
        resp = await _call("GET", "/api/v1/super-admin/viewers/signup-request", None)
    assert resp.json() == {"text": f"直した文 {viewer_bot_texts.SIGNUP_URL}"}


async def test_signup_request_without_template_is_503(override_user):
    """T6: 行が無いとき 503（コピー系は送らない）。"""
    from app.main import app

    async def _no_db():
        yield None

    override_user(_make_user(is_super_admin=True))
    app.dependency_overrides[get_db] = _no_db
    with patch.object(vmt, "load_body", new=make_load_body({"signup_request": None})):
        resp = await _call("GET", "/api/v1/super-admin/viewers/signup-request", None)
    assert resp.status_code == 503 and resp.json()["detail"] == "template_not_found"


async def test_non_super_admin_gets_403_on_all_routes(override_user):
    override_user(_make_user(is_super_admin=False))
    for method, path, body in ROUTES:
        resp = await _call(method, path, body)
        assert resp.status_code == 403, (method, path)


@pytest.mark.parametrize("days", [0, -1, 1.5, "7", 366])
async def test_extend_days_validation_422(override_user, days):
    from app.main import app

    async def _no_db():
        yield None

    override_user(_make_user(is_super_admin=True))
    app.dependency_overrides[get_db] = _no_db
    resp = await _call("POST", "/api/v1/super-admin/viewers/1/extend", {"days": days})
    assert resp.status_code == 422


@pytest.mark.parametrize(
    "body",
    [{}, {"days": 7, "until_date": "2999-01-01"}, {"until_date": "not-a-date"}, {"days": None, "until_date": None}],
)
async def test_extend_body_needs_exactly_one_of_days_or_until_date_422(override_user, body):
    from app.main import app

    async def _no_db():
        yield None

    override_user(_make_user(is_super_admin=True))
    app.dependency_overrides[get_db] = _no_db
    resp = await _call("POST", "/api/v1/super-admin/viewers/1/extend", body)
    assert resp.status_code == 422


# ── PG 共通 ───────────────────────────────────────────────────

ACTOR_ID = 999


def _prepare(conn, async_url, *, seed_templates=True, skip_templates=()):
    async def _run():
        engine = create_async_engine(async_url, echo=False)
        try:
            async with engine.begin() as aconn:
                await _ensure_public_users(aconn)
        finally:
            await engine.dispose()

    asyncio.run(_run())
    cur = conn.cursor()
    cur.execute((MIGRATIONS / "20261016_150000_add_viewer_accounts.sql").read_text())
    cur.execute((MIGRATIONS / "20261017_100000_add_viewer_discord_config.sql").read_text())
    cur.execute((MIGRATIONS / "20261020_120000_create_viewer_message_templates.sql").read_text())
    if seed_templates:  # 送る側は DB の本文を読む。既定で 9件入れておく（行なしの試験は seed_templates=False か DELETE）
        for key, body in DEFAULT_BODIES.items():
            if key in skip_templates:
                continue  # この鍵だけ行なしにする試験用
            cur.execute(
                "INSERT INTO public.viewer_message_templates (key, body) VALUES (%s, %s)", (key, body)
            )
    return cur


def _account(cur, email, status, *, expires_in_days=None):
    cur.execute(
        "INSERT INTO public.viewer_accounts (email, line_name, status, trial_expires_at) "
        "VALUES (%s, 'fake', %s, "
        "CASE WHEN %s::int IS NULL THEN NULL ELSE NOW() + make_interval(days => %s::int) END) RETURNING id",
        (email, status, expires_in_days, expires_in_days),
    )
    return cur.fetchone()[0]


def _event(cur, vid, ip, hours_ago, event_type="login_succeeded"):
    cur.execute(
        "INSERT INTO public.viewer_login_events (viewer_id, event_type, client_ip, user_agent, created_at) "
        "VALUES (%s, %s, %s, 'agent-x', NOW() - make_interval(hours => %s::int))",
        (vid, event_type, ip, hours_ago),
    )


def _changes(cur, vid):
    cur.execute(
        "SELECT action, from_status, to_status, from_expires_at, to_expires_at, extend_days, actor, actor_user_id "
        "FROM public.viewer_status_changes WHERE viewer_id=%s ORDER BY id",
        (vid,),
    )
    return cur.fetchall()


def _state(cur, vid):
    cur.execute("SELECT status, trial_expires_at FROM public.viewer_accounts WHERE id=%s", (vid,))
    return cur.fetchone()


def _with_db(async_url, fn):
    """AsyncSession で fn(db) を実行し commit する（失敗は rollback して再送出）。"""

    async def _go():
        engine = create_async_engine(async_url, echo=False)
        try:
            async with AsyncSession(engine, expire_on_commit=False) as db:
                try:
                    result = await fn(db)
                    await db.commit()
                    return result
                except Exception:
                    await db.rollback()
                    raise
        finally:
            await engine.dispose()

    return asyncio.run(_go())


def _change(async_url, vid, action, **kw):
    kw.setdefault("actor", "po")
    kw.setdefault("actor_user_id", ACTOR_ID)
    return _with_db(async_url, lambda db: viewer_admin.change_status(db, vid, action, **kw))


def _api(async_url, method, path, body=None, *, super_admin=True):
    """実 PG に対して API を呼ぶ。"""

    async def _go():
        from app.auth.dependencies import get_current_tenant, get_current_user
        from app.main import app

        engine = create_async_engine(async_url, echo=False)

        async def _db():
            async with AsyncSession(engine, expire_on_commit=False) as session:
                yield session

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[get_current_user] = lambda: _make_user(is_super_admin=super_admin)
        app.dependency_overrides[get_current_tenant] = lambda: 999
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
                return await http.request(method, path, json=body)
        finally:
            app.dependency_overrides.clear()
            await engine.dispose()

    return asyncio.run(_go())


def _error_code(async_url, vid, action, **kw):
    with pytest.raises(ViewerAdminError) as exc:
        _change(async_url, vid, action, **kw)
    return exc.value.code


# ── PG 試験 ───────────────────────────────────────────────────


@needs_ci_pg
def test_activate_suspend_unsuspend_extend_write_one_row_each(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    vid = _account(cur, "a1@x.com", "trial", expires_in_days=5)
    now = datetime(2026, 10, 16, 0, 0, tzinfo=timezone.utc)

    _change(async_url, vid, "extend", days=10, now=now)
    _change(async_url, vid, "suspend", now=now)
    _change(async_url, vid, "unsuspend", now=now)
    _change(async_url, vid, "activate", now=now)
    rows = _changes(cur, vid)
    assert [r[0] for r in rows] == ["extend", "suspend", "unsuspend", "activate"]
    assert [(r[1], r[2]) for r in rows] == [
        ("trial", "trial"), ("trial", "suspended"), ("suspended", "trial"), ("trial", "active"),
    ]
    assert rows[0][5] == 10 and all(r[5] is None for r in rows[1:])
    assert rows[0][4] == now + timedelta(days=10)
    assert all(r[6] == "po" and r[7] == ACTOR_ID for r in rows)
    status, expires = _state(cur, vid)
    assert status == "active" and expires == now + timedelta(days=10)


@needs_ci_pg
def test_unsuspend_returns_to_last_suspend_from_status(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    t = _account(cur, "t@x.com", "trial", expires_in_days=5)
    a = _account(cur, "act@x.com", "active")
    for vid, expected in ((t, "trial"), (a, "active")):
        _change(async_url, vid, "suspend")
        assert _state(cur, vid)[0] == "suspended"
        result = _change(async_url, vid, "unsuspend")
        assert result["status"] == expected
        assert _state(cur, vid)[0] == expected


@needs_ci_pg
def test_unsuspend_without_suspend_row_is_409(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    vid = _account(cur, "nosus@x.com", "suspended")
    assert _error_code(async_url, vid, "unsuspend") == "conflict"
    resp = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{vid}/unsuspend", {})
    assert resp.status_code == 409 and resp.json()["detail"] == "viewer_status_conflict"
    assert _changes(cur, vid) == []


@needs_ci_pg
def test_conflicts_are_409(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    by_status = {s: _account(cur, f"{s}@x.com", s, expires_in_days=5 if s == "trial" else None)
                 for s in ("pending", "verified", "trial", "active", "suspended")}
    for s in ("pending", "verified", "active", "suspended"):
        assert _error_code(async_url, by_status[s], "activate") == "conflict", s
    assert _error_code(async_url, by_status["suspended"], "suspend") == "conflict"
    for s in ("active", "suspended", "pending", "verified"):
        assert _error_code(async_url, by_status[s], "extend", days=7) == "conflict", s
    resp = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{by_status['active']}/activate", {})
    assert resp.status_code == 409
    for vid in by_status.values():
        assert _changes(cur, vid) == []


@needs_ci_pg
def test_extend_expired_trial_sets_now_plus_7_and_inventory_200(pg, monkeypatch):  # noqa: F811
    from app.tasks import viewer_inventory_cache as vic

    monkeypatch.setenv("AUTH_VIEWER_JWT_SECRET", SECRET)
    monkeypatch.setenv("AUTH_JWT_SECRET", "a" * 48)
    fake = FakeRedis()
    monkeypatch.setattr(cache, "_redis", fake)
    fake.store[vic.CACHE_KEY] = json.dumps({"updated_at": "2026-10-16T00:00:00+00:00", "rows": []})
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)

    fixed = datetime(2026, 10, 16, 0, 0, tzinfo=timezone.utc)
    vid = _account(cur, "exp@x.com", "trial", expires_in_days=-3)
    result = _change(async_url, vid, "extend", days=7, now=fixed)
    assert result["trial_expires_at"] == fixed + timedelta(days=7)
    assert _changes(cur, vid)[0][4] == fixed + timedelta(days=7)

    # 期限切れのままだと在庫は 403。API で延長（実時刻）すると 200 になる
    vid2 = _account(cur, "exp2@x.com", "trial", expires_in_days=-3)
    _, auth = _bearer(vid2)

    async def _get_inventory():
        from app.main import app

        engine = create_async_engine(async_url, echo=False)

        async def _db():
            async with AsyncSession(engine, expire_on_commit=False) as session:
                yield session

        app.dependency_overrides[get_db] = _db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
                return await http.get("/api/v1/viewer/inventory", headers=auth)
        finally:
            app.dependency_overrides.pop(get_db, None)
            await engine.dispose()

    assert asyncio.run(_get_inventory()).status_code == 403
    resp = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{vid2}/extend", {"days": 7})
    assert resp.status_code == 200 and resp.json()["status"] == "trial"
    assert asyncio.run(_get_inventory()).status_code == 200


@needs_ci_pg
def test_extend_until_date_sets_jst_end_of_day_and_rejects_bad_dates(pg):  # noqa: F811
    from datetime import date

    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    fixed = datetime(2026, 10, 16, 0, 0, tzinfo=timezone.utc)
    vid = _account(cur, "ud@x.com", "trial", expires_in_days=3)
    result = _change(async_url, vid, "extend", until_date=date(2026, 10, 31), now=fixed)
    # 日本時間 10/31 23:59:59 = UTC 10/31 14:59:59
    assert result["trial_expires_at"] == datetime(2026, 10, 31, 14, 59, 59, tzinfo=timezone.utc)
    row = _changes(cur, vid)[0]
    assert row[0] == "extend" and row[4] == datetime(2026, 10, 31, 14, 59, 59, tzinfo=timezone.utc)
    assert row[5] is None  # until_date のときは extend_days を入れない
    # 今日（日本時間 10/16 23:59:59 は「今」より後）は通り、前日は断る
    assert _change(async_url, vid, "extend", until_date=date(2026, 10, 16), now=fixed)["status"] == "trial"
    assert _error_code(async_url, vid, "extend", until_date=date(2026, 10, 15), now=fixed) == "invalid_days"
    # 365日以内（JST 23:59:59 が 今+365日 を超えない日）まで。366日後は断る
    assert _error_code(async_url, vid, "extend", until_date=date(2027, 10, 17), now=fixed) == "invalid_days"
    assert _error_code(async_url, vid, "extend", until_date=date(2026, 10, 31), days=7, now=fixed) == "invalid_days"
    resp = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{vid}/extend", {"until_date": "2000-01-01"})
    assert resp.status_code == 422 and resp.json()["detail"] == "invalid_days"
    resp = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{vid}/extend", {"days": 3, "until_date": "2999-01-01"})
    assert resp.status_code == 422


@needs_ci_pg
def test_share_flag_hits_match_list_flags(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    many = _account(cur, "m@x.com", "active")
    sh1 = _account(cur, "s1@x.com", "active")
    sh2 = _account(cur, "s2@x.com", "active")
    quiet = _account(cur, "q@x.com", "active")
    for i, ip in enumerate(("10.1.0.1", "10.1.0.2", "10.1.0.3")):
        _event(cur, many, ip, i)
    _event(cur, sh1, "10.9.9.9", 0)
    _event(cur, sh2, "10.9.9.9", 5)
    _event(cur, quiet, "10.7.7.7", 0)

    hits = _with_db(async_url, lambda db: viewer_admin.share_flag_hits(db))
    assert hits == [
        (many, "many_ips", []),
        (sh1, "shared_ip", [sh2]),
        (sh2, "shared_ip", [sh1]),
    ]
    items = _with_db(async_url, lambda db: viewer_admin.list_viewers(db))
    flagged_many = {i["id"] for i in items if i["flag_many_ips"]}
    flagged_shared = {i["id"] for i in items if i["flag_shared_ip"]}
    assert flagged_many == {h[0] for h in hits if h[1] == "many_ips"}
    assert flagged_shared == {h[0] for h in hits if h[1] == "shared_ip"}


@needs_ci_pg
def test_404_for_missing_viewer(pg):  # noqa: F811
    conn, _, async_url = pg
    _prepare(conn, async_url)
    assert _error_code(async_url, 424242, "suspend") == "not_found"
    for method, path, body in ROUTES[1:]:
        if "/1/" not in path:
            continue  # viewer_id を含まない口（signup-request）は対象外
        resp = _api(async_url, method, path.replace("/1/", "/424242/"), body)
        assert resp.status_code == 404 and resp.json()["detail"] == "viewer_not_found", path


@needs_ci_pg
def test_flags_many_ips_and_shared_ip(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    many = _account(cur, "many@x.com", "active")
    spread = _account(cur, "spread@x.com", "active")
    two = _account(cur, "two@x.com", "active")
    failed = _account(cur, "failed@x.com", "active")
    sh1 = _account(cur, "sh1@x.com", "active")
    sh2 = _account(cur, "sh2@x.com", "active")
    same = _account(cur, "same@x.com", "active")
    for i, ip in enumerate(("10.1.0.1", "10.1.0.2", "10.1.0.3")):
        _event(cur, many, ip, i)
    for ip, h in (("10.2.0.1", 0), ("10.2.0.2", 25), ("10.2.0.3", 50)):
        _event(cur, spread, ip, h)
    _event(cur, two, "10.3.0.1", 0)
    _event(cur, two, "10.3.0.2", 1)
    for i, ip in enumerate(("10.4.0.1", "10.4.0.2", "10.4.0.3")):
        _event(cur, failed, ip, i, "login_failed")
    _event(cur, sh1, "10.9.9.9", 0)
    _event(cur, sh2, "10.9.9.9", 5)
    _event(cur, same, "10.8.8.8", 0)
    _event(cur, same, "10.8.8.8", 30)

    items = _with_db(async_url, lambda db: viewer_admin.list_viewers(db))
    flags = {i["id"]: (i["flag_many_ips"], i["flag_shared_ip"]) for i in items}
    assert flags[many] == (True, False)
    assert flags[spread] == (False, False)
    assert flags[two] == (False, False)
    assert flags[failed] == (False, False)
    assert flags[sh1] == (False, True) and flags[sh2] == (False, True)
    assert flags[same] == (False, False)
    # 並び: created_at 降順・id 降順
    assert [i["id"] for i in items] == sorted((i["id"] for i in items), reverse=True)


@needs_ci_pg
def test_logins_listed_newest_first_with_ip_and_agent(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    vid = _account(cur, "log@x.com", "active")
    _event(cur, vid, "10.5.0.1", 5)
    _event(cur, vid, "10.5.0.2", 1)
    resp = _api(async_url, "GET", f"/api/v1/super-admin/viewers/{vid}/logins")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [i["client_ip"] for i in items] == ["10.5.0.2", "10.5.0.1"]
    assert all(i["user_agent"] == "agent-x" and i["event_type"] == "login_succeeded" for i in items)
    listed = _api(async_url, "GET", "/api/v1/super-admin/viewers")
    assert listed.status_code == 200 and [i["id"] for i in listed.json()["items"]] == [vid]


@needs_ci_pg
def test_cli_change_status_records_actor_claude(pg, monkeypatch):  # noqa: F811
    from app import viewer_admin_cli

    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    vid = _account(cur, "cli@x.com", "trial", expires_in_days=3)

    async def _go():
        engine = create_async_engine(async_url, echo=False)
        try:
            factory = lambda: AsyncSession(engine, expire_on_commit=False)  # noqa: E731
            ok = await viewer_admin_cli.run({"action": "suspend", "email": " CLI@x.com "}, session_factory=factory)
            bad = None
            try:
                await viewer_admin_cli.run({"action": "drop", "email": "cli@x.com"}, session_factory=factory)
            except ViewerAdminError as exc:
                bad = exc.code
            return ok, bad
        finally:
            await engine.dispose()

    sent = []

    async def _fake_send(channel_id, text):
        sent.append((channel_id, text))
        return True

    monkeypatch.setattr("app.services.viewer_room_notice.send_room_notice", _fake_send)
    ok, bad = asyncio.run(_go())
    assert ok["id"] == vid and ok["status"] == "suspended" and bad == "invalid_input"
    assert ok["room_notice"] == "no_room" and sent == []  # 部屋なしには送らない
    rows = _changes(cur, vid)
    assert len(rows) == 1 and rows[0][0] == "suspend" and rows[0][6] == "claude" and rows[0][7] is None


@needs_ci_pg
def test_cli_room_notice_sent_when_room_exists(pg, monkeypatch):  # noqa: F811
    from app import viewer_admin_cli

    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    vid = _account(cur, "clr@x.com", "trial", expires_in_days=3)
    cur.execute("UPDATE public.viewer_accounts SET discord_channel_id='777' WHERE id=%s", (vid,))
    sent = []

    async def _fake_send(channel_id, text):
        sent.append((channel_id, text))
        return True

    monkeypatch.setattr("app.services.viewer_room_notice.send_room_notice", _fake_send)

    async def _go():
        engine = create_async_engine(async_url, echo=False)
        try:
            factory = lambda: AsyncSession(engine, expire_on_commit=False)  # noqa: E731
            return await viewer_admin_cli.run({"action": "activate", "email": "clr@x.com"}, session_factory=factory)
        finally:
            await engine.dispose()

    res = asyncio.run(_go())
    assert res["room_notice"] == "sent" and sent == [("777", DEFAULT_BODIES["notice_activated"])]


# ── 4つの入口の room_notice（K3。入口を通して確かめる） ──


def _set_room(cur, vid, channel="777"):
    cur.execute("UPDATE public.viewer_accounts SET discord_channel_id=%s WHERE id=%s", (channel, vid))


@needs_ci_pg
@pytest.mark.parametrize("sender_ok", [True, False])
def test_entrypoints_report_room_notice_sent_or_failed(pg, monkeypatch, sender_ok):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    sent = []

    async def _fake_send(channel_id, text):
        sent.append((channel_id, text))
        return sender_ok

    monkeypatch.setattr("app.services.viewer_room_notice.send_room_notice", _fake_send)
    expected = "sent" if sender_ok else "failed"
    base = "/api/v1/super-admin/viewers"

    v1 = _account(cur, "n1@x.com", "trial", expires_in_days=3)
    _set_room(cur, v1)
    until = (datetime.now(timezone.utc) + timedelta(days=30)).date()
    r = _api(async_url, "POST", f"{base}/{v1}/extend", {"until_date": until.isoformat()})
    assert r.status_code == 200 and r.json()["room_notice"] == expected
    assert r.json()["room_notice_text"] == f"お試し期間を {until.month}月{until.day}日 まで延長しました😊"

    v2 = _account(cur, "n2@x.com", "trial", expires_in_days=3)
    _set_room(cur, v2)
    r = _api(async_url, "POST", f"{base}/{v2}/activate", {})
    assert r.json()["room_notice"] == expected
    assert r.json()["room_notice_text"] == DEFAULT_BODIES["notice_activated"]

    r = _api(async_url, "POST", f"{base}/{v2}/suspend", {})
    assert r.json()["room_notice"] == expected
    assert r.json()["room_notice_text"] == DEFAULT_BODIES["notice_suspended"]

    n_before = len(sent)
    r = _api(async_url, "POST", f"{base}/{v2}/unsuspend", {})
    assert r.status_code == 200
    assert r.json()["room_notice"] is None and r.json()["room_notice_text"] is None
    assert len(sent) == n_before  # unsuspend は送らない
    assert all(c == "777" for c, _ in sent) and len(sent) == 3


@needs_ci_pg
def test_entrypoints_no_room_does_not_send(pg, monkeypatch):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    sent = []

    async def _fake_send(channel_id, text):
        sent.append(channel_id)
        return True

    monkeypatch.setattr("app.services.viewer_room_notice.send_room_notice", _fake_send)
    vid = _account(cur, "nr@x.com", "trial", expires_in_days=3)
    r = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{vid}/suspend", {})
    assert r.status_code == 200
    assert r.json()["room_notice"] == "no_room"
    assert r.json()["room_notice_text"] == DEFAULT_BODIES["notice_suspended"]
    assert sent == []


@needs_ci_pg
def test_register_cli_counts_and_is_idempotent(pg):  # noqa: F811
    from app import viewer_register_cli

    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    rows = [
        {"applied_at": "2026-10-01T10:00:00", "line_name": "n1", "email": "r1@x.com", "status": "trial"},
        {"applied_at": "2026-10-02T09:30:00+09:00", "line_name": "n2", "email": "R2@x.com", "status": "trial"},
        {"applied_at": "2026-09-01T00:00:00", "line_name": "n3", "email": "r3@x.com", "status": "active"},
    ]

    async def _go(payload):
        engine = create_async_engine(async_url, echo=False)
        try:
            return await viewer_register_cli.run(
                payload, session_factory=lambda: AsyncSession(engine, expire_on_commit=False)
            )
        finally:
            await engine.dispose()

    assert asyncio.run(_go({"rows": rows})) == {"registered": 3, "skipped": 0, "failed": 0}
    assert asyncio.run(_go({"rows": rows})) == {"registered": 0, "skipped": 3, "failed": 0}
    cur.execute("SELECT count(*) FROM public.viewer_accounts")
    assert cur.fetchone()[0] == 3
    cur.execute("SELECT email, status, trial_expires_at FROM public.viewer_accounts ORDER BY email")
    got = {r[0]: r for r in cur.fetchall()}
    jst = timezone(timedelta(hours=9))
    assert got["r1@x.com"][2] == datetime(2026, 10, 1, 10, 0, tzinfo=jst) + timedelta(days=14)
    assert got["r2@x.com"][2] == datetime(2026, 10, 2, 9, 30, tzinfo=jst) + timedelta(days=14)
    assert got["r3@x.com"][1] == "active" and got["r3@x.com"][2] is None
    cur.execute("SELECT count(*) FROM public.viewer_status_changes")
    assert cur.fetchone()[0] == 0

    mixed = [
        {"applied_at": "2026-10-03T00:00:00", "line_name": "n4", "email": "r4@x.com", "status": "trial"},
        {"applied_at": "not-a-date", "line_name": "n5", "email": "r5@x.com", "status": "trial"},
    ]
    assert asyncio.run(_go({"rows": mixed})) == {"registered": 1, "skipped": 0, "failed": 1}
    cur.execute("SELECT count(*) FROM public.viewer_accounts")
    assert cur.fetchone()[0] == 4


@needs_ci_pg
def test_suspend_record_feeds_purge(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    vid = _account(cur, "purge@x.com", "active")
    _change(async_url, vid, "suspend")
    cur.execute(
        "SELECT count(*) FROM public.viewer_status_changes WHERE viewer_id=%s AND action='suspend'", (vid,)
    )
    assert cur.fetchone()[0] == 1


# ── 申込コードの作り直し（ADR-1019 段5） ─────────────────────────


def _signup_hashes(cur, vid):
    cur.execute(
        "SELECT token_sha256 FROM public.viewer_login_tokens "
        "WHERE viewer_account_id=%s AND purpose='signup_code'",
        (vid,),
    )
    return [bytes(r[0]) for r in cur.fetchall()]


@needs_ci_pg
def test_reissue_pending_replaces_code_and_returns_invite(pg, monkeypatch):  # noqa: F811
    from app.auth.viewer_signup_code import normalize_signup_code, signup_code_sha256

    async def _fake_invite(db):
        return "https://discord.gg/fakecode"

    monkeypatch.setattr("app.routers.super_admin_viewers.create_viewer_invite", _fake_invite)
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    vid = _account(cur, "p1@x.com", "pending")
    old = b"\x01" * 32
    cur.execute(
        "INSERT INTO public.viewer_login_tokens (viewer_account_id, token_sha256, purpose, expires_at) "
        "VALUES (%s, %s, 'signup_code', NOW() + interval '1 day')",
        (vid, old),
    )
    resp = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{vid}/reissue-signup-code", {})
    assert resp.status_code == 200
    body = resp.json()
    assert re.fullmatch(r"[0-9A-Z]{4}(-[0-9A-Z]{4}){3}", body["signup_code"])
    assert body["invite_url"] == "https://discord.gg/fakecode"
    assert body["signup_code"] in body["message"]
    assert "https://discord.gg/fakecode?openExternalBrowser=1" in body["message"]
    hashes = _signup_hashes(cur, vid)
    assert hashes == [signup_code_sha256(normalize_signup_code(body["signup_code"]))]
    assert old not in hashes


@needs_ci_pg
def test_reissue_invite_none_is_200_with_null(pg, monkeypatch):  # noqa: F811
    async def _no_invite(db):
        return None

    monkeypatch.setattr("app.routers.super_admin_viewers.create_viewer_invite", _no_invite)
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    vid = _account(cur, "p2@x.com", "pending")
    resp = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{vid}/reissue-signup-code", {})
    assert resp.status_code == 200 and resp.json()["invite_url"] is None
    assert "Discord への招待" not in resp.json()["message"]
    assert len(_signup_hashes(cur, vid)) == 1


@needs_ci_pg
def test_reissue_trial_and_active_200_keep_state_suspended_409_linked_409(pg, monkeypatch):  # noqa: F811
    async def _fake_invite(db):
        return "https://discord.gg/fakecode"

    monkeypatch.setattr("app.routers.super_admin_viewers.create_viewer_invite", _fake_invite)
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    for status in ("trial", "active"):
        vid = _account(cur, f"{status}@x.com", status, expires_in_days=5 if status == "trial" else None)
        before = _state(cur, vid)
        resp = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{vid}/reissue-signup-code", {})
        assert resp.status_code == 200
        assert len(_signup_hashes(cur, vid)) == 1
        assert _state(cur, vid) == before  # 状態と期限は変えない
    sid = _account(cur, "suspended@x.com", "suspended")
    resp = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{sid}/reissue-signup-code", {})
    assert resp.status_code == 409 and resp.json()["detail"] == "viewer_status_conflict"
    assert _signup_hashes(cur, sid) == []
    lid = _account(cur, "linked@x.com", "trial", expires_in_days=5)
    cur.execute("UPDATE public.viewer_accounts SET discord_user_id='d-1' WHERE id=%s", (lid,))
    resp = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{lid}/reissue-signup-code", {})
    assert resp.status_code == 409 and resp.json()["detail"] == "viewer_already_linked"
    assert _signup_hashes(cur, lid) == []
    resp = _api(async_url, "POST", "/api/v1/super-admin/viewers/999999/reissue-signup-code", {})
    assert resp.status_code == 404
    pid = _account(cur, "p3@x.com", "pending")
    resp = _api(
        async_url, "POST", f"/api/v1/super-admin/viewers/{pid}/reissue-signup-code", {}, super_admin=False
    )
    assert resp.status_code == 403


# ── LINE名を直す（ADR-1019 段8） ──────────────────────────────


async def test_non_super_admin_gets_403_on_patch_line_name(override_user):
    override_user(_make_user(is_super_admin=False))
    resp = await _call("PATCH", "/api/v1/super-admin/viewers/1", {"line_name": "新しい名前"})
    assert resp.status_code == 403


@needs_ci_pg
def test_patch_line_name_trims_saves_and_keeps_other_fields(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    vid = _account(cur, "ln1@x.com", "trial", expires_in_days=5)
    before = _api(async_url, "GET", "/api/v1/super-admin/viewers").json()["items"]
    before_item = next(i for i in before if i["id"] == vid)

    resp = _api(
        async_url, "PATCH", f"/api/v1/super-admin/viewers/{vid}", {"line_name": "  新しい名前  "}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["line_name"] == "新しい名前"
    for key in ("id", "email", "status", "trial_expires_at", "created_at", "discord_user_id"):
        assert body[key] == before_item[key], key
    cur.execute("SELECT line_name FROM public.viewer_accounts WHERE id=%s", (vid,))
    assert cur.fetchone()[0] == "新しい名前"
    assert _changes(cur, vid) == []


@needs_ci_pg
def test_patch_line_name_rejects_blank_and_too_long_with_422(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    vid = _account(cur, "ln2@x.com", "trial", expires_in_days=5)
    for bad in ("", "   ", "あ" * 101, " " + "a" * 101 + " "):
        resp = _api(async_url, "PATCH", f"/api/v1/super-admin/viewers/{vid}", {"line_name": bad})
        assert resp.status_code == 422, repr(bad)
    ok = _api(async_url, "PATCH", f"/api/v1/super-admin/viewers/{vid}", {"line_name": "a" * 100})
    assert ok.status_code == 200
    cur.execute("SELECT line_name FROM public.viewer_accounts WHERE id=%s", (vid,))
    assert cur.fetchone()[0] == "a" * 100


@needs_ci_pg
def test_patch_line_name_invalid_is_service_error_and_missing_is_404(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    vid = _account(cur, "ln3@x.com", "trial", expires_in_days=5)
    with pytest.raises(ViewerAdminError) as exc:
        _with_db(async_url, lambda db: viewer_admin.update_line_name(db, vid, "   "))
    assert exc.value.code == "invalid_line_name"
    resp = _api(async_url, "PATCH", "/api/v1/super-admin/viewers/424242", {"line_name": "x"})
    assert resp.status_code == 404 and resp.json()["detail"] == "viewer_not_found"


@needs_ci_pg
def test_patch_line_name_forbidden_for_non_super_admin_on_pg(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    vid = _account(cur, "ln4@x.com", "trial", expires_in_days=5)
    resp = _api(
        async_url, "PATCH", f"/api/v1/super-admin/viewers/{vid}", {"line_name": "変更"}, super_admin=False
    )
    assert resp.status_code == 403
    cur.execute("SELECT line_name FROM public.viewer_accounts WHERE id=%s", (vid,))
    assert cur.fetchone()[0] == "fake"


# ── テンプレートを DB から読む（段11 便2: T5 / T6 / T9 / N2-3） ──────────


def _fake_session_factory():
    from unittest.mock import AsyncMock, MagicMock

    db = MagicMock()
    db.commit = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)
    return db, (lambda: cm)


async def test_cli_result_json_has_no_template_when_row_missing():
    """N2-3: テンプレートが無くても状態は変え、結果 JSON の room_notice は no_template。"""
    from unittest.mock import AsyncMock

    from app import viewer_admin_cli

    item = {"id": 5, "status": "suspended", "trial_expires_at": None, "discord_channel_id": "777"}
    db, factory = _fake_session_factory()
    send = AsyncMock(return_value=True)
    with patch.object(viewer_admin, "change_status_by_email", new=AsyncMock(return_value=item)), patch.object(
        vmt, "load_body", new=make_load_body({"notice_suspended": None})
    ), patch("app.services.viewer_room_notice.send_room_notice", new=send):
        res = await viewer_admin_cli.run({"action": "suspend", "email": "a@x.com"}, session_factory=factory)
    assert res["room_notice"] == "no_template" and res["status"] == "suspended"
    db.commit.assert_awaited_once()  # 状態は変わる（commit される）
    send.assert_not_awaited()  # 送らない


async def test_cli_sends_edited_body():
    from unittest.mock import AsyncMock

    from app import viewer_admin_cli

    item = {"id": 5, "status": "suspended", "trial_expires_at": None, "discord_channel_id": "777"}
    _db, factory = _fake_session_factory()
    send = AsyncMock(return_value=True)
    with patch.object(viewer_admin, "change_status_by_email", new=AsyncMock(return_value=item)), patch.object(
        vmt, "load_body", new=make_load_body({"notice_suspended": "直した停止の文"})
    ), patch("app.services.viewer_room_notice.send_room_notice", new=send):
        res = await viewer_admin_cli.run({"action": "suspend", "email": "a@x.com"}, session_factory=factory)
    assert res["room_notice"] == "sent"
    send.assert_awaited_once_with("777", "直した停止の文")


@needs_ci_pg
def test_extend_without_template_changes_state_and_reports_no_template(pg, monkeypatch):  # noqa: F811
    """T9 ③: 行が無くても延長は効く。応答は room_notice=no_template、送らない。"""
    conn, _, async_url = pg
    cur = _prepare(conn, async_url, skip_templates=("notice_extended",))
    sent = []

    async def _fake_send(channel_id, text):
        sent.append((channel_id, text))
        return True

    monkeypatch.setattr("app.services.viewer_room_notice.send_room_notice", _fake_send)
    vid = _account(cur, "nt1@x.com", "trial", expires_in_days=3)
    _set_room(cur, vid)
    before = _state(cur, vid)
    r = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{vid}/extend", {"days": 10})
    assert r.status_code == 200
    assert r.json()["room_notice"] == "no_template" and r.json()["room_notice_text"] is None
    assert _state(cur, vid) != before  # 期限は延びた
    assert sent == []
    assert len(_changes(cur, vid)) == 1


@needs_ci_pg
def test_edited_body_is_used_by_extend(pg, monkeypatch):  # noqa: F811
    """T5: DB の本文を直すと、延長の部屋への文がそのまま変わる。"""
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    sent = []

    async def _fake_send(channel_id, text):
        sent.append(text)
        return True

    monkeypatch.setattr("app.services.viewer_room_notice.send_room_notice", _fake_send)
    cur.execute(
        "UPDATE public.viewer_message_templates SET body = %s WHERE key = 'notice_extended'",
        ("直した文：{until_date}まで",),
    )
    vid = _account(cur, "ed1@x.com", "trial", expires_in_days=3)
    _set_room(cur, vid)
    until = (datetime.now(timezone.utc) + timedelta(days=30)).date()
    r = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{vid}/extend", {"until_date": until.isoformat()})
    assert r.json()["room_notice_text"] == f"直した文：{until.month}月{until.day}日まで"
    assert sent == [f"直した文：{until.month}月{until.day}日まで"]


@needs_ci_pg
@pytest.mark.parametrize("missing", ["reissue_notice", "reissue_notice_no_invite"])
def test_reissue_without_template_is_503_and_code_unchanged(pg, monkeypatch, missing):  # noqa: F811
    """T6 / T9 ②: 案内の行が（どちらか）無いとき 503、申込コードは作り直さない・招待も作らない。"""
    invited = []

    async def _fake_invite(db):
        invited.append(1)
        return "https://discord.gg/fakecode"

    monkeypatch.setattr("app.routers.super_admin_viewers.create_viewer_invite", _fake_invite)
    conn, _, async_url = pg
    cur = _prepare(conn, async_url, skip_templates=(missing,))
    vid = _account(cur, "rt1@x.com", "pending")
    old = b"\x02" * 32
    cur.execute(
        "INSERT INTO public.viewer_login_tokens (viewer_account_id, token_sha256, purpose, expires_at) "
        "VALUES (%s, %s, 'signup_code', NOW() + interval '1 day')",
        (vid, old),
    )
    resp = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{vid}/reissue-signup-code", {})
    assert resp.status_code == 503 and resp.json()["detail"] == "template_not_found"
    assert _signup_hashes(cur, vid) == [old]  # 申込コードは変わらない
    assert invited == []


@needs_ci_pg
def test_reissue_message_uses_edited_body(pg, monkeypatch):  # noqa: F811
    async def _no_invite(db):
        return None

    monkeypatch.setattr("app.routers.super_admin_viewers.create_viewer_invite", _no_invite)
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    cur.execute(
        "UPDATE public.viewer_message_templates SET body = %s WHERE key = 'reissue_notice_no_invite'",
        ("{line_name}さん、直した案内 {code} {expires}",),
    )
    vid = _account(cur, "rt2@x.com", "pending")
    resp = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{vid}/reissue-signup-code", {})
    assert resp.status_code == 200
    assert resp.json()["message"].startswith("fakeさん、直した案内 " + resp.json()["signup_code"])


@needs_ci_pg
def test_reissue_message_with_invite_uses_edited_body(pg, monkeypatch):  # noqa: F811
    """T5: 招待ありの作り直し案内も、直した本文がそのまま出る。"""

    async def _invite(db):
        return "https://discord.gg/fakecode"

    monkeypatch.setattr("app.routers.super_admin_viewers.create_viewer_invite", _invite)
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    cur.execute(
        "UPDATE public.viewer_message_templates SET body = %s WHERE key = 'reissue_notice'",
        ("{line_name}さん、直した招待つき案内 {code} {expires} {invite_url}",),
    )
    vid = _account(cur, "rt3@x.com", "pending")
    resp = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{vid}/reissue-signup-code", {})
    assert resp.status_code == 200
    msg = resp.json()["message"]
    assert msg.startswith("fakeさん、直した招待つき案内 " + resp.json()["signup_code"])
    assert msg.endswith("https://discord.gg/fakecode?openExternalBrowser=1")


# ── 詳細欄から「送る文」をコピーする GET（template-text） ─────────────────


def _text_path(vid, key):
    return f"/api/v1/super-admin/viewers/{vid}/template-text?key={key}"


@needs_ci_pg
def test_template_text_returns_each_key_with_viewer_values(pg):  # noqa: F811
    """K1: 6つの鍵それぞれで、その人の値を入れた文が返る。"""
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    vid = _account(cur, "tt1@x.com", "trial", expires_in_days=5)
    cur.execute("SELECT trial_expires_at FROM public.viewer_accounts WHERE id=%s", (vid,))
    date_text = viewer_bot_texts.format_jst_date(cur.fetchone()[0])
    expected = {
        "signup_request": DEFAULT_BODIES["signup_request"].format(signup_url=viewer_bot_texts.SIGNUP_URL),
        "room_recreated": DEFAULT_BODIES["room_recreated"].format(email="tt1@x.com"),
        "notice_extended": DEFAULT_BODIES["notice_extended"].format(until_date=date_text),
        "interview_request": DEFAULT_BODIES["interview_request"].format(expires_date=date_text),
        "notice_activated": DEFAULT_BODIES["notice_activated"],
        "notice_suspended": DEFAULT_BODIES["notice_suspended"],
    }
    for key, want in expected.items():
        resp = _api(async_url, "GET", _text_path(vid, key))
        assert resp.status_code == 200, key
        assert resp.json() == {"text": want}, key


@needs_ci_pg
def test_template_text_matches_auto_sent_extend_text(pg, monkeypatch):  # noqa: F811
    """K2: 延長の自動送信の文と、その後のコピーの文が一字一句同じ。"""
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)

    async def _fake_send(channel_id, text):
        return True

    monkeypatch.setattr("app.services.viewer_room_notice.send_room_notice", _fake_send)
    vid = _account(cur, "tt2@x.com", "trial", expires_in_days=3)
    _set_room(cur, vid)
    ext = _api(async_url, "POST", f"/api/v1/super-admin/viewers/{vid}/extend", {"days": 10})
    assert ext.status_code == 200 and ext.json()["room_notice_text"]
    resp = _api(async_url, "GET", _text_path(vid, "notice_extended"))
    assert resp.status_code == 200
    assert resp.json()["text"] == ext.json()["room_notice_text"]


@needs_ci_pg
@pytest.mark.parametrize("key", ["reissue_notice", "reissue_notice_no_invite", "room_welcome", "unknown_key"])
def test_template_text_not_copyable_key_is_422(pg, key):  # noqa: F811
    """K3: 対象外の鍵は 422。"""
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    vid = _account(cur, "tt3@x.com", "trial", expires_in_days=5)
    resp = _api(async_url, "GET", _text_path(vid, key))
    assert resp.status_code == 422 and resp.json()["detail"] == "template_not_copyable"


@needs_ci_pg
@pytest.mark.parametrize("key", ["notice_extended", "interview_request"])
def test_template_text_without_expiry_is_409(pg, key):  # noqa: F811
    """K4: 期限なしの人に延長・面談は 409。"""
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    vid = _account(cur, "tt4@x.com", "pending")
    resp = _api(async_url, "GET", _text_path(vid, key))
    assert resp.status_code == 409 and resp.json()["detail"] == "no_trial_expiry"


@needs_ci_pg
def test_template_text_missing_viewer_is_404(pg):  # noqa: F811
    """K4: 存在しない人は 404。"""
    conn, _, async_url = pg
    _prepare(conn, async_url)
    resp = _api(async_url, "GET", _text_path(424242, "signup_request"))
    assert resp.status_code == 404 and resp.json()["detail"] == "viewer_not_found"


@needs_ci_pg
def test_template_text_without_template_row_is_503(pg):  # noqa: F811
    """K4: 本文の行なしは 503。"""
    conn, _, async_url = pg
    cur = _prepare(conn, async_url, skip_templates=("notice_activated",))
    vid = _account(cur, "tt5@x.com", "trial", expires_in_days=5)
    resp = _api(async_url, "GET", _text_path(vid, "notice_activated"))
    assert resp.status_code == 503 and resp.json()["detail"] == "template_not_found"
