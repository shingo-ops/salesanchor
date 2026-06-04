"""
Super-admin CRUD for public.link_templates（SA-05 リンクテンプレート SSOT）。

API:
  GET    /api/v1/super-admin/link-templates          - 全テンプレート一覧
  GET    /api/v1/super-admin/link-templates/{channel} - 単一テンプレート
  PUT    /api/v1/super-admin/link-templates/{channel} - upsert（create or update）
  DELETE /api/v1/super-admin/link-templates/{channel} - 削除

channel は PRIMARY KEY（VARCHAR(30)）のため、PUT で create/update を一本化する。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db

router = APIRouter()

_COLS = "channel, url_pattern, required_ids, is_verified, notes, updated_at"


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------


class LinkTemplateResponse(BaseModel):
    channel: str
    url_pattern: str
    required_ids: dict
    is_verified: bool
    notes: str | None
    updated_at: str

    model_config = {"from_attributes": True}


class LinkTemplateUpsert(BaseModel):
    url_pattern: str = Field(min_length=1, max_length=500)
    required_ids: dict = Field(description='{"field_name": true} 形式')
    is_verified: bool = False
    notes: str | None = Field(default=None, max_length=500)


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@router.get(
    "/super-admin/link-templates",
    response_model=list[LinkTemplateResponse],
    dependencies=[Depends(require_super_admin)],
    summary="リンクテンプレート一覧（super-admin）",
)
async def list_link_templates(db: AsyncSession = Depends(get_db)) -> list[LinkTemplateResponse]:
    result = await db.execute(
        text(f"SELECT {_COLS} FROM public.link_templates ORDER BY channel")
    )
    return [
        LinkTemplateResponse(
            **{**dict(row), "updated_at": str(row["updated_at"])}
        )
        for row in result.mappings().all()
    ]


@router.get(
    "/super-admin/link-templates/{channel}",
    response_model=LinkTemplateResponse,
    dependencies=[Depends(require_super_admin)],
    summary="リンクテンプレート単一取得（super-admin）",
)
async def get_link_template(
    channel: str,
    db: AsyncSession = Depends(get_db),
) -> LinkTemplateResponse:
    result = await db.execute(
        text(f"SELECT {_COLS} FROM public.link_templates WHERE channel = :channel"),
        {"channel": channel},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"テンプレートが見つかりません: {channel}")
    return LinkTemplateResponse(**{**dict(row), "updated_at": str(row["updated_at"])})


@router.put(
    "/super-admin/link-templates/{channel}",
    response_model=LinkTemplateResponse,
    dependencies=[Depends(require_super_admin)],
    summary="リンクテンプレート upsert（super-admin）",
)
async def upsert_link_template(
    channel: str,
    data: LinkTemplateUpsert,
    db: AsyncSession = Depends(get_db),
) -> LinkTemplateResponse:
    try:
        result = await db.execute(
            text(
                "INSERT INTO public.link_templates "
                "(channel, url_pattern, required_ids, is_verified, notes, updated_at) "
                "VALUES (:channel, :url_pattern, :required_ids::jsonb, :is_verified, :notes, NOW()) "
                "ON CONFLICT (channel) DO UPDATE SET "
                "url_pattern = EXCLUDED.url_pattern, "
                "required_ids = EXCLUDED.required_ids, "
                "is_verified = EXCLUDED.is_verified, "
                "notes = EXCLUDED.notes, "
                "updated_at = NOW() "
                f"RETURNING {_COLS}"
            ),
            {
                "channel": channel,
                "url_pattern": data.url_pattern,
                "required_ids": json.dumps(data.required_ids),
                "is_verified": data.is_verified,
                "notes": data.notes,
            },
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"制約違反: {exc.orig}",
        )
    row = result.mappings().first()
    await db.commit()
    return LinkTemplateResponse(**{**dict(row), "updated_at": str(row["updated_at"])})


@router.delete(
    "/super-admin/link-templates/{channel}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
    summary="リンクテンプレート削除（super-admin）",
)
async def delete_link_template(
    channel: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        text("DELETE FROM public.link_templates WHERE channel = :channel"),
        {"channel": channel},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"テンプレートが見つかりません: {channel}")
    await db.commit()
