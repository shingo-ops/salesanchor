"""ADR-1025 便2: 再解析のあとの照合（同期）。

Celery タスクの中から呼ぶ。再解析そのものは呼び出し側が渡す関数（reanalyze_v102_job）に任せ、ここでは
「報告の項目ごとに期待値と今の値を比べ、events と status に残し、Discord へ送る」だけを行う。
operator フラグはトランザクション内だけ有効（set_config の第 3 引数 true）。commit で自動的に戻る。
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services import discord_notifier

# 便1と同じ SQL・対応表・JSON 変換を使い回す（新しい SQL を書かない）
from app.services.analysis_error_report_svc import _INSERT_EVENT_SQL, _SYSTEM_COLUMN, _SYSTEM_VALUES_SQL, _json

logger = logging.getLogger(__name__)

_OPERATOR_ON_SQL = "SELECT set_config('app.is_operator', 'true', true)"
_REPORT_SQL = (
    "SELECT id::text AS id, report_code, extraction_item_id::text AS extraction_item_id, "
    "extraction_job_id::text AS extraction_job_id, reported_at "
    "FROM public.analysis_error_reports WHERE id = CAST(:rid AS uuid)"
)
_FIELDS_SQL = (
    "SELECT field_name, expected_value, expected_missing_product "
    "FROM public.analysis_error_report_fields WHERE report_id = CAST(:rid AS uuid) ORDER BY id"
)
_PRODUCT_CREATED_SQL = "SELECT created_at FROM public.products WHERE id = :pid"
_SET_STATUS_SQL = "UPDATE public.analysis_error_reports SET status = :st WHERE id = CAST(:rid AS uuid)"


def _same_decimal(expected: Any, actual: Any) -> bool:
    if actual is None or expected is None or isinstance(expected, bool):
        return False
    try:
        return Decimal(str(expected)) == Decimal(str(actual))
    except (InvalidOperation, ValueError):
        return False


def _note_words(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        items: list[Any] = value.split(",")  # 区切りは半角カンマ（tcg_analyzer_svc.build_note_ja）
    elif isinstance(value, list):
        items = value
    else:
        return {repr(value)}
    return {str(w).strip() for w in items if str(w).strip()}


def match_field(
    field_name: str,
    expected: Any,
    actual: Any,
    *,
    expected_missing_product: bool = False,
    reported_at: datetime | None = None,
    product_created_at: datetime | None = None,
) -> bool:
    """項目 1 つの一致判定。"""
    if field_name == "product_id":
        if expected_missing_product:
            if actual is None:
                return True
            return product_created_at is not None and reported_at is not None and product_created_at > reported_at
        if actual is None:
            return False
        try:
            return int(expected) == int(actual)
        except (TypeError, ValueError):
            return False
    if field_name in ("quantity", "price"):
        return _same_decimal(expected, actual)
    if field_name in ("unit", "condition", "status"):
        return actual is not None and expected == actual
    if field_name == "note":
        return _note_words(expected) == _note_words(actual)
    return False


def build_verdict(
    fields: list[dict[str, Any]],
    current: dict[str, Any],
    *,
    reported_at: datetime | None = None,
    product_created_at: datetime | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """(resolved か unresolved, 項目ごとの結果) を返す。全部一致で resolved。"""
    results = []
    for f in fields:
        name = f["field_name"]
        actual = current.get(name)
        ok = match_field(
            name, f["expected_value"], actual,
            expected_missing_product=bool(f.get("expected_missing_product")),
            reported_at=reported_at, product_created_at=product_created_at,
        )
        results.append({"field": name, "expected": f["expected_value"], "actual": actual, "match": ok})
    return ("resolved" if results and all(r["match"] for r in results) else "unresolved"), results


def failure_payload(detail: str) -> dict[str, Any]:
    return {"result": "reanalyze_failed", "detail": detail}


def _record_event(session: Session, report_id: str, actor: str, kind: str, payload: dict[str, Any]) -> None:
    session.execute(text(_INSERT_EVENT_SQL), {"rid": report_id, "actor": actor, "kind": kind, "payload": _json(payload)})


def record_verdict(session: Session, report_id: str, payload: dict[str, Any], status: str) -> None:
    """verified の出来事と status を 1 トランザクションで残す（operator フラグはこの中だけ）。"""
    session.execute(text(_OPERATOR_ON_SQL))
    _record_event(session, report_id, "system", "verified", payload)
    session.execute(text(_SET_STATUS_SQL), {"st": status, "rid": report_id})
    session.commit()


def record_notify_result(session: Session, report_id: str, message_id: str | None, reason: str | None) -> None:
    session.execute(text(_OPERATOR_ON_SQL))
    if message_id is not None:
        _record_event(session, report_id, "system", "notified", {})
    else:
        _record_event(session, report_id, "system", "notify_failed", {"reason": reason or "unknown"})
    session.commit()


def _load(session: Session, report_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    session.execute(text(_OPERATOR_ON_SQL))
    report = session.execute(text(_REPORT_SQL), {"rid": report_id}).mappings().first()
    if report is None:
        session.rollback()
        raise LookupError(f"report not found: {report_id}")
    fields = [dict(r) for r in session.execute(text(_FIELDS_SQL), {"rid": report_id}).mappings().all()]
    session.commit()
    return dict(report), fields


def _read_current(session: Session, report: dict[str, Any], fields: list[dict[str, Any]]) -> tuple[dict[str, Any], datetime | None]:
    row = session.execute(text(_SYSTEM_VALUES_SQL), {"eid": report["extraction_item_id"]}).mappings().first()
    current = {name: row[column] for name, column in _SYSTEM_COLUMN.items()} if row is not None else {}
    created_at = None
    wants_created = any(f["field_name"] == "product_id" and f.get("expected_missing_product") for f in fields)
    if wants_created and current.get("product_id") is not None:
        created = session.execute(text(_PRODUCT_CREATED_SQL), {"pid": current["product_id"]}).first()
        created_at = created[0] if created else None
    return current, created_at


def run_reanalyze_and_verify(
    report_id: str,
    *,
    reanalyze: Callable[[str], dict],
    session_factory: Callable[[], Session],
) -> dict[str, Any]:
    """再解析 → 照合 → events・status → Discord。戻り値は結果の要約（値は含めない）。"""
    session = session_factory()
    try:
        report, fields = _load(session, report_id)
        try:
            outcome = reanalyze(report["extraction_job_id"])
            failed = None if outcome.get("status") == "reanalyzed" else f"status={outcome.get('status')}"
        except Exception as exc:  # noqa: BLE001 - 失敗も unresolved として残す
            logger.exception("[error_report] reanalyze failed: report=%s", report["report_code"])
            failed = type(exc).__name__
        if failed is not None:
            payload, status, result_fields = failure_payload(failed), "unresolved", []
        else:
            current, created_at = _read_current(session, report, fields)
            status, result_fields = build_verdict(
                fields, current, reported_at=report["reported_at"], product_created_at=created_at,
            )
            payload = {"result": status, "fields": result_fields}
        record_verdict(session, report_id, payload, status)
        summary = {"report_code": report["report_code"], "result": payload["result"], "status": status}
        # commit の後に通知する（失敗時も PO が気付けるよう送る）。送れなくても status と events はそのまま
        message_id, reason = discord_notifier.notify_analysis_error_report_verified(
            report["report_code"], payload["result"], result_fields,
        )
        try:
            record_notify_result(session, report_id, message_id, reason)
        except Exception:  # noqa: BLE001
            session.rollback()
            logger.warning("[error_report] notify result record failed: report=%s", report["report_code"], exc_info=True)
        return summary
    finally:
        session.close()


__all__ = ["build_verdict", "failure_payload", "match_field", "record_verdict", "run_reanalyze_and_verify"]
