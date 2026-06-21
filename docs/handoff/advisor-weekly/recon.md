# recon: Advisor Weekly / W-1b 今やること UI

**仕事名**: Advisor Weekly / W-1b 今やること UI
**日付**: 2026-06-21
**対象ADR**: ADR-139 / ADR-067
**担当**: architect

## file:line 引用表

| 引用先 path:line | 確認内容 |
|------------------|---------|
| frontend/src/pages/dashboard/DashboardPage.tsx:487-493 | `FunnelSection` の直下に `WeeklyAdvisorSection` を差し込める |
| frontend/src/pages/dashboard/DashboardPage.tsx:502-618 | 既存の固定エリアはフォローアップ / 目標のまま残る |
| frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:1-120 | W-1 API を `scope=mine` で呼び、守り3種を score 順で表示する UI |
| frontend/src/pages/dashboard/WeeklyAdvisorSection.css:1-120 | 意味ベース色・ダークモード対応のセクションスタイル |
| frontend/src/api/funnel.ts:167-180 | `/analytics/weekly-advisor-defensive` の API クライアント |
| frontend/tests-e2e/scene1-dashboard.spec.ts:1-220 | Dashboard 画面で今やることセクションを確認する Playwright 追加 |
| frontend/tests-e2e/funnel-dashboard.spec.ts:1-200 | ダッシュボードのスクリーンショット系 spec に weekly advisor mock を追加 |

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | CI 上での screenshot baseline 差分量 | GitHub Actions の Playwright 実行結果を確認 | 未確認 |
| 2 | browser sandbox 制約の有無 | CI の chromium 実行ログを確認 | 未確認 |

**未解決ゼロ確認**: UI 実装に必要な差し込み点は確認済み

## 補足

- 表示のみで、フォロー追加導線は含めない。
- `tenant_006` 前提での確認、`tenant_4` は使わない。
- DB / API の追加変更は不要。
