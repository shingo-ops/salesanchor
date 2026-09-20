# Design: Remove analysis_rule system

## 目的
PR #3621 で `tcg_status_master` が SSOT として確立された。`analysis_rule` システム（完売ルール・予約ルール管理 UI + 13 DB テーブル + バックエンドサービス群）は機能的に重複・不要となったため削除する。

## 参照
- recon.md: `docs/handoff/remove-analysis-rule-system/recon.md`
- SSOT 統合 PR: #3621

## 変更概要

### DB
13 テーブルを DROP（冪等 `IF EXISTS`）。migration: `20260921_010000_drop_analysis_rule_tables.sql`

### Backend
- router/service/csv_svc/task ファイル 4 件削除
- test ディレクトリ 3 ファイル削除
- main.py から import / router 登録を除去
- tcg_distribution_svc.py から安全装置 #8c 除去（テーブルが消えるため不要）
- item_corrections_svc.py から C93 UPDATE 除去（テーブルが消えるため不要）

### Frontend
- SoldOutRulesPanel / SoldOutWordsTab / DateRulesPanel 削除
- AnalysisRulesPage からそれらの import / 条件レンダリング除去
- AnalysisRulesSidebar から `sold-out` / `date-rule` 型定義・ナビ項目・「ルール管理」グループ除去
- i18n: `analysisRules.tabs`, `analysisRules.soldOut`, `analysisRules.dateRule`, `sidebar.soldOut/dateRule/groupRuleManagement` 削除

### CI
- migration-guard.yml の PUBLIC_TABLES から 13 テーブル除去

## 基準と検証方法

| 基準 | 検証方法 |
|------|---------|
| TypeScript エラーなし | `cd frontend && npx tsc --noEmit` がゼロエラーで完了 |
| Python lint エラーなし | `cd backend && python -m ruff check .` がゼロエラーで完了 |
| analysis_rule 残存参照なし | grep で残存しないことを確認 |
| AnalysisRulesPage が起動する | 解析管理ページでダッシュボード・精度管理・マスタ管理が表示される |
| StatusMasterPanel が動作する | ステータスマスタ管理パネルが表示・操作できる |

## 外部事例
- SSOT 統合による旧サブシステム削除のパターン（Rails では concerns/service 削除、FastAPI では router/service 削除が標準）

## 守り手
- TypeScript コンパイラ: 削除コンポーネントへの参照が残るとエラー
- Ruff lint: import エラーが残るとエラー
- migration-guard CI: DROP テーブルが PUBLIC_TABLES に残っているとエラー
