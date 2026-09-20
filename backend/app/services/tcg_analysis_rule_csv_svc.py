"""
分析ルール語句 CSV ラウンドトリップサービス。

CSV 形式: rule_id,title,word_kind,text（BOM 付き UTF-8、Excel 対応）

エクスポート: アクティブ版（active_revision_id）の語句を全件出力。
インポートプレビュー: 既存語句との差分を計算して追加/更新/削除件数を返す。
インポートコミット: changes 配列を構築して create_draft_revision を呼ぶ。

設計根拠: ProductMasterPanel の CSV パターン（tcg_product_roundtrip_svc.py）を踏襲。
"""
from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import tcg_analysis_rule_svc as rule_svc

CSV_COLUMNS = ["rule_id", "title", "word_kind", "text"]
MAX_BYTES = 2 * 1024 * 1024


class AnalysisRuleCsvError(ValueError):
    def __init__(self, code: str, status: int = 422):
        super().__init__(code)
        self.status = status


# ---------------------------------------------------------------------------
# エクスポート
# ---------------------------------------------------------------------------


async def export_csv(db: AsyncSession, policy_type: str) -> bytes:
    """アクティブ版の語句を CSV（BOM 付き UTF-8）で返す。"""
    rule_svc._validate_policy_type(policy_type)

    # active_revision_id を取得
    state = await rule_svc.get_current_state(db, policy_type)
    if state is None:
        raise AnalysisRuleCsvError("ANALYSIS_RULE_POLICY_NOT_FOUND", 404)
    revision_id = state.get("active_revision_id")
    if not revision_id:
        raise AnalysisRuleCsvError("ANALYSIS_RULE_NO_ACTIVE_REVISION", 422)

    # アクティブ版の語句を全件取得
    rows = await _fetch_all_words(db, str(revision_id))

    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\r\n", quoting=csv.QUOTE_ALL)
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        writer.writerow([row.get(col, "") for col in CSV_COLUMNS])

    raw = out.getvalue().encode("utf-8-sig")
    if len(raw) > MAX_BYTES:
        raise AnalysisRuleCsvError("ANALYSIS_RULE_CSV_EXPORT_TOO_LARGE", 413)
    return raw


async def _fetch_all_words(db: AsyncSession, revision_id: str) -> list[dict[str, Any]]:
    """指定版の全語句を取得（削除済み除く）。"""
    sql = text(
        """
        SELECT
            ar.id           AS rule_id,
            arv.title,
            w.kind          AS word_kind,
            w.text          AS text
        FROM public.analysis_revision_rules arr
        JOIN public.analysis_rules ar
            ON ar.id = arr.rule_id
        JOIN public.analysis_rule_versions arv
            ON arv.id = arr.rule_version_id
        JOIN public.analysis_rule_words w
            ON w.rule_version_id = arv.id
        WHERE arr.revision_id = :revision_id
          AND arr.is_deleted = FALSE
        ORDER BY ar.id, w.position, w.id
        """
    )
    result = await db.execute(sql, {"revision_id": revision_id})
    return [dict(r) for r in result.mappings().all()]


# ---------------------------------------------------------------------------
# CSV パース共通
# ---------------------------------------------------------------------------


def _parse_csv_bytes(raw: bytes) -> list[list[str]]:
    if len(raw) > MAX_BYTES:
        raise AnalysisRuleCsvError("ANALYSIS_RULE_CSV_FILE_TOO_LARGE", 413)
    try:
        return list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline="")))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise AnalysisRuleCsvError("ANALYSIS_RULE_CSV_INVALID") from exc


def _read_records(raw: bytes) -> list[dict[str, str]]:
    rows = _parse_csv_bytes(raw)
    if not rows:
        raise AnalysisRuleCsvError("ANALYSIS_RULE_CSV_EMPTY")
    if rows[0] != CSV_COLUMNS:
        raise AnalysisRuleCsvError("ANALYSIS_RULE_CSV_HEADER_MISMATCH")
    if len(rows) == 1:
        raise AnalysisRuleCsvError("ANALYSIS_RULE_CSV_EMPTY")
    records = []
    for i, row in enumerate(rows[1:], 1):
        if len(row) != len(CSV_COLUMNS):
            raise AnalysisRuleCsvError(f"ANALYSIS_RULE_CSV_COLUMN_COUNT_MISMATCH_ROW_{i}")
        records.append(dict(zip(CSV_COLUMNS, row, strict=True)))
    return records


# ---------------------------------------------------------------------------
# インポートプレビュー
# ---------------------------------------------------------------------------


async def preview_import(
    db: AsyncSession,
    policy_type: str,
    raw: bytes,
) -> dict[str, Any]:
    """CSV をパースして既存語句との差分を返す（書き込みなし）。"""
    rule_svc._validate_policy_type(policy_type)
    records = _read_csv_records(raw)

    state = await rule_svc.get_current_state(db, policy_type)
    if state is None:
        raise AnalysisRuleCsvError("ANALYSIS_RULE_POLICY_NOT_FOUND", 404)
    revision_id = state.get("active_revision_id")
    if not revision_id:
        raise AnalysisRuleCsvError("ANALYSIS_RULE_NO_ACTIVE_REVISION", 422)

    existing = await _fetch_all_words(db, str(revision_id))
    # (rule_id, word_kind) → text をキーに既存マップを作成
    existing_map: dict[tuple[str, str], str] = {}
    existing_rule_ids: set[str] = set()
    for row in existing:
        key = (str(row["rule_id"]), str(row["word_kind"]))
        existing_map[key] = str(row["text"])
        existing_rule_ids.add(str(row["rule_id"]))

    add_list: list[dict[str, str]] = []
    update_list: list[dict[str, str]] = []
    csv_rule_ids: set[str] = set()

    for rec in records:
        rule_id = rec["rule_id"].strip()
        word_kind = rec["word_kind"].strip()
        text_val = rec["text"].strip()
        key = (rule_id, word_kind)
        csv_rule_ids.add(rule_id)

        if key not in existing_map:
            add_list.append({"rule_id": rule_id, "title": rec["title"], "word_kind": word_kind, "text": text_val})
        elif existing_map[key] != text_val:
            update_list.append({"rule_id": rule_id, "title": rec["title"], "word_kind": word_kind, "text": text_val, "before": existing_map[key]})

    # CSV に含まれない既存ルール語句 → 削除対象
    delete_list: list[dict[str, str]] = []
    for row in existing:
        rule_id = str(row["rule_id"])
        if rule_id not in csv_rule_ids:
            delete_list.append({"rule_id": rule_id, "title": str(row["title"]), "word_kind": str(row["word_kind"]), "text": str(row["text"])})

    return {
        "add_count": len(add_list),
        "update_count": len(update_list),
        "delete_count": len(delete_list),
        "add": add_list,
        "update": update_list,
        "delete": delete_list,
    }


def _read_csv_records(raw: bytes) -> list[dict[str, str]]:
    """_read_records のラッパー（AnalysisRuleCsvError をそのまま伝播）。"""
    return _read_records(raw)


# ---------------------------------------------------------------------------
# インポートコミット
# ---------------------------------------------------------------------------


async def commit_import(
    db: AsyncSession,
    policy_type: str,
    raw: bytes,
    user_email: str,
    lock_version: int,
    draft_revision_id: str | None,
    active_revision_id: str | None,
) -> dict[str, Any]:
    """CSV の内容を changes 配列に変換して create_draft_revision を呼ぶ。"""
    rule_svc._validate_policy_type(policy_type)

    # プレビューで差分を計算
    preview = await preview_import(db, policy_type, raw)

    # 追加・更新・削除を changes に変換
    changes: list[dict[str, Any]] = []

    # 追加: rule_id が既存にない場合は add_rule（CSV の rule_id は参照用 hint のみ）
    for item in preview["add"]:
        changes.append({
            "type": "add_rule",
            "title": item["text"],
            "words": [{"kind": item["word_kind"], "text": item["text"]}],
        })

    # 更新: update_rule（既存 rule_id + 新テキスト）
    for item in preview["update"]:
        changes.append({
            "type": "update_rule",
            "rule_id": item["rule_id"],
            "title": item["title"] or item["text"],
            "words": [{"kind": item["word_kind"], "text": item["text"]}],
        })

    # 削除: delete_rule
    for item in preview["delete"]:
        changes.append({
            "type": "delete_rule",
            "rule_id": item["rule_id"],
        })

    import uuid as _uuid
    result = await rule_svc.create_draft_revision(
        db,
        policy_type,
        expected_draft_id=draft_revision_id,
        expected_active_id=active_revision_id,
        lock_version=lock_version,
        changes=changes,
        request_key=str(_uuid.uuid4()),
        created_by=user_email,
    )
    return {
        **result,
        "imported_add": len(preview["add"]),
        "imported_update": len(preview["update"]),
        "imported_delete": len(preview["delete"]),
    }
