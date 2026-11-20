# 設計 便E — PayPal の支払い手数料を請求書の合計に足す

基準: origin/main `77971367b7aba4eb789bc1a913b80fc5d50a8b89`（2026-11-20 23:xx JST に fetch）。調べの元は同じフォルダの recon-e.md。
状態: 設計審査済み（4回目 APPROVE・推奨4件反映）。PO 決定 2026-11-20 は下の §0。

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
- AI 用の読み取りの分類（§3-4）: migrations/20261024_100300_create_ai_cloud_views.sql の分類表に1行・その件数を数える試験・docs/handoff/cloud-case-ai/stage1-column-class.tsv と scripts/migration-guard/reference-allowlist.tsv のハッシュ（前例: コミット 1206acb5）
- 試験の登録: backend/tests/rls_bootstrap.py の一覧（:192 付近）と backend/tests/test_tenant_loop_migration_guard.py の `_REVIEWED` に新しい移行を足す（前例: 同じ 1206acb5）
- frontend: invoice-create（試算の依頼に支払方法を足す・合計枠に1行）、invoice-detail（1行・PayPal リンクの出し方 §3-5・同じファイルの型 `interface InvoiceDetail`（frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:56）に `payment_fee_charged: number | null` を足す）、lib/invoiceDraftContext.ts の型、lib/apiErrorReason.ts、ja.json/en.json
- 試験: test_invoice_totals.py（純粋な計算）・test_invoice_totals_pg.py・invoices の道の試験・test_paypal_invoicing.py（§3-5 の PayPal リンクの条件）・conftest.py（SQLite の invoices 表に2列・stub_invoice_totals の差し替えに引数と手数料の行）・画面の単体試験

対象外（触らない）:
- 銀行・Wise の手数料（登録0件。PO 決定で今回は0円）
- 出金・即時引き出し・その他の為替（withdrawal・instant_withdrawal・fx_other）は売り手が自分でお金を動かす時の費用なので使わない
- invoices.payment_fee（PayPal の入金時に実際の手数料を書く既存の列。integrations.py:799・:948、invoices.py:1095）は意味も書き方も変えない
- 見積（quotes）の合計。見積には支払方法が無い
- 見積から作る道（from-quote）は支払方法が無い（payment None）ので手数料0。変えない
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
- 理由の置き場所: invoice_totals.py:28 の `REASON_ORDER` の最後に REASON_PAYMENT_FEE を足す。`uncomputed=[r for r in REASON_ORDER if r in reasons]`（:353）は REASON_ORDER に無い理由を捨てるため、足さないと理由が消える。最後に置くのは、送料・為替・税・関税が先に止まっていれば手数料は計算できない（元の額が無い）ため。止め方は既存の first_block（:459-464）のまま 409 "payment_fee"。
- 地域（fee_type を決める値）の出どころは道ごとに1つ:
  - preview・create: decide_issuer_region(bill_to)（create は今もこれで issuer_region を決めて保存している :640-642）。preview で None（請求先の国なし）のときは手数料の理由 "payment_fee" で止める（create は今どおり 422 "bill_to_country" で先に止まる）。
  - PATCH・issue: 保存された invoices.issuer_region。None のとき（ADR-1061 より前の行だけ）は今の支払方法の確かめと同じ "overseas"（invoices.py:748・:797 の `or "overseas"`）。

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
- 手数料を計算する場所: 今の「合計」の塊（:313-318）と「請求書の通貨の為替」の塊（:320-331。為替が無いと total_amount を None にする）の後、amount_jpy・amount_usd を出す塊（:332-341）の前。total_amount が None のときは手数料も計算しない（理由はすでに入っている）。手数料を足した total_amount から amount_jpy・amount_usd を出すので、円・ドル換算も手数料込みになる。
- TotalsInputs に `payment_fee_rows: PaymentFeeRows | None = None`（受取の行・為替の行・それぞれ id/rate_pct/fixed_amount/threshold/fee_type）を足す。既定値 None を付けるのは、TotalsInputs を作っている既存の4か所（invoice_totals.py・conftest.py の stub_invoice_totals・test_invoice_totals.py・test_invoice_totals_pg.py）を壊さないため。
- 行の選び方（§3-1。テナント独自を優先・期間内・新しい effective_from）は load_totals_inputs の SQL が受け持ち、選んだ1行ずつを PaymentFeeRows に入れる。compute_totals は選ばれた行を使うだけ。
- load_totals_inputs にキーワード引数 `issuer_region: str | None = None`・`currency: str | None = None`・`payment_method_type: str | None = None` を足し、payment_method_type == "paypal" のときだけ表を読む。既定値があるので今の呼び出しは変えなくても動く。
- conftest.py の stub_invoice_totals（:2356-2390）の `_fake` は `**_kw` を受けるようにし、state に `"payment_fee_rows": None` を足して TotalsInputs に渡す（試験は `.set(payment_fee_rows=...)` で行を与える）。
- PaymentFeeRows の中身: receiving（1行。無ければ None）・fx（1行か None。JPY のときは読まない）・required_fx（bool。通貨が JPY 以外か）。compute は「receiving が None」「required_fx なのに fx が None」「どちらかの threshold が NULL でない」で REASON_PAYMENT_FEE。
- payment_method_type == "paypal" なのに inputs.payment_fee_rows が None のとき（stub の既定値・読み忘れ）も REASON_PAYMENT_FEE にする（黙って0にしない）。
- 呼び出し側の引数: invoices.py の `_compute`（:245-252）にキーワード引数 `payment_method_type: str | None = None`・`issuer_region: str | None = None` を足し、load_totals_inputs へ `issuer_region`・`currency`・`payment_method_type` を、compute_totals へ `payment_method_type` を渡す。preview は `_compute` を通らず直接呼ぶ（:416-425）ので、そこにも同じ3つ（load）と1つ（compute）を足す。
- TotalsResult に `payment_fee: Decimal`（paypal 以外は 0。REASON_PAYMENT_FEE で止まったときも 0。そのとき total_amount は None）と `payment_fee_snapshot: dict | None`（paypal のときだけ: method_type・fee_types・setting_ids・rate_pct 合計・fixed_amount_jpy・fixed_converted・base_amount・base_date）を足す。
- to_db_params に `payment_fee_charged`・`payment_fee_snapshot` を足す。

### 3-4 保存（DB の正本）

- 全テナントの invoices に2列を足す（nullable・既存の行は NULL のまま）:
  - payment_fee_charged NUMERIC(15,2): お客様への合計に足した支払い手数料（請求書の通貨）
  - payment_fee_snapshot JSONB: その計算に使った行と値の写し（あとで設定が変わっても、この請求書が何で計算されたか分かる）
- 既存の payment_fee（入金時の実際の額）とは別の列にする。理由: 1つの列に「請求した額」と「実際に引かれた額」を混ぜると、入金時に上書きされて請求額が消える（integrations.py:799）。
- 移行の形は 20260611_020000 と 20261113_120000（便A）にならう: pg_namespace の tenant_% を回し ADD COLUMN IF NOT EXISTS と COMMENT。破壊操作なし。tenant.py の雛形（:865-918）にも同じ2列を足す。置き場所は `notes TEXT`（:912）の前で、便A のコメント（:131 付近の「invoice-create-portfolio 便A: …」）と同じ形のコメントを1行付ける。
- クラウドの読み取りの見え方（AI 用の分類表）: 変える。JSONB は型だけでは通らない（migrations/20261024_100000_create_ai_cloud_meta.sql:122-129）ので、分類表に行が無いと backend/tests/ops/test_ai_cloud_views.py:518-520 が「分類なし」と数え、T10（:528-567）が落ちる。便A の shipping_snapshot と同じ形にする:
  - migrations/20261024_100300_create_ai_cloud_views.sql の invoices の行（:454 付近）に `('tenant_*','invoices',ARRAY['payment_fee_snapshot'],'mask','')` を足す（中身は伏せる）。payment_fee_charged は数の列なので行は要らない。
  - test_ai_cloud_views.py:486 の件数を 1164 → 1165 にする。
  - docs/handoff/cloud-case-ai/stage1-column-class.tsv に `tenant_*\tinvoices\tpayment_fee_snapshot\tmask\t\tjsonb` の1行（invoices の行の並び・shipping_snapshot の次）を足す。scripts/migration-guard/reference-allowlist.tsv の 20261024_100300 の sha256 を作り直し、根拠の欄の最後に「 / invoice-create-portfolio card-E（分類1行追加）」を足す（手順は 1206acb5 と同じ）。
- _INVOICE_COLUMNS（invoices.py:142）・_INSERT_INVOICE_SQL（:173）・_RECOMPUTE_SET_SQL（:195-200）に2列を足す。InvoiceResponse/InvoiceDetailResponse に payment_fee_charged を足す（snapshot は返さない）。

### 3-5 4つの道

- POST /invoices/preview: 依頼に `payment_method_type: Literal['bank','wise','paypal'] | None = None` を足す（id は要らない。額は種類だけで決まる）。作成画面は選んだ支払方法の種類を送る。応答に `payment_fee: Decimal` を足す。地域は今ある decide_issuer_region(bill_to) で決める（preview は今 bill_to を読んでいる :414）。
- POST /invoices: resolve_payment_ref で確かめた method_type を compute に渡す。今は支払方法の確かめが計算の後（計算 :645-650・確かめ :652-662）なので、確かめを計算の前へ移す（順番だけ。中身は同じ）。
- PATCH /invoices/{id}（下書きだけ）: payment_method_ref が来たら、その種類で合計を作り直し、_RECOMPUTE_SET_SQL と同じ列を書く（今は支払方法だけ書いて合計を直さない :740-760。直さないと詳細画面の合計が古いまま）。手順:
  1. 今の resolve_payment_ref の確かめ（region は今どおり `old_row["issuer_region"] or "overseas"`）。
  2. 明細を読み（_get_invoice_items）、issue と同じ引数（_shipping_from_stored(old_row)・保存された ship_to/bill_to の写し・保存された currency）に payment_method_type=ref.method_type・issuer_region を足して _compute。
  3. `_raise_if_blocked(totals)`。止まるときは UPDATE の前なので何も書かない（支払方法も変わらない）。409 と理由の文字（例 "payment_fee"・"fx_rate"）を返す。
  4. issue と同じく to_db_params から shipping_carrier・shipping_service を外し、`UPDATE invoices SET payment_method=…, payment_method_id=…, {_RECOMPUTE_SET_SQL}, updated_at=NOW() WHERE id=:id AND status='draft'` を1文で書く。同じ依頼で due_date・notes も来たときは、今の set_clauses（:757）と同じくその列もこの1文に入れる（2回に分けない）。
  - due_date・notes だけの PATCH は今どおり作り直さない。
  - 作り直すので、税・為替・送料の換算も今日の値になる（発行のときも同じく作り直すので、発行時の額は今と変わらない）。
- POST /invoices/{id}/issue: 保存されている payment_method（'bank'/'wise'/'paypal' の文字。resolve_payment_ref が返す method_type をそのまま保存している :656-661）と issuer_region を compute に渡す。今も発行時に合計を作り直しているので、手数料も同じ時点の値で作り直される。
- POST /invoices/from-quote: 支払方法なし → 手数料0。変えない（compute の既定値 None）。下書きのうちに詳細画面で PayPal を選べば、上の PATCH で手数料込みに作り直される。
- POST /invoices/{id}/paypal-link（発行済みに PayPal の請求を出す道 :943-1042）: 今は支払方法が銀行・Wise・なしの請求書でも出せ、手数料の無い total_amount を PayPal へ送る（:986）。ADR-101 :173 の決まりに反するので、出せる条件を絞る:
  - `inv_row["payment_method"] != "paypal"` なら PayPal へ送る前に 409 "payment_method" で止める（何も書かない）。
  - :1002 の `COALESCE(payment_method, 'paypal')` は、条件を絞った後は常に 'paypal' なので式はそのまま残す（変えない）。
  - 詳細画面 frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:216 のリンクのボタンは `invoice.payment_method === "paypal"` のときだけ出す（条件を1つ足す）。
  - 既存の試験 test_paypal_invoicing.py の `_issued_invoice`（:202-211）は支払方法なしで作っているので、PayPal の請求書として作る形に直す。支払方法なしの請求書で 409 になる試験を1つ足す。
  - 試験での支払方法の作り方（SQLite）: SQLite の試験の表には振込先の表 tenant_invoice_payment_methods が無い（backend/tests/conftest.py には :1238 の tenant_paypal_config だけ）。resolve_payment_ref → list_payment_choices（backend/app/services/invoice_payment_methods.py:28-62）はこの表を読むので、そのままでは落ちる。そこで conftest.py に fixture `fake_payment_ref` を足す: `monkeypatch.setattr(invoice_payment_methods, "resolve_payment_ref", _fake)`。`_fake(db, tenant_id, *, method_type, method_id, region, currency)` は `(method_type, method_id)` を返す。invoices.py は `invoice_payment_methods.resolve_payment_ref`（:656・:746）とモジュール経由で呼ぶので、この差し替えが効く。手数料の行は stub_invoice_totals の `.set(payment_fee_rows=...)` で与える（表は読まない）。
  - test_paypal_invoicing.py は fixture `fake_payment_ref` を使い、`_issued_invoice` に `payment_method_ref: {"method_type": "paypal", "id": None}` を足し、作る前に stub へ手数料の行を set する。K6・K7 の道の試験も同じ fixture で SQLite で動かす。
  - 道の試験では銀行（bank）も `{"method_type": "bank", "id": None}` で作る。method_id が空でないと、詳細の `load_payment_label`（invoices.py:499）と発行の `is_current_choice`（invoices.py:793-795）が SQLite に無い表を読んで落ちるため。id を入れる試験が要るときは、同じ fixture でこの2つも差し替える。

### 3-6 画面

- 作成画面 frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:113-121 の試算の依頼に `payment_method_type`（選んだ支払方法の種類。paymentRefFromKey と同じ出どころ）を足す。支払方法を変えると試算が取り直される（依頼の中身が変わるので useInvoicePreview の key が変わる）。
- 合計枠 frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx:200-207 の TotalsBox の rows に、`preview.payment_fee > 0` のときだけ1行足す: key "paymentFee"・ラベル t("invoiceForm.paymentFee")・data-testid "invoice-total-payment-fee"。TotalsBox は既存の金型。新しい部品・色・直書きは作らない。
- 理由の表示: frontend/src/lib/apiErrorReason.ts の API_ERROR_REASON_KEYS（:30-35 に既存の理由）に `payment_fee: "apiError.paymentFee"` を足す。uncomputedReasonKey（invoiceDraftContext.ts:191）はこの表を読むので、そこは変えない。ja/en に apiError.paymentFee の文を足す。既存の `payment_fee_setting`（:72・設定の画面の「見つかりません」）とは別のキー。
- 詳細画面 frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:357-358 の tfoot に、payment_fee_charged > 0 のときだけ1行（t("invoices.paymentFeeCharged")）。既存の行と同じ書き方（この表は既存の形のまま。新しい直書きの色は足さない）。
- PDF invoice_renderer.py:387-401 の送料・税・関税の行と同じ形で、payment_fee_charged > 0 のときだけ "Payment fee" の行（既存の行の英語の書き方に合わせる）。invoice_data は2か所あるので両方に payment_fee_charged を渡す: 請求書の PDF（invoices.py:1155-1180）と PayPal の写しの PDF（_render_paypal_copy_pdf の :1201-1224）。invoice_renderer.py のデータ型（duty_amount の :149 の次）と組み立て（:572 の次）にも `payment_fee_charged: float | None = None` を足す。見積の組み立て（:645）は None のまま。
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
| K4 | テナント独自の行があれば共用の行より優先・期間外の行は使わない・同じ側に2行あれば effective_from が新しい行 | test_invoice_totals_pg.py（PG に payment_fee_settings の行を入れて load_totals_inputs を呼ぶ。`_PUBLIC_MIGRATIONS`（:42-48）に 20261002_160000_create_payment_fee_settings.sql を足す。テナント独自の行の tenant_id は public.tenants に要る（外部キー）ので、試験の中で tenants に無ければ入れて最後に戻す） |
| K5 | 受取の行が無い・threshold がある・為替の行が要るのに無い → uncomputed に "payment_fee"（REASON_ORDER の最後）、create・PATCH は 409 "payment_fee" で何も書かない | 純粋な関数の試験＋道の試験 |
| K6 | create・PATCH・issue で payment_fee_charged と total_amount が保存され、詳細の応答に出る | invoices の道の試験（SQLite・fixture fake_payment_ref と stub の手数料の行） |
| K7 | 下書きで支払方法を bank→PayPal に変えると合計が手数料の分だけ上がる・PayPal→bank で手数料0に戻る・止まるときは支払方法も合計も変わらない | 道の試験（SQLite・fixture fake_payment_ref） |
| K7c | 請求書の PDF と PayPal の写しの PDF の両方に、手数料 > 0 のとき "Payment fee" の行が出る（PDF の文字を読む試験） | invoice_renderer の試験＋test_paypal_invoicing.py |
| K7b | 支払方法が PayPal でない発行済みの請求書に PayPal リンクを出すと 409 "payment_method"・PayPal へ送らない。PayPal の請求書は今どおり出せ、送る額は手数料込みの total_amount | test_paypal_invoicing.py |
| K8 | 作成画面: PayPal を選ぶと合計枠に「支払い手数料」行が出て合計が上がる・銀行では行が出ない | 画面の単体試験（vitest） |
| K9 | 移行が全テナントで2列を足し、2回流しても失敗しない・雛形にも同じ2列・AI 用の分類の漏れ0件（T10）・件数 1165 | CI の migration の試験・migration-guard・test_ai_cloud_views.py・test_tenant_loop_migration_guard.py。雛形は便A の test_tenant_ddl_has_duty_tables_and_invoice_columns（backend/tests/test_tenant_duty_rules_pg.py:74）と同じ型で確かめる。新しい試験ファイルに移行の名前を書くなら `_REVIEWED` にそのファイルの "scoped" の行を足し（前例 1206acb5）、rls_bootstrap.py の一覧（:192 の並び）に数1で入れる |
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
- 支払方法が PayPal でない請求書（銀行・Wise・見積から作って支払方法を選ばずに発行したもの）には、発行後に PayPal の請求を出せなくなる（§3-5）。PayPal で受けたいときは下書きのうちに支払方法を PayPal にする。今の請求書は全テナントで0件（§6 でマージ前に数え直す）。
- 下書きで支払方法を変えると、税・為替・送料の換算もその日の値で作り直される（§3-5 PATCH）。
- 手数料の値は表の値をそのまま使う。値が PayPal の今の値と合っているかは PO が画面で確かめる（K12 の前に PO に頼む）。

## 8. 外部・過去事例の参照と我々への応用

- PayPal の手数料の公式ページ（表の source_url。https://www.paypal.com/jp/business/paypal-business-fees）が値の出どころ。今回は表の値を正本として使い、外部の値を設計に書き写さない（数を作らない）。
- 他社の事例は使わない。理由: 今回の論点は「自社の表の値をどの道で合計に足すか」で、外部の数値の当てはめが無い。

## 9. 維持の仕組み

- 計算は invoice_totals.py の1か所（純粋な関数）。試験 K1〜K5 が式と行の選び方を固定する。
- 値は public.payment_fee_settings が正本。コードに率を書かない（試験の入力にだけ書く）。
- 請求書ごとの写し（payment_fee_snapshot）で、あとから「何で計算したか」を確かめられる。
- 画面の行は既存の金型 TotalsBox だけを使う。i18n は CI の ja/en 一致チェック。
- 守り手: 試験 test_invoice_totals.py・test_invoice_totals_pg.py（CI の必須チェック）と、手数料の値を PO が確かめる設定の画面（payment_fee_settings）。

## 10. 便の分け方

- 1本の PR（移行1本を含むので危険な道。ADR-136 の GO 手順）。移行と画面を分けると、列が無い間に新しいコードが動かないため。
- 実装はクラウドの Sonnet。カードは card-e.md。
