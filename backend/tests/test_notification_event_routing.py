"""通知の送信先振り分け ＋ 商談アサインの Discord 通知（design.md ⑤ A1-A12 / R1）。

対象:
  - GET  /notification-event-types（新規）
  - POST /notification-channels（event_types の既定値是正 + 検証）
  - PATCH /notification-channels/{id}（新規）
  - app.services.lead_assign_notifier.notify_lead_assigned（新規）
  - app.routers.leads.update_lead の fire-and-forget 呼び出し

A11（他テナント漏洩防止）について:
  本番の送信先分離は PostgreSQL の search_path によるスキーマ分離に依存していたが、
  コーディネータの設計変更により send_discord_notification の SELECT と
  update_channel の UPDATE に tenant_id 条件を多重防御として追加した
  （notification_channels.tenant_id 列を使う）。これにより SQLite 上でも
  行レベルで直接検証できる
  （test_send_discord_notification_only_posts_to_matching_tenant_row）。
  加えて、分離を支えるもう一段のアプリ層制御（ADR-072 の set_tenant_context 呼び出し）
  の確認テストも残している。
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text

from app.routers.notifications import send_discord_notification
from app.schemas.notification import NotificationEventType
from app.services.lead_assign_notifier import notify_lead_assigned

# Discord のユーザー ID は 18 桁の数字。18 桁の数字リテラルを直書きすると
# gitleaks の既定ルール discord-client-id が「実在の資格情報」として誤検知するため、
# 組み立てて作る（検出器の設定は緩めない）。いずれも架空の値。
FAKE_DISCORD_ID = "9" * 18
FAKE_DISCORD_ID_ALT = "8" * 18


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

class _SessionCtx:
    """`async with AsyncSessionLocal() as db:` を既存の db_session に固定する。

    既存の作法: test_webhook_instagram.py / test_adr072_phase_2_reset_rollout.py
    """

    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _capture_create_task():
    """asyncio.create_task を横取りし、notify_lead_assigned のタスクだけ記録する。

    実体は本物の asyncio.create_task に委譲する（audit middleware 等、他の
    create_task 呼び出しのスケジューリングを変えない）。記録したタスクを
    テスト側が明示的に await することで、イベントループのスケジューリング
    順に依存しない決定的なテストにする。
    """
    captured: list = []
    real_create_task = asyncio.create_task

    def _fake(coro, *a, **kw):
        task = real_create_task(coro, *a, **kw)
        if "notify_lead_assigned" in getattr(coro, "__qualname__", ""):
            captured.append(task)
        return task

    return captured, _fake


async def _insert_channel(db, *, tenant_id, channel_name, webhook_url, event_types, is_active=True):
    await db.execute(
        text("""
            INSERT INTO notification_channels (tenant_id, channel_name, webhook_url, event_types, is_active)
            VALUES (:tenant_id, :name, :url, :events, :is_active)
        """),
        {"tenant_id": tenant_id, "name": channel_name, "url": webhook_url,
         "events": json.dumps(event_types), "is_active": is_active},
    )


async def _insert_staff(db, *, tenant_id, user_id, surname_jp, given_name_jp, discord_user_id=None):
    await db.execute(
        text("""
            INSERT INTO staff (tenant_id, user_id, staff_code, surname_jp, given_name_jp, discord_user_id)
            VALUES (:tenant_id, :user_id, :staff_code, :surname_jp, :given_name_jp, :discord_user_id)
        """),
        {"tenant_id": tenant_id, "user_id": user_id, "staff_code": f"S{user_id:04d}",
         "surname_jp": surname_jp, "given_name_jp": given_name_jp,
         "discord_user_id": discord_user_id},
    )


async def _insert_lead(db, *, tenant_id, lead_id, customer_name, lead_code, assigned_to=None):
    await db.execute(
        text("""
            INSERT INTO leads (id, tenant_id, customer_name, lead_code, assigned_to)
            VALUES (:id, :tenant_id, :customer_name, :lead_code, :assigned_to)
        """),
        {"id": lead_id, "tenant_id": tenant_id, "customer_name": customer_name,
         "lead_code": lead_code, "assigned_to": assigned_to},
    )


@pytest.fixture
def notifier_env(db_session):
    """notify_lead_assigned が自前で開くセッションを db_session に固定する。"""
    with patch("app.database.AsyncSessionLocal", new=lambda: _SessionCtx(db_session)):
        yield db_session


# ---------------------------------------------------------------------------
# R1: event_types の部分一致安全性（互いに部分文字列でない）
# ---------------------------------------------------------------------------

def test_event_type_values_are_pairwise_non_substrings():
    """event_types LIKE '%x%' の部分一致で別の種類に誤ヒットしないことを保証する。"""
    values = [e.value for e in NotificationEventType]
    for a in values:
        for b in values:
            if a == b:
                continue
            assert a not in b, f"{a!r} は {b!r} の部分文字列 — LIKE 部分一致が誤爆する"


# ---------------------------------------------------------------------------
# A1: GET /notification-event-types
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_event_types_returns_three_codes(client):
    resp = await client.get("/api/v1/notification-event-types")
    assert resp.status_code == 200
    codes = [e["code"] for e in resp.json()]
    assert codes == ["lead_assigned", "meta_message_received", "tcg_distribution_error"]


# ---------------------------------------------------------------------------
# A2 / A3: POST /notification-channels
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_channel_rejects_unknown_event_type(client):
    resp = await client.post(
        "/api/v1/notification-channels",
        json={"channel_name": "c1", "webhook_url": "https://discord.example/webhooks/1",
              "event_types": ["bogus"]},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_channel_default_event_types_is_empty(client):
    resp = await client.post(
        "/api/v1/notification-channels",
        json={"channel_name": "c1", "webhook_url": "https://discord.example/webhooks/1"},
    )
    assert resp.status_code == 201
    assert json.loads(resp.json()["event_types"]) == []


# ---------------------------------------------------------------------------
# A4 / A5 / A6: PATCH /notification-channels/{id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_channel_updates_event_types_and_get_reflects(client):
    create_resp = await client.post(
        "/api/v1/notification-channels",
        json={"channel_name": "c1", "webhook_url": "https://discord.example/webhooks/1"},
    )
    channel_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/notification-channels/{channel_id}",
        json={"event_types": ["lead_assigned", "tcg_distribution_error"]},
    )
    assert patch_resp.status_code == 200
    assert sorted(json.loads(patch_resp.json()["event_types"])) == ["lead_assigned", "tcg_distribution_error"]

    get_resp = await client.get("/api/v1/notification-channels")
    row = next(c for c in get_resp.json() if c["id"] == channel_id)
    assert sorted(json.loads(row["event_types"])) == ["lead_assigned", "tcg_distribution_error"]


@pytest.mark.asyncio
async def test_patch_channel_requires_manage_permission(client):
    with patch("app.auth.dependencies.load_user_permissions",
               new=AsyncMock(return_value={"notifications.view"})):
        resp = await client.patch("/api/v1/notification-channels/1", json={"channel_name": "x"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_patch_channel_404_when_missing(client):
    resp = await client.patch("/api/v1/notification-channels/999999", json={"channel_name": "x"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_channel_404_when_other_tenant(client, db_session):
    """他テナント（tenant_id=1）の channel_id を client（tenant_id=999）から PATCH しても 404。"""
    await _insert_channel(db_session, tenant_id=1, channel_name="other-tenant",
                          webhook_url="https://discord.example/webhooks/other-tenant",
                          event_types=[])
    await db_session.commit()
    row = (await db_session.execute(
        text("SELECT id FROM notification_channels WHERE tenant_id = 1"),
    )).mappings().first()
    channel_id = row["id"]

    resp = await client.patch(f"/api/v1/notification-channels/{channel_id}", json={"channel_name": "hacked"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# A7 / A8: leads.update_lead からの fire-and-forget 呼び出し
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_lead_assigned_to_changed_sends_notification_once(client, db_session):
    await _insert_lead(db_session, tenant_id=999, lead_id=1, customer_name="Acme",
                       lead_code="L-0001", assigned_to=None)
    await _insert_staff(db_session, tenant_id=999, user_id=7, surname_jp="佐藤", given_name_jp="太郎",
                        discord_user_id=FAKE_DISCORD_ID_ALT)
    await db_session.commit()

    captured, fake_create_task = _capture_create_task()
    with patch("app.routers.leads.asyncio.create_task", side_effect=fake_create_task), \
         patch("app.database.AsyncSessionLocal", new=lambda: _SessionCtx(db_session)), \
         patch("app.services.lead_assign_notifier.send_discord_notification", new=AsyncMock()) as mock_send:
        resp = await client.patch("/api/v1/leads/1", json={"assigned_to": 7})
        assert resp.status_code == 200
        assert len(captured) == 1
        for coro in captured:
            await coro

    assert mock_send.await_count == 1
    _, kwargs = mock_send.await_args
    assert kwargs["event_type"] == NotificationEventType.lead_assigned.value


@pytest.mark.asyncio
async def test_patch_lead_same_assigned_to_does_not_notify(client, db_session):
    await _insert_lead(db_session, tenant_id=999, lead_id=2, customer_name="Acme",
                       lead_code="L-0002", assigned_to=7)
    await db_session.commit()

    captured, fake_create_task = _capture_create_task()
    with patch("app.routers.leads.asyncio.create_task", side_effect=fake_create_task), \
         patch("app.services.lead_assign_notifier.notify_lead_assigned", new=AsyncMock()) as mock_notify:
        resp = await client.patch("/api/v1/leads/2", json={"assigned_to": 7})

    assert resp.status_code == 200
    assert captured == []
    mock_notify.assert_not_called()


# ---------------------------------------------------------------------------
# A12: 通知失敗が商談更新のレスポンスに影響しない
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_lead_returns_200_even_if_notify_raises(client, db_session):
    await _insert_lead(db_session, tenant_id=999, lead_id=3, customer_name="Acme",
                       lead_code="L-0003", assigned_to=None)
    await db_session.commit()

    with patch("app.services.lead_assign_notifier.notify_lead_assigned",
               side_effect=RuntimeError("boom")):
        resp = await client.patch("/api/v1/leads/3", json={"assigned_to": 9})

    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# A9 / A10: send_discord_notification への payload（content / allowed_mentions）
# ---------------------------------------------------------------------------

class _FakeDiscordResponse:
    status_code = 204


class _FakeDiscordAsyncClient:
    """httpx.AsyncClient の代わりに payload を捕捉する。"""

    captured_payloads: list = []

    def __init__(self, *_a, **_kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    async def post(self, _url, json):  # noqa: A002 - httpx の引数名に合わせる
        _FakeDiscordAsyncClient.captured_payloads.append(json)
        return _FakeDiscordResponse()


@pytest.mark.asyncio
async def test_notify_lead_assigned_payload_has_mention_in_content_and_fails_closed(notifier_env):
    db = notifier_env
    _FakeDiscordAsyncClient.captured_payloads = []
    await _insert_channel(db, tenant_id=999, channel_name="internal",
                          webhook_url="https://discord.example/webhooks/1",
                          event_types=["lead_assigned"])
    await _insert_staff(db, tenant_id=999, user_id=5, surname_jp="谷澤", given_name_jp="伸吾",
                        discord_user_id=FAKE_DISCORD_ID)
    await _insert_lead(db, tenant_id=999, lead_id=10, customer_name="山田商事", lead_code="L-00123")
    await db.commit()

    with patch("app.routers.notifications.httpx.AsyncClient", _FakeDiscordAsyncClient):
        await notify_lead_assigned(tenant_id=999, lead_id=10, assigned_to_user_id=5)

    assert len(_FakeDiscordAsyncClient.captured_payloads) == 1
    payload = _FakeDiscordAsyncClient.captured_payloads[0]
    assert payload["content"] == f"<@{FAKE_DISCORD_ID}>"
    # フェイルクローズ: allowed_mentions.parse が空 + users を明示（@everyone 等の暴発防止）
    assert payload["allowed_mentions"] == {"parse": [], "users": [FAKE_DISCORD_ID]}


@pytest.mark.asyncio
async def test_notify_lead_assigned_posts_without_mention_when_discord_user_id_missing(notifier_env):
    db = notifier_env
    _FakeDiscordAsyncClient.captured_payloads = []
    await _insert_channel(db, tenant_id=999, channel_name="internal",
                          webhook_url="https://discord.example/webhooks/1",
                          event_types=["lead_assigned"])
    await _insert_staff(db, tenant_id=999, user_id=6, surname_jp="鈴木", given_name_jp="一郎",
                        discord_user_id=None)
    await _insert_lead(db, tenant_id=999, lead_id=11, customer_name="鈴木商店", lead_code="L-00124")
    await db.commit()

    with patch("app.routers.notifications.httpx.AsyncClient", _FakeDiscordAsyncClient):
        await notify_lead_assigned(tenant_id=999, lead_id=11, assigned_to_user_id=6)

    assert len(_FakeDiscordAsyncClient.captured_payloads) == 1
    payload = _FakeDiscordAsyncClient.captured_payloads[0]
    assert "content" not in payload
    assert "allowed_mentions" not in payload


# ---------------------------------------------------------------------------
# A11: 他テナントの送信先に送られないこと
#
# send_discord_notification の SELECT に tenant_id 条件が追加された（多重防御・
# コーディネータによる設計変更）ため、SQLite 上でも行レベルで直接検証できる。
# 以下の set_tenant_context 呼び出し確認テストは、分離を支えるもう一段のアプリ層
# 制御（ADR-072）の確認として残す。
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_discord_notification_only_posts_to_matching_tenant_row(db_session):
    """notification_channels に tenant_id の異なる2行を用意し、tenant_id=1 でだけ送信する。

    tenant_id=1 の webhook_url にのみ POST され、tenant_id=2 の webhook_url には
    一度も POST されないことを検証する（A11 の行レベル検証）。
    """
    db = db_session
    await _insert_channel(db, tenant_id=1, channel_name="tenant-1-internal",
                          webhook_url="https://discord.example/webhooks/tenant-1",
                          event_types=["lead_assigned"])
    await _insert_channel(db, tenant_id=2, channel_name="tenant-2-internal",
                          webhook_url="https://discord.example/webhooks/tenant-2",
                          event_types=["lead_assigned"])
    await db.commit()

    posted_urls: list[str] = []

    class _CapturingAsyncClient:
        def __init__(self, *_a, **_kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_a):
            return False

        async def post(self, url, json):  # noqa: A002 - httpx の引数名に合わせる
            posted_urls.append(url)
            return _FakeDiscordResponse()

    with patch("app.routers.notifications.httpx.AsyncClient", _CapturingAsyncClient):
        await send_discord_notification(db=db, tenant_id=1, event_type="lead_assigned",
                                        title="t", message="m")

    assert posted_urls == ["https://discord.example/webhooks/tenant-1"]
    assert "https://discord.example/webhooks/tenant-2" not in posted_urls


@pytest.mark.asyncio
async def test_notify_lead_assigned_sets_tenant_context_for_tenant_a_only(notifier_env):
    db = notifier_env
    await _insert_staff(db, tenant_id=1, user_id=101, surname_jp="A", given_name_jp="Tenant")
    await _insert_lead(db, tenant_id=1, lead_id=201, customer_name="TenantA Co", lead_code="L-A01")
    await db.commit()

    with patch("app.services.lead_assign_notifier.set_tenant_context", new=AsyncMock()) as mock_ctx, \
         patch("app.services.lead_assign_notifier.send_discord_notification", new=AsyncMock()):
        await notify_lead_assigned(tenant_id=1, lead_id=201, assigned_to_user_id=101)

    mock_ctx.assert_awaited_once_with(db, 1)


@pytest.mark.asyncio
async def test_notify_lead_assigned_sets_tenant_context_for_tenant_b_only(notifier_env):
    db = notifier_env
    await _insert_staff(db, tenant_id=2, user_id=102, surname_jp="B", given_name_jp="Tenant")
    await _insert_lead(db, tenant_id=2, lead_id=202, customer_name="TenantB Co", lead_code="L-B01")
    await db.commit()

    with patch("app.services.lead_assign_notifier.set_tenant_context", new=AsyncMock()) as mock_ctx, \
         patch("app.services.lead_assign_notifier.send_discord_notification", new=AsyncMock()):
        await notify_lead_assigned(tenant_id=2, lead_id=202, assigned_to_user_id=102)

    mock_ctx.assert_awaited_once_with(db, 2)
    # tenant 1 で呼ばれていないこと（コピペ・固定値化の防止）
    assert mock_ctx.await_args.args[1] != 1


async def _run_assign_notify(db, *, lead_id, customer_name, lead_code):
    await _insert_staff(db, tenant_id=999, user_id=8, surname_jp="佐藤", given_name_jp="花子",
                        discord_user_id=None)
    await _insert_lead(db, tenant_id=999, lead_id=lead_id, customer_name=customer_name,
                       lead_code=lead_code)
    await db.commit()
    with patch("app.services.lead_assign_notifier.send_discord_notification",
               new=AsyncMock()) as mock_send:
        await notify_lead_assigned(tenant_id=999, lead_id=lead_id, assigned_to_user_id=8)
    assert mock_send.await_count == 1
    return mock_send.await_args.kwargs["message"]


@pytest.mark.asyncio
async def test_notify_lead_assigned_message_has_customer_name(notifier_env):
    message = await _run_assign_notify(
        notifier_env, lead_id=30, customer_name="山田商事", lead_code="LD-00030")
    assert "山田商事" in message
    assert "佐藤 花子" in message


@pytest.mark.asyncio
async def test_notify_lead_assigned_message_for_empty_name(notifier_env):
    message = await _run_assign_notify(
        notifier_env, lead_id=31, customer_name="  ", lead_code="LD-00031")
    assert "名前の無いリード" in message


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["山田商事", ""])
async def test_notify_lead_assigned_message_never_has_lead_code(notifier_env, name):
    message = await _run_assign_notify(
        notifier_env, lead_id=32, customer_name=name, lead_code="LD-00032")
    assert "LD-00032" not in message
    assert "LD-" not in message


@pytest.mark.asyncio
async def test_notify_lead_assigned_message_for_null_name(notifier_env):
    """テスト用 DB は customer_name が NOT NULL のため、リード表だけ NULL を返す副問い合わせに差し替える。"""
    from app.auth.dependencies import tenant_table_ref as real_ref

    def fake_ref(db, tenant_id, table):
        if table == "leads":
            return "(SELECT 34 AS id, NULL AS customer_name)"
        return real_ref(db, tenant_id, table)

    db = notifier_env
    await _insert_staff(db, tenant_id=999, user_id=8, surname_jp="佐藤", given_name_jp="花子",
                        discord_user_id=None)
    await db.commit()
    with patch("app.services.lead_assign_notifier.tenant_table_ref", new=fake_ref), \
         patch("app.services.lead_assign_notifier.send_discord_notification",
               new=AsyncMock()) as mock_send:
        await notify_lead_assigned(tenant_id=999, lead_id=34, assigned_to_user_id=8)
    message = mock_send.await_args.kwargs["message"]
    assert "名前の無いリード" in message
    assert "LD-" not in message
