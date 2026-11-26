"""書類に載せる会社情報（国内用・海外用）の型（ADR-1061 便2-2c2b。design.md §3-4b）。名前は DB の列名と同じ。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

IssuerRegion = Literal["domestic", "overseas"]


class IssuerProfileUpdate(BaseModel):
    company_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=255)
    country_code: str | None = Field(default=None, max_length=2)
    postal_code: str | None = Field(default=None, max_length=10)
    prefecture_code: str | None = Field(default=None, max_length=2)
    state_region: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    address1: str | None = Field(default=None, max_length=255)
    address2: str | None = Field(default=None, max_length=5000)
    phone: str | None = Field(default=None, max_length=16)
    is_invoice_registered: bool = False
    registration_number: str | None = Field(default=None, max_length=14)


class IssuerProfileResponse(BaseModel):
    region: IssuerRegion
    company_name: str
    email: str | None = None
    website: str | None = None
    country_code: str
    postal_code: str | None = None
    prefecture_code: str | None = None
    state_region: str | None = None
    city: str
    address1: str
    address2: str | None = None
    phone: str | None = None
    is_invoice_registered: bool
    registration_number: str | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class LegacyIssuerValues(BaseModel):
    """旧来の会社情報の表の6欄（読むだけ）。"""

    company_name: str | None = None
    company_name_en: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None


class IssuerProfilesResponse(BaseModel):
    domestic: IssuerProfileResponse | None = None
    overseas: IssuerProfileResponse | None = None
    legacy: LegacyIssuerValues | None = None
