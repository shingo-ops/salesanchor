# Recon: Remove analysis_rule system

## 背景
PR #3621 で SSOT が `tcg_status_master` に統合された。`analysis_rule` システム（完売ルール・予約ルール管理 UI + 13 DB テーブル + バックエンドサービス群）は不要となり削除する。

## ADR 確認
- `git grep -i "analysis_rule" docs/adr/` → 該当 ADR なし（設計書は sold-out-rules-design.md として存在するが ADR 番号なし）
- PR #3621: tcg_status_master SSOT 化完了

## 削除対象ファイル一覧

### DB テーブル (13 テーブル × 3 スキーマ)
- `public.analysis_policies`
- `public.analysis_policy_revisions`
- `public.analysis_instruction_versions`
- `public.analysis_execution_profile_versions`
- `public.analysis_rules`
- `public.analysis_rule_versions`
- `public.analysis_rule_words`
- `public.analysis_revision_rules`
- `public.analysis_rule_runs`
- `public.analysis_rule_run_results`
- `public.analysis_test_case_versions`
- `public.analysis_test_suites`
- `public.analysis_suite_cases`
- (同構造 tenant_001.*, tenant_004.*)

### Backend (削除)
- `backend/app/routers/tcg_analysis_rule.py`
- `backend/app/services/tcg_analysis_rule_svc.py` (1004 行)
- `backend/app/services/tcg_analysis_rule_csv_svc.py`
- `backend/app/tasks/tcg_analysis_rule.py`
- `backend/tests/analysis_rule/__init__.py`
- `backend/tests/analysis_rule/test_distribution_integration.py`
- `backend/tests/analysis_rule/test_integration_e2e.py`
- `backend/tests/analysis_rule/test_tcg_analysis_rule_svc.py`

### Backend (編集)
- `backend/app/main.py:106` — import 行削除
- `backend/app/main.py:623-626` — router 登録削除
- `backend/app/services/tcg_distribution_svc.py:719-747` — 安全装置 #8c (analysis_rule_runs チェック) 削除
- `backend/app/services/item_corrections_svc.py:73-90` — C93 (analysis_rule_run_results 無効化) 削除

### Frontend (削除)
- `frontend/src/pages/super-admin/components/SoldOutRulesPanel.tsx`
- `frontend/src/pages/super-admin/components/SoldOutWordsTab.tsx`
- `frontend/src/pages/super-admin/components/DateRulesPanel.tsx`

### Frontend (編集)
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx` — import + レンダリング行 2 件削除
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx` — sold-out / date-rule 型 + ナビ項目削除
- `frontend/src/locales/ja.json` — `analysisRules.tabs`, `analysisRules.soldOut`, `analysisRules.dateRule`, sidebar の soldOut/dateRule/groupRuleManagement 削除
- `frontend/src/locales/en.json` — 同上

### CI/ワークフロー (編集)
- `.github/workflows/migration-guard.yml:224` — PUBLIC_TABLES から 13 テーブル削除
- `scripts/run_all_migrations.sh` — DROP migration 追加

### 触らない範囲
- `frontend/src/pages/super-admin/TcgSoldOutPage.tsx` — 配信結果ビュー（ルール管理ではない）
- `frontend/src/features/tcg-sold-out/` — 配信結果フィーチャー（ルール管理ではない）
- `frontend/src/pages/super-admin/components/StatusMasterPanel.tsx` — SSOT の tcg_status_master 管理 UI（残置）
- `tcg_analysis_dashboard` ルーター / `tcg_analysis_review` ルーター — 解析ダッシュボード・レビュー（残置）
