# recon: 抽出テーブル列改善

## 対象ファイル

- `backend/app/routers/tcg_analysis_dashboard.py:91-96` — RecentExtractionJobItem (channel_name 1フィールド)
- `backend/app/services/tcg_analysis_dashboard_svc.py:190-220` — recent_extraction_jobs クエリ (sc.channel のみ集計)
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:175-181` — RecentExtractionJob 型定義
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1044-1089` — recentJobColumns (4列: channel/items/status/date)
- `frontend/src/locales/ja.json:4371` — extractionJobChannel キーのみ
- `frontend/src/locales/en.json:4371` — extractionJobChannel キーのみ

## 既存パターン確認

- `backend/app/services/tcg_analysis_dashboard_svc.py:402-444` — get_supplier_pipeline(): `LEFT JOIN suppliers s ON s.id = sc.supplier_id` パターン稼働中
- `backend/app/services/tcg_analysis_dashboard_svc.py:477` — `analysis_results ar ON ar.extraction_item_id = ei.id` JOIN パターン稼働中
- `supplier_channels` テーブル: `channel` カラム（channel_name ではない）、`supplier_id` カラムで suppliers に JOIN 可能

## ADR 検索結果

- ADR-027: i18n 強制 (`t("key")` 経由必須)
- ADR-067: デザイントークン強制 (CSS変数のみ)
- ADR-144: UIガバナンス (Badge/DataTable 金型のみ)
- 抽出テーブル固有の ADR なし

## 変更前後の差分サマリ

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| テーブル列数 | 4列 | 7列 |
| 提供者表示 | channel 名 | suppliers.name |
| 解決カウント | なし | analysis_results.pid_resolved=true |
| 未解決カウント | なし | analysis_results.pid_resolved=false |
| 要確認カウント | なし | analysis_results.needs_review=true |
