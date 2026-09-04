"""
PARITY-03 Phase 3: 商品マスタ登録 API サービス層。

GAS 対照:
  B-1: getAnalysisReviewProductMasterRegistrationForm
  B-2: checkProductMasterV2RegistrationDuplicates
  B-3: createProductMasterV2FromAnalysisReview
  B-4: searchProductMasterV2ByName
  B-5: addProductMasterV2SearchKeyword
  R-1: analyze_extraction_job (単一ジョブ再解析)

tenant_004 専用スキーマ。全 SQL は tenant_004. で修飾する。
"""
from __future__ import annotations

import asyncio
import os
import re
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

TCG_SCHEMA = "tenant_004"

_PM_CODE_RE = re.compile(r"^PM(\d{4})$")


# ---------------------------------------------------------------------------
# B-1: 登録フォーム初期データ取得（READ ONLY）
# ---------------------------------------------------------------------------


async def fetch_registration_form(
    db: AsyncSession,
    *,
    extraction_item_id: str,
    source_message_id: str,
) -> dict[str, Any]:
    """
    GAS: getAnalysisReviewProductMasterRegistrationForm 相当。

    extraction_item_id → source_message_id リンクを検証し、
    rawName（raw_product_name）と分類マスタ選択肢を返す。
    """
    # ── item 検証 ─────────────────────────────────────────────────────────
    item_row = await db.execute(
        text(
            f"""
            SELECT
                ei.id::text            AS extraction_item_id,
                ej.source_message_id::text AS source_message_id,
                ei.raw_product_name    AS raw_name,
                ar.pid_resolved
            FROM {TCG_SCHEMA}.extraction_items ei
            JOIN {TCG_SCHEMA}.extraction_jobs ej ON ej.id = ei.extraction_job_id
            LEFT JOIN {TCG_SCHEMA}.analysis_results ar
                ON ar.extraction_item_id = ei.id
            WHERE ei.id = :eid
              AND ej.source_message_id::text = :smid
            """
        ),
        {"eid": extraction_item_id, "smid": source_message_id},
    )
    row = item_row.fetchone()
    if row is None:
        raise ValueError("PRODUCT_MASTER_V2_EXTRACTION_ITEM_NOT_FOUND")
    if row.pid_resolved:
        raise ValueError("PRODUCT_MASTER_V2_ALREADY_RESOLVED")

    item = {
        "extraction_item_id": row.extraction_item_id,
        "source_message_id": row.source_message_id,
        "raw_name": row.raw_name or "",
        "mark": "",
        "english_title": "",
    }

    # ── 分類マスタ一覧（有効行のみ） ──────────────────────────────────────
    lookups: dict[str, list[dict]] = {}

    for key, table, name_col in [
        ("division_id", "tcg_major_categories", "display_name"),
        ("work_id", "tcg_series", "display_name"),
        ("manufacturer_id", "tcg_manufacturers", "display_name"),
        ("product_category_id", "tcg_product_categories", "display_name"),
    ]:
        rows = await db.execute(
            text(
                f"""
                SELECT id::text AS id, {name_col} AS name
                FROM {TCG_SCHEMA}.{table}
                WHERE is_active = TRUE
                ORDER BY {name_col}
                """
            )
        )
        lookups[key] = [{"id": r.id, "name": r.name} for r in rows.fetchall()]

    return {"item": item, "lookups": lookups}


# ---------------------------------------------------------------------------
# B-4: 商品名検索（READ ONLY）
# ---------------------------------------------------------------------------


async def search_products_by_name(
    db: AsyncSession,
    *,
    query: str,
) -> dict[str, Any]:
    """
    GAS: searchProductMasterV2ByName 相当。

    japanese_title 部分一致（case-insensitive）、最大 10 件。
    search_keywords は comma-join で返す。
    """
    if not query.strip():
        return {"candidates": []}

    rows = await db.execute(
        text(
            f"""
            SELECT
                p.code          AS product_id,
                p.id::text      AS product_uuid,
                p.japanese_title,
                COALESCE(
                    STRING_AGG(psk.keyword, ',' ORDER BY psk.position),
                    ''
                )               AS search_keywords
            FROM {TCG_SCHEMA}.tcg_products p
            LEFT JOIN {TCG_SCHEMA}.product_search_keywords psk
                ON psk.product_id = p.id
            WHERE p.is_active = TRUE
              AND p.japanese_title ILIKE :query
            GROUP BY p.id, p.code, p.japanese_title
            ORDER BY p.japanese_title
            LIMIT 10
            """
        ),
        {"query": f"%{query.strip()}%"},
    )
    candidates = [
        {
            "product_id": r.product_id,
            "product_uuid": r.product_uuid,
            "japanese_title": r.japanese_title,
            "search_keywords": r.search_keywords,
        }
        for r in rows.fetchall()
    ]
    return {"candidates": candidates}


# ---------------------------------------------------------------------------
# B-2: 重複候補チェック（READ ONLY）
# ---------------------------------------------------------------------------


def _build_duplicate_candidates(
    rows: list[Any],
    *,
    japanese_title: str,
    work_id: str,
    manufacturer_id: str,
    product_category_id: str,
    mark: str = "",
    search_keywords: str = "",
) -> list[dict]:
    """
    GAS productMasterV2RegistrationCandidates_ 相当（1対1移植）。

    exact title match OR (same-classification AND (same-mark OR same-search_keywords))
    GAS 準拠: mark / search_keywords いずれも空のときは same_cls のみでは候補にならない。
    """
    normalized = japanese_title.strip().lower()
    mark_v = mark.strip()
    skw_v = search_keywords.strip()
    candidates = []
    for r in rows:
        exact_title = r.japanese_title.lower() == normalized
        same_cls = (
            r.work_id == work_id
            and r.manufacturer_id == manufacturer_id
            and r.product_category_id == product_category_id
        )
        same_mark = bool(mark_v) and getattr(r, "mark", "") == mark_v
        same_search = bool(skw_v) and getattr(r, "search_keywords", "") == skw_v
        if exact_title or (same_cls and (same_mark or same_search)):
            candidates.append(
                {"product_id": r.product_id, "japanese_title": r.japanese_title}
            )
        if len(candidates) >= 10:
            break
    return candidates


async def check_duplicates(
    db: AsyncSession,
    *,
    japanese_title: str,
    work_id: str,
    manufacturer_id: str,
    product_category_id: str,
    mark: str = "",
    search_keywords: str = "",
) -> dict[str, Any]:
    """
    GAS: checkProductMasterV2RegistrationDuplicates 相当。

    title 近似 OR 同一分類の商品を最大 10 件返す。
    mark / search_keywords で GAS 準拠フィルタリングを行う。
    """
    rows = await db.execute(
        text(
            f"""
            SELECT
                p.code::text              AS product_id,
                p.japanese_title,
                p.work_id::text           AS work_id,
                p.manufacturer_id::text   AS manufacturer_id,
                p.product_category_id::text AS product_category_id,
                COALESCE(p.mark, '')      AS mark,
                COALESCE(
                    STRING_AGG(psk.keyword, ',' ORDER BY psk.position),
                    ''
                )                         AS search_keywords
            FROM {TCG_SCHEMA}.tcg_products p
            LEFT JOIN {TCG_SCHEMA}.product_search_keywords psk
                ON psk.product_id = p.id
            WHERE p.is_active = TRUE
              AND (
                p.japanese_title ILIKE :title_pattern
                OR (
                    p.work_id::text = :work_id
                    AND p.manufacturer_id::text = :manufacturer_id
                    AND p.product_category_id::text = :product_category_id
                )
              )
            GROUP BY
                p.id, p.code, p.japanese_title,
                p.work_id, p.manufacturer_id, p.product_category_id, p.mark
            ORDER BY p.japanese_title
            LIMIT 20
            """
        ),
        {
            "title_pattern": f"%{japanese_title.strip()}%",
            "work_id": work_id,
            "manufacturer_id": manufacturer_id,
            "product_category_id": product_category_id,
        },
    )
    candidates = _build_duplicate_candidates(
        rows.fetchall(),
        japanese_title=japanese_title,
        work_id=work_id,
        manufacturer_id=manufacturer_id,
        product_category_id=product_category_id,
        mark=mark,
        search_keywords=search_keywords,
    )
    return {"candidates": candidates}


# ---------------------------------------------------------------------------
# B-3: 商品マスタ新規登録（WRITE）
# ---------------------------------------------------------------------------


async def _next_pm_code(db: AsyncSession) -> str:
    """
    GAS productMasterV2RegistrationNextId_ 相当。
    PM0001〜PM9999 形式で現在の最大番号 +1 を採番する。
    """
    result = await db.execute(
        text(
            f"""
            SELECT code
            FROM {TCG_SCHEMA}.tcg_products
            WHERE code ~ '^PM[0-9]{{4}}$'
            ORDER BY code DESC
            LIMIT 1
            """
        )
    )
    row = result.fetchone()
    if row is None:
        return "PM0001"
    m = _PM_CODE_RE.match(row[0])
    if m is None:
        return "PM0001"
    num = int(m.group(1)) + 1
    if num > 9999:
        raise ValueError("PRODUCT_MASTER_V2_PM_CODE_EXHAUSTED")
    return f"PM{num:04d}"


async def create_product(
    db: AsyncSession,
    *,
    extraction_item_id: str,
    source_message_id: str,
    division_id: str,
    work_id: str,
    manufacturer_id: str,
    product_category_id: str,
    japanese_title: str,
    release_date: str | None,
    search_keywords: str,
    exclude_keywords: str,
    mark: str = "",
    english_title: str = "",
    force: bool = False,
) -> dict[str, Any]:
    """
    GAS: createProductMasterV2FromAnalysisReview 相当。

    1. 重複チェック（重複あり かつ force=False → 早期 return）
    2. PM コード採番
    3. tcg_products に INSERT
    4. product_search_keywords / product_exclude_keywords に INSERT
    5. post-write gate

    force=True: GAS ソフトブロック準拠。重複候補があっても登録を続行する。
    """
    # 重複チェック（force=True なら DUPLICATE_CANDIDATE で弾かない）
    dup_result = await check_duplicates(
        db,
        japanese_title=japanese_title,
        work_id=work_id,
        manufacturer_id=manufacturer_id,
        product_category_id=product_category_id,
        mark=mark,
        search_keywords=search_keywords,
    )
    if dup_result["candidates"] and not force:
        return {
            "ok": False,
            "code": "DUPLICATE_CANDIDATE",
            "candidates": dup_result["candidates"],
        }

    pm_code = await _next_pm_code(db)

    # category_class: work_id（tcg_series.display_name）から導出
    series_row = await db.execute(
        text(
            f"SELECT display_name FROM {TCG_SCHEMA}.tcg_series WHERE id = :id"
        ),
        {"id": work_id},
    )
    sr = series_row.fetchone()
    category_class = sr.display_name if sr else ""

    rd = release_date if release_date else None

    # tcg_products INSERT
    product_row = await db.execute(
        text(
            f"""
            INSERT INTO {TCG_SCHEMA}.tcg_products
                (code, japanese_title, release_date, category_class,
                 division_id, work_id, manufacturer_id, product_category_id,
                 mark, english_title, is_active)
            VALUES
                (:code, :japanese_title, :release_date, :category_class,
                 :division_id, :work_id, :manufacturer_id, :product_category_id,
                 :mark, :english_title, TRUE)
            RETURNING id::text AS id
            """
        ),
        {
            "code": pm_code,
            "japanese_title": japanese_title.strip(),
            "release_date": rd,
            "category_class": category_class,
            "division_id": division_id,
            "work_id": work_id,
            "manufacturer_id": manufacturer_id,
            "product_category_id": product_category_id,
            "mark": mark.strip() or None,
            "english_title": english_title.strip() or None,
        },
    )
    new_row = product_row.fetchone()
    if new_row is None:
        raise ValueError("PRODUCT_MASTER_V2_INSERT_FAILED")
    product_uuid = new_row.id

    # search_keywords INSERT
    if search_keywords.strip():
        for pos, kw in enumerate(
            [k.strip() for k in search_keywords.split(",") if k.strip()], start=1
        ):
            await db.execute(
                text(
                    f"""
                    INSERT INTO {TCG_SCHEMA}.product_search_keywords
                        (product_id, keyword, position)
                    VALUES (:pid, :kw, :pos)
                    """
                ),
                {"pid": product_uuid, "kw": kw, "pos": pos},
            )

    # exclude_keywords INSERT
    if exclude_keywords.strip():
        for pos, kw in enumerate(
            [k.strip() for k in exclude_keywords.split(",") if k.strip()], start=1
        ):
            await db.execute(
                text(
                    f"""
                    INSERT INTO {TCG_SCHEMA}.product_exclude_keywords
                        (product_id, keyword, position)
                    VALUES (:pid, :kw, :pos)
                    """
                ),
                {"pid": product_uuid, "kw": kw, "pos": pos},
            )

    await db.commit()

    # post-write gate: code が実際に存在するか確認
    verify = await db.execute(
        text(
            f"SELECT code FROM {TCG_SCHEMA}.tcg_products WHERE id = :id"
        ),
        {"id": product_uuid},
    )
    vr = verify.fetchone()
    if vr is None or vr.code != pm_code:
        raise ValueError("PRODUCT_MASTER_V2_POST_WRITE_GATE_FAILED")

    return {"ok": True, "product_id": pm_code}


# ---------------------------------------------------------------------------
# B-5: 検索キーワード追加（WRITE）
# ---------------------------------------------------------------------------


async def add_search_keyword(
    db: AsyncSession,
    *,
    product_code: str,
    new_keyword: str,
) -> dict[str, Any]:
    """
    GAS: addProductMasterV2SearchKeyword 相当。

    既存キーワードは削除しない。重複は KEYWORD_ALREADY_EXISTS で返す。
    """
    kw = new_keyword.strip()
    if not kw:
        raise ValueError("SEARCH_KEYWORD_EMPTY")

    # product_id 取得
    pid_row = await db.execute(
        text(
            f"""
            SELECT id::text AS id
            FROM {TCG_SCHEMA}.tcg_products
            WHERE code = :code AND is_active = TRUE
            """
        ),
        {"code": product_code},
    )
    pr = pid_row.fetchone()
    if pr is None:
        raise ValueError("SEARCH_KEYWORD_PRODUCT_NOT_FOUND")
    product_uuid = pr.id

    # 既存キーワード確認
    existing = await db.execute(
        text(
            f"""
            SELECT keyword
            FROM {TCG_SCHEMA}.product_search_keywords
            WHERE product_id = :pid
            ORDER BY position
            """
        ),
        {"pid": product_uuid},
    )
    existing_kws = [r.keyword for r in existing.fetchall()]
    if kw in existing_kws:
        return {"ok": False, "code": "KEYWORD_ALREADY_EXISTS"}

    # 追記（position = MAX + 1）
    next_pos = len(existing_kws) + 1
    await db.execute(
        text(
            f"""
            INSERT INTO {TCG_SCHEMA}.product_search_keywords
                (product_id, keyword, position)
            VALUES (:pid, :kw, :pos)
            """
        ),
        {"pid": product_uuid, "kw": kw, "pos": next_pos},
    )
    await db.commit()

    return {"ok": True}


# ---------------------------------------------------------------------------
# R-1: 単一ジョブ再解析（WRITE — analysis_results を UPSERT）
# ---------------------------------------------------------------------------

_SYNC_DB_URL = os.getenv("DATABASE_URL", "").replace(
    "postgresql+asyncpg://", "postgresql://"
)


def _run_reanalyze_sync(extraction_job_id: str) -> dict[str, Any]:
    """
    同期 SQLAlchemy Session で analyze_extraction_job を実行する。
    asyncio.to_thread で呼ばれるため同期関数。

    戻り値: {before: {...}, after: {...}, run_id: str}
    """
    from app.services.tcg_analyzer_svc import (  # lazy import
        ENGINE_VERSION,
        analyze_extraction_job,
    )

    engine = create_engine(_SYNC_DB_URL, echo=False, pool_pre_ping=True)
    Session = sessionmaker(engine, expire_on_commit=False)

    with Session() as session:
        # ── HIST Step 1: analysis_runs に1行 INSERT（started_at = NOW()）──
        run_id_row = session.execute(
            text(
                f"""
                INSERT INTO {TCG_SCHEMA}.analysis_runs
                    (extraction_job_id, run_type, triggered_by, engine_version)
                VALUES
                    (:job_id, 'R1_API', 'api', :engine)
                RETURNING id
                """
            ),
            {"job_id": extraction_job_id, "engine": ENGINE_VERSION},
        ).fetchone()
        session.commit()
        run_id = str(run_id_row[0])

        # ── HIST Step 2: 再解析前スナップショットを analysis_run_snapshots に INSERT ──
        session.execute(
            text(
                f"""
                INSERT INTO {TCG_SCHEMA}.analysis_run_snapshots (
                    run_id,
                    analysis_result_id,
                    extraction_item_id,
                    product_id,
                    pid_resolved,
                    pid_basis,
                    unit_id,
                    unit_canonical,
                    unit_resolved,
                    condition_id,
                    condition_canonical,
                    condition_basis,
                    quantity_normalized,
                    price_normalized,
                    note_ja,
                    status,
                    exclusion,
                    needs_review,
                    review_reasons,
                    engine_version,
                    computed_at,
                    updated_at
                )
                SELECT
                    :run_id,
                    ar.id,
                    ar.extraction_item_id,
                    ar.product_id,
                    ar.pid_resolved,
                    ar.pid_basis,
                    ar.unit_id,
                    ar.unit_canonical,
                    ar.unit_resolved,
                    ar.condition_id,
                    ar.condition_canonical,
                    ar.condition_basis,
                    ar.quantity_normalized,
                    ar.price_normalized,
                    ar.note_ja,
                    ar.status,
                    ar.exclusion,
                    ar.needs_review,
                    ar.review_reasons,
                    ar.engine_version,
                    ar.computed_at,
                    ar.updated_at
                FROM {TCG_SCHEMA}.analysis_results ar
                JOIN {TCG_SCHEMA}.extraction_items ei
                    ON ei.id = ar.extraction_item_id
                WHERE ei.extraction_job_id = :job_id
                """
            ),
            {"run_id": run_id, "job_id": extraction_job_id},
        )
        session.commit()

        # before: 現行 analysis_results のサマリー
        before_row = session.execute(
            text(
                f"""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN pid_resolved THEN 1 ELSE 0 END) AS pid_resolved,
                    SUM(CASE WHEN unit_resolved THEN 1 ELSE 0 END) AS unit_resolved,
                    SUM(CASE WHEN needs_review THEN 1 ELSE 0 END) AS needs_review
                FROM {TCG_SCHEMA}.analysis_results ar
                JOIN {TCG_SCHEMA}.extraction_items ei
                    ON ei.id = ar.extraction_item_id
                WHERE ei.extraction_job_id = :job_id
                """
            ),
            {"job_id": extraction_job_id},
        ).fetchone()

        before = {
            "total": int(before_row.total or 0),
            "pid_resolved": int(before_row.pid_resolved or 0),
            "unit_resolved": int(before_row.unit_resolved or 0),
            "needs_review": int(before_row.needs_review or 0),
        }

        # 再解析（UPSERT — 元には戻せないので before を返す）
        after = analyze_extraction_job(session, extraction_job_id)

        # ── HIST Step 3: MULTI / NONE カウントを取得 ──
        status_row = session.execute(
            text(
                f"""
                SELECT
                    SUM(CASE WHEN ar.status = 'MULTI' THEN 1 ELSE 0 END) AS multi_count,
                    SUM(CASE WHEN ar.status = 'NONE'  THEN 1 ELSE 0 END) AS none_count
                FROM {TCG_SCHEMA}.analysis_results ar
                JOIN {TCG_SCHEMA}.extraction_items ei
                    ON ei.id = ar.extraction_item_id
                WHERE ei.extraction_job_id = :job_id
                """
            ),
            {"job_id": extraction_job_id},
        ).fetchone()

        # ── HIST Step 4: analysis_runs を completed_at・stats で UPDATE ──
        session.execute(
            text(
                f"""
                UPDATE {TCG_SCHEMA}.analysis_runs
                SET
                    completed_at  = NOW(),
                    total         = :total,
                    pid_resolved  = :pid_resolved,
                    unit_resolved = :unit_resolved,
                    needs_review  = :needs_review,
                    multi_count   = :multi_count,
                    none_count    = :none_count
                WHERE id = :run_id
                """
            ),
            {
                "run_id": run_id,
                "total": after.get("total", 0),
                "pid_resolved": after.get("pid_resolved", 0),
                "unit_resolved": after.get("unit_resolved", 0),
                "needs_review": after.get("needs_review", 0),
                "multi_count": int(status_row.multi_count or 0),
                "none_count": int(status_row.none_count or 0),
            },
        )
        session.commit()

    engine.dispose()
    return {"before": before, "after": after, "run_id": run_id}


async def reanalyze_extraction_job(extraction_job_id: str) -> dict[str, Any]:
    """
    単一 extraction_job を再解析し analysis_results を UPSERT する。

    GAS: refreshShadowReviewV2 相当（ただし全件ではなく 1 ジョブ限定）。

    ⚠️  ロールバック手順:
      再解析は Python エンジンで上書きする。GAS が計算した値には戻らない。
      実行前に analysis_results_gas_baseline_YYYYMMDD テーブルで全行を退避し、
      復元時は ON CONFLICT DO UPDATE で元行を差し戻すこと（routers 側 docstring 参照）。
    """
    if not _SYNC_DB_URL:
        raise ValueError("DATABASE_URL not configured for sync session")

    return await asyncio.to_thread(_run_reanalyze_sync, extraction_job_id)
