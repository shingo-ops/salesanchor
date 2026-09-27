# design: DB構造ビューア追加

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

## KPI / 検証方法
- [ ] `/super-admin/analysis-rules` にアクセスしてサイドメニューに「データ構造」が表示される
- [ ] テーブルクリックでカラム一覧が表示される
- [ ] FK列の参照先リンクをクリックで遷移できる
- [ ] CI全緑（lint/test/type-check）
