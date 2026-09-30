"""
ADR-1004: llm_usage_events 台帳への記録 — tcg_extraction_record_svc.AttemptRecorder。

複雑な所有権判定 (_owned) / トランザクション SQL は既存の *_pg.py テスト（実 Postgres、
CI-only）でカバー済み。ここでは「usage_counts の有無で record_usage_event_sync を
呼ぶ/呼ばない」という新規ロジックだけを、_owned と実 SQL 実行を monkeypatch した
軽量ユニットテストで検証する（DB 不要）。
"""
from __future__ import annotations

from unittest.mock import MagicMock

from app.services import tcg_extraction_record_svc as records
from app.services.llm_budget import UsageCounts


def _recorder(monkeypatch, *, owned: bool = True) -> records.AttemptRecorder:
    session = MagicMock()
    recorder = records.AttemptRecorder(
        session, job_id="job-1", source_id="source-1", reference={}, prompt_version="v1",
    )
    recorder._requested_model = "gemini-3.1-flash-lite"
    monkeypatch.setattr(recorder, "_owned", lambda required=True: owned)
    monkeypatch.setattr(recorder, "_parsed_size", lambda body: len(body))
    return recorder


class TestCompleteWritesLedgerOnlyWhenUsageKnown:
    def test_complete_writes_one_ledger_row_when_usage_counts_present(self, monkeypatch):
        recorder = _recorder(monkeypatch)
        counts = UsageCounts(prompt_tokens=1000, candidates_tokens=100, thoughts_tokens=50)
        recorder.on_response("response text", input_tokens=1000, output_tokens=150, usage_counts=counts)
        # complete() の UPDATE 自体は scalar_one() を呼ぶので MagicMock で吸収させる
        recorder.session.execute.return_value.scalar_one.return_value = recorder.id

        record_calls = []
        monkeypatch.setattr(
            records, "record_usage_event_sync",
            lambda session, **kwargs: record_calls.append(kwargs) or "usage-event-id",
        )

        recorder.complete(items=[{"a": 1}])

        assert len(record_calls) == 1
        assert record_calls[0]["purpose"] == "line_extraction"
        assert record_calls[0]["model"] == "gemini-3.1-flash-lite"
        assert record_calls[0]["sdk"] == "google-genai"
        assert record_calls[0]["extraction_attempt_id"] == recorder.id
        assert record_calls[0]["counts"] is counts

    def test_complete_writes_no_ledger_row_when_usage_counts_absent(self, monkeypatch):
        """on_response が usage_counts なしで呼ばれた場合（呼び出し元が渡さなかった等）は書かない。"""
        recorder = _recorder(monkeypatch)
        recorder.on_response("response text", input_tokens=0, output_tokens=0, usage_counts=None)
        recorder.session.execute.return_value.scalar_one.return_value = recorder.id

        record_calls = []
        monkeypatch.setattr(
            records, "record_usage_event_sync",
            lambda session, **kwargs: record_calls.append(kwargs) or "usage-event-id",
        )

        recorder.complete(items=[])

        assert record_calls == []


class TestFailWritesLedgerOnlyWhenResponseReceived:
    def test_fail_writes_ledger_row_when_usage_counts_present(self, monkeypatch):
        """応答は受け取れたがパース等で失敗したケース（usage は既知）。"""
        recorder = _recorder(monkeypatch)
        counts = UsageCounts(prompt_tokens=200, candidates_tokens=10)
        recorder.on_response("response text", input_tokens=200, output_tokens=10, usage_counts=counts)

        record_calls = []
        monkeypatch.setattr(
            records, "record_usage_event_sync",
            lambda session, **kwargs: record_calls.append(kwargs) or "usage-event-id",
        )

        recorder.fail("PARSED_TOO_LARGE")

        assert len(record_calls) == 1
        assert record_calls[0]["purpose"] == "line_extraction"
        assert record_calls[0]["extraction_attempt_id"] == recorder.id
        assert record_calls[0]["counts"] is counts

    def test_fail_writes_no_ledger_row_when_no_response_received(self, monkeypatch):
        """呼び出し自体が失敗（on_response 未呼び出し）→ usage 不明 → 行を作らない。"""
        recorder = _recorder(monkeypatch)

        record_calls = []
        monkeypatch.setattr(
            records, "record_usage_event_sync",
            lambda session, **kwargs: record_calls.append(kwargs) or "usage-event-id",
        )

        recorder.fail("API_ERROR")

        assert record_calls == []

    def test_fail_writes_no_ledger_row_when_not_owned(self, monkeypatch):
        """所有権を失っている（新しい子 attempt にフェンスされた）場合は何も書かない。"""
        recorder = _recorder(monkeypatch, owned=False)
        counts = UsageCounts(prompt_tokens=200, candidates_tokens=10)
        recorder.on_response("response text", input_tokens=200, output_tokens=10, usage_counts=counts)

        record_calls = []
        monkeypatch.setattr(
            records, "record_usage_event_sync",
            lambda session, **kwargs: record_calls.append(kwargs) or "usage-event-id",
        )

        recorder.fail("API_ERROR")

        assert record_calls == []
