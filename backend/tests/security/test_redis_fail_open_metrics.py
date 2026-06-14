import logging

import pytest
from prometheus_client import REGISTRY

from app.middleware import rate_limit, session_guard


class _ExplodingRedis:
    async def incr(self, key: str) -> int:  # pragma: no cover - used by test
        raise RuntimeError("redis boom")

    async def get(self, key: str):  # pragma: no cover - used by test
        raise RuntimeError("redis boom")


def _counter_value(component: str, reason: str) -> float:
    sample_name = "security_fail_open_total"
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
async def test_rate_limit_records_fail_open_when_redis_unavailable(monkeypatch, caplog):
    monkeypatch.setattr("app.cache.get_redis", lambda: None)
    before = _counter_value("rate_limit", "redis_unavailable")

    with caplog.at_level(logging.WARNING):
        exceeded = await rate_limit._check_rate_limit("ip:203.0.113.10", 60, 60)

    after = _counter_value("rate_limit", "redis_unavailable")
    assert exceeded is False
    assert after == before + 1
    assert "security_fail_open component=rate_limit reason=redis_unavailable" in caplog.text


@pytest.mark.asyncio
async def test_rate_limit_records_fail_open_when_redis_raises(monkeypatch, caplog):
    monkeypatch.setattr("app.cache.get_redis", lambda: _ExplodingRedis())
    before = _counter_value("rate_limit", "redis_exception")

    with caplog.at_level(logging.WARNING):
        exceeded = await rate_limit._check_rate_limit("ip:203.0.113.10", 60, 60)

    after = _counter_value("rate_limit", "redis_exception")
    assert exceeded is False
    assert after == before + 1
    assert "security_fail_open component=rate_limit reason=redis_exception" in caplog.text


@pytest.mark.asyncio
async def test_session_guard_records_fail_open_when_redis_unavailable(monkeypatch, caplog):
    monkeypatch.setattr("app.cache.get_redis", lambda: None)
    before = _counter_value("session_guard", "redis_unavailable")

    with caplog.at_level(logging.WARNING):
        compromised = await session_guard._check_session_ip("tokenhash", "203.0.113.10")

    after = _counter_value("session_guard", "redis_unavailable")
    assert compromised is False
    assert after == before + 1
    assert "security_fail_open component=session_guard reason=redis_unavailable" in caplog.text


@pytest.mark.asyncio
async def test_session_guard_records_fail_open_when_redis_raises(monkeypatch, caplog):
    monkeypatch.setattr("app.cache.get_redis", lambda: _ExplodingRedis())
    before = _counter_value("session_guard", "redis_exception")

    with caplog.at_level(logging.WARNING):
        compromised = await session_guard._check_session_ip("tokenhash", "203.0.113.10")

    after = _counter_value("session_guard", "redis_exception")
    assert compromised is False
    assert after == before + 1
    assert "security_fail_open component=session_guard reason=redis_exception" in caplog.text
