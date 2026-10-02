"""
決済手数料設定（public.payment_fee_settings）用 Pydantic スキーマ。

§D01: PO承認2026-10-02
パターン: public + NULLパターン（public.unitsと同一方式）
  tenant_id IS NULL = 共用デフォルト（運営者管理）
  tenant_id = X    = テナント独自設定
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PaymentFeeSettingBase(BaseModel):
    service: str = Field(min_length=1, max_length=30)
    fee_type: str = Field(min_length=1, max_length=50)
    rate_pct: Decimal = Field(default=Decimal(0), ge=0, max_digits=8, decimal_places=4)
    fixed_amount: Decimal = Field(default=Decimal(0), ge=0, max_digits=14, decimal_places=2)
    threshold: Optional[Decimal] = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    threshold_rule: Optional[str] = Field(default=None, max_length=10)
    currency: str = Field(default="JPY", min_length=3, max_length=3)
    effective_from: date
    effective_to: Optional[date] = None
    source_url: Optional[str] = None
    note: Optional[str] = None


class PaymentFeeSettingCreate(PaymentFeeSettingBase):
    pass


class PaymentFeeSettingUpdate(BaseModel):
    service: Optional[str] = Field(default=None, min_length=1, max_length=30)
    fee_type: Optional[str] = Field(default=None, min_length=1, max_length=50)
    rate_pct: Optional[Decimal] = Field(default=None, ge=0, max_digits=8, decimal_places=4)
    fixed_amount: Optional[Decimal] = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    threshold: Optional[Decimal] = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    threshold_rule: Optional[str] = Field(default=None, max_length=10)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    source_url: Optional[str] = None
    note: Optional[str] = None


class PaymentFeeSettingResponse(PaymentFeeSettingBase):
    id: int
    tenant_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
