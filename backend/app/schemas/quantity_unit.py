"""
数量単位マスタ Pydantic スキーマ（public.quantity_units テーブル）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class QuantityUnitBase(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    name_en: Optional[str] = Field(default=None, max_length=100)
    display_order: int = Field(default=100, ge=0)
    is_active: bool = True


class QuantityUnitCreate(QuantityUnitBase):
    value: int


class QuantityUnitUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    name_en: Optional[str] = Field(default=None, max_length=100)
    display_order: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    value: Optional[int] = None


class QuantityUnitResponse(QuantityUnitBase):
    id: int
    value: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
