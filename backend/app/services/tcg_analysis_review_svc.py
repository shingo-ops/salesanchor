"""
PARITY-03: 解析レビュー API サービス層。

GAS の getAnalysisReviewPage に相当する解析結果一覧取得ロジック。

TCG 解析システムは tenant_004 専用スキーマ。全 SQL は tenant_004. で修飾する。
DB 書き込みは行わない（読み取り専用）。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TCG_SCHEMA = "tenant_004"

# ---------------------------------------------------------------------------
# review_issues ラベル定数
# ---------------------------------------------------------------------------

_ISSUE_PID_UNRESOLVED = "PRODUCT_ID_UNRESOLVED"
_ISSUE_UNIT_UNRESOLVED = "UNIT_UNRESOLVED"
_ISSUE_EXCLUDED = "EXCLUDED"
_ISSUE_MASTER_UNREGISTERED = "PRODUCT_MASTER_UNREGISTERED"
_ISSUE_SUPPLIER_UNREGISTERED = "SUPPLIER_UNREGISTERED"

# ---------------------------------------------------------------------------
# 共通 FROM 句（全クエリで再利用）
# ---------------------------------------------------------------------------

_BASE_FROM = f"""
    FROM {TCG_SCHEMA}.analysis_results ar
    JOIN {TCG_SCHEMA}.extraction_items ei ON ei.id = ar.extraction_item_id
    JOIN {TCG_SCHEMA}.extraction_jobs ej ON ej.id = ei.extraction_job_id
    JOIN {TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id
    JOIN {TCG_SCHEMA}.supplier_channels sc ON sc.id = sm.supplier_channel_id
    LEFT JOIN {TCG_SCHEMA}.tcg_suppliers ts ON ts.id = sc.supplier_id
    LEFT JOIN {TCG_SCHEMA}.tcg_products p ON p.id = ar.product_id
"""

# ---------------------------------------------------------------------------
# WHERE 句ビルダー
# ---------------------------------------------------------------------------


def _build_where(
    *,
    query: str | None,
    provider: str | None,
    status_tab: str,
    review_only: bool,
    unregistered_only: bool,
    unresolved_unit_only: bool,
) -> tuple[str, dict]:
    """フィルタ条件を WHERE 句と bind パラメータに変換する。"""
    conditions: list[str] = []
    params: dict = {}

    if query:
        conditions.append(
            "(ei.raw_product_name ILIKE :query"
            " OR COALESCE(ts.name, '') ILIKE :query"
            " OR COALESCE(p.code, '') ILIKE :query)"
        )
        params["query"] = f"%{query}%"

    if provider:
        conditions.append("ts.name = :provider")
        params["provider"] = provider

    # status_tab による絞り込み（review_only より優先）
    if status_tab == "NEEDS_REVIEW":
        conditions.append(
            "(NOT ar.pid_resolved OR NOT ar.unit_resolved OR ar.exclusion IS NOT NULL)"
        )
    elif status_tab == "PRODUCT_MASTER_UNREGISTERED":
        conditions.append("ar.pid_basis = 'NONE'")
    elif status_tab == "SUPPLIER_UNREGISTERED":
        conditions.append("ts.id IS NULL")
    elif status_tab == "PRODUCT_ID_UNRESOLVED":
        conditions.append("NOT ar.pid_resolved")
    elif status_tab == "NORMAL_COMPLETED":
        conditions.append(
            "ar.pid_resolved AND ar.unit_resolved AND ar.exclusion IS NULL"
        )
    # 'ALL' は追加条件なし

    # チェックボックスフィルタ（タブ絞り込みに追加）
    if review_only and status_tab not in ("NEEDS_REVIEW",):
        conditions.append(
            "(NOT ar.pid_resolved OR NOT ar.unit_resolved OR ar.exclusion IS NOT NULL)"
        )
    if unregistered_only:
        conditions.append("ar.pid_basis = 'NONE'")
    if unresolved_unit_only:
        conditions.append("NOT ar.unit_resolved")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params


# ---------------------------------------------------------------------------
# review_issues 計算
# ---------------------------------------------------------------------------


def _compute_issues(
    pid_resolved: bool,
    pid_basis: str | None,
    unit_resolved: bool,
    exclusion: str | None,
    supplier_registered: bool,
) -> list[str]:
    issues: list[str] = []
    if not pid_resolved:
        issues.append(_ISSUE_PID_UNRESOLVED)
        if pid_basis == "NONE":
            issues.append(_ISSUE_MASTER_UNREGISTERED)
    if not unit_resolved:
        issues.append(_ISSUE_UNIT_UNRESOLVED)
    if exclusion:
        issues.append(_ISSUE_EXCLUDED)
    if not supplier_registered:
        issues.append(_ISSUE_SUPPLIER_UNREGISTERED)
    return issues


# ---------------------------------------------------------------------------
# 解析結果一覧（A-1）
# ---------------------------------------------------------------------------


async def fetch_analysis_results(
    db: AsyncSession,
    *,
    query: str | None = None,
    provider: str | None = None,
    status_tab: str = "ALL",
    offset: int = 0,
    limit: int = 10,
    review_only: bool = False,
    unregistered_only: bool = False,
    unresolved_unit_only: bool = False,
    strip_raw_text: bool = False,
) -> dict:
    """
    解析結果一覧を返す（GAS: getAnalysisReviewPage 相当）。

    ページングはアイテム単位（GAS の groupBySource=false 相当）。
    groupBySource は FE 側でグルーピングして表示する。
    """
    where, params = _build_where(
        query=query,
        provider=provider,
        status_tab=status_tab,
        review_only=review_only,
        unregistered_only=unregistered_only,
        unresolved_unit_only=unresolved_unit_only,
    )

    # 総件数
    count_sql = f"SELECT COUNT(*) {_BASE_FROM} {where}"
    total: int = (await db.execute(text(count_sql), params)).scalar_one()

    # 提供者一覧（フィルタ後の全仕入元）
    prov_sql = f"""
        SELECT DISTINCT COALESCE(ts.name, '不明') AS name
        {_BASE_FROM}
        {where}
        ORDER BY name
    """
    provider_rows = (await db.execute(text(prov_sql), params)).fetchall()
    providers = [r[0] for r in provider_rows]

    # アイテム一覧
    items_sql = f"""
        SELECT
            ei.id::text                          AS extraction_item_id,
            ej.source_message_id::text           AS source_message_id,
            COALESCE(ts.name, '不明')            AS provider,
            sm.raw_text,
            ei.raw_product_name,
            ei.raw_quantity,
            ei.raw_price,
            ei.raw_unit,
            ei.raw_state,
            ei.raw_memo,
            ei.line_start,
            ei.line_end,
            p.code                               AS product_code,
            ar.pid_resolved,
            ar.pid_basis,
            ar.unit_canonical,
            ar.unit_resolved,
            ar.condition_canonical,
            ar.note_ja,
            ar.status,
            ar.exclusion,
            (ts.id IS NOT NULL)                  AS supplier_registered
        {_BASE_FROM}
        {where}
        ORDER BY sm.received_at DESC, ei.line_start ASC
        LIMIT :limit OFFSET :offset
    """
    item_params = dict(params, limit=limit, offset=offset)
    rows = (await db.execute(text(items_sql), item_params)).fetchall()

    items = []
    for row in rows:
        span = (
            f"L{row.line_start}-{row.line_end}"
            if row.line_start is not None
            else ""
        )
        items.append(
            {
                "extraction_item_id": row.extraction_item_id,
                "source_message_id": row.source_message_id,
                "provider": row.provider,
                "raw_text": row.raw_text or "",
                "gemini": {
                    "name": row.raw_product_name or "",
                    "quantity": row.raw_quantity or "",
                    "price": row.raw_price or "",
                    "unit": row.raw_unit or "",
                    "state": row.raw_state or "",
                    "memo": row.raw_memo or "",
                    "span": span,
                },
                "system": {
                    "product_id": row.product_code or "",
                    "pid_resolved": "YES" if row.pid_resolved else "NO",
                    "pid_basis": row.pid_basis or "",
                    "unit": row.unit_canonical or "",
                    "unit_resolved": "YES" if row.unit_resolved else "NO",
                    "condition": row.condition_canonical or "",
                    "status": row.status or "",
                    "note": row.note_ja or "",
                    "exclusion": row.exclusion or "",
                },
                "review_issues": _compute_issues(
                    pid_resolved=row.pid_resolved,
                    pid_basis=row.pid_basis,
                    unit_resolved=row.unit_resolved,
                    exclusion=row.exclusion,
                    supplier_registered=row.supplier_registered,
                ),
            }
        )

    if strip_raw_text:
        for item in items:
            item["raw_text"] = ""

    return {
        "items": items,
        "total": total,
        "item_total": total,
        "offset": offset,
        "limit": limit,
        "providers": providers,
    }
