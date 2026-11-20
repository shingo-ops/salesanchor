# design-v2: 請求書作成画面を見本の「見た目と操作」に合わせる（8部品すべて見本どおり）

状態: 設計案 第10版（Opus 作成 2026-11-17・第7版 2026-11-18・第8版 2026-11-19・第9版 2026-11-20・第10版 2026-11-20）。第10版は R7 のカードを書くために §3-8 を見積の画面の作りの細部（為替の読み先・消す部品・保存の形・試験）まで書き、§8・K16 を足した（新しい PO の決定は無い）。第9版は PO の答え2件（2026-11-20「1」: ボタン名は今のまま・作成のあとは PDF を埋め込まず小さな枠）で §3-6・R6・K15・§11 を書き直した。第8版は R5 のカードを書くときに見つけた「キャンセル」の扱い（§3-6）を書いた。第7版は PO の答え2件（2026-11-18「1」: 単価の為替の直し方 §1-2・在庫表に出ない21商品は別テーマ §8・§11）を書き、§3-8 の LineItem に `price_yen`・`price_edited` を足した（R5 のカードで為替の入れ直しに使う）。PO 承認済みの決定は §1-2 のとおり。設計審査 1回目（クラウドの Opus・2026-11-17 17:31 JST）は REVISE（直すべき4件）。第2版でその4件と覚え書き5件を直した。2回目（2026-11-17 17:37 JST）は REVISE（直すべき1件）。第3版でその1件と覚え書き2件を直した。3回目（2026-11-17 17:41 JST）は REVISE（直すべき1件）。第4版でその1件と覚え書き2件を直した。4回目（2026-11-17 17:45 JST）は APPROVE（覚え書き2件）。第5版で覚え書き1件と、Opus が R1 のカードを書くときに見つけた抜け1件（見積の PDF）を直した（§12）。5回目（2026-11-17 17:49 JST）は APPROVE（覚え書き2件）。第6版でその2件と、審査役が未確認とした詳細画面の表示を確かめて書いた。
基準: origin/main `cbd85f01d`（調査は `337ebbd1b` で行い、下で引く請求書・在庫・送料・部品のファイルは `git diff --stat 337ebbd1b cbd85f01d` で差が0件であることを確かめた）。
根拠: docs/handoff/invoice-create-portfolio/recon.md（前の調べ）と docs/handoff/invoice-create-portfolio/recon-gap.md（Q 番号で指す。基準 `094cae3b0`）、本書 §2 の追加調査（本番は読むだけの道 ADR-1024 で読んだ）。
前の設計: docs/handoff/invoice-create-portfolio/design.md（第9版。便 A・V・B・C/D は本番済み。PR #5542 まで）。本書はその上に重ねる。design.md の決まり（額はサーバー計算・SSOT・振込先の版）は変えない。
対象 ADR: ADR-144（UI の金型）、ADR-067（デザイントークン）、ADR-027（i18n）、ADR-125 D5（FedEx 未連携を隠さない）、ADR-1028（荷姿の表＝重さの正本）、ADR-1061・ADR-1079（振込先）、ADR-072（commit 後の reset）、ADR-1016（即時反映の表。§3-9）、ADR-135・ADR-136（危険な PR）。

## 1. 目的と PO の決定

### 1-1. 目的
- PO の言葉: 「ポートフォリオと全然違うんだけど差分を把握できている？」（2026-11-16）。前の設計の受入れ条件は「見出しの順」しか確かめておらず、見た目と操作が見本と違った（~/kb/04-records/intent/log.md 13件目）。
- 奥の目的: 海外のお客さんへの請求書を、見本と同じ「選ぶだけ」の操作で、迷わず出せる画面にする。
- 本書の受入れ条件は、見た目（カード・2列・3列・色つき合計枠）と操作（選ぶと埋まる・上限で止まる・重ねて出る）を1件ずつ○×で確かめる（§6）。

### 1-2. PO の決定（承認済み。創作ではなく比べるページ claude.ai/artifact/URBKT332sfF6ceEH5NDNWS の記録と質問の答え）
| 番号 | 部品 | PO の選択 | 日時 |
|---|---|---|---|
| p1 | 区切りごとに1枚のカード | 見本どおり | 2026-11-17 03:40Z〜03:41Z（比べるページの記録） |
| p2 | 発送先12欄・2列 | 見本どおり。追加の答え「書き換えない」＝会社の住所から入り、請求書の画面では読むだけ（灰色）。直すのは会社の画面 | 同上・質問の答え |
| p3 | 支払い・送料・合計の3列 | 見本どおり | 同上 |
| p4 | 送料を便ごとに全部並べ、自動で見積もる | 見本どおり | 同上 |
| p5 | 色つきの合計枠 | 見本どおり | 同上 |
| p6 | 商品行（#・カテゴリ・カテゴリで絞る商品検索・状態・在庫上限の数量・重さと値段の自動・初期12行）。見積の画面も同じ行にする | 見本どおり。追加の答え「在庫表の値段を初期値・手で変更可」 | 同上・2026-11-17 質問の答え |
| p7 | 「請求書を発行」で請求書の見た目を重ねて出し、印刷・PDF | 見本どおり。その後 2026-11-20 回答「1」で、ボタン名は今の「請求書を作成」のまま。2026-11-20 回答「1」で、重ねて出すのは PDF の中身でなく小さな枠（「PDF を保存」「詳細へ」「閉じる」）に変えた（§3-6。本番の守りの設定で PDF を画面に埋め込めないため） | 同上・2026-11-20 回答 |
| p8 | 「在庫表から／見積から」の切り替えを無くす | 見本どおり | 同上 |

p6 の追加の答えにより、値段の欄だけは見本と違い「手で直せる」。理由は、在庫表の値段が仕入元の値段に上乗せの無い値段だから（§2-3）。

p6 の2つ目の追加の答え（2026-11-18 PO「1」）: 在庫表の値段は円なので、請求書の通貨が円でないときは為替で直して入れる。直し方は合計の試算と同じ決まり（円の額 ÷ その通貨の rate_jpy、円以外は 0.01 未満を切り捨て。backend/app/services/invoice_totals.py:46-51・:160-171）。通貨を選び直すと、手で直していない行は入れ直す。手で直した行はそのまま。為替の値が無い通貨では単価を空（0）にし、手で打ってもらう。

## 2. 追加の調査（recon-gap に無いもの）

### 2-1. 見本の作り（https://shingo-portfolio.github.io/invoice-tool/ の js/app.js・js/data.js を取得して読んだ。写しは /tmp/CC報告ファイル/invtool/）
- 初期12行・最大20行（app.js:4 `MAX_ROWS = 20, INIT_ROWS = 12`）。行が1行だけのときは消せない（:216）。
- 行の値段と在庫は「商品×状態」ごと（data.js の `variants: { '単品': { price, stock }, 'ケース': {...} }`）。重さは状態で単品/ケースの重さを選ぶ（app.js:95）。
- 数量が在庫を超えると在庫数に戻し「在庫超過（最大: N）」と出す（app.js:169-172）。状態を選ぶと数量が空なら1を入れる（:193）。
- 発送先は12欄（app.js:224 `custName, recipient, phone, email, taxNo, country, addr1, addr2, addr3, city, state, zip`）。
- 発送メモは請求書ごとの自由記入で、請求書の見た目に出る（index.html:56・app.js:313・:326）。クリアで空になる（:233）。
- 送料は便ごとに全部計算して並べる（app.js:106-109）。

### 2-2. 状態と重さ（本番を読むだけで数えた。2026-11-17 14:28 JST）
- 在庫あり（status='in_stock'）は88件・48商品。形（unit）は box 56件・case 6件・空 26件。状態（raw_condition）は shrink・sealed・no_shrink。**単品（バラ）の在庫は0件**。生出力 /tmp/CC報告ファイル/invq/unit.tsv・unit_cond.tsv。
- 在庫表（GET /inventory/aggregated）は、商品×状態の1マスに「最良の1件の値段と数」を出す。集計が拾う状態は "Case"・"Sealed box"・"Damaged sealed box"・"No shrink box" の4つだけ（backend/app/services/inventory_aggregation.py の aggregate_inventory_offers の track1_conditions）。
- 在庫の1行の状態の名前は、軸（unit・seal・damage・grade）から決まる（backend/app/services/inventory_axes.py の resolve_condition_resolution → backend/app/services/condition_vocab.py の axes_to_aggkey）。box＋shrink→"Sealed box"、box＋no_shrink→"No shrink box"、case＋sealed→"Case"、box＋damage→"Damaged sealed box"。それ以外（box＋sealed、case＋shrink、unit が空）は名前が付かず、元の状態の語（"sealed"・"shrink"）に戻る。この語は4つに入らないので、集計で落ちる。grade に値がある行も名前が付かず落ちる（condition_vocab.py の axes_to_aggkey で grade があれば None）。軸（seal・search_cond・grade・damage）がすべて空の行は、axes_to_aggkey を通らず元の状態の語のまま判定される（inventory_axes.py の resolve_condition_resolution）。
- 本番の在庫88件に当てはめると（2026-11-17 17:33 JST、生出力 /tmp/CC報告ファイル/rev1/axes.tsv・shown.tsv）: 在庫表に出るのは **44件・27商品** だけ。落ちるのは box＋sealed 17件、unit 空 26件、case＋shrink 1件。在庫のある48商品のうち **21商品は今の在庫表にも出ない**。今の在庫に出る状態は "Sealed box"・"No shrink box"・"Case" の3つ（"Damaged sealed box" は0件）。
- → 見本の「状態」は、在庫表の状態の列と同じものとして扱う。選択肢はその商品に在庫がある状態だけ。在庫表に出ない21商品は、請求書でも選べない（在庫表と同じ正本を使うため。§8・§11）。
- 重さの正本は荷姿の表 public.product_packagings（ADR-1028。backend/app/services/product_packagings.py:14-19 の対応表）。在庫のある48商品のうち、BOX の重さあり48・CASE の重さあり47（本番 2026-11-17 17:20 JST）。

### 2-3. 値段と在庫数の出どころ
- 商品マスタの値段は 1472 商品のうち 469 だけ、在庫数が入っている商品は1つだけ（本番 2026-11-17）。今の画面はこの1つの値段と在庫数を使っている（recon-gap Q3 / backend/app/services/inventory_search.py:338-339）。
- 状態ごとの値段と在庫数があるのは在庫表だけ。値段は仕入元の値段の最良の1件で、上乗せは無い（backend/app/services/inventory_aggregation.py:263-304。上乗せの計算は無い）。
- PO の答え（2026-11-17）: 在庫表の値段を最初に入れ、手で直せる。

### 2-4. 在庫表の今の形の弱点
- 行の鍵が商品名（series = products.name）で、商品の番号を返さない（backend/app/services/inventory_aggregated_service.py:71・:92-95 ／ backend/app/schemas/inventory_aggregated.py の AggregatedRow）。同じ名前の商品が2つあると1行にまとまる。請求書の明細には商品の番号が要る。

### 2-5. 権限
- 請求書の材料の道は `invoices.create`（backend/app/routers/invoices.py:259-262）。在庫表は `products.view` か `inventory.visibility.*`（backend/app/routers/inventory_aggregated.py:33-40）。送料は `shipping.calculate`（backend/app/routers/shipping.py:388）。
- 見積を作る道は `quotes.create`（backend/app/routers/quotes.py:150）。見積の画面も同じ商品行を使う（§3-8）ので、在庫の道は見積の権限でも通す必要がある。`require_permission` は渡した権限の「どれか1つ」で通す（backend/app/auth/dependencies.py:613-637）。
- 請求書を作る役割が後の2つを持つかは **未確認**（本番の権限の表を読む問い合わせは、読む道の見張りが文中の語を書き込みと判定して止めた。言い換えはしていない）。
- → 本書では、請求書の画面が使う在庫と送料の道を、`invoices.create` で守る請求書側の道として作る（§3-4・§3-5）。中身は既存の関数を呼ぶだけにして、計算を2か所に分けない。

### 2-6. 見積から請求書を作る道
- 見積の詳細画面に「請求書にする」ボタンが既にある（frontend/src/pages/quote-detail/QuoteDetailPage.tsx:88 が POST /invoices/from-quote/{id} を呼ぶ）。p8 で作成画面の切り替えを無くしても、承認済みの見積から請求書を作る道は残る。

### 2-7. 発送メモ
- 請求書ごとの備考 invoices.notes が既にあり、PDF に出る（backend/app/schemas/invoice.py:84 ／ backend/app/services/invoice_renderer.py:430-435）。見本の発送メモも請求書ごとの自由記入なので、invoices.notes を使う。会社の shipping_note（会社に1つの決まり事）は使わない。

## 3. 変更前と変更後

### 3-1. 画面の並び（見本と同じ）
| 順 | カード（p1） | 中身 |
|---|---|---|
| 1 | 発送先 | 顧客の検索（CompanyContactSelector）→ 12欄を2列で読むだけ（p2・§3-2）。「会社の画面で直す」ボタン |
| 2 | 支払いと合計（3列。p3） | 左: 通貨・支払方法・発送メモ／中: 総重量と便ごとの送料の一覧（p4・§3-5）／右: 色つきの合計枠（p5） |
| 3 | 商品一覧 | 行の表（p6・§3-3）。下に「＋行を追加」（20行まで） |
| 4 | 操作 | 「クリア」「請求書を作成」（p7・§3-6） |

- 「在庫表から／見積から」の切り替え（InvoiceCreatePage.tsx:94・:305-320）を消す（p8）。見積からの読み込みの状態と処理も消す。見積から作るのは見積の詳細画面の道（§2-6）。
- 在庫表の画面から選んだ商品を持ってくる道（QuoteHandoffState。InvoiceCreatePage.tsx:24-30）は残す。持ってきた商品は先頭の行から入れる。

### 3-2. 発送先12欄（p2）
| 欄 | 出どころ（会社の住所 company_addresses の届け先の既定。無ければ請求先の既定。今の _fetch_address_snapshot と同じ選び方 invoices.py:66-106） |
|---|---|
| 顧客名 | 会社名（billing_display_name を優先。今と同じ） |
| 受取人 | 住所の name。空なら選んだ担当者の名前 |
| 電話 | telephone |
| メール | 住所の email。空なら担当者の primary_email |
| TAX Number | tax_id |
| 国名 | country_code を国名にした文字。サーバーが国の表 public.countries（GET /countries と同じ表。backend/app/routers/countries.py:25-26）から name を引き、draft-context の `country_name` で返す |
| 住所1・2・3 | address_line_1・2・3 を別々に |
| 都市・州・ZIP | city・state・zip |

- 画面では12欄とも読むだけ（灰色）。値が空の欄は「未登録」と出す。
- サーバー: GET /invoices/draft-context の ship_to・bill_to に `recipient_name`・`email`・`tax_id`・`address_line_1`・`address_line_2`・`address_line_3`・`country_name` を足す（`country_name` は表示だけで写しには入れない）（backend/app/schemas/invoice.py:117-126 の DraftContextAddress）。今の `address`（1と2をつないだ文字）は残す（他の読み手のため）。
- 写し（ship_to_snap・bill_to_snap）にも同じ6項目を足す（invoices.py:66-106）。古い請求書の写しには無いので、読む側は「無ければ空」とする。
- PDF（invoice_renderer.py:513-522・:170-187）は、受取人・住所1〜3・「都市, 州, ZIP」の1行・国・TAX Number・電話・メールを出す。写しに新しい項目が無い古い請求書は、今と同じ `address` の1行を出す（作り直しても古い PDF の見た目が変わらない）。
- 見積の PDF は変えない。見積の PDF の道（invoices.py:1229-1230）も同じ `_fetch_address_snapshot` を呼び、見積の `_to_addr`（invoice_renderer.py:595-606）は写しの tax_id・email を読む。今は写しに tax_id・email が無いので見積の PDF には出ていない。6項目を足すと見積の PDF に TAX とメールの行が増えるため、見積の PDF の道だけは描く前に新しい6項目を写しから除く（除く関数を invoices.py に1つ作り、そこだけで使う）。見積の宛名の作り直しは本書の範囲外（§3-8 は商品行だけ）。
- PDF の新しい並び（住所1〜3を別の行・「都市, 州, ZIP」の行）にするかどうかは、写しに `address_line_1` のキーがあるかで決める（値が空でもキーがあれば新しい並び）。キーが無ければ今の行のまま。新しい並びの材料は請求書の `_to_addr`（invoice_renderer.py:513-524）だけが渡し、見積の `_to_addr`（:595-606）は渡さない。宛名の行を作る `_addr_lines`（:173-191）は請求書と見積で共用だが、見積には材料が来ないので並びは変わらない。
- 請求書の詳細画面（frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:164-174）は写しの `tax_id` を既に読んで「Tax ID:」の行を出す。新しい請求書から、会社の住所に TAX Number があればこの行が出る。PDF と同じ中身なので狙いどおり。詳細画面の並びは本書では変えない（email・住所3 は詳細画面には出ない）。

### 3-3. 商品行（p6）
| 列 | 動き | 出どころ |
|---|---|---|
| # | 行番号（1から） | 画面 |
| カテゴリ | 選ぶ（Select）。選び直すと、その行の商品・状態・数量を空にする | 中分類の表 public.type_master（code・name_ja）。§3-4 の道が返す |
| 商品 | 候補つき検索（AsyncCombobox）。候補はそのカテゴリで在庫のある商品だけ。商品名・英語名・型番で絞る | §3-4 の道 |
| 状態 | 選ぶ（Select）。選択肢はその商品に在庫がある状態だけ。選ぶと数量が空なら1を入れる | §3-4 の道の cells |
| 数量 | 数を打つ。在庫数を超えたら在庫数に戻し「在庫は N まで」と出す | cells の quantity |
| 重さ | 読むだけ。状態が "Case" ならケースの重さ、それ以外は BOX の重さ | 荷姿の表（ADR-1028）。§3-4 の道が返す |
| 単価 | 最初は在庫表の値段（円）を請求書の通貨に為替で直して入れる。手で直せる（PO の答え 2026-11-17・2026-11-18） | cells の price と draft-context の fx_rates |
| 小計 | 数量×単価（画面の表示だけ。合計はサーバー試算のまま） | 画面 |
| × | 行を消す。行が1行だけのときは消せない | 画面 |

- 初期は空の12行。最大20行。
- 明細を保存するときの値: product_id・product_name（商品名）・name_en・condition（状態の名前）・unit（"Case"→case、名前に box を含む→box、pack を含む→pack、それ以外は空）・quantity・unit_price・weight（1個の重さ）。今の InvoiceItemInput の形のまま（backend/app/schemas/invoice.py:28-37）。
- 空の行（商品が選ばれていない行）は送らない。商品を選んだのに状態が無い行があれば発行を止め、その欄に印を付ける（見本 app.js:283-287 と同じ）。
- 重さが登録されていない商品（今は CASE で1商品）は、重さの欄に「未登録」と出し、発行を止める。会社の画面ではなく商品の画面で登録してもらう案内を出す。
- 在庫の上限は画面だけで守る。サーバーは在庫数で止めない（在庫は仕入元の申し出で変わるため。作る時点の在庫で弾くと、画面で選べたのに作れない事故になる）。

### 3-4. 請求書用の在庫の道（新）
- `GET /invoices/draft-inventory?category=<code>`。権限は `require_permission("invoices.create", "quotes.create")`（どちらか1つで通る。見積の画面も使うため。§2-5）。読むだけ。
- 道の登録は `GET /invoices/{invoice_id}`（backend/app/routers/invoices.py:384）より前に置く（後ろだと draft-inventory が番号として読まれ 422 になる）。
- 返す形: `categories: [{code, name_ja}]`（在庫のある中分類だけ・sort_order 順）と `items: [{product_id, name, name_en, mark, work_code, box_weight_kg, case_weight_kg, cells: {状態: {price, quantity}}}]`。
- 中身は在庫表と同じ関数で作る（backend/app/services/inventory_aggregated_service.py の get_aggregated_inventory の流れ）。集計の鍵を商品の番号にした版の関数を同じファイルに足し、今の在庫表の道（GET /inventory/aggregated）の応答は1文字も変えない（試験で固定）。重さは legacy_field_sql（product_packagings.py:41-57）で読む。
- 秘密の列（仕入元名・採用理由）は返さない（今の在庫表と同じ境界）。

### 3-5. 送料の一覧と自動見積もり（p4）
- `POST /invoices/draft-shipping-quotes`。権限 `invoices.create`。入力は company_id と総重量。届け先の国・郵便番号と発送元の国は、サーバーが draft-context と同じ関数で決める（画面からは受けない）。
- 返す形: 今の /shipping/calculate と同じ `ShippingCalcResponse`（backend/app/schemas/shipping.py:107-134）。中身は、静的な表の FedEx 以外の便（calculate_shipping_fee を carrier なしで呼び、carrier が fedex の行を除く。backend/app/routers/shipping.py:264-299）と、FedEx が連携済みなら FedEx のライブ見積もり（同じファイルの _try_fedex_live）を足したもの。
- FedEx の行はライブだけ。静的な表の FedEx の行は、ライブが取れても取れなくても常に出さない。今の決まり（ADR-125 D4・D5 と PO の C1 判断。backend/app/routers/shipping.py:430-437 が「static に落とさず」、backend/tests/test_fedex_rates.py:470-500 が試験で固定）と同じ。FedEx が未連携・失敗なら、FedEx の行は0件で live_error だけ返す（未連携の文は今の calc_shipping と同じ）。これで FedEx の行が二重になることも無い。
- 各行に出所の印（「ライブ」／「静的」）を必ず出す（ADR-125 D6。行の `source` が fedex_live か static か）。
- 画面は、届け先の会社・総重量が変わったときだけ、最後の変更から 800ms 待って呼ぶ。同じ材料ならもう呼ばない。行の一覧から1つ選ぶか「送料を請求しない」を選ぶ。選んだ便は今の ShippingInput（invoice.py:55-72）でそのまま送る。総重量が0のときは呼ばない。
- FedEx の呼び出しの上限: 公式の案内では1プロジェクト10秒に1,400回（developer.fedex.com/api/en-pw/guides/ratelimits.html。2026-11-17 に読んだ）。1枚の請求書を作る間の呼び出しは、総重量を変えた回数（数回）に限られる。1日の上限（Rate API）と1回ごとの費用は **未確認**。そのため K7 で呼び出しの回数を数える。

### 3-6. 作成のあとに出す小さな枠（p7。第9版で書き直し）
- 「請求書を作成」（今のボタン名 `invoices.createBtn`。PO 2026-11-20 回答「1」）を押すと、今の作る道（POST /invoices。下書きで保存。backend/app/routers/invoices.py:609）を1回呼ぶ。今は成功すると詳細画面へ移る（origin/main `d4bea69c1` の InvoiceCreatePage.tsx:184 `navigate(`/invoices/${inv.id}`)`）。R6 ではこの移動をやめ、作成の画面の上に小さな枠（金型 `frontend/src/components/Modal.tsx`）を出す。
- PDF の中身を枠に埋め込まない。根拠（Opus が 2026-11-20 に確かめた）: 本番の守りの設定 nginx/nginx.conf:96 は `default-src 'self'` で `frame-src`・`object-src` を書いておらず、blob の PDF を iframe・object・embed に入れると手元の試しで止められた。守りの設定は変えない（PO 2026-11-20 回答「1」）。印刷のボタンも作らない（PDF を開けないため）。
- 枠の中身: 題「請求書を作成しました」・請求書番号（金型 `ReadOnlyField`。POST の返事の `invoice_number`。作るときに必ず `IN-{id:04d}-01` が入る invoices.py:665）・知らせ（金型 `Callout` info。「下書きで保存しました。送付・確定は詳細画面で行います」）。
- 枠のボタン（金型 `Button`、下段 `footer`）: 「閉じる」（`common.close`。今の「クリア」と同じ `clearAll()` で新しい空の請求書に戻り、枠を閉じる）・「詳細へ」（今の詳細画面 `/invoices/{id}` へ移る）・「PDF を保存」（主ボタン。GET /invoices/{id}/pdf を `api.getBlob` で読み、`<a download>` で保存する）。
- PDF を保存する決め方: 道（origin/main `d4bea69c1` の backend/app/routers/invoices.py:1133・権限 `invoices.view`）は `Content-Disposition: attachment; filename="{invoice_number または IN-{id:04d}-01}.pdf"` で返す（同 :1156・:1183・:1188）。`api.getBlob`（frontend/src/lib/api.ts:203 の requestBlob・:305 の getBlob）は応答の見出しを返さないので、ファイル名は POST の返事の `invoice_number` に `.pdf` を付ける（道が付ける名前 `{invoice_number}.pdf` と同じ。番号の正本はサーバー）。返事の型は `invoice_number: str | None`（backend/app/schemas/invoice.py:210）だが作るときに必ず入る。もし空なら「PDF を保存」を出さない（番号の形 `IN-…` を画面で作り直さない＝正本を2つにしない）。同じ出所の blob の URL を `a[download]` で保存するのは守りの設定に関わらない（MDN: CSP の移動の決まりは form-action・frame-ancestors だけ。Context7 で確かめた）。
- 保存の小さな関数 frontend/src/lib/saveBlob.ts（新規）を新しく作る（blob の URL を作る→a を付けて押す→外す→URL を捨てる）。今は同じ書き方が18ファイルに散らばっているが、R6 ではそれらを書き換えない（別の作業にする）。
- PDF の道の権限は `invoices.view`。作る権限だけで見る権限の無い役割では「PDF を保存」を出さず、「PDF の保存には請求書を見る権限が要ります。必要なら会社の管理者に連絡してください」の知らせ（金型 `Callout` info）を出す。権限は今の `usePermissions()` で読む（新しい取り方を作らない）。
- PDF の読み込みに失敗したら、枠の中に知らせ（金型 `Callout` warning。「PDF を保存できませんでした。少し待ってもう一度お試しください」（詳細画面の PDF のボタンは下の別件のとおり今は動かないので案内しない））を出し、枠は閉じない。
- 枠は背景を押しても閉じない（`dismissOnOverlay={false}`。作ったことを見落とさないため）。Esc と右上の×は金型どおり「閉じる」と同じ動き。
- 保存せずに PDF だけ作る新しい道は作らない（書かない道の権限と記録の決まりを新しく決めずに済む。recon-gap Q4 の未確認を避ける）。
- 別件（R6 では直さない）: 今の詳細画面の PDF のボタン（InvoiceDetailPage.tsx:154-156・QuoteDetailPage.tsx:97）は `window.open('/api/invoices/{id}/pdf')` で、本番の道は `/api/v1/...` のため 404 になる。別のテーマとして PO に伝える。
- 「クリア」は確認を出してから、12行・発送先・送料・メモを空に戻す。
- 今の画面の「キャンセル」（請求書の一覧へ戻る。origin/main の InvoiceCreatePage.tsx:518）は操作のカードにそのまま残す。見本に無いが、消すと一覧へ戻る道が減るため（R5 のカードを書くときに Opus が見つけた。第8版）。

### 3-7. 新しく登録する金型（ADR-144。PO が p1・p3・p5 で見本どおりを選んだことで新設を承認済み）
| 金型 | 中身 | 置き場所 |
|---|---|---|
| SectionCard | 見出しつきのカード。Card（variant container）の中に見出し（--font-lg）と右上の操作の置き場 | frontend/src/components/SectionCard.tsx・.css・.stories.tsx |
| ReadOnlyField | 読むだけの欄（ラベル＋灰色の値。空なら「未登録」） | frontend/src/components/ReadOnlyField.* |
| ThreeColumn | 3列の並び（狭い画面では縦1列）。TwoColumn と同じ作り | frontend/src/components/ThreeColumn.* |
| TotalsBox | 色つきの合計枠（小計・送料・税または関税・合計。合計は大きい字） | frontend/src/components/TotalsBox.* |
- 色・余白・角丸・字の大きさはすべて tokens.css の変数。足す変数があれば tokens.css に足す（ADR-067）。色の直値・生の select・生の input は使わない。
- 各金型に Storybook の話（明るい・暗い・狭い画面）を付ける。docs/CC_UI_GOVERNANCE.md の目録に1行ずつ足す。

### 3-8. 見積の画面（p6 の「見積の画面も同じ行」）
- 商品行の表を共通の部品 `LineItemsTable`（frontend/src/pages/quote-create/ か components/ に置く。置き場は実装カードで決める）にし、請求書と見積の両方で使う。
- 見積の画面で変わるのは商品行の表だけ。見積の送料（FedExRateModal）・保存の道は変えない。
- LineItem（frontend/src/pages/quote-create/quoteDraft.ts:8-29）には、画面だけで使う `category_code`・`stock_limit`・`price_yen`（在庫表の円の値段）・`price_edited`（単価を手で直したか。通貨を選び直したとき、直していない行だけ入れ直す）を足す（どれも任意。保存には送らない）。

#### 3-8-1. R7 の作り（第10版。基準 origin/main `4209886d9`）
- 今の見積の画面（frontend/src/pages/quote-create/QuoteCreatePage.tsx・297行）は、自由記入の行の表（:170-252）・「行を追加」（:254-256 `quote-add-blank`）・検索で足す欄 InventorySearchBar（:258-264）・在庫0の注意（:206-214）を持つ。これを請求書と同じ `LineItemsTable`（frontend/src/pages/quote-create/LineItemsTable.tsx。請求書は frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:249-257 で使う）に替える。
- 行の初めは請求書と同じ `handoffRows(handoff)`（frontend/src/pages/quote-create/lineItems.ts:42-51。在庫表の画面から持ってきた商品が先頭の行に入り、12行まで空の行）。今の `buildInitialItems`（quoteDraft.ts:116-128）は画面から外す。quoteDraft.ts は変えない（K16 で quoteDraft.test.ts を緑のまま残すため。`buildInitialItems`・`blankItem`・`weightForUnit` は試験と lineItems.ts からだけ使われる形になる。片付けは別の作業）。
- 在庫は請求書と同じ `useDraftInventory()`（GET /invoices/draft-inventory。権限は invoices.create か quotes.create・backend/app/routers/invoices.py:384-388。K23）。
- 為替: 見積には請求書の draft-context が無い。今ある GET /api/v1/fx-rates/{currency}（backend/app/routers/fx_rate_admin.py:61-95。ログインだけで読める。public.app_fx_rate_history の最新の1行を返し、無ければ 404）を `useApiQuery`（frontend/src/lib/query/apiQuery.ts:52-72）で読む。請求書の draft-context の為替（backend/app/services/invoice_totals.py:369-377 `load_latest_fx`）も同じ表を読むので、正本は1つのまま。円のときは読まない（`enabled: currency !== "JPY"`）。答えの `rate_jpy` が 0 より大きいときだけ使い、読めない・404 のときは為替なし（単価 0。§8）。通貨を選び直したら請求書と同じ `reconvertPrices`（lineItems.ts:166-172）で手で直していない行だけ入れ直す。
- 通貨の選び肢（JPY・USD・EUR、既定 USD。:158-164）・取引先と担当者・メモ・送料（FedEx の見積もり）・税・合計・総重量・「キャンセル」「下書き保存」は変えない。総重量は `totalWeight(rows)`（lineItems.ts:196-199）、小計の和は商品の入った行の `rowSubtotal`（lineItems.ts:202-204）の和にする。FedEx の枠に渡す重さも `totalWeight(rows)`。
- 保存の前の点検: 担当者が無ければ今と同じ文。`allRowsReady(rows)`（lineItems.ts:190-193）が偽なら、行に印を出し（`showErrors`）、今と同じ「quotes.itemsRequired」の文を出して送らない。
- 送る形: POST /quotes の `items` は `filledRows(rows).map(toInvoiceItem)`（lineItems.ts:185-187・207-218）。中身の8項目（product_id・product_name・name_en・condition・unit・quantity・unit_price・weight）は今の見積の形（backend/app/schemas/quote.py:27-36 QuoteItemInput）と同じ。サーバーは変えない。
- 消すもの: 自由記入の表・addItem・removeItem・updateItem・appendFromSearch・InventorySearchBar の読み込み・在庫0の注意。InventorySearchBar の部品そのもの（frontend/src/components/InventorySearchBar.tsx と Storybook）は残す（使う画面が無くなるが、部品の片付けは別の作業）。使われなくなる文言キー4つ（quotes.productNamePlaceholder・quotes.addItem・quotes.removeItem・inventory.search.zeroStockWarning。ほかで使う所は0件と Opus が 2026-11-20 に数えた）は R7 では消さない（文言の片付けは別の作業。CI の文言の検査は「足りないキー」だけを見る）。
- `LineItemsTable` の「×」（行を消す。LineItemsTable.tsx:234-243）と「行を追加」（:263-271）の Button に `type="button"` を足す。見積の画面は表を `<form>`（QuoteCreatePage.tsx:145）の中に置き、Button（frontend/src/components/Button.tsx）は type を決めないため、そのままだと押すと見積の保存が走る。請求書の画面は `<form>` を持たないので動きは変わらない。表の中のほかのボタン（AsyncCombobox・Select・DataTable）は既に `type="button"`（Opus が 2026-11-20 に読んだ）。
- 在庫表の画面からの引き継ぎで `draft`（往復のときの見積の下書き）を送る所は今は無い（送るのは ProductsPage.tsx:142 の `selectedProducts` だけ。Opus が 2026-11-20 に数えた）。取引先・通貨・メモなどを `draft` から読む今の書き方（QuoteCreatePage.tsx:39-47）は残し、行は `handoffRows` だけで作る。
- 試験: frontend/src/components/CommerceSubmitButtonMigration.test.tsx の見積の4本（「行を追加」・名前0/単価0/数量0・送る形・空の送料）を在庫の行の形に書き直す。frontend/src/components/CommerceNavigationButtonMigration.test.tsx は為替の道の受け答えを足すだけ。frontend/tests-e2e/quote-create-inventory-search.spec.ts（消える検索欄と自由記入の行を見る画面の試験）は R7 では触らず、後の片付けで消す。CI では流れていない: 全部の画面の試験を流す仕事は .github/workflows/e2e.yml:294 `if: false` で止まっていて、動いているのは :226 `npm run test:e2e:vl`（visual-language の試験だけ）。止めた仕事を再開する前に消す必要がある（再開すると必ず落ちる）。R7 で消さないのは、指示書の検査 scripts/card-lint.sh L11 が手順の中の消す命令を止めるため（2026-11-20 Opus 判断）。

### 3-9. 即時反映の表（ADR-1016）
- 新しい道2つは読むだけ（書かない）。即時反映の表に載せる対象ではない。実装カードで、その表の検査（CI）が通ることを確かめる。

## 4. 便の分け方（1便1PR。順に作る）
| 便 | 中身 | 主なファイル | 危険なパス |
|---|---|---|---|
| R1 | 発送先12欄のサーバー側（draft-context と写しに6項目・PDF の宛名） | backend/app/schemas/invoice.py・routers/invoices.py・services/invoice_renderer.py・試験 | 無し（移行なし） |
| R2 | 請求書用の在庫の道（§3-4） | services/inventory_aggregated_service.py・routers/invoices.py（または新ファイル）・schemas・試験 | 無し |
| R3 | 請求書用の送料一覧の道（§3-5。静的な表から FedEx を常に除く） | routers/invoices.py・routers/shipping.py（今の calc_shipping の FedEx の分岐と未連携の文を1つの関数に出し、calc_shipping と新しい道の両方から呼ぶ。分岐を2か所に書かない。今の /shipping/calculate の応答と 422 は変えない。test_fedex_rates.py が緑のまま）・試験 | 無し |
| R4 | 金型4つ（§3-7） | frontend/src/components/*・tokens.css・docs/CC_UI_GOVERNANCE.md | 無し |
| R5 | 請求書の作成画面の作り直し（§3-1〜§3-3・§3-5 の画面・p8） | frontend/src/pages/invoice-create/*・LineItemsTable・locales | 無し |
| R6 | 作成のあとの小さな枠（§3-6） | frontend/src/pages/invoice-create/*・frontend/src/lib/saveBlob.ts（新規）・ja.json・en.json | 無し |
| R7 | 見積の画面を同じ商品行に（§3-8） | frontend/src/pages/quote-create/* | 無し |
- どの便も migrations/・deploy.yml・本番の scripts/ に触らない。触ることになったら止めて PO に戻す（ADR-135/136）。
- R1〜R3 は互いに独立。R5 は R1・R2・R3・R4 の後。R6 は R5 の後。R7 は R5 の後。

## 5. 触らない範囲
- 額の計算（invoice_totals）・税・関税・振込先の版・作る道の検査（design.md 第9版のまま）。
- 今の在庫表の道 GET /inventory/aggregated と在庫表の画面の応答と見た目。
- /shipping/calculate の応答と権限。見積の画面の送料の部品。
- 会社の画面（住所を直す場所）。
- 決済手数料（便 E。別の設計）。

## 6. 受入れ条件（見た目と操作を1件ずつ）
| 番号 | 基準 | 検証方法 |
|---|---|---|
| K1 | 画面に4枚のカードが「発送先→支払いと合計→商品一覧→操作」の順に出て、各カードに見出しがある | 画面の試験（vitest・Testing Library）で SectionCard 4つと見出しの順を確かめる。本番は PO の目視 |
| K2 | 発送先の12欄が2列で出て、12欄とも入力できない（読むだけ） | 画面の試験: 12個の ReadOnlyField があり、input・textarea が0個。2列の並びの class を確かめる |
| K3 | 顧客を選ぶと、会社の住所の受取人・メール・TAX Number・住所3・都市・州・ZIP が12欄に入る | サーバー試験: draft-context が6項目を返す。画面の試験: 返った値が各欄に出る |
| K4 | 発行した請求書の PDF に、受取人・住所1〜3・都市/州/ZIP・TAX Number・メールが出る。古い請求書の PDF は今と同じ | サーバー試験: 新しい写しで描いた PDF の文字に各値がある。古い写し（6項目なし）で描いた PDF の文字が変更前と同じ。見積の PDF の道で、新しい6項目のある住所でも描く写しに6項目が無い（見積の PDF の文字が今と同じ）。見積から作った請求書（invoices.py:441-442）も同じ写しを保存するので、その PDF にも新しい行が出る（狙いどおり） |
| K5 | 「支払いと合計」が3列（左: 通貨・支払方法・発送メモ／中: 総重量・送料一覧／右: 合計枠）。狭い画面では縦1列 | 画面の試験で ThreeColumn の3つの子の中身を確かめる。Storybook の狭い画面の話 |
| K6 | 総重量が入ると、操作なしで便ごとの送料が全部並ぶ。FedEx の行はライブだけで、静的な FedEx の行はどの場合も無い。各行に「ライブ」か「静的」の印がある。FedEx 未連携・失敗なら、その旨が出て FedEx の行は0件 | サーバー試験: ライブありで FedEx の static 行が0件・FedEx の fedex_live 行あり・DHL と UPS の static 行あり。未連携・失敗なら live_error あり・FedEx の行（static も fedex_live も）0件・DHL と UPS の static 行あり。画面の試験: 重さが変わったあと 800ms で1回だけ呼び、一覧と印が出る |
| K7 | 同じ材料では送料の道を2回呼ばない。重さを3回変えたら呼び出しは最大3回 | 画面の試験で呼び出しの回数を数える。本番は反映後に1週間、送料の道のログの数を数えて、作った請求書1枚あたりの回数を出す（目安10回以下） |
| K8 | 合計枠が色つき（トークンの色）で、小計・送料・税または関税・合計を出す。合計の字が一番大きい | TotalsBox の試験と Storybook。色の直値0件（CI の UI の検査） |
| K9 | 商品一覧の初期は12行。「＋行を追加」で20行まで増え、21行目は増えず案内が出る。1行のときは×で消せない | 画面の試験 |
| K10 | カテゴリを選ぶと、商品の候補がそのカテゴリの在庫のある商品だけになる | サーバー試験: category で絞った items。画面の試験: 候補の数が絞った数と同じ |
| K11 | 商品を選ぶと、状態の選択肢がその商品に在庫のある状態だけになる。状態を選ぶと、重さ・単価・在庫上限が入る | 画面の試験 |
| K12 | 数量に在庫より大きい数を打つと、在庫数に戻り「在庫は N まで」と出る | 画面の試験 |
| K13 | 重さの欄は打てない。単価の欄は打てる（初期値は在庫表の値段） | 画面の試験: 重さに input が無い・単価の input の初期値 |
| K14 | 「在庫表から／見積から」の切り替えが画面に無い。見積の詳細画面の「請求書にする」は今のまま動く | 画面の試験（切り替えのボタン0個）。QuoteDetailPage の既存の試験が緑 |
| K15 | 「請求書を作成」で作成が1回だけ行われ、詳細画面へは移らず、小さな枠に請求書番号と「PDF を保存」「詳細へ」「閉じる」が出る。「PDF を保存」で PDF の道が1回呼ばれ `{請求書番号}.pdf` で保存される。「詳細へ」で詳細画面へ移る。「閉じる」で空の請求書に戻る。見る権限が無い役割では「PDF を保存」が出ない。PDF の失敗では知らせが出て枠は残る | 画面の試験: POST /invoices が1回・場所が変わらない・枠と3つのボタン／getBlob が `/invoices/11/pdf` で1回・a の download が `IN-0011-01.pdf`／場所が `/invoices/11`／12行が空・枠が消える／invoices.view 無しでボタン0個／getBlob 失敗で warning が出る |
| K16 | 見積の作成画面の商品行が、請求書と同じ列（#・カテゴリ・商品・状態・数量・重さ・単価・小計・×）になり、見積の保存は今のまま動く（R7 の内訳: (a) 開くと空の行が12行・「行を追加」で13行 (b) 在庫表の画面から持ってきた商品で状態を選ぶと、USD は在庫表の円の値段 ÷ 為替（小数2けた切り捨て）・重さが入る (c) 状態の無い行・単価0の行があると送らず「quotes.itemsRequired」の文 (d) 送る items は8項目で、空の行は送らない (e) 失敗のあと押し直すと同じ形で送り、成功で見積の一覧へ (f) 送料・税・メモが空なら null (g) 自由記入の欄と検索で足す欄が画面に無い） | CommerceSubmitButtonMigration.test.tsx の見積の試験（(a)〜(f)）・(g) は同じ試験で `quote-add-search` と `quote-item-row-` が0件。quoteDraft.test.ts が緑。本番は配った画面の束に見積の画面の新しい印が入ったことを Opus が数える |
| K17 | 今の在庫表の道 GET /inventory/aggregated の応答が変わらない | サーバー試験で変更前と同じ応答を固定 |
| K18 | 画面の文字はすべて t()。ja.json と en.json に同じキー。色の直値・生の select/input が0件 | CI（i18n・UI の検査） |
| K19 | 「クリア」を押すと確認が出る。はいで、12行・発送先・送料の選択・発送メモが空に戻る。いいえなら何も変わらない | 画面の試験 |
| K20 | 商品を選んで状態を選んでいない行があると、「請求書を発行」で作成の道が呼ばれず、その行の状態の欄に印が付く | 画面の試験: POST /invoices が0回・印の class |
| K21 | 重さが登録されていない商品を選ぶと、重さの欄に「未登録」と出て、「請求書を発行」で作成の道が呼ばれない | 画面の試験 |
| K22 | 発送メモに書いた文字が、発行した請求書の PDF に出る。「クリア」で空になる | サーバー試験: notes 入りで描いた PDF の文字にメモがある。画面の試験: クリア後に空 |
| K23 | 見積の作る権限だけの役割でも、見積の画面の商品行で在庫の候補が出る（403 にならない） | サーバー試験: quotes.create だけの利用者で draft-inventory が 200 |

## 7. 代わりの案と選んだ理由
- 在庫の道を請求書側に作る（選んだ）／画面から GET /inventory/aggregated と /shipping/calculate を直接呼ぶ（選ばない）: 請求書を作る役割が在庫と送料の権限を持つか未確認（§2-5）。権限の食い違いで画面が動かない事故を避ける。中身は同じ関数なので計算は1か所のまま。
- 作ってから PDF を重ねる（選んだ）／保存せずに PDF を作る新しい道（選ばない）: 書かない道の記録の決まりを新しく作らずに済む。見本でも「発行」は発行の操作。
- 値段は在庫表の値段を初期値にして直せる（PO の答え）。
- 在庫の上限は画面だけ（選んだ）／サーバーでも止める（選ばない）: §3-3 の理由。

## 8. 弊害と対処
| 弊害 | 対処 |
|---|---|
| 在庫のない商品は請求書に入れられなくなる（今は検索で何でも入る）。見積の画面も同じ（R7） | 見本どおりの決定。在庫表に無い商品の請求は、在庫を登録してから。反映後の1週間、「商品が見つからない」という声を PO に確かめる |
| 在庫はあるのに今の在庫表に出ない21商品（box＋sealed・unit 空・case＋shrink。§2-2）は、請求書でも選べない | 請求書の道だけで拾うと、在庫表と請求書で正本が2つになる（禁止）。在庫表の集計の直しは別のテーマとして PO に判断をもらう（§11）。**PO 2026-11-18 回答「1」: 画面の組み込み（R5）を先に進め、21商品は在庫表の集計を直す別のテーマとして後で直す。** それまで請求書で選べるのは在庫表に出る27商品だけ |
| 請求書・見積を作る権限だけの役割（在庫表の権限 products.view・inventory.visibility.* が無い役割）にも、在庫の値段と数が見えるようになる。見える範囲は、選んだ中分類の在庫のある全商品の、状態ごとの値段・数と、重さ・作業コード（§3-4 の items と同じ） | 単価の初期値を在庫表の値段にする PO の決定（§1-2）に必要。仕入元の名前と採用の理由は返さない（§3-4）。どの役割が該当するかは R2 のカードで役割の表を読んで数え、0でなければ PO に伝えてから R2 を出す |
| FedEx の自動見積もりで呼び出しが増える | §3-5 の待ちと同じ材料なら呼ばない作り。K7 で数える。1日の上限は未確認のまま見張る |
| 見積の画面の行も変わる | R7 を別の便にし、見積の保存の試験を緑にしてから出す |
| 見積で EUR を選ぶと、単価が 0 で入り、手で打つまで保存できない | 本番の為替の表（public.app_fx_rate_history）にある通貨は USD だけ（96行・最新 2026-11-19 21:00 UTC。Opus が 2026-11-20 に読む道で数えた）。EUR は 404 で為替なし → 単価 0 の印が出る。単価の欄は手で直せる（請求書と同じ）。本番の見積は USD の1件だけで、EUR の見積は0件（同じ日に数えた）。通貨の選び肢は変えない（R7 は商品行だけを替える） |
| 見積の画面に、在庫表に無い商品を自由に書けなくなる | 上の1行目と同じ（見本どおりの決定）。今の本番の見積は1件だけ |
| 古い請求書の PDF の見た目 | 写しに新しい項目が無いときは今の1行の住所を出す（K4） |
| 同じ名前の商品が在庫表で1行にまとまる今の弱点 | 請求書の道では商品の番号で分ける。在庫表の画面は今のまま（別のテーマ） |

## 9. 外部・過去事例の参照と我々への応用
- 見本そのもの（PO のポートフォリオ。2026-11-17 に js を読んだ）が目指す形。数値の効果を示す外部事例は使わない。理由: 今回の目的は「PO の見本と同じ見た目と操作」で、効果の測り方は §6 の○×で足りる。
- FedEx の呼び出しの上限は公式の案内（§3-5）だけを使った。

## 10. 維持の仕組み
守り手: scripts/check-ui-governance.js（色の直値・生の部品を CI で止める）と、K1〜K23 の試験（CI で毎回走る）
- 金型4つは目録（docs/CC_UI_GOVERNANCE.md）と Storybook に載せる。CI の UI の検査（scripts/check-ui-governance.js）が直値と生の部品を止める。
- 受入れ条件 K1〜K23 は試験として残し、CI で毎回走る。
- 本番の反映ごとに、PO の目視の手引き（見本と並べて見る点 8つ）を渡す。

## 11. 未確認（設計合格の前に決めること・実装で確かめること）
- 請求書を作る役割の在庫・送料の権限（§2-5）。本書は請求書側の道を作るので、この答えに左右されない。
- FedEx の Rate API の1日の上限と費用（§3-5）。K7 で数える。
- 状態の名前: 本番の今の在庫で出るのは3つ（§2-2）。R2 の試験は集計が拾う4つ全部で確かめる。
- **決定済み（PO 2026-11-18 回答「1」）**: 在庫はあるのに在庫表に出ない21商品（§2-2）。画面の組み込み（R5）を先に進め、21商品は在庫表の集計を直す別のテーマとして後で直す。本書の作り（在庫表と同じ正本を使う）は変わらない。別テーマは tasks/todo.md に登録する。
- **決定済み（PO 2026-11-20 回答「1」）**: ボタン名は今の「請求書を作成」のまま（作られるのが下書きのため）。
- **決定済み（PO 2026-11-20 回答「1」）**: 作成のあとは PDF を埋め込まず、小さな枠に「PDF を保存」「詳細へ」「閉じる」を出す。印刷のボタンは作らない。本番の守りの設定は変えない（§3-6）。

## 12. 設計審査の記録
| 回 | 日時 | 判定 | 指摘と直したところ |
|---|---|---|---|
| 1 | 2026-11-17 17:31 JST（クラウドの Opus・読むだけ） | REVISE | 直すべき4件: (1) 見積の権限で在庫の道が 403 → §2-5・§3-4・K23 (2) FedEx の行が二重・出所の印が無い → §3-5・K6 (3) 出ない在庫の説明が無い → §2-2・§8・§11（審査は「unit 空 26件が出ない」とした。Opus が本番に当てはめ直し、出ないのは44件・21商品と数え直した） (4) クリア・状態の未選択・重さ未登録・発送メモの受入れ条件が無い → K19〜K22。覚え書き: PDF は blob で読む（§3-6）・道の登録順（§3-4）・国名の引用先（§3-2）・ボタン名（§11）・見積でも在庫外は入らない（§8） |
| 2 | 2026-11-17 17:37 JST（クラウドの Opus・読むだけ） | REVISE | 直すべき1件: FedEx 未連携のとき静的な FedEx の行を残すと書いたのは、今の決まり（ADR-125 D5・PO C1 判断・test_fedex_rates.py）と逆 → §3-5・K6・R3 で「FedEx はライブだけ」に直した。覚え書き: grade あり・軸が全部空の行の扱い → §2-2 に追記。在庫の値段と数が見える役割が広がる → §8 に追記。1回目の4件・覚え書き5件は直ったと確認された |
| 3 | 2026-11-17 17:41 JST（クラウドの Opus・読むだけ） | REVISE | 直すべき1件: §8 の追記が「選んだ商品の値段と数だけ」と書き、§3-4 の道（中分類ごとに在庫のある全商品を返す）より見える範囲を小さく書いていた → §8 を §3-4 と同じ範囲に直した。覚え書き: 冒頭の版の表記 → 第4版に直した。R3 で FedEx の分岐を2か所に書く恐れ → §4 の R3 の行に「1つの関数に出して両方から呼ぶ」と書いた。2回目の1件と覚え書き2件は直ったと確認された |
| 4 | 2026-11-17 17:45 JST（クラウドの Opus・読むだけ） | APPROVE | 覚え書き2件: R3 で今の /shipping/calculate の動きを変えない決まりが無い → §4 の R3 の行に書いた。§8 の見える項目に商品名などが並んでいない → 「§3-4 の items と同じ」で通じるため直さない。審査のあと Opus が R1 のカードを書くときに、見積の PDF も同じ写しを使い、6項目を足すと見積の PDF に TAX とメールの行が増えることに気づいた → §3-2 に「見積の PDF の道では6項目を除く」、K4 に確かめ方を足した |
| 5 | 2026-11-17 17:49 JST（クラウドの Opus・読むだけ） | APPROVE | 覚え書き2件: 宛名の行を作る関数は請求書と見積で共用なので、新しい並びに切り替える決め方を書く → §3-2 に「写しに `address_line_1` のキーがあるか」で決め、材料は請求書の `_to_addr` だけが渡すと書いた。見積から作った請求書にも新しい行が出ることが書かれていない → K4 に足した。未確認1件（詳細画面がキーの増えた写しをどう出すか）は Opus が InvoiceDetailPage.tsx:164-174 を読んで §3-2 に書いた |
