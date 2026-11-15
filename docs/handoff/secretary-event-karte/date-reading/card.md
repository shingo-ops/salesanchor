# 実装の手順書 — 秘書チャット 予定の日付の読み方（card-secretary-date-reading）

- 設計: [design.md](design.md) ／ 目標: [kgi.md](kgi.md) ／ 現在地: [recon.md](recon.md) ／ 親: [../card.md](../card.md)
- 状態: 手順書（Opus 作成 2026-11-15）。PO 実装承認あり（2026-11-15 チャット、選択肢 1「このまま承認して、設計から本番まで進める」。design.md の「状態」）。
- ブランチ `release/secretary-date-reading-impl`。PR は作らない（Opus が作る）。危険 PR ではない（migrations・deploy.yml・本番 scripts を触らない）。
- 行番号と「前」の文面はすべて origin/main = 1eaefbf8c のもの。

## 読んだ節

- docs/handoff/design-partner-card-ops/guards/00-common.md ○
- docs/handoff/design-partner-card-ops/guards/03-file.md ○
- docs/handoff/design-partner-card-ops/guards/10-executor.md ○
- docs/handoff/design-partner-card-ops/guards/11-lint.md ○

## 受領確認

着手前に、報告の 1 行目へ「受領確認: card-secretary-date-reading を読んだ」と書く。

## この便で決めたこと

|決めたこと|理由・出典|
|---|---|
|日付の言い方は新しい部品 `backend/app/services/secretary_dates.py` で決まりの表どおりに日付にする|design.md §3-1・§5 案 A|
|替えるのは時刻の文字の先頭の日付だけ。時刻と時差の印は AI の読みのまま|design.md §3-2・kgi.md §2|
|「今」は `_now_jst()` で 1 回だけ作り、AI に渡す今と「今日」を同じにする|design.md §3-3|
|新しい画面の道で AI が予定で答えたときだけ通す。古い画面の道・`merge_karte`・`settle_dates`・`next_ask` は触らない|design.md §2・§3-3|
|既存の `test_assistant_karte.py` は「今」を 2026-11-01（日）に固定する 2 か所だけ足す。期待は変えない|design.md §7・§11（審査 1 回目の指摘 1）|

## やること（この順）

### 1. 準備

- (1a) `cd /Users/tanizawashingo/salesanchor 2>/dev/null || cd "$(git rev-parse --show-toplevel)"; git fetch origin main`
- (1b) `git branch --list release/secretary-date-reading-impl` の出力が空であること。空でなければ `BLOCKED: 同名のブランチがある` で止まる。
- (1c) `bash scripts/new-worktree.sh release/secretary-date-reading-impl`（`--claude` は付けない）
- (1d) `git worktree list` に `$HOME/worktrees/salesanchor/release-secretary-date-reading-impl` があること。以下この場所を `$REPO` と書く（`REPO="$HOME/worktrees/salesanchor/release-secretary-date-reading-impl"`）。以降のコマンドはすべて `cd "$REPO"` してから流す。
- (1e) `./scripts/dev/executor-preflight.sh`。クラウドでは [1/3]・[2/3] が FAIL でもよい。[3/3] と [4/4] は OK であること。OK でなければ `BLOCKED:` で止まる。
- (1f) 次の出力が空であること（空でなければ `NEEDS_DECISION: 1eaefbf8c から変わったファイル（一覧）` で止まる）:

```
git diff --stat 1eaefbf8c HEAD -- backend/app/routers/assistant.py backend/app/services/secretary_karte.py backend/app/schemas/assistant.py backend/tests/test_assistant_karte.py backend/tests/test_assistant_router.py
```

- (1g) `ls backend/app/services/secretary_dates.py backend/tests/test_secretary_dates.py` が 2 つとも「無い」こと。あれば `BLOCKED: 新しいファイルがもうある`。
- (1h) `mkdir -p /tmp/CC報告ファイル`

### 2. 編集のきまり

- 書き換えは 1 か所ずつ。「前」の文面がファイルの中にちょうど 1 回だけあることを確かめてから「後」に置き換える。0 回か 2 回以上なら `BLOCKED: 前が一致しない（ファイル名・節の番号）` で止まる。
- 書いていない行は触らない。新しいファイルは下の全文をそのまま置く。

### 3. 新しいファイル `backend/app/services/secretary_dates.py`（全文）

```python
"""秘書の「予定の日付の読み方」（date-reading/design.md）。「来週の月曜」などの日付を AI に任せず決まりの表で決める。

時刻は AI が読んだまま変えない。日付（YYYY-MM-DD の部分）だけを差し替える。
決まりの表に無い言い方・日付の言い方が 2 つ以上の文は None（AI の読んだ日付のまま）。
週は月曜から日曜まで（PO 2026-11-15）。
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta

from app.schemas.assistant import IntentEvent, KarteIn, parse_iso

_WEEKDAYS = "月火水木金土日"  # date.weekday() の 0〜6 と同じ並び
_JST_OFFSET = timedelta(hours=9)

# 表に無い日付の言い方。1 つでもあれば AI の読んだ日付のまま（design.md §3-1 (1)）
_OTHER_DATE_WORDS = re.compile(
    r"\d+\s*年|再来年|来年|今年|去年|昨年|月末|月初|週末|年末|年始|再来月|来月|今月|先月|翌日|翌週|前日|先週|一昨日|昨日|おととい|きのう|"
    r"毎|隔週|第\s*[\d一二三四五六七八九十]|\d+\s*日\s*(?:中|\d+\s*(?:回|時間)|あたり|当たり|おき|ごと)|\d+\s*日\s*に\s*(?:わた|渡|またが|跨|分け|分割|[\d一二三四五六七八九十]+\s*(?:回|度|件))|"
    r"(?:丸|まる)\s*\d+\s*日|\d+\s*日\s*の?\s*(?:延長|猶予|日程|遅れ|遅延|期間|休暇)|\d+\s*泊|\d+\s*(?:日|週間?|か月|ヶ月|カ月|ヵ月)\s*(?:後|前|間)"
)
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
    r"[月火水木金土日][^\u4e00-\u9fff〓〒]{0,3}〒|〒[^\u4e00-\u9fff〓〒]{0,3}[月火水木金土日]"
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


def _resolve(text: str, today: date) -> tuple[date, bool] | None:
    """resolve_day の中身。(日付, 〇日だけの言い方で決めたか) を返す。決まらなければ None。"""
    s = unicodedata.normalize("NFKC", text)
    if _OTHER_DATE_WORDS.search(s):
        return None
    found: list[tuple[date | None, bool]] = []
    for m in _MONTH_DAY.finditer(s):
        found.append((_month_day(today, int(m.group(1)), int(m.group(2))), False))
    s = _MONTH_DAY.sub("〓", s)
    for m in _DAY_ONLY.finditer(s):
        found.append((_day_only(today, int(m.group(1))), True))
    s = _DAY_ONLY.sub("〓", s)
    for m in _WEEKDAY.finditer(s):
        found.append((_weekday(today, m.group(1), m.group(2)), False))
    s = _WEEKDAY.sub("〒", s)
    if _LEFTOVER.search(_TIME_OR_LENGTH.sub("", s)):
        return None
    for m in _RELATIVE_RE.finditer(s):
        found.append((today + timedelta(days=_RELATIVE[m.group(0)]), False))
    if len(found) != 1:
        return None
    day, bare = found[0]
    if day is None:
        return None
    return day, bare


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


def _with_day(value: str | None, day: date) -> str | None:
    """時刻の文字の日付の部分だけを day に替える（時刻・時差の印は文字のまま）。替えられなければ None。"""
    if _day_of(value) is None:
        return None
    assert value is not None
    return day.isoformat() + value[10:]


def _same_date_number(value: str | None, day: date) -> bool:
    """AI の読んだ日付の「日にち」が day と同じか（〇日だけの言い方は、月だけを直す。design.md §3-2）。"""
    old = _day_of(value)
    return old is not None and old.day == day.day


def apply_day(ev: IntentEvent, text: str, today: date, karte: KarteIn | None) -> IntentEvent:
    """AI の答えの日付を、今の文の言い方から決まりの表で決めた日付に替える（design.md §3）。

    直前に終わりを聞いたなら終わりに、それ以外は始まりに当てる。始まりがカルテの値（この文で読んだものでない）なら替えない。
    始まりを替えたとき、終わりが元の始まりと同じ日なら終わりも同じ日に動かす。
    〇日だけの言い方は、AI の読んだ日付の日にちが同じときだけ替える（月を直すだけ）。
    """
    resolved = _resolve(text, today)
    if resolved is None:
        return ev
    day, bare = resolved
    if karte is not None and karte.asked == "end":
        if bare and not _same_date_number(ev.end, day):
            return ev
        new_end = _with_day(ev.end, day)
        return ev if new_end is None else ev.model_copy(update={"end": new_end})
    if karte is not None and karte.start is not None and karte.asked != "start":
        return ev
    if bare and not _same_date_number(ev.start, day):
        return ev
    new_start = _with_day(ev.start, day)
    if new_start is None:
        return ev
    update: dict[str, object] = {"start": new_start}
    old_day = _day_of(ev.start)
    if old_day is not None and _day_of(ev.end) == old_day:
        update["end"] = _with_day(ev.end, day)
    return ev.model_copy(update=update)
```

### 4. `backend/app/routers/assistant.py`

#### 4-1. :53 の import の次に 1 行足す

前:

```python
from app.services.secretary_karte import merge_karte, next_ask, settle_dates
```

後:

```python
from app.services.secretary_dates import apply_day
from app.services.secretary_karte import merge_karte, next_ask, settle_dates
```

#### 4-2. :175-182 の `_agent_payload` の頭を置き換える（`_now_jst` を足す）

前:

```python
def _agent_payload(text: str, model: str, rules: list[str], karte: KarteIn | None = None) -> bytes:
    """容器への頼みの本文（ADR-1077 便2b）。測ったバイト数と送るバイト数を同じにするため、ここで JSON にする。

    ADR-1078: カルテがあるときだけ日時の 3 欄と直前に聞いた欄を足す（題名・場所・メモは送らない。design.md §4-3「大きさ」）。
    カルテが無いときは今と 1 バイトも違わない。
    """
    now = datetime.now(_JST).isoformat(timespec="seconds")
    body: dict[str, object] = {"text": text, "now": now, "model": model, "rules": rules}
```

後:

```python
def _now_jst() -> datetime:
    """今の日本時間（date-reading/design.md §3-3。AI に渡す今と日付の決まりの「今日」を同じにする。試験で差し替える）。"""
    return datetime.now(_JST)


def _agent_payload(
    text: str, model: str, rules: list[str], karte: KarteIn | None = None, now: datetime | None = None
) -> bytes:
    """容器への頼みの本文（ADR-1077 便2b）。測ったバイト数と送るバイト数を同じにするため、ここで JSON にする。

    ADR-1078: カルテがあるときだけ日時の 3 欄と直前に聞いた欄を足す（題名・場所・メモは送らない。design.md §4-3「大きさ」）。
    カルテが無いときは今と 1 バイトも違わない。now を省くとその場の今を使う（送る形は同じ）。
    """
    now_text = (now or _now_jst()).isoformat(timespec="seconds")
    body: dict[str, object] = {"text": text, "now": now_text, "model": model, "rules": rules}
```

#### 4-3. :284 を置き換える

前:

```python
    payload = _agent_payload(body.text, assignment.model, rules, karte)
```

後:

```python
    now = _now_jst()
    payload = _agent_payload(body.text, assignment.model, rules, karte, now=now)
```

#### 4-4. :321-324 を置き換える（`settle_dates` の前に `apply_day` を通す）

前:

```python
            if final_kind == "event":
                assert final_ev is not None
                try:
                    final_ev = settle_dates(final_ev)
```

後:

```python
            if final_kind == "event":
                assert final_ev is not None
                if intent.kind == "event":
                    # date-reading: 今の文の日付の言い方を決まりの表で日付にする（AI の数えた日付の揺れを止める）
                    final_ev = apply_day(final_ev, body.text, now.date(), karte)
                try:
                    final_ev = settle_dates(final_ev)
```

### 5. 新しいファイル `backend/tests/test_secretary_dates.py`（全文）

```python
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
    ev = IntentEvent(title="歯医者", start="2026-11-27T10:00:00+09:00")
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
```

### 5b. 既存の試験 `backend/tests/test_assistant_karte.py`（「今」を固定するだけ。期待は変えない）

この試験の日付（:21-22 の `S`・`E` と :220 の金曜 11/6）は、今日を 2026-11-01（日）として書いてある。日付の決まりが入ると「明日」「金曜」が本当の今日で決まり、:151 の試験が落ちる。「今」を 2026-11-01 10:00 に固定する 2 か所だけを足す。

5b-1. :8-9 の import に 1 行足す

前:

```python
import json
from unittest.mock import AsyncMock
```

後:

```python
import json
from datetime import datetime
from unittest.mock import AsyncMock
```

5b-2. :68-71 の `meet` の後に「今」を固定する仕組みを足す

前:

```python
    return _set


# ---- next_ask（全部の分かれ道） -------------------------------------------------
```

後:

```python
    return _set


@pytest.fixture(autouse=True)
def _fixed_now(monkeypatch):
    # date-reading: S・E と「金曜」の日付は今日を 2026-11-01（日）として書いてある。
    # 日付の決まりが本当の今日に左右されないよう「今」を固定する（期待は変えない）
    monkeypatch.setattr(assistant, "_now_jst", lambda: datetime(2026, 11, 1, 10, 0, tzinfo=assistant._JST))


# ---- next_ask（全部の分かれ道） -------------------------------------------------
```

### 6. 確かめ（どれも生の出力を /tmp/CC報告ファイル/ に保存し、全文を読んでから判定する）

- (6a) `cd "$REPO/backend" && uv run --no-project --python 3.12 --with ruff ruff check app/ > /tmp/CC報告ファイル/ruff.txt 2>&1; echo "exit=$?"` → exit=0（CI と同じ範囲。`.github/workflows/test.yml:92`。試験のファイルは CI の ruff の対象外）
- (6b) `cd "$REPO/backend" && uv run --no-project --python 3.12 --with ruff ruff format --check app/services/secretary_dates.py > /tmp/CC報告ファイル/ruff-format.txt 2>&1; echo "exit=$?"` → exit=0。落ちたら `ruff format app/services/secretary_dates.py` で整え、整えた差分を報告に貼る（中身は変えない）。`app/routers/assistant.py` は元から整っていない行（:373-374）があるので format をかけない。
- (6c) `cd "$REPO/backend" && ENVIRONMENT=test uv run --no-project --python 3.12 --with-requirements requirements.txt --with-requirements requirements-dev.txt python -m pytest --no-cov tests/test_secretary_dates.py tests/test_assistant_router.py tests/test_assistant_karte.py tests/test_assistant_rules_router.py tests/test_assistant_karte_pg.py -q > /tmp/CC報告ファイル/pytest.txt 2>&1; echo "exit=$?"` → exit=0。最後の 1 行（passed・skipped の数）を報告に貼る。続けて同じ形で `tests/test_secretary_dates.py` だけを流し（保存先 `/tmp/CC報告ファイル/pytest-dates.txt`）、最後の 1 行を貼る（期待 412 passed）。
- (6d) `cd "$REPO" && git diff --check > /tmp/CC報告ファイル/diff-check.txt 2>&1; echo "exit=$?"` → exit=0
- (6e) `cd "$REPO" && git status --short` を報告に貼る。変わるのは `backend/app/routers/assistant.py`・`backend/tests/test_assistant_karte.py`（変更）と `backend/app/services/secretary_dates.py`・`backend/tests/test_secretary_dates.py`（新規）の 4 つだけ。
- (6a)〜(6c) が手順書の書き損じ（import の並び・未使用の名前・行の長さ）で落ちたら、その書き損じだけ直し、直した所を報告に書く。試験の期待の日付を変えないと通らないとき、または手順書と違う作りに変えないと通らないときは `NEEDS_DECISION:` で止まる（期待の日付は PO 承認の決まりの表なので変えない）。

### 7. 記録（commit）と送り出し（push）

- (7a) `git -C "$REPO" add backend/app/routers/assistant.py backend/app/services/secretary_dates.py backend/tests/test_secretary_dates.py backend/tests/test_assistant_karte.py`（`git add -A`・`git add .` は使わない）。
- (7b) commit の文:

```
fix(secretary): decide event dates like 来週の月曜 by a fixed table (ADR-1078 date-reading)

- new secretary_dates.resolve_day/apply_day: one table phrase per message sets the date, time kept as the AI read it
- week runs Monday to Sunday; unknown or multiple date phrases keep the AI's date
- the same "now" is sent to the AI and used as today; old screens (no karte key) unchanged

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
```

- (7c) `git -C "$REPO" log --oneline -1` を報告に貼る。
- (7d) `cd "$REPO" && bash scripts/dev/check-before-submit.sh > /tmp/CC報告ファイル/check-before-submit.txt 2>&1; echo "exit=$?"` → exit=0（落ちたら生の出力のパスを添えて `NEEDS_DECISION:`）
- (7e) `git -C "$REPO" push -u origin release/secretary-date-reading-impl`

## 触らない

- `backend/app/services/secretary_karte.py`（`merge_karte`・`settle_dates`・`next_ask`）・`backend/app/schemas/assistant.py`
- `backend/app/routers/assistant.py` の古い画面の道（:327 以降の `elif intent.kind == "event":`）と、4-1〜4-4 以外の行
- 既存の試験 `backend/tests/test_assistant_router.py`・`backend/tests/test_assistant_rules_router.py`・`backend/tests/test_assistant_karte_pg.py`。`backend/tests/test_assistant_karte.py` は 5b の 2 か所だけ（期待の値は変えない）
- 容器（`secretary-agent/`・`secretary-codex/`）・画面（`frontend/`）・`migrations/`・`.github/`・`deploy.yml`・本番の `scripts/`
- PR は作らない（Opus が作る）

## 想定される分かれ道

|起きたこと|すること|
|---|---|
|(1f) で 1eaefbf8c から変わったファイルがある|直さずに `NEEDS_DECISION:` で一覧を出す|
|「前」がちょうど 1 回一致しない|`BLOCKED:` でファイル名と節の番号を出す|
|`test_secretary_dates.py` の日付の試験が落ちる|期待を変えずに、落ちた試験の名前（引数つき）と生の出力のパスを添えて `NEEDS_DECISION:`|
|既存の試験（`test_assistant_router.py` など）が落ちる|直さずに、落ちた試験の名前と生の出力のパスを添えて `NEEDS_DECISION:`|
|5b を足しても `test_assistant_karte.py` の試験が落ちる|期待を変えずに、落ちた試験の名前と生の出力のパスを添えて `NEEDS_DECISION:`|
|`tests.test_assistant_karte` から `meet` を読み込むと fixture が見つからない|`NEEDS_DECISION:`（試験の置き場を Opus が決める）|
|PG の試験が skipped|続けてよい。報告に書く|
|push が見張りに止められる|言い換えずに止められた文面を貼って `BLOCKED:`|

## Opus が合流の前に確かめること（実装役はしない）

- 差分の全文をこの手順書の「後」と照合する。
- CI の結果（backend の試験・PG の試験が passed）。
- マージ前の審査役（reviewer・model opus）の判定。
- 本番反映の後: design.md §7 の D2（2 つの文を 5 回ずつ）・D3（T1〜T10）・D4（見本 69 件）・D5（予定の件数の前後）。

## 終わりの報告

- 1 行目: 「受領確認: card-secretary-date-reading を読んだ」
- 途中で停止するときも、ここまでの観測を書いてから下の BLOCKED: か NEEDS_DECISION: の行で終える（続きの作業はしない）。
- 最後の行は次のどれか 1 つ:
  - `DONE: release/secretary-date-reading-impl を push（commit の短い番号）`
  - `BLOCKED: 理由（生の出力のパス）`
  - `NEEDS_DECISION: 決めてほしいこと（生の出力のパス）`
- 間に: (1e)〜(1g) の結果・§6 の各 exit と最後の行・(6e) のファイルの数と `git log --oneline -1`。報告に書くのは観測した事実だけ（生の出力のパスを添える）。
- 1 つの発言は 600 文字以内。長いときは番号付きの発言に分ける。

END OF CARD
