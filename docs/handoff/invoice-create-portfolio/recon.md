# recon: 請求書作成画面をポートフォリオの形に作り直す（2026-11-13）

基準: origin/main `a40dd8b91`（このブランチの起点）。第2版で `c296af3bb` に読み直した（該当行は一致）。本番の数は reader 鍵（ai_ro）で 2026-11-13 10:10〜10:20 JST に読んだ。生出力は /tmp/CC報告ファイル/ の counts_ic.txt・fx_ic.txt・pm_ic.txt・invcols_ic.txt。

## 0. PO の言葉

- 2026-11-13「請求書の作成画面だけどhttps://shingo-portfolio.github.io/invoice-tool/　こういう形式にできる？」
- 2026-11-13「ハードコードはなくしてDBから該当する部分を取得するSSOTを採用、画面の構成はポートフォリオを参照する」
- 2026-11-13 の選択「2. 1と同じだが、関税の決まりも記録の表を新しく作って自動で計算する — 見本に一番近くなります。作る量が増え、時間もかかります。」
  - 「1と同じ」の中身（Opus が出した選択肢1の文面）: 住所は取引先の記録を読むだけ（直すときは取引先の画面へ）。消費税は税率の表から計算。支払方法は記録の表から選ぶ。

## 1. 既存の ADR・仕様書の検索

`git grep -n -i -l -e "関税" -e "duty" origin/main -- docs/adr docs/specs` の結果（2026-11-13）:

| 文書 | 該当 | 今回への効き方 |
|---|---|---|
| docs/specs/quote-invoice/kgi.md:8-22 | Q1〜Q15（PO 承認 2026-07-08） | 今回の KGI はこの Q3・Q4・Q5・Q7・Q8・Q10 に結び付ける |
| docs/specs/quote-invoice/to-be.md:10・:17-22・:42-49 | 人の操作は「選ぶ」と「発行を押す」だけ。米国宛の関税は設定ページの値で自動 | 画面の原則 |
| docs/specs/quote-invoice/kgi.md:13・:28 | Q6（顧客別の関税）は対象外（顧客マスタへ送り状） | 今回も顧客別は作らない |
| docs/adr/ADR-101-sa-quotation-invoice-generation.md:149-159 | §7 関税ポリシー: 既定インコタームズ DAP/DDU/DDP・国別の ON/OFF・式は「キャリア×国×テナント」。Duty 行は課税のときだけ出す。日本の輸出は消費税0%。FedEx 米国の式は「一例」 | 関税の表の形の根拠 |
| docs/adr/ADR-101-sa-quotation-invoice-generation.md:166-173 | 配送先はスナップショット。関税の式をハードコードしない。:171 送料が未連携なら0でなく「未計算」。:173 支払い手数料を合計に含める | 守る決まり |
| docs/adr/ADR-095-sa-ssot-two-backbone-architecture.md:89・:94 | 付録1-4「キャリア別の送料・関税の正確な数式（エビデンス確立）」は未決 | 式の値は AI が決めない。PO が根拠付きで画面から入れる |
| docs/adr/ADR-103-sa-shipping-dispatch-timing.md | 関税の語あり（発送時期の決定） | 今回の計算には関わらない（読んだ範囲で計算式の記述なし） |
| docs/adr/ADR-106-sa-multitenant-policy.md | 関税の語あり（テナント別ポリシー） | テナント別に持つ根拠 |
| ADR-125（FedEx ライブ見積） | D5 暗黙フォールバック禁止 | 送料の一覧の扱い |
| ADR-1061（閲覧者の契約） | 振込先の表・税率の表・発行元の表を作った | 今回はその表を読む |

**第2版で足した事実（コードの検索。第1版は docs だけを検索して見落とした）**: `git grep -n -i -e duty -e incoterm origin/main -- backend/app frontend/src migrations` で、関税の条件の会社の設定が既にある。

- public.tenant_settings.duty_incoterms（DAP・DDU・DDP。既定 DAP）: migrations/20260604_050000_add_tenant_policy_columns.sql:31、backend/app/schemas/tenant_policy.py:20、backend/app/routers/tenant_policy.py:41（権限 tenant.profile.view）、画面 frontend/src/pages/admin/TenantPolicyPage.tsx:258-265。
- 同じ表の default_currency（既定 "JPY"。backend/app/schemas/tenant_policy.py:18）。

## 2. 今の請求書作成画面（frontend/src/pages/invoice-create/InvoiceCreatePage.tsx、449行）

- :77 作り方の切り替え（在庫から／見積から）。既定は見積から。
- :83 通貨の初期値 "USD"。:315-319 通貨の選択肢が JPY・USD・EUR の直書き（**ハードコード**）。
- :170-174 小計・総重量・送料・税・合計を画面で計算。送料と税は人が数字を打つ欄（:172・:173）。
- :191-196 POST /invoices に shipping_fee と tax_amount を画面の数字のまま送る。
- :212・:234 請求先の国が無いとき（422 bill_to_country）取引先の画面へ移るボタン（ADR-1061 便2-2c2a）。
- :224 会社情報のページへのボタン。
- :305 取引先と担当者の選択は CompanyContactSelector。:415 商品は InventorySearchBar。
- 住所の表示・支払方法の選択・送料の比較・関税の行は無い。

## 3. 請求書を作るサーバーの道（backend/app/routers/invoices.py）

- :211-217 見積から作る道。見積の金額をそのまま写す。
- :314-320 直接作る道。:341 小計＝Σ数量×単価、:343 税＝送られた tax_amount（無ければ0）、:344 合計＝小計＋送料＋税。関税は計算しない。
- 発送先と請求先の写しは取引先の既定の住所（delivery・billing）から取る（同ファイルの create_invoice 内 `_fetch_address_snapshot(db, data.company_id, "delivery")`・`"billing"`）。請求先の国が無いと 422。
- backend/app/schemas/invoice.py:40-49 InvoiceCreate: shipping_fee・tax_amount（任意・0以上）・payment_method（文字50字まで）。
- 呼ぶ画面は2つ: InvoiceCreatePage.tsx:191 と frontend/src/features/secretary/SecretaryDraftInvoice.tsx:92（秘書チャット。送料・税は送らない）。

## 4. 本番の請求書の表（tenant_NNN.invoices）

- 列（invcols_ic.txt）: … subtotal, shipping_fee, tax_amount, total_amount, … payment_method, … ship_to_snapshot, bill_to_snapshot, issue_mode, duty_amount, duty_policy_snapshot, fx_rate_snapshot, … payment_fee, … issuer_region。
- duty_amount・duty_policy_snapshot は列があるが、書く処理は無い（invoices.py に duty の書き込みは無く、:836・:880 で読むだけ）。
- 送料の会社・サービス名と、使った税率を残す列は無い。
- 表を作る場所: backend/app/services/tenant.py:861（新しいテナント用）と migrations/005_add_phase2_tenant_tables.sql:110。列を足した前例: migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql:152（全テナントのスキーマを回して ADD COLUMN IF NOT EXISTS）。

### 4-1. 新しいテナントの請求書の表（第2版で足した）

- backend/app/services/tenant.py:861-893 の請求書の表には ship_to_snapshot・bill_to_snapshot・duty_amount・duty_policy_snapshot・fx_rate_snapshot・paypal の4列・payment_fee の9列が無い（tenant.py を grep して0件）。列は migrations/20260604_160000_add_invoice_snapshot_columns.sql だけにある。新しいテナントでは作る道の INSERT（invoices.py:382-387）がこの列を書くので動かない。
- tenant.py の請求書の表（:861）は振込先の表（:1246）より前に作られる。
- 見積の表に shipping_carrier がある（tenant.py:811）。
- 道の一覧（invoices.py）: :211 見積から作る、:314 作る、:432 直す（PATCH）、:474 発行（状態を変えるだけ）。直す道で変えられる列は :120 _UPDATABLE_COLUMNS（payment_method・due_date・exchange_rate_jpy・exchange_rate_usd・notes）。画面から PATCH を呼ぶ所は無い（frontend/src を git grep。詳細画面 InvoiceDetailPage.tsx:296・:300-301 は表示だけ）。

## 5. 読む材料の表と道

| 材料 | 正本の表 | 普通の利用者が読める道 | 本番の行数（tenant_004） |
|---|---|---|---|
| 国 | public.countries | GET /countries | 190（有効） |
| 為替 | public.app_fx_rate_history | GET /fx-rates/{currency}（backend/app/routers/fx_rate_admin.py:62。ログインだけ） | USD だけ 82行（最新 2026-11-12 21:00 UTC） |
| 消費税率 | public.tax_rates（rate_percent・effective_from。全社共通） | **無い**（/super-admin/tax-rates は最高管理者だけ。backend/app/routers/super_admin_tax_rates.py:63） | 0 |
| 振込先 | tenant_NNN.tenant_invoice_payment_methods（region domestic/overseas・method_type bank/wise・display_name・sort_order・is_active）と詳細2表 | **無い**（ADR-1061 design.md:336 に /admin/invoice-payment-methods の予定。main には未実装） | 0 |
| 発行元 | tenant_NNN.tenant_issuer_profiles（country_code を持つ） | get_issuer（backend/app/services/issuer.py） | 0 |
| PayPal | public.tenant_paypal_config | 連携画面 | （数えていない。今回は「行があるか」だけ使う） |
| 決済手数料 | public.payment_fee_settings | GET /payment-fee-settings（権限 suppliers.view。backend/app/routers/payment_fee_settings.py:56） | 7（共用含む） |
| 送料 | FedEx ライブ（認証1行）／静的表 shipping_zones・shipping_rates | POST /shipping/calculate（backend/app/routers/shipping.py:386。権限の確かめは :388。権限 shipping.calculate） | 静的表は 0・0 |
| 関税の決まり | **無い** | 無い | — |
| 請求書 | tenant_NNN.invoices | — | 0（B2B の請求書は本番で一度も作られていない） |
| 見積 | tenant_NNN.quotes | — | 0 |

### 5-1. 為替（第2版で足した）

- 作る道と見積から作る道は外部の値をその場で取る（invoices.py:356・:253 の get_fx_rate。backend/app/services/fx_rate.py:27 の open.er-api.com）。
- 為替の表 app_fx_rate_history は backend/app/tasks/fx_rate_updater.py:42-83 が同じ get_fx_rate("USD") で1日2回（日本時間6時・18時）USD だけを足す。EUR は取っていない。
- 口座番号の見張り: 読み取りの鍵の見え方は列名が account_number などに当たる列を外す（migrations/20261017_130100_create_ai_ro_views.sql:23）。JSONB の中身は外さない。クラウドの読み取りの見え方は列ごとの分類の表（migrations/20261024_100300_create_ai_cloud_views.sql:446 に invoices、:601-608 に振込先の表）。

- ADR-1061 design.md:417 「B2B の支払い方法とこの振込先の表を1つにするかは、海外の請求書の設計で決める。それまでは閲覧者の請求書だけがこの表を読む。」→ 今回の設計で決める。
- ADR-1061 design.md:246 PayPal は振込先の表に入れない（PayPal の正本は public.tenant_paypal_config）。

## 6. 送料の道（backend/app/routers/shipping.py:386-440）

- carrier='fedex' のとき origin_country_code が無いと 422（:410-414）。認証があればライブ見積、無ければ results 空と live_error（:430-436。静的表に落とさない）。
- carrier 無しのときは静的表で計算（:438）。本番は静的表が空なので結果は0件。
- 応答（backend/app/schemas/shipping.py:107-134）: carrier・zone・fee・currency・source・service_type・service_name・transit_days、live_error、rate_precision。
- 画面の部品 frontend/src/components/FedExRateModal.tsx: :112 発送元の国の初期値 "JP"（直書き）、:126-130 /shipping/calculate を呼ぶ、:57 onSelectRate(fee, currency, serviceType)。見積作成画面 frontend/src/pages/quote-create/QuoteCreatePage.tsx:289 が使う。

## 7. 商品の材料（frontend/src/components/InventorySearchBar.tsx:40-62）

- 候補は name・name_en・unit_price・stock_quantity・box_weight_kg・case_weight_kg・inventory_offers（仕入元×状態の在庫）を持つ。
- 単位に応じた重さは frontend/src/pages/quote-create/quoteDraft.ts:33-36 weightForUnit（InvoiceCreatePage.tsx:26 で取り込み）（box→box_weight_kg、case→case_weight_kg）。
- 見本の「カテゴリ」列に当たる値は候補に無い（今回は列を作らない。§design 2）。

## 8. 見本（ポートフォリオ）の画面の形

出典: https://shingo-portfolio.github.io/invoice-tool/（写し: scratchpad の invtool/index.html・js_app.js）

- 区切りは上から「発送先情報」（顧客名・受取人・電話・メール・TAX Number・国・住所1〜3・都市・州・ZIP）→「支払いと合計」（支払い方法・支払い通貨・発送方法・発送メモ／総重量・送料の便ごとの一覧／小計・送料・税・合計）→「商品一覧」（#・カテゴリ・商品名・状態・数量・重量・単価・小計・×、＋商品を追加）→「クリア」「請求書を発行」→ 印刷・PDF の画面。
- 税の行は、日本宛は「消費税（10%）」＝(小計＋送料)×10%（js_app.js:116-117）、米国宛は「関税・手数料（概算）」＝関税15%＋手数料 max(2%, $20)＋MPF（js_app.js:119-124）。どちらでもない国は税の行を出さない（js_app.js:138）。
- 見本の数字（10%・15%・$20・150円換算）はすべて js に直書き。今回は表から読む。

## 9. 法の根拠（消費税）

- 国税庁 タックスアンサー No.6551 輸出取引の免税: https://www.nta.go.jp/taxes/shiraberu/taxanswer/shohi/6551.htm （輸出として行う資産の譲渡は免税）
- 国税庁 タックスアンサー No.6301 課税標準: https://www.nta.go.jp/taxes/shiraberu/taxanswer/shohi/6301.htm （課税標準は受け取る対価の額）
- 送料そのものの扱いを直接書いた国税庁の頁は、2026-11-13 の検索では見つけていない（**未確認**）。見本は送料を含めて計算している（js_app.js:117）。

## 10. 未確認

- FedEx ライブ見積が tenant_004 の認証で本当に料金を返すか（呼んでいない。本番の外部 API を試しに呼ばないため）。
- 関税の値そのもの（率・手数料・下限・上限）。ADR-095 付録1-4 で未決。AI は入れない。
