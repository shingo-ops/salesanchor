"""
商品カテゴリマスタ Pydantic スキーマ（tcg_product_categories テーブル）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductCategoryBase(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    display_name: str = Field(min_length=1, max_length=255)
    kubun_type: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = True


class ProductCategoryCreate(ProductCategoryBase):
    pass


class ProductCategoryUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    kubun_type: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = None


class ProductCategoryResponse(ProductCategoryBase):
    id: int
    tenant_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
