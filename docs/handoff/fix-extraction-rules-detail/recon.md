# recon: fix-extraction-rules-detail

## 既存ADR検索結果

- `docs/adr/ADR-027-ui-internationalization.md` — i18n 強制（全 UI 文字列は t("key") 経由）
- `docs/adr/ADR-144` — UIガバナンス（金型コンポーネントのみ使用）

## バグ1: SupplierOverviewItem フィールド名不一致

**対象**: `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:27-33`

```
// 変更前
interface SupplierOverviewItem {
  id: number;       // バックエンドは supplier_id を返す
  unit_ng: number;  // バックエンドは unit_ng_count を返す
}
```

ユーザー指示で確定したフィールド名不一致:
- `id` → `supplier_id`
- `unit_ng` → `unit_ng_count`

影響箇所（全て `SupplierExtractionRulesPage.tsx` 内）:
- `:27` — インターフェース定義
- `:92` — `selectedSupplier` state 型
- `:113` — sort 関数の `.unit_ng`
- `:150` — `handleSelectSupplier` の `row.id`
- `:154` — `fetchDetail(row.id)`
- `:184` — API PATCH パス `selectedSupplier.id`
- `:222` — DataTable `key` 属性
- `:224-226` — `renderCell` の `row.unit_ng`
- `:379` — `rowKey` の `row.id`

## バグ2: MobileShell に supplier-extraction-rules が欠落

**対象**: `frontend/src/components/MobileShell.tsx:162-177`

- DesktopShell (`frontend/src/components/DesktopShell.tsx:190-195`) には `supplier-extraction-rules` が `saasAdminItems` に含まれている
- MobileShell には `analysisRules` と `buybackPrices` のみで、`supplierExtractionRules` が欠落

i18n キー確認:
- `frontend/src/locales/ja.json:287` — `"superAdminSupplierExtractionRules": "抽出ルール設定"` ✅
- `frontend/src/locales/en.json:287` — `"superAdminSupplierExtractionRules": "Extraction Rules"` ✅
