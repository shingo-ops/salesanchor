# recon: /inventory UI 整理

## 対象 ADR
ADR-093 (`docs/adr/ADR-093-inventory-page.md`)

## 調査ファイル一覧（file:line 引用）

- `frontend/src/pages/inventory/InventoryPage.tsx:521` — selection-action-bar ブロック開始（往復バー + 権限別ボタン）
- `frontend/src/pages/inventory/InventoryPage.tsx:606` — selection-action-bar ブロック終端
- `frontend/src/pages/inventory/InventoryPage.tsx:279` — `selectedPayload()` 関数（action-bar専用・削除対象）
- `frontend/src/pages/inventory/InventoryPage.tsx:294` — `goCreate()` 関数（action-bar専用・削除対象）
- `frontend/src/pages/inventory/InventoryPage.tsx:302` — `onCreateQuote()` 関数（action-bar専用・削除対象）
- `frontend/src/pages/inventory/InventoryPage.tsx:314` — `openPurchaseOrder()` 関数（action-bar専用・削除対象）
- `frontend/src/pages/inventory/InventoryPage.tsx:458` — category `<select>` 開始（全TCGシリーズ選択・削除対象）
- `frontend/src/pages/inventory/InventoryPage.tsx:472` — category `<select>` 終端
- `frontend/src/pages/inventory/InventoryPage.tsx:440` — search `<input>` style（height未設定・btn-sm と高さ不一致）
- `frontend/src/pages/inventory/InventoryPage.tsx:452` — search button `className="btn-primary btn-sm"`（高さ基準）
- `frontend/src/pages/inventory/InventoryPage.tsx:424` — warning banner（`className="error-message"` 赤表示・移動対象）
- `frontend/src/pages/inventory/InventoryPage.tsx:618` — TCG種別タブ開始（全種別ループ・4ボタン＋その他に変更対象）
- `frontend/src/pages/inventory/InventoryPage.tsx:631` — TCG種別タブ終端
- `frontend/src/pages/inventory/InventoryPage.tsx:90` — `category` state（InventoryFilterPanel に渡す・削除しない）
- `frontend/src/pages/inventory/InventoryPage.tsx:93` — `activeTab` state デフォルト `"pokemon_booster_box"`
- `migrations/085_create_tcg_type_master.sql:1` — tcg_type_master seed: pokemon_booster_box / one_piece / dragon_ball / union_arena / yugioh / other
- `migrations/086_seed_additional_tcg_types.sql:1` — 追加 seed: gundam / weiss_schwarz / digimon / hololive / lorcana / xross_stars

## 削除不可の依存関係

- `selectedIds` / `toggleSelect` → テーブル行チェックボックス（L667-673）で使用
- `category` / `sortedCategories` → `InventoryFilterPanel` props（L491）で使用
- `quoteReturn` → selectedIds 初期値（L95-97）で参照
