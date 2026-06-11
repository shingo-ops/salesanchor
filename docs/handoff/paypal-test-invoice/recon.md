# recon — PayPal 決済テストボタン（テスト請求書ワンクリック発行）

対象: PayPal 連携ページの「決済テスト」ボタン→**sandbox 限定**で専用「PayPalテスト」会社/担当者＋小額(¥100)テスト請求書を自動作成・発行・PayPal リンク発行→戻りURL/webhook/手動の3方式を確認可能にする。**migration 不要**。

実コードを **フルパス:行番号** で突合（短縮禁止）。

## 1. 請求書作成ロジック（流用元）
- `backend/app/routers/invoices.py:327`（`create_invoice`）。採番 `next_id = MAX(id)+1`（`backend/app/routers/invoices.py:361`）→`invoice_number = f"IN-{next_id:04d}-01"`（`:363`）、`erp_key = uuid[:8]`（`:364`）。INSERT invoices（status 'draft'・branch 1）（`:366-396`）＋ INSERT invoice_items（`:401-411`）。
- 発行: `issue_invoice`（`backend/app/routers/invoices.py:477` 付近）= `UPDATE ... status='issued', issued_at=NOW() WHERE status='draft'`。
- PayPal リンク発行: `issue_paypal_link`（`backend/app/routers/invoices.py:596`）= creds→`create_order`(custom_id=tenant:invoice)→`UPDATE paypal_order_id/paypal_approval_url`。

## 2. 会社/担当者の最小必須列（自動作成用）
- `companies`（`backend/app/services/tenant.py:147`）：必須 = `company_code VARCHAR(20) NOT NULL`（`:149`）、`name VARCHAR(255) NOT NULL`（`:151`）。他は nullable。
- `contacts`（`backend/app/services/tenant.py:184`）：必須 = `company_id NOT NULL`（`:186`）、`contact_code VARCHAR(20) NOT NULL`（`:187`）。surname/given_name/display_name は nullable、`is_primary_contact` default false。

## 3. PayPal サービス（流用）
- `backend/app/services/paypal_payments.py:61`（`get_credentials`→`{client_id,client_secret,environment}`）/ `:213`（`create_order`・custom_id 対応済）/ `:371`（`make_return_token`）。
- 環境判定: creds["environment"]（'sandbox'/'live'）。**'sandbox' 以外は拒否**（実課金防止）。

## 4. 公開/認証・テナント文脈
- 既存 PayPal テスト endpoint は `backend/app/routers/integrations.py:538`（`paypal_test_connection`・`require_permission` 経由）。test-invoice も `integrations.py` の認証必須 router に追加。
- `_API_BASE_URL`（`backend/app/routers/integrations.py:51` 付近・Increment 2.5 で追加）で return_url 生成。書込後 `reset_tenant_context`（ADR-072）。

## 5. フロント PayPal ページ
- `frontend/src/pages/integrations/PaypalIntegrationPage.tsx:76`（`handleTest`→`api.post("/integrations/paypal/test-connection")`）。`status.configured`（`:31`）でガード。接続テストセクション（`:165-172`）。
- → 「決済テスト」セクションを追加し `handlePaymentTest`→新 endpoint→返ってきた approval_url/invoice リンクを表示。i18n `paypalIntegration.*`。

## 6. 範囲外/注意
- **sandbox 限定**（live は実課金になるため endpoint 側で拒否）。テストデータ（PayPalテスト会社/担当者/請求書）は残るが独立（PO 選択 B）。
- conftest に companies/contacts/invoices あり（既存テスト稼働）＝SQLite でも INSERT 可。tenant_paypal_config は conftest 未定義（service モック）。
