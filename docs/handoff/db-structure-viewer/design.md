# design: DB構造ビューア追加

参照: [recon.md](./recon.md) (`docs/handoff/db-structure-viewer/recon.md`)

## KGI
管理者が画面上でDB全テーブル構造・FK関係を把握できる（ツール切り替え不要）

## 設計方針

### データ取得: SSOT（information_schema）
- `information_schema.tables` でテーブル一覧取得（schema別カテゴリ分け）
- `information_schema.columns` でカラム情報取得
- `information_schema.table_constraints` + `information_schema.key_column_usage` でFK関係取得
- migration不要・DBスキーマ変更に自動追従

### UIアーキテクチャ
- 既存 `AnalysisRulesSidebar` にメニュー追加（サイドバー拡張）
- `AnalysisRulesPage` にパネルとして配線
- `DbViewerPanel` = 左ナビ（カテゴリ別ツリー）+ 右メイン（DataTable）

### ADR遵守
- ADR-144: DataTable/Card既存金型使用・生input禁止・CSS変数のみ
- ADR-027: ja.json/en.json 両方にキー追加（33キー）

## 影響範囲
- 新規ファイル3件追加（router, component, css）
- 既存ファイル5件変更（main.py, AnalysisRulesPage, Sidebar, locales x2）
- migrations/・deploy.yml・本番スクリプト: 変更なし

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| サイドメニューに「データ構造」が表示される | `/super-admin/analysis-rules` にアクセスしてサイドバー確認 |
| テーブル一覧がカテゴリ別に表示される | テーブルクリック前の左ペインを目視確認 |
| テーブルクリックでカラム一覧がDataTable表示される | 任意テーブルをクリックして右ペイン確認 |
| FK列の参照先リンクをクリックで遷移できる | FK列のリンクをクリックして遷移先テーブルが表示されることを確認 |
| 検索ボックスでテーブル名を絞り込める | 検索ボックスに文字入力してリストが絞り込まれることを確認 |
| CI全緑 | GitHub Actions チェック結果 |

## 外部・過去事例の参照と我々への応用
- PostgreSQL公式: information_schemaはSQL標準準拠のスキーマメタ情報ビュー。pg_catalogより移植性が高く、カラム・FK・制約を動的取得に最適。
- 既存実装参照: `backend/app/routers/super_admin_tcg.py:1` のルーター構造・`frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx:73` のサイドツリー+テーブルパターンを踏襲し、コードベース内で一貫性を保つ。

## 維持の仕組み
守り手: `frontend/src/pages/super-admin/components/DbViewerPanel.tsx`
- テーブル追加・カラム変更はDBに反映された瞬間にビューアにも自動反映（migration不要・SSOT）
- FK設計変更はinformation_schema.key_column_usageが追跡するため手動更新不要
- i18nキー追加時はja.json/en.json両方に同一キーが必須（CIでチェック）
