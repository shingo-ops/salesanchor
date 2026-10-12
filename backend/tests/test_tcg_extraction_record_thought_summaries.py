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
