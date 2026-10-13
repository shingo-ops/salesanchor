# ruff: noqa: F811
"""発送日の専用列 ship_ja が違う件が ADR-158 のマージ（_merge_supplier_products）で全部 current になることの PostgreSQL 試験（CI の使い捨て PostgreSQL 専用）。

K2（同じ投稿で発送日が違えば全部 current）・K4（新しい投稿は古い投稿を発送日が違っても外す）。
同じ投稿の同じ組の行はどれも current（#4169・ADR-158:26）なので、発送日が同じ件の重複も1件にはしない。商品・原文はすべて架空。
"""
from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from tests.test_line_analysis_v102_pg import v102 as v102  # noqa: F401  fixture
from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture
from tests.test_v102_soldout_extra_targets_pg import _COMPUTED_AT, _current, _merge
from tests.test_v102_soldout_extra_targets_pg import ids as ids  # noqa: F401  fixture


def _add_ship_post(pg_fixture, hours_ago: float, rows: list[tuple[int, int, str | None, int]]) -> SimpleNamespace:
    """投稿を1つ入れる。rows は (商品, 状態, ship_ja, gemini_index)。rows の並び順で入れる（行の上下は gemini_index が決める）。"""
    source_id, job_id = str(uuid4()), str(uuid4())
    results: list[str] = []
    with pg_fixture[0].cursor() as cur:
        cur.execute(
            f"""INSERT INTO {SCHEMA}.source_messages (id,supplier_channel_id,raw_text,raw_sha256,is_active,received_at,line_posted_at)
                SELECT %s,id,'架空',%s,true,now() - make_interval(secs => %s),now() - make_interval(secs => %s)
                FROM {SCHEMA}.supplier_channels LIMIT 1""",
            (source_id, uuid4().hex, hours_ago * 3600, hours_ago * 3600),
        )
        cur.execute(f"INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'done')", (job_id, source_id))
        for product_id, condition_id, ship_ja, gemini_index in rows:
            item_id, result_id = str(uuid4()), str(uuid4())
            cur.execute(
                f"""INSERT INTO {SCHEMA}.extraction_items (id,extraction_job_id,line_start,line_end,source_lines,gemini_index,created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,now())""",
                (item_id, job_id, gemini_index + 1, gemini_index + 1, [gemini_index + 1], gemini_index),
            )
            cur.execute(
                f"""INSERT INTO {SCHEMA}.analysis_results
                    (id,extraction_item_id,product_id,pid_resolved,unit_resolved,condition_id,needs_review,engine_version,computed_at,ship_ja)
                    VALUES (%s,%s,%s,true,false,%s,false,'test',%s,%s)""",
                (result_id, item_id, product_id, condition_id, _COMPUTED_AT, ship_ja),
            )
            results.append(result_id)
    return SimpleNamespace(job=job_id, results=results)


def test_k2_same_post_different_ship_are_all_current(pg, ids):
    post = _add_ship_post(pg, 1, [(ids.p1, ids.box, "発送日要相談", 0), (ids.p1, ids.box, "発売日発送", 1), (ids.p1, ids.box, "10/19発送", 2)])
    _merge(pg, post.job)
    assert [_current(pg, r) for r in post.results] == [True, True, True]


def test_k4_newer_post_demotes_older_post_even_with_different_ship(pg, ids):
    older = _add_ship_post(pg, 5, [(ids.p1, ids.box, "10/16発送", 0)])
    newer = _add_ship_post(pg, 1, [(ids.p1, ids.box, "10/19発送", 0)])
    _merge(pg, older.job)
    _merge(pg, newer.job)
    assert (_current(pg, older.results[0]), _current(pg, newer.results[0])) == (False, True)
