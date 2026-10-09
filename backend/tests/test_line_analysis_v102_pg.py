# ruff: noqa: F811
"""LINE解析の本番エンジン v102 の PostgreSQL 試験（CI の使い捨て PostgreSQL 専用）。Gemini は呼ばない。原文・応答はすべて架空。

K3（要確認の件は配信に出ない）・K7（呼び出し1回ごとに台帳1行）・K8（本番経路と試作版で同じ結果）。
"""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

import app.services.line_analysis_v102_svc as svc
import app.tools.prompt_ab as pab
from app.services import tcg_distribution_svc as distribution
from app.services.llm_budget import UsageCounts
from app.tasks import tcg_extraction as extraction
from tests.test_tcg_work_matching_integration import MIGRATIONS, SCHEMA, seed_products
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

RAW = "商品A\n3BOX@1,000円\n商品B\n未開封 2BOX@2,000円"
# 0 番目は正常、1 番目は価格が原文に無い（落とされる）、2 番目は正常。落とされた件が途中にあっても対応が崩れないことを見る
ITEMS = [
    {"lines": [1, 2], "price": "1,000円", "quantity": "3"},
    {"lines": [3], "price": "7,777円", "quantity": "1"},
    {"lines": [3, 4], "price": "2,000円", "quantity": "2"},
]
RESPONSE = json.dumps({"items": ITEMS, "unsure": [{"line": 2, "candidates": [2, 4]}]}, ensure_ascii=False)
COUNTS = UsageCounts(prompt_tokens=100, candidates_tokens=20, thoughts_tokens=30, total_tokens=150)


@pytest.fixture
def v102(pg, monkeypatch):  # noqa: F811
    """tenant_901 に便Bの列を足し、Gemini・指示書・マスタを差し替える。差し替えた Gemini の呼び出し回数を返す。"""
    connection, _engine, _url = pg
    sql = (MIGRATIONS / "20261009_180000_v102_engine_columns.sql").read_text(encoding="utf-8")
    with connection.cursor() as cur:
        cur.execute(sql.replace("public.extraction_", f"{SCHEMA}.extraction_"))
        cur.execute("INSERT INTO public.units(code,canonical,kubun,is_active) VALUES ('UN9001','BOX','箱系',true) RETURNING id")
        unit_id = cur.fetchone()[0]
        cur.execute("SELECT id, code, canonical, priority, app_kubun, search_kw, exclude_kw FROM public.conditions")
        conditions = cur.fetchall()
    cond_entries = [
        {"cond_id": str(r[0]), "code": r[1], "canonical": r[2], "priority": r[3], "app_kubun": r[4] or "",
         "search_kw": r[5] or "", "exclude_kw": r[6] or "", "match_type": "KEYWORD", "effect": "OUTPUT"}
        for r in conditions
    ]
    masters = {
        "cond_entries": cond_entries, "cond_canonical_to_uuid": {e["canonical"]: e["cond_id"] for e in cond_entries},
        "status_entries": [], "unit_alias_to_info": {"BOX": ("BOX", "箱系")},
    }
    state = SimpleNamespace(calls=0, response=RESPONSE)

    def fake_gemini(*_a, **_k):
        state.calls += 1
        return {"response_text": state.response, "thought_summaries": [], "usage_raw": {}, "usage_counts": COUNTS}

    monkeypatch.setattr(svc, "call_gemini_raw_copy_v8", fake_gemini)
    monkeypatch.setattr(svc, "load_prompt_from_db", lambda _s, _k: "架空の指示書")
    monkeypatch.setattr(svc, "load_v102_masters", lambda _s: (masters, {"BOX": unit_id}))
    seed_products(connection)
    state.masters = masters
    return state


def make_job(pg_fixture, raw: str = RAW) -> tuple[str, str]:
    connection = pg_fixture[0]
    source_id, job_id = str(uuid4()), str(uuid4())
    with connection.cursor() as cur:
        cur.execute(
            f"""INSERT INTO {SCHEMA}.source_messages (id,supplier_channel_id,raw_text,raw_sha256,is_active,received_at,line_posted_at)
                SELECT %s,id,%s,%s,true,now(),now() FROM {SCHEMA}.supplier_channels LIMIT 1""",
            (source_id, raw, uuid4().hex),
        )
        cur.execute(f"INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'pending')", (job_id, source_id))
    return source_id, job_id


def one(pg_fixture, query: str, args: tuple = ()):
    with pg_fixture[0].cursor() as cur:
        cur.execute(query, args)
        return cur.fetchall()


def run_extraction(pg_fixture, job_id):
    with Session(pg_fixture[1]) as session:
        return svc.run_v102_extraction(session, job_id)


def run_analysis(pg_fixture, job_id):
    with Session(pg_fixture[1]) as session:
        return svc.run_v102_analysis(session, job_id)


def test_extraction_saves_skipped_lines_gemini_order_prompt_version_and_one_ledger_row(pg, v102):
    _s, job = make_job(pg)
    result = run_extraction(pg, job)
    items = one(pg, f"SELECT gemini_index, source_lines, line_start, line_end, raw_price, raw_quantity, raw_product_name "
                    f"FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s ORDER BY gemini_index", (job,))
    assert items == [(0, [1, 2], 1, 2, "1,000円", "3", None), (1, [3], 3, 3, "7,777円", "1", None), (2, [3, 4], 3, 4, "2,000円", "2", None)]
    status, version, unsure, reasons = one(pg, f"SELECT status, prompt_version, gemini_unsure, review_reasons FROM {SCHEMA}.extraction_jobs WHERE id=%s", (job,))[0]
    assert (status, result["status"], v102.calls) == ("done", "done", 1)
    assert version.startswith("v102:raw_copy_v101_f_c:") and unsure == [{"line": 2, "candidates": [2, 4]}] and reasons is None
    ledger = one(pg, "SELECT purpose, prompt_tokens FROM public.llm_usage_events WHERE source_ref=%s", (f"extraction_job:{job}",))
    assert ledger == [("line_extraction", 100)]  # K7


def test_unreadable_response_gives_no_items_and_response_unreadable(pg, v102):
    v102.response = "これは JSON ではない"
    _s, job = make_job(pg)
    result = run_extraction(pg, job)
    assert result["status"] == "empty"
    assert one(pg, f"SELECT count(*) FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s", (job,)) == [(0,)]
    assert one(pg, f"SELECT status, review_reasons FROM {SCHEMA}.extraction_jobs WHERE id=%s", (job,)) == [("empty", "response_unreadable")]
    assert one(pg, "SELECT count(*) FROM public.llm_usage_events WHERE source_ref=%s", (f"extraction_job:{job}",)) == [(1,)]
    stats = run_analysis(pg, job)  # 応答が読めなかった理由を、件が無いことの理由で上書きしない
    assert stats["total"] == 0
    assert one(pg, f"SELECT review_reasons FROM {SCHEMA}.extraction_jobs WHERE id=%s", (job,)) == [("response_unreadable",)]


def test_zero_items_is_empty_and_analysis_records_no_items(pg, v102):
    v102.response = json.dumps({"items": []})
    _s, job = make_job(pg)
    assert run_extraction(pg, job)["status"] == "empty"
    run_analysis(pg, job)
    assert one(pg, f"SELECT status, review_reasons FROM {SCHEMA}.extraction_jobs WHERE id=%s", (job,)) == [("empty", "no_items")]


def analysis_rows(pg_fixture, job):
    return one(pg_fixture, f"""SELECT ei.gemini_index, ar.product_id, ar.pid_resolved, ar.unit_canonical, ar.condition_canonical,
        ar.price_normalized, ar.quantity_normalized, ar.review_reasons, ar.engine_version, ar.needs_review
        FROM {SCHEMA}.analysis_results ar JOIN {SCHEMA}.extraction_items ei ON ei.id=ar.extraction_item_id
        WHERE ei.extraction_job_id=%s ORDER BY ei.gemini_index""", (job,))


def test_k8_analysis_results_equal_the_prototype_for_the_same_response(pg, v102):
    _s, job = make_job(pg)
    run_extraction(pg, job)
    stats = run_analysis(pg, job)
    with Session(pg[1]) as session:
        ctx = extraction.load_extraction_context(session, job)
    expected = pab._v102_row_fields(RESPONSE, ctx, v102.masters)["v102_items"]
    rejected = {it["gemini_index"] for it in expected if it.get("rejected")}
    order = [it for it in expected if not it.get("rejected")]
    indexes = [i for i in range(len(ITEMS)) if i not in rejected]
    by_index = {i: it for i, it in zip(indexes, order, strict=True)} | {it["gemini_index"]: it for it in expected if it.get("rejected")}
    rows = analysis_rows(pg, job)
    assert [r[0] for r in rows] == [0, 1, 2] and stats["total"] == 3
    for index, product_id, pid_resolved, unit, condition, price, quantity, reasons, engine, needs_review in rows:
        item = by_index[index]
        kinds = list(dict.fromkeys([r["kind"] for r in [*item["review"], *item["gemini_review"]]]))
        assert (product_id, pid_resolved) == (item.get("product_id"), item.get("product_id") is not None and item["match_status"] == "matched")
        assert unit == (None if item["unit"] == "none" else item["unit"])
        assert condition == (item["condition"] if item["condition"] in v102.masters["cond_canonical_to_uuid"] and item["condition"] != "none" else "FLAG_SINGLE")
        as_float = lambda v: None if v is None else float(v)  # noqa: E731  NUMERIC は Decimal で返る
        assert (as_float(price), as_float(quantity)) == (as_float(item["price_normalized"]), as_float(item["quantity_normalized"]))
        assert (reasons, needs_review, engine) == (",".join(kinds) or None, bool(kinds), svc.V102_ENGINE_VERSION)
    assert rows[1][7] and "price_not_in_lines" in rows[1][7]  # 落とされた件も要確認として残る


def test_analysis_is_idempotent_and_keeps_extraction_items(pg, v102):
    _s, job = make_job(pg)
    run_extraction(pg, job)
    run_analysis(pg, job)
    first = analysis_rows(pg, job)
    run_analysis(pg, job)
    assert analysis_rows(pg, job) == first
    assert one(pg, f"SELECT count(*) FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s", (job,)) == [(3,)]


def test_pipeline_failure_marks_extract_exception_and_keeps_items(pg, v102, monkeypatch):
    _s, job = make_job(pg)
    run_extraction(pg, job)
    monkeypatch.setattr(svc, "parse_v101_response", MagicMock(side_effect=ValueError("boom")))
    stats = run_analysis(pg, job)
    assert stats["pid_resolved"] == 0
    assert one(pg, f"SELECT review_reasons FROM {SCHEMA}.extraction_jobs WHERE id=%s", (job,)) == [("extract_exception",)]
    assert one(pg, f"SELECT count(*) FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s", (job,)) == [(3,)]


def test_k3_items_with_review_reasons_are_not_in_the_distribution_output(pg, v102):
    _s, job = make_job(pg)
    run_extraction(pg, job)
    run_analysis(pg, job)
    product_id = one(pg, "SELECT id FROM public.products ORDER BY id LIMIT 1")[0][0]
    # ほかの条件（商品・単位・価格）を満たしても、理由が付いた件は出ない
    one_sql = f"""UPDATE {SCHEMA}.analysis_results SET pid_resolved=TRUE, unit_resolved=TRUE, product_id=%s,
        price_normalized=1000, is_current=TRUE, exclusion=NULL, condition_canonical='Sealed box', review_reasons=%s"""
    with pg[0].cursor() as cur:
        cur.execute(one_sql, (product_id, "condition_unknown"))

    async def fetch():
        engine = create_async_engine(str(pg[2]))
        try:
            async with AsyncSession(engine) as db:
                return await distribution.fetch_output_rows(db, include_flag_single=True)
        finally:
            await engine.dispose()

    assert asyncio.run(fetch()) == []
