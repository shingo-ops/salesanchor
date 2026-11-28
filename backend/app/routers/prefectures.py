from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_tenant
from app.database import get_db
from app.schemas.prefectures import PrefectureResponse

router = APIRouter()


@router.get(
    "/prefectures",
    response_model=list[PrefectureResponse],
    summary="都道府県一覧",
)
async def list_prefectures(
    _tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[PrefectureResponse]:
    result = await db.execute(
        text(
            "SELECT code, name_ja, name_en, sort_order "
            "FROM public.prefectures "
            "ORDER BY sort_order, code"
        )
    )
    return [PrefectureResponse(**dict(row)) for row in result.mappings().all()]
