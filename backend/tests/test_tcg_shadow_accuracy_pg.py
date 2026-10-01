"""
解析精度管理（新方式）の実 PostgreSQL 試験: 兆候 S1〜S6 の判定と summary / posts / detail の件数。

スキーマは本物の migration（.sql）を流して作る（柱3-c: テストでの本番テーブル定義コピー禁止 —
scripts/check_test_schema_dup.py）。共有 `pg` フィクスチャは CI 専用
（GITHUB_ACTIONS=true + RLS_ADMIN_DATABASE_URL 必須）。
S1〜S6 それぞれについて「当たる行」と「当たらない行」を1件以上用意し、判定を固定する。
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  (fixture)

pytestmark = pytest.mark.asyncio

# shadow の migration は extraction_prompt_config に初期値を INSERT するため、先にその表の migration を流す。
_SHADOW_MIGRATIONS = (
    "20260926_080000_create_extraction_prompt_config.sql",
    "20260928_110000_create_extraction_shadow_tables.sql",
)

# 原文（行番号は 1 始まり）
_RAW_TEXT = "\n".join(
    [
        "予約 新弾ボックス",  # 1: 「予約」を含む見出し（S2 用）
        "商品1 売切 BOX",  # 2: 完売語（S1 用）
        "商品2 在庫あり BOX",  # 3
        "商品3 個 枚 PCS 100",  # 4: 単位の語（S3 用）
        "ヘッダー 新弾",  # 5: 「予約」を含まない見出し（S5 用）
    ]
)

# 各ブロック: (名前, 上書き項目, 当たるはずの兆候)。既定は「どの兆候にも当たらない」ブロック。
_DEFAULT = dict(
    line_start=3, line_end=3, heading_line_start=None, heading_line_end=None,
    raw_unit="BOX", status="In Stock", match_status="unmatched", needs_review=True,
    ship_offer_type=None, condition_code=None, product="none", evidence={},
)
_BLOCKS = [
    ("s1_hit", dict(line_start=2, line_end=2), {"S1"}),
    ("s1_miss_in_stock_no_word", dict(), set()),
    ("s1_miss_sold_out_status", dict(line_start=2, line_end=2, status="Sold out"), set()),
    ("s2_hit", dict(heading_line_start=1, heading_line_end=1, match_status="matched"), {"S2"}),
    ("s2_miss_pre_order", dict(heading_line_start=1, heading_line_end=1, match_status="matched",
                               ship_offer_type="pre_order"), set()),
    ("s3_hit_box_unit", dict(condition_code="CN0008", raw_unit="BOX"), {"S3"}),
    ("s3_hit_unit_none", dict(condition_code="CN0008", raw_unit="none"), {"S3"}),
    ("s3_hit_unit_null", dict(condition_code="CN0008", raw_unit=None), {"S3"}),
    ("s3_hit_unknown_unit", dict(condition_code="CN0008", raw_unit="個", line_start=4, line_end=4), {"S3"}),
    ("s3_miss_single_unit", dict(condition_code="CN0008", raw_unit="枚", line_start=4, line_end=4), set()),
    ("s3_miss_lower_match", dict(condition_code="CN0008", raw_unit="pcs", line_start=4, line_end=4), set()),
    ("s3_miss_other_condition", dict(condition_code="CN0003", raw_unit="個", line_start=4, line_end=4), set()),
    ("s4_hit", dict(match_status="matched", product="short", evidence={"basis": "RAWCODE"}), {"S4"}),
    ("s4_miss_long_mark", dict(match_status="matched", product="long", evidence={"basis": "RAWCODE"}), set()),
    ("s4_miss_keyword_basis", dict(match_status="matched", product="short", evidence={"basis": "SK:x"}), set()),
    ("s4_miss_unmatched", dict(match_status="unmatched", product="short", evidence={"basis": "RAWCODE"}), set()),
    ("s5_hit_unmatched", dict(heading_line_start=5, heading_line_end=5), {"S5"}),
    ("s5_hit_ambiguous", dict(heading_line_start=5, heading_line_end=5, match_status="ambiguous"), {"S5"}),
    ("s5_miss_matched", dict(heading_line_start=5, heading_line_end=5, match_status="matched"), set()),
    ("s5_miss_no_heading", dict(), set()),
    ("s6_hit", dict(raw_unit="カートン"), {"S6"}),
    ("s6_miss_none", dict(raw_unit="none"), set()),
    ("s6_miss_spaces_and_case", dict(raw_unit="b o x"), set()),
]


def _insert_post(cur, *, supplier_channel_id, raw_text, started_at, blocks, product_ids):
    cur.execute(
        "INSERT INTO public.source_messages (supplier_channel_id, raw_text, raw_sha256, is_active)"
        " VALUES (%s, %s, md5(%s), TRUE) RETURNING id",
        (supplier_channel_id, raw_text, raw_text),
    )
    message_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO public.extraction_jobs (source_message_id, status) VALUES (%s, 'done') RETURNING id",
        (message_id,),
    )
    job_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO public.extraction_shadow_runs (extraction_job_id, prompt_key, engine_version,"
        " requested_model, status, started_at)"
        " VALUES (%s, 'k', 'v7', 'm', 'completed', COALESCE(%s::timestamptz, now())) RETURNING id",
        (job_id, started_at),
    )
    run_id = cur.fetchone()[0]
    for index, (_, overrides, _) in enumerate(blocks):
        b = {**_DEFAULT, **overrides}
        cur.execute(
            "INSERT INTO public.extraction_shadow_results (run_id, block_index, line_start, line_end,"
            " heading_line_start, heading_line_end, raw_unit, status, match_status, needs_review,"
            " ship_offer_type, product_id, condition_id, evidence)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,"
            " (SELECT id FROM public.conditions WHERE code = %s), %s::jsonb)",
            (
                run_id, index, b["line_start"], b["line_end"], b["heading_line_start"],
                b["heading_line_end"], b["raw_unit"], b["status"], b["match_status"],
                b["needs_review"], b["ship_offer_type"], product_ids.get(b["product"]),
                b["condition_code"], json.dumps(b["evidence"]),
            ),
        )
    return str(job_id), str(run_id)


@pytest.fixture
def seeded(pg):  # noqa: F811
    connection, _, async_url = pg
    with connection.cursor() as cur:
        for name in _SHADOW_MIGRATIONS:
            cur.execute((MIGRATIONS / name).read_text())
        # 単位マスタ（S3: kubun「単品系」かどうかで判定する）
        cur.execute(
            "INSERT INTO public.units (code, canonical, kubun, is_active) VALUES"
            " ('UN9001', '枚', '単品系', TRUE), ('UN9002', 'BOX', '箱系', TRUE) RETURNING id, canonical"
        )
        unit_ids = {canonical: uid for uid, canonical in cur.fetchall()}
        cur.execute(
            "INSERT INTO public.unit_aliases (unit_id, alias_text, lang) VALUES"
            " (%s, '枚', 'ja'), (%s, 'PCS', 'en'), (%s, 'BOX', 'en')",
            (unit_ids["枚"], unit_ids["枚"], unit_ids["BOX"]),
        )
        # 商品（S4: mark の長さ）
        cur.execute("SELECT id FROM public.type_master WHERE is_active = TRUE LIMIT 1")
        work_id = cur.fetchone()[0]
        product_ids = {}
        for key, code, mark in (("short", "TSAS0001", "M"), ("long", "TSAS0002", "LONGMARK")):
            cur.execute(
                "INSERT INTO public.products (product_code, name, category_class, is_active, work_id, mark)"
                " VALUES (%s, %s, 'Box', TRUE, %s, %s) RETURNING id",
                (code, f"商品{code}", work_id, mark),
            )
            product_ids[key] = cur.fetchone()[0]
        # 仕入元（1件目の投稿だけ仕入元あり）
        cur.execute(
            "INSERT INTO public.suppliers (name, extraction_price_format, extraction_qty_format,"
            " extraction_order_pattern) VALUES ('精度試験仕入元', '円', '在庫', '[\"price\"]') RETURNING id"
        )
        supplier_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO public.supplier_channels (channel, external_id, is_active, supplier_id)"
            " VALUES ('line', 'acc-test', TRUE, %s) RETURNING id",
            (supplier_id,),
        )
        channel_id = cur.fetchone()[0]
        # 投稿1: 全パターン（直近）。投稿2: 兆候なし・確定済み・100日前・仕入元なし。
        job1, _ = _insert_post(
            cur, supplier_channel_id=channel_id, raw_text=_RAW_TEXT,
            started_at=None, blocks=_BLOCKS, product_ids=product_ids,
        )
        quiet = [("quiet", dict(match_status="matched", needs_review=False), set())]
        job2, _ = _insert_post(
            cur, supplier_channel_id=None, raw_text="商品2 在庫あり BOX",
            started_at=None, blocks=quiet, product_ids=product_ids,
        )
        cur.execute(
            "UPDATE public.extraction_shadow_runs SET started_at = now() - interval '100 days'"
            " WHERE extraction_job_id = %s", (job2,),
        )
    return {"job1": job1, "job2": job2, "supplier_id": supplier_id, "url": async_url}


async def _with_db(seeded_data, fn):
    engine = create_async_engine(seeded_data["url"])
    try:
        async with AsyncSession(engine) as db:
            return await fn(db)
    finally:
        await engine.dispose()


async def test_detail_flags_each_signal_exactly_as_defined(seeded):
    from app.services.tcg_shadow_accuracy_svc import fetch_post_detail

    detail = await _with_db(seeded, lambda db: fetch_post_detail(db, seeded["job1"]))
    assert detail is not None
    assert detail["raw_text"] == _RAW_TEXT
    assert len(detail["blocks"]) == len(_BLOCKS)
    for (name, _, expected), block in zip(_BLOCKS, detail["blocks"], strict=True):
        actual = {code for code, hit in block["signals"].items() if hit}
        assert actual == expected, f"{name}: expected {sorted(expected)} got {sorted(actual)}"


async def test_summary_counts_match_the_block_definitions(seeded):
    from app.services.tcg_shadow_accuracy_svc import fetch_summary

    summary = await _with_db(seeded, lambda db: fetch_summary(db, days=7, supplier_id=None))
    assert summary["totals"]["blocks"] == len(_BLOCKS)  # 100日前の投稿は 7 日に入らない
    for code in ("S1", "S2", "S3", "S4", "S5", "S6"):
        expected = sum(1 for _, _, hits in _BLOCKS if code in hits)
        assert summary["signals"][code] == expected, code
    assert summary["totals"]["needs_review_count"] == len(_BLOCKS)
    assert summary["totals"]["sold_out"] == 1
    assert summary["totals"]["pre_order"] == 1
    assert [row["supplier_name"] for row in summary["by_supplier"]] == ["精度試験仕入元"]
    assert summary["by_supplier"][0]["signals"] == summary["signals"]


async def test_summary_all_time_includes_old_post_and_supplier_filter(seeded):
    from app.services.tcg_shadow_accuracy_svc import fetch_summary

    everything = await _with_db(seeded, lambda db: fetch_summary(db, days=0, supplier_id=None))
    only_supplier = await _with_db(
        seeded, lambda db: fetch_summary(db, days=0, supplier_id=seeded["supplier_id"])
    )
    assert everything["totals"]["blocks"] == len(_BLOCKS) + 1
    assert everything["totals"]["auto_confirmed"] == 1
    assert only_supplier["totals"]["blocks"] == len(_BLOCKS)


async def test_posts_are_per_run_and_filter_by_signal_and_review_state(seeded):
    from app.services.tcg_shadow_accuracy_svc import fetch_posts

    base = dict(days=0, supplier_id=None)
    all_posts = await _with_db(seeded, lambda db: fetch_posts(db, **base))
    assert all_posts["total"] == 2
    assert [p["job_id"] for p in all_posts["items"]] == [seeded["job1"], seeded["job2"]]
    first = all_posts["items"][0]
    assert first["blocks"] == len(_BLOCKS)
    assert first["signals"]["S3"] == 4

    by_signal = await _with_db(seeded, lambda db: fetch_posts(db, signal="S1", **base))
    assert [p["job_id"] for p in by_signal["items"]] == [seeded["job1"]]

    confirmed = await _with_db(seeded, lambda db: fetch_posts(db, needs_review=False, **base))
    assert [p["job_id"] for p in confirmed["items"]] == [seeded["job2"]]
    pending = await _with_db(seeded, lambda db: fetch_posts(db, needs_review=True, **base))
    assert [p["job_id"] for p in pending["items"]] == [seeded["job1"]]


async def test_posts_period_supplier_and_paging(seeded):
    from app.services.tcg_shadow_accuracy_svc import fetch_posts

    seven = await _with_db(seeded, lambda db: fetch_posts(db, days=7, supplier_id=None))
    assert [p["job_id"] for p in seven["items"]] == [seeded["job1"]]
    supplier = await _with_db(seeded, lambda db: fetch_posts(db, days=0, supplier_id=seeded["supplier_id"]))
    assert supplier["total"] == 1 and supplier["items"][0]["supplier_name"] == "精度試験仕入元"
    page2 = await _with_db(seeded, lambda db: fetch_posts(db, days=0, supplier_id=None, offset=1, limit=1))
    assert page2["total"] == 2 and [p["job_id"] for p in page2["items"]] == [seeded["job2"]]
    beyond = await _with_db(seeded, lambda db: fetch_posts(db, days=0, supplier_id=None, offset=5, limit=1))
    assert beyond["items"] == [] and beyond["total"] == 2


async def test_detail_of_unknown_job_is_none(seeded):
    from app.services.tcg_shadow_accuracy_svc import fetch_post_detail

    missing = await _with_db(
        seeded, lambda db: fetch_post_detail(db, "00000000-0000-0000-0000-000000000000")
    )
    assert missing is None
