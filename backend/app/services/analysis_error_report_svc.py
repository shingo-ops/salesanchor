"""ADR-1025 便1: 解析の誤り報告の保存と通知。

候補の正本はそれぞれの今の取得元（単位・販売状況・状態・商品・メモの各マスタ）だけ。値を手で書いた一覧は持たない。
表は運用者の旗（app.is_operator）が立った接続だけ読み書きできる。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import reset_operator_context, set_operator_context
from app.schemas.analysis_error_report import ErrorReportField
from app.services import discord_notifier
from app.services.tcg_condition_review_svc import condition_options
from app.services.v102_human_decisions_svc import (
    find_job_of_item,
    invalid_product_values,
    override_options,
)

logger = logging.getLogger(__name__)

# 項目 → analysis_results の列（system_value の出どころ）
_SYSTEM_COLUMN = {
    "product_id": "product_id",
    "quantity": "quantity_normalized",
    "price": "price_normalized",
    "unit": "unit_canonical",
    "condition": "condition_canonical",
    "status": "status",
    "note": "note_ja",
}

_SYSTEM_VALUES_SQL = (
    "SELECT product_id, quantity_normalized, price_normalized, unit_canonical, "
    "condition_canonical, status, note_ja "
    "FROM public.analysis_results WHERE extraction_item_id = CAST(:eid AS uuid)"
)
_NOTE_LABELS_SQL = "SELECT label_ja FROM public.tcg_note_master WHERE enabled = TRUE AND tenant_id IS NULL"

_INSERT_REPORT_SQL = (
    "INSERT INTO public.analysis_error_reports (extraction_item_id, extraction_job_id, reported_by) "
    "VALUES (CAST(:eid AS uuid), CAST(:jid AS uuid), :by) RETURNING id::text AS id, report_code"
)
_INSERT_FIELD_SQL = (
    "INSERT INTO public.analysis_error_report_fields "
    "(report_id, field_name, system_value, expected_value, expected_missing_product) "
    "VALUES (CAST(:rid AS uuid), :fn, CAST(:sv AS jsonb), CAST(:ev AS jsonb), :emp)"
)
_INSERT_EVENT_SQL = (
    "INSERT INTO public.analysis_error_report_events (report_id, actor, kind, payload) "
    "VALUES (CAST(:rid AS uuid), :actor, :kind, CAST(:payload AS jsonb))"
)
_SET_MESSAGE_ID_SQL = (
    "UPDATE public.analysis_error_reports SET discord_message_id = :mid WHERE id = CAST(:rid AS uuid)"
)


class ReportRejected(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class CreatedReport:
    report_id: str
    report_code: str
    field_names: list[str]


def _json(value: Any) -> str:
    def default(obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(type(obj).__name__)

    return json.dumps(value, ensure_ascii=False, default=default)


# --- 候補の取得元（それぞれの今の取得元を呼ぶだけ） ----------------------------------------


async def _unit_and_status_choices(db: AsyncSession) -> dict[str, list[str]]:
    from app.services.tcg_analyzer_svc import load_status_master, load_unit_canonical_ids  # noqa: PLC0415

    unit_ids = await db.run_sync(load_unit_canonical_ids)
    status_entries = await db.run_sync(load_status_master)
    return override_options(unit_ids, status_entries)


async def _condition_canonicals(db: AsyncSession) -> set[str]:
    return {row["canonical"] for row in await condition_options(db) if row.get("canonical")}


async def _note_labels(db: AsyncSession) -> set[str]:
    return {str(r[0]) for r in (await db.execute(text(_NOTE_LABELS_SQL))).fetchall() if r[0]}


async def _invalid_products(db: AsyncSession, values: list[str]) -> list[str]:
    return await invalid_product_values(db, values)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


async def validate_fields(db: AsyncSession, fields: list[ErrorReportField]) -> None:
    """候補にない値は ReportRejected(422)。"""
    for f in fields:
        name, value = f.field_name, f.expected_value
        if name == "product_id":
            if f.expected_missing_product:
                if value is not None:
                    raise ReportRejected(422, "expected_value must be null when expected_missing_product is true")
            elif value is None or isinstance(value, bool) or await _invalid_products(db, [str(value)]):
                raise ReportRejected(422, f"Unknown product: {value}")
        elif name in ("quantity", "price"):
            if not _is_number(value):
                raise ReportRejected(422, f"{name} must be a number of 0 or more")
        elif name in ("unit", "status"):
            choices = (await _unit_and_status_choices(db))["units" if name == "unit" else "statuses"]
            if not isinstance(value, str) or value not in choices:
                raise ReportRejected(422, f"Unknown {name}: {value}")
        elif name == "condition":
            if not isinstance(value, str) or value not in await _condition_canonicals(db):
                raise ReportRejected(422, f"Unknown condition: {value}")
        elif name == "note":
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                raise ReportRejected(422, "note must be a list of strings")
            labels = await _note_labels(db) if value else set()
            bad = [v for v in value if v not in labels]
            if bad:
                raise ReportRejected(422, f"Unknown note label: {bad[0]}")


async def _read_system_values(db: AsyncSession, extraction_item_id: str) -> dict[str, Any]:
    row = (await db.execute(text(_SYSTEM_VALUES_SQL), {"eid": extraction_item_id})).mappings().first()
    if row is None:
        return {}
    return {name: row[column] for name, column in _SYSTEM_COLUMN.items()}


async def create_report(
    db: AsyncSession, *, extraction_item_id: str, fields: list[ErrorReportField], reported_by: str,
) -> CreatedReport:
    """報告 1 行・項目・created の出来事を 1 トランザクションで保存する。件が無ければ 404、候補にない値は 422。"""
    found = await find_job_of_item(db, extraction_item_id)
    if found is None:
        raise ReportRejected(404, "Extraction item not found")
    await validate_fields(db, fields)
    await set_operator_context(db)
    try:
        system_values = await _read_system_values(db, extraction_item_id)
        row = (
            await db.execute(text(_INSERT_REPORT_SQL), {"eid": extraction_item_id, "jid": found.job_id, "by": reported_by})
        ).mappings().one()
        for f in fields:
            await db.execute(
                text(_INSERT_FIELD_SQL),
                {
                    "rid": row["id"], "fn": f.field_name,
                    "sv": _json(system_values.get(f.field_name)),
                    "ev": _json(f.expected_value),
                    "emp": f.expected_missing_product,
                },
            )
        await db.execute(
            text(_INSERT_EVENT_SQL),
            {"rid": row["id"], "actor": reported_by, "kind": "created", "payload": "{}"},
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await reset_operator_context(db)
    return CreatedReport(report_id=row["id"], report_code=row["report_code"], field_names=[f.field_name for f in fields])


async def _record_notify_result(db: AsyncSession, created: CreatedReport, message_id: str | None, reason: str | None) -> None:
    """通知の結果を保存する（成功: message id と notified。失敗・未設定: notify_failed と理由だけ）。"""
    await set_operator_context(db)
    try:
        if message_id is not None:
            await db.execute(text(_SET_MESSAGE_ID_SQL), {"mid": message_id, "rid": created.report_id})
            kind, payload = "notified", {}
        else:
            kind, payload = "notify_failed", {"reason": reason or "unknown"}
        await db.execute(
            text(_INSERT_EVENT_SQL),
            {"rid": created.report_id, "actor": "system", "kind": kind, "payload": _json(payload)},
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await reset_operator_context(db)


async def notify_report(db: AsyncSession, created: CreatedReport) -> bool:
    """commit の後に呼ぶ。通知の失敗で報告は消さない（例外も握る）。成功なら True。"""
    message_id, reason = await discord_notifier.notify_analysis_error_report(created.report_code, created.field_names)
    try:
        await _record_notify_result(db, created, message_id, reason)
    except Exception:  # noqa: BLE001 - 結果の記録に失敗しても報告は残す
        logger.warning("[error_report] notify result record failed: report=%s", created.report_code, exc_info=True)
    return message_id is not None


__all__ = ["CreatedReport", "ReportRejected", "create_report", "notify_report", "validate_fields"]
