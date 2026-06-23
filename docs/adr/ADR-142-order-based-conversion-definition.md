# ADR-142: 成約定義の一本化（受注ベース）

**Status:** Accepted  
**Date:** 2026-06-23  
**Authors:** Generator / ChatGPT Planner  
**PO Approval:** Shingo 2026-06-22  
Amends ADR-094, Amends ADR-107, Amends ADR-138, Amends ADR-139  
**Related:** ADR-021, ADR-094, ADR-107, ADR-119, ADR-138, ADR-139  

---

## Context

Sales Anchor では、同じ「成約」という語が少なくとも 2 つの意味で使われていた。

1. **商談化**: `leads.converted_deal_id` により lead を deal に変換すること
2. **受注成立**: lead の company が order を持つこと

この混在により、`conversion_rate` / `lead_conversion_rate` / 属性別成約率 / 目標 KPI の意味が揺れ、ダッシュボード・分析・目標画面で異なる定義が混在しうる状態だった。

本 ADR では、**「成約」** を受注ベースに一本化し、**商談化** は別概念として温存する。

---

## Decision

### 1. 成約の正式定義

**成約 = lead の company (`companies.lead_id = leads.id`) が、`status != 'cancelled'` の order を持つこと**

- lead 単位で判定する
- `companies.lead_id` から order へ辿る
- `converted_deal_id` は成約判定に使わない
- 重複防止のため、集計は `EXISTS` または lead 単位の `DISTINCT` で行う

### 2. `converted_deal_id` の位置づけ

`converted_deal_id` は **商談化** を表す別概念として残す。

- lead → deal 変換
- 商談ボードや商談ライフサイクルの分析では引き続き利用可能
- ただし **成約率** の定義には使わない

### 3. `conversion_rate` / `lead_conversion_rate` の意味

`conversion_rate` / `lead_conversion_rate` は **受注ベース成約率** を意味する。

- `dashboard.py` の `lead_conversion_rate`
- `analytics.py` の担当者別 / 属性別 / サマリー系 conversion 指標
- `goals.py` の `conversion_rate`

これらはすべて **受注成立** を分母・分子にする。

### 4. ADR-107 の請求勝ち判定補正

`invoices.status` には `cancelled` が存在しないため、請求勝ちの判定は **`status != 'voided'`** に補正する。

---

## Why

- `converted_deal_id` は「商談化」であり、「受注成立」ではない
- 受注ベースに統一することで、ダッシュボード・分析・目標の KPI 名と実態が一致する
- `companies.lead_id` を SSOT として使うことで、lead から order までの経路を一意に追える
- `EXISTS` / `DISTINCT` を使うことで、1 lead に複数 company があっても二重計上しない

---

## Consequences

### 1. 変わるもの

- `dashboard.py` の `lead_conversion_rate`
- `analytics.py` の担当者別 conversion、属性別 conversion、サマリー系 conversion
- `goals.py` の `conversion_rate`

### 2. 変わらないもの

- `converted_deal_id` 自体は削除しない
- `close_rate`（deal の won/lost）は商談指標として温存する
- 既存の商談ボードや商談ライフサイクルは別トラックで扱う

### 3. 実装上の前提

- migration は不要
- 既存列の join だけで算出できる
- RLS の tenant isolation を維持したまま集計する

---

## Implementation surface

- `backend/app/services/conversion_metrics.py`
- `backend/app/routers/dashboard.py`
- `backend/app/routers/analytics.py`
- `backend/app/routers/goals.py`
- `backend/app/services/priority_scoring.py`
- `backend/app/tasks/dashboard.py`
- `backend/tests/test_analytics.py`
- `backend/tests/test_analytics_conversion_by_attribute_rls.py`

---

## Related ADRs

- ADR-094: CRM 定義と商談リネーム
- ADR-107: 分析エージェント (A) 顧客優先度付け
- ADR-138: ファネル型目標対比ダッシュボード 第1弾
- ADR-139: ファネル型目標対比ダッシュボード フロントエンド

