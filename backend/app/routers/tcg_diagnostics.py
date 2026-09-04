"""
TCG 診断 API。

エンドポイント:
  GET /api/v1/tcg/diagnostics/{key}
    認証: require_super_admin
    key は許可リストに完全一致する場合のみ実行。
    SQL はすべてコード内に固定（外部入力から SQL を組み立てない）。
    SELECT のみ。INSERT / UPDATE / DELETE / DDL を実行しない。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.services.tcg_diagnostics_svc import get_allowed_keys, run_diagnostic

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic スキーマ
# ---------------------------------------------------------------------------


class DiagnosticsResponse(BaseModel):
    ok: bool
    key: str
    rows: list[dict]


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
