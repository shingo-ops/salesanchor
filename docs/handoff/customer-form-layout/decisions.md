# 顧客登録フォーム PC 版 決定記録

PO の回答を原文のまま記録する。設計の草案と PO 決定を分けるための台帳。

| # | 日付 | 問い | PO 回答（原文） | 決まったこと |
|---|---|---|---|---|
| D1 | 2026-11-23 | City・State・ZIP の並べ方（1: City単独行＋State/ZIP 1行 ／ 2: 3つを1行 ／ 3: City/State 1行＋ZIP単独） | 「1」 | City は1行を占める。State と ZIP を1行に並べる（Google 見本・Stripe と同じ形。evidence-local.md §1・§2） |
| D2 | 2026-11-23 | 35文字の決まりを請求先にも付けるか（1: 請求先は自由・「同じ」を選んだ時だけ請求先も35文字で確かめる ／ 2: 請求先にも付ける ／ 3: 送り先だけ） | 「配送先についてはFedExが35文字以上の入力ができないのでその対策として35時制限を付けたい、請求先については問題ないがどうするべき？」→ 提案1を受けて次の D3 | 送り先の住所1〜3は35文字以内。請求先は自由。「Ship to the same address.」を選んだ時だけ、請求先の住所1〜3も35文字以内か確かめる |
| D3 | 2026-11-23 | （PO 発案） | 「1にした場合に請求先住所にも住所3がないと書き込めなくなるリスクがあるから住所3を追加しておいて」 | 請求先にも Address Line 3 を足す（/register と /register/change-billing）。「同じ」を選んだ長い住所を35文字×3行に分けて入れられるようにするため |
| D4 | 2026-11-24 | 見積書の紙で住所3が抜け落ちる件（1: 今回の直しに入れて見積書にも住所3を印刷 ／ 2: 別の仕事で後で ／ 3: 直さない） | 「1,」 | 見積書の宛名の「1つにつないだ住所」に住所3を加える。請求先・送り先の両方に効く |
| D5 | 2026-11-24 | 送り先の住所に英語以外の文字が入った時（1: 英字・数字・記号・空白以外は赤くして「英字・数字・記号で入力してください」 ／ 2: 文字の種類は見ない ／ 3: é・ü・ß などは通す） | 「1」 | 送り先の住所1〜3（と「同じ」を選んだ時の請求先の住所1〜3）は、半角の英字・数字・記号・空白だけ。ほかの字は赤くして専用の文を出す。日本語も é も通さない |
| D6 | 2026-11-24 | 社内の会社の画面でも同じ決まりにするか（1: 社内の画面の送り先にも付ける・今ある決まり外の住所は残し直す時に赤くなる ／ 2: お客様のフォームだけ ／ 3: 1＋今ある分を一度に直す） | 「1」 | 新しく決まり外の送り先が入る道をすべてふさぐ。今ある決まり外の住所は消さず書き換えず、次に直す時に赤くなる |

## PO に聞かずに既存の決まりで確定したこと

| # | 事柄 | 根拠 |
|---|---|---|
| F1 | 国の一覧の正本は `frontend/src/constants/countries.ts`。DB の `public.countries` は使わない（公開フォームに新しい道を作らない） | `docs/adr/ADR-126-registration-form-input-contract-v2.md:81`「DBテーブル化はしない」／`migrations/20260621_010000_create_countries_master.sql:31-34`（ADR-1007/ADR-155 で seed を外し、正本は countries.ts と明記） |
| F2 | 国の欄は「打つと候補が絞られる」形を続ける | `ADR-126…md:48`・`:141` |

## D3 の実物確認（Opus・2026-11-23・worktree の main 土台で読んだ）

- 請求先の欄は住所1・2だけ: `frontend/src/pages/register/RegisterPage.tsx:385`・`:396`、`frontend/src/pages/register/RegisterChangeBillingPage.tsx:331`・`:342`
- 送り先の欄は住所1〜3: `frontend/src/pages/register/RegisterPage.tsx:614`・`:625`・`:635`、`frontend/src/pages/register/RegisterAddressPage.tsx:375`・`:385`・`:395`
- 画面の入れ物は請求先にも住所3を持っている（使っていないだけ）: `RegisterPage.tsx:39`・`:57`、`RegisterChangeBillingPage.tsx:37`・`:55`
- 受け口（API）は請求先・送り先共通で住所3を受ける: `backend/app/schemas/registration_token.py:73`
- DB の列は既にある: `migrations/030_create_company_contact_subtables.sql:51`。→ DB 変更は不要
- 住所3の読み手:
  - 請求書の PDF は住所1〜3を描く: `backend/app/services/invoice_renderer.py:544`
  - 帳票は住所1〜3をつなぐ: `backend/app/tasks/reports.py:53`
  - 管理画面の会社編集は住所3を扱う: `backend/app/routers/companies.py:59`・`:247`
  - **見積の PDF などが使う「1つにつないだ住所」は住所1・2だけで、住所3が落ちる**: `backend/app/routers/invoices.py:105-107`（`_to_addr` の `address`、`invoice_renderer.py:623` の見積側で使用）。この穴は送り先の住所3でも既に起きている（今回の変更で新しく生まれる穴ではない）
- ADR-126 §1 Section 1 の表（`docs/adr/ADR-126-registration-form-input-contract-v2.md:36-47`）に住所3の行が無い → 設計書の段で ADR-126 の改訂案に入れる

## D4 の実物確認（Opus・2026-11-24）

- 見積の PDF は `backend/app/routers/invoices.py:1375-1376` で宛名を取り、`_quote_pdf_address`（`:128-131`）で住所1〜3の分けた値を消してから描く。描くのは `address` だけ（`backend/app/services/invoice_renderer.py:625`）。
- `address` は住所1・2だけをつないでいる: `backend/app/routers/invoices.py:105-107`。→ ここに住所3を足すのが直し。
- 既に決まっていた「見積の PDF は宛名を変えない」（`invoices.py:121` のコメント、invoice-create-portfolio design-v2 §3-2）は、新しく足した6項目を見積に出さないという意味。D4 は住所3を「つないだ住所」の中に入れるだけで、6項目は出さないまま。この理解で食い違わないかは設計審査で確かめる。
- `address` を作る関数 `_fetch_address_snapshot` は請求書を作る時の写し（`invoices.py:350-351`・`:420-421`・`:468-469`・`:556-557`・`:653-654`）にも使われる。保存済みの写しは変わらず、これから作る写しの `address` に住所3が入る。請求書の PDF は分けた値で住所1〜3を描くので見た目は変わらない（`invoice_renderer.py:533-546` の `split`）。
- 画面（frontend）で写しの `address` を読んでいる箇所は、`git grep` で見つからなかった（未確認として設計書で全走査する）。

## 本番の今の住所の数（Opus・2026-11-24 01:24 JST・本番の読み取り専用の道 ADR-1024 で数えた。住所の中身は読んでいない）

生の出力: scratchpad の ca_count.tsv・ca_kind.tsv（AUDIT sha=7fa4ed695564・1575e68a2e07）

| 会社の区画 | 種類 | 件数 | 35文字を超える行がある | 英字・数字・記号以外の字がある | 住所3が入っている |
|---|---|---|---|---|---|
| tenant_001 | 請求先 | 4 | 0 | 0 | 0 |
| tenant_001 | 送り先 | 3 | 0 | 0 | 0 |
| tenant_004 | 請求先 | 51 | 5 | 4（日本語1・é などの字3） | 0 |
| tenant_004 | 送り先 | 50 | 5 | 3（日本語1・é などの字2） | 2 |

- tenant_003・005・006 は 0 件（行が出なかった）。
- いちばん長い1行は 53 文字（tenant_004・請求先と送り先の両方）。
- 判定の式: 35文字は `length()`、英字等以外は正規表現 `[^ -~]`、日本語は `[ぁ-んァ-ヶ一-龯]`、é などは `[À-ɏ]`。

## D6 の実物確認：送り先の住所を書き込む道（Opus・2026-11-24）

`git grep "INSERT INTO company_addresses|UPDATE company_addresses"` と住所3の欄の全走査で見つけた道:

| 道 | 書き込む所 | 受け口の決まり（今） |
|---|---|---|
| お客様の登録フォーム（/register・/register/address・/register/change-billing） | 会社の住所の表 | `backend/app/schemas/registration_token.py:71-73` 各255文字 |
| 社内の会社の画面の住所の窓（`frontend/src/pages/company-detail/CompanyAddressModal.tsx:125`） | 会社の住所の表（`backend/app/routers/companies.py:244`） | `backend/app/schemas/company.py:64-66` 各255文字 |
| 注文ごとの発送の欄（`frontend/src/components/ShippingDetailPanel.tsx:110`） | 注文の発送の表（会社の住所とは別の表） | `backend/app/schemas/order_shipping_detail.py:76-78` 各255文字 |

- 3つ目（注文ごとの発送の欄）は D6 を聞いた時の説明に入れていなかった。D6 の意図（決まり外の送り先が入る道をすべてふさぐ）に含めて設計し、PO に報告する。
- アプリから FedEx の伝票を出す受け口 `POST /shipping/shipments`（`backend/app/routers/shipping.py:492-493`）は、画面からの呼び出しが `git grep` で見つからなかった。今の送り先が FedEx へどう渡っているか（人が書き写しているのか等）は未確認。
- 会社の併合（`companies.py:852-915`）は既存の行の付け替えだけで、住所の文字は書かない。
