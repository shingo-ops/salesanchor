"""
DIST-01: TCG 在庫配信サービス層。

設計書: ~/Documents/dist01_backup/DISTRIBUTION_DESIGN.md
担当: Session 3 (CC_TASK_DIST-01/02)

機能:
  D. SA 認証ユーティリティ（TCG_SHEETS_SA_KEY_FILE 環境変数）
  E. 出力データ取得クエリ（10列・確定フィルター）
  F. 配信処理コア（安全装置 7 項目）
  H. 失敗時の Discord 通知

安全装置:
  #1 spreadsheetId 完全一致検証
  #2 シート自動作成禁止
  #3 書き込み前に所有者を Drive API で確認・ログ記録
  #4 タブ名の DB 登録値との完全一致検証
  #5 書き込み行数を DIST_ROW_LIMIT（5000）で上限制限
  #6 失敗時 Discord 通知
  #7 配信履歴（日時・件数・成否）を DB に記録
  #8 再解析未完了（analysis_runs.completed_at IS NULL）があれば配信中止
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.services.tcg_condition_review_svc import review_joins, source_cte
from app.services.tcg_result_order import result_order_sql

# Step 4/5: TCG テーブルは public スキーマに移行済み。
# テスト互換性のため TCG_SCHEMA 属性を維持する（monkeypatch.setattr 対象）。
TCG_SCHEMA = "public"

# 安全装置 #5: 書き込み行数上限
DIST_ROW_LIMIT = 5000

# 出力ヘッダー（確定・14列）
DIST_HEADERS = [
    "投稿日時",
    "Mark",
    "Japanese Title",
    "English Title",
    "Condition",
    "Unit Price",
    "Quantity",
    "Note_JA",
    "Status",
    "Release Date",
    "Series",
    "提供者",
    "Search Keywords",
    "Ship_JA",
]

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


# ---------------------------------------------------------------------------
# D. SA 認証ユーティリティ
# ---------------------------------------------------------------------------

def _build_gspread_client() -> Any:
    """
    gspread クライアントを SA キーファイルから生成する。
    tcg_mirror.py の _build_client() と同パターン。
    """
    import gspread
    from google.oauth2.service_account import Credentials

    key_file = os.getenv("TCG_SHEETS_SA_KEY_FILE", "").strip()
    if not key_file:
        raise RuntimeError(
            "TCG_SHEETS_SA_KEY_FILE が未設定です。"
            "配信タスクを実行するにはこの環境変数を設定してください。"
        )
    creds = Credentials.from_service_account_file(key_file, scopes=_SCOPES)
    return gspread.authorize(creds)


# ---------------------------------------------------------------------------
# 安全装置 #1: spreadsheetId 完全一致検証
# ---------------------------------------------------------------------------

def _verify_spreadsheet_id(gc: Any, spreadsheet_id: str) -> Any:
    """
    spreadsheets.get で取得した spreadsheetId が引数と完全一致することを検証する。
    不一致またはシート不存在の場合は RuntimeError を raise する。
    シート自動作成は一切行わない。

    参考: write_mirror_once.py:verify_spreadsheet_id()
    """
    import gspread

    try:
        sh = gc.open_by_key(spreadsheet_id)
    except gspread.exceptions.SpreadsheetNotFound:
        raise RuntimeError(
            f"[安全装置 #1/#2] spreadsheetId={spreadsheet_id!r} のシートが見つかりません。"
            " シートの自動作成は行いません。"
        )

    meta = sh.fetch_sheet_metadata()
    actual_id = meta["spreadsheetId"]
    if actual_id != spreadsheet_id:
        raise RuntimeError(
            f"[安全装置 #1] spreadsheetId 不一致: 期待={spreadsheet_id!r} 実際={actual_id!r}"
        )

    logger.info("[dist] spreadsheetId 検証 OK: %s / title=%s",
                actual_id, meta["properties"]["title"])
    return sh


# ---------------------------------------------------------------------------
# 安全装置 #3: 書き込み前に所有者を Drive API で確認・ログ記録
# ---------------------------------------------------------------------------

def _log_sheet_permissions(spreadsheet_id: str, creds: Any) -> str:
    """
    Drive API の permissions.list で所有者を取得しログに記録する。
    配信先シートの権限変更を事後に追跡できるようにするための監査ログ。
    権限取得に失敗しても配信は続行する（非致命的）。
    """
    try:
        from googleapiclient.discovery import build
        drive = build("drive", "v3", credentials=creds)
        resp = drive.permissions().list(
            fileId=spreadsheet_id,
            fields="permissions(id,emailAddress,role,type)",
        ).execute()
        permissions = resp.get("permissions", [])
        owners = [p["emailAddress"] for p in permissions if p.get("role") == "owner"]
        logger.info("[dist] 安全装置 #3 permissions: spreadsheet_id=%s owners=%s all_count=%d",
                    spreadsheet_id, owners, len(permissions))
        return f"owners={owners}"
    except Exception as exc:  # noqa: BLE001
        logger.warning("[dist] 安全装置 #3 permissions.list 失敗（配信は続行）: %s", exc)
        return "permissions_check_failed"


# ---------------------------------------------------------------------------
# 安全装置 #1 前段: スプレッドシートアクセス確認（読み取りのみ・書き込みなし）
# ---------------------------------------------------------------------------

async def verify_spreadsheet_access(spreadsheet_id: str) -> dict:
    """
    登録前にスプレッドシートへのアクセスを確認する（読み取りのみ）。
    - SA クライアントを構築し spreadsheetId の存在・ID 一致を検証する。
    - 成功: {"accessible": True, "title": "<シートタイトル>"}
    - 失敗: {"accessible": False, "error": "<エラーメッセージ>"}
    """
    try:
        loop = asyncio.get_event_loop()
        gc = await loop.run_in_executor(None, _build_gspread_client)
        sh = await loop.run_in_executor(None, _verify_spreadsheet_id, gc, spreadsheet_id)
        title = sh.title
        return {"accessible": True, "title": title}
    except Exception as exc:  # noqa: BLE001
        return {"accessible": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# E. 設定ロード
# ---------------------------------------------------------------------------

async def load_distribution_settings(db: AsyncSession) -> dict[str, str]:
    """tcg_distribution_settings から全設定を取得する。"""
    result = await db.execute(
        text(f"SELECT key, value FROM {TCG_SCHEMA}.tcg_distribution_settings")
    )
    return {row.key: row.value for row in result.mappings()}


# ---------------------------------------------------------------------------
# E. 出力データ取得クエリ（10列・確定フィルター）
# ---------------------------------------------------------------------------

MAX_AGE_UNSET_MESSAGE = "max_age_hours 未設定のため配信しない"


class MaxAgeHoursUnsetError(Exception):
    """tcg_distribution_settings の max_age_hours が無い・不正な時に送出する。"""


def _max_age_hours(settings: dict[str, str]) -> int | None:
    """設定表から max_age_hours を読む（唯一の読み口）。

    値が無い・整数でない・負の時は None（= 配信しない）。0 は「無制限」（設定画面の説明どおり）。
    """
    raw = settings.get("max_age_hours")
    if raw is None:
        return None
    try:
        value = int(str(raw).strip())
    except ValueError:
        return None
    return value if value >= 0 else None


# 在庫表の「24時間以内」トグルが使う窓（時間）。GAS の FRESH_WINDOW_HOURS と同じ値。
FRESH_WINDOW_HOURS = 24


def _age_window(max_age_hours: int | None) -> tuple[str, dict]:
    """「LINE 投稿が max_age_hours 時間以内」の SQL 断片と bind を返す（唯一の定義）。

    0 / None は絞らない（空文字・空 dict）。配信可否の判断は呼び出し側で _max_age_hours を使う。
    """
    if not max_age_hours:
        return "", {}
    return (
        "\n          AND sm.line_posted_at >= NOW() - make_interval(hours => :max_age_hours)",
        {"max_age_hours": max_age_hours},
    )


def _condition_filter(include_flag_single: bool) -> str:
    """配信する状態の条件（唯一の定義）。FLAG_ 系は除外し、include_flag_single のとき FLAG_SINGLE だけ通す。

    effect='EXCLUDE'（Error 等・配信しない状態）は include_flag_single に関わらず常に除外する。
    """
    if include_flag_single:
        base = "(cr.canonical NOT LIKE 'FLAG_%' OR cr.canonical = 'FLAG_SINGLE')"
    else:
        base = "cr.canonical NOT LIKE 'FLAG_%'"
    return f"{base} AND cr.effect IS DISTINCT FROM 'EXCLUDE'"


def _sold_out_filter() -> str:
    """Sold out の行を配信行から除く条件（唯一の定義）。

    ar.（analysis_results）の別名を前提にしている。status は前後の空白と大文字小文字を無視し、
    'sold out' / 'soldout' を除く（GAS の isSoldOut と同じ判定）。
    """
    return "lower(btrim(COALESCE(ar.status, ''))) NOT IN ('sold out', 'soldout')"


# 配信行の出力列（GAS の14列 → 在庫表が使う列の順）。distribution_rows_sql の最終 SELECT と同じ並び。
_GAS_COLUMNS = (
    "posted_at", "mark", "japanese_title", "english_title", "condition", "unit_price", "quantity",
    "note_ja", "status", "release_date", "series", "provider", "search_keywords", "ship_ja",
)


def bundle_title_sql() -> tuple[str, str]:
    """配信の商品名の2欄（日本語, 英語）の SQL の式。まとめ売りの表示の作り方はここだけに置く（ADR-1027）。

    bundle_size が NULL なら今までと同じ商品名。あれば「商品名 + 空白 + N + 単位の呼び名 + セット」（英語は「name N unit Set」）。
    単位の呼び名は public.line_units の name_ja・name_en（NULL のときは canonical）。「セット」「Set」はこの関数の中だけに書く。
    ar（analysis_results）・p（products）・lu（line_units）の別名を前提にする。
    """
    japanese = (
        "CASE WHEN ar.bundle_size IS NULL THEN COALESCE(p.name, '') "
        "ELSE COALESCE(p.name, '') || ' ' || ar.bundle_size::text || COALESCE(lu.name_ja, lu.canonical, ar.unit_canonical, '') || 'セット' END"
    )
    english = (
        "CASE WHEN ar.bundle_size IS NULL THEN COALESCE(p.name_en, '') "
        "ELSE COALESCE(p.name_en, '') || ' ' || ar.bundle_size::text || ' ' || COALESCE(lu.name_en, lu.canonical, ar.unit_canonical, '') || ' Set' END"
    )
    return japanese, english


# 区分（offer_type）と LINE 解析の status の対応。1つの定数で持ち、絞り込みは逆引きに使う。
OFFER_TYPE_TO_STATUS: dict[str, str] = {"in_stock": "In Stock", "pre_order": "Pre-order"}
_STATUS_TO_OFFER_TYPE = {status_value: offer for offer, status_value in OFFER_TYPE_TO_STATUS.items()}


def status_to_offer_type(status_value: str | None) -> str | None:
    """LINE 解析の status を区分に写す。対応に無い status は None。"""
    return _STATUS_TO_OFFER_TYPE.get(status_value or "")


def _distribution_final_select(source: str, *, price: str, qty: str, merged_count: str, sort_ord: str, item_keys: str) -> str:
    """最終 SELECT。GAS 14列は今までと同じ式・同じ書式。price/qty は集約後の列名を受ける。"""
    return f"""SELECT
            posted_at, mark, japanese_title, english_title, condition,
            COALESCE(ROUND({price})::bigint::text, '')  AS unit_price,
            COALESCE(ROUND({qty})::bigint::text, '') AS quantity,
            note_ja, status, release_date, series, provider, search_keywords, ship_ja,
            posted_ts, row_key, product_id, supplier_id, unit_canonical,
            {price} AS price_num, {qty} AS qty_num, {merged_count} AS merged_count, {sort_ord} AS sort_ord,
            {item_keys} AS extraction_item_ids
        FROM {source}"""


def distribution_final_select_plain() -> str:
    """まとめなし（merge_same_post=False）の最終 SELECT。在庫表の絞り込み候補（facets）が使う。"""
    return _distribution_final_select("dist_base", price="price_num", qty="qty_num", merged_count="1", sort_ord="sort_ord", item_keys="ARRAY[item_key]")


def distribution_rows_parts(
    *, include_flag_single: bool, age_condition: str, merge_same_post: bool,
) -> tuple[str, str]:
    """distribution_rows_sql を (head, final_select) に分けて返す。

    head は WITH 句（dist_base。merge_same_post=True なら dist_merged まで）、final_select は最終 SELECT。
    distribution_rows_sql は f"{head}\n        {final_select}" で組み立てる。在庫表は head を共有して1文にまとめる。
    配信行の定義（列・WHERE・まとめ条件）はこの関数だけに置く。
    """
    cond_filter = _condition_filter(include_flag_single)
    sold_out_filter = _sold_out_filter()
    title_ja, title_en = bundle_title_sql()
    base = f"""{source_cte(schema=TCG_SCHEMA, include_inactive=True, latest_stock=False)},
    dist_base AS (
        SELECT
            COALESCE(TO_CHAR(sm.line_posted_at AT TIME ZONE 'Asia/Tokyo',
                             'YYYY-MM-DD HH24:MI:SS'), '')          AS posted_at,
            sm.line_posted_at                                       AS posted_ts,
            COALESCE(p.mark, '')                                    AS mark,
            {title_ja}                                    AS japanese_title,
            {title_en}                                 AS english_title,
            cr.canonical                                            AS condition,
            ar.price_normalized                                     AS price_num,
            ar.quantity_normalized                                  AS qty_num,
            COALESCE(ar.note_ja, '')                                AS note_ja,
            COALESCE(ar.status, '')                                 AS status,
            COALESCE(p.release_date::text, '')                      AS release_date,
            COALESCE(ser.name_ja, '')                               AS series,
            COALESCE(ps.name, '')                                   AS provider,
            COALESCE((
                SELECT string_agg(psk.keyword, ' | ' ORDER BY psk.position, psk.id)
                FROM public.product_search_keywords psk
                WHERE psk.product_id = p.id
            ), '')                                                  AS search_keywords,
            COALESCE(ar.ship_ja, '')                                AS ship_ja,
            ar.id::text                                             AS row_key,
            ei.id::text                                             AS item_key,
            ar.product_id                                           AS product_id,
            sc.supplier_id                                          AS supplier_id,
            COALESCE(ar.unit_canonical, '')                         AS unit_canonical,
            cr.basis                                                AS basis,
            concat_ws(chr(31), ej.id::text, ar.product_id::text, COALESCE(cr.condition_id, ''),
                      COALESCE(ar.unit_canonical, ''), COALESCE(ar.note_ja, ''),
                      COALESCE(ar.ship_ja, ''), COALESCE(ar.status, ''), COALESCE(ar.bundle_size::text, '')) AS gkey,
            ROW_NUMBER() OVER (ORDER BY {result_order_sql()})       AS sort_ord
        FROM {TCG_SCHEMA}.analysis_results ar
        JOIN {TCG_SCHEMA}.extraction_items ei
            ON ei.id = ar.extraction_item_id
        JOIN {TCG_SCHEMA}.extraction_jobs ej
            ON ej.id = ei.extraction_job_id
        JOIN {TCG_SCHEMA}.source_messages sm
            ON sm.id = ej.source_message_id
        JOIN {TCG_SCHEMA}.supplier_channels sc
            ON sc.id = sm.supplier_channel_id
        LEFT JOIN public.suppliers ps
            ON ps.id = sc.supplier_id
        LEFT JOIN public.products p
            ON p.id = ar.product_id
        LEFT JOIN public.line_units lu
            ON lu.id = ar.unit_id
        LEFT JOIN public.type_master ser
            ON ser.id = p.work_id
        {review_joins(schema=TCG_SCHEMA, fenced=True, shime=False)}
        WHERE ar.pid_resolved = TRUE
          AND ar.is_current = TRUE
          AND cr.needs_review IS FALSE
          AND ar.exclusion IS DISTINCT FROM 'excluded'
          AND ar.unit_resolved = TRUE
          AND ar.price_normalized IS NOT NULL
          AND sm.line_posted_at IS NOT NULL
          AND {cond_filter}
          AND {sold_out_filter}{age_condition}
    )"""
    if not merge_same_post:
        return base, distribution_final_select_plain()
    head = f"""{base},
    dist_groups AS (
        SELECT gkey,
               (COUNT(*) >= 2
                AND COUNT(DISTINCT basis) = COUNT(*)
                AND COUNT(*) FILTER (WHERE basis IS NULL) = 0
                AND COUNT(*) FILTER (WHERE qty_num IS NULL) = 0) AS can_merge
        FROM dist_base
        GROUP BY gkey
    ),
    dist_keyed AS (
        SELECT b.*, CASE WHEN g.can_merge THEN b.gkey ELSE b.row_key END AS ekey
        FROM dist_base b
        JOIN dist_groups g ON g.gkey = b.gkey
    ),
    dist_agg AS (
        SELECT k.*,
               ROW_NUMBER() OVER (PARTITION BY ekey ORDER BY sort_ord) AS rn,
               SUM(qty_num)   OVER (PARTITION BY ekey) AS qty_agg,
               MAX(price_num) OVER (PARTITION BY ekey) AS price_agg,
               COUNT(*)       OVER (PARTITION BY ekey) AS group_n,
               MIN(sort_ord)  OVER (PARTITION BY ekey) AS sort_min,
               array_agg(item_key) OVER (PARTITION BY ekey ORDER BY sort_ord
                   ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS item_keys_agg
        FROM dist_keyed k
    ),
    dist_merged AS (SELECT * FROM dist_agg WHERE rn = 1)"""
    final = _distribution_final_select("dist_merged", price="price_agg", qty="qty_agg", merged_count="group_n", sort_ord="sort_min", item_keys="item_keys_agg")
    return head, final


def distribution_rows_sql(*, include_flag_single: bool, age_condition: str, merge_same_post: bool) -> str:
    """配信行を作る SQL（配信行の定義はここ1か所だけ。GAS 出力とアプリの在庫表が使う。配信プレビューの件数は変更前の問い合わせを残しており（products を結合しない）、状態の条件だけ _condition_filter を共有する）。

    出す列: GAS の14列（_GAS_COLUMNS）+ posted_ts, row_key, product_id, supplier_id,
    unit_canonical, price_num, qty_num, merged_count, sort_ord。並びは sort_ord（result_order_sql の通し番号）。
    merge_same_post=True のとき、同じ投稿・同じ商品・同じ状態・同じ形態・同じ備考・同じ発送・同じ status の行で、
    根拠（cr.basis）がすべて違い、根拠と数量に NULL が無い組だけを1行にまとめる（数量は合計・単価は最大）。
    状態の鍵と判定は cr の列（表示と同じ値）を使う。ランクを表す語はコードに書かない。
    age_condition は _age_window が返す信頼できる SQL 断片（bind は呼び出し側が渡す）。
    """
    head, final = distribution_rows_parts(
        include_flag_single=include_flag_single, age_condition=age_condition, merge_same_post=merge_same_post,
    )
    return f"{head}\n        {final}"


async def fetch_output_rows(
    db: AsyncSession,
    *,
    include_flag_single: bool = False,
    max_age_hours: int | None = None,
) -> list[list[str]]:
    """
    配信対象行を14列（DIST_HEADERS）で取得する。行の定義は distribution_rows_sql（まとめなし）。

    注意: 現在の全レコードは engine_version='compat-v1'（GAS計算値）。
    正規化ルール（NR0001〜NR0136）は新エンジン再解析まで未適用。
    再解析後は価格 NULL が減り配信件数が変動する。
    """
    # line_posted_at IS NOT NULL は常時適用（PO決定: NULL行は配信対象外）
    age_condition, bind_params = _age_window(max_age_hours)
    inner = distribution_rows_sql(
        include_flag_single=include_flag_single, age_condition=age_condition, merge_same_post=False,
    )
    sql = text(f"SELECT * FROM ({inner}) dist ORDER BY sort_ord")

    result = await db.execute(sql, bind_params)
    rows = result.mappings().all()
    return [[row[column] for column in _GAS_COLUMNS] for row in rows]


# ---------------------------------------------------------------------------
# E. プレビューデータ取得（件数・除外内訳・精度ゲート状態）
# ---------------------------------------------------------------------------

async def fetch_preview_data(db: AsyncSession) -> dict:
    """
    配信プレビュー用のデータを返す（書き込みなし）。
    設定をロードし、配信候補件数・除外内訳・精度ゲート状態を取得する。
    """
    settings = await load_distribution_settings(db)
    include_flag_single = settings.get("include_flag_single", "false").lower() == "true"
    max_age_hours = _max_age_hours(settings)
    if max_age_hours is None:
        logger.error("[dist] %s", MAX_AGE_UNSET_MESSAGE)
        raise MaxAgeHoursUnsetError(MAX_AGE_UNSET_MESSAGE)

    # 配信候補件数（変更前と同じ問い合わせ。products を結合しない。行の絞り込み条件は _condition_filter と共通）
    # line_posted_at IS NOT NULL は常時適用（PO決定: NULL行は配信対象外）
    cond_filter = _condition_filter(include_flag_single)
    sold_out_filter = _sold_out_filter()
    age_condition, age_bind_params = _age_window(max_age_hours)

    count_result = await db.execute(text(f"""{source_cte(schema=TCG_SCHEMA, include_inactive=True, latest_stock=False)}
        SELECT COUNT(*) AS cnt
        FROM {TCG_SCHEMA}.analysis_results ar
        JOIN {TCG_SCHEMA}.extraction_items ei ON ei.id=ar.extraction_item_id
        JOIN {TCG_SCHEMA}.extraction_jobs ej ON ej.id=ei.extraction_job_id
        JOIN {TCG_SCHEMA}.source_messages sm ON sm.id=ej.source_message_id
        JOIN {TCG_SCHEMA}.supplier_channels sc ON sc.id=sm.supplier_channel_id
        {review_joins(schema=TCG_SCHEMA, shime=False)}
        WHERE ar.pid_resolved = TRUE
          AND ar.is_current = TRUE
          AND cr.needs_review IS FALSE
          AND ar.exclusion IS DISTINCT FROM 'excluded'
          AND ar.unit_resolved = TRUE
          AND ar.price_normalized IS NOT NULL
          AND sm.line_posted_at IS NOT NULL
          AND {cond_filter}
          AND {sold_out_filter}{age_condition}
    """), age_bind_params)
    output_count = count_result.scalar()

    # 除外内訳
    excl_result = await db.execute(text(f"""{source_cte(schema=TCG_SCHEMA, include_inactive=True, latest_stock=False)}
        SELECT
            COUNT(*) FILTER (WHERE cr.canonical LIKE 'FLAG_%' OR cr.effect = 'EXCLUDE')
                AS exc_flag,
            COUNT(*) FILTER (
                WHERE cr.canonical NOT LIKE 'FLAG_%' AND cr.effect IS DISTINCT FROM 'EXCLUDE'
                  AND ar.pid_resolved = FALSE
                  AND ar.unit_resolved = TRUE)
                AS exc_pid_only,
            COUNT(*) FILTER (
                WHERE cr.canonical NOT LIKE 'FLAG_%' AND cr.effect IS DISTINCT FROM 'EXCLUDE'
                  AND ar.pid_resolved = TRUE
                  AND ar.unit_resolved = FALSE)
                AS exc_unit_only,
            COUNT(*) FILTER (
                WHERE cr.canonical NOT LIKE 'FLAG_%' AND cr.effect IS DISTINCT FROM 'EXCLUDE'
                  AND ar.pid_resolved = FALSE
                  AND ar.unit_resolved = FALSE)
                AS exc_both,
            COUNT(*) FILTER (
                WHERE ar.pid_resolved = TRUE
                  AND ar.unit_resolved = TRUE
                  AND cr.canonical NOT LIKE 'FLAG_%' AND cr.effect IS DISTINCT FROM 'EXCLUDE'
                  AND ar.price_normalized IS NULL)
                AS exc_price
        FROM {TCG_SCHEMA}.analysis_results ar
        JOIN {TCG_SCHEMA}.extraction_items ei ON ei.id=ar.extraction_item_id
        JOIN {TCG_SCHEMA}.extraction_jobs ej ON ej.id=ei.extraction_job_id
        JOIN {TCG_SCHEMA}.source_messages sm ON sm.id=ej.source_message_id
        JOIN {TCG_SCHEMA}.supplier_channels sc ON sc.id=sm.supplier_channel_id
        {review_joins(schema=TCG_SCHEMA, shime=False)}
        WHERE ar.is_current = TRUE{age_condition}
    """), age_bind_params)
    excl = excl_result.mappings().one()

    # 精度ゲート: item_corrections との JOIN（テーブル存在チェック付き）
    gate_status = await _fetch_flag_gate_status(db, settings)

    return {
        "output_count": output_count,
        "note": "GASエンジン値。新エンジン再解析後に変動します。",
        "exclusion": {
            "flag_series": excl["exc_flag"],
            "pid_unresolved_only": excl["exc_pid_only"],
            "unit_unresolved_only": excl["exc_unit_only"],
            "both_unresolved": excl["exc_both"],
            "price_unresolved": excl["exc_price"],
        },
        "flag_gate": gate_status,
        "settings": settings,
    }


async def _fetch_flag_gate_status(db: AsyncSession, settings: dict) -> dict:
    """FLAG_SINGLE 精度ゲートの現在状態を返す。"""
    include_flag_single = settings.get("include_flag_single", "false").lower() == "true"
    min_samples = int(settings.get("flag_gate_min_samples", "50"))
    max_rate_pct = float(settings.get("flag_gate_max_correction_rate_pct", "5"))

    # item_corrections テーブルの存在確認
    tbl_check = await db.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = 'item_corrections'
        ) AS exists
    """), {"schema": TCG_SCHEMA})
    has_corrections = tbl_check.scalar()

    if not has_corrections:
        return {
            "include_flag_single": include_flag_single,
            "flag_single_count": None,
            "recent_samples": 0,
            "correction_rate_pct": None,
            "gate_status": "no_correction_table",
            "gate_message": "item_corrections テーブル未作成（Session 1 待ち）",
        }

    # 直近30日の FLAG_SINGLE 行と修正件数
    gate_result = await db.execute(text(f"""
        SELECT
            COUNT(*) AS total_flag,
            COUNT(ic.id) AS corrected_count
        FROM {TCG_SCHEMA}.analysis_results ar
        LEFT JOIN {TCG_SCHEMA}.item_corrections ic
            ON ic.extraction_item_id = ar.extraction_item_id
            AND ic.corrected_at >= NOW() - INTERVAL '30 days'
        WHERE ar.condition_canonical = 'FLAG_SINGLE'
          AND ar.computed_at >= NOW() - INTERVAL '30 days'
    """))
    gate = gate_result.mappings().one()
    total = gate["total_flag"] or 0
    corrected = gate["corrected_count"] or 0
    rate = round(corrected / total * 100, 1) if total > 0 else None

    if total < min_samples:
        status = "insufficient_samples"
        message = f"直近サンプル不足（{total} / {min_samples}件以上必要）"
    elif rate is not None and rate <= max_rate_pct:
        status = "threshold_met"
        message = f"閾値達成（修正率 {rate}% ≤ {max_rate_pct}%）"
    else:
        status = "threshold_not_met"
        message = f"修正率 {rate}% > 閾値 {max_rate_pct}%"

    return {
        "include_flag_single": include_flag_single,
        "flag_single_count": total,
        "recent_samples": total,
        "correction_rate_pct": rate,
        "gate_status": status,
        "gate_message": message,
    }


# ---------------------------------------------------------------------------
# F. 配信処理コア（安全装置 #1〜#5・同期実行・thread executor 経由で呼ぶ）
# ---------------------------------------------------------------------------

def _write_tab_sync(
    gc: Any,
    creds: Any,
    target: dict,
    tab_name: str,
    headers: list[str],
    rows: list[list[str]],
) -> dict:
    """
    指定タブへ「見出し + データ」を全置換で書く共通の関数（同期）。
    安全装置 #1〜#5 はここだけに置く（配信タブと要確認タブで共有）。
    asyncio.get_event_loop().run_in_executor() 経由で呼ぶこと。

    Returns:
        {"status": "ok", "rows_written": N} または
        {"status": "error", "error": "message"}
    """
    import gspread

    spreadsheet_id = target["spreadsheet_id"]
    sheet_name = tab_name

    try:
        # 安全装置 #1/#2: spreadsheetId 検証（存在しなければ RuntimeError）
        sh = _verify_spreadsheet_id(gc, spreadsheet_id)

        # 安全装置 #3: 所有者確認・ログ記録
        _log_sheet_permissions(spreadsheet_id, creds)

        # 安全装置 #2: シート自動作成禁止
        try:
            worksheet = sh.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            raise RuntimeError(
                f"[安全装置 #2] シート '{sheet_name}' が見つかりません。"
                " シートの自動作成は行いません。"
                " スプレッドシートにタブが存在するか確認してください。"
            )

        # 安全装置 #4: タブ名の DB 登録値との完全一致検証
        actual_title = worksheet.title
        if actual_title != sheet_name:
            raise RuntimeError(
                f"[安全装置 #4] タブ名不一致: 期待={sheet_name!r} 実際={actual_title!r}"
            )

        # 安全装置 #5: 行数上限チェック
        total_rows = len(rows)
        if total_rows > DIST_ROW_LIMIT:
            raise RuntimeError(
                f"[安全装置 #5] 配信行数 {total_rows} が上限 {DIST_ROW_LIMIT} を超えています。"
                " 配信を中止します。"
            )

        # 全置換: clear → ヘッダー + データ書き込み
        worksheet.clear()
        all_rows = [headers] + rows
        worksheet.append_rows(all_rows, value_input_option="RAW")

        rows_written = len(rows)
        logger.info(
            "[dist] 書き込み完了: target=%s tab=%s rows=%d", target["name"], sheet_name, rows_written
        )
        return {"status": "ok", "rows_written": rows_written}

    except Exception as exc:
        error_msg = str(exc)
        logger.error(
            "[dist] 書き込みエラー: target=%s tab=%s error=%s", target["name"], sheet_name, error_msg
        )
        return {"status": "error", "error": error_msg}


def _write_to_target_sync(
    gc: Any,
    creds: Any,
    target: dict,
    rows: list[list[str]],
) -> dict:
    """単一配信先の在庫集計タブ（target["sheet_name"]）への書き込み。動きは共通の _write_tab_sync と同じ。"""
    return _write_tab_sync(gc, creds, target, target["sheet_name"], DIST_HEADERS, rows)


# ---------------------------------------------------------------------------
# 配信先 CRUD
# ---------------------------------------------------------------------------

async def list_targets(db: AsyncSession) -> list[dict]:
    result = await db.execute(text(f"""
        SELECT id, name, spreadsheet_id, sheet_name, review_sheet_name, is_active,
               sa_key_secret_name, last_distributed_at, last_distributed_count,
               last_result, created_at, updated_at
        FROM {TCG_SCHEMA}.tcg_distribution_targets
        ORDER BY name
    """))
    return [dict(row) for row in result.mappings()]


async def get_target(db: AsyncSession, target_id: str) -> dict | None:
    result = await db.execute(
        text(f"""
            SELECT id, name, spreadsheet_id, sheet_name, review_sheet_name, is_active,
                   sa_key_secret_name, last_distributed_at, last_distributed_count,
                   last_result, created_at, updated_at
            FROM {TCG_SCHEMA}.tcg_distribution_targets
            WHERE id = :id
        """),
        {"id": target_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def create_target(db: AsyncSession, data: dict) -> dict:
    result = await db.execute(
        text(f"""
            INSERT INTO {TCG_SCHEMA}.tcg_distribution_targets
                (name, spreadsheet_id, sheet_name, is_active, sa_key_secret_name)
            VALUES
                (:name, :spreadsheet_id, :sheet_name, :is_active, :sa_key_secret_name)
            RETURNING id, name, spreadsheet_id, sheet_name, is_active,
                      sa_key_secret_name, last_distributed_at, last_distributed_count,
                      last_result, created_at, updated_at
        """),
        {
            "name": data["name"],
            "spreadsheet_id": data["spreadsheet_id"],
            "sheet_name": data["sheet_name"],
            "is_active": data.get("is_active", True),
            "sa_key_secret_name": data.get("sa_key_secret_name", "TCG_SHEETS_SA_KEY_FILE"),
        },
    )
    await db.commit()
    row = result.mappings().first()
    return dict(row)


async def update_target(db: AsyncSession, target_id: str, data: dict) -> dict | None:
    # 更新可能フィールドのみ
    allowed = {"name", "spreadsheet_id", "sheet_name", "is_active", "sa_key_secret_name"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return await get_target(db, target_id)

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = target_id
    updates["updated_at"] = datetime.now(timezone.utc)

    result = await db.execute(
        text(f"""
            UPDATE {TCG_SCHEMA}.tcg_distribution_targets
            SET {set_clause}, updated_at = :updated_at
            WHERE id = :id
            RETURNING id, name, spreadsheet_id, sheet_name, is_active,
                      sa_key_secret_name, last_distributed_at, last_distributed_count,
                      last_result, created_at, updated_at
        """),
        updates,
    )
    await db.commit()
    row = result.mappings().first()
    return dict(row) if row else None


async def soft_delete_target(db: AsyncSession, target_id: str) -> bool:
    result = await db.execute(
        text(f"""
            UPDATE {TCG_SCHEMA}.tcg_distribution_targets
            SET is_active = FALSE, updated_at = NOW()
            WHERE id = :id
            RETURNING id
        """),
        {"id": target_id},
    )
    await db.commit()
    return result.first() is not None


# ---------------------------------------------------------------------------
# 設定管理
# ---------------------------------------------------------------------------

async def list_settings(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        text(f"SELECT key, value, note, updated_at FROM {TCG_SCHEMA}.tcg_distribution_settings ORDER BY key")
    )
    return [dict(row) for row in result.mappings()]


async def update_setting(db: AsyncSession, key: str, value: str) -> dict | None:
    result = await db.execute(
        text(f"""
            UPDATE {TCG_SCHEMA}.tcg_distribution_settings
            SET value = :value, updated_at = NOW()
            WHERE key = :key
            RETURNING key, value, note, updated_at
        """),
        {"key": key, "value": value},
    )
    await db.commit()
    row = result.mappings().first()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# 安全装置 #7: 配信履歴の DB 記録
# ---------------------------------------------------------------------------

async def _record_distribution_result(
    db: AsyncSession,
    target_id: str,
    result_status: str,
    rows_written: int | None,
) -> None:
    last_result = result_status if result_status == "ok" else f"error: {result_status}"
    await db.execute(
        text(f"""
            UPDATE {TCG_SCHEMA}.tcg_distribution_targets
            SET last_distributed_at    = NOW(),
                last_distributed_count = :count,
                last_result            = :result,
                updated_at             = NOW()
            WHERE id = :id
        """),
        {"id": target_id, "count": rows_written, "result": last_result},
    )
    await db.commit()


# ---------------------------------------------------------------------------
# H. メイン配信ランナー
# ---------------------------------------------------------------------------

async def _export_review_tab(
    db: AsyncSession,
    gc: Any,
    creds: Any,
    target: dict,
    review_cache: dict,
) -> dict | None:
    """review_sheet_name がある配信先の要確認タブを書く。失敗は握りつぶさず、エラーの辞書を返す（配信の結果は変えない）。

    要確認の一覧は1回の配信で1回だけ取る（review_cache に残す）。成功なら None。
    """
    # 循環 import を避けるため、使う時に読む（tcg_review_sheet_svc は本モジュールの _write_tab_sync を使う）
    from app.services.tcg_review_sheet_svc import collect_review_rows, write_review_sheet_sync

    name = target["name"]
    try:
        if "rows" not in review_cache:
            review_cache["rows"] = await collect_review_rows(db)
        result = await asyncio.get_event_loop().run_in_executor(
            None, write_review_sheet_sync, gc, creds, target, review_cache["rows"]
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("[dist] 要確認タブの書き込み失敗（配信の結果は変えない）: target=%s error=%s", name, exc)
        await db.rollback()  # 取得で DB が失敗していても、次の配信先の履歴の記録を巻き込まない
        return {"target_id": str(target["id"]), "target_name": f"{name}（要確認タブ）", "error": str(exc)}
    if result["status"] != "ok":
        logger.error(
            "[dist] 要確認タブの書き込み失敗（配信の結果は変えない）: target=%s error=%s", name, result["error"]
        )
        return {"target_id": str(target["id"]), "target_name": f"{name}（要確認タブ）", "error": result["error"]}
    return None


@dataclass(frozen=True)
class DistributionRowsResult:
    """build_distribution_rows の結果。kind: ok＝rows あり／hold＝再解析・抽出が未完了／unset＝max_age_hours 未設定／error＝取得失敗。"""

    kind: Literal["ok", "hold", "unset", "error"]
    rows: list
    message: str


async def build_distribution_rows(db: AsyncSession) -> DistributionRowsResult:
    """配信行を作る手順 0（#8）・0-b（#8b）・1（設定）・2（出力データ取得）。ログは出さない（呼び出し側が決める）。

    analysis_runs・extraction_jobs・load_distribution_settings の例外は捕まえない。
    fetch_output_rows の例外だけ kind="error" にして返す。
    """
    # 0. 再解析完了チェック（安全装置 #8）
    # analysis_runs に completed_at IS NULL の行があれば配信を中止する。
    # 再解析中に配信すると、unit_resolved が未確定の行が含まれる可能性がある。
    pending_rows = (
        await db.execute(
            text(
                f"SELECT id, started_at FROM {TCG_SCHEMA}.analysis_runs"
                " WHERE completed_at IS NULL ORDER BY started_at LIMIT 10"
            )
        )
    ).mappings().all()
    if pending_rows:
        details = [
            {"run_id": str(r["id"]), "started_at": r["started_at"].isoformat()}
            for r in pending_rows
        ]
        msg = (
            f"安全装置 #8: 再解析未完了の runs が {len(pending_rows)} 件あります。"
            f" 完了を待ってから配信を実行してください。未完了: {details}"
        )
        return DistributionRowsResult(kind="hold", rows=[], message=msg)

    # 0-b. 抽出・解析の未完了チェック（安全装置 #8b）
    # extraction_jobs に未完了のジョブが残っている間は配信しない。
    # 終端扱い: done / empty / error（これらは待っても変わらないため止めない）。
    unfinished = (
        await db.execute(
            text(
                f"SELECT status, count(*) AS cnt FROM {TCG_SCHEMA}.extraction_jobs"
                " WHERE status IN ('pending', 'running', 'extracted')"
                " GROUP BY status ORDER BY status"
            )
        )
    ).mappings().all()
    if unfinished:
        breakdown = {r["status"]: r["cnt"] for r in unfinished}
        total_unfinished = sum(breakdown.values())
        msg = (
            f"安全装置 #8b: 未完了の extraction_jobs が {total_unfinished} 件あります。"
            f" 完了を待ってから配信を実行してください。内訳: {breakdown}"
        )
        return DistributionRowsResult(kind="hold", rows=[], message=msg)

    # 1. 設定ロード
    settings = await load_distribution_settings(db)
    include_flag_single = settings.get("include_flag_single", "false").lower() == "true"
    max_age_hours = _max_age_hours(settings)
    if max_age_hours is None:
        return DistributionRowsResult(kind="unset", rows=[], message=MAX_AGE_UNSET_MESSAGE)

    # 2. 出力データ取得
    try:
        rows = await fetch_output_rows(db, include_flag_single=include_flag_single, max_age_hours=max_age_hours)
    except Exception as exc:
        return DistributionRowsResult(kind="error", rows=[], message=f"出力データ取得失敗: {exc}")
    return DistributionRowsResult(kind="ok", rows=rows, message="")


async def run_distribution(
    db: AsyncSession,
    target_id: str | None = None,
) -> dict:
    """
    全アクティブ配信先（または特定 target_id）へ配信を実行する。

    手順:
      0. 再解析完了チェック（安全装置 #8）
      1. 設定ロード
      2. 出力データ取得（確定フィルター）
      3. 配信先取得
      4. 各配信先へ thread executor で書き込み（安全装置 #1〜#5）
      5. 結果を DB に記録（安全装置 #7）
      6. 失敗があれば Discord 通知（安全装置 #6）
    """
    started_at = datetime.now(timezone.utc)

    result = await build_distribution_rows(db)
    if result.kind != "ok":
        if result.kind == "hold":
            logger.warning("[dist] %s", result.message)
        else:  # unset・error
            logger.error("[dist] %s", result.message)
        return {
            "run_id": None,
            "started_at": started_at.isoformat(),
            "output_count": 0,
            "results": [],
            "errors": [{"target_id": None, "error": result.message}],
        }
    rows = result.rows

    output_count = len(rows)

    # 3. 配信先取得
    if target_id:
        target = await get_target(db, target_id)
        targets = [target] if target and target["is_active"] else []
    else:
        all_targets = await list_targets(db)
        targets = [t for t in all_targets if t["is_active"]]

    if not targets:
        return {
            "run_id": None,
            "started_at": started_at.isoformat(),
            "output_count": output_count,
            "results": [],
            "errors": [{"target_id": target_id, "error": "アクティブな配信先が見つかりません"}],
        }

    # SA クライアントを1回構築して全ターゲットで共有
    try:
        from google.oauth2.service_account import Credentials
        key_file = os.getenv("TCG_SHEETS_SA_KEY_FILE", "").strip()
        if not key_file:
            raise RuntimeError("TCG_SHEETS_SA_KEY_FILE が未設定です")
        loop = asyncio.get_event_loop()
        creds = await loop.run_in_executor(
            None, lambda: Credentials.from_service_account_file(key_file, scopes=_SCOPES)
        )
        gc = await loop.run_in_executor(None, _build_gspread_client)
    except Exception as exc:
        logger.error("[dist] SA クライアント生成エラー: %s", exc)
        return {
            "run_id": None,
            "started_at": started_at.isoformat(),
            "output_count": output_count,
            "results": [],
            "errors": [{"target_id": None, "error": f"SA 認証失敗: {exc}"}],
        }

    # 4. 各配信先へ書き込み（thread executor・リトライあり）
    # リトライ設定: 最大4回・指数バックオフ 1→2→4→8 秒（設計 §14.1.4 C96）
    _RETRY_MAX = 4
    _RETRY_DELAYS = [1, 2, 4, 8]

    loop = asyncio.get_event_loop()
    results = []
    errors = []
    review_errors: list[dict] = []  # 要確認タブの失敗（通知にだけ載せる。返り値の results / errors は変えない）
    review_cache: dict = {}

    for target in targets:
        write_result: dict | None = None
        last_error: str = ""
        for attempt in range(_RETRY_MAX):
            write_result = await loop.run_in_executor(
                None,
                _write_to_target_sync,
                gc,
                creds,
                target,
                rows,
            )
            if write_result["status"] == "ok":
                break
            last_error = write_result.get("error", "unknown error")
            if attempt < _RETRY_MAX - 1:
                delay = _RETRY_DELAYS[attempt]
                logger.warning(
                    "[dist] 書き込み失敗（%d/%d回目）: target=%s error=%s 次のリトライまで%d秒待機",
                    attempt + 1, _RETRY_MAX, target["name"], last_error, delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "[dist] 書き込み失敗（%d/%d回目・最終）: target=%s error=%s",
                    attempt + 1, _RETRY_MAX, target["name"], last_error,
                )

        # 5. 配信履歴を DB に記録（安全装置 #7）
        if write_result and write_result["status"] == "ok":
            await _record_distribution_result(db, target["id"], "ok", write_result["rows_written"])
            results.append({
                "target_id": str(target["id"]),
                "target_name": target["name"],
                "status": "ok",
                "rows_written": write_result["rows_written"],
            })
            if target.get("review_sheet_name"):
                review_error = await _export_review_tab(db, gc, creds, target, review_cache)
                if review_error:
                    review_errors.append(review_error)
        else:
            await _record_distribution_result(
                db, target["id"], last_error, None
            )
            errors.append({
                "target_id": str(target["id"]),
                "target_name": target["name"],
                "error": last_error,
            })

    # 6. 失敗時 Discord 通知（安全装置 #6）
    if errors or review_errors:
        await _notify_distribution_failure(db, errors + review_errors, output_count)

    return {
        "started_at": started_at.isoformat(),
        "output_count": output_count,
        "results": results,
        "errors": errors,
    }


async def _notify_distribution_failure(
    db: AsyncSession,
    errors: list[dict],
    output_count: int,
) -> None:
    """安全装置 #6: 配信失敗時に Discord 通知を送る。"""
    try:
        from app.routers.notifications import send_discord_notification

        error_lines = "\n".join(
            f"  - {e.get('target_name', e.get('target_id', '?'))}: {e['error']}"
            for e in errors
        )
        await send_discord_notification(
            db=db,
            tenant_id=4,  # tenant_004
            event_type="tcg_distribution_error",
            title="⚠️ TCG 在庫配信エラー",
            message=(
                f"配信候補 {output_count} 件の配信中にエラーが発生しました。\n\n"
                f"失敗した配信先:\n{error_lines}"
            ),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[dist] Discord 通知失敗（配信結果には影響なし）: %s", exc)
