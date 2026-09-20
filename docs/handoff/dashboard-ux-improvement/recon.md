# Dashboard UX Improvement — Recon

## 現状調査（本番DB実データ: 2026-09-20）

### extraction_jobs (tenant_004)
- 総数: 865件
- 完了(done): 771件 (89.1%)
- 空(empty): 91件 (10.5%)
- エラー(error): 3件 (0.3%)

### analysis_results (tenant_004)
- 総数: 12,643件
- PID解決率: 68.9% (8,714件)
- Unit解決率: 59.1% (7,475件)
- 要確認率: 34.1% (4,311件)

### ボトルネック
- 最大: pid_unresolved = 3,883件 (要確認理由の90%)
- 問題仕入先: INスタッフ(PID 23%), funスタッフ(PID 26%), Ryum.a(PID 0%)

### 既存コード
- `backend/app/services/tcg_analysis_dashboard_svc.py:15` — get_pipeline_summary()
- `backend/app/routers/tcg_analysis_dashboard.py:85` — GET /pipeline-summary
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:76` — コンポーネント
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css:1` — スタイル

### ADR検索結果
- ADR-027: i18n強制
- ADR-067: デザイントークン強制
- ADR-144: UIガバナンス（金型コンポーネントのみ）
