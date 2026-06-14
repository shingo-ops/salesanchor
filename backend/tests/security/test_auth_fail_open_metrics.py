import logging

import pytest
from prometheus_client import REGISTRY

from app import cache


class _ExplodingRedis:
    async def get(self, key: str):  # pragma: no cover - used by test
        raise RuntimeError("redis boom")

    async def incr(self, key: str) -> int:  # pragma: no cover - used by test
        raise RuntimeError("redis boom")

    async def exists(self, key: str) -> int:  # pragma: no cover - used by test
        raise RuntimeError("redis boom")


def _counter_value(component: str, reason: str) -> float:
    sample_name = "auth_fail_open_total"
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            if (
                sample.name == sample_name
                and sample.labels.get("component") == component
                and sample.labels.get("reason") == reason
            ):
                return float(sample.value)
    return 0.0


@pytest.mark.asyncio
async def test_auth_lockout_records_fail_open_when_redis_unavailable(monkeypatch, caplog):
    monkeypatch.setattr("app.cache.get_redis", lambda: None)
    before = _counter_value("auth_lockout", "redis_unavailable")

    with caplog.at_level(logging.WARNING):
        locked = await cache.check_auth_rate_limit("203.0.113.10")

    after = _counter_value("auth_lockout", "redis_unavailable")
    assert locked is False
    assert after == before + 1
    assert "auth_fail_open component=auth_lockout reason=redis_unavailable" in caplog.text


@pytest.mark.asyncio
async def test_auth_lockout_records_fail_open_when_redis_raises(monkeypatch, caplog):
    monkeypatch.setattr("app.cache.get_redis", lambda: _ExplodingRedis())
    before = _counter_value("auth_lockout", "redis_exception")

    with caplog.at_level(logging.WARNING):
        locked = await cache.check_auth_rate_limit("203.0.113.10")

    after = _counter_value("auth_lockout", "redis_exception")
    assert locked is False
    assert after == before + 1
    assert "auth_fail_open component=auth_lockout reason=redis_exception" in caplog.text


@pytest.mark.asyncio
async def test_auth_failure_record_records_fail_open_when_redis_unavailable(monkeypatch, caplog):
    monkeypatch.setattr("app.cache.get_redis", lambda: None)
    before = _counter_value("auth_failure_record", "redis_unavailable")

    with caplog.at_level(logging.WARNING):
        await cache.record_auth_failure("203.0.113.10")

    after = _counter_value("auth_failure_record", "redis_unavailable")
    assert after == before + 1
    assert "auth_fail_open component=auth_failure_record reason=redis_unavailable" in caplog.text


@pytest.mark.asyncio
async def test_auth_failure_record_records_fail_open_when_redis_raises(monkeypatch, caplog):
    monkeypatch.setattr("app.cache.get_redis", lambda: _ExplodingRedis())
    before = _counter_value("auth_failure_record", "redis_exception")

    with caplog.at_level(logging.WARNING):
        await cache.record_auth_failure("203.0.113.10")

    after = _counter_value("auth_failure_record", "redis_exception")
    assert after == before + 1
    assert "auth_fail_open component=auth_failure_record reason=redis_exception" in caplog.text


@pytest.mark.asyncio
async def test_token_blacklist_records_fail_open_when_redis_unavailable(monkeypatch, caplog):
    monkeypatch.setattr("app.cache.get_redis", lambda: None)
    before = _counter_value("token_blacklist", "redis_unavailable")

    with caplog.at_level(logging.WARNING):
        blacklisted = await cache.is_token_blacklisted("token")

    after = _counter_value("token_blacklist", "redis_unavailable")
    assert blacklisted is False
    assert after == before + 1
    assert "auth_fail_open component=token_blacklist reason=redis_unavailable" in caplog.text


@pytest.mark.asyncio
async def test_token_blacklist_records_fail_open_when_redis_raises(monkeypatch, caplog):
    monkeypatch.setattr("app.cache.get_redis", lambda: _ExplodingRedis())
    before = _counter_value("token_blacklist", "redis_exception")

    with caplog.at_level(logging.WARNING):
        blacklisted = await cache.is_token_blacklisted("token")

    after = _counter_value("token_blacklist", "redis_exception")
    assert blacklisted is False
    assert after == before + 1
    assert "auth_fail_open component=token_blacklist reason=redis_exception" in caplog.text
