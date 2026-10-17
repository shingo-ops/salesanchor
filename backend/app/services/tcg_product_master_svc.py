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
import logging
import os
import re
from datetime import date
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.services.tcg_product_code_collision_svc import find_code_collisions

# Step 4/5: TCG テーブルは public スキーマに移行済み
TCG_SCHEMA = "public"

logger = logging.getLogger(__name__)

# ADR-1020: 共用商品の登録で入れる9項目と、「調べたが無い」の印で空を認める4項目
REQUIRED_FIELDS: tuple[str, ...] = (
    "name", "name_en", "mark", "release_date", "search_keywords",
    "exclude_keywords", "work_id", "product_format_id", "product_category_id",
)
BLANK_CONFIRMABLE_FIELDS: tuple[str, ...] = ("name_en", "mark", "release_date", "exclude_keywords")

_PM_CODE_RE = re.compile(r"^PM(\d{4})$")


def _split_csv_words(value: str) -> list[str]:
    """カンマ区切りの語を割り、前後の空白と空を捨てる（INSERT と同じ扱い）。"""
    return [k.strip() for k in (value or "").split(",") if k.strip()]


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple)):
        return not [v for v in value if str(v).strip()]
    return False


def check_required_fields(values: dict[str, Any], blank_confirmations: set[str] | frozenset[str]) -> list[str]:
    """足りない項目の名前を REQUIRED_FIELDS の順で返す（DB は触らない）。

    values のキーは REQUIRED_FIELDS の名前。検索ワード・除外ワードは文字列（カンマ区切り）か語の一覧。
    印は BLANK_CONFIRMABLE_FIELDS の項目にだけ効く。
    """
    missing: list[str] = []
    for field in REQUIRED_FIELDS:
        value = values.get(field)
        if isinstance(value, str) and field in ("search_keywords", "exclude_keywords"):
            value = _split_csv_words(value)
        if not _is_blank(value):
            continue
        if field in BLANK_CONFIRMABLE_FIELDS and field in blank_confirmations:
            continue
        missing.append(field)
    return missing


def missing_for_create(args: dict[str, Any]) -> list[str]:
    """ADR-1020 便3: create_product の引数（名前は create_product と同じ）から、足りない項目名を返す。"""
    values = {
        "name": args.get("japanese_title"),
        "name_en": args.get("english_title"),
        "mark": args.get("mark"),
        "release_date": args.get("release_date"),
        "search_keywords": args.get("search_keywords"),
        "exclude_keywords": args.get("exclude_keywords"),
        "work_id": args.get("work_id"),
        "product_format_id": args.get("product_format_id"),
        "product_category_id": args.get("product_category_id"),
    }
    return check_required_fields(values, set(args.get("blank_confirmations") or []))


def find_cleared_fields(
    before: dict[str, Any], before_marks: Any, after: dict[str, Any], after_marks: Any,
) -> list[str]:
    """ADR-1020 便3: 前は足りていた（値か印があった）のに、後で足りなくなった項目名を返す。

    前も後も足りない項目（古い空欄）は返さない。before / after のキーは REQUIRED_FIELDS の名前。
    """
    was_missing = set(check_required_fields(before, set(before_marks or [])))
    return [f for f in check_required_fields(after, set(after_marks or [])) if f not in was_missing]


async def format_matches_game(db: AsyncSession, product_format_id: int, work_id: int) -> bool:
    """ADR-1020 便2a: 細分類がそのゲーム（作品）に紐づいているか。"""
    row = (await db.execute(
        text("SELECT 1 FROM public.product_format_game_links "
             "WHERE format_id = :fid AND type_master_id = :wid"),
        {"fid": int(product_format_id), "wid": int(work_id)},
    )).first()
    return row is not None


async def _validate_product_format(
    db: AsyncSession, product_format_id: int | None, work_id: int | None = None,
) -> None:
    if product_format_id is None:
        return
    row = (await db.execute(
        text("SELECT 1 FROM public.product_formats WHERE id = :id AND is_active = TRUE"),
        {"id": int(product_format_id)},
    )).first()
    if row is None:
        raise ValueError("PRODUCT_FORMAT_INVALID")
    if work_id is not None and not await format_matches_game(db, product_format_id, work_id):
        raise ValueError("PRODUCT_FORMAT_GAME_MISMATCH")


async def fetch_product_format_options(db: AsyncSession, selected: int | None = None) -> list[dict[str, Any]]:
    """ADR-1020 便2a: 細分類の選択肢。各細分類に紐づくゲーム（作品）の id を付ける。"""
    rows = await db.execute(text(
        "SELECT f.id::text AS id, f.name AS name, f.is_active AS is_active, "
        "COALESCE(array_agg(l.type_master_id::text ORDER BY l.type_master_id) "
        "FILTER (WHERE l.type_master_id IS NOT NULL), ARRAY[]::text[]) AS game_ids "
        "FROM public.product_formats f "
        "LEFT JOIN public.product_format_game_links l ON l.format_id = f.id "
        "WHERE f.is_active = TRUE OR f.id = :selected "
        "GROUP BY f.id, f.name, f.is_active, f.display_order "
        "ORDER BY f.display_order, f.id"
    ), {"selected": selected})
    return [
        {"id": r["id"], "name": r["name"], "is_active": r["is_active"], "game_ids": list(r["game_ids"])}
        for r in rows.mappings()
    ]


async def save_blank_confirmations(
    db: AsyncSession,
    *,
    product_id: int,
    values: dict[str, Any],
    confirmations: set[str] | None,
    actor: str,
) -> None:
    """ADR-1020: 印を保存する。呼ぶ側が app.is_operator を立てた同じトランザクションで呼ぶ。

    confirmations が None なら、値が入った項目の印だけを消す（D4）。
    集合なら、その商品の印を「空の項目 ∩ confirmations」に置き換える（D2・D4）。
    """
    filled = [f for f in BLANK_CONFIRMABLE_FIELDS if not _is_blank(
        _split_csv_words(values.get(f)) if f == "exclude_keywords" and isinstance(values.get(f), str) else values.get(f)
    )]
    if confirmations is None:
        if filled:
            await db.execute(
                text("DELETE FROM public.product_blank_confirmations "
                     "WHERE product_id = :pid AND field_code = ANY(:fields)"),
                {"pid": product_id, "fields": filled},
            )
        return
    keep = [f for f in BLANK_CONFIRMABLE_FIELDS if f in confirmations and f not in filled]
    await db.execute(
        text("DELETE FROM public.product_blank_confirmations "
             "WHERE product_id = :pid AND NOT (field_code = ANY(:keep))"),
        {"pid": product_id, "keep": keep},
    )
    for field in keep:
        await db.execute(
            text("INSERT INTO public.product_blank_confirmations (product_id, field_code, confirmed_by) "
                 "VALUES (:pid, :field, :actor) ON CONFLICT (product_id, field_code) DO NOTHING"),
            {"pid": product_id, "field": field, "actor": (actor or "unknown")[:200]},
        )


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

    # work_id → public.type_master (SSOT)
    work_rows = await db.execute(text(
        "SELECT id::text AS id, name_ja AS name "
        "FROM public.type_master "
        "WHERE is_active = TRUE ORDER BY name_ja"
    ))
    lookups["work_id"] = [{"id": r.id, "name": r.name} for r in work_rows.fetchall()]
    # product_kind_id → public.product_kinds (SSOT, INTEGER PK)
    pk_rows = await db.execute(text(
        "SELECT id::text AS id, name AS name "
        "FROM public.product_kinds "
        "WHERE is_active = TRUE ORDER BY name"
    ))
    lookups["product_kind_id"] = [{"id": r.id, "name": r.name} for r in pk_rows.fetchall()]
    # ADR-156 Phase 3B: tcg_product_categories is now SSOT in public schema (INTEGER PK).
    _PUBLIC_TABLES = {"product_kinds", "tcg_product_categories"}
    for key, table, name_col in [
        ("manufacturer_id", "tcg_manufacturers", "display_name"),
        ("product_category_id", "tcg_product_categories", "display_name"),
    ]:
        schema = "public" if table in _PUBLIC_TABLES else TCG_SCHEMA
        rows = await db.execute(
            text(
                f"""
                SELECT id::text AS id, {name_col} AS name
                FROM {schema}.{table}
                WHERE is_active = TRUE
                ORDER BY {name_col}
                """
            )
        )
        lookups[key] = [{"id": r.id, "name": r.name} for r in rows.fetchall()]

    # ADR-1020 便2a: 細分類（紐づくゲーム付き）
    lookups["product_format_id"] = await fetch_product_format_options(db)
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
            """
            SELECT
                p.id::text      AS product_id,
                p.id::text      AS product_uuid,
                p.name          AS japanese_title,
                COALESCE(
                    STRING_AGG(psk.keyword, ',' ORDER BY psk.position),
                    ''
                )               AS search_keywords
            FROM public.products p
            LEFT JOIN public.product_search_keywords psk
                ON psk.product_id = p.id
            WHERE p.is_active = TRUE
              AND p.name ILIKE :query
            GROUP BY p.id, p.name
            ORDER BY p.name
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
    product_category_id: str | int,
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
            """
            SELECT
                p.id::text                AS product_id,
                p.name                    AS japanese_title,
                p.work_id::text           AS work_id,
                p.manufacturer_id::text   AS manufacturer_id,
                p.product_category_id::text AS product_category_id,
                COALESCE(p.mark, '')      AS mark,
                COALESCE(
                    STRING_AGG(psk.keyword, ',' ORDER BY psk.position),
                    ''
                )                         AS search_keywords
            FROM public.products p
            LEFT JOIN public.product_search_keywords psk
                ON psk.product_id = p.id
            WHERE p.is_active = TRUE
              AND (
                p.name ILIKE :title_pattern
                OR (
                    p.work_id::text = :work_id
                    AND p.manufacturer_id::text = :manufacturer_id
                    AND p.product_category_id = :product_category_id
                )
              )
            GROUP BY
                p.id, p.name,
                p.work_id, p.manufacturer_id, p.product_category_id, p.mark
            ORDER BY p.name
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
    ADR-1002 Phase B: PostgreSQL SEQUENCE で採番する（冪等・競合なし）。
    SEQUENCE が存在しない環境（テスト等）では MAX+1 フォールバックを使う。
    """
    # Try SEQUENCE first (production, post-Phase-B migration)
    try:
        result = await db.execute(text("SELECT nextval('public.product_code_seq')"))
        num = result.scalar_one()
        return f"PM{num:04d}"
    except Exception:
        # Fallback: MAX+1 approach (test environments without migration)
        await db.rollback()
        result = await db.execute(
            text(
                """
                SELECT product_code FROM public.products
                WHERE product_code ~ '^PM[0-9]{4}$'
                ORDER BY product_code DESC LIMIT 1
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
    product_kind_id: str | int,
    work_id: str | int,
    manufacturer_id: str,
    product_category_id: str | int,
    japanese_title: str,
    release_date: str | None,
    search_keywords: str,
    exclude_keywords: str,
    mark: str = "",
    english_title: str = "",
    force: bool = False,
    commit: bool = True,
    product_format_id: int | None = None,
    blank_confirmations: list[str] | None = None,
    actor: str = "",
) -> dict[str, Any]:
    """
    GAS: createProductMasterV2FromAnalysisReview 相当。

    1. 重複チェック（重複あり かつ force=False → 早期 return）
    2. PM コード採番
    3. public.products に INSERT
    4. product_search_keywords / product_exclude_keywords に INSERT
    5. post-write gate

    commit=False: caller owns commit/rollback, including the post-write check.
    force=True: GAS ソフトブロック準拠。重複候補があっても登録を続行する。
    """
    # ADR-1020 便3: 足りない項目があれば DB を読む前に止める（全入口がここを通る）
    missing = missing_for_create({
        "japanese_title": japanese_title, "english_title": english_title, "mark": mark,
        "release_date": release_date, "search_keywords": search_keywords,
        "exclude_keywords": exclude_keywords, "work_id": work_id,
        "product_format_id": product_format_id, "product_category_id": product_category_id,
        "blank_confirmations": blank_confirmations,
    })
    if missing:
        raise ValueError("REQUIRED_FIELDS_MISSING:" + ",".join(missing))
    try:
        _work_id_int: int | None = int(work_id) if str(work_id).strip() else None
    except (TypeError, ValueError):
        _work_id_int = None
    await _validate_product_format(db, product_format_id, work_id=_work_id_int)
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

    work_id_int = int(work_id)
    # category_class: work_id（type_master.name_ja）から導出
    series_row = await db.execute(
        text("SELECT name_ja FROM public.type_master WHERE id = :id"),
        {"id": work_id_int},
    )
    sr = series_row.fetchone()
    category_class = sr.name_ja if sr else ""

    rd = date.fromisoformat(release_date.strip()) if release_date and release_date.strip() else None

    product_kind_id_int = int(product_kind_id) if product_kind_id else None

    # public.products INSERT
    await db.execute(text("SET LOCAL app.is_operator = 'true'"))
    product_row = await db.execute(
        text(
            """
            INSERT INTO public.products
                (product_code, name, release_date, category_class,
                 product_kind_id, work_id, manufacturer_id, product_category_id,
                 mark, name_en, product_format_id, is_active)
            VALUES
                (:code, :japanese_title, :release_date, :category_class,
                 :product_kind_id, :work_id, :manufacturer_id, :product_category_id,
                 :mark, :english_title, :product_format_id, TRUE)
            RETURNING id::text AS id, id AS int_id
            """
        ),
        {
            "code": pm_code,
            "japanese_title": japanese_title.strip(),
            "release_date": rd,
            "category_class": category_class,
            "product_kind_id": product_kind_id_int,
            "work_id": work_id_int,
            "manufacturer_id": manufacturer_id,
            "product_category_id": product_category_id,
            "mark": mark.strip() or None,
            "english_title": english_title.strip() or None,
            "product_format_id": int(product_format_id) if product_format_id is not None else None,
        },
    )
    new_row = product_row.fetchone()
    if new_row is None:
        raise ValueError("PRODUCT_MASTER_V2_INSERT_FAILED")
    product_id_int = new_row.int_id  # integer for keyword FK references and post-write gate

    # ADR-1020 便1: 印の保存（来たときだけ・D3）
    confirmed = set(blank_confirmations or [])
    filled_values = {
        "name": japanese_title, "name_en": english_title, "mark": mark,
        "release_date": release_date, "search_keywords": search_keywords,
        "exclude_keywords": exclude_keywords, "work_id": work_id,
        "product_format_id": product_format_id, "product_category_id": product_category_id,
    }
    if confirmed:
        await save_blank_confirmations(
            db, product_id=product_id_int, values=filled_values, confirmations=confirmed, actor=actor,
        )

    # search_keywords INSERT
    if search_keywords.strip():
        for pos, kw in enumerate(
            [k.strip() for k in search_keywords.split(",") if k.strip()], start=1
        ):
            await db.execute(
                text(
                    """
                    INSERT INTO public.product_search_keywords
                        (product_id, keyword, position)
                    VALUES (:pid, :kw, :pos)
                    """
                ),
                {"pid": product_id_int, "kw": kw, "pos": pos},
            )

    # exclude_keywords INSERT
    if exclude_keywords.strip():
        for pos, kw in enumerate(
            [k.strip() for k in exclude_keywords.split(",") if k.strip()], start=1
        ):
            await db.execute(
                text(
                    """
                    INSERT INTO public.product_exclude_keywords
                        (product_id, keyword, position)
                    VALUES (:pid, :kw, :pos)
                    """
                ),
                {"pid": product_id_int, "kw": kw, "pos": pos},
            )

    if commit:
        await db.commit()

    # post-write gate: 挿入した id が実際に存在するか確認
    verify = await db.execute(
        text(
            "SELECT id FROM public.products WHERE id = :id"
        ),
        {"id": product_id_int},
    )
    vr = verify.fetchone()
    if vr is None:
        raise ValueError("PRODUCT_MASTER_V2_POST_WRITE_GATE_FAILED")

    collisions = await find_code_collisions(
        db,
        product_code=pm_code,
        mark=mark,
        name=japanese_title.strip(),
        search_keywords=_split_csv_words(search_keywords),
        exclude_keywords=_split_csv_words(exclude_keywords),
        exclude_product_id=product_id_int,
    )
    return {"ok": True, "product_id": str(product_id_int), "code_collisions": collisions}


# ---------------------------------------------------------------------------
# B-5: 検索キーワード追加（WRITE）
# ---------------------------------------------------------------------------


async def add_search_keyword(
    db: AsyncSession,
    *,
    product_id: int,
    new_keyword: str,
) -> dict[str, Any]:
    """
    GAS: addProductMasterV2SearchKeyword 相当。

    既存キーワードは削除しない。重複は KEYWORD_ALREADY_EXISTS で返す。
    """
    kw = new_keyword.strip()
    if not kw:
        raise ValueError("SEARCH_KEYWORD_EMPTY")

    # product の存在確認
    pid_row = await db.execute(
        text(
            """
            SELECT id
            FROM public.products
            WHERE id = :pid AND is_active = TRUE
            FOR UPDATE
            """
        ),
        {"pid": product_id},
    )
    pr = pid_row.fetchone()
    if pr is None:
        raise ValueError("SEARCH_KEYWORD_PRODUCT_NOT_FOUND")
    product_uuid = pr.id

    # 既存キーワード確認
    existing = await db.execute(
        text(
            """
            SELECT keyword
            FROM public.product_search_keywords
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
            """
            INSERT INTO public.product_search_keywords
                (product_id, keyword, position)
            VALUES (:pid, :kw, :pos)
            """
        ),
        {"pid": product_uuid, "kw": kw, "pos": next_pos},
    )
    await db.commit()

    return {"ok": True}


# ---------------------------------------------------------------------------
# PR-D: 除外ワード追加（WRITE）
# ---------------------------------------------------------------------------


async def add_exclude_keyword(
    db: AsyncSession,
    *,
    product_id: int,
    new_keyword: str,
) -> dict[str, Any]:
    """
    add_search_keyword を写した作り（design.md PR-D）。

    既存キーワードは削除しない。重複は KEYWORD_ALREADY_EXISTS で返す。
    """
    kw = new_keyword.strip()
    if not kw:
        raise ValueError("EXCLUDE_KEYWORD_EMPTY")

    # product の存在確認
    pid_row = await db.execute(
        text(
            """
            SELECT id
            FROM public.products
            WHERE id = :pid AND is_active = TRUE
            FOR UPDATE
            """
        ),
        {"pid": product_id},
    )
    pr = pid_row.fetchone()
    if pr is None:
        raise ValueError("EXCLUDE_KEYWORD_PRODUCT_NOT_FOUND")
    product_uuid = pr.id

    # 既存キーワード確認
    existing = await db.execute(
        text(
            """
            SELECT keyword
            FROM public.product_exclude_keywords
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
            """
            INSERT INTO public.product_exclude_keywords
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
