# recon: analysis_results に work_id カラム追加

## 問題の実測確認

`public.analysis_results` に `work_id` カラムが存在しない（本番DB実測 2026-09-23）。
アナライザーで work_id が解決・保存されるが、`analysis_results` テーブルには記録されていない。
Gemini の work_id 抽出精度を計測するために比較対象（実際に保存された work_id）が必要。

## 関連ファイル

- `backend/app/services/tcg_analyzer_svc.py:1374-1472` — analysis_results UPSERT（INSERT INTO の work_id 追加箇所）
- `migrations/20260923_120000_add_work_id_to_analysis_results.sql:1` — 今回追加する migration
- `scripts/run_all_migrations.sh:1` — migration 実行順序登録

## ADR参照

- 該当ADR: なし（単純なカラム追加）
- 共用マスタSSOT方針: public.analysis_results は public スキーマに統一済み
