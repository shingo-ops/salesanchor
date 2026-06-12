# Recon: 取引額 SSOT 化（v_company_stats 一本化）

**作成日**: 2026-06-12  
**ブランチ**: temp-detach-head  
**目的**: 顧客ごとの取引額の計算が何か所に散らばり、定義がどう食い違っているかを実コードで確定する

---

## 1. v_company_stats の現状

### 定義ファイル

```
migrations/20260604_100000_create_company_stats_view.sql:38-60
```

### 計算式（抜粋）

```sql
CREATE OR REPLACE VIEW %I.v_company_stats AS
SELECT
    c.id AS company_id,
    COALESCE(SUM(i.total_amount), 0) AS total_deal_amount,   -- :42
    COUNT(DISTINCT d.id) AS deal_count,
    COUNT(DISTINCT cl.id) AS conversation_count,
    MAX(cl.occurred_at) AS last_conversation_at
FROM %I.companies c
LEFT JOIN %I.invoices i
    ON i.company_id = c.id AND i.status != 'cancelled'       -- :48 ← フィルタ条件
LEFT JOIN %I.deals d ON d.company_id = c.id
LEFT JOIN %I.conversation_logs cl ON cl.company_id = c.id
GROUP BY c.id
```

### キーポイント

| 項目 | 内容 |
|------|------|
| 対象テーブル | `invoices` |
| フィルタ条件 | `status != 'cancelled'` のみ |
| `paid_at` の扱い | **無視**（NULL でも含む） |
| `voided_at` の扱い | **無視**（NULL でも含む） |
| テナント分離 | あり（スキーマループ `migrations/20260604_100000_create_company_stats_view.sql:24-60`） |
| 集計値 | `total_deal_amount`, `deal_count`, `conversation_count`, `last_conversation_at` |

**→ 未払い（issued/overdue）・支払い済み・無効化済み を区別せず合計している。**

---

## 2. 「取引額・売上・累計」系の計算箇所 全列挙

### 2-A. バックエンド

#### (1) v_company_stats 経由（会社詳細 API）

```
backend/app/routers/companies.py:193-194
```
```python
SELECT total_deal_amount, deal_count, conversation_count, last_conversation_at
FROM v_company_stats
WHERE company_id = :company_id
```
- フィルタ: `status != 'cancelled'`（ビューの定義に準ずる）
- 用途: 顧客一覧・顧客詳細の `total_deal_amount` フィールド
- スキーマ: `backend/app/schemas/company.py:197`（`total_deal_amount: Optional[Decimal]`）

---

#### (2) ダッシュボード KPI — invoices の unpaid amount

```
backend/app/routers/dashboard.py:176-177
```
```sql
SELECT
    COUNT(*) FILTER (WHERE status IN ('issued', 'overdue')) AS unpaid_count,
    COALESCE(SUM(total_amount) FILTER (WHERE status IN ('issued', 'overdue')), 0) AS unpaid_amount
FROM invoices
```
- フィルタ: `status IN ('issued', 'overdue')`
- 用途: ダッシュボード「未払い請求額」カード
- 取引額合計とは別の概念（未回収）

---

#### (3) ダッシュボード KPI — orders の受注合計

```
backend/app/routers/dashboard.py:156-157
```
```sql
SELECT
    COUNT(*) FILTER (WHERE status = 'pending') AS pending_count,
    COALESCE(SUM(total_amount), 0) AS total_amount
FROM orders
```
- ソーステーブル: `orders`（invoices ではない）
- フィルタ: なし（全ステータス合計）
- 用途: ダッシュボード「受注合計」カード

---

#### (4) ダッシュボード KPI — deals の商談金額

```
backend/app/routers/dashboard.py:124-127
```
```sql
SELECT
    COUNT(*) FILTER (WHERE status = 'open') AS open_count,
    COUNT(*) FILTER (WHERE status = 'won') AS won_count,
    COALESCE(SUM(amount), 0) AS total_amount,
    COALESCE(SUM(amount) FILTER (WHERE status = 'won'), 0) AS won_amount
FROM deals
```
- ソーステーブル: `deals.amount`（invoices でも orders でもない）
- 用途: ダッシュボード「商談パイプライン」「成約済み金額」

---

#### (5) 分析 KPI サマリー（analytics.py）— orders を「売上」として使用

```
backend/app/routers/analytics.py:482-492
```
```sql
SELECT
    COALESCE(SUM(total_amount), 0) AS revenue,
    COUNT(*) AS cnt,
    COUNT(*) FILTER (WHERE status IN ('pending', 'processing', 'shipped')) AS active
FROM orders
WHERE created_at::date >= :start AND created_at::date <= :end
```
- ソーステーブル: `orders`（invoices ではない）
- フィルタ: 期間のみ（ステータスフィルタなし、全注文を合計）
- 用途: 分析ページ「売上」KPI カード（前期比含む）

---

#### (6) 月次売上グラフ（analytics.py）— orders を「実績」として使用

```
backend/app/routers/analytics.py:663  （日次）
backend/app/routers/analytics.py:708  （月次）
```
```sql
SELECT
    TO_CHAR(DATE_TRUNC('day'/'month', created_at), ...) AS label,
    COALESCE(SUM(total_amount), 0) AS actual
FROM orders
WHERE created_at >= :start AND created_at < :end
```
- ソーステーブル: `orders`（invoices ではない）
- フィルタ: 期間のみ、ステータス不問
- 用途: 分析ページ「月次売上グラフ」

---

#### (7) 目標 KPI（goals.py）— orders を「売上」として使用

```
backend/app/routers/goals.py:319-328
```
```python
# 売上（受注の total_amount）
SELECT COALESCE(SUM(total_amount), 0) AS val
FROM orders
WHERE created_at >= :start AND created_at < :end
```
- ソーステーブル: `orders`（invoices ではない）
- フィルタ: 期間のみ
- 用途: 目標ページの「売上」KPI 達成率

---

#### (8) 延滞請求レポート（analytics.py）

```
backend/app/routers/analytics.py:183-205
```
```sql
SELECT id, invoice_number, company_id, total_amount, currency, due_date, ...
FROM invoices
WHERE status IN ('issued', 'overdue')
  AND due_date < CURRENT_DATE
```
- ソーステーブル: `invoices`
- フィルタ: `status IN ('issued', 'overdue') AND due_date < CURRENT_DATE`
- 合計は Python で後処理: `backend/app/routers/analytics.py:203`（`sum(i.total_amount or 0 for i in invoices)`）
- 用途: 延滞請求一覧の「合計」表示

---

#### (9) 受注財務 月次サマリー（order_financials.py）

```
backend/app/routers/order_financials.py:337-349
```
```sql
COALESCE(SUM(revenue_amount), 0) AS revenue_total
FROM order_financials
```
- ソーステーブル: `order_financials`（invoices でも orders でもない専用テーブル）
- 用途: 財務管理ページの月次 P&L
- `gross_profit = revenue_total - cost_total`（`backend/app/routers/order_financials.py:356`）

---

### 2-B. フロントエンド（受け取り値をさらに加工）

#### (1) InboxKartePanel — 取引額累計（最重要）

```
frontend/src/pages/inbox/InboxKartePanel.tsx:558-575
```
```typescript
// Fetch invoices for total revenue + order count + last order date
// ...
const paid = invoices.filter((inv) => inv.paid_at != null && inv.voided_at == null);  // :565
const total = paid.reduce((sum, inv) => sum + (Number(inv.total_amount) || 0), 0);    // :567
// ...
setLastOrderDate(sorted[0].paid_at ?? null);  // :575
```
- データ元: `GET /invoices?lead_id=${leadId}` で全件取得してクライアントでフィルタ
- フィルタ: `paid_at IS NOT NULL AND voided_at IS NULL`
- 用途: カルテ「顧客タブ」の取引額累計 / 取引回数 / 最終取引日（`:616`, `:623`）

---

#### (2) 帳票作成フォームの小計計算（フォーム内部）

以下はすべて「フォーム内の行計算」であり、DB集計値とは無関係。

```
frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:187-189
frontend/src/pages/quote-create/QuoteCreatePage.tsx:114-116
frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:96
```

---

## 3. 各箇所の計算式差分表

| 箇所 | ソーステーブル | フィルタ条件 | paid_at の扱い | voided_at の扱い | status の扱い |
|------|--------------|------------|---------------|-----------------|--------------|
| **ADR-108 公式定義** | invoices | paid_at IS NOT NULL AND voided_at IS NULL | **必須** | **除外必須** | 使わない |
| v_company_stats | invoices | status != 'cancelled' | 無視 | 無視 | cancelled のみ除外 |
| InboxKartePanel (FE) | invoices | paid_at IS NOT NULL AND voided_at IS NULL | **必須** | **除外必須** | 使わない |
| dashboard.py unpaid | invoices | status IN ('issued', 'overdue') | 無視 | 無視 | issued/overdue のみ |
| dashboard.py orders | orders | なし（全件） | — | — | なし |
| analytics.py KPI | orders | 期間のみ | — | — | なし |
| analytics.py monthly | orders | 期間のみ | — | — | なし |
| analytics.py overdue | invoices | status IN ('issued','overdue') AND due_date past | 無視 | 無視 | issued/overdue |
| goals.py revenue | orders | 期間のみ | — | — | なし |
| order_financials.py | order_financials | （独自） | — | — | — |

**— は「そのカラムが対象テーブルに存在しない or 集計の概念外」を示す。**

---

## 4. v_company_stats を使っている箇所 vs 自前計算

### v_company_stats を参照している箇所

| ファイル | 行番号 | 用途 |
|----------|--------|------|
| `backend/app/routers/companies.py` | 193-194 | 会社詳細・会社一覧 API |
| `backend/app/schemas/company.py` | 197 | `total_deal_amount` フィールド定義 |

**→ v_company_stats の利用は companies.py の 1 箇所のみ。**

### 自前計算（v_company_stats を使わない）箇所

| ファイル | 行番号 | ソース | 用途 |
|----------|--------|--------|------|
| `frontend/src/pages/inbox/InboxKartePanel.tsx` | 558-575 | invoices (fetch全件) | カルテ取引額累計 |
| `backend/app/routers/analytics.py` | 482-492 | orders | 分析KPI売上 |
| `backend/app/routers/analytics.py` | 663, 708 | orders | 月次売上グラフ |
| `backend/app/routers/goals.py` | 319-328 | orders | 目標KPI売上 |
| `backend/app/routers/dashboard.py` | 156-157 | orders | ダッシュボード受注合計 |
| `backend/app/routers/dashboard.py` | 176-177 | invoices (未払い) | ダッシュボード未払い額 |
| `backend/app/routers/analytics.py` | 183-205 | invoices (延滞) | 延滞請求レポート |
| `backend/app/routers/order_financials.py` | 337-349 | order_financials | 財務月次P&L |

---

## 5. ADR-108 定義の実装確認

**ADR-108 の定義**（`docs/adr/ADR-108-inbox-karte-panel-redesign.md:40`）:
> 取引額＝`invoices` の `paid_at` 非NULL かつ `voided_at` NULL の合計。判定は `status` ではなく invoice データ。

**受け入れ条件**（`docs/adr/ADR-108-inbox-karte-panel-redesign.md:107`）:
> 取引額累計は、`invoices` の `paid_at` 非NULL かつ `voided_at` NULL の合計に一致する。

### 実装状況

| 箇所 | ADR-108 準拠 | 備考 |
|------|-------------|------|
| `frontend/src/pages/inbox/InboxKartePanel.tsx:565` | **準拠** | `paid_at != null && voided_at == null` のフィルタを適用 |
| `v_company_stats`（migrations:48） | **非準拠** | `status != 'cancelled'` のみ。paid_at/voided_at を無視 |
| backend `backend/app/routers/companies.py:193` | **非準拠** | v_company_stats 経由のため同上 |

**ADR-108 を正しく実装しているのはフロントエンドの InboxKartePanel のみ。**  
バックエンドの SSOT（v_company_stats）は ADR-108 と矛盾した定義を持っている。

---

## 6. 一本化した場合の影響範囲

### 変更が必要な箇所

ADR-108 定義（`paid_at IS NOT NULL AND voided_at IS NULL`）を SSOT とした場合:

#### 必須変更

| 対象 | 変更内容 | 表示値の方向 |
|------|----------|------------|
| `migrations/20260604_100000_create_company_stats_view.sql:48` | `AND i.status != 'cancelled'` → `AND i.paid_at IS NOT NULL AND i.voided_at IS NULL` | **減少**（未払い請求が除外される） |

#### 連鎖影響（v_company_stats 変更後）

| ファイル | 行番号 | 画面 | 表示値の変化 |
|----------|--------|------|------------|
| `backend/app/routers/companies.py:193-194` | 自動追従 | 会社詳細・会社一覧の `total_deal_amount` | **減少**（未払い・voided 分が落ちる） |
| `backend/app/schemas/company.py:197` | 変更不要 | — | — |

#### 別途対応が必要な箇所（v_company_stats 一本化とは独立）

以下は「ソーステーブルが orders」であり、invoices とは別の概念のため SSOT 化の影響外。
ただし「売上 = 受注額」vs「売上 = 入金済み請求額」の概念統一は別途判断が必要:

| ファイル | 行番号 | 現在の「売上」定義 |
|----------|--------|-----------------|
| `backend/app/routers/analytics.py:486` | 分析KPI | orders.total_amount（全件・期間フィルタのみ） |
| `backend/app/routers/analytics.py:663` | 月次グラフ | orders.total_amount（全件・期間フィルタのみ） |
| `backend/app/routers/goals.py:322` | 目標KPI | orders.total_amount（全件・期間フィルタのみ） |

#### フロントエンド変更

| ファイル | 行番号 | 変更方針 |
|----------|--------|---------|
| `InboxKartePanel.tsx:558-575` | カルテ取引額 | v_company_stats の API を呼ぶように変更可（現在フロントでフィルタ中） |

---

## 7. 取引額系の値に依存する既存テスト

| ファイル | 行番号 | テスト名 / 内容 | 何を検証 |
|----------|--------|---------------|---------|
| `backend/tests/test_dashboard.py:72-73` | `test_dashboard_kpi_empty` | `deal_total_amount == 0.0`, `order_total_amount == 0.0` | ゼロ状態のアサーション |
| `backend/tests/test_dashboard.py:40,45,50` | fixture | `orders.total_amount` 50000/80000/120000 | テストデータ作成 |
| `backend/tests/test_invoices.py:362` | 支払い操作後 | `paid_at is not None` | 支払い後に paid_at が設定されること |
| `backend/tests/test_invoices.py:652-653` | 新規作成後 | `paid_at: None`, `voided_at: None` | 初期値がNULL |
| `backend/tests/test_invoices.py:243,319` | 合計金額 | `total_amount == 2600.0 / 7500.0` | 行計算の正確性 |
| `backend/tests/test_celery.py:123-124` | Celery 通知 | `deal_total_amount`, `order_total_amount` をペイロードに含む | 通知メッセージのフォーマット |
| `backend/tests/test_orders.py:316,344` | ソート | `sort_by_total_amount_desc/asc` | 金額ソートの動作 |
| `backend/tests/test_orders.py:674` | 新規作成 | `paid_at is null` | 注文初期値 |
| `frontend/src/pages/quotes/quotesSort.test.ts:48,50` | ソート | `total_amount` フィールドでのソート | フロントのソート |

**v_company_stats 自体のテストは存在しない。**  
`paid_at IS NOT NULL AND voided_at IS NULL` の集計ロジックをカバーするバックエンドテストも存在しない。

---

## 要約：主要な食い違い 3 点

### 食い違い A（最優先）: v_company_stats と ADR-108 の定義不一致

| | フィルタ | issued（未払い）を含む | voided を含む |
|--|---------|---------------------|--------------|
| ADR-108 公式定義 | paid_at IS NOT NULL AND voided_at IS NULL | **含まない** | **含まない** |
| v_company_stats | status != 'cancelled' | **含む** | **含む** |
| InboxKartePanel (FE) | paid_at != null && voided_at == null | 含まない | 含まない |

**結果**: 会社詳細の `total_deal_amount` はカルテの「取引額累計」より大きな値を表示する可能性がある。

### 食い違い B: 「売上」のソーステーブルが analytics/goals では orders、v_company_stats では invoices

analytics.py・goals.py の「売上」は `orders.total_amount`（受注ベース）であり、
v_company_stats の `total_deal_amount` は `invoices.total_amount`（請求ベース）。
これらは別概念であり、SSOT 化の範囲定義が必要。

### 食い違い C: フロントエンドが唯一 ADR-108 準拠だが、全件フェッチで実装

InboxKartePanel は `/invoices?lead_id=...` で全件取得しクライアントでフィルタしており、
件数増加に伴うパフォーマンスリスクがある。SSOT API を作れば排除できる。
