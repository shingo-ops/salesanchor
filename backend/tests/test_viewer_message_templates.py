"""閲覧者向け文面テンプレート（ADR-1019 段11 便1）の試験。

非 PG: validate・copy_text・403。PG（CI の使い捨て DB。pg fixture）: 一覧 GET・seed/verify CLI。
テストデータはすべて架空。
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.discord_gateway import viewer_bot_texts as T
from app.services import viewer_message_templates as vmt
from tests.test_super_admin_viewers import _api, _call, _make_user, _prepare, needs_ci_pg, override_user  # noqa: F401
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
    vmt.validate(key, vmt.seed_bodies()[key])


def test_seed_bodies_are_the_current_constants():
    assert vmt.seed_bodies()["room_welcome"] is T.ROOM_WELCOME
    assert vmt.seed_bodies()["interview_request"] is T.INTERVIEW_REQUEST


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
    good = vmt.seed_bodies()[key]
    assert good.startswith("{line_name}さん、")
    bad = good.replace("{line_name}さん、", "{line_name} さん、", 1)
    assert _code(key, bad) == "line_name_prefix"
    assert _code(key, "こんにちは、" + good.replace("{line_name}さん、", "{line_name}")) == "line_name_prefix"


def test_copy_text_fills_only_signup_url():
    text_ = vmt.build_copy_text("signup_request", T.SIGNUP_REQUEST)
    assert T.SIGNUP_URL in text_ and "?openExternalBrowser=1#signup" in text_ and "{signup_url}" not in text_
    notice = vmt.build_copy_text("reissue_notice", T.REISSUE_NOTICE)
    assert "{line_name}" in notice and "{code}" in notice and "{invite_url}" in notice
    assert vmt.build_copy_text("notice_activated", T.NOTICE_ACTIVATED) == T.NOTICE_ACTIVATED
    assert vmt.build_copy_text("room_welcome", "壊れた {email") is None


# ── 非 PG: 権限 ───────────────────────────────────────────────


async def test_viewer_templates_get_is_403_for_non_super_admin(override_user):  # noqa: F811
    override_user(_make_user(is_super_admin=False))
    resp = await _call("GET", "/api/v1/super-admin/viewer-templates", None)
    assert resp.status_code == 403


async def test_viewer_templates_has_no_put_in_bin1(override_user):  # noqa: F811
    override_user(_make_user(is_super_admin=True))
    resp = await _call("PUT", "/api/v1/super-admin/viewer-templates/signup_request", {"body": "x"})
    assert resp.status_code in (404, 405)


# ── PG ────────────────────────────────────────────────────────


def _insert(cur, key, body, *, user_id=None):
    cur.execute(
        "INSERT INTO public.viewer_message_templates (key, body, updated_by_user_id) VALUES (%s, %s, %s)",
        (key, body, user_id),
    )


@needs_ci_pg
def test_get_returns_nine_rows_with_null_body_for_missing_keys(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    _insert(cur, "signup_request", T.SIGNUP_REQUEST)
    _insert(cur, "room_welcome", T.ROOM_WELCOME, user_id=999)
    resp = _api(async_url, "GET", "/api/v1/super-admin/viewer-templates")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [i["key"] for i in items] == KEYS
    by_key = {i["key"]: i for i in items}
    assert by_key["signup_request"]["body"] == T.SIGNUP_REQUEST
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
    cur = _prepare(conn, async_url)
    cur.execute("UPDATE public.users SET full_name = '' WHERE id = 999")
    _insert(cur, "room_welcome", T.ROOM_WELCOME, user_id=999)
    resp = _api(async_url, "GET", "/api/v1/super-admin/viewer-templates")
    assert resp.status_code == 200
    by_key = {i["key"]: i for i in resp.json()["items"]}
    assert by_key["room_welcome"]["updated_by_name"] == "testuser"  # full_name が空なら username


@needs_ci_pg
def test_get_is_403_for_non_super_admin_on_pg(pg):  # noqa: F811
    conn, _, async_url = pg
    _prepare(conn, async_url)
    assert _api(async_url, "GET", "/api/v1/super-admin/viewer-templates", super_admin=False).status_code == 403


def _cli(async_url, payload):
    from app import viewer_template_cli

    async def _go():
        engine = create_async_engine(async_url, echo=False)
        try:
            return await viewer_template_cli.run(payload, session_factory=async_sessionmaker(engine, expire_on_commit=False))
        finally:
            await engine.dispose()

    return asyncio.run(_go())


def _rows(cur):
    cur.execute("SELECT key, body FROM public.viewer_message_templates ORDER BY key")
    return dict(cur.fetchall())


@needs_ci_pg
def test_cli_seed_dry_run_writes_nothing_then_seed_inserts_only_missing(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    _insert(cur, "notice_extended", "手で直した文 {until_date}")
    res = _cli(async_url, {"action": "seed", "dry_run": True})
    assert res["dry_run"] is True and sorted(res["would_insert"]) == sorted(k for k in KEYS if k != "notice_extended")
    assert list(_rows(cur)) == ["notice_extended"]
    res = _cli(async_url, {"action": "seed", "dry_run": False})
    assert sorted(res["inserted"]) == sorted(k for k in KEYS if k != "notice_extended")
    rows = _rows(cur)
    assert sorted(rows) == sorted(KEYS)
    assert rows["notice_extended"] == "手で直した文 {until_date}"  # ある行は触らない
    assert rows["room_welcome"] == T.ROOM_WELCOME
    res = _cli(async_url, {"action": "seed", "dry_run": False})
    assert res["inserted"] == []


@needs_ci_pg
def test_cli_verify_reports_exists_and_matches_per_key(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    _insert(cur, "signup_request", T.SIGNUP_REQUEST)
    _insert(cur, "room_welcome", T.ROOM_WELCOME + "!")
    res = _cli(async_url, {"action": "verify"})
    assert list(res["keys"]) == KEYS
    assert res["keys"]["signup_request"] == {"exists": True, "matches": True}
    assert res["keys"]["room_welcome"] == {"exists": True, "matches": False}
    assert res["keys"]["notice_suspended"] == {"exists": False, "matches": False}
    assert T.ROOM_WELCOME not in str(res)  # 本文は出さない


@pytest.mark.parametrize(
    "payload",
    [{}, {"action": "drop"}, {"action": "seed"}, {"action": "seed", "dry_run": "yes"}, [], "seed"],
)
def test_cli_rejects_invalid_input(payload):
    from app import viewer_template_cli

    with pytest.raises(viewer_template_cli.ViewerTemplateError):
        asyncio.run(viewer_template_cli.run(payload, session_factory=None))


def test_cli_seed_writes_nothing_when_a_constant_fails_validate(monkeypatch):
    from app import viewer_template_cli

    monkeypatch.setattr(T, "NOTICE_EXTENDED", "延長しました {unknown}")

    class _NoDb:
        def __call__(self):
            raise AssertionError("DB must not be opened")

    with pytest.raises(viewer_template_cli.ViewerTemplateError) as exc:
        asyncio.run(viewer_template_cli.run({"action": "seed", "dry_run": False}, session_factory=_NoDb()))
    assert exc.value.code == "invalid_constant"
