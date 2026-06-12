# ADR-136: 取引額集計の SSOT — v_company_stats（公式定義: 入金済み・取消なし）

**Status**: Accepted  
**日付**: 2026-06-12  
**関連**: ADR-108（カルテ受け入れ基準）/ ADR-109（status SSOT）/ ADR-120  
**配置先**: `docs/adr/`

---

## Why

`recon.md`（2026-06-12）で確認した問題：

| 箇所 | 定義 | 食い違い |
|------|------|---------|
| v_company_stats（会社詳細） | `status != 'cancelled'` | 未払い・取消済みを含む |
| InboxKartePanel（カルテ） | `paid_at IS NOT NULL AND voided_at IS NULL` | ADR-108 準拠 |

- 同一テナント内で「会社詳細の取引額」と「カルテの取引額累計」が食い違う状態。
- フロントエンドで全件フェッチ＋クライアント集計しており、件数増加でパフォーマンスリスク。
- 定義変更箇所が複数あり、将来の変更で再び乖離するリスク。

---

## What（決定）

1. **公式定義** = `invoices` テーブルの `paid_at IS NOT NULL AND voided_at IS NULL` の合計  
   （ADR-108 の定義を全アプリの正とする。`status` フィールドで判定しない）

2. **SSOT** = `v_company_stats` ビュー  
   - migration で `status != 'cancelled'` → `paid_at IS NOT NULL AND voided_at IS NULL` に変更
   - `paid_invoice_count`（入金件数）・`last_paid_at`（最終入金日）カラムを追加

3. **カルテ取引実績** = `GET /leads/{lead_id}/stats` API 経由（v_company_stats 由来）  
   - `InboxKartePanel.tsx` のクライアント側全件フェッチ集計を撤去
   - `companies.lead_id` でリード→会社を逆引きし、ビュー値を返す

---

## Scope 外

- analytics / goals の「売上」（`orders.total_amount` ベース）は**受注ベースとして現状維持**。  
  画面上の呼称が「取引額累計」と混同しないか確認推奨（修正は別タスク）。
- 通貨換算・期間集計の高度化は対象外。

---

## 表示値の変化（想定内）

会社詳細の `total_deal_amount` は、未入金・取消分が除外されるため **小さく（正しく）なる**。  
これは修正であってバグではない。

---

## 実装ファイル

| ファイル | 変更内容 |
|---------|---------|
| `migrations/20260612_100000_fix_company_stats_ssot.sql` | ビュー再定義（フィルタ変更・新カラム追加） |
| `backend/app/schemas/lead.py` | `LeadStatsResponse` スキーマ追加 |
| `backend/app/schemas/company.py` | `paid_invoice_count`, `last_paid_at` フィールド追加 |
| `backend/app/routers/companies.py` | `_fetch_company_stats` で新カラムを取得 |
| `backend/app/routers/leads.py` | `GET /leads/{lead_id}/stats` エンドポイント追加 |
| `frontend/src/pages/inbox/InboxKartePanel.tsx` | クライアント集計撤去・stats API 呼び出しに置換 |
| `frontend/tests-e2e/karte-visual-gate.spec.ts` | モック更新（invoices → stats） |
| `backend/tests/test_company_stats.py` | 集計テスト新設 |

---

## 危険カテゴリ

- migration（view 再作成）を含む。
- develop マージは CI 緑で可。
- **本番適用（main → デプロイ）は Shingo の明示 GO 後**。
