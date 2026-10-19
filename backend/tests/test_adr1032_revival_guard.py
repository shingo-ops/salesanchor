# ruff: noqa: F811
"""ADR-1032 復活止めの PostgreSQL 試験（CI の使い捨て PostgreSQL 専用）。原文・値はすべて架空。

docs/handoff/revival-guard/sandbox/scenarios.sql の場面を実コード（_merge_supplier_products・_load_current_pairs・
apply_transcription_edit）で再現する。期待値は docs/handoff/revival-guard/logs/sandbox_guard.txt と同じ。
再解析は run_v102_analysis の「解析だけやり直す」経路（既存の行の商品・状態を上書きし is_current は触らない）のまね。
"""
from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

from app.services import line_analysis_v102_svc as svc
from app.services import tcg_analyzer_svc as analyzer
from app.services import v102_transcription_svc as tsvc
from tests.test_line_analysis_v102_pg import one
from tests.test_line_analysis_v102_pg import v102 as v102  # noqa: F401  fixture
from tests.test_same_post_rows_pg import _add_job, _add_row, _current
from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

pytestmark = pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required")


@pytest.fixture
def ids(pg, v102):  # noqa: F811
    products = [r[0] for r in one(pg, "SELECT id FROM public.products ORDER BY id")]
    conditions = [r[0] for r in one(pg, "SELECT id FROM public.conditions ORDER BY id")]
    assert len(products) >= 2 and len(conditions) >= 6
    return SimpleNamespace(A=products[0], B=products[1], single=conditions[0], error=conditions[1], box=conditions[2],
                           case=conditions[3], sealed=conditions[4], damaged=conditions[5])


def rejoin(pg_fixture, job: str, **kwargs) -> None:
    """is_current の付け直しを 1 回呼ぶ。"""
    with Session(pg_fixture[1]) as session:
        analyzer._merge_supplier_products(session, job, SCHEMA, **kwargs)


def reanalyze(pg_fixture, job: str, changes: dict[str, tuple[int, int]]) -> None:
    """v102 の「解析だけやり直す」経路のまね（line_analysis_v102_svc.run_v102_analysis）。

    前の組と現行だった組を書く前に読み → 既存の行の商品・状態を上書き（is_current は触らない）
    → extra_pairs と prior_current_pairs を実コードと同じ形で渡して付け直す。changes は {行の id: (product_id, condition_id)}。
    """
    with Session(pg_fixture[1]) as session:
        previous = svc._load_resolved_pairs(session, job)
        prior_current = svc._load_current_pairs(session, job) if previous else None
        session.rollback()
    with pg_fixture[0].cursor() as cur:
        for result_id, (product, condition) in changes.items():
            cur.execute(f"UPDATE {SCHEMA}.analysis_results SET product_id=%s, condition_id=%s WHERE id=%s", (product, condition, result_id))
    rejoin(pg_fixture, job, extra_pairs=previous, prior_current_pairs=prior_current)


def states(pg_fixture, rows: dict[str, str]) -> dict[str, bool]:
    return {name: _current(pg_fixture, result_id) for name, result_id in rows.items()}


def test_s1_first_analysis_keeps_older_row_of_another_condition(pg, ids):
    old_job, new_job = _add_job(pg, 5), _add_job(pg, 1)
    old = _add_row(pg, old_job, ids.A, ids.error)
    new = _add_row(pg, new_job, ids.A, ids.single)
    rejoin(pg, new_job)  # 初回は控え無し。別の状態の古い行は残る
    assert states(pg, {"old": old, "new": new}) == {"old": True, "new": True}


def test_s8_older_row_of_same_condition_is_hidden_and_other_condition_stays(pg, ids):
    old_job, new_job = _add_job(pg, 5), _add_job(pg, 1)
    old_box, old_case = _add_row(pg, old_job, ids.A, ids.box), _add_row(pg, old_job, ids.A, ids.case)
    new = _add_row(pg, new_job, ids.A, ids.box)
    rejoin(pg, new_job)
    assert states(pg, {"old_box": old_box, "old_case": old_case, "new": new}) == {"old_box": False, "old_case": True, "new": True}


def test_r1_reanalysis_of_newest_post_does_not_revive_older_row(pg, ids):
    old_job, new_job = _add_job(pg, 5), _add_job(pg, 1)
    old = _add_row(pg, old_job, ids.A, ids.error)
    new = _add_row(pg, new_job, ids.A, ids.error)
    rejoin(pg, new_job)
    reanalyze(pg, new_job, {new: (ids.A, ids.single)})  # A/Error → A/Single
    assert states(pg, {"old": old, "new": new}) == {"old": False, "new": True}


def test_r2_reanalysis_moving_a_to_b_restores_older_row_of_a(pg, ids):
    old_job, new_job = _add_job(pg, 5), _add_job(pg, 1)
    old = _add_row(pg, old_job, ids.A, ids.single)
    new = _add_row(pg, new_job, ids.A, ids.single)
    rejoin(pg, new_job)
    reanalyze(pg, new_job, {new: (ids.B, ids.single)})  # A → B
    assert states(pg, {"old": old, "new": new}) == {"old": True, "new": True}


def _r3_setup(pg, ids, y_product: int, y_condition: int):
    z_job = _add_job(pg, 9)
    x_job, y_job = _add_job(pg, 5), _add_job(pg, 1)
    z = _add_row(pg, z_job, ids.A, ids.error)
    x_error = _add_row(pg, x_job, ids.A, ids.error)
    x_damaged = _add_row(pg, x_job, ids.A, ids.damaged)
    y = _add_row(pg, y_job, y_product, y_condition)
    for job in (z_job, x_job, y_job):
        rejoin(pg, job)
    return z, x_job, x_error, x_damaged, y


def test_r3a_older_post_reanalysis_with_newer_post_having_same_product_is_not_current(pg, ids):
    _z, x_job, single, damaged, y = _r3_setup(pg, ids, ids.A, ids.box)
    reanalyze(pg, x_job, {single: (ids.A, ids.single)})  # (A,Error) → (A,Single)
    assert states(pg, {"x_single": single, "x_damaged": damaged, "y": y}) == {"x_single": False, "x_damaged": True, "y": True}


def test_r3b_older_post_reanalysis_without_same_product_in_newer_post_is_current(pg, ids):
    _z, x_job, single, damaged, y = _r3_setup(pg, ids, ids.B, ids.box)
    reanalyze(pg, x_job, {single: (ids.A, ids.single)})
    assert states(pg, {"x_single": single, "x_damaged": damaged, "y": y}) == {"x_single": True, "x_damaged": True, "y": True}


def test_r3c_oldest_post_row_hidden_by_older_post_does_not_revive(pg, ids):
    z, x_job, x_error, _damaged, _y = _r3_setup(pg, ids, ids.A, ids.box)
    assert _current(pg, z) is False
    reanalyze(pg, x_job, {x_error: (ids.A, ids.single)})  # (A,Error) を手放しても、最古の z の (A,Error) は戻らない
    assert _current(pg, z) is False


def _r5_setup(pg, ids):
    old_job, new_job = _add_job(pg, 5), _add_job(pg, 1)
    old_sealed, old_damaged = _add_row(pg, old_job, ids.A, ids.sealed), _add_row(pg, old_job, ids.A, ids.damaged)
    new = _add_row(pg, new_job, ids.A, ids.sealed)
    rejoin(pg, old_job)
    rejoin(pg, new_job)
    return old_job, new_job, {"old_sealed": old_sealed, "old_damaged": old_damaged, "new": new}


def test_r5_sealed_does_not_return_but_damaged_stays(pg, ids):
    _old_job, new_job, rows = _r5_setup(pg, ids)
    reanalyze(pg, new_job, {rows["new"]: (ids.A, ids.single)})  # A/Sealed → A/Single
    assert states(pg, rows) == {"old_sealed": False, "old_damaged": True, "new": True}


def test_r6_reanalysis_without_change_changes_nothing(pg, ids):
    _old_job, new_job, rows = _r5_setup(pg, ids)
    reanalyze(pg, new_job, {rows["new"]: (ids.A, ids.sealed)})
    assert states(pg, rows) == {"old_sealed": False, "old_damaged": True, "new": True}


def test_d1b_deleting_an_item_through_the_service_restores_older_row(pg, ids, monkeypatch):
    """件の削除は実コード（v102_transcription_svc.apply_transcription_edit）を呼ぶ。削除は revival_guard=False で付け直す。"""
    monkeypatch.setattr(tsvc, "TCG_SCHEMA", SCHEMA)
    old_job, new_job = _add_job(pg, 5), _add_job(pg, 1)
    with pg[0].cursor() as cur:  # load_job は v102 の投稿だけ通す（v102_transcription_svc.py:201-202）
        cur.execute(f"UPDATE {SCHEMA}.extraction_jobs SET prompt_version='v102:test' WHERE id=%s", (new_job,))
    old = _add_row(pg, old_job, ids.A, ids.single)
    doomed = _add_row(pg, new_job, ids.A, ids.single)  # 行 1
    kept = _add_row(pg, new_job, ids.A, ids.box)  # 行 2
    rejoin(pg, old_job)
    rejoin(pg, new_job)
    assert states(pg, {"old": old, "doomed": doomed, "kept": kept}) == {"old": False, "doomed": True, "kept": True}
    with pg[0].cursor() as cur:
        cur.execute(
            f"UPDATE {SCHEMA}.source_messages SET raw_text=%s WHERE id=(SELECT source_message_id FROM {SCHEMA}.extraction_jobs WHERE id=%s)",
            ("架空1\n架空2", new_job),
        )
    kept_item = one(pg, f"SELECT extraction_item_id::text FROM {SCHEMA}.analysis_results WHERE id=%s", (kept,))[0][0]

    async def run():
        engine = create_async_engine(pg[2])
        try:
            async with AsyncSession(engine) as db:
                job = await tsvc.load_job(db, new_job)
                return await tsvc.apply_transcription_edit(db, job, [tsvc.ItemInput(kept_item, [2], None, None)], "test")
        finally:
            await engine.dispose()

    assert asyncio.run(run()).changed is True
    assert one(pg, f"SELECT count(*) FROM {SCHEMA}.analysis_results WHERE id=%s", (doomed,))[0][0] == 0
    assert states(pg, {"old": old, "kept": kept}) == {"old": True, "kept": True}


def test_extraction_restart_path_has_no_prior_and_behaves_like_first_analysis(pg, ids):
    """抽出からやり直す経路（tasks/tcg_extraction.py:470-476）は行が作り直され、控えも extra_pairs も空。初回（S1）と同じ扱い。
    既知の限界: この経路での R3a 型（古い投稿の自分の行）は復活止めが働かず TRUE のまま。"""
    x_job, y_job = _add_job(pg, 5), _add_job(pg, 1)
    y = _add_row(pg, y_job, ids.A, ids.box)
    rejoin(pg, y_job)
    x_new = _add_row(pg, x_job, ids.A, ids.single)  # 作り直された新しい件の行（is_current は既定 TRUE）
    rejoin(pg, x_job, prior_current_pairs=None)
    assert states(pg, {"x_new": x_new, "y": y}) == {"x_new": True, "y": True}


def test_idempotent_second_pass_without_prior_changes_nothing(pg, ids):
    old_job, new_job, rows = _r5_setup(pg, ids)
    reanalyze(pg, new_job, {rows["new"]: (ids.A, ids.single)})
    before = states(pg, rows)
    for job in (old_job, new_job):  # 全投稿を控え無しでもう1回
        rejoin(pg, job)
    assert states(pg, rows) == before
