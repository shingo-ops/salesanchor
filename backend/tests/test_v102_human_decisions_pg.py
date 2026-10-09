# ruff: noqa: F811
"""v102 の人の判断（便D1）の PostgreSQL 試験（CI の使い捨て PostgreSQL 専用）。Gemini は呼ばない。原文・応答はすべて架空。

D-K1（商品の固定）・D-K2（判断なしは不変）・D-K3（確認済みと書き写しの直し）・D-K4（直した件の配信）・D-K5（A→B の付け直し）、
判断の有効性（後・前・同時刻）、review-ack の保存。D-K6 と API の 422 / 409 は test_v102_human_decisions.py。
"""
from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

import app.services.v102_human_decisions_svc as decisions_svc
from app.services import tcg_distribution_svc as distribution
from app.services.extraction_shadow_svc import load_product_entries
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters
from tests.test_line_analysis_v102_pg import analysis_rows, one, run_analysis, run_extraction
from tests.test_line_analysis_v102_pg import v102 as v102  # noqa: F401  fixture
from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

RAW = "ゼッタイ存在しない商品ZZ\n3BOX@1,000円"  # マスタに無い商品名（product_not_in_master になる）
RESPONSE = json.dumps({"items": [{"lines": [1, 2], "price": "1,000円", "quantity": "3"}]}, ensure_ascii=False)
BASE_TIME = "2026-01-01T00:00:00+00:00"  # 判断の時刻は、これからの秒数で決める（時刻の前後を試験で固定するため）
REASON_NOT_IN_MASTER = "product_not_in_master"
REASON_MULTIPLE = "product_multiple"


@pytest.fixture
def pf(pg, v102, monkeypatch):  # noqa: F811
    """v102 の試験の材料に、商品を先に決める流れのマスタを足す。商品 p_a・p_b は seed の商品。"""
    monkeypatch.setattr(decisions_svc, "TCG_SCHEMA", SCHEMA)
    with Session(pg[1]) as session:
        entries = tuple(load_product_entries(session))
    v102.masters["product_first"] = ProductFirstMasters(entries, {str(e.id): "箱系" for e in entries}, {}, ())
    v102.response = RESPONSE
    ids = [r[0] for r in one(pg, "SELECT id FROM public.products ORDER BY id")]
    v102.p_a, v102.p_b = ids[0], ids[1]
    return v102


def prepare(pg_fixture, hours_ago: int) -> tuple[str, str, str]:
    """投稿を1つ作り、Gemini 段とシステム段を回す。(source_message_id, extraction_job_id, 件の id)。"""
    source_id, job_id = str(uuid4()), str(uuid4())
    with pg_fixture[0].cursor() as cur:
        cur.execute(
            f"""INSERT INTO {SCHEMA}.source_messages (id,supplier_channel_id,raw_text,raw_sha256,is_active,received_at,line_posted_at)
                SELECT %s,id,%s,%s,true,now() - make_interval(hours => %s),now() FROM {SCHEMA}.supplier_channels LIMIT 1""",
            (source_id, RAW, uuid4().hex, hours_ago),
        )
        cur.execute(f"INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'pending')", (job_id, source_id))
    run_extraction(pg_fixture, job_id)
    run_analysis(pg_fixture, job_id)
    item_id = one(pg_fixture, f"SELECT id::text FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s", (job_id,))[0][0]
    return source_id, job_id, item_id


def correct(pg_fixture, item_id: str, source_id: str, field: str, value: str, at: int) -> None:
    """item_corrections に1行足す。時刻は BASE_TIME から at 秒後。"""
    with pg_fixture[0].cursor() as cur:
        cur.execute(
            f"""INSERT INTO {SCHEMA}.item_corrections
                (extraction_item_id, source_message_id, field_name, system_value, human_value, corrected_by, corrected_at)
                VALUES (%s, %s, %s, '', %s, 'test', %s::timestamptz + make_interval(secs => %s))""",
            (item_id, source_id, field, value, BASE_TIME, at),
        )


def ack(codes: list[str]) -> str:
    return json.dumps({"v": 1, "codes": codes})


def state(pg_fixture, job_id: str) -> dict:
    keys = ("product_id", "pid_resolved", "pid_basis", "review_reasons", "needs_review", "is_current", "condition_basis")
    row = one(pg_fixture, f"""SELECT {', '.join('ar.' + k for k in keys)} FROM {SCHEMA}.analysis_results ar
        JOIN {SCHEMA}.extraction_items ei ON ei.id=ar.extraction_item_id WHERE ei.extraction_job_id=%s""", (job_id,))[0]
    return dict(zip(keys, row, strict=True))


def reasons_of(pg_fixture, job_id: str) -> list[str]:
    return [r for r in (state(pg_fixture, job_id)["review_reasons"] or "").split(",") if r]


def fix_product(pg_fixture, post: tuple[str, str, str], product_id: int, at: int) -> None:
    """人が商品を決め、残った理由は「このままで良い」にして、システム段をやり直す。"""
    source_id, job_id, item_id = post
    correct(pg_fixture, item_id, source_id, "product_id", str(product_id), at)
    run_analysis(pg_fixture, job_id)
    remaining = reasons_of(pg_fixture, job_id)
    if remaining:
        correct(pg_fixture, item_id, source_id, "review_ack", ack(remaining), at + 1)
        run_analysis(pg_fixture, job_id)


def fetch_output(pg_fixture) -> list:
    async def fetch():
        engine = create_async_engine(pg_fixture[2])
        try:
            async with AsyncSession(engine) as db:
                return await distribution.fetch_output_rows(db, include_flag_single=True)
        finally:
            await engine.dispose()

    return asyncio.run(fetch())


# --- D-K1 -------------------------------------------------------------------------------------------


def test_k1_manual_product_survives_reanalysis_without_product_reasons(pg, pf):
    source_id, job_id, item_id = prepare(pg, 0)
    assert REASON_NOT_IN_MASTER in reasons_of(pg, job_id)  # 判断の前は、商品が無い理由が付く
    correct(pg, item_id, source_id, "product_id", str(pf.p_a), at=10)
    for _ in range(3):
        run_analysis(pg, job_id)
        now = state(pg, job_id)
        assert (now["product_id"], now["pid_resolved"], now["pid_basis"]) == (pf.p_a, True, "MANUAL")
        assert REASON_NOT_IN_MASTER not in reasons_of(pg, job_id) and REASON_MULTIPLE not in reasons_of(pg, job_id)


# --- D-K2 -------------------------------------------------------------------------------------------


def test_k2_without_decisions_for_the_item_the_result_is_unchanged(pg, pf):
    source_id, job_id, _item_id = prepare(pg, 0)
    before = analysis_rows(pg, job_id)
    other_item = str(uuid4())  # 別の件への判断・関係のない欄は、この件の結果を変えない
    correct(pg, other_item, source_id, "product_id", str(pf.p_a), at=10)
    correct(pg, other_item, source_id, "review_ack", ack([REASON_NOT_IN_MASTER]), at=11)
    run_analysis(pg, job_id)
    assert analysis_rows(pg, job_id) == before


# --- D-K3 と判断の有効性 ---------------------------------------------------------------------------


def test_k3_ack_survives_reanalysis_and_transcription_fix_brings_reason_back(pg, pf):
    source_id, job_id, item_id = prepare(pg, 0)
    correct(pg, item_id, source_id, "review_ack", ack([REASON_NOT_IN_MASTER]), at=10)
    for _ in range(2):
        run_analysis(pg, job_id)
        assert REASON_NOT_IN_MASTER not in reasons_of(pg, job_id)
    correct(pg, item_id, source_id, "v102_price", "1,100円", at=20)  # 書き写しを直した → それより前の確認済みは無効
    run_analysis(pg, job_id)
    assert REASON_NOT_IN_MASTER in reasons_of(pg, job_id)
    correct(pg, item_id, source_id, "review_ack", ack([REASON_NOT_IN_MASTER]), at=30)  # 直した後の確認済みは有効
    run_analysis(pg, job_id)
    assert REASON_NOT_IN_MASTER not in reasons_of(pg, job_id)


@pytest.mark.parametrize(
    ("ack_at", "transcription_at", "is_valid"),
    [(20, 10, True), (10, 20, False), (10, 10, False), (10, None, True)],
    ids=["ack_after_transcription", "ack_before_transcription", "same_time", "no_transcription"],
)
def test_decision_is_valid_only_when_after_the_last_transcription_fix(pg, pf, ack_at, transcription_at, is_valid):
    source_id, job_id, item_id = prepare(pg, 0)
    correct(pg, item_id, source_id, "review_ack", ack([REASON_NOT_IN_MASTER]), at=ack_at)
    if transcription_at is not None:
        correct(pg, item_id, source_id, "v102_lines", "[1, 2]", at=transcription_at)
    with Session(pg[1]) as session:
        loaded = decisions_svc.load_v102_decisions(session, [item_id])
    assert (item_id in loaded) is is_valid
    if is_valid:
        assert loaded[item_id].ack_codes == frozenset({REASON_NOT_IN_MASTER})


def test_latest_valid_decision_wins_and_invalid_ones_are_ignored(pg, pf):
    source_id, _job_id, item_id = prepare(pg, 0)
    correct(pg, item_id, source_id, "product_id", str(pf.p_a), at=10)
    correct(pg, item_id, source_id, "product_id", str(pf.p_b), at=20)
    correct(pg, item_id, source_id, "review_ack", "not json", at=30)
    with Session(pg[1]) as session:
        loaded = decisions_svc.load_v102_decisions(session, [item_id])
    assert loaded[item_id].product_id == pf.p_b and loaded[item_id].ack_codes == frozenset()


def test_condition_review_decision_needs_an_active_condition(pg, pf):
    source_id, _job_id, item_id = prepare(pg, 0)
    active, inactive = one(pg, "SELECT id FROM public.conditions WHERE is_active ORDER BY id LIMIT 1")[0][0], 987654
    correct(pg, item_id, source_id, "condition_review", json.dumps({"v": 1, "decision": "correct", "condition_id": str(inactive)}), at=10)
    with Session(pg[1]) as session:
        assert decisions_svc.load_v102_decisions(session, [item_id]) == {}
    correct(pg, item_id, source_id, "condition_review", json.dumps({"v": 1, "decision": "correct", "condition_id": str(active)}), at=20)
    with Session(pg[1]) as session:
        assert decisions_svc.load_v102_decisions(session, [item_id])[item_id].condition_id == active


def test_condition_review_decision_sets_manual_condition_and_drops_condition_reasons(pg, pf):
    source_id, job_id, item_id = prepare(pg, 0)
    target = one(pg, "SELECT id FROM public.conditions WHERE is_active ORDER BY id LIMIT 1")[0][0]
    correct(pg, item_id, source_id, "condition_review", json.dumps({"v": 1, "decision": "confirm", "condition_id": str(target)}), at=10)
    run_analysis(pg, job_id)
    assert state(pg, job_id)["condition_basis"] == "MANUAL_CONDITION_REVIEW"
    assert one(pg, f"SELECT condition_id FROM {SCHEMA}.analysis_results ar JOIN {SCHEMA}.extraction_items ei "
                   f"ON ei.id=ar.extraction_item_id WHERE ei.extraction_job_id=%s", (job_id,)) == [(target,)]
    assert "condition_unknown" not in reasons_of(pg, job_id) and "condition_multiple_candidates" not in reasons_of(pg, job_id)


# --- D-K4 -------------------------------------------------------------------------------------------


def test_k4_fixed_item_enters_distribution_only_when_its_post_is_the_latest(pg, pf):
    older = prepare(pg, 2)
    newer = prepare(pg, 0)
    fix_product(pg, newer, pf.p_a, at=10)
    fix_product(pg, older, pf.p_a, at=10)  # 古い投稿を直しても、記録だけ残して配信には出ない
    assert (state(pg, older[1])["is_current"], state(pg, newer[1])["is_current"]) == (False, True)
    assert state(pg, older[1])["pid_basis"] == "MANUAL" and state(pg, older[1])["needs_review"] is False
    assert len(fetch_output(pg)) == 1  # 最新の投稿の1件だけ


# --- D-K5 -------------------------------------------------------------------------------------------


def test_k5_moving_a_product_from_a_to_b_restores_the_next_newest_post_for_a(pg, pf):
    older = prepare(pg, 2)
    newer = prepare(pg, 0)
    fix_product(pg, newer, pf.p_a, at=10)
    fix_product(pg, older, pf.p_a, at=10)
    assert (state(pg, older[1])["is_current"], state(pg, newer[1])["is_current"]) == (False, True)
    fix_product(pg, newer, pf.p_b, at=30)  # 新しい投稿を A → B に直す
    assert state(pg, newer[1])["product_id"] == pf.p_b and state(pg, newer[1])["is_current"] is True
    assert state(pg, older[1])["is_current"] is True  # A の組で次に新しい投稿(古い方)が最新に戻る


# --- review-ack の保存 -------------------------------------------------------------------------------


def test_save_review_ack_writes_one_row_and_the_loader_reads_it(pg, pf):
    source_id, job_id, item_id = prepare(pg, 0)

    async def save() -> int:
        engine = create_async_engine(pg[2])
        try:
            async with AsyncSession(engine) as db:
                return await decisions_svc.save_review_ack(
                    db, extraction_item_id=item_id, source_message_id=source_id,
                    codes=[REASON_NOT_IN_MASTER, REASON_NOT_IN_MASTER], corrected_by="admin@example.com",
                )
        finally:
            await engine.dispose()

    assert asyncio.run(save()) == 1
    rows = one(pg, f"SELECT field_name, human_value, system_value, corrected_by FROM {SCHEMA}.item_corrections "
                   f"WHERE extraction_item_id=%s", (item_id,))
    assert len(rows) == 1 and rows[0][0] == "review_ack" and rows[0][3] == "admin@example.com"
    assert json.loads(rows[0][1]) == {"v": 1, "codes": [REASON_NOT_IN_MASTER]}
    assert REASON_NOT_IN_MASTER in rows[0][2]  # system_value は保存時点の review_reasons
    run_analysis(pg, job_id)
    assert REASON_NOT_IN_MASTER not in reasons_of(pg, job_id)
