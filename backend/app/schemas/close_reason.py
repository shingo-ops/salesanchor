from __future__ import annotations

"""
成約・失注理由マスタ（close_reasons）用Pydanticスキーマ。

テナントスキーマの close_reasons テーブル定義:
  id, type CHECK('won'/'lost'), label, sort_order, is_active, created_at

作成: 2026-06-13 (PR3 — ADR-138 §D1-2)
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CloseReasonCreate(BaseModel):
    type: str = Field(description="理由区分: 'won' または 'lost'")
    label: str = Field(min_length=1, max_length=100, description="表示ラベル")
    sort_order: int = Field(default=0, description="表示順")

    def model_post_init(self, __context):
        if self.type not in ("won", "lost"):
            raise ValueError("type は 'won' または 'lost' のみ有効です")


class CloseReasonUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=100)
    sort_order: int | None = None
    is_active: bool | None = None


class CloseReasonResponse(BaseModel):
    id: int
    type: str
    label: str
    sort_order: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
