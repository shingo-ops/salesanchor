"""最高管理者の消費税率の API（ADR-1061 便2-2a。design.md §3-4 tax_rates・§3-4b・§8 A15・A31）。

GET    /api/v1/super-admin/tax-rates            一覧（適用日の新しい順）と今日（日本時間）
POST   /api/v1/super-admin/tax-rates            行を足す
DELETE /api/v1/super-admin/tax-rates/{rate_id}  まだ始まっていない行だけ消す

決まり:
- 足す行の適用日は、今ある最も新しい行の適用日より後で、かつ明日（日本時間）以降。表が空のときだけ過去の日付も通す。
- 適用日が今日（日本時間）以前の行は消せない。過去の行を直す口は作らない。
- public.tax_rates は FORCE RLS。書き込みは app.is_operator='true' のときだけ通る。印はハンドラの中だけ張り、
  finally で戻す（super_admin_suppliers.py の _operator_writes と同じ寿命。接続に残らない根拠は database.py の ADR-1070）。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin, reset_operator_context, set_operator_context
from app.database import get_db
from app.models import User
from app.services.time import JST

router = APIRouter(prefix="/super-admin/tax-rates", tags=["super-admin"])

_COLS = "id, rate_percent, effective_from, created_at"


class TaxRateOut(BaseModel):
    id: int
    rate_percent: Decimal = Field(description="消費税率（%）。例 10.00")
    effective_from: date = Field(description="この日から使う（日本時間の日付）")
    created_at: datetime


class TaxRateListOut(BaseModel):
    rates: list[TaxRateOut]
    today: date = Field(description="サーバーの今日（日本時間）。画面はこれより後の行だけに削除を出す")


class TaxRateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rate_percent: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    effective_from: date


def _today_jst() -> date:
    return datetime.now(JST).date()


def _sqlstate(exc: IntegrityError) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


@router.get("", response_model=TaxRateListOut, dependencies=[Depends(require_super_admin)])
async def list_tax_rates(db: AsyncSession = Depends(get_db)) -> TaxRateListOut:
    rows = (
        await db.execute(text(f"SELECT {_COLS} FROM public.tax_rates ORDER BY effective_from DESC"))
    ).mappings().all()
    return TaxRateListOut(rates=[TaxRateOut(**row) for row in rows], today=_today_jst())


async def _latest_effective_from(db: AsyncSession) -> date | None:
    """今ある最も新しい適用日（表が空なら None）。"""
    return (await db.execute(text("SELECT max(effective_from) FROM public.tax_rates"))).scalar_one()


@router.post("", response_model=TaxRateOut, status_code=status.HTTP_201_CREATED)
async def create_tax_rate(
    body: TaxRateIn,
    user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> TaxRateOut:
    today = _today_jst()
    latest = await _latest_effective_from(db)
    if latest is not None and (body.effective_from <= latest or body.effective_from <= today):
        raise HTTPException(status_code=422, detail="tax_rate.effective_from_invalid")
    try:
        await set_operator_context(db)
        row = (
            await db.execute(
                text(
                    "INSERT INTO public.tax_rates (rate_percent, effective_from, created_by_user_id) "
                    f"VALUES (:rate_percent, :effective_from, :user_id) RETURNING {_COLS}"
                ),
                {"rate_percent": body.rate_percent, "effective_from": body.effective_from, "user_id": user.id},
            )
        ).mappings().one()
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if _sqlstate(exc) == "23505":
            raise HTTPException(status_code=409, detail="tax_rate.effective_from_taken") from exc
        raise
    except Exception:
        await db.rollback()
        raise
    finally:
        await reset_operator_context(db)
    return TaxRateOut(**row)


@router.delete(
    "/{rate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(require_super_admin)],
)
async def delete_tax_rate(rate_id: int, db: AsyncSession = Depends(get_db)) -> Response:
    effective_from = (
        await db.execute(text("SELECT effective_from FROM public.tax_rates WHERE id = :id"), {"id": rate_id})
    ).scalar_one_or_none()
    if effective_from is None:
        raise HTTPException(status_code=404, detail="tax_rate.not_found")
    if effective_from <= _today_jst():
        raise HTTPException(status_code=409, detail="tax_rate.not_deletable")
    try:
        await set_operator_context(db)
        deleted = (
            await db.execute(text("DELETE FROM public.tax_rates WHERE id = :id"), {"id": rate_id})
        ).rowcount
        if deleted != 1:
            raise RuntimeError(f"tax_rates delete affected {deleted} rows")
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await reset_operator_context(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
