# design: /inventory UI 整理

## 対象 ADR
ADR-093 (`docs/adr/ADR-093-inventory-page.md`)

## recon 相互参照
`docs/handoff/inventory-ui-cleanup/recon.md`

---

## 変更概要（5件）

### #1: selection action bar 削除（書類作成は別ページ・往復動線不使用・PO決定）
- 対象: `InventoryPage.tsx:521-606`（往復バー + 権限別発注書/見積/請求ボタン群）
- 削除根拠: 発注書/見積/請求の作成は各専用ページで完結するため /inventory でのショートカット動線は不要。往復バー（fromQuote フロー）も実運用で使われていないとの PO 判断。
- 往復(fromQuote)フロー全廃: 在庫画面の往復バー削除に加え、入口（QuoteCreatePage / InvoiceCreatePage の `goToInventory` 呼び出し・addMode ラジオボタン）も削除（蛇足機能・PO決定）。キャンセル先も各一覧（/quotes, /invoices）に固定。
- 削除関数: `selectedPayload`, `goCreate`, `onCreateQuote`, `openPurchaseOrder`, `clearSelection`, `noSelection`
- 保持: `toggleSelect`, `selectedIds`（テーブルチェックボックスで使用）
- `usePermissions` import・`hasPermission` 呼び出しも合わせて削除

### #2: 全TCGシリーズ category select 削除
- 対象: `InventoryPage.tsx:458-472`（`<select data-testid="inventory-category-filter">`）
- `category` state / `sortedCategories` は InventoryFilterPanel に渡すため保持

### #3: 検索 input 高さを btn-sm に揃える
- 対象: `InventoryPage.tsx:440`
- 追加 style: `padding: var(--space-1) var(--space-10px)`, `fontSize: var(--font-xs)`, `boxSizing: border-box`
- btn-sm の CSS と同一値（`components.css: .btn-sm { padding: var(--space-1) var(--space-10px); font-size: var(--font-xs); }`）

### #4: タブを主要4ボタン + その他ドロップダウンに変更
- 対象: `InventoryPage.tsx:618-631`
- 固定ボタン: すべて(`all`) / ポケモンカード(`pokemon_booster_box`) / ワンピース(`one_piece`) / ドラゴンボール(`dragon_ball`)
- `<select>` に残りの tcgTypes を表示（union_arena, yugioh, other, gundam, weiss_schwarz, digimon, hololive, lorcana, xross_stars）
- `activeTab` が primary 4 外の値の場合、select の value に反映
- i18n key 追加: `inventory.filter.otherTypes` → ja: "その他" / en: "Other"

### #5: 警告バナーを検索下へ移動・グレー化
- 削除元: `InventoryPage.tsx:424`（`<div className="error-message">` 赤・ページ最上部）
- 挿入先: InventoryFilterPanel の直後
- 新スタイル: `<p>` + `color: var(--text-secondary)`, `fontSize: var(--font-sm)`（赤を除去）

---

## KPI 検証基準

| 基準 | 検証方法 |
|------|---------|
| action-bar DOM が存在しない | `data-testid="inventory-action-groups"` が render 結果に含まれないこと |
| 往復バー DOM が存在しない | `data-testid="inventory-roundtrip-bar"` が render 結果に含まれないこと |
| category select DOM が存在しない | `data-testid="inventory-category-filter"` が render 結果に含まれないこと |
| 検索 input と検索ボタンの高さが揃う | Chrome DevTools で input/button の clientHeight が同一であること |
| タブが4ボタン + select に変化 | `tab active` ボタンが最大4個、残りが `<select>` の option に入ること |
| 警告が検索下・グレー表示 | `data-testid="inventory-expiry-warning"` が `<p>` タグで FilterPanel 以降に存在すること |
| tsc エラーなし | `tsc --noEmit` が 0 exit であること |
| i18n キー同期 | ja.json と en.json に `inventory.filter.otherTypes` が存在すること |
