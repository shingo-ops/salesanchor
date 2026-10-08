# recon: paid-at-payment-date

## 調査日
2026-10-09

## 対象ADR
- ADR-072: write endpoint の db.commit() 直後に reset_tenant_context() 必須
- ADR-027: UI文字列は t("key") 経由
- ADR-144: UIコンポーネントは金型使用

## 調査ファイル

### backend/app/services/paypal_payments.py
- `get_invoice_status` 関数（行 719-735）
- 現状: `payment_date = None` の初期化のみ、`txn.get("payment_date")` で抽出されていない
- 変更: txn から `payment_date` を抽出して返す

### backend/app/routers/integrations.py
- `paypal_return` 関数（行 801-830）: `paid_at = NOW()` ハードコード
- `_handle_invoice_paid` webhook（行 953-978）: `paid_at = NOW()` ハードコード
- 変更: COALESCE(:paid_at, NOW()) + payment_date バインド

### backend/app/routers/invoices.py
- `PayInvoiceRequest` クラス（行 55-57）: モデル定義あり
- `pay_invoice` 関数（行 521-550）: ボディ受け取り・COALESCE 実装済み
- `confirm_paypal_payment` 関数（行 769-789）: COALESCE 実装済み

### backend/app/routers/orders.py
- `set_order_paid` 関数（行 569-618）: `OrderPaidStatusUpdate.paid_at` 使用・COALESCE 実装済み

### backend/app/schemas/order.py
- `OrderPaidStatusUpdate`（行 167-175）: `paid_at: datetime | None` フィールドあり

### frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx
- `paymentDate` state（行 115）: `useState<string>("")` 追加済み
- TextField type=date（行 202-207）: ADR-144 金型使用済み
- doAction call（行 208）: `{ paid_at: new Date(paymentDate).toISOString() }` 送信済み

### frontend/src/locales/ja.json
- `"paidAt": "入金日"` 行 1655 に存在

### frontend/src/locales/en.json
- `"paidAt": "Payment Date"` 行 1655 に存在
