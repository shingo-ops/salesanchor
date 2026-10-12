"""型番（品番・マーク）の重なり警告を返す API 応答の型。

判定そのものは app.services.tcg_product_code_collision_svc が唯一の場所。
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CodeCollision(BaseModel):
    """型番が重なった既存の有効商品1件。"""

    product_id: str = Field(description="重なった相手の商品ID（public.products.id の文字列）")
    name: str = Field(description="相手の商品名")
    work_name: str = Field(description="相手の作品名（public.type_master.name_ja）。無ければ空文字")
    matched_value: str = Field(description="重なった相手側の値（保存されている原文）")
    matched_field: str = Field(
        description="重なった相手側の項目。product_code または mark"
    )
    suggest_add_to_this: list[str] = Field(
        description="この商品の除外ワードに足すことを勧める語（相手の名前全体と型番でない検索ワード）"
    )
    suggest_add_to_other: list[str] = Field(
        description="相手の除外ワードに足すことを勧める語（この商品の名前全体と型番でない検索ワード）"
    )
    already_excluded_by_this: list[str] = Field(
        description="この商品の除外ワードのうち、相手に既に当たっている語"
    )
    already_excluded_by_other: list[str] = Field(
        description="相手の除外ワードのうち、この商品に既に当たっている語"
    )


class ProductCreateResult(BaseModel):
    """商品の新規登録の応答。保存は型番の重なりでは止めない。"""

    ok: bool = Field(description="登録できたか。重複候補で止めたときは false")
    product_id: str | None = Field(default=None, description="登録した商品のID。失敗時は null")
    code: str | None = Field(default=None, description="失敗理由のコード（DUPLICATE_CANDIDATE など）")
    candidates: list[dict[str, Any]] | None = Field(
        default=None, description="重複候補（ok が false のときだけ）"
    )
    code_collisions: list[CodeCollision] = Field(
        default_factory=list, description="型番が重なった既存商品の一覧。重なりが無ければ空"
    )


class ProductDetailSaveResult(BaseModel):
    """商品詳細の保存後の応答。保存は型番の重なりでは止めない。"""

    model_config = ConfigDict(extra="allow")

    product: dict[str, Any] = Field(description="保存後の商品の内容")
    revision: str = Field(description="保存後の版を表す指紋")
    lookups: dict[str, Any] = Field(description="分類の選択肢")
    code_collisions: list[CodeCollision] = Field(
        description="保存後の型番が重なった既存商品の一覧。重なりが無ければ空"
    )
