# design — PayPal 決済リンク (ADR-101 mode1 / Increment 1)

参照: recon = `docs/handoff/paypal-payment-link/recon.md` ／ 設計の正本 ADR: **ADR-101**（見積・請求の生成・発行モード）§6 PayPal (1)、**ADR-104**（入金確認・ステータス）§1。SOP: `docs/STANDARD-WORKFLOW.md`。

## 0. KGI（定量・PO 承認済み 2026-06-10）

- 「請求書から PayPal 決済リンクを自動発行し、入金確認で請求書を `paid` にできる」を実装し、**sandbox 認証情報で create→capture→paid が通る**こと。
- スコープ＝Increment 1（リンク発行＋手動トリガ capture 確認）。webhook 自動確認は Increment 2。PO（Hikky-dev）GO 取得済み（migration 込み）。

## 1. 外部・過去事例の参照と我々への応用

- **PayPal Orders API v2**（公式）: `POST /v2/checkout/orders`（`intent=CAPTURE`・`purchase_units[].amount={currency_code,value}`）→ レスポンスの `links[rel=approve].href` が顧客が支払う承認 URL。承認後 `POST /v2/checkout/orders/{id}/capture` で確定。→ 本実装はこの2段（create=リンク発行 / capture=入金確認）にそのまま対応。
  - 出典: developer.paypal.com/docs/api/orders/v2/ （create order / capture order）。
- **過去事例（自社）**: 既存 `paypal_payments.py:135 test_connection` が同じ sync httpx＋Basic 認証（`get_credentials` で復号した Client ID/Secret）でトークン取得済み＝**同方式でアクセストークンを取り、Orders API を叩く**（新しい認証経路を増やさない）。
- **過去事例（自社・請求書アクション）**: `issue_invoice`/`pay_invoice`（recon §1）の「UPDATE…RETURNING→audit→commit→reset_tenant_context→cache」定型を**完全踏襲**（ADR-072 整合・独自実装を増やさない）。
- **過去事例の教訓の適用**: 接続テスト実装で `test_connection` がシークレット/例外をクライアントに返さない設計（recon §2）→ Orders API もエラーは status_code＋定型文のみ返す。

## 2. 技術 How

### 2.1 DB（migration・nullable 追加のみ＝安全）
`migrations/20260611_020000_add_invoice_paypal_columns.sql`（全テナントスキーマ＋public 分岐は既存 migration に倣う／列存在ガード `information_schema` 付き）:
- `invoices.paypal_order_id  TEXT`（PayPal の order id）
- `invoices.paypal_approval_url TEXT`（顧客に送る承認リンク）
- `invoices.payment_fee NUMERIC(15,2)`（capture で得た PayPal 手数料・将来の合計/P&L 算入用に保存のみ）
- `scripts/run_all_migrations.sh` に `run_sql` 追記、`TOTAL=124→125`（recon §5）。

### 2.2 backend service（`paypal_payments.py` に追加）
- `_get_token(env, client_id, client_secret) -> str | None`（`test_connection` のトークン取得を共通化）。
- `create_order(env, cid, csec, amount, currency, invoice_number, return_url, cancel_url) -> dict`:
  `{ok, order_id, approval_url, status_code, message}`。`POST {base}/v2/checkout/orders`（`intent=CAPTURE`）。
- `capture_order(env, cid, csec, order_id) -> dict`:
  `{ok, captured, fee, status_code, message}`。`POST {base}/v2/checkout/orders/{id}/capture`。`status==COMPLETED` で `captured=True`、`purchase_units[].payments.captures[].seller_receivable_breakdown.paypal_fee` から手数料抽出。
- いずれも sync httpx（呼び出し側 `run_in_threadpool`）＋例外は status_code/定型文のみ（既存方針）。

### 2.3 backend router（`invoices.py` に追加）
- `_INVOICE_COLUMNS`（recon §1）に `paypal_order_id, paypal_approval_url, payment_fee` を追加。`InvoiceResponse`（`schemas/invoice.py`）にも 3 フィールド（`str|None`/`Decimal|None`）追加。
- `POST /invoices/{id}/paypal-link`（`require_permission("invoices.update")`）:
  対象は `status IN ('issued','overdue')`。`get_credentials` → 無ければ 400「PayPal 未接続」。`run_in_threadpool(create_order, ...)` → 成功で `UPDATE invoices SET paypal_order_id, paypal_approval_url, payment_method='paypal' … RETURNING _INVOICE_COLUMNS`。audit→commit→reset_tenant_context→cache。失敗は 502＋定型文。
- `POST /invoices/{id}/paypal-confirm`（`require_permission("invoices.update")`）:
  `paypal_order_id` 必須・`status IN ('issued','overdue')`。`run_in_threadpool(capture_order, ...)` → `captured` なら `UPDATE … status='paid', paid_at=NOW(), payment_fee=:fee`。未確定なら 409「まだ入金が確認できません」。audit→commit→reset_tenant_context→cache。
- return/cancel URL は `settings` の app ベース URL（無ければ請求書詳細パス）を使用。

### 2.4 frontend（`InvoiceDetailPage.tsx`）
- `status IN issued/overdue` かつ `hasPermission("invoices.update")` のとき:
  - リンク未発行: 「PayPalリンク発行」ボタン → `doAction("paypal-link")`。
  - `paypal_approval_url` あり: リンク表示（コピー/別タブ）＋「PayPal入金確認」ボタン → `doAction("paypal-confirm")`。
- 文言は `t("invoices.paypal.*")`。emoji 不使用（check:jsx-emoji）。i18n ja/en 同一キー。

## 3. 受け入れ基準（各基準に検証方法をリンク）

| # | 基準 | 検証方法 |
|---|---|---|
| 1 | issued/overdue の請求書で「PayPalリンク発行」すると Orders API が呼ばれ、`paypal_order_id`/`paypal_approval_url` が保存される | backend pytest: `create_order` を httpx mock（200＋links）→ エンドポイントが列更新を返すことを assert（`backend/tests/test_paypal_payment_link.py`） |
| 2 | PayPal 未接続テナントでリンク発行すると 400 | pytest: `get_credentials`→None で 400 |
| 3 | 「PayPal入金確認」で capture が COMPLETED なら請求書が `paid`＋`paid_at`＋`payment_fee` 記録 | pytest: `capture_order` mock（COMPLETED＋fee）→ status=paid・payment_fee 検証 |
| 4 | capture 未確定（APPROVED 等）なら 409 で `paid` にしない | pytest: capture mock（not completed）→ 409・status 不変 |
| 5 | 書き込み後に `reset_tenant_context` が呼ばれる（ADR-072） | コードレビュー＋ pytest で reset 呼び出し（既存 `pay_invoice` と同型）／Reviewer 確認 |
| 6 | フロント詳細でリンク発行/確認ボタンが status・権限で出し分く | tsc 型チェック＋ Reviewer UI 確認（issued 時のみ表示） |
| 7 | i18n: `invoices.paypal.*` が ja/en 同一キー・ハードコード日本語なし | `check:all`（ESLint no-japanese-literal）＋ i18n parity スクリプト |
| 8 | migration が run_all_migrations.sh に登録・列追加のみ（既存データ不変） | CI `migration-guard.yml`＋ `migration-test`／SQL レビュー（nullable・列ガード） |
| 9 | sandbox 実認証情報で create→approve→capture→paid が通る | 本番(sandbox環境)実機: 請求書でリンク発行→PayPal sandbox 購入→入金確認→paid（Evaluator/手動） |

## 4. 弊害・トレードオフ

- capture を「確認ボタン」トリガにするため、**顧客が承認しただけで自動 paid にはならない**（スタッフ操作が要る）＝Increment 1 の割り切り。完全自動は Increment 2（webhook）。
- 受注(order)ステータス連携は本 Increment 範囲外（請求書 `paid` まで）。誤解防止のため UI は「請求書の入金」に限定表記。
- 実決済はお金が動く → 本番は会社 PayPal 接続後。それまで sandbox で検証（PO 領域）。

## 5. 計画・継続

- Increment 2: PayPal webhook で自動 capture/確認 → 受注ステータス自動遷移（ADR-104）。
- Increment 3: `payment_fee` を合計／売上P&L に算入（ADR-101 §2 / ADR-104 §3）。
- 本 Increment 完了時に [[project_pending_backlog]] PayPal 節を更新。
