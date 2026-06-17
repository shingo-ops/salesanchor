# design: company-list-detail-navigation

## KGI

| 基準 | 検証方法 |
|---|---|
| 一覧の右側操作ボタン（詳細・編集・削除）が消える | `/crm/companies` を開いて確認 |
| 顧客名クリックで `/crm/companies/{id}` に遷移 | 名前セルをクリックして URL 確認 |
| 行の空白部分クリックでも詳細へ遷移 | 行の空白をクリックして URL 確認 |
| 行クリックで右スライド編集が開かない | 旧 `useRecordDrawer` 廃止で担保 |
| 詳細ページに削除ボタンが表示される | `customers.delete` 権限アカウントで確認 |
| 削除は確認モーダルなしで実行されない | ConfirmModal の存在確認 |
| 削除成功後 `/crm/companies` へ遷移 | 削除実行後の URL 確認 |
| 新規登録モーダルは従来通り動く | 「+ 新規顧客情報」クリックで確認 |
| 会話履歴タブへの影響なし | convHistory タブが正常表示 |

## 外部事例欄

既存 ADR-122（DataTable・Drawer標準化バッチC）に基づく操作集約。右スライド編集の廃止は PO 合意済み（CompaniesPage限定）。詳細ページへの削除移動は「操作の文脈に合わせた配置」パターン。

## 変更内容

### CompaniesPage.tsx

- 削除: `Drawer`・`useRecordDrawer`・`CompanyFormFields` の import
- 削除: `emptyEditForm`・`toForm` const（Drawer 用）
- 削除: `useRecordDrawer` call と `drawerOpen`・`editId`・`editForm`・`handleRowClick`・`closeDrawer`
- 削除: `deleteTarget` state
- 削除: `handleEditSubmit` / `handleDelete` 関数
- 削除: `actions` 列（詳細・編集・削除ボタン）
- 変更: 名前列 Link の `to` を `/crm/companies/${c.id}` に統一
- 変更: `onRowClick` を `(c) => navigate(\`/crm/companies/${c.id}\`)` に変更（常時有効・権限ガード不要）
- 削除: Drawer JSX / 会社削除 ConfirmModal JSX

### CompanyDetailPage.tsx

- 追加: `canDelete = hasPermission("customers.delete")`
- 追加: `deleteOpen` / `deleteError` state
- 追加: `handleCompanyDelete` 関数（`api.delete` → 成功時 `/crm/companies` へ navigate）
- 追加: ヘッダー右側の削除ボタン（`Button variant="danger"`・`canDelete` 条件付き）
- 追加: `deleteError` バナー表示
- 追加: 会社削除 `ConfirmModal`（既存キー `companies.deleteCompany` / `companies.deleteConfirmMessage` を使用）

## 参照 ADR

- ADR-060: Client Profile 管理
- ADR-058: 顧客情報
- ADR-122: Modal標準化（ConfirmModal 使用方針と整合）
