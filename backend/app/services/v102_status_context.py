"""試作版 v102：ステータスを、件の外の手がかり（発売日・先の日付・見出し）で予約などに決める。

設計: docs/handoff/v102-preorder-context/card-PO.md。規則・語・文字列はすべて tcg_status_master の行から読む（ここには書かない）。
resolve_status_v2 が DEFAULT で決めたときだけ使う（EXCLUDE の Sold out・OUTPUT の規則は変えない）。
該当する行（effect が RELEASE_AHEAD・DATE_AHEAD・HEADING）が表に無ければ、何もしない。
"""
from __future__ import annotations

import calendar
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.services.tcg_analyzer_svc import _match_status_pattern, resolve_status_v2
from app.services.tcg_status_values import (
    EFFECT_DATE_AHEAD,
    EFFECT_HEADING,
    EFFECT_RELEASE_AHEAD,
    MATCH_DEFAULT,
    MATCH_REGEX,
    MATCH_RELEASE,
)

JST = timezone(timedelta(hours=9))
EARLY_PART_END_DAY = 10  # 上旬の終わり
MIDDLE_PART_END_DAY = 20  # 中旬の終わり
# 旬の語 → 終わりの日（None は月末）。日付の書き方（正規表現）は表の行にあり、ここは名前付きグループ part の語だけを日に直す
_PART_END_DAY: Mapping[str, int | None] = {"上旬": EARLY_PART_END_DAY, "中旬": MIDDLE_PART_END_DAY, "下旬": None, "末": None, "頃": None}
_DEFAULT_SENTINEL = "\0v102-status-context-default"


@dataclass(frozen=True)
class StatusContext:
    """件の外の手がかり。posted_date が None のとき、日付に基づく規則（発売日・先の日付）は働かない。"""

    posted_date: date | None
    product_release: Mapping[str, date]  # 商品ID（文字列）→ 発売日
    owned_lines: frozenset[int]  # どれかの件の lines に入っている行番号（見出しの探索で飛ばす）


def posted_jst_date(posted_at: datetime | None) -> date | None:
    """投稿日時（line_posted_at）の JST の日付。タイムゾーンが無い値は JST とみなす。None は None。"""
    if posted_at is None:
        return None
    aware = posted_at if posted_at.tzinfo is not None else posted_at.replace(tzinfo=JST)
    return aware.astimezone(JST).date()


def _rules(status_entries: Sequence[dict], effect: str, match_type: str) -> list[dict]:
    return sorted((e for e in status_entries if e["effect"] == effect and e["match_type"] == match_type), key=lambda e: e["priority"])


def _hits(text_val: str, entry: dict) -> bool:
    if not _match_status_pattern(text_val, entry["search_pattern"], MATCH_REGEX):
        return False
    return not (entry.get("exclude_pattern") and _match_status_pattern(text_val, entry["exclude_pattern"], MATCH_REGEX))


def decided_by_default(block: str, status_entries: list[dict]) -> bool:
    """resolve_status_v2 が DEFAULT の行で決めたか。本物の resolve_status_v2 に、先頭へ目印の DEFAULT を足して通し、目印が返れば DEFAULT。"""
    if not any(e["match_type"] == MATCH_DEFAULT for e in status_entries):
        return False
    sentinel = {"canonical": _DEFAULT_SENTINEL, "search_pattern": "", "exclude_pattern": "", "priority": 0,
                "match_type": MATCH_DEFAULT, "effect": "OUTPUT"}
    return resolve_status_v2(block, [sentinel, *status_entries], raw_memo=block)[0] == _DEFAULT_SENTINEL


def _period_end(posted: date, month: int, day: int | None, part: str | None) -> date | None:
    """日付の終わり。年は投稿日の年、その月が投稿日の月より前なら翌年。日付として成り立たなければ None。"""
    if not 1 <= month <= 12:
        return None
    year = posted.year + (1 if month < posted.month else 0)
    last_day = calendar.monthrange(year, month)[1]
    if day is not None:
        return date(year, month, day) if 1 <= day <= last_day else None
    end_day = _PART_END_DAY.get(part or "")
    return date(year, month, min(end_day, last_day) if end_day else last_day)


def _group(m: re.Match, name: str) -> str | None:
    return m.groupdict().get(name)


def _date_ahead(block: str, posted: date, entry: dict) -> str | None:
    """この行の search_pattern が当たった中で、終わりが投稿日より後の最初の当たり（その文字列）。"""
    if not _hits(block, entry):
        return None
    try:
        matches = list(re.finditer(entry["search_pattern"], block))
    except re.error:
        return None
    for m in matches:
        month, day = _group(m, "m"), _group(m, "d")
        if month is None:
            continue
        end = _period_end(posted, int(month), int(day) if day else None, _group(m, "part"))
        if end is not None and end > posted:
            return m.group(0)
    return None


def _heading(lines: Sequence[str], first_line: int, owned: frozenset[int], rules: list[dict]) -> tuple[str, int] | None:
    for n in range(first_line - 1, 0, -1):
        text_val = lines[n - 1]
        if n in owned or not text_val.strip():
            continue
        for entry in rules:
            if _hits(text_val, entry):
                return entry["canonical"], n
    return None


def context_status(
    status: str, effect: str | None, *, block: str, item_lines: Sequence[int], lines: Sequence[str], product_id: object,
    status_entries: list[dict], context: StatusContext,
) -> tuple[str, str | None]:
    """(ステータス, 根拠)。変えないときは (status, None)。

    RELEASE_AHEAD → DATE_AHEAD → HEADING の順で最初に決まったものを採る。見出しの canonical が DEFAULT と同じなら変えない。
    """
    if effect is not None or not status_entries or not decided_by_default(block, status_entries):
        return status, None
    posted = context.posted_date
    release = context.product_release.get(str(product_id)) if product_id is not None else None
    if posted is not None and release is not None and release > posted:
        for entry in _rules(status_entries, EFFECT_RELEASE_AHEAD, MATCH_RELEASE):
            return entry["canonical"], f"{EFFECT_RELEASE_AHEAD}:{release.isoformat()}"
    if posted is not None:
        for entry in _rules(status_entries, EFFECT_DATE_AHEAD, MATCH_REGEX):
            matched = _date_ahead(block, posted, entry)
            if matched is not None:
                return entry["canonical"], f"{EFFECT_DATE_AHEAD}:{matched}"
    found = _heading(lines, min(item_lines), context.owned_lines, _rules(status_entries, EFFECT_HEADING, MATCH_REGEX)) if item_lines else None
    if found is not None and found[0] != status:
        return found[0], f"{EFFECT_HEADING}:{found[1]}"
    return status, None
