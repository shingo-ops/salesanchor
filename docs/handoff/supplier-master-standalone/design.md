# design: 仕入元マスタ独立ページ化

## KGI

`/super-admin/supplier-master` にアクセスすると TcgProductMasterPage と同じ構成部品でレンダリングされる。

## KPI

| 基準 | 検証方法 |
|------|----------|
| PageLayout が使われている | SupplierMasterPage.tsx に PageLayout import あり |
| DataTable selectable が使われている | DataTable props に selectable, selectedKeys, onSelectChange あり |
| 生 input/button/table が使われていない | SupplierMasterPage.tsx に `<input type=` `<button` `<table` なし（Discord routing table のみ ui-allow） |
| i18n キーが ja/en 両方に存在 | locales/ja.json locales/en.json に nav.superAdminSupplierMaster あり |
| /super-admin/masters ルートが削除されている | App.tsx に /super-admin/masters なし |

## 変更前後

| 変更点 | before | after |
|--------|--------|-------|
| ルート | /super-admin/masters | /super-admin/supplier-master |
| ページコンポーネント | SuperAdminMastersPage（タブ） | SupplierMasterPage（独立） |
| レイアウト | 生div | PageLayout |
| 検索 | 生input | TextField |
| ボタン | 生button | HeaderButton |
| テーブル | 生table | DataTable（selectableあり） |

## ADR参照

- ADR-027: i18n強制
- ADR-144: UIガバナンス

## 外部・過去事例の参照と我々への応用

同プロジェクト内の TcgProductMasterPage.tsx が直接参照先。同じ金型セット（PageLayout/ContentToolbar/HeaderButton/DataTable/EmptyState/TextField）と useSuperAdmin パターンをそのまま適用する。

## 維持の仕組み

- ADR-027 の i18n チェック（ESLint ルール）が日本語ハードコードを検出
- ADR-144 の UIガバナンスチェックが生 input/button を検出
- PR本文の標準ワークフロー確認セクションで毎回確認
- 守り手: Hikky-dev（コードレビュー時にUIガバナンス・i18n遵守を確認）

## 触らない範囲

- バックエンド（/super-admin/suppliers API は変更なし）
- ProductMastersTab.tsx（orphanedだが有用なため残置）
