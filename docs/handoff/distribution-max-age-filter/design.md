<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# 設計 — distribution-max-age-filter

**対象ADR**: ADR-025  
**recon**: docs/handoff/distribution-max-age-filter/recon.md  
**日付**: 2026-09-27  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 過去事例: `docs/handoff/fix-distribution-posted-at` — posted_at ベースのフィルタ実装パターンを踏襲。WHERE句でNULL除外を追加する手法と同じアプローチ
- DB SSOT パターン: `tcg_distribution_settings` KVテーブルへの設定格納は既存パターン（auto_distribute_flag 等）を踏襲

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| migration 実行後 key='max_age_hours' で value='48' が返る | `SELECT value FROM public.tcg_distribution_settings WHERE key='max_age_hours'` |
| fetch_output_rows が 48h 超えの行を除外する | pytest または手動 preview で件数確認 |
| null_posted_at_count が distribution-summary API から返る | GET /tcg/analysis-dashboard/distribution-summary レスポンス確認 |
| NULL 件数 > 0 の場合にダッシュボード配信タブに danger バッジが表示される | Playwright または手動 UI 確認 |
| DistributionSettingsDrawer が開閉・保存できる | 手動 UI 確認 |

---

## 技術 How・KPI

- KPI: 配信時に line_posted_at が 48h 超の行がスプレッドシートに出力されない（件数=0）
- 技術選択: SQL WHERE 句に `AND sm.line_posted_at >= NOW() - make_interval(hours => :max_age_hours)` を追加。make_interval はパラメータバインドが容易でインジェクションリスクなし
- 設定SSOT: `tcg_distribution_settings` KVテーブルに max_age_hours を格納。Drawer UI からのみ変更可（直接DB変更は非推奨）

---

## 弊害・トレードオフ

- 48h フィルタにより一部の正規商品が除外される可能性 → 閾値は Drawer から変更可（0 を設定でフィルタ無効化）
- NULL 除外フィルタにより line_posted_at が NULL の行が配信されなくなる → バッジで件数を通知し運営者が原因調査できる

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | migration: tcg_distribution_settings に max_age_hours=48 追加 | Generator |
| 2 | backend: fetch_output_rows/fetch_preview_data/run_distribution にフィルタ追加 | Generator |
| 3 | backend: tcg_analysis_dashboard_svc に null_posted_at_count カウント追加 | Generator |
| 4 | backend: DistributionSummaryResponse に null_posted_at_count フィールド追加 | Generator |
| 5 | frontend: DistributionSettingsDrawer 新規作成 | Generator |
| 6 | frontend: AnalysisRulesPage にボタン追加 | Generator |
| 7 | frontend: AnalysisDashboardPanel に NULL 異常バナー追加 | Generator |
| 8 | frontend: i18n キー追加（ja/en） | Generator |

---

## 継続

- 完了後の監視: 配信件数の推移を dashboard で確認。閾値 0 件なら意図しないフィルタが疑われる
- 次フェーズへの引き継ぎ: 必要なら max_age_hours を条件別に設定できる拡張（現時点では不要）

---

## 触るファイル:

- `backend/app/routers/tcg_analysis_dashboard.py`
- `backend/app/services/tcg_distribution_svc.py`
- `frontend/src/locales/en.json`
- `frontend/src/locales/ja.json`
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx`

---

## 維持の仕組み

守り手: 人手で守る  
- `tcg_distribution_settings` の max_age_hours 設定は Drawer UI から変更。直接 SQL 変更は禁止（ADR-025）
- NULL バッジが常時表示される場合は line_posted_at が NULL になる上流パイプラインを調査すること
