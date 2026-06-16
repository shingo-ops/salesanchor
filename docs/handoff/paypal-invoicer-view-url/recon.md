# recon — paypal-invoicer-view-url

**仕事名**: paypal-invoicer-view-url  
**日付**: 2026-06-16  
**対象ADR**: ADR-101  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/integrations.py:730` | paypal_test_invoice の UPDATE 文（paypal_invoicer_view_url が欠落していた） |
| `backend/app/services/paypal_payments.py:628` | create_and_send_invoice が invoicer_view_url を返却済み |
| `backend/app/services/paypal_payments.py:543` | _fetch_view_urls が invoicer_view_url を取得する実装 |
| `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:227` | paypal_invoicer_view_url が設定されている場合のみ「原本を開く」ボタンを表示 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `paypal_invoicer_view_url` カラムは既存か | `backend/app/routers/invoices.py` の `_INVOICE_COLUMNS` に含まれることを確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
