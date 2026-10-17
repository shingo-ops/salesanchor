import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from app import cache
from app.cache import _mask_url

PW = "secretpw-Zq9"


def test_mask_password_only():
    out = _mask_url("redis://:secretpw@redis:6379/0")
    assert out == "redis://:***@redis:6379/0"
    assert "secretpw" not in out


def test_mask_user_and_password():
    assert _mask_url("redis://user:pw@host:6380/2") == "redis://user:***@host:6380/2"


def test_no_password_unchanged():
    assert _mask_url("redis://redis:6379/0") == "redis://redis:6379/0"


def test_invalid_port_redacted():
    assert _mask_url("redis://:pw@host:notaport/0") == "<redacted>"


@pytest.mark.asyncio
async def test_init_redis_log_has_no_password(monkeypatch, caplog):
    url = f"redis://:{PW}@redis:6379/0"
    monkeypatch.setattr(cache, "REDIS_URL", url)
    client = MagicMock()
    client.ping = AsyncMock()
    monkeypatch.setattr(cache.redis, "from_url", lambda *a, **k: client)
    with caplog.at_level(logging.INFO, logger="app.cache"):
        await cache.init_redis()
    assert "Redis接続成功" in caplog.text
    assert PW not in caplog.text
    monkeypatch.setattr(cache, "_redis", None)
