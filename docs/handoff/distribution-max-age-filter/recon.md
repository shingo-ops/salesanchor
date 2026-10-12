<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — distribution-max-age-filter

**仕事名**: distribution-max-age-filter  
**日付**: 2026-09-27  
**対象ADR**: ADR-025  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/tcg_distribution_svc.py:192` | fetch_output_rows に max_age_hours パラメータ追加済み |
| `backend/app/services/tcg_distribution_svc.py:216` | max_age_hours > 0 の場合に AND sm.line_posted_at >= NOW() - make_interval(hours => :max_age_hours) を追加 |
| `backend/app/services/tcg_distribution_svc.py:257` | sm.line_posted_at IS NOT NULL フィルタ追加済み |
| `backend/app/services/tcg_distribution_svc.py:294` | fetch_preview_data で settings から max_age_hours を取得 |
| `backend/app/services/tcg_analysis_dashboard_svc.py:661` | null_posted_at_count を COUNT クエリで取得 |
| `backend/app/services/tcg_analysis_dashboard_svc.py:679` | distribution-summary レスポンスに null_posted_at_count 追加 |
| `backend/app/routers/tcg_analysis_dashboard.py:187` | DistributionSummaryResponse に null_posted_at_count: int = 0 フィールド追加 |
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:255` | DistributionSummary 型に null_posted_at_count: number 追加 |
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:2214` | null_posted_at_count > 0 の場合に danger バッジ表示 |
| `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:46` | DistributionSettingsDrawer import 追加 |
| `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:165` | DistributionSettingsDrawer レンダリング追加 |
| `migrations/20260927_120000_add_max_age_hours_setting.sql:1` | max_age_hours=48 を tcg_distribution_settings に INSERT |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | tcg_distribution_settings テーブルが存在するか | file:line で確認 | ✅ 解消済み（既存テーブル利用） |
| 2 | run_distribution も同フィルタを使うか | サービス実装確認 | ✅ 解消済み（fetch_output_rows 経由で適用） |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- `tcg_distribution_settings` は KV ストアとして既存。key='max_age_hours', value='48' を追加するだけ
- NULL フィルタ（line_posted_at IS NOT NULL）はフィルタとバッジの両方で対応
- DistributionSettingsDrawer は新規コンポーネント（118行）
