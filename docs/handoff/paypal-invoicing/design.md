# design — PayPal を Invoicing 方式へ移行（案Y 併存）

参照: recon = `docs/handoff/paypal-invoicing/recon.md` ／ 正本 ADR: **ADR-101 改訂 2026-06-12**（PayPal を Invoicing 方式へ・自社請求書 SSOT 併存）。SOP: `docs/STANDARD-WORKFLOW.md`。

## 0. KGI（PO 了承: しんごさん事前承認・Hitoshi 判断 GO 2026-06-12）
PayPal 決済を **PayPal Invoicing API**（PayPal が請求書をメール送付＋ホスト決済ページ＋ステータス管理）へ切替。**自社請求書は SSOT のまま併存**（Wise 等流用）。入金は `INVOICING.INVOICE.PAID` webhook／status 取得で確認→自社請求書 paid＋受注 sourcing。**migration なし**（既存列流用）。

## 1. 外部・過去事例の参照と我々への応用
- **PayPal Invoicing API（公式・recon §1）**: create→send→（顧客がメール/ホストページで支払い）→`INVOICING.INVOICE.PAID` webhook、の標準フローに準拠。`detail.invoice_number`=自社IN-NNNN、`detail.reference`=ルーティングキー。
- **過去事例（自社・Increment 1-2.5）**: tenant別認証情報・`verify_webhook`(署名検証)・webhook公開エンドポイント・受注遷移 UPDATE を**そのまま流用**（基盤を作り直さない）。決済リンク発行ロジックのみ Orders→Invoicing に差し替え。
- **過去事例（自社・SSOT）**: ADR-101 の「自社請求書＋自社PDF が正本」を維持（PayPal は支払いチャネル）。PayPal が API で PDF を返さない制約とも整合。

## 2. 技術 How（migration なし）
### 2.1 service `paypal_payments.py`（追加）
- `create_and_send_invoice(env, cid, csec, *, invoice_number, currency, amount, recipient_email, reference, item_name) -> dict`:
  ①`POST /v2/invoicing/invoices`(detail.currency_code/invoice_number/reference, invoicer.name='Sales Anchor', primary_recipients[].billing_info.email_address, items[1])→ id。②`POST .../{id}/send`(send_to_recipient=true)。③`GET .../{id}`→`detail.metadata.recipient_view_url`。返り `{ok, paypal_invoice_id, recipient_view_url, status_code, message}`。
- `get_invoice_status(env, cid, csec, paypal_invoice_id) -> dict`: `GET .../{id}`→`{ok, status, paid(status=='PAID'), fee, message}`。
- `register_webhook` の event を `CHECKOUT.ORDER.APPROVED`→`INVOICING.INVOICE.PAID` に変更。`verify_webhook` は不変。旧 `create_order`/`capture_order`/`make_return_token` は**残す（dormant・既存テスト維持）**。

### 2.2 router `invoices.py`
- `issue_paypal_link`（パス維持）: invoice + contact.primary_email を JOIN 取得。email 無し→400。`create_and_send_invoice(... reference=f"{tenant_id}:{invoice_id}")`→ `UPDATE invoices SET paypal_order_id=:pp_inv_id, paypal_approval_url=:recipient_view_url, payment_method='paypal'`。失敗→502。
- `paypal-confirm`（手動・パス維持）: `get_invoice_status(paypal_order_id)`→`paid` なら `UPDATE status='paid', paid_at, payment_fee` ＋受注 sourcing。未払い→409。

### 2.3 router `integrations.py`
- `paypal_webhook`: `event_type=='INVOICING.INVOICE.PAID'` を処理（旧 CHECKOUT.ORDER.APPROVED 置換）。resource から `detail.reference`("tenant:invoice") を取り（`resource.invoice.detail.reference` or `resource.detail.reference` 防御的）→ 署名検証→ set_tenant_context→ 請求書 paid（`AND status IN('issued','overdue')`）＋受注 sourcing→ reset。冪等。
- `test-invoice`: Invoicing フローに変更。PayPalテスト contact に placeholder email 設定→`create_and_send_invoice`→`recipient_view_url` 返却。
- `paypal_return`/`paypal_cancel` 公開エンドポイントは dormant（Invoicing では不要・削除せず）。

### 2.4 frontend / i18n
- `InvoiceDetailPage`: ボタン文言「PayPalリンク発行」→「**PayPal請求書を送付**」、表示を recipient_view_url（顧客の支払いページ）に。linkHint 更新。
- `PaypalIntegrationPage` 決済テスト: 文言更新。i18n ja/en 同期。

## 3. 受け入れ基準（各基準に検証方法）
| # | 基準 | 検証方法 |
|---|---|---|
| 1 | `create_and_send_invoice` が create→send→get で recipient_view_url を返す | pytest: httpx mock(create 201+id / send 200 / get 200+metadata)→ assert（`backend/tests/test_paypal_invoicing.py`） |
| 2 | `get_invoice_status` が status=PAID で paid=True、他で False | pytest: get mock(PAID/SENT)→bool |
| 3 | issue_paypal_link: contact.email 無しは 400 | pytest: email NULL contact→400 |
| 4 | webhook `INVOICING.INVOICE.PAID` で reference ルーティング→請求書 paid＋受注 sourcing | コードレビュー（reference 解析→UPDATE 2本）＋ sandbox 実機(Evaluator) |
| 5 | 署名検証 False は paid にしない（400）／冪等（paid 早期return） | コードレビュー |
| 6 | register_webhook が `INVOICING.INVOICE.PAID` を購読 | コードレビュー＋既存 test_paypal_webhook 維持 |
| 7 | ADR-072: 書込後 reset_tenant_context | コードレビュー＋lint |
| 8 | i18n ja/en 同一キー・ハードコード日本語なし | check:all/parity |
| 9 | 自社請求書 SSOT は不変（自社PDF・採番・受注連携は維持） | コードレビュー（invoices テーブル/PDF 不変） |

## 4. 弊害・トレードオフ
- PayPal Invoicing は **email 必須**（送付できないと発行不可）→ email 未登録 contact は 400。
- PDF は PayPal から取得不可→自社生成のまま（ADR-101 通り）。
- 旧 Orders 経路は dormant（段階整理）。関数/エンドポイントは削除せず残し既存テストを壊さない。
- 顧客は PayPal のホストページ(recipient_view_url)で支払う（自社サイトに戻る導線は不要に）。

## 5. 計画・継続
- 旧 Orders 経路コードの本撤去は別 PR（dormant を確認後）。
- Increment 3=手数料を合計/P&L 算入（別）。Wise は自社請求書＋メール送金（ADR-101 §6）。
