"""買取価格変動アラートルール CRUD API。ADR-157"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db

router = APIRouter()


class AlertRuleBase(BaseModel):
    name: str
    card_game: str | None = None
    shop_code: str | None = None
    product_type: str | None = None
    shop_product_id: uuid.UUID | None = None
    direction: str = Field(default="down", pattern="^(down|up|both)$")
    threshold_pct: float = Field(gt=0, le=100)
    price_grade: str = Field(default="price_s", pattern="^price_(s|a|am|b|c)$")
    is_active: bool = True
    cooldown_minutes: int = Field(default=360, ge=0)


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(AlertRuleBase):
    pass


class AlertRuleResponse(AlertRuleBase):
    id: uuid.UUID
    last_notified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AlertRuleListResponse(BaseModel):
    items: list[AlertRuleResponse]
    total: int


@router.get(
    "/buyback-alerts",
    response_model=AlertRuleListResponse,
    tags=["buyback-alerts"],
)
async def list_alert_rules(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    """アラートルール一覧"""
    await db.execute(text("SET LOCAL app.is_operator = 'true'"))
    rows = (
        await db.execute(
            text("""
                SELECT id, name, card_game, shop_code, product_type, shop_product_id,
                       direction, threshold_pct, price_grade, is_active,
                       last_notified_at, cooldown_minutes, created_at, updated_at
                FROM public.buyback_alert_rules
                ORDER BY created_at DESC
            """)
        )
    ).mappings().all()
    items = [AlertRuleResponse(**dict(r)) for r in rows]
    return AlertRuleListResponse(items=items, total=len(items))


@router.post(
    "/buyback-alerts",
    response_model=AlertRuleResponse,
    status_code=201,
    tags=["buyback-alerts"],
)
async def create_alert_rule(
    body: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    """アラートルール作成"""
    await db.execute(text("SET LOCAL app.is_operator = 'true'"))
    row = (
        await db.execute(
            text("""
                INSERT INTO public.buyback_alert_rules
                    (name, card_game, shop_code, product_type, shop_product_id,
                     direction, threshold_pct, price_grade, is_active, cooldown_minutes)
                VALUES
                    (:name, :card_game, :shop_code, :product_type, :shop_product_id,
                     :direction, :threshold_pct, :price_grade, :is_active, :cooldown_minutes)
                RETURNING id, name, card_game, shop_code, product_type, shop_product_id,
                          direction, threshold_pct, price_grade, is_active,
                          last_notified_at, cooldown_minutes, created_at, updated_at
            """),
            body.model_dump(),
        )
    ).mappings().first()
    await db.commit()
    return AlertRuleResponse(**dict(row))


@router.put(
    "/buyback-alerts/{rule_id}",
    response_model=AlertRuleResponse,
    tags=["buyback-alerts"],
)
async def update_alert_rule(
    rule_id: uuid.UUID,
    body: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    """アラートルール更新"""
    await db.execute(text("SET LOCAL app.is_operator = 'true'"))
    row = (
        await db.execute(
            text("""
                UPDATE public.buyback_alert_rules
                SET name = :name, card_game = :card_game, shop_code = :shop_code,
                    product_type = :product_type, shop_product_id = :shop_product_id,
                    direction = :direction, threshold_pct = :threshold_pct,
                    price_grade = :price_grade, is_active = :is_active,
                    cooldown_minutes = :cooldown_minutes,
                    updated_at = now()
                WHERE id = :rule_id
                RETURNING id, name, card_game, shop_code, product_type, shop_product_id,
                          direction, threshold_pct, price_grade, is_active,
                          last_notified_at, cooldown_minutes, created_at, updated_at
            """),
            {**body.model_dump(), "rule_id": rule_id},
        )
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    await db.commit()
    return AlertRuleResponse(**dict(row))


@router.delete(
    "/buyback-alerts/{rule_id}",
    status_code=204,
    tags=["buyback-alerts"],
)
async def delete_alert_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    """アラートルール削除"""
    await db.execute(text("SET LOCAL app.is_operator = 'true'"))
    result = await db.execute(
        text("DELETE FROM public.buyback_alert_rules WHERE id = :rule_id"),
        {"rule_id": rule_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    await db.commit()
