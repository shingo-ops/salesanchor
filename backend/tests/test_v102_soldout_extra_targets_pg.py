# ruff: noqa: F811
"""v102 の〆（完売）で複数の商品・状態を完売にする（便2-2）の PostgreSQL 試験（CI の使い捨て PostgreSQL 専用）。Gemini は呼ばない。

書き込み（親の行は先頭の相手の状態・2つ目以降は analysis_soldout_extra_targets）、やり直しで古い相手が消えること、
ADR-158 のマージ（相手の組の古い在庫の行が is_current=FALSE・〆より新しい在庫で戻る・消すと戻る・表が空なら今と同じ）。原文・応答はすべて架空。
"""
from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

import app.services.line_analysis_v102_svc as svc
import app.services.v102_transcription_svc as transcription
from app.services import tcg_analyzer_svc as analyzer
from tests.test_line_analysis_v102_pg import make_job, one, run_analysis, run_extraction
from tests.test_line_analysis_v102_pg import v102 as v102  # noqa: F401  fixture
from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

_ORIGINAL_PIPELINE = svc.run_v102_pipeline
_COMPUTED_AT = "2026-10-10 00:00:00+00"


@pytest.fixture
def ids(pg, v102):  # noqa: F811
    """seed の商品 2 つと、状態 3 つ（public.conditions）の id。"""
    products = [r[0] for r in one(pg, "SELECT id FROM public.products ORDER BY id")]
    conditions = {r[1]: r[0] for r in one(pg, "SELECT id, canonical FROM public.conditions")}
    return SimpleNamespace(p1=products[0], p2=products[1], box=conditions["Sealed box"], case=conditions["Case"], nos=conditions["No shrink box"])


def _target(product_id: int, condition_id: int, line: int) -> dict:
    return {"product_id": product_id, "condition_id": condition_id, "ref_message_id": str(uuid4()), "ref_line": line}


def _inject(monkeypatch, targets: list[dict]) -> None:
    """パイプラインの結果の最初の受理した件を、〆の相手が決まった件（matched_soldout_ref）にする。"""

    def wrapped(*args, **kwargs):
        out = _ORIGINAL_PIPELINE(*args, **kwargs)
        items = list(out["v102_items"])
        index = next(i for i, it in enumerate(items) if not it.get("rejected"))
        items[index] = {**items[index], "product_id": targets[0]["product_id"], "match_status": "matched_soldout_ref", "soldout_targets": targets}
        return {**out, "v102_items": items}

    monkeypatch.setattr(svc, "run_v102_pipeline", wrapped)


def _parent(pg_fixture, job: str) -> tuple:
    return one(pg_fixture, f"""SELECT ar.id::text, ar.product_id, ar.condition_id, ar.condition_basis, ar.pid_basis
        FROM {SCHEMA}.analysis_results ar JOIN {SCHEMA}.extraction_items ei ON ei.id = ar.extraction_item_id
        WHERE ei.extraction_job_id=%s AND ei.gemini_index=0""", (job,))[0]


def _extras(pg_fixture, job: str) -> list[tuple]:
    return one(pg_fixture, f"""SELECT et.product_id, et.condition_id, et.ref_message_id::text, et.ref_line
        FROM {SCHEMA}.analysis_soldout_extra_targets et
        JOIN {SCHEMA}.analysis_results ar ON ar.id = et.analysis_result_id
        JOIN {SCHEMA}.extraction_items ei ON ei.id = ar.extraction_item_id
        WHERE ei.extraction_job_id=%s ORDER BY et.product_id, et.condition_id""", (job,))


# --- 書き込み ------------------------------------------------------------------------------------


def test_parent_row_takes_the_first_target_and_the_others_go_to_the_table(pg, ids, monkeypatch):
    targets = [_target(ids.p1, ids.box, 1), _target(ids.p1, ids.case, 2), _target(ids.p2, ids.box, 3)]
    _inject(monkeypatch, targets)
    _s, job = make_job(pg)
    run_extraction(pg, job)
    run_analysis(pg, job)
    _id, product_id, condition_id, basis, pid_basis = _parent(pg, job)
    assert (product_id, condition_id, basis, pid_basis) == (ids.p1, ids.box, "SOLDOUT_REF", "V102:matched_soldout_ref")
    expected = sorted((t["product_id"], t["condition_id"], t["ref_message_id"], t["ref_line"]) for t in targets[1:])
    assert _extras(pg, job) == expected


def test_rerun_replaces_the_old_extra_targets_and_keeps_the_parent_row(pg, ids, monkeypatch):
    _inject(monkeypatch, [_target(ids.p1, ids.box, 1), _target(ids.p1, ids.case, 2), _target(ids.p2, ids.box, 3)])
    _s, job = make_job(pg)
    run_extraction(pg, job)
    run_analysis(pg, job)
    first = _parent(pg, job)
    assert len(_extras(pg, job)) == 2
    _inject(monkeypatch, [_target(ids.p1, ids.nos, 1), _target(ids.p2, ids.nos, 2)])
    run_analysis(pg, job)
    assert _parent(pg, job)[0] == first[0] and _parent(pg, job)[2] == ids.nos
    assert [(p, c) for p, c, _m, _l in _extras(pg, job)] == [(ids.p2, ids.nos)]
    _inject(monkeypatch, [_target(ids.p1, ids.nos, 1)])
    run_analysis(pg, job)
    assert _extras(pg, job) == []


def test_a_human_condition_decision_wins_and_writes_no_extra_target(pg, ids, monkeypatch):
    _inject(monkeypatch, [_target(ids.p1, ids.box, 1), _target(ids.p2, ids.box, 2)])
    monkeypatch.setattr(svc, "load_v102_decisions", lambda _session, item_ids: {item_ids[0]: svc.Decisions(condition_id=ids.case)})
    _s, job = make_job(pg)
    run_extraction(pg, job)
    run_analysis(pg, job)
    _id, _product, condition_id, basis, _pid_basis = _parent(pg, job)
    assert (condition_id, basis) == (ids.case, svc.CONDITION_BASIS_MANUAL)
    assert _extras(pg, job) == []


# --- ADR-158 のマージ ------------------------------------------------------------------------------


def _add_post(pg_fixture, hours_ago: float, pairs: list[tuple[int, int]]) -> SimpleNamespace:
    """投稿を1つ、pairs の (商品, 状態) ごとに件と解析結果を1つずつ直接入れる。"""
    source_id, job_id = str(uuid4()), str(uuid4())
    items, results = [], []
    with pg_fixture[0].cursor() as cur:
        cur.execute(
            f"""INSERT INTO {SCHEMA}.source_messages (id,supplier_channel_id,raw_text,raw_sha256,is_active,received_at,line_posted_at)
                SELECT %s,id,'架空',%s,true,now() - make_interval(secs => %s),now() - make_interval(secs => %s)
                FROM {SCHEMA}.supplier_channels LIMIT 1""",
            (source_id, uuid4().hex, hours_ago * 3600, hours_ago * 3600),
        )
        cur.execute(f"INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'done')", (job_id, source_id))
        for index, (product_id, condition_id) in enumerate(pairs):
            item_id, result_id = str(uuid4()), str(uuid4())
            cur.execute(
                f"""INSERT INTO {SCHEMA}.extraction_items (id,extraction_job_id,line_start,line_end,source_lines,gemini_index,created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,now())""",
                (item_id, job_id, index + 1, index + 1, [index + 1], index),
            )
            cur.execute(
                f"""INSERT INTO {SCHEMA}.analysis_results (id,extraction_item_id,product_id,pid_resolved,unit_resolved,condition_id,needs_review,engine_version,computed_at)
                    VALUES (%s,%s,%s,true,false,%s,false,'test',%s)""",
                (result_id, item_id, product_id, condition_id, _COMPUTED_AT),
            )
            items.append(item_id)
            results.append(result_id)
    return SimpleNamespace(job=job_id, items=items, results=results)


def _add_extra(pg_fixture, result_id: str, product_id: int, condition_id: int) -> None:
    with pg_fixture[0].cursor() as cur:
        cur.execute(
            f"""INSERT INTO {SCHEMA}.analysis_soldout_extra_targets (analysis_result_id,product_id,condition_id,ref_message_id,ref_line)
                VALUES (%s,%s,%s,%s,1)""",
            (result_id, product_id, condition_id, str(uuid4())),
        )


def _merge(pg_fixture, job: str, extra_pairs=()) -> None:
    with Session(pg_fixture[1]) as session:
        analyzer._merge_supplier_products(session, job, SCHEMA, extra_pairs=extra_pairs)


def _current(pg_fixture, result_id: str) -> bool:
    return one(pg_fixture, f"SELECT is_current FROM {SCHEMA}.analysis_results WHERE id=%s", (result_id,))[0][0]


def test_merge_demotes_the_older_stock_row_of_an_extra_target(pg, ids):
    older = _add_post(pg, 5, [(ids.p2, ids.box)])
    sold = _add_post(pg, 3, [(ids.p1, ids.box)])
    _add_extra(pg, sold.results[0], ids.p2, ids.box)
    _merge(pg, sold.job)
    assert (_current(pg, older.results[0]), _current(pg, sold.results[0])) == (False, True)


def test_merge_keeps_a_stock_post_newer_than_the_soldout_current(pg, ids):
    older = _add_post(pg, 5, [(ids.p2, ids.box)])
    sold = _add_post(pg, 3, [(ids.p1, ids.box)])
    newer = _add_post(pg, 1, [(ids.p2, ids.box)])
    _add_extra(pg, sold.results[0], ids.p2, ids.box)
    _merge(pg, sold.job)
    assert (_current(pg, older.results[0]), _current(pg, newer.results[0])) == (False, True)


def test_merge_without_extra_rows_is_unchanged(pg, ids):
    older = _add_post(pg, 5, [(ids.p2, ids.box)])
    sold = _add_post(pg, 3, [(ids.p1, ids.box)])
    _merge(pg, sold.job)
    assert (_current(pg, older.results[0]), _current(pg, sold.results[0])) == (True, True)  # 組が違えば触らない


def test_merge_gives_a_real_row_of_the_same_post_priority_over_a_virtual_row(pg, ids):
    sold = _add_post(pg, 3, [(ids.p1, ids.box), (ids.p2, ids.box)])  # 同じ投稿・同じ計算時刻
    _add_extra(pg, sold.results[0], ids.p2, ids.box)
    _merge(pg, sold.job)
    assert _current(pg, sold.results[1]) is True


def test_deleting_the_soldout_row_removes_its_extras_and_restores_the_older_stock_row(pg, ids):
    older = _add_post(pg, 5, [(ids.p2, ids.box)])
    sold = _add_post(pg, 3, [(ids.p1, ids.box)])
    _add_extra(pg, sold.results[0], ids.p2, ids.box)
    _merge(pg, sold.job)
    assert _current(pg, older.results[0]) is False
    with Session(pg[1]) as session:
        removed = session.execute(
            text(transcription._PAIRS_OF_ITEMS_SQL.format(schema=SCHEMA)), {"ids": [sold.items[0]]}
        ).fetchall()
    assert sorted((int(r[0]), int(r[1])) for r in removed) == sorted([(ids.p1, ids.box), (ids.p2, ids.box)])  # 相手の組も返る
    with pg[0].cursor() as cur:
        cur.execute(f"DELETE FROM {SCHEMA}.analysis_results WHERE id=%s", (sold.results[0],))
    assert one(pg, f"SELECT count(*) FROM {SCHEMA}.analysis_soldout_extra_targets") == [(0,)]  # CASCADE
    _merge(pg, sold.job, extra_pairs=[(int(r[0]), int(r[1])) for r in removed])
    assert _current(pg, older.results[0]) is True


def test_run_analysis_demotes_the_older_stock_row_and_a_rerun_restores_it(pg, ids, monkeypatch):
    older = _add_post(pg, 5, [(ids.p2, ids.box)])
    _inject(monkeypatch, [_target(ids.p1, ids.case, 1), _target(ids.p2, ids.box, 2)])
    _s, job = make_job(pg)
    run_extraction(pg, job)
    run_analysis(pg, job)
    assert _current(pg, older.results[0]) is False
    _inject(monkeypatch, [_target(ids.p1, ids.case, 1)])  # やり直しで相手が減る → 前の相手の組を付け直す
    run_analysis(pg, job)
    assert _current(pg, older.results[0]) is True
