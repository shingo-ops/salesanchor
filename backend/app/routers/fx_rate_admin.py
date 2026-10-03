"""
為替レート SSOT API ルーター。

GET    /api/v1/fx-rates/{currency}        — 現在レート取得（ログイン認証のみ）
POST   /api/v1/super-admin/fx-rate/refresh — 手動即時更新（require_super_admin）

設計（ADR-148 2026-10-03 追記・PR-B）:
  - public.app_fx_rate_history を SSOT とする（追記専用）。Celery Beat が1日2回追記する。
  - 読み取りは `ORDER BY fetched_at DESC LIMIT 1` で最新行を返す。レスポンス形状
    （FxRateResponse: currency/rate_jpy/fetched_at/updated_at）は維持し、`updated_at`
    は履行テーブルの `created_at`（当行がテーブルに挿入された時刻）を転用する。
  - public.app_fx_rates への読み書きは廃止（過去レートが UPSERT で上書きされ失われるため）。
    テーブル自体は当面残置（DROPはPO本人のGO必須、ADR-148追記）。
  - 読み取りは全ログイン済みユーザーが可（為替は秘匿でない）。
  - 書き込み（手動更新）は require_super_admin のみ。operator コンテキストの明示セットは
    従来から行っていない（PR-B は書き込み先テーブルの切替のみで、この挙動は変更しない）。
  - invoices.py の fetch_fx_rate（ライブ取得）は別系統のまま。このルーターは触らない。
  - 2026-10-01: 読み取りパスを /fx-rate/{currency} から /fx-rates/{currency} に変更。
    invoices.py の fetch_fx_rate が同一パス /fx-rate/{currency} を先に登録しており、
    このルーターの読み取りエンドポイントが到達不能になっていたため（ADR-148 追記参照）。
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
    "/fx-rates/{currency}",
    response_model=FxRateResponse,
    tags=["fx-rate"],
)
async def get_fx_rate(
    currency: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """public.app_fx_rate_history から指定通貨の最新レートを返す。

    (currency, fetched_at) で追記される履歴テーブルから、最新の1行を
    `ORDER BY fetched_at DESC LIMIT 1` で取得する。行が存在しない場合は 404 を返す
    （app_fx_rates 時代と同じ 404 挙動）。
    """
    result = await db.execute(
        text(
            "SELECT currency, rate_jpy, fetched_at, created_at "
            "FROM public.app_fx_rate_history "
            "WHERE currency = :cur "
            "ORDER BY fetched_at DESC LIMIT 1"
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
        # created_at（当行が履歴テーブルに挿入された時刻）を updated_at として転用する。
        # レスポンス形状は app_fx_rates 時代と同一に保つ（フロントの型を変えないため）。
        updated_at=row["created_at"].isoformat(),
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
    """USD/JPY レートを即時取得して public.app_fx_rate_history に追記する（手動更新）。

    外部 API 障害時は 503 を返す。(currency, fetched_at) が既存行と重複する場合は
    ON CONFLICT DO NOTHING（追記専用・上書きしない）。
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
            INSERT INTO public.app_fx_rate_history (currency, rate_jpy, fetched_at)
            VALUES ('USD', :rate, :fetched)
            ON CONFLICT (currency, fetched_at) DO NOTHING
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
            "SELECT currency, rate_jpy, fetched_at, created_at "
            "FROM public.app_fx_rate_history WHERE currency = 'USD' "
            "ORDER BY fetched_at DESC LIMIT 1"
        )
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=500, detail="追記後の行取得に失敗しました")

    return FxRateResponse(
        currency=row["currency"],
        rate_jpy=float(row["rate_jpy"]),
        fetched_at=row["fetched_at"].isoformat(),
        updated_at=row["created_at"].isoformat(),
    )
