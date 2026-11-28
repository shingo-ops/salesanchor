"""秘書の「予定の日付の読み方」（date-reading/design.md）。「来週の月曜」などの日付を AI に任せず決まりの表で決める。

時刻は AI が読んだまま変えない。日付（YYYY-MM-DD の部分）だけを差し替える。
決まりの表に無い言い方・日付の言い方が 2 つ以上の文は None（AI の読んだ日付のまま）。
週は月曜から日曜まで（PO 2026-11-15）。
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta, timezone

from app.schemas.assistant import IntentEvent, KarteIn, parse_iso

_WEEKDAYS = "月火水木金土日"  # date.weekday() の 0〜6 と同じ並び
_JST_OFFSET = timedelta(hours=9)

# 表に無い日付の言い方。1 つでもあれば AI の読んだ日付のまま（design.md §3-1 (1)）
_OTHER_DATE_WORDS = re.compile(
    r"\d+\s*年|再来年|来年|今年|去年|昨年|月末|月初|週末|年末|年始|再来月|来月|今月|先月|翌日|翌週|前日|先週|一昨日|昨日|おととい|きのう|"
    r"今夜|今晩|今宵|今朝|今夕|明朝|明晩|明夕|昨夜|昨晩|今から|これから|当日|近日|今度|近々|平日|土日|"
    r"あす|あくる|明くる|みょうにち|こんや|こんばん|けさ|このあと|あとで|のちほど|すぐ|ただちに|直ちに|即日|深夜|未明|夜中|"
    r"いまから|いますぐ|今のうち|いまのうち|クリスマス|イブ|"
    r"毎|隔週|第\s*[\d一二三四五六七八九十]|\d+\s*日\s*(?:中|\d+\s*(?:回|時間)|あたり|当たり|おき|ごと)|\d+\s*日\s*に\s*(?:わた|渡|またが|跨|分け|分割|[\d一二三四五六七八九十]+\s*(?:回|度|件))|"
    r"(?:丸|まる)\s*\d+\s*日|\d+\s*日\s*の?\s*(?:延長|猶予|日程|遅れ|遅延|期間|休暇)|\d+\s*泊|\d+\s*(?:日|週間?|か月|ヶ月|カ月|ヵ月)\s*(?:後|前|間)"
)
# 日付を言い直す語・打ち消しの語。文のどこかに 1 つでもあれば AI の読んだ日付のまま（design.md §3-1 (2)）
# 前後の点検は隣の 1 字しか見ないので「年明けは月曜」「月曜、次の日」「とおか、木曜」のような離れた語はここで止める
_DATE_MODIFIERS = re.compile(
    r"明け|開け|末|旬|初め|始め|頭|半ば|次|翌|(?<!午)前|(?<![午明])後|過ぎ|以降|以前|以外|以内|以来|最初|最後|年内|月内|週内|"
    r"ついたち|ふつか|みっか|よっか|いつか|むいか|なのか|ようか|ここのか|とおか|はつか|みそか|つごもり|晦|朔|"
    r"ではなく|じゃなく|でなく|除|抜き|違|別の日|別日|都合|だめ|ダメ|駄目|無理|ほか|他の日|つぎ|正月|盆|連休|休み|祝|年度|期|元旦|元日|締|〆"
)
# 理由や前置きの句をつなぐ形。文のどこかに 1 つでもあれば AI の読んだ日付のまま（design.md §3-1 (1b)・§11-14）
# 「今日は終日外出なので、あす10時」「明日は出張です。あとで電話」のように、別の句に一覧に無い日付の言葉が入りうる
_CLAUSE_LINK = re.compile(
    r"ので|ため|だから|から\s*[、,]|けど|けれど|が\s*[、,]|で\s*[、,]|(?:です|ます|でした|ました)\s*[。.!?]\s*\S"
)
# 言い方の後ろが「は・も・が」＋朝・昼・夕方・夜・終日（その日の様子を言う形）のとき、
# その先に句読点と続きの文があれば AI の読んだ日付のまま（「明日は朝から出張。このあと30分」。design.md §3-1 (1b)）
_STATE_AFTER = re.compile(r"\s*[はもが]\s*(?:朝|昼|夕方|夜|終日)")
_BREAK_THEN_MORE = re.compile(r"[、,。.!?]\s*\S")
_MONTH_DAY = re.compile(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日")
_DAY_ONLY = re.compile(
    r"(?<![月\d])(\d{1,2})\s*日(?=\s*(?:$|\d|まで|から|ごろ|頃|午前|午後|朝|昼|夕方|夜|[のにはも、。,.!?]))"
)
_WEEKDAY = re.compile(r"(再来週|来週|今週)?\s*の?\s*([月火水木金土日])\s*曜日?")
# 時刻と長さ（日付ではない数字）。残りの点検の前に消す
_TIME_OR_LENGTH = re.compile(r"\d+\s*(?:時間|分間?|時(?:\s*\d+\s*分|\s*半)?)|\d{1,2}\s*:\s*\d{2}")
# 数えた言い方と時刻を消した残りに、数字・漢数字の日付・「週」・曜日の字を〒につなぐ形があれば
# AI の読んだ日付のまま（design.md §3-1 (2)）
_LEFTOVER = re.compile(
    r"\d|[一二三四五六七八九十百〇]+\s*[日月週年]|週|"
    r"[月火水木金土日][^一-鿿〓〒]{0,3}〒|〒[^一-鿿〓〒]{0,3}[月火水木金土日]"
)
# 数える言い方の前後に付いてよい字と語。ほかの語が付けば（「次の月曜」「月曜の次の日」「やのあさって」など）
# AI の読んだ日付のまま（design.md §3-1 (2)）
_BEFORE_OK = frozenset(" 、。,.!?「」『』()[]【】とはもでがをに〓〒")
# 後ろに「は・も・を・が・、」や空白が付くときは、その後ろが時刻（数字・午前・朝など）か文の終わりのときだけ。
# 「25日はクリスマス会」「月曜は避けて」「月曜 クリスマス会」のように別の語が続けば AI の読んだ日付のまま（design.md §3-1 (2)・§11-12）
_TIME_START = r"(?:$|\d|午前|午後|朝|昼|夕方|夜|終日)"
_AFTER_OK = re.compile(
    r"\s*(?:$|\d|[。.!?」』)\]】〓〒]|から|まで|ごろ|頃|中|午前|午後|朝|昼|夕方|夜|終日|[にで](?![はもを])|"
    r"(?:の|[はもをが、,])\s*" + _TIME_START + r")"
)
_RELATIVE = {"しあさって": 3, "あさって": 2, "明後日": 2, "明日": 1, "あした": 1, "今日": 0, "本日": 0}
_RELATIVE_RE = re.compile("|".join(sorted(_RELATIVE, key=len, reverse=True)))
_WEEK_SHIFT = {"今週": 0, "来週": 1, "再来週": 2}


def _month_day(today: date, month: int, day: int) -> date | None:
    try:
        target = date(today.year, month, day)
    except ValueError:
        return None
    if target < today:
        try:
            target = date(today.year + 1, month, day)
        except ValueError:
            return None
    return target


def _day_only(today: date, day: int) -> date | None:
    try:
        target = date(today.year, today.month, day)
    except ValueError:
        return None
    if target < today:
        year, month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        try:
            target = date(year, month, day)
        except ValueError:
            return None
    return target


def _weekday(today: date, week_word: str | None, weekday_char: str) -> date:
    wd = _WEEKDAYS.index(weekday_char)
    if week_word is None:
        ahead = (wd - today.weekday()) % 7 or 7
        return today + timedelta(days=ahead)
    monday = today - timedelta(days=today.weekday())
    return monday + timedelta(weeks=_WEEK_SHIFT[week_word], days=wd)


def _bounded(s: str, m: re.Match[str]) -> bool:
    """数える言い方 m の前後が、文の始め・終わり・空白・句読点・決まった助詞と時刻だけか。"""
    if m.start() > 0 and s[m.start() - 1] not in _BEFORE_OK and not s[m.start() - 1].isspace():
        return False
    if _STATE_AFTER.match(s, m.end()) and _BREAK_THEN_MORE.search(s, m.end()):
        return False
    return _AFTER_OK.match(s, m.end()) is not None


def _resolve(text: str, today: date) -> tuple[date, str | None] | None:
    """resolve_day の中身。(日付, 守りの種類) を返す。決まらなければ None。

    守りの種類: "day" は〇日だけの言い方、"weekday" は「来週」などの付かない〇曜だけの言い方、None は守りなし。
    """
    s = unicodedata.normalize("NFKC", text)
    if _OTHER_DATE_WORDS.search(s) or _DATE_MODIFIERS.search(s) or _CLAUSE_LINK.search(s):
        return None
    found: list[tuple[date | None, str | None]] = []
    for m in _MONTH_DAY.finditer(s):
        if not _bounded(s, m):
            return None
        found.append((_month_day(today, int(m.group(1)), int(m.group(2))), None))
    s = _MONTH_DAY.sub("〓", s)
    for m in _DAY_ONLY.finditer(s):
        # 〇日だけの言い方は文の頭にあるときだけ。前に語があれば（「クリスマスは25日」など）AI の読んだ日付のまま（design.md §3-2）
        if s[: m.start()].strip() or not _bounded(s, m):
            return None
        found.append((_day_only(today, int(m.group(1))), "day"))
    s = _DAY_ONLY.sub("〓", s)
    for m in _WEEKDAY.finditer(s):
        if not _bounded(s, m):
            return None
        guard = "weekday" if m.group(1) is None else None
        found.append((_weekday(today, m.group(1), m.group(2)), guard))
    s = _WEEKDAY.sub("〒", s)
    if _LEFTOVER.search(_TIME_OR_LENGTH.sub("", s)):
        return None
    for m in _RELATIVE_RE.finditer(s):
        if not _bounded(s, m):
            return None
        found.append((today + timedelta(days=_RELATIVE[m.group(0)]), None))
    if len(found) != 1:
        return None
    day, guard = found[0]
    if day is None:
        return None
    return day, guard


def resolve_day(text: str, today: date) -> date | None:
    """文の中の日付の言い方を決まりの表で日付にする。表に無い・2 つ以上・あり得ない日付なら None。"""
    resolved = _resolve(text, today)
    return None if resolved is None else resolved[0]


def _day_of(value: str | None) -> date | None:
    """時刻の文字の日付の部分（日本時間・時差の印なしのときだけ）。読めなければ None。"""
    if value is None or not re.match(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        parsed = parse_iso(value)
    except ValueError:
        return None
    if parsed.tzinfo is not None and parsed.utcoffset() != _JST_OFFSET:
        return None
    return parsed.date()


def same_day(a: str | None, b: str | None) -> bool:
    """両方の日付（日本時間・時差の印なしか +09:00）が読めて同じ日なら真。それ以外は偽。"""
    day_a, day_b = _day_of(a), _day_of(b)
    return day_a is not None and day_b is not None and day_a == day_b


def _with_day(value: str | None, day: date) -> str | None:
    """時刻の文字の日付の部分だけを day に替える（時刻・時差の印は文字のまま）。替えられなければ None。"""
    if _day_of(value) is None:
        return None
    assert value is not None
    return day.isoformat() + value[10:]


def _guard_ok(value: str | None, day: date, guard: str | None, today: date) -> bool:
    """AI の読んだ日付を替えてよいか（design.md §3-2）。

    〇日だけの言い方は、AI の読んだ日にちが同じときだけ（月を直すだけ）。
    「来週」などの付かない〇曜だけの言い方は、AI の読んだ日付が明日から 7 日のうち（決まりの数え方の範囲）のときだけ。
    範囲の外なら、AI は「クリスマスは金曜」のように別の言い方で日付を読んだとみて替えない。
    """
    if guard is None:
        return True
    old = _day_of(value)
    if old is None:
        return False
    if guard == "day":
        return old.day == day.day
    return today + timedelta(days=1) <= old <= today + timedelta(days=7)


def apply_day(ev: IntentEvent, text: str, today: date, karte: KarteIn | None) -> IntentEvent:
    """AI の答えの日付を、今の文の言い方から決まりの表で決めた日付に替える（design.md §3）。

    直前に終わりを聞いたなら終わりに、それ以外は始まりに当てる。始まりがカルテの値（この文で読んだものでない）なら替えない。
    始まりを替えたとき、終わりが元の始まりと同じ日なら終わりも同じ日に動かす。
    〇日だけの言い方と、「来週」などの付かない〇曜だけの言い方は、_guard_ok が通すときだけ替える。
    """
    resolved = _resolve(text, today)
    if resolved is None:
        return ev
    day, guard = resolved
    if karte is not None and karte.asked == "end":
        if not _guard_ok(ev.end, day, guard, today):
            return ev
        new_end = _with_day(ev.end, day)
        return ev if new_end is None else ev.model_copy(update={"end": new_end})
    if karte is not None and karte.start is not None and karte.asked != "start":
        return ev
    if not _guard_ok(ev.start, day, guard, today):
        return ev
    new_start = _with_day(ev.start, day)
    if new_start is None:
        return ev
    update: dict[str, object] = {"start": new_start}
    old_day = _day_of(ev.start)
    if old_day is not None and _day_of(ev.end) == old_day:
        update["end"] = _with_day(ev.end, day)
    return ev.model_copy(update=update)


# ---- 便W3: 午前・午後を言わない 1〜6時は午後（design §18-4 の 1） ----------------------------

# これが文にあれば午前・午後を言っている。何も変えない。英字の am・pm は前後が英字でないときだけ
_AMPM_WORDS = re.compile(
    r"午前|午後|朝|昼|夕方|夕|夜|晩|深夜|未明|早朝|明け方|ごぜん|ごご|a\.m\.|p\.m\.|(?<![a-z])(?:am|pm)(?![a-z])",
    re.IGNORECASE,
)
_BARE_HOUR = re.compile(r"(?<![0-9])([1-6])\s*時(?!間)")


def _shift_12h(value: str | None, hours: set[int]) -> str | None:
    """+09:00 の値で、時が hours に入っていれば 12 時間足した文字を返す。それ以外は None（触らない）。"""
    if value is None:
        return None
    try:
        dt = parse_iso(value)
    except (ValueError, TypeError):
        return None
    if dt.utcoffset() != _JST_OFFSET or dt.hour not in hours:
        return None
    return (dt + timedelta(hours=12)).isoformat(timespec="seconds")


def afternoon_hours(ev: IntentEvent, text: str, karte: KarteIn | None) -> IntentEvent:
    """午前・午後を言わない「1〜6時」を午後（13〜18時）にする。AI の答えの後・カルテと合わせる前に当てる。"""
    norm = unicodedata.normalize("NFKC", text)
    if _AMPM_WORDS.search(norm) or ev.is_all_day:
        return ev
    hours = {int(m) for m in _BARE_HOUR.findall(norm)}
    if not hours:
        return ev
    if karte is not None and karte.start is not None:
        try:
            ks = parse_iso(karte.start)
        except (ValueError, TypeError):
            ks = None
        if ks is not None:
            if ks.tzinfo is not None:
                ks = ks.astimezone(timezone(_JST_OFFSET))
            if 0 <= ks.hour <= 6:
                return ev
    new_start = _shift_12h(ev.start, hours)
    new_end = _shift_12h(ev.end, hours)
    update: dict[str, object] = {}
    if new_start is not None:
        update["start"] = new_start
        # 始まりを足したあと、終わりが +09:00 で新しい始まりより前なら終わりも足す
        if new_end is None and ev.end is not None:
            try:
                end_dt = parse_iso(ev.end)
            except (ValueError, TypeError):
                end_dt = None
            if end_dt is not None and end_dt.utcoffset() == _JST_OFFSET and end_dt < parse_iso(new_start):
                new_end = (end_dt + timedelta(hours=12)).isoformat(timespec="seconds")
    if new_end is not None:
        update["end"] = new_end
    return ev.model_copy(update=update) if update else ev
