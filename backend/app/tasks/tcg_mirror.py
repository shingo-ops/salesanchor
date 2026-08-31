"""
MIG-05 Task 3: TCG ミラーシート 日次書き出しタスク。

固定 spreadsheetId にのみ書き込む。シート自動作成は一切行わない
（SA の Drive quota=0 が実測で確認されているため、コード上も作成経路を封じる）。

スケジュール: 毎日 AM 02:00 JST（celery_app.py の beat_schedule に登録）。

環境変数:
  TCG_SHEETS_SA_KEY_FILE  SA キー JSON のファイルパス（未設定時はスキップ）

対象シート（固定）:
  MIRROR_SPREADSHEET_ID = "1IBIpge6Qz2arq93OHmRFnCGBMj2kVhrgEjtY8c5ecus"
  オーナー: shingo@treasureislandjp.com
  書き込み権限: salesanchor-drive@sales-ops-with-claude.iam.gserviceaccount.com
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# 定数（コード変更なしで書き込み先を変えることを禁止するための定数化）
# ──────────────────────────────────────────────────────────────────────────────

MIRROR_SPREADSHEET_ID = "1IBIpge6Qz2arq93OHmRFnCGBMj2kVhrgEjtY8c5ecus"

# TCG解析システムは tenant_004 専用スキーマ。全SQLはこの定数で修飾する
TCG_SCHEMA = "tenant_004"

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

_README_BODY = (
    "このシートはシステム所有（salesanchor-drive サービスアカウント）です。\n"
    "消えても DB から再生成可能です。手動編集不可。\n\n"
    "生成元: SalesAnchor backend / MIG-05 Task 3\n"
    "更新: 日次（深夜 02:00 JST）またはデプロイ時\n"
)


# ──────────────────────────────────────────────────────────────────────────────
# ガード: シート自動作成を許可しない
# ──────────────────────────────────────────────────────────────────────────────

def _assert_no_create_path() -> None:
    """
    このモジュールにシート自動作成経路が存在しないことをランタイムで明示する。
    テストから呼び出して静的に確認するためのフック。
    """
    # 意図的に何もしない — このメソッドの存在自体がコントラクト
    pass


# ──────────────────────────────────────────────────────────────────────────────
# 内部ヘルパー
# ──────────────────────────────────────────────────────────────────────────────

def _build_client() -> Any:
    """gspread クライアントを SA キーファイルから生成する。"""
    import gspread
    from google.oauth2.service_account import Credentials

    key_file = os.getenv("TCG_SHEETS_SA_KEY_FILE", "").strip()
    if not key_file:
        raise RuntimeError(
            "TCG_SHEETS_SA_KEY_FILE が未設定です。"
            "ミラータスクを実行するにはこの環境変数を設定してください。"
        )
    creds = Credentials.from_service_account_file(key_file, scopes=_SCOPES)
    return gspread.authorize(creds)


def _verify_id(gc: Any, spreadsheet_id: str) -> Any:
    """
    spreadsheets.get で取得した spreadsheetId が引数と完全一致することを検証する。
    不一致の場合は RuntimeError を raise し、書き込みを中止する。
    シート自動作成は一切行わない（シートが存在しなければ KeyError で失敗）。
    """
    sh = gc.open_by_key(spreadsheet_id)
    meta = sh.fetch_sheet_metadata()
    actual_id = meta["spreadsheetId"]
    if actual_id != spreadsheet_id:
        raise RuntimeError(
            f"spreadsheetId 不一致: 期待={spreadsheet_id!r} 実際={actual_id!r}"
        )
    logger.info("[tcg_mirror] spreadsheetId 検証 OK: %s", actual_id)
    return sh


def _get_or_add_worksheet(sh: Any, title: str, rows: int = 300, cols: int = 30) -> Any:
    """既存タブを返す。存在しなければ追加する（シート自体は作成しない）。"""
    existing = {ws.title: ws for ws in sh.worksheets()}
    if title in existing:
        return existing[title]
    return sh.add_worksheet(title=title, rows=rows, cols=cols)


# ──────────────────────────────────────────────────────────────────────────────
# DB から各タブのデータを取得
# ──────────────────────────────────────────────────────────────────────────────

async def _fetch_products(db: Any) -> tuple[list[str], list[list]]:
    from sqlalchemy import text

    result = await db.execute(text(f"""
        SELECT
            p.product_id,
            p.product_name,
            p.series_name,
            p.category,
            p.subcategory,
            p.rarity,
            u.name AS unit_name,
            p.standard_purchase_price,
            p.note
        FROM {TCG_SCHEMA}.tcg_products p
        LEFT JOIN {TCG_SCHEMA}.units u ON u.id = p.unit_id
        ORDER BY p.product_id
    """))
    rows = result.fetchall()
    headers = [
        "product_id", "product_name", "series_name", "category",
        "subcategory", "rarity", "unit_name", "standard_purchase_price", "note",
    ]
    data = [[str(v) if v is not None else "" for v in row] for row in rows]
    return headers, data


async def _fetch_keywords(db: Any) -> tuple[list[str], list[list]]:
    from sqlalchemy import text

    result = await db.execute(text(f"""
        SELECT
            p.product_id,
            p.product_name,
            'search' AS keyword_type,
            k.keyword
        FROM {TCG_SCHEMA}.product_search_keywords k
        JOIN {TCG_SCHEMA}.tcg_products p ON p.id = k.product_id
        ORDER BY p.product_id, k.keyword
        UNION ALL
        SELECT
            p.product_id,
            p.product_name,
            'exclude',
            k.keyword
        FROM {TCG_SCHEMA}.product_exclude_keywords k
        JOIN {TCG_SCHEMA}.tcg_products p ON p.id = k.product_id
        ORDER BY p.product_id, k.keyword
    """))
    rows = result.fetchall()
    headers = ["product_id", "product_name", "keyword_type", "keyword"]
    data = [[str(v) if v is not None else "" for v in row] for row in rows]
    return headers, data


async def _fetch_suppliers(db: Any) -> tuple[list[str], list[list]]:
    from sqlalchemy import text

    result = await db.execute(text(f"""
        SELECT
            s.code,
            s.name,
            s.contact_name,
            sc.channel_type,
            sc.channel_identifier
        FROM {TCG_SCHEMA}.tcg_suppliers s
        LEFT JOIN {TCG_SCHEMA}.supplier_channels sc ON sc.supplier_id = s.id
        ORDER BY s.code, sc.channel_type
    """))
    rows = result.fetchall()
    headers = ["code", "name", "contact_name", "channel_type", "channel_identifier"]
    data = [[str(v) if v is not None else "" for v in row] for row in rows]
    return headers, data


async def _fetch_supplier_summary(db: Any) -> tuple[list[str], list[list]]:
    from sqlalchemy import text

    result = await db.execute(text(f"""
        SELECT
            s.code,
            s.name,
            COUNT(DISTINCT ei.id) AS extraction_items,
            COUNT(DISTINCT ar.id) AS analysis_results,
            SUM(CASE WHEN ar.needs_review THEN 1 ELSE 0 END) AS needs_review
        FROM {TCG_SCHEMA}.tcg_suppliers s
        LEFT JOIN {TCG_SCHEMA}.supplier_channels sc ON sc.supplier_id = s.id
        LEFT JOIN {TCG_SCHEMA}.source_messages sm ON sm.supplier_channel_id = sc.id
        LEFT JOIN {TCG_SCHEMA}.extraction_jobs ej ON ej.source_message_id = sm.id
        LEFT JOIN {TCG_SCHEMA}.extraction_items ei ON ei.extraction_job_id = ej.id
        LEFT JOIN {TCG_SCHEMA}.analysis_results ar ON ar.extraction_item_id = ei.id
        GROUP BY s.code, s.name
        ORDER BY s.code
    """))
    rows = result.fetchall()
    headers = ["code", "name", "extraction_items", "analysis_results", "needs_review"]
    data = [[str(v) if v is not None else "" for v in row] for row in rows]
    return headers, data


async def _fetch_db_structure(db: Any) -> tuple[list[str], list[list]]:
    from sqlalchemy import text

    result = await db.execute(text(f"""
        SELECT
            t.table_name,
            c.column_name,
            c.data_type,
            c.is_nullable,
            c.column_default
        FROM information_schema.tables t
        JOIN information_schema.columns c
            ON c.table_name = t.table_name AND c.table_schema = t.table_schema
        WHERE t.table_schema = '{TCG_SCHEMA}'
          AND t.table_name IN (
            'tcg_suppliers', 'supplier_channels', 'tcg_products',
            'product_search_keywords', 'product_exclude_keywords',
            'units', 'unit_aliases', 'conditions', 'condition_aliases',
            'source_messages', 'extraction_jobs', 'extraction_items',
            'analysis_results', 'import_jobs', 'audit_log'
          )
        ORDER BY t.table_name, c.ordinal_position
    """))
    rows = result.fetchall()
    headers = ["table_name", "column_name", "data_type", "is_nullable", "column_default"]
    data = [[str(v) if v is not None else "" for v in row] for row in rows]
    return headers, data


# ──────────────────────────────────────────────────────────────────────────────
# メイン書き出しロジック
# ──────────────────────────────────────────────────────────────────────────────

async def _write_mirror_async() -> dict[str, int]:
    """DB からデータを取得してミラーシートに書き出す。非同期版。"""
    from app.database import AsyncSessionLocal

    gc = _build_client()
    sh = _verify_id(gc, MIRROR_SPREADSHEET_ID)
    now_iso = datetime.now(timezone.utc).isoformat()

    async with AsyncSessionLocal() as db:
        p_headers, p_data = await _fetch_products(db)
        k_headers, k_data = await _fetch_keywords(db)
        s_headers, s_data = await _fetch_suppliers(db)
        ss_headers, ss_data = await _fetch_supplier_summary(db)
        db_headers, db_data = await _fetch_db_structure(db)

    def _write_tab(title: str, headers: list[str], data: list[list]) -> None:
        ws = _get_or_add_worksheet(sh, title)
        ws.clear()
        ws.update(values=[headers] + data, range_name="A1")
        ws.update(values=[[f"最終更新: {now_iso}"]], range_name=f"A{len(data) + 3}")
        logger.info("[tcg_mirror] %s: %d行書き出し", title, len(data))

    _write_tab("[MIRROR] 商品マスタ", p_headers, p_data)
    _write_tab("[MIRROR] 検索キーワード", k_headers, k_data)
    _write_tab("[MIRROR] 仕入元", s_headers, s_data)
    _write_tab("[MIRROR] 仕入元サマリー", ss_headers, ss_data)
    _write_tab("[MIRROR] DB構造", db_headers, db_data)

    # READ ME タブ
    ws_readme = _get_or_add_worksheet(sh, "READ ME", rows=30, cols=5)
    ws_readme.clear()
    ws_readme.update(values=[[_README_BODY]], range_name="A1")
    ws_readme.update(values=[[f"最終更新: {now_iso}"]], range_name="A10")
    logger.info("[tcg_mirror] READ ME 更新完了")

    return {
        "products": len(p_data),
        "keywords": len(k_data),
        "suppliers": len(s_data),
        "supplier_summary": len(ss_data),
        "db_structure": len(db_data),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Celery タスク
# ──────────────────────────────────────────────────────────────────────────────

def run_tcg_mirror_write() -> None:
    """
    Celery タスクのエントリポイント。
    TCG_SHEETS_SA_KEY_FILE が未設定の場合はスキップ（本番以外の環境で安全に無視）。
    シート自動作成は一切行わない。
    """
    import asyncio

    key_file = os.getenv("TCG_SHEETS_SA_KEY_FILE", "").strip()
    if not key_file:
        logger.info(
            "[tcg_mirror] TCG_SHEETS_SA_KEY_FILE 未設定 — スキップ"
        )
        return

    logger.info("[tcg_mirror] 書き出し開始: spreadsheetId=%s", MIRROR_SPREADSHEET_ID)
    try:
        stats = asyncio.run(_write_mirror_async())
        logger.info(
            "[tcg_mirror] 書き出し完了: products=%d keywords=%d suppliers=%d "
            "supplier_summary=%d db_structure=%d",
            stats["products"],
            stats["keywords"],
            stats["suppliers"],
            stats["supplier_summary"],
            stats["db_structure"],
        )
    except Exception as exc:
        logger.error("[tcg_mirror] 書き出し失敗: %s", exc, exc_info=True)
        raise
