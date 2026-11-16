"""ADR-1078: 秘書の「予定のカルテ」。カルテと AI の答えを合わせ、日時を検査し、次に聞く欄を決まった順で 1 つ決める。

AI には次に聞く欄を決めさせない（聞く順と回数を試験で確かめるため。design.md §3-1）。
カルテは保存しない（画面が会話の間だけ持つ）。
"""

from __future__ import annotations

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
