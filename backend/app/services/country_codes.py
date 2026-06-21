from __future__ import annotations

"""国コード正規化ヘルパー。

国名表記や小文字 alpha-2 を ISO 3166-1 alpha-2 に寄せる。
既存の data_migration/data_cleansing.py と同じ解決規則を backend 側で再利用するための
共通実装。
"""

import logging

import pycountry

logger = logging.getLogger(__name__)

_COUNTRY_OVERRIDES = {
    "usa": "US",
    "u.s.a.": "US",
    "u.s.": "US",
    "us": "US",
    "united states of america": "US",
    "united states": "US",
    "uk": "GB",
    "u.k.": "GB",
    "united kingdom": "GB",
    "britain": "GB",
    "great britain": "GB",
    "jp": "JP",
    "japan": "JP",
    "日本": "JP",
    "china": "CN",
    "中国": "CN",
    "taiwan": "TW",
    "台湾": "TW",
    "hong kong": "HK",
    "香港": "HK",
    "korea": "KR",
    "south korea": "KR",
    "韓国": "KR",
}


def parse_country_code(value: str | None) -> str | None:
    """任意の国名表記を ISO 3166-1 alpha-2 に正規化する。

    すでに 2 文字の alpha-2 が入っている場合はそのまま大文字化する。
    解決不能なら None を返す。
    """
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if len(stripped) == 2 and stripped.isalpha():
        try:
            pycountry.countries.lookup(stripped.upper())
            return stripped.upper()
        except LookupError:
            pass
    lowered = stripped.lower()
    if lowered in _COUNTRY_OVERRIDES:
        return _COUNTRY_OVERRIDES[lowered]
    try:
        matches = pycountry.countries.search_fuzzy(stripped)
        if matches:
            return matches[0].alpha_2
    except LookupError:
        pass
    logger.warning("parse_country_code: 国名解決不能 %r → None", value)
    return None
