"""秘書の「予定の日付の読み方」の試験（date-reading/design.md §7。D1）。

期待の日付は、本体と違う数え方（月曜どうしの差・1 日ずつ進める）で出す。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta

import httpx
import pytest

from app.routers import assistant
from app.schemas.assistant import IntentEvent, KarteIn
from app.services.secretary_dates import apply_day, resolve_day
from tests.test_assistant_karte import _event, _karte
from tests.test_assistant_karte import meet as meet  # noqa: F401
from tests.test_assistant_router import _mock_agent
from tests.test_assistant_router import allowed as allowed  # noqa: F401

URL = "/api/v1/assistant/messages"
WEEKDAYS = "月火水木金土日"
# 2026-11-16（月）〜 2026-11-22（日）を「今日」にする 7 日
TODAYS = [date(2026, 11, 16) + timedelta(days=i) for i in range(7)]


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _expected_week(today: date, shift: int, wd: int) -> date:
    for i in range(-7, 22):
        c = today + timedelta(days=i)
        if (_monday(c) - _monday(today)).days == 7 * shift and c.weekday() == wd:
            return c
    raise AssertionError("見つからない")


def _expected_bare(today: date, wd: int) -> date:
    for i in range(1, 8):
        c = today + timedelta(days=i)
        if c.weekday() == wd:
            return c
    raise AssertionError("見つからない")


# ---- D1: 表の言い方 × 7 曜日 ------------------------------------------------------

RELATIVE = [("今日", 0), ("本日", 0), ("明日", 1), ("あした", 1), ("あさって", 2), ("明後日", 2), ("しあさって", 3)]


@pytest.mark.parametrize("today", TODAYS)
@pytest.mark.parametrize(("word", "days"), RELATIVE)
def test_relative_words(today, word, days):
    assert resolve_day(f"{word}の13時から会議", today) == today + timedelta(days=days)


@pytest.mark.parametrize("today", TODAYS)
@pytest.mark.parametrize("wd", range(7))
@pytest.mark.parametrize(("prefix", "shift"), [("今週の", 0), ("来週の", 1), ("再来週の", 2), ("来週", 1)])
def test_week_words(today, wd, prefix, shift):
    assert resolve_day(f"{prefix}{WEEKDAYS[wd]}曜 13 時から会議", today) == _expected_week(today, shift, wd)


@pytest.mark.parametrize("today", TODAYS)
@pytest.mark.parametrize("wd", range(7))
def test_bare_weekday_is_nearest_from_tomorrow(today, wd):
    assert resolve_day(f"{WEEKDAYS[wd]}曜日の10時", today) == _expected_bare(today, wd)


@pytest.mark.parametrize(
    ("text", "today", "expected"),
    [
        # kgi.md §2 の表の例（日曜 11/15・水曜 11/18）
        ("来週の月曜 13 時から会議", date(2026, 11, 15), date(2026, 11, 16)),
        ("来週の月曜 13 時から会議", date(2026, 11, 18), date(2026, 11, 23)),
        ("来週の月曜 13 時に佐藤さんと電話の予定", date(2026, 11, 15), date(2026, 11, 16)),
        ("今週の月曜", date(2026, 11, 15), date(2026, 11, 9)),
        ("今週の金曜", date(2026, 11, 18), date(2026, 11, 20)),
        ("再来週の月曜", date(2026, 11, 15), date(2026, 11, 23)),
        ("再来週の月曜", date(2026, 11, 18), date(2026, 11, 30)),
        ("金曜", date(2026, 11, 15), date(2026, 11, 20)),
        ("日曜", date(2026, 11, 15), date(2026, 11, 22)),
        # 〇月〇日・〇日だけ（来年・来月・年の終わりの繰り越し・全角）
        ("11 月 25 日は終日 展示会に出る予定を入れて", date(2026, 11, 15), date(2026, 11, 25)),
        ("１１月２５日", date(2026, 11, 15), date(2026, 11, 25)),
        ("11月15日", date(2026, 11, 15), date(2026, 11, 15)),
        ("11月10日", date(2026, 11, 15), date(2027, 11, 10)),
        ("25日", date(2026, 11, 15), date(2026, 11, 25)),
        ("10日", date(2026, 11, 18), date(2026, 12, 10)),
        ("10日", date(2026, 12, 20), date(2027, 1, 10)),
        ("25日 10時から", date(2026, 11, 15), date(2026, 11, 25)),
        ("25日に会議", date(2026, 11, 15), date(2026, 11, 25)),
        ("25日に10時から会議", date(2026, 11, 15), date(2026, 11, 25)),
        # 試しの会話の文
        ("明日の10時に打ち合わせを入れて", date(2026, 11, 15), date(2026, 11, 16)),
        ("あさって 9 時、北風商会の山田さんと商談。1 時間", date(2026, 11, 15), date(2026, 11, 17)),
        ("今日の 17 時半から在庫の棚卸し 2 時間", date(2026, 11, 15), date(2026, 11, 15)),
        ("金曜の 14 時から 12 時まで 仕入れ", date(2026, 11, 15), date(2026, 11, 20)),
        # 時刻・長さの数字と「〇曜日」の「日」は残りの点検に当てない（design.md §3-1 (2)）
        ("来週の月曜 13時30分から1時間", date(2026, 11, 15), date(2026, 11, 16)),
        ("来週の月曜 13:00から会議", date(2026, 11, 15), date(2026, 11, 16)),
        ("来週月曜日の午後2時", date(2026, 11, 15), date(2026, 11, 16)),
        ("水曜日に北風商会と商談", date(2026, 11, 15), date(2026, 11, 18)),
        ("明日 10 時から棚卸し", date(2026, 11, 15), date(2026, 11, 16)),  # 前後が空白・助詞・時刻なら数える
        ("金曜 10 時", date(2026, 11, 15), date(2026, 11, 20)),
        ("会議は明日の朝", date(2026, 11, 15), date(2026, 11, 16)),
        ("明後日の午後3時", date(2026, 11, 15), date(2026, 11, 17)),  # 「午後」「明後日」の「後」は言い直しの語に当てない
        ("明日の午前10時", date(2026, 11, 15), date(2026, 11, 16)),
        # その日の様子を言う形でも、続きの句が無ければ数える（design.md §3-1 (1b)・§11-14）
        ("明日は朝10時から会議", date(2026, 11, 15), date(2026, 11, 16)),
        ("明日は終日 展示会", date(2026, 11, 15), date(2026, 11, 16)),
    ],
)
def test_table_examples(text, today, expected):
    assert resolve_day(text, today) == expected


@pytest.mark.parametrize(
    "text",
    [
        "金曜から月曜まで",  # 2 つ
        "明日と明後日",  # 2 つ
        "月末に",
        "週末",
        "来月の5日",
        "3日後",
        "明日から3日間",
        "2027年1月5日",
        "来年の11月25日",  # 年の言い方は表に無い
        "再来年の1月5日",
        "1日中研修",  # 「1 日中」は日付ではない
        "明日、25日中に提出",  # 「〇日中」があれば表の言い方があっても替えない
        "第1日曜",  # 「第〇」は表に無い
        "1日1回",  # 回数・長さの「〇日」
        "1日2時間",
        "3日おき",
        "第一日曜",  # 漢数字の「第〇」
        "25日 2時間の打ち合わせ",  # 長さの「〇日〇時間」に見えるので替えない（design.md §6）
        "来週月曜 第2会議室",  # 部屋の名前の「第〇」でも替えない（design.md §6）
        "研修1日目 10時から",  # 日数の「〇日」（後ろが日付の続き方でない。design.md §3-1 (2)）
        "3日分の資料を準備 10時から",
        "1日がかりの作業 9時から",
        "3日連続の研修 10時から",
        "5日以内に返事",
        "2日程度の作業",
        "5日ぶりの面談 14時",
        "2日で終わる作業 10時",
        "1日休み 9時から",
        "10日(火)",  # 括弧の曜日は日付と照合しないので替えない（design.md §6）
        "2泊3日の出張",  # 「〇泊」は表に無い
        "5日に1回",  # 回数の「〇日に〇回」
        "3日に四回 打ち合わせ",
        "1日に3件の訪問 10時から",
        "3日にわたる研修 10時から",  # 日数の「〇日にわたる」「〇日に分ける」
        "2日にわたって展示会 9時から",
        "研修を3日に分けて 10時から",
        "丸1日の研修 9時から",  # 「丸〇日」「まる〇日」
        "まる2日の作業 9時から",
        "2日の延長 14時から",  # 期間の「〇日の延長」など
        "5日の猶予で 10時に返事",
        "3日の日程で研修 10時から",
        "25日水曜 10時から",  # 〇日に曜日を足した形は、残りの「〇日」で替えない（design.md §3-1 (2)）
        "25日(水曜)10時",
        "25日（水曜）10時",
        "3日(木曜) 10時から",
        "12/3 木曜 10時から",  # 「/」「-」の日付の形
        "2026-12-03 木曜 10時",
        "12月 月曜 10時",  # 月だけの言い方
        "土日曜の展示会 10時から",  # 曜日を並べる形
        "月・水・金曜の10時から研修",
        "月〜金曜 9時から研修",
        "月~金曜 9時から",
        "月-金曜 9時",
        "月から金曜まで研修 9時",  # 曜日を「から・と・か・や・/」でつなぐ形
        "月と水曜の10時",
        "月/水/金曜 10時",
        "月、水と金曜",
        "月か火曜",
        "金曜日と土曜日",
        "12.3 木曜 10時",  # 「.」「・」「_」でつないだ日付（残りに数字）
        "12・3 木曜",
        "12_3 木曜",
        "二十五日（水曜）10時",  # 漢数字の日付
        "来々週の月曜 10時",  # 表に無い週の言い方（残りに「週」）
        "先々週の月曜",
        "一週間後の月曜",
        "二週間後の金曜",
        "来週の月曜 3名で会議",  # 時刻・長さでない数字が残れば替えない（design.md §6）
        "次の次の月曜 10時",  # 数えた言い方の前後に表に無い語が付く形（design.md §3-1 (2)）
        "その次の月曜 10時",
        "月曜の次の日に会議",
        "金曜の次の日 10時",
        "来週の月曜の次の日",
        "明日の次の日",
        "11月25日の次の日",
        "年明けの月曜 10時",
        "年明け最初の月曜 10時に会議",
        "正月明けの月曜 10時",
        "連休明けの火曜 10時",
        "年度末の金曜 15時",
        "年内最後の金曜",
        "翌月上旬の月曜 10時",
        "上旬の金曜",
        "はつかの金曜",
        "ついたちの月曜",
        "やのあさって",
        "今度の月曜",
        "次回の月曜",
        "明日以降",
        # 離れた所の言い直しの語・打ち消しの語（design.md §3-1 (2)）
        "年明けは月曜 10時から仕事始め",
        "連休明けは火曜 10時から会議",
        "祝日明け、火曜 10時",
        "年度末は金曜 15時から棚卸し",
        "次の次は月曜 10時",
        "上旬、金曜 10時",
        "とおか、木曜 10時",
        "みそか、木曜",
        "月曜、次の日に会議",
        "金曜、その翌々日",
        "月曜ではなく",
        "明日を除く",
        "月曜じゃなくて火曜",
        "明日以外",
        "来週の月曜の前日",
        "月曜は都合が悪いので別の日で",
        "月曜は別日で",
        "月曜はだめ、ほかの日の10時",  # 打ち消し・言い替えの語（だめ・ほか・つぎ など）
        "月曜、つぎの日 10時から会議",
        "月曜は無理",
        "クリスマスは25日 19時からパーティー",  # 〇日だけの言い方の前に語がある（design.md §3-2）
        "仕事納めは28日 17時から納会",
        "新年会は8日 18時から",
        "打ち合わせは25日 10時",
        "明日は朝から出張なので、今夜20時に打ち合わせ",
        "明日は朝が早いので今晩21時から電話",
        "明日は朝から出張なので今から30分打ち合わせ",
        "明日は終日外出なので、これから1時間電話",
        "あさっては朝から研修なので今晩20時",
        "今日は夜まで外出なので明朝9時から会議",
        "本日は終日不在のため明朝10時に電話",
        "11月25日は終日不在なので今夜20時に会議",
        "来週の月曜は朝から出張なので今夜20時",
        "今週の金曜は朝から出張なので今夜20時",
        "今日は夜まで仕事なので、明晩19時から食事",
        "月曜は朝から外出なので今朝のうちに電話",
        "明日は終日外出なので当日の連絡は不要、今度の金曜10時",
        # 審査 14 回目 §11-14: 理由や前置きの句の後ろに一覧に無い日付の言葉が続く
        "今日は終日外出なので、あす10時に会議",
        "今日は夜まで外出です。あす10時に会議",
        "今日は夜まで外出だから、あす10時に会議",
        "明日は朝から出張で、このあと30分打ち合わせ",
        "明日は終日外出なので、あとで電話",
        "明日は朝から出張だから、すぐ電話",
        "明日は朝から出張。このあと30分打ち合わせ",
        "明日は朝から出張です。あとで電話ください",
        "明日は朝から出張なので、クリスマスに会議",
        "今日は夜まで外出なので、あくる日の朝9時",
        "明日は朝から出張 このあと30分打ち合わせ",
        "明日は終日外出、いまから電話",
        "明日は10時に出社なので、すぐ電話",
        "明日は朝から出張。北風商会へ電話",
        "今日は夜まで外出。みょうにち10時に会議",
        "25日はクリスマス会 19時から",  # 言い方の後ろの「は・も・を・が・、」・空白に、時刻でない語が続く（design.md §3-1 (2)）
        "28日は仕事納め、17時から納会",
        "8日は新年会 18時から",
        "24日はクリスマスイブ 18時から食事",
        "月曜は避けて10時から会議",
        "月曜はNGなので",
        "月曜はむり、10時で",
        "月曜は難しいので",
        "月曜はやめて",
        "月曜はキャンセルで",
        "来週の月曜は避けて10時から",
        "明日はNGで10時から",
        "月曜を避けて10時",
        "月曜 クリスマス会 10時",
        "11月31日",  # あり得ない日付
        "2月30日",
        "31日",  # 11 月 31 日は無い（今日 11/15）
        "面談を入れたい",
        "11時に終わる",
        "14時",
        "はい",
    ],
)
def test_not_in_table_is_none(text):
    assert resolve_day(text, date(2026, 11, 15)) is None


# ---- apply_day ---------------------------------------------------------------

SUN = date(2026, 11, 15)


def test_apply_moves_start_and_same_day_end():
    ev = IntentEvent(start="2026-11-17T13:00:00+09:00", end="2026-11-17T14:00:00+09:00")
    out = apply_day(ev, "来週の月曜 13 時から会議", SUN, None)
    assert (out.start, out.end) == ("2026-11-16T13:00:00+09:00", "2026-11-16T14:00:00+09:00")


def test_apply_keeps_end_on_other_day():
    ev = IntentEvent(start="2026-11-17T13:00:00+09:00", end="2026-11-18T14:00:00+09:00")
    out = apply_day(ev, "来週の月曜", SUN, None)
    assert (out.start, out.end) == ("2026-11-16T13:00:00+09:00", "2026-11-18T14:00:00+09:00")


def test_apply_after_asking_end_moves_only_end():
    ev = IntentEvent(start="2026-11-16T13:00:00+09:00", end="2026-11-24T14:00:00+09:00")
    karte = KarteIn(start="2026-11-16T13:00:00+09:00", asked="end", asked_count=1)
    out = apply_day(ev, "来週の月曜の14時まで", SUN, karte)
    assert (out.start, out.end) == ("2026-11-16T13:00:00+09:00", "2026-11-16T14:00:00+09:00")


def test_apply_keeps_start_from_karte():
    ev = IntentEvent(start="2026-11-17T13:00:00+09:00")
    karte = KarteIn(start="2026-11-17T13:00:00+09:00", asked="title", asked_count=1)
    assert apply_day(ev, "来週の月曜会", SUN, karte).start == "2026-11-17T13:00:00+09:00"


def test_apply_after_asking_start_moves_start():
    ev = IntentEvent(title="歯医者", start="2026-11-21T10:00:00+09:00")
    karte = KarteIn(title="歯医者", asked="start", asked_count=1)
    assert apply_day(ev, "金曜 10 時", SUN, karte).start == "2026-11-20T10:00:00+09:00"


@pytest.mark.parametrize("start", [None, "あした", "2026-11-17T04:00:00Z", "2026-11-17T13:00:00"])
def test_apply_leaves_empty_unreadable_and_non_jst(start):
    # 時差の印の無い時刻は日本時間として扱い替える（settle_dates がその後で今までどおり検査する）
    ev = IntentEvent(start=start)
    out = apply_day(ev, "来週の月曜", SUN, None)
    if start == "2026-11-17T13:00:00":
        assert out.start == "2026-11-16T13:00:00"
    else:
        assert out.start == start


def test_apply_bare_day_fixes_month_only():
    # 〇日だけの言い方は、AI の読んだ日にちが同じなら月を直す（design.md §3-2）
    ev = IntentEvent(start="2026-12-25T10:00:00+09:00")
    assert apply_day(ev, "25日 10時から", SUN, None).start == "2026-11-25T10:00:00+09:00"


def test_apply_bare_day_with_other_number_keeps_start():
    # AI の読んだ日にちが違えば、日数の言い方かもしれないので替えない（design.md §3-2・§6）
    ev = IntentEvent(start="2026-11-15T10:00:00+09:00")
    assert apply_day(ev, "打ち合わせ1日、10時から", SUN, None) == ev


def test_apply_bare_day_with_other_number_keeps_end():
    ev = IntentEvent(start="2026-11-16T13:00:00+09:00", end="2026-11-16T14:00:00+09:00")
    karte = KarteIn(start="2026-11-16T13:00:00+09:00", asked="end", asked_count=1)
    assert apply_day(ev, "1日、14時まで", SUN, karte) == ev


def test_apply_modifier_word_keeps_start():
    # 離れた所に言い直しの語があれば、AI の読んだ日付のまま（design.md §3-1 (2)）
    ev = IntentEvent(start="2027-01-04T10:00:00+09:00")
    assert apply_day(ev, "年明けは月曜 10時から仕事始め", SUN, None) == ev


@pytest.mark.parametrize(
    ("text", "start"),
    [
        ("クリスマスは金曜 19時からパーティー", "2026-12-25T19:00:00+09:00"),
        ("仕事納めは月曜 17時から納会", "2026-12-28T17:00:00+09:00"),
        ("新年は金曜 10時から初詣", "2027-01-01T10:00:00+09:00"),
        ("一か月先、月曜 10時", "2026-12-14T10:00:00+09:00"),
        ("金曜 10 時", "2026-11-27T10:00:00+09:00"),
    ],
)
def test_apply_bare_weekday_far_keeps_start(text, start):
    # 「来週」などの付かない〇曜は、AI の読んだ日付が明日から 7 日のうちのときだけ替える（design.md §3-2）
    ev = IntentEvent(start=start)
    assert apply_day(ev, text, SUN, None) == ev


def test_apply_bare_weekday_far_keeps_end():
    ev = IntentEvent(start="2026-11-16T13:00:00+09:00", end="2026-11-24T14:00:00+09:00")
    karte = KarteIn(start="2026-11-16T13:00:00+09:00", asked="end", asked_count=1)
    assert apply_day(ev, "火曜の14時まで", SUN, karte) == ev


def test_apply_day_after_words_keeps_ai_date():
    # 〇日だけの言い方は文の頭にあるときだけ替える（design.md §3-2）
    ev = IntentEvent(start="2026-12-25T19:00:00+09:00", end=None)
    assert apply_day(ev, "クリスマスは25日 19時からパーティー", SUN, None) == ev
    ev = IntentEvent(start="2026-11-16T13:00:00+09:00", end="2026-12-28T17:00:00+09:00")
    karte = KarteIn(start="2026-11-16T13:00:00+09:00", asked="end", asked_count=1)
    assert apply_day(ev, "仕事納めは28日 17時まで", SUN, karte) == ev
    assert apply_day(ev, "28日は仕事納めなので17時まで", SUN, karte) == ev


def test_apply_without_date_words_changes_nothing():
    ev = IntentEvent(start="2026-11-17T13:00:00+09:00", end="2026-11-17T14:00:00+09:00")
    assert apply_day(ev, "13 時から会議", SUN, None) == ev


# ---- 窓口を通す（「今」を日曜 11/15 14:00 に固定） ----------------------------------

NOW = datetime(2026, 11, 15, 14, 0, 0, tzinfo=assistant._JST)


@pytest.fixture
def sunday(monkeypatch):
    monkeypatch.setattr(assistant, "_now_jst", lambda: NOW)


@pytest.mark.asyncio
async def test_new_path_uses_table_date_and_same_now(allowed, monkeypatch, meet, sunday):
    meet(False)
    sent: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        ai = _event(title="会議", start="2026-11-17T13:00:00+09:00", end="2026-11-17T14:00:00+09:00")
        return httpx.Response(200, json=ai)

    _mock_agent(monkeypatch, handler)
    resp = await allowed.post(URL, json={"text": "来週の月曜 13 時から会議", "karte": None})
    assert resp.status_code == 200, resp.text
    d = resp.json()["draft"]
    assert d["start"].startswith("2026-11-16T13:00:00")
    assert d["end"].startswith("2026-11-16T14:00:00")
    assert sent["now"] == "2026-11-15T14:00:00+09:00"


@pytest.mark.asyncio
async def test_new_path_after_asking_end(allowed, monkeypatch, meet, sunday):
    meet(False)
    ai = _event(end="2026-11-24T14:00:00+09:00")
    _mock_agent(monkeypatch, lambda request: httpx.Response(200, json=ai))
    karte = _karte(title="会議", start="2026-11-16T13:00:00+09:00", asked="end", asked_count=1)
    resp = await allowed.post(URL, json={"text": "来週の月曜の14時まで", "karte": karte})
    assert resp.status_code == 200, resp.text
    d = resp.json()["draft"]
    assert d["start"].startswith("2026-11-16T13:00:00")
    assert d["end"].startswith("2026-11-16T14:00:00")


@pytest.mark.asyncio
async def test_old_path_keeps_ai_date(allowed, monkeypatch, sunday):
    ai = _event(title="会議", start="2026-11-17T13:00:00+09:00", end="2026-11-17T14:00:00+09:00")
    _mock_agent(monkeypatch, lambda request: httpx.Response(200, json=ai))
    resp = await allowed.post(URL, json={"text": "来週の月曜 13 時から会議"})
    assert resp.status_code == 200, resp.text
    assert "2026-11-17" in json.dumps(resp.json(), ensure_ascii=False)
    assert "2026-11-16" not in json.dumps(resp.json(), ensure_ascii=False)
