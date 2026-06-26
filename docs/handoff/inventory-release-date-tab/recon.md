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
- `backend/app/routers/inventory_offers.py:96` — `_VIEW_SELECT` の SELECT 開始。末尾は `p.category, p.mark, p.tcg_type` で `p.release_date` 未選択（`backend/app/routers/inventory_offers.py:107`）。
- `backend/app/routers/inventory_offers.py:121` — `_SORT_COLUMNS` 定義。name〜offered_at の10列のみで release_date エントリなし（`backend/app/routers/inventory_offers.py:133`）。
- `backend/app/routers/inventory_offers.py:192` — sort Query。`default="name"`・pattern に release_date を含まない。
- `backend/app/routers/inventory_offers.py:296` — ORDER BY 構築。`{sort_col} {order_dir} NULLS LAST, i.id ASC`。NULLS LAST 既存のため発売日NULLは末尾・変更不要。
- `backend/app/routers/inventory_offers.py:177` — tcg_type クエリパラメータ定義（`default=None`）。
- `backend/app/routers/inventory_offers.py:216` — tcg_type の WHERE 適用（`p.tcg_type = :tcg_type`）。既存・変更不要。

## フロント（frontend/src/pages/inventory/InventoryPage.tsx）
- `frontend/src/pages/inventory/InventoryPage.tsx:18` — `InventoryRow` interface 開始。supplier_name / tcg_type あり、release_date フィールドなし（`frontend/src/pages/inventory/InventoryPage.tsx:35`）。
- `frontend/src/pages/inventory/InventoryPage.tsx:90` — sortField 初期値 `useState("name")`。
- `frontend/src/pages/inventory/InventoryPage.tsx:91` — sortDir 初期値 `useState("asc")`。
- `frontend/src/pages/inventory/InventoryPage.tsx:154` — params に sort/order を set（tcg_type は現状 set していない）。
- `frontend/src/pages/inventory/InventoryPage.tsx:199` — 種別マスタ取得 `GET /products/tcg-types` → tcgTypes を state 保持。
- `frontend/src/pages/inventory/InventoryPage.tsx:626` — sortTh ヘッダ群（列クリックでソート）。
- `frontend/src/pages/inventory/InventoryPage.tsx:657` — tcg_type の badge 表示。

## 種別マスタ（backend/app/routers/products.py）
- `backend/app/routers/products.py:259` — `GET /products/tcg-types` 定義開始。`SELECT code, name_ja FROM public.tcg_type_master WHERE is_active ORDER BY sort_order, code`（`backend/app/routers/products.py:287`）。
- 先頭 = `pokemon_booster_box`（sort_order=10・表示名「ポケモンカード」）→ 初期タブに使用。

## 発売日カラムの実在（migrations/082_extend_products_box_attributes.sql）
- `migrations/082_extend_products_box_attributes.sql:18` — `ADD COLUMN IF NOT EXISTS release_date DATE`。
- `migrations/082_extend_products_box_attributes.sql:47` — `CREATE INDEX idx_products_release_date ON public.products (release_date DESC)`。
- → 本番 products に release_date は実在。新規migration不要。

## ☆優先提供者の不在（migrations/007_add_phase3_tenant_tables.sql）
- `migrations/007_add_phase3_tenant_tables.sql:1` — suppliers テーブルは id/name/contact_name/email/is_active のみ。priority/star/favorite カラムなし。
- → ☆優先提供者は本テーマ対象外・別イニシアチブ。

## ギャップ結論
- 発売日順: products.release_date 実在。API が SELECT/_SORT_COLUMNS/pattern に未対応＝API小改修3点＋フロント既定変更で実現可（migration不要）。
- タブ: `?tcg_type=` は既存。種別一覧も取得済み＝フロントにタブUI＋params送信を足すだけ。
- ☆: suppliers に優先カラムなし＝別テーマ。
