"""閲覧者向け文面テンプレート（ADR-1019 段11 便1・便2）の試験。

非 PG: validate・copy_text・render・load_rendered・403・PUT の入力検査（422/404）と競合の応答。
PG（CI の使い捨て DB。pg fixture）: 一覧 GET・PUT の 200/409/INSERT。
テストデータはすべて架空。
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.database import get_db
from app.discord_gateway import viewer_bot_texts as T
from app.services import viewer_message_templates as vmt
from tests.test_super_admin_viewers import _api, _call, _make_user, _prepare, needs_ci_pg, override_user  # noqa: F401
from tests.viewer_template_fixtures import DEFAULT_BODIES, make_load_body
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

KEYS = [
    "signup_request", "reissue_notice", "reissue_notice_no_invite", "room_welcome", "room_recreated",
    "notice_extended", "notice_activated", "notice_suspended", "interview_request",
]


def _code(key, body):
    with pytest.raises(vmt.TemplateInvalid) as exc:
        vmt.validate(key, body)
    return exc.value.code


# ── 非 PG: validate ───────────────────────────────────────────


def test_ledger_has_the_nine_keys_in_order():
    assert [s.key for s in vmt.LEDGER] == KEYS


@pytest.mark.parametrize("key", KEYS)
def test_current_nine_constants_pass_validate(key):
    vmt.validate(key, DEFAULT_BODIES[key])


@pytest.mark.parametrize(
    "body,code",
    [
        ("在庫のご案内です", "placeholders"),  # 不足
        ("{email} {password} {extra}", "placeholders"),  # 余計
        ("{email} {password}{email.x}", "placeholders"),
        ("{email} {password[0]}", "placeholders"),
        ("{email} {password} {}", "placeholders"),
        ("{email} {password} {0}", "placeholders"),
        ("{email!r} {password}", "format_spec"),
        ("{email:>10} {password}", "format_spec"),
        ("{email} {password} abc}", "bad_syntax"),
        ("{email} {password} {abc", "bad_syntax"),
        ("", "empty"),
        ("{email} {password}" + "あ" * 1800, "too_long"),
    ],
)
def test_validate_rejects_bad_bodies(body, code):
    assert _code("room_welcome", body) == code


def test_validate_boundary_1800_ok_and_1801_not():
    pad = "あ" * (1800 - len("{email}"))
    vmt.validate("room_recreated", "{email}" + pad)
    assert _code("room_recreated", "{email}" + pad + "あ") == "too_long"


def test_validate_allows_escaped_braces_but_not_as_placeholder():
    vmt.validate("notice_activated", "{{x}} 本登録です")
    assert _code("room_recreated", "{{email}}") == "placeholders"


def test_validate_unknown_key_and_non_string():
    assert _code("nope", "x") == "unknown_key"
    assert _code("notice_activated", None) == "empty"


@pytest.mark.parametrize("key", ["reissue_notice", "reissue_notice_no_invite"])
def test_reissue_must_start_with_line_name_san(key):
    good = DEFAULT_BODIES[key]
    assert good.startswith("{line_name}さん、")
    bad = good.replace("{line_name}さん、", "{line_name} さん、", 1)
    assert _code(key, bad) == "line_name_prefix"
    assert _code(key, "こんにちは、" + good.replace("{line_name}さん、", "{line_name}")) == "line_name_prefix"


def test_copy_text_fills_only_signup_url():
    text_ = vmt.build_copy_text("signup_request", DEFAULT_BODIES["signup_request"])
    assert T.SIGNUP_URL in text_ and "?openExternalBrowser=1#signup" in text_ and "{signup_url}" not in text_
    notice = vmt.build_copy_text("reissue_notice", DEFAULT_BODIES["reissue_notice"])
    assert "{line_name}" in notice and "{code}" in notice and "{invite_url}" in notice
    assert vmt.build_copy_text("notice_activated", DEFAULT_BODIES["notice_activated"]) == DEFAULT_BODIES["notice_activated"]
    assert vmt.build_copy_text("room_welcome", "壊れた {email") is None


# ── 非 PG: 権限 ───────────────────────────────────────────────


async def test_viewer_templates_get_is_403_for_non_super_admin(override_user):  # noqa: F811
    override_user(_make_user(is_super_admin=False))
    resp = await _call("GET", "/api/v1/super-admin/viewer-templates", None)
    assert resp.status_code == 403


def _fake_db():
    db = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def fake_db():
    from app.main import app

    db = _fake_db()

    async def _dep():
        yield db

    app.dependency_overrides[get_db] = _dep
    return db


async def test_put_is_403_for_non_super_admin(override_user, fake_db):  # noqa: F811
    override_user(_make_user(is_super_admin=False))
    resp = await _call(
        "PUT", "/api/v1/super-admin/viewer-templates/notice_activated", {"body": "x", "expected_updated_at": None}
    )
    assert resp.status_code == 403


async def test_put_unknown_key_is_404(override_user, fake_db):  # noqa: F811
    override_user(_make_user(is_super_admin=True))
    resp = await _call(
        "PUT", "/api/v1/super-admin/viewer-templates/nope", {"body": "x", "expected_updated_at": None}
    )
    assert resp.status_code == 404
    fake_db.commit.assert_not_awaited()


@pytest.mark.parametrize(
    "key,body,detail",
    [
        ("room_welcome", "在庫のご案内です", "template_placeholders"),  # 不足
        ("room_welcome", "{email} {password} {extra}", "template_placeholders"),  # 余計
        ("room_welcome", "", "template_empty"),
        ("room_recreated", "{email}" + "あ" * 1794, "template_too_long"),  # 1801 字
        ("room_welcome", "{email} {password} {abc", "template_bad_syntax"),  # 括弧崩れ
        ("room_welcome", "{email!r} {password}", "template_format_spec"),
        ("reissue_notice_no_invite", "{line_name} さん、{code}{expires}", "template_line_name_prefix"),  # 書き出し違い
    ],
)
async def test_put_invalid_body_is_422_with_code(override_user, fake_db, key, body, detail):  # noqa: F811
    override_user(_make_user(is_super_admin=True))
    resp = await _call("PUT", f"/api/v1/super-admin/viewer-templates/{key}", {"body": body, "expected_updated_at": None})
    assert resp.status_code == 422 and resp.json()["detail"] == detail
    fake_db.commit.assert_not_awaited()


async def test_put_conflict_is_409(override_user, fake_db):  # noqa: F811
    override_user(_make_user(is_super_admin=True))
    with patch.object(vmt, "save_body", new=AsyncMock(side_effect=vmt.TemplateConflict())):
        resp = await _call(
            "PUT",
            "/api/v1/super-admin/viewer-templates/notice_activated",
            {"body": "本登録です", "expected_updated_at": "2026-10-20T00:00:00Z"},
        )
    assert resp.status_code == 409 and resp.json()["detail"] == "template_conflict"
    fake_db.commit.assert_not_awaited()
    fake_db.rollback.assert_awaited()


async def test_put_success_returns_the_get_row_shape(override_user, fake_db):  # noqa: F811
    override_user(_make_user(is_super_admin=True))
    now = datetime(2026, 10, 21, tzinfo=timezone.utc)
    rows = [
        {
            "key": s.key, "body": "本登録です" if s.key == "notice_activated" else None,
            "copy_text": "本登録です" if s.key == "notice_activated" else None,
            "placeholders": list(s.placeholders), "send_mode": s.send_mode,
            "updated_at": now if s.key == "notice_activated" else None,
            "updated_by_name": "Test User" if s.key == "notice_activated" else None,
        }
        for s in vmt.LEDGER
    ]
    save = AsyncMock()
    with patch.object(vmt, "save_body", new=save), patch.object(vmt, "list_rows", new=AsyncMock(return_value=rows)):
        resp = await _call(
            "PUT", "/api/v1/super-admin/viewer-templates/notice_activated",
            {"body": "本登録です", "expected_updated_at": None},
        )
    assert resp.status_code == 200
    j = resp.json()
    assert j["key"] == "notice_activated" and j["body"] == "本登録です" and j["updated_by_name"] == "Test User"
    assert save.await_args.args[1:4] == ("notice_activated", "本登録です", None) and save.await_args.args[4] == 999
    fake_db.commit.assert_awaited_once()


# ── 非 PG: 台帳の読み出し（load_rendered / render） ─────────────────


async def test_load_rendered_uses_db_body_and_fills_values():
    with patch.object(vmt, "load_body", new=make_load_body({"notice_extended": "{until_date}まで延ばしました"})):
        assert await vmt.load_rendered(object(), "notice_extended", until_date="11月3日") == "11月3日まで延ばしました"


async def test_load_rendered_none_when_row_missing():
    with patch.object(vmt, "load_body", new=make_load_body({"notice_extended": None})):
        assert await vmt.load_rendered(object(), "notice_extended", until_date="x") is None


async def test_load_body_none_when_row_missing_or_invalid(caplog):
    caplog.set_level("WARNING")

    def _db(row):
        res = MagicMock()
        res.first.return_value = row
        db = MagicMock()
        db.execute = AsyncMock(return_value=res)
        return db

    assert await vmt.load_body(_db(None), "notice_activated") is None
    assert await vmt.load_body(_db(("壊れた {x",)), "notice_activated") is None
    assert await vmt.load_body(_db(("本登録です",)), "notice_activated") == "本登録です"
    assert "template missing" in caplog.text and "template invalid" in caplog.text


def test_render_failures_are_none_not_exceptions():
    assert vmt.render("room_welcome", "{email}{password}", email="a") is None  # 値が足りない
    assert vmt.render("nope", "x") is None
    assert vmt.render("room_welcome", "壊れた {email", email="a", password="b") is None


def test_render_reissue_drops_leading_san_when_name_empty():
    body = DEFAULT_BODIES["reissue_notice_no_invite"]
    with_name = vmt.render("reissue_notice_no_invite", body, line_name="架空", code="A", expires="11月1日 10:00")
    assert with_name.startswith("架空さん、申込コードを作り直しました。")
    no_name = vmt.render("reissue_notice_no_invite", body, line_name="  ", code="A", expires="11月1日 10:00")
    assert no_name.startswith("申込コードを作り直しました。")


def test_render_auto_over_2000_is_none_but_manual_is_not(caplog):
    caplog.set_level("WARNING")
    over = "{password}" + "あ" * 1700
    assert vmt.render("room_welcome", "{email}" + over, email="e" * 300, password="p" * 300) is None
    assert "too long" in caplog.text
    pad = "あ" * 1700
    long_manual = vmt.render("signup_request", "{signup_url}" + pad, signup_url="u" * 400)
    assert long_manual is not None and len(long_manual) > 2000  # コピー用は長さで落とさない


# ── PG ────────────────────────────────────────────────────────


def _insert(cur, key, body, *, user_id=None):
    cur.execute(
        "INSERT INTO public.viewer_message_templates (key, body, updated_by_user_id) VALUES (%s, %s, %s)",
        (key, body, user_id),
    )


@needs_ci_pg
def test_get_returns_nine_rows_with_null_body_for_missing_keys(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url, seed_templates=False)
    _insert(cur, "signup_request", DEFAULT_BODIES["signup_request"])
    _insert(cur, "room_welcome", DEFAULT_BODIES["room_welcome"], user_id=999)
    resp = _api(async_url, "GET", "/api/v1/super-admin/viewer-templates")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [i["key"] for i in items] == KEYS
    by_key = {i["key"]: i for i in items}
    assert by_key["signup_request"]["body"] == DEFAULT_BODIES["signup_request"]
    assert T.SIGNUP_URL in by_key["signup_request"]["copy_text"]
    assert by_key["signup_request"]["send_mode"] == "manual" and by_key["room_welcome"]["send_mode"] == "auto"
    assert by_key["reissue_notice"]["placeholders"] == ["line_name", "code", "expires", "invite_url"]
    assert by_key["notice_activated"]["placeholders"] == []
    for k in KEYS:
        if k not in ("signup_request", "room_welcome"):
            assert by_key[k]["body"] is None and by_key[k]["copy_text"] is None
            assert by_key[k]["updated_at"] is None and by_key[k]["updated_by_name"] is None
    assert by_key["signup_request"]["updated_by_name"] is None
    assert by_key["room_welcome"]["updated_by_name"] == "Test User"  # full_name があればそれ
    assert by_key["room_welcome"]["updated_at"] is not None


@needs_ci_pg
def test_get_updated_by_name_falls_back_to_username_when_full_name_empty(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url, seed_templates=False)
    cur.execute("UPDATE public.users SET full_name = '' WHERE id = 999")
    _insert(cur, "room_welcome", DEFAULT_BODIES["room_welcome"], user_id=999)
    resp = _api(async_url, "GET", "/api/v1/super-admin/viewer-templates")
    assert resp.status_code == 200
    by_key = {i["key"]: i for i in resp.json()["items"]}
    assert by_key["room_welcome"]["updated_by_name"] == "testuser"  # full_name が空なら username


@needs_ci_pg
def test_get_is_403_for_non_super_admin_on_pg(pg):  # noqa: F811
    conn, _, async_url = pg
    _prepare(conn, async_url, seed_templates=False)
    assert _api(async_url, "GET", "/api/v1/super-admin/viewer-templates", super_admin=False).status_code == 403


def _put(async_url, key, body, expected):
    return _api(
        async_url, "PUT", f"/api/v1/super-admin/viewer-templates/{key}",
        {"body": body, "expected_updated_at": expected},
    )


def _row(cur, key):
    cur.execute("SELECT body, updated_by_user_id, updated_at FROM public.viewer_message_templates WHERE key = %s", (key,))
    return cur.fetchone()


@needs_ci_pg
def test_put_null_expected_inserts_when_row_missing_then_409_when_it_exists(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url, seed_templates=False)
    resp = _put(async_url, "notice_activated", "本登録です", None)
    assert resp.status_code == 200
    j = resp.json()
    assert j["key"] == "notice_activated" and j["body"] == "本登録です" and j["updated_at"] is not None
    assert j["updated_by_name"] == "Test User" and j["copy_text"] == "本登録です"
    assert _row(cur, "notice_activated")[:2] == ("本登録です", 999)
    resp = _put(async_url, "notice_activated", "別の文です", None)  # 行があるのに null は 409
    assert resp.status_code == 409 and resp.json()["detail"] == "template_conflict"
    assert _row(cur, "notice_activated")[0] == "本登録です"


@needs_ci_pg
def test_put_with_expected_updates_then_stale_expected_is_409(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url, seed_templates=False)
    _insert(cur, "notice_activated", "古い文です")
    opened = _api(async_url, "GET", "/api/v1/super-admin/viewer-templates").json()["items"]
    opened_at = {i["key"]: i for i in opened}["notice_activated"]["updated_at"]
    resp = _put(async_url, "notice_activated", "新しい文です", opened_at)
    assert resp.status_code == 200 and resp.json()["body"] == "新しい文です"
    assert resp.json()["updated_at"] != opened_at and resp.json()["updated_by_name"] == "Test User"
    stale = _put(async_url, "notice_activated", "遅れた人の文です", opened_at)  # 開いた時の時刻はもう古い
    assert stale.status_code == 409
    assert _row(cur, "notice_activated")[0] == "新しい文です"


@needs_ci_pg
def test_put_expected_for_missing_row_is_409_and_invalid_is_422_without_write(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url, seed_templates=False)
    assert _put(async_url, "notice_activated", "本登録です", "2026-10-20T00:00:00Z").status_code == 409
    assert _put(async_url, "notice_activated", "", None).status_code == 422
    assert _put(async_url, "nope", "x", None).status_code == 404
    assert _row(cur, "notice_activated") is None
    assert _api(async_url, "PUT", "/api/v1/super-admin/viewer-templates/notice_activated",
                {"body": "x", "expected_updated_at": None}, super_admin=False).status_code == 403
