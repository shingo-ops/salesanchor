# recon — PayPal を Invoicing 方式へ移行（案Y 併存）

対象: PayPal 決済を Checkout/Orders（決済リンク）から **Invoicing API（PayPal が請求書をメール送付＋ホスト決済）** へ切替。自社請求書は SSOT のまま併存。**migration なし**（既存列流用）。設計正本: **ADR-101 改訂 2026-06-12**。

実コードを **フルパス:行番号** で突合（短縮禁止）。

## 1. PayPal Invoicing API（公式確認済 2026-06-12）
- 作成: `POST /v2/invoicing/invoices`（`detail.currency_code`/`detail.invoice_number`(自社IN-NNNN可)/`detail.reference`(自社参照"tenant:invoice")/`invoicer.name`/`primary_recipients[].billing_info.email_address`/`items[].name,quantity,unit_amount{currency_code,value}`）→ レスポンス id 例 `INV2-XXXX-XXXX-XXXX-XXXX`。
- 送付: `POST /v2/invoicing/invoices/{id}/send`（`send_to_recipient=true`）→ PayPal が顧客にメール＋決済リンク。
- 取得: `GET /v2/invoicing/invoices/{id}` → `status`(DRAFT/SENT/UNPAID/PAID/CANCELLED/OVERDUE)、`detail.metadata.recipient_view_url`(顧客が支払うホストページ)。
- 入金 webhook: **`INVOICING.INVOICE.PAID`**（他: CANCELLED/REFUNDED/UPDATED/CREATED）。署名検証は既存 `verify_webhook`（verify-webhook-signature）を流用。
- 出典: developer.paypal.com/docs/invoicing/integrate, /api/invoicing/v2, /api/rest/webhooks/event-names。

## 2. 自社モデル（流用）
- contacts に `primary_email VARCHAR(255)`（`backend/app/services/tenant.py:195`・conftest `contacts.primary_email`）＝PayPal 送付先。**email 必須**。
- invoices の既存 PayPal 列（Increment 1）: `paypal_order_id`/`paypal_approval_url`/`payment_fee`。→ **流用**: `paypal_order_id`=PayPal Invoice ID(INV2-)、`paypal_approval_url`=`recipient_view_url`、`payment_fee`=手数料。**migration 不要**。

## 3. 置換対象コード（現行 Orders 方式）
- `backend/app/services/paypal_payments.py:213`(`create_order`)/`:303`(`capture_order`)/`:379`(`make_return_token`)/`:432`(`register_webhook`= CHECKOUT.ORDER.APPROVED 購読)/`:465`(`verify_webhook`・流用)。
- `backend/app/routers/invoices.py:599`(`issue_paypal_link`= create_order→決済リンク・`:624-631`)/`:663`(`paypal-confirm`= capture_order `:688`)。→ Invoicing(create+send / status取得)へ置換。
- `backend/app/routers/integrations.py:523`(save時 register_webhook)/`:584`(`test-invoice`= create_order `:668`)/`:802`(`paypal_webhook`= `CHECKOUT.ORDER.APPROVED` `:807`、capture `:855`)/`:580`付近(`paypal_return` 公開 capture)。→ webhook を `INVOICING.INVOICE.PAID` へ、test-invoice を Invoicing へ。`paypal_return`/`paypal_cancel` は Invoicing では不要（PayPal がホスト）→ dormant 化（削除はしない・既存テスト維持）。
- 既存テスト: `test_paypal_payment_link.py`(create_order/capture_order)/`test_paypal_return.py`(token)/`test_paypal_webhook.py`(register/verify) は **create_order/capture_order/make_return_token/verify_webhook 関数を残せば維持**（関数は dormant でも残す）。register_webhook の event 名変更は body 内なのでテスト不破壊（テストは webhook_id のみ assert）。

## 4. webhook ルーティング
- 旧: `custom_id`("tenant:invoice")。新: PayPal Invoice の **`detail.reference`** に "tenant:invoice" を埋め、`INVOICING.INVOICE.PAID` の resource から reference を取り出してルーティング。resource 構造は `resource.invoice.detail.reference` or `resource.detail.reference`（防御的に両対応）。PayPal Invoice ID は `resource.invoice.id` or `resource.id`。

## 5. フロント・i18n
- `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx`(paypal-link/confirm ボタン・linkHint)/`PaypalIntegrationPage.tsx`(決済テスト)。文言を「PayPal請求書を送付」「支払い状況を確認」へ更新。i18n `invoices.paypal.*`/`paypalIntegration.payTest*`。

## 6. 制約・範囲外
- email 未登録 contact は 400。test-invoice の PayPalテスト contact に placeholder email を設定。
- PDF は自社生成のまま（PayPal は API で PDF 不可）。
- 旧 Orders 経路は dormant（段階整理）。本番では Invoicing 一本化。
