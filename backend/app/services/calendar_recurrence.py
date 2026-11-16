"""予定の繰り返しの決まり（RRULE）を作る・読み戻す・回に広げる（ADR-1075・design.md §12.4・§12.5）。

表を読まない・書かない純粋な関数だけを置く。決まりの文字は calendar_events.recurrence_rule の 1 か所だけに持つ。
- 時刻つき: dtstart は日本時間の aware。UNTIL は UTC の Z 形（YYYYMMDDTHHMMSSZ）。
- 終日: dtstart は日本時間の日付の 0:00（naive）。UNTIL は日付の形（YYYYMMDD）。
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr

logger = logging.getLogger(__name__)

JST = ZoneInfo("Asia/Tokyo")

RECURRENCE_VALUES = (
    "none",
    "daily",
    "weekly",
    "monthly_nth",
    "monthly_last",
    "yearly",
    "weekdays",
)

MAX_OCCURRENCES = 1000

_DAYS = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")
_WEEKDAYS_RULE = "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
_UNTIL_RE = re.compile(r";UNTIL=[0-9TZ]+")


def to_jst(dt: datetime) -> datetime:
    """日本時間の aware にそろえる（時差の無い値は日本時間とみなす）。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    return dt.astimezone(JST)


def build_rule(recurrence: str, start: datetime) -> Optional[str]:
    """選び方と開始日（日本時間で見る）から決まりの文字を作る。none は None。

    開始日で選べない値（第 5 週の monthly_nth・その月の最後の同じ曜日でない monthly_last）は ValueError。
    """
    if recurrence == "none":
        return None
    s = to_jst(start)
    day = _DAYS[s.weekday()]
    if recurrence == "daily":
        return "FREQ=DAILY"
    if recurrence == "weekly":
        return f"FREQ=WEEKLY;BYDAY={day}"
    if recurrence == "weekdays":
        return _WEEKDAYS_RULE
    if recurrence == "yearly":
        return "FREQ=YEARLY"
    if recurrence == "monthly_nth":
        n = (s.day - 1) // 7 + 1
        if n > 4:
            raise ValueError("monthly_nth_not_available")
        return f"FREQ=MONTHLY;BYDAY={n}{day}"
    if recurrence == "monthly_last":
        if (s + timedelta(days=7)).month == s.month:
            raise ValueError("monthly_last_not_available")
        return f"FREQ=MONTHLY;BYDAY=-1{day}"
    raise ValueError("unknown_recurrence")


def strip_until(rule: str) -> str:
    return _UNTIL_RE.sub("", rule)


def get_until(rule: str) -> Optional[str]:
    m = _UNTIL_RE.search(rule)
    return m.group(0)[len(";UNTIL="):] if m else None


def rule_to_recurrence(rule: Optional[str]) -> str:
    """決まりの文字から選び方を読み戻す（UNTIL は除いてから）。読み戻せないものは "custom"。"""
    if not rule:
        return "none"
    r = strip_until(rule)
    if r == "FREQ=DAILY":
        return "daily"
    if r == _WEEKDAYS_RULE:
        return "weekdays"
    if r == "FREQ=YEARLY":
        return "yearly"
    m = re.fullmatch(r"FREQ=WEEKLY;BYDAY=(MO|TU|WE|TH|FR|SA|SU)", r)
    if m:
        return "weekly"
    m = re.fullmatch(r"FREQ=MONTHLY;BYDAY=([1-4])(MO|TU|WE|TH|FR|SA|SU)", r)
    if m:
        return "monthly_nth"
    m = re.fullmatch(r"FREQ=MONTHLY;BYDAY=-1(MO|TU|WE|TH|FR|SA|SU)", r)
    if m:
        return "monthly_last"
    return "custom"


def until_before(occurrence_start: datetime, is_all_day: bool) -> str:
    """「これ以降」で切る UNTIL: その回の前の日の終わり（§12.5 following）。

    時刻つき: 前の日の 23:59:59 日本時間を UTC の Z 形。終日: 前の日の日付。
    """
    prev_day = to_jst(occurrence_start).date() - timedelta(days=1)
    if is_all_day:
        return prev_day.strftime("%Y%m%d")
    end_jst = datetime.combine(prev_day, time(23, 59, 59), tzinfo=JST)
    return end_jst.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def with_until(rule: str, until: str) -> str:
    """決まりに UNTIL を付ける。既に UNTIL があれば早い方を残す（§12.5 UNTIL の扱い）。

    同じ決まりの UNTIL どうしは同じ形（時刻つきは Z 形・終日は日付）なので文字の比べで早い方が分かる。
    """
    old = get_until(rule)
    if old is not None and old <= until:
        return rule
    return strip_until(rule) + f";UNTIL={until}"


def _until_value(dt: datetime, is_all_day: bool) -> str:
    """UNTIL と同じ形の文字（終日は日本時間の日付・時刻つきは UTC の Z 形）。"""
    j = to_jst(dt)
    if is_all_day:
        return j.strftime("%Y%m%d")
    return j.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def convert_until(until: str, to_all_day: bool) -> str:
    """UNTIL の形を終日／時刻つきに合わせ直す（終日⇄時刻つきを直した回で元の UNTIL を引き継ぐため）。

    時刻つき→終日: UTC の時刻を日本時間の日付にする。終日→時刻つき: その日の 23:59:59 日本時間を UTC の Z 形にする。
    """
    has_time = "T" in until
    if to_all_day and has_time:
        dt = datetime.strptime(until, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return dt.astimezone(JST).strftime("%Y%m%d")
    if not to_all_day and not has_time:
        day = datetime.strptime(until, "%Y%m%d").date()
        end_jst = datetime.combine(day, time(23, 59, 59), tzinfo=JST)
        return end_jst.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return until


def carry_until(new_rule: str, old_rule: Optional[str], is_all_day: bool) -> str:
    """元の決まりの UNTIL を新しい決まりへ引き継ぐ（§12.5 UNTIL の扱い）。元に UNTIL が無ければそのまま。"""
    old = get_until(old_rule) if old_rule else None
    if old is None:
        return new_rule
    return with_until(new_rule, convert_until(old, is_all_day))


def starts_after_until(rule: str, start: datetime, is_all_day: bool) -> bool:
    """新しい始まりが決まりの UNTIL より後か（後なら 422 recurrence_after_until）。UNTIL が無ければ False。"""
    until = get_until(rule)
    if until is None:
        return False
    return _until_value(start, is_all_day) > convert_until(until, is_all_day)


def _dtstart(master_start: datetime, is_all_day: bool) -> datetime:
    s = to_jst(master_start)
    if is_all_day:
        return datetime.combine(s.date(), time(0, 0))
    return s


def _to_rule_tz(dt: datetime, is_all_day: bool) -> datetime:
    """比べる時刻を決まりの型にそろえる（終日は日本時間の naive）。"""
    j = to_jst(dt)
    return j.replace(tzinfo=None) if is_all_day else j


def _from_rule_tz(dt: datetime, is_all_day: bool) -> datetime:
    return dt.replace(tzinfo=JST) if is_all_day else dt.astimezone(JST)


def expand(
    rule: str,
    master_start: datetime,
    duration: timedelta,
    is_all_day: bool,
    window_start: datetime,
    window_end: datetime,
    limit: int = MAX_OCCURRENCES,
) -> list[datetime]:
    """期間の中の回の始まり（日本時間の aware）を返す。

    期間の始まり − 長さ から 期間の終わり まで（両端を含む）で取り、
    回の始まりが期間の終わりより前、かつ回の終わりが期間の始まりより後の回だけに最後に絞る（§12.5・審査1 ⑥）。
    limit を超えたら打ち切って警告を残す。
    """
    rr = rrulestr(rule, dtstart=_dtstart(master_start, is_all_day))
    lo = _to_rule_tz(window_start - duration, is_all_day)
    hi = _to_rule_tz(window_end, is_all_day)
    out: list[datetime] = []
    ws = to_jst(window_start)
    we = to_jst(window_end)
    for occ in rr.xafter(lo, inc=True):
        if occ > hi:
            break
        start = _from_rule_tz(occ, is_all_day)
        if start < we and start + duration > ws:
            if len(out) >= limit:
                logger.warning("繰り返しの回が %s を超えたので打ち切った: rule=%s", limit, rule)
                break
            out.append(start)
    return out


def is_occurrence(rule: str, master_start: datetime, is_all_day: bool, occurrence_start: datetime) -> bool:
    """occurrence_start が決まりの回に当たるか（その時刻 ±1 秒）。"""
    rr = rrulestr(rule, dtstart=_dtstart(master_start, is_all_day))
    o = _to_rule_tz(occurrence_start, is_all_day)
    return bool(rr.between(o - timedelta(seconds=1), o + timedelta(seconds=1), inc=True))


def occurrence_of(master_start: datetime, is_all_day: bool, occurrence_start: datetime) -> datetime:
    """回の始まりを表に入れる形にそろえる（終日はその日の日本時間 0:00・§12.4）。"""
    o = to_jst(occurrence_start)
    if is_all_day:
        return datetime.combine(o.date(), time(0, 0), tzinfo=JST)
    return o


def is_first_occurrence(master_start: datetime, is_all_day: bool, occurrence_start: datetime) -> bool:
    return occurrence_of(master_start, is_all_day, occurrence_start) == occurrence_of(
        master_start, is_all_day, master_start
    )


def google_recurrence(rule: str) -> list[str]:
    """Google へ送る本文の recurrence（§12.7）。"""
    return ["RRULE:" + rule]
