"""Pydantic schemas for `/super-admin/inventory-offers/*` endpoints.

spec.md v1.3 F11 / AC11.5:
  - 中央 admin が public.inventory (仕入元現在オファー) を一覧 / 編集 / 追加 / 削除する
  - 入力 condition は raw_condition + 軸列へ投影して 1 行に集約
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

InventoryStatus = Literal["in_stock", "out_of_stock", "reserved", "archived"]
InventorySource = Literal["manual", "discord_parsed", "csv_import", "f6_approved"]
InventoryUnit = Literal["piece", "pack", "box", "case", "set"]
# 区分: 在庫(in_stock) / 予約(pre_order)（ADR-093 Phase 3）
InventoryOfferType = Literal["in_stock", "pre_order"]
# 発送日: 発売日発送 / 発売1日前 / 発売2日前 / その他（予約品のみ。在庫品は None）
InventoryShipTiming = Literal["on_release", "1day_before", "2day_before", "other"]

# 状態の正規 16 値 (migration 089)。
# 入力 condition の正規化と軸投影に使う。
InventoryCondition = Literal[
    "shrink",      # シュリンク付き  (box 主)
    "no_shrink",   # シュリンクなし  (box 主)
    "sealed",      # 未開封         (case / set 主)
    "damage",      # ダメージあり    (box / case / set 共用)
    "unsearched",  # 未サーチ        (pack 主)
    "searched",    # サーチ済み      (pack 主)
    "graded",      # 鑑定品         (piece 主)
    "grade_s",     # S 評価         (piece 主)
    "grade_a",     # A 評価         (piece 主)
    "grade_b",     # B 評価         (piece 主)
    "grade_c",     # C 評価         (piece 主)
    "grade_d",     # D 評価         (piece 主)
    "junk",        # ジャンク        (piece 主)
    "bulk",        # バルク          (piece 主)
    "normal",      # ノーマル        (piece 主)
    "unknown",     # 不明            (全単位)
]


class InventoryOfferBase(BaseModel):
    """共通フィールド (新規作成 / 更新で共有)。"""

    supplier_id: int = Field(..., gt=0)
    product_id: int = Field(..., gt=0)
    # 状態。入力 condition として受け、保存時は raw_condition + 軸列へ投影する。
    # migration 089 で 16 値に正規化・CHECK 制約追加済み。
    condition: InventoryCondition = Field(...)
    quantity: int = Field(..., ge=0)
    unit_price: int = Field(..., ge=0)
    # 数量の単位。正規値: piece / pack / box / case / set。
    unit: InventoryUnit | None = Field(default=None)
    # 区分(在庫/予約) と 発送日（予約品のみ）。UNIQUE キーの discriminator（ADR-093 Phase 3）。
    offer_type: InventoryOfferType = "in_stock"
    ship_timing: InventoryShipTiming | None = Field(default=None)
    status: InventoryStatus = "in_stock"
    notes_ja: str | None = Field(default=None, max_length=2000)
    notes_en: str | None = Field(default=None, max_length=2000)
    expires_at: datetime | None = None
    source: InventorySource = "manual"


class InventoryOfferCreate(InventoryOfferBase):
    """新規 INSERT 用。UNIQUE 衝突は 409 を返す。"""


class InventoryOfferUpdate(BaseModel):
    """PATCH 用。すべて任意。supplier_id / product_id / condition は変更不可
    （状態変更したい場合は DELETE + INSERT 相当で再作成）。"""

    quantity: int | None = Field(default=None, ge=0)
    unit_price: int | None = Field(default=None, ge=0)
    unit: InventoryUnit | None = Field(default=None)
    offer_type: InventoryOfferType | None = None
    ship_timing: InventoryShipTiming | None = Field(default=None)
    status: InventoryStatus | None = None
    notes_ja: str | None = Field(default=None, max_length=2000)
    notes_en: str | None = Field(default=None, max_length=2000)
    expires_at: datetime | None = None


class InventoryOfferResponse(InventoryOfferBase):
    """list / detail レスポンス。supplier_name / product 情報を join 結果として埋める。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    offered_at: datetime
    created_at: datetime
    updated_at: datetime

    # レスポンスでは condition を str に緩める（非正規値を含む既存データで500にならないよう）
    # 書き込み側（Create/Update）は InventoryCondition のまま維持、保存時は raw_condition + 軸列に投影
    condition: str = Field(...)
    # 区分/発送日もレスポンスは str に緩める（旧データ/将来値で500を避ける）
    offer_type: str = "in_stock"
    ship_timing: str | None = None

    # JOIN 結果 (admin UI 表示用、任意)
    supplier_name: str | None = None
    product_code: str | None = None
    product_name: str | None = None
    # ADR-093: オファー画面の列順を在庫表に揃えるため products 由来の表示列を付与（読取専用）
    name_en: str | None = None
    category: str | None = None
    mark: str | None = None
    work_code: str | None = None


class InventoryOfferListResponse(BaseModel):
    """ページング付き一覧。"""

    items: list[InventoryOfferResponse]
    total: int
    page: int
    per_page: int


# ---------------------------------------------------------------------------
# 最終ユーザー向け在庫表ビュー (GET /inventory) — 読み取り専用・参考画像準拠の列
# ADR-093 Phase 2: 在庫表を public.inventory（仕入元オファー）ベースに作替え。
# ---------------------------------------------------------------------------


class InventoryRow(BaseModel):
    """在庫表ビューの 1 明細行（商品×仕入元×状態）。読み取り専用。

    admin 専用フィールド（notes/source/status）は含めない。最終ユーザー（各クライアントの
    営業担当ロール以上）が閲覧 + 見積/請求/発注作成するための列のみ。
    condition は migration 089 の 16 値だが、旧データ混入時も 500 にしないため str で受ける
    （inventory_offers 500 の教訓）。
    """

    id: str                           # 行の識別（LINE 解析の analysis_results.id。まとめた行は組の先頭の行）
    product_id: int
    product_name: str | None = None   # 商品名（= public.products.name = name_ja）
    name_en: str | None = None        # 英語名（任意表示）
    category: str | None = None       # カテゴリ（例: Pokemon）
    mark: str | None = None           # マーク（例: M4）
    condition: str                    # 状態（LINE 解析の canonical をそのまま。GAS 在庫一覧と同じ英語）
    unit: str | None = None           # 形態（LINE 解析の unit_canonical をそのまま）
    offer_type: str | None = "in_stock"  # 区分 在庫/予約。status から写す。対応外の status は None
    ship_timing: str | None = None    # 常に None（発送は ship_ja）
    supplier_id: int
    supplier_name: str | None = None  # 仕入元
    unit_price: int                   # 単価
    quantity: int | None = None       # 数量（空の行は None）
    work_code: str | None = None       # 作品の符号（products.work_id → type_master.code）
    offered_at: datetime              # 掲載時間（LINE の投稿日時）
    posted_at: datetime | None = None  # LINE の投稿日時（offered_at と同じ値）
    release_date: str | None = None   # 発売日
    note_ja: str | None = None        # 備考
    ship_ja: str | None = None        # 発送
    status: str | None = None         # LINE 解析の status（In Stock / Pre-order など。値のまま）
    merged_count: int = 1             # まとめた行数（まとめない行は 1）
    badge_cheapest: bool = False      # 同じ商品・ステータス・状態のまとまり（絞り込み後・ページ前）で最安か（ADR-1014 改訂 2026-10-19（3））
    badge_most_stock: bool = False    # 同じ商品・ステータス・状態のまとまり（絞り込み後・ページ前）で在庫最多か（ADR-1014 改訂 2026-10-19（3））
    extraction_item_ids: list[str] = []  # 行の元になった extraction_items.id（まとめた行は組の全件。解析パネル用）


class InventorySupplierFacet(BaseModel):
    """在庫表フィルタ用の仕入元ファセット（ADR-093 Phase 4）。

    在庫オファーに登場する仕入元のみ。フィルタ ポップアップの「仕入元 表示/非表示」
    チェックボックス候補に使う（ページング・他フィルタに依存せず全候補を返す）。
    """

    id: int
    name: str | None = None


class InventoryRawTextItem(BaseModel):
    """在庫表スライドの原文タブ用。返す項目はこの4つだけ（gemini・system・要約・送信者は出さない）。"""

    extraction_item_id: str
    raw_text: str
    line_start: int | None = None
    line_end: int | None = None


class InventoryRawTextsResponse(BaseModel):
    items: list[InventoryRawTextItem]


class InventoryListResponse(BaseModel):
    """在庫表ビューのページング付き一覧。"""

    items: list[InventoryRow]
    total: int
    page: int
    per_page: int
    # ADR-093 Phase 4: フィルタ UI 用の仕入元一覧（在庫オファーに存在する仕入元）。
    suppliers: list[InventorySupplierFacet] = []
    # ADR-093 在庫表改修: フィルタ UI 用のカテゴリー一覧（在庫オファーに存在するカテゴリー）。
    categories: list[str] = []
    # ADR-093 表示条件: 在庫オファーに存在する状態(condition)・形態(unit)の一覧（複数選択 UI 用）。
    conditions: list[str] = []
    units: list[str] = []
    # LINE の投稿から何時間以内の行を出しているか（0 は絞らない・None は配信設定なしで空）。
    window_hours: int | None = None
    fresh_window_hours: int = 24  # 「24時間以内」トグルの窓（時間）。値は tcg_distribution_svc.FRESH_WINDOW_HOURS
    # いま出ている行（まとめ前・絞り込み前）のうち最も早く時間の枠から外れる行まで、あと何秒か。
    # 負は既に外れている。None は外れる行なし。
    next_expiry_in_seconds: int | None = None


__all__ = [
    "InventoryCondition",
    "InventoryOfferBase",
    "InventoryOfferCreate",
    "InventoryOfferUpdate",
    "InventoryOfferResponse",
    "InventoryOfferListResponse",
    "InventoryRow",
    "InventorySupplierFacet",
    "InventoryListResponse",
    "InventoryStatus",
    "InventorySource",
    "InventoryUnit",
    "InventoryOfferType",
    "InventoryShipTiming",
]
