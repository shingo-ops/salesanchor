"""キャリアアダプタ Protocol と共通データクラス（ADR-128）。

将来的に DHL・ヤマト等のキャリアを追加する際も、この Protocol に準拠した
実装クラスを作成するだけでルーター側の変更を最小化できる。

変更履歴:
  2026-06-11: 初版（ADR-128）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Protocol, runtime_checkable


@dataclass
class SurchargeDetail:
    """追加料金の内訳。"""

    description: str
    amount: Decimal
    currency: str


@dataclass
class RateQuote:
    """送料見積もり結果。"""

    service_type: str
    service_name: str
    total_net_charge: Decimal
    currency: str
    transit_days: Optional[int] = None
    delivery_timestamp: Optional[str] = None
    surcharges: list[SurchargeDetail] = field(default_factory=list)


@dataclass
class ShipmentResult:
    """ラベル発行結果。"""

    tracking_number: str
    label_bytes: bytes          # Base64 decode 済み PDF バイト列
    confirmed_fee: Decimal
    confirmed_currency: str
    surcharges: list[SurchargeDetail] = field(default_factory=list)


@dataclass
class PickupResult:
    """集荷予約結果。"""

    confirmation_code: str
    location_code: Optional[str] = None  # Express のみ


@runtime_checkable
class CarrierShipAdapter(Protocol):
    """キャリアシッピングアダプタの Protocol 定義。"""

    carrier_code: str
    dimensions_required: bool

    async def create_shipment(self, *args, **kwargs) -> ShipmentResult:
        """ラベルを発行する。"""
        ...

    async def create_pickup(self, *args, **kwargs) -> PickupResult:
        """集荷を予約する。"""
        ...


__all__ = [
    "SurchargeDetail",
    "RateQuote",
    "ShipmentResult",
    "PickupResult",
    "CarrierShipAdapter",
]
