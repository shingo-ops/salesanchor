"""
PARITY-03 Phase 3 Stage 3: 解析レビュー手動修正保存 API。

エンドポイント:
  POST /api/v1/tcg/items/{extraction_item_id}/corrections

認証: require_super_admin（tenant_004 専用）
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.models import User
from app.services.item_corrections_svc import save_corrections
from app.services.tcg_condition_review_svc import save_condition_review

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic スキーマ
# ---------------------------------------------------------------------------


class CorrectionField(BaseModel):
    field_name: str
    system_value: str = ""
    human_value: str


class ConditionReviewRequest(BaseModel):
    request_id: UUID
    expected_review_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: Literal["confirm", "correct"]
    condition_id: UUID


class ConditionReviewResponse(BaseModel):
    condition_id: str | None
    canonical: str | None
    needs_review: bool
    review_reasons: str
    review_version: str
    replayed: bool


class SaveCorrectionsRequest(BaseModel):
    source_message_id: str
    fields: list[CorrectionField] = Field(default_factory=list)
    condition_review: ConditionReviewRequest | None = None

    @model_validator(mode="after")
    def validate_route(self) -> SaveCorrectionsRequest:
        if self.condition_review is not None:
            if "fields" in self.model_fields_set:
                raise ValueError("fields and condition_review cannot be combined")
            UUID(self.source_message_id)
        if any(field.field_name == "condition_review" for field in self.fields):
            raise ValueError("condition_review is reserved")
        return self


class SaveCorrectionsResponse(BaseModel):
    ok: bool
    saved: int
    condition_review: ConditionReviewResponse | None = None


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
    if body.condition_review is not None:
        try:
            UUID(extraction_item_id)
        except ValueError as exc:
            from fastapi import HTTPException
            raise HTTPException(404, "Condition review item not found") from exc
        result = await save_condition_review(
            db, extraction_item_id=extraction_item_id, source_message_id=body.source_message_id,
            request=body.condition_review.model_dump(mode="json"), corrected_by=current_user.email,
        )
        return SaveCorrectionsResponse(ok=True, **result)
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
