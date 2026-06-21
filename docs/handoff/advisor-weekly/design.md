# design: Advisor Weekly / W-1b 今やること UI

**対象ADR**: ADR-139 / ADR-067
**recon**: docs/handoff/advisor-weekly/recon.md
**日付**: 2026-06-21
**担当**: Planner

## 目的

週次アドバイザーの表示をダッシュボードの固定位置に差し込み、担当者自身のスコープだけを表示する。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 画面の差し込み位置が正しい | frontend/src/pages/dashboard/DashboardPage.tsx の 487-493行 |
| 打ち手が score 降順で表示される | frontend/tests-e2e/scene1-dashboard.spec.ts |
| 個人スコープ固定で表示される | frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx の 1-120行 |
| ローディング / 空状態 / エラーが崩れない | frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx の 1-120行 / frontend/src/pages/dashboard/WeeklyAdvisorSection.css の 1-120行 |
| ダークモード・意味ベース色に従う | frontend/src/pages/dashboard/WeeklyAdvisorSection.css の 1-120行 |
| process-artifacts gate に必要な標準ワークフロー確認が PR に含まれる | PR本文 |

## 技術方針

- 既存の db-section-card / db-section-header を流用する
- 追加 CTA は置かない
- セクションは読み取り専用で描画する
- 書き込み導線は後続の W-1c へ切り分ける

## 完了条件

- ダッシュボードに「今やること」が表示される
- Playwright で表示確認できる
- CI が green なら通常マージ

## 外部・過去事例の参照と我々への応用

- 該当なし（UI 追加のみで、外部導入事例を参照せずとも受け入れ基準を file:line で検証できる）
- 画面追加のみで、外部API / DB / migration の設計追加は不要
- 既存の dashboard / funnel / API 連携を流用するため、追加の設計リスクはない
