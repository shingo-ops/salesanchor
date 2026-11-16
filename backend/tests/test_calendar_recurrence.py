"""予定の繰り返しの決まり（calendar_recurrence）の純粋関数の試験（ADR-1075 便15A）。表は使わない。"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pytest

from app.services import calendar_recurrence as rec

JST = rec.JST


def _jst(y, mo, d, h=0, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=JST)


def test_build_rule_six_kinds():
    s = _jst(2026, 11, 12, 10)  # 木曜・第 2 木曜
    assert rec.build_rule("none", s) is None
    assert rec.build_rule("daily", s) == "FREQ=DAILY"
    assert rec.build_rule("weekly", s) == "FREQ=WEEKLY;BYDAY=TH"
    assert rec.build_rule("weekdays", s) == "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
    assert rec.build_rule("yearly", s) == "FREQ=YEARLY"
    assert rec.build_rule("monthly_nth", s) == "FREQ=MONTHLY;BYDAY=2TH"
    assert rec.build_rule("monthly_last", _jst(2026, 11, 30, 10)) == "FREQ=MONTHLY;BYDAY=-1MO"


def test_build_rule_not_available():
    with pytest.raises(ValueError):
        rec.build_rule("monthly_nth", _jst(2026, 10, 29, 10))  # 第 5 木曜
    with pytest.raises(ValueError):
        rec.build_rule("monthly_last", _jst(2026, 11, 12, 10))  # 最後の木曜ではない


def test_rule_to_recurrence_round_trip():
    s = _jst(2026, 11, 12, 10)
    for choice, start in (
        ("daily", s),
        ("weekly", s),
        ("weekdays", s),
        ("yearly", s),
        ("monthly_nth", s),
        ("monthly_last", _jst(2026, 11, 30, 10)),
    ):
        rule = rec.build_rule(choice, start)
        assert rec.rule_to_recurrence(rule) == choice
        assert rec.rule_to_recurrence(rule + ";UNTIL=20261231T145959Z") == choice
    assert rec.rule_to_recurrence("FREQ=WEEKLY;INTERVAL=2;BYDAY=TH") == "custom"
    assert rec.rule_to_recurrence(None) == "none"


def test_expand_two_months():
    ws, we = _jst(2026, 11, 1), _jst(2027, 1, 1)
    hour = timedelta(hours=1)

    def run(rule, start):
        return rec.expand(rule, start, hour, False, ws, we)

    weekly = run("FREQ=WEEKLY;BYDAY=TH", _jst(2026, 11, 12, 10))
    assert len(weekly) == 8
    assert weekly[:2] == [_jst(2026, 11, 12, 10), _jst(2026, 11, 19, 10)]

    last = run("FREQ=MONTHLY;BYDAY=-1MO", _jst(2026, 11, 30, 10))
    assert last == [_jst(2026, 11, 30, 10), _jst(2026, 12, 28, 10)]

    s = _jst(2026, 11, 12, 10)
    daily = run("FREQ=DAILY", s)
    assert len(daily) == 50 and daily[:2] == [_jst(2026, 11, 12, 10), _jst(2026, 11, 13, 10)]
    weekdays = run("FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR", s)
    assert len(weekdays) == 36 and weekdays[:2] == [_jst(2026, 11, 12, 10), _jst(2026, 11, 13, 10)]
    yearly = run("FREQ=YEARLY", s)
    assert yearly == [_jst(2026, 11, 12, 10)]
    nth = run("FREQ=MONTHLY;BYDAY=2TH", s)
    assert nth == [_jst(2026, 11, 12, 10), _jst(2026, 12, 10, 10)]
    for occ in daily + weekdays + nth + weekly:
        assert (occ.hour, occ.minute) == (10, 0) and occ.utcoffset() == timedelta(hours=9)


def test_expand_strict_window():
    hour = timedelta(hours=1)
    rule = "FREQ=DAILY"
    start = _jst(2026, 11, 1, 10)
    # 期間の終わりちょうどに始まる回は入らない
    out = rec.expand(rule, start, hour, False, _jst(2026, 11, 3, 0), _jst(2026, 11, 5, 10))
    assert _jst(2026, 11, 5, 10) not in out
    assert _jst(2026, 11, 4, 10) in out
    # 期間の始まりちょうどに終わる回は入らない
    out = rec.expand(rule, start, hour, False, _jst(2026, 11, 3, 11), _jst(2026, 11, 5, 0))
    assert _jst(2026, 11, 3, 10) not in out
    assert _jst(2026, 11, 4, 10) in out


def test_expand_all_day():
    out = rec.expand(
        "FREQ=WEEKLY;BYDAY=TH",
        _jst(2026, 11, 12, 0),
        timedelta(hours=23, minutes=59),
        True,
        _jst(2026, 11, 1),
        _jst(2026, 12, 1),
    )
    assert len(out) == 3
    assert all((o.hour, o.minute) == (0, 0) and o.utcoffset() == timedelta(hours=9) for o in out)


def test_expand_limit_1000(caplog):
    with caplog.at_level(logging.WARNING, logger="app.services.calendar_recurrence"):
        out = rec.expand(
            "FREQ=DAILY",
            _jst(2026, 1, 1, 10),
            timedelta(hours=1),
            False,
            _jst(2026, 1, 1),
            _jst(2036, 1, 1),
        )
    assert len(out) == 1000
    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1


def test_until_before_and_with_until():
    occ = _jst(2026, 11, 26, 10)
    assert rec.until_before(occ, False) == "20261125T145959Z"
    assert rec.until_before(_jst(2026, 11, 26, 0), True) == "20261125"
    cut = rec.with_until("FREQ=WEEKLY;BYDAY=TH", "20261125T145959Z")
    assert cut == "FREQ=WEEKLY;BYDAY=TH;UNTIL=20261125T145959Z"
    # 既にある早い UNTIL は残る
    early = "FREQ=WEEKLY;BYDAY=TH;UNTIL=20261101T145959Z"
    assert rec.with_until(early, "20261125T145959Z") == early
    # 遅い UNTIL は新しい早いものに置き換わる
    late = "FREQ=WEEKLY;BYDAY=TH;UNTIL=20261231T145959Z"
    assert rec.with_until(late, "20261125T145959Z") == cut


def test_carry_and_after_until():
    assert rec.convert_until("20261125T145959Z", True) == "20261125"
    assert rec.convert_until("20261125", False) == "20261125T145959Z"
    assert rec.convert_until("20261125", True) == "20261125"
    new_rule = "FREQ=WEEKLY;BYDAY=TH"
    assert rec.carry_until(new_rule, "FREQ=DAILY", False) == new_rule
    assert rec.carry_until(new_rule, "FREQ=DAILY;UNTIL=20261125", False) == new_rule + ";UNTIL=20261125T145959Z"
    assert rec.carry_until(new_rule, "FREQ=DAILY;UNTIL=20261125T145959Z", True) == new_rule + ";UNTIL=20261125"
    rule = new_rule + ";UNTIL=20261125T145959Z"
    assert rec.starts_after_until(rule, _jst(2026, 11, 26, 10), False) is True
    assert rec.starts_after_until(rule, _jst(2026, 11, 25, 10), False) is False
    assert rec.starts_after_until(new_rule, _jst(2030, 1, 1, 10), False) is False


def test_is_occurrence_and_first():
    rule = "FREQ=WEEKLY;BYDAY=TH"
    start = _jst(2026, 11, 12, 10)
    assert rec.is_occurrence(rule, start, False, _jst(2026, 11, 19, 10)) is True
    assert rec.is_occurrence(rule, start, False, _jst(2026, 11, 20, 10)) is False
    assert rec.is_occurrence(rule, start, False, _jst(2026, 11, 19, 11)) is False
    assert rec.is_first_occurrence(start, False, _jst(2026, 11, 12, 10)) is True
    assert rec.is_first_occurrence(start, False, _jst(2026, 11, 19, 10)) is False
    all_day = _jst(2026, 11, 12, 0)
    assert rec.is_occurrence(rule, all_day, True, _jst(2026, 11, 19, 0)) is True
    assert rec.is_first_occurrence(all_day, True, _jst(2026, 11, 12, 0)) is True
