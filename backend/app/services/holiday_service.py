"""日本の祝日（ADR なし・design schedule-gcal-clone §3.4 案 C）。

正本は PyPI の holidays 部品 1 か所。DB には持たない。
翌年分は部品の版上げで入る（内閣府の翌年分の掲載は毎年 2 月）。
"""
from __future__ import annotations

from datetime import date

import holidays

# 画面の言語 → 部品の言語（JP が持つのは en_US・ja・th）
_LANGUAGES = {"ja": "ja", "en": "en_US"}


def list_japan_holidays(start: date, end: date, lang: str = "ja") -> list[dict[str, str]]:
    """start 以上 end 未満の日本の祝日を、日付の早い順に返す。"""
    language = _LANGUAGES.get(lang, "ja")
    years = range(start.year, end.year + 1)
    jp = holidays.country_holidays("JP", years=years, language=language)
    return [
        {"date": day.isoformat(), "name": jp[day]}
        for day in sorted(jp)
        if start <= day < end
    ]
