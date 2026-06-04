"""TenantPolicy Pydantic schemas (ADR-106: 標準エンジン + テナント変数の土台)

テナントごとの在庫集計フィルタ・見積有効期限・通貨・書類言語・
関税ポリシー・発行モードを管理する。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TenantPolicyRead(BaseModel):
    inventory_agg_filter: Literal["none", "cheapest", "balanced"] = "none"
    agg_price_threshold_jpy: int = 0
    agg_qty_threshold: int = 0
    quote_validity_days: int = Field(default=1, ge=1, le=365)
    default_currency: str = Field(default="JPY", max_length=10)
    document_language: str = Field(default="en", max_length=10)
    duty_incoterms: Literal["DAP", "DDU", "DDP"] = "DAP"
    issue_mode: Literal["paypal_auto", "paypal_manual", "pdf", "wise_pdf"] = "pdf"

    model_config = {"from_attributes": True}


class TenantPolicyUpdate(BaseModel):
    inventory_agg_filter: Literal["none", "cheapest", "balanced"] | None = None
    agg_price_threshold_jpy: int | None = None
    agg_qty_threshold: int | None = None
    quote_validity_days: int | None = Field(default=None, ge=1, le=365)
    default_currency: str | None = Field(default=None, max_length=10)
    document_language: str | None = Field(default=None, max_length=10)
    duty_incoterms: Literal["DAP", "DDU", "DDP"] | None = None
    issue_mode: Literal["paypal_auto", "paypal_manual", "pdf", "wise_pdf"] | None = None
