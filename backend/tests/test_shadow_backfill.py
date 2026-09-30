"""shadow_backfill（新方式だけを過去ジョブに一括で流す道具）の単体試験。

設計: docs/handoff/gemini-extract-role-split/shadow-backfill-design.md §3・§6
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

import app.tools.shadow_backfill as sb
from app.tasks import tcg_extraction as task
from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg_fixture

pg = pg_fixture  # 共有 fixture（本物の migration 済み DB。CI 専用）

_CTX = task.ExtractionContext(
    raw_text="raw", supplier_context={"extraction_price_format": "円"},
    knowledge_links=[{"category": "c", "pattern": "p", "normalized_to": "n"}], supplier_id=7,
)


@pytest.fixture
def fakes(monkeypatch):
    """Gemini を呼ぶ関数・読み込み・直前の再確認を差し替える。run は呼ぶたびに run_id r1, r2... を返す。"""
    counter = {"n": 0}

    def run_fn(*a, **kw):
        counter["n"] += 1
        return {"status": "completed", "run_id": f"r{counter['n']}"}

    run = MagicMock(side_effect=run_fn)
    monkeypatch.setattr(sb, "run_shadow_for_job", run)
    monkeypatch.setattr(sb, "load_extraction_context", MagicMock(return_value=_CTX))
    monkeypatch.setattr(sb, "shadow_run_exists", MagicMock(return_value=False))
    return run


def _totals(costs, *, null_rows=0, missing=False):
    """台帳の読み取り。run_id の数だけ行があり（missing なら0行）、費用は costs の順に進む。"""
    it = iter(costs)

    def fake(session, run_ids):
        rows = 0 if missing else len(run_ids)
        return sb.LedgerTotals(rows=rows, null_cost_rows=null_rows, cost_usd=next(it))

    return fake


def _session():
    return MagicMock()


def _targets(monkeypatch, ids):
    monkeypatch.setattr(sb, "select_target_jobs", lambda s, limit: ids)


# --- §6 費用の上限で止まる ----------------------------------------------------
def test_stops_when_cumulative_cost_exceeds_limit_and_skips_gemini(monkeypatch, fakes):
    _targets(monkeypatch, ["j1", "j2", "j3", "j4"])
    monkeypatch.setattr(
        sb, "fetch_ledger_totals", _totals([Decimal("0.4"), Decimal("1.1"), Decimal("9")])
    )

    summary = sb.run_backfill(_session(), limit=4, max_cost_usd=Decimal("1.0"), dry_run=False)

    assert [c.args[1] for c in fakes.call_args_list] == ["j1", "j2"]
    assert summary.processed == 2
    assert summary.stop_reason == "cost_limit"
    assert summary.total_cost_usd == Decimal("1.1")


def test_ledger_is_read_by_run_ids_created_by_this_tool(monkeypatch, fakes):
    _targets(monkeypatch, ["j1", "j2"])
    seen = []

    def fake(session, run_ids):
        seen.append(list(run_ids))
        return sb.LedgerTotals(rows=len(run_ids), null_cost_rows=0, cost_usd=Decimal("0.1"))

    monkeypatch.setattr(sb, "fetch_ledger_totals", fake)
    sb.run_backfill(_session(), limit=2, max_cost_usd=Decimal("5"), dry_run=False)
    assert seen == [["r1"], ["r1", "r2"]]


def test_runs_all_targets_when_under_limit(monkeypatch, fakes):
    _targets(monkeypatch, ["j1", "j2", "j3"])
    monkeypatch.setattr(sb, "fetch_ledger_totals", _totals([Decimal("0.1")] * 3))

    summary = sb.run_backfill(_session(), limit=3, max_cost_usd=Decimal("5"), dry_run=False)

    assert (summary.processed, summary.succeeded, summary.failed) == (3, 3, 0)
    assert summary.stop_reason is None


# --- §6 費用を見張れないときに止まる ------------------------------------------
def test_stops_when_completed_run_has_no_ledger_row(monkeypatch, fakes):
    _targets(monkeypatch, ["j1", "j2", "j3"])
    monkeypatch.setattr(sb, "fetch_ledger_totals", _totals([Decimal("0")] * 3, missing=True))

    summary = sb.run_backfill(_session(), limit=3, max_cost_usd=Decimal("5"), dry_run=False)

    assert fakes.call_count == 1
    assert summary.stop_reason == "ledger_missing"


def test_stops_when_ledger_cost_is_null(monkeypatch, fakes):
    _targets(monkeypatch, ["j1", "j2", "j3"])
    monkeypatch.setattr(sb, "fetch_ledger_totals", _totals([Decimal("0")] * 3, null_rows=1))

    summary = sb.run_backfill(_session(), limit=3, max_cost_usd=Decimal("5"), dry_run=False)

    assert fakes.call_count == 1
    assert summary.stop_reason == "cost_null"


# --- §6 失敗1件で止まる -------------------------------------------------------
@pytest.mark.parametrize(
    "outcome",
    [{"status": "failed", "error_code": "JUDGEMENT_FAILED"}, {"status": "failed"}, RuntimeError("boom")],
)
def test_stops_at_first_failure_and_skips_next_gemini(monkeypatch, fakes, outcome):
    _targets(monkeypatch, ["j1", "j2", "j3"])
    monkeypatch.setattr(sb, "fetch_ledger_totals", _totals([Decimal("0")] * 3))
    fakes.side_effect = [outcome]

    summary = sb.run_backfill(_session(), limit=3, max_cost_usd=Decimal("5"), dry_run=False)

    assert fakes.call_count == 1
    assert (summary.processed, summary.succeeded, summary.failed) == (1, 0, 1)
    assert summary.stop_reason == "job_failed"


def test_missing_job_context_stops_without_gemini(monkeypatch, fakes):
    _targets(monkeypatch, ["j1", "j2"])
    monkeypatch.setattr(sb, "load_extraction_context", MagicMock(return_value=None))

    summary = sb.run_backfill(_session(), limit=2, max_cost_usd=Decimal("1"), dry_run=False)

    fakes.assert_not_called()
    assert (summary.processed, summary.failed, summary.stop_reason) == (1, 1, "job_failed")


# --- §6 直前の再確認 ----------------------------------------------------------
def test_skips_job_whose_run_appeared_after_selection(monkeypatch, fakes):
    _targets(monkeypatch, ["j1", "j2", "j3"])
    monkeypatch.setattr(sb, "shadow_run_exists", lambda s, job_id: job_id == "j2")
    monkeypatch.setattr(sb, "fetch_ledger_totals", _totals([Decimal("0.1")] * 3))

    summary = sb.run_backfill(_session(), limit=3, max_cost_usd=Decimal("5"), dry_run=False)

    assert [c.args[1] for c in fakes.call_args_list] == ["j1", "j3"]
    assert (summary.processed, summary.skipped) == (2, 1)


# --- §6 dry-run は書き込まない ------------------------------------------------
def test_dry_run_calls_neither_gemini_nor_writes(monkeypatch, fakes):
    ids = [f"j{i}" for i in range(15)]
    _targets(monkeypatch, ids)
    cost = MagicMock()
    monkeypatch.setattr(sb, "fetch_ledger_totals", cost)
    session = _session()

    summary = sb.run_backfill(session, limit=15, max_cost_usd=Decimal("1"), dry_run=True)

    fakes.assert_not_called()
    sb.load_extraction_context.assert_not_called()
    sb.shadow_run_exists.assert_not_called()
    cost.assert_not_called()
    session.commit.assert_not_called()
    assert all("INSERT" not in str(c.args[0]).upper() for c in session.execute.call_args_list)
    assert summary.target_count == 15
    assert summary.preview_job_ids == ids[:10]
    assert summary.processed == 0


def test_cli_requires_limit_and_max_cost():
    with pytest.raises(SystemExit):
        sb.parse_args(["--limit", "5"])
    with pytest.raises(SystemExit):
        sb.parse_args(["--max-cost-usd", "1"])
    args = sb.parse_args(["--limit", "5", "--max-cost-usd", "1.5", "--dry-run"])
    assert (args.limit, args.max_cost_usd, args.dry_run) == (5, Decimal("1.5"), True)


# --- §6 基準4: 読み込みの切り出し（本番の動きを変えない）-----------------------
def test_load_extraction_context_returns_four_parts():
    session = MagicMock()
    row = ("ej", "原文", "p", "q", "o", None, None, None, None, None, 7)
    session.execute.return_value.fetchone.return_value = row
    session.execute.return_value.fetchall.return_value = [("cat", "pat", "norm")]

    ctx = task.load_extraction_context(session, "ej")

    assert ctx.raw_text == "原文"
    assert ctx.supplier_context["extraction_price_format"] == "p"
    assert ctx.knowledge_links == [{"category": "cat", "pattern": "pat", "normalized_to": "norm"}]
    assert ctx.supplier_id == 7


def test_load_extraction_context_none_when_job_missing():
    session = MagicMock()
    session.execute.return_value.fetchone.return_value = None
    assert task.load_extraction_context(session, "nope") is None


# --- §6 対象の選び方（実 PostgreSQL）-------------------------------------------
# スキーマは本物の migration で作る（柱3-c: テストでの本番テーブル定義コピー禁止）。
# 共有 `pg` フィクスチャは CI 専用（GITHUB_ACTIONS=true + RLS_ADMIN_DATABASE_URL 必須）。
# shadow の migration は extraction_prompt_config に初期値を INSERT するため、先にその表の migration を流す。
_SHADOW_MIGRATIONS = (
    "20260926_080000_create_extraction_prompt_config.sql",
    "20260928_110000_create_extraction_shadow_tables.sql",
)


def _apply_shadow_migration(connection) -> None:
    with connection.cursor() as cur:
        for name in _SHADOW_MIGRATIONS:
            cur.execute((MIGRATIONS / name).read_text())


def test_select_target_jobs_rules_on_real_postgres(pg):
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    connection, engine, _ = pg
    _apply_shadow_migration(connection)
    with Session(engine) as s:
        sup_ok = s.execute(text(
            "INSERT INTO public.suppliers (name, extraction_price_format, extraction_qty_format,"
            " extraction_order_pattern) VALUES ('ok','円','在庫','[\"price\"]') RETURNING id"
        )).scalar_one()
        sup_norule = s.execute(text(
            "INSERT INTO public.suppliers (name, extraction_price_format, extraction_qty_format,"
            " extraction_order_pattern) VALUES ('norule','円','','[\"price\"]') RETURNING id"
        )).scalar_one()
        channels = {}
        for key, sup in (("ok", sup_ok), ("norule", sup_norule)):
            channels[key] = s.execute(text(
                "INSERT INTO public.supplier_channels (channel, external_id, is_active, supplier_id)"
                " VALUES ('line', :e, TRUE, :s) RETURNING id"
            ), {"e": key, "s": sup}).scalar_one()

        def add(ch, raw, posted, status, created):
            sm = s.execute(text(
                "INSERT INTO public.source_messages (supplier_channel_id, raw_text, raw_sha256,"
                " is_active, line_posted_at) VALUES (:c, :r, md5(:r), TRUE, :p) RETURNING id"
            ), {"c": channels[ch], "r": raw, "p": posted}).scalar_one()
            return str(s.execute(text(
                "INSERT INTO public.extraction_jobs (source_message_id, status, created_at)"
                " VALUES (:m, :s, :c) RETURNING id"
            ), {"m": sm, "s": status, "c": created}).scalar_one())

        def mark_ran(job_id):
            s.execute(text(
                "INSERT INTO public.extraction_shadow_runs (extraction_job_id, prompt_key,"
                " engine_version, requested_model, status) VALUES (:j, 'k', 'v', 'm', 'completed')"
            ), {"j": job_id})

        dup_old = add("ok", "A B\n\nC", "2026-01-02", "done", "2026-01-03")
        dup_new = add("ok", "A B C", "2026-01-02", "done", "2026-01-04")
        early = add("ok", "early", "2026-01-01", "done", "2026-01-05")
        ran = add("ok", "ran", "2026-01-06", "done", "2026-01-06")
        grp_a = add("ok", "G H", "2026-01-09", "done", "2026-01-09")
        grp_b = add("ok", "G\nH", "2026-01-09", "done", "2026-01-10")
        nd_ran = add("ok", "N O", "2026-01-11", "error", "2026-01-11")
        nd_done = add("ok", "N\nO", "2026-01-11", "done", "2026-01-12")
        add("ok", "pending", "2026-01-07", "pending", "2026-01-07")
        add("norule", "norule", "2026-01-08", "done", "2026-01-08")
        for job_id in (ran, grp_a, nd_ran):
            mark_ran(job_id)
        s.commit()

        ids = sb.select_target_jobs(s, 100)

    assert ids == [early, dup_new]
    assert dup_old not in ids
    assert grp_a not in ids and grp_b not in ids
    assert nd_ran not in ids and nd_done not in ids


def test_ledger_totals_by_run_id_with_real_record_usage_event_sync(pg):
    """本物の record_usage_event_sync が（未commitで）書いた行を、run_id だけで集計できる。"""
    from sqlalchemy.orm import Session

    from app.services.llm_budget import UsageCounts, record_usage_event_sync

    _, engine, _ = pg
    mine, other = str(uuid.uuid4()), str(uuid.uuid4())
    priced = UsageCounts(prompt_tokens=1000, candidates_tokens=100)
    with Session(engine) as s:
        for run_id in (mine, other):
            record_usage_event_sync(
                s, purpose="line_extraction_shadow", model="gemini-3.1-flash-lite",
                sdk="google-genai", counts=priced, extraction_shadow_run_id=run_id,
            )
        # 同じ run でも費用が不明（単価表に無いモデル）の行 → null_cost_rows に数える
        record_usage_event_sync(
            s, purpose="line_extraction_shadow", model="unknown-model", sdk="google-genai",
            counts=priced, extraction_shadow_run_id=mine,
        )
        only_mine = sb.fetch_ledger_totals(s, [mine])
        both = sb.fetch_ledger_totals(s, [mine, other])
        none = sb.fetch_ledger_totals(s, [])
        s.rollback()

    assert only_mine.rows == 1 and only_mine.null_cost_rows == 1
    assert both.rows == 2 and both.cost_usd == 2 * only_mine.cost_usd
    assert only_mine.cost_usd > 0
    assert (none.rows, none.null_cost_rows, none.cost_usd) == (0, 0, Decimal("0"))
