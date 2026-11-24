# recon — お客様の住所フォームと住所の決まり（customer-address-form）

- 調べた人: Claude Opus（設計担当）・2026-11-24
- 基準: `origin/main` = `a12741e7234b7fe2ec40a790a8aa3422e0d6eaa4`（`git fetch` 後。行番号はすべてこの版を `git show origin/main:<path>` で読んだもの）
- 親: [kgi.md](../../specs/customer-address-form/kgi.md)（PO 承認 2026-11-24）／決定: [decisions.md](decisions.md)／外部の実測: [evidence-local.md](evidence-local.md)

## 0. 既存 ADR の検索

- `git grep -i -l "registration\|register\|address_line\|company_addresses" origin/main -- docs/adr/` と `docs/adr/FEATURE-INDEX.md` の 39 行目（顧客登録フォーム）で拾った ADR: ADR-058・ADR-060・ADR-089・ADR-097・ADR-126・ADR-127。
- 直接の正本は ADR-126（登録フォームの入力契約 v2）。`docs/adr/ADR-126-registration-form-input-contract-v2.md` の Section 1 の表（ファイルの 36〜47 行目付近）に **Address Line 3 の行が無い**。35文字・文字の種類の決まりも無い。→ design.md §8 で改訂案を出す。
- 国の一覧の正本は `frontend/src/constants/countries.ts`（ADR-126「DBテーブル化はしない」・decisions.md F1）。
- UI の金型の決まりは ADR-144（`docs/CC_UI_GOVERNANCE.md`）、色・余白の直書き禁止は ADR-067、翻訳キーは ADR-027。

## 1. 住所の文字が DB に入る道（全部で3つ・D6 の対象）

| 道 | 画面 | 受け口 | 受け口の型（今） |
|---|---|---|---|
| A お客様のフォーム | `frontend/src/pages/register/RegisterPage.tsx`（/register）・`RegisterAddressPage.tsx`（/register/address）・`RegisterChangeBillingPage.tsx`（/register/change-billing） | `backend/app/routers/registration_tokens.py:217` register_customer・`:423` add_address・`:512` change_billing | `backend/app/schemas/registration_token.py:62-90` `AddressInput`（住所1〜3 は各 255 文字まで）。`RegisterRequest.addresses`・`AddAddressRequest.address`・`ChangeBillingRequest.address` の3つが同じ型を使う |
| B 社内の会社の画面の住所の窓 | `frontend/src/pages/company-detail/CompanyAddressModal.tsx`（住所1〜3 は `:117-128`） | `backend/app/routers/companies.py:517` PATCH `/companies/{id}`（住所は `:586-588`）・`:377` POST `/companies`（住所は `:479`） | `backend/app/schemas/company.py:53-69` `_CompanyAddressFields`／`:72-` `CompanyAddressInput`（電話・メールの確かめだけ） |
| C 注文ごとの発送の欄 | `frontend/src/components/ShippingDetailPanel.tsx`（住所の欄の定義 `:107-110`・描画 `:424-434`） | `backend/app/routers/order_shipping_details.py:139-245`（POST で作る・PATCH で直す） | `backend/app/schemas/order_shipping_detail.py:63` `OrderShippingDetailBase`（address1〜3 は `:76-78`）。`Create` `:122`・`Update` `:127`・`Response` `:135` がすべて Base を継ぐ |

- POST `/companies` を呼ぶ画面は無い（`git grep -n -E "post\(.*companies" origin/main -- frontend/src` が 0 件）。受け口だけがある。
- 会社の併合（`companies.py:852-915`）は既存の行の付け替えだけで、住所の文字を書かない（decisions.md D6 の実物確認）。

## 2. 会社の住所は「全部消して全部入れ直す」

- 保存は `companies.py:227-276` `_replace_addresses`：その会社の住所を全部消し、送られてきた住所を全部入れ直す。
- 住所の窓は保存のたびに、その会社の **全部の住所** を送り直す：`CompanyAddressModal.tsx:55-62`（今の住所を全部並べ、直した1件だけ差し替える）→ `frontend/src/pages/company-detail/useCompanyDetail.ts:185-206`（`api.patch(`/companies/${company.id}`, { addresses: payload })`）。
- **このため、受け口の型（`CompanyAddressInput`）に決まりを付けると、決まり外の送り先を持つ会社では、請求先を1件直すだけでも保存できなくなる。** 本番のテナント004 には決まり外の送り先がある（decisions.md の「本番の今の住所の数」：35文字超え5件・英字等以外3件）。D6「今ある決まり外の住所は消さず書き換えず、次に直す時に赤くなる」に反する。→ design.md §3-2。
- 住所の窓は空欄を `null` で送る（`useCompanyDetail.ts` の `toNull`）。DB に `""` で入っている行と `null` で送られた行は、比べる時に同じとみなす必要がある。

## 3. 注文ごとの発送の欄の本番の件数

- 本番の読み取り専用の道（ADR-1024）で数えた：テナント001・003・004・005・006 の注文の発送の表は **0 件**（生の出力 `scratchpad/osd_count.txt`）。
- この表に書く道はこの受け口だけ（`order_shipping_details.py:168` の INSERT）。→ 決まり外の行は今 0 件なので、作る時・直す時は必ず確かめてよい。
- ただし `Response`（読み出し）も Base を継ぐ（`order_shipping_detail.py:135`）。決まりを Base に付けると読み出しにも効いてしまう。→ `Create` と `Update` にだけ付ける。

## 4. お客様のフォームの今の形（RegisterPage.tsx・692 行）

| 事柄 | 場所 | 今 |
|---|---|---|
| 言語切替 | `:282-286` | 見出しの上に、右寄せの別の行（`justifyContent: "flex-end"`） |
| 見出し | `:288` | `<h1>` |
| 国番号の欄 | `:320-344` | 外枠が `width: "140px"` の直書き（`:322`）。表示は `${c.dial} ${c.code}`（`:330`） |
| 請求先の住所 | `:384-402` | 住所1・2 だけ（住所3 の欄が無い）。入れ物 `AddressForm` は住所3 を持つ（`:39`・`:57`） |
| City・State・ZIP | `:405-432` | 3つが縦に1つずつ |
| 国 | `:438-451` | `CountryCombobox`（打つと絞られる） |
| 送り先を登録するか | `:454-476` | `proceed`／`same` の2択 |
| 「同じ」を選んだ時 | `:200-207` | 請求先をそのまま `address_type: "delivery"` として足して送る |
| 送り先の欄 | `ShippingAddressFields` `:541-692` | 国番号 `:566`（140px）・住所1〜3 `:613-641`・City/State/ZIP `:644-671`・国 `:677-689` |
| 必須の印 | `:277`・ほか | `style={{ color: "var(--color-red-500)" }}` の直書き |
| 登録されていない変数 | 全体 | `--spacing-*`・`--border-default`・`--color-red-500`・`--color-primary`・`--font-size-xs`・`--font-size-sm` は `frontend/src/tokens.css` に定義が無い（`grep -c -- "--spacing-3:"` などで 0 件。正しい名前は `--space-*`・`--border`・`--danger`（`frontend/src/index.css:53`、暗い画面は `:262`）・`--accent`（`tokens.css:736`）・`--font-xs`・`--font-sm`） |
| 送信の前の確かめ | `:140-195` | 必須だけ。決まり違反は画面の上の帯（`error-banner`）に1つずつ出す |
| 受け口の 422 | `:222-227` | `detail` が配列なら `msg` をつないで帯に出す |

- `RegisterChangeBillingPage.tsx`（411 行）：請求先だけ。言語切替 `:230`・見出し `:235`・国番号 140px `:268`・住所1・2 `:331`/`:342`（住所3 が無い）・国 `:384`・送り先 `POST /api/v1/public/register/change-billing` `:162`。
- `RegisterAddressPage.tsx`（464 行）：**自前の `function CountryCombobox` を `:76` に持つ**（`pages/register/CountryCombobox.tsx` と同じものの写し）。言語切替 `:296`・見出し `:301`・国番号 140px `:327`・住所1〜3 `:375`/`:385`/`:395`・国 `:437`・送り先 `POST /api/v1/public/register/address` `:227`。

## 5. 国の欄の部品が2つある

| 部品 | 使う所 | 国の一覧の出どころ |
|---|---|---|
| `frontend/src/components/CountryCombobox.tsx`（207 行・Storybook あり） | 社内の画面（`DutyRuleFormModal.tsx:187`・`LeadEditPage.tsx:264`・`LeadFormFields.tsx:162`・`LeadsPage.tsx:409`） | `api.get("/countries")`（`:43`）。この受け口はログインが要る（`backend/app/routers/countries.py` の `Depends(get_current_tenant)`）→ お客様のフォームでは使えない |
| `frontend/src/pages/register/CountryCombobox.tsx`（98 行） | お客様のフォーム（RegisterPage・RegisterChangeBillingPage） | `constants/countries.ts`（ADR-126・F1） |

- お客様のフォームの部品は、表示を `displayFn` で作り、選んだ値を探す時に `displayFn(c) === value || c.code === value || c.dial === value` の **最初の1件** を取る（`:30-33`）。米国の「+1」を選んでも、一覧で先に来るバハマ（BS）が見つかり「+1 BS」と出る。これが「+1 BS」の原因。
- 一覧の見た目は直書き：`zIndex: 10`・`maxHeight: "200px"`・`var(--border-default)`（未定義）・`var(--spacing-2/3)`（未定義）（`:61-93`）。
- 国番号は 191 か国のうち 137 か国が4文字（「+355」など）（kgi.md「決める前の事実」）。

## 6. 使える金型・変数（実物）

- `TextField`（`frontend/src/components/TextField.tsx:60-106`）：`label`・`required`（`comp-field__required` の `*`）・`helperText`・`error`（外枠 `comp-field--error`・文 `comp-field__hint--error`・`role="alert"`）。赤は `FormField.css` の `var(--danger)`（`:115-128`）。
- `TextFieldControl`（`:43-57`）：`invalid` で赤い枠だけ付く。
- `TwoColumn`（`frontend/src/components/TwoColumn.tsx`）：`ratio="1:1"` で等幅2列。間隔 `gap` は `--space-N`。
- 見出しと操作を1行に並べる型：`frontend/src/company-forms.css:17-31` の `.page-container .page-header`（`display:flex; justify-content:space-between`）と `h1` の字の大きさ。登録フォームの外枠は既に `className="page-container"`。
- 幅の金型：`frontend/src/components/field-size.css` の `field-w-sm`（160）・`field-w-md`（280）・`field-w-lg`（100%・上限 480）。変数は `frontend/src/tokens.css:196-198`。「+000」が入る狭い段は無い。設計書は `docs/specs/design-system/component-ssot/field-size/design.md`（§1 幅3段）。
- 一覧の重なり順の変数 `--z-dropdown`・影 `--shadow-lg`・角 `--radius-sm` は tokens.css にある。
- フォームの最大幅 600px は直書き（`RegisterPage.tsx:280` の `maxWidth: "600px"`）。tokens.css に 600px のフォーム幅の変数は無い（`--max-width-form` は 560px・`--modal-max-w-md` はモーダル用）。

## 7. 見積書の宛名（D4）

- `backend/app/routers/invoices.py:105-107`：`"address": " ".join(filter(None, [row["address_line_1"], row["address_line_2"]]))`。住所3 が入らない。
- 見積の PDF は `_quote_pdf_address`（`:128-131`）で分けた値を除いてから描くので、描くのは `address` だけ。
- 請求書の PDF は分けた値で住所1〜3 を描くので、`address` に住所3 を足しても見た目は変わらない（decisions.md D4 の実物確認）。
- 既存の試験 `backend/tests/test_invoice_pdf_address.py`。

## 8. 既存の試験

- 受け口: `backend/tests/test_registration_token_schema.py`・`test_register_invite.py`・`test_public_register_company.py`・`test_order_shipping_details.py`・`test_invoice_pdf_address.py`。
- 画面: `frontend/tests-e2e/register-form-ux.spec.ts`。

## 9. 未確認として残すもの

- アプリから FedEx の伝票を出す受け口 `POST /shipping/shipments`（`backend/app/routers/shipping.py:492-493`）を呼ぶ画面が見つからない。今の送り先が FedEx へどう渡っているかは未確認（この仕事の範囲外。decisions.md D6）。
- 社内の画面の国の部品とお客様のフォームの国の部品を1つにするか（出どころが違う。この仕事では1つにしない・design.md §7）。
