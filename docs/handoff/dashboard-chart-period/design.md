# Design: Dashboard Chart Period Selector

recon: docs/handoff/dashboard-chart-period/recon.md
作業日: 2026-09-25

## 設計方針

LINE解析ダッシュボードのチャートに期間セレクタを追加する。
SelectControlコンポーネントを使い、7/30/90/180/360日を選択可能にする。

## 変更範囲

| 層 | 変更 |
|---|---|
| backend service | days clamp 90→360（pipeline_trend・import_trend両方） |
| backend router | import-trend Query le=90→le=360 |
| frontend state | `trendDays: number` (default 7) を AnalysisDashboardPanel に追加 |
| frontend UI | `SelectControl` size="sm" をタブバー右端に配置（1つで全タブ共有） |
| frontend fetch | pipeline-trend・import-trend を `days=${trendDays}` に変更 |
| i18n | period7d/30d/90d/180d/360d/periodLabel キーを ja.json・en.json 両方に追加 |

## 触るファイル

1. `backend/app/services/tcg_analysis_dashboard_svc.py` — clamp 90→360
2. `backend/app/routers/tcg_analysis_dashboard.py` — Query le=90→le=360
3. `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` — state追加・SelectControl追加・API呼び出し変更
4. `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css` — セレクタ配置スタイル
5. `frontend/src/locales/ja.json` — period系キー追加
6. `frontend/src/locales/en.json` — period系キー追加（同一キー）

## 受入基準

| 基準 | 検証方法 |
|---|---|
| ハードコード `days=7` なし | `grep "days=7" AnalysisDashboardPanel.tsx` でコメント行のみ |
| 期間変更でAPIが再フェッチされる | ブラウザNetworkタブで days パラメータ確認 |
| 360日まで選択可能 | セレクタで360日選択 → APIが200を返す |
| i18n完全 | check-i18n-missing-keys.js PASS |
| TypeScript型エラーなし | tsc --noEmit PASS |
| デザインシステム遵守 | SelectControl使用（生select禁止） |

## 外部・過去事例の参照と我々への応用

該当なし（内部機能追加。SelectControlは既存デザインシステムコンポーネントを使用）

## 守り手

- i18n check: check-i18n-missing-keys.js
- TypeScript型チェック: tsc --noEmit
- ADR-144 UIガバナンス: 生select禁止確認
