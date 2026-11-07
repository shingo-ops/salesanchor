"""全社1つのチャネル名簿（共用行＋会社独自の行＋会社ごとの「隠す」）の試験（SQLite）。

card-pr-b.md §5。K3（会社独自は自社だけ）・K6（新しい会社でも共用6つ）・D1（会社ごとに隠せる）。
SQLite には RLS が無いため、会社の絞りは読み口の SQL（tenant_id IS NULL OR tenant_id = :tenant_id）で見る。
PostgreSQL の守りは test_channel_masters_shared_pg.py。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.auth.dependencies import get_current_tenant

SHARED_PLATFORMS = {"messenger", "instagram", "discord", "phone", "in_person", "whatsapp"}
_LIST = "/api/v1/channel-masters"
_ADMIN = "/api/v1/admin/channel-masters"


def _as_tenant(tenant_id: int) -> None:
    from app.main import app

    async def override() -> int:
        return tenant_id

    app.dependency_overrides[get_current_tenant] = override


@pytest.fixture
def audit():
    with patch("app.routers.conv_logs.record_audit_log", new=AsyncMock()) as mocked:
        yield mocked


async def _list(client, query: str = "") -> list[dict]:
    res = await client.get(f"{_LIST}{query}")
    assert res.status_code == 200, res.text
    return res.json()


def _by_platform(rows: list[dict]) -> dict[str, dict]:
    return {r["platform"]: r for r in rows}


# ── K3: 会社独自の行は自社だけ ───────────────────────────────────
async def test_tenant_row_is_visible_to_own_tenant_only(client):
    _as_tenant(1)
    res = await client.post(_ADMIN, json={"platform": "line", "display_name": "LINE"})
    assert res.status_code == 201, res.text
    assert "line" in _by_platform(await _list(client))
    row = _by_platform(await _list(client))["line"]
    assert row["is_shared"] is False and row["connection_type"] == "manual"

    _as_tenant(2)
    assert "line" not in _by_platform(await _list(client))


async def test_other_tenant_cannot_delete_or_hide_a_tenant_row(client, audit):
    _as_tenant(1)
    new_id = (await client.post(_ADMIN, json={"platform": "line", "display_name": "LINE"})).json()["id"]

    _as_tenant(2)
    assert (await client.delete(f"{_ADMIN}/{new_id}")).status_code == 404
    res = await client.put(f"{_ADMIN}/{new_id}/visibility", json={"is_hidden": True})
    assert res.status_code == 404

    _as_tenant(1)
    assert "line" in _by_platform(await _list(client))


async def test_adding_same_platform_as_shared_row_returns_409(client):
    _as_tenant(1)
    res = await client.post(_ADMIN, json={"platform": "phone", "display_name": "別の電話"})
    assert res.status_code == 409
    assert "同じ名前" in res.json()["detail"]


async def test_adding_same_platform_twice_returns_409(client):
    _as_tenant(1)
    assert (await client.post(_ADMIN, json={"platform": "line", "display_name": "LINE"})).status_code == 201
    assert (await client.post(_ADMIN, json={"platform": "line", "display_name": "LINE 2"})).status_code == 409


async def test_tenant_can_deactivate_own_row_but_not_shared_row(client):
    _as_tenant(1)
    new_id = (await client.post(_ADMIN, json={"platform": "line", "display_name": "LINE"})).json()["id"]
    shared_phone = _by_platform(await _list(client))["phone"]
    assert (await client.delete(f"{_ADMIN}/{shared_phone['id']}")).status_code == 403
    assert (await client.delete(f"{_ADMIN}/{new_id}")).status_code == 204
    assert "line" not in _by_platform(await _list(client))


# ── K6: 新しい会社でも共用6つが読める ───────────────────────────
async def test_new_tenant_sees_the_six_shared_channels(client):
    _as_tenant(5)
    rows = await _list(client)
    assert {r["platform"] for r in rows} == SHARED_PLATFORMS
    assert all(r["is_shared"] is True and r["is_hidden"] is False for r in rows)


# ── D1: 会社ごとに隠せる ────────────────────────────────────────
async def test_hidden_channel_leaves_picker_for_that_tenant_only(client, audit):
    _as_tenant(1)
    phone_id = _by_platform(await _list(client))["phone"]["id"]
    res = await client.put(f"{_ADMIN}/{phone_id}/visibility", json={"is_hidden": True})
    assert res.status_code == 200, res.text
    assert res.json() == {"id": phone_id, "is_hidden": True}

    assert "phone" not in _by_platform(await _list(client, "?for=picker"))
    # 設定画面の一覧には残り、is_hidden が付く
    assert _by_platform(await _list(client))["phone"]["is_hidden"] is True

    _as_tenant(2)
    assert "phone" in _by_platform(await _list(client, "?for=picker"))
    assert _by_platform(await _list(client))["phone"]["is_hidden"] is False

    # 戻すと出る
    _as_tenant(1)
    res = await client.put(f"{_ADMIN}/{phone_id}/visibility", json={"is_hidden": False})
    assert res.status_code == 200
    assert "phone" in _by_platform(await _list(client, "?for=picker"))


async def test_keep_param_keeps_hidden_channel_in_picker(client, audit):
    _as_tenant(1)
    phone_id = _by_platform(await _list(client))["phone"]["id"]
    await client.put(f"{_ADMIN}/{phone_id}/visibility", json={"is_hidden": True})
    kept = _by_platform(await _list(client, "?for=picker&keep=phone"))
    assert "phone" in kept
    assert "in_person" in kept


async def test_visibility_of_auto_channel_returns_400(client, audit):
    _as_tenant(1)
    messenger_id = _by_platform(await _list(client))["messenger"]["id"]
    res = await client.put(f"{_ADMIN}/{messenger_id}/visibility", json={"is_hidden": True})
    assert res.status_code == 400
    audit.assert_not_awaited()


async def test_visibility_without_permission_returns_403(client, audit):
    _as_tenant(1)
    phone_id = _by_platform(await _list(client))["phone"]["id"]
    with patch("app.auth.dependencies.load_user_permissions", new=AsyncMock(return_value=set())):
        res = await client.put(f"{_ADMIN}/{phone_id}/visibility", json={"is_hidden": True})
        assert res.status_code == 403
        res = await client.post(_ADMIN, json={"platform": "line", "display_name": "LINE"})
        assert res.status_code == 403
        res = await client.delete(f"{_ADMIN}/{phone_id}")
        assert res.status_code == 403
    audit.assert_not_awaited()


async def test_visibility_change_writes_one_audit_record(client, audit):
    _as_tenant(1)
    phone_id = _by_platform(await _list(client))["phone"]["id"]
    res = await client.put(f"{_ADMIN}/{phone_id}/visibility", json={"is_hidden": True})
    assert res.status_code == 200, res.text
    audit.assert_awaited_once()
    args, kwargs = audit.await_args
    assert args[3] == "update"
    assert args[4] == "channel_master_tenant_settings"
    assert kwargs["record_id"] == phone_id
    assert kwargs["old_data"] == {"is_hidden": False}
    assert kwargs["new_data"] == {"is_hidden": True}
