# 設計 便E — PayPal の支払い手数料を請求書の合計に足す

基準: origin/main `77971367b7aba4eb789bc1a913b80fc5d50a8b89`（2026-11-20 23:xx JST に fetch）。調べの元は同じフォルダの recon-e.md。
状態: 設計案（Opus 作成）。PO 決定 2026-11-20 は下の §0。

## 0. PO の決定（原文）

- 2026-11-20 1回目「1」: 「支払方法ごとに手数料を計算して、お客様への合計に足す【おすすめ】 決まりどおりの形です。登録済みの手数料の値は、しんごさんに画面で確かめてもらってから使います。」
- 2026-11-20 2回目「2」: 「1に加えて、PayPal の為替手数料4%も足す ドルなど円以外の請求で、お客様の請求額がさらに4%上がります。」
  - 選ぶ前に PO へ見せた値（recon-e.md R1）: 日本のお客様 3.6%＋40円、海外のお客様 4.1%＋40円、為替 4%。銀行・Wise の登録は0件。
- 決まり: ADR-101 :173「支払い手数料（Wise/PayPalで異なる）を合計計算に必ず含める。」

## 1. 目的と利用者に見える変化

- 前: 支払方法に PayPal を選んでも、お客様への合計は手数料なしの額。手数料は売り手が負う。
- 後: 支払方法が PayPal のとき、作成画面の合計枠に「支払い手数料」の行が出て、合計に足される。作った請求書の詳細画面と PDF にも同じ行と額が出る。PayPal の請求リンクもこの合計で作られる（既存どおり total_amount を送る）。
- 銀行振込・Wise を選んだときは何も変わらない（行も出ない・0円）。

## 2. 対象と対象外

対象:
- backend/app/services/invoice_totals.py（計算と手数料の行の読み込み）
- backend/app/routers/invoices.py（preview・create・update・issue の4つの道）
- backend/app/schemas/invoice.py（preview の依頼に支払方法・応答に手数料）
- backend/app/services/invoice_renderer.py（PDF の行）
- backend/app/services/tenant.py（新しいテナントの請求書の表に2列）
- migrations/ 新しい1本（全テナントの invoices に2列・nullable・ADD COLUMN IF NOT EXISTS）＋ scripts/run_all_migrations.sh に1行
- frontend: invoice-create（試算の依頼に支払方法を足す・合計枠に1行）、invoice-detail（1行）、lib/invoiceDraftContext.ts の型、ja.json/en.json
- 試験: test_invoice_totals.py（純粋な計算）・test_invoice_totals_pg.py か invoices の道の試験・画面の単体試験

対象外（触らない）:
- 銀行・Wise の手数料（登録0件。PO 決定で今回は0円）
- 出金・即時引き出し・その他の為替（withdrawal・instant_withdrawal・fx_other）は売り手が自分でお金を動かす時の費用なので使わない
- invoices.payment_fee（PayPal の入金時に実際の手数料を書く既存の列。integrations.py:799・:948、invoices.py:1095）は意味も書き方も変えない
- 見積（quotes）の合計。見積には支払方法が無い
- 見積から作る道（from-quote）は支払方法が無い（payment None）ので手数料0。変えない
- 発行済みの請求書に後から PayPal リンクを出す道（issue_paypal_link が payment_method を COALESCE で 'paypal' にする :1002）は合計を作り直さない。§7 弊害に書く
- 手数料の表の画面（設定の画面）。値の登録・変更は既存の画面のまま

## 3. 設計

### 3-1 どの行を使うか

- 使う条件: 支払方法の種類（method_type）が 'paypal' のときだけ。'bank'・'wise'・支払方法なしは手数料0で、表を読まない。
- 受取の種類（fee_type）: 発行元の地域（issuer_region。backend/app/services/issuer.py:20-27 が請求先の国 JP なら domestic）で決める。
  - domestic → 'receiving_domestic'
  - overseas → 'receiving_international'
- 為替: 請求書の通貨が 'JPY' でないときだけ 'fx_receiving' の行も足す（PO 決定 2回目）。
- 行の選び方（どの fee_type も同じ）: public.payment_fee_settings から service='paypal'・fee_type 一致・currency='JPY'・effective_from <= 基準日・COALESCE(effective_to, DATE '9999-12-31') >= 基準日（関税の行の読み方 invoice_totals.py:407-412 と同じ）。テナント独自の行（tenant_id = 自社）があればそれを、無ければ共用の行（tenant_id IS NULL）を使う（NULL パターン・d01 design.md）。同じ側に複数あれば effective_from が新しい1行。
- 基準日: 既存の totals と同じ base_date（today_jst）。
- 受取の行が無い、または選んだ行の threshold が NULL でない（今の受取の行はすべて NULL。recon-e.md R1）ときは計算しない: 新しい理由 REASON_PAYMENT_FEE = "payment_fee" を uncomputed に入れる。為替の行が要るのに無いときも同じ。

### 3-2 計算

- 元の額 B = subtotal + shipping_fee + tax_amount + duty_amount（どれも今の compute_totals がすでに請求書の通貨で出している額）。
- 率 r = 受取の rate_pct ＋（為替が要るとき）為替の rate_pct。
- 固定額 F = 受取の fixed_amount（JPY）を今の _convert で請求書の通貨に直した額（為替が無ければ既存の REASON_FX で止まる）。為替の行の fixed_amount も足す（今は0）。
- 手数料 = B × r / 100 + F を、他の額と同じ切り捨て（通貨の最小単位）にする。
- 合計 = B + 手数料。
- 式は手数料の表の決まり（amount × rate_pct/100 + fixed_amount。migrations/20261002_180000 の列の説明）に合わせる。手数料にさらに手数料がかかる分（PayPal は合計全体に率をかける）は足さない。§7 に差の大きさを書く。

例（試験に使う）:
- JPY・国内・B=100,000 → 100,000×3.6/100 + 40 = 3,640 → 合計 103,640
- USD・海外・B=1,000.00・1USD=150円 → 1,000×(4.1+4)/100 + 40/150 = 81 + 0.2666… = 81.26（切り捨て）→ 合計 1,081.26

### 3-3 compute_totals の形

- 純粋な関数のまま（DB を読まない）。引数に `payment_method_type: str | None = None` を足す。
- TotalsInputs に `payment_fee_rows: PaymentFeeRows | None`（受取の行・為替の行・それぞれ id/rate_pct/fixed_amount/threshold/fee_type）を足す。load_totals_inputs が `issuer_region`・`currency`・`payment_method_type` を受けて、paypal のときだけ読む。
- TotalsResult に `payment_fee: Decimal`（paypal 以外は 0）と `payment_fee_snapshot: dict | None`（paypal のときだけ: method_type・fee_types・setting_ids・rate_pct 合計・fixed_amount_jpy・fixed_converted・base_amount・base_date）を足す。
- to_db_params に `payment_fee_charged`・`payment_fee_snapshot` を足す。

### 3-4 保存（DB の正本）

- 全テナントの invoices に2列を足す（nullable・既存の行は NULL のまま）:
  - payment_fee_charged NUMERIC(15,2): お客様への合計に足した支払い手数料（請求書の通貨）
  - payment_fee_snapshot JSONB: その計算に使った行と値の写し（あとで設定が変わっても、この請求書が何で計算されたか分かる）
- 既存の payment_fee（入金時の実際の額）とは別の列にする。理由: 1つの列に「請求した額」と「実際に引かれた額」を混ぜると、入金時に上書きされて請求額が消える（integrations.py:799）。
- 移行の形は 20260611_020000 と 20261113_120000（便A）にならう: pg_namespace の tenant_% を回し ADD COLUMN IF NOT EXISTS と COMMENT。破壊操作なし。tenant.py の雛形（:875-918）にも同じ2列を足す。
- クラウドの読み取りの見え方: 新しい JSONB 列は分類表に載せなければ伏せられる（backend/tests/ops/test_ai_cloud_views.py:310「分類の無い text は伏せる」・jsonb も同じ）。数の列は見える。分類表は変えない。
- _INVOICE_COLUMNS（invoices.py:142）・_INSERT_INVOICE_SQL（:173）・_RECOMPUTE_SET_SQL（:195-200）に2列を足す。InvoiceResponse/InvoiceDetailResponse に payment_fee_charged を足す（snapshot は返さない）。

### 3-5 4つの道

- POST /invoices/preview: 依頼に `payment_method_type: Literal['bank','wise','paypal'] | None = None` を足す（id は要らない。額は種類だけで決まる）。作成画面は選んだ支払方法の種類を送る。応答に `payment_fee: Decimal` を足す。地域は今ある decide_issuer_region(bill_to) で決める（preview は今 bill_to を読んでいる :411）。
- POST /invoices: resolve_payment_ref で確かめた method_type を compute に渡す。今は支払方法の確かめが計算の後（計算 :645-650・確かめ :652-662）なので、確かめを計算の前へ移す（順番だけ。中身は同じ）。
- PATCH /invoices/{id}（下書きだけ）: payment_method_ref が来たら、その種類で合計を作り直し、_RECOMPUTE_SET_SQL と同じ列を書く（今は支払方法だけ書いて合計を直さない :740-760。直さないと詳細画面の合計が古いまま）。
- POST /invoices/{id}/issue: 保存されている payment_method（'bank'/'wise'/'paypal' の文字。resolve_payment_ref が返す method_type をそのまま保存している :656-661）を compute に渡す。今も発行時に合計を作り直しているので、手数料も同じ時点の値で作り直される。
- POST /invoices/from-quote: 支払方法なし → 手数料0。変えない（compute の既定値 None）。

### 3-6 画面

- 作成画面 InvoiceCreatePage.tsx:113-121 の試算の依頼に `payment_method_type`（選んだ支払方法の種類。paymentRefFromKey と同じ出どころ）を足す。支払方法を変えると試算が取り直される（依頼の中身が変わるので useInvoicePreview の key が変わる）。
- 合計枠 InvoicePaymentTotalsSection.tsx:200-207 の TotalsBox の rows に、`preview.payment_fee > 0` のときだけ1行足す: key "paymentFee"・ラベル t("invoiceForm.paymentFee")・data-testid "invoice-total-payment-fee"。TotalsBox は既存の金型。新しい部品・色・直書きは作らない。
- 理由の表示: uncomputedReasonKey に "payment_fee" を足し、ja/en に文を足す。
- 詳細画面 InvoiceDetailPage.tsx:357-358 の tfoot に、payment_fee_charged > 0 のときだけ1行（t("invoices.paymentFeeCharged")）。既存の行と同じ書き方（この表は既存の形のまま。新しい直書きの色は足さない）。
- PDF invoice_renderer.py:387-401 の送料・税・関税の行と同じ形で、payment_fee_charged > 0 のときだけ "Payment fee" の行（既存の行の英語の書き方に合わせる）。invoices.py:1162-1180 の invoice_data に payment_fee_charged を渡す。PayPal の写しの PDF も同じ render を通る。
- i18n: ja「支払い手数料」/ en「Payment fee」・理由 ja「支払い手数料の設定が見つかりません」/ en「No payment fee setting was found」。ja.json と en.json に同じキー（ADR-027）。

## 4. 代替案と選んだ理由

| 案 | 中身 | 選ばない理由 |
|---|---|---|
| A（採用） | 新しい2列に請求額と写しを保存 | — |
| B | 既存の payment_fee に請求額を入れる | 入金時に実際の額で上書きされ請求額が消える |
| C | 保存せず毎回計算 | 設定を変えると過去の請求書の額が変わる。PDF と合計が食い違う |
| D | 手数料を商品の行として足す | 商品の行は在庫・重さ・関税の計算に入るので混ざる |
| E | 手数料にかかる手数料まで足す（割り戻し） | 表の決まりの式と違う式になる。§7 で差を示し、要るなら別の決定で |

## 5. 受入条件

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | JPY・国内・PayPal・B=100,000 で手数料 3,640・合計 103,640 | test_invoice_totals.py の純粋な関数の試験 |
| K2 | USD・海外・PayPal・B=1,000.00・1USD=150円で手数料 81.26・合計 1,081.26 | 同上 |
| K3 | bank・wise・支払方法なしで手数料0・合計は今と同じ | 同上（今の試験の期待値が1つも変わらない） |
| K4 | テナント独自の行があれば共用の行より優先・期間外の行は使わない | 同上（行を入力で与える） |
| K5 | 受取の行が無い・threshold がある・為替の行が要るのに無い → uncomputed に "payment_fee"、create は 409 | 純粋な関数の試験＋道の試験 |
| K6 | create・PATCH・issue で payment_fee_charged と total_amount が保存され、詳細の応答に出る | test_invoice_totals_pg.py か invoices の道の試験（PG） |
| K7 | 下書きで支払方法を bank→PayPal に変えると合計が手数料の分だけ上がる | 道の試験 |
| K8 | 作成画面: PayPal を選ぶと合計枠に「支払い手数料」行が出て合計が上がる・銀行では行が出ない | 画面の単体試験（vitest） |
| K9 | 移行が全テナントで2列を足し、2回流しても失敗しない・雛形にも同じ2列 | CI の migration の試験・migration-guard |
| K10 | 本番: 移行の後、全テナントの invoices に2列がある | reader 鍵で information_schema.columns を数える（5テナント×2列＝10行） |
| K11 | 本番の画面の束に新しい testid "invoice-total-payment-fee" がある | 本番の bundle を取って文字を数える（1以上） |
| K12 | PO が本番の作成画面で PayPal を選び、行と額を見て○ | PO 目視（推測で○にしない） |

## 6. リスクと対処

- 移行（危険な道）: nullable の ADD COLUMN だけ・既存の行を書かない。ADR-136 の GO 手順（委任 GO）とバックアップの確認をマージの前にする。ロック待ちは run_sql の lock_timeout（ADR-1037）。
- 今の請求書は全テナントで0件（recon の 11/14 の数え）。今回マージ前にもう一度数える。
- 合計の額が変わる: PayPal のときだけ。銀行・Wise・なしは試験 K3 で今と同じことを確かめる。
- 戻し方: 画面とコードは前のコミットに戻す。2列は nullable で残しても害なし（戻すときは DROP COLUMN IF EXISTS を手で。移行の頭に書く）。

## 7. 弊害・トレードオフ

- 手数料にかかる手数料は足さない（§3-2）。差の大きさ: 国内 B=100,000 で、PayPal は 103,640 に 3.6%+40 = 3,771 を引くので、手取りは 99,869（131 円少ない）。
- 発行済みの請求書にあとで PayPal リンクを出す道（支払方法が空のとき 'paypal' を入れる）は合計を作り直さないので、その場合は手数料なしの額で PayPal の請求が作られる。支払方法を下書きで選ぶ今の流れでは起きない。
- 手数料の値は表の値をそのまま使う。値が PayPal の今の値と合っているかは PO が画面で確かめる（K12 の前に PO に頼む）。

## 8. 外部事例

- PayPal の手数料の公式ページ（表の source_url。https://www.paypal.com/jp/business/paypal-business-fees）が値の出どころ。今回は表の値を正本として使い、外部の値を設計に書き写さない（数を作らない）。
- 他社の事例は使わない。理由: 今回の論点は「自社の表の値をどの道で合計に足すか」で、外部の数値の当てはめが無い。

## 9. 維持の仕組み

- 計算は invoice_totals.py の1か所（純粋な関数）。試験 K1〜K5 が式と行の選び方を固定する。
- 値は public.payment_fee_settings が正本。コードに率を書かない（試験の入力にだけ書く）。
- 請求書ごとの写し（payment_fee_snapshot）で、あとから「何で計算したか」を確かめられる。
- 画面の行は既存の金型 TotalsBox だけを使う。i18n は CI の ja/en 一致チェック。

## 10. 便の分け方

- 1本の PR（移行1本を含むので危険な道。ADR-136 の GO 手順）。移行と画面を分けると、列が無い間に新しいコードが動かないため。
- 実装はクラウドの Sonnet。カードは card-e.md。
