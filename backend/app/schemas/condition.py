"""
テナント用状態マスタ Pydantic スキーマ（conditions テーブル）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ConditionBase(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    canonical: str = Field(min_length=1, max_length=100)
    app_kubun: Optional[str] = None
    is_active: bool = True
    priority: Optional[int] = None
    search_kw: str = ""
    exclude_kw: str = ""
    match_type: str = "KEYWORD"
    effect: str = "OUTPUT"


class ConditionCreate(ConditionBase):
    pass


class ConditionUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    canonical: Optional[str] = Field(default=None, min_length=1, max_length=100)
    app_kubun: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    search_kw: Optional[str] = None
    exclude_kw: Optional[str] = None
    match_type: Optional[str] = None
    effect: Optional[str] = None


class ConditionResponse(ConditionBase):
    id: int
    tenant_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConditionAliasCreate(BaseModel):
    condition_id: int
    alias_text: str = Field(min_length=1, max_length=500)
    lang: str = Field(default="ja", min_length=2, max_length=5)


class ConditionAliasResponse(BaseModel):
    id: int
    condition_id: int
    alias_text: str
    lang: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
