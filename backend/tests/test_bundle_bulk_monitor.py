"""ADR-1027 便3: バルク系まとめ売りの週次件数通知の単体テスト。"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.schedules import crontab

from app.tasks import bundle_bulk_monitor as m
from app.tasks.bundle_bulk_monitor import (
    BASELINE_ALL_BUNDLE_UNVERIFIED,
    BASELINE_PRICE_UNKNOWN,
    build_message,
)

_OK = {
    "bulk_rows": 10,
    "bulk_price_basis_unknown": BASELINE_PRICE_UNKNOWN,
    "bulk_bundle_unverified": 0,
    "all_bundle_unverified": BASELINE_ALL_BUNDLE_UNVERIFIED,
}


def test_build_message_within_baseline_is_ok():
    msg = build_message(_OK)
    assert msg.split("\n")[0].startswith("✅")
    assert "バルク系（全エンジン）: 10行" in msg


def test_build_message_price_over_baseline_is_warning():
    msg = build_message({**_OK, "bulk_price_basis_unknown": BASELINE_PRICE_UNKNOWN + 1})
    assert msg.split("\n")[0].startswith("⚠️")


def test_build_message_bulk_bundle_is_warning():
    msg = build_message({**_OK, "bulk_bundle_unverified": 1})
    assert msg.split("\n")[0].startswith("⚠️")


def test_build_message_zero_counts():
    msg = build_message({})
    lines = msg.split("\n")
    assert lines[0].startswith("✅")
    assert "0行" in lines[1]
    assert len(lines) == 5


def test_params_use_constants():
    from app.services.gemini_raw_copy_v102_product_first import PRODUCT_KUBUN_BULK
    from app.services.line_analysis_v102_svc import (
        REASON_BULK_PRICE_BASIS_UNKNOWN,
        REASON_BUNDLE_UNVERIFIED,
    )

    assert m._params() == {
        "bulk": PRODUCT_KUBUN_BULK,
        "r_price": REASON_BULK_PRICE_BASIS_UNKNOWN,
        "r_bundle": REASON_BUNDLE_UNVERIFIED,
    }
    sql = str(m._COUNT_SQL)
    for k in (":bulk", ":r_price", ":r_bundle"):
        assert k in sql
    assert PRODUCT_KUBUN_BULK not in sql and "'bundle_unverified'" not in sql and "'bulk_price_basis_unknown'" not in sql


@pytest.mark.asyncio
async def test_post_discord_skips_without_webhook(monkeypatch):
    monkeypatch.delenv("ADMIN_NOTIFICATION_DISCORD_WEBHOOK", raising=False)
    with patch("app.tasks.bundle_bulk_monitor.httpx.AsyncClient") as cli:
        await m._post_discord("x")
    cli.assert_not_called()


@pytest.mark.asyncio
async def test_run_report_posts_once_with_bind_params():
    db = AsyncMock()
    res = MagicMock()
    res.mappings.return_value.one.return_value = _OK
    db.execute = AsyncMock(return_value=res)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)
    with patch("app.database.AsyncSessionLocal", return_value=cm), \
         patch("app.tasks.bundle_bulk_monitor._post_discord", new_callable=AsyncMock) as post:
        out = await m._run_report()
    post.assert_awaited_once()
    assert db.execute.await_args.args[1] == m._params()
    assert out["counts"] == _OK


def test_beat_schedule_registered_monday_905():
    import importlib

    from app.celery_app import celery_app

    entry = celery_app.conf.beat_schedule["report-bundle-bulk-weekly"]
    assert entry["task"] == "app.tasks.bundle_bulk_monitor.report_bundle_bulk"
    assert "app.tasks.bundle_bulk_monitor" in celery_app.conf.include
    importlib.import_module("app.tasks.bundle_bulk_monitor")
    assert entry["task"] in celery_app.tasks
    s = entry["schedule"]
    assert isinstance(s, crontab)
    assert s._orig_hour == 9 and s._orig_minute == 5 and str(s._orig_day_of_week) == "1"
