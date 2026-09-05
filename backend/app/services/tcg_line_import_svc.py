"""
MIG-04 Phase 2: LINE エクスポートファイル取り込みサービス。

GAS の Latest24LineImport.js (parseLatest24LineExport / resolveSuppliers /
buildProviderEntries / importLineExport) と同等のロジックを Python に移植。

TCG解析システムは tenant_004 専用スキーマ。全 SQL は tenant_004. で修飾する。

【確認工程】
未解決の仕入元が 1 件以上のとき source_messages を書かず、
import_jobs に pending_messages / window / unresolved_names を保存して保留にする。
確認後に POST /{import_job_id}/commit で書き込みを再開する。

【JST 窓計算】
窓は JST の現在時刻を基準に計算する（旧実装は UTC 基準で実質 33h になっていた）。
JST 定数は #3305 で追加済みの timezone(timedelta(hours=9)) を使用する。
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
from app.tcg_config import TCG_SCHEMA

JST = timezone(timedelta(hours=9))

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


def _split_sender(tail: str, sorted_names: list[str]) -> tuple[str, str]:
    """
    GAS の latest24SplitHeader_ と同等ロジック。

    仕入元マスタ名（長さ降順）で前方一致を試し、
    一致すれば (name, rest_body) を返す。
    一致しなければ最初のスペースで分割（GAS のフォールバックと同等）。

    Args:
        tail:         時刻行から時刻部分を除いた残り文字列（例: "倉田 和博 本文..."）
        sorted_names: tcg_suppliers.name を長さ降順に並べたリスト

    Returns:
        (display_name, body)

    GAS 参照:
        latest24SplitHeader_ — Latest24LineImport.js:23-37
        if (tail === name) → exact match
        if (tail.indexOf(name + ' ') === 0) → prefix+space match
        else → split at first space
    """
    for name in sorted_names:
        if tail == name:
            return name, ""
        if tail.startswith(name + " "):
            return name, tail[len(name) + 1:]
    # GAS フォールバックと同等: 最初のスペースで分割
    parts = tail.split(" ", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def _compute_window(
    window_hours: int,
    window_start: str | None,
    window_end: str | None,
) -> tuple[str | None, str | None]:
    """
    JST 基準の窓を計算して (effective_start, effective_end) を返す。

    window_start が明示されている場合はそのまま使う。
    window_start が None かつ window_hours > 0 の場合、
    JST 現在時刻から window_hours 時間前を cutoff として計算する。

    旧実装は UTC 基準のため JST +9h と合算して実質 33h になっていた（DIST-R3）。
    この関数は JST 基準のため正確に 24h（指定値）になる。
    """
    effective_start = window_start
    if effective_start is None and window_hours > 0:
        cutoff_jst = datetime.now(JST) - timedelta(hours=window_hours)
        effective_start = cutoff_jst.strftime("%Y-%m-%d %H:%M:%S")
    return effective_start, window_end


# ---------------------------------------------------------------------------
# パーサ
# ---------------------------------------------------------------------------


def parse_line_export(
    export_text: str,
    supplier_names: list[str] | None = None,
) -> list[dict]:
    """
    LINE エクスポートテキストをメッセージ単位に分解する。

    GAS の parseLatest24LineExport と同等ロジック。

    Args:
        export_text:    LINE エクスポートファイルの全文字列
        supplier_names: tcg_suppliers.name の一覧（長さ降順ソート済み）。
                        渡すと GAS の latest24SplitHeader_ と同等の送信者名切り出しを行う。
                        None または空リストの場合は最初のスペースで分割（後方互換）。

    戻り値:
        [{
            "timestamp": "YYYY-MM-DD HH:MM:00",
            "display_name": str,
            "body": str,             # 継続行を \n\n で結合済み
            "is_system_event": bool,
        }]
    """
    sorted_names: list[str] = supplier_names or []
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
            # 前の日のメッセージが未確定なら確定する
            if current_msg is not None:
                messages.append(current_msg)
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

            # GAS の latest24SplitHeader_ と同等:
            # マスタ名で前方一致 → 一致しなければ最初のスペースで分割
            display_name, body = _split_sender(rest, sorted_names)

            timestamp = f"{current_date} {hour:02d}:{minute:02d}:00"
            # GAS と同等: displayName + firstBody の連結に対してシステムイベント判定
            # (Latest24LineImport.js:73)
            check_str = display_name + (" " + body if body else "")
            is_system = bool(_SYSTEM_EVENT_RE.search(check_str))

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
            # システムイベント再判定（継続行込みで再チェック）
            check_str = current_msg["display_name"] + " " + current_msg["body"]
            current_msg["is_system_event"] = bool(
                _SYSTEM_EVENT_RE.search(check_str)
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
    display_name の完全一致で (sp_code, canonical_name) を解決。

    parse_line_export が supplier_names を使って送信者名を確定した後は、
    display_name はマスタ名そのものになるため完全一致で十分。
    これは GAS の `spId: byName[m.displayName] || ''`（Latest24LineImport.js:74）
    と同等。

    Args:
        messages: parse_line_export の戻り値（is_system_event=False のみを渡すこと）
        db_suppliers: [{"code": str, "name": str}, ...] — tcg_suppliers is_active=TRUE 全件

    Returns:
        (resolved, unresolved)
        resolved:   [{...message, "sp_code": str, "canonical_name": str}]
        unresolved: [{"display_name": str, "timestamps": list[str]}]
    """
    # 完全一致辞書（GAS の byName と同等）
    name_to_supplier: dict[str, dict] = {s["name"]: s for s in db_suppliers}

    resolved: list[dict] = []
    unresolved_map: dict[str, list[str]] = {}  # display_name → timestamp list

    for msg in messages:
        dn = msg["display_name"]
        sup = name_to_supplier.get(dn)
        matched_code: str | None = sup["code"] if sup else None
        matched_name: str | None = sup["name"] if sup else None

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
    同一 sp_code のメッセージを timestamp 昇順ソートし、
    最新の 1 件のみを raw_text として採用する（SQR-05）。

    戻り値:
        [{
            "sp_code": str,
            "canonical_name": str,
            "raw_text": str,               # 最新メッセージ本文のみ（SQR-05）
            "received_at": str,            # 最初の timestamp "YYYY-MM-DD HH:MM:00"
            "sha256": str,
            "skipped_message_count": int,  # 棄却したメッセージ数（最新以外）
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
        # timestamp 昇順ソート → 末尾が最新
        sorted_msgs = sorted(msgs, key=lambda m: m["timestamp"])
        latest_msg = sorted_msgs[-1]
        raw_text = latest_msg["body"]
        received_at = sorted_msgs[0]["timestamp"]
        canonical_name = sorted_msgs[0]["canonical_name"]
        skipped_message_count = len(sorted_msgs) - 1

        entries.append(
            {
                "sp_code": code,
                "canonical_name": canonical_name,
                "raw_text": raw_text,
                "received_at": received_at,
                "sha256": sha256_text(raw_text),
                "skipped_message_count": skipped_message_count,
            }
        )
    return entries


# ---------------------------------------------------------------------------
# source_messages / extraction_jobs への書き込み（import と commit で共有）
# ---------------------------------------------------------------------------


async def _write_source_messages(
    db: AsyncSession,
    provider_entries: list[dict],
) -> list[str]:
    """
    provider_entries を source_messages / extraction_jobs に書き込む。

    Returns:
        エンキュー対象の source_message_id リスト
    """
    enqueued_ids: list[str] = []

    for entry in provider_entries:
        sp_code = entry["sp_code"]

        # supplier_channel の取得（channel='line', sp_code に対応する channel）
        channel_row = await db.execute(
            text(
                f"""
                SELECT sc.id
                FROM {TCG_SCHEMA}.supplier_channels sc
                JOIN {TCG_SCHEMA}.tcg_suppliers ts ON ts.id = sc.supplier_id
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
            continue

        supplier_channel_id = channel_rec[0]

        existing_active = await db.execute(
            text(
                f"""
                SELECT id FROM {TCG_SCHEMA}.source_messages
                WHERE supplier_channel_id = :scid AND is_active = TRUE
                """
            ),
            {"scid": str(supplier_channel_id)},
        )
        active_records = existing_active.fetchall()

        new_sm_id = uuid.uuid4()

        try:
            received_at_dt = datetime.strptime(
                entry["received_at"], "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=JST)
        except ValueError:
            received_at_dt = None

        await db.execute(
            text(
                f"""
                INSERT INTO {TCG_SCHEMA}.source_messages
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

        for old_rec in active_records:
            old_id = old_rec[0]
            await db.execute(
                text(
                    f"""
                    UPDATE {TCG_SCHEMA}.source_messages
                    SET superseded_by = :new_id, is_active = FALSE
                    WHERE id = :old_id
                    """
                ),
                {"new_id": str(new_sm_id), "old_id": str(old_id)},
            )

        new_ej_id = uuid.uuid4()
        await db.execute(
            text(
                f"""
                INSERT INTO {TCG_SCHEMA}.extraction_jobs
                  (id, source_message_id, status, prompt_version, created_at)
                VALUES
                  (:id, :smid, 'pending', NULL, now())
                """
            ),
            {"id": str(new_ej_id), "smid": str(new_sm_id)},
        )
        enqueued_ids.append(str(new_sm_id))

    return enqueued_ids


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
    window_hours: int = 24,
) -> dict[str, Any]:
    """
    LINE エクスポートファイルを取り込む。

    1. ファイル全体の sha256 で冪等化チェック
    2. tcg_suppliers 先行取得（parse_line_export に渡す名前リストを構築）
    3. parse_line_export → システムイベント除外 → JST 基準窓フィルタ
    4. サプライヤー解決（完全一致）→ resolved / unresolved に分ける
    5-a. unresolved 0 件: source_messages INSERT + commit + エンキュー
    5-b. unresolved 1 件以上: source_messages を書かず pending_review で保留
    6. 結果を返す（review_status と import_job_id を含む）

    Args:
        window_start: 明示的な開始 timestamp (YYYY-MM-DD HH:MM:00 以上)。
                      未指定かつ window_hours>0 の場合は JST 基準で自動計算。
        window_end:   明示的な終了 timestamp (YYYY-MM-DD HH:MM:00 未満)。
        window_hours: 自動ウィンドウ幅（時間単位）。
                      0 を指定するとウィンドウフィルタを無効化してファイル全体を取り込む。

    Returns:
        {
            "status": "imported" | "already_imported",
            "review_status": "ok" | "pending_review",
            "message_count": int,
            "provider_count": int,
            "unresolved_count": int,
            "unresolved_display_names": list[str],
            "skipped_message_count": int,
            "import_job_id": str,
        }
    """
    # --- 1. 冪等化チェック ---
    file_sha256 = sha256_text(export_text)

    existing_row = await db.execute(
        text(f"SELECT id, status FROM {TCG_SCHEMA}.import_jobs WHERE raw_sha256 = :sha256"),
        {"sha256": file_sha256},
    )
    existing = existing_row.fetchone()
    if existing:
        return {
            "status": "already_imported",
            "review_status": "ok",
            "message_count": 0,
            "provider_count": 0,
            "unresolved_count": 0,
            "unresolved_display_names": [],
            "skipped_message_count": 0,
            "import_job_id": str(existing[0]),
        }

    # --- 2. マスタ先行取得 ---
    suppliers_rows = await db.execute(
        text(f"SELECT code, name FROM {TCG_SCHEMA}.tcg_suppliers WHERE is_active = TRUE")
    )
    db_suppliers = [{"code": r[0], "name": r[1]} for r in suppliers_rows.fetchall()]
    supplier_names = sorted((s["name"] for s in db_suppliers), key=len, reverse=True)

    # --- 3. パース & フィルタ ---
    all_messages = parse_line_export(export_text, supplier_names)
    messages = [m for m in all_messages if not m["is_system_event"]]

    # 窓を JST 基準で計算（旧実装は UTC 基準のため実質 33h だった: DIST-R3 是正）
    effective_window_start, effective_window_end = _compute_window(
        window_hours, window_start, window_end
    )

    if effective_window_start:
        messages = [m for m in messages if m["timestamp"] >= effective_window_start]
    if effective_window_end:
        messages = [m for m in messages if m["timestamp"] < effective_window_end]

    message_count = len(messages)

    # --- 4. サプライヤー解決 ---
    resolved_msgs, unresolved = resolve_suppliers(messages, db_suppliers)
    unresolved_count = len(unresolved)
    unresolved_display_names = [u["display_name"] for u in unresolved]

    # --- 5. 分岐 ---
    import_job_id = uuid.uuid4()

    if unresolved_count == 0:
        # 5-a. 全件解決済み: 書き込み → commit → エンキュー
        provider_entries = build_provider_entries(resolved_msgs)
        provider_count = len(provider_entries)
        skipped_message_count = sum(e["skipped_message_count"] for e in provider_entries)

        enqueued_ids = await _write_source_messages(db, provider_entries)

        # TIMESTAMPTZ カラムへは datetime オブジェクトで渡す
        # （asyncpg は文字列を拒否する: IMP-39 で本番障害として発覚）
        ws_dt = datetime.strptime(effective_window_start, "%Y-%m-%d %H:%M:%S") if effective_window_start else None
        we_dt = datetime.strptime(effective_window_end, "%Y-%m-%d %H:%M:%S") if effective_window_end else None

        await db.execute(
            text(
                f"""
                INSERT INTO {TCG_SCHEMA}.import_jobs
                  (id, filename, raw_sha256, message_count, provider_count,
                   unresolved_count, uploaded_by, status, review_status, created_at,
                   window_start, window_end)
                VALUES
                  (:id, :filename, :sha256, :msg_count, :prov_count,
                   0, :uploaded_by, 'ok', 'ok', now(),
                   :ws, :we)
                """
            ),
            {
                "id": str(import_job_id),
                "filename": filename,
                "sha256": file_sha256,
                "msg_count": message_count,
                "prov_count": provider_count,
                "uploaded_by": uploaded_by,
                "ws": ws_dt,
                "we": we_dt,
            },
        )

        await db.commit()

        for sm_id in enqueued_ids:
            _enqueue_extraction(sm_id)

        return {
            "status": "imported",
            "review_status": "ok",
            "message_count": message_count,
            "provider_count": provider_count,
            "unresolved_count": 0,
            "unresolved_display_names": [],
            "skipped_message_count": skipped_message_count,
            "import_job_id": str(import_job_id),
        }

    else:
        # 5-b. 未解決あり: source_messages を1件も書かず保留
        # 解決済みの仕入元も含め全件が保留になる（意図した挙動）

        # TIMESTAMPTZ カラムへは datetime オブジェクトで渡す（IMP-39 是正）
        ws_dt = datetime.strptime(effective_window_start, "%Y-%m-%d %H:%M:%S") if effective_window_start else None
        we_dt = datetime.strptime(effective_window_end, "%Y-%m-%d %H:%M:%S") if effective_window_end else None

        await db.execute(
            text(
                f"""
                INSERT INTO {TCG_SCHEMA}.import_jobs
                  (id, filename, raw_sha256, message_count, provider_count,
                   unresolved_count, uploaded_by, status, review_status, created_at,
                   window_start, window_end, pending_messages, unresolved_names)
                VALUES
                  (:id, :filename, :sha256, :msg_count, 0,
                   :unresolved_count, :uploaded_by, 'ok', 'pending_review', now(),
                   :ws, :we, :pending_messages, :unresolved_names)
                """
            ),
            {
                "id": str(import_job_id),
                "filename": filename,
                "sha256": file_sha256,
                "msg_count": message_count,
                "unresolved_count": unresolved_count,
                "uploaded_by": uploaded_by,
                "ws": ws_dt,
                "we": we_dt,
                "pending_messages": json.dumps(messages, ensure_ascii=False),
                "unresolved_names": json.dumps(unresolved_display_names, ensure_ascii=False),
            },
        )

        await db.commit()

        return {
            "status": "imported",
            "review_status": "pending_review",
            "message_count": message_count,
            "provider_count": 0,
            "unresolved_count": unresolved_count,
            "unresolved_display_names": unresolved_display_names,
            "skipped_message_count": 0,
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
        import logging  # noqa: PLC0415

        logging.getLogger(__name__).warning(
            "[tcg_line_import] Celery enqueue skipped for sm=%s: %s",
            source_message_id,
            exc,
        )
