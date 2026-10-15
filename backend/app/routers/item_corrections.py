"""
PARITY-03 Phase 3 Stage 3: 解析レビュー手動修正保存 API。

エンドポイント:
  POST /api/v1/tcg/items/{extraction_item_id}/corrections
  POST /api/v1/tcg/items/{extraction_item_id}/review-ack   （v102 の件の「このままで良い」）

v102 の件に判断を保存したら、その投稿のシステム段のやり直し → 配信の予約を Celery に積む（v6 の件は積まない）。

認証: require_super_admin（tenant_004 専用）
"""
from __future__ import annotations

import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.models import User
from app.services.item_corrections_svc import save_corrections
from app.services.review_reason_codes_svc import load_review_reason_codes
from app.services.tcg_condition_review_svc import save_condition_review
from app.services.v102_human_decisions_svc import (
    FIELD_PRODUCT_ID,
    MAX_NOTE_LENGTH,
    OVERRIDE_PREFIX,
    DecisionRejected,
    find_job_of_item,
    invalid_product_values,
    item_rejection,
    normalize_ack_codes,
    override_options,
    product_rejection,
    review_ack_rejection,
    save_review_ack,
    save_review_ack_revoke,
    save_value_override,
    v102_job_id_of_item,
)
from app.tasks.tcg_extraction import enqueue_v102_reanalyze

logger = logging.getLogger(__name__)

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
    condition_id: str = Field(pattern=r"^[1-9][0-9]{0,9}$")


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
        if any(field.field_name.startswith(OVERRIDE_PREFIX) for field in self.fields):
            raise ValueError("override_ field names are reserved (use /value-override)")
        return self


class SaveCorrectionsResponse(BaseModel):
    ok: bool
    saved: int
    condition_review: ConditionReviewResponse | None = None


class ReviewAckRequest(BaseModel):
    source_message_id: UUID
    codes: list[str] = Field(min_length=1)

    @field_validator("codes")
    @classmethod
    def clean_codes(cls, codes: list[str]) -> list[str]:
        cleaned = normalize_ack_codes(code.strip() for code in codes)
        if not cleaned or any(not code for code in cleaned):
            raise ValueError("codes must be non-empty strings")
        return cleaned


class ReviewAckResponse(BaseModel):
    ok: bool
    saved: int


async def _enqueue_reanalyze_if_v102(db: AsyncSession, extraction_item_id: str) -> None:
    """保存後に呼ぶ。その件の投稿が v102 のときだけやり直しを積む（v6 は積まない）。失敗しても保存は成功のまま。"""
    try:
        job_id = await v102_job_id_of_item(db, extraction_item_id)
        if job_id is not None:
            enqueue_v102_reanalyze(job_id)
    except Exception:  # noqa: BLE001
        logger.warning("[item_corrections] v102 reanalyze trigger failed: item=%s", extraction_item_id, exc_info=True)


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
            raise HTTPException(404, "Condition review item not found") from exc
        result = await save_condition_review(
            db, extraction_item_id=extraction_item_id, source_message_id=body.source_message_id,
            request=body.condition_review.model_dump(mode="json"), corrected_by=current_user.email,
        )
        if result["saved"] > 0:
            await _enqueue_reanalyze_if_v102(db, extraction_item_id)
        return SaveCorrectionsResponse(ok=True, **result)
    non_empty = [
        {"field_name": f.field_name, "system_value": f.system_value, "human_value": f.human_value}
        for f in body.fields
        if f.human_value.strip()
    ]
    v102_job_id = await v102_job_id_of_item(db, extraction_item_id)
    if v102_job_id is not None:  # v102 の件だけ、無効な商品の判断は何も書かずに 422（v6 の件の挙動は変えない）
        bad = await invalid_product_values(db, [f["human_value"] for f in non_empty if f["field_name"] == FIELD_PRODUCT_ID])
        rejected = product_rejection(bad)
        if rejected is not None:
            raise HTTPException(rejected.status, rejected.message)
    result = await save_corrections(
        db,
        extraction_item_id=extraction_item_id,
        source_message_id=body.source_message_id,
        fields=non_empty,
        corrected_by=current_user.email,
    )
    if result["saved"] > 0 and v102_job_id is not None:
        enqueue_v102_reanalyze(v102_job_id)
    return SaveCorrectionsResponse(ok=True, saved=result["saved"])


# ---------------------------------------------------------------------------
# POST /tcg/items/{extraction_item_id}/review-ack
# ---------------------------------------------------------------------------


@router.post(
    "/tcg/items/{extraction_item_id}/review-ack",
    response_model=ReviewAckResponse,
    summary="v102 の要確認を「このままで良い」として記録する",
)
async def save_item_review_ack(
    extraction_item_id: str,
    body: ReviewAckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> ReviewAckResponse:
    found = await find_job_of_item(db, extraction_item_id)
    rejected = review_ack_rejection(body.codes, await load_review_reason_codes(db), found, str(body.source_message_id))
    if rejected is not None:
        raise HTTPException(rejected.status, rejected.message)
    saved = await save_review_ack(
        db, extraction_item_id=extraction_item_id, source_message_id=str(body.source_message_id),
        codes=body.codes, corrected_by=current_user.email,
    )
    enqueue_v102_reanalyze(found.job_id)
    return ReviewAckResponse(ok=True, saved=saved)


# ---------------------------------------------------------------------------
# POST /tcg/items/{extraction_item_id}/review-ack/revoke
# ---------------------------------------------------------------------------


class ReviewAckRevokeRequest(BaseModel):
    source_message_id: UUID


@router.post(
    "/tcg/items/{extraction_item_id}/review-ack/revoke",
    response_model=ReviewAckResponse,
    summary="v102 の「このままで良い」（確認済み）を取り消す",
)
async def revoke_item_review_ack(
    extraction_item_id: str,
    body: ReviewAckRevokeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> ReviewAckResponse:
    found = await find_job_of_item(db, extraction_item_id)
    rejected = item_rejection(found, str(body.source_message_id))
    if rejected is not None:
        raise HTTPException(rejected.status, rejected.message)
    saved = await save_review_ack_revoke(
        db, extraction_item_id=extraction_item_id, source_message_id=str(body.source_message_id),
        corrected_by=current_user.email,
    )
    if saved == 0:
        raise HTTPException(409, "No review-ack to revoke")
    enqueue_v102_reanalyze(found.job_id)
    return ReviewAckResponse(ok=True, saved=saved)


# ---------------------------------------------------------------------------
# POST /tcg/items/{extraction_item_id}/value-override
# GET  /tcg/review/value-options
# ---------------------------------------------------------------------------


class ValueOverrideRequest(BaseModel):
    source_message_id: UUID
    field: Literal["quantity", "price", "unit", "note", "status"]
    value: str = Field(max_length=MAX_NOTE_LENGTH)


class ValueOptionsResponse(BaseModel):
    units: list[str]
    statuses: list[str]


@router.post(
    "/tcg/items/{extraction_item_id}/value-override",
    response_model=ReviewAckResponse,
    summary="v102 の件の数量・単価・単位・メモ・販売状況を人の値に直す",
)
async def save_item_value_override(
    extraction_item_id: str,
    body: ValueOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> ReviewAckResponse:
    found = await find_job_of_item(db, extraction_item_id)
    rejected = item_rejection(found, str(body.source_message_id))
    if rejected is not None:
        raise HTTPException(rejected.status, rejected.message)
    try:
        saved = await save_value_override(
            db, extraction_item_id=extraction_item_id, source_message_id=str(body.source_message_id),
            field=body.field, value=body.value, corrected_by=current_user.email,
        )
    except DecisionRejected as exc:
        raise HTTPException(exc.status, exc.message) from exc
    enqueue_v102_reanalyze(found.job_id)
    return ReviewAckResponse(ok=True, saved=saved)


@router.get(
    "/tcg/review/value-options",
    response_model=ValueOptionsResponse,
    summary="数量・単価などを直す欄の選択肢（単位・販売状況）",
)
async def get_value_options(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> ValueOptionsResponse:
    from app.services.tcg_analyzer_svc import load_status_master, load_unit_canonical_ids  # noqa: PLC0415

    unit_ids = await db.run_sync(load_unit_canonical_ids)
    status_entries = await db.run_sync(load_status_master)
    return ValueOptionsResponse(**override_options(unit_ids, status_entries))
