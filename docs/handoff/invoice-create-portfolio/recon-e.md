# 調べ 便E — 支払い手数料

基準: origin/main `77971367b7aba4eb789bc1a913b80fc5d50a8b89`（コードの行番号はこの版）。本番の値は reader 鍵（ai_ro の写し）で 2026-11-20 23:11〜23:13 JST に読んだ。

## 既存 ADR の検索

- `git grep -i 'fee' docs/adr/` と FEATURE-INDEX で見た。当たる決まり:
  - ADR-101 :173「支払い手数料（Wise/PayPalで異なる）を合計計算に必ず含める。」
  - ADR-072（テナントの表と NULL パターン。手数料の表は docs/handoff/payment-fee-settings-d01/design.md）
  - ADR-1079（振込先の版。backend/app/services/invoice_payment_methods.py の頭）
  - ADR-136（移行を含む PR の GO 手順）・ADR-1037（移行のロック待ち）・ADR-155（全テナントを回す移行）・ADR-027（i18n）

## R1 本番の手数料の表（ai_ro.public__payment_fee_settings・7行・全部共用 tenant_id 空・currency JPY・effective_from 2026-01-22・effective_to 空）

| id | fee_type | rate_pct | fixed_amount | threshold | 説明 |
|---|---|---|---|---|---|
| 1 | receiving_domestic | 3.6000 | 40.00 | 空 | 国内商用受取 |
| 2 | receiving_international | 4.1000 | 40.00 | 空 | 海外受取 |
| 3 | withdrawal | 0 | 0 | 50000 above | 出金 5万以上 |
| 4 | withdrawal | 0 | 250 | 50000 below | 出金 5万未満 |
| 5 | instant_withdrawal | 2.0000 | 0 | 空 | 即時引き出し |
| 6 | fx_receiving | 4.0000 | 0 | 空 | 為替（受取時） |
| 7 | fx_other | 3.0000 | 0 | 空 | 為替（その他） |

- service はすべて paypal。wise・stripe・銀行の行は0。
- public.payment_fee_settings そのものは reader 鍵に権限なし（InsufficientPrivilege）。ai_ro の写しで読んだ。

## R2 支払方法の登録（本番）

- public.tenant_paypal_config: tenant 6 に1行だけ。
- tenant_001・003・004・005・006 の tenant_invoice_payment_methods: 0行（GROUP BY の結果0行）。

## R3 合計の計算（backend/app/services/invoice_totals.py）

- :190 compute_totals は純粋な関数。合計 = 小計＋送料＋税＋関税。手数料は無い。
- :407-412 関税の行は `effective_from <= :d AND COALESCE(effective_to, DATE '9999-12-31') >= :d` で選ぶ。
- :443 load_totals_inputs・:459 first_block・:467 to_db_params。
- 呼ぶ所は backend/app/routers/invoices.py だけ（:247-250 _compute・:416-419 preview・:575 from-quote・:679 create・:810 issue）。見積の道からは呼ばない。

## R4 請求書の道（backend/app/routers/invoices.py）

- :142 _INVOICE_COLUMNS・:173 _INSERT_INVOICE_SQL・:195-200 _RECOMPUTE_SET_SQL（発行時に作り直す列）。
- :403-431 preview: 支払方法を受けない。bill_to を読み（:414）、destination を決めて計算。
- :513-606 from-quote: payment None・payment_method_id None。
- :615-716 create: 計算（:645-650）の後に支払方法を確かめる（:652-662）。payment_text は resolve_payment_ref が返す method_type（'bank'/'wise'/'paypal'）。
- :724-771 update（下書き）: 支払方法を書き換えるが合計は作り直さない。
- :779-830 issue: 支払方法の版の確かめ（:791-797）→ 合計を作り直して _RECOMPUTE_SET_SQL で書く。
- :943-1042 issue_paypal_link: PayPal へ total_amount を送る（:986）。payment_method を COALESCE(payment_method,'paypal') にする（:1002）。
- :1124-1131 _pdf_payment・:1137-1190 PDF（invoice_data は :1155-1180）。PayPal の写しの PDF は _render_paypal_copy_pdf（:1196-）が別の invoice_data（:1201-1224）を作る。invoice_data に subtotal・shipping_fee・tax_amount・total_amount・duty_amount を渡す。
- 既存の payment_fee 列は入金時に実際の手数料を書く: invoices.py:1095・integrations.py:799・:948。列は migrations/20260611_020000_add_invoice_paypal_columns.sql:28。

## R5 地域

- backend/app/services/issuer.py:20-27 decide_issuer_region: 請求先の国 JP → 'domestic'、それ以外 → 'overseas'、国なし → None。

## R6 画面

- frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:113-121 試算の依頼（company_id・currency・items・shipping）。支払方法は入っていない。:184 作成時に payment_method_ref を送る。
- frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx:200-207 TotalsBox の rows（小計・送料・税）と total。:209-216 未計算の理由。
- frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:93 payment_fee の型・:354-361 tfoot の合計行。
- backend/app/services/invoice_renderer.py:387-401 PDF の送料・税・関税の行（0 や None なら描かない）。

## R7 表の雛形と見え方

- backend/app/services/tenant.py:875-918 請求書の表の雛形（payment_fee は :902）。
- migrations/20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql（便A の列追加の前例）。
- クラウドの見え方の分類表 migrations/20261024_100300_create_ai_cloud_views.sql:446 付近に invoices。分類の無い text/jsonb は伏せる（backend/tests/ops/test_ai_cloud_views.py:310）。

## R8 見本

- 見本（https://shingo-portfolio.github.io/invoice-tool/）は支払方法が「銀行振込・クレジットカード・送金サービス」で、合計に支払い手数料は無い。「関税・手数料（概算）」は米国の関税の計算（app.js:119）。PO 決定（design-e.md §0）で ADR-101 に合わせて足す。
