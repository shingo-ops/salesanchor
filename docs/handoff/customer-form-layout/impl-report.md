本報告はカード customer-form-layout/card.md の実行結果である
DONE（ただし下の「差異・注意」3点を読むこと）

## §1 作業前の点検（1行ずつ）

- 設計の sha: `origin/release/customer-form-pc-layout-design` = 8b111e4504871619a4eac03320c1cac9d144b710（依頼文の 8b111e450 と一致）
- `backend/app/schemas/base.py`: `def validate_email_loose` あり（32行）・`DELIVERY_ADDRESS_LINE_MAX` なし ✔
- `backend/app/routers/invoices.py` 106行: `            filter(None, [row["address_line_1"], row["address_line_2"]])` ✔
- `companies.py`: `async def _replace_addresses(` 1か所（227行）・`await _replace_addresses(db, new_id, data.addresses)` 1か所（479行）・`addresses = update_data.pop("addresses", None)` 1か所（550行） ✔
- `tokens.css`: `--field-w-lg-max`（198行）・`--max-width-form`（334行）あり、`--field-w-xs`・`--max-width-public-form` なし ✔
- `RegisterAddressPage.tsx` に `function CountryCombobox`（76行）あり ✔

## 手順ごとの commit

| 手順 | sha | 中身 |
|---|---|---|
| 0 | 393919a14 | 設計の取り込み（`git merge --no-ff --no-edit` を1回。衝突なし） |
| 1 | 7ef3f6c7e | base.py の決まり・registration_token.py の検査・test_delivery_address_rule.py |
| 2 | 6495808e1 | companies.py の受け口・test_companies.py の3試験 |
| 3 | 1d20d9933 | invoices.py の `_join_address_lines`・見積書の試験・nasty_addr/nasty_recipient の差し替え |
| 4 | 7d184719f | tokens.css・field-size.css・addressRules.ts(+test)・ja/en の翻訳 |
| 5 | d5b56d22e | 国の部品（optionLabelFn・CountryCombobox.css・試験）・RegisterAddressPage の写しを削除 |
| 6 | 6468a6d33 | 3つの公開フォーム |
| 7 | c046aba9c | CompanyAddressModal・ShippingDetailPanel と試験 |
| 8 | 60677943a | register-form-ux.spec.ts（B-3 書き換え・K1・K2・K5・K6〜K9） |

## 差異・注意（カードの文と実物が違った所）

1. **手順1と手順3の境界**: 発送の型（設計 §3-4 の `order_shipping_detail.py`）はカードでは手順3だが、手順1の試験 `test_delivery_address_rule.py` が発送の型を試すので、手順1の commit に入れた。内容は設計どおり。
2. **§4「`git grep -nF 'x20-' … が base.py 1件と addressRules.ts 1件だけ」は文のとおりにならない**: 今回の変更で足したのはその2件だけだが、もとからある `backend/app/services/tcg_analyzer_svc.py`（248・296行）と `backend/app/services/tcg_keyword_lint.py`（25行）にも `x20-` がある（下の生出力）。設計 K13 の確かめ方の想定漏れ。これらは触っていない（カードの範囲外）。
3. **§4「`npm run lint` が 0 件」**: `npm run lint`（`eslint src`）は終了コード 0・エラー 0 だが、警告が 58 件ある。今回の差分で変えた frontend/src のファイル全部に `--max-warnings 0` をかけると 0 件（終了コード 0）。58 件は今回触っていないファイルの既存の警告（未検証: 変更前の件数は数えていない）。
4. 設計 §6 の「国番号191か国」は実物の `COUNTRIES` が **190 件**。試験は件数の固定値を使わず全件を回す形にした（vitest は `COUNTRIES.length > 0`・e2e は全件）。
5. 設計 §6「お客様の受け口」の `test_public_register_company.py` への試験追加は、カードの手順1〜8に書かれていないので足していない。既存の `test_public_register_company.py` は通る（下の pytest）。
6. DB の試験は、手元（Python 3.12 の使い捨て venv）で SQLite の試験環境のまま動いた（Postgres は使っていない）。Postgres での確認は CI に任せる。
7. e2e は `/opt/pw-browsers/chromium` を指す一時の設定ファイル（コミットしていない・削除済み）で手元の Chromium で流した。K5 の「変更前との比べ」は行っていない（evaluator の担当）。測った幅は 1280px 幅で住所1=600・住所2=600・外枠=600。

## §4 の生出力

保存先（scratchpad）: `/tmp/claude-0/-home-user-salesanchor/e9eea1e5-9103-5f4a-9336-829edabb02f4/scratchpad/` の `sec4.txt`・`sec4-pytest.txt`・`sec4-lint-changed.txt`・`step8-e2e.txt` ほか。以下は `sec4.txt` から。

```
## vitest
 Test Files  4 passed (4)
      Tests  39 passed (39)
## tsc
tsc-exit=0
## lint
✖ 58 problems (0 errors, 58 warnings)
lint-exit=0
## locale
true ascii,maxLength ascii,maxLength
## grep position   （`style={{ position` in CountryCombobox.tsx）
exit=1   （0件）
## grep vars   （spacing-|border-default|color-red-500|color-primary|font-size-xs|font-size-sm in pages/register）
exit=1   （0件）
## grep x20
backend/app/schemas/base.py:43:_DELIVERY_ADDRESS_LINE_RE = re.compile(r"^[\x20-\x7E]*$")
backend/app/services/tcg_analyzer_svc.py:247:# 純ASCII語判定: 0x20-0x7E のみで構成
backend/app/services/tcg_analyzer_svc.py:248:_RE_PURE_ASCII = re.compile(r"^[\x20-\x7e]+$")
backend/app/services/tcg_analyzer_svc.py:296:      if (/^[\\x20-\\x7e]+$/.test(kw)) {
backend/app/services/tcg_keyword_lint.py:25:_RE_PURE_ASCII = re.compile(r"^[\x20-\x7e]+$")
frontend/src/utils/addressRules.ts:3:const PRINTABLE_ASCII = /^[\x20-\x7E]*$/;
## wc
715 frontend/src/pages/register/RegisterPage.tsx
```

pytest（3ファイル＋関連。`--no-cov`）:

```
tests/test_delivery_address_rule.py tests/test_invoice_pdf_address.py tests/test_order_shipping_details.py
  → 52 passed（手順3の時点）
上の3つ＋ tests/test_companies.py tests/test_public_register_company.py
  → 79 passed, 8 warnings
```

e2e（`register-form-ux.spec.ts -g "B-3|K1|K2|K5|K6|K7|K8|K9"`・手元の Chromium）:

```
K1 ×3（/register・/register/change-billing・/register/address） ✓
B-3 ✓  K5 ✓（K5 width: line1=600 line2=600 outer=600）
K6 ✓  K7 ✓  K8 ✓  K9 ✓
K2 ✓（COUNTRIES 190 件すべて scrollWidth <= clientWidth・欄の幅 80px）
10 passed (33.5s)
```

差分一覧（`git diff --stat origin/main...HEAD`）は 41 ファイル。内訳は、設計の取り込みで入った docs・台帳（docs/handoff/customer-form-layout/*・docs/specs/customer-address-form/*・ADR-126 追補・docs/adr/README.md・docs/specs/README.md・field-size 設計書・`.claude-pipeline/active-work.d/release-customer-form-pc-layout-design.md`）と、カード §2 の触るファイル。`migrations/`・`.github/`・`components/CountryCombobox.tsx`・`constants/countries.ts`・`registration_tokens.py`・`useCompanyDetail.ts` は変えていない。

## 残り（この報告の範囲外）

- K5 の前後比べ・撮影・PO 目視は evaluator。
- Postgres での pytest・本番での K10・K12 の確かめは CI／反映後。
- PR は作っていない・マージしていない。
