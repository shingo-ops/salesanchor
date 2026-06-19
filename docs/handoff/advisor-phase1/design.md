# Phase 3 設計 — Advisor Phase 1 / PR-2 新規/既存セグメント別 売上サマリーAPI

**対象ADR**: ADR-139
**recon**: docs/handoff/advisor-phase1/recon.md
**日付**: 2026-06-20
**担当**: Planner

## 外部・過去事例の参照と我々への応用

該当なし。

今回は既存 revenue-summary の new / repeat 定義を再利用し、orders の件数だけを segment 別に足す read-only 集計 API である。外部事例や追加の過去事例参照は不要。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| GET /api/v1/analytics/revenue-segments が返る | pytest backend/tests/test_analytics.py -q -k revenue_segments --no-cov |
| new / repeat の売上・件数・平均単価・顧客数・構成比が返る | pytest backend/tests/test_analytics.py -q -k revenue_segments --no-cov |
| scope=mine で担当外注文が混ざらない | pytest backend/tests/test_analytics.py -q -k revenue_segments --no-cov |
| 片側セグメントがゼロのとき 0 / null で壊れない | pytest backend/tests/test_analytics.py -q -k revenue_segments --no-cov |
| process-artifacts gate が通る | GitHub Actions の process-artifacts gate |

## 技術 How・KPI

- KPI: new / repeat の売上、件数、平均単価、顧客数、構成比が period / scope 別に read-only で返ること
- 技術選択: period は 1m / 3m / 6m / 12m、scope は team / mine。mine は deals.assigned_to 経由で既存流儀に揃える

## API

- ルート: /api/v1/analytics/revenue-segments
- クエリ:
  - period: 1m / 3m / 6m / 12m
  - scope: team / mine
- レスポンス:
  - new: revenue, order_count, avg_order_amount, customer_count, share
  - repeat: revenue, order_count, avg_order_amount, customer_count, share
  - total: revenue, order_count, customer_count

## 弊害・トレードオフ

- new / repeat の分類は revenue-summary と同じく、当月以前に注文があるかで決まる
- average は order_count が 0 のとき null にするため、ゼロ埋め前提のUIではなく集計表示前提になる
- segment-aware conversion rate は扱わないため、新規開拓の率は既存 funnel 側をそのまま使う

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | segment summary の API と response model を追加 | Generator |
| 2 | SQLite + PostgreSQL RLS の pytest を追加 | Generator |
| 3 | process-artifacts gate と required checks を通す | CI |

## 継続

- 完了後の監視: PR の required checks 確認
- 次フェーズへの引き継ぎ: 新規 / 既存 segment の率や UI 表示の後続 PR
