from __future__ import annotations

"""
自社在庫（own_inventory）用 Pydantic スキーマ。

ADR SA-04/05: A在庫（テナント専用）の CRUD + 2段階引当 API スキーマ。

変更履歴:
  2026-06-04: 初版作成（SA-Foundation PR#6）
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


_STATUS_VALUES = Literal["active", "inactive", "sold_out"]


class OwnInventoryCreate(BaseModel):
    product_id: int = Field(ge=1)
    physical_qty: int = Field(default=0, ge=0)
    reserved_qty: int = Field(default=0, ge=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    condition: str | None = Field(default=None, max_length=50)
    status: _STATUS_VALUES = Field(default="active")
    note_ja: str | None = Field(default=None, max_length=5000)
    note_en: str | None = Field(default=None, max_length=5000)
    antique_ledger_id: int | None = None


class OwnInventoryUpdate(BaseModel):
    unit_price: Decimal | None = Field(default=None, ge=0)
    condition: str | None = Field(default=None, max_length=50)
    status: _STATUS_VALUES | None = None
    note_ja: str | None = Field(default=None, max_length=5000)
    note_en: str | None = Field(default=None, max_length=5000)
    antique_ledger_id: int | None = None


class OwnInventoryResponse(BaseModel):
    id: int
    tenant_id: int
    product_id: int
    physical_qty: int
    reserved_qty: int
    available_qty: int | None
    unit_price: Decimal | None
    condition: str | None
    status: str
    note_ja: str | None
    note_en: str | None
    antique_ledger_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QtyRequest(BaseModel):
    qty: int = Field(ge=1, description="操作対象の数量（1以上）")
