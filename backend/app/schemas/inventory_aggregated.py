"""テナント向け在庫集計エンドポイント GET /inventory/aggregated のレスポンス schema。

応答に含めないフィールド (境界):
  - supplier_name, reason, reason_category, raw offer data
タブ分割:
  - products.tcg_type を基準。?category= で絞り込み可。
列 (cells キー):
  - "Case" / "Sealed box" / "No shrink box" / "Damaged sealed box"
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ConditionCell(BaseModel):
    price: int | None = Field(default=None, description="集計後最良単価 (円)。")
    quantity: int | None = Field(default=None, description="集計後数量。")


class AggregatedRow(BaseModel):
    series: str = Field(description="商品名 (products.name)。")
    tcg_type: str | None = Field(default=None, description="TCG 種別 (products.tcg_type)。タブ分割キー。")
    cells: dict[str, ConditionCell] = Field(
        default_factory=dict,
        description=(
            "状態別集計。キー例: 'Sealed box' / 'Case' / 'No shrink box' / 'Damaged sealed box'。"
            "該当なし列は含まれない (null ではなくキーごと省略)。"
        ),
    )


class InventoryAggregatedResponse(BaseModel):
    tabs: list[str] = Field(description="存在する tcg_type の一覧 (重複なし、昇順)。")
    rows: list[AggregatedRow] = Field(description="series 単位の集計行。")
