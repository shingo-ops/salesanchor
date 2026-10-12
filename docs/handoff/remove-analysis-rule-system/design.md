# Design: Remove analysis_rule system

## 目的
PR #3621 で `tcg_status_master` が SSOT として確立された。`analysis_rule` システム（完売ルール管理・予約ルール管理 UI + 13 DB テーブル + バックエンドサービス群）は機能的に重複・不要となったため削除する。

## 参照
- recon.md: `docs/handoff/remove-analysis-rule-system/recon.md`
- SSOT 統合 PR: #3621

## 変更概要

### DB
13 テーブルを DROP（冪等 `IF EXISTS`）。migration: `migrations/20260921_010000_drop_analysis_rule_tables.sql`

### Backend
- router/service/csv_svc/task ファイル 4 件削除
- test ディレクトリ 3 ファイル削除
- `backend/app/main.py` から import / router 登録を除去
- `backend/app/services/tcg_distribution_svc.py` から安全装置 #8c 除去（テーブルが消えるため不要）
- `backend/app/services/item_corrections_svc.py` から C93 UPDATE 除去（テーブルが消えるため不要）

### Frontend
- SoldOutRulesPanel / SoldOutWordsTab / DateRulesPanel 削除
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx` からそれらの import / 条件レンダリング除去
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx` から `sold-out` / `date-rule` 型定義・ナビ項目・「ルール管理」グループ除去
- i18n: `analysisRules.tabs`, `analysisRules.soldOut`, `analysisRules.dateRule`, `sidebar.soldOut/dateRule/groupRuleManagement` 削除

### CI
- `.github/workflows/migration-guard.yml` の PUBLIC_TABLES から 13 テーブル除去

## 基準と検証方法

| 基準 | 検証方法 |
|------|---------|
| TypeScript エラーなし | `cd frontend && tsc --noEmit` がゼロエラーで完了 |
| Python lint エラーなし | `cd backend && ruff check app/` がゼロエラーで完了 |
| analysis_rule 残存参照なし | grep で残存しないことを確認 |
| AnalysisRulesPage が起動する | 解析管理ページでダッシュボード・精度管理・マスタ管理が表示される |
| StatusMasterPanel が動作する | ステータスマスタ管理パネルが表示・操作できる |

## 外部・過去事例の参照と我々への応用

- **Rails における concerns/service 削除パターン**: SSOT 統合後に旧サブシステムを削除するのは標準的な技術負債解消手順。router + service + test を一括削除し、参照箇所（main.py 相当）から除去する。
- **FastAPI router 削除ガイドライン**: `include_router` の削除は import + 登録行の両方を削除しないと ImportError が発生する。本 PR では両行を削除済み。
- **DB DROP TABLE IF EXISTS の冪等性**: PostgreSQL の `DROP TABLE IF EXISTS` はテーブルが存在しない環境でも安全に実行でき、re-run に耐える。

**我々への応用**: analysis_rule テーブルは本番・QA・ローカルの各環境で存在状況が異なる可能性があるため、`IF EXISTS` を使用し冪等性を確保した。

## 維持の仕組み

守り手: TypeScript コンパイラ（削除コンポーネントへの参照が残ると TS2307）、Ruff lint（import エラー）、migration-guard CI（`.github/workflows/migration-guard.yml` — DROP テーブルが PUBLIC_TABLES に残るとエラー）
