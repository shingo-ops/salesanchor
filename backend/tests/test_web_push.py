"""許可依頼の通知（web push・ADR-1055 段W）のテスト。SQLite で動かす。

段A の足場（fixture と手助けの関数）は test_new_device_approval.py から名前を挙げて使う（import * はしない）。
VAPID の3つは試験用の値で、実際の鍵は使わない。pywebpush.webpush は差し替える。
ログインの口を通す試験は app.routers.auth.send_login_request_push を差し替える
（本物は AsyncSessionLocal を開くが、試験の client は get_db しか差し替えないため）。
"""
# ruff: noqa: F811  (段A の fixture を名前で取り込むため、引数の名前が import と重なる)

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sqlalchemy as sa
from pywebpush import WebPushException
from sqlalchemy import text

from app.services import web_push
from tests.test_new_device_approval import (  # noqa: F401  (fixture は名前で取り込む)
    _T,
    AUTH,
    EMAIL,
    FLOOR,
    ORIGIN,
    OTHER_EMAIL,
    OTHER_USER_ID,
    USER_ID,
    _bearer,
    _first_machine,
    _insert_user,
    _login,
    _pending_from_new_machine,
    _row,
    _rows,
    base_env,
    enforce,
    machine,
    no_redis_and_spies,
    password_hash,
    spies,
)

EP = "https://fcm.googleapis.com/fcm/send/abc123"
EP2 = "https://updates.push.services.mozilla.com/wpush/v2/xyz"
KEYS = {"p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM", "auth": "tBHItJI5svbpez7KI4CCXg"}


@pytest.fixture(autouse=True)
def vapid_env(monkeypatch):
    monkeypatch.setenv("WEBPUSH_VAPID_PRIVATE_KEY", "test-private")
    monkeypatch.setenv("WEBPUSH_VAPID_PUBLIC_KEY", "test-public-key")
    monkeypatch.setenv("WEBPUSH_VAPID_SUBJECT", "https://app.salesanchor.jp/")


@pytest.fixture(autouse=True)
async def cleanup(db_session):
    """段A の cleanup はこの表を消さないので、同じ名前でこの表を先に消す版に差し替える。"""

    async def _wipe():
        await db_session.rollback()
        await db_session.execute(sa.text("DELETE FROM user_push_subscriptions"))
        for name in (
            "user_recovery_codes", "auth_login_requests", "auth_refresh_tokens",
            "user_trusted_devices", "password_reset_tokens",
        ):
            await db_session.execute(sa.delete(_T[name]))
        await db_session.execute(sa.delete(_T["users"]).where(_T["users"].c.id >= FLOOR))
        await db_session.commit()

    await _wipe()
    yield
    await _wipe()


def _b64(n: int) -> str:
    return "A" * n


async def _add_device(db, user_id: int, tag: str) -> int:
    await db.execute(
        text(
            "INSERT INTO user_trusted_devices (user_id, token_hash, label, created_via) "
            "VALUES (:u, :h, :l, 'first_login')"
        ),
        {"u": user_id, "h": tag.encode(), "l": tag},
    )
    await db.commit()
    return (await _row(db, "SELECT id FROM user_trusted_devices WHERE token_hash = :h", h=tag.encode())).id


async def _add_sub(db, user_id: int, device_id: int, endpoint: str, revoked=False) -> int:
    await db.execute(
        text(
            "INSERT INTO user_push_subscriptions (user_id, trusted_device_id, endpoint, p256dh, auth, revoked_at) "
            "VALUES (:u, :d, :e, :p, :a, :r)"
        ),
        {"u": user_id, "d": device_id, "e": endpoint, "p": KEYS["p256dh"], "a": KEYS["auth"],
         "r": datetime.now(timezone.utc) if revoked else None},
    )
    await db.commit()
    return (await _row(db, "SELECT id FROM user_push_subscriptions WHERE endpoint = :e", e=endpoint)).id


def _body(endpoint: str = EP, keys: dict | None = None) -> dict:
    return {"endpoint": endpoint, "keys": keys or KEYS}


async def _subs(db):
    return await _rows(db, "SELECT id, user_id, trusted_device_id, endpoint, revoked_at, last_success_at, failed_count "
                           "FROM user_push_subscriptions ORDER BY id")


# ── W-t1/W-t2/W-t2b: 依頼から通知まで ─────────────────────────────

async def test_wt1_request_triggers_one_push_for_all_subscriptions(enforce, machine, db_session, password_hash, spies):
    a, _tok = await _first_machine(machine, db_session, password_hash)
    dev_a = (await _row(db_session, "SELECT id FROM user_trusted_devices")).id
    dev_b = await _add_device(db_session, USER_ID, "second-machine")
    await _add_sub(db_session, USER_ID, dev_a, EP)
    await _add_sub(db_session, USER_ID, dev_b, EP2)
    sender = AsyncMock()

    with patch("app.routers.auth.send_login_request_push", new=sender):
        await _pending_from_new_machine(machine, db_session)

    sender.assert_awaited_once()
    targets = sender.await_args.args[0]
    assert len(targets) == 2
    assert {t.endpoint for t in targets} == {EP, EP2}
    assert sender.await_args.kwargs["when"] and sender.await_args.kwargs["device"]


async def test_wt2_without_vapid_no_push_but_request_and_mail_work(enforce, machine, db_session, password_hash, spies, monkeypatch):
    a, _tok = await _first_machine(machine, db_session, password_hash)
    dev_a = (await _row(db_session, "SELECT id FROM user_trusted_devices")).id
    await _add_sub(db_session, USER_ID, dev_a, EP)
    monkeypatch.delenv("WEBPUSH_VAPID_PRIVATE_KEY")
    sender = AsyncMock()
    spies.mail.reset_mock()

    with patch("app.routers.auth.send_login_request_push", new=sender):
        b = machine()
        resp = await _login(b)

    assert resp.status_code == 202
    sender.assert_not_awaited()
    spies.mail.assert_called_once()


async def test_wt2b_list_targets_error_does_not_break_request(enforce, machine, db_session, password_hash, spies):
    a, _tok = await _first_machine(machine, db_session, password_hash)
    spies.mail.reset_mock()
    sender = AsyncMock()

    with patch("app.routers.auth.send_login_request_push", new=sender), \
         patch("app.services.web_push.list_targets", new=AsyncMock(side_effect=RuntimeError("boom"))):
        b = machine()
        resp = await _login(b)

    assert resp.status_code == 202
    sender.assert_not_awaited()
    spies.mail.assert_called_once()


# ── W-t3: 送った結果の記録 ───────────────────────────────────────

async def _one_target(db_session, password_hash, endpoint=EP):
    await _insert_user(db_session, password_hash)
    dev = await _add_device(db_session, USER_ID, "dev-x")
    await _add_sub(db_session, USER_ID, dev, endpoint)
    return await web_push.list_targets(db_session, USER_ID)


def _exc(code: int) -> WebPushException:
    return WebPushException("failed", response=MagicMock(status_code=code))


@pytest.mark.parametrize("code", [410, 404])
async def test_wt3_gone_revokes_subscription(db_session, password_hash, code):
    targets = await _one_target(db_session, password_hash)
    with patch("pywebpush.webpush", side_effect=_exc(code)):
        results = await web_push.deliver(targets, {"title": "t"})
    assert results == [(targets[0].id, "gone")]

    await web_push.record_results(db_session, results)

    row = (await _subs(db_session))[0]
    assert row.revoked_at is not None


async def test_wt3_server_error_counts_failure_only(db_session, password_hash):
    targets = await _one_target(db_session, password_hash)
    with patch("pywebpush.webpush", side_effect=_exc(500)):
        results = await web_push.deliver(targets, {"title": "t"})
    assert results == [(targets[0].id, "failed")]

    await web_push.record_results(db_session, results)

    row = (await _subs(db_session))[0]
    assert row.failed_count == 1 and row.revoked_at is None and row.last_success_at is None


async def test_wt3_success_sets_last_success_and_resets_failures(db_session, password_hash):
    targets = await _one_target(db_session, password_hash)
    await db_session.execute(text("UPDATE user_push_subscriptions SET failed_count = 3"))
    await db_session.commit()
    with patch("pywebpush.webpush", return_value=MagicMock(status_code=201)):
        results = await web_push.deliver(targets, {"title": "t"})
    assert results == [(targets[0].id, "ok")]

    await web_push.record_results(db_session, results)

    row = (await _subs(db_session))[0]
    assert row.last_success_at is not None and row.failed_count == 0 and row.revoked_at is None


async def test_wt3_one_failure_does_not_stop_the_rest(db_session, password_hash):
    await _insert_user(db_session, password_hash)
    d1 = await _add_device(db_session, USER_ID, "d1")
    d2 = await _add_device(db_session, USER_ID, "d2")
    await _add_sub(db_session, USER_ID, d1, EP)
    await _add_sub(db_session, USER_ID, d2, EP2)
    targets = await web_push.list_targets(db_session, USER_ID)
    calls = []

    def fake(**kwargs):
        calls.append(kwargs["subscription_info"]["endpoint"])
        if kwargs["subscription_info"]["endpoint"] == EP:
            raise _exc(500)
        return MagicMock(status_code=201)

    with patch("pywebpush.webpush", side_effect=fake):
        results = await web_push.deliver(targets, {"title": "t"})

    assert sorted(r[1] for r in results) == ["failed", "ok"]
    assert sorted(calls) == sorted([EP, EP2])


# ── W-t4: 取り消した機械には送らない ─────────────────────────────

async def test_wt4_revoked_device_subscription_is_not_a_target(enforce, machine, db_session, password_hash):
    a, tok = await _first_machine(machine, db_session, password_hash)
    dev_a = (await _row(db_session, "SELECT id FROM user_trusted_devices")).id
    dev_b = await _add_device(db_session, USER_ID, "second-machine")
    await _add_sub(db_session, USER_ID, dev_a, EP)
    await _add_sub(db_session, USER_ID, dev_b, EP2)
    assert len(await web_push.list_targets(db_session, USER_ID)) == 2

    resp = await a.delete(f"{AUTH}/devices/{dev_b}", headers=_bearer(tok))

    assert resp.status_code == 204
    targets = await web_push.list_targets(db_session, USER_ID)
    assert [t.endpoint for t in targets] == [EP]


async def test_wt4_other_users_subscription_is_not_a_target(db_session, password_hash):
    await _insert_user(db_session, password_hash)
    await _insert_user(db_session, password_hash, user_id=OTHER_USER_ID, email=OTHER_EMAIL)
    mine = await _add_device(db_session, USER_ID, "mine")
    theirs = await _add_device(db_session, OTHER_USER_ID, "theirs")
    await _add_sub(db_session, USER_ID, mine, EP)
    await _add_sub(db_session, OTHER_USER_ID, theirs, EP2)

    targets = await web_push.list_targets(db_session, USER_ID)

    assert [t.endpoint for t in targets] == [EP]


# ── W-t5: 送り方 ─────────────────────────────────────────────────

async def test_wt5_fresh_claims_each_time_and_no_match_number(db_session, password_hash):
    await _insert_user(db_session, password_hash)
    d1 = await _add_device(db_session, USER_ID, "d1")
    d2 = await _add_device(db_session, USER_ID, "d2")
    await _add_sub(db_session, USER_ID, d1, EP)
    await _add_sub(db_session, USER_ID, d2, EP2)
    targets = await web_push.list_targets(db_session, USER_ID)
    seen: list[dict] = []
    datas: list[str] = []

    def fake(**kwargs):
        seen.append(kwargs["vapid_claims"])
        datas.append(kwargs["data"])
        kwargs["vapid_claims"]["aud"] = "x"  # pywebpush は渡された dict に書き足す
        return MagicMock(status_code=201)

    fake_session = MagicMock()
    fake_session.__aenter__ = AsyncMock(return_value=MagicMock())
    fake_session.__aexit__ = AsyncMock(return_value=False)
    with patch("pywebpush.webpush", side_effect=fake), \
         patch("app.services.web_push.AsyncSessionLocal", new=lambda: fake_session), \
         patch("app.services.web_push.record_results", new=AsyncMock()):
        await web_push.send_login_request_push(targets, when="2026/11/02 09:00", device="iPhone", location="Tokyo")

    assert len(seen) == 2 and seen[0] is not seen[1]
    assert seen[0] == {"sub": "https://app.salesanchor.jp/", "aud": "x"}
    payload = json.loads(datas[0])
    assert "match_number" not in payload and "match" not in json.dumps(payload)
    assert payload["body"] == "2026/11/02 09:00 / iPhone / Tokyo" and payload["url"] == "/"


async def test_wt5_body_without_location(db_session, password_hash):
    targets = await _one_target(db_session, password_hash)
    datas: list[str] = []

    def fake(**kwargs):
        datas.append(kwargs["data"])
        return MagicMock(status_code=201)

    fake_session = MagicMock()
    fake_session.__aenter__ = AsyncMock(return_value=MagicMock())
    fake_session.__aexit__ = AsyncMock(return_value=False)
    with patch("pywebpush.webpush", side_effect=fake), \
         patch("app.services.web_push.AsyncSessionLocal", new=lambda: fake_session), \
         patch("app.services.web_push.record_results", new=AsyncMock()):
        await web_push.send_login_request_push(targets, when="W", device="D", location=None)

    assert json.loads(datas[0])["body"] == "W / D"


async def test_wt5_send_login_request_push_never_raises(db_session, password_hash):
    targets = await _one_target(db_session, password_hash)
    with patch("app.services.web_push.deliver", new=AsyncMock(side_effect=RuntimeError("boom"))):
        await web_push.send_login_request_push(targets, when="W", device="D", location=None)


# ── W-t6: POST /auth/push-subscriptions ──────────────────────────

URL = f"{AUTH}/push-subscriptions"


async def test_wt6_post_ok_for_trusted_machine(enforce, machine, db_session, password_hash):
    a, tok = await _first_machine(machine, db_session, password_hash)

    resp = await a.post(URL, json=_body(), headers=_bearer(tok))

    assert resp.status_code == 200
    rows = await _subs(db_session)
    assert len(rows) == 1 and resp.json() == {"id": rows[0].id}
    dev = (await _row(db_session, "SELECT id FROM user_trusted_devices")).id
    assert rows[0].user_id == USER_ID and rows[0].trusted_device_id == dev and rows[0].revoked_at is None


async def test_wt6_post_without_trusted_device_is_403(machine, db_session, password_hash):
    # off（既定）のログインは sid だけで trusted_device_id が無い
    await _insert_user(db_session, password_hash, last_login=None)
    c = machine()
    tok = (await _login(c)).json()["access_token"]

    resp = await c.post(URL, json=_body(), headers=_bearer(tok))

    assert resp.status_code == 403 and resp.json()["detail"] == "not_trusted_device"


async def test_wt6_post_wrong_origin_is_403(enforce, machine, db_session, password_hash):
    a, tok = await _first_machine(machine, db_session, password_hash)

    resp = await a.post(URL, json=_body(), headers={"Authorization": f"Bearer {tok}", "origin": "https://evil.example"})

    assert resp.status_code == 403 and resp.json()["detail"] == "forbidden_origin"


async def test_wt6_post_without_vapid_is_409(enforce, machine, db_session, password_hash, monkeypatch):
    a, tok = await _first_machine(machine, db_session, password_hash)
    monkeypatch.delenv("WEBPUSH_VAPID_PUBLIC_KEY")

    resp = await a.post(URL, json=_body(), headers=_bearer(tok))

    assert resp.status_code == 409 and resp.json()["detail"] == "push_not_configured"


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://fcm.googleapis.com/fcm/send/abc",
        "https://example.com/push/abc",
        "https://evilfcm.googleapis.com.evil.com/x",
        "https://notfcm.googleapis.com.example/x",
        "https://127.0.0.1/x",
        "https://192.168.0.1:443/x",
        "https://[::1]/x",
        "https://127.0.0.1:6379\\@fcm.googleapis.com/x",
        "https://u:p@fcm.googleapis.com/x",
        "https://fcm.googleapis.com:8443/x",
        "https://fcm.googleapis.com/x y",
        "https://fcm.googleapis.com/x\ty",
        "https://fcm.googleapis.com/" + "a" * 2100,
        "",
    ],
)
async def test_wt6_post_bad_endpoint_is_422(enforce, machine, db_session, password_hash, endpoint):
    a, tok = await _first_machine(machine, db_session, password_hash)

    resp = await a.post(URL, json=_body(endpoint), headers=_bearer(tok))

    assert resp.status_code == 422
    assert (await _subs(db_session)) == []


@pytest.mark.parametrize(
    "keys",
    [
        {"p256dh": "A" * 201, "auth": KEYS["auth"]},
        {"p256dh": KEYS["p256dh"], "auth": "A" * 101},
        {"p256dh": "not base64!", "auth": KEYS["auth"]},
    ],
)
async def test_wt6_post_bad_keys_is_422(enforce, machine, db_session, password_hash, keys):
    a, tok = await _first_machine(machine, db_session, password_hash)

    resp = await a.post(URL, json=_body(EP, keys), headers=_bearer(tok))

    assert resp.status_code == 422


async def test_wt6_same_endpoint_twice_is_one_row(enforce, machine, db_session, password_hash):
    a, tok = await _first_machine(machine, db_session, password_hash)

    r1 = await a.post(URL, json=_body(), headers=_bearer(tok))
    r2 = await a.post(URL, json=_body(), headers=_bearer(tok))

    assert r1.status_code == r2.status_code == 200 and r1.json() == r2.json()
    assert len(await _subs(db_session)) == 1


async def test_wt6_new_endpoint_revokes_old_one_of_same_machine(enforce, machine, db_session, password_hash):
    a, tok = await _first_machine(machine, db_session, password_hash)
    await a.post(URL, json=_body(EP), headers=_bearer(tok))

    resp = await a.post(URL, json=_body(EP2), headers=_bearer(tok))

    assert resp.status_code == 200
    rows = await _subs(db_session)
    by_ep = {r.endpoint: r for r in rows}
    assert by_ep[EP].revoked_at is not None and by_ep[EP2].revoked_at is None


async def test_wt6_other_users_endpoint_is_409_and_nothing_changes(enforce, machine, db_session, password_hash):
    a, tok = await _first_machine(machine, db_session, password_hash)
    await _insert_user(db_session, password_hash, user_id=OTHER_USER_ID, email=OTHER_EMAIL)
    other_dev = await _add_device(db_session, OTHER_USER_ID, "other")
    await _add_sub(db_session, OTHER_USER_ID, other_dev, EP2)
    mine = await a.post(URL, json=_body(EP), headers=_bearer(tok))
    assert mine.status_code == 200

    resp = await a.post(URL, json=_body(EP2), headers=_bearer(tok))

    assert resp.status_code == 409 and resp.json()["detail"] == "push_subscription_conflict"
    by_ep = {r.endpoint: r for r in await _subs(db_session)}
    assert by_ep[EP2].user_id == OTHER_USER_ID and by_ep[EP2].trusted_device_id == other_dev
    assert by_ep[EP].revoked_at is None  # 送った人の機械の既存の購読は取り消されていない


# ── W-t7: DELETE ─────────────────────────────────────────────────

async def test_wt7_delete_own_then_again_then_others_then_origin(enforce, machine, db_session, password_hash):
    a, tok = await _first_machine(machine, db_session, password_hash)
    sub_id = (await a.post(URL, json=_body(), headers=_bearer(tok))).json()["id"]
    await _insert_user(db_session, password_hash, user_id=OTHER_USER_ID, email=OTHER_EMAIL)
    other_dev = await _add_device(db_session, OTHER_USER_ID, "other")
    other_sub = await _add_sub(db_session, OTHER_USER_ID, other_dev, EP2)

    wrong = await a.delete(f"{URL}/{sub_id}", headers={"Authorization": f"Bearer {tok}", "origin": "https://evil.example"})
    assert wrong.status_code == 403
    assert (await _subs(db_session))[0].revoked_at is None

    first = await a.delete(f"{URL}/{sub_id}", headers=_bearer(tok))
    assert first.status_code == 204
    revoked_at = (await _row(db_session, "SELECT revoked_at FROM user_push_subscriptions WHERE id = :i", i=sub_id)).revoked_at
    assert revoked_at is not None

    again = await a.delete(f"{URL}/{sub_id}", headers=_bearer(tok))
    assert again.status_code == 204
    assert (await _row(db_session, "SELECT revoked_at FROM user_push_subscriptions WHERE id = :i", i=sub_id)).revoked_at == revoked_at

    theirs = await a.delete(f"{URL}/{other_sub}", headers=_bearer(tok))
    assert theirs.status_code == 404
    assert (await _row(db_session, "SELECT revoked_at FROM user_push_subscriptions WHERE id = :i", i=other_sub)).revoked_at is None

    assert (await a.delete(f"{URL}/999999", headers=_bearer(tok))).status_code == 404


# ── W-t8: GET /auth/push-public-key ──────────────────────────────

async def test_wt8_public_key(enforce, machine, db_session, password_hash, monkeypatch):
    a, tok = await _first_machine(machine, db_session, password_hash)
    path = f"{AUTH}/push-public-key"

    ok = await a.get(path, headers=_bearer(tok))
    assert ok.status_code == 200 and ok.json() == {"public_key": "test-public-key"}

    monkeypatch.delenv("WEBPUSH_VAPID_SUBJECT")
    unset = await a.get(path, headers=_bearer(tok))
    assert unset.status_code == 200 and unset.json() == {"public_key": None}

    anon = await machine().get(path, headers={"origin": ORIGIN})
    assert anon.status_code == 401
