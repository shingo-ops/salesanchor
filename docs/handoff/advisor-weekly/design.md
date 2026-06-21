# design: Advisor Weekly / W-1b 今やること UI

**対象ADR**: ADR-139 / ADR-067
**recon**: docs/handoff/advisor-weekly/recon.md
**日付**: 2026-06-21
**担当**: Planner

## 目的

W-1 API `/analytics/weekly-advisor-defensive` を `scope=mine` で取得し、ダッシュボードの `FunnelSection` 直下に「今やること」セクションを表示する。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `WeeklyAdvisorSection` が `DashboardPage` の `FunnelSection` 直下に出る | `frontend/src/pages/dashboard/DashboardPage.tsx:487-493` |
| 守り3種が score 降順で表示される | `frontend/tests-e2e/scene1-dashboard.spec.ts` |
| `scope=mine` 固定で表示される | `frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx` |
| ローディング / 空状態 / エラーが崩れない | `frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx` / `.css` |
| ダークモード・意味ベース色に従う | `frontend/src/pages/dashboard/WeeklyAdvisorSection.css` |
| process-artifacts gate に必要な標準ワークフロー確認が PR に含まれる | PR本文 |

## 技術方針

- 既存の `db-section-card` / `db-section-header` を流用する
- 追加 CTA は置かない
- `WeeklyAdvisorSection` 内で API を読み、結果を score 降順のまま描画する
- フォロー追加などの書き込み導線は W-1c へ切り分ける

## 外部・過去事例の参照と我々への応用

該当なし。今回の UI は既存ダッシュボードの section-card / dark mode token / score 表示パターンをそのまま流用すれば足りるため、外部事例の新規参照は不要。重要なのは、提案は表示のみで確定しないことと、`scope=mine` に固定して担当者スコープを明示すること。

## 完了条件

- ダッシュボードに「今やること」が表示される
- Playwright で表示確認できる
- CI が green なら通常マージ
