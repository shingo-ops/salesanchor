from __future__ import annotations

from datetime import date, timedelta

from app.services.holiday_service import list_japan_holidays

# 内閣府の表（2026-11-06 に取得した syukujitsu.csv）の 2026・2027 年の 35 日
# 2028 年分は 2027 年 2 月の内閣府の掲載後に部品の版を上げて足す
CABINET_OFFICE_DAYS = [
    "2026-01-01", "2026-01-12", "2026-02-11", "2026-02-23", "2026-03-20", "2026-04-29",
    "2026-05-03", "2026-05-04", "2026-05-05", "2026-05-06", "2026-07-20", "2026-08-11",
    "2026-09-21", "2026-09-22", "2026-09-23", "2026-10-12", "2026-11-03", "2026-11-23",
    "2027-01-01", "2027-01-11", "2027-02-11", "2027-02-23", "2027-03-21", "2027-03-22",
    "2027-04-29", "2027-05-03", "2027-05-04", "2027-05-05", "2027-07-19", "2027-08-11",
    "2027-09-20", "2027-09-23", "2027-10-11", "2027-11-03", "2027-11-23",
]


def test_s1_matches_cabinet_office_table():
    result = list_japan_holidays(date(2026, 1, 1), date(2028, 1, 1))
    assert [h["date"] for h in result] == CABINET_OFFICE_DAYS


def test_s2_november_2026_has_two_holidays_in_japanese():
    result = list_japan_holidays(date(2026, 11, 1), date(2026, 12, 1))
    assert [h["date"] for h in result] == ["2026-11-03", "2026-11-23"]
    assert result[0]["name"] == "文化の日"
    assert result[1]["name"] == "勤労感謝の日"


def test_s3_english_name():
    result = list_japan_holidays(date(2026, 11, 3), date(2026, 11, 4), lang="en")
    assert result[0]["name"] == "Culture Day"


def test_s4_end_is_exclusive():
    day = date(2026, 11, 3)
    assert len(list_japan_holidays(day, day + timedelta(days=1))) == 1
    assert list_japan_holidays(date(2026, 11, 4), date(2026, 11, 23)) == []
