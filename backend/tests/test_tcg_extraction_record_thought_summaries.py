"""AttemptRecorder.on_response の思考要約（thought_summaries）の書き方。DB は使わない（SQL の引数を見る）。"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

from app.services import tcg_extraction_record_svc as records


def _recorder(monkeypatch) -> records.AttemptRecorder:
    recorder = records.AttemptRecorder(
        MagicMock(), job_id="job-1", source_id="source-1", reference={}, prompt_version="v1",
    )
    monkeypatch.setattr(recorder, "_owned", lambda required=True: True)
    return recorder


def _bound_thoughts(recorder: records.AttemptRecorder):
    statement, params = recorder.session.execute.call_args.args
    assert "thought_summaries=CAST(:thoughts AS jsonb)" in str(statement)
    return params["thoughts"]


def test_on_response_writes_thought_summaries_as_json_text(monkeypatch):
    recorder = _recorder(monkeypatch)

    recorder.on_response("response", thought_summaries=["考え1", "second"])

    assert json.loads(_bound_thoughts(recorder)) == ["考え1", "second"]
    assert "考え1" in _bound_thoughts(recorder)  # ensure_ascii=False
    assert recorder.response_saved is True


def test_on_response_writes_null_when_thought_summaries_is_none(monkeypatch):
    recorder = _recorder(monkeypatch)

    recorder.on_response("response", thought_summaries=None)

    assert _bound_thoughts(recorder) is None


def test_on_response_writes_null_when_called_without_thought_summaries(monkeypatch):
    recorder = _recorder(monkeypatch)

    recorder.on_response("response")

    assert _bound_thoughts(recorder) is None


def test_on_response_writes_null_when_thought_summaries_exceed_max_bytes(monkeypatch):
    recorder = _recorder(monkeypatch)
    monkeypatch.setattr(records, "MAX_BYTES", 100)

    recorder.on_response("ok", thought_summaries=["x" * 101])

    assert _bound_thoughts(recorder) is None
    assert recorder.response_saved is True


def test_on_response_keeps_thought_summaries_at_exactly_max_bytes(monkeypatch):
    recorder = _recorder(monkeypatch)
    body = json.dumps(["x" * 6], ensure_ascii=False)
    monkeypatch.setattr(records, "MAX_BYTES", len(body.encode("utf-8")))

    recorder.on_response("ok", thought_summaries=["x" * 6])

    assert json.loads(_bound_thoughts(recorder)) == ["x" * 6]


def test_on_response_strips_nul_characters_from_thoughts(monkeypatch):
    recorder = _recorder(monkeypatch)

    recorder.on_response("response", thought_summaries=["a\x00b", "c"])

    assert json.loads(_bound_thoughts(recorder)) == ["ab", "c"]
    assert "\\u0000" not in _bound_thoughts(recorder)
    assert recorder.response_saved is True


def test_on_response_replaces_lone_surrogate_and_still_updates(monkeypatch):
    recorder = _recorder(monkeypatch)

    recorder.on_response("response", thought_summaries=["x\ud800y"])

    thoughts = _bound_thoughts(recorder)
    assert thoughts is not None
    assert json.loads(thoughts)[0].startswith("x")
    assert recorder.response_saved is True


def test_on_response_drops_non_str_thought_items(monkeypatch):
    recorder = _recorder(monkeypatch)

    recorder.on_response("response", thought_summaries=["a", 1, None, {"k": "v"}, "b"])

    assert json.loads(_bound_thoughts(recorder)) == ["a", "b"]


def test_on_response_writes_null_thoughts_when_json_dumps_raises(monkeypatch):
    recorder = _recorder(monkeypatch)

    def boom(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(records.json, "dumps", boom)

    recorder.on_response("response", thought_summaries=["a"])

    assert _bound_thoughts(recorder) is None
    assert recorder.response_saved is True
