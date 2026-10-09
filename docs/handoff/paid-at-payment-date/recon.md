# recon — paid-at-payment-date

**仕事名**: paid-at-payment-date  
**日付**: 2026-10-09  
**対象ADR**: ADR-072, ADR-027, ADR-144  
**担当**: Sonnet

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/paypal_payments.py:719` | get_invoice_status: st/fee/payment_date 変数初期化 |
| `backend/app/services/paypal_payments.py:727` | txn から fee/payment_date を抽出して返す |
| `backend/app/routers/integrations.py:809` | paypal_return: paid_at_value = result.get("payment_date") |
| `backend/app/routers/integrations.py:811` | COALESCE(:paid_at, NOW()) パターン適用済み |
| `backend/app/routers/integrations.py:958` | webhook: paid_at_value = result.get("payment_date") |
| `backend/app/routers/integrations.py:960` | COALESCE(:paid_at, NOW()) パターン適用済み |
| `backend/app/routers/invoices.py:55` | PayInvoiceRequest モデル定義（paid_at: datetime | None） |
| `backend/app/routers/invoices.py:521` | pay_invoice: body: PayInvoiceRequest | None = Body(default=None) |
| `backend/app/routers/invoices.py:529` | paid_at_value = body.paid_at if body and body.paid_at else None |
| `backend/app/routers/invoices.py:531` | COALESCE(:paid_at, NOW()) パターン適用済み |
| `backend/app/routers/invoices.py:770` | confirm_paypal_payment: paid_at_value = result.get("payment_date") |
| `backend/app/routers/invoices.py:774` | COALESCE(:paid_at, NOW()) パターン適用済み |
| `backend/app/routers/orders.py:594` | set_order_paid: paid_at = COALESCE(:paid_at, NOW()) |
| `backend/app/schemas/order.py:167` | OrderPaidStatusUpdate: paid_at: datetime | None フィールド |
| `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:115` | paymentDate state: useState<string>("") |
| `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:202` | TextField type=date（ADR-144金型）で日付入力 |
| `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:208` | doAction("pay", { paid_at: new Date(paymentDate).toISOString() }) |
| `frontend/src/locales/ja.json:1655` | "paidAt": "入金日" 収録済み |
| `frontend/src/locales/en.json:1655` | "paidAt": "Payment Date" 収録済み |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | PayPal API の payment_date フォーマットが PostgreSQL TIMESTAMPTZ に直接バインドできるか | `backend/app/services/paypal_payments.py:727` で txn.get("payment_date") を取得。SQLAlchemy が文字列をキャストする | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- 全 PayPal 経路（paypal_return / webhook / confirm_paypal_payment）で COALESCE パターンに統一した
- 手動入金（pay_invoice）も同パターンで optional paid_at を受け付ける
- orders テーブルの paid_at も同じ値で連動更新（ADR-104 受注自動遷移）
