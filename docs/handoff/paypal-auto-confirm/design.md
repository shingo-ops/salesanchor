# design — PayPal 入金自動確認（戻りURL capture）/ Increment 2

参照: recon = `docs/handoff/paypal-auto-confirm/recon.md` ／ 正本 ADR: **ADR-101** §6 PayPal (1)「入金自動確認」、**ADR-104** §1 受注ライフサイクル（入金確認→sourcing）。SOP: `docs/STANDARD-WORKFLOW.md`。Increment 1: `docs/handoff/paypal-payment-link/`。

## 0. KGI（PO 承認 2026-06-11「推奨で」）
顧客が PayPal 決済リンクで支払うと、**スタッフ操作なしで請求書が paid になり、紐づく受注が awaiting_payment→sourcing に自動遷移**する。方式 B（戻りURL自動 capture）。webhook は Increment 2.5 に分割。**migration なし＝危ない変更なし**。

## 1. 外部・過去事例の参照と我々への応用
- **PayPal の標準フロー**：`create_order(intent=CAPTURE)` の `application_context.return_url` に顧客が承認後リダイレクトされ、`?token={order_id}&PayerID=...` が付与される。戻り先で `capture_order` を呼ぶ「return-then-capture」は PayPal 公式の標準パターン（developer.paypal.com/docs/checkout/standard/integrate）。本実装はこれに準拠。
- **過去事例（自社・公開endpoint）**：Drive OAuth callback（`integrations.py` public_router・Bearer 不要・処理後 reset_tenant_context）を雛形に、**顧客（非ログイン）が到達する公開 return エンドポイント**を実装。
- **過去事例（自社・署名）**：`encryption`（Fernet）を流用し戻りトークンを改ざん防止（save_credentials と同じ暗号基盤＝新しい鍵管理を増やさない）。
- **過去事例（自社・capture/手動確認）**：Increment 1 の `capture_order`・手動 `paypal-confirm` を再利用。自動と手動の両経路で同じ「paid＋受注 sourcing」処理を共有。

## 2. 技術 How
### 2.1 service `paypal_payments.py`
- `make_return_token(tenant_id, invoice_id) -> str` = `encryption.encrypt(f"{tenant_id}:{invoice_id}")`（URLセーフ・改ざん不可）。
- `parse_return_token(token) -> tuple[int,int] | None` = decrypt→split→int。改ざん/不正は None。

### 2.2 router `invoices.py`
- `issue_paypal_link`：`return_url` を **公開 return エンドポイント＋署名トークン**へ変更：
  `return_url = f"{_API_BASE_URL}/api/v1/integrations/paypal/return?t={make_return_token(tenant_id, invoice_id)}"`、`cancel_url = f"{_API_BASE_URL}/api/v1/integrations/paypal/cancel"`（`_API_BASE_URL=os.getenv("API_BASE_URL","https://api.salesanchor.jp")`）。create_order に return_url/cancel_url を渡す。
- `confirm_paypal_payment`（手動・Increment 1）：請求書 paid 後に **受注遷移を追加**（自動経路と一貫）：
  `UPDATE orders SET status='sourcing', paid_at=NOW(), updated_at=NOW() WHERE invoice_id=:iid AND status='awaiting_payment'`。

### 2.3 router `integrations.py`（public_router・Bearer 不要）
- `GET /integrations/paypal/return?t={signed}&token={paypal_order_id}`：
  1. `parse_return_token(t)`→None なら 400 HTML。
  2. `set_tenant_context(db, tenant_id)`。
  3. 請求書 SELECT（id/status/paypal_order_id）。無し or `token` 不一致→404 HTML（順序的に PayPal token と保存値の一致を確認＝他注文の流用防止）。
  4. 既に `paid`→「支払い済み」HTML（冪等）。
  5. creds 取得→`capture_order`。`captured` なら invoices を paid（`AND status IN('issued','overdue')` ガード）＋ orders を sourcing 遷移→commit→reset_tenant_context→「ありがとうございました」HTML。未確定→409 HTML。
- `GET /integrations/paypal/cancel`：「キャンセルされました」HTML。
- 顧客向け文言は ADR-101（顧客向けは英語）に従い**英語＋日本語併記の最小 HTML**（React 外＝i18n対象外）。

### 2.4 frontend `InvoiceDetailPage` / i18n
- 手動「PayPal入金確認」ボタンはフォールバックとして維持。`invoices.paypal.linkHint` を「リンクで支払うと自動で確定」に更新（ja/en）。

## 3. 受け入れ基準（各基準に検証方法）
| # | 基準 | 検証方法 |
|---|---|---|
| 1 | `make_return_token`→`parse_return_token` で (tenant_id, invoice_id) が往復復元できる | pytest: round-trip assert（`backend/tests/test_paypal_return.py`） |
| 2 | 改ざんトークン/不正文字列は `parse_return_token` が None を返す | pytest: 改変トークン→None |
| 3 | `issue_paypal_link` の return_url が公開 return エンドポイント＋署名トークンになる | pytest: create_order mock の引数 return_url を assert（既存 service テスト拡張）／コードレビュー |
| 4 | 戻り capture 成功で請求書 paid＋紐づく受注が sourcing に遷移する | コードレビュー（return endpoint の UPDATE 2本）＋ sandbox 実機（Evaluator） |
| 5 | 既に paid の請求書は冪等（再度 return しても二重処理しない） | コードレビュー（status='paid' 早期 return ＋ UPDATE の `AND status IN('issued','overdue')` ガード） |
| 6 | PayPal token と請求書の paypal_order_id 不一致は 404（他注文流用防止） | コードレビュー（token 一致チェック） |
| 7 | 公開 endpoint が `set_tenant_context`→処理→`reset_tenant_context` を踏む（ADR-072/RLS） | コードレビュー＋ ADR-072 lint |
| 8 | 手動 `paypal-confirm` でも受注が sourcing に遷移する（自動と一貫） | コードレビュー（UPDATE orders 追加） |
| 9 | i18n: linkHint 更新が ja/en 同一キー | check:all / parity |

## 4. 弊害・トレードオフ
- 顧客がブラウザを閉じて return に戻らないと自動 capture されない → **手動「PayPal入金確認」ボタンがフォールバック**（Increment 1）。完全自動の堅牢化は Increment 2.5（webhook）。
- 公開 endpoint は capture（お金）を実行するが、(a) Fernet 署名トークン必須、(b) PayPal token と保存値一致必須、(c) capture は PayPal 側で承認済の注文のみ成功、(d) 冪等、の4重で保護。
- 受注遷移は `awaiting_payment` の受注のみ（他状態は変更しない＝安全側）。

## 5. 計画・継続
- Increment 2.5: PayPal webhook（per-tenant webhook_id・署名検証）で「顧客が戻らなくても確定」を担保。
- Increment 3: `payment_fee` を合計／売上 P&L 算入（ADR-101 §2 / ADR-104 §3）。
