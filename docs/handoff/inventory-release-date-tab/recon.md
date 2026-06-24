# recon — inventory-release-date-tab

**対象ADR**: ADR-093
**仕事名**: inventory-release-date-tab（/inventory に発売日順ソート＋tcg_typeタブを追加）
**日付**: 2026-06-24

---

## 目的
既存の全オファー台帳 `/inventory`（ADR-093 で定義された在庫表ビュー）に、
「発売日の新しい順を既定にする」「TCG種別タブで切替（初期=ポケモンカード）」を追加するための現在地把握。
推測を排し、変更対象を file:line で実在引用する。

## バックエンド（backend/app/routers/inventory_offers.py）
- `_VIEW_SELECT` L96-107: SELECT 末尾は `… p.category, p.mark, p.tcg_type`。**p.release_date は未選択**。
- `_SORT_COLUMNS` L121-133: name/category/mark/condition/unit/offer_type/quantity/unit_price/supplier/offered_at の10列。**release_date エントリなし**。
- sort Query L192: `Query(default="name", pattern="^(name|category|…|offered_at)$")`。**release_date は許可外・既定は name**。
- ORDER BY 構築 L296: `f"ORDER BY {sort_col} {order_dir} NULLS LAST, i.id ASC"`。**NULLS LAST 既存＝発売日NULLは末尾になる・変更不要**。
- tcg_type 受け口 L177: `tcg_type: str | None = Query(default=None, max_length=50)`。
- tcg_type WHERE 適用 L216-218: `if tcg_type: conditions.append("p.tcg_type = :tcg_type")`。**既存・変更不要**。

## フロント（frontend/src/pages/inventory/InventoryPage.tsx）
- `InventoryRow` interface L18-35: supplier_name / tcg_type あり。**release_date フィールドなし**。
- sortField 初期 L90: `useState("name")`。
- sortDir 初期 L91: `useState<"asc"|"desc">("asc")`。
- params 組立 L152-176: sort/order/q/category 等を毎回 set。**tcg_type は現状 set していない**。
- 種別マスタ取得 L199-204: `GET /products/tcg-types` → `tcgTypes=[{code,name_ja}]` を**既に取得・state保持**。
- sortTh ヘッダ群 L626-634: 列ヘッダクリックでソート（既存UX）。
- badge表示 L657: tcg_type をラベル表示。

## 種別マスタ（GET /products/tcg-types, backend/app/routers/products.py L259-287）
- `SELECT code, name_ja FROM public.tcg_type_master WHERE is_active ORDER BY sort_order, code`。
- 先頭 = `pokemon_booster_box`（sort_order=10・表示名「ポケモンカード」）→ **初期タブに使用**。
- 末尾 = `other`（900）。pokemon/weiss は migration 20260616 で正規コードへ統合済み。

## 発売日カラムの実在（migrations/082_extend_products_box_attributes.sql）
- L18: `ADD COLUMN IF NOT EXISTS release_date DATE`。
- L47-49: `CREATE INDEX idx_products_release_date ON public.products (release_date DESC) WHERE release_date IS NOT NULL`。
- → **本番 products に release_date は実在**。新規migration不要。

## ギャップ結論
- 発売日順: products.release_date は実在。API が SELECT/_SORT_COLUMNS/pattern に未対応＝**API小改修3点＋フロント既定変更で実現可（migration不要）**。
- タブ: 裏の `?tcg_type=` は既存。種別一覧も取得済み＝**フロントにタブUI＋params送信を足すだけ**。
- ☆優先提供者: suppliers に優先カラムなし（migration 007 確認）＝**本テーマ対象外・別イニシアチブ**。
