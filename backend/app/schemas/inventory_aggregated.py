"""テナント向け在庫集計エンドポイント GET /inventory/aggregated のレスポンス schema。

応答に含めないフィールド (境界):
  - supplier_name, reason, reason_category, raw offer data
タブ分割:
  - work_id の作品の符号（type_master.code） を基準。?category= で絞り込み可。
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
    work_code: str | None = Field(default=None, description="作品の符号（products.work_id → type_master.code）。タブ分割キー。")
    cells: dict[str, ConditionCell] = Field(
        default_factory=dict,
        description=(
            "状態別集計。キー例: 'Sealed box' / 'Case' / 'No shrink box' / 'Damaged sealed box'。"
            "該当なし列は含まれない (null ではなくキーごと省略)。"
        ),
    )


class InventoryAggregatedResponse(BaseModel):
    tabs: list[str] = Field(description="存在する work_code の一覧 (重複なし、昇順)。")
    rows: list[AggregatedRow] = Field(description="series 単位の集計行。")


# invoice-create-portfolio R2（design-v2 §3-4）: 請求書・見積の商品行の在庫。値段と数の形は ConditionCell を使う。
class DraftInventoryCategory(BaseModel):
    code: str = Field(description="中分類の符号（type_master.code）。")
    name_ja: str | None = Field(default=None, description="中分類の日本語名（type_master.name_ja）。")


class DraftInventoryItem(BaseModel):
    product_id: int
    name: str = Field(description="商品名 (products.name)。")
    name_en: str | None = None
    mark: str | None = Field(default=None, description="型番 (products.mark)。")
    work_code: str | None = None
    box_weight_kg: float | None = Field(default=None, description="BOX の重さ（荷姿の表）。")
    case_weight_kg: float | None = Field(default=None, description="ケースの重さ（荷姿の表）。")
    cells: dict[str, ConditionCell] = Field(default_factory=dict, description="状態別の集計。在庫表と同じ。")


class DraftInventoryResponse(BaseModel):
    categories: list[DraftInventoryCategory] = Field(description="在庫のある中分類（sort_order 順）。category で絞らない。")
    items: list[DraftInventoryItem] = Field(description="商品ごとの在庫（商品の番号の順）。category で絞る。")
