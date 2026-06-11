# design — PayPal webhook 自動確認（Increment 2.5）

参照: recon = `docs/handoff/paypal-webhook/recon.md` ／ 正本 ADR: **ADR-101** §6 PayPal「入金自動確認」、**ADR-104** §1 受注遷移。SOP: `docs/STANDARD-WORKFLOW.md`。Increment 1: `docs/handoff/paypal-payment-link/`、Increment 2: `docs/handoff/paypal-auto-confirm/`。

## 0. KGI（PO 承認 2026-06-11「2.5 で進めてOK・migration 込み・自動登録方式」）
顧客が決済リンクで支払い後に **return URL に戻らなくても**、PayPal webhook（`CHECKOUT.ORDER.APPROVED`）で当方が capture→請求書 paid＋受注 sourcing にする。webhook はテナント接続時に**自動登録**（手動設定ゼロ）＋**署名検証**。

## 1. 外部・過去事例の参照と我々への応用
- **PayPal Webhooks（公式）**：`POST /v1/notifications/webhooks` で url＋event_types を登録→`id`(webhook_id) を取得。受信は `POST /v1/notifications/verify-webhook-signature`（webhook_id＋transmission ヘッダ＋webhook_event）で `verification_status=SUCCESS` を確認。`intent=CAPTURE` は承認≠capture のため、`CHECKOUT.ORDER.APPROVED` 受信で merchant が capture する（developer.paypal.com/api/rest/webhooks, /docs/checkout/standard）。本実装はこれに準拠。
- **過去事例（自社・公開endpoint）**：Increment 2 の公開 `/integrations/paypal/return`（`backend/app/routers/integrations.py:580`・set/reset_tenant_context・冪等・受注遷移）を雛形に webhook を追加。capture→paid→受注遷移は **同じ処理を共有**。
- **過去事例（自社・テナント別認証情報）**：`tenant_paypal_config`（Fernet 暗号）に `webhook_id` を1列追加するだけで multi-tenant webhook を実現（新基盤を増やさない）。
- **マルチテナント webhook ルーティング**：イベントの `custom_id`（create_order で `tenant_id:invoice_id` を埋める）で対象テナント/請求書を特定→そのテナントの webhook_id で署名検証（検証成功＝正当）。

## 2. 技術 How
### 2.1 migration（public 単一テーブル・安全）
`migrations/20260611_150000_add_paypal_webhook_id.sql`: `ALTER TABLE tenant_paypal_config ADD COLUMN IF NOT EXISTS webhook_id TEXT;` ＋ COMMENT。`scripts/run_all_migrations.sh` に run_sql 追記、`TOTAL=130→131`。

### 2.2 service `paypal_payments.py`
- `register_webhook(env, cid, csec, webhook_url) -> dict`：`POST /v1/notifications/webhooks`（event=CHECKOUT.ORDER.APPROVED）。既存(400 WEBHOOK_URL_ALREADY_EXISTS)は `GET /v1/notifications/webhooks` で既存 id を返す。`{ok, webhook_id, message}`。
- `verify_webhook(env, cid, csec, webhook_id, headers, event) -> bool`：`POST /v1/notifications/verify-webhook-signature`→`SUCCESS`。
- `get_webhook_id(db, tenant_id)` / `save_webhook_id(db, tenant_id, webhook_id)`（tenant_paypal_config）。
- `create_order` に `custom_id` 引数追加（purchase_unit に `custom_id`）。

### 2.3 router `invoices.py`
- `issue_paypal_link`：create_order に `custom_id=f"{tenant_id}:{invoice_id}"` を渡す（webhook ルーティング用）。

### 2.4 router `integrations.py`
- `save_paypal_credentials`：保存後に **webhook 自動登録**（best-effort・`run_in_threadpool(register_webhook, ...)`→`save_webhook_id`。失敗は warning ログのみで接続は成功）。
- 公開 `POST /integrations/paypal/webhook`（Bearer 不要）：
  1. body JSON 解析。`event_type != CHECKOUT.ORDER.APPROVED` は 200（無視）。
  2. `resource.purchase_units[0].custom_id`→`tenant_id:invoice_id` 解析。不正は 200（無視・PayPal 再送防止）。
  3. `get_webhook_id(tenant)`＋creds 取得。`verify_webhook`→False は 400（不正署名）。検証不能(例外)は 500（PayPal 再送）。
  4. 検証OK：`set_tenant_context`→請求書 SELECT。`paid` 済みは 200（冪等）。`issued/overdue` かつ `paypal_order_id==resource.id` なら `capture_order`→`captured` で請求書 paid＋受注 sourcing→commit。`reset_tenant_context`(finally)。200 返却。

### 2.5 frontend
- 変更なし（webhook は裏方）。i18n 変更なし。

## 3. 受け入れ基準（各基準に検証方法）
| # | 基準 | 検証方法 |
|---|---|---|
| 1 | `register_webhook` が webhook 作成 200 で webhook_id を返す | pytest: httpx mock(201＋id)→webhook_id assert（`backend/tests/test_paypal_webhook.py`） |
| 2 | 既存 URL(400 WEBHOOK_URL_ALREADY_EXISTS) は list から既存 id を返す | pytest: 400→GET list mock→既存 id |
| 3 | `verify_webhook` が SUCCESS で True、それ以外で False | pytest: verify mock(SUCCESS/FAILURE)→bool |
| 4 | `create_order` が purchase_unit に custom_id を含める | pytest: create_order mock 引数 `custom_id` を assert（既存 service テスト拡張） |
| 5 | webhook 受信で署名検証→capture→請求書 paid＋受注 sourcing | コードレビュー（endpoint の検証→capture→UPDATE 2本）＋ sandbox 実機(Evaluator) |
| 6 | 不正署名/改ざんイベントは paid にしない（400） | コードレビュー（verify False→400・早期return） |
| 7 | 既に paid は冪等（再送で二重処理しない） | コードレビュー（status='paid' 早期return＋UPDATE status ガード） |
| 8 | 公開 endpoint が set_tenant_context→処理→reset_tenant_context(finally) | コードレビュー＋ ADR-072 lint |
| 9 | webhook 自動登録失敗で接続(save)が失敗しない（best-effort） | コードレビュー（try/except warning・save は別 commit） |
| 10 | migration が run_all_migrations 登録・public 単一 ALTER・nullable | CI migration-guard / migration-test ＋ SQL レビュー |

## 4. 弊害・トレードオフ
- webhook 自動登録は各テナントの PayPal アプリに webhook を作る → PayPal アプリ権限が必要。失敗時は best-effort（return 経路＝Increment 2 が確定を担保）。
- 公開 webhook は capture（お金）を実行するが、署名検証（PayPal 正規イベントのみ）＋custom_id 経由のテナント固定＋order_id 一致＋冪等で保護。
- intent=CAPTURE のため `CHECKOUT.ORDER.APPROVED` で当方 capture（PAYMENT.CAPTURE.COMPLETED は当方 capture の結果＝重複処理回避のため本 Increment は APPROVED のみ購読）。

## 5. 計画・継続
- Increment 3: `payment_fee` を請求合計／売上 P&L 算入（ADR-101 §2 / ADR-104 §3）。
- 運用: webhook 未登録テナントの検出・再登録ボタン（将来）。
