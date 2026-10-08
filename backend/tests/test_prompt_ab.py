"""prompt_ab（Gemini v7/v8 比較試験の道具）の単体試験。

設計: docs/handoff/gemini-v8/design.md §6
"""
from __future__ import annotations

import hashlib
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
         max_cost="1.0", dry_run=False, null_rows=0, missing=False, v8_error=None, session=None, **over):
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
    if session is None:  # v102 の既定は DB の key raw_copy_v101_f_c を読むので、行がある偽 session を渡す
        session = _db_session("DEFAULT_F_C_FROM_DB") if config == "v102" else MagicMock()
    return pab.run_ab(session, **kw)


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


# --- v9 ---------------------------------------------------------------------


def test_v9_config_passes_v9_schema_and_prompt(monkeypatch, fakes):
    from app.services.gemini_raw_copy_v9 import V9_RESPONSE_SCHEMA

    monkeypatch.setattr(pab, "load_v9_prompt", lambda: "PROMPT9")
    _run(fakes, monkeypatch, config="v9", run_ids=("r1",))
    kwargs = fakes.v8.call_args.kwargs
    assert kwargs["response_schema"] is V9_RESPONSE_SCHEMA
    assert kwargs["prompt_text"] == "PROMPT9"


def test_v8_config_does_not_pass_response_schema(monkeypatch, fakes):
    _run(fakes, monkeypatch, config="v8", run_ids=("r1",))
    assert "response_schema" not in fakes.v8.call_args.kwargs


def test_v9_dry_run_never_calls_gemini_nor_ledger(monkeypatch, fakes, capsys):
    monkeypatch.setattr(pab, "load_v9_prompt", lambda: "PROMPT9")
    summary = _run(fakes, monkeypatch, config="v9", dry_run=True)
    assert summary.dry_run is True
    assert fakes.v8.call_count == 0 and fakes.v7.call_count == 0
    assert fakes.record.call_count == 0
    assert "PROMPT9" in capsys.readouterr().out


def test_parse_args_accepts_v9_with_thinking_level():
    args = pab.parse_args([
        "--runs-file", "f", "--config", "v9", "--thinking-level", "low", "--repeat", "1",
        "--max-cost-usd", "1", "--test-id", "X", "--out-dir", "/o",
    ])
    assert args.config == "v9" and args.thinking_level == "LOW"


# --- v9 --prompt-name（trial1）-----------------------------------------------


@pytest.fixture
def named_prompts(monkeypatch, tmp_path):
    """prompts/ の代わりの置き場。raw_copy_v9_trial1.txt だけ置く。"""
    d = tmp_path / "prompts"
    d.mkdir()
    (d / "raw_copy_v9_trial1.txt").write_text("TRIAL1", encoding="utf-8")
    monkeypatch.setattr(pab, "_PROMPTS_DIR", d)
    return d


def test_v9_without_prompt_name_uses_default_prompt_and_records_default_name(monkeypatch, fakes):
    monkeypatch.setattr(pab, "load_v9_prompt", lambda: "PROMPT9")
    _run(fakes, monkeypatch, config="v9", run_ids=("r1",))
    assert fakes.v8.call_args.kwargs["prompt_text"] == "PROMPT9"
    assert _lines(fakes)[0]["prompt_name"] == "raw_copy_v9"


def test_v9_prompt_name_uses_named_prompt_and_records_name(monkeypatch, fakes, named_prompts):
    from app.services.gemini_raw_copy_v9 import V9_RESPONSE_SCHEMA

    monkeypatch.setattr(pab, "load_v9_prompt", lambda: "PROMPT9")
    _run(fakes, monkeypatch, config="v9", run_ids=("r1",), prompt_name="raw_copy_v9_trial1")
    kwargs = fakes.v8.call_args.kwargs
    assert kwargs["prompt_text"] == "TRIAL1"
    assert kwargs["response_schema"] is V9_RESPONSE_SCHEMA
    assert _lines(fakes)[0]["prompt_name"] == "raw_copy_v9_trial1"


def test_v9_prompt_name_dry_run_shows_named_prompt(monkeypatch, fakes, named_prompts, capsys):
    monkeypatch.setattr(pab, "load_v9_prompt", lambda: "PROMPT9")
    _run(fakes, monkeypatch, config="v9", dry_run=True, prompt_name="raw_copy_v9_trial1")
    out = capsys.readouterr().out
    assert "TRIAL1" in out and "PROMPT9" not in out
    assert fakes.v8.call_count == 0


def test_real_trial1_prompt_file_exists_and_is_loaded():
    path = pab.resolve_prompt_path("raw_copy_v9_trial1")
    assert path.name == "raw_copy_v9_trial1.txt"
    assert pab._load_prompt_text("v9", "raw_copy_v9_trial1") == path.read_text(encoding="utf-8")


@pytest.mark.parametrize("bad", ["../x", "raw_copy_v8_x", "raw_copy_v9_A", "raw_copy_v9_", "raw_copy_v9_a/b", "raw_copy_v9_a\n"])
def test_run_ab_stops_before_gemini_on_invalid_prompt_name(monkeypatch, fakes, named_prompts, bad):
    with pytest.raises(ValueError):
        _run(fakes, monkeypatch, config="v9", prompt_name=bad)
    assert fakes.v8.call_count == 0 and fakes.record.call_count == 0


def test_run_ab_stops_before_gemini_on_missing_prompt_file(monkeypatch, fakes, named_prompts):
    with pytest.raises(ValueError):
        _run(fakes, monkeypatch, config="v9", prompt_name="raw_copy_v9_nothing")
    assert fakes.v8.call_count == 0 and fakes.record.call_count == 0


@pytest.mark.parametrize("config", ["v7", "v8"])
def test_run_ab_stops_when_prompt_name_is_combined_with_v7_or_v8(monkeypatch, fakes, named_prompts, config):
    with pytest.raises(ValueError):
        _run(fakes, monkeypatch, config=config, prompt_name="raw_copy_v9_trial1")
    assert fakes.v8.call_count == 0 and fakes.v7.call_count == 0


_BASE_ARGS = ["--runs-file", "f", "--repeat", "1", "--max-cost-usd", "1", "--test-id", "X", "--out-dir", "/o"]


def test_parse_args_accepts_prompt_name_for_v9(named_prompts):
    args = pab.parse_args([*_BASE_ARGS, "--config", "v9", "--prompt-name", "raw_copy_v9_trial1"])
    assert args.prompt_name == "raw_copy_v9_trial1"


@pytest.mark.parametrize("config,name", [
    ("v8", "raw_copy_v9_trial1"), ("v7", "raw_copy_v9_trial1"),
    ("v9", "../x"), ("v9", "raw_copy_v8_x"), ("v9", "raw_copy_v9_A"), ("v9", "raw_copy_v9_nothing"),
])
def test_parse_args_rejects_bad_prompt_name(named_prompts, config, name):
    with pytest.raises(SystemExit):
        pab.parse_args([*_BASE_ARGS, "--config", config, "--prompt-name", name])


# ---------------------------------------------------------------------------
# v10（設計: docs/handoff/gemini-v10/design.md §3-5・§5-2）
# ---------------------------------------------------------------------------

_V10_RAW = "商品A\n3BOX@1,000円"
_V10_CTX = task.ExtractionContext(
    raw_text=_V10_RAW, supplier_context={"extraction_order_pattern": '["price","quantity"]'},
    knowledge_links=[], supplier_id=7,
)
_V10_RESPONSE = json.dumps({"items": [{
    "price": "1,000円", "quantity": "3", "price_line": 2, "item_lines": [2],
    "heading_lines": [1], "shared_lines": [], "name_lines": [1],
}]}, ensure_ascii=False)


@pytest.fixture
def v10_fakes(monkeypatch, fakes):
    """v10 の試験用：マスタ読み込みを差し替え、呼ばれた回数を数える。"""
    masters = SimpleNamespace(
        cond=MagicMock(return_value=[]), status=MagicMock(return_value=[]),
        lookup=MagicMock(return_value=({}, {}, {}, {}, {}, {"BOX": ("BOX", "箱系")})),
    )
    monkeypatch.setattr(pab, "load_condition_entries", masters.cond)
    monkeypatch.setattr(pab, "load_status_master", masters.status)
    monkeypatch.setattr(pab, "load_lookup_maps", masters.lookup)
    # v102 の商品先行のマスタは None に差し替える（None なら v10.2 の流れのまま。商品先行の試験は別ファイル）
    monkeypatch.setattr(pab, "load_product_first_masters", lambda session: None)
    monkeypatch.setattr(pab, "load_v10_prompt", lambda: "V10PROMPT")
    monkeypatch.setattr(pab, "load_extraction_context", MagicMock(return_value=_V10_CTX))
    fakes.v8.side_effect = lambda *a, **k: {**_v8_result(), "response_text": _V10_RESPONSE}
    fakes.masters = masters
    return fakes


def test_v10_config_calls_with_v10_schema_and_prompt(monkeypatch, v10_fakes):
    from app.services.gemini_raw_copy_v10 import V10_RESPONSE_SCHEMA

    _run(v10_fakes, monkeypatch, config="v10", run_ids=("r1",))
    kwargs = v10_fakes.v8.call_args.kwargs
    assert kwargs["response_schema"] is V10_RESPONSE_SCHEMA
    assert kwargs["prompt_text"] == "V10PROMPT"


def test_v10_row_has_v10_items_with_system_extracted_values(monkeypatch, v10_fakes):
    _run(v10_fakes, monkeypatch, config="v10", run_ids=("r1",))
    row = _lines(v10_fakes)[0]
    assert row["config"] == "v10" and row["item_count"] == 1 and row["errors"] == []
    item = row["v10_items"][0]
    assert item["name"] == "商品A" and item["unit"] == "BOX"
    assert item["raw_price"] == "1,000円" and item["price_normalized"] == 1000
    assert item["price_line"] == 2 and item["item_lines"] == [2]


def test_v10_masters_are_loaded_once_per_run_not_per_call(monkeypatch, v10_fakes):
    _run(v10_fakes, monkeypatch, config="v10", run_ids=("r1", "r2"), repeat=2)
    m = v10_fakes.masters
    assert (m.cond.call_count, m.status.call_count, m.lookup.call_count) == (1, 1, 1)


def test_v10_dry_run_does_not_read_masters(monkeypatch, v10_fakes, capsys):
    _run(v10_fakes, monkeypatch, config="v10", dry_run=True)
    m = v10_fakes.masters
    assert (m.cond.call_count, m.status.call_count, m.lookup.call_count) == (0, 0, 0)
    assert v10_fakes.v8.call_count == 0
    assert "V10PROMPT" in capsys.readouterr().out


def test_v9_and_v8_rows_have_no_v10_items_and_do_not_read_masters(monkeypatch, v10_fakes):
    for config in ("v8", "v9"):
        v10_fakes.out.joinpath("T.jsonl").unlink(missing_ok=True)
        _run(v10_fakes, monkeypatch, config=config, run_ids=("r1",))
        assert "v10_items" not in _lines(v10_fakes)[0]
    assert v10_fakes.masters.lookup.call_count == 0


def test_v10_extraction_failure_is_recorded_in_row_not_fatal(monkeypatch, v10_fakes):
    monkeypatch.setattr(pab, "extract_v10_items", MagicMock(side_effect=ValueError("boom")))
    summary = _run(v10_fakes, monkeypatch, config="v10", run_ids=("r1",))
    row = _lines(v10_fakes)[0]
    assert summary.stop_reason is None
    assert row["v10_items"] == [] and "ValueError" in row["v10_items_error"]


def test_v10_with_prompt_name_is_an_error(monkeypatch, v10_fakes):
    summary_error = None
    try:
        _run(v10_fakes, monkeypatch, config="v10", prompt_name="raw_copy_v9_x")
    except ValueError as exc:
        summary_error = exc
    assert summary_error is not None and "--config v9" in str(summary_error)
    assert v10_fakes.v8.call_count == 0


def test_parse_args_accepts_v10_and_rejects_prompt_name_with_v10(tmp_path):
    base = ["--runs-file", str(tmp_path / "r"), "--repeat", "1", "--max-cost-usd", "1", "--test-id", "T",
            "--out-dir", str(tmp_path)]
    assert pab.parse_args([*base, "--config", "v10"]).config == "v10"
    with pytest.raises(SystemExit):
        pab.parse_args([*base, "--config", "v10", "--prompt-name", "raw_copy_v9_x"])


# ---------------------------------------------------------------------------
# v101（設計: docs/handoff/gemini-v101/design.md §3-6・§5-4）
# ---------------------------------------------------------------------------

_V101_RESPONSE = json.dumps({"items": [{"lines": [1, 2], "price": "1,000円", "quantity": "3"}]}, ensure_ascii=False)


@pytest.fixture
def v101_fakes(monkeypatch, v10_fakes):
    """v101 の試験用：v10 の差し替え（マスタ・原文）に、v101 の応答を返させる。"""
    v10_fakes.v8.side_effect = lambda *a, **k: {**_v8_result(), "response_text": _V101_RESPONSE}
    return v10_fakes


def test_v101_config_calls_with_v101_schema_and_default_prompt_a(monkeypatch, v101_fakes):
    from app.services.gemini_raw_copy_v101 import V101_RESPONSE_SCHEMA, load_v101_prompt

    _run(v101_fakes, monkeypatch, config="v101", run_ids=("r1",))
    kwargs = v101_fakes.v8.call_args.kwargs
    assert kwargs["response_schema"] is V101_RESPONSE_SCHEMA
    assert kwargs["prompt_text"] == load_v101_prompt("raw_copy_v101_a")
    assert _lines(v101_fakes)[0]["prompt_name"] == "raw_copy_v101_a"


def test_v101_prompt_name_b_uses_the_b_prompt_file_and_records_name(monkeypatch, v101_fakes):
    from app.services.gemini_raw_copy_v101 import load_v101_prompt

    _run(v101_fakes, monkeypatch, config="v101", run_ids=("r1",), prompt_name="raw_copy_v101_b")
    assert v101_fakes.v8.call_args.kwargs["prompt_text"] == load_v101_prompt("raw_copy_v101_b")
    assert _lines(v101_fakes)[0]["prompt_name"] == "raw_copy_v101_b"


def test_v101_prompt_files_a_and_b_both_exist_and_differ():
    a, b = pab._load_prompt_text("v101"), pab._load_prompt_text("v101", "raw_copy_v101_b")
    assert a != b and "行番号の担当" in a and "行番号の担当" in b


def test_resolve_prompt_path_resolves_raw_copy_v101_d_for_v101_and_v102():
    # Arrange
    names_and_configs = ("v101", "v102")

    # Act
    paths = [pab.resolve_prompt_path("raw_copy_v101_d", config) for config in names_and_configs]

    # Assert
    assert all(path.name == "raw_copy_v101_d.txt" and path.is_file() for path in paths)


def test_v101_row_has_three_new_fields(monkeypatch, v101_fakes):
    _run(v101_fakes, monkeypatch, config="v101", run_ids=("r1",))
    row = _lines(v101_fakes)[0]
    assert row["config"] == "v101" and row["item_count"] == 1 and row["errors"] == []
    assert row["v101_items"][0]["name"] == "商品A" and row["v101_items"][0]["price_line"] == 2
    assert row["v101_items"][0]["unit"] == "BOX" and row["v101_items"][0]["price_normalized"] == 1000
    assert row["v101_items_norule"][0]["price_line"] == 2
    assert row["v101_flags"] == {"possible_missing_item": []}
    assert "v10_items" not in row


def test_v101_items_and_norule_are_extracted_with_reassign_on_and_off(monkeypatch, v101_fakes):
    spy = MagicMock(return_value=([], {"possible_missing_item": []}))
    monkeypatch.setattr(pab, "extract_v101_items", spy)
    _run(v101_fakes, monkeypatch, config="v101", run_ids=("r1",))
    assert [c.kwargs["reassign"] for c in spy.call_args_list] == [True, False]


def test_v101_masters_are_loaded_once_per_run_and_not_in_dry_run(monkeypatch, v101_fakes, capsys):
    _run(v101_fakes, monkeypatch, config="v101", run_ids=("r1", "r2"), repeat=2)
    m = v101_fakes.masters
    assert (m.cond.call_count, m.status.call_count, m.lookup.call_count) == (1, 1, 1)
    _run(v101_fakes, monkeypatch, config="v101", dry_run=True)
    assert (m.cond.call_count, m.status.call_count, m.lookup.call_count) == (1, 1, 1)
    assert "行番号の担当" in capsys.readouterr().out


def test_v101_extraction_failure_is_recorded_in_row_not_fatal(monkeypatch, v101_fakes):
    monkeypatch.setattr(pab, "extract_v101_items", MagicMock(side_effect=ValueError("boom")))
    summary = _run(v101_fakes, monkeypatch, config="v101", run_ids=("r1",))
    row = _lines(v101_fakes)[0]
    assert summary.stop_reason is None
    assert row["v101_items"] == [] and row["v101_items_norule"] == [] and "ValueError" in row["v101_items_error"]


def test_v9_still_uses_default_name_and_rejects_v101_names(monkeypatch, v101_fakes):
    monkeypatch.setattr(pab, "load_v9_prompt", lambda: "PROMPT9")
    _run(v101_fakes, monkeypatch, config="v9", run_ids=("r1",))
    assert _lines(v101_fakes)[0]["prompt_name"] == "raw_copy_v9"
    with pytest.raises(ValueError):
        _run(v101_fakes, monkeypatch, config="v9", prompt_name="raw_copy_v101_a")
    with pytest.raises(ValueError):
        _run(v101_fakes, monkeypatch, config="v101", prompt_name="raw_copy_v9_trial1")


@pytest.mark.parametrize("bad", ["../x", "raw_copy_v101_A", "raw_copy_v101_", "raw_copy_v101_nothing"])
def test_v101_bad_prompt_name_stops_before_gemini(monkeypatch, v101_fakes, bad):
    with pytest.raises(ValueError):
        _run(v101_fakes, monkeypatch, config="v101", prompt_name=bad)
    assert v101_fakes.v8.call_count == 0 and v101_fakes.record.call_count == 0


def test_v7_to_v10_rows_have_no_v101_fields(monkeypatch, v101_fakes):
    for config in ("v8", "v9", "v10"):
        v101_fakes.out.joinpath("T.jsonl").unlink(missing_ok=True)
        _run(v101_fakes, monkeypatch, config=config, run_ids=("r1",))
        assert not {"v101_items", "v101_items_norule", "v101_flags"} & set(_lines(v101_fakes)[0])


def test_parse_args_v101_prompt_name(tmp_path):
    base = ["--runs-file", str(tmp_path / "r"), "--repeat", "1", "--max-cost-usd", "1", "--test-id", "T",
            "--out-dir", str(tmp_path)]
    assert pab.parse_args([*base, "--config", "v101"]).prompt_name is None
    assert pab.parse_args([*base, "--config", "v101", "--prompt-name", "raw_copy_v101_b"]).prompt_name == "raw_copy_v101_b"
    for config, name in (("v101", "raw_copy_v9_trial1"), ("v9", "raw_copy_v101_a"), ("v10", "raw_copy_v101_a")):
        with pytest.raises(SystemExit):
            pab.parse_args([*base, "--config", config, "--prompt-name", name])


# ---------------------------------------------------------------------------
# v102（設計: docs/handoff/gemini-v102/design.md §3-3・§5-3）
# ---------------------------------------------------------------------------


def test_v102_config_calls_with_v101_schema_and_default_prompt_f_c_from_db(monkeypatch, v101_fakes):
    from app.services.gemini_raw_copy_v101 import V101_RESPONSE_SCHEMA

    # Arrange
    session = _db_session("F_C_FROM_DB")
    # Act
    _run(v101_fakes, monkeypatch, config="v102", run_ids=("r1",), session=session)
    kwargs = v101_fakes.v8.call_args.kwargs
    # Assert
    assert kwargs["response_schema"] == V101_RESPONSE_SCHEMA
    assert pab.DEFAULT_V102_PROMPT_KEY == "raw_copy_v101_f_c"
    assert session.execute.call_args.args[1] == {"key": "raw_copy_v101_f_c"}
    assert kwargs["prompt_text"] == "F_C_FROM_DB"
    row = _lines(v101_fakes)[0]
    assert (row["prompt_name"], row["prompt_source"]) == ("raw_copy_v101_f_c", "db")


def test_v102_default_stops_before_gemini_when_f_c_row_missing(monkeypatch, v101_fakes):
    # Act
    with pytest.raises(ValueError, match="raw_copy_v101_f_c"):
        _run(v101_fakes, monkeypatch, config="v102", run_ids=("r1",), session=_db_session(None))
    # Assert
    assert v101_fakes.v8.call_count == 0


def test_v102_prompt_name_e_uses_file_not_db(monkeypatch, v101_fakes):
    from app.services.gemini_raw_copy_v101 import load_v101_prompt

    # Arrange
    session = _db_session("SHOULD_NOT_BE_USED")
    # Act
    _run(v101_fakes, monkeypatch, config="v102", run_ids=("r1",), prompt_name="raw_copy_v101_e", session=session)
    # Assert
    row = _lines(v101_fakes)[0]
    assert (row["prompt_name"], row["prompt_source"]) == ("raw_copy_v101_e", "file")
    assert v101_fakes.v8.call_args.kwargs["prompt_text"] == load_v101_prompt("raw_copy_v101_e")
    assert session.execute.call_count == 0


def test_v102_prompt_name_b_can_be_chosen_and_default_e_differs_from_b():
    assert pab._load_prompt_text("v102") == pab._load_prompt_text("v101", "raw_copy_v101_e")
    assert pab._load_prompt_text("v102") != pab._load_prompt_text("v101", "raw_copy_v101_b")
    assert pab._load_prompt_text("v102", "raw_copy_v101_b") == pab._load_prompt_text("v101", "raw_copy_v101_b")


def test_v102_row_has_v102_items_and_flags_but_no_v101_fields(monkeypatch, v101_fakes):
    _run(v101_fakes, monkeypatch, config="v102", run_ids=("r1",))
    row = _lines(v101_fakes)[0]
    assert row["config"] == "v102" and row["item_count"] == 1 and row["errors"] == []
    assert row["v102_items"][0]["name"] == "商品A" and row["v102_items"][0]["fixes"] == []
    assert set(row["v102_flags"]) == {"possible_missing_item", "quantity_no_number", "possible_footer_line", "post_review"}
    assert not {"v101_items", "v101_items_norule", "v101_flags"} & set(row)


def test_v102_extracts_once_with_v102_fixes_and_reassign_on(monkeypatch, v101_fakes):
    spy = MagicMock(return_value=([], {}))
    monkeypatch.setattr(pab, "extract_v101_items", spy)
    _run(v101_fakes, monkeypatch, config="v102", run_ids=("r1",))
    assert spy.call_count == 1
    assert spy.call_args.kwargs["reassign"] is True and spy.call_args.kwargs["v102_fixes"] is True


def test_v102_extraction_failure_is_recorded_in_row_not_fatal(monkeypatch, v101_fakes):
    monkeypatch.setattr(pab, "extract_v101_items", MagicMock(side_effect=ValueError("boom")))
    summary = _run(v101_fakes, monkeypatch, config="v102", run_ids=("r1",))
    row = _lines(v101_fakes)[0]
    assert summary.stop_reason is None
    assert row["v102_items"] == [] and "ValueError" in row["v102_items_error"]
    assert row["v102_flags"]["post_review"][0]["kind"] == "extract_exception"
    assert "ValueError" in row["v102_flags"]["post_review"][0]["error"]


def test_v102_row_keeps_dropped_items_and_result_count_equals_gemini_count(monkeypatch, v101_fakes):
    # Arrange
    response = json.dumps({"items": [
        {"lines": [1, 2], "price": "1,000円", "quantity": "3"},
        {"lines": [1, 2], "price": "9,999円", "quantity": "3"},
    ]}, ensure_ascii=False)
    v101_fakes.v8.side_effect = lambda *a, **k: {**_v8_result(), "response_text": response}
    # Act
    _run(v101_fakes, monkeypatch, config="v102", run_ids=("r1",))
    row = _lines(v101_fakes)[0]
    # Assert
    assert len(row["v102_items"]) == 2 and row["v102_items"][1]["rejected"] == "price_not_in_lines"
    assert row["v102_items"][1]["review"][0]["kind"] == "price_not_in_lines"


def test_v102_unreadable_response_is_recorded_in_post_review(monkeypatch, v101_fakes):
    # Arrange
    v101_fakes.v8.side_effect = lambda *a, **k: {**_v8_result(), "response_text": "not json"}
    # Act
    _run(v101_fakes, monkeypatch, config="v102", run_ids=("r1",))
    row = _lines(v101_fakes)[0]
    # Assert
    assert row["v102_items"] == []
    assert [r["kind"] for r in row["v102_flags"]["post_review"]] == ["response_unreadable"]
    assert row["v102_flags"]["post_review"][0]["error"]


def test_v102_zero_gemini_items_gives_no_items_in_post_review(monkeypatch, v101_fakes):
    v101_fakes.v8.side_effect = lambda *a, **k: {**_v8_result(), "response_text": '{"items": []}'}
    _run(v101_fakes, monkeypatch, config="v102", run_ids=("r1",))
    assert _lines(v101_fakes)[0]["v102_flags"]["post_review"] == [{"kind": "no_items"}]


def test_v101_row_flags_do_not_get_post_review(monkeypatch, v101_fakes):
    _run(v101_fakes, monkeypatch, config="v101", run_ids=("r1",))
    assert "post_review" not in _lines(v101_fakes)[0]["v101_flags"]


def test_v101_row_is_unchanged_and_has_no_v102_fields(monkeypatch, v101_fakes):
    _run(v101_fakes, monkeypatch, config="v101", run_ids=("r1",))
    row = _lines(v101_fakes)[0]
    assert row["prompt_name"] == "raw_copy_v101_a"
    assert row["v101_flags"] == {"possible_missing_item": []}
    assert "fixes" not in row["v101_items"][0]
    assert not {"v102_items", "v102_flags"} & set(row)


def test_v102_bad_prompt_name_stops_before_gemini(monkeypatch, v101_fakes):
    with pytest.raises(ValueError):
        _run(v101_fakes, monkeypatch, config="v102", prompt_name="raw_copy_v9_trial1")
    assert v101_fakes.v8.call_count == 0 and v101_fakes.record.call_count == 0


def test_parse_args_accepts_v102_and_its_prompt_name(tmp_path):
    base = ["--runs-file", str(tmp_path / "r"), "--repeat", "1", "--max-cost-usd", "1", "--test-id", "T",
            "--out-dir", str(tmp_path)]
    assert pab.parse_args([*base, "--config", "v102"]).prompt_name is None
    assert pab.parse_args([*base, "--config", "v102", "--prompt-name", "raw_copy_v101_b"]).prompt_name == "raw_copy_v101_b"
    with pytest.raises(SystemExit):
        pab.parse_args([*base, "--config", "v102", "--prompt-name", "raw_copy_v9_trial1"])


# ---------------------------------------------------------------------------
# --omit-supplier-field（仕入元ルールの欄を外す）
# ---------------------------------------------------------------------------

_SHIP_LABEL = "発送日フォーマット"
_OMIT_CTX = task.ExtractionContext(
    raw_text="a\nb",
    supplier_context={"extraction_price_format": "円", "extraction_ship_format": "SHIPRULE"},
    knowledge_links=[], supplier_id=7,
)


def _omit_ctx_run(fakes, monkeypatch, **over):
    monkeypatch.setattr(pab, "load_extraction_context", MagicMock(return_value=_OMIT_CTX))
    return _run(fakes, monkeypatch, run_ids=("r1",), **over)


def _prompt_given_to_gemini(fakes):
    kw = fakes.v8.call_args.kwargs
    return pab.build_prompt_v8(
        "a", prompt_text="P", supplier_context=kw["supplier_context"], knowledge_links=kw["knowledge_links"],
    )


def test_omit_field_removes_only_that_field_from_prompt(monkeypatch, fakes):
    # Arrange / Act
    _omit_ctx_run(fakes, monkeypatch, omit_supplier_fields=["extraction_ship_format"])
    # Assert
    prompt = _prompt_given_to_gemini(fakes)
    assert _SHIP_LABEL not in prompt and "SHIPRULE" not in prompt
    assert "円" in prompt


def test_without_omit_the_field_stays_in_prompt(monkeypatch, fakes):
    _omit_ctx_run(fakes, monkeypatch)
    prompt = _prompt_given_to_gemini(fakes)
    assert _SHIP_LABEL in prompt and "SHIPRULE" in prompt


def test_omit_does_not_change_original_context(monkeypatch, fakes):
    before = dict(_OMIT_CTX.supplier_context)
    _omit_ctx_run(fakes, monkeypatch, omit_supplier_fields=["extraction_ship_format"])
    assert _OMIT_CTX.supplier_context == before


def test_omit_handles_none_supplier_context():
    assert pab._supplier_context_without(None, ["extraction_ship_format"]) is None


def test_omit_dry_run_prompt_has_no_omitted_field(monkeypatch, fakes, capsys):
    _omit_ctx_run(fakes, monkeypatch, dry_run=True, omit_supplier_fields=["extraction_ship_format"])
    out = capsys.readouterr().out
    assert _SHIP_LABEL not in out and "[L0001] a" in out


def test_omit_writes_sorted_field_list_to_jsonl(monkeypatch, fakes):
    _omit_ctx_run(fakes, monkeypatch, omit_supplier_fields=["extraction_ship_format", "extraction_price_format"])
    assert _lines(fakes)[0]["omitted_supplier_fields"] == ["extraction_price_format", "extraction_ship_format"]


def test_without_omit_jsonl_has_no_omitted_field_key(monkeypatch, fakes):
    _omit_ctx_run(fakes, monkeypatch)
    assert "omitted_supplier_fields" not in _lines(fakes)[0]


def test_parse_args_accepts_repeated_omit_supplier_field():
    args = pab.parse_args([*_BASE_ARGS, "--config", "v101",
                           "--omit-supplier-field", "extraction_ship_format",
                           "--omit-supplier-field", "extraction_price_format"])
    assert args.omit_supplier_field == ["extraction_ship_format", "extraction_price_format"]


def test_parse_args_v102_omits_legacy_supplier_fields_by_default():
    assert pab.parse_args([*_BASE_ARGS, "--config", "v102"]).omit_supplier_field == sorted(pab.LEGACY_SUPPLIER_FIELDS)


def test_parse_args_v102_explicit_omit_is_unioned_with_legacy_fields():
    args = pab.parse_args([*_BASE_ARGS, "--config", "v102", "--omit-supplier-field", "extraction_layout_rules"])
    assert args.omit_supplier_field == sorted({*pab.LEGACY_SUPPLIER_FIELDS, "extraction_layout_rules"})
    assert len(args.omit_supplier_field) == 8


def test_parse_args_v102_keep_legacy_supplier_fields_omits_nothing():
    args = pab.parse_args([*_BASE_ARGS, "--config", "v102", "--keep-legacy-supplier-fields"])
    assert args.omit_supplier_field is None


def test_parse_args_v101_default_omits_nothing():
    assert pab.parse_args([*_BASE_ARGS, "--config", "v101"]).omit_supplier_field is None


def test_parse_args_rejects_keep_legacy_supplier_fields_for_v101():
    with pytest.raises(SystemExit):
        pab.parse_args([*_BASE_ARGS, "--config", "v101", "--keep-legacy-supplier-fields"])


_LEGACY_CTX = task.ExtractionContext(
    raw_text="a\nb", supplier_context={name: f"V_{name}" for name in pab.LEGACY_SUPPLIER_FIELDS},
    knowledge_links=[], supplier_id=7,
    new_system_rules={"extraction_layout_rules": "DBLAYOUT", "extraction_hard_cases": "DBHARD"},
)


def test_v102_default_run_uses_prompt_f_c_and_records_seven_omitted_fields(monkeypatch, v101_fakes):
    # Arrange
    args = pab.parse_args([*_BASE_ARGS, "--config", "v102"])
    # Act
    _run(v101_fakes, monkeypatch, config="v102", run_ids=("r1",), omit_supplier_fields=args.omit_supplier_field,
         session=_db_session("F_C_FROM_DB"))
    # Assert
    row = _lines(v101_fakes)[0]
    assert row["prompt_name"] == "raw_copy_v101_f_c"
    assert row["omitted_supplier_fields"] == sorted(pab.LEGACY_SUPPLIER_FIELDS)
    assert len(row["omitted_supplier_fields"]) == 7


def test_v102_default_omit_removes_legacy_fields_but_keeps_new_system_rules(monkeypatch, v101_fakes):
    # Arrange
    monkeypatch.setattr(pab, "load_extraction_context", MagicMock(return_value=_LEGACY_CTX))
    args = pab.parse_args([*_BASE_ARGS, "--config", "v102"])
    # Act
    _run(v101_fakes, monkeypatch, config="v102", run_ids=("r1",), omit_supplier_fields=args.omit_supplier_field)
    # Assert
    kwargs = v101_fakes.v8.call_args.kwargs
    assert not set(pab.LEGACY_SUPPLIER_FIELDS) & set(kwargs["supplier_context"] or {})
    assert kwargs["new_system_rules"] == {"extraction_layout_rules": "DBLAYOUT", "extraction_hard_cases": "DBHARD"}


@pytest.mark.parametrize("bad", ["ship_format", "Extraction_x", "extraction_", "extraction_a-b", "extraction_x1", ""])
def test_parse_args_rejects_bad_omit_supplier_field(bad):
    with pytest.raises(SystemExit):
        pab.parse_args([*_BASE_ARGS, "--config", "v102", "--omit-supplier-field", bad])


def test_parse_args_rejects_omit_supplier_field_for_v7():
    with pytest.raises(SystemExit):
        pab.parse_args([*_BASE_ARGS, "--config", "v7", "--omit-supplier-field", "extraction_ship_format"])


def test_resolve_prompt_path_resolves_raw_copy_v101_e_for_v101_and_v102():
    # Arrange
    names_and_configs = ("v101", "v102")

    # Act
    paths = [pab.resolve_prompt_path("raw_copy_v101_e", config) for config in names_and_configs]

    # Assert
    assert all(path.name == "raw_copy_v101_e.txt" and path.is_file() for path in paths)


# ---------------------------------------------------------------------------
# --supplier-rules-file（仕入元ルールの欄を差し替える）
# ---------------------------------------------------------------------------

_RULES_CTX = task.ExtractionContext(
    raw_text="a\nb",
    supplier_context={"extraction_price_format": "DBPRICE", "extraction_notes": "DBNOTES",
                      "extraction_ship_format": "SHIPRULE"},
    knowledge_links=[], supplier_id=7,
)


def _write_rules(tmp_path, data, name="rules.json"):
    path = tmp_path / name
    path.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _rules_run(fakes, monkeypatch, rules_path, ctx=_RULES_CTX, **over):
    monkeypatch.setattr(pab, "load_extraction_context", MagicMock(return_value=ctx))
    return _run(fakes, monkeypatch, run_ids=("r1",), supplier_rules_file=rules_path, **over)


def test_rules_file_overrides_listed_field_and_keeps_unlisted_and_drops_null(monkeypatch, fakes, tmp_path):
    # Arrange
    path = _write_rules(tmp_path, {"7": {"extraction_price_format": "NEWPRICE", "extraction_ship_format": None}})
    # Act
    _rules_run(fakes, monkeypatch, path)
    # Assert
    sent = fakes.v8.call_args.kwargs["supplier_context"]
    assert sent == {"extraction_price_format": "NEWPRICE", "extraction_notes": "DBNOTES"}


def test_rules_file_does_not_change_original_context(monkeypatch, fakes, tmp_path):
    # Arrange
    before = dict(_RULES_CTX.supplier_context)
    path = _write_rules(tmp_path, {"7": {"extraction_price_format": "NEWPRICE", "extraction_ship_format": None}})
    # Act
    _rules_run(fakes, monkeypatch, path)
    # Assert
    assert _RULES_CTX.supplier_context == before


def test_rules_file_without_matching_supplier_id_behaves_as_before(monkeypatch, fakes, tmp_path):
    # Arrange
    path = _write_rules(tmp_path, {"999": {"extraction_price_format": "NEWPRICE"}})
    # Act
    _rules_run(fakes, monkeypatch, path)
    # Assert
    assert fakes.v8.call_args.kwargs["supplier_context"] == _RULES_CTX.supplier_context
    assert "supplier_rules_override" not in _lines(fakes)[0]


def test_rules_file_applies_to_supplier_without_db_rules(monkeypatch, fakes, tmp_path):
    # Arrange
    ctx = task.ExtractionContext("a\nb", None, [], 7)
    path = _write_rules(tmp_path, {"7": {"extraction_price_format": "NEWPRICE"}})
    # Act
    _rules_run(fakes, monkeypatch, path, ctx=ctx)
    # Assert
    assert fakes.v8.call_args.kwargs["supplier_context"] == {"extraction_price_format": "NEWPRICE"}


def test_rules_file_with_no_supplier_id_in_context_behaves_as_before(monkeypatch, fakes, tmp_path):
    # Arrange
    ctx = task.ExtractionContext("a\nb", {"extraction_price_format": "DBPRICE"}, [], None)
    path = _write_rules(tmp_path, {"7": {"extraction_price_format": "NEWPRICE"}})
    # Act
    _rules_run(fakes, monkeypatch, path, ctx=ctx)
    # Assert
    assert fakes.v8.call_args.kwargs["supplier_context"] == {"extraction_price_format": "DBPRICE"}


def test_rules_file_writes_override_record_to_jsonl(monkeypatch, fakes, tmp_path):
    # Arrange
    path = _write_rules(tmp_path, {"7": {"extraction_price_format": "NEWPRICE", "extraction_ship_format": None}})
    # Act
    _rules_run(fakes, monkeypatch, path)
    # Assert
    record = _lines(fakes)[0]["supplier_rules_override"]
    assert record == {
        "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "supplier_id": "7",
        "fields": ["extraction_price_format", "extraction_ship_format"],
    }


def test_without_rules_file_jsonl_has_no_override_key_and_context_is_unchanged(monkeypatch, fakes):
    # Arrange / Act
    _rules_run(fakes, monkeypatch, None)
    # Assert
    assert "supplier_rules_override" not in _lines(fakes)[0]
    assert fakes.v8.call_args.kwargs["supplier_context"] == _RULES_CTX.supplier_context


def test_rules_file_is_applied_before_omit(monkeypatch, fakes, tmp_path):
    # Arrange
    path = _write_rules(tmp_path, {"7": {"extraction_price_format": "NEWPRICE", "extraction_ship_format": "NEWSHIP"}})
    # Act
    _rules_run(fakes, monkeypatch, path, omit_supplier_fields=["extraction_ship_format"])
    # Assert
    assert fakes.v8.call_args.kwargs["supplier_context"] == {
        "extraction_price_format": "NEWPRICE", "extraction_notes": "DBNOTES",
    }


def test_rules_file_dry_run_prompt_uses_overridden_rules(monkeypatch, fakes, tmp_path, capsys):
    # Arrange
    path = _write_rules(tmp_path, {"7": {"extraction_price_format": "NEWPRICE", "extraction_ship_format": None}})
    # Act
    _rules_run(fakes, monkeypatch, path, dry_run=True)
    # Assert
    out = capsys.readouterr().out
    assert "NEWPRICE" in out and "DBPRICE" not in out and "SHIPRULE" not in out
    fakes.v8.assert_not_called()


@pytest.mark.parametrize("content", [
    "not json", "[]", '{"7": []}', '{"7": {"ship_format": "x"}}', '{"7": {"extraction_Bad": "x"}}',
    '{"7": {"extraction_notes": 1}}',
])
def test_run_ab_stops_before_gemini_on_invalid_rules_file(monkeypatch, fakes, tmp_path, content):
    # Arrange
    path = _write_rules(tmp_path, content)
    # Act / Assert
    with pytest.raises(ValueError):
        _rules_run(fakes, monkeypatch, path)
    fakes.v8.assert_not_called()


def test_run_ab_stops_before_gemini_on_missing_rules_file(monkeypatch, fakes, tmp_path):
    with pytest.raises(ValueError):
        _rules_run(fakes, monkeypatch, tmp_path / "nothing.json")
    fakes.v8.assert_not_called()


def test_run_ab_rejects_rules_file_with_v7(monkeypatch, fakes, tmp_path):
    # Arrange
    path = _write_rules(tmp_path, {"7": {"extraction_notes": "x"}})
    # Act / Assert
    with pytest.raises(ValueError):
        _rules_run(fakes, monkeypatch, path, config="v7")
    fakes.v7.assert_not_called()


def test_parse_args_accepts_supplier_rules_file(tmp_path):
    path = _write_rules(tmp_path, {"7": {"extraction_notes": "x"}})
    args = pab.parse_args([*_BASE_ARGS, "--config", "v102", "--supplier-rules-file", str(path)])
    assert args.supplier_rules_file == path


def test_parse_args_supplier_rules_file_default_is_none():
    assert pab.parse_args([*_BASE_ARGS, "--config", "v102"]).supplier_rules_file is None


def test_parse_args_rejects_supplier_rules_file_for_v7(tmp_path):
    path = _write_rules(tmp_path, {"7": {"extraction_notes": "x"}})
    with pytest.raises(SystemExit):
        pab.parse_args([*_BASE_ARGS, "--config", "v7", "--supplier-rules-file", str(path)])


@pytest.mark.parametrize("content", ["not json", '{"7": {"bad": "x"}}'])
def test_parse_args_rejects_invalid_supplier_rules_file(tmp_path, content):
    path = _write_rules(tmp_path, content)
    with pytest.raises(SystemExit):
        pab.parse_args([*_BASE_ARGS, "--config", "v102", "--supplier-rules-file", str(path)])


# ---------------------------------------------------------------------------
# new_system_rules（新しい仕組み専用の2欄）
# ---------------------------------------------------------------------------

_NEW_RULES_CTX = task.ExtractionContext(
    raw_text="a\nb", supplier_context={"extraction_price_format": "DBPRICE"}, knowledge_links=[], supplier_id=7,
    new_system_rules={"extraction_layout_rules": "DBLAYOUT", "extraction_hard_cases": "DBHARD"},
)


def test_new_system_rules_are_passed_to_v8_family_and_not_to_supplier_context(monkeypatch, fakes):
    # Arrange / Act
    monkeypatch.setattr(pab, "load_extraction_context", MagicMock(return_value=_NEW_RULES_CTX))
    _run(fakes, monkeypatch, run_ids=("r1",))
    # Assert
    kwargs = fakes.v8.call_args.kwargs
    assert kwargs["new_system_rules"] == {"extraction_layout_rules": "DBLAYOUT", "extraction_hard_cases": "DBHARD"}
    assert kwargs["supplier_context"] == {"extraction_price_format": "DBPRICE"}


def test_new_system_rules_are_not_passed_to_v7(monkeypatch, fakes):
    monkeypatch.setattr(pab, "load_extraction_context", MagicMock(return_value=_NEW_RULES_CTX))
    _run(fakes, monkeypatch, config="v7", run_ids=("r1",))
    assert "new_system_rules" not in fakes.v7.call_args.kwargs
    assert fakes.v7.call_args.kwargs["supplier_context"] == {"extraction_price_format": "DBPRICE"}


def test_rules_file_overrides_new_system_rules_and_null_removes(monkeypatch, fakes, tmp_path):
    path = _write_rules(tmp_path, {"7": {"extraction_layout_rules": "FILELAYOUT", "extraction_hard_cases": None}})
    _rules_run(fakes, monkeypatch, path, ctx=_NEW_RULES_CTX)
    kwargs = fakes.v8.call_args.kwargs
    assert kwargs["new_system_rules"] == {"extraction_layout_rules": "FILELAYOUT"}
    assert kwargs["supplier_context"] == {"extraction_price_format": "DBPRICE"}
    assert _lines(fakes)[0]["supplier_rules_override"]["fields"] == ["extraction_hard_cases", "extraction_layout_rules"]
    assert _NEW_RULES_CTX.new_system_rules == {"extraction_layout_rules": "DBLAYOUT", "extraction_hard_cases": "DBHARD"}


def test_rules_file_can_supply_new_system_rules_when_db_has_none(monkeypatch, fakes, tmp_path):
    ctx = task.ExtractionContext("a\nb", None, [], 7)
    path = _write_rules(tmp_path, {"7": {"extraction_hard_cases": "FILEHARD"}})
    _rules_run(fakes, monkeypatch, path, ctx=ctx)
    kwargs = fakes.v8.call_args.kwargs
    assert kwargs["new_system_rules"] == {"extraction_hard_cases": "FILEHARD"}
    assert kwargs["supplier_context"] is None


def test_omit_supplier_field_also_removes_new_system_rule(monkeypatch, fakes):
    monkeypatch.setattr(pab, "load_extraction_context", MagicMock(return_value=_NEW_RULES_CTX))
    _run(fakes, monkeypatch, run_ids=("r1",), omit_supplier_fields=["extraction_layout_rules"])
    assert fakes.v8.call_args.kwargs["new_system_rules"] == {"extraction_hard_cases": "DBHARD"}


def test_no_new_system_rules_passes_none_to_v8(monkeypatch, fakes):
    _run(fakes, monkeypatch, run_ids=("r1",))
    assert fakes.v8.call_args.kwargs["new_system_rules"] is None


# ---------------------------------------------------------------------------
# --prompt-key（指示書を DB から読む。設計: docs/handoff/prompt-ab-db-source/design.md §3）
# ---------------------------------------------------------------------------

_DB_KEY = "raw_copy_v101_zz"
_DB_BODY = "PROMPT_FROM_DB"


def _db_session(body):
    """execute(...).first() が (本文,) を返す偽の session。body が None なら行なし（SQL が行を返さない）。"""
    session = MagicMock()
    session.execute.return_value.first.return_value = None if body is None else (body,)
    return session


def test_load_prompt_from_db_returns_the_row_text_as_is():
    # Arrange
    session = _db_session(_DB_BODY)
    # Act
    result = pab._load_prompt_text("v101", prompt_key=_DB_KEY, session=session)
    # Assert
    assert result == _DB_BODY
    assert session.execute.call_args.args[1] == {"key": _DB_KEY}


@pytest.mark.parametrize("body", [None, "", "  \n\t "], ids=["no_row_or_inactive", "empty", "blank"])
def test_prompt_key_stops_before_gemini_when_row_missing_or_empty(monkeypatch, v101_fakes, body):
    # Arrange
    session = _db_session(body)
    # Act
    with pytest.raises(ValueError, match=_DB_KEY) as exc_info:
        _run(v101_fakes, monkeypatch, config="v101", run_ids=("r1",), prompt_key=_DB_KEY, session=session)
    # Assert
    assert v101_fakes.v8.call_count == 0
    assert _DB_BODY not in str(exc_info.value)


@pytest.mark.parametrize("bad", ["raw_copy_extraction", "base_extraction", "work_id_extraction", "../x", "raw_copy_v101_A"])
def test_parse_args_rejects_prompt_key_with_bad_shape(bad):
    # Act / Assert
    with pytest.raises(SystemExit):
        pab.parse_args([*_BASE_ARGS, "--config", "v101", "--prompt-key", bad])


def test_parse_args_rejects_prompt_key_with_prompt_name():
    # Act / Assert
    with pytest.raises(SystemExit):
        pab.parse_args([*_BASE_ARGS, "--config", "v101", "--prompt-key", _DB_KEY, "--prompt-name", "raw_copy_v101_a"])


@pytest.mark.parametrize("config", ["v9", "v7"])
def test_parse_args_rejects_prompt_key_for_other_configs(config):
    # Act / Assert
    with pytest.raises(SystemExit):
        pab.parse_args([*_BASE_ARGS, "--config", config, "--prompt-key", _DB_KEY])


def test_parse_args_accepts_prompt_key_for_v101_and_v102():
    # Act
    args = [pab.parse_args([*_BASE_ARGS, "--config", c, "--prompt-key", _DB_KEY]) for c in ("v101", "v102")]
    # Assert
    assert [a.prompt_key for a in args] == [_DB_KEY, _DB_KEY]


def test_prompt_key_row_records_source_sha256_and_key(monkeypatch, v101_fakes):
    # Arrange
    expected_sha = hashlib.sha256(_DB_BODY.encode("utf-8")).hexdigest()
    # Act
    _run(v101_fakes, monkeypatch, config="v101", run_ids=("r1",), prompt_key=_DB_KEY, session=_db_session(_DB_BODY))
    # Assert
    row = _lines(v101_fakes)[0]
    assert (row["prompt_source"], row["prompt_sha256"], row["prompt_name"]) == ("db", expected_sha, _DB_KEY)
    assert v101_fakes.v8.call_args.kwargs["prompt_text"] == _DB_BODY


def test_file_prompt_row_records_source_file_and_sha256(monkeypatch, v101_fakes):
    # Act
    _run(v101_fakes, monkeypatch, config="v101", run_ids=("r1",))
    # Assert
    row = _lines(v101_fakes)[0]
    prompt_text = v101_fakes.v8.call_args.kwargs["prompt_text"]
    assert row["prompt_source"] == "file"
    assert row["prompt_sha256"] == hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()


def test_v7_row_has_no_prompt_source_or_sha256(monkeypatch, fakes):
    # Act
    _run(fakes, monkeypatch, config="v7", run_ids=("r1",))
    # Assert
    row = _lines(fakes)[0]
    assert (row["prompt_source"], row["prompt_sha256"]) == (None, None)
