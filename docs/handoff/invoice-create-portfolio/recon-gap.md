# 請求書作成画面 見本とのギャップ調査（recon-gap）

- 基準: origin/main `094cae3b039c37334f48ba8cd8331e1fe2493177`（git fetch origin main 後に確認）
- 役割: 調査役（読むだけ）。本番・DB・secret・GitHub 設定には触れていない。
- 根拠の書き方: 以下 `パス:行`。パスは origin/main のリポジトリ相対のフルパス。
- 見本 https://shingo-portfolio.github.io/invoice-tool/ は、この環境からは**未確認**（見本の中身は依頼文の記述を前提にした）。
- 実行前検査 `./scripts/dev/executor-preflight.sh` はこの環境で FAIL（GitHub API 不達・gh 名義切替不可）。調査は読み取りのみなので続行。
- 既存の下調べ（docs/handoff/invoice-create-portfolio/design.md・recon.md）は参考にとどめ、事実は下のコードの行だけを根拠にした。

---

## Q1 発送先12欄

### 事実

- 住所の正本は `company_addresses`（billing / delivery × 拠点）。列は branch_name・name・email・telephone・tax_id・address_line_1〜3・city・state・zip・country_code・is_default。 migrations/030_create_company_contact_subtables.sql:40-59 ／ backend/app/schemas/company.py:53-71
- 会社の列: name・name_en・billing_display_name・payment_recipient_name・fedex_account・shipping_note。 migrations/028_create_companies.sql（`name VARCHAR(255) NOT NULL` ほか） ／ backend/app/schemas/company.py:11
- 担当者の列: display_name・surname・given_name・primary_email。 backend/app/routers/invoices.py:147（draft-context 内の SELECT）
- 請求書に「写し」を残す元は `_fetch_address_snapshot`。写しに入る項目は company_name・billing_display_name・label・postal_code・address（address_line_1 と 2 を空白でつなぐ）・city・state・country・phone。 backend/app/routers/invoices.py:66-106
- 作成時に写しを書く: ship_to_snap・bill_to_snap を INSERT。 backend/app/routers/invoices.py:538-541・:577-578（`create_invoice` は :516。見積から作る道は :441-444・:473）
- GET /invoices/draft-context が返すのは `ship_to`・`bill_to`（上の写しと同じ形）・`contact_name`・`contact_email`・`issuer_region`・`origin_country_code`・`destination_country_code`・`destination_postal_code`・通貨・為替・支払方法・税率・incoterms。 backend/app/schemas/invoice.py:117-158 ／ backend/app/routers/invoices.py:259-342
- PDF の宛名は写しから `company_name`（billing_display_name 優先）・`contact_name`・`address`・`country`・`tax_id`・`phone`・`email` を読む。 backend/app/services/invoice_renderer.py:513-522 ／ 描画の行 :170-187（Tax ID は `Tax ID:` 行）
- PDF に出る住所は `address` と `country` だけ。city・state・postal_code は読まない。 backend/app/services/invoice_renderer.py:513-522
- 画面側の住所表示は `addressLine`（postal_code・state・city・address・country を空白でつなぐ 1 行）。 frontend/src/lib/invoiceDraftContext.ts:190-193

### 12欄ごとの対応

| 見本の欄 | DB の表・列 | draft-context が返すか | 請求書の表・PDF に残るか |
|---|---|---|---|
| 顧客名(検索) | companies.name / billing_display_name（028） | ship_to.company_name・billing_display_name は返す（schemas/invoice.py:117-126）。検索は draft-context ではなく CompanyContactSelector が `/companies?per_page=100` を取る（frontend/src/components/CompanyContactSelector.tsx:107） | 写しに company_name・billing_display_name が残る（invoices.py:94-97）。PDF に出る（invoice_renderer.py:514） |
| 受取人氏名 | contacts.display_name / surname / given_name、company_addresses.name | contact_name は返す。company_addresses.name は返さない（invoices.py:156-159・:94-106） | 写しに contact_name も name も入らない。PDF は snap の contact_name を読むが、写しが書かないので空 → **残らない**（invoices.py:94-106 と invoice_renderer.py:515 の食い違い） |
| 電話 | company_addresses.telephone | ship_to.phone は返す（schemas/invoice.py:126） | 写しに phone が残り PDF に出る（invoices.py:105 ／ invoice_renderer.py:519） |
| メール | company_addresses.email、contacts.primary_email | contact_email は返す。住所側 email は返さない | 写しに email は入らない → PDF の Email 行は空（invoices.py:94-106 ／ invoice_renderer.py:520） |
| TAX Number | company_addresses.tax_id（030:48） | **返さない**（DraftContextAddress に tax_id 無し。schemas/invoice.py:117-126） | 写しに入らない → PDF の Tax ID 行は空（invoices.py:94-106 ／ invoice_renderer.py:518） |
| 国名 | company_addresses.country_code（ISO2） | ship_to.country は返す（コード） | 写しに country が残り PDF に出る。国名（英語名など）への変換は**未確認** |
| 住所1・2・3 | address_line_1・2・3（030:49-51） | address は 1 と 2 をつないだ 1 文字列。3 は**返さない**（invoices.py:99-101） | 写しは同じ 1 文字列。3 は**残らない** |
| 都市 | city | ship_to.city は返す | 写しに残る。PDF は読まない（invoice_renderer.py:513-522） |
| 州 | state | ship_to.state は返す | 写しに残る。PDF は読まない |
| ZIP | zip | ship_to.postal_code は返す | 写しに残る。PDF は読まない |

### 未確認

- 画面側で受取人氏名・メール・TAX Number・住所3 を編集して請求書に残す道（InvoiceCreate に宛名の欄は無い。backend/app/schemas/invoice.py:75-85）。現状は会社の画面で登録した値を読むだけの設計（frontend/src/pages/invoice-create/InvoiceShipToSection.tsx:4）。
- DraftContextAddress を広げたとき、既存の写し（JSONB）の古い行との整合。
- 国コード → 国名の変換の正本表（CountryCombobox は別名の一覧を持つが、請求書の PDF が使うかは未確認。frontend/src/components/CountryCombobox.tsx:24）。

---

## Q2 送料・運送会社・支払方法・通貨

### 事実

- POST /shipping/calculate は**複数の便を返しうる**。応答は `results` の配列＋`cheapest`。 backend/app/schemas/shipping.py:107-134 ／ backend/app/routers/shipping.py:386-447
  - carrier="fedex": FedEx Rates API のライブ見積もり。サービスごと（service_type・service_name・transit_days・surcharges）に複数行。 backend/app/routers/shipping.py:312-383
  - carrier 未指定: 静的表 `shipping_zones` × `shipping_rates` を国コード・重量で引き、**会社をまたいで複数行**（fedex / dhl / ups を含む）。 backend/app/routers/shipping.py:266-309・:440-441（コメント :274 に「FedEx/DHL/UPS全社を返す」）
  - FedEx が未連携のときは静的に落とさず `live_error` だけ返す（ADR-125 D5）。 backend/app/routers/shipping.py:434-438
  - `origin_country_code` は carrier="fedex" で必須（422）。 backend/app/routers/shipping.py:410-414
- 今の画面は FedExRateModal（ボタンで開く）。開いたあと「見積を取る」で初めて /shipping/calculate を carrier="fedex" で呼ぶ。開いただけでは呼ばない。 frontend/src/components/FedExRateModal.tsx:128-146 ／ frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx:205-225
- 画面を開いたとき自動で呼べるか: 呼び出しに必要な材料（届け先の国・郵便番号・総重量・発送元の国）は draft-context と明細から画面で揃う（invoices.py:183-185 ／ InvoiceCreatePage.tsx:215）。**呼ぶ道は技術的に存在する**。ただし「自動で呼んでよい」かは次の通り**未確認**。
- 外部 API・費用・回数制限の記述: コードに FedEx 向けの**呼び出し回数の制限や費用の記述は見つからなかった**（backend/app/services/fedex_rates.py の timeout は connect 3s / read 7s のみ :15。OAuth トークンはプロセス内キャッシュ :152-175）。ADR-125 本文にも制限・費用の文言は無し（docs/adr/ADR-125-fedex-rates-stage1.md を「制限・上限・クォータ」で検索して 0 件）。FedEx 側の契約上の上限・課金は**未確認**。
- 送料の権限: /shipping/calculate は `shipping.calculate` が必要。請求書作成は `invoices.create`。 backend/app/routers/shipping.py:388 ／ backend/app/routers/invoices.py:261。両方を持つ役割かは**未確認**（design.md:241 も同じ懸念を記す）。
- 運送会社の一覧の正本:
  - 連携できる運送会社の定数 `CARRIERS = ("fedex","dhl","ups")`。 backend/app/services/carrier_credentials.py:34
  - 連携の中身はテナント別の `public.tenant_carrier_credentials`。 backend/app/services/carrier_credentials.py:84-85
  - 静的送料の便は `shipping_zones.carrier` と `shipping_rates.carrier`（GET /shipping/zones・/shipping/rates）。 backend/app/routers/shipping.py:64-87・:164-195
  - 「運送会社だけの一覧を返す API」は**無い**（上の定数と表から読む形）。
- 支払方法の正本: テナント別 `tenant_invoice_payment_methods`（＋bank / wise の詳細表）と `public.tenant_paypal_config`。draft-context の `payment_methods` に `id・method_type・display_name・wise_currency` で返る。 backend/app/services/invoice_payment_methods.py:28-64 ／ backend/app/schemas/invoice.py:135-139
- 通貨の正本: `public.app_fx_rate_history`（JPY は常に先頭に足す）。draft-context の `currencies` に返る。 backend/app/services/fx_currencies.py:1-21 ／ backend/app/routers/invoices.py:318
- 発送方法・発送メモの「選択肢の表」: 送料の選び方は `ShippingInput`（mode=calculate / none）。 backend/app/schemas/invoice.py:56-72。「発送メモ」に当たる請求書の列は `invoices.notes`（備考）で、会社側に `companies.shipping_note`（028）がある。見本の「発送メモ」が会社の shipping_note か請求書の notes かは**未確認**。
- 総重量・送料を便ごとに全部並べる一覧: 総重量は画面で `Σ(数量 × 行重量)` を持つ（InvoiceCreatePage.tsx:215）。便ごとの一覧を**並べて出す部品は今の画面に無い**（今は 1 つ選ぶ形。InvoicePaymentTotalsSection.tsx:187-203）。
- 合計の枠: preview の答え（小計・送料・税・関税・合計）をサーバー計算で返す。 backend/app/routers/invoices.py:348-381 ／ backend/app/schemas/invoice.py:103-114

---

## Q3 商品

### 事実

- カテゴリの正本の表:
  - **中分類**は `public.type_master`（code・name_ja・is_active・sort_order）。GET /products/tcg-types が `code, name_ja` を返す（権限 products.view）。 backend/app/routers/products.py:243-271 ／ frontend/src/pages/inventory/InventoryPage.tsx:171（「中分類マスタ（type_master.code → 日本語名）」）
  - 商品は `products.work_id → type_master.id` で結ぶ。 backend/app/services/inventory_search.py:372
  - 大分類は別表（super_admin_product_kinds が「この大分類は中分類（type_master）で使用中」と断る。backend/app/routers/super_admin_product_kinds.py:146）。
  - `tcg_product_categories`（code・display_name・kubun_type）も別にある。GET /product-categories（権限 product_categories.view）。 backend/app/routers/product_categories.py:92-123。これが見本の「カテゴリ」と同じ軸かは**未確認**。
  - 設計書も「見本の『カテゴリ』列（商品の候補にその値が無い）」を対象外としている。 docs/handoff/invoice-create-portfolio/design.md:29
- InventorySearchBar の候補（InventorySearchCandidate）が持つもの:
  - 単価: `unit_price`（1 つだけ。単位ごとではない）。 backend/app/schemas/inventory_search.py:51 ／ frontend/src/components/InventorySearchBar.tsx:48
  - 在庫: `stock_quantity`（1 つだけ。単位ごとではない）。 :53 ／ :49
  - 重さ: `box_weight_kg`・`case_weight_kg`（単位ごとに 2 つ）。 backend/app/schemas/inventory_search.py:62-63 ／ InventorySearchBar.tsx:54-55
  - カテゴリ: `work_code`（type_master.code）をバックエンドは返す（schemas/inventory_search.py:65）。ただしフロントの型 InventorySearchCandidate には `work_code` の宣言があり（InventorySearchBar.tsx:57）、中分類の名前（name_ja）は返さない。
  - 単位ごとの単価・在庫は**持たない**（単価と在庫は商品 1 つにつき 1 つ。 backend/app/services/inventory_search.py:338-339）。仕入元のオファー `inventory_offers`（condition ごとの quantity・unit_price）はあるが、これは仕入側で、マスク対象。 frontend/src/components/InventorySearchBar.tsx:31-38・:61
- カテゴリで絞る検索 API:
  - GET /inventory/search の引数は `q`・`lang`・`op`・`limit` だけ。**カテゴリの引数は無い**。 backend/app/routers/inventory_search.py:68-79
  - GET /products には `work_code`（作品の符号で絞り込み）と `category` がある。ただし `search` は 10 列の部分一致・OR 検索で、在庫の並び替えや仕入元は入らず、`per_page` 最大 100・権限 products.view。 backend/app/routers/products.py:133-160
  - GET /inventory/aggregated は `?category=`（work_code）で絞れるが、中身は商品×状態のピボットで、候補の形ではない。 backend/app/routers/inventory_aggregated.py:43-52
- 状態（単品/ケース）に当たる値の正本:
  - 請求書の明細の `unit`（形態）。値の選択肢は `public.product_attribute_masters` の `attribute='unit'`（piece・pack・box・case）。 migrations/20260604_170000_create_product_attribute_masters.sql:94-97
  - 読み出しは GET /products/attribute-options（権限 products.view、`{"unit":[{code,label_ja,label_en}]}` の形）。 backend/app/routers/products.py:274-317
  - 別に `condition`（状態。50 文字）の列が明細にある（backend/app/schemas/invoice.py:33-34）。見本の「状態(単品/ケース)」は意味としては `unit` 側。**見本の「状態」を condition と unit のどちらに結ぶかは未確認**。
  - 画面は unit から重さを引く `weightForUnit`（box→box_weight_kg / case→case_weight_kg）。 frontend/src/pages/quote-create/quoteDraft.ts:36-46。「単品」に当たる unit の値（piece か pack か）は未確認。
- 数量の在庫上限: 候補は `stock_quantity` を持つが、画面の数量欄は `min=1` だけで上限は無い。 frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:484 ／ バックエンドの InvoiceItemInput も `quantity: ge=1` だけ（backend/app/schemas/invoice.py:36）。在庫数を明細行に持ち回る入れ物（LineItem）に stock の欄があるかは**未確認**（`zero_stock_warning` だけ確認。InvoiceCreatePage.tsx:157）。

---

## Q4 作成前に請求書の見た目（PDF）を出す道

### 事実

- **作成前に PDF を出す道は無い**。 PDF の道は `GET /invoices/{invoice_id}/pdf` で、保存済みの請求書の列とスナップショットから描く。 backend/app/routers/invoices.py:1034-1091
- 見積の PDF も `GET /quotes/{quote_id}/pdf` で保存済みを描く。 backend/app/routers/invoices.py:1194-1265
- 描画器は `render_invoice_pdf(invoice_data, tenant_profile)` で、dict を渡せば描ける形（保存と別の関数）。 backend/app/routers/invoices.py:53・:1083 ／ backend/app/services/invoice_renderer.py:513 付近
- 試算の POST /invoices/preview は額だけで PDF は返さない。 backend/app/routers/invoices.py:348-381 ／ backend/app/schemas/invoice.py:103-114
- 作成すると status は `draft` で保存され、詳細画面に PDF ボタンがある。 backend/app/routers/invoices.py:154 ／ frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:155
- 見本の「発行で請求書の見た目を重ねて出し印刷・PDF」: 重ね表示（画面上のプレビュー）の部品は**今の画面に無い**。ブラウザ側の PDF 生成や画面上の請求書の見た目の部品も**未確認（検索で見つからず）**。
- 未確認: 「保存せずに（書かずに）PDF だけ返す新しい道」を作る場合の、権限・監査・realtime 登録の要否（design.md:126 は書き込みの道の登録の決まりを述べる）。

---

## Q5 デザインシステム（frontend/src/components と金型の目録）

目録の正本: docs/CC_UI_GOVERNANCE.md（必須チェック :7-17・禁止の一覧 :21-30）。Storybook は frontend/.storybook/（main.ts・preview.tsx）。各部品は `Xxx.tsx` + `Xxx.css` + `Xxx.stories.tsx`。トークンは frontend/src/tokens.css。

| 使いたい用途 | 使える部品（あれば） | 根拠 | 評価 |
|---|---|---|---|
| 区切りのカード | `Card`（variant: container / interactive / metric、density） | frontend/src/components/Card.tsx:27・Card.stories.tsx:10 | **ある**。今の請求書作成画面は使わず、素の `<form style=…>` と `<h3>` で区切っている（InvoiceCreatePage.tsx:360-362・:370） |
| 区切りの見出し（セクション見出し） | 専用部品は**無い**。トークン `--font-lg`（セクション見出し用）はある | frontend/src/tokens.css:18 | 見出し部品は無い |
| 読むだけの欄 | 専用の読み取り表示部品は**無い**。`TextFieldControl` は readOnly を渡せる（試験あり） | frontend/src/components/TextField.test.tsx（readOnly の試験）／ 部品側に専用 variant の記述は**未確認** | 見本の「読むだけの欄」を表す金型は**無い**（今は `<dl>` の素書き。InvoiceShipToSection.tsx:55-64） |
| 候補つき検索欄 | `AsyncCombobox`（非同期候補） | frontend/src/components/AsyncCombobox.tsx:18-88・AsyncCombobox.stories.tsx:64 | **ある**（汎用。会社の検索への流用は未確認） |
| 在庫・商品の検索欄 | `InventorySearchBar`（7 種横断、AND/OR、250ms debounce） | frontend/src/components/InventorySearchBar.tsx:96-103 | ある。ただし**カテゴリで絞る入口は無い**（Q3） |
| 会社・担当者の検索 | `CompanyContactSelector` | frontend/src/components/CompanyContactSelector.tsx:80 | ある（`/companies?per_page=100` を取る。:107 ） |
| 国の選択 | `CountryCombobox` | frontend/src/components/CountryCombobox.tsx:24 | ある |
| 選択（プルダウン） | `Select` / `SelectControl`（表の中は SelectControl） | frontend/src/components/Select.tsx:64・:126 | ある |
| 2 択の切替 | `SegmentedToggle`、`Radio` / `RadioControl` | frontend/src/components/SegmentedToggle.tsx:34 | ある（単品/ケースの選択に使える候補） |
| 表 | `DataTable`（density: compact / default / relaxed、列定義、並び替え） | frontend/src/components/DataTable.tsx:39-175 | ある。今の請求書の明細は部品を使わず `className="data-table"` の素の `<table>`（InvoiceCreatePage.tsx:424） |
| 合計の枠 | **専用部品は無い**。`Card variant="metric"` が KPI 用に近い | frontend/src/components/Card.css:65-66 | 見本の「小計・送料・税・合計の枠」を表す金型は**無い**（今は `<dl>` の素書き。InvoicePaymentTotalsSection.tsx:228-252） |
| 2 列・3 列の並び | `TwoColumn`（ratio '1:2' / '1:1'）、`Stack` | frontend/src/components/TwoColumn.tsx:13-28 ／ Stack.tsx:12-16 | 2 列はある。**3 列の部品は無い**（見本の「3列」） |
| 注意・案内の囲み | `Callout` | frontend/src/components/Callout.tsx:25 | ある |
| ボタン・読み込み | `Button`、`LoadingBlock` | frontend/src/components/Button.tsx、frontend/src/components/loading/LoadingBlock.tsx | ある |
| 数量・単価・小計の入力 | `TextFieldControl`（size sm） | frontend/src/components/TextField.tsx:43 | ある |

- 主なトークン: `--space-4`（16px）・`--radius-lg`・`--font-lg`・`--input-width-qty`（70px）・`--table-col-product-name-min-w`（320px）・`--bg-surface`。 frontend/src/tokens.css:77・:98・:18・:476・:478・:700
- 目録の決まり: 金型があるなら必ず使う。無いものは止めて報告し、PO 許可のうえ `components/` に登録してから使う（docs/CC_UI_GOVERNANCE.md:7-17）。→ 上の表で **「無い」と書いた部品**（読むだけの欄・合計の枠・3 列・区切りの見出し）は新設に PO 許可が要る。
- 今の請求書作成画面は色直値・生 `<select>` などの禁止事項は使っていないことを grep で確認していない（**未確認**。CI ゲート scripts/check-ui-governance.js の結果は見ていない）。

---

## Q6 見積作成画面 frontend/src/pages/quote-create/ への流用

### 事実

- 請求書作成画面は見積作成画面と**同じ明細エディタ**を使うと明記している。共通ロジックは `../quote-create/quoteDraft`（LineItem・QuoteHandoffState・blankItem・buildInitialItems・weightForUnit）。 frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:13・:24-30
- 流用できる形:
  - `LineItem` と `weightForUnit`（unit から重さを引く）: frontend/src/pages/quote-create/quoteDraft.ts:36-46
  - 「検索して追加」で候補を新しい明細行にする処理 `appendFromSearch`: 見積側 frontend/src/pages/quote-create/QuoteCreatePage.tsx:70、請求書側 InvoiceCreatePage.tsx:141-160（同じ形）
  - InventorySearchBar を明細の下に置く構成: QuoteCreatePage.tsx:259 ／ InvoiceCreatePage.tsx:509
- 流用してはいけない／違う点:
  - 見積は送料を `/shipping/calculate`（FedExRateModal）で出して `shipping_fee` を送る形で、請求書は送料・税の打ち込み欄を持たずサーバー試算に任せる。 QuoteCreatePage.tsx:21（FedExRateModal の import）／ InvoiceCreatePage.tsx:9-12
  - 見積には preview（試算）の道が無い。請求書の `useInvoicePreview`（frontend/src/pages/invoice-create/useInvoicePreview.ts:1-59）は請求書の道 `/invoices/preview` 専用。
- 見本の新しい商品行（カテゴリ選択・状態選択・在庫上限・重量/単価の自動）を作るなら、LineItem に `category` や `stock` の欄を足す必要があるかを含め、見積側と共通のため**見積作成画面にも影響する**。影響範囲の確認は**未確認**。見積作成の試験は frontend/src/pages/quote-create/quoteDraft.test.ts。

---

## Q7 今の請求書作成画面の作り（InvoiceCreatePage.tsx 等）と見本の部品の対応

画面本体: frontend/src/pages/invoice-create/InvoiceCreatePage.tsx（526 行）。区切りは 2 部品 + 本体。

| 見本の部品 | 今の画面 | 根拠 |
|---|---|---|
| 見出し「発送先」 | `<h3>`（invoiceForm.sectionShipTo）＋ CompanyContactSelector（会社・担当者の 2 欄）＋ `InvoiceShipToSection`（住所・担当者・メールを `<dl>` で**読むだけ**・直すボタンは会社の画面へ移動） | InvoiceCreatePage.tsx:370-383 ／ InvoiceShipToSection.tsx:22-70 |
| 発送先の 12 欄・2 列 | **無い**。見本の 12 欄の代わりに、請求先・届け先・担当者の 3 行の文字（addressLine で 1 行） | InvoiceShipToSection.tsx:44-64 |
| 顧客名(検索) | CompanyContactSelector（一覧を取って選ぶ） | InvoiceCreatePage.tsx:372-377 |
| 支払方法 | `Select`（候補は draft-context の payment_methods。1 件も無ければ案内の Callout） | InvoicePaymentTotalsSection.tsx:159-178 |
| 通貨 | `Select`（候補は draft-context の currencies）＋ 為替の 1 行 | InvoicePaymentTotalsSection.tsx:139-158 |
| 発送方法 | `Select`（送料を請求しない / 選んだ運送会社）＋ 見積ボタン → `FedExRateModal` | InvoicePaymentTotalsSection.tsx:186-226 |
| 発送メモ | 備考 `TextFieldControl`（notes。invoices.notes に保存） | InvoicePaymentTotalsSection.tsx:181-184 ／ InvoiceCreatePage.tsx:107・:273 |
| 総重量 | `<dl>` の 1 行（`totalWeight` kg） | InvoicePaymentTotalsSection.tsx:229-230 ／ InvoiceCreatePage.tsx:215 |
| 送料を便ごとに全部並べた一覧 | **無い**（モーダルで 1 つ選ぶ。選んだ 1 件だけ画面に残す） | InvoicePaymentTotalsSection.tsx:197-201 |
| 合計の枠（小計・送料・税・関税・合計） | `<dl>`。サーバーの preview の答えを表示（画面で足し算しない） | InvoicePaymentTotalsSection.tsx:228-252 ／ useInvoicePreview.ts:1-59 |
| 3 列配置 | **無い**（通貨・支払方法は 2 列 grid、そのあと縦並び） | InvoicePaymentTotalsSection.tsx:138 |
| 商品一覧 #（行番号） | **無い**（行番号の欄は無し） | InvoiceCreatePage.tsx:426-435 |
| カテゴリ選択 | **無い** | 同上（列は titleColumn・condition・unit・quantity・unitPrice・weight・subtotal） |
| 商品名/型番検索（カテゴリで絞る） | 明細の下に InventorySearchBar を 1 つ置き、選ぶと新しい行を追加。行内検索は廃止済み。カテゴリで絞る入口は無い | InvoiceCreatePage.tsx:421・:509-513 |
| 状態（単品/ケース） | `unit` の自由入力欄（`TextFieldControl`）。選択肢ではない。変更すると重さを引き直す | InvoiceCreatePage.tsx:469-482 |
| 数量（在庫で上限） | 数値入力。**上限なし**（min=1） | InvoiceCreatePage.tsx:484 |
| 重量自動 | 候補の box/case 重量を unit で引く。手入力もできる | InvoiceCreatePage.tsx:476・:490 ／ quoteDraft.ts:36-46 |
| 単価自動 | 候補の `unit_price` を入れる。手入力もできる | InvoiceCreatePage.tsx:154・:487 |
| 小計 | `数量 × 単価` を画面で計算して表示（行の小計）。**請求書全体の合計は画面で足さずサーバー試算** | InvoiceCreatePage.tsx:492 |
| ×（行を消す） | `Button variant="danger"`（行が 2 行以上のとき） | InvoiceCreatePage.tsx:494-496 |
| クリア | `Button`（clearAll） | InvoiceCreatePage.tsx:203-212・:519 |
| 請求書を発行 | `Button`（作成）。押せる条件は材料・送料・試算が揃い「未計算」0 件のとき。作成は draft で保存し詳細画面へ | InvoiceCreatePage.tsx:234-247・:249-288・:520 |
| 発行で請求書の見た目を重ねて出し・印刷・PDF | **無い**。作成後は詳細画面へ移り PDF ボタンで別タブ | InvoiceCreatePage.tsx:282 ／ InvoiceDetailPage.tsx:155 |
| モード切替（在庫表から / 見積から） | 2 つのボタン。既定は見積選択（承認済み見積の一覧から読み込み） | InvoiceCreatePage.tsx:94・:305-320 |

見本との差の要点（事実のみ）:

1. 見本の 12 欄の宛名は今の画面に無く、写しにも PDF にも一部しか残らない（Q1）。
2. 送料は「選ぶ 1 件」であり、便を全部並べる一覧と 3 列の枠が無い（Q2）。
3. 商品行はカテゴリ選択・行番号・在庫上限が無く、状態は自由入力（Q3）。
4. 作成前の PDF・見た目の重ね表示は無い（Q4）。
5. 新設が要る金型: 読むだけの欄・合計の枠・3 列・区切りの見出し（Q5）。
