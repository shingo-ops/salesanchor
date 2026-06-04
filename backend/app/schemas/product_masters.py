"""
各種マスタ (public.product_attribute_masters) 用 Pydantic スキーマ。

商品マスタ画面「各種マスタ」タブで編集する選択肢系マスタ:
  product_kind / set_type / rarity / language / unit / hs_code / item / material
（TCGシリーズは public.tcg_type_master 側で管理するため対象外）

すべて require_super_admin 経由で書込される public schema のマスタ。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# UI から編集可能な属性キー（DB の attribute 列と一致）
VALID_ATTRIBUTES = {
    "product_kind",
    "set_type",
    "rarity",
    "language",
    "unit",
    "hs_code",
    "item",
    "material",
}


class ProductAttributeMasterBase(BaseModel):
    attribute: str = Field(min_length=1, max_length=40)
    code: Optional[str] = Field(default=None, max_length=100)
    label_ja: str = Field(min_length=1, max_length=255)
    label_en: Optional[str] = Field(default=None, max_length=255)
    sort_order: int = Field(default=100, ge=0, le=100000)
    is_active: bool = True

    @field_validator("attribute")
    @classmethod
    def _validate_attribute(cls, v: str) -> str:
        if v not in VALID_ATTRIBUTES:
            raise ValueError(
                f"attribute must be one of {sorted(VALID_ATTRIBUTES)}"
            )
        return v


class ProductAttributeMasterCreate(ProductAttributeMasterBase):
    pass


class ProductAttributeMasterUpdate(BaseModel):
    # attribute は不変（区分の付け替えは不可）。表示名・コード・並び順・有効フラグのみ更新可。
    code: Optional[str] = Field(default=None, max_length=100)
    label_ja: Optional[str] = Field(default=None, min_length=1, max_length=255)
    label_en: Optional[str] = Field(default=None, max_length=255)
    sort_order: Optional[int] = Field(default=None, ge=0, le=100000)
    is_active: Optional[bool] = None


class ProductAttributeMasterResponse(ProductAttributeMasterBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
