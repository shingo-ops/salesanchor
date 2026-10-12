"""
フォーマットマスタ Pydantic スキーマ（public.product_formats テーブル）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductFormatBase(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    name_en: Optional[str] = Field(default=None, max_length=100)
    display_order: int = Field(default=100, ge=0)
    is_active: bool = True
    line_id: Optional[int] = None
    type_master_id: Optional[int] = None


class ProductFormatCreate(ProductFormatBase):
    pass


class ProductFormatUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    name_en: Optional[str] = Field(default=None, max_length=100)
    display_order: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    line_id: Optional[int] = None
    type_master_id: Optional[int] = None


class ProductFormatResponse(ProductFormatBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
