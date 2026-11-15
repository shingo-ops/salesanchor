"""関税の額の決まりの入出力の形（invoice-create-portfolio 便B・design.md §3-3・§3-6）。

表は migrations/20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql（会社ごとのスキーマ）。
- 送料の会社（carrier）は前後の空白を除き小文字にして持つ。空の文字は「どの会社でも」（NULL）。
- 根拠の URL は必須（ADR-095 付録1-4）。
- 基準（base）の3つは表の CHECK と同じ。並びの正本はこの DutyBase だけ（画面は /admin/duty-rules/options で受け取る）。
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DutyBase = Literal["subtotal", "subtotal_shipping", "subtotal_shipping_prior"]
DUTY_BASES: tuple[str, ...] = get_args(DutyBase)


def _strip(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


def _blank_to_none(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class DutyComponentIn(BaseModel):
    """関税の中身の1行（例: 関税・DDP 手数料・MPF）。"""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., min_length=1)
    base: DutyBase
    rate_pct: Decimal = Field(..., ge=0, max_digits=8, decimal_places=4)
    min_amount: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=2)
    max_amount: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=2)
    amount_currency: str | None = Field(None, pattern=r"^[A-Z]{3}$")

    @field_validator("label", mode="before")
    @classmethod
    def _strip_label(cls, value: Any) -> Any:
        return _strip(value)

    @field_validator("min_amount", "max_amount", "amount_currency", mode="before")
    @classmethod
    def _blank_amounts(cls, value: Any) -> Any:
        return _blank_to_none(value)

    @model_validator(mode="after")
    def _check_amounts(self) -> "DutyComponentIn":
        if self.min_amount is not None and self.max_amount is not None and self.min_amount > self.max_amount:
            raise ValueError("min_amount must be <= max_amount")
        if (self.min_amount is not None or self.max_amount is not None) and self.amount_currency is None:
            raise ValueError("amount_currency is required with min_amount or max_amount")
        return self


class DutyRuleIn(BaseModel):
    """関税の額の決まり1件（足す・直すで同じ形。中身の行は丸ごと置き換える）。"""

    model_config = ConfigDict(extra="forbid")

    destination_country_code: str = Field(..., pattern=r"^[A-Z]{2}$")
    carrier: str | None = Field(None, max_length=50)
    label: str = Field(..., min_length=1)
    effective_from: datetime.date
    effective_to: datetime.date | None = None
    source_url: str = Field(..., pattern=r"^https?://\S+$")
    note: str | None = None
    is_active: bool = True
    components: list[DutyComponentIn] = Field(..., min_length=1, max_length=20)

    @field_validator("destination_country_code", mode="before")
    @classmethod
    def _upper_country(cls, value: Any) -> Any:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("carrier", mode="before")
    @classmethod
    def _normalize_carrier(cls, value: Any) -> Any:
        # 表の CHECK（carrier = lower(btrim(carrier)) AND carrier <> ''）と同じ形にそろえる（design.md §3-3 第7版）
        if isinstance(value, str):
            value = value.strip().lower()
            return value or None
        return value

    @field_validator("label", "source_url", mode="before")
    @classmethod
    def _strip_text(cls, value: Any) -> Any:
        return _strip(value)

    @field_validator("note", "effective_to", mode="before")
    @classmethod
    def _blank(cls, value: Any) -> Any:
        return _blank_to_none(value)

    @model_validator(mode="after")
    def _check_period(self) -> "DutyRuleIn":
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be >= effective_from")
        return self


class DutyComponentRead(BaseModel):
    id: int
    sort_order: int
    label: str
    base: str
    rate_pct: str
    min_amount: str | None = None
    max_amount: str | None = None
    amount_currency: str | None = None


class DutyRuleRead(BaseModel):
    id: int
    destination_country_code: str
    carrier: str | None = None
    label: str
    effective_from: datetime.date
    effective_to: datetime.date | None = None
    source_url: str
    note: str | None = None
    is_active: bool
    created_at: datetime.datetime | None = None
    updated_at: datetime.datetime | None = None
    components: list[DutyComponentRead]


class DutyRuleOptions(BaseModel):
    """画面の選択肢（正本はそれぞれ tenant_settings・為替の表・DutyBase）。"""

    duty_incoterms: str
    currencies: list[str]
    bases: list[str]
