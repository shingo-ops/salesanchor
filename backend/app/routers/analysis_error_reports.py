"""
ADR-1025 便1: 解析の誤り報告 API。

エンドポイント:
  POST /api/v1/tcg/items/{extraction_item_id}/error-reports

認証: require_super_admin。保存は 1 トランザクション、Discord 通知は commit の後（失敗しても報告は残る）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.models import User
from app.schemas.analysis_error_report import ErrorReportRequest, ErrorReportResponse
from app.services.analysis_error_report_svc import ReportRejected, create_report, notify_report

router = APIRouter()


@router.post(
    "/tcg/items/{extraction_item_id}/error-reports",
    response_model=ErrorReportResponse,
    status_code=201,
    summary="解析の誤りを報告する（ADR-1025）",
)
async def post_error_report(
    extraction_item_id: str,
    body: ErrorReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> ErrorReportResponse:
    try:
        created = await create_report(
            db, extraction_item_id=extraction_item_id, fields=body.fields, reported_by=current_user.email,
        )
    except ReportRejected as exc:
        raise HTTPException(exc.status, exc.message) from exc
    notified = await notify_report(db, created)
    return ErrorReportResponse(report_code=created.report_code, notified=notified)
