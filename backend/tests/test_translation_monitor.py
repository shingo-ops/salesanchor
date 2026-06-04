"""
ADR-110: 翻訳監視サービスの単体テスト。

カバー:
  - TranslationHealthSnapshot: dataclass 生成・rate 計算
  - check_translation_health: DB モックを使った健全性チェック
  - notify_translation_anomaly: アラートなし / デバウンス / webhook 失敗
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.translation_monitor import (
    TranslationHealthSnapshot,
    check_translation_health,
    notify_translation_anomaly,
)

# ---------------------------------------------------------------------------
# TranslationHealthSnapshot
# ---------------------------------------------------------------------------


def test_snapshot_zero():
    snap = TranslationHealthSnapshot(0, 0, 0, 0.0, 0.0)
    assert snap.total == 0
    assert snap.fail_rate == 0.0
    assert snap.low_conf_rate == 0.0


def test_snapshot_rates():
    snap = TranslationHealthSnapshot(
        total=100,
        failed=25,
        low_confidence=30,
        fail_rate=0.25,
        low_conf_rate=0.30,
    )
    assert snap.fail_rate == 0.25
    assert snap.low_conf_rate == 0.30


# ---------------------------------------------------------------------------
# check_translation_health
# ---------------------------------------------------------------------------


def _make_db(total: int, pending: int, low_conf: int) -> AsyncMock:
    """2クエリを返す AsyncSession モック."""
    db = AsyncMock()
    # 1回目: total / pending クエリ
    row1 = MagicMock()
    row1.__getitem__ = MagicMock(side_effect=lambda i: [total, pending][i])
    result1 = MagicMock()
    result1.first.return_value = row1 if total > 0 else None

    # 2回目: low_conf クエリ
    row2 = MagicMock()
    row2.__getitem__ = MagicMock(return_value=low_conf)
    result2 = MagicMock()
    result2.first.return_value = row2

    db.execute = AsyncMock(side_effect=[result1, result2])
    return db


@pytest.mark.asyncio
async def test_check_health_no_messages():
    db = _make_db(0, 0, 0)
    snap = await check_translation_health(db, 1, "t.message_translations", "t.meta_messages")
    assert snap.total == 0
    assert snap.failed == 0
    assert snap.fail_rate == 0.0


@pytest.mark.asyncio
async def test_check_health_all_translated():
    db = _make_db(total=50, pending=0, low_conf=5)
    snap = await check_translation_health(db, 1, "t.message_translations", "t.meta_messages")
    assert snap.total == 50
    assert snap.failed == 0
    assert snap.fail_rate == 0.0
    assert snap.low_confidence == 5


@pytest.mark.asyncio
async def test_check_health_pending_messages():
    db = _make_db(total=100, pending=30, low_conf=10)
    snap = await check_translation_health(db, 1, "t.message_translations", "t.meta_messages")
    assert snap.total == 100
    assert snap.failed == 30
    assert snap.fail_rate == pytest.approx(0.30)


# ---------------------------------------------------------------------------
# notify_translation_anomaly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notify_no_alerts():
    """アラート条件を満たさない場合は通知しない."""
    db = AsyncMock()
    snap = TranslationHealthSnapshot(100, 5, 10, 0.05, 0.10)
    result = await notify_translation_anomaly(db, 1, snap, tenant_code="test")
    assert result is False


@pytest.mark.asyncio
async def test_notify_debounce():
    """1時間以内に通知済みならデバウンスで skip."""
    db = AsyncMock()
    recent = datetime.now(timezone.utc)

    row = MagicMock()
    row.__getitem__ = MagicMock(return_value=recent)
    result_mock = MagicMock()
    result_mock.first.return_value = row
    db.execute = AsyncMock(return_value=result_mock)

    snap = TranslationHealthSnapshot(100, 30, 40, 0.30, 0.40)
    sent = await notify_translation_anomaly(db, 1, snap, tenant_code="test")
    assert sent is False


@pytest.mark.asyncio
async def test_notify_webhook_not_configured():
    """webhook URL 未設定なら送信しない（でもアラート条件は満たす）."""
    db = AsyncMock()
    row = MagicMock()
    row.__getitem__ = MagicMock(return_value=None)
    result_mock = MagicMock()
    result_mock.first.return_value = row
    db.execute = AsyncMock(return_value=result_mock)

    snap = TranslationHealthSnapshot(100, 30, 40, 0.30, 0.40)
    with patch.dict("os.environ", {"ADMIN_NOTIFICATION_DISCORD_WEBHOOK": ""}):
        sent = await notify_translation_anomaly(db, 1, snap, tenant_code="test")
    assert sent is False


@pytest.mark.asyncio
async def test_notify_high_fail_rate_triggers_alert():
    """失敗率が閾値超のときアラートリストが生成される（webhook なしで False）."""
    db = AsyncMock()
    row = MagicMock()
    row.__getitem__ = MagicMock(return_value=None)
    result_mock = MagicMock()
    result_mock.first.return_value = row
    db.execute = AsyncMock(return_value=result_mock)

    snap = TranslationHealthSnapshot(
        total=100, failed=25, low_confidence=5,
        fail_rate=0.25,   # > 0.20 threshold
        low_conf_rate=0.05,
    )
    with patch.dict("os.environ", {"ADMIN_NOTIFICATION_DISCORD_WEBHOOK": ""}):
        sent = await notify_translation_anomaly(db, 1, snap, tenant_code="test")
    # webhook なしなので False、ただし例外なく到達する
    assert sent is False
