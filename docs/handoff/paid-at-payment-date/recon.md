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
| 2 | DBドライバは asyncpg 0.31.0 | /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/database.py:8 ／ /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/requirements.txt:5 |
| 3 | asyncpg は timestamptz パラメータに str を渡すと TypeError | asyncpg 公式ソース pgproto/codecs/datetime.pyx timestamptz_encode |
| 4 | 旧実装（本ブランチ初版）は payment_date の文字列をそのまま :paid_at に渡していた → PayPal 入金時に失敗する | git show 752379111:backend/app/routers/integrations.py（paid_at_value = result.get("payment_date")） |
| 5 | 画面は new Date(paid_at).toLocaleDateString() で表示 | /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx（paid_at 表示行）／ InvoicesPage.tsx |
| 6 | 手動の入金確認でも 支払い待ち→仕入れ中（ADR-104 L34/L92） | docs/adr/ADR-104 |
| 7 | SQLite テスト DB の NOW() は固定値 "2026-04-07 00:00:00+00:00" | /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/tests/conftest.py:138 |

---

## file:line 引用表（最新）

| 引用先 | 確認内容 |
|-------|---------|
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/services/payment_dates.py:19 | PAID_AT_SQL 定数 |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/services/payment_dates.py:25 | paid_at_from_date（date→UTC正午） |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/services/payment_dates.py:30 | parse_paypal_payment_date |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/services/paypal_payments.py:730 | get_invoice_status が payment_date を date で返す |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/routers/integrations.py:810 | paypal_return: paid_at_from_date(result.get("payment_date")) |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/routers/integrations.py:812 | invoices UPDATE に PAID_AT_SQL |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/routers/integrations.py:819 | orders UPDATE に PAID_AT_SQL |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/routers/integrations.py:959 | webhook(_handle_invoice_paid): paid_at_from_date |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/routers/integrations.py:961 | webhook invoices UPDATE |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/routers/integrations.py:968 | webhook orders UPDATE |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/routers/invoices.py:56 | PayInvoiceRequest（paid_date: date または None） |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/routers/invoices.py:532 | 未来日（UTC 明日より後）は 422 |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/routers/invoices.py:536 | pay_invoice: invoices UPDATE に PAID_AT_SQL |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/routers/invoices.py:775 | confirm_paypal_payment: paid_at_from_date |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/routers/invoices.py:791 | confirm_paypal_payment: orders UPDATE |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/backend/app/routers/orders.py:595 | set_order_paid は origin/main と同じ（paid_at = NOW()）。ADR-072 の reset_tenant_context のみ追加 |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:106 | localTodayString（ローカル今日） |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:210 | TextFieldControl type=date（max=ローカル今日） |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:217 | doAction("pay", { paid_date }) |
| /Users/tanizawashingo/worktrees/salesanchor/release-paid-at-payment-date/frontend/src/locales/ja.json:1655 | "paidAt": "入金日"（既存キー使用） |

---

## 不明点リスト

| # | 不明点 | 状態 |
|---|-------|------|
| 1 | PayPal の payment_date 形式 | 解消（date_no_time、事実1） |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- invoices.py の flex items-center gap-sm は frontend の CSS に定義が無い（grep 0 件）ため、ラッパー div を廃止。ContentToolbar の right スロット（.content-toolbar__right は flex・gap 付き）にそのまま並べる
