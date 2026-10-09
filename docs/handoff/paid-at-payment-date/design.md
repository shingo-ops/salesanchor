# 設計 — paid-at-payment-date

**対象ADR**: ADR-072（reset_tenant_context）, ADR-027（i18n）, ADR-104（入金で受注が仕入れ中へ）, ADR-144（UIコンポーネント）  
**recon**: docs/handoff/paid-at-payment-date/recon.md  
**日付**: 2026-10-09  
**担当**: Sonnet（設計: Opus）

---

## 外部・過去事例の参照と我々への応用

- 事例1: PayPal Invoicing API v2 公式仕様（github.com/paypal/paypal-rest-api-specifications openapi/invoicing_v2.json）。payment_date は date_no_time（"YYYY-MM-DD"）。我々への応用: 時刻も時差も無い値なので、日付を UTC 正午の timestamptz に変換して保存する（UTC-11〜+11 のどの画面でも同じ日付で表示される）
- 事例2: asyncpg 公式ソース pgproto/codecs/datetime.pyx timestamptz_encode。timestamptz へは datetime しか渡せず str は TypeError。我々への応用: 文字列を渡さず、必ず paid_at_from_date で datetime にしてから渡す
- 事例3: SQL の LEAST/COALESCE。我々への応用: paid_at = LEAST(COALESCE(:paid_at, NOW()), NOW()) で、日付なしは現在時刻、未来になる場合は現在時刻

---

## 規則（SSOT: backend/app/services/payment_dates.py）

- 日付 d → datetime(d.year, d.month, d.day, 12, 0, tzinfo=UTC)
- SQL: PAID_AT_SQL = "LEAST(COALESCE(:paid_at, NOW()), NOW())"
- 全経路（paypal_return / webhook / paypal-confirm / 手動 pay）で同じ関数・同じ SQL 断片を使う

## 旧実装の不具合

旧初版は PayPal の payment_date（str）を :paid_at にそのまま渡していた。asyncpg は timestamptz に str を渡せず TypeError になるため、PayPal 入金の記録が失敗する。本修正で datetime に変換して渡す。

## orders 側の巻き戻し理由

初版は PATCH /orders/{id}/paid（set_order_paid）にも paid_at を追加していたが、呼び出す画面が無い。範囲外のため origin/main と同じ（paid_at = NOW()）に戻した。ADR-072 の reset_tenant_context（commit 直後）だけ残した。

---

## 受け入れ基準

| 基準 | 検証方法（テスト） |
|------|---------|
| date→UTC正午、None→None | backend/tests/test_payment_dates.py::test_paid_at_from_date_* |
| "2026-10-05"→date、None/""/"2026-13-01"/"2026-10-05T01:00:00Z"/123→None | backend/tests/test_payment_dates.py::test_parse_paypal_payment_date_* |
| get_invoice_status が payment_date を date で返す／欠落時 None | backend/tests/test_paypal_invoicing.py::test_get_invoice_status_returns_payment_date_as_date / _payment_date_missing_is_none |
| 手動入金で paid_date を渡すとその日付で記録 | backend/tests/test_invoices.py::test_pay_with_paid_date_sets_that_date |
| body なしでも paid_at が入る | backend/tests/test_invoices.py::test_pay_without_body_uses_now |
| 未来日（今日+3日）は 422 | backend/tests/test_invoices.py::test_pay_future_date_returns_422 |
| 受注が仕入れ中になり paid_at が請求書と同じ | backend/tests/test_invoices.py::test_pay_moves_linked_order_to_sourcing_with_same_paid_at |
| paypal-confirm で invoices/orders 両方の paid_at が payment_date の日付 | backend/tests/test_invoices.py::test_confirm_paypal_uses_payment_date_for_invoice_and_order |
| 画面: 入金日 input は未来日不可・送信は paid_date | frontend の lint・tsc（InvoiceDetailPage に専用テストなし）。目視は PO 確認 |

テスト上の注意: SQLite の NOW() は固定 2026-04-07 のため、日付指定テストは 2026-03-15 を使用。SQLite に LEAST が無いため tests/conftest.py に LEAST を登録した。

---

## 技術 How・KPI

- KPI: PayPal 入金で TypeError にならず、paid_at が入金日（UTC正午）で記録される
- UI: TextFieldControl（ADR-144 の金型の本体）type=date、max はブラウザのローカル今日、aria-label は既存キー invoices.paidAt
- 手動入金の未来日判定は「UTC の明日」までを許容（時差で現地の今日が UTC の明日になる地域のため）。SQL 側 LEAST が最終防御

## 弊害・トレードオフ

- 表示は日付のみ有効（UTC 正午固定のため時刻部分に意味は無い）
- 手動入金で UTC 明日の日付を指定すると LEAST により現在時刻に丸められ、前日表示になることがある

## 計画票

| ステップ | 内容 |
|---------|------|
| 1 | payment_dates.py 新設（テスト先行） |
| 2 | get_invoice_status が date を返す |
| 3 | integrations.py / invoices.py を PAID_AT_SQL・paid_at_from_date に統一 |
| 4 | pay_invoice を paid_date に変更・未来日 422 |
| 5 | orders.py / schemas/order.py を origin/main に戻す（ADR-072 のみ残す） |
| 6 | InvoiceDetailPage.tsx を paid_date 送信・max 付きに |

## 継続

- 完了後の監視: 本番で invoices.paid_at の抜き打ち確認（PO 実行 SQL）

## 維持の仕組み

- 日付→paid_at の変換と SQL 断片は payment_dates.py に一元化。新しい入金経路は paid_at_from_date と PAID_AT_SQL を使うこと
- 守り手: backend/tests/test_payment_dates.py（規則）と backend/tests/test_invoices.py（経路）
