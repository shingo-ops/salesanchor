"""ADR-1078: 秘書の「予定のカルテ」の試験（SQLite・容器は httpx をモック・can_add_meet は差し替え）。

design.md §9 の行ごとに 1 つ以上。next_ask の全部の分かれ道は関数を直接呼んで確かめる。
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import httpx
import pytest

from app.routers import assistant
from app.schemas.assistant import IntentEvent, KarteIn
from app.services.secretary_karte import merge_karte, next_ask, settle_dates
from tests.test_assistant_router import _fixture, _mock_agent, _respond
from tests.test_assistant_router import allowed as allowed  # noqa: F401

URL = "/api/v1/assistant/messages"
S = "2026-11-02T10:00:00+09:00"
E = "2026-11-02T11:00:00+09:00"


def _event(**fields) -> dict:
    ev = {
        "title": None,
        "start": None,
        "end": None,
        "is_all_day": False,
        "location": None,
        "description": None,
        "is_meeting": False,
        "add_meet": None,
    }
    ev.update(fields)
    return {"intent": {"kind": "event", "invoice": None, "event": ev, "reply": None}}


def _unknown() -> dict:
    return {"intent": {"kind": "unknown", "invoice": None, "event": None, "reply": "もう少し教えてください"}}


def _karte(**fields) -> dict:
    k = {
        "title": None,
        "start": None,
        "end": None,
        "is_all_day": False,
        "location": None,
        "description": None,
        "is_meeting": False,
        "add_meet": None,
        "asked": None,
        "asked_count": 0,
    }
    k.update(fields)
    return k


@pytest.fixture
def meet(monkeypatch):
    def _set(value: bool) -> AsyncMock:
        mock = AsyncMock(return_value=value)
        monkeypatch.setattr(assistant, "can_add_meet", mock)
        return mock

    return _set


# ---- next_ask（全部の分かれ道） -------------------------------------------------


def _ev(**fields) -> IntentEvent:
    return IntentEvent(**fields)


def test_next_ask_order_title_start_end():
    assert next_ask(_ev(), False, None, 0) == ("title", 1)
    assert next_ask(_ev(title="t"), False, None, 0) == ("start", 1)
    assert next_ask(_ev(title="t", start=S), False, None, 0) == ("end", 1)
    assert next_ask(_ev(title="t", start=S, end=E), False, None, 0) == (None, 0)


def test_next_ask_meet_needs_meeting_and_available_and_unset():
    full = {"title": "t", "start": S, "end": E}
    assert next_ask(_ev(**full, is_meeting=True), True, None, 0) == ("add_meet", 1)
    assert next_ask(_ev(**full, is_meeting=True), False, None, 0) == (None, 0)
    assert next_ask(_ev(**full, is_meeting=False), True, None, 0) == (None, 0)
    assert next_ask(_ev(**full, is_meeting=True, add_meet=False), True, None, 0) == (None, 0)
    assert next_ask(_ev(**full, is_meeting=True, add_meet=True), True, None, 0) == (None, 0)


def test_next_ask_same_field_counts_up_and_stops_after_two():
    assert next_ask(_ev(title="t", start=S), False, "end", 1) == ("end", 2)
    assert next_ask(_ev(title="t", start=S), False, "end", 2) == (None, 2)
    # 違う欄を聞いた後は 1 から数える
    assert next_ask(_ev(title="t", start=S), False, "start", 2) == ("end", 1)


def test_settle_dates_all_day_end_equals_start_and_end_before_start_is_cleared():
    assert settle_dates(_ev(title="t", start=S, is_all_day=True)).end == S
    assert settle_dates(_ev(title="t", start=S, end="2026-11-02T09:00:00+09:00")).end is None
    assert settle_dates(_ev(title="t", start=S)).end is None
    with pytest.raises(ValueError):
        settle_dates(_ev(title="t", start="あした"))


# ---- merge_karte -----------------------------------------------------------------


def test_merge_karte_keeps_filled_fields_when_ai_returns_null():
    k = KarteIn(title="打ち合わせ", start=S, asked="end", asked_count=1)
    merged = merge_karte(_ev(end=E), k)
    assert (merged.title, merged.start, merged.end) == ("打ち合わせ", S, E)


def test_merge_karte_asked_field_takes_ai_value():
    k = KarteIn(title="打ち合わせ", start=S, end="2026-11-02T10:30:00+09:00", asked="end", asked_count=1)
    assert merge_karte(_ev(end=E), k).end == E


def test_merge_karte_not_asked_field_keeps_karte_value():
    k = KarteIn(title="打ち合わせ", description="メモ", start=S, asked="end", asked_count=1)
    merged = merge_karte(_ev(title="別の名前", description="別のメモ", end=E), k)
    assert merged.title == "打ち合わせ"
    assert merged.description == "メモ"


def test_merge_karte_meeting_and_all_day_stay_true():
    k = KarteIn(title="会議", start=S, is_meeting=True, asked="end", asked_count=1)
    assert merge_karte(_ev(end=E, is_meeting=False), k).is_meeting is True
    k2 = KarteIn(title="展示会", start=S, is_all_day=True)
    assert merge_karte(_ev(), k2).is_all_day is True


def test_merge_karte_none_takes_all_karte_values():
    k = KarteIn(title="棚卸し", start=S, location="倉庫", asked="end", asked_count=1)
    merged = merge_karte(None, k)
    assert (merged.title, merged.start, merged.end, merged.location) == ("棚卸し", S, None, "倉庫")


# ---- 口の試験（新しい画面の道） -------------------------------------------------------


@pytest.mark.asyncio
async def test_first_message_with_null_karte_asks_end(allowed, monkeypatch, meet):
    meet(True)
    _mock_agent(monkeypatch, _respond(200, _event(title="打ち合わせ", start=S, is_meeting=True)))
    resp = await allowed.post(URL, json={"text": "明日の10時に打ち合わせを入れて", "karte": None})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["kind"] == "event"
    d = data["draft"]
    assert (d["title"], d["start"], d["end"]) == ("打ち合わせ", S, None)
    assert (d["ask"], d["ask_count"], d["meet_available"], d["is_meeting"]) == ("end", 1, True, True)


@pytest.mark.asyncio
async def test_meet_asked_only_when_available(allowed, monkeypatch, meet):
    karte = _karte(title="打ち合わせ", start=S, is_meeting=True, asked="end", asked_count=1)
    meet(True)
    _mock_agent(monkeypatch, _respond(200, _event(end=E, is_meeting=True)))
    d = (await allowed.post(URL, json={"text": "11時に終わる", "karte": karte})).json()["draft"]
    assert (d["ask"], d["ask_count"]) == ("add_meet", 1)
    meet(False)
    _mock_agent(monkeypatch, _respond(200, _event(end=E, is_meeting=True, add_meet=True)))
    d = (await allowed.post(URL, json={"text": "11時に終わる", "karte": karte})).json()["draft"]
    assert (d["ask"], d["meet_available"], d["add_meet"]) == (None, False, None)


@pytest.mark.asyncio
async def test_meet_yes_reaches_final_draft(allowed, monkeypatch, meet):
    meet(True)
    karte = _karte(title="打ち合わせ", start=S, end=E, is_meeting=True, asked="add_meet", asked_count=1)
    _mock_agent(monkeypatch, _respond(200, _event(add_meet=True)))
    d = (await allowed.post(URL, json={"text": "はい", "karte": karte})).json()["draft"]
    assert (d["ask"], d["add_meet"], d["title"], d["start"], d["end"]) == (None, True, "打ち合わせ", S, E)


@pytest.mark.asyncio
async def test_unknown_mid_karte_stays_event_and_asks_same_field(allowed, monkeypatch, meet):
    meet(False)
    _mock_agent(monkeypatch, _respond(200, _unknown()))
    karte = _karte(title="棚卸し", start=S, asked="end", asked_count=1)
    data = (await allowed.post(URL, json={"text": "うーん", "karte": karte})).json()
    assert data["kind"] == "event"
    assert (data["draft"]["ask"], data["draft"]["ask_count"], data["draft"]["title"]) == ("end", 2, "棚卸し")
    karte["asked_count"] = 2
    data = (await allowed.post(URL, json={"text": "わからない", "karte": karte})).json()
    assert data["kind"] == "event"
    assert (data["draft"]["ask"], data["draft"]["end"]) == (None, None)


@pytest.mark.asyncio
async def test_unknown_on_first_message_stays_unknown(allowed, monkeypatch, meet):
    meet(False)
    _mock_agent(monkeypatch, _respond(200, _unknown()))
    data = (await allowed.post(URL, json={"text": "次からは丁寧に", "karte": None})).json()
    assert data["kind"] == "unknown"
    assert data["draft"] == {"reply": "もう少し教えてください"}


@pytest.mark.asyncio
async def test_null_start_on_new_path_is_200_and_asks_start(allowed, monkeypatch, meet):
    meet(False)
    _mock_agent(monkeypatch, _respond(200, _event(title="面談")))
    resp = await allowed.post(URL, json={"text": "面談を入れたい", "karte": None})
    assert resp.status_code == 200, resp.text
    assert resp.json()["draft"]["ask"] == "start"


@pytest.mark.asyncio
async def test_end_before_start_is_cleared_and_asked(allowed, monkeypatch, meet):
    meet(False)
    _mock_agent(monkeypatch, _respond(200, _event(title="仕入れ", start="2026-11-06T14:00:00+09:00", end="2026-11-06T12:00:00+09:00")))
    d = (await allowed.post(URL, json={"text": "金曜の14時から12時まで仕入れ", "karte": None})).json()["draft"]
    assert (d["end"], d["ask"]) == (None, "end")


@pytest.mark.asyncio
async def test_unreadable_start_on_new_path_is_502(allowed, monkeypatch, meet):
    meet(False)
    _mock_agent(monkeypatch, _respond(200, _event(title="t", start="あした")))
    resp = await allowed.post(URL, json={"text": "a", "karte": None})
    assert resp.status_code == 502
    assert resp.json()["detail"] == {"code": "unreadable"}


@pytest.mark.asyncio
async def test_old_container_answer_without_new_fields_passes(allowed, monkeypatch, meet):
    meet(False)
    _mock_agent(monkeypatch, _respond(200, _fixture("envelope-event.json")))
    resp = await allowed.post(URL, json={"text": "予定", "karte": None})
    assert resp.status_code == 200, resp.text
    d = resp.json()["draft"]
    assert (d["is_meeting"], d["add_meet"], d["ask"]) == (False, None, "end")


# ---- 口の試験（古い画面の道 = karte の鍵なし） ------------------------------------------


@pytest.mark.asyncio
async def test_old_path_null_start_is_502_and_ledger_failed(allowed, monkeypatch):
    _mock_agent(monkeypatch, _respond(200, _event(title="面談")))
    resp = await allowed.post(URL, json={"text": "面談"})
    assert resp.status_code == 502
    assert resp.json()["detail"] == {"code": "unreadable"}
    kwargs = assistant.record_usage_isolated.await_args.kwargs
    assert kwargs["outcome"] == "failed"


@pytest.mark.asyncio
async def test_old_path_does_not_read_meet_and_keeps_plus_one_hour(allowed, monkeypatch, meet):
    mock = meet(True)
    _mock_agent(monkeypatch, _respond(200, _fixture("envelope-event.json")))
    resp = await allowed.post(URL, json={"text": "予定"})
    assert resp.status_code == 200, resp.text
    d = resp.json()["draft"]
    assert d["end"] == "2026-11-02T16:00:00+09:00"
    assert (d["ask"], d["ask_count"], d["add_meet"], d["meet_available"]) == (None, 0, None, False)
    assert mock.await_count == 0


# ---- 入口の守りと送る量 --------------------------------------------------------------


@pytest.mark.asyncio
async def test_karte_start_over_40_chars_is_422(allowed):
    resp = await allowed.post(URL, json={"text": "a", "karte": _karte(start="2026-11-02T10:00:00.123456789012345678+09:00")})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_karte_unreadable_start_and_extra_field_and_count_are_422(allowed):
    for bad in (_karte(start="あした"), {**_karte(), "extra": 1}, _karte(asked_count=3), _karte(asked="location")):
        resp = await allowed.post(URL, json={"text": "a", "karte": bad})
        assert resp.status_code == 422, bad


@pytest.mark.asyncio
async def test_payload_sends_only_dates_and_asked(allowed, monkeypatch, meet):
    meet(False)
    sent: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        return httpx.Response(200, json=_event(end=E))

    _mock_agent(monkeypatch, handler)
    karte = _karte(title="ひみつの題名", location="ひみつの場所", start=S, asked="end", asked_count=1)
    await allowed.post(URL, json={"text": "11時", "karte": karte})
    assert sent["karte"] == {"start": S, "end": None, "is_all_day": False}
    assert sent["asked"] == "end"
    assert "ひみつ" not in json.dumps(sent, ensure_ascii=False)


@pytest.mark.asyncio
async def test_payload_without_karte_is_unchanged(allowed, monkeypatch):
    sent: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        return httpx.Response(200, json=_unknown())

    _mock_agent(monkeypatch, handler)
    await allowed.post(URL, json={"text": "a"})
    assert set(sent) == {"text", "now", "model", "rules"}


def test_payload_at_max_size_is_within_limit():
    karte = KarteIn(
        title="あ" * 1000,
        location="あ" * 1000,
        description="あ" * 1000,
        start="2026-11-02T10:00:00.123456+09:00",
        end="2026-11-02T11:00:00.123456+09:00",
        is_all_day=True,
        asked="add_meet",
        asked_count=2,
    )
    payload = assistant._agent_payload("あ" * 1000, "sonnet", ["あ" * 150] * 20, karte)
    assert len(payload) <= assistant.AGENT_BODY_MAX_BYTES, len(payload)
