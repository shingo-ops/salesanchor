# design — PayPal 決済テストボタン（テスト請求書ワンクリック発行）

参照: recon = `docs/handoff/paypal-test-invoice/recon.md` ／ 関連 ADR: **ADR-101**（請求書・PayPal発行モード）。SOP: `docs/STANDARD-WORKFLOW.md`。Increment 1/2/2.5: `docs/handoff/paypal-payment-link|paypal-auto-confirm|paypal-webhook/`。

## 0. KGI（PO 承認 2026-06-11「B でOK」）
PayPal 連携ページの「決済テスト」ボタン1つで、**sandbox 限定**・専用「PayPalテスト」会社/担当者＋¥100 テスト請求書を自動作成・発行・PayPal リンク発行し、**戻りURL自動／webhook自動／手動の3方式を実機確認**できる。**migration なし**。

## 1. 外部・過去事例の参照と我々への応用
- **過去事例（自社・create_invoice）**：`invoices.py create_invoice` の採番・INSERT・items 作成（recon §1）をテスト用に最小化して流用（独自採番ロジックを増やさない）。
- **過去事例（自社・接続テスト）**：`integrations.py paypal_test_connection` ＋ フロント `handleTest` の「ボタン→POST→結果表示」パターン（recon §4,§5）を踏襲。
- **過去事例（自社・PayPal リンク）**：Increment 1 の `issue_paypal_link` と同じ `create_order(custom_id)`→`paypal_order_id/approval_url` 保存（recon §1,§3）。テスト経路でも本番と同じ発行ロジックを使い乖離を防ぐ。
- **PayPal 公式**：sandbox 環境はテスト用（実課金なし）。本機能は creds.environment=='sandbox' のときのみ動作させ、live 実課金を防ぐ。

## 2. 技術 How
### 2.1 backend `integrations.py`（認証必須・admin）
新 endpoint `POST /integrations/paypal/test-invoice`（`require erp.view`＋`_require_admin`）:
1. `get_credentials`→無ければ 400。**`environment != 'sandbox'` なら 400「本番環境ではテストできません」**（実課金防止）。
2. 「PayPalテスト」会社 find-or-create：`SELECT id FROM companies WHERE company_code='PAYPAL-TEST'`→無ければ INSERT（company_code='PAYPAL-TEST', name='PayPal決済テスト'）。
3. 担当者 find-or-create：`SELECT id FROM contacts WHERE company_id=:cid AND contact_code='PAYPAL-TEST'`→無ければ INSERT（contact_code='PAYPAL-TEST', display_name='PayPal Test'）。
4. 請求書作成（create_invoice 最小流用）：`next_id=MAX(id)+1`、`IN-{n:04d}-01`、currency='JPY'、subtotal/total=100、status='issued'（発行済で作成）、branch 1、erp_key。INSERT invoice_items（'PayPal決済テスト'×1・¥100）。
5. `create_order(env, cid, csec, 100, 'JPY', invoice_number, return_url, cancel_url, f"{tenant_id}:{invoice_id}")`→`UPDATE invoices SET paypal_order_id, paypal_approval_url, payment_method='paypal'`。return_url=`{_API_BASE_URL}/api/v1/integrations/paypal/return?t={make_return_token}`。
6. commit→reset_tenant_context→`{invoice_id, invoice_number, amount, currency, approval_url}` 返却。

### 2.2 frontend `PaypalIntegrationPage.tsx`
- 「決済テスト」セクション追加（sandbox 環境＋configured のとき表示）。ボタン→`api.post("/integrations/paypal/test-invoice")`→結果に **「PayPalで支払う」リンク（別タブ）＋「テスト請求書を開く」(/invoices/{id})＋¥100** を表示。3方式の説明文。
- i18n `paypalIntegration.payTest*`（ja/en）。emoji 不使用。

## 3. 受け入れ基準（各基準に検証方法）
| # | 基準 | 検証方法 |
|---|---|---|
| 1 | sandbox 接続済テナントでボタン→テスト請求書(issued)＋PayPal リンクが返る | コードレビュー（endpoint 一連）＋ sandbox 実機(Evaluator) |
| 2 | live 環境では 400（実課金防止） | pytest: get_credentials を environment='live' でモック→400（`backend/tests/test_paypal_test_invoice.py`） |
| 3 | PayPal 未接続では 400 | pytest: get_credentials None→400 |
| 4 | 「PayPalテスト」会社/担当者は2回目以降 再利用（重複作成しない） | コードレビュー（company_code/contact_code で find-or-create）＋ pytest（SQLite で2回呼び1社/1担当者） |
| 5 | create_order 失敗時は 502 で請求書を中途半端に残さない | コードレビュー（create_order 失敗→例外/ロールバック前に return） |
| 6 | 書込後 reset_tenant_context（ADR-072） | コードレビュー＋ADR-072 lint |
| 7 | フロント：sandbox＋configured のときのみ「決済テスト」表示、結果リンク表示 | tsc＋Reviewer UI 確認 |
| 8 | i18n ja/en 同一キー・ハードコード日本語なし | check:all / parity |

## 4. 弊害・トレードオフ
- テストデータ（PayPalテスト会社/担当者/請求書）が残る（PO 選択 B＝独立で許容）。会社/担当者は再利用で1組のみ、請求書はテスト毎に増える。
- sandbox 限定のため本番(live)接続テナントではボタンを出さない/拒否。実課金は構造的に発生しない。
- create_order は外部 API 呼び出し（sandbox）。失敗時は 502 を返し、commit 前なので請求書も残さない（atomic）。

## 5. 計画・継続
- これは Increment 1/2/2.5 の実機検証を容易にする補助機能。実決済の会計（Increment 3=手数料算入）は別。
