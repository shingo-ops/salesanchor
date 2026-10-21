"""
PARITY-03: 解析レビュー API サービス層。

GAS の getAnalysisReviewPage に相当する解析結果一覧取得ロジック。

TCG 解析システムは tenant_004 専用スキーマ。全 SQL は tenant_004. で修飾する。
DB 書き込みは行わない（読み取り専用）。
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import is_postgresql
from app.services.line_analysis_v102_svc import V102_PROMPT_VERSION_PREFIX
from app.services.review_reason_codes_svc import build_review_reason_details, load_review_reason_codes
from app.services.tcg_condition_review_svc import review_joins, source_cte
from app.services.tcg_result_order import result_order_sql
from app.services.v102_gap_lines import gap_suspects_by_item
from app.services.v102_gap_suspect_view import with_candidate_names
from app.services.v102_human_decisions_svc import Decisions, format_decimal, load_v102_decisions

TCG_SCHEMA = "public"

# ---------------------------------------------------------------------------
# review_issues ラベル定数
# ---------------------------------------------------------------------------

_ISSUE_PID_UNRESOLVED = "PRODUCT_ID_UNRESOLVED"
_ISSUE_UNIT_UNRESOLVED = "UNIT_UNRESOLVED"
_ISSUE_EXCLUDED = "EXCLUDED"
_ISSUE_MASTER_UNREGISTERED = "PRODUCT_MASTER_UNREGISTERED"
_ISSUE_SUPPLIER_UNREGISTERED = "SUPPLIER_UNREGISTERED"
_ISSUE_PRODUCT_CONFIRMED = "PRODUCT_CONFIRMED"

def _manual_values(decision: Decisions | None) -> dict[str, str]:
    """人が直した項目だけ（数字は format_decimal の書式。メモを空にした件は note が空文字）。"""
    if decision is None:
        return {}
    v = decision.values
    candidates = {
        "quantity": format_decimal(v.quantity) if v.quantity is not None else None,
        "price": format_decimal(v.price) if v.price is not None else None,
        "unit": v.unit, "note": v.note, "status": v.status,
    }
    return {key: value for key, value in candidates.items() if value is not None}


def _thought_summaries(stored: object) -> list[str] | None:
    """extraction_attempts.thought_summaries（JSONB）→ list[str] | None。JSONB が文字列で返る場合（asyncpg + text()）はここで読む。"""
    if isinstance(stored, str):
        try:
            stored = json.loads(stored)
        except json.JSONDecodeError:
            return None
    if not isinstance(stored, list):
        return None
    return [x for x in stored if isinstance(x, str)]


# ---------------------------------------------------------------------------
# 共通 FROM 句（全クエリで再利用）
# ---------------------------------------------------------------------------

def _base_from(*, include_inactive: bool = False) -> str:
    return f"""
    FROM {TCG_SCHEMA}.analysis_results ar
    JOIN {TCG_SCHEMA}.extraction_items ei ON ei.id = ar.extraction_item_id
    JOIN {TCG_SCHEMA}.extraction_jobs ej ON ej.id = ei.extraction_job_id
    JOIN {TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id AND {"ar.is_current = TRUE" if include_inactive else "sm.is_active = TRUE"}
    JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
    LEFT JOIN public.suppliers ps ON ps.id = sc.supplier_id
    LEFT JOIN public.products p ON p.id = ar.product_id
    LEFT JOIN public.type_master ws ON ws.id = p.work_id
    {review_joins(schema=TCG_SCHEMA)}
"""


_BASE_FROM = _base_from()

# ---------------------------------------------------------------------------
# WHERE 句ビルダー
# ---------------------------------------------------------------------------


# 要確認の定義（1か所）。旧解析版（v102 以外）の行は要確認に出さない。
_NEEDS_REVIEW_COND = (
    "((NOT ar.pid_resolved OR NOT ar.unit_resolved OR cr.needs_review)"
    " AND COALESCE(starts_with(ej.prompt_version, :v102_prefix), FALSE))"
)

# ---------------------------------------------------------------------------
# 一覧の SELECT 列と取得ログの LATERAL（今の道と新しい道の両方がここを使う＝1か所）
# 文字列は一字一句変えない（SQL スナップショット試験が sha256 で守る）。
# ---------------------------------------------------------------------------

_ITEM_COLUMNS = f"""ei.id::text                          AS extraction_item_id,
            ej.source_message_id::text           AS source_message_id,
            ej.system_review_detail,
            COALESCE(ps.name, '不明')            AS provider,
            sm.raw_text,
            sm.line_posted_at                    AS posted_at,
            ei.raw_product_name,
            ei.raw_quantity,
            ei.raw_price,
            ei.raw_unit,
            ei.raw_state,
            ei.raw_memo,
            ei.line_start,
            ei.line_end,
            p.work_id::text                      AS work_id,
            ws.name_ja                           AS work_name,
            ws.name_en                           AS work_alt_name,
            p.id::text                           AS product_code,
            p.name                               AS product_title,
            ar.product_id::text                  AS product_uuid,
            ar.pid_resolved,
            ar.pid_basis,
            ar.condition_basis,
            ar.unit_canonical,
            ar.unit_resolved,
            cr.canonical AS condition_canonical,
            cr.condition_id, cr.review_version, cr.needs_review, cr.review_reasons,
            cr.valid_ack AS condition_confirmed, cr.classification AS empty_box_classification,
            ar.note_ja,
            ar.status,
            ar.exclusion,
            ar.quantity_normalized,
            ar.price_normalized,
            (ps.id IS NOT NULL)                  AS supplier_registered,
            COALESCE(starts_with(ej.prompt_version, :v102_prefix), FALSE) AS is_v102,
            COALESCE(
                (SELECT ic.system_value = ic.human_value
                 FROM {TCG_SCHEMA}.item_corrections ic
                 WHERE ic.extraction_item_id = ei.id
                   AND ic.field_name = 'product_id'
                 ORDER BY ic.corrected_at DESC
                 LIMIT 1),
                FALSE
            )                                    AS product_confirmed,
            eat.thought_summaries"""

_EAT_LATERAL = f"""LEFT JOIN LATERAL (
            SELECT ea.thought_summaries
            FROM {TCG_SCHEMA}.extraction_attempts ea
            WHERE ea.extraction_job_id = ej.id AND ea.phase = 'completed'
            ORDER BY ea.started_at DESC, ea.id DESC
            LIMIT 1
        ) eat ON TRUE"""


def _build_where(
    *,
    query: str | None,
    provider: str | None,
    status_tab: str,
    review_only: bool,
    unregistered_only: bool,
    unresolved_unit_only: bool,
    work_id: str | None = None,
    extraction_item_ids: list[str] | None = None,
) -> tuple[str, dict]:
    """フィルタ条件を WHERE 句と bind パラメータに変換する。"""
    conditions: list[str] = []
    params: dict = {}

    if extraction_item_ids is not None:
        conditions.append("ei.id = ANY(CAST(:item_ids AS uuid[]))")
        params["item_ids"] = extraction_item_ids

    if query:
        conditions.append(
            "(ei.raw_product_name ILIKE :query"
            " OR COALESCE(ps.name, '') ILIKE :query"
            " OR p.id::text ILIKE :query)"
        )
        params["query"] = f"%{query}%"

    if provider:
        conditions.append("ps.name = :provider")
        params["provider"] = provider

    # status_tab による絞り込み（review_only より優先）
    if status_tab == "NEEDS_REVIEW":
        conditions.append(_NEEDS_REVIEW_COND)
        params["v102_prefix"] = V102_PROMPT_VERSION_PREFIX
    elif status_tab == "ACKED":
        conditions.append("cr.review_acked")
    elif status_tab == "PRODUCT_MASTER_UNREGISTERED":
        conditions.append("ar.pid_basis = 'NONE'")
    elif status_tab == "SUPPLIER_UNREGISTERED":
        conditions.append("ps.id IS NULL")
    elif status_tab == "PRODUCT_ID_UNRESOLVED":
        conditions.append("NOT ar.pid_resolved")
    elif status_tab == "NORMAL_COMPLETED":
        conditions.append(
            "ar.pid_resolved AND ar.unit_resolved AND ar.exclusion IS NULL AND NOT cr.needs_review"
        )
    # 'ALL' は追加条件なし

    # チェックボックスフィルタ（タブ絞り込みに追加）
    if review_only and status_tab not in ("NEEDS_REVIEW",):
        conditions.append(_NEEDS_REVIEW_COND)
        params["v102_prefix"] = V102_PROMPT_VERSION_PREFIX
    if unregistered_only:
        conditions.append("ar.pid_basis = 'NONE'")
    if unresolved_unit_only:
        conditions.append("NOT ar.unit_resolved")
    if work_id:
        conditions.append("p.work_id = :work_id")
        params["work_id"] = work_id

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
    product_confirmed: bool = False,
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
    if product_confirmed:
        issues.append(_ISSUE_PRODUCT_CONFIRMED)
    return issues


async def _fetch_needs_review_posted_desc(
    db: AsyncSession,
    *,
    src: str,
    base_from: str,
    where: str,
    params: dict,
    offset: int,
    limit: int,
    posted_within_hours: int | None,
) -> tuple[list, int, list[str]]:
    """要確認タブ専用の道: 件数・仕入元・本体を1本の SQL で取る（設計 ADR-1023 改訂 2026-10-21, §10）。

    並びは投稿日の新しい順 → 投稿 id → 既存の result_order_sql()（全順序）。
    戻り値は (行, 総件数, 仕入元の名前一覧)。
    """
    assert where.startswith("WHERE "), where  # NEEDS_REVIEW は必ず WHERE で始まる（窓の条件を AND でつなぐ）
    window = ""
    if posted_within_hours is not None:
        # 24時間の絞り（S3）。+0秒を足すのは、素直な比較だと索引の見積りが1行になり
        # 本番で55秒かかったため（2026-10-20 実測）。消さないこと。
        window = (
            " AND (sm.line_posted_at + interval '0 second') >= now() - make_interval(hours => :posted_within_hours)"
        )
    sql = f"""{src}
        , base AS MATERIALIZED (
            SELECT
                row_number() OVER (ORDER BY sm.line_posted_at DESC NULLS LAST, sm.id ASC, {result_order_sql()}) AS rn,
                {_ITEM_COLUMNS}
            {base_from}
            {_EAT_LATERAL}
            {where}{window}
        )
        , meta AS (
            SELECT count(*) AS total,
                   COALESCE(json_agg(DISTINCT provider ORDER BY provider) FILTER (WHERE provider IS NOT NULL), '[]'::json) AS providers
            FROM base
        )
        SELECT meta.total AS meta_total, meta.providers AS meta_providers, base.*
        FROM meta LEFT JOIN base ON base.rn > :offset AND base.rn <= :offset + :limit
        ORDER BY base.rn
    """
    p = dict(params, limit=limit, offset=offset, v102_prefix=V102_PROMPT_VERSION_PREFIX)
    if posted_within_hours is not None:
        p["posted_within_hours"] = posted_within_hours

    if is_postgresql(db):
        # S2: JIT をこの1本だけ切る（本番 EXPLAIN で JIT の準備に時間を取られた。設計 §10-4）。
        # is_local=true なので、例外時も元の値はトランザクション終了で戻る。
        prev_jit = (await db.execute(text("SELECT current_setting('jit')"))).scalar_one()
        await db.execute(text("SELECT set_config('jit', 'off', true)"))
        result_rows = (await db.execute(text(sql), p)).fetchall()
        await db.execute(text("SELECT set_config('jit', :v, true)"), {"v": prev_jit})
    else:
        result_rows = (await db.execute(text(sql), p)).fetchall()

    if not result_rows:
        return [], 0, []
    total = int(result_rows[0].meta_total)
    providers_raw = result_rows[0].meta_providers
    # json 列はドライバによって文字列で返る
    providers = json.loads(providers_raw) if isinstance(providers_raw, str) else list(providers_raw or [])
    # ページが空のときは base 側が NULL の1行だけ返る
    rows = [r for r in result_rows if r.extraction_item_id is not None]
    return rows, total, providers


# ---------------------------------------------------------------------------
# 解析結果一覧（A-1）
# ---------------------------------------------------------------------------


async def _fetch_current_path(
    db: AsyncSession,
    *,
    src: str,
    base_from: str,
    where: str,
    params: dict,
    offset: int,
    limit: int,
) -> tuple[list, int, list[str]]:
    """今の道: 件数・仕入元・本体を3本の SQL で取る（CSV・シート・配信・他タブ・確認済みタブが使う）。

    SQL 文字列は便1より前から1文字も変えていない（test_tcg_analysis_review_sql_snapshot.py が sha256 で守る）。
    """
    # 総件数
    count_sql = f"{src} SELECT COUNT(*) {base_from} {where}"
    total: int = (await db.execute(text(count_sql), params)).scalar_one()

    # 提供者一覧（フィルタ後の全仕入元）
    prov_sql = f"""{src}
        SELECT DISTINCT COALESCE(ps.name, '不明') AS name
        {base_from}
        {where}
        ORDER BY name
    """
    provider_rows = (await db.execute(text(prov_sql), params)).fetchall()
    providers = [r[0] for r in provider_rows]

    # アイテム一覧
    items_sql = f"""{src}
        , result_order_page AS MATERIALIZED (
            SELECT ei.id
            {base_from}
            {where}
            ORDER BY {result_order_sql()}
            LIMIT :limit OFFSET :offset
        )
        SELECT
            {_ITEM_COLUMNS}
        {base_from}
        JOIN result_order_page ON result_order_page.id = ei.id
        {_EAT_LATERAL}
        {where}
        ORDER BY {result_order_sql()}
    """
    item_params = dict(params, limit=limit, offset=offset, v102_prefix=V102_PROMPT_VERSION_PREFIX)
    rows = (await db.execute(text(items_sql), item_params)).fetchall()
    return rows, total, providers



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
    work_id: str | None = None,
    extraction_item_ids: list[str] | None = None,
    order: str = "default",
    posted_within_hours: int | None = None,
) -> dict:
    """
    解析結果一覧を返す（GAS: getAnalysisReviewPage 相当）。

    ページングはアイテム単位（GAS の groupBySource=false 相当）。
    groupBySource は FE 側でグルーピングして表示する。

    order / posted_within_hours は新しい道でだけ効く。他の道では無視する
    （要確認画面の要確認タブだけが送る）。
    """
    where, params = _build_where(
        query=query,
        provider=provider,
        status_tab=status_tab,
        review_only=review_only,
        unregistered_only=unregistered_only,
        unresolved_unit_only=unresolved_unit_only,
        work_id=work_id,
        extraction_item_ids=extraction_item_ids,
    )
    # ID 指定時は在庫表と同じ範囲（非アクティブな投稿も含む）で引く
    inactive = extraction_item_ids is not None
    src = source_cte(schema=TCG_SCHEMA, include_inactive=inactive)
    base_from = _base_from(include_inactive=inactive)

    if status_tab == "NEEDS_REVIEW" and order == "posted_desc" and extraction_item_ids is None:
        rows, total, providers = await _fetch_needs_review_posted_desc(
            db,
            src=src,
            base_from=base_from,
            where=where,
            params=params,
            offset=offset,
            limit=limit,
            posted_within_hours=posted_within_hours,
        )
    else:
        rows, total, providers = await _fetch_current_path(
            db, src=src, base_from=base_from, where=where, params=params, offset=offset, limit=limit
        )

    reason_table = await load_review_reason_codes(db)
    page_ids = {row.extraction_item_id for row in rows}
    raw_suspects: dict[str, dict] = {}
    for row in rows:
        raw_suspects.update(gap_suspects_by_item(row.system_review_detail))
    suspects = await with_candidate_names(db, {k: v for k, v in raw_suspects.items() if k in page_ids})
    decisions = await db.run_sync(lambda sync: load_v102_decisions(sync, page_ids))  # 直した値の読み方の正本
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
                "posted_at": row.posted_at,
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
                    "work_id": row.work_id or "",
                    "work_name": row.work_name or "",
                    "product_id": row.product_code or "",
                    "product_title": row.product_title or "",
                    "product_uuid": row.product_uuid or "",
                    "pid_resolved": "YES" if row.pid_resolved else "NO",
                    "pid_basis": row.pid_basis or "",
                    "condition_basis": row.condition_basis or "",
                    "unit": row.unit_canonical or "",
                    "unit_resolved": "YES" if row.unit_resolved else "NO",
                    "condition": row.condition_canonical or "",
                    "status": row.status or "",
                    "note": row.note_ja or "",
                    "exclusion": row.exclusion or "",
                    "quantity": format_decimal(row.quantity_normalized),
                    "price": format_decimal(row.price_normalized),
                },
                "manual_values": _manual_values(decisions.get(row.extraction_item_id)),
                "condition_review": {
                    "condition_id": row.condition_id, "review_version": row.review_version,
                    "needs_review": row.needs_review, "review_reasons": row.review_reasons or "",
                    "confirmed": row.condition_confirmed, "classification": row.empty_box_classification,
                },
                "review_reason_details": build_review_reason_details(row.review_reasons, reason_table),
                "is_v102": bool(row.is_v102),
                "thought_summaries": _thought_summaries(row.thought_summaries),
                "gap_suspect": suspects.get(row.extraction_item_id),
                "review_issues": (["CONDITION_REVIEW_REQUIRED"] if row.needs_review else []) + _compute_issues(
                    pid_resolved=row.pid_resolved,
                    pid_basis=row.pid_basis,
                    unit_resolved=row.unit_resolved,
                    exclusion=row.exclusion,
                    supplier_registered=row.supplier_registered,
                    product_confirmed=bool(row.product_confirmed),
                ),
            }
        )

    if strip_raw_text:
        for item in items:
            item["raw_text"] = ""

    # works 一覧取得（tcg_product_import.py:134-142 と同一パターン）
    work_rows = await db.execute(text(
        "SELECT s.id, s.code, s.name_ja AS display_name, s.name_en AS alt_name FROM public.type_master s "
        "WHERE s.is_active = TRUE OR EXISTS (SELECT 1 FROM public.products p "
        "WHERE p.work_id = s.id) ORDER BY s.code ASC"
    ))
    works = [
        {"id": str(r.id), "code": r.code, "display_name": r.display_name or "", "alt_name": r.alt_name or ""}
        for r in work_rows.fetchall()
    ]

    return {
        "items": items,
        "total": total,
        "item_total": total,
        "offset": offset,
        "limit": limit,
        "providers": providers,
        "works": works,
    }
