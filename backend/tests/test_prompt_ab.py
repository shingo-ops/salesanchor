"""prompt_ab（Gemini v7/v8 比較試験の道具）の単体試験。

設計: docs/handoff/gemini-v8/design.md §6
"""
from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import app.tools.prompt_ab as pab
from app.services import llm_budget
from app.tasks import tcg_extraction as task
from tests.test_tcg_work_matching_integration import pg as pg_fixture

pg = pg_fixture  # 共有 fixture（本物の migration 済み DB。CI 専用）

_CTX = task.ExtractionContext(
    raw_text="a\nb", supplier_context={"extraction_price_format": "円"},
    knowledge_links=[{"category": "block_delimiter", "pattern": "■", "normalized_to": None}],
    supplier_id=7,
)
_COUNTS = llm_budget.UsageCounts(prompt_tokens=10, candidates_tokens=5, thoughts_tokens=1, total_tokens=16)


def _v8_result():
    return {
        "response_text": '{"items": []}', "thought_summaries": ["t"],
        "usage_raw": {"prompt_token_count": 10}, "usage_counts": _COUNTS,
    }


@pytest.fixture
def fakes(monkeypatch, tmp_path):
    """Gemini・DB・台帳をすべて差し替える。"""
    m = SimpleNamespace(
        v8=MagicMock(side_effect=lambda *a, **k: _v8_result()),
        v7=MagicMock(side_effect=lambda *a, **k: {"response_text": "H|x", "usage_counts": _COUNTS,
                                                  "input_tokens": 10, "output_tokens": 6}),
        parse7=MagicMock(return_value=([{"raw_product_name": "p"}], [])),
        record=MagicMock(return_value="evt"),
        out=tmp_path,
    )
    monkeypatch.setattr(pab, "call_gemini_raw_copy_v8", m.v8)
    monkeypatch.setattr(pab, "call_gemini_raw_copy", m.v7)
    monkeypatch.setattr(pab, "parse_raw_copy_response", m.parse7)
    monkeypatch.setattr(pab, "record_usage_event_sync", m.record)
    monkeypatch.setattr(pab, "load_extraction_context", MagicMock(return_value=_CTX))
    monkeypatch.setattr(pab, "fetch_job_ids", lambda s, ids: {i: f"job-{i}" for i in ids})
    monkeypatch.setattr(pab, "load_v8_prompt", lambda: "PROMPT")
    monkeypatch.setattr(pab, "check_sdk_capabilities", lambda: (True, "ok"))
    return m


def _totals(costs, *, null_rows=0, missing=False):
    it = iter(costs)

    def fake(session, source_ref):
        calls = m_calls["n"]
        return pab.LedgerTotals(rows=0 if missing else calls, null_cost_rows=null_rows, cost_usd=next(it))

    return fake


m_calls = {"n": 0}


def _raise(exc):
    def fn(*a, **k):
        raise exc

    return fn


def _run(fakes, monkeypatch, *, costs=None, run_ids=("r1", "r2", "r3"), config="v8", repeat=1,
         max_cost="1.0", dry_run=False, null_rows=0, missing=False, v8_error=None, **over):
    m_calls["n"] = 0
    orig = fakes.v8.side_effect if v8_error is None else _raise(v8_error)
    orig7 = fakes.v7.side_effect

    def count_v8(*a, **k):
        m_calls["n"] += 1
        return orig(*a, **k)

    def count_v7(*a, **k):
        m_calls["n"] += 1
        return orig7(*a, **k)

    fakes.v8.side_effect, fakes.v7.side_effect = count_v8, count_v7
    monkeypatch.setattr(
        pab, "fetch_ledger_totals",
        _totals(costs or [Decimal("0.01")] * 50, null_rows=null_rows, missing=missing),
    )
    kw = dict(
        run_ids=list(run_ids), config=config, repeat=repeat, max_cost_usd=Decimal(max_cost),
        test_id="T", out_dir=fakes.out, dry_run=dry_run, thinking_level="LOW",
        include_thoughts=True, use_schema=True, temperature=None,
    )
    kw.update(over)
    return pab.run_ab(MagicMock(), **kw)


def _lines(fakes):
    path = fakes.out / "T.jsonl"
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def test_stops_when_cumulative_cost_exceeds_limit(monkeypatch, fakes):
    summary = _run(fakes, monkeypatch, costs=[Decimal("0.4"), Decimal("0.9"), Decimal("1.2")], max_cost="1.0")
    assert summary.stop_reason == "cost_limit"
    assert summary.calls == 3  # 3回目で超えたのでそこで止まる（4回目はない）
    assert fakes.v8.call_count == 3


def test_stops_when_cost_is_null(monkeypatch, fakes):
    summary = _run(fakes, monkeypatch, null_rows=1)
    assert summary.stop_reason == "cost_null"
    assert fakes.v8.call_count == 1


def test_stops_when_ledger_row_is_missing(monkeypatch, fakes):
    summary = _run(fakes, monkeypatch, missing=True)
    assert summary.stop_reason == "ledger_missing"
    assert fakes.v8.call_count == 1


def test_stops_after_first_gemini_failure_and_records_the_failure(monkeypatch, fakes):
    summary = _run(fakes, monkeypatch, v8_error=RuntimeError("Gemini API 呼び出し失敗: x"))
    assert summary.stop_reason == "job_failed"
    assert summary.failed == 1
    assert fakes.v8.call_count == 1
    assert fakes.record.call_count == 0
    assert "Gemini" in _lines(fakes)[0]["error"]


def test_stops_on_unexpected_exception(monkeypatch, fakes):
    pab.load_extraction_context.side_effect = Exception("db down")
    summary = _run(fakes, monkeypatch)
    assert summary.stop_reason == "job_failed"
    assert fakes.v8.call_count == 0


def test_non_gemini_exception_text_is_sanitized_before_jsonl(monkeypatch, fakes):
    pab.load_extraction_context.side_effect = Exception("db error url?key=SECRETVALUE123&x=1")
    _run(fakes, monkeypatch)
    written = (fakes.out / "T.jsonl").read_text(encoding="utf-8")
    assert "SECRETVALUE123" not in written
    assert "APIキー省略" in written


def test_parse_exception_text_is_sanitized_before_jsonl(monkeypatch, fakes):
    fakes.parse7.side_effect = ValueError("bad header key=SECRETVALUE456")
    _run(fakes, monkeypatch, config="v7", run_ids=("r1",))
    written = (fakes.out / "T.jsonl").read_text(encoding="utf-8")
    assert "SECRETVALUE456" not in written


def test_stops_when_job_not_found(monkeypatch, fakes):
    pab.load_extraction_context.return_value = None
    summary = _run(fakes, monkeypatch)
    assert summary.stop_reason == "job_failed"


def test_stops_when_run_id_unknown(monkeypatch, fakes):
    monkeypatch.setattr(pab, "fetch_job_ids", lambda s, ids: {})
    summary = _run(fakes, monkeypatch)
    assert summary.stop_reason == "run_not_found"
    assert fakes.v8.call_count == 0


def test_dry_run_never_calls_gemini_nor_ledger(monkeypatch, fakes, capsys):
    summary = _run(fakes, monkeypatch, dry_run=True)
    assert summary.dry_run is True and summary.target_count == 3
    assert fakes.v8.call_count == 0 and fakes.v7.call_count == 0
    assert fakes.record.call_count == 0
    out = capsys.readouterr().out
    assert "target_count=3" in out
    assert "PROMPT" in out and "[L0001] a" in out
    assert len([ln for ln in out.split("\n") if ln.strip()]) <= 40


def test_v7_config_calls_existing_functions_unchanged(monkeypatch, fakes):
    summary = _run(fakes, monkeypatch, config="v7", run_ids=("r1",))
    assert summary.succeeded == 1
    fakes.v7.assert_called_once_with(
        "a\nb", supplier_context=_CTX.supplier_context, knowledge_links=_CTX.knowledge_links
    )
    fakes.parse7.assert_called_once_with("H|x", "a\nb")
    assert fakes.v8.call_count == 0


def test_v8_config_passes_options_and_keep_chars_source(monkeypatch, fakes):
    _run(fakes, monkeypatch, run_ids=("r1",), thinking_level="HIGH", include_thoughts=False,
         use_schema=False, temperature=0.3)
    kw = fakes.v8.call_args.kwargs
    assert fakes.v8.call_args.args == ("a\nb",)
    assert kw["prompt_text"] == "PROMPT"
    assert kw["thinking_level"] == "HIGH" and kw["include_thoughts"] is False
    assert kw["use_schema"] is False and kw["temperature"] == 0.3
    assert kw["knowledge_links"] == _CTX.knowledge_links


def test_repeat_runs_each_run_id_n_times_and_writes_one_jsonl_line_each(monkeypatch, fakes):
    summary = _run(fakes, monkeypatch, run_ids=("r1", "r2"), repeat=2)
    assert summary.succeeded == 4
    rows = _lines(fakes)
    assert [(r["run_id"], r["repeat"]) for r in rows] == [("r1", 1), ("r1", 2), ("r2", 1), ("r2", 2)]
    first = rows[0]
    for key in ("job_id", "config", "response_text", "thought_summaries", "usage_raw",
                "item_count", "errors", "elapsed_sec"):
        assert key in first
    assert first["job_id"] == "job-r1" and first["config"] == "v8"


def test_ledger_row_is_written_per_call_with_source_ref_and_committed(monkeypatch, fakes):
    session = MagicMock()
    monkeypatch.setattr(
        pab, "fetch_ledger_totals",
        lambda s, ref: pab.LedgerTotals(rows=fakes.v8.call_count, null_cost_rows=0, cost_usd=Decimal("0.01")),
    )
    pab.run_ab(
        session, run_ids=["r1", "r2"], config="v8", repeat=1, max_cost_usd=Decimal("1"),
        test_id="T9", out_dir=fakes.out, dry_run=False, thinking_level=None,
        include_thoughts=True, use_schema=True, temperature=None,
    )
    assert fakes.record.call_count == 2
    kw = fakes.record.call_args.kwargs
    assert kw["purpose"] == "line_extraction_shadow"
    assert kw["source_ref"] == "prompt_ab:T9"
    assert kw["sdk"] == "google-genai"
    assert kw["counts"] == _COUNTS
    assert session.commit.call_count == 2


def test_parse_failure_is_recorded_not_fatal(monkeypatch, fakes):
    fakes.parse7.side_effect = ValueError("header mismatch")
    summary = _run(fakes, monkeypatch, config="v7", run_ids=("r1", "r2"))
    assert summary.succeeded == 2 and summary.stop_reason is None
    assert "header mismatch" in json.dumps(_lines(fakes)[0]["errors"], ensure_ascii=False)


def test_job_context_is_loaded_once_per_job_across_repeats(monkeypatch, fakes):
    _run(fakes, monkeypatch, run_ids=("r1",), repeat=3)
    assert pab.load_extraction_context.call_count == 1


# --- 起動時の確認・引数 --------------------------------------------------------


def test_capability_check_passes_with_installed_sdk():
    ok, msg = pab.check_sdk_capabilities()
    assert ok is True, msg


def test_capability_check_reports_version_when_missing(monkeypatch):
    monkeypatch.setattr(
        pab, "_sdk_field_names",
        lambda: ({"response_json_schema", "thinking_config"}, {"include_thoughts"}),
    )
    ok, msg = pab.check_sdk_capabilities()
    assert ok is False
    assert "thinking_level" in msg and "google-genai" in msg


def test_main_exits_without_calling_gemini_when_capability_missing(monkeypatch, fakes, tmp_path, capsys):
    monkeypatch.setattr(pab, "check_sdk_capabilities", lambda: (False, "google-genai 0.0.1: thinking_level なし"))
    runs = tmp_path / "runs.txt"
    runs.write_text("r1\n", encoding="utf-8")
    monkeypatch.setattr(pab, "_get_sync_session", lambda: MagicMock())
    rc = pab.main(["--runs-file", str(runs), "--config", "v8", "--repeat", "1", "--max-cost-usd", "1",
                   "--test-id", "T", "--out-dir", str(tmp_path / "o")])
    assert rc == 2
    assert fakes.v8.call_count == 0
    assert "0.0.1" in capsys.readouterr().out


def test_parse_args_defaults_and_options(tmp_path):
    args = pab.parse_args([
        "--runs-file", "f", "--config", "v8", "--thinking-level", "low", "--no-thoughts", "--no-schema",
        "--temperature", "0.7", "--repeat", "2", "--max-cost-usd", "3", "--test-id", "X", "--out-dir", "/o",
    ])
    assert args.thinking_level == "LOW" and args.no_thoughts and args.no_schema
    assert args.temperature == 0.7 and args.repeat == 2 and args.max_cost_usd == Decimal("3")


def test_parse_args_rejects_v8_options_for_v7():
    with pytest.raises(SystemExit):
        pab.parse_args(["--runs-file", "f", "--config", "v7", "--thinking-level", "low", "--repeat", "1",
                        "--max-cost-usd", "1", "--test-id", "X", "--out-dir", "/o"])


def test_read_run_ids_ignores_blank_and_comment_lines(tmp_path):
    f = tmp_path / "r.txt"
    f.write_text("a\n\n# c\n b \n", encoding="utf-8")
    assert pab.read_run_ids(f) == ["a", "b"]


# --- 実 PG：台帳を source_ref で合計できる --------------------------------------


def test_ledger_totals_sum_by_source_ref_on_real_postgres(pg):
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    _conn, engine, _url = pg
    with Session(engine) as s:
        for ref, n in (("prompt_ab:T1", 2), ("prompt_ab:OTHER", 1)):
            for _ in range(n):
                llm_budget.record_usage_event_sync(
                    s, purpose="line_extraction_shadow", model="gemini-3.1-flash-lite",
                    sdk="google-genai", counts=_COUNTS, source_ref=ref,
                )
        s.commit()
        totals = pab.fetch_ledger_totals(s, "prompt_ab:T1")
        # 台帳の cost_usd は NUMERIC(12,6)。1行ぶんの費用 0.0000115 は保存時に 0.000012 に丸められる。
        # 合計は「保存された行の合計」なので、期待値は保存された各行から求める（手書きの定数にしない）。
        stored = [
            Decimal(str(r[0]))
            for r in s.execute(
                text("SELECT cost_usd FROM public.llm_usage_events WHERE source_ref = :r"), {"r": "prompt_ab:T1"}
            ).fetchall()
        ]
        per_row = llm_budget.calculate_usage_cost(_COUNTS, "gemini-3.1-flash-lite")
        assert len(stored) == 2
        assert all(v == per_row.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP) for v in stored)
        assert totals.rows == 2
        assert totals.null_cost_rows == 0
        assert totals.cost_usd == sum(stored)
        assert pab.fetch_ledger_totals(s, "prompt_ab:NONE").rows == 0
