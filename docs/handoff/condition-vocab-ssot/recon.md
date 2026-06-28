# recon — condition-vocab-ssot (Phase 1: products.condition / products.unit コード除去)

**仕事名**: condition-vocab-ssot  
**日付**: 2026-06-28  
**対象ADR**: ADR-093  
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/products.py:1` | `_UPDATABLE_COLUMNS` から `"condition"` / `"unit"` 除去済み |
| `backend/app/routers/inventory_offers.py:1` | `COALESCE(NULLIF(i.unit,''),p.unit)` → `NULLIF(i.unit,'')` 7箇所変換済み |
| `backend/app/routers/inventory_search.py:1` | `InventorySearchCandidate` 構築から condition/unit 除去済み |
| `backend/app/routers/super_admin_inbound.py:1` | `_PARSED_ITEMS_CTE` 縮小・`rep` クエリ削除・INSERT 列縮小済み |
| `backend/app/schemas/product.py:1` | `ProductCreate`/`ProductUpdate`/`ProductResponse` から condition/unit 削除済み |
| `backend/app/schemas/discord_inbound.py:1` | `InboundProductCandidate` から unit/condition フィールド削除済み |
| `backend/app/schemas/inventory_search.py:1` | `InventorySearchCandidate` から condition/unit フィールド削除済み |
| `backend/app/services/inventory_axes.py:1` | `build_condition_filter_clause` 既定値を `NULLIF(i.unit,'')` に変更済み |
| `backend/app/services/inventory_search.py:1` | SQL SELECT・`SearchCandidate` dataclass・mapping から condition/unit 除去済み |
| `frontend/src/components/InventorySearchBar.tsx:1` | `InventorySearchCandidate` interface から condition/unit 削除済み |
| `frontend/src/pages/quote-create/QuoteCreatePage.tsx:1` | `appendFromSearch` を condition/unit null 固定に変更済み |
| `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:1` | `appendFromSearch` を condition/unit null 固定に変更済み |
| `frontend/src/pages/products/ProductEditPage.tsx:1` | unit セレクター JSX 削除・form state/payload から condition/unit 除去済み |
| `frontend/src/pages/products/products.types.ts:1` | `Product`・`FormState`・`emptyForm` から condition/unit 削除済み |
| `frontend/src/pages/super-admin/DiscordInboundPage.tsx:1` | ローカル interface・`capUnit` 関数・「形態」列削除済み |
| `backend/tests/test_condition_vocab.py:1` | `COALESCE(NULLIF(i.unit,''),p.unit)` → `NULLIF(i.unit,'')` 4箇所更新済み |
| `backend/tests/test_super_admin_inbound_api.py:1` | `products.unit` スキップガード削除・unit/condition アサーション削除済み |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `COALESCE(NULLIF(i.unit,''),p.unit)` の正しい除去形式 | Planner 指示: `NULLIF(i.unit,'')` を使用（NULL-for-empty-string 保持） | ✅ 解消済み |
| 2 | `unit_price` / `unit_price_usd` / `unit_price_eur` への誤影響 | grep 確認: `p\.unit_price` 行はすべて保持 | ✅ 解消済み |
| 3 | `quote_items.condition` / `quote_items.unit` への影響 | 対象外: 明細スナップショット列・手動入力欄はそのまま | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

Phase 2（`inventory.unit` バックフィル 62 行 + `ALTER TABLE DROP COLUMN`）は本 PR マージ・CI green 確認後に別ステップで PO GO を得て実施する。
