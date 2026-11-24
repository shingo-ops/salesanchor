# 設計審査 1回目（architect）— customer-address-form

- 審査した物: `origin/release/customer-form-pc-layout-design`（a774e7a10）の `docs/handoff/customer-form-layout/{design,recon,decisions}.md`・`docs/specs/customer-address-form/kgi.md`・`docs/adr/ADR-126-registration-form-input-contract-v2.md` 末尾の追補
- 突き合わせた実物: `origin/main` = a12741e7234b7fe2ec40a790a8aa3422e0d6eaa4（読むだけ。製品のコード・DB・本番には触っていない。pytest・vitest・e2e は流していない＝「動く」ことの確認ではなく、読んで確かめた結果）

## 判定: REVISE（直す必要）

1. 受け口（§3）の設計は読んで通る。会社の PATCH（dict・Enum）も、今ある決まり外の行をそのまま保存する場合も、既存試験も壊れない（§1 に根拠）。
2. ただし受入表の K5「住所1・2 の幅が今と同じ」は、設計 §4-5 e（未定義の変数を直す）を入れると必ず ×（600px → 約 518px）になり、設計の中で矛盾している（R1）。
3. 国の部品（§4-4）は CSS の移し先だけで、TSX 側の変更（class を付ける・CSS を読み込む）が書かれておらず、そのまま作ると K14 が崩れる。見積書の試験（§6）は書ける形になっていない（R2・R3）。行番号の間違いが6件ある（R4）。

## 直す点（R）

### R1. K5 と §4-5 e が両立しない（K5 が判定できない）

- 事実: 今の外枠 `style={{ maxWidth: "600px", margin: "0 auto", padding: "var(--spacing-6)" }}`（`frontend/src/pages/register/RegisterPage.tsx:280`・`RegisterAddressPage.tsx:293`・`RegisterChangeBillingPage.tsx:227`）の `--spacing-6` は定義が無い（`grep -rnE -e "^\s*--spacing-6:" frontend/src frontend/index.html` が0件）。定義の無い変数を使った宣言は「計算の時点で無効」になり、値は初期値（0）になる。fieldset の `border: 1px solid var(--border-default)`・`padding: var(--spacing-4)`（`RegisterPage.tsx:299`）も同じ。つまり今は外枠の余白 0・fieldset の余白 0・枠なしで、住所1の欄は 600px いっぱい。
- 設計 §4-5 e は `--space-6`（24px。`frontend/src/tokens.css:79`）・`--space-4`（16px）・`--border` に直す。→ 外枠の内側が 600 − 48 = 552px、fieldset の中はさらに 16×2 + 枠 1×2 = 34px 狭くなり、住所1の幅は約 518px。`box-sizing: border-box`（`frontend/src/index.css:447`）なので 600px の最大幅は変わらず、中身だけ狭くなる。
- 設計 §9 K5 の検証「変更の前（本番）と後で住所1の幅が同じ（外枠の最大幅の値は同じ 600px）」は、住所1の幅を測るので ×。設計 §7 の弊害にも幅の縮みは書かれていない（色・余白・枠が効き始める、とだけある）。
- 直し方（`design.md`）:
  - §7 に「外枠と fieldset の余白・枠が効き始めるので、住所1・2 の欄の絶対の幅は 600px → 約 518px に縮む」を足す。
  - §9 K5 の検証方法を、PO 承認済みの意味「フォームの横幅いっぱい」に合わせて書き換える。例: 「住所1・2 の欄の幅 ＝ それを囲む fieldset の内側の幅（`getBoundingClientRect` の差が 1px 以内）。外枠の `max-width` は 600px のまま」。
  - 絶対の幅を今と同じにしたい（PO の意図がそちら）なら、§4-5 e のうち外枠の `padding` と fieldset の `padding`・`border` だけは直さない（今のまま効いていない）と決め、§7 に理由を書く。どちらにするか PO に1つ聞いて決める（KGI の文言 `kgi.md:24` の「今のまま（フォームの横幅いっぱい）」を変えるなら PO 承認が要る）。

### R2. §4-4 国の部品の TSX の変更が抜けている

- 事実: 今の `frontend/src/pages/register/CountryCombobox.tsx` は、外枠が `style={{ position: "relative" }}`（`:55`）、一覧が `<ul style={{ position:"absolute", zIndex: 10, … }}>`（`:62-75` 付近）、行が `<li style={{ padding: "var(--spacing-2) var(--spacing-3)", … }}>`（`:81`）。設計 §4-4 は「新しい CSS を作る」と引数 `optionLabelFn` を書くが、(a) `import "./CountryCombobox.css";`、(b) 外枠に `className="register-combobox"`、(c) `<ul className="register-combobox__list">`、(d) `<li className="register-combobox__option">`、(e) 直書きの `style` の削除、が書かれていない。実装者がそのまま作ると CSS が当たらず、直書きも残って K14（差分の直書き 0 件）が ×。
- 直し方（`design.md` §4-4）: 上の (a)〜(e) を箇条で足す。あわせて「`zIndex` が 10 → `--z-dropdown`（50、`tokens.css:127`）に変わる」を §7 に1行足す。
- `RegisterAddressPage.tsx:75` の写し（`function CountryCombobox`）を消す指示は正しい（実物 `RegisterAddressPage.tsx:75-` に写しがある）。

### R3. K10 の試験（§6）が今のままでは書けない

- 事実: `backend/tests/test_invoice_pdf_address.py` は DB なしで、`_quote_pdf_address`（`invoices.py:128`）と描画だけを試す。`address` を作る `" ".join(...)`（`backend/app/routers/invoices.py:105`）は DB を読む `_fetch_address_snapshot` の中にあり、試験から呼べない。設計 §6 は「小さい関数に分けて試す」とだけ言い、§3-5 の変更後のコードには関数が無い。
- 直し方（`design.md` §3-5・§6）: §3-5 の変更を「`invoices.py` に `def _join_address_lines(row) -> str: return " ".join(filter(None, [row["address_line_1"], row["address_line_2"], row["address_line_3"]]))` を足し、`:105-107` を `"address": _join_address_lines(row),` にする」に書き換える。§6 の K10 の行は「`_join_address_lines` に住所1〜3の入った行を渡すと `"Line A Line B Line C"`、住所3が None・空なら今と同じ、を `test_invoice_pdf_address.py` に足す。さらに `_quote_pdf_address` の後の dict を `render_quote_pdf` に渡して `Line A Line B Line C` が描かれることを `drawn` で確かめる」と具体にする。

### R4. 設計書の行番号・場所の間違い（全部）

| 設計書の書き方 | 実物（origin/main） | 直し |
|---|---|---|
| §3-2 `RegisterChangeBillingPage.tsx:29`（billing 固定） | `frontend/src/pages/register/RegisterChangeBillingPage.tsx:28`（型 `address_type: "billing"`）・`:46`（初期値） | `:28`・`:46` に直す |
| §4-7 `CompanyAddressModal.tsx:87-98`（住所1〜3の `TextField`） | `frontend/src/pages/company-detail/CompanyAddressModal.tsx:117-127`（recon.md:19 は `:117-128` で正しい） | `:117-127` に直す |
| §4-8 `ShippingDetailPanel.tsx:422-430`（`TEXT_FIELDS.address.map`） | `frontend/src/components/ShippingDetailPanel.tsx:424-433`（`.map` は `:424`）。`handleSubmit` は `:277` | `:424-433` と `handleSubmit :277` に直す |
| §3-3 `update_company` の `addresses = update_data.pop(...)`「`:551` 付近」 | `backend/app/routers/companies.py:550` | `:550` に直す |
| §3-3 `_replace_addresses`（「定義の直前」） | `companies.py:227` | `:227` を書く |
| §4-6 住所3を足す位置 `RegisterChangeBillingPage.tsx` の住所2「`:342-348`」 | 住所2のラベルは `RegisterChangeBillingPage.tsx:342`、閉じるのは `:349` 付近（未確認の端） | 実装者が迷わないよう「住所2の `</label>` の直後」と書く |

- 合っていたもの（参考）: `base.py:10` の `import re`・`validate_email_loose` の直後に足す位置（`base.py:32`）／`registration_token.py:62-90` の `AddressInput`／`companies.py:479`／`invoices.py:105-107`・`:128-131`／`RegisterPage.tsx:200-207`・`:394-402`・`:454-476`／`RegisterAddressPage.tsx:44`／`tokens.css:198`・`:334`／`company-forms.css:17-31`・`App.tsx:137`（`company-forms.css` の import）／`.github/workflows/e2e.yml:294`（`if: false # 一時停止 2026-06-01`）。

## 軽い指摘（L・直さなくても作れる）

- L1. §3-2 の `ValueError("address_line_non_ascii")` は FastAPI の 422 で「Value error, address_line_non_ascii」になる。お客様のフォームは画面側で先に赤くするので通常は出ないが、直接送った時の帯（`RegisterPage.tsx` の 422 の組み立て・recon.md:54）に英語の符号がそのまま出る。画面の通る道では問題なし。
- L2. §3-3 `create_company`: 確かめを `_replace_addresses` の直前（`companies.py:479`）に置くと、会社の INSERT と deal の UPDATE の後で断ることになる。`get_db`（`backend/app/database.py:70-79`）が例外でロールバックするので残らないが、`explicit_code` の確かめの近く（`:396` 付近）に置くと無駄な INSERT が無い。
- L3. §4-7 の `lineErrors` は、窓の「種類」の切り替え（`handleAddressTypeChange`）で請求先に替えた時に消す指示が無い（送り先 → 請求先に替えても赤が残る）。切り替えで `setLineErrors({})` を足す。
- L4. §4-8 の文が崩れている（「`TextFieldControl` に `invalid` を付け、その下に…を出すため、この3つは `TextField` に替える」）。「住所1〜3の3つだけ `TextField`（`label`・`error`・`data-testid` 付き）に替える」の1文にする。`TextField` は `data-testid` を `...rest` で入力欄に渡す（`frontend/src/components/TextField.tsx:93`）ので、`ship-input-address1`（`frontend/tests-e2e/order-shipping.spec.ts:269`）は壊れない。
- L5. `TextField`（`.comp-field`）は `margin-bottom: var(--space-4)`（`frontend/src/components/FormField.css:21`）を持つ。登録フォームの縦並びは `gap: var(--spacing-3)` → `--space-3` に直るので、住所1〜3だけ余白が 16 + 12 = 28px になり、City など `<label>` のままの欄と間隔がずれる。§7 に「住所1〜3の下の間隔が他より広い」を書くか、E2E の撮影で PO に見せる。
- L6. `RegisterPage.tsx` は今 692 行。`check:page-size` の上限は 800 行（`frontend/scripts/check-page-size.js:19`）。住所3・TextField・エラー表示・TwoColumn を足すと近づく。実装の時に行数を見る。
- L7. §6 会社の受け口 ②③ の試験は `db_session` が要る。`backend/tests/test_companies.py` は今 `db_session` を使っていない（import は `tests.helpers_txn.create_lead` のみ）。`backend/tests/test_public_register_company.py:144` の「SQL で `company_addresses` を入れる」書き方を写し、`db_session` を引数に足す、と書くと迷わない。
- L8. §9 K11「vitest または e2e」は1つに決める。`CompanyAddressModal` には今 vitest も e2e も無い（`git grep` で試験側の参照が0件）ので、新しく作る前提を書く。発送の欄は既存の `frontend/src/components/SharedButtonMigration.test.tsx`（`t` は鍵をそのまま返すモック）に足せる。
- L9. §9 K13 の `git grep -n "x20-\\\\x7E"` は書き方のエスケープが読み手によってずれる。`git grep -nF 'x20-\x7E' -- backend/app frontend/src` と、試験を除く範囲を明示する。
- L10. §6 e2e: 住所1〜3を `TextField` に替えると、ラベルは `<label for>` で入力欄の外にある。既存の `register-form-ux.spec.ts` は担当者欄で `label.locator("input")`（`:96` 付近の C-2 など）を使うが住所の欄は触っていないので壊れない。新しい試験で住所の欄を探す時は `getByLabel` を使う、と書く。
- L11. 画面の `shippingChoice` の初期値は `"same"`（`RegisterPage.tsx:107`）。つまり開いた直後は請求先にも決まりが効く（日本語を打つと赤）。K8 の画面の操作として問題ないが、§4-6 に「初期値が same なので最初から効く」と書くと evaluator が迷わない。

## 1. 設計 §3（受け口）の確認結果（観点 2）

- 会社の PATCH の `addresses`: `update_data = data.model_dump(exclude_unset=True, mode="python")`（`companies.py:546` 付近）なので、`addresses` の各要素は dict で `address_type` は `AddressType`（Enum。`backend/app/schemas/company.py:47-49`）のまま。設計 §3-3 の `getattr(a_type, "value", a_type) != "delivery"` は Enum でも文字列でも正しく動く。`exclude_unset` で送られなかった列は dict に無いが、`_addr_lines` の `a.get(k)` が `None` を返し `or None` で空欄と同じに扱うので落ちない。
- 今ある決まり外の行をそのまま保存: 今の送り先の住所1〜3（DB の値）と、送られた行の住所1〜3が同じなら確かめを飛ばす → 通る。住所1〜3のどれかを変えると確かめが走る（D6 どおり）。同じ会社で電話だけ変える保存は受け口では通り、画面（§4-7）が止める（設計 §7 に既出）。
- 順序: `update_company` では会社の UPDATE（`companies.py:572`）より前に確かめるので途中まで書かれない。`create_company` は `get_db` のロールバックで残らない（L2）。
- 併合・`_replace_addresses` の本体は触らない方針で矛盾なし。
- `registration_token.py`: `AddressInput` に `model_validator(mode="after")` を足す方式は、`normalize_empty_strings`（before・`:77-85`）の後に走るので `""` は `None` になって通る。`/register/change-billing` は `AddressInput` を共用（`:160`）するが画面は `billing` 固定で決まりは効かない。直接 `address_type: "delivery"` で送られると、その時は決まりが効く（INSERT は `'billing'` 固定 `registration_tokens.py:575` 付近のままで害なし）。
- `order_shipping_detail.py`: 親が `BaseModel` の混ぜ込み（`_DeliveryAddressLinesCheck`）に `field_validator(..., check_fields=False)` を付ける形は pydantic 2.10.6（`backend/requirements.txt:8`）で成り立つ。`Response` は `Base` を継ぐ（`:135`）が混ぜ込みを継がないので読み出しは影響なし。`frontend/src/components/SharedButtonMigration.test.tsx:176` が住所3つとも `null` を送る形を期待するが、`None` は通るので壊れない。
- 既存試験の住所の値を全部 grep で確かめた（`backend/tests`・`frontend/src/**/*.test.*`・`frontend/tests-e2e`。`address_line_1〜3`・`address1〜3` に36文字超・英字等以外・改行・タブ）: 該当は次の1件だけ。
  - `backend/tests/test_order_shipping_details.py:316-325`（`nasty_addr = 'Line1, "Quoted"\nLine2'`）。設計 §6 が直す指示を書いている。直さないと POST が 422 になり、その後の `GET .../elogi-csv` が 200 にならず落ちる。設計の直し方（受取人の欄に改行を移す）で足りる（受取人は `recipient_name` で決まり対象外）。
  - ほかに `backend/tests/test_tenant_issuer_tables_pg.py:198`（`"address1": "千代田1-1"`）があるが、これは発行元（issuer）の表で、会社の住所でも注文ごとの発送でもないので対象外。
  - 住所を SQL で直接入れている試験（`backend/tests/conftest.py`・`test_invoice_totals_pg.py:247`・`test_public_register_company.py:144`）は受け口の型を通らないので影響なし。
- 他に決まり外の送り先が入る道（観点 6）: `git grep "company_addresses"` と `address1`/`address_line_1` の全走査で、書き込む所は `registration_tokens.py:328`・`:463`・`:572`（すべて `AddressInput` 経由・§3-2 で覆う）、`companies.py:244`（§3-3 で覆う）、`order_shipping_details.py` の INSERT／UPDATE（§3-4 で覆う）の3系統。`backend/app/services/issuer.py`・`suppliers.py`・`super_admin_suppliers.py`・`central_masters.py` の住所は発行元・仕入元で会社の送り先ではない。請求書の `ship_to_snapshot`（`backend/app/schemas/invoice.py:124-135`）は読み出し専用の写しで、画面 `InvoiceShipToSection.tsx` に入力欄が無い（読むだけ）。→ 抜けている道は見つからなかった。ただし FedEx の伝票を出す `backend/app/routers/shipping.py` は、リクエストに住所を直接受ける作りで、この設計の範囲外と書かれている（`decisions.md:69`・`design.md:12`）。範囲外のままでよいが、PO に「新しく決まり外の送り先が入らない」の対象に含まれない道が残ることは §7 に1行書く（L12）。
- L12. 上の通り、§7 に「FedEx 伝票の受け口 `POST /shipping/shipments` は決まりの対象外」と明記する。

## 2. 設計 §4（画面）の確認結果（観点 3）

- 未定義の変数: 直す対象6つ（`--spacing-N`・`--border-default`・`--color-red-500`・`--color-primary`・`--font-size-xs`・`--font-size-sm`）は `frontend/src` と `frontend/index.html` に定義が0件で、設計の言うとおり。置き換え先 `--space-N`（`tokens.css:74-79`）・`--border`（`:735`）・`--danger`（`frontend/src/index.css:53`・暗い画面 `:262`）・`--accent`（`tokens.css:736`）・`--font-xs`・`--font-sm`（`:14-15`）・`--radius-md`（`:97`）は定義あり。新しい `--field-w-xs`・`--max-width-public-form` は `tokens.css` の `:198`・`:334` の次に足す書き方で名前の衝突なし。CSS の新ファイルが使う `--z-dropdown`（`:127`）・`--dropdown-max-h`（`:388`）・`--min-width-dropdown`（`:316`）・`--bg-surface`（`:729`）・`--radius-sm`（`:96`）も定義あり。→ 未定義の変数は残らない（ただし `RegisterPage.tsx:482` 以降の直書きの `border: "2px solid var(--color-primary)"`（`:492`）の `2px` は設計の対象表にあるので置き換えで `--accent` になる。`2px` の枠は設計 §9 K14 の「`1px solid` の枠を除く」の外なので、検査の例外か、`1px` に変えるか、決めておくとよい＝L13）。
- L13. `RegisterPage.tsx:492` の `border: "2px solid var(--color-primary)"` は §9 K14 の「`[0-9]+px` が0件」に引っかかる。「`2px solid var(--accent)` の枠は例外」と書くか、既存の枠の変数（`--border-width-*` があれば）を使う。
- i18n: `addressRule.ascii`・`addressRule.maxLength` は `frontend/src/locales/ja.json`・`en.json` の最上位に今ない（`grep` 0件・最上位に `addressRule` のキー無し）。両方に同じキーを足す設計で `check:i18n-missing-keys` と合う。`{{max}}` の書式は両ファイルで既に使われている（`{{` が `ja.json` に282件）。vitest は `react-i18next` を `t: key => key` でモックする（`SharedButtonMigration.test.tsx:15`）ので `t(key, { max })` で落ちない。
- 見出し（K1）: `.page-container .page-header`（`company-forms.css:17-24`）は `display:flex; justify-content:space-between; align-items:flex-start`、`h1` は `margin: var(--space-2) 0 0`（`:27-31`）。登録フォームの外枠は既に `className="page-container"`（`RegisterPage.tsx:280`）で、`company-forms.css` は `App.tsx:137` で全画面に読み込まれる。公開ページの経路が `App` を通るかは設計が「全画面に読み込み済み」とだけ書いている＝実物の確認は evaluator の撮影で必須（`frontend/src/main.tsx` の経路は未確認）。
- 既存の e2e・vitest への影響: `frontend/tests-e2e/register-form-ux.spec.ts` が使うセレクタは `fieldset` の番号（`nth(1)`・`nth(2)`）と、担当者・都道府県・市区町村の `label`、`input[type=email|tel]`、`.error-banner`、`h1`。住所1〜3を `TextField` に替えても fieldset の数と順は変わらず、都道府県・市区町村は `<label>` のままなので壊れない（B-3 は設計どおり書き換える）。`h1` は `page-header` の中に入るが `page.locator("h1")` は変わらない。登録フォームを対象にした vitest は無い（`frontend/src/pages/register` に `*.test.*` が0件）。社内の画面の e2e `order-shipping.spec.ts:269` は `getByTestId("ship-input-address1")` で、`TextField` が `data-testid` を入力欄に渡すので壊れない。
- 国番号（K2）: `CountryCombobox` の選択済み表示は `entries.find((c) => displayFn(c) === value || c.code === value || c.dial === value)`（`CountryCombobox.tsx:31`）。`displayFn = c => c.dial` にすると、`value = "+1"` で最初に見つかる国の `dial` は同じ `"+1"` なので表示は「+1」になる（設計 §4-5 c の理由づけは合う）。`onChange` が受け取る値も `displayFn(c)` ＝ dial で、`combinePhone`（`RegisterPage.tsx:137`）が使う `telephone_dial` と一致する。`find` を消す提案も妥当（`update…("telephone_dial", val)`）。
- `TwoColumn`（`frontend/src/components/TwoColumn.tsx:11-26`）に `ratio="1:1"`・`gap="4"` はある（`TwoColumnGap` は `'2'|'3'|'4'|'6'`）。

## 3. 設計 §6（試験）が書けるか（観点 4）

| 試験 | 判定 | 補足 |
|---|---|---|
| 決まりの関数・お客様の型・発送の型（pytest・DB なし） | 書ける | 設計の値で足りる |
| お客様の受け口（`test_public_register_company.py`） | 書ける | `_form()`（`:36-62`）の請求先・送り先の住所1を書き換えれば足りる |
| 会社の受け口（K12 ①②③） | 書ける（L7 を足せば） | `db_session` の引数追加が要る |
| 見積書（K10） | **今のままでは書けない** | R3 |
| 既存試験の直し | 書ける | §1 のとおり。直す先の文字列でも CSV の再パースは通る（csv モジュールが改行を引用符で包む。`test_order_shipping_details.py:331` で `csv.reader` を使っている）が、`data[11]`（受取人の列）が `nasty_recipient` と一致するかは eLogi の出力で改行が変わらないか未確認。実装の時に試験を流して確かめる |
| 画面の決まり（vitest） | 書ける | `frontend/vitest.unit.config.ts` の `include: ['src/**/*.test.{ts,tsx}']` に入る |
| 国番号 191 か国（K2） | vitest は「表示の文字列」まで書ける | jsdom には画面の幅（`scrollWidth`）が無いので、欠けないことの確認は e2e（設計も分けている）。191 件を数える元は `COUNTRIES`（`frontend/src/constants/countries.ts:20`） |
| 画面の並び（e2e） | 書ける（CI は止まっている `e2e.yml:294`） | evaluator の手元実行が前提と設計に書かれている |

## 4. 設計 §9 受入表 K1〜K14 が ○× で判定できるか（観点 5）

| K | 判定 | 理由・直し |
|---|---|---|
| K1 | ○× できる | 位置の数値で判定。公開ページが `company-forms.css` を読むかは撮影で確認（上記） |
| K2 | ○× できる | 幅は `.field-w-xs` を付けた外枠の div の幅（80px）。欄の中身の欠けは e2e の `scrollWidth <= clientWidth` |
| K3 | ○× できる | 「City の幅＝住所1の幅」は R1 の変更後も成り立つ（同じ fieldset の内側幅） |
| K4 | ○× できる | 操作で判定 |
| K5 | **判定できない（×にしかならない）** | R1 |
| K6〜K8 | ○× できる | 画面の操作＋pytest。K8 は `shippingChoice` の初期値が same（L11） |
| K9 | ○× できる | 送る中身は e2e の mock で `address_line_3` を見る。「保存された住所3」は本番の目視か pytest（`test_public_register_company.py`） |
| K10 | pytest 部分が R3 のため今は書けない | 本番の目視は ○× できる |
| K11 | 「vitest または e2e」を1つに（L8） | それ以外は ○× できる |
| K12 | ○× できる | 反映前後の本番の読み取り（件数）と pytest ②③ |
| K13 | ○× できる（L9 を直せば） | 数える検索の書き方を直す |
| K14 | 条件つきで ○× できる | `2px` の枠（L13）・`--field-w-xs` の `80px`（`field-size.css` は例外に入っている） |

## 5. recon.md・decisions.md・kgi.md・ADR-126 追補との食い違い

- `decisions.md` の行番号（`RegisterPage.tsx:385`・`:396`・`:614`・`:625`・`:635`、`RegisterAddressPage.tsx:375`・`:385`・`:395`、`RegisterChangeBillingPage.tsx:331`・`:342`）は実物と全部一致。
- `recon.md:19` の `CompanyAddressModal.tsx` の住所は `:117-128` で実物（`:117-127`）とほぼ一致。`design.md` §4-7 の `:87-98` だけが違う（R4）。
- ADR-126 追補の「決まりの正本は受け口 `validate_delivery_address_line` と画面 `deliveryAddressLineError` の2か所」は design §2 と一致。ただし §3-3 の `_check_new_delivery_lines` は同じ関数を呼ぶだけで決まりを複製しないので K13 の「受け口1か所」と矛盾しない。
- `design.md:5` が指す `ideal-state.md`・`evidence-local.md` は枝の中にある（`docs/specs/customer-address-form/ideal-state.md`・`docs/handoff/customer-form-layout/evidence-local.md`）。`design.md:327` の `card.md` は枝にまだ無い（段取りの2番で作る前提なので問題なし）。
- 設計書の言う「`origin/main` = a12741e7」は実物の `origin/main` と一致（確認: `git rev-parse origin/main` = a12741e7234b7fe2ec40a790a8aa3422e0d6eaa4）。

## 6. 審査していないこと（未確認）

- pytest・vitest・e2e・`npm run check:all` は流していない。設計どおりに作った時に CI が緑になるかは未確認。
- 本番の住所の数（decisions.md の表）は本番の読み取りが要るので追っていない（設計書の記述のまま）。
- 公開ページ（`/register`）の経路で `company-forms.css` が効くか、`h1` の見た目が実際にどう変わるかは、画面を開いていないので未確認（R1 と合わせて evaluator の撮影で確かめる）。
- `eLogi` の CSV 出力で受取人の改行がどう扱われるか（§3 表の既存試験の直し）は未確認。
