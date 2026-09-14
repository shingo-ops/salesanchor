"""
TCG 診断 API。

エンドポイント:
  GET /api/v1/tcg/diagnostics/{key}
    認証: require_super_admin
    key は許可リストに完全一致する場合のみ実行。
    SQL はすべてコード内に固定（外部入力から SQL を組み立てない）。
    SELECT のみ。INSERT / UPDATE / DELETE / DDL を実行しない。

  POST /api/v1/tcg/diagnostics/retry-extraction
    認証: require_super_admin
    body: { "job_ids": [...] } または { "scope": "pending" }
    対象の extraction_jobs を status='pending' に戻し、Celery タスクを再エンキューする。
    レスポンス: { "enqueued": 件数, "skipped": 件数 }
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from pydantic import BaseModel, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.services.tcg_diagnostics_svc import get_allowed_keys, retry_extraction, run_diagnostic
from app.services.tcg_extraction_record_svc import read_attempts

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic スキーマ
# ---------------------------------------------------------------------------


class DiagnosticsResponse(BaseModel):
    ok: bool
    key: str
    rows: list[dict]


class RetryExtractionRequest(BaseModel):
    job_ids: list[str] | None = None
    scope: Literal["pending"] | None = None

    @model_validator(mode="after")
    def check_exactly_one(self) -> "RetryExtractionRequest":
        has_ids = self.job_ids is not None
        has_scope = self.scope is not None
        if has_ids == has_scope:
            raise ValueError("Specify exactly one of 'job_ids' or 'scope'.")
        if has_ids and len(self.job_ids) > 50:  # type: ignore[arg-type]
            raise ValueError("'job_ids' must contain at most 50 entries.")
        return self


class RetryExtractionResponse(BaseModel):
    enqueued: int
    skipped: int


# ---------------------------------------------------------------------------
# エンドポイント
# ---------------------------------------------------------------------------


@router.get(
    "/tcg/diagnostics/{key}",
    response_model=DiagnosticsResponse,
    summary="TCG 診断クエリ（固定 SQL 方式・super_admin 限定）",
)
async def get_diagnostics(
    key: str = Path(description="診断キー（例: suppliers）"),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> DiagnosticsResponse:
    allowed = get_allowed_keys()
    if key not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown key '{key}'. Allowed keys: {allowed}",
        )
    rows = await run_diagnostic(db, key=key)
    return DiagnosticsResponse(ok=True, key=key, rows=rows)


@router.post(
    "/tcg/diagnostics/retry-extraction",
    response_model=RetryExtractionResponse,
    summary="extraction_jobs を再エンキュー（super_admin 限定）",
)
async def post_retry_extraction(
    body: RetryExtractionRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_super_admin),
) -> RetryExtractionResponse:
    try:
        result = await retry_extraction(
            db,
            job_ids=body.job_ids,
            scope=body.scope,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return RetryExtractionResponse(**result)


@router.get("/tcg/diagnostics/extraction-jobs/{job_id}/attempts")
async def get_extraction_attempts(
    job_id: UUID, response: Response, limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db),
    _user=Depends(require_super_admin),
):
    response.headers["Cache-Control"] = "no-store"
    return await read_attempts(db, str(job_id), limit=limit, offset=offset)


@router.get("/tcg/diagnostics/extraction-jobs/{job_id}/attempts/{attempt_id}")
async def get_extraction_attempt(
    job_id: UUID, attempt_id: UUID, response: Response, db: AsyncSession = Depends(get_db),
    _user=Depends(require_super_admin),
):
    response.headers["Cache-Control"] = "no-store"
    return await read_attempts(db, str(job_id), attempt_id=str(attempt_id))
