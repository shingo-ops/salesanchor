"""
MIG-04 Phase 2: LINE エクスポートファイル取り込みサービス。

GAS の Latest24LineImport.js (parseLatest24LineExport / resolveSuppliers /
buildProviderEntries / importLineExport) と同等のロジックを Python に移植。
"""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

# 日付行: "2026.08.26 月曜日" など
_DATE_RE = re.compile(r"^(\d{4})\.(\d{2})\.(\d{2})\s+.+$")
# 時刻行: "14:30 山田太郎 こんにちは" など（時が 1 桁でも対応）
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})\s+(.+)$")
# システムイベント（除外対象）
_SYSTEM_EVENT_RE = re.compile(
    r"(?:がグループに参加しました。?|をグループに招待しました。?"
    r"|招待をキャンセルしました。?|がメッセージの送信を取り消しました。?)$"
)
# メッセージ結合セパレーター（SQR-05）
_MSG_SEPARATOR = "\n\n"


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------


def sha256_text(text_content: str) -> str:
    """UTF-8 SHA-256 hex を返す。"""
    return hashlib.sha256(text_content.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# パーサ
# ---------------------------------------------------------------------------


def parse_line_export(export_text: str) -> list[dict]:
    """
    LINE エクスポートテキストをメッセージ単位に分解する。

    GAS の parseLatest24LineExport と同等ロジック（supplierRows なし版）。

    戻り値:
        [{
            "timestamp": "YYYY-MM-DD HH:MM:00",
            "display_name": str,
            "body": str,             # 継続行を \n\n で結合済み
            "is_system_event": bool,
        }]
    """
    current_date: str | None = None
    messages: list[dict] = []
    current_msg: dict | None = None

    for raw_line in export_text.splitlines():
        line = raw_line.rstrip()

        # 空行はスキップ
        if not line:
            continue

        # 日付行
        date_m = _DATE_RE.match(line)
        if date_m:
            current_date = f"{date_m.group(1)}-{date_m.group(2)}-{date_m.group(3)}"
            current_msg = None
            continue

        # 時刻行（メッセージ開始）
        time_m = _TIME_RE.match(line)
        if time_m and current_date:
            # 前のメッセージを確定
            if current_msg is not None:
                messages.append(current_msg)

            hour = int(time_m.group(1))
            minute = int(time_m.group(2))
            rest = time_m.group(3)

            # "送信者名 本文" を分割（最初のスペースが境界）
            parts = rest.split(" ", 1)
            display_name = parts[0] if len(parts) >= 1 else ""
            body = parts[1] if len(parts) >= 2 else ""

            timestamp = f"{current_date} {hour:02d}:{minute:02d}:00"
            is_system = bool(_SYSTEM_EVENT_RE.search(body))

            current_msg = {
                "timestamp": timestamp,
                "display_name": display_name,
                "body": body,
                "is_system_event": is_system,
            }
            continue

        # 継続行（時刻・日付・空行のどれでもない行）
        if current_msg is not None:
            current_msg["body"] = current_msg["body"] + _MSG_SEPARATOR + line
            # システムイベント再判定
            current_msg["is_system_event"] = bool(
                _SYSTEM_EVENT_RE.search(current_msg["body"])
            )

    # 最後のメッセージを確定
    if current_msg is not None:
        messages.append(current_msg)

    return messages


# ---------------------------------------------------------------------------
# サプライヤー解決
# ---------------------------------------------------------------------------


def resolve_suppliers(
    messages: list[dict],
    db_suppliers: list[dict],
) -> tuple[list[dict], list[dict]]:
    """
    最長一致優先プレフィックスマッチで display_name → (sp_code, canonical_name) を解決。

    Args:
        messages: parse_line_export の戻り値（is_system_event=False のみを渡すこと）
        db_suppliers: [{"code": str, "name": str}, ...] — tcg_suppliers 全件

    Returns:
        (resolved, unresolved)
        resolved:   [{...message, "sp_code": str, "canonical_name": str}]
        unresolved: [{"display_name": str, "timestamps": list[str]}]
    """
    # 最長一致のため name 長で降順ソート
    sorted_suppliers = sorted(db_suppliers, key=lambda s: len(s["name"]), reverse=True)

    resolved: list[dict] = []
    unresolved_map: dict[str, list[str]] = {}  # display_name → timestamp list

    for msg in messages:
        dn = msg["display_name"]
        matched_code: str | None = None
        matched_name: str | None = None

        for sup in sorted_suppliers:
            if dn.startswith(sup["name"]):
                matched_code = sup["code"]
                matched_name = sup["name"]
                break

        if matched_code:
            resolved.append(
                {
                    **msg,
                    "sp_code": matched_code,
                    "canonical_name": matched_name,
                }
            )
        else:
            if dn not in unresolved_map:
                unresolved_map[dn] = []
            unresolved_map[dn].append(msg["timestamp"])

    unresolved = [
        {"display_name": dn, "timestamps": tss}
        for dn, tss in unresolved_map.items()
    ]
    return resolved, unresolved


# ---------------------------------------------------------------------------
# プロバイダエントリ構築 (SQR-05)
# ---------------------------------------------------------------------------


def build_provider_entries(
    resolved_messages: list[dict],
) -> list[dict]:
    """
    同一 sp_code のメッセージを timestamp 昇順ソートして _MSG_SEPARATOR で結合。

    戻り値:
        [{
            "sp_code": str,
            "canonical_name": str,
            "raw_text": str,        # "\n\n" 結合済み
            "received_at": str,     # 最初の timestamp "YYYY-MM-DD HH:MM:00"
            "sha256": str,
        }]
    """
    # sp_code ごとにグループ化
    groups: dict[str, list[dict]] = {}
    for msg in resolved_messages:
        code = msg["sp_code"]
        if code not in groups:
            groups[code] = []
        groups[code].append(msg)

    entries: list[dict] = []
    for code, msgs in groups.items():
        # timestamp 昇順ソート
        sorted_msgs = sorted(msgs, key=lambda m: m["timestamp"])
        raw_text = _MSG_SEPARATOR.join(m["body"] for m in sorted_msgs)
        received_at = sorted_msgs[0]["timestamp"]
        canonical_name = sorted_msgs[0]["canonical_name"]

        entries.append(
            {
                "sp_code": code,
                "canonical_name": canonical_name,
                "raw_text": raw_text,
                "received_at": received_at,
                "sha256": sha256_text(raw_text),
            }
        )
    return entries


# ---------------------------------------------------------------------------
# メイン取り込み関数
# ---------------------------------------------------------------------------


async def import_line_export(
    db: AsyncSession,
    filename: str,
    export_text: str,
    uploaded_by: str | None,
    window_start: str | None = None,
    window_end: str | None = None,
) -> dict[str, Any]:
    """
    LINE エクスポートファイルを取り込む。

    1. ファイル全体の sha256 で冪等化チェック
    2. parse_line_export → システムイベント除外 → ウィンドウフィルタ
    3. tcg_suppliers 全件取得 → サプライヤー解決
    4. provider_entries 構築
    5. 各 sp_code の source_messages を supersede + 新規 INSERT + extraction_jobs INSERT
    6. import_jobs に記録
    7. 結果を返す

    Returns:
        {
            "status": "imported" | "already_imported",
            "message_count": int,
            "provider_count": int,
            "unresolved_count": int,
            "unresolved_display_names": list[str],
            "import_job_id": str,
        }
    """
    # --- 1. 冪等化チェック ---
    file_sha256 = sha256_text(export_text)

    existing_row = await db.execute(
        text("SELECT id, status FROM import_jobs WHERE raw_sha256 = :sha256"),
        {"sha256": file_sha256},
    )
    existing = existing_row.fetchone()
    if existing:
        return {
            "status": "already_imported",
            "message_count": 0,
            "provider_count": 0,
            "unresolved_count": 0,
            "unresolved_display_names": [],
            "import_job_id": str(existing[0]),
        }

    # --- 2. パース & フィルタ ---
    all_messages = parse_line_export(export_text)

    # システムイベント除外
    messages = [m for m in all_messages if not m["is_system_event"]]

    # ウィンドウフィルタ（指定がある場合のみ）
    if window_start:
        messages = [m for m in messages if m["timestamp"] >= window_start]
    if window_end:
        messages = [m for m in messages if m["timestamp"] < window_end]

    message_count = len(messages)

    # --- 3. サプライヤー解決 ---
    suppliers_rows = await db.execute(
        text("SELECT code, name FROM tcg_suppliers WHERE is_active = TRUE")
    )
    db_suppliers = [{"code": r[0], "name": r[1]} for r in suppliers_rows.fetchall()]

    resolved_msgs, unresolved = resolve_suppliers(messages, db_suppliers)

    # --- 4. プロバイダエントリ構築 ---
    provider_entries = build_provider_entries(resolved_msgs)
    provider_count = len(provider_entries)
    unresolved_count = len(unresolved)
    unresolved_display_names = [u["display_name"] for u in unresolved]

    # --- 5. source_messages / extraction_jobs へ INSERT ---
    for entry in provider_entries:
        sp_code = entry["sp_code"]

        # supplier_channel の取得（channel='line', sp_code に対応する channel）
        channel_row = await db.execute(
            text(
                """
                SELECT sc.id
                FROM supplier_channels sc
                JOIN tcg_suppliers ts ON ts.id = sc.supplier_id
                WHERE ts.code = :code
                  AND sc.channel = 'line'
                  AND sc.is_active = TRUE
                LIMIT 1
                """
            ),
            {"code": sp_code},
        )
        channel_rec = channel_row.fetchone()

        if channel_rec is None:
            # supplier_channel が存在しない場合はスキップ（supplier 未登録 or channel 未設定）
            continue

        supplier_channel_id = channel_rec[0]

        # 既存の active source_message を supersede
        existing_active = await db.execute(
            text(
                """
                SELECT id FROM source_messages
                WHERE supplier_channel_id = :scid AND is_active = TRUE
                """
            ),
            {"scid": str(supplier_channel_id)},
        )
        active_records = existing_active.fetchall()

        # 新しい source_message の ID を先に確定
        new_sm_id = uuid.uuid4()

        # 既存レコードを supersede
        for old_rec in active_records:
            old_id = old_rec[0]
            await db.execute(
                text(
                    """
                    UPDATE source_messages
                    SET superseded_by = :new_id, is_active = FALSE
                    WHERE id = :old_id
                    """
                ),
                {"new_id": str(new_sm_id), "old_id": str(old_id)},
            )

        # received_at を datetime に変換
        try:
            received_at_dt = datetime.strptime(
                entry["received_at"], "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            received_at_dt = None

        # 新しい source_message を INSERT
        await db.execute(
            text(
                """
                INSERT INTO source_messages
                  (id, supplier_channel_id, raw_text, raw_sha256,
                   received_at, superseded_by, is_active, created_at)
                VALUES
                  (:id, :scid, :raw_text, :sha256,
                   :received_at, NULL, TRUE, now())
                """
            ),
            {
                "id": str(new_sm_id),
                "scid": str(supplier_channel_id),
                "raw_text": entry["raw_text"],
                "sha256": entry["sha256"],
                "received_at": received_at_dt,
            },
        )

        # extraction_jobs を pending で INSERT
        new_ej_id = uuid.uuid4()
        await db.execute(
            text(
                """
                INSERT INTO extraction_jobs
                  (id, source_message_id, status, prompt_version, created_at)
                VALUES
                  (:id, :smid, 'pending', NULL, now())
                """
            ),
            {"id": str(new_ej_id), "smid": str(new_sm_id)},
        )
        # Celery タスクを非同期起動（Redis 未起動時はスキップ）
        _enqueue_extraction(str(new_sm_id))

    # --- 6. import_jobs に記録 ---
    import_job_id = uuid.uuid4()
    await db.execute(
        text(
            """
            INSERT INTO import_jobs
              (id, filename, raw_sha256, message_count, provider_count,
               unresolved_count, uploaded_by, status, created_at)
            VALUES
              (:id, :filename, :sha256, :msg_count, :prov_count,
               :unresolved_count, :uploaded_by, 'ok', now())
            """
        ),
        {
            "id": str(import_job_id),
            "filename": filename,
            "sha256": file_sha256,
            "msg_count": message_count,
            "prov_count": provider_count,
            "unresolved_count": unresolved_count,
            "uploaded_by": uploaded_by,
        },
    )

    await db.commit()

    return {
        "status": "imported",
        "message_count": message_count,
        "provider_count": provider_count,
        "unresolved_count": unresolved_count,
        "unresolved_display_names": unresolved_display_names,
        "import_job_id": str(import_job_id),
    }


# ---------------------------------------------------------------------------
# Celery タスクエンキュー（Redis 未起動時は no-op）
# ---------------------------------------------------------------------------


def _enqueue_extraction(source_message_id: str) -> None:
    """
    extract_source_message_task を非同期でエンキューする。

    Redis が起動していない場合は kombu.exceptions.OperationalError を
    握りつぶしてスキップする。
    """
    try:
        from app.tasks.tcg_extraction import extract_source_message_task  # noqa: PLC0415

        if extract_source_message_task is not None:
            extract_source_message_task.delay(source_message_id)
    except Exception as exc:  # noqa: BLE001
        # Redis 未起動時など Celery への接続失敗は警告ログのみ
        import logging  # noqa: PLC0415

        logging.getLogger(__name__).warning(
            "[tcg_line_import] Celery enqueue skipped for sm=%s: %s",
            source_message_id,
            exc,
        )
