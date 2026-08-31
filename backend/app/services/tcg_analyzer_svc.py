"""
MIG-04 Phase 3: TCG 照合サービス。

feat/tcg-migration-phase2:backend/tcg_migration/analyzer.py のロジックを
backend/app/services 層に移植。

extraction_items → analysis_results へのキーワード照合・単位解決・状態解決を行う。
同期 SQLAlchemy Session を使用（Celery タスク / スクリプト実行から呼ぶため）。

エンジンバージョン: "name-first-v1"

TCG解析システムは tenant_004 専用スキーマ。全 SQL は tenant_004. で修飾する。
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ENGINE_VERSION = "name-first-v1"

# TCG解析システムは tenant_004 専用スキーマ
TCG_SCHEMA = "tenant_004"


# ---------------------------------------------------------------------------
# マスタロード
# ---------------------------------------------------------------------------


def load_lookup_maps(
    session: Session,
) -> tuple[dict, dict, dict, dict, dict]:
    """
    照合に必要なルックアップマップを一括ロードする。

    Returns:
      product_code_to_uuid   : {code: uuid_str}
      unit_alias_to_canonical: {alias_text: canonical}
      unit_canonical_to_uuid : {canonical: uuid_str}
      cond_alias_to_canonical: {alias_text: canonical}
      cond_canonical_to_uuid : {canonical: uuid_str}
    """
    # --- 商品コード → UUID ---
    rows = session.execute(
        text(f"SELECT code, id FROM {TCG_SCHEMA}.tcg_products WHERE is_active = TRUE")
    ).fetchall()
    product_code_to_uuid: dict[str, str] = {r[0]: str(r[1]) for r in rows}

    # --- 単位エイリアス → canonical + UUID ---
    rows = session.execute(
        text(
            f"""
            SELECT ua.alias_text, u.canonical, u.id
            FROM {TCG_SCHEMA}.unit_aliases ua
            JOIN {TCG_SCHEMA}.units u ON u.id = ua.unit_id
            WHERE u.is_active = TRUE
            """
        )
    ).fetchall()
    unit_alias_to_canonical: dict[str, str] = {}
    unit_canonical_to_uuid: dict[str, str] = {}
    for alias_text, canonical, uid in rows:
        unit_alias_to_canonical[alias_text] = canonical
        unit_canonical_to_uuid[canonical] = str(uid)

    # canonical 自体もエイリアスとして登録（直接マッチ用）
    for canonical, uid in list(unit_canonical_to_uuid.items()):
        unit_alias_to_canonical.setdefault(canonical, canonical)

    # --- 状態エイリアス → canonical + UUID ---
    rows = session.execute(
        text(
            f"""
            SELECT ca.alias_text, c.canonical, c.id
            FROM {TCG_SCHEMA}.condition_aliases ca
            JOIN {TCG_SCHEMA}.conditions c ON c.id = ca.condition_id
            WHERE c.is_active = TRUE
            """
        )
    ).fetchall()
    cond_alias_to_canonical: dict[str, str] = {}
    cond_canonical_to_uuid: dict[str, str] = {}
    for alias_text, canonical, cid in rows:
        cond_alias_to_canonical[alias_text] = canonical
        cond_canonical_to_uuid[canonical] = str(cid)

    # canonical 自体もエイリアスとして登録
    for canonical, cid in list(cond_canonical_to_uuid.items()):
        cond_alias_to_canonical.setdefault(canonical, canonical)

    return (
        product_code_to_uuid,
        unit_alias_to_canonical,
        unit_canonical_to_uuid,
        cond_alias_to_canonical,
        cond_canonical_to_uuid,
    )


def load_product_keywords(
    session: Session,
) -> tuple[dict, dict]:
    """
    商品ごとの検索キーワード・除外キーワードをロードする。

    Returns:
      search_kw : {product_code: [kw1, kw2, ...]}
      exclude_kw: {product_code: [kw1, kw2, ...]}
    """
    # 検索キーワード
    rows = session.execute(
        text(
            f"""
            SELECT p.code, psk.keyword
            FROM {TCG_SCHEMA}.product_search_keywords psk
            JOIN {TCG_SCHEMA}.tcg_products p ON p.id = psk.product_id
            WHERE p.is_active = TRUE
            ORDER BY p.code, psk.position
            """
        )
    ).fetchall()
    search_kw: dict[str, list[str]] = {}
    for code, kw in rows:
        if code not in search_kw:
            search_kw[code] = []
        search_kw[code].append(kw)

    # 除外キーワード
    rows = session.execute(
        text(
            f"""
            SELECT p.code, pek.keyword
            FROM {TCG_SCHEMA}.product_exclude_keywords pek
            JOIN {TCG_SCHEMA}.tcg_products p ON p.id = pek.product_id
            WHERE p.is_active = TRUE
            ORDER BY p.code, pek.position
            """
        )
    ).fetchall()
    exclude_kw: dict[str, list[str]] = {}
    for code, kw in rows:
        if code not in exclude_kw:
            exclude_kw[code] = []
        exclude_kw[code].append(kw)

    return search_kw, exclude_kw


# ---------------------------------------------------------------------------
# キーワード照合
# ---------------------------------------------------------------------------


def match_pid_name_first(
    raw_name: str,
    product_codes: list[str],
    search_kw: dict,
    exclude_kw: dict,
) -> tuple[Optional[str], str, bool, list[str]]:
    """
    raw_name に対してキーワード照合を行い product_code を解決する。

    最長マッチキーワードを持つ商品を優先する。
    除外キーワードにヒットした商品は候補から除外する。

    Returns:
      (matched_code, pid_basis, resolved, candidates)
      - 0 candidates → (None, "NONE", False, [])
      - 1 candidate  → (code, "SK:<kw>", True, [code])
      - 2+ candidates → (best_code, "MULTI(PM.../...):要確認", False, [codes])

    pid_basis は VARCHAR(100) に収まるよう截断する。
    """
    candidates: list[tuple[str, str, int]] = []  # (code, matched_kw, kw_len)

    for code in product_codes:
        kws = search_kw.get(code, [])
        ex_kws = exclude_kw.get(code, [])

        best_match: Optional[str] = None
        best_len = 0

        for kw in kws:
            if kw in raw_name and len(kw) > best_len:
                best_match = kw
                best_len = len(kw)

        if best_match is None:
            continue

        # 除外キーワードチェック
        excluded = any(ex_kw in raw_name for ex_kw in ex_kws)
        if excluded:
            continue

        candidates.append((code, best_match, best_len))

    if not candidates:
        return (None, "NONE", False, [])

    # 最長マッチ優先でソート
    candidates.sort(key=lambda x: x[2], reverse=True)

    if len(candidates) == 1:
        code, kw, _ = candidates[0]
        pid_basis = f"SK:{kw}"[:100]
        return (code, pid_basis, True, [code])

    # 複数候補: 最長マッチを返すが resolved=False
    codes = [c[0] for c in candidates]
    best_code, best_kw, _ = candidates[0]
    parts = "/".join(f"PM.{c}" for c in codes[:5])
    pid_basis = f"MULTI({parts}):要確認"[:100]
    return (best_code, pid_basis, False, codes)


# ---------------------------------------------------------------------------
# 単位・状態解決
# ---------------------------------------------------------------------------


def resolve_unit(
    raw_unit: str,
    unit_alias_to_canonical: dict,
) -> tuple[Optional[str], bool]:
    """
    raw_unit → (canonical, resolved_bool)。
    解決不能は (None, False)。
    """
    if not raw_unit or not raw_unit.strip():
        return (None, False)

    stripped = raw_unit.strip()

    # 完全一致
    if stripped in unit_alias_to_canonical:
        return (unit_alias_to_canonical[stripped], True)

    # 小文字一致
    lower = stripped.lower()
    lower_map = {k.lower(): v for k, v in unit_alias_to_canonical.items()}
    if lower in lower_map:
        return (lower_map[lower], True)

    return (None, False)


def resolve_condition(
    raw_state: str,
    cond_alias_to_canonical: dict,
) -> Optional[str]:
    """
    raw_state → canonical または None。
    """
    if not raw_state or not raw_state.strip():
        return None

    stripped = raw_state.strip()

    if stripped in cond_alias_to_canonical:
        return cond_alias_to_canonical[stripped]

    # 小文字一致
    lower = stripped.lower()
    lower_map = {k.lower(): v for k, v in cond_alias_to_canonical.items()}
    if lower in lower_map:
        return lower_map[lower]

    return None


# ---------------------------------------------------------------------------
# 数値正規化
# ---------------------------------------------------------------------------


def _parse_numeric(raw: str) -> Optional[float]:
    """
    カンマ・通貨記号・全角数字を除去して float に変換する。
    失敗したら None を返す。
    """
    if not raw or not raw.strip():
        return None

    # 全角数字 → 半角
    s = raw.strip()
    s = s.translate(str.maketrans("０１２３４５６７８９", "0123456789"))

    # 通貨記号・単位・スペースを除去
    import re
    s = re.sub(r"[^\d.,]", "", s)
    s = s.replace(",", "")

    try:
        return float(s) if s else None
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# 照合メイン
# ---------------------------------------------------------------------------


def analyze_extraction_job(session: Session, extraction_job_id: str) -> dict:
    """
    extraction_job の全 extraction_items に対して照合を実行し、
    analysis_results を INSERT/UPDATE (冪等) する。

    Args:
        session: 同期 SQLAlchemy Session
        extraction_job_id: UUID 文字列

    Returns:
        {total, pid_resolved, unit_resolved, needs_review}
    """
    # ルックアップマップをロード
    (
        product_code_to_uuid,
        unit_alias_to_canonical,
        unit_canonical_to_uuid,
        cond_alias_to_canonical,
        cond_canonical_to_uuid,
    ) = load_lookup_maps(session)

    search_kw, exclude_kw = load_product_keywords(session)
    product_codes = list(product_code_to_uuid.keys())

    # extraction_items を取得
    rows = session.execute(
        text(
            f"""
            SELECT id, raw_product_name, raw_quantity, raw_price, raw_unit, raw_state
            FROM {TCG_SCHEMA}.extraction_items
            WHERE extraction_job_id = :ej_id
            ORDER BY line_start, id
            """
        ),
        {"ej_id": extraction_job_id},
    ).fetchall()

    now = datetime.now(timezone.utc)
    stats = {"total": 0, "pid_resolved": 0, "unit_resolved": 0, "needs_review": 0}

    for row in rows:
        (
            item_id,
            raw_product_name,
            raw_quantity,
            raw_price,
            raw_unit,
            raw_state,
        ) = row

        stats["total"] += 1
        raw_product_name = raw_product_name or ""
        raw_unit = raw_unit or ""
        raw_state = raw_state or ""

        # 商品照合
        matched_code, pid_basis, pid_resolved, candidates = match_pid_name_first(
            raw_product_name, product_codes, search_kw, exclude_kw
        )
        product_uuid = product_code_to_uuid.get(matched_code) if matched_code else None

        if pid_resolved:
            stats["pid_resolved"] += 1

        # 単位解決
        unit_canonical, unit_resolved = resolve_unit(raw_unit, unit_alias_to_canonical)
        unit_uuid = unit_canonical_to_uuid.get(unit_canonical) if unit_canonical else None

        if unit_resolved:
            stats["unit_resolved"] += 1

        # 状態解決
        condition_canonical = resolve_condition(raw_state, cond_alias_to_canonical)
        condition_uuid = (
            cond_canonical_to_uuid.get(condition_canonical) if condition_canonical else None
        )

        # 数量・価格正規化
        quantity_normalized = _parse_numeric(raw_quantity or "")
        price_normalized = _parse_numeric(raw_price or "")

        # needs_review 判定
        review_reasons: list[str] = []
        if not pid_resolved:
            review_reasons.append("pid_unresolved")
        if len(candidates) > 1:
            review_reasons.append("multi_candidate")
        needs_review = len(review_reasons) > 0

        if needs_review:
            stats["needs_review"] += 1

        review_reasons_str = ",".join(review_reasons) if review_reasons else None

        # analysis_results を UPSERT (extraction_item_id に UNIQUE 制約あり)
        session.execute(
            text(
                f"""
                INSERT INTO {TCG_SCHEMA}.analysis_results (
                    id,
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
                VALUES (
                    :id,
                    :extraction_item_id,
                    :product_id,
                    :pid_resolved,
                    :pid_basis,
                    :unit_id,
                    :unit_canonical,
                    :unit_resolved,
                    :condition_id,
                    :condition_canonical,
                    :condition_basis,
                    :quantity_normalized,
                    :price_normalized,
                    NULL,
                    'active',
                    NULL,
                    :needs_review,
                    :review_reasons,
                    :engine_version,
                    :computed_at,
                    :updated_at
                )
                ON CONFLICT (extraction_item_id)
                DO UPDATE SET
                    product_id          = EXCLUDED.product_id,
                    pid_resolved        = EXCLUDED.pid_resolved,
                    pid_basis           = EXCLUDED.pid_basis,
                    unit_id             = EXCLUDED.unit_id,
                    unit_canonical      = EXCLUDED.unit_canonical,
                    unit_resolved       = EXCLUDED.unit_resolved,
                    condition_id        = EXCLUDED.condition_id,
                    condition_canonical = EXCLUDED.condition_canonical,
                    condition_basis     = EXCLUDED.condition_basis,
                    quantity_normalized = EXCLUDED.quantity_normalized,
                    price_normalized    = EXCLUDED.price_normalized,
                    needs_review        = EXCLUDED.needs_review,
                    review_reasons      = EXCLUDED.review_reasons,
                    engine_version      = EXCLUDED.engine_version,
                    computed_at         = EXCLUDED.computed_at,
                    updated_at          = EXCLUDED.updated_at
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "extraction_item_id": str(item_id),
                "product_id": product_uuid,
                "pid_resolved": pid_resolved,
                "pid_basis": pid_basis,
                "unit_id": unit_uuid,
                "unit_canonical": unit_canonical,
                "unit_resolved": unit_resolved,
                "condition_id": condition_uuid,
                "condition_canonical": condition_canonical,
                "condition_basis": condition_canonical,
                "quantity_normalized": quantity_normalized,
                "price_normalized": price_normalized,
                "needs_review": needs_review,
                "review_reasons": review_reasons_str,
                "engine_version": ENGINE_VERSION,
                "computed_at": now,
                "updated_at": now,
            },
        )

    session.commit()

    logger.info(
        "[tcg_analyzer] extraction_job=%s stats=%s", extraction_job_id, stats
    )
    return stats


__all__ = [
    "ENGINE_VERSION",
    "load_lookup_maps",
    "load_product_keywords",
    "match_pid_name_first",
    "resolve_unit",
    "resolve_condition",
    "analyze_extraction_job",
]
