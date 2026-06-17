# recon: company-list-detail-navigation

## 対象ファイル

| ファイル | 行 | 内容 |
|---|---|---|
| `frontend/src/pages/companies/CompaniesPage.tsx:390-408` | 389-409 | columns定義: name列はLink、actions列に「詳細を表示」「編集」「削除」ボタン |
| `frontend/src/pages/companies/CompaniesPage.tsx:416` | 416 | `onRowClick={hasPermission("customers.update") ? handleRowClick : undefined}` で右スライド編集が開く |
| `frontend/src/pages/companies/CompaniesPage.tsx:190-191` | 190-191 | `useRecordDrawer` を使って `handleRowClick` / `drawerOpen` / `editId` / `editForm` を管理 |
| `frontend/src/pages/companies/CompaniesPage.tsx:552-569` | 552-569 | 編集 Drawer JSX |
| `frontend/src/pages/companies/CompaniesPage.tsx:571-585` | 571-585 | 会社削除 ConfirmModal JSX |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:34` | 34 | `canEdit = hasPermission("customers.update")` のみ。`canDelete` はなし |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:152-187` | 152-187 | ヘッダー右側に登録リンク系ボタン + ステータスバッジ。削除ボタンなし |
| `frontend/src/hooks/useRecordDrawer.ts` | — | `handleRowClick` が `drawerOpen=true` にする。詳細遷移とは非互換 |
| `frontend/src/components/DataTable.tsx` | — | `onRowClick` は行クリック・Enter・Spaceに対応。行内 button/a は二重発火しない |

## 関連ADR

- `docs/adr/ADR-060`: 会社管理（Client Profile）の正準ADR
- `docs/adr/ADR-058`: 顧客情報の正準ADR
- `docs/adr/ADR-122-realpage-modal-standardization.md`: Modal標準化。今回の削除確認は既存 ConfirmModal を使うため対象外

## i18n キー確認

- `companies.deleteCompany`: ja=「顧客情報を削除」/ en=「Delete Client Profile」（存在確認済み）
- `companies.deleteConfirmMessage`: ja=「{{name}}({{code}})を削除しますか？...」（存在確認済み・689行目）
- `common.delete`: 存在確認済み

## ルーティング確認（`frontend/src/App.tsx`）

```
/companies        → redirect /crm/companies
/companies/:id    → redirect /crm/companies/:id
/crm/companies    → CompaniesPage
/crm/companies/:id → CompanyDetailPage
```

名前セルのリンク先は `/crm/companies/${c.id}` に統一する（旧: `/companies/${c.id}` はリダイレクト経由）。

## 既存削除ConfirmModal位置

- `CompaniesPage.tsx` 一覧内に存在 → 今回削除
- `CompanyDetailPage.tsx` 住所削除・担当者削除の ConfirmModal は既存 → 触らない
- 今回: 会社削除 ConfirmModal を `CompanyDetailPage.tsx` に新規追加
