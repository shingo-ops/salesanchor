# design: 請求書作成画面をポートフォリオの形に作り直す（住所・税・関税・支払方法を記録の表から）

状態: 設計案 第3版（Opus 作成 2026-11-13）。第1版はクラウドの設計審査で REVISE（止める2・直すべき11・覚え書き6）、第2版は REVISE（止める0・直すべき9・覚え書き5）。本版は両方を反映した（§11・§12 に対応表）。再審査前。PO 承認前。
根拠: 同じ場所の recon.md（§番号で指す）。基準 origin/main `c296af3bb`。対象 ADR: ADR-101（§7 関税・実装上の注意）、ADR-095 付録1-4、ADR-106（テナント別ポリシー）、ADR-125 D5、ADR-1061（振込先・税率・発行元の表）、ADR-027（i18n）、ADR-144（UI の金型）、ADR-072（commit 後の reset）、ADR-135/136（危険な PR）。あるべき姿: docs/specs/quote-invoice/（KGI Q1〜Q15）。

## 1. 目的（PO の言葉から）

- 請求書の作成画面を、PO のポートフォリオ（https://shingo-portfolio.github.io/invoice-tool/）と同じ並びにする（recon §0・§8）。
- 画面に数字や選択肢を直書きしない。住所・税率・関税の決まり・支払方法・通貨は記録の表から読む（PO 2026-11-13「ハードコードはなくしてDBから該当する部分を取得するSSOTを採用」）。
- 関税の決まりは新しい表に持ち、自動で計算する（PO の選択「2」）。
- 奥の目的: 海外のお客さんへの請求書を、人が金額を打たずに、選ぶだけで正しく出せるようにする（quote-invoice/to-be.md:10）。

## 2. 対象と対象外

対象:
- 関税の額の表2つ（新）と、その設定画面。
- 請求書の表に列を足す（§3-5）。tenant.py の請求書の表に、移行だけで足してあった12列と、明細の表2つの hs_code も足す（recon §4-1）。
- 作成画面の材料を返す道・試算の道（新）、作る道・見積から作る道・発行する道・直す道（直す）。
- 合計の計算を1つの関数（invoice_totals）にまとめる。為替は表（app_fx_rate_history）だけにする。為替を見せる道（GET /fx-rate/{currency}。今は見積の詳細画面だけが呼ぶ）も表から読む形に直す。
- 請求書作成画面の並びの作り直し。秘書チャットの請求書の通貨の選択肢も同じ材料から読む。
- 請求書の詳細画面に、下書きのあいだだけ支払方法を選ぶ欄を足す（見積から作った請求書と秘書チャットで作った請求書に支払方法を付ける道）。
- PDF に支払方法（振込先）と消費税の率を出す。

対象外:
- 見積の作成画面（QuoteCreatePage）。見積の金額の計算は今のまま。送料を選んでも送料の会社と通貨を保存しない今の作り（QuoteCreatePage.tsx:293 は額だけを受け取る）も変えない。見積の画面の FedEx の発送元の初期値 "JP"（FedExRateModal.tsx:112・:130）も今のまま（§3-4 の FedEx の部品の扱い・§6）。
- 顧客別の関税（quote-invoice/kgi.md:13・:28 で対象外と決まっている）。
- 見本の「カテゴリ」列（商品の候補にその値が無い。recon §7）。
- PDF の見た目のそれ以外の変更。
- 振込先を登録する画面（ADR-1061 の残りの便で作る。recon §5）。
- 為替の表に EUR などを足すこと（今は USD だけを1日2回取っている。recon §5-1）。通貨を足すのは別のテーマ。
- 決済手数料を合計に入れること。ADR-101:173 は「合計計算に必ず含める」と書くが、payment_fee_settings の値と支払方法の結び付けが決まっていない。PO の判断で先送りにするかを §7 の2で聞く（ADR と食い違うまま黙って進めない）。
- 関税・税率・振込先の値を入れること。AI は値を入れない（ADR-095 付録1-4。PO が根拠付きで画面から入れる）。

## 3. 変更前と変更後

### 3-1. 画面の並び（見本と同じ順）

| 順 | 見本の区切り | 変更後の中身 | 値の出どころ |
|---|---|---|---|
| 0 | （無し） | 作り方の切り替え（在庫から／見積から）は残す | 今のまま（recon §2 :77） |
| 1 | 発送先情報 | 取引先と担当者を選ぶ（CompanyContactSelector）。選ぶと発送先と請求先を**読むだけで**出す。直す欄は無い。「取引先の画面で直す」ボタン（/crm/companies/{id}） | 住所の項目は作る道が写しに使う関数 _fetch_address_snapshot の返す項目だけ（invoices.py:62-104。会社名・電話・国・住所）。宛名とメールは選んだ担当者（contacts）の名前とメール |
| 2 | 支払いと合計 | 支払方法（選ぶ）・通貨（選ぶ。外貨は「1 USD = N 円（取得日時）」を添える）・備考（今の notes）／総重量・送料（会社ごとの一覧から選ぶ。または「送料を請求しない」を選ぶ）／小計・送料・消費税（率つき）または関税（中身ごと）・合計 | 振込先の表・PayPal 設定・為替の表・送料の道・税率の表・関税の表 |
| 3 | 商品一覧 | 商品名・状態・数量・重量・単価・小計・削除。＋商品を追加（InventorySearchBar） | 今のまま |
| 4 | クリア・発行 | 「クリア」（入力を空にする）と「作成」 | — |
| 5 | 印刷・PDF | 作成後は今の請求書の詳細画面へ移る（PDF のボタンがある。frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:151・:222） | — |

- 合計の欄は入力の途中もずっと見える（Q8）。
- 部品は金型だけを使う（ADR-144）。選ぶ欄は Select、ボタンは Button。生の select・input・色の直値は使わない。文言はすべて t()、ja.json と en.json に同じキー（ADR-027）。どの金型をどの行で使うかは実装カードで file:line を付ける。

### 3-2. 選択肢と数字の出どころ（直書きを0にする）

| 項目 | 変更前 | 変更後 |
|---|---|---|
| 通貨の選択肢 | JPY・USD・EUR の直書き（InvoiceCreatePage.tsx:315-319。秘書チャット SecretaryDraftInvoice.tsx:190 も同じ直書き） | JPY と、為替の表（app_fx_rate_history）に行がある通貨。JPY を必ず入れる理由は、表の値が「1外貨＝何円」（列 rate_jpy）で円を基準に作られているため。今は JPY・USD の2つになる（EUR は表に無いので出ない。§2 対象外） |
| 通貨の初期値 | "USD" の直書き（:83） | 会社の設定 tenant_settings.default_currency（tenant_policy.py:18。ADR-106）。選択肢に無い値なら初期値なし。見積から作るときは見積の通貨（今の :144 と同じ） |
| 支払方法 | 選ぶ欄なし | 振込先の表（tenant_invoice_payment_methods）の有効な行のうち、発行元の地域（請求先の国から decide_issuer_region で決まる。issuer.py:20-27）と同じ行、sort_order 順。Wise の行は wise_currency が請求書の通貨と同じ行だけ（材料の道が全行を wise_currency つきで返し、画面が通貨を変えるたびに絞る。サーバーも作る道・直す道で同じ条件を確かめる）。PayPal は public.tenant_paypal_config にこのテナントの行があるときだけ（PayPal の正本はそこだけ。ADR-1061 design.md:246） |
| 送料 | 人が打つ欄（:172） | POST /shipping/calculate の結果から選ぶ。FedEx の発送元の国は発行元の表の country_code（その地域の行）。取れないときは「未計算」と出し、そのままでは作成できない。人が「送料を請求しない」を選んだときだけ送料0で作れる（§3-4 の送料の規則） |
| 消費税 | 人が打つ欄（:173） | 税率の表（public.tax_rates）で計算（§3-4） |
| 関税 | 無し | 会社の関税の条件（tenant_settings.duty_incoterms）と関税の額の表（§3-3）で計算 |
| 合計 | 画面で足し算（:170-174） | 試算の道（§3-4）がサーバーで計算した値を出す。画面は計算しない |

### 3-3. 関税

**条件の正本は今ある会社の設定1つだけ**: tenant_settings.duty_incoterms（DAP・DDU・DDP。既定 DAP。migrations/20260604_050000_add_tenant_policy_columns.sql:31・schemas/tenant_policy.py:20・画面 frontend/src/pages/admin/TenantPolicyPage.tsx:258-265）。新しい表には条件の列を持たない（第1版の incoterm 列は取りやめ。条件の正本が2つになるため）。

**新しい表は「DDP のときにいくら請求するか」だけを持つ**（会社ごとのスキーマ）。置き場と作り方は前例 migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql と同じ（全テナントのスキーマを回す・RLS は tenant_id で分ける・ポリシー名は `<表名>_tenant_isolation`・新しいテナント用に tenant.py にも同じ表を足す）。

**tenant_duty_rules**（どの国・どの送料の会社のときの額か）
- id、tenant_id（NOT NULL）
- destination_country_code（CHAR(2) NOT NULL。届け先の国）
- carrier（VARCHAR(50) NULL。NULL は「どの送料の会社でも」。値は /shipping/calculate の結果の carrier と同じ文字）
- label（TEXT NOT NULL。請求書の関税の行に出す名前）
- effective_from（DATE NOT NULL）、effective_to（DATE NULL）
- source_url（TEXT NOT NULL。値の根拠。空は不可。ADR-095 付録1-4「エビデンス確立」）
- note、is_active、created_at、updated_at
- 同じ国・同じ送料の会社で有効期間が重なる行は作れない（書く道で 409 duty_rule_overlap）。

**tenant_duty_rule_components**（関税の中身。1つの決まりに複数）
- id、rule_id（外部キー。決まりを消すと一緒に消える）、tenant_id（NOT NULL）
- sort_order（計算の順）
- label（TEXT NOT NULL。例: 関税・DDP 手数料・MPF）
- base（VARCHAR(30) NOT NULL。CHECK で `subtotal`（小計）・`subtotal_shipping`（小計＋送料）・`subtotal_shipping_prior`（小計＋送料＋この行より前の中身の合計）の3つ）
- rate_pct（NUMERIC(8,4) NOT NULL・0以上）
- min_amount・max_amount（NUMERIC(14,2) NULL）、amount_currency（CHAR(3)。min か max があるときは必須。CHECK）

計算（invoice_totals の中だけ）:
1. 届け先の国＝発送先の写しの国。発送先の住所が無いときは請求先の国。
2. 会社の条件が DAP・DDU のときは関税の行を出さない。duty_amount は NULL（0 ではない。PDF は NULL のとき Duty 行を描かない。invoice_renderer.py:358）。理由: 買い手が着いてから払う条件（ADR-101:157「Duty 行は課税判定時のみ表示」）。
3. DDP のとき、その国・その日に有効な行を探す。送料の会社が一致する行を先に、無ければ carrier が NULL の行。行が無ければ関税の行を出さない（duty_amount は NULL。国別の ON/OFF は「行があるか」で表す。ADR-101:149-159）。
4. 行があれば中身を sort_order 順に、金額＝基準×rate_pct/100。min があれば下限、max があれば上限で挟む。min・max の通貨が請求書の通貨と違うときは為替の表で換算する（§3-4 の為替の規則）。
5. 中身の合計を duty_amount に入れる。条件・使った行・中身・換算に使った値を duty_policy_snapshot に写す（列は今ある。recon §4）。
6. DDP で、その国に有効な行が「送料の会社つきの行だけ」あり、送料の会社が選ばれていない（「送料を請求しない」を含む）ときは、関税を決められない。試算は関税を「未計算」で返し、作成と発行は 409 duty_needs_carrier で止める（少なく請求するのを防ぐ）。

### 3-4. 計算の規則とサーバーの道

**invoice_totals（backend/app/services/invoice_totals.py、新）が唯一の計算の場所。** 試算・作成・見積から作成・発行がすべてこれを呼ぶ。

- 合計＝小計＋送料＋消費税＋関税（関税が NULL のときは0として足す）。tax_amount と duty_amount は別の列に入れる。
- 端数: 消費税と関税の中身の1つずつを、通貨の最小単位（円は1円、ドルは1セント）で処理する。処理の仕方は §7 の1で PO が決める。決まるまで便 C を始めない。
- 基準日: 税率と関税の行は「基準日」に有効な行を使う。作成・試算では今日（日本時間）、発行では発行の日（日本時間）。発行の道（invoices.py:474-501。今は状態を変えるだけ）で invoice_totals を発行日で計算し直し、税・関税・合計・写しを上書きしてから issued にする。理由: 税率の表の決まり「請求書は発行日に有効な行の率を写す」（migrations/20261112_150000_create_viewer_contract_public_tables.sql:166）。
- 発行で計算し直すものは次のすべて。どれも発行の時点の同じ為替の行の組（通貨ごとに最新の1行）を使う: ①税率の行 ②関税の行と中身（min・max の換算を含む） ③送料の換算（shipping_snapshot に残した元の額と元の通貨から、発行時の率で換算し直す。元の通貨が請求書の通貨と同じなら額は変わらない） ④exchange_rate_jpy・exchange_rate_usd・amount_jpy・amount_usd・fx_rate_snapshot ⑤合計。明細の単価と数量・選んだ送料の会社と元の額・支払方法は変えない。
- 消費税: 届け先の国（§3-3 の1と同じ）が JP のときだけ。基準は小計＋送料（見本 js_app.js:117・国税庁 No.6301）。外国宛はかけない（輸出免税。国税庁 No.6551）。基準日に有効な行が無い日本宛は、試算で「未計算」、作成・発行は 409 tax_rate。使った率を tax_rate_percent に残す。
- 消費税と支払方法の決まり方は別: 消費税は届け先の国、発行元の地域と支払方法は請求先の国で決まる。例: 請求先が日本・発送先が米国 → 国内の振込先を選び、消費税なし、DDP なら関税あり。
- 為替の規則（為替の正本は app_fx_rate_history だけ）: 通貨ごとに fetched_at が一番新しい行を使う（作成と発行の時点で）。fx_rate_snapshot・exchange_rate_jpy・amount_jpy はこの行から作る。作る道の外部のライブ取得（invoices.py:253・:356 の get_fx_rate）は外す。表は今 fx_rate_updater（backend/app/tasks/fx_rate_updater.py:42-83）が同じ外部の値を1日2回入れている。換算が要るのに行が無い通貨は 409 fx_rate。2つの外貨の間は円を通して換算する。
- 為替の列の作り方（今の _calc_currency_amounts invoices.py:135-153 と同じ意味を保つ。値の出どころだけを表に変える）: exchange_rate_jpy＝請求書の通貨の表の rate_jpy（JPY の請求書は NULL）。exchange_rate_usd＝USD の表の rate_jpy（1ドル＝何円。USD の請求書は NULL）。amount_jpy＝合計×exchange_rate_jpy（JPY は合計そのまま）。amount_usd＝amount_jpy÷exchange_rate_usd を1セントに丸める（USD は合計そのまま）。USD の行が無いときは amount_usd を NULL にし、止めない（請求の額は変わらないため）。
- 為替を見せる道 GET /fx-rate/{currency}（invoices.py:1024-1049。今は get_fx_rate で外部から取る）も、表の最新行を同じ形（currency・rate・fetched_at）で返すように直す。呼ぶのは見積の詳細画面だけ（QuoteDetailPage.tsx:104。2026-11-13 git grep）。表に行が無ければ今と同じ 503。理由: 見積の詳細画面で見せた率と、同じ画面から見積を請求書にしたとき（:88）に保存する率を同じにする。
- 送料の規則: 送料は次のどちらかでないと作成できない。（ア）/shipping/calculate の結果の1つを選んだ（carrier・service_type・fee・currency を受ける。送料の通貨が請求書の通貨と違えば為替の規則で換算し、元の額と率を duty_policy_snapshot と同じ形で shipping の写しに残す）。（イ）人が「送料を請求しない」を選んだ（送料0・carrier は NULL）。どちらでもないと 422 shipping_required。理由: ADR-101:171「未連携なら0でなく未計算」。黙って0にしない。日本国内宛は今は FedEx 国際しか取れず静的表も0行なので、（イ）しか選べない（§7 の3）。送料の額は画面が選んだ値を受ける（見積は時間で変わるため取り直さない。今の道も同じ）。
- 見積から作るときの送料の規則: 見積の画面は送料の額だけを保存し、送料の会社と通貨を保存しない（QuoteCreatePage.tsx:293）。そこで、見積の shipping_fee が 0 より大きいときは（ア）として扱い、元の額＝見積の送料、元の通貨＝見積の通貨（請求書の通貨も見積の通貨なので換算しない）、送料の会社＝quotes.shipping_carrier（NULL のことがある）、source＝'quote' を shipping_snapshot に写す。shipping_fee が 0 または NULL のときは（イ）「送料を請求しない」として扱う。見積はすでに人が送料を決めた書類なので、見積から作る道では 422 shipping_required を返さない。送料の会社が NULL で、届け先の国の DDP の行が会社つきだけのときは、関税の規則（§3-3 の6）のとおり 409 duty_needs_carrier で止まる（§6）。
- FedEx の部品（frontend/src/components/FedExRateModal.tsx）の発送元: 任意の受け取り口 originCountryCode を足す。請求書作成画面は draft-context の発送元の国を渡し、部品はその値を使って発送元の欄を直せない形にする。渡された値が null のときは見積を取らず「未計算」と会社情報のページへの案内を出す。受け取り口を渡さない呼び出し（見積の作成画面 QuoteCreatePage.tsx:289）は今のまま（:112 の初期値 "JP" と :130 の `|| "JP"` を残す。見積の画面は §2 で対象外）。

| 道 | 中身 | 権限 |
|---|---|---|
| GET /invoices/draft-context?company_id= （新） | 発送先・請求先（_fetch_address_snapshot と同じ）、担当者の名前とメール、発行元の地域、発送元の国（発行元の表の country_code。無ければ null）、通貨の一覧と最新の為替（通貨・値・取得日時）、通貨の初期値（default_currency）、支払方法の一覧（id・display_name・method_type・wise_currency（Wise の行だけ。ほかは null）。発行元の地域で絞った全行を返し、通貨での絞りは画面が行う。PayPal は method_type 'paypal'・id null）、今日有効な税率（無ければ null）、会社の関税の条件 | invoices.create（今の POST /invoices と同じ） |
| POST /invoices/preview （新・書かない） | 受ける: company_id・currency・items（数量・単価）・shipping（§3-4 の（ア）か（イ）。任意）。返す: 小計・送料・消費税（率と額）・関税（ラベル・中身ごとの額）・合計、「未計算」の印と理由のキー | 同上 |
| POST /invoices （直す） | 受ける値に payment_method_ref（method_type と id）と shipping を足す。tax_amount・shipping_fee・payment_method（文字）・exchange_rate_jpy・exchange_rate_usd は受けない（InvoiceCreate からこの5つの欄を消し（今は schemas/invoice.py:45-49 にある）、extra="forbid" にして、送られたら 422）。計算は invoice_totals。payment_method_ref は draft-context と同じ選び方の中にあるか確かめ、無ければ 422 payment_method。支払方法は任意（秘書チャットは送らない）。作成画面は必須にする | 同上 |
| POST /invoices/from-quote/{id} （直す） | 明細は見積から写す。送料は上の「見積から作るときの送料の規則」で写す（送料の会社は quotes.shipping_carrier。tenant.py:811）。消費税・関税・合計は invoice_totals で計算する（見積の tax_amount・total_amount は写さない）。見積の送料の会社が空で、DDP の行が会社つきだけなら 409 duty_needs_carrier。支払方法はここでは付けない（体は今と同じ空。付けるのは詳細画面の下書きの欄で、下の PATCH を通る） | 今のまま（invoices.create） |
| POST /invoices/{id}/issue （直す） | §3-4 の基準日の規則で計算し直してから issued にする | 今のまま |
| PATCH /invoices/{id} （直す） | _UPDATABLE_COLUMNS（invoices.py:120）から payment_method・exchange_rate_jpy・exchange_rate_usd を外す。支払方法を直すときは payment_method_ref で受け、作る道と同じ検査と写しの作り直しをする。支払方法を直せるのは下書き（draft）のあいだだけ（発行後に案内の口座が変わらないように。それ以外は 409 invoice_not_draft）。為替は直せない（正本は表）。今は画面に PATCH を呼ぶ所は無い（2026-11-13 git grep。詳細画面は表示だけ InvoiceDetailPage.tsx:296・:300-301）。便 D で詳細画面に下書きのときだけ支払方法を選ぶ欄を足し、この道を呼ぶ（選択肢は draft-context と同じ） | 今のまま（invoices.update） |

- 支払方法を受けたら、作る道は payment_method（文字）に display_name（PayPal は 'paypal'。invoices.py:672）、payment_method_id に行の id、写しの列に詳細を入れる（§3-5）。
- 2つの支払方法の列の意味を分ける: payment_method_id・payment_method_snapshot・payment_account_number は「請求書で案内した支払い先」。payment_method（文字）は今のまま「実際に払われた方法」も兼ね、PayPal の入金確認で 'paypal' に上書きされる（invoices.py:766）。案内の列は入金確認で変えない。PDF の支払方法の区切りは案内の列から描く。
- 秘書チャット（SecretaryDraftInvoice.tsx:92）は同じ POST /invoices を通る。tax_amount・shipping を送っていないので、shipping が無いと 422 shipping_required になる。便 D で秘書チャットにも送料の選択（少なくとも「送料を請求しない」）を足し、同じ便で通貨の選択肢を draft-context から読む。
- 新しい道は realtime/topics.py の請求書の道（:228-235）に同じ扱いで登録する（test_realtime_topics.py が落ちないように）。
- 書いた後は reset_tenant_context()（ADR-072）。

### 3-5. 請求書の表に足す列（tenant_NNN.invoices。全テナント）

- payment_method_id（INTEGER NULL。外部キーは張らない。理由: 請求書には選んだ時点の写しを残すので、振込先の行が後で消されても請求書は困らない。外部キーで消すことを止める必要が無い）
- payment_method_snapshot（JSONB NULL。選んだ時点の振込先の項目と行の id。銀行の口座番号と Wise の IBAN は入れない。Wise の wise_email は入れる（Wise はメールで送金してもらう運用で必須の項目。docs/handoff/viewer-contract-stage/design.md:260））
- payment_account_number（TEXT NULL。銀行の行は account_number、Wise の行は iban（無ければ NULL）。Wise の表には口座番号の列は無い（tenant.py:1283-1301）。列名に account_number を含めるのは、読み取りの鍵の見張りが名前で自動で外すため（migrations/20261017_130100_create_ai_ro_views.sql:23 の deny）
- tax_rate_percent（NUMERIC(5,2) NULL。使った税率）
- shipping_carrier（VARCHAR(50) NULL）、shipping_service（VARCHAR(100) NULL）、shipping_snapshot（JSONB NULL。送料の元の額・元の通貨・換算の率・source（'calculate'・'quote'・'none'）・「送料を請求しない」の印）

backend/app/services/tenant.py（新しいテナント用）には次を足す。どれも本番の会社のスキーマには移行で入っているが、tenant.py に無い（2026-11-13 origin/main c296af3bb で tenant.py を列名ごとに grep して0件。issue_mode の1件は tenant_settings の行 :1887）:
- 請求書の表（:861-893）に12列: ship_to_snapshot・bill_to_snapshot・issue_mode・duty_amount・duty_policy_snapshot・fx_rate_snapshot（migrations/20260604_160000_add_invoice_snapshot_columns.sql:30-35）、paypal_order_id・paypal_approval_url・payment_fee（migrations/20260611_020000_add_invoice_paypal_columns.sql:26-28）、paypal_invoicer_view_url・paypal_copy_pdf・paypal_copy_pdf_at（migrations/20260612_131520_add_invoice_copypdf.sql:32-34）。型は移行と同じ。
- 見積の明細（quote_items :844-857）と請求書の明細（invoice_items :898-）に hs_code VARCHAR(20)（migrations/20260604_160000_add_invoice_snapshot_columns.sql:74・:86）。作る道と見積から作る道が読む（invoices.py:127・:287）。
- 上の新しい7列と関税の表2つ。
今はこの列が無いので、新しいテナントでは請求書の一覧・詳細（_INVOICE_COLUMNS invoices.py:105-118）・作る道・見積から作る道が動かない（recon §4-1）。

クラウドの読み取りの見え方（便 A に入れる）: 分類表は migrations/20261024_100300_create_ai_cloud_views.sql が正本で、毎回全行を入れ直す（同ファイル :3）。分類の無い文字・JSONB の列があると試験 T10（backend/tests/ops/test_ai_cloud_views.py:5）が落ちる。そこで同じファイルと元の表（docs/handoff/cloud-case-ai/stage1-column-class.tsv）に次の行を足す。数・日付の型の列（payment_method_id・tax_rate_percent・rate_pct・min_amount・max_amount・sort_order・rule_id・effective_from・effective_to・is_active）は型で通るので行を足さない（名前の見張りに当たる列は無い）。
| 表 | 列 | 分類 | 理由 |
|---|---|---|---|
| invoices | payment_method_snapshot・payment_account_number・shipping_snapshot | mask | 振込先・口座・送料の写し |
| invoices | shipping_carrier・shipping_service | mask | 値の決まりが無く自由に入る列（初期は最小） |
| tenant_duty_rules | destination_country_code・carrier・label・source_url・note | mask | 値の決まりが無く自由に入る列（初期は最小） |
| tenant_duty_rule_components | label・amount_currency | mask | 同上 |
| tenant_duty_rule_components | base | allow | CHECK で3つの値に限られる |
ファイル先頭の行数の注記（:3 の「1151 行」）も足した数に直す。

### 3-6. 関税の額の設定画面

- 置き場: 管理センターの「ビジネス設定」の中に「関税の額」を1つ足す（会社情報のページと同じ並び。ADR-1061 design.md:242 の入口の作り）。新しい大きなメニューは作らない。
- 画面の上に今の会社の条件（DAP・DDU・DDP）を読むだけで出し、「条件を変えるのは会社の決まりのページ」と案内する（TenantPolicyPage）。DAP・DDU のときは「今は関税を請求しません」と出す。
- 一覧（国・送料の会社・有効期間・根拠）と、足す・直す・消す。中身の行は足せる。根拠の URL は必須。
- 権限: 会社情報のページと同じ tenant.profile.view／edit。
- 足す・直す・消すたびに会社ごとの audit_logs に1行（ADR-1061 design.md:269 と同じ record_audit_log）。
- 道: GET・POST・PUT・DELETE /admin/duty-rules（会社ごとのスキーマ。commit 後に reset。realtime/topics.py に登録）。

### 3-7. PDF（invoice_renderer.py）

- 合計の区切り（:340-360 付近）の Tax 行に率を添える（tax_rate_percent があるとき）。Duty 行は今のまま duty_amount が NULL でないときだけ。
- 合計の下に支払方法の区切りを足す: payment_method_snapshot と payment_account_number から、銀行は銀行名・支店・種別・口座番号・名義、Wise は名義・送金先のメール（wise_email）・銀行名・SWIFT・IBAN（あるときだけ）。PayPal は「PayPal」の1行。支払方法が無い請求書はこの区切りを描かない。
- 見積の PDF（:583）は変えない。

## 4. 便の順番

| 便 | 中身 | 利用者に見える変化 | 危険 |
|---|---|---|---|
| A | 移行: 関税の表2つ・請求書の7列・tenant.py の同じ形と欠けた12列・明細2表の hs_code・クラウドの読み取りの見え方の表への分類（§3-5 の表。SQL と元の表の両方） | 無し | **危険**（migrations/。ADR-135/136 の GO とバックアップ確認） |
| B | 関税の額の道と設定画面 | 管理センターに「関税の額」 | 普通 |
| C | invoice_totals・draft-context・preview・作る／見積から作る／発行／直す道・為替を表だけに（GET /fx-rate も表の最新行を返す）・PDF の支払方法と率 | PDF に支払方法が出る。作る道が新しい形になる | 普通（**C と D は同じ PR で出す**。今の作成画面は tax_amount を送るので、C だけ先に出すと作成画面が 422 になる） |
| D | 作成画面の作り直し・FedExRateModal に任意の originCountryCode を足し請求書の画面から渡す（渡さない見積の画面は今のまま）・秘書チャットの送料の選択と通貨の選択肢・詳細画面の下書きのときだけの支払方法の選択 | 作成画面が見本の並びになる。下書きの詳細画面で支払方法を選び直せる | 普通 |

- 1便1目的。C と D だけは上の理由で1つの PR にする（実装は C→D の順に2つのコミットで分ける）。
- **便 C・D を本番に出す前の条件**: 本番の税率の表に1行以上あること（reader 鍵で数える）。今は0行（recon §5）。0行のまま出すと、日本宛の請求書が秘書チャットも含めて作れなくなる（409 tax_rate）。PO が最高管理者の税率の画面で 10%・2019-10-01 を入れる（ADR-1061 の予定と同じ）。
- 便 A の後、PO が行うこと: 関税の額を根拠付きで入れる（便 B の後。会社の条件を DDP にしたときだけ効く）。振込先を入れる（ADR-1061 の登録画面ができた後）。

## 5. 代替案と選んだ理由

- 画面で合計を計算する（今の形）→ 取りやめ。関税の式を画面とサーバーの2か所に持つことになる。画面の値をそのまま保存すると、誤った額が通る。
- 新しい表の各行に DAP・DDU・DDP を持つ（第1版）→ 取りやめ。会社の設定 duty_incoterms が既に正本で、画面もある。2か所に持つと食い違う。
- 為替をライブ取得のまま残す → 取りやめ。画面に出す率（表）と保存する率（ライブ）が別になり、画面の額と PDF の額がずれる。
- 関税の式を「率1つ」だけにする → 取りやめ。ADR-101:159 の FedEx の例は率・下限つき手数料・上下限つき MPF の3つの形を持つ。中身の行（率・下限・上限・基準）なら3つとも表せる。
- 関税の式を計算式の文字で持つ → 取りやめ。文字の式を実行する仕組みは誤りや危険が入りやすい。決まった形（基準×率を下限と上限で挟む）なら検査できる。
- 消費税をテナントごとの表に持つ → 取りやめ。税率は国の決まりで全社同じ。ADR-1061 で public.tax_rates を作ってある。
- 支払方法に B2B 専用の表を作る → 取りやめ。振込先の表がすでにある。2か所に持つと SSOT が崩れる（ADR-1061 design.md:417 の宿題をこの形で閉じる）。
- 振込先の写しに口座番号も入れる → 取りやめ。JSONB の中は読み取りの鍵の見張り（列名で外す）が効かず、口座番号が読める。口座番号だけ名前で外れる列に分ける。
- 住所を作成画面で直せるようにする → 取りやめ。PO が選択肢1・2で「取引先の記録を読むだけ」を選んだ。

## 6. リスクと対処

| リスク | 対処 |
|---|---|
| 関税の値が誤っていて請求額がずれる | 根拠の URL を必須にする。試算で中身ごとの額を出す。使った条件と値を duty_policy_snapshot に残す |
| 税率の表が0行のまま便 C・D が出て、日本宛の請求書が作れなくなる | §4 の出す前の条件（reader 鍵で1行以上を確かめてからマージ） |
| 送料が取れない宛先（日本国内など）で作れない | 「送料を請求しない」を選べば作れる。黙って0にはしない |
| 秘書チャットで作るとき送料が無く 422 になる | 同じ PR の便 D で秘書チャットに送料の選択を足す |
| EUR が選べなくなる | 本番の請求書と見積は0件（recon §5）。EUR の見積から作ると 409 fx_rate で理由が出る。為替の表に通貨を足すのは別のテーマ |
| 発行の時に税率や関税の行が変わっていて額が変わる | 発行日の行で計算し直すのが税率の表の決まり（:166）。詳細画面と PDF は発行後の値を出す |
| 振込先が0件のあいだ作成画面で支払方法を選べない | 選択肢が0件のときは会社情報のページへの案内を出す。PayPal 連携があれば PayPal を選べる |
| 発行元の表が0行のあいだ FedEx の見積が取れない | 送料は「未計算」で出し、会社情報のページへの案内を出す。暗黙に "JP" を使わない（ADR-125 D5） |
| 作成画面を開ける人が送料の道の権限（shipping.calculate。shipping.py:388）を持たない | 便 D の実装カードで、invoices.create を持つ役割が shipping.calculate も持つかを本番の役割の表で数える。持たない役割があれば止めて PO へ |
| 口座番号が AI の読み取りに出る | 口座番号は名前で自動で外れる列に分ける（§3-5）。便 A の後に reader 鍵で列が見えないことを確かめる。クラウドの見え方は mask に分類する（§3-5 の表） |
| 運送会社が NULL の見積（QuoteCreatePage.tsx:293 は送料の額だけ保存）から作り、関税の行が運送会社つきしか無い | 409 duty_needs_carrier で理由が出る。運送会社を問わない行（carrier NULL）を入れれば作れる。見積の画面で運送会社を保存するのは対象外 |
| 見積の画面の発送元は今の "JP" のまま残る（FedExRateModal.tsx:112・:130） | 請求書の画面だけ渡す値に替える。見積の画面の直しは別のテーマ（§2 対象外） |
| PayPal で支払われると payment_method が 'paypal' に上書きされ（invoices.py:766）、案内の列と違って見える | 列の意味を分ける（§3-4）。payment_method は実際に使われた方法、案内の3列は請求書に書いた振込先。PDF は案内の列を描く。上書きしても案内の列は変えない |
| 為替の表に USD の行が無い | amount_usd を NULL にして止めない（§3-4）。JPY 以外の通貨で行が無いときは 409 fx_rate |

## 7. 未決（PO に決めてもらうこと）

1. 端数の処理（消費税と関税の中身の1つずつ）: 切り捨て・四捨五入・切り上げのどれにするか。
2. 決済手数料を合計に入れること（ADR-101:173）を、このテーマでは行わず別のテーマにしてよいか。
3. 日本国内宛は送料が自動で取れない（FedEx 国際だけのため）。当面は「送料を請求しない」だけで作ることでよいか。

## 8. 受入条件

| 基準 | 検証方法 |
|---|---|
| K1 作成画面に住所を打つ欄が0個 | 画面の試験: 発送先の区切り（data-testid="invoice-ship-to"）の中の input・textarea を数えて0。取引先を選ぶと住所の文字と担当者の名前・メールが出ること |
| K2 作成画面と秘書チャットの通貨・支払方法の選択肢は材料の道の値だけ | 画面の試験: draft-context の応答の通貨と支払方法を変えると、選択肢がその通りに変わる（直書きの配列が残ると落ちる） |
| K3 支払方法は表の行だけ（Q7） | サーバーの試験: 表に無い id を作る道と PATCH に送ると 422 payment_method。Wise は通貨が違う行を送ると 422 payment_method。画面の試験: 通貨を USD→JPY に変えると wise_currency が USD の Wise の行が選択肢から消え、選んでいた値が外れる |
| K4 送料が取れないとき 0 でなく「未計算」、選ばないと作れない（ADR-101:171・Q3） | 画面の試験: /shipping/calculate が空のとき送料の欄が「未計算」。サーバーの試験: shipping 無しの作成が 422 shipping_required、「送料を請求しない」なら送料0で作れる |
| K5 送料の会社の一覧が出て選べる（Q4。今あるのは FedEx だけ） | 画面の試験: 結果の会社が一覧に出て、選ぶと送料と合計が変わる。本番で FedEx のライブ見積が出るかは PO の目視（§9） |
| K6 関税の値を直すと請求書の額が変わる（Q5 = 1） | サーバーの試験: 条件 DDP で中身の率を変えると preview と作成の duty_amount が変わる。DAP・DDU・行が無いときは duty_amount が NULL で関税の行が出ない |
| K7 消費税は日本宛だけ・税率の表の値で | サーバーの試験: JP 宛 10% の行で (小計＋送料)×10%（§7 の1の端数）、US 宛は0で行が出ない。税率の行が無い JP 宛は 409 tax_rate |
| K8 小計・送料・税または関税・合計が入力の間ずっと見える（Q8） | 画面の試験: 明細を足す前・後で合計の区切りが出ている |
| K9 画面に出た額と保存された額が同じ | サーバーの試験: preview の結果と、同じ材料で作った請求書の各額が一致。合計＝小計＋送料＋消費税＋関税 |
| K10 見本と同じ並び | 画面の試験: 区切りの見出しが 発送先 → 支払いと合計 → 商品一覧 → クリア・作成 の順 |
| K11 金型・トークン・i18n を守る | npm run check:all が通る。ja.json と en.json のキー数が同じ。`ui-allow` の新しい例外が0件 |
| K12 作成画面から PDF まで（Q10） | 作成後に詳細画面へ移り PDF のボタンがある。サーバーの試験: 振込先を選んだ請求書の PDF の文字に口座番号と銀行名が出る。消費税の行に率が出る |
| K13 為替は表だけ | サーバーの試験: 作る道・見積から作る道・発行が外部の取得（get_fx_rate）を呼ばない（呼ぶと失敗する差し替えで確かめる）。fx_rate_snapshot の率・exchange_rate_jpy・exchange_rate_usd が表の最新行と同じ。amount_jpy＝合計×率、amount_usd＝amount_jpy÷USD の率（セント）。USD の行が無いとき amount_usd が NULL で作れる |
| K14 関税の条件の正本は1つ | 新しい表に incoterm の列が無い（移行の試験）。会社の設定を DAP→DDP に変えると preview の関税が出る |
| K15 発行で計算し直す | サーバーの試験: 作成の後に税率の行を足して発行すると、発行日の率で tax_amount が変わる。作成の後に為替の行を足して発行すると、送料が shipping_snapshot の元の額から新しい率で換算し直され、exchange_rate・amount・合計が変わる。明細・運送会社・送料の元の額・支払方法は変わらない |
| K16 見積から作っても同じ計算 | サーバーの試験: 同じ明細・送料で、作る道と見積から作る道の税・関税・合計が一致。送料0の見積から作ると「送料を請求しない」になり 422 にならない |
| K17 新しい表の会社の分け | 移行の試験: 別の会社の文脈で tenant_duty_rules・中身の行が0行に見える |
| K18 誤りの返し方 | サーバーの試験: 409 duty_needs_carrier・duty_rule_overlap・fx_rate・tax_rate、422 shipping_required・payment_method、tax_amount・exchange_rate_jpy・exchange_rate_usd・amount_jpy・amount_usd のどれかを送ると 422・下書きでない請求書の支払方法を PATCH すると 409 invoice_not_draft |
| K19 秘書チャットが壊れない | 画面の試験: 秘書チャットで「送料を請求しない」を選んで作成でき、POST の中身に tax_amount が無い |
| K20 関税の額の変更が記録に残る | サーバーの試験: 足す・直す・消すで audit_logs が1行ずつ増える |
| K21 口座番号が AI の読み取りに出ない | 移行の試験: ai_ro の請求書の見え方の列に payment_account_number が無い。クラウドの見え方の試験 T10 が通る（新しい文字・JSONB の列がすべて分類済み）。便 A の後、reader 鍵で ai_ro の請求書の見え方の列を数えて payment_account_number が0件 |
| K22 新しいテナントでも作れる | サーバーの試験: tenant.py で作ったスキーマに対して、作る道・見積から作る道・詳細（_INVOICE_COLUMNS を読む）が通る |
| K23 支払方法は下書きのときだけ選び直せる | 画面の試験: 下書きの詳細画面に支払方法の選択があり、発行済みには無い。サーバーの試験: 下書きでない請求書への PATCH が 409 invoice_not_draft |
| K24 GET /fx-rate は表を読む | サーバーの試験: get_fx_rate を呼ぶと失敗する差し替えのもとで 200 と表の最新行（currency・rate・fetched_at）を返す。行が無い通貨は 503 |

## 9. PO の確かめ方（本番）

- 便 C・D の後、請求書作成画面を開き、見本と同じ並びになっていることを見る。
- 米国の取引先を選び、送料の一覧が出ること、選ぶと合計が変わることを見る（作成は押さなくてよい。試算だけで出る）。
- 関税を使うときは、会社の決まりのページで条件を DDP にし、関税の額を入れた後、同じ画面で関税の行と額が出ることを見る。

## 10. 外部・過去事例の参照と我々への応用

- 画面の手本は PO 本人のポートフォリオ（recon §8）。並びと「国によって税の行が出たり消えたりする」動きをそのまま使う。数字の直書きだけを表に置き換える。
- 消費税の扱いは国税庁の頁（recon §9）に合わせた。
- 口座番号を見せる範囲は、ADR-1061 で使った PCI DSS の手本（viewer-contract-stage の evidence-payment-methods.md）と同じ考えで、AI の読み取りには出さない。
- 関税の値の外部事例（運送会社の公開の料金）は使わない。理由: 値は PO が根拠の URL 付きで入れる仕組みにし、AI が値を持ち込まないため（ADR-095 付録1-4 が未決）。ADR-101:159 の FedEx の例は、表の形が足りるかの確かめにだけ使った（§5）。

## 11. 第1版の審査の指摘と対応

| 指摘 | 対応 |
|---|---|
| F1 関税の条件の正本が2つ（止める） | §3-3 で新しい表の incoterm 列を取りやめ、tenant_settings.duty_incoterms だけにした |
| F2 為替の出どころが2つ（止める） | §3-4 為替の規則。表だけにし、ライブ取得を作る道から外す。K13 |
| F3 税率0行で日本宛が止まる | §4 出す前の条件・§6 |
| F4 送料が未計算のときの作成・送料の通貨 | §3-4 送料の規則・§7 の3・K4 |
| F5 合計の式・端数・NULL | §3-4 の合計と端数・§3-3 の2〜3・§7 の1 |
| F6 tenant.py の外部キーの順・欠けた列 | §3-5（外部キーは張らない・9列を足す）・K22 |
| F7 直す道（PATCH）で支払方法を自由に書ける | §3-4 の PATCH |
| F8 見積から作る道が計算を通らない | §3-4 の from-quote・K16 |
| F9 PDF に支払方法が出ない・消すと失われる | §3-5 写しの列・§3-7・K12 |
| F10 税率を選ぶ日 | §3-4 基準日・発行で計算し直す・K15 |
| F11 通貨の初期値の正本・EUR | §3-2・§2・§6 |
| F12 K2 の判定・受入条件の不足 | K2 を画面の試験に変更・K13〜K22 |
| F13 決済手数料と ADR-101 | §2・§7 の2 で PO に聞く |
| F14 パスの誤り | recon を直した。§3-1 のパスを直した |
| F15 K1 と Q1 の結び付け | K1 から Q1 を外した |
| F16 宛名・メールの出どころ | §3-1 で担当者から読むと書いた |
| F17 送料の道の権限 | §6 で便 D のカードで数える |
| F18 tax_amount を送ったときの 422・秘書の通貨 | §3-4 extra="forbid"・§2 と便 D に秘書の通貨 |
| F19 請求先と発送先が別の国 | §3-4 に期待値を書いた |

## 12. 第2版の審査の指摘と対応

| 指摘 | 対応 |
|---|---|
| R1 tenant.py に欠けた列の数え漏れ（9列でなく12列＋明細の hs_code） | §3-5 に12列と hs_code を移行の行番号つきで並べた。K22 に見積から作る道・詳細を足した |
| R2 作る道の schema に為替の欄が残る | §3-4 の道の表で POST から5つの欄を外し extra="forbid"。K18 に 422 を足した |
| R3 GET /fx-rate がライブ取得 | §3-4 で表の最新行を同じ形で返す（無ければ 503）。便 C。K24 |
| R4 見積から作るときの送料・運送会社・支払方法 | §3-4 の from-quote に規則を書いた（送料>0 は見積の通貨と運送会社、0・NULL は「送料を請求しない」、支払方法は付けない）。§6 に運送会社 NULL の409。K16 |
| R5 発行で何を計算し直すか | §3-4 に5つ（税率・関税・送料の換算・為替の列・合計）と変えないものを並べた。K15 |
| R6 draft-context に wise_currency が無い | §3-2・§3-4 の道の表に足した。画面で絞り、サーバーでも同じ決まりで確かめる。K3 |
| R7 新しい列のクラウドの分類 | §3-5 の表。便 A。K21 に T10 |
| R8 FedExRateModal は見積の画面と共用 | 任意の originCountryCode を足し、渡さないときは今のまま（§3-4・便 D）。§6 に見積の画面の "JP" を残すと書いた |
| R9 Wise には口座番号の列が無い | §3-5（IBAN を入れる）・§3-7（wise_email を出す） |
| N1 権限の行番号 | recon §1 を tenant_policy.py:48 に直した |
| N2 外部キーを張らない理由 | §3-5 を「写しで残すので消すことを止める必要が無い」だけにした |
| N3 K1 の数え方 | K1 を data-testid の中の入力欄を数える形にした |
| N4 ai_ro から外れることの試験 | K21 に移行の試験を足した |
| N5 PayPal で支払われたときと写し | §3-4 で列の意味を分けた。§6 |

## 維持の仕組み

- 関税の条件の正本は tenant_settings.duty_incoterms だけ。額の正本は tenant_duty_rules と中身の表だけ。試算・作成・見積から作成・発行はすべて invoice_totals を通す（K16・K15 の試験で守る）。
- 為替の正本は app_fx_rate_history だけ（K13・K24 の試験で守る）。
- 新しい文字・JSONB の列を足したら、クラウドの見え方の分類を足さないと試験 T10 が落ちる（既存の仕組み）。
- 税率の正本は public.tax_rates だけ（最高管理者の画面で足す）。
- 支払方法の正本は振込先の表と public.tenant_paypal_config だけ。
- 直書きの選択肢が戻ったら K2 の画面の試験が落ちる。
