"""請求先フォーム（viewer-customer-sheet 便2）の試験。

PG（CI の使い捨て DB。pg fixture）: 表の CHECK・鍵の入口・送る API・フォームの2本の API。
送信部（部屋・メール）は差し替えて回数と宛先を数える。テストデータはすべて架空。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import psycopg2
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app import cache
from app.auth import self_tokens
from app.database import get_db
from tests.test_super_admin_viewers import (
    _account,
    _api,
    _prepare,
    needs_ci_pg,
)
from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture
from tests.test_viewer_api import FakeRedis

SEND = "/api/v1/super-admin/viewers/{}/send-billing-form"
PROFILE = "/api/v1/super-admin/viewers/{}/billing-profile"
OPEN = "/api/v1/viewer/billing-form/open"
SUBMIT = "/api/v1/viewer/billing-form/submit"

GOOD = {
    "party_type": "company",
    "bill_to_name": "株式会社テスト",
    "contact_name": "担当テスト",
    "postal_code": "100-0001",
    "address": "テスト県テスト市1-1",
    "phone": "03-0000-0000",
    "invoice_email": "",
}


def _prepare_billing(conn, async_url, **kw):
    cur = _prepare(conn, async_url, **kw)
    cur.execute((MIGRATIONS / "20261105_120000_create_viewer_billing_profiles.sql").read_text())
    return cur


def _tokens(cur, vid, purpose="billing_form"):
    cur.execute(
        "SELECT count(*) FROM public.viewer_login_tokens WHERE viewer_account_id = %s AND purpose = %s",
        (vid, purpose),
    )
    return cur.fetchone()[0]


def _send(async_url, vid, *, room=True):
    """送る API を呼ぶ。部屋・メールの送信部は差し替えて呼び出しを数える。"""
    with patch(
        "app.services.viewer_room_notice.send_room_notice", new=AsyncMock(return_value=room)
    ) as room_mock, patch("app.routers.super_admin_viewers.send_viewer_billing_form_email") as mail_mock:
        resp = _api(async_url, "POST", SEND.format(vid), {})
    return resp, room_mock, mail_mock


def _token_from(resp) -> str:
    text = resp.json()["room_notice_text"]
    return text.split("#billing=")[1].split()[0]


def _viewer_call(async_url, path, body, *, origin=None, ip="10.0.0.1", redis=None):
    async def _go():
        from app.main import app

        engine = create_async_engine(async_url, echo=False)

        async def _db():
            async with AsyncSession(engine, expire_on_commit=False) as session:
                yield session

        app.dependency_overrides[get_db] = _db
        fake = redis or FakeRedis()
        old = cache._redis
        cache._redis = fake
        try:
            headers = {"Origin": origin or self_tokens.rp_origin(), "X-Real-IP": ip}
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
                return await http.post(path, json=body, headers=headers)
        finally:
            cache._redis = old
            app.dependency_overrides.pop(get_db, None)
            await engine.dispose()

    return asyncio.run(_go())


def _insert_profile(cur, vid, **over):
    row = {
        "party_type": "company", "bill_to_name": "株式会社テスト", "contact_name": "担当テスト",
        "postal_code": "1000001", "address": "テスト県テスト市1-1", "phone": "0300000000", **over,
    }
    cur.execute(
        "INSERT INTO public.viewer_billing_profiles "
        "(viewer_account_id, party_type, bill_to_name, contact_name, postal_code, address, phone) "
        "VALUES (%(vid)s, %(party_type)s, %(bill_to_name)s, %(contact_name)s, %(postal_code)s, %(address)s, %(phone)s)",
        {**row, "vid": vid},
    )


# ── 表の決まり（CHECK） ───────────────────────────────────────


@needs_ci_pg
@pytest.mark.parametrize(
    "over, constraint",
    [
        ({"party_type": "company", "contact_name": None}, "ck_viewer_billing_profiles_contact_name"),
        ({"postal_code": "123456"}, "ck_viewer_billing_profiles_postal_code"),
        ({"phone": "123456789"}, "ck_viewer_billing_profiles_phone"),
        ({"bill_to_name": "   "}, "ck_viewer_billing_profiles_bill_to_name"),
    ],
)
def test_check_constraints_reject_bad_rows(pg, over, constraint):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "chk@x.com", "active")
    with pytest.raises(psycopg2.errors.CheckViolation) as exc:
        _insert_profile(cur, vid, **over)
    assert constraint in str(exc.value)


@needs_ci_pg
def test_deleting_viewer_deletes_profile(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "gone@x.com", "active")
    _insert_profile(cur, vid)
    cur.execute("DELETE FROM public.viewer_accounts WHERE id = %s", (vid,))
    cur.execute("SELECT count(*) FROM public.viewer_billing_profiles WHERE viewer_account_id = %s", (vid,))
    assert cur.fetchone()[0] == 0


@needs_ci_pg
def test_migration_is_idempotent_and_purpose_allows_billing_form(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    cur.execute((MIGRATIONS / "20261105_120000_create_viewer_billing_profiles.sql").read_text())
    vid = _account(cur, "p@x.com", "active")
    cur.execute(
        "INSERT INTO public.viewer_login_tokens (viewer_account_id, token_sha256, purpose, expires_at) "
        "VALUES (%s, decode(repeat('cd', 32), 'hex'), 'billing_form', NOW() + interval '1 day')",
        (vid,),
    )
    assert _tokens(cur, vid) == 1


@needs_ci_pg
def test_billing_fields_live_in_one_table_only(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    # この試験の DB に名簿と配信先の表があること（無ければ表を作らず止める）
    for name in ("public.viewer_accounts", "public.tcg_distribution_targets"):
        cur.execute("SELECT to_regclass(%s)", (name,))
        assert cur.fetchone()[0] is not None, f"{name} が無い"
    # 請求先の4列をすべて持つ public の表は viewer_billing_profiles だけ
    cur.execute(
        "SELECT table_name FROM information_schema.columns "
        "WHERE table_schema = 'public' "
        "AND column_name IN ('bill_to_name', 'contact_name', 'invoice_email', 'party_type') "
        "GROUP BY table_name HAVING count(DISTINCT column_name) = 4"
    )
    assert {r[0] for r in cur.fetchall()} == {"viewer_billing_profiles"}
    # 名簿と配信先には請求先の7列のどれも無い
    cur.execute(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' "
        "AND table_name IN ('viewer_accounts', 'tcg_distribution_targets') "
        "AND column_name IN ('party_type', 'bill_to_name', 'contact_name', 'postal_code', "
        "'address', 'phone', 'invoice_email')"
    )
    assert cur.fetchall() == []


# ── 送る API ──────────────────────────────────────────────────


@needs_ci_pg
def test_send_twice_leaves_one_key_and_old_link_is_invalid(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "twice@x.com", "active")
    first, _, _ = _send(async_url, vid)
    second, _, _ = _send(async_url, vid)
    assert first.status_code == 200 and second.status_code == 200
    assert _tokens(cur, vid) == 1
    old = _viewer_call(async_url, OPEN, {"token": _token_from(first)})
    new = _viewer_call(async_url, OPEN, {"token": _token_from(second)})
    assert old.status_code == 400 and new.status_code == 200


@needs_ci_pg
def test_send_expiry_is_seven_days_and_room_and_mail_are_called(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "seven@x.com", "active")
    cur.execute("UPDATE public.viewer_accounts SET discord_channel_id = '123456789012345678' WHERE id = %s", (vid,))
    before = datetime.now(timezone.utc)
    resp, room_mock, mail_mock = _send(async_url, vid)
    assert resp.status_code == 200
    body = resp.json()
    assert body["room_notice"] == "sent" and body["mail_queued"] is True
    cur.execute("SELECT expires_at FROM public.viewer_login_tokens WHERE viewer_account_id = %s", (vid,))
    expires = cur.fetchone()[0]
    assert timedelta(days=7) - timedelta(minutes=2) <= expires - before <= timedelta(days=7, minutes=2)
    assert room_mock.await_count == 1 and room_mock.await_args.args[0] == "123456789012345678"
    assert mail_mock.call_count == 1 and mail_mock.call_args.args[0] == "seven@x.com"
    assert "#billing=" in mail_mock.call_args.args[2] and "#billing=" in body["room_notice_text"]


@needs_ci_pg
def test_send_without_room_returns_no_room_and_text(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "noroom@x.com", "active")
    resp, room_mock, mail_mock = _send(async_url, vid)
    assert resp.status_code == 200 and resp.json()["room_notice"] == "no_room"
    assert "#billing=" in resp.json()["room_notice_text"]
    assert room_mock.await_count == 0 and mail_mock.call_count == 1


@needs_ci_pg
def test_send_room_failure_still_queues_mail(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "fail@x.com", "active")
    cur.execute("UPDATE public.viewer_accounts SET discord_channel_id = '123456789012345678' WHERE id = %s", (vid,))
    resp, _, mail_mock = _send(async_url, vid, room=False)
    assert resp.status_code == 200 and resp.json()["room_notice"] == "failed"
    assert mail_mock.call_count == 1


@needs_ci_pg
@pytest.mark.parametrize("status", ["pending", "verified", "trial", "suspended"])
def test_send_to_non_contracted_is_409_with_no_key(pg, status):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, f"{status}@x.com", status, expires_in_days=5 if status == "trial" else None)
    resp, room_mock, mail_mock = _send(async_url, vid)
    assert resp.status_code == 409 and resp.json()["detail"] == "viewer_status_conflict"
    assert _tokens(cur, vid) == 0 and room_mock.await_count == 0 and mail_mock.call_count == 0


@needs_ci_pg
def test_send_to_unknown_viewer_is_404(pg):  # noqa: F811
    conn, _, async_url = pg
    _prepare_billing(conn, async_url)
    resp, _, _ = _send(async_url, 987654)
    assert resp.status_code == 404


@needs_ci_pg
def test_send_without_template_is_503_with_no_key_and_no_send(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url, skip_templates=("billing_form_request",))
    vid = _account(cur, "notpl@x.com", "active")
    resp, room_mock, mail_mock = _send(async_url, vid)
    assert resp.status_code == 503 and resp.json()["detail"] == "template_not_found"
    assert _tokens(cur, vid) == 0 and room_mock.await_count == 0 and mail_mock.call_count == 0


@needs_ci_pg
def test_billing_profile_api_returns_null_then_row(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "prof@x.com", "active")
    empty = _api(async_url, "GET", PROFILE.format(vid))
    assert empty.status_code == 200 and empty.json() is None
    _insert_profile(cur, vid)
    got = _api(async_url, "GET", PROFILE.format(vid))
    assert got.status_code == 200 and got.json()["bill_to_name"] == "株式会社テスト"
    assert _api(async_url, "GET", PROFILE.format(vid), super_admin=False).status_code == 403


# ── フォームの2本 ─────────────────────────────────────────────


@needs_ci_pg
def test_open_keeps_key_and_returns_current_values(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "open@x.com", "active")
    _insert_profile(cur, vid)
    resp, _, _ = _send(async_url, vid)
    token = _token_from(resp)
    for _ in range(2):  # 何度開いても鍵は残る
        opened = _viewer_call(async_url, OPEN, {"token": token})
        assert opened.status_code == 200
        assert opened.json()["bill_to_name"] == "株式会社テスト" and opened.json()["postal_code"] == "1000001"
    assert _tokens(cur, vid) == 1


@needs_ci_pg
def test_open_returns_empty_values_when_no_profile(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "empty@x.com", "active")
    resp, _, _ = _send(async_url, vid)
    opened = _viewer_call(async_url, OPEN, {"token": _token_from(resp)})
    assert opened.status_code == 200 and opened.json()["party_type"] is None and opened.json()["address"] == ""


@needs_ci_pg
def test_submit_success_saves_and_consumes_key(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "submit@x.com", "active")
    token = _token_from(_send(async_url, vid)[0])
    resp = _viewer_call(async_url, SUBMIT, {"token": token, **GOOD})
    assert resp.status_code == 200
    assert _tokens(cur, vid) == 0
    cur.execute(
        "SELECT postal_code, phone, invoice_email FROM public.viewer_billing_profiles WHERE viewer_account_id = %s",
        (vid,),
    )
    assert cur.fetchone() == ("1000001", "0300000000", None)  # ハイフンを外した値で保存される
    again = _viewer_call(async_url, SUBMIT, {"token": token, **GOOD})
    assert again.status_code == 400  # 使い切った鍵は無効


@needs_ci_pg
def test_submit_invalid_input_keeps_key(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "bad@x.com", "active")
    token = _token_from(_send(async_url, vid)[0])
    for over in ({"contact_name": ""}, {"postal_code": "12345"}, {"phone": "12"}, {"bill_to_name": "  "}):
        resp = _viewer_call(async_url, SUBMIT, {"token": token, **{**GOOD, **over}})
        assert resp.status_code == 422, over
    assert _tokens(cur, vid) == 1  # 失敗では鍵が残る（同じリンクで送り直せる）


@needs_ci_pg
def test_submit_save_failure_rolls_back_and_key_remains(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "boom@x.com", "active")
    token = _token_from(_send(async_url, vid)[0])
    with patch("app.services.viewer_billing_form.upsert_profile", new=AsyncMock(side_effect=RuntimeError("x"))):
        resp = _viewer_call(async_url, SUBMIT, {"token": token, **GOOD})
    assert resp.status_code == 500
    assert _tokens(cur, vid) == 1
    ok = _viewer_call(async_url, SUBMIT, {"token": token, **GOOD})
    assert ok.status_code == 200 and _tokens(cur, vid) == 0


@needs_ci_pg
def test_submit_overwrites_existing_profile(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "over@x.com", "active")
    _insert_profile(cur, vid)
    token = _token_from(_send(async_url, vid)[0])
    resp = _viewer_call(async_url, SUBMIT, {"token": token, **{**GOOD, "party_type": "individual", "contact_name": ""}})
    assert resp.status_code == 200
    cur.execute("SELECT party_type, contact_name FROM public.viewer_billing_profiles WHERE viewer_account_id = %s", (vid,))
    assert cur.fetchone() == ("individual", None)
    cur.execute("SELECT count(*) FROM public.viewer_billing_profiles WHERE viewer_account_id = %s", (vid,))
    assert cur.fetchone()[0] == 1


@needs_ci_pg
def test_expired_or_wrong_purpose_or_not_active_keys_are_invalid(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "inv@x.com", "active")
    token = _token_from(_send(async_url, vid)[0])
    cur.execute("UPDATE public.viewer_login_tokens SET expires_at = NOW() - interval '1 minute' WHERE viewer_account_id = %s", (vid,))
    assert _viewer_call(async_url, OPEN, {"token": token}).status_code == 400
    assert _viewer_call(async_url, SUBMIT, {"token": token, **GOOD}).status_code == 400
    # 別の用途の鍵では開けない
    import hashlib

    cur.execute(
        "INSERT INTO public.viewer_login_tokens (viewer_account_id, token_sha256, purpose, expires_at) "
        "VALUES (%s, %s, 'password_reset', NOW() + interval '1 hour')",
        (vid, psycopg2.Binary(hashlib.sha256(b"other-purpose").digest())),
    )
    assert _viewer_call(async_url, OPEN, {"token": "other-purpose"}).status_code == 400
    # 本契約でなくなった人
    token2 = _token_from(_send(async_url, vid)[0])
    cur.execute("UPDATE public.viewer_accounts SET status = 'suspended' WHERE id = %s", (vid,))
    assert _viewer_call(async_url, OPEN, {"token": token2}).status_code == 400
    assert _viewer_call(async_url, SUBMIT, {"token": token2, **GOOD}).status_code == 400
    assert _tokens(cur, vid) == 0  # 送信では鍵が消費されたまま
    cur.execute("SELECT count(*) FROM public.viewer_billing_profiles WHERE viewer_account_id = %s", (vid,))
    assert cur.fetchone()[0] == 0


@needs_ci_pg
def test_form_apis_reject_foreign_origin_and_rate_limit(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "rl@x.com", "active")
    token = _token_from(_send(async_url, vid)[0])
    for path, body in ((OPEN, {"token": token}), (SUBMIT, {"token": token, **GOOD})):
        resp = _viewer_call(async_url, path, body, origin="https://evil.example")
        assert resp.status_code == 403 and resp.json()["detail"] == "forbidden_origin"
    assert _tokens(cur, vid) == 1
    # 失敗を重ねると 429
    fake = FakeRedis()
    codes = [
        _viewer_call(async_url, OPEN, {"token": "no-such-key"}, redis=fake).status_code for _ in range(12)
    ]
    assert codes[0] == 400 and codes[-1] == 429


@needs_ci_pg
def test_logs_do_not_contain_key_or_profile_values(pg, caplog):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "log@x.com", "active")
    token = _token_from(_send(async_url, vid)[0])
    caplog.set_level("DEBUG")
    _viewer_call(async_url, SUBMIT, {"token": token, **GOOD})
    joined = "\n".join(r.getMessage() for r in caplog.records)
    for secret in (token, "株式会社テスト", "テスト県", "0300000000", "1000001"):
        assert secret not in joined
