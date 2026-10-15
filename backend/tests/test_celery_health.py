from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app import celery_health
from app.metrics import register_metrics


def test_record_heartbeat_sets_numeric_string():
    client = MagicMock()
    with patch.object(celery_health, "_get_sync", return_value=client):
        celery_health.record_heartbeat()
    client.set.assert_called_once()
    key, value = client.set.call_args.args
    assert key == celery_health.HEARTBEAT_KEY
    assert float(value) > 0


def test_record_task_failure_increments_by_task_name():
    client = MagicMock()
    with patch.object(celery_health, "_get_sync", return_value=client):
        celery_health.record_task_failure("x")
    client.hincrby.assert_called_once_with(celery_health.FAILURES_KEY, "x", 1)


def test_record_functions_swallow_redis_errors():
    client = MagicMock()
    client.set.side_effect = RuntimeError("down")
    client.hincrby.side_effect = RuntimeError("down")
    with patch.object(celery_health, "_get_sync", return_value=client):
        celery_health.record_heartbeat()
        celery_health.record_task_failure("x")


@pytest.mark.asyncio
async def test_read_celery_health_returns_tuple():
    raw = AsyncMock(return_value=["123.5", {"x": "2"}, 5])
    with patch.object(celery_health, "_read_raw", raw):
        assert await celery_health.read_celery_health() == (123.5, {"x": 2}, 5)


@pytest.mark.asyncio
async def test_read_celery_health_missing_heartbeat_is_zero():
    raw = AsyncMock(return_value=[None, {}, 0])
    with patch.object(celery_health, "_read_raw", raw):
        assert await celery_health.read_celery_health() == (0.0, {}, 0)


@pytest.mark.asyncio
async def test_read_celery_health_none_on_redis_error():
    raw = AsyncMock(side_effect=RuntimeError("down"))
    with patch.object(celery_health, "_read_raw", raw):
        assert await celery_health.read_celery_health() is None


@pytest.mark.asyncio
async def test_read_celery_health_none_on_corrupt_value():
    raw = AsyncMock(return_value=["not-a-number", {}, 0])
    with patch.object(celery_health, "_read_raw", raw):
        assert await celery_health.read_celery_health() is None


@pytest.mark.asyncio
async def test_read_celery_health_none_on_timeout():
    async def slow():
        await asyncio.sleep(5)

    with (
        patch.object(celery_health, "_read_raw", slow),
        patch.object(celery_health, "READ_TIMEOUT_SEC", 0.05),
    ):
        assert await celery_health.read_celery_health() is None


async def _get_metrics(health):
    app = FastAPI()
    register_metrics(app)
    transport = ASGITransport(app=app)
    with patch("app.metrics.read_celery_health", AsyncMock(return_value=health)):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/metrics")


@pytest.mark.asyncio
async def test_metrics_exports_celery_gauges():
    response = await _get_metrics((1700000000.0, {"x": 2}, 5))
    assert response.status_code == 200
    assert "celery_heartbeat_last_success_timestamp_seconds" in response.text
    assert 'celery_task_failures{task="x"} 2.0' in response.text
    assert "celery_queue_length 5.0" in response.text


@pytest.mark.asyncio
async def test_metrics_ok_when_health_unreadable():
    response = await _get_metrics(None)
    assert response.status_code == 200


def test_heartbeat_in_beat_schedule():
    from app.celery_app import celery_app

    entry = celery_app.conf.beat_schedule["ai-ops-celery-heartbeat"]
    assert entry["task"] == "app.tasks.ai_ops_heartbeat.celery_heartbeat"
    assert entry["schedule"] == 60.0


def test_task_failure_signal_records_by_task_name():
    from celery.signals import task_failure

    import app.celery_app  # noqa: F401

    class FakeTask:
        name = "some.task"

    fake = FakeTask()
    with patch("app.celery_app.record_task_failure") as rec:
        task_failure.send(sender=fake)
    rec.assert_called_once_with("some.task")
