"""
PARITY-03 Phase 3 Stage 3: 解析レビュー手動修正保存 API。

エンドポイント:
  POST /api/v1/tcg/items/{extraction_item_id}/corrections

認証: require_super_admin（tenant_004 専用）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.models import User
from app.services.item_corrections_svc import save_corrections

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic スキーマ
# ---------------------------------------------------------------------------


class CorrectionField(BaseModel):
    field_name: str
    system_value: str = ""
    human_value: str


class SaveCorrectionsRequest(BaseModel):
    source_message_id: str
    fields: list[CorrectionField]


class SaveCorrectionsResponse(BaseModel):
    ok: bool
    saved: int


# ---------------------------------------------------------------------------
# POST /tcg/items/{extraction_item_id}/corrections
# ---------------------------------------------------------------------------


@router.post(
    "/tcg/items/{extraction_item_id}/corrections",
    response_model=SaveCorrectionsResponse,
    summary="解析レビュー手動修正保存（PARITY-03 Phase 3 Stage 3）",
)
async def save_item_corrections(
    extraction_item_id: str,
    body: SaveCorrectionsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> SaveCorrectionsResponse:
    non_empty = [
        {"field_name": f.field_name, "system_value": f.system_value, "human_value": f.human_value}
        for f in body.fields
        if f.human_value.strip()
    ]
    result = await save_corrections(
        db,
        extraction_item_id=extraction_item_id,
        source_message_id=body.source_message_id,
        fields=non_empty,
        corrected_by=current_user.email,
    )
    return SaveCorrectionsResponse(ok=True, saved=result["saved"])
