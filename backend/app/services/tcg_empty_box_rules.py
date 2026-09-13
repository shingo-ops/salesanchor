"""Finite empty-box classification, shared by the analyzer and PostgreSQL reads."""
from __future__ import annotations

from collections.abc import Mapping

EMPTY_CODE = "CN0011"
EMPTY_CANONICAL = "Empty box"
EMPTY_WORD = "空箱"
NEGATIVE_SUFFIXES = ("空箱ではない", "空箱ではありません", "空箱なし", "空箱無し")
POSITIVE_SUFFIXES = ("空箱", "空箱のみ")
AMBIGUOUS_WORDS = (
    "かもしれ", "可能性", "不明", "未確認", "おそらく", "と思", "？", "?",
    "とは限ら", "保証", "付属", "同梱", "中身入り", "中身あり", "本体あり", "付き",
)
EMPTY_REASONS = ("empty_box", "empty_box_ambiguous", "empty_box_master_unavailable")
# Explicit Unicode whitespace set keeps Python and SQL trimming identical.
WHITESPACE = " \t\n\r\v\f\x1c\x1d\x1e\x1f\x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"


def classify_field(value: str | None) -> str:
    value = (value or "").strip(WHITESPACE)
    if EMPTY_WORD not in value:
        return "none"
    if value.count(EMPTY_WORD) > 1 or any(word in value for word in AMBIGUOUS_WORDS):
        return "ambiguous"
    if value.endswith(NEGATIVE_SUFFIXES):
        return "negative"
    if value.endswith(POSITIVE_SUFFIXES):
        return "positive"
    return "ambiguous"


def classify_empty_box(*values: str | None) -> str:
    states = {classify_field(value) for value in values}
    if "ambiguous" in states or {"positive", "negative"} <= states:
        return "ambiguous"
    return "positive" if "positive" in states else "none"


def mentions_empty_box(*values: str | None) -> bool:
    return any(EMPTY_WORD in (value or "") for value in values)


def consumes_empty_memo(value: str | None) -> bool:
    return (value or "").strip(WHITESPACE) in POSITIVE_SUFFIXES


def valid_empty_definition(entry: Mapping | None) -> bool:
    return bool(entry and entry.get("code") == EMPTY_CODE
                and entry.get("canonical") == EMPTY_CANONICAL
                and entry.get("priority") == 1 and entry.get("app_kubun") == ""
                and entry.get("search_kw") == EMPTY_WORD
                and entry.get("exclude_kw") == ",".join(NEGATIVE_SUFFIXES)
                and entry.get("is_active", True) is True)


def literal(value: str) -> str:
    """Quote internal rule constants only; user data remains SQL expressions/binds."""
    return "'" + value.replace("'", "''") + "'"


def field_sql(expression: str) -> str:
    value = f"btrim(COALESCE({expression}, ''), {literal(WHITESPACE)})"
    uncertain = " OR ".join(f"strpos({value}, {literal(word)}) > 0" for word in AMBIGUOUS_WORDS)
    negative = " OR ".join(f"right({value}, {len(word)}) = {literal(word)}" for word in NEGATIVE_SUFFIXES)
    positive = " OR ".join(f"right({value}, {len(word)}) = {literal(word)}" for word in POSITIVE_SUFFIXES)
    return f"""CASE WHEN strpos({value}, {literal(EMPTY_WORD)}) = 0 THEN 'none'
        WHEN (length({value}) - length(replace({value}, {literal(EMPTY_WORD)}, ''))) > 2
          OR ({uncertain}) THEN 'ambiguous'
        WHEN {negative} THEN 'negative'
        WHEN {positive} THEN 'positive' ELSE 'ambiguous' END"""


def classification_sql(*expressions: str) -> str:
    fields = ",".join(f"({field_sql(expression)})" for expression in expressions)
    return f"""(SELECT CASE
        WHEN bool_or(value = 'ambiguous') OR (bool_or(value = 'positive') AND bool_or(value = 'negative'))
            THEN 'ambiguous'
        WHEN bool_or(value = 'positive') THEN 'positive' ELSE 'none' END
        FROM (VALUES {fields}) AS empty_fields(value))"""


def empty_definition_sql(expression: str) -> str:
    pairs = {"code": EMPTY_CODE, "canonical": EMPTY_CANONICAL, "app_kubun": "",
             "search_kw": EMPTY_WORD, "exclude_kw": ",".join(NEGATIVE_SUFFIXES)}
    parts = [f"{expression}->>{literal(key)} = {literal(value)}" for key, value in pairs.items()]
    return "COALESCE((" + " AND ".join(parts) + f" AND {expression}->>'priority' = '1' AND {expression}->>'is_active' = 'true'), FALSE)"
