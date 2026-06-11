# recon — PayPal 決済リンク (ADR-101 mode1 / Increment 1)

対象: 請求書（INVOICE）から PayPal 決済リンクを自動発行し、入金を確認して請求書を `paid` にする（Increment 1 = リンク発行＋手動トリガの capture 確認。webhook 自動確認は Increment 2）。

実コードを file:line で突合した事実のみを記載（推測なし）。

## 1. 既存の請求書システム（実装済み）

- ルーター: `backend/app/routers/invoices.py:45`（`router = APIRouter()`）。エンドポイントは `list_invoices`(`backend/app/routers/invoices.py:169`) / `get_invoice`(`:205`) / `create_invoice_from_quote`(`:225`) / `create_invoice`(`:323`) / `update_invoice`(`:435`) / `issue_invoice`(`:477`) / `pay_invoice`(`:506`) / `void_invoice`(`:535`) / PDF系。
- 認証/テナント文脈の依存: `backend/app/routers/invoices.py:24-29` が `get_current_tenant` / `get_current_user` / `require_permission` / `reset_tenant_context` を import。
- 既存の権限キー: `invoices.view`(`:167`) / `invoices.create`(`:223,475`) / `invoices.update`(`:504`) / `invoices.void`(`:533`)。
- **書き込みエンドポイントの定型**（`pay_invoice` `backend/app/routers/invoices.py:506-527`）:
  - `UPDATE invoices SET status='paid', paid_at=NOW(), updated_at=NOW() WHERE id=:id AND status IN ('issued','overdue') RETURNING {_INVOICE_COLUMNS}` (`:514`)
  - `record_audit_log(...)`(`:521`) → `await db.commit()`(`:524`) → `await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5`(`:525`) → `await invalidate_dashboard_cache(tenant_id)`(`:526`) → `return InvoiceResponse(**dict(row))`(`:527`)。
- 列定数 `_INVOICE_COLUMNS`（`backend/app/routers/invoices.py:116-126`）= RETURNING / SELECT 共通の列リスト。`status` / `payment_method` / `paid_at` を既に含む。
- スキーマ: `backend/app/schemas/invoice.py:19-24`（`InvoiceStatus`= draft/issued/paid/overdue/voided）。`InvoiceResponse`(`:85-130`) に `status`/`payment_method`/`paid_at`/`total_amount`/`currency` あり。`InvoiceDetailResponse`(`:133`)。
- テーブル定義: `migrations/005_add_phase2_tenant_tables.sql:110-125`（`invoices` に `invoice_number`/`status`/`payment_method`/`paid_at`/`total_amount`/`currency`/為替列）。**PayPal 固有列（order_id/approval_url/fee）は無い**。

## 2. PayPal サービス（接続テストのみ・Orders API 未実装）

- `backend/app/services/paypal_payments.py:135`（`test_connection`）= OAuth2 client_credentials でトークン取得確認のみ。
- テナント別認証情報 CRUD: `get_credentials`(`backend/app/services/paypal_payments.py:61`) が復号して `{client_id, client_secret, environment}` を返す。`save_credentials`(`:80`) / `get_status`(`:49`)。
- base URL: `backend/app/services/paypal_payments.py:34-37`（sandbox `https://api-m.sandbox.paypal.com` / live `https://api-m.paypal.com`）、`_norm_env`(`:40`)。
- **不足**: 注文作成（`POST /v2/checkout/orders`）・capture（`POST /v2/checkout/orders/{id}/capture`）が無い（`def`一覧 `:40,49,61,80,115,128,135` に Orders API なし）。

## 3. フロント請求書詳細（アクション導線）

- `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:163-173` にステータス別アクション:
  - draft→`doAction("issue")`(`:164`) / issued|overdue→`doAction("pay")`(`:167`) / void(`:170`) / PDF(`:172`)。
  - `doAction` ヘルパ＋ `t("invoices.xxx")` 国際化、`hasPermission("invoices.xxx")` でガード。
  - 型 `invoice.status`(`:64`) / `paid_at`(`:67` 付近)。

## 4. ステータス・ライフサイクル（ADR-104）

- ADR-104 §1: 「支払い待ち →（入金確認: PayPal API＝自動 / 不使用＝手動）→ 仕入れ中」。本 Increment は **請求書(invoice)の `paid` 化**までを対象（受注(order)側ステータス連携は Increment 2/別ADR-102 範囲）。
- ADR-101 §2: 合計＝小計＋送料＋**支払い手数料(PayPal)**＋通貨換算。手数料の合計算入は Increment 3。

## 5. migration 実行経路（危ない変更の確実性）

- `.github/workflows/deploy.yml:359`（`bash scripts/run_all_migrations.sh`）が本番で migration を実行。
- 新規 migration は **`scripts/run_all_migrations.sh` に `run_sql` 追記**（`deploy.yml` ではない。`deploy.yml:108,344` のコメント）。
- CI `.github/workflows/migration-guard.yml:119-135` が「全 migration ファイルが run_all_migrations.sh に登録済みか」を検査（登録漏れは CI fail）。
- 現状: `scripts/run_all_migrations.sh:47`（`TOTAL=124`）、末尾 `run_sql migrations/20260611_010000_fix_owner_role_color.sql`(`:327`)。→ 追加で `TOTAL=125`。

## 6. 不明点（PO 確認 / Increment 範囲外で先送り）

- webhook（PAYMENT.CAPTURE.COMPLETED）による完全自動確認 = **Increment 2**（署名検証必須）。本 Increment は capture をスタッフ操作トリガで実行。
- 受注(order)ステータス連携（支払い待ち→仕入れ中）= ADR-102/別 Increment。
- 手数料の合計・P&L 算入 = Increment 3（ADR-101 §2 / ADR-104 §3）。
- 本番実決済は会社 PayPal 接続後（PO=しんごさん領域）。開発/検証は sandbox。
