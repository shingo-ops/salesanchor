"""bots.owner_staff_id は public.users.id を指す（ADR-1008 P2）。

- 作成・更新時、同一テナントの users.id なら成功、別テナントの users.id なら 400
- 一覧の owner_staff_name は staff.user_id で結んだ名簿の氏名
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import text

_SAME_TENANT_USER_ID = 4001
_OTHER_TENANT_USER_ID = 4002


@pytest_asyncio.fixture
async def seeded(client, db_session):
    await db_session.execute(
        text(
            "INSERT OR IGNORE INTO users (id, tenant_id, username, email, role, is_active) "
            "VALUES (:u1, 999, 'same', 'same@example.com', 'user', TRUE), "
            "       (:u2, 888, 'other', 'other@example.com', 'user', TRUE)"
        ),
        {"u1": _SAME_TENANT_USER_ID, "u2": _OTHER_TENANT_USER_ID},
    )
    await db_session.execute(
        text(
            "INSERT OR IGNORE INTO roles (id, tenant_id, name, color, priority, is_system) "
            "VALUES (4000, 999, '営業-bots', '#888888', 10, 0)"
        )
    )
    await db_session.execute(
        text(
            "INSERT OR IGNORE INTO staff (id, tenant_id, user_id, role_id, staff_code, primary_email, surname_jp, given_name_jp) "
            "VALUES (40, 999, :u1, 4000, 'EMP-00040', 'same@example.com', '山田', '太郎')"
        ),
        {"u1": _SAME_TENANT_USER_ID},
    )
    await db_session.commit()
    return client


def _payload(owner_id: int, code: str | None = None) -> dict:
    return {
        "bot_code": code or f"BOT-{uuid.uuid4().hex[:12]}",
        "display_name": "テストBot",
        "purpose": "custom",
        "owner_staff_id": owner_id,
    }


@pytest.mark.asyncio
async def test_create_bot_accepts_user_of_same_tenant(seeded):
    with patch("app.routers.bots.record_audit_log", new=AsyncMock()):
        res = await seeded.post("/api/v1/bots", json=_payload(_SAME_TENANT_USER_ID))
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["owner_staff_id"] == _SAME_TENANT_USER_ID
    assert body["owner_staff_name"] == "山田 太郎"


@pytest.mark.asyncio
async def test_create_bot_rejects_user_of_other_tenant(seeded):
    with patch("app.routers.bots.record_audit_log", new=AsyncMock()):
        res = await seeded.post("/api/v1/bots", json=_payload(_OTHER_TENANT_USER_ID))
    assert res.status_code == 400
    assert "このテナントに存在しません" in res.json()["detail"]


@pytest.mark.asyncio
async def test_create_bot_rejects_staff_id_that_is_not_a_user_id(seeded):
    """名簿の staff.id（40）は users.id ではないので受け付けない。"""
    with patch("app.routers.bots.record_audit_log", new=AsyncMock()):
        res = await seeded.post("/api/v1/bots", json=_payload(40))
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_update_bot_rejects_user_of_other_tenant(seeded):
    with patch("app.routers.bots.record_audit_log", new=AsyncMock()):
        created = await seeded.post("/api/v1/bots", json=_payload(_SAME_TENANT_USER_ID))
        assert created.status_code == 201, created.text
        bot_id = created.json()["id"]
        res = await seeded.patch(
            f"/api/v1/bots/{bot_id}", json={"owner_staff_id": _OTHER_TENANT_USER_ID}
        )
    assert res.status_code == 400


def test_pending_bot_code_fits_column():
    from app.routers.bots import _pending_bot_code

    for _ in range(100):
        code = _pending_bot_code()
        assert len(code) <= 20
        assert code.startswith("BOT-P-")


@pytest.mark.asyncio
async def test_create_bot_blank_code_gets_sequential_code(seeded):
    payload = _payload(_SAME_TENANT_USER_ID)
    payload["bot_code"] = ""
    with patch("app.routers.bots.record_audit_log", new=AsyncMock()):
        res = await seeded.post("/api/v1/bots", json=payload)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["bot_code"] == f"BOT-{body['id']:05d}"


@pytest.mark.asyncio
async def test_create_bot_resets_tenant_context_after_commit(seeded):
    """ADR-072 Phase 2.5: commit の後に会社の文脈を付け直してから読み直す。"""
    from unittest.mock import ANY

    payload = _payload(_SAME_TENANT_USER_ID)
    payload["bot_code"] = ""
    with patch("app.routers.bots.record_audit_log", new=AsyncMock()), patch(
        "app.routers.bots.reset_tenant_context", new=AsyncMock()
    ) as reset_mock:
        res = await seeded.post("/api/v1/bots", json=payload)
    assert res.status_code == 201, res.text
    assert reset_mock.await_count >= 1
    reset_mock.assert_any_await(ANY, 999)
