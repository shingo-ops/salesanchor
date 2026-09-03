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
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

TCG_SCHEMA = "tenant_004"

# 安全装置 #5: 書き込み行数上限
DIST_ROW_LIMIT = 5000

# 出力ヘッダー（確定・10列）
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
    "提供者",
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

async def fetch_output_rows(
    db: AsyncSession,
    *,
    include_flag_single: bool = False,
) -> list[list[str]]:
    """
    配信対象行を10列で取得する。
    フィルター:
      pid_resolved AND unit_resolved AND NOT LIKE 'FLAG_%'
      AND price_normalized IS NOT NULL  ← 価格未解決行を除外
    include_flag_single=True のとき FLAG_SINGLE も含める。

    注意: 現在の全レコードは engine_version='compat-v1'（GAS計算値）。
    正規化ルール（NR0001〜NR0136）は新エンジン再解析まで未適用。
    再解析後は価格 NULL が減り配信件数が変動する。
    """
    # include_flag_single=True のとき FLAG_SINGLE だけは通す。他の FLAG_* は常に除外。
    if include_flag_single:
        cond_filter = (
            "(ar.condition_canonical NOT LIKE 'FLAG_%'"
            " OR ar.condition_canonical = 'FLAG_SINGLE')"
        )
    else:
        cond_filter = "ar.condition_canonical NOT LIKE 'FLAG_%'"

    sql = text(f"""
        SELECT
            COALESCE(TO_CHAR(sm.received_at AT TIME ZONE 'Asia/Tokyo',
                             'YYYY-MM-DD HH24:MI:SS'), '')          AS posted_at,
            COALESCE(p.mark, '')                                    AS mark,
            COALESCE(p.japanese_title, '')                          AS japanese_title,
            COALESCE(p.english_title, '')                           AS english_title,
            ar.condition_canonical                                   AS condition,
            COALESCE(ar.price_normalized::text, '')                 AS unit_price,
            COALESCE(ar.quantity_normalized::text, '')              AS quantity,
            COALESCE(ar.note_ja, '')                                AS note_ja,
            COALESCE(ar.status, '')                                 AS status,
            COALESCE(ts.name, '')                                   AS provider
        FROM {TCG_SCHEMA}.analysis_results ar
        JOIN {TCG_SCHEMA}.extraction_items ei
            ON ei.id = ar.extraction_item_id
        JOIN {TCG_SCHEMA}.extraction_jobs ej
            ON ej.id = ei.extraction_job_id
        JOIN {TCG_SCHEMA}.source_messages sm
            ON sm.id = ej.source_message_id
        JOIN {TCG_SCHEMA}.supplier_channels sc
            ON sc.id = sm.supplier_channel_id
        LEFT JOIN {TCG_SCHEMA}.tcg_suppliers ts
            ON ts.id = sc.supplier_id
        LEFT JOIN {TCG_SCHEMA}.tcg_products p
            ON p.id = ar.product_id
        WHERE ar.pid_resolved = TRUE
          AND ar.unit_resolved = TRUE
          AND ar.price_normalized IS NOT NULL
          AND {cond_filter}
        ORDER BY ts.name NULLS LAST, p.code NULLS LAST, ar.id
    """)

    result = await db.execute(sql)
    rows = result.mappings().all()
    return [
        [
            row["posted_at"],
            row["mark"],
            row["japanese_title"],
            row["english_title"],
            row["condition"],
            row["unit_price"],
            row["quantity"],
            row["note_ja"],
            row["status"],
            row["provider"],
        ]
        for row in rows
    ]


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

    # 配信候補件数
    if include_flag_single:
        cond_filter = (
            "(ar.condition_canonical NOT LIKE 'FLAG_%'"
            " OR ar.condition_canonical = 'FLAG_SINGLE')"
        )
    else:
        cond_filter = "ar.condition_canonical NOT LIKE 'FLAG_%'"
    count_result = await db.execute(text(f"""
        SELECT COUNT(*) AS cnt
        FROM {TCG_SCHEMA}.analysis_results ar
        WHERE ar.pid_resolved = TRUE
          AND ar.unit_resolved = TRUE
          AND ar.price_normalized IS NOT NULL
          AND {cond_filter}
    """))
    output_count = count_result.scalar()

    # 除外内訳
    excl_result = await db.execute(text(f"""
        SELECT
            COUNT(*) FILTER (WHERE ar.condition_canonical LIKE 'FLAG_%')
                AS exc_flag,
            COUNT(*) FILTER (
                WHERE ar.condition_canonical NOT LIKE 'FLAG_%'
                  AND ar.pid_resolved = FALSE
                  AND ar.unit_resolved = TRUE)
                AS exc_pid_only,
            COUNT(*) FILTER (
                WHERE ar.condition_canonical NOT LIKE 'FLAG_%'
                  AND ar.pid_resolved = TRUE
                  AND ar.unit_resolved = FALSE)
                AS exc_unit_only,
            COUNT(*) FILTER (
                WHERE ar.condition_canonical NOT LIKE 'FLAG_%'
                  AND ar.pid_resolved = FALSE
                  AND ar.unit_resolved = FALSE)
                AS exc_both,
            COUNT(*) FILTER (
                WHERE ar.pid_resolved = TRUE
                  AND ar.unit_resolved = TRUE
                  AND ar.condition_canonical NOT LIKE 'FLAG_%'
                  AND ar.price_normalized IS NULL)
                AS exc_price
        FROM {TCG_SCHEMA}.analysis_results ar
    """))
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
          AND ar.created_at >= NOW() - INTERVAL '30 days'
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

def _write_to_target_sync(
    gc: Any,
    creds: Any,
    target: dict,
    rows: list[list[str]],
) -> dict:
    """
    単一配信先への書き込みを実行する（同期関数）。
    安全装置 #1〜#5 を実装する。
    asyncio.get_event_loop().run_in_executor() 経由で呼ぶこと。

    Returns:
        {"status": "ok", "rows_written": N} または
        {"status": "error", "error": "message"}
    """
    import gspread

    spreadsheet_id = target["spreadsheet_id"]
    sheet_name = target["sheet_name"]

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
        all_rows = [DIST_HEADERS] + rows
        worksheet.append_rows(all_rows, value_input_option="RAW")

        rows_written = len(rows)
        logger.info("[dist] 書き込み完了: target=%s rows=%d", target["name"], rows_written)
        return {"status": "ok", "rows_written": rows_written}

    except Exception as exc:
        error_msg = str(exc)
        logger.error("[dist] 書き込みエラー: target=%s error=%s", target["name"], error_msg)
        return {"status": "error", "error": error_msg}


# ---------------------------------------------------------------------------
# 配信先 CRUD
# ---------------------------------------------------------------------------

async def list_targets(db: AsyncSession) -> list[dict]:
    result = await db.execute(text(f"""
        SELECT id, name, spreadsheet_id, sheet_name, is_active,
               sa_key_secret_name, last_distributed_at, last_distributed_count,
               last_result, created_at, updated_at
        FROM {TCG_SCHEMA}.tcg_distribution_targets
        ORDER BY name
    """))
    return [dict(row) for row in result.mappings()]


async def get_target(db: AsyncSession, target_id: str) -> dict | None:
    result = await db.execute(
        text(f"""
            SELECT id, name, spreadsheet_id, sheet_name, is_active,
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

async def run_distribution(
    db: AsyncSession,
    target_id: str | None = None,
) -> dict:
    """
    全アクティブ配信先（または特定 target_id）へ配信を実行する。

    手順:
      1. 設定ロード
      2. 出力データ取得（確定フィルター）
      3. 配信先取得
      4. 各配信先へ thread executor で書き込み（安全装置 #1〜#5）
      5. 結果を DB に記録（安全装置 #7）
      6. 失敗があれば Discord 通知（安全装置 #6）
    """
    started_at = datetime.now(timezone.utc)

    # 1. 設定ロード
    settings = await load_distribution_settings(db)
    include_flag_single = settings.get("include_flag_single", "false").lower() == "true"

    # 2. 出力データ取得
    try:
        rows = await fetch_output_rows(db, include_flag_single=include_flag_single)
    except Exception as exc:
        logger.error("[dist] 出力データ取得エラー: %s", exc)
        return {
            "run_id": None,
            "started_at": started_at.isoformat(),
            "output_count": 0,
            "results": [],
            "errors": [{"target_id": None, "error": f"出力データ取得失敗: {exc}"}],
        }

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
        creds = Credentials.from_service_account_file(key_file, scopes=_SCOPES)
        gc = _build_gspread_client()
    except Exception as exc:
        logger.error("[dist] SA クライアント生成エラー: %s", exc)
        return {
            "run_id": None,
            "started_at": started_at.isoformat(),
            "output_count": output_count,
            "results": [],
            "errors": [{"target_id": None, "error": f"SA 認証失敗: {exc}"}],
        }

    # 4. 各配信先へ書き込み（thread executor）
    loop = asyncio.get_event_loop()
    results = []
    errors = []

    for target in targets:
        write_result = await loop.run_in_executor(
            None,
            _write_to_target_sync,
            gc,
            creds,
            target,
            rows,
        )

        # 5. 配信履歴を DB に記録（安全装置 #7）
        if write_result["status"] == "ok":
            await _record_distribution_result(db, target["id"], "ok", write_result["rows_written"])
            results.append({
                "target_id": str(target["id"]),
                "target_name": target["name"],
                "status": "ok",
                "rows_written": write_result["rows_written"],
            })
        else:
            await _record_distribution_result(
                db, target["id"], write_result["error"], None
            )
            errors.append({
                "target_id": str(target["id"]),
                "target_name": target["name"],
                "error": write_result["error"],
            })

    # 6. 失敗時 Discord 通知（安全装置 #6）
    if errors:
        await _notify_distribution_failure(db, errors, output_count)

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
