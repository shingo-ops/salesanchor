"""v102 の書き写しを直す API（便C1）の PostgreSQL を使わない試験。原文・応答はすべて架空。

C-K2 の入口（本文の形の検査）、404 / 409 / source_message_id 不一致、行の数え方、並びの計画。
PostgreSQL を使う試験（C-K1・422 で何も書かない・一覧と詳細）は test_v102_transcription_pg.py。
"""
from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import app.routers.tcg_v102_posts as router  # noqa: E402
import app.services.v102_transcription_svc as svc  # noqa: E402
from app.services.line_analysis_v102_svc import V102_PROMPT_VERSION_PREFIX  # noqa: E402

SOURCE = "bbbbbbbb-0000-0000-0000-0000000000c1"
JOB = "aaaaaaaa-0000-0000-0000-0000000000c1"


def _item(**over) -> dict:
    return {"id": None, "source_lines": [1, 2], "raw_price": "1,000円", "raw_quantity": "3", **over}


def _job(**over) -> svc.PostJob:
    base = {
        "job_id": JOB, "source_message_id": SOURCE, "prompt_version": f"{V102_PROMPT_VERSION_PREFIX}x", "review_reasons": None,
        "gemini_unsure": None, "raw_text": "a\nb\nc", "line_posted_at": None, "provider": "不明",
    }
    return svc.PostJob(**{**base, **over})


# --- 本文の形の検査（C-K2 の入口。422 になり、DB には届かない） ------------------------------------------


@pytest.mark.parametrize(
    "item",
    [
        _item(source_lines=[]),
        _item(source_lines=[1, 1]),
        _item(source_lines=["1"]),
        _item(source_lines=[1.5]),
        _item(source_lines=[True]),
        _item(source_lines=None),
        _item(raw_price="x" * 201),
        _item(raw_quantity="x" * 201),
        _item(id="not-a-uuid"),
        {**_item(), "unknown": 1},
    ],
    ids=["empty", "duplicate", "str", "float", "bool", "null", "price_201", "quantity_201", "bad_id", "extra_field"],
)
def test_request_rejects_malformed_item(item):
    with pytest.raises(ValidationError):
        router.SaveItemsRequest(source_message_id=SOURCE, items=[item])


def test_request_rejects_empty_items_and_duplicate_ids():
    with pytest.raises(ValidationError):
        router.SaveItemsRequest(source_message_id=SOURCE, items=[])
    same = str(uuid4())
    with pytest.raises(ValidationError):
        router.SaveItemsRequest(source_message_id=SOURCE, items=[_item(id=same), _item(id=same)])


def test_request_accepts_200_chars_and_null_values():
    body = router.SaveItemsRequest(source_message_id=SOURCE, items=[_item(raw_price="x" * 200, raw_quantity=None)])
    assert body.items[0].raw_price == "x" * 200 and body.items[0].raw_quantity is None


# --- サービスの検査（行番号の範囲・id） -----------------------------------------------------------------


def _input(lines: list[int], item_id: str | None = None) -> svc.ItemInput:
    return svc.ItemInput(id=item_id, source_lines=lines, raw_price=None, raw_quantity=None)


@pytest.mark.parametrize("lines", [[0], [4], [1, 99], [-1]], ids=["zero", "over", "one_over", "negative"])
def test_validate_rejects_line_numbers_outside_the_raw_text(lines):
    with pytest.raises(svc.InvalidTranscription):
        svc._validate([_input(lines)], 3, set())


def test_validate_rejects_foreign_and_duplicated_ids():
    mine = str(uuid4())
    with pytest.raises(svc.InvalidTranscription):
        svc._validate([_input([1], str(uuid4()))], 3, {mine})
    with pytest.raises(svc.InvalidTranscription):
        svc._validate([_input([1], mine), _input([2], mine)], 3, {mine})
    svc._validate([_input([1, 3], mine), _input([2])], 3, {mine})  # 正しい形は通る


# --- 行の数え方は Gemini に渡す側(raw_text.split) と同じ ---------------------------------------------------


@pytest.mark.parametrize("raw", ["", "a", "a\nb", "a\n\nb\n", "\n\n"], ids=["empty", "one", "two", "blank_and_trailing", "only_breaks"])
def test_split_raw_lines_counts_like_the_gemini_side(raw):
    lines = svc.split_raw_lines(raw)
    assert [line["number"] for line in lines] == list(range(1, len(raw.split("\n")) + 1))
    assert "\n".join(line["text"] for line in lines) == raw


# --- 並びの計画 ---------------------------------------------------------------------------------------------


def test_plan_order_sorts_by_min_line_then_existing_before_new_then_original_index():
    a, b = str(uuid4()), str(uuid4())
    existing = {a: SimpleNamespace(gemini_index=0), b: SimpleNamespace(gemini_index=1)}
    ordered = svc._plan_order([_input([5], a), _input([2], None), _input([2], b), _input([2], None)], existing)
    ids = [item_id for _item_in, item_id in ordered]
    assert ids[0] == b and ids[1] != ids[2] and ids[3] == a  # 行 2 の既存(b) → 行 2 の新しい 2 件(body の順) → 行 5(a)
    assert [item.source_lines[0] for item, _ in ordered] == [2, 2, 2, 5]


# --- ルーター: 404 / 409 / 不一致 / 変更なし ---------------------------------------------------------------


@pytest.fixture
def env(monkeypatch):
    state = SimpleNamespace(job=_job(), enqueued=[], result=svc.EditResult(True, ["x"]), applied=0)

    async def load_job(_db, _job_id):
        if isinstance(state.job, Exception):
            raise state.job
        return state.job

    async def apply(_db, _job, _items, _by):
        state.applied += 1
        return state.result

    monkeypatch.setattr(router.svc, "load_job", load_job)
    monkeypatch.setattr(router.svc, "apply_transcription_edit", apply)
    monkeypatch.setattr(router, "enqueue_v102_reanalyze", lambda job_id: state.enqueued.append(job_id))
    return state


def _put(source: str = SOURCE):
    body = router.SaveItemsRequest(source_message_id=source, items=[_item()])
    user = SimpleNamespace(email="admin@example.com")
    return asyncio.run(router.save_v102_post_items(JOB, body, db=MagicMock(), current_user=user))


def test_put_missing_post_is_404(env):
    env.job = svc.PostNotFound(JOB)
    with pytest.raises(HTTPException) as caught:
        _put()
    assert caught.value.status_code == 404 and env.applied == 0


def test_put_v6_post_is_409(env):
    env.job = svc.PostNotV102(JOB)
    with pytest.raises(HTTPException) as caught:
        _put()
    assert caught.value.status_code == 409 and env.applied == 0 and env.enqueued == []


def test_put_source_message_mismatch_is_422_and_does_not_reach_the_service(env):
    with pytest.raises(HTTPException) as caught:
        _put(str(uuid4()))
    assert caught.value.status_code == 422 and env.applied == 0 and env.enqueued == []


def test_put_invalid_content_is_422(env, monkeypatch):
    async def invalid(*_a):
        raise svc.InvalidTranscription("items[0].source_lines out of range")

    monkeypatch.setattr(router.svc, "apply_transcription_edit", invalid)
    with pytest.raises(HTTPException) as caught:
        _put()
    assert caught.value.status_code == 422 and env.enqueued == []


def test_put_changed_enqueues_once_and_unchanged_does_not(env):
    out = _put()
    assert (out.changed, out.enqueued, env.enqueued) == (True, True, [JOB])
    env.enqueued.clear()
    env.result = svc.EditResult(False, ["x"])
    out = _put()
    assert (out.changed, out.enqueued, env.enqueued) == (False, False, [])


def test_get_detail_v6_post_is_409_and_missing_is_404(env):
    for error, status in ((svc.PostNotV102(JOB), 409), (svc.PostNotFound(JOB), 404)):
        env.job = error
        with pytest.raises(HTTPException) as caught:
            asyncio.run(router._load_job_or_http_error(MagicMock(), JOB))
        assert caught.value.status_code == status


@pytest.mark.asyncio
@pytest.mark.parametrize(("method", "path"), [("get", "/api/v1/tcg/v102/posts"), ("get", f"/api/v1/tcg/v102/posts/{JOB}"), ("put", f"/api/v1/tcg/v102/posts/{JOB}/items")])
async def test_endpoints_require_authentication(method, path):
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path, json={} if method == "put" else None)
    assert response.status_code in (401, 403)


# --- 保存は最初に D1 と同じ advisory lock を取る ----------------------------------------------------------


class RecordingDb:
    """execute に渡された SQL と引数を記録する。件の読み出しには rows を返す。"""

    def __init__(self, rows: list) -> None:
        self.rows, self.calls, self.rollbacks, self.commits = rows, [], 0, 0

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        return SimpleNamespace(fetchall=lambda: self.rows)

    async def rollback(self):
        self.rollbacks += 1

    async def commit(self):
        self.commits += 1


def test_apply_takes_the_system_stage_lock_first_and_writes_nothing_when_unchanged():
    item_id = str(uuid4())
    row = SimpleNamespace(id=item_id, gemini_index=0, source_lines=[1, 2], raw_price="1", raw_quantity="2", review_reasons=None)
    db = RecordingDb([row])
    unchanged = svc.ItemInput(id=item_id, source_lines=[1, 2], raw_price="1", raw_quantity="2")
    result = asyncio.run(svc.apply_transcription_edit(db, _job(), [unchanged], "admin@example.com"))
    assert result == svc.EditResult(False, [item_id])
    assert "pg_advisory_xact_lock" in db.calls[0][0] and db.calls[0][1] == {"key": f"v102_analysis:{JOB}"}
    assert len(db.calls) == 2 and db.rollbacks == 1 and db.commits == 0  # 鍵と読み出しだけ。書き込みなし


def test_apply_invalid_rolls_back_without_writing():
    db = RecordingDb([])
    with pytest.raises(svc.InvalidTranscription):
        asyncio.run(svc.apply_transcription_edit(db, _job(), [_input([9])], "admin@example.com"))
    assert len(db.calls) == 2 and db.rollbacks == 1 and db.commits == 0
