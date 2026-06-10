from __future__ import annotations

"""
配送ゾーン・配送料金用Pydanticスキーマ。

変更履歴:
  2026-04-17: 初版作成（Phase 2）
  2026-06-09: ADR-125 — FedEx ライブ見積もり対応
                source / transit_days / live_error フィールド追加
                ShippingCalcRequest に origin_country_code を追加
  2026-06-10: ADR-125 仕様追補 — 郵便番号（任意）+ rate_precision フラグ追加
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ShippingZoneCreate(BaseModel):
    country_code: str = Field(min_length=2, max_length=3)
    country_name: str = Field(min_length=1, max_length=100)
    carrier: str = Field(min_length=1, max_length=50)
    zone: str = Field(min_length=1, max_length=20)


class ShippingZoneResponse(BaseModel):
    id: int
    country_code: str
    country_name: str
    carrier: str
    zone: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ShippingRateCreate(BaseModel):
    carrier: str = Field(min_length=1, max_length=50)
    zone: str = Field(min_length=1, max_length=20)
    weight_min: Decimal = Field(ge=0, max_digits=10, decimal_places=3)
    weight_max: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
    price: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    currency: str = Field(default="JPY", max_length=10)


class ShippingRateResponse(BaseModel):
    id: int
    carrier: str
    zone: str
    weight_min: Decimal
    weight_max: Decimal
    price: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShippingCalcRequest(BaseModel):
    country_code: str = Field(min_length=2, max_length=3)
    weight_kg: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
    carrier: Optional[str] = Field(default=None, max_length=50)
    # ADR-125: FedEx ライブ見積もり時の発送元国コード（FedEx 選択時に必須）
    origin_country_code: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=3,
        description="FedEx ライブ見積もり時の発送元国コード。carrier='fedex' 指定時に必須。",
    )
    # ADR-125 仕様追補 2026-06-10: 郵便番号（任意）
    # 指定あり → rate_precision='exact'、未指定 → 代表値で補完 + rate_precision='approximate'
    origin_postal_code: Optional[str] = Field(
        default=None,
        max_length=20,
        description="発送元郵便番号（任意）。未指定時は国コードから代表値を補完し rate_precision='approximate' を返す。",
    )
    destination_postal_code: Optional[str] = Field(
        default=None,
        max_length=20,
        description="届け先郵便番号（任意）。未指定時は国コードから代表値を補完し rate_precision='approximate' を返す。",
    )


class ShippingCalcResult(BaseModel):
    carrier: str
    zone: str
    fee: Decimal
    currency: str
    # ADR-125: 見積もりの出所（D5 — 暗黙フォールバック禁止）
    source: Literal["static", "fedex_live"] = "static"
    # ADR-125: FedEx ライブ見積もり時の追加フィールド
    service_type: Optional[str] = None      # 例: FEDEX_INTERNATIONAL_PRIORITY
    service_name: Optional[str] = None      # 例: FedEx International Priority
    transit_days: Optional[int] = None      # 配達日数
    delivery_timestamp: Optional[str] = None  # ISO 8601 配達予定


class ShippingCalcResponse(BaseModel):
    results: list[ShippingCalcResult]
    cheapest: Optional[ShippingCalcResult]
    # ADR-125 D5: FedEx ライブAPI呼び出しに失敗した場合の明示エラー
    # None = 成功または FedEx 非選択
    # 文字列 = エラーメッセージ（この場合 results は空または静的データ）
    live_error: Optional[str] = None
    # ADR-125 仕様追補 2026-06-10: 見積もり精度フラグ
    # 'exact'       : 届け先郵便番号を指定して取得した正確な見積もり
    # 'approximate' : 郵便番号未指定・代表値で補完した概算見積もり
    # None          : FedEx ライブ見積もり以外（static / 未連携エラー等）
    rate_precision: Optional[Literal["exact", "approximate"]] = None
