# Phase 3 設計 — Advisor Phase 1 / PR-1 顧客別受注履歴 API

**対象ADR**: ADR-139
**recon**: docs/handoff/advisor-phase1/recon.md
**日付**: 2026-06-19
**担当**: Planner

## 外部・過去事例の参照と我々への応用

該当なし。

今回の PR は既存 analytics の period / scope 実装と orders の既存カラムを使う read-only 集計 API であり、外部事例の比較や過去事例の追加参照は不要。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 顧客別受注履歴 API が 200 で返る | pytest backend/tests/test_analytics.py -q -k customer_orders --no-cov |
| 1 件のみの受注では平均間隔と予測日が null になる | pytest backend/tests/test_analytics.py -q -k customer_orders --no-cov |
| scope=mine で担当外会社が混ざらない | pytest backend/tests/test_analytics.py -q -k customer_orders --no-cov |
| period の不正値が 422 になる | pytest backend/tests/test_analytics.py -q -k customer_orders --no-cov |
| process-artifacts gate が通る | GitHub Actions の process-artifacts gate |

## 技術 How・KPI

- KPI: 顧客ごとの受注履歴、平均受注額、平均受注間隔、最終受注日、次回受注予測日が read-only で返ること
- 技術選択: 既存 analytics の scope / period の流儀に揃え、orders.deal_id と deals.assigned_to を結合して mine を実現する

## 弊害・トレードオフ

- 受注 1 件の会社では平均間隔と予測日が計算できないため null を返す
- 集計は read-only で、編集や保存は行わない

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | analytics に customer-orders エンドポイントを追加 | Generator |
| 2 | pytest で境界ケースを確認 | Generator |
| 3 | process-artifacts gate を通す | CI |

## 継続

- 完了後の監視: PR の CI 結果確認
- 次フェーズへの引き継ぎ: フロント表示と advisor の後続 PR
