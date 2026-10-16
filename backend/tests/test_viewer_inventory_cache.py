"""閲覧ページ用の在庫の作り置き（ADR-1019 段2・設計 D3）の試験。Redis と DB は mock（PG の1関数だけ CI 専用）。"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.services import tcg_distribution_svc as svc
from app.tasks import viewer_inventory_cache as vic
from tests.test_inventory_distribution_rows_pg import _seed_mixed
from tests.test_inventory_distribution_rows_pg import ids as ids  # noqa: F401  fixture
from tests.test_line_analysis_v102_pg import v102 as v102  # noqa: F401  fixture
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture


class FakeRedis:
    """refresh_once が使う set(nx, ex)・incr だけを持つ最小の Redis。"""

    def __init__(self) -> None:
        self.store: dict = {}
        self.ttls: dict = {}
        self.set_calls: list = []
        self.fail_set_for: set = set()

    async def set(self, key, value, nx=False, ex=None):
        self.set_calls.append(key)
        if key in self.fail_set_for:
            raise RuntimeError("redis set failed")
        if nx and key in self.store:
            return None
        self.store[key] = value
        self.ttls[key] = ex
        return True

    async def incr(self, key):
        self.store[key] = int(self.store.get(key, 0)) + 1
        return self.store[key]


def _row(i: int = 0, status: str = "In Stock") -> list:
    values = [f"{c}{i}" for c in svc._GAS_COLUMNS]
    values[svc._GAS_COLUMNS.index("status")] = status
    return values


def _built(kind: str, rows: list | None = None, message: str = "") -> svc.DistributionRowsResult:
    return svc.DistributionRowsResult(kind=kind, rows=rows or [], message=message)


@pytest.fixture
def notify():
    with patch("app.routers.notifications.send_discord_notification", new=AsyncMock()) as mock:
        yield mock


def _patch_build(*, result=None, exc=None):
    if exc is not None:
        return patch.object(vic, "build_distribution_rows", new=AsyncMock(side_effect=exc))
    return patch.object(vic, "build_distribution_rows", new=AsyncMock(return_value=result))


async def _refresh(redis, result=None, exc=None) -> str:
    redis.store.pop(vic.LOCK_KEY, None)  # 別の1分として扱う
    with _patch_build(result=result, exc=exc):
        return await vic.refresh_once(AsyncMock(), redis)


async def test_ok_writes_cache_with_ttl_and_resets_fail_count():
    redis = FakeRedis()
    redis.store[vic.FAIL_KEY] = 2
    with _patch_build(result=_built("ok", [_row(1), _row(2, "Pre-order")])):
        assert await vic.refresh_once(AsyncMock(), redis) == "ok"
    assert redis.ttls[vic.CACHE_KEY] == 86400
    payload = json.loads(redis.store[vic.CACHE_KEY])
    assert payload["fresh_window_hours"] == svc.FRESH_WINDOW_HOURS
    assert payload["updated_at"]
    assert len(payload["rows"]) == 2
    for item in payload["rows"]:
        assert set(item) == set(svc._GAS_COLUMNS) | {"offer_type"}
    assert [r["offer_type"] for r in payload["rows"]] == ["in_stock", "pre_order"]
    assert redis.store[vic.FAIL_KEY] == 0


async def test_hold_touches_neither_cache_nor_fail_count():
    redis = FakeRedis()
    with _patch_build(result=_built("hold", message="m")):
        assert await vic.refresh_once(AsyncMock(), redis) == "hold"
    assert redis.set_calls == [vic.LOCK_KEY, vic.LAST_HOLD_TS_KEY]  # 保留の時刻だけは書く（段2b）
    assert vic.CACHE_KEY not in redis.store and vic.FAIL_KEY not in redis.store


async def test_ok_writes_updated_ts_with_ttl():
    redis = FakeRedis()
    with _patch_build(result=_built("ok", [_row(1)])):
        assert await vic.refresh_once(AsyncMock(), redis) == "ok"
    assert abs(int(redis.store[vic.UPDATED_TS_KEY]) - time.time()) <= 5
    assert redis.ttls[vic.UPDATED_TS_KEY] == 86400
    assert vic.LAST_HOLD_TS_KEY not in redis.store


async def test_hold_writes_only_last_hold_ts_with_ttl():
    redis = FakeRedis()
    with _patch_build(result=_built("hold", message="m")):
        assert await vic.refresh_once(AsyncMock(), redis) == "hold"
    assert abs(int(redis.store[vic.LAST_HOLD_TS_KEY]) - time.time()) <= 5
    assert redis.ttls[vic.LAST_HOLD_TS_KEY] == 86400
    assert set(redis.store) == {vic.LOCK_KEY, vic.LAST_HOLD_TS_KEY}


async def test_unset_error_locked_write_neither_ts_key(notify):
    redis = FakeRedis()
    assert await _refresh(redis, result=_built("unset", message="m")) == "failed"
    assert await _refresh(redis, result=_built("error", message="m")) == "failed"
    assert await _refresh(redis, exc=RuntimeError("boom")) == "failed"
    redis.store[vic.LOCK_KEY] = "1"
    with _patch_build(result=_built("ok", [_row(1)])):
        assert await vic.refresh_once(AsyncMock(), redis) == "locked"
    assert vic.UPDATED_TS_KEY not in redis.store and vic.LAST_HOLD_TS_KEY not in redis.store


async def test_hold_ts_set_exception_still_returns_hold_and_not_counted(notify):
    redis = FakeRedis()
    redis.fail_set_for = {vic.LAST_HOLD_TS_KEY}
    with _patch_build(result=_built("hold", message="m")):
        assert await vic.refresh_once(AsyncMock(), redis) == "hold"
    assert vic.FAIL_KEY not in redis.store
    notify.assert_not_awaited()


async def test_unset_keeps_cache_and_counts_failure(notify):
    redis = FakeRedis()
    redis.store[vic.CACHE_KEY] = "previous"
    with _patch_build(result=_built("unset", message="max_age_hours 未設定のため配信しない")):
        assert await vic.refresh_once(AsyncMock(), redis) == "failed"
    assert redis.store[vic.CACHE_KEY] == "previous"
    assert vic.CACHE_KEY not in redis.set_calls
    assert redis.store[vic.FAIL_KEY] == 1


async def test_build_exception_keeps_cache_and_counts_failure(notify):
    redis = FakeRedis()
    redis.store[vic.CACHE_KEY] = "previous"
    with _patch_build(exc=RuntimeError("db down")):
        assert await vic.refresh_once(AsyncMock(), redis) == "failed"
    assert redis.store[vic.CACHE_KEY] == "previous"
    assert redis.store[vic.FAIL_KEY] == 1


async def test_cache_set_exception_keeps_cache_and_counts_failure(notify):
    redis = FakeRedis()
    redis.store[vic.CACHE_KEY] = "previous"
    redis.fail_set_for = {vic.CACHE_KEY}
    with _patch_build(result=_built("ok", [_row(1)])):
        assert await vic.refresh_once(AsyncMock(), redis) == "failed"
    assert redis.store[vic.CACHE_KEY] == "previous"
    assert redis.store[vic.FAIL_KEY] == 1


async def test_notify_once_at_third_failure_not_at_fourth(notify):
    redis = FakeRedis()
    for _ in range(2):
        await _refresh(redis, result=_built("error", message="出力データ取得失敗: boom"))
    notify.assert_not_awaited()
    await _refresh(redis, result=_built("error", message="出力データ取得失敗: boom"))
    assert notify.await_count == 1
    kwargs = notify.await_args.kwargs
    assert kwargs["tenant_id"] == 4 and kwargs["event_type"] == "tcg_distribution_error"
    assert kwargs["title"] == "閲覧ページの在庫の作り置きが続けて失敗"
    assert kwargs["message"] == "[viewer-cache] 3回続けて失敗しました: 出力データ取得失敗: boom"
    await _refresh(redis, result=_built("error", message="x"))
    assert notify.await_count == 1


async def test_notify_again_after_success_resets_count(notify):
    redis = FakeRedis()
    for _ in range(3):
        await _refresh(redis, result=_built("unset", message="m"))
    assert notify.await_count == 1
    assert await _refresh(redis, result=_built("ok", [_row(1)])) == "ok"
    for _ in range(3):
        await _refresh(redis, exc=RuntimeError("x"))
    assert notify.await_count == 2


async def test_notify_failure_is_swallowed(notify):
    notify.side_effect = RuntimeError("discord down")
    redis = FakeRedis()
    results = [await _refresh(redis, result=_built("unset", message="m")) for _ in range(3)]
    assert results == ["failed"] * 3


async def test_locked_writes_and_counts_nothing(notify):
    redis = FakeRedis()
    redis.store[vic.LOCK_KEY] = "1"
    build = AsyncMock()
    with patch.object(vic, "build_distribution_rows", new=build):
        assert await vic.refresh_once(AsyncMock(), redis) == "locked"
    build.assert_not_awaited()
    assert redis.set_calls == [vic.LOCK_KEY]
    assert vic.FAIL_KEY not in redis.store and vic.CACHE_KEY not in redis.store


async def test_lock_is_set_with_55_seconds(notify):
    calls = []

    class Spy(FakeRedis):
        async def set(self, key, value, nx=False, ex=None):
            calls.append((key, nx, ex))
            return await super().set(key, value, nx=nx, ex=ex)

    with _patch_build(result=_built("hold")):
        await vic.refresh_once(AsyncMock(), Spy())
    assert calls[0] == (vic.LOCK_KEY, True, 55)


async def test_failure_logs_use_viewer_cache_prefix_not_dist(notify, caplog):
    redis = FakeRedis()
    with caplog.at_level(logging.DEBUG):
        await _refresh(redis, result=_built("unset", message="m"))
    messages = [r.getMessage() for r in caplog.records]
    assert any(m.startswith("[viewer-cache]") for m in messages)
    assert not any("[dist]" in m for m in messages)


def test_to_cache_rows_matches_zip_of_gas_columns():
    rows = [_row(1), _row(2, "Pre-order"), _row(3, "Other")]
    out = vic.to_cache_rows(rows)
    for item, row in zip(out, rows):
        assert {k: v for k, v in item.items() if k != "offer_type"} == dict(zip(svc._GAS_COLUMNS, row))
        assert len(item) == 15
    assert [i["offer_type"] for i in out] == ["in_stock", "pre_order", None]
    assert len({k for item in out for k in item if k != "offer_type"}) == 14


def test_beat_has_refresh_viewer_inventory_and_task_is_registered():
    import importlib

    from app.celery_app import celery_app

    entry = celery_app.conf.beat_schedule["refresh-viewer-inventory"]
    assert entry["task"] == "app.tasks.viewer_inventory_cache.refresh_viewer_inventory"
    assert entry["schedule"] == 60.0
    for module_name in celery_app.conf.include:
        importlib.import_module(module_name)
    assert entry["task"] in celery_app.tasks


def test_task_never_raises_even_when_run_fails(caplog):
    with patch.object(vic, "_run", side_effect=RuntimeError("redis down")), caplog.at_level(logging.ERROR):
        vic.refresh_viewer_inventory()
    assert any("[viewer-cache]" in r.getMessage() for r in caplog.records)


@pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required")
def test_pg_build_rows_to_cache_rows_matches_fetch_output_rows(pg, ids):  # noqa: F811
    _seed_mixed(pg, ids)

    async def _go():
        engine = create_async_engine(pg[2])
        try:
            async with AsyncSession(engine) as db:
                direct = await svc.fetch_output_rows(db)
                with patch.object(
                    svc, "load_distribution_settings", new=AsyncMock(return_value={"max_age_hours": "0"})
                ):
                    built = await svc.build_distribution_rows(db)
                return direct, built
        finally:
            await engine.dispose()

    direct, built = asyncio.run(_go())
    assert built.kind == "ok" and direct
    cached = vic.to_cache_rows(built.rows)
    assert [{k: v for k, v in c.items() if k != "offer_type"} for c in cached] == [
        dict(zip(svc._GAS_COLUMNS, row)) for row in direct
    ]
