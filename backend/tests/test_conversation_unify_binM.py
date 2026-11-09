"""会話の一本化 便M: 受信箱の「手で会話を書き足す欄」を外した確かめ。

検証項目:
  1〜4. リード配下の会話記録の道（作成・一覧・変更・削除）が無い（404 か 405）
  5. アプリの道の一覧に、リード配下のその道が0件（会社の会話タブの道は残す）
  6. 連絡手段の名簿の一覧 API（GET /api/v1/channel-masters）は残っている
"""
from __future__ import annotations

import pytest

_GONE_PATH = "/conv" + "-logs"


@pytest.mark.asyncio
async def test_post_manual_path_is_gone(client):
    res = await client.post(
        f"/api/v1/leads/1{_GONE_PATH}",
        json={"channel_type": "phone", "content_text": "x", "occurred_at": "2026-06-01T10:00:00+00:00"},
    )
    assert res.status_code in (404, 405)


@pytest.mark.asyncio
async def test_get_manual_path_is_gone(client):
    res = await client.get(f"/api/v1/leads/1{_GONE_PATH}")
    assert res.status_code in (404, 405)


@pytest.mark.asyncio
async def test_patch_manual_path_is_gone(client):
    res = await client.patch(f"/api/v1/leads/1{_GONE_PATH}/1", json={"content_text": "x"})
    assert res.status_code in (404, 405)


@pytest.mark.asyncio
async def test_delete_manual_path_is_gone(client):
    res = await client.delete(f"/api/v1/leads/1{_GONE_PATH}/1")
    assert res.status_code in (404, 405)


def test_no_route_contains_the_gone_path():
    from app.main import app

    paths = [getattr(r, "path", "") for r in app.routes]
    assert [p for p in paths if p.startswith("/api/v1/leads/") and _GONE_PATH in p] == []


def test_channel_masters_list_route_remains():
    from app.main import app

    paths = [getattr(r, "path", "") for r in app.routes]
    assert paths.count("/api/v1/channel-masters") == 1
