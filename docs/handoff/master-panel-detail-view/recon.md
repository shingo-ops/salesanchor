# recon: 全マスタパネルDrawer化

## 対象ADR
- ADR-144: UIガバナンス（金型準拠・生select/生input/自作タブ/色直値禁止）

## 調査結果

### 変更対象ファイル（13件）
- `frontend/src/pages/super-admin/components/TypeMasterPanel.tsx`
- `frontend/src/pages/super-admin/components/ProductKindsMasterPanel.tsx`
- `frontend/src/pages/super-admin/components/ProductLinesMasterPanel.tsx`
- `frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx`
- `frontend/src/pages/super-admin/components/QuantityUnitsMasterPanel.tsx`
- `frontend/src/pages/super-admin/components/ConditionDefsMasterPanel.tsx`
- `frontend/src/pages/super-admin/components/WeightClassesMasterPanel.tsx`
- `frontend/src/pages/super-admin/components/StatusMasterPanel.tsx`
- `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx`
- `frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx`
- `frontend/src/pages/super-admin/components/UnitMasterPanel.tsx`
- `frontend/src/pages/super-admin/components/NoteMasterPanel.tsx`
- `frontend/src/pages/super-admin/components/ProductCategoriesMasterPanel.tsx`

### 既存実装の確認
- 金型となるProductMasterPanelはDrawerを採用済み
- 上記13ファイルはいずれもModalを使用（Drawerへの移行対象）
- テーブルにcode列・編集ボタン列・削除ボタン列が存在（廃止対象）

### 関連ADR検索結果
- `git grep -i "ADR-144" docs/adr/` → ADR-144-ui-governance.md 存在確認済み
- `docs/adr/FEATURE-INDEX.md` 参照済み
