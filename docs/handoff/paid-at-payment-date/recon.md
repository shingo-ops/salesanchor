# recon — paid-at-payment-date

**仕事名**: paid-at-payment-date  
**日付**: 2026-10-09  
**対象ADR**: ADR-072, ADR-027, ADR-104, ADR-144  
**担当**: Sonnet（設計: Opus）

---

## 確認した事実（出典付き）

| # | 事実 | 出典 |
|---|------|------|
| 1 | PayPal Invoicing v2 の payments.transactions[].payment_date は schema `date_no_time`（"YYYY-MM-DD"・10文字・時刻/時差なし） | github.com/paypal/paypal-rest-api-specifications openapi/invoicing_v2.json |
| 2 | DBドライバは asyncpg 0.31.0 | backend/app/database.py:8 ／ backend/requirements.txt:5 |
| 3 | asyncpg は timestamptz パラメータに str を渡すと TypeError | asyncpg 公式ソース pgproto/codecs/datetime.pyx timestamptz_encode |
| 4 | 旧実装（本ブランチ初版）は payment_date の文字列をそのまま :paid_at に渡していた → PayPal 入金時に失敗する | git show 752379111:backend/app/routers/integrations.py（paid_at_value = result.get("payment_date")） |
| 5 | 画面は new Date(paid_at).toLocaleDateString() で表示 | frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx（paid_at 表示行）／ InvoicesPage.tsx |
| 6 | 手動の入金確認でも 支払い待ち→仕入れ中（ADR-104 L34/L92） | docs/adr/ADR-104 |
| 7 | SQLite テスト DB の NOW() は固定値 "2026-04-07 00:00:00+00:00" | backend/tests/conftest.py:138 |

---

## file:line 引用表（最新）

| 引用先 | 確認内容 |
|-------|---------|
| `backend/app/services/payment_dates.py:18` | PAID_AT_SQL 定数 |
| `backend/app/services/payment_dates.py:28` | paid_at_from_date（date→UTC正午） |
| `backend/app/services/payment_dates.py:25` | PAYPAL_DATE_RECENT_WINDOW（36時間・時差が最大±1日不明のため） |
| `backend/app/services/payment_dates.py:35` | paypal_paid_at（最近の支払いは None で NOW()） |
| `backend/app/services/payment_dates.py:46` | parse_paypal_payment_date |
| `backend/app/services/paypal_payments.py:730` | get_invoice_status が payment_date を date で返す |
| `backend/app/routers/integrations.py:810` | paypal_return: paypal_paid_at(result.get("payment_date")) |
| `backend/app/routers/integrations.py:812` | invoices UPDATE に PAID_AT_SQL |
| `backend/app/routers/integrations.py:819` | orders UPDATE に PAID_AT_SQL |
| `backend/app/routers/integrations.py:959` | webhook(_handle_invoice_paid): paypal_paid_at |
| `backend/app/routers/integrations.py:961` | webhook invoices UPDATE |
| `backend/app/routers/integrations.py:968` | webhook orders UPDATE |
| `backend/app/routers/invoices.py:56` | PayInvoiceRequest（paid_date: date または None） |
| `backend/app/routers/invoices.py:532` | 未来日（UTC 明日より後）は 422 |
| `backend/app/routers/invoices.py:545` | pay_invoice の orders 連動 UPDATE も PAID_AT_SQL |
| `backend/app/routers/invoices.py:536` | pay_invoice: invoices UPDATE に PAID_AT_SQL |
| `backend/app/routers/invoices.py:775` | confirm_paypal_payment: paypal_paid_at |
| `backend/app/routers/invoices.py:791` | confirm_paypal_payment: orders UPDATE |
| `backend/app/routers/orders.py:595` | set_order_paid は origin/main と同じ（paid_at = NOW()）。ADR-072 の reset_tenant_context のみ追加 |
| `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:106` | localTodayString（ローカル今日） |
| `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:210` | TextFieldControl type=date（max=ローカル今日） |
| `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:217` | doAction("pay", { paid_date }) |
| `frontend/src/locales/ja.json:1655` | "paidAt": "入金日"（既存キー使用） |

---

## 不明点リスト

| # | 不明点 | 状態 |
|---|-------|------|
| 1 | PayPal の payment_date 形式 | 解消（date_no_time、事実1） |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- 初版 InvoiceDetailPage.tsx の flex items-center gap-sm は frontend の CSS に定義が無い（grep 0 件）ため、ラッパー div を廃止。ContentToolbar の right スロット（.content-toolbar__right は flex・gap 付き）にそのまま並べる
