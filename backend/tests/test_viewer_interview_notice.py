"""期限前日の面談のお願い（ADR-1019 段10 便3）。PG 不要: DB読み・送信・Redis はモック。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.discord_gateway import viewer_interview_notice as n
from app.services import viewer_message_templates as vmt
from tests.viewer_template_fixtures import DEFAULT_BODIES, make_load_body

JST = timezone(timedelta(hours=9))
# 期限: JST 11/10 23:59 -> 前日は JST 11/9
EXP = datetime(2026, 11, 10, 23, 59, tzinfo=JST)


def jst(m, d, h, mi=0):
    return datetime(2026, m, d, h, mi, tzinfo=JST).astimezone(timezone.utc)


def test_is_due_boundaries():
    assert not n.is_due(jst(11, 9, 9, 59), EXP)
    assert n.is_due(jst(11, 9, 10, 0), EXP)
    assert n.is_due(jst(11, 9, 23, 59), EXP)
    assert not n.is_due(jst(11, 10, 10, 0), EXP)  # 当日
    assert not n.is_due(jst(11, 8, 12, 0), EXP)  # 2日前


def test_is_due_utc_day_boundary():
    # UTC 15:00 = JST 翌0:00。期限 JST 11/10 00:30 (= UTC 11/9 15:30) の前日は JST 11/9
    exp = datetime(2026, 11, 9, 15, 30, tzinfo=timezone.utc)
    assert n.expiry_jst_date(exp).isoformat() == "2026-11-10"
    assert n.is_due(datetime(2026, 11, 9, 1, 0, tzinfo=timezone.utc), exp)  # JST 11/9 10:00
    assert not n.is_due(datetime(2026, 11, 9, 0, 59, tzinfo=timezone.utc), exp)  # JST 9:59
    assert not n.is_due(datetime(2026, 11, 9, 15, 0, tzinfo=timezone.utc), exp)  # JST 11/10 0:00 当日


def test_redis_key_uses_jst_date():
    assert n.redis_key(7, EXP) == "viewer_interview_notice:7:2026-11-10"


class _Redis:
    def __init__(self):
        self.keys, self.ttls = {}, {}

    async def exists(self, k):
        return k in self.keys

    async def set(self, k, v, ex=None):
        self.keys[k] = v
        self.ttls[k] = ex


def _factory(rows):
    session = MagicMock()
    res = MagicMock()
    res.all.return_value = rows
    session.execute = AsyncMock(return_value=res)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=cm)
    factory.session = session
    return factory


NOW = jst(11, 9, 11, 0)


async def _run(rows, redis, send_ok=True, now=NOW, bodies=None):
    send = AsyncMock(return_value=send_ok)
    with patch.object(n, "send_room_notice", new=send), patch.object(
        vmt, "load_body", new=make_load_body(bodies)
    ):
        count = await n.run_once(_factory(rows), redis, now)
    return count, send


async def test_sent_sets_key_and_second_run_skips():
    r = _Redis()
    rows = [(1, "555", EXP)]
    c, send = await _run(rows, r)
    assert c == 1 and r.ttls["viewer_interview_notice:1:2026-11-10"] == 30 * 86400
    assert send.await_args.args == (
        "555",
        DEFAULT_BODIES["interview_request"].format(expires_date="11月10日"),
    )
    c2, send2 = await _run(rows, r)
    assert c2 == 0 and send2.await_count == 0


async def test_failed_send_makes_no_key_and_retries():
    r = _Redis()
    rows = [(1, "555", EXP)]
    c, _ = await _run(rows, r, send_ok=False)
    assert c == 0 and r.keys == {}
    c2, _ = await _run(rows, r, send_ok=True)
    assert c2 == 1


async def test_no_redis_sends_nothing():
    c, send = await _run([(1, "555", EXP)], None)
    assert c == 0 and send.await_count == 0


async def test_not_due_row_skipped():
    c, send = await _run([(1, "555", EXP)], _Redis(), now=jst(11, 9, 9, 59))
    assert c == 0 and send.await_count == 0


async def test_query_limits_to_trial_with_room_and_expiry():
    f = _factory([])
    with patch.object(vmt, "load_body", new=make_load_body()):
        await n.run_once(f, _Redis(), NOW)
    sql = str(f.session.execute.await_args.args[0])
    assert "status = 'trial'" in sql
    assert "discord_channel_id IS NOT NULL" in sql
    assert "trial_expires_at IS NOT NULL" in sql


async def test_extension_changes_key_only_when_date_changes():
    r = _Redis()
    await _run([(1, "555", EXP)], r)
    # 同じ日付（時刻だけ違う）への延長: 再送しない
    same_day = datetime(2026, 11, 10, 12, 0, tzinfo=JST)
    c, _ = await _run([(1, "555", same_day)], r)
    assert c == 0
    # 別の日付へ延長: 新しい期限の前日に再送
    later = datetime(2026, 11, 17, 23, 59, tzinfo=JST)
    c, send = await _run([(1, "555", later)], r, now=jst(11, 16, 10, 0))
    assert c == 1 and "viewer_interview_notice:1:2026-11-17" in r.keys


async def test_log_has_no_body(caplog):
    caplog.set_level("INFO")
    await _run([(1, "555", EXP)], _Redis())
    assert "面談" not in caplog.text and "id=1" in caplog.text


async def test_edited_body_is_sent():
    """T5: 画面で直した本文がそのまま出る。"""
    c, send = await _run(
        [(1, "555", EXP)], _Redis(), bodies={"interview_request": "{expires_date}で終わります"}
    )
    assert c == 1 and send.await_args.args == ("555", "11月10日で終わります")


async def test_no_template_sends_nothing_warns_once_and_no_redis_key(caplog):
    """T6: 行が無いとき 0 件・警告1回・Redis キーを作らない。"""
    caplog.set_level("WARNING")
    r = _Redis()
    c, send = await _run([(1, "555", EXP), (2, "556", EXP)], r, bodies={"interview_request": None})
    assert c == 0 and send.await_count == 0 and r.keys == {}
    assert caplog.text.count("template unavailable") == 1
