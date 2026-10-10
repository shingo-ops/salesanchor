# ruff: noqa: F811
"""v102 の書き写しを直す API（便C1）の PostgreSQL 試験（CI の使い捨て PostgreSQL 専用）。Gemini は呼ばない。原文・応答はすべて架空。

C-K1（id が変わらない・記録がすべて残る・gemini_index の振り直し）、C-K2（不正な入力は 422 で何も書かない）、
一覧と詳細の形、404 / 409、書き写しを直した後に古い商品の判断が無効になること。
"""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

import app.routers.tcg_v102_posts as router
import app.services.v102_human_decisions_svc as decisions_svc
import app.services.v102_transcription_svc as svc
from app.auth.dependencies import require_super_admin
from app.database import get_db
from tests.test_line_analysis_v102_pg import MIGRATIONS, one, run_analysis, run_extraction
from tests.test_line_analysis_v102_pg import v102 as v102  # noqa: F401  fixture
from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture
from tests.test_v102_human_decisions_pg import (
    RAW_MULTI,
    REASON_NOT_IN_MASTER,
    RESPONSE_MULTI,
    correct,
    fix_product,
    prepare,
    reasons_of,
    state,
)
from tests.test_v102_human_decisions_pg import pf as pf  # noqa: F401  fixture

ADMIN = "admin@example.com"
EXTRACTION_CODE = "ext_code_for_test"  # fix_stage='extraction' の試験用コード
ANALYSIS_CODE = REASON_NOT_IN_MASTER  # fix_stage='analysis'
ZERO = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def tx(pg, pf, monkeypatch):  # noqa: F811
    """書き写しのサービスを試験のスキーマに向け、理由コード表を作る。Celery への積みはモック。"""
    monkeypatch.setattr(svc, "TCG_SCHEMA", SCHEMA)
    enqueued: list[str] = []
    monkeypatch.setattr(router, "enqueue_v102_reanalyze", lambda job_id: enqueued.append(job_id))
    with pg[0].cursor() as cur:
        cur.execute((MIGRATIONS / "20261009_200000_create_review_reason_codes.sql").read_text(encoding="utf-8"))
        cur.execute(
            "INSERT INTO public.review_reason_codes (code, source, fix_stage) VALUES (%s,'gemini','extraction'), (%s,'system','analysis')",
            (EXTRACTION_CODE, ANALYSIS_CODE),
        )
    return SimpleNamespace(pf=pf, enqueued=enqueued)


def prepare_multi(pg_fixture, pf_fixture, *, hours_ago: int = 0) -> tuple[str, str]:
    """4 件(行 [1,2][3,4][5,6][7,8])の投稿を作り、Gemini 段とシステム段を回す。(source_message_id, job_id)。"""
    pf_fixture.response = RESPONSE_MULTI
    source_id, job_id = str(uuid4()), str(uuid4())
    with pg_fixture[0].cursor() as cur:
        cur.execute(
            f"""INSERT INTO {SCHEMA}.source_messages (id,supplier_channel_id,raw_text,raw_sha256,is_active,received_at,line_posted_at)
                SELECT %s,id,%s,%s,true,now() - make_interval(hours => %s),now() FROM {SCHEMA}.supplier_channels LIMIT 1""",
            (source_id, RAW_MULTI, uuid4().hex, hours_ago),
        )
        cur.execute(f"INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'pending')", (job_id, source_id))
    run_extraction(pg_fixture, job_id)
    run_analysis(pg_fixture, job_id)
    return source_id, job_id


def stored_items(pg_fixture, job_id: str) -> list[dict]:
    rows = one(
        pg_fixture,
        f"SELECT id::text, gemini_index, source_lines, line_start, line_end, raw_price, raw_quantity FROM {SCHEMA}.extraction_items "
        f"WHERE extraction_job_id=%s ORDER BY gemini_index, id",
        (job_id,),
    )
    keys = ("id", "gemini_index", "source_lines", "line_start", "line_end", "raw_price", "raw_quantity")
    return [dict(zip(keys, row, strict=True)) for row in rows]


def as_body_item(row: dict, **over) -> dict:
    return {"id": row["id"], "source_lines": row["source_lines"], "raw_price": row["raw_price"], "raw_quantity": row["raw_quantity"], **over}


def corrections(pg_fixture, source_id: str) -> list[tuple]:
    """この投稿の v102_* の記録（古い順）。(件の id, field_name, system_value, human_value, corrected_by)。"""
    return one(
        pg_fixture,
        f"SELECT extraction_item_id::text, field_name, system_value, human_value, corrected_by FROM {SCHEMA}.item_corrections "
        f"WHERE source_message_id=%s AND field_name LIKE 'v102\\_%%' ORDER BY id",
        (source_id,),
    )


def call(pg_fixture, method: str, path: str, payload: dict | None = None):
    """API を本物の PostgreSQL につないで 1 回呼ぶ。(status_code, json)。"""

    async def run():
        engine = create_async_engine(pg_fixture[2])
        app = FastAPI()
        app.include_router(router.router, prefix="/api/v1")

        async def override_db():
            async with AsyncSession(engine) as session:
                yield session

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[require_super_admin] = lambda: SimpleNamespace(email=ADMIN)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.request(method, path, json=payload)
            return response.status_code, response.json()
        finally:
            await engine.dispose()

    return asyncio.run(run())


def put(pg_fixture, job_id: str, source_id: str, items: list[dict]):
    return call(pg_fixture, "PUT", f"/api/v1/tcg/v102/posts/{job_id}/items", {"source_message_id": source_id, "items": items})


# --- C-K1 -------------------------------------------------------------------------------------------


def test_ck1_unchanged_ids_stay_and_every_change_is_recorded_and_indexes_follow_line_order(pg, tx):
    source_id, job_id = prepare_multi(pg, tx.pf)
    before = stored_items(pg, job_id)
    assert [r["source_lines"] for r in before] == [[1, 2], [3, 4], [5, 6], [7, 8]]
    body = [
        as_body_item(before[0]),
        as_body_item(before[1]),
        as_body_item(before[2], raw_price="9,999円"),  # 値が変わる
        {"id": None, "source_lines": [2], "raw_price": "新価格", "raw_quantity": None},  # 追加（行 2 → 並びは 0 番目の次）
        # before[3] は body に無い → 削除
    ]
    status, out = put(pg, job_id, source_id, body)
    assert status == 200 and out["changed"] is True and out["enqueued"] is True
    after = stored_items(pg, job_id)
    new_id = next(r["id"] for r in after if r["id"] not in {b["id"] for b in before})
    assert [r["id"] for r in after] == [before[0]["id"], new_id, before[1]["id"], before[2]["id"]]  # 行番号順
    assert out["item_ids"] == [r["id"] for r in after]
    assert [r["gemini_index"] for r in after] == [0, 1, 2, 3]
    assert after[3]["raw_price"] == "9,999円" and after[1]["source_lines"] == [2] and (after[1]["line_start"], after[1]["line_end"]) == (2, 2)
    assert after[0] == {**before[0], "gemini_index": 0} and after[2] == {**before[1], "gemini_index": 2}  # 変えていない件は 1 文字も変わらない
    assert one(pg, f"SELECT COUNT(*) FROM {SCHEMA}.analysis_results WHERE extraction_item_id=%s", (before[3]["id"],))[0][0] == 0
    rows = corrections(pg, source_id)
    assert len(rows) == 3 and {r[4] for r in rows} == {ADMIN}
    by_field = {r[1]: r for r in rows}
    assert by_field["v102_price"][:4] == (before[2]["id"], "v102_price", before[2]["raw_price"], "9,999円")
    deleted = by_field["v102_item_deleted"]
    assert deleted[0] == before[3]["id"] and deleted[3] == "{}" and json.loads(deleted[2])["id"] == before[3]["id"]
    added = by_field["v102_item_added"]
    assert added[0] == new_id and added[2] == "" and json.loads(added[3])["source_lines"] == [2]
    assert tx.enqueued == [job_id]


def test_ck1_lines_and_quantity_changes_each_get_a_row(pg, tx):
    source_id, job_id = prepare_multi(pg, tx.pf)
    before = stored_items(pg, job_id)
    body = [as_body_item(r) for r in before]
    body[1] = as_body_item(before[1], source_lines=[4, 3], raw_quantity=None)  # 昇順に直して保存される
    status, out = put(pg, job_id, source_id, body)
    assert status == 200 and out["changed"] is True
    assert stored_items(pg, job_id)[1] == {**before[1], "raw_quantity": None}  # [4,3] は昇順の [3,4] と同じ → 行番号は変わらない
    rows = {r[1]: r for r in corrections(pg, source_id)}
    assert set(rows) == {"v102_quantity"}  # [4,3] は [3,4] と同じ集合・昇順で保存 → 行番号の変更は無い
    assert rows["v102_quantity"][2:4] == (before[1]["raw_quantity"], "")
    body[2] = as_body_item(before[2], source_lines=[5])
    assert put(pg, job_id, source_id, body)[1]["changed"] is True
    lines_row = next(r for r in corrections(pg, source_id) if r[1] == "v102_lines")
    assert (json.loads(lines_row[2]), json.loads(lines_row[3])) == ([5, 6], [5])
    item = next(r for r in stored_items(pg, job_id) if r["id"] == before[2]["id"])
    assert (item["source_lines"], item["line_start"], item["line_end"]) == ([5], 5, 5)


def test_unchanged_body_changes_nothing_and_does_not_enqueue(pg, tx):
    source_id, job_id = prepare_multi(pg, tx.pf)
    before = stored_items(pg, job_id)
    status, out = put(pg, job_id, source_id, [as_body_item(r) for r in before])
    assert status == 200 and out == {"changed": False, "item_ids": [r["id"] for r in before], "enqueued": False}
    assert stored_items(pg, job_id) == before and corrections(pg, source_id) == [] and tx.enqueued == []


# --- C-K2 -------------------------------------------------------------------------------------------


def test_ck2_invalid_input_is_422_and_writes_nothing(pg, tx):
    source_id, job_id = prepare_multi(pg, tx.pf)
    other_source, other_job = prepare_multi(pg, tx.pf)
    before = stored_items(pg, job_id)
    other_item = stored_items(pg, other_job)[0]["id"]
    ok = [as_body_item(r) for r in before]

    def with_first(**over) -> list[dict]:
        return [{**ok[0], **over}, *ok[1:]]

    cases = {
        "line_zero": (source_id, with_first(source_lines=[0, 1])),
        "line_over_count": (source_id, with_first(source_lines=[1, 9])),  # 原文は 8 行
        "line_negative": (source_id, with_first(source_lines=[-1])),
        "line_duplicate": (source_id, with_first(source_lines=[2, 2])),
        "line_not_integer": (source_id, with_first(source_lines=["1"])),
        "line_float": (source_id, with_first(source_lines=[1.5])),
        "line_empty": (source_id, with_first(source_lines=[])),
        "price_201": (source_id, with_first(raw_price="x" * 201)),
        "other_post_item": (source_id, [*ok[:3], {"id": other_item, "source_lines": [7], "raw_price": None, "raw_quantity": None}]),
        "unknown_item": (source_id, [*ok[:3], {"id": ZERO, "source_lines": [7], "raw_price": None, "raw_quantity": None}]),
        "duplicate_id": (source_id, [ok[0], ok[0]]),
        "source_mismatch": (other_source, ok),
        "empty_items": (source_id, []),
    }
    for name, (source, items) in cases.items():
        status, _out = put(pg, job_id, source, items)
        assert status == 422, name
        assert stored_items(pg, job_id) == before, name
        assert corrections(pg, source_id) == [], name
        assert tx.enqueued == [], name
    assert other_source and other_job  # 他の投稿の件を宛先にしても、この投稿には何も書かれない（上の assert）


# --- 404 / 409 --------------------------------------------------------------------------------------


def test_missing_and_v6_posts(pg, tx):
    source_id, job_id = prepare_multi(pg, tx.pf)
    with pg[0].cursor() as cur:
        cur.execute(f"UPDATE {SCHEMA}.extraction_jobs SET prompt_version='v6:old' WHERE id=%s", (job_id,))
    before = stored_items(pg, job_id)
    item = {"id": None, "source_lines": [1], "raw_price": None, "raw_quantity": None}
    assert put(pg, job_id, source_id, [item])[0] == 409
    assert call(pg, "GET", f"/api/v1/tcg/v102/posts/{job_id}")[0] == 409
    assert put(pg, ZERO, source_id, [item])[0] == 404
    assert call(pg, "GET", f"/api/v1/tcg/v102/posts/{ZERO}")[0] == 404
    assert call(pg, "GET", "/api/v1/tcg/v102/posts/not-a-uuid")[0] == 404
    assert stored_items(pg, job_id) == before and corrections(pg, source_id) == [] and tx.enqueued == []


# --- GET 詳細 ---------------------------------------------------------------------------------------


def test_detail_shape_lines_and_reasons(pg, tx):
    source_id, job_id = prepare_multi(pg, tx.pf)
    items = stored_items(pg, job_id)
    with pg[0].cursor() as cur:
        cur.execute(f"UPDATE {SCHEMA}.extraction_jobs SET review_reasons=%s, gemini_unsure=%s::jsonb WHERE id=%s",
                    (EXTRACTION_CODE, json.dumps([{"line": 2, "candidates": [2, 4]}]), job_id))
        cur.execute(f"UPDATE {SCHEMA}.analysis_results SET review_reasons=%s WHERE extraction_item_id=%s",
                    (f"{ANALYSIS_CODE},{EXTRACTION_CODE}", items[1]["id"]))
        cur.execute(f"DELETE FROM {SCHEMA}.analysis_results WHERE extraction_item_id=%s", (items[3]["id"],))  # 解析結果が無い件
    status, out = call(pg, "GET", f"/api/v1/tcg/v102/posts/{job_id}")
    assert status == 200 and (out["job_id"], out["source_message_id"]) == (job_id, source_id)
    assert out["lines"] == [{"number": n, "text": t} for n, t in enumerate(RAW_MULTI.split("\n"), 1)]  # 1 始まり・空行も数える・Gemini 側と同じ
    assert out["job_review_reason_details"] == [{"code": EXTRACTION_CODE, "source": "gemini", "fix_stage": "extraction"}]
    assert out["gemini_unsure"] == [{"line": 2, "candidates": [2, 4]}]
    assert [i["id"] for i in out["items"]] == [r["id"] for r in items]  # gemini_index 順
    assert [i["gemini_index"] for i in out["items"]] == [0, 1, 2, 3]
    assert out["items"][1]["review_reason_details"] == [
        {"code": ANALYSIS_CODE, "source": "system", "fix_stage": "analysis"},
        {"code": EXTRACTION_CODE, "source": "gemini", "fix_stage": "extraction"},
    ]
    assert out["items"][3]["review_reason_details"] == []
    expected_provider = one(
        pg,
        f"""SELECT COALESCE(ps.name, '不明') FROM {SCHEMA}.source_messages sm
            LEFT JOIN {SCHEMA}.supplier_channels sc ON sc.id = sm.supplier_channel_id
            LEFT JOIN public.suppliers ps ON ps.id = sc.supplier_id WHERE sm.id=%s""",
        (source_id,),
    )[0][0]
    assert out["provider"] == expected_provider
    assert (out["items"][0]["source_lines"], out["items"][0]["raw_price"]) == (items[0]["source_lines"], items[0]["raw_price"])


# --- GET 一覧 ---------------------------------------------------------------------------------------


def test_list_includes_job_reason_or_extraction_stage_item_reason_only_for_v102(pg, tx):
    posts = {name: prepare_multi(pg, tx.pf, hours_ago=n)[1] for n, name in enumerate(("job_reason", "item_extraction", "item_analysis", "v6", "clean"))}
    with pg[0].cursor() as cur:
        cur.execute(f"UPDATE {SCHEMA}.extraction_jobs SET review_reasons=NULL")
        cur.execute(f"UPDATE {SCHEMA}.extraction_jobs SET review_reasons=%s WHERE id=%s", (ANALYSIS_CODE, posts["job_reason"]))  # (a)
        cur.execute(f"UPDATE {SCHEMA}.analysis_results SET review_reasons=%s WHERE extraction_item_id IN "
                    f"(SELECT id FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s)", (ANALYSIS_CODE, posts["item_analysis"]))
        cur.execute(f"UPDATE {SCHEMA}.analysis_results SET review_reasons=NULL WHERE extraction_item_id IN "
                    f"(SELECT id FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s)", (posts["clean"],))
        first = one(pg, f"SELECT id::text FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s ORDER BY gemini_index", (posts["item_extraction"],))
        cur.execute(f"UPDATE {SCHEMA}.analysis_results SET review_reasons=%s WHERE extraction_item_id=%s", (f" {EXTRACTION_CODE} ,{ANALYSIS_CODE}", first[0][0]))  # (b)
        cur.execute(f"UPDATE {SCHEMA}.analysis_results SET review_reasons=%s WHERE extraction_item_id=%s", (EXTRACTION_CODE, first[1][0]))
        cur.execute(f"UPDATE {SCHEMA}.extraction_jobs SET prompt_version='v6:old', review_reasons=%s WHERE id=%s", (EXTRACTION_CODE, posts["v6"]))
        cur.execute(f"UPDATE {SCHEMA}.analysis_results SET review_reasons=%s WHERE extraction_item_id IN "
                    f"(SELECT id FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s)", (EXTRACTION_CODE, posts["v6"]))
    status, out = call(pg, "GET", "/api/v1/tcg/v102/posts")
    assert status == 200
    listed = {i["job_id"]: i for i in out["items"]}
    assert set(listed) == {posts["job_reason"], posts["item_extraction"]} and out["total"] == 2
    assert listed[posts["job_reason"]]["job_review_reason_details"] == [{"code": ANALYSIS_CODE, "source": "system", "fix_stage": "analysis"}]
    assert (listed[posts["job_reason"]]["item_count"], listed[posts["job_reason"]]["extraction_item_count"]) == (4, 0)
    assert (listed[posts["item_extraction"]]["item_count"], listed[posts["item_extraction"]]["extraction_item_count"]) == (4, 2)
    assert listed[posts["item_extraction"]]["job_review_reason_details"] == []
    assert {"source_message_id", "provider", "line_posted_at"} <= set(listed[posts["job_reason"]])


def test_list_order_paging_and_limits(pg, tx):
    ids = [prepare_multi(pg, tx.pf)[1] for _ in range(3)]
    with pg[0].cursor() as cur:
        cur.execute(f"UPDATE {SCHEMA}.extraction_jobs SET review_reasons=%s WHERE id = ANY(%s::uuid[])", (EXTRACTION_CODE, ids))
        for n, job_id in enumerate(ids):  # ids[0] と ids[1] は同時刻、ids[2] は新しい
            cur.execute(
                f"UPDATE {SCHEMA}.source_messages SET line_posted_at = timestamptz '2026-01-01 00:00:00+00' + make_interval(hours => %s) "
                f"WHERE id = (SELECT source_message_id FROM {SCHEMA}.extraction_jobs WHERE id=%s)",
                (0 if n < 2 else 5, job_id),
            )
    status, out = call(pg, "GET", "/api/v1/tcg/v102/posts")
    expected = [ids[2], *sorted(ids[:2])]  # 新しい順・同時刻は job_id
    assert status == 200 and [i["job_id"] for i in out["items"]] == expected and out["total"] == 3
    status, page = call(pg, "GET", "/api/v1/tcg/v102/posts?limit=1&offset=1")
    assert status == 200 and [i["job_id"] for i in page["items"]] == expected[1:2] and page["total"] == 3
    assert (page["limit"], page["offset"]) == (1, 1)
    for query in ("limit=0", "limit=201", "offset=-1"):
        assert call(pg, "GET", f"/api/v1/tcg/v102/posts?{query}")[0] == 422
    assert call(pg, "GET", "/api/v1/tcg/v102/posts?limit=200")[0] == 200


# --- 書き写しを直した後、古い商品の判断が無効になる（D1 の有効性） --------------------------------------------


def test_after_a_transcription_fix_the_old_product_decision_is_invalid(pg, tx):
    source_id, job_id, item_id = prepare(pg, 0)
    correct(pg, item_id, source_id, "product_id", str(tx.pf.p_a), at=10)  # 直す前の判断（2026-01-01 付近）
    run_analysis(pg, job_id)
    assert state(pg, job_id)["pid_basis"] == "MANUAL"
    with Session(pg[1]) as session:
        assert decisions_svc.load_v102_decisions(session, [item_id])[item_id].product_id == tx.pf.p_a
    current = stored_items(pg, job_id)[0]
    status, out = put(pg, job_id, source_id, [as_body_item(current, raw_quantity="4")])  # 書き写しを直す（今の時刻で記録される）
    assert status == 200 and out["changed"] is True and out["item_ids"] == [item_id]
    assert [r[1] for r in corrections(pg, source_id)] == ["v102_quantity"]
    with Session(pg[1]) as session:
        assert item_id not in decisions_svc.load_v102_decisions(session, [item_id])  # 古い商品の判断は無効
    run_analysis(pg, job_id)
    now = state(pg, job_id)
    assert (now["product_id"], now["pid_basis"]) != (tx.pf.p_a, "MANUAL") and REASON_NOT_IN_MASTER in reasons_of(pg, job_id)


# --- 削除した件が最新だった組は、次に新しい投稿の件が is_current に戻る（G5） ------------------------------------


def test_deleting_the_current_item_restores_the_next_newest_post_for_the_same_product(pg, tx):
    older = prepare(pg, 2)
    newer = prepare(pg, 0)
    fix_product(pg, newer, tx.pf.p_a, at=10)
    fix_product(pg, older, tx.pf.p_a, at=10)
    assert (state(pg, older[1])["is_current"], state(pg, newer[1])["is_current"]) == (False, True)
    source_id, job_id, item_id = newer
    replacement = {"id": None, "source_lines": [1], "raw_price": None, "raw_quantity": None}  # 件は 1 件以上必要
    status, out = put(pg, job_id, source_id, [replacement])
    assert status == 200 and out["changed"] is True and item_id not in out["item_ids"]
    assert one(pg, f"SELECT COUNT(*) FROM {SCHEMA}.analysis_results WHERE extraction_item_id=%s", (item_id,))[0][0] == 0
    assert state(pg, older[1])["is_current"] is True  # 古い投稿の件が最新に戻る
