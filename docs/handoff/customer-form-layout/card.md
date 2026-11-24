# 実装カード: お客様の登録フォームの並びと、送り先の住所の決まり

- 区分: B-2（backend 5 ファイル・frontend 13 ファイル・試験。migration・deploy 設定・本番 scripts なし）
- 枝: 作業は `release/customer-form-pc-layout-impl`（`bash scripts/new-worktree.sh release/customer-form-pc-layout-impl` で作る）。設計 docs は `origin/release/customer-form-pc-layout-design` にあり、手順0で取り込む
- 設計: `docs/handoff/customer-form-layout/design.md`（以下「設計」）・recon: 同 `recon.md`・審査: 同 `review-architect-*.md`
- 読んだ節: `docs/handoff/design-partner-card-ops/guards/00-common.md`（1手順1コマンド・待たない・報告に無い出力を成功と扱わない）・`03-file.md`（既存ファイルの変更は逐語の基準行で）・`10-executor.md`。照合: 本カードはプレースホルダ無し・sleep 無し・削除の命令無し・PR 作成とマージ無し。
- 受領確認: 作業を始める前に、このカードの「1. 作業前の点検」の結果を1行ずつ書き出す。

## 1. 作業前の点検（どれか違えば停止して `BLOCKED:` に違った行を書く）

- `git rev-parse origin/release/customer-form-pc-layout-design` が依頼文に書いた sha。
- `backend/app/schemas/base.py` に `def validate_email_loose` がある。`DELIVERY_ADDRESS_LINE_MAX` がまだ無い。
- `backend/app/routers/invoices.py` の 106 行が `            filter(None, [row["address_line_1"], row["address_line_2"]])`。
- `backend/app/routers/companies.py` に `async def _replace_addresses(` が1か所・`await _replace_addresses(db, new_id, data.addresses)` が1か所・`addresses = update_data.pop("addresses", None)` が1か所。
- `frontend/src/tokens.css` に `--field-w-lg-max` と `--max-width-form` があり、`--field-w-xs` と `--max-width-public-form` が無い。
- `frontend/src/pages/register/RegisterAddressPage.tsx` に `function CountryCombobox` がある。

## 2. 触るもの／触らないもの

- 触る: 設計 §5 の左の列のファイルだけ。新しく作るのは `frontend/src/utils/addressRules.ts`・`addressRules.test.ts`・`frontend/src/pages/register/CountryCombobox.css`・`CountryCombobox.test.tsx`・`frontend/src/pages/company-detail/CompanyAddressModal.test.tsx`・`backend/tests/test_delivery_address_rule.py`。
- 触らない: 設計 §5 の右の列。特に `migrations/`・`.github/`・`components/CountryCombobox.tsx`・`constants/countries.ts`・`registration_tokens.py`・`useCompanyDetail.ts`。

## 3. 手順（commit は手順ごとに1つ。commit 文は Write でファイルに書き `git commit -F`）

- 手順0 設計の取り込み: 作業場所で `git merge --no-ff --no-edit origin/release/customer-form-pc-layout-design` を1回だけ流す（設計 docs と台帳が入る。ぶつかったら止めて `BLOCKED:`）。このカードで許す取り込みはこの1回だけ。

- 手順1 受け口の決まり: 設計 §3-1・§3-2 のコードをそのまま足す。試験 `backend/tests/test_delivery_address_rule.py` を設計 §6 の上3行どおりに作る。
- 手順2 会社の受け口: 設計 §3-3 をそのまま足す。`test_companies.py` に設計 §6 の ①②③ を足す（②の行は SQL の INSERT で入れる。会社の作り方は同じファイルの既存の試験の作り方に合わせる）。
- 手順3 発送と見積書: 設計 §3-4・§3-5。`test_order_shipping_details.py` の `nasty_addr`・`nasty_recipient` を設計 §6 どおりに替える。`test_invoice_pdf_address.py` に住所3の試験を足す。
- 手順4 変数・幅の金型・翻訳・決まりの関数: 設計 §4-1〜§4-3。`addressRules.test.ts` を設計 §6 どおり。
- 手順5 国の部品: 設計 §4-4。`CountryCombobox.test.tsx` を設計 §6 どおり。
- 手順6 3つの公開フォーム: 設計 §4-5・§4-6。
- 手順7 社内の窓と発送の欄: 設計 §4-7・§4-8。試験は設計 §6 の「社内の窓・発送の欄（K11）」の行どおり。
- 手順8 e2e: `frontend/tests-e2e/register-form-ux.spec.ts` の B-3 を設計 §6 の最後の行どおりに書き換え、K1・K2・K6〜K9 の試験を足す（K5 の前後比べは evaluator が行うので、ここでは住所1の幅を測る試験だけ足す）（API は既存の試験と同じく `page.route` で mock）。

## 4. 確かめ（全部の生出力をそのまま報告に貼る）

- `cd frontend && npm ci` の後 `npx vitest run --config vitest.unit.config.ts src/utils/addressRules.test.ts src/pages/register/CountryCombobox.test.tsx src/pages/company-detail/CompanyAddressModal.test.tsx src/components/SharedButtonMigration.test.tsx` が全部 passed。
- `cd frontend && npx tsc --noEmit -p tsconfig.json` が 0 件。`npm run lint` が 0 件。
- `cd frontend && node -e "const a=require('./src/locales/ja.json'),b=require('./src/locales/en.json');console.log(!!a.addressRule&&!!b.addressRule,Object.keys(a.addressRule||{}).join(),Object.keys(b.addressRule||{}).join())"` が `true ascii,maxLength ascii,maxLength`。
- `git grep -n "style={{ position" -- frontend/src/pages/register/CountryCombobox.tsx` が 0 件。
- `git grep -n "spacing-\|border-default\|color-red-500\|color-primary\|font-size-xs\|font-size-sm" -- frontend/src/pages/register` が 0 件。
- `git grep -nF 'x20-' -- backend/app frontend/src ':!*.test.*'` が `backend/app/schemas/base.py` 1件と `frontend/src/utils/addressRules.ts` 1件だけ。
- `cd backend && python -m pytest tests/test_delivery_address_rule.py tests/test_invoice_pdf_address.py tests/test_order_shipping_details.py -q` が全部 passed。DB の要る試験は手元で動かなければその旨を書き、CI で確かめる。
- `wc -l frontend/src/pages/register/RegisterPage.tsx` が 800 未満。
- `git diff --stat origin/main...HEAD` が、docs・台帳・§2 の触るファイルだけ。

## 5. 想定分岐

- 設計のコードがその場所の実物と合わない（行が無い・名前が違う）時は、合わせて書き換えず停止して `BLOCKED:` に、設計の節・実物のファイル:行・違いを書く。
- `TextField` に替えたことで既存の vitest・e2e のセレクタが外れたら、セレクタを `getByLabel` か `data-testid` に直してよい。試験の意味（何を確かめるか）は変えない。
- 80px で国番号が欠ける（K2 の試験が赤）時は、幅を変えず停止して `NEEDS_DECISION:` に欠けた国番号と `scrollWidth`・`clientWidth` を書く。
- 未定義の変数を直して、既存の画面試験が見た目の違いで赤になったら停止して `NEEDS_DECISION:`。
- 見張りに止められたら言い換えず停止して `BLOCKED:` に見張りの文を全文書く。

## 6. 報告の形

1行目「本報告はカード customer-form-layout/card.md の実行結果である」、2行目 `DONE` / `BLOCKED: 理由` / `NEEDS_DECISION: 理由`、3行目から手順ごとの commit sha と §4 の生出力。push の前に `git log --oneline -10` で手順0の取り込みと手順ごとの commit があることを確かめ、push は `git -C` の後に new-worktree.sh が作った作業場所の絶対パスを字で書き `push -u origin release/customer-form-pc-layout-impl` を単独で流す。PR の作成・マージはしない。

END OF CARD
