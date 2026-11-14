# design: 請求書作成画面をポートフォリオの形に作り直す（住所・税・関税・支払方法を記録の表から）

状態: 設計案 第9版（Opus 作成 2026-11-14。PO が振込先を版で持つ案を「1,」で選んだ。§18・§19）。以下は第8版までの経緯。第8版（Opus 作成 2026-11-13）。第1版はクラウドの設計審査で REVISE（止める2・直すべき11・覚え書き6）、第2版は REVISE（止める0・直すべき9・覚え書き5）、第3版は REVISE 相当（止める0・直すべき5・覚え書き6）、第4版は REVISE（止める0・直すべき1・覚え書き5）、第5版は REVISE（止める0・直すべき3・覚え書き4）、第6版は REVISE（止める0・直すべき1・覚え書き3）、第7版は REVISE（止める0・直すべき1・覚え書き2）。本版はすべてを反映した（§11〜§17 に対応表）。第8版はクラウドの設計審査で APPROVE（止める0・直すべき0・覚え書き3。覚え書きは実装カードで決める。PR #5486 のコメント）。PO 承認済み（2026-11-13「1,（２）決済手数料を合計に足す仕組みは、今回は作りません。別の作業に回します。→次便で」。§7 の決定のとおり）。
第9版（Opus 作成 2026-11-14）: PO が振込先を「版」で残す案を選んだ（2026-11-14「1,」）。振込先の表に版の仕組みを足し（§3-8・便 V・ADR-1079）、請求書は選んだ版の番号だけを持つ形に変えた（§3-5・§3-7）。変えた所は §18。第9版の審査は1回目が途中で止まり、2回目が REVISE。対応は §19。3回目の審査待ち。
根拠: 同じ場所の recon.md（§番号で指す）。基準 origin/main `c296af3bb`（第6版の審査で `56bd5c3ef` と照らし、引いた行番号はすべて一致。実装カードでは基準をその時の origin/main に更新する）。対象 ADR: ADR-101（§7 関税・実装上の注意）、ADR-095 付録1-4、ADR-106（テナント別ポリシー）、ADR-125 D5、ADR-1061（振込先・税率・発行元の表）、ADR-027（i18n）、ADR-144（UI の金型）、ADR-072（commit 後の reset）、ADR-135/136（危険な PR）。あるべき姿: docs/specs/quote-invoice/（KGI Q1〜Q15）。

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
- 振込先の表を「版」で持つ（直すと新しい版を足し、消すと隠す。前の版は消えない。§3-8・ADR-1079）。DB の見張りと新しいテナント用の同じ形まで。

対象外:
- 見積の作成画面（QuoteCreatePage）。見積の金額の計算は今のまま。送料を選んでも送料の会社と通貨を保存しない今の作り（QuoteCreatePage.tsx:293 は額だけを受け取る）も変えない。見積の画面の FedEx の発送元の初期値 "JP"（FedExRateModal.tsx:112・:130）も今のまま（§3-4 の FedEx の部品の扱い・§6）。
- 顧客別の関税（quote-invoice/kgi.md:13・:28 で対象外と決まっている）。
- 見本の「カテゴリ」列（商品の候補にその値が無い。recon §7）。
- PDF の見た目のそれ以外の変更。
- 振込先を登録する画面（ADR-1061 の残りの便で作る。recon §5）。その便は §3-8 の版の決まり（直す＝新しい版、消す＝消した時刻）で作る。
- 為替の表に EUR などを足すこと（今は USD だけを1日2回取っている。recon §5-1）。通貨を足すのは別のテーマ。
- 決済手数料を合計に入れること。ADR-101:173 は「合計計算に必ず含める」と書くが、payment_fee_settings の値と支払方法の結び付けが決まっていない。PO の決定（§7 の2）で、この設計の便 A〜D には入れず、次の便 E で行う。便 E は便 D の後に設計と審査をしてから作る。
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
| 支払方法 | 選ぶ欄なし | 振込先の表（tenant_invoice_payment_methods）の今の版（§3-8。superseded_by_id と deleted_at が NULL）で is_active の行のうち、発行元の地域（請求先の国から decide_issuer_region で決まる。issuer.py:20-27）と同じ行、sort_order 順。Wise の行は wise_currency が請求書の通貨と同じ行だけ（材料の道が全行を wise_currency つきで返し、画面が通貨を変えるたびに絞る。サーバーも作る道・直す道で同じ条件を確かめる）。PayPal は public.tenant_paypal_config にこのテナントの行があるときだけ（PayPal の正本はそこだけ。ADR-1061 design.md:246） |
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
- carrier（VARCHAR(50) NULL。NULL は「どの送料の会社でも」。値は /shipping/calculate の結果の carrier と同じ会社名。第7版で決めた: 書く道は前後の空白を除き小文字にして保存し、空の文字は NULL にする。表にも CHECK (carrier IS NULL OR (carrier = lower(btrim(carrier)) AND carrier <> '')) を付ける）
- label（TEXT NOT NULL。請求書の関税の行に出す名前）
- effective_from（DATE NOT NULL）、effective_to（DATE NULL）
- source_url（TEXT NOT NULL。値の根拠。空は不可。ADR-095 付録1-4「エビデンス確立」）
- note、is_active、created_at、updated_at
- 同じ国・同じ送料の会社で有効期間が重なる行は作れない（書く道で 409 duty_rule_overlap）。会社の比べは保存した形（上の小文字の形）どうしで行い、carrier が NULL の行どうしも同じ会社とみなす（SQL では IS NOT DISTINCT FROM を使う。= だと NULL どうしの重なりを見逃す。第7版で足した）。有効期間の終わりが NULL の行は終わりの無い行として重なりを見る。PUT で行を直すときは、その行自身（id <> :id）を重なりの相手から除く。同時に2つの書き込みが来ても重なりがすり抜けないように、検査の前に同じ取引の中で pg_advisory_xact_lock（会社と国から作った鍵）を取り、同じ会社・同じ国の書き込みを1つずつ順に通す（第8版で足した）。

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
3. DDP のとき、その国・その日に有効な行を探す。送料の会社が一致する行を先に、無ければ carrier が NULL の行。会社の比べ方は、両方の前後の空白を除き小文字にしてから同じかどうかを見る（第6版で決めた。見積の自由文字にも同じ比べ方を使う）。行が無ければ関税の行を出さない（duty_amount は NULL。国別の ON/OFF は「行があるか」で表す。ADR-101:149-159）。
4. 行があれば中身を sort_order 順に、金額＝基準×rate_pct/100。min があれば下限、max があれば上限で挟む。min・max の通貨が請求書の通貨と違うときは為替の表で換算する（§3-4 の為替の規則）。
5. 中身の合計を duty_amount に入れる。条件・使った行・中身・換算に使った値を duty_policy_snapshot に写す（列は今ある。recon §4）。
6. DDP で、その国に有効な行が「送料の会社つきの行だけ」あり（carrier が NULL の行が無い）、送料の会社が空（「送料を請求しない」を含む）か、どの行の会社とも一致しないときは、関税を決められない。試算は関税を「未計算」で返し、作成・見積から作る・発行のすべての道で 409 duty_needs_carrier で止める（少なく請求するのを防ぐ。第6版で、会社が一致しない場合も含めて全部の道で同じ規則にした）。その国に有効な DDP の行が1つも無いとき・条件が DAP・DDU のときは、この規則に当たらない（2・3 のとおり関税の行を出さない）。

### 3-4. 計算の規則とサーバーの道

**invoice_totals（backend/app/services/invoice_totals.py、新）が唯一の計算の場所。** 試算・作成・見積から作成・発行がすべてこれを呼ぶ。

- 合計＝小計＋送料＋消費税＋関税（関税が NULL のときは0として足す）。tax_amount と duty_amount は別の列に入れる。
- 端数: 消費税と関税の中身の1つずつを、通貨の最小単位（円は1円、ドルは1セント）で切り捨てる（§7 の1で PO が決めた）。
- 基準日: 税率と関税の行は「基準日」に有効な行を使う。作成・試算では今日（日本時間）、発行では発行の日（日本時間）。発行の道（invoices.py:474-501。今は状態を変えるだけ）で invoice_totals を発行日で計算し直し、税・関税・合計・写しを上書きしてから issued にする。理由: 税率の表の決まり「請求書は発行日に有効な行の率を写す」（migrations/20261112_150000_create_viewer_contract_public_tables.sql:166）。
- 発行で計算し直すものは次のすべて。どれも発行の時点の同じ為替の行の組（通貨ごとに最新の1行）を使う: ①税率の行 ②関税の行と中身（min・max の換算を含む） ③送料の換算（shipping_snapshot に残した元の額と元の通貨から、発行時の率で換算し直す。元の通貨が請求書の通貨と同じなら額は変わらない） ④exchange_rate_jpy・exchange_rate_usd・amount_jpy・amount_usd・fx_rate_snapshot ⑤合計。写しの形: fx_rate_snapshot は今の形 {currency, rate, fetched_at}（invoice_renderer.py:146・:371-380 と InvoiceDetailPage.tsx:86 が読む）のまま、請求書の通貨の1行だけを入れる。送料の換算に使った率は shipping_snapshot に、関税の換算に使った率は duty_policy_snapshot に、それぞれ {currency, rate_jpy, fetched_at} で入れる。明細の単価と数量・選んだ送料の会社と元の額・支払方法は変えない。
- 消費税: 届け先の国（§3-3 の1と同じ）が JP のときだけ。基準は小計＋送料（見本 js_app.js:117・国税庁 No.6301）。外国宛はかけない（輸出免税。国税庁 No.6551）。基準日に有効な行が無い日本宛は、試算で「未計算」、作成・発行は 409 tax_rate。使った率を tax_rate_percent に残す。
- 消費税と支払方法の決まり方は別: 消費税は届け先の国、発行元の地域と支払方法は請求先の国で決まる。例: 請求先が日本・発送先が米国 → 国内の振込先を選び、消費税なし、DDP なら関税あり。
- 為替の規則（為替の正本は app_fx_rate_history だけ）: 通貨ごとに fetched_at が一番新しい行を使う（作成と発行の時点で）。fx_rate_snapshot・exchange_rate_jpy・amount_jpy はこの行から作る。作る道の外部のライブ取得（invoices.py:253・:356 の get_fx_rate）は外す。表は今 fx_rate_updater（backend/app/tasks/fx_rate_updater.py:42-83）が同じ外部の値を1日2回入れている。換算が要るのに行が無い通貨は 409 fx_rate。2つの外貨の間は円を通して換算する。
- 為替の列の作り方（今の _calc_currency_amounts invoices.py:135-153 の JPY と USD の枝と同じ意味を保ち、値の出どころだけを表に変える。EUR の枝 :150-152 は total×rate_usd で意味が合わないので使わない。下の式に置き換える。丸めは今と同じく amount_jpy・amount_usd とも小数2桁の round（:142・:147）。これは表示用の換算額で、§7 の1の請求の額の端数とは別）: exchange_rate_jpy＝請求書の通貨の表の rate_jpy（JPY の請求書は NULL）。exchange_rate_usd＝USD の表の rate_jpy（1ドル＝何円。USD の請求書は NULL）。amount_jpy＝合計×exchange_rate_jpy（JPY は合計そのまま）。amount_usd＝amount_jpy÷exchange_rate_usd を1セントに丸める（USD は合計そのまま）。USD の行が無いときは amount_usd を NULL にし、止めない（請求の額は変わらないため）。
- 為替を見せる道 GET /api/v1/fx-rate/{currency}（invoices.py:1026-1050。今は get_fx_rate で外部から取る）も、表の最新行を同じ形（currency・rate・fetched_at）で返すように直す。呼ぶのは見積の詳細画面だけ（QuoteDetailPage.tsx:104。2026-11-13 git grep）。表に行が無ければ今と同じ 503。理由: 見積の詳細画面で見せた率と、同じ画面から見積を請求書にしたとき（:88）に保存する率を同じにする。
- 送料の規則: 送料は次のどちらかでないと作成できない。（ア）/shipping/calculate の結果の1つを選んだ（carrier・service_type・fee・currency を受ける。送料の通貨が請求書の通貨と違えば為替の規則で換算し、元の額と率を duty_policy_snapshot と同じ形で shipping の写しに残す）。（イ）人が「送料を請求しない」を選んだ（送料0・carrier は NULL）。どちらでもないと 422 shipping_required。理由: ADR-101:171「未連携なら0でなく未計算」。黙って0にしない。日本国内宛は今は FedEx 国際しか取れず静的表も0行なので、（イ）しか選べない（§7 の3）。送料の額は画面が選んだ値を受ける（見積は時間で変わるため取り直さない。今の道も同じ）。
- 見積から作るときの送料の規則: 見積の画面は送料の額だけを保存し、送料の会社と通貨を保存しない（QuoteCreatePage.tsx:293）。そこで、見積の shipping_fee が 0 より大きいときは（ア）として扱い、元の額＝見積の送料、元の通貨＝見積の通貨（請求書の通貨も見積の通貨なので換算しない）、送料の会社＝quotes.shipping_carrier（NULL のことがある）、source＝'quote' を shipping_snapshot に写す。shipping_fee が 0 または NULL のときは（イ）「送料を請求しない」として扱う。見積はすでに人が送料を決めた書類なので、見積から作る道では 422 shipping_required を返さない。送料の会社が NULL で、届け先の国の DDP の行が会社つきだけのときは、関税の規則（§3-3 の6）のとおり 409 duty_needs_carrier で止まる（§6）。
- FedEx の部品（frontend/src/components/FedExRateModal.tsx）の発送元: 任意の受け取り口 originCountryCode を足す。請求書作成画面は draft-context の発送元の国を渡し、部品はその値を使って発送元の欄を直せない形にする。渡された値が null のときは見積を取らず「未計算」と会社情報のページへの案内を出す。受け取り口を渡さない呼び出し（見積の作成画面 QuoteCreatePage.tsx:289）は今のまま（:112 の初期値 "JP" と :130 の `|| "JP"` を残す。見積の画面は §2 で対象外）。
- FedEx の部品の宛先・重量・運送会社（第4版で足した）: 部品は今、宛先の国（:113・:187）と重量（:197）を人が直せ、onSelectRate（:57・:340）は運送会社を渡さない。請求書作成画面からは、宛先＝draft-context の届け先の国（§3-3 の1と同じ決まり。発送先の写しが無ければ請求先の写し。第6版で直した）、重量＝明細の重さの合計を渡し、部品はこの2つも直せない形にする（originCountryCode を渡したときだけ。任意の受け取り口 lockInputs のような別の口は作らず、originCountryCode が渡された呼び出しを「請求書から」とみなす）。onSelectRate に4つめの引数 carrier（結果の r.carrier）を足す。見積の作成画面は受け取っても使わない。部品の内側の useState（:112-114）は開いた時の値しか読まないので、請求書作成画面は部品を開くたびに key を変えて作り直し、最新の宛先と重量で始める。宛先の郵便番号（第5版で足した。今は :115 の useState と :210-220 の欄で人が打て、:131 で送る）も、originCountryCode を渡したときは draft-context の届け先の postal_code（国と同じ写しから取る。_fetch_address_snapshot が zip を読み（invoices.py:75）、:94 で postal_code にする）を受け取り口 destinationPostalCode で渡し、欄を直せない形にする。写しに郵便番号が無いときは送らない（今と同じく任意）。発送先と請求先の写しがどちらも無いときは、届け先の国が無いので見積を取らず「未計算」と取引先の住所の登録への案内を出す。

| 道 | 中身 | 権限 |
|---|---|---|
| GET /invoices/draft-context?company_id= （新） | 発送先・請求先（_fetch_address_snapshot と同じ）、担当者の名前とメール、発行元の地域、発送元の国（発行元の表の country_code。無ければ null）、通貨の一覧と最新の為替（通貨・値・取得日時）、通貨の初期値（default_currency）、支払方法の一覧（id・display_name・method_type・wise_currency（Wise の行だけ。ほかは null）。発行元の地域で絞った全行を返し、通貨での絞りは画面が行う。PayPal は method_type 'paypal'・id null）、今日有効な税率（無ければ null）、会社の関税の条件、届け先（§3-3 の1の決まりで選んだ国と postal_code。第6版で足した。FedEx の部品・税・関税が同じ国を使う）。為替の取得日時は UTC の ISO 8601 の文字で返す。任意の invoice_id（第5版で足した）を受けたときは、その請求書に保存した issuer_region で支払方法を絞り、保存した currency を返す（請求先の今の国から地域を決め直さない。PATCH と同じ基準）。invoice_id のときは請求書の company_id を使う。company_id も渡されて請求書の company_id と違えば 422。保存した issuer_region が NULL の古い請求書は 'overseas' とみなす（詳細の道 invoices.py:814 の `or "overseas"` と同じ。PATCH も同じ扱い）。invoice_id の請求書が無ければ 404。道の順番: この道は GET /invoices/{invoice_id}（invoices.py:192-198。invoice_id は int）より前に宣言する（後だと draft-context が int に読まれて 422 になる） | invoices.create（今の POST /invoices と同じ） |
| POST /invoices/preview （新・書かない） | 受ける: company_id・currency・items（数量・単価）・shipping（§3-4 の（ア）か（イ）。任意）。返す: 小計・送料・消費税（率と額）・関税（ラベル・中身ごとの額）・合計、「未計算」の印と理由のキー | 同上 |
| POST /invoices （直す） | 受ける値に payment_method_ref（method_type と id）と shipping を足す。tax_amount・shipping_fee・payment_method（文字）・exchange_rate_jpy・exchange_rate_usd は受けない（InvoiceCreate からこの5つの欄を消し（今は schemas/invoice.py:45-49 にある）、extra="forbid" にして、送られたら 422）。計算は invoice_totals。payment_method_ref は draft-context と同じ選び方（今の版・is_active・地域・Wise の通貨）の中にあるか確かめ、無ければ 422 payment_method。前の版や消した版の id も 422 payment_method。支払方法は任意（秘書チャットは送らない）。作成画面は必須にする | 同上 |
| POST /invoices/from-quote/{id} （直す） | 明細は見積から写す。送料は上の「見積から作るときの送料の規則」で写す（送料の会社は quotes.shipping_carrier。tenant.py:811）。消費税・関税・合計は invoice_totals で計算する（見積の tax_amount・total_amount は写さない）。関税は §3-3 の6の規則（全部の道で共通）に従う。見積の送料の会社（自由文字）は §3-3 の3の比べ方で行の会社と比べる。支払方法はここでは付けない（体は今と同じ空。付けるのは詳細画面の下書きの欄で、下の PATCH を通る） | 今のまま（invoices.create） |
| POST /invoices/{id}/issue （直す） | §3-4 の基準日の規則で計算し直してから issued にする。payment_method_id があり、その版が今の版でない（直された・消された）か is_active でないときは、発行しないで 409 payment_method を返す（下書きの詳細画面で選び直してもらう。§3-8）。PayPal（payment_method_id が NULL）はこの検査に当たらない | 今のまま |
| PATCH /invoices/{id} （直す） | _UPDATABLE_COLUMNS（invoices.py:120）から payment_method・exchange_rate_jpy・exchange_rate_usd を外す。支払方法を直すときは payment_method_ref で受け、作る道と同じ検査をして payment_method と payment_method_id を入れ直す。支払方法を直せるのは下書き（draft）のあいだだけ（発行後に案内の口座が変わらないように）。下書きでないときは、今ある門（invoices.py:449-450。どの欄でも 400「draft状態の請求書のみ編集できます」）がそのまま止める。新しい返し方は作らない。InvoiceUpdate（schemas/invoice.py:55-60）からも payment_method・exchange_rate_jpy・exchange_rate_usd を外して payment_method_ref を足し、extra="forbid" にする。支払方法の検査は、請求書に保存した issuer_region と currency を基準にする（今の請求先から地域を決め直さない）。為替は直せない（正本は表）。今は画面に PATCH を呼ぶ所は無い（2026-11-13 git grep。詳細画面は表示だけ InvoiceDetailPage.tsx:296・:300-301）。便 D で詳細画面に下書きのときだけ支払方法を選ぶ欄を足し、この道を呼ぶ（選択肢は draft-context に invoice_id を付けて取る。保存済みの issuer_region で絞られるので、PATCH の検査と同じ候補になる） | 今のまま（invoices.update） |

- 支払方法を受けたら、作る道は payment_method（文字）に行の method_type（'bank'・'wise'。PayPal は今と同じ 'paypal'。invoices.py:672・:766）、payment_method_id に版の id を入れる（§3-5。写しは持たない。§3-8）。payment_method に display_name を入れないのは、payment_method が VARCHAR(50)（tenant.py:878）で display_name は長さの上限が無い TEXT（tenant.py:1251）のため。列を広げる案は取らない。理由: PostgreSQL はビューが使っている列の型の変更を断るので、この列を読む ai_ro・ai_cloud の見え方を作り直す移行が要り、便 A が大きくなる。詳細の道（GET /invoices/{id}）は payment_method_id の版の display_name と method_type を返し、詳細画面の支払方法の表示（InvoiceDetailPage.tsx:296）は、版の display_name があればそれを、無ければ payment_method を出す（便 C・D）。詳細の道は口座番号を返さない（口座番号は PDF だけに出す）。
- 2つの支払方法の列の意味を分ける: payment_method_id は「請求書で案内した支払い先の版」。payment_method（文字）は今のまま「実際に払われた方法」も兼ね、PayPal の入金確認で 'paypal' に上書きされる（invoices.py:766）。payment_method_id は入金確認で変えない。PDF の支払方法の区切りは payment_method_id の版から描く。
- 秘書チャット（SecretaryDraftInvoice.tsx:92）は同じ POST /invoices を通る。tax_amount・shipping を送っていないので、shipping が無いと 422 shipping_required になる。便 D で秘書チャットにも送料の選択（少なくとも「送料を請求しない」）を足し、同じ便で通貨の選択肢を draft-context から読む。
- realtime/topics.py には書き込みの道（POST・PUT・PATCH・DELETE）だけを載せる。試験は書き込みの道が表にあるかと、表に実在しない道が無いかを見る（test_realtime_topics.py:34-39・:108-111）。新しい書き込みの道（POST /invoices/preview・POST/PUT/DELETE /admin/duty-rules）は NO_SIGNAL_ROUTES（topics.py:95。請求書の道は :228-235）に今の請求書の道と同じ _PENDING で足す。GET の道（draft-context・GET /admin/duty-rules）は載せない（載せると ghost で落ちる）。
- GET /fx-rate/{currency} で JPY を頼まれたときは、今と同じく {currency: JPY, rate: 1.0, fetched_at: null} を返す（invoices.py:1040-1041。表に JPY の行は無いので、503 にしない。第7版で足した）。JPY 以外で表に行が無い通貨だけ 503。
- 為替の fetched_at（第5版で足し、第6版で道にも広げた）: 表の fetched_at（timestamptz）は UTC に直した ISO 8601 の文字で、写し・GET /fx-rate・draft-context のすべてに入れる。PDF は fetched_at[:19] の後に Z を付けて出し（invoice_renderer.py:377-378）、見積の詳細画面も slice(0, 19) の後に Z を付けて出す（QuoteDetailPage.tsx:169）ので、日本時間の文字を入れると9時間ずれて見える。
- 書いた後は reset_tenant_context()（ADR-072）。

### 3-5. 請求書の表に足す列（tenant_NNN.invoices。全テナント）

- payment_method_id（INTEGER NULL。選んだ振込先の版の id。外部キーは張らない。理由: ①版は DB の見張りで消せないので（§3-8）、外部キーで守るものが無い。②tenant.py は請求書の表（:861）を振込先の表（:1246）より前に作るので、外部キーを張るには作る順を入れ替える必要があり、便 A が大きくなる。PayPal は NULL）
- 振込先の写しと口座番号の列は持たない（第9版で取りやめ。§3-8・§18）。口座番号は振込先の詳細の表だけにある（1か所）。
- tax_rate_percent（NUMERIC(5,2) NULL。使った税率）
- shipping_carrier（VARCHAR(50) NULL）、shipping_service（VARCHAR(100) NULL）、shipping_snapshot（JSONB NULL。送料の元の額・元の通貨・換算の率・source（'calculate'・'quote'・'none'）・「送料を請求しない」の印）

backend/app/services/tenant.py（新しいテナント用）には次を足す。どれも本番の会社のスキーマには移行で入っているが、tenant.py に無い（2026-11-13 origin/main c296af3bb で tenant.py を列名ごとに grep して0件。issue_mode の1件は tenant_settings の行 :1887）:
- 請求書の表（:861-893）に12列: ship_to_snapshot・bill_to_snapshot・issue_mode・duty_amount・duty_policy_snapshot・fx_rate_snapshot（migrations/20260604_160000_add_invoice_snapshot_columns.sql:30-35）、paypal_order_id・paypal_approval_url・payment_fee（migrations/20260611_020000_add_invoice_paypal_columns.sql:26-28）、paypal_invoicer_view_url・paypal_copy_pdf・paypal_copy_pdf_at（migrations/20260612_131520_add_invoice_copypdf.sql:32-34）。型は移行と同じ。
- 見積の明細（quote_items :844-857）と請求書の明細（invoice_items :898-）に hs_code VARCHAR(20)（migrations/20260604_160000_add_invoice_snapshot_columns.sql:74・:86）。作る道と見積から作る道が読む（invoices.py:127・:287）。
- 上の新しい5列と関税の表2つ。
今はこの列が無いので、新しいテナントでは請求書の一覧・詳細（_INVOICE_COLUMNS invoices.py:105-118）・作る道・見積から作る道が動かない（recon §4-1）。

クラウドの読み取りの見え方（便 A に入れる）: 分類表は migrations/20261024_100300_create_ai_cloud_views.sql が正本で、毎回全行を入れ直す（同ファイル :3）。分類の無い文字・JSONB の列があると試験 T10（backend/tests/ops/test_ai_cloud_views.py:5）が落ちる。そこで同じファイルと元の表（docs/handoff/cloud-case-ai/stage1-column-class.tsv）に次の行を足す。数・日付の型の列（payment_method_id・tax_rate_percent・rate_pct・min_amount・max_amount・sort_order・rule_id・effective_from・effective_to・is_active）は型で通るので行を足さない（名前の見張りに当たる列は無い）。
| 表 | 列 | 分類 | 理由 |
|---|---|---|---|
| invoices | shipping_snapshot | mask | 送料の写し |
| invoices | shipping_carrier・shipping_service | mask | 値の決まりが無く自由に入る列（初期は最小） |
| tenant_duty_rules | destination_country_code・carrier・label・source_url・note | mask | 値の決まりが無く自由に入る列（初期は最小） |
| tenant_duty_rule_components | label・amount_currency | mask | 同上 |
| tenant_duty_rule_components | base | allow | CHECK で3つの値に限られる |
足す行は上の表の列の数で11（invoices 3・tenant_duty_rules 5・中身の表 3）。分類表の行数は2か所で固定されているので、両方を 1151 から 1162 に直す: ファイル先頭の注記（:3）と試験 backend/tests/ops/test_ai_cloud_views.py:486 の `== n0 == 1151`。実装では足した後の行数を数え直して一致を確かめる。

### 3-6. 関税の額の設定画面

- 置き場: 管理センターの「ビジネス設定」の中に「関税の額」を1つ足す（会社情報のページと同じ並び。ADR-1061 design.md:242 の入口の作り）。新しい大きなメニューは作らない。
- 画面の上に今の会社の条件（DAP・DDU・DDP）を読むだけで出し、「条件を変えるのは会社の決まりのページ」と案内する（TenantPolicyPage）。DAP・DDU のときは「今は関税を請求しません」と出す。
- 一覧（国・送料の会社・有効期間・根拠）と、足す・直す・消す。中身の行は足せる。根拠の URL は必須。
- 権限: 会社情報のページと同じ tenant.profile.view／edit。
- 足す・直す・消すたびに会社ごとの audit_logs に1行（ADR-1061 design.md:269 と同じ record_audit_log）。
- 道: GET・POST・PUT・DELETE /admin/duty-rules（会社ごとのスキーマ。commit 後に reset。書き込みの3つだけ realtime/topics.py の NO_SIGNAL_ROUTES に登録。§3-4）。

### 3-7. PDF（invoice_renderer.py）

- 合計の区切り（:340-360 付近）の Tax 行に率を添える（tax_rate_percent があるとき）。Duty 行は今のまま duty_amount が NULL でないときだけ。
- 合計の下に支払方法の区切りを足す: payment_method_id の版（一覧の行と詳細の行。今の版でなくても、直された版・消された版でもその版を読む）から、銀行は銀行名・支店・種別・口座番号・名義、Wise は名義・送金先のメール（wise_email）・銀行名・SWIFT・IBAN（あるときだけ）。PayPal は「PayPal」の1行。支払方法が無い請求書はこの区切りを描かない。payment_method_id の版が見つからないときも描かない（版は消せないので起きない作りだが、落とさない）。
- 見積の PDF（:583）は変えない。

### 3-8. 振込先の版（ADR-1079。PO 2026-11-14「1,」）

**なぜ**: PO の求め（振込先は会社情報の画面で直せて消せる・作成画面では登録名で選ぶだけ・直しても前のデータを残す）。今の形（ADR-1061）は直すと上書き、消すと詳細も CASCADE で消える（migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql:106・:128 の ON DELETE CASCADE）。前の版が残らないと、発行済みの請求書の振込先を出せない。写しを請求書に持つと口座番号の列が請求書の表にでき、運用の確かめの道が請求書の表ごと断る（migrations/20261031_210000_create_ops_case.sql:202-227 の is_denied_source。recon §11）。

**版の単位**: 一覧の1行（tenant_invoice_payment_methods）と、その詳細の1行（tenant_invoice_payment_bank か tenant_invoice_payment_wise。主キーは payment_method_id）で1つの版。

**一覧の表に足す2列**（全テナント・移行は便 V）:
- superseded_by_id（INTEGER NULL・REFERENCES 同じ表の id）。次の版の id。CHECK (superseded_by_id <> id)。同じ版を2つの版が指さないように、superseded_by_id に NULL を除く UNIQUE の部分の索引（uq_tenant_invoice_payment_methods_superseded_by）。
- deleted_at（TIMESTAMPTZ NULL）。消した時刻。
- 今の版＝superseded_by_id が NULL かつ deleted_at が NULL。選択肢に出すのは今の版で is_active のものだけ。

**DB の見張り（トリガー。テナントごとのスキーマに関数を置く。tenant.py:553-593 の trg_set_updated_at と同じ置き方）**:
- 詳細の2表: BEFORE INSERT OR UPDATE OR DELETE（関数 trg_payment_detail_immutable）。UPDATE と DELETE は必ず断る（詳細は版の中身なので後から変えない）。INSERT は、親の一覧の行（payment_method_id）が今の版（superseded_by_id と deleted_at が NULL）のときだけ通す。古い版や消した版に後から詳細を足すことを断る。
- 一覧の表: BEFORE UPDATE OR DELETE（関数 trg_payment_method_version_guard）。DELETE は断る。UPDATE は、id・tenant_id・region・method_type・display_name・created_at のどれかが変わると断る。superseded_by_id と deleted_at は NULL から値へ1回だけ入れられ、値が入った後に変えると断る。sort_order・is_active・updated_by_user_id・updated_at は直せる（並び順と「使う・使わない」は版を作らない）。superseded_by_id を入れるときは、指す先の行が同じ表にあり、id が自分より大きく、region と method_type が自分と同じで、今の版であることを確かめ、違えば断る。id が大きい向きにしか指せないので、2つの版が互いを指す輪はできない。
- 3表（一覧と詳細2表）に、表を丸ごと空にする命令を断る見張りも置く（`BEFORE TRUNCATE ... FOR EACH STATEMENT`。関数 trg_payment_version_no_wipe）。
- 見張りは1テナントに6つ（行ごとの見張りが詳細2表に1つずつと一覧に1つ、表を丸ごと空にする命令を断る見張りが3表に1つずつ）。断るときは RAISE EXCEPTION で、SQLSTATE は既定の P0001。
- 会社を消すときは DROP SCHEMA ... CASCADE（backend/app/routers/super_admin_tenants.py:167）なので、行ごとの見張りには当たらない。
- 表を丸ごと空にする命令は行ごとの見張りに当たらないので、上の文ごとの見張りで断る。権限だけに頼らない理由: アプリの普段の接続は、印 SA18_PHASE2_ENABLED=1 が無いと表の持ち主の役に戻される（.github/workflows/deploy.yml:452-467）。アプリは表の持ち主の役の接続も常に持つ（backend/app/database.py:90 の ADMIN_DATABASE_URL）。本番がどちらの役で動いているかは確かめていない。今ある試験で振込先の表を丸ごと空にするものは無い（試験 backend/tests/test_lead_merge_pg.py:344 は leads などを空にするが、振込先の表は leads などを参照しないので連鎖しない。migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql の REFERENCES は国・都道府県と自分の表だけ）。
- tenant.py では、見張りの関数と見張りを振込先の表を作る文の後ろに置く。前例の trg_set_updated_at（:553-593）は表を作る文より前にあるが、同じ位置に置くとまだ無い表を指して失敗する（振込先の表は :1246 以降で作られる。recon §11）。正確な行は便 V のカードで、便 A が入った後の main で測る。

**直すときの手順（登録画面の便で作る。本設計は道の決まりだけを決める）**: 1つの取引の中で、①新しい一覧の行と詳細の行を足す（region・method_type は前の版と同じ）②`UPDATE 一覧 SET superseded_by_id = :new WHERE id = :old AND superseded_by_id IS NULL AND deleted_at IS NULL`。②で変わった行が0なら取引を戻して 409（同時に2人が直したとき、後の人を止める）。種類（銀行⇔Wise）を変えるのは「消す＋足す」で、ADR-1061 の 422 type_immutable は残す。地域（国内⇔海外）を変えるのも「消す＋足す」とする。消すは `deleted_at = NOW()`。登録画面の便への申し送り: 見張りが断ったとき（P0001）に 500 のまま返さず、409 か 422 の理由コードに置き換える。

**請求書との関係**: 請求書は payment_method_id（版の id）だけを持つ。作る道・直す道（PATCH）は今の版で is_active のものだけを受け、ほかは 422 payment_method（§3-4）。下書きの請求書が指す版が今の版でなくなったら、発行は 409 payment_method で止まり、下書きの詳細画面で選び直す（§3-4）。発行済みの請求書は、版が直されても消されても、PDF でその版を出し続ける（§3-7）。

**影響を数えた結果（recon §11）**: 振込先の表を読む・書くアプリの道は今0本。本番の振込先の表は全社0行、請求書も全社0行（2026-11-14 reader 鍵）。試験 backend/tests/test_tenant_issuer_tables_pg.py の「一覧を消すと詳細も消える」（:248 付近）は「消すことを断る」に変わる（便 V）。同じ試験の形の比べ（:259-277。tenant.py で作った形と、表を消して 20261112_160000 の移行だけを流し直した形を比べる）は、便 V の後は tenant.py の側にだけ2列と見張りがあるので落ちる。便 V で、流し直しを「20261112_160000 の後に便 V の移行も2回流す」に変え、2列・索引・見張り6つも比べる形に足す。

## 4. 便の順番

| 便 | 中身 | 利用者に見える変化 | 危険 |
|---|---|---|---|
| A | 移行: 関税の表2つ・請求書の5列・tenant.py の同じ形と欠けた12列・明細2表の hs_code・クラウドの読み取りの見え方の表への分類（§3-5 の表。SQL と元の表の両方） | 無し | **危険**（migrations/。ADR-135/136 の GO とバックアップ確認） |
| V | 移行: 振込先の一覧の表に superseded_by_id・deleted_at、見張りの関数3つと見張り6つ（全テナント）。tenant.py にも同じ形。移行の試験の直し（§3-8・K25） | 無し | **危険**（migrations/。ADR-135/136 の GO とバックアップ確認） |
| B | 関税の額の道と設定画面 | 管理センターに「関税の額」 | 普通 |
| C | invoice_totals・draft-context・preview・作る／見積から作る／発行／直す道・為替を表だけに（GET /fx-rate も表の最新行を返す）・PDF の支払方法と率 | PDF に支払方法が出る。作る道が新しい形になる。新しい理由コード（duty_needs_carrier・duty_rule_overlap・shipping_required・fx_rate・tax_rate・payment_method）を、frontend/src/lib/apiErrorReason.ts の API_ERROR_REASON_KEYS（:11-30）、ja.json と en.json の apiError、backend/tests/test_api_error_reason_sync.py の固定の一覧、frontend/src/lib/apiErrorReason.test.ts:76 の件数（今は18）に足す（第8版で足した。足さないと画面と秘書チャットにコードの文字がそのまま出る。api.ts:129-131） | 普通（**C と D は同じ PR で出す**。今の作成画面は tax_amount を送るので、C だけ先に出すと作成画面が 422 になる） |
| D | 作成画面の作り直し・FedExRateModal に任意の originCountryCode を足し請求書の画面から渡す（渡さない見積の画面は今のまま）・秘書チャットの送料の選択と通貨の選択肢・詳細画面の下書きのときだけの支払方法の選択 | 作成画面が見本の並びになる。下書きの詳細画面で支払方法を選び直せる | 普通 |
| E | 決済手数料を合計に入れる（ADR-101:173。PO 2026-11-13「次便で」）。中身は便 D の後に設計し審査する | 合計に手数料の行が出る（設計で決める） | 設計で決める |

- 1便1目的。C と D だけは上の理由で1つの PR にする（実装は C→D の順に2つのコミットで分ける）。
- 便 V は便 A の後、便 C の前に出す（便 C の作る道と PDF が版の決まりを前提にする）。A と V はどちらも tenant.py を直すので、V は A が main に入った後の main から作る。
- **便 C・D を本番に出す前の条件**: 本番の税率の表に1行以上あること（reader 鍵で数える）。今は0行（recon §5）。0行のまま出すと、日本宛の請求書が秘書チャットも含めて作れなくなる（409 tax_rate）。PO が最高管理者の税率の画面で 10%・2019-10-01 を入れる（ADR-1061 の予定と同じ）。
- 便 A の後、PO が行うこと: 関税の額を根拠付きで入れる（便 B の後。会社の条件を DDP にしたときだけ効く）。振込先を入れる（ADR-1061 の登録画面ができた後。その画面は §3-8 の版の決まりで作る）。

## 5. 代替案と選んだ理由

- 画面で合計を計算する（今の形）→ 取りやめ。関税の式を画面とサーバーの2か所に持つことになる。画面の値をそのまま保存すると、誤った額が通る。
- 新しい表の各行に DAP・DDU・DDP を持つ（第1版）→ 取りやめ。会社の設定 duty_incoterms が既に正本で、画面もある。2か所に持つと食い違う。
- 為替をライブ取得のまま残す → 取りやめ。画面に出す率（表）と保存する率（ライブ）が別になり、画面の額と PDF の額がずれる。
- 関税の式を「率1つ」だけにする → 取りやめ。ADR-101:159 の FedEx の例は率・下限つき手数料・上下限つき MPF の3つの形を持つ。中身の行（率・下限・上限・基準）なら3つとも表せる。
- 関税の式を計算式の文字で持つ → 取りやめ。文字の式を実行する仕組みは誤りや危険が入りやすい。決まった形（基準×率を下限と上限で挟む）なら検査できる。
- 消費税をテナントごとの表に持つ → 取りやめ。税率は国の決まりで全社同じ。ADR-1061 で public.tax_rates を作ってある。
- 支払方法に B2B 専用の表を作る → 取りやめ。振込先の表がすでにある。2か所に持つと SSOT が崩れる（ADR-1061 design.md:417 の宿題をこの形で閉じる）。
- 振込先の写しを請求書に持つ（第8版まで）→ 取りやめ（第9版）。口座番号を写すと請求書の表に口座番号の列ができ、運用の確かめの道（is_denied_source）が請求書の表ごと断る。写さないと、振込先を直したり消したりした後に発行済みの請求書の振込先が出せない。
- 振込先を上書きで直し、前の値を別の履歴の表に持つ → 取りやめ。今の版と前の版が別の表になり、請求書がどちらを指すかで読み方が2つに割れる。
- 振込先を版で持ち、請求書は版の番号だけを持つ → 採用（§3-8・ADR-1079）。口座番号は詳細の表の1か所に残り、ADR-1061 決定9 の列名の隠し方がそのまま効く。
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
| 口座番号が AI の読み取りに出る | 請求書の表に口座番号を持たない（§3-5・§3-8）。口座番号は振込先の詳細の表だけで、ADR-1061 決定9 のとおり列名で外れる |
| 振込先の版が増え続ける | 1社の直しは年に数回の見込み。行の数は問題にならない（ADR-1079 の受け入れたリスク） |
| 人が DB で版の中身を直したい | 見張りが断る。直すときも新しい版を足す。間違えた版は消す（deleted_at）で隠す |
| 下書きの請求書が指す版が直された | 発行が 409 payment_method で止まり、下書きの詳細画面で選び直す（§3-4・K25） |
| 作成画面または秘書チャットで「送料を請求しない」を選び、届け先の国の DDP の関税の行が運送会社つきしか無い（第7版で足した） | §3-3 の6のとおり 409 duty_needs_carrier で止まる。作成画面は試算の段階で関税を「未計算」と理由（duty_needs_carrier の文言キー）を見せ、作るボタンを押せない。秘書チャットは 409 の理由の文言を返事に出す。運送会社を問わない行（carrier NULL）を入れれば作れる。少なく請求するよりは止めるほうを選ぶ（§3-3 の6） |
| 運送会社が NULL の見積（QuoteCreatePage.tsx:293 は送料の額だけ保存）から作り、関税の行が運送会社つきしか無い | 409 duty_needs_carrier で理由が出る。運送会社を問わない行（carrier NULL）を入れれば作れる。見積の画面で運送会社を保存するのは対象外 |
| 見積の画面の発送元は今の "JP" のまま残る（FedExRateModal.tsx:112・:130） | 請求書の画面だけ渡す値に替える。見積の画面の直しは別のテーマ（§2 対象外） |
| PayPal で支払われると payment_method が 'paypal' に上書きされ（invoices.py:766）、案内した振込先と違って見える | 列の意味を分ける（§3-4）。payment_method は実際に使われた方法、payment_method_id は請求書に書いた振込先の版。PDF は版を描く。上書きしても payment_method_id は変えない |
| 見積の送料の通貨が見積の通貨と違うことがある（QuoteCreatePage.tsx:293 は FedEx の通貨を捨て、額を Math.round で丸めて保存する） | 見積から作る道は、見積の送料を見積の通貨の額とみなす（人が見積で見て決めた額のため）。FedEx の料金の通貨が見積の通貨と違ったときの誤りは、見積の画面の今の作りから来るもので、この設計では直さない（§2 対象外）。PO の目視（§9）で見積の送料の通貨を確かめる |
| 詳細画面の支払方法の選択には2つの権限が要る（材料の draft-context は invoices.create、PATCH は invoices.update） | 選択は両方の権限を持つ人にだけ出す。便 D の実装カードで、片方だけ持つ役割が本番の役割の表にあるかを数える。あれば止めて PO へ |
| 為替の表に USD の行が無い | amount_usd を NULL にして止めない（§3-4）。JPY 以外の通貨で行が無いときは 409 fx_rate |

## 7. 未決（PO に決めてもらうこと）

2026-11-13 に PO が決めた（原文「1,（２）決済手数料を合計に足す仕組みは、今回は作りません。別の作業に回します。→次便で」。選択肢1＝設計と3つの案をそのまま承認、ただし2は「次便で」）。
1. 端数の処理（消費税と関税の中身の1つずつ）: 切り捨て。
2. 決済手数料を合計に入れること（ADR-101:173）: 便 A〜D には入れず、次の便 E で行う。便 E は payment_fee_settings と支払方法の結び付けを決める設計と審査を便 D の後に行う。
3. 日本国内宛の送料: 当面は「送料を請求しない」だけで作る。

## 8. 受入条件

| 基準 | 検証方法 |
|---|---|
| K1 作成画面に住所を打つ欄が0個 | 画面の試験: 発送先の区切り（data-testid="invoice-ship-to"）の中の input・textarea を数えて0。取引先を選ぶと住所の文字と担当者の名前・メールが出ること |
| K2 作成画面と秘書チャットの通貨・支払方法の選択肢は材料の道の値だけ | 画面の試験: draft-context の応答の通貨と支払方法を変えると、選択肢がその通りに変わる（直書きの配列が残ると落ちる） |
| K3 支払方法は表の行だけ（Q7） | サーバーの試験: 表に無い id を作る道と PATCH に送ると 422 payment_method。Wise は通貨が違う行を送ると 422 payment_method。画面の試験: 通貨を USD→JPY に変えると wise_currency が USD の Wise の行が選択肢から消え、選んでいた値が外れる |
| K4 送料が取れないとき 0 でなく「未計算」、選ばないと作れない（ADR-101:171・Q3） | 画面の試験: /shipping/calculate が空のとき送料の欄が「未計算」。サーバーの試験: shipping 無しの作成が 422 shipping_required、「送料を請求しない」なら送料0で作れる |
| K5 送料の会社の一覧が出て選べる（Q4。今あるのは FedEx だけ） | 画面の試験: 結果の会社が一覧に出て、選ぶと送料と合計が変わり、保存される送料の会社が選んだ会社になる。請求書作成画面から開いた部品では宛先・重量・発送元の欄を直せず、値が draft-context の届け先の国（発送先の写しが無い取引先では請求先の国）と郵便番号・明細の重さの合計・発行元の国と同じ。本番で FedEx のライブ見積が出るかは PO の目視（§9） |
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
| K17 新しい表の会社の分け | 移行の試験: 別の会社の文脈で tenant_duty_rules・中身の行が0行に見える。便 A の移行は全テナントを回すので、backend/tests/rls_bootstrap.py の _TENANT_LOOP_MIGRATIONS（:172-191。前例 20261112_160000 が :190）にテナントを選ぶ条件の回数と一緒に登録する。あわせて backend/tests/test_tenant_loop_migration_guard.py の _REVIEWED（:5「書くまでこの試験は落ちる」）に、キー rls_bootstrap.py の行の集合（同じファイルの :28-53。前例 20261112_160000 が :52）へ同じ移行の名前を足し、移行の試験の新しいファイルを 'scoped' の行として足す（前例 test_tenant_issuer_tables_pg.py が :110-113）。同じ移行の試験で、道を通さず直接 INSERT した carrier が大文字まじり・前に空白つき・空の文字の3通りとも CHECK で拒まれることを確かめる（第8版で足した） |
| K18 誤りの返し方 | サーバーの試験: 409 duty_needs_carrier・duty_rule_overlap・fx_rate・tax_rate、422 shipping_required・payment_method、作る道に tax_amount・exchange_rate_jpy・exchange_rate_usd・amount_jpy・amount_usd・shipping_fee・payment_method（文字）のどれかを送ると 422。PATCH に exchange_rate_jpy・exchange_rate_usd・payment_method（文字）を送ると 422。下書きでない請求書の PATCH は今と同じ 400。409 duty_needs_carrier は作る・見積から作る・発行の3つの道それぞれで、DDP・会社つきの行だけの国に「会社が空」と「会社が一致しない」の2通りを試す。比べ方は、前後に空白がある大文字まじりの会社名の見積と、同じ名前を小文字だけで書いた行が一致する。409 duty_rule_overlap は、大文字まじりと空白つきで書いた同じ会社名の行と、carrier が NULL の行どうしの2通りで、有効期間が重なると返る。書いた行の carrier は小文字・空白なしで保存され、空の文字は NULL で保存される。PUT で行の金額だけを直すとき、自分の行とは重ならないとみなされて 200 になり、ほかの行と期間が重なるように直すと 409 duty_rule_overlap になる |
| K19 秘書チャットが壊れない | 画面の試験: 秘書チャットで「送料を請求しない」を選んで作成でき、POST の中身に tax_amount が無い。DDP で運送会社つきの関税の行しか無い国の取引先では、409 duty_needs_carrier の理由として ja.json の apiError の日本語の文言が返事に出て、コードの文字 duty_needs_carrier はそのまま出ない。請求書は作られない。あわせて apiErrorReason.test.ts で新しい6つのコードが日本語の文言に変わることを確かめる |
| K20 関税の額の変更が記録に残る | サーバーの試験: 足す・直す・消すで audit_logs が1行ずつ増える |
| K21 請求書の表に口座番号を持たない・新しい列はすべて分類済み | 単体の試験（test_invoices_hold_no_payment_copy）: 新しい会社の DDL の請求書の表と便 A の移行の文に、payment_method_snapshot・payment_account_number・account_number・iban の文字が無い。PG の試験（便 A の形の試験の中）: 試験の会社の請求書の表の列を information_schema で引き、列名の決まり DENY_COLUMN_RE（backend/app/ops/readonly_query.py:43）に当たる列が0個。クラウドの見え方の試験 T10 が通る（新しい文字・JSONB の列がすべて分類済み） |
| K22 新しいテナントでも作れる | サーバーの試験: tenant.py で作ったスキーマに対して、作る道・見積から作る道・詳細（_INVOICE_COLUMNS を読む）が通る |
| K23 支払方法は下書きのときだけ選び直せる | 画面の試験: 下書きの詳細画面に支払方法の選択があり、発行済みには無い。サーバーの試験: 下書きでない請求書への payment_method_ref の PATCH が 400 で、payment_method_id が変わらない。下書きなら変わり、payment_method が行の method_type になる。請求書を作った後に取引先の請求先の国を JP と外国の間で変えても、invoice_id 付きの draft-context が返す候補は保存済みの issuer_region のもので、その候補を PATCH すると 200 になる |
| K24 GET /fx-rate は表を読む | サーバーの試験: get_fx_rate を呼ぶと失敗する差し替えのもとで 200 と表の最新行（currency・rate・fetched_at）を返す。行が無い通貨は 503。fetched_at は UTC の ISO 8601 の文字（末尾が Z か +00:00）。draft-context の為替の取得日時も同じ形。JPY は表を読まず 200 で rate 1.0・fetched_at null |
| K25 振込先の版（§3-8） | 移行の試験（便 V）: 詳細の2表の UPDATE と DELETE が断られる。一覧の DELETE が断られる。一覧の region・method_type・display_name・tenant_id・created_at の UPDATE が断られる。superseded_by_id・deleted_at は NULL から値へ1回入れられ、2回目の変更は断られる。sort_order・is_active は直せる。superseded_by_id に自分の id は CHECK で断られ、2つの版が同じ次の版を指すと UNIQUE で断られる。superseded_by_id が自分より小さい id・別の region か method_type の行・今の版でない行を指すと断られる。古い版と消した版への詳細の INSERT は断られ、今の版への詳細の INSERT は通る。3表それぞれを丸ごと空にする命令が断られる（表の持ち主の役でも）。既存の試験 test_tenant_issuer_tables_pg.py の形の比べ（:259-277）は、20261112_160000 の後に便 V の移行も2回流して、2列・索引・見張り6つまで同じ。便 V の移行は全テナントを回すので、K17 と同じく backend/tests/rls_bootstrap.py の _TENANT_LOOP_MIGRATIONS と backend/tests/test_tenant_loop_migration_guard.py の _REVIEWED（rls_bootstrap.py の集合と、新しい試験ファイルの 'scoped' の行）に登録する。tenant.py で作ったスキーマと移行で作ったスキーマで、2列・索引・見張り6つが同じ。サーバーの試験（便 C）: 版 X で請求書を発行し、X を直して版 Y を作ると、PDF は X の口座番号を出す。draft-context の候補は Y だけ。X の id で作ると 422 payment_method。X を指す下書きを発行すると 409 payment_method。本番（便 V の後）: reader 鍵で全テナントの2列と見張り6つを数える |

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

## 13. 第3版の審査の指摘と対応

| 指摘 | 対応 |
|---|---|
| F1 分類表の行数 1151 が試験 test_ai_cloud_views.py:486 にも固定 | §3-5 の分類の後に、注記（:3）と試験（:486）の両方を 1163 に直すと書いた。実装で数え直す |
| F2 PATCH は draft 以外を既に 400 で止める（invoices.py:449-450） | §3-4 の PATCH の行で、今の 400 を残し新しい 409 は作らないとした。K23 を 400 に合わせた |
| F3 payment_method は VARCHAR(50)、振込先の表示名は長さ無制限 | §3-4 で列には method_type（'bank'・'wise'・'paypal'）を入れ、表示名は写しに入れる。列は広げない（理由を書いた）。詳細は写しの表示名を出す（便 D） |
| F4 FedEx の部品は宛先・重量を直せ、運送会社を渡さない | §3-4 の部品の項に、宛先・重量を固定、onSelectRate に carrier、開くたびに key を変えると書いた。K5 に足した |
| F5 fx_rate_snapshot の形 | 今の形（請求書の通貨の1行）を変えない。送料・関税に使った率はそれぞれの写しに入れる（§3-4） |
| F6 為替の道の名前と行番号 | /api/v1/fx-rate/{currency}（invoices.py:1026-1050）に直した（design・recon） |
| F7 見積の送料の通貨は保証されない（QuoteCreatePage.tsx:293） | §6 にリスクと対処（見積の通貨の額とみなす・見積の画面は直さない・PO の目視） |
| F8 payment_account_number にクラウドの行は要らない | §3-5 の表から外し、名前の見張りで外れる前例を書いた |
| F9 PATCH は保存済みの発行元・通貨で確かめる／権限が2つに分かれる | §3-4 の PATCH の行に保存済みの値で確かめると書いた。§6 に権限の行（両方を持つ人にだけ出す・便 D で数える） |
| F10 K18 に shipping_fee・payment_method が無い | K18 に足した（作成7つ・PATCH 3つで 422） |
| F11 為替の列の計算の枝と丸め | §3-4 で JPY・USD の枝だけを使い、EUR の枝（:150-152）は使わない、丸めは小数2桁（:142・:147）と書いた。§7 の丸めとは別 |

## 14. 第4版の審査の指摘と対応

| 指摘 | 対応 |
|---|---|
| G1 詳細画面の支払方法の候補（draft-context＝今の請求先の国）と PATCH の検査（保存済みの issuer_region）がずれる | §3-4 の draft-context に任意の invoice_id を足し、保存済みの issuer_region と currency で絞ると書いた。PATCH の行で詳細画面は invoice_id 付きで取るとした。K23 に請求先の国を変えた場合の試験を足した |
| G2 realtime/topics.py に GET を載せると ghost で落ちる | §3-4 で書き込みの道だけを NO_SIGNAL_ROUTES に足し、GET は載せないと書いた。§3-6 も合わせた |
| G3 今ある試験が消す欄を送る（test_invoices.py 17か所・test_issuer.py 4・test_paypal_invoicing.py 1）・get_fx_rate の差し替え34か所 | 便 C の実装カードに直す試験の一覧として書く（設計の決まりは変えない） |
| G4 FedEx の部品の郵便番号の欄が決まっていない | §3-4 の部品の項に、発送先の写しの postal_code を渡して固定、無ければ送らないと書いた |
| G5 fetched_at の時刻の形 | §3-4 に UTC の ISO 8601 で写しに入れると書いた |
| G6 移行の試験の登録・quotes.shipping_carrier は自由文字 | K17 に _TENANT_LOOP_MIGRATIONS への登録を書いた。見積から作る道では、見積の送料の会社が届け先の国の DDP の会社つきの行のどれとも一致せず、会社なしの行も無いときは、送料の会社が選ばれていないとみなして 409 duty_needs_carrier で止める（§3-4 の見積から作る道の行。自由文字の違いで関税が黙って抜けるのを防ぐ） |

## 15. 第5版の審査の指摘と対応

| 指摘 | 対応 |
|---|---|
| F1 関税の会社の不一致の扱いが道で割れる（見積から作る道だけ 409、ほかは黙って抜ける）・DDP の行が無い国でも 409 に読める | §3-3 の6を全部の道で共通の規則にし、会社が空と一致しないの両方で 409、DDP の行が無い国と DAP・DDU は当たらないと書いた。比べ方（空白を除き小文字）を §3-3 の3に決めた。見積から作る道の行は §3-3 の6を指すだけにした。K18 に足した |
| F2 FedEx の宛先と郵便番号が発送先の写しだけから取られる | draft-context に届け先（§3-3 の1と同じ決まりの国と postal_code）を足し、部品はそれを使うとした。両方無いときは見積を取らない |
| F3 K17 に test_tenant_loop_migration_guard.py の _REVIEWED が抜けている | K17 に _REVIEWED の2か所（rls_bootstrap.py の集合・新しい試験ファイルの行）を足した |
| F4 draft-context の道の順番 | §3-4 の draft-context の行に GET /invoices/{invoice_id} より前に宣言すると書いた |
| F5 invoice_id のときの company_id と issuer_region が NULL の扱い | 請求書の company_id を使い、違えば 422、NULL は 'overseas'（invoices.py:814 と同じ）と書いた |
| F6 zip の行番号のずれ | invoices.py:75・:94 に直した |
| F7 GET /fx-rate と draft-context の時刻の形 | UTC の ISO 8601 を写し・GET /fx-rate・draft-context の全部に書いた。K24 に形の確かめを足した |

## 16. 第6版の審査の指摘と対応

| 指摘 | 対応 |
|---|---|
| G1 関税の行の重なりの検査で会社名の比べ方が決まっていない（大文字小文字や空白だけ違う行・carrier が NULL の行どうしの重なりが通る） | §3-3 の表の carrier に、書く道で小文字・空白なしにして保存し空は NULL、表に CHECK を付けると書いた。重なりの検査は保存した形どうしで、NULL どうしは IS NOT DISTINCT FROM で同じとみなすと書いた。K18 に足した |
| N1 GET /fx-rate の JPY が 503 に読める | §3-4 に JPY は今と同じ返し方（invoices.py:1040-1041）と書いた。K24 に足した |
| N2 「送料を請求しない」で DDP・会社つきの行だけの国は、作成画面と秘書チャットでいつも 409 になるのに §6 に無い | §6 に行を足した（作成画面は未計算と理由を見せる。秘書チャットは理由を返事に出す。対処は carrier NULL の行）。K19 に期待を足した |
| N3 基準の origin/main が古い | 冒頭の基準に、56bd5c3ef で行番号が一致したことと、実装カードで基準を更新することを書いた |

## 17. 第7版の審査の指摘と対応

| 指摘 | 対応 |
|---|---|
| F1 K19 の「理由の文言が出る」が判定できない（新しいコードが理由の表に無く、コードの文字がそのまま出る） | 便 C に、6つのコードを apiErrorReason.ts の表・ja.json/en.json の apiError・test_api_error_reason_sync.py の固定の一覧・apiErrorReason.test.ts の件数に足すと書いた。K19 を日本語の文言が出てコードの文字が出ないことの確かめに直した |
| M1 PUT で自分の行と重なる・同時の書き込みで重なりがすり抜ける | §3-3 に、PUT は id <> :id で自分を除き、会社と国ごとの pg_advisory_xact_lock で順に通すと書いた。K18 に PUT の2通りを足した |
| M2 CHECK が直接 INSERT を拒むかの試験が無い | K17 の移行の試験に、大文字まじり・前に空白・空の3通りの直接 INSERT が拒まれることを足した |

## 18. 第9版で変えた所（PO 2026-11-14「1,」で振込先を版で持つ）

| 所 | 第8版 | 第9版 |
|---|---|---|
| §2 対象 | 振込先の表は変えない | 振込先の表に版の仕組みを足す（便 V） |
| §3-5 請求書の列 | 7列（payment_method_snapshot・payment_account_number を含む） | 5列。写しと口座番号の列は持たない |
| §3-5 分類 | 12行・1163 | 11行・1162（payment_method_snapshot の行を外す） |
| §3-4 発行 | 版の検査なし | 下書きの版が今の版でなければ 409 payment_method |
| §3-7 PDF | 写しの列から描く | 版の id で一覧と詳細を読んで描く |
| §3-8 | 無し | 版の決まり・見張り・直す手順 |
| §4 | 便 A〜E | 便 V を A の後・C の前に足す |
| K21 | ai_ro に口座番号の列が無い | 請求書の表に口座番号の列が無い |
| K25 | 無し | 版の試験（移行・サーバー・本番の数え） |

## 19. 第9版の設計審査（1回目・2026-11-14・クラウド）への対応

1回目は審査役の調べる命令が見張りに止められ、判定の前に終わった。止まるまでの指摘と、Opus が別に見つけた1件をすべて直した。

| 指摘 | 対応 |
|---|---|
| ADR-1079 が A26（閲覧者の請求書）の確かめ方を改めると書くが、同じ ADR の「影響」は閲覧者の請求書を変えないと書く | ADR-1079 の「改める」から A26 を外し、A26 は変えないと書いた |
| 詳細の表への INSERT を断っていない（古い版・消した版に後から詳細を足せる） | §3-8: 詳細の見張りを INSERT にも掛け、親が今の版のときだけ通す。K25 に試験を足した |
| superseded_by_id が別の地域の行を指す・2つの版が互いを指す輪 | §3-8: 指す先は id が大きく、region と method_type が同じで、今の版の行だけ。K25 に試験を足した |
| 表を丸ごと空にする命令が見張りに当たらない | §3-8: アプリの役に権限が無いこと（根拠の行）を書き、人が直接入る場合と同じ受け入れたリスクとした（ADR-1079） |
| 便 V の移行の試験への登録が K25 に無い | K25 に K17 と同じ登録（_TENANT_LOOP_MIGRATIONS・_REVIEWED）を足した |
| tenant.py の見張りの置き場所を誤読しやすい | §3-8: 表を作る文の後ろに置くと書いた。行は便 V のカードで測る |
| K21 の試験が文字を探すだけ | card-A §2-10 の PG の試験に、実物の請求書の表の列を引いて DENY_COLUMN_RE に当たる列が0個かを確かめる2行を足した。K21 の確かめ方も書き直した |
| 先頭の状態の文が第8版のまま | 第9版と書き直した |

### 19-2. 2回目（2026-11-14・クラウド・判定 REVISE）への対応

file:line と card-A の数はすべて実物と合うと確かめられた。直すべき3件と覚え書きを直した。審査の返事は記録の上で5件目の途中から切れて読めなかったので、5件目以降は3回目の審査で改めて確かめてもらう。

| 指摘 | 対応 |
|---|---|
| 便 V を入れると、既存の試験の形の比べ（test_tenant_issuer_tables_pg.py:259-277）が落ちる | §3-8 の影響と K25 に、流し直しへ便 V の移行を足し、2列・索引・見張りまで比べると書いた（Opus が試験の実物で確かめた） |
| 表を丸ごと空にする命令を受け入れたリスクとした根拠が足りない（アプリは持ち主の役で動きうる。deploy.yml:452-467・database.py:90） | 受け入れたリスクから外し、3表に文ごとの見張りを足して断る形にした。見張りは6つ。既存の試験で振込先の表を空にするものが無いことを確かめた（§3-8） |
| ADR-1079 が ADR-1061 決定6 を範囲を限らずに改める | ADR-1079 の「改める」を「B2B の請求書に限って」と書き直した |
| 覚え書き: 地域を変える直しの決まりが無く、見張りが断ると 500 になる | §3-8: 地域を変えるのも「消す＋足す」。見張りが断ったときは 409 か 422 に置き換える、と登録画面の便へ申し送った |
| （Opus が見つけた）card-A §2-10 の PG の試験が請求書の新しい列を7と数えたまま | 5 に直した（_shape は _NEW_INVOICE_COLUMNS の5列だけを引く） |

## 維持の仕組み

- 関税の条件の正本は tenant_settings.duty_incoterms だけ。額の正本は tenant_duty_rules と中身の表だけ。試算・作成・見積から作成・発行はすべて invoice_totals を通す（K16・K15 の試験で守る）。
- 為替の正本は app_fx_rate_history だけ（K13・K24 の試験で守る）。
- 新しい文字・JSONB の列を足したら、クラウドの見え方の分類を足さないと試験 T10 が落ちる（既存の仕組み）。
- 税率の正本は public.tax_rates だけ（最高管理者の画面で足す）。
- 支払方法の正本は振込先の表と public.tenant_paypal_config だけ。請求書は版の番号だけを持ち、写しを持たない。
- 振込先の版の中身は DB の見張りが変えさせない（K25 の移行の試験で守る）。新しいテナントの形は tenant.py と移行が同じであることを同じ試験で守る。
- 直書きの選択肢が戻ったら K2 の画面の試験が落ちる。
