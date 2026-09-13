"""
issue_state の extra パラメータ追加に対する単体テスト。

実 Redis は使わず AsyncMock で差し替える。
Fernet 鍵は _fernet_key fixture で生成する（test_oauth_state.py と同パターン）。

実行:
    pytest backend/tests/test_oauth_state_extra.py -v
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet

from app.services import encryption
from app.services.oauth_state import issue_state


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fernet_key(monkeypatch):
    """encryption に有効な Fernet 鍵をセット。"""
    encryption.reset_cache()
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("METADATA_FERNET_KEY", key)
    yield
    encryption.reset_cache()


# ---------------------------------------------------------------------------
# extra=None（省略）— 既存呼び出しと同一挙動
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extra_none_payload_has_no_extra_keys():
    """extra を指定しない場合、payload は 4 つの予約キーのみ。"""
    redis_mock = AsyncMock()
    captured: dict = {}

    async def _setex(key, ttl, value):
        captured["value"] = value

    redis_mock.setex.side_effect = _setex

    with patch("app.services.oauth_state.get_redis", return_value=redis_mock):
        await issue_state(tenant_id=1, staff_id=2)

    payload = json.loads(encryption.decrypt(captured["value"]))
    assert set(payload.keys()) == {"tenant_id", "staff_id", "created_at", "nonce"}


# ---------------------------------------------------------------------------
# extra={"lead_id": 123} — 正常系
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extra_lead_id_stored_in_payload():
    """extra={"lead_id": 123} を渡すと payload に lead_id が含まれる。"""
    redis_mock = AsyncMock()
    captured: dict = {}

    async def _setex(key, ttl, value):
        captured["value"] = value

    redis_mock.setex.side_effect = _setex

    with patch("app.services.oauth_state.get_redis", return_value=redis_mock):
        await issue_state(tenant_id=3, staff_id=7, extra={"lead_id": 123})

    payload = json.loads(encryption.decrypt(captured["value"]))
    assert payload["lead_id"] == 123
    # 予約キーは上書きされていない
    assert payload["tenant_id"] == 3
    assert payload["staff_id"] == 7


# ---------------------------------------------------------------------------
# extra と予約キーの衝突 — ValueError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extra_conflict_tenant_id_raises():
    """extra に tenant_id を含むと ValueError。"""
    redis_mock = AsyncMock()
    with patch("app.services.oauth_state.get_redis", return_value=redis_mock):
        with pytest.raises(ValueError, match="予約済みキー"):
            await issue_state(tenant_id=1, staff_id=1, extra={"tenant_id": 999})


@pytest.mark.asyncio
async def test_extra_conflict_staff_id_raises():
    """extra に staff_id を含むと ValueError。"""
    redis_mock = AsyncMock()
    with patch("app.services.oauth_state.get_redis", return_value=redis_mock):
        with pytest.raises(ValueError, match="予約済みキー"):
            await issue_state(tenant_id=1, staff_id=1, extra={"staff_id": 999})


@pytest.mark.asyncio
async def test_extra_conflict_nonce_raises():
    """extra に nonce を含むと ValueError。"""
    redis_mock = AsyncMock()
    with patch("app.services.oauth_state.get_redis", return_value=redis_mock):
        with pytest.raises(ValueError, match="予約済みキー"):
            await issue_state(tenant_id=1, staff_id=1, extra={"nonce": "x"})


# ---------------------------------------------------------------------------
# extra={} — 空 dict は no-op
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extra_empty_dict_no_op():
    """extra={} は falsy なので conflict check も update も走らない。"""
    redis_mock = AsyncMock()
    captured: dict = {}

    async def _setex(key, ttl, value):
        captured["value"] = value

    redis_mock.setex.side_effect = _setex

    with patch("app.services.oauth_state.get_redis", return_value=redis_mock):
        await issue_state(tenant_id=5, staff_id=10, extra={})

    payload = json.loads(encryption.decrypt(captured["value"]))
    assert set(payload.keys()) == {"tenant_id", "staff_id", "created_at", "nonce"}
