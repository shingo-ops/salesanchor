# recon — PayPal webhook 自動確認（Increment 2.5）

対象: 顧客が決済リンクで支払い後に **return URL に戻らなくても**、PayPal の `CHECKOUT.ORDER.APPROVED` webhook で当方が capture→請求書 paid＋受注 sourcing にする堅牢化。テナント毎に webhook を自動登録＋署名検証。

実コードを **フルパス:行番号** で突合（短縮禁止）。

## 1. tenant_paypal_config（webhook_id 追加先）
- `migrations/20260610_071110_add_paypal_config.sql:15`（`CREATE TABLE IF NOT EXISTS tenant_paypal_config`）= **public スキーマの単一テーブル**（`tenant_id` UNIQUE 列・1テナント1行・`client_id_encrypted`/`client_secret_encrypted`/`environment`）。→ `webhook_id TEXT` を **単一 ALTER ADD COLUMN IF NOT EXISTS** で追加（全テナントループ不要・nullable・破壊なし）。
- `backend/app/tests/` 配下 conftest に tenant_paypal_config の CREATE は無し（PayPal endpoint テストは service をモック）。→ **SQLite 同期不要**（Increment 1 の conftest 漏れ事象は起きない）。

## 2. Increment 1/2 の基盤
- `backend/app/services/paypal_payments.py:213`（`create_order`）= 注文作成。purchase_unit に `custom_id` を未設定 → **webhook ルーティング用に `custom_id=f"{tenant_id}:{invoice_id}"` を追加**する。
- `backend/app/services/paypal_payments.py:299`（`capture_order`）= capture（webhook 経路でも再利用）。
- `backend/app/services/paypal_payments.py:371`（`make_return_token`）/ `:61`（`get_credentials`）/ `:49`（`get_status`）。
- `backend/app/routers/integrations.py:580`（`@public_router.get("/integrations/paypal/return")`）= Increment 2 の公開 capture。同型で `POST .../webhook` を追加。`set_tenant_context`→処理→`reset_tenant_context`(finally) は Increment 2 で実証（`backend/app/routers/integrations.py:580` 以降）。
- `backend/app/routers/integrations.py:499`（`save_paypal_credentials`・PUT /credentials）= 認証情報保存。**保存後に webhook を自動登録**するフック地点。

## 3. PayPal webhook の署名検証
- API: `POST {base}/v1/notifications/verify-webhook-signature`（body: `auth_algo`/`cert_url`/`transmission_id`/`transmission_sig`/`transmission_time`/`webhook_id`/`webhook_event`）→ `verification_status=="SUCCESS"` で正当。**webhook_id 必須**（テナント毎に保存）。
- 受信ヘッダ: `paypal-transmission-id`/`paypal-transmission-time`/`paypal-cert-url`/`paypal-auth-algo`/`paypal-transmission-sig`。
- webhook 登録 API: `POST {base}/v1/notifications/webhooks`（body: `url`＋`event_types:[{name:"CHECKOUT.ORDER.APPROVED"}]`）→ 返り `id` が webhook_id。既存 URL は 400 `WEBHOOK_URL_ALREADY_EXISTS`→`GET .../webhooks` で既存 id を取得。
- base URL は `backend/app/services/paypal_payments.py:34`（sandbox/live）を流用。
- intent=CAPTURE のため承認≠capture。顧客が戻らないと未 capture → **`CHECKOUT.ORDER.APPROVED` 受信時に当方が capture** するのが本 Increment の肝。

## 4. 公開エンドポイント・テナント文脈
- `public_router`（`backend/app/routers/integrations.py:49`）。main 登録は public（Bearer 不要）。
- `set_tenant_context`（`backend/app/auth/dependencies.py:255`）/ `reset_tenant_context`（ADR-072）。
- 受注遷移 `UPDATE orders SET status='sourcing' WHERE invoice_id=:iid AND status='awaiting_payment'` は Increment 2 で実装済（`backend/app/routers/integrations.py` の return ＋ invoices.py confirm）。webhook 経路も同処理を共有。

## 5. 環境
- 公開 webhook/return の本番ベース = `API_BASE_URL`（既定 `https://api.salesanchor.jp`、Increment 2 で導入。`backend/app/routers/invoices.py` の `_API_BASE_URL`）。
- run_all_migrations 現状 `scripts/run_all_migrations.sh:47`（`TOTAL=130`）→ +1 で 131。

## 6. 範囲外
- Increment 3=手数料を請求合計／P&L 算入。
- webhook 自動登録の失敗時は best-effort（接続自体は成功させ、webhook 未登録でも return 経路で確定可）。
