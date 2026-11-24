"""ADR-1078: 秘書の「予定のカルテ」。カルテと AI の答えを合わせ、日時を検査し、次に聞く欄を決まった順で 1 つ決める。

AI には次に聞く欄を決めさせない（聞く順と回数を試験で確かめるため。design.md §3-1）。
カルテは保存しない（画面が会話の間だけ持つ）。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.schemas.assistant import IntentEvent, KarteIn, parse_iso

ASK_ORDER = ("title", "start", "end", "add_meet")
MAX_ASKS_PER_FIELD = 2

# カルテと AI の答えで、どちらの値を使うかを決める欄（is_all_day・is_meeting はどちらかが真なら真）
_MERGED_FIELDS = ("title", "start", "end", "location", "description", "add_meet")


def merge_karte(ev: IntentEvent | None, karte: KarteIn) -> IntentEvent:
    """カルテと AI の答えを合わせる（design.md §4-3 ④・④'）。

    各欄: カルテに値があり、その欄が直前に聞いた欄でなければカルテの値（AI は題名などを見ていないので上書きさせない）。
    それ以外は AI の値が null でなければ AI の値、null ならカルテの値。ev が None（AI が unknown）なら全欄カルテの値。
    """
    values: dict[str, object] = {}
    for field in _MERGED_FIELDS:
        karte_value = getattr(karte, field)
        ai_value = getattr(ev, field) if ev is not None else None
        if karte_value is not None and karte.asked != field:
            values[field] = karte_value
        elif ai_value is not None:
            values[field] = ai_value
        else:
            values[field] = karte_value
    values["is_all_day"] = karte.is_all_day or (ev is not None and ev.is_all_day)
    values["is_meeting"] = karte.is_meeting or (ev is not None and ev.is_meeting)
    return IntentEvent(**values)


def _readable_time(value: str | None) -> str | None:
    """時刻として読めない文字は null にする（fix1/design.md §3。AI が「わからない」を時刻の欄に入れる場合）。"""
    if value is None:
        return None
    try:
        parse_iso(value)
    except ValueError:
        return None
    return value


def settle_dates(ev: IntentEvent) -> IntentEvent:
    """日時の検査（design.md §4-3 ⑤・fix1/design.md §3）。例外は出さない。

    始まり・終わりが時刻として読めなければ null に戻す（もう一度聞く）。終日で終わりが空なら終わり＝始まり。
    終わり < 始まり、または片方だけ時差の印が無く比べられなければ、終わりを null に戻す。+1 時間は足さない。
    """
    start_text = _readable_time(ev.start)
    end_text = _readable_time(ev.end)
    if start_text is None:
        return ev.model_copy(update={"start": None, "end": end_text})
    if ev.is_all_day and end_text is None:
        end_text = start_text
    if end_text is not None:
        try:
            if parse_iso(end_text) < parse_iso(start_text):
                end_text = None
        except TypeError:
            end_text = None
    return ev.model_copy(update={"start": start_text, "end": end_text})


def next_ask(ev: IntentEvent, meet_available: bool, asked: str | None, asked_count: int) -> tuple[str | None, int]:
    """空いている欄を決まった順で 1 つ返す。同じ欄を 2 回聞いても埋まらなければ None（最後の確かめの欄を出す）。"""
    missing = [f for f in ("title", "start", "end") if getattr(ev, f) is None]
    if ev.is_meeting and meet_available and ev.add_meet is None:
        missing.append("add_meet")
    if not missing:
        return None, 0
    field = missing[0]
    if field == asked:
        if asked_count >= MAX_ASKS_PER_FIELD:
            return None, asked_count
        return field, asked_count + 1
    return field, 1


def _text(value: str | None) -> str | None:
    """前後の空白を除く。空なら None。"""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def same_time(a: str | None, b: str | None) -> bool:
    """時刻として同じか。読めない・時差の印の有無が混ざって比べられないときは文字で比べる。"""
    if a is None or b is None:
        return a is b
    try:
        return parse_iso(a) == parse_iso(b)
    except (ValueError, TypeError):
        return a == b


def edit_changed(ev: IntentEvent, base: IntentEvent) -> bool:
    """直す頼みで、題名・始まり・終わり・場所・説明・Meet のどれかが土台と違うか。"""
    return (
        _text(ev.title) != _text(base.title)
        or _text(ev.location) != _text(base.location)
        or _text(ev.description) != _text(base.description)
        or ev.add_meet != base.add_meet
        or not same_time(ev.start, base.start)
        or not same_time(ev.end, base.end)
    )


def _read_time(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return parse_iso(value)
    except ValueError:
        return None


def merge_edit(ev: IntentEvent | None, karte: KarteIn) -> tuple[IntentEvent, bool]:
    """便W: 直す頼みの合わせ方（design.md §16-4 の 2）。土台はカルテ。AI が値を返した欄だけ AI の値。

    戻り値は (合わせた予定, 変わったか)。ev が None なら土台のまま・変わった＝偽。
    """
    base = IntentEvent(
        title=_text(karte.title),
        start=karte.start,
        end=karte.end,
        is_all_day=karte.is_all_day,
        location=_text(karte.location),
        description=_text(karte.description),
        is_meeting=karte.is_meeting,
        add_meet=karte.add_meet,
    )
    if ev is None:
        return base, False
    values: dict[str, object] = base.model_dump()
    for field in ("title", "location", "description"):
        ai_value = _text(getattr(ev, field))
        if ai_value is not None:
            values[field] = ai_value
    if ev.add_meet is not None:
        values["add_meet"] = ev.add_meet
    values["is_meeting"] = karte.is_meeting or ev.is_meeting
    if not karte.is_all_day:
        ai_start = _read_time(ev.start)
        ai_end = _read_time(ev.end)
        if ai_start is not None and not same_time(ev.start, karte.start):
            values["start"] = ev.start
        if ai_end is not None and not same_time(ev.end, karte.end):
            values["end"] = ev.end
        if ai_end is None and ai_start is not None and values["start"] == ev.start:
            k_start = _read_time(karte.start)
            k_end = _read_time(karte.end)
            if (
                k_start is not None
                and k_end is not None
                and ai_start.tzinfo is not None
                and k_start.tzinfo is not None
                and k_end.tzinfo is not None
            ):
                length = k_end - k_start
                if length >= timedelta(0):
                    values["end"] = (ai_start + length).isoformat(timespec="seconds")
    merged = IntentEvent(**values)
    return merged, edit_changed(merged, base)
