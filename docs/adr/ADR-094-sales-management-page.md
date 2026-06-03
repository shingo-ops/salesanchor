# ADR-094: 売上管理ページ（Single Source of Truth）

## Status
**Proposed** — 未着手・実装禁止。

> ⚠️ **実装着手禁止**
> このADRは設計の方向性を記録したものであり、詳細仕様はまだ確定していません。
> POとの壁打ちが完了していないため、いかなるエージェント・開発者も
> POの明示的な指示なしに実装を開始してはなりません。
> 「Proposed」のまま放置されていても自動着手・解釈着手は禁止です。

**着手条件（両方を満たすこと）:**
1. 既存ページ（受注管理・請求書・顧客管理）の粒度向上が完了していること
2. POが「ADR-093の実装を開始して」と明示的に指示していること

## Context

現状、1取引のデータが複数ページに分散している。

- 受注管理: 受注の作成・編集・ステータス管理
- 請求書ページ: 請求・入金管理
- ダッシュボード: 売上の集計サマリー

1取引における詳細データを横断的に見るページが存在しない。

## Decision

売上管理ページ（`/sales`）を新規作成し、`orders` テーブルを母体とした Single Source of Truth を確立する。

## Business Flow（対象範囲）

```
【対象外】見積もり提示
          ↓
【ここから売上管理の対象】
① 成約 → 受注データ入力（会社・担当者・金額）
② 請求書発行
③ 入金確認
④ 仕入れ手続き
⑤ 発送手続き → 発送通知送信
⑥ 到着確認 → 取引完了
```

見積書（quotes）は対象外。

## DB設計

### 新規テーブル: なし

### 追加カラム（Migration 102・additive only）

```sql
-- 取引完了日時（売上認識日・期間フィルタに必要）
ALTER TABLE orders
  ADD COLUMN closed_at TIMESTAMPTZ;

-- 発送通知送信日時
ALTER TABLE order_shipping_details
  ADD COLUMN notification_sent_at TIMESTAMPTZ;

CREATE INDEX idx_orders_closed_at ON orders (tenant_id, closed_at);
```

### 新規VIEW: v_sales_transactions

`orders` を中心に以下をJOIN:
- `order_financials` — 売上額・粗利・各原価
- `order_shipping_details` — 発送情報・通知日時
- `order_purchase_details` — 仕入情報
- `order_commissions` — 担当者報酬
- `invoices` — 請求書番号・入金日・入金額
- `deals` — 担当営業（assigned_to）

## 売上管理ページに表示するデータ定義

| カテゴリ | フィールド | ソース |
|---|---|---|
| 受注 | 受注番号・成約日・会社名・担当者・担当営業・受注金額 | orders / deals |
| 請求書 | 請求書番号・請求金額・請求日・支払期限・通貨 | invoices |
| 入金 | 入金日・入金方法・入金額（JPY/USD）・為替レート | invoices |
| 仕入れ | 仕入先・仕入金額・仕入日・担当者 | order_purchase_details |
| 発送 | 配送業者・追跡番号・発送日・発送通知日・届け先国 | order_shipping_details |
| 完了 | 完了日時・ステータス | orders |
| 財務 | 売上額・仕入原価・粗利・粗利率・各手数料 | order_financials |

## API設計

```
GET /sales/transactions          一覧（フィルタ: 期間・担当営業・会社・ステータス）
GET /sales/transactions/{id}     1取引の全データ
GET /sales/summary               集計（合計売上・粗利・粗利率・件数）
```

## 実装順序

1. Migration 102（2カラム追加 + VIEW作成）
2. バックエンド `/sales/` ルーター
3. フロントエンド SalesPage（読み取り専用・フィルタ・集計行）
4. ダッシュボードの集計を `/sales/summary` に切り替え
5. Google Drive エクスポート追加

## Consequences

- 新テーブル不要のため既存データへの影響なし
- 各ページ（受注管理・請求書）は引き続き独自エンドポイントで動作
- ダッシュボードの集計ロジックが `/sales/summary` に一本化される
