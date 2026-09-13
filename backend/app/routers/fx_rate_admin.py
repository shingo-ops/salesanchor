"""
為替レート SSOT API ルーター。

GET    /api/v1/fx-rate/{currency}         — 現在レート取得（ログイン認証のみ）
POST   /api/v1/super-admin/fx-rate/refresh — 手動即時更新（require_super_admin）

設計:
  - public.app_fx_rates を SSOT とする。Celery Beat が1日2回 UPSERT する。
  - 読み取りは全ログイン済みユーザーが可（為替は秘匿でない）。
  - 書き込み（手動更新）は require_super_admin のみ。
  - invoices.py の fetch_fx_rate（ライブ取得）は別系統のまま。このルーターは触らない。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_super_admin
from app.database import get_db
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


class FxRateResponse(BaseModel):
    currency: str
    rate_jpy: float
    fetched_at: str
    updated_at: str


@router.get(
    "/fx-rate/{currency}",
    response_model=FxRateResponse,
    tags=["fx-rate"],
)
async def get_fx_rate(
    currency: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """public.app_fx_rates から指定通貨の現在レートを返す。

    行が存在しない場合は 404 を返す。
    """
    result = await db.execute(
        text(
            "SELECT currency, rate_jpy, fetched_at, updated_at "
            "FROM public.app_fx_rates "
            "WHERE currency = :cur"
        ),
        {"cur": currency.upper()},
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"為替レートが未取得です: {currency.upper()}",
        )
    return FxRateResponse(
        currency=row["currency"],
        rate_jpy=float(row["rate_jpy"]),
        fetched_at=row["fetched_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.post(
    "/super-admin/fx-rate/refresh",
    response_model=FxRateResponse,
    tags=["super-admin"],
    dependencies=[Depends(require_super_admin)],
)
async def refresh_fx_rate(
    db: AsyncSession = Depends(get_db),
):
    """USD/JPY レートを即時取得して public.app_fx_rates に UPSERT する（手動更新）。

    外部 API 障害時は 503 を返す。
    """
    from app.services.fx_rate import get_fx_rate as _get_fx_rate

    snapshot = _get_fx_rate("USD")
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="外部 API から為替レートを取得できませんでした。しばらく待ってから再試行してください。",
        )

    rate_jpy = snapshot["rate"]
    fetched_at = snapshot["fetched_at"]

    await db.execute(
        text(
            """
            INSERT INTO public.app_fx_rates (currency, rate_jpy, fetched_at)
            VALUES ('USD', :rate, :fetched)
            ON CONFLICT (currency) DO UPDATE
                SET rate_jpy   = EXCLUDED.rate_jpy,
                    fetched_at = EXCLUDED.fetched_at
            """
        ),
        {"rate": str(rate_jpy), "fetched": fetched_at},
    )
    await db.commit()

    logger.info(
        "[fx_rate_admin] 手動更新完了: USD/JPY = %.4f (fetched_at=%s)",
        rate_jpy,
        fetched_at,
    )

    result = await db.execute(
        text(
            "SELECT currency, rate_jpy, fetched_at, updated_at "
            "FROM public.app_fx_rates WHERE currency = 'USD'"
        )
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=500, detail="UPSERT 後の行取得に失敗しました")

    return FxRateResponse(
        currency=row["currency"],
        rate_jpy=float(row["rate_jpy"]),
        fetched_at=row["fetched_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )
