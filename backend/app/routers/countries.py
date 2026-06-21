from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_tenant
from app.database import get_db
from app.schemas.countries import CountryResponse

router = APIRouter()


@router.get(
    "/countries",
    response_model=list[CountryResponse],
    summary="国マスタ一覧",
)
async def list_countries(
    _tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[CountryResponse]:
    result = await db.execute(
        text(
            "SELECT code, name, dial_code, is_active "
            "FROM public.countries "
            "WHERE is_active = TRUE "
            "ORDER BY name, code"
        )
    )
    return [CountryResponse(**dict(row)) for row in result.mappings().all()]
