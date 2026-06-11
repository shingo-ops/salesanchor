# recon — PayPal 入金自動確認（戻りURL capture）/ Increment 2

対象: Increment 1（手動 capture）に対し、**顧客が決済リンクで支払うと自動で capture→請求書 paid＋受注 awaiting_payment→sourcing** にする（方式 B＝戻りURL自動 capture。webhook は Increment 2.5 に分割）。**migration 不要**（既存列のみ使用）。

実コードを file:line で突合（推測なし）。

## 1. Increment 1 の基盤（develop 反映済）
- `backend/app/services/paypal_payments.py:213`（`create_order`）/ `:299`（`capture_order`）= リンク発行・capture。
- `backend/app/routers/invoices.py:597`（`paypal-link`）。現状 `return_url = f"{_APP_BASE_URL}/invoices/{invoice_id}"`（`backend/app/routers/invoices.py:621`）＝ログイン必須の管理画面（顧客は到達不可）。`:658`（`paypal-confirm`）。
- invoices に `paypal_order_id`/`paypal_approval_url`/`payment_fee`（Increment 1 migration）。

## 2. 公開エンドポイントの雛形（Drive callback）
- `backend/app/routers/integrations.py:49`（`public_router = APIRouter()`）。main.py:397 で `prefix="/api/v1"` 登録（Bearer 不要）。
- Drive callback `backend/app/routers/integrations.py:104` 付近 = 認証なしで `state`→tenant 解決→`public.tenant_google_drive_config` upsert→`reset_tenant_context`（`:156`）→`RedirectResponse`。※Drive は public スキーマのみ操作。

## 3. テナントスキーマ文脈の設定（公開endpointで必須）
- `backend/app/auth/dependencies.py:255`（`set_tenant_context(db, tenant_id)`）= search_path + app.tenant_id + app.is_operator を一括設定。「**この関数を経由せず生の SET search_path を書いてはいけない**」（`:262`）。tenant_NNN.invoices/orders を触る公開endpointはこれを呼ぶ。
- 書込後は `reset_tenant_context(db, tenant_id)`（ADR-072 Phase 2.5）。invoices.py の各 write が踏襲（`backend/app/routers/invoices.py:649` 他）。

## 4. 受注↔請求書リンクとステータス（ADR-104）
- `OrderStatus` 6値 `backend/app/schemas/order.py:30`：`awaiting_payment(支払い待ち)→sourcing(仕入れ中)→awaiting_shipping→completed`＋trouble/cancelled。
- orders に `invoice_id` 列（`backend/app/routers/orders.py:110`）＝請求書↔受注リンク。`set_order_paid`（`backend/app/routers/orders.py:475`）は `paid_at` のみ更新（status は別）。
- → 入金確認時の遷移＝`UPDATE orders SET status='sourcing', paid_at=NOW() WHERE invoice_id=:iid AND status='awaiting_payment'`（ADR-104 §1）。
- SQLite テストスキーマにも orders/invoices あり（`backend/tests/conftest.py:379` orders / `:744` invoices）。unqualified テーブル名は search_path/SQLite 単一スキーマで解決（invoices.py が unqualified `invoices` で実証済）。

## 5. 署名（改ざん防止トークン）
- 専用 SECRET_KEY は app/config に未確認。**既存の Fernet（`app.services.encryption` の encrypt/decrypt、paypal save_credentials で使用済 `backend/app/services/paypal_payments.py:106`）を流用**してトークン署名（`encrypt("tenant_id:invoice_id")`＝改ざん不可・URLセーフ base64）。

## 6. 不明点 / 範囲外
- webhook（PayPal POST 主動・per-tenant webhook_id 登録）= **Increment 2.5**（本 Increment 範囲外）。
- 顧客が戻らず capture されなかった場合のフォールバック = 既存の手動「PayPal入金確認」ボタン（Increment 1）が担保。
- 本番 API ベース URL は `API_BASE_URL`（env・既定 https://api.salesanchor.jp）。
