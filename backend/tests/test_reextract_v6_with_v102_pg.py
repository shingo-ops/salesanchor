# ruff: noqa: F811
"""v6 -> v102 やり直しの道具の PostgreSQL 試験（CI の使い捨て PostgreSQL 専用）。Gemini は呼ばない。原文・応答はすべて架空。

設計: docs/handoff/reextract-v6-with-v102/design.md §7
Gemini（svc.call_gemini_raw_copy_v8）と指示書・マスタは、test_line_analysis_v102_pg.py の fixture で差し替える。
"""
from __future__ import annotations

import io
import json
import os
import re
import stat
import subprocess
import time
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

import app.services.line_analysis_v102_svc as svc
import app.tools.reextract_v6_with_v102 as tool
from app.services import tcg_analyzer_svc as analyzer
from app.tasks import tcg_extraction as extraction
from tests.test_line_analysis_v102_pg import RAW, RESPONSE, SCHEMA, make_job, one
from tests.test_line_analysis_v102_pg import pg as pg  # noqa: F401  fixture
from tests.test_line_analysis_v102_pg import v102 as v102  # noqa: F401  fixture
from tests.test_tcg_work_matching_integration import prohibit_live_gemini as prohibit_live_gemini  # noqa: F401  autouse fixture

V6 = tool.V6_PROMPT_VERSION
REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def env(pg, v102, monkeypatch, tmp_path):  # noqa: F811
    """道具を使い捨て DB に向ける。除外ルールを1件入れ、通知と自動配信を見張る。"""
    _connection, engine, _url = pg
    monkeypatch.setattr(tool, "new_session", lambda: Session(engine))
    monkeypatch.setenv(svc.ENGINE_ENV, svc.ENGINE_V102)
    with pg[0].cursor() as cur:
        # 試験用のスキーマ構築は analysis_results の FK を全部外す。本番と同じ ON DELETE CASCADE を戻す
        cur.execute(f"ALTER TABLE {SCHEMA}.analysis_results ADD CONSTRAINT fk_ar_items_test FOREIGN KEY (extraction_item_id) "
                    f"REFERENCES {SCHEMA}.extraction_items (id) ON DELETE CASCADE")
        cur.execute("CREATE TABLE public.knowledge_rules (id serial PRIMARY KEY, category text, pattern_type text, pattern text, is_active boolean DEFAULT TRUE)")
    one(pg, "INSERT INTO public.knowledge_rules (category, pattern_type, pattern) VALUES ('message_exclude', 'substring', '除外ワード') RETURNING 1")
    state = v102
    state.published = 0
    state.out_dir = tmp_path / "work"
    monkeypatch.setattr(extraction, "_publish_review_changed", lambda: setattr(state, "published", state.published + 1))

    def forbidden():
        pytest.fail("道具は自動配信を呼んではいけません")

    monkeypatch.setattr(extraction, "_enqueue_auto_distribute", forbidden)
    return state


def run_execute(env, **kw) -> int:
    args = {"only_job": None, "limit": None, "max_cost": Decimal("11"), "stop_after_errors": 5, "timeout_sec": 300}
    args.update(kw)
    return tool.execute(env.out_dir, **args)


def records(env) -> list[dict]:
    path = env.out_dir / "records.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def categories(env, mode: str | None = None) -> dict[str, str]:
    return {r["job_id"]: r["category"] for r in records(env) if mode is None or r["mode"] == mode}


def make_v6(pg_fixture, raw: str = RAW, *, days_ago: float = 0, status: str = "done", pair: tuple[int, int] | None = None,
            recv_null: bool = False, results: bool = True) -> tuple[str, str]:
    """v6 の job。items を2件持つ。pair があれば、その (product_id, condition_id) の解析結果を1件持つ。"""
    source_id, job_id = make_job(pg_fixture, raw)
    with pg_fixture[0].cursor() as cur:
        cur.execute(
            f"""UPDATE {SCHEMA}.source_messages SET received_at = now() - make_interval(secs => %s),
                line_posted_at = now() - make_interval(secs => %s) WHERE id = %s""",
            (days_ago * 86400, days_ago * 86400, source_id),
        )
        if recv_null:
            cur.execute(f"UPDATE {SCHEMA}.source_messages SET received_at = NULL WHERE id = %s", (source_id,))
        cur.execute(f"UPDATE {SCHEMA}.extraction_jobs SET prompt_version = %s, status = %s WHERE id = %s", (V6, status, job_id))
        for n in (1, 2):
            item_id = str(uuid4())
            cur.execute(
                f"""INSERT INTO {SCHEMA}.extraction_items (id, extraction_job_id, line_start, line_end, source_lines, created_at)
                    VALUES (%s, %s, %s, %s, ARRAY[%s], now())""",
                (item_id, job_id, n, n, n),
            )
            if results and pair is not None and n == 1:
                cur.execute(
                    f"""INSERT INTO {SCHEMA}.analysis_results
                        (id, extraction_item_id, product_id, pid_resolved, unit_canonical, unit_resolved, condition_id, condition_canonical,
                         price_normalized, quantity_normalized, needs_review, engine_version, computed_at)
                        VALUES (%s, %s, %s, true, 'Box', true, %s, 'Sealed box', 1000, 1, false, 'v6', now())""",
                    (str(uuid4()), item_id, pair[0], pair[1]),
                )
    return source_id, job_id


def pair_ids(pg_fixture) -> tuple[int, int]:
    return (one(pg_fixture, "SELECT id FROM public.products WHERE product_code='PM0123'")[0][0],
            one(pg_fixture, "SELECT id FROM public.conditions WHERE code='CN0003'")[0][0])


def job_row(pg_fixture, job_id: str):
    return one(pg_fixture, f"SELECT prompt_version, status, review_reasons FROM {SCHEMA}.extraction_jobs WHERE id=%s", (job_id,))[0]


def item_ids(pg_fixture, job_id: str) -> list[str]:
    return [str(r[0]) for r in one(pg_fixture, f"SELECT id FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s ORDER BY id", (job_id,))]


def current_flags(pg_fixture, job_id: str) -> list[bool]:
    return [r[0] for r in one(pg_fixture, f"""SELECT ar.is_current FROM {SCHEMA}.analysis_results ar
        JOIN {SCHEMA}.extraction_items ei ON ei.id = ar.extraction_item_id WHERE ei.extraction_job_id=%s""", (job_id,))]


def merge(pg_fixture, job_id: str) -> None:
    with Session(pg_fixture[1]) as session:
        analyzer._merge_supplier_products(session, job_id, SCHEMA)
        session.commit()


def counts_snapshot(pg_fixture) -> tuple:
    return tuple(one(pg_fixture, f"SELECT count(*) FROM {SCHEMA}.{t}")[0][0]
                 for t in ("extraction_jobs", "extraction_items", "analysis_results")) + (
        one(pg_fixture, "SELECT count(*) FROM public.llm_usage_events")[0][0],)


# ---------------------------------------------------------------------------
# dry-run・対象の選び方
# ---------------------------------------------------------------------------


def test_dry_run_writes_no_database_rows_and_lists_exclusions(pg, env, capsys):
    _s, ok = make_v6(pg)
    make_v6(pg, status="filtered")
    make_v6(pg, recv_null=True)
    _s, corrected = make_v6(pg)
    one(pg, f"INSERT INTO {SCHEMA}.item_corrections(extraction_item_id, source_message_id, field_name, human_value, corrected_by) "
            f"SELECT ei.id, ej.source_message_id, 'product_id', 'x', 't' FROM {SCHEMA}.extraction_items ei "
            f"JOIN {SCHEMA}.extraction_jobs ej ON ej.id = ei.extraction_job_id WHERE ej.id=%s LIMIT 1 RETURNING 1", (corrected,))
    _s, filtered_by_rule = make_v6(pg, raw="除外ワード 在庫なし")
    before = counts_snapshot(pg)
    assert tool.dry_run(env.out_dir, None) == tool.EXIT_OK
    assert counts_snapshot(pg) == before  # DB には書かない
    assert (env.out_dir / "order.txt").read_text().split() == [ok]
    reasons = dict(line.split("\t")[::-1] for line in (env.out_dir / "excluded.tsv").read_text().splitlines())
    assert sorted(reasons) == ["filtered", "item_corrections", "prefilter", "received_at_null"]
    assert filtered_by_rule in reasons.values()
    assert env.calls == 0 and env.published == 0


def test_targets_exclude_v102_and_are_ordered_oldest_first(pg, env):
    _s, new = make_v6(pg, days_ago=1)
    _s, old = make_v6(pg, days_ago=5)
    _s, mid = make_v6(pg, days_ago=3)
    _s, done_v102 = make_v6(pg, days_ago=4)
    one(pg, f"UPDATE {SCHEMA}.extraction_jobs SET prompt_version='v102:x' WHERE id=%s RETURNING 1", (done_v102,))
    with Session(pg[1]) as session:
        targets, excluded = tool.classify_v6_jobs(session, with_prefilter=True)
    assert [j for j, _ in targets] == [old, mid, new] and excluded == []


def test_prefilter_hit_is_skipped_and_stays_v6(pg, env):
    _s, hit = make_v6(pg, raw="除外ワード 在庫なし")
    _s, ok = make_v6(pg)
    assert run_execute(env) == tool.EXIT_OK
    assert categories(env) == {ok: "done"} | {hit: "skip_prefilter"} or categories(env)[hit] == "skip_prefilter"
    assert job_row(pg, hit)[0] == V6 and env.calls == 1
    assert job_row(pg, ok)[0].startswith("v102:")


def test_recheck_right_before_processing_excludes_late_corrections_and_late_rules(pg, env):
    _s, corrected = make_v6(pg)
    _s, ruled = make_v6(pg)
    smid = one(pg, f"SELECT source_message_id FROM {SCHEMA}.extraction_jobs WHERE id=%s", (corrected,))[0][0]
    eid = item_ids(pg, corrected)[0]
    one(pg, f"INSERT INTO {SCHEMA}.item_corrections(extraction_item_id, source_message_id, field_name, human_value, corrected_by) "
            f"VALUES (%s, %s, 'product_id', 'x', 't') RETURNING 1", (eid, smid))
    one(pg, f"UPDATE {SCHEMA}.source_messages SET raw_text = '除外ワード' WHERE id = (SELECT source_message_id FROM {SCHEMA}.extraction_jobs WHERE id=%s) RETURNING 1", (ruled,))
    # 選んだ後に条件が付いた、という状況を作るため、process_job を直接呼ぶ
    assert tool.process_job(corrected, env.out_dir, 300)[0] == "skip_corrections"
    assert tool.process_job(ruled, env.out_dir, 300)[0] == "skip_prefilter"
    assert env.calls == 0 and job_row(pg, corrected)[0] == V6 and job_row(pg, ruled)[0] == V6


# ---------------------------------------------------------------------------
# 区分の判定
# ---------------------------------------------------------------------------


def test_done_job_becomes_v102_with_pairs_file_one_publish_and_no_auto_distribute(pg, env):
    pair = pair_ids(pg)
    _s, job = make_v6(pg, pair=pair)
    assert run_execute(env) == tool.EXIT_OK
    assert categories(env) == {job: "done"}
    assert job_row(pg, job)[0].startswith("v102:") and len(item_ids(pg, job)) == 3
    assert tool.read_pairs(env.out_dir, job) == [pair]  # 抽出の前に控えた v6 の組
    assert env.published == 1  # 要確認画面へ1回
    assert (env.out_dir / "started_at.txt").exists()


def test_gemini_exception_is_gemini_error_and_keeps_v6_items(pg, env, monkeypatch):
    _s, job = make_v6(pg)
    before = item_ids(pg, job)

    def boom(*_a, **_k):
        raise RuntimeError("Gemini v8 API 呼び出し失敗: 架空")

    monkeypatch.setattr(svc, "call_gemini_raw_copy_v8", boom)
    assert run_execute(env) == tool.EXIT_OK
    assert categories(env) == {job: "gemini_error"}
    assert job_row(pg, job)[0] == V6 and item_ids(pg, job) == before


def test_unreadable_response_is_unreadable_and_counts_as_a_failure(pg, env):
    env.response = "これは JSON ではない"
    _s, job = make_v6(pg)
    assert run_execute(env) == tool.EXIT_OK
    assert categories(env) == {job: "unreadable"}
    assert job_row(pg, job)[2] == "response_unreadable"
    assert "unreadable" in tool.FAILURE_CATEGORIES


def test_analysis_pipeline_failure_is_analysis_error(pg, env, monkeypatch):
    _s, job = make_v6(pg)

    def boom(*_a, **_k):
        raise ValueError("架空の解析の失敗")

    monkeypatch.setattr(svc, "run_v102_pipeline", boom)
    assert run_execute(env) == tool.EXIT_OK
    assert categories(env) == {job: "analysis_error"}
    assert job_row(pg, job)[2] == svc.REASON_EXTRACT_EXCEPTION


def test_exception_after_the_extraction_commit_is_read_back_and_classified(pg, env, monkeypatch):
    _s, job = make_v6(pg)
    real = svc.run_v102_extraction

    def commit_then_fail(session, job_id, **kw):
        real(session, job_id, **kw)
        raise RuntimeError("確定した後の例外")

    monkeypatch.setattr(svc, "run_v102_extraction", commit_then_fail)
    assert run_execute(env) == tool.EXIT_OK
    assert categories(env) == {job: "done"}  # gemini_error と数えない
    assert "確定後の例外" in records(env)[0]["note"]
    assert len(one(pg, f"SELECT 1 FROM {SCHEMA}.analysis_results ar JOIN {SCHEMA}.extraction_items ei ON ei.id = ar.extraction_item_id "
                       f"WHERE ei.extraction_job_id=%s", (job,))) == 3


# ---------------------------------------------------------------------------
# is_current（M3）・--repair
# ---------------------------------------------------------------------------


def two_posts_sharing_a_pair(pg):
    """古い投稿 P1（v102 風の行）と新しい投稿 P2（v6）が、同じ (商品, 状態) の組を持つ。P2 が現行。"""
    pair = pair_ids(pg)
    _s, older = make_v6(pg, days_ago=2, pair=pair)
    _s, newer = make_v6(pg, days_ago=1, pair=pair)
    one(pg, f"UPDATE {SCHEMA}.extraction_jobs SET prompt_version='v102:older' WHERE id=%s RETURNING 1", (older,))
    merge(pg, newer)
    assert current_flags(pg, newer) == [True] and current_flags(pg, older) == [False]
    return older, newer, pair


def test_pair_only_v6_had_returns_to_the_previous_post_as_current(pg, env):
    older, newer, _pair = two_posts_sharing_a_pair(pg)
    assert run_execute(env) == tool.EXIT_OK  # v102 の新しい解析は、この組を出さない（商品が決まらない）
    assert categories(env) == {newer: "done"}
    assert current_flags(pg, older) == [True]  # M3: v6 だけの組の現行が、一つ前の投稿へ戻る
    assert tool.read_pairs(env.out_dir, newer) is not None


def test_repair_reattaches_a_job_that_stopped_before_the_merge(pg, env, monkeypatch):
    older, newer, pair = two_posts_sharing_a_pair(pg)
    real_merge = tool._merge_pairs
    monkeypatch.setattr(tool, "_merge_pairs", lambda *_a, **_k: "merge_error")  # 解析の確定後・付け直しの前に止まった
    run_execute(env)
    assert categories(env) == {newer: "analysis_error"} and current_flags(pg, older) == [False]
    monkeypatch.setattr(tool, "_merge_pairs", real_merge)
    assert tool.repair(env.out_dir, env.out_dir / "order.txt", max_cost=Decimal("11"), stop_after_errors=5, timeout_sec=300) == tool.EXIT_OK
    assert categories(env, "repair") == {newer: "done"} and current_flags(pg, older) == [True]


def test_repair_reruns_the_analysis_for_a_job_left_without_results(pg, env, monkeypatch):
    _s, job = make_v6(pg)
    real = svc.run_v102_analysis
    monkeypatch.setattr(svc, "run_v102_analysis", lambda *_a, **_k: (_ for _ in ()).throw(ValueError("止まった")))
    run_execute(env)
    assert categories(env) == {job: "analysis_error"}
    state = tool.read_job_state(job)
    assert state["v102"] and state["items"] == 3 and state["results"] == 0  # 取り残し（K7 の (a)）
    monkeypatch.setattr(svc, "run_v102_analysis", real)
    assert tool.repair(env.out_dir, env.out_dir / "order.txt", max_cost=Decimal("11"), stop_after_errors=5, timeout_sec=300) == tool.EXIT_OK
    assert categories(env, "repair") == {job: "done"} and tool.read_job_state(job)["results"] == 3
    assert env.calls == 1  # --repair の解析は Gemini を呼ばない


def test_repair_reextracts_unreadable_at_most_twice(pg, env):
    env.response = "これは JSON ではない"
    _s, job = make_v6(pg)
    run_execute(env)
    assert env.calls == 1 and categories(env) == {job: "unreadable"}
    ids = env.out_dir / "order.txt"

    def run_repair() -> int:
        return tool.repair(env.out_dir, ids, max_cost=Decimal("11"), stop_after_errors=50, timeout_sec=300)

    run_repair()
    run_repair()
    assert env.calls == 3  # 初回 + 再抽出2回
    run_repair()
    assert env.calls == 3  # 3回目は Gemini を呼ばない
    assert categories(env, "repair")[job] == "repair_exhausted"
    assert json.loads((env.out_dir / "repair_counts.json").read_text()) == {job: 2}


def test_repair_reextracts_unreadable_and_succeeds_when_the_response_is_readable(pg, env):
    env.response = "これは JSON ではない"
    _s, job = make_v6(pg)
    run_execute(env)
    env.response = RESPONSE
    assert tool.repair(env.out_dir, env.out_dir / "order.txt", max_cost=Decimal("11"), stop_after_errors=5, timeout_sec=300) == tool.EXIT_OK
    assert categories(env, "repair") == {job: "done"} and job_row(pg, job)[2] != "response_unreadable"


# ---------------------------------------------------------------------------
# 止める仕組み
# ---------------------------------------------------------------------------


def test_consecutive_failures_stop_at_five(pg, env, monkeypatch):
    for _ in range(7):
        make_v6(pg)

    def boom(*_a, **_k):
        raise RuntimeError("架空")

    monkeypatch.setattr(svc, "call_gemini_raw_copy_v8", boom)
    assert run_execute(env) == tool.EXIT_LIMIT
    assert len(records(env)) == 5 and set(categories(env).values()) == {"gemini_error"}


def test_a_success_resets_the_consecutive_failure_count(pg, env, monkeypatch):
    for _ in range(4):
        make_v6(pg)
    calls = {"n": 0}
    real = svc.call_gemini_raw_copy_v8

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] % 2:
            raise RuntimeError("架空")
        return real(*a, **k)

    monkeypatch.setattr(svc, "call_gemini_raw_copy_v8", flaky)
    assert run_execute(env, stop_after_errors=2) == tool.EXIT_OK
    assert len(records(env)) == 4


def test_cost_limit_stops(pg, env):
    for _ in range(4):
        make_v6(pg)
    assert run_execute(env, max_cost=Decimal("0.00015")) == tool.EXIT_LIMIT  # 1件 0.0001
    assert len(records(env)) == 2


def test_null_cost_stops(pg, env, monkeypatch):
    for _ in range(3):
        make_v6(pg)
    monkeypatch.setattr(tool, "total_cost", lambda *_a: (Decimal(0), 1))
    assert run_execute(env) == tool.EXIT_LIMIT
    assert records(env) == []  # 最初の確かめで止まり、1件も流さない
    assert env.calls == 0


def test_cost_is_counted_from_started_at_across_processes(pg, env):
    _s, done_before = make_v6(pg)
    _s, job = make_v6(pg)
    env.out_dir.mkdir(parents=True)
    tool.write_text_durable(env.out_dir / "started_at.txt", "2000-01-01T00:00:00+00:00\n")
    tool.write_text_durable(env.out_dir / "order.txt", f"{done_before}\n{job}\n")
    one(pg, "INSERT INTO public.llm_usage_events (id, purpose, model, sdk, cost_usd, source_ref) "
            "VALUES (%s, 'line_extraction', 'm', 'google-genai', 9, %s) RETURNING 1", (str(uuid4()), f"extraction_job:{done_before}"))
    assert run_execute(env, max_cost=Decimal("3")) == tool.EXIT_LIMIT  # 前のプロセスの分が数えられている
    assert env.calls == 0
    since = tool.ensure_started_at(env.out_dir)
    with Session(pg[1]) as session:
        assert tool.total_cost(session, [done_before, job], since)[0] == Decimal("9")


def test_timeout_is_a_base_exception_and_becomes_gemini_error(pg, env, monkeypatch):
    assert not issubclass(tool.GeminiTimeout, Exception)  # 台帳などの `except Exception` に飲まれない
    _s, job = make_v6(pg)
    before = item_ids(pg, job)

    def slow(*_a, **_k):
        time.sleep(5)

    monkeypatch.setattr(svc, "call_gemini_raw_copy_v8", slow)
    monkeypatch.setattr(tool, "ALARM_MARGIN_SEC", 0)
    started = time.monotonic()
    assert tool.extract_one(job, 1) == ("gemini_error", "timeout")
    assert time.monotonic() - started < 4
    assert job_row(pg, job)[0] == V6 and item_ids(pg, job) == before
    assert signal_alarm_cleared()


def signal_alarm_cleared() -> bool:
    import signal

    return signal.alarm(0) == 0  # 残っていれば、残り秒数が返る


def test_pairs_that_cannot_be_written_stop_the_extraction(pg, env, monkeypatch):
    _s, job = make_v6(pg)

    def cannot(*_a, **_k):
        raise PermissionError("書けない")

    monkeypatch.setattr(tool, "write_pairs", cannot)
    run_execute(env)
    assert categories(env) == {job: "pairs_error"} and env.calls == 0 and job_row(pg, job)[0] == V6


def test_preflight_fails_with_exit_2(pg, env, monkeypatch):
    make_v6(pg)
    monkeypatch.setenv(svc.ENGINE_ENV, svc.ENGINE_V6)
    assert run_execute(env) == tool.EXIT_CONFIG and env.calls == 0
    monkeypatch.setenv(svc.ENGINE_ENV, svc.ENGINE_V102)
    one(pg, "UPDATE public.knowledge_rules SET is_active = FALSE RETURNING 1")
    assert tool.dry_run(env.out_dir, None) == tool.EXIT_CONFIG


def test_job_id_and_limit_narrow_the_run(pg, env):
    _s, first = make_v6(pg, days_ago=3)
    _s, second = make_v6(pg, days_ago=2)
    assert run_execute(env, limit=1) == tool.EXIT_OK
    assert categories(env) == {first: "done"} and job_row(pg, second)[0] == V6


# ---------------------------------------------------------------------------
# Gemini client の時間切れ
# ---------------------------------------------------------------------------


def test_build_genai_client_sets_http_timeout_in_milliseconds(monkeypatch):
    from google import genai

    seen = {}
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    monkeypatch.delenv("GEMINI_PROXY_URL", raising=False)
    monkeypatch.setattr(genai, "Client", lambda **kw: seen.update(kw) or "client")
    assert tool.build_genai_client(300) == "client"
    assert seen["http_options"].timeout == 300000
    monkeypatch.setenv("GEMINI_PROXY_URL", "http://proxy.invalid:3128")
    tool.build_genai_client(300)
    assert seen["http_options"].client_args == {"proxy": "http://proxy.invalid:3128"}


def test_install_gemini_timeout_replaces_only_the_client_factory(monkeypatch):
    from app.services import gemini_extraction_svc as gem

    monkeypatch.setattr(gem, "_get_genai_client", gem._get_genai_client)  # 戻すために登録
    built = {}
    monkeypatch.setattr(tool, "build_genai_client", lambda sec: built.setdefault("sec", sec) or "c")
    tool.install_gemini_timeout(123)
    assert gem._get_genai_client() == 123 and built == {"sec": 123}


# ---------------------------------------------------------------------------
# 戻し（--rollback-from）
# ---------------------------------------------------------------------------


def dump_csv(pg_fixture, directory: Path, job_ids: list[str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    ids = "{" + ",".join(job_ids) + "}"
    queries = {
        "extraction_jobs": f"SELECT * FROM {SCHEMA}.extraction_jobs WHERE id = ANY('{ids}'::uuid[])",
        "extraction_items": f"SELECT * FROM {SCHEMA}.extraction_items WHERE extraction_job_id = ANY('{ids}'::uuid[])",
        "analysis_results": f"SELECT ar.* FROM {SCHEMA}.analysis_results ar JOIN {SCHEMA}.extraction_items ei "
                            f"ON ei.id = ar.extraction_item_id WHERE ei.extraction_job_id = ANY('{ids}'::uuid[])",
    }
    with pg_fixture[0].cursor() as cur:
        for name, query in queries.items():
            buffer = io.StringIO()
            cur.copy_expert(f"COPY ({query}) TO STDOUT WITH (FORMAT csv, HEADER true, NULL '\\N')", buffer)
            (directory / f"{name}.csv").write_text(buffer.getvalue(), encoding="utf-8")


def snapshot(pg_fixture, job_id: str) -> dict:
    return {
        "job": one(pg_fixture, f"SELECT row_to_json(j)::jsonb - 'extracted_at' FROM {SCHEMA}.extraction_jobs j WHERE id=%s", (job_id,))[0][0],
        "items": one(pg_fixture, f"SELECT coalesce(jsonb_agg(row_to_json(i)::jsonb ORDER BY id), '[]'::jsonb) FROM {SCHEMA}.extraction_items i WHERE extraction_job_id=%s", (job_id,))[0][0],
        "results": one(pg_fixture, f"SELECT coalesce(jsonb_agg(row_to_json(a)::jsonb ORDER BY a.id), '[]'::jsonb) FROM {SCHEMA}.analysis_results a "
                                   f"JOIN {SCHEMA}.extraction_items i ON i.id = a.extraction_item_id WHERE i.extraction_job_id=%s", (job_id,))[0][0],
    }


def test_rollback_restores_items_results_and_job_columns(pg, env, tmp_path):
    pair = pair_ids(pg)
    _s, job = make_v6(pg, pair=pair)
    merge(pg, job)
    before = snapshot(pg, job)
    backup = tmp_path / "backups"
    dump_csv(pg, backup, [job])
    run_execute(env)
    assert job_row(pg, job)[0].startswith("v102:")
    assert tool.rollback(env.out_dir, backup, only_job=None, execute_writes=False) == tool.EXIT_OK  # dry-run は書かない
    assert job_row(pg, job)[0].startswith("v102:") and categories(env, "rollback") == {job: "would_rollback"}
    assert tool.rollback(env.out_dir, backup, only_job=None, execute_writes=True) == tool.EXIT_OK
    assert categories(env, "rollback")[job] == "rolled_back"
    after = snapshot(pg, job)
    assert after["items"] == before["items"] and after["results"] == before["results"]
    assert {k: v for k, v in after["job"].items() if k != "extracted_at"} == before["job"]
    assert current_flags(pg, job) == [True]


def test_rollback_skips_a_job_with_item_corrections_and_isolates_a_failing_job(pg, env, tmp_path):
    pair = pair_ids(pg)
    _s, corrected = make_v6(pg, pair=pair, days_ago=3)
    _s, broken = make_v6(pg, pair=pair, days_ago=2)
    _s, fine = make_v6(pg, pair=pair, days_ago=1)
    backup = tmp_path / "backups"
    dump_csv(pg, backup, [corrected, broken, fine])
    run_execute(env)
    smid = one(pg, f"SELECT source_message_id FROM {SCHEMA}.extraction_jobs WHERE id=%s", (corrected,))[0][0]
    one(pg, f"INSERT INTO {SCHEMA}.item_corrections(extraction_item_id, source_message_id, field_name, human_value, corrected_by) "
            f"VALUES (%s, %s, 'product_id', 'x', 't') RETURNING 1", (item_ids(pg, corrected)[0], smid))
    # broken の控えは analysis_results の product_id が存在しない商品を指す（INSERT が FK で失敗する）
    path = backup / "analysis_results.csv"
    header, rows = tool._read_csv(path)
    broken_items = {r["id"] for r in tool._read_csv(backup / "extraction_items.csv")[1] if r["extraction_job_id"] == broken}
    lines = path.read_text(encoding="utf-8").splitlines()
    out = [lines[0]]
    column = header.index("product_id")
    import csv as _csv
    for raw, row in zip(lines[1:], rows, strict=True):
        if row["extraction_item_id"] in broken_items:
            cells = next(_csv.reader([raw]))
            cells[column] = "999999999"
            buf = io.StringIO()
            _csv.writer(buf, lineterminator="").writerow(cells)
            raw = buf.getvalue()
        out.append(raw)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    before_broken = snapshot(pg, broken)
    tool.rollback(env.out_dir, backup, only_job=None, execute_writes=True)
    result = categories(env, "rollback")
    assert result == {corrected: "skip_corrections", broken: "rollback_error", fine: "rolled_back"}
    assert job_row(pg, corrected)[0].startswith("v102:") and job_row(pg, fine)[0] == V6
    assert snapshot(pg, broken) == before_broken and job_row(pg, broken)[0].startswith("v102:")  # その job だけ rollback


def test_rollback_job_id_selects_one_job(pg, env, tmp_path):
    _s, first = make_v6(pg, days_ago=2)
    _s, second = make_v6(pg, days_ago=1)
    backup = tmp_path / "backups"
    dump_csv(pg, backup, [first, second])
    run_execute(env)
    tool.rollback(env.out_dir, backup, only_job=second, execute_writes=True)
    assert job_row(pg, second)[0] == V6 and job_row(pg, first)[0].startswith("v102:")


# ---------------------------------------------------------------------------
# ホストの繰り返し
# ---------------------------------------------------------------------------


def fake_docker(tmp_path: Path, codes: list[int]) -> tuple[Path, Path]:
    """呼ばれた引数を記録する偽の docker。`compose run` の終了コードは codes を順に返す（check の分も含む）。"""
    log = tmp_path / "docker.log"
    counter = tmp_path / "counter"
    counter.write_text("0")
    script = tmp_path / "docker"
    script.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "$@" >> {log}\n'
        'if [ "$1" = "compose" ]; then\n'
        f'  n=$(cat {counter}); echo $((n+1)) > {counter}\n'
        f'  codes=({" ".join(str(c) for c in codes)})\n'
        '  exit "${codes[$n]:-0}"\n'
        "fi\nexit 0\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script, log


def run_loop(tmp_path: Path, codes: list[int]) -> tuple[int, list[str]]:
    script, log = fake_docker(tmp_path, codes)
    result = subprocess.run(
        ["bash", str(REPO / "scripts/ops/reextract-v6-loop.sh")],
        env={**os.environ, "DOCKER_BIN": str(script), "WORKDIR": str(tmp_path / "w"), "DATE_TAG": "20261016", "MAX_ROUNDS": "3"},
        capture_output=True, text=True, timeout=60,
    )
    return result.returncode, log.read_text().splitlines() if log.exists() else []


def test_container_names_never_start_with_the_deploy_removal_prefix(tmp_path):
    code, calls = run_loop(tmp_path, [0, 0, 0])
    assert code == 0
    names = [m.group(1) for line in calls if (m := re.search(r"--name (\S+)", line))]
    assert names and all(re.fullmatch(r"reextract-v6-\d{8}-\d+", n) for n in names)
    assert not any(n.startswith("astro-webapp-celery-worker") for n in names)
    assert all("--no-deps" in line and " -T " in line and "-v " in line for line in calls if line.startswith("compose run"))


def test_loop_stops_on_exit_3_and_continues_after_137(tmp_path):
    code, calls = run_loop(tmp_path, [0, 3])  # check 0, execute 3
    assert code == 3 and sum("--execute" in c for c in calls) == 1
    code, calls = run_loop(tmp_path, [0, 137, 0, 0])  # check, execute 137 -> 次の回, execute 0, repair 0
    assert code == 0
    names = [m.group(1) for line in calls if (m := re.search(r"--name (\S+)", line))]
    assert "reextract-v6-20261016-1" in names and "reextract-v6-20261016-2" in names
    assert sum("--repair" in c for c in calls) == 1


def test_help_runs():
    result = subprocess.run(["python3", "-m", "app.tools.reextract_v6_with_v102", "--help"], capture_output=True, text=True,
                            cwd=Path(__file__).resolve().parents[1], timeout=120)
    assert result.returncode == 0 and "--rollback-from" in result.stdout
