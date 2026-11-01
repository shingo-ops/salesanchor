"""GET /analytics/lead-conversion-factors の応答の型（カード A §3。カード B と共有・変えない）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LeadConversionExcluded(BaseModel):
    by_status: int
    other_values: int
    no_inbound: int
    no_outbound: int
    no_reply_pair: int
    no_sales_form: int
    missing_scale_or_type: int


class LeadConversionFactorItem(BaseModel):
    key: str
    odds_ratio: float | None
    ci_low: float | None
    ci_high: float | None
    significant: bool
    computable: bool


class LeadConversionFactorsResponse(BaseModel):
    status: Literal["ok", "insufficient", "not_computable"]
    included_count: int
    won_count: int
    lost_count: int
    required_per_item: int
    item_count: int
    excluded: LeadConversionExcluded
    items: list[LeadConversionFactorItem]
