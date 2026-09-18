# recon: 仕入元マスタ独立ページ化

## 対象ファイル

- `frontend/src/pages/super-admin/SuperAdminMastersPage.tsx` — 削除対象タブページ
- `frontend/src/pages/super-admin/SuppliersAdminTab.tsx:1-385` — リネーム・改修元
- `frontend/src/pages/super-admin/TcgProductMasterPage.tsx:1-95` — レイアウト参照先
- `frontend/src/App.tsx:89` — import行（SuperAdminMastersPage）
- `frontend/src/App.tsx:310-314` — /super-admin/masters ルート
- `frontend/src/components/DesktopShell.tsx:191` — saasAdminItems のリンク
- `frontend/src/locales/ja.json:278` — nav.masterManagement キー（残置）
- `frontend/src/locales/en.json:278` — nav.masterManagement キー（残置）
- `frontend/src/components/DataTable.tsx:1-311` — selectable prop 確認
- `frontend/src/components/ContentToolbar.tsx:1-24` — props確認
- `frontend/src/components/HeaderButton.tsx:1-60` — variant確認（danger未サポート）
- `frontend/src/components/TextField.tsx:1-35` — InputHTMLAttributes継承確認

## 既存ADR確認

- ADR-027: UI文字列は t("key") 経由必須
- ADR-144: 生select/input/table/色直値禁止
