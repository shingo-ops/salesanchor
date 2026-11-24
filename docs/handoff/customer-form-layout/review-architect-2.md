# 設計審査 2回目（architect）— customer-address-form

- 審査した物: `origin/release/customer-form-pc-layout-design`（fb0868741）の `docs/handoff/customer-form-layout/design.md`・`card.md`、1回目の `review-architect-1.md`（同じ枝）。差分は `git diff a774e7a10 fb0868741 -- docs/handoff/customer-form-layout/design.md` で読んだ。
- 突き合わせた実物: `origin/main`（作業場所の HEAD = 24cf739cd）。設計書の基準 a12741e7 からの差分を、設計が触る `frontend/src/pages/register`・`backend/app/routers/{invoices,companies}.py`・`backend/app/schemas`・`frontend/src/tokens.css`・`CompanyAddressModal.tsx`・`ShippingDetailPanel.tsx` で取ったところ 0 件（行番号は a12741e7 と同じ）。
- 読むだけ。製品のコード・DB・本番には触っていない。pytest・vitest・e2e は流していない（読んで確かめた結果）。

## 判定: REVISE（直す必要）

1. 1回目の R1〜R4 は中身が直っている。特に R1（外枠の padding と全 fieldset の border・padding を 0・none と書く）は、今の計算の値と同じになり、住所1の幅は変わらない（下の §1）。
2. ただし直しの中で新しい間違いが2件出た。(a) `design.md` §3-5 と `card.md` §1 の見積書の行番号が1行ずれており、カードの作業前の点検をそのまま流すと実装者が必ず `BLOCKED:` になる（R1'）。(b) §4-7 の `handleAddressTypeChange` は、触らない `useCompanyDetail.ts` の中の関数で、設計の書き方では作れない（R2'）。
3. 上の2件を直せば作れる。ほかは軽い指摘（L）。

## 直す点（R）

### R1'. 見積書の行番号が1行ずれている（`design.md` §3-5・`card.md` §1）

- 事実: `backend/app/routers/invoices.py` の実物は `:105` が `        "address": " ".join(`、`:106` が `            filter(None, [row["address_line_1"], row["address_line_2"]])`、`:107` が `        ),`。
- 設計 §3-5 は「`:104-106` の `"address": " ".join(` から `),` までの3行」と書いているが、実物は `:105-107`（`:104` は `"postal_code": row["zip"],`）。
- `card.md` §1（13行目）は「`invoices.py` の 105 行が `filter(None, [row["address_line_1"], row["address_line_2"]])`」と書いているが、105 行は `"address": " ".join(`。`filter(None, …)` は 106 行。→ カードの最初の点検が違うので、実装者は何も始められず `BLOCKED:` で止まる。
- 直し方:
  - `design.md` §3-5 の `:104-106` を `:105-107` に直す。
  - `card.md` §1 の「105 行が」を「106 行が」に直す。

### R2'. §4-7 の `handleAddressTypeChange` は窓の中の関数ではない（`design.md` §4-7）

- 事実: `handleAddressTypeChange` は `frontend/src/pages/company-detail/useCompanyDetail.ts:224` の中で定義され、`CompanyAddressModal.tsx:24` で props として受け取るだけ（`:92` で `onChange={(e) => handleAddressTypeChange(…)}` と呼ぶ）。
- 設計 §4-7 の4つ目の箇条「窓の種類の切り替え（`handleAddressTypeChange`）で `setLineErrors({})` を呼ぶ」は、`lineErrors` が窓（`CompanyAddressModal.tsx`）の状態なので、`useCompanyDetail.ts` の中では呼べない。一方、設計 §5・`card.md` §2 は `useCompanyDetail.ts` を「触らない」にしている。実装者はどちらを守るか迷う。
- 直し方（`design.md` §4-7）: 「窓の種類の選択（`CompanyAddressModal.tsx:92` の `onChange`）を `(e) => { setLineErrors({}); handleAddressTypeChange(e.target.value as "billing" | "delivery"); }` に替える。`useCompanyDetail.ts` は触らない」と書く。

## 1. 1回目の R1〜R4 が直っているか（観点 1）

| 1回目 | 結果 | 根拠 |
|---|---|---|
| R1（K5 と §4-5 e の矛盾） | 直っている | 下の詳細 |
| R2（国の部品の TSX の変更） | 直っている（行番号の小さい誤りは L1） | `design.md` §4-4 に (a)〜(e) が入り、`zIndex` の変更は §7 にもある |
| R3（K10 の試験が書けない） | 試験の形は直っている。行番号だけ R1' | §3-5 に `_join_address_lines`、§6 に具体の試験。`invoices.py` の SELECT は `a.address_line_3` を既に読んでいる |
| R4（行番号6件） | 直っている | 下の表 |

### R1 の詳細（外枠・fieldset を `0`・`none` と書けば幅は今と同じか）

- 未定義の確認: `grep -rnE -e "--(spacing-[0-9]+|border-default|color-red-500|color-primary|font-size-xs|font-size-sm):" frontend/src frontend/index.html` は 0 件。つまり今の `padding: "var(--spacing-6)"`（外枠）と、fieldset の `border: "1px solid var(--border-default)"`・`padding: "var(--spacing-4)"` は、計算の時点で無効になり、初期値（余白 0・枠なし）。インラインの宣言が優先で勝つので、`company-forms.css:12-15` の `.page-container { padding: var(--space-2) var(--space-8); }` にも戻らない。
- 外枠: 4つの外枠（各フォームの読み込み中・エラー・期限切れの3つ＋本体）は `RegisterPage.tsx:249, :257, :265, :280`・`RegisterAddressPage.tsx:264, :272, :280, :293`・`RegisterChangeBillingPage.tsx:203, :211, :219, :227` で、すべて同じ `style={{ maxWidth: "600px", margin: "0 auto", padding: "var(--spacing-6)" }}`。`padding: 0` と書けば今の計算の値と同じ。
- fieldset: `RegisterPage.tsx:299, :482, :492`・`RegisterAddressPage.tsx:311`・`RegisterChangeBillingPage.tsx:245` の5つが `border`・`padding` に未定義の変数を使っている。設計 §4-5 e は「3フォームのすべての `<fieldset>`」の `border` と `padding` を `"none"`・`0` と書くので、5つとも今と同じ。`:492` の `2px solid var(--color-primary)` も今は無効（枠なし）なので `none` で同じ。
- よって外枠の内側の幅も fieldset の中の幅も変わらず、住所1の幅は今と同じ（1280px の画面で 600px）。§7（`design.md:299`）と §9 K5・K14 の文もこれと矛盾しない。
- 注意（L2）: `fieldset` の `marginBottom`・`legend` の字・`gap` は置き換えで効き始めるが、これは横幅に効かない（§7 に既出）。

### R4 の行番号（実物と照合）

| 設計書 | 実物 | 結果 |
|---|---|---|
| §3-2 `RegisterChangeBillingPage.tsx:28`・`:46` | `:28` `address_type: "billing";`・`:46` `address_type: "billing",` | 合っている |
| §4-7 `CompanyAddressModal.tsx:117-127` | 住所1〜3の `form-row` が `:117-127` | 合っている |
| §4-8 `ShippingDetailPanel.tsx:424-433`・`handleSubmit :277` | `.map` は `:424`・`handleSubmit` は `:277` | 合っている |
| §3-3 `companies.py:550`・`:227`・`:479` | `:550` `addresses = update_data.pop(…)`・`:227` `async def _replace_addresses(`・`:479` `await _replace_addresses(db, new_id, data.addresses)` | 合っている |
| §4-6 `RegisterChangeBillingPage.tsx` 住所2の `</label>` の直後 | `:342` のコメント → `:343-349` の `<label>…</label>` | 合っている（書き方どおり迷わない） |
| §3-1 `base.py` の `import re`（10 行目）・`validate_email_loose` の直後 | `:10` `import re`・`:31` が `def validate_email_loose` | 合っている |
| §4-1 `tokens.css:198`・`:334`・`:127` | `--field-w-lg-max`・`--max-width-form`・`--z-dropdown` | 合っている |
| §4-6 `RegisterPage.tsx:200-207`・`:394-402`・`:107`、`RegisterAddressPage.tsx:44` | 実物と合う | 合っている |

## 2. 直しで新しい食い違いが出ていないか（観点 2）

- 出ているもの: R1'・R2'（上）。
- 出ていないもの: §3-3 の `companies.py` の行・§4-1 の `tokens.css` の行・§4-7 の窓の行・§4-8 の発送の行・§9 の K5・K13・K14 の文は互いに合っている。K14 の `[0-9]+px` は、登録フォームの `600px`・`140px`・`200px` が変数・CSS 側に移る前提で、差分の追加行を数える形なので成り立つ（`CountryCombobox.css` の `1px solid` だけが例外と書かれている）。
- L の指摘は下。

## 3. card.md が design.md と合い、実装者が迷わず作れるか（観点 3）

- 触る物: 設計 §5 の左の列と、新しく作る 6 ファイル（`addressRules.ts`・`addressRules.test.ts`・`CountryCombobox.css`・`CountryCombobox.test.tsx`・`CompanyAddressModal.test.tsx`・`test_delivery_address_rule.py`）が設計 §4・§6 と一致する。
- 手順 1〜8 は設計の節と1対1で対応している。「そのまま足す」「設計 §6 どおり」の指す先がどれも実在する。
- 確かめの命令: §4 の各 grep・vitest・tsc・`node -e` の i18n 確認は書いたとおりに流せる形。想定分岐（設計と実物が違う時は `BLOCKED:`・80px で欠けたら `NEEDS_DECISION:`・見張りに止められたら `BLOCKED:`）も揃っている。
- 作れない点は R1'（作業前の点検が通らない）と R2'（設計 §4-7 の矛盾）だけ。直せばカードどおりに作れる。

## 軽い指摘（L・直さなくても作れる）

- L1. `design.md` §4-4 の (b)「外枠の `<div style={{ position: "relative" }}>`（`:55`）」は実物では `CountryCombobox.tsx:46`（`:55` は `setOpen(true)` の周辺）。(c) `:62-75` と (d) `<li>`（`:78` 開始・`style` は `:80-83`）は付近で合っている。また「`RegisterAddressPage.tsx:75-` の写し」は、`:75` が直前のコメントで、`function CountryCombobox(` は `:76`。実装者は文字列で探せば迷わない。
- L2. `design.md` §4-5 e の「3フォームのすべての `<fieldset>`」は、実物では5つ（上の R1 の詳細）。また外枠は各ファイルに4つ（読み込み中・エラー・期限切れ・本体）ある。§4-5 a の「外枠」は「4つとも」と書くと、実装者が読み込み中の画面の外枠を直し忘れて `--spacing-6` が残るのを防げる。`card.md` §4 の `git grep "spacing-\|…"`（0 件）が最後の網になるので、直さなくても気づける。
- L3. `design.md` §4-8 などが引く `TextField.tsx:93` は、実物では `TextFieldControl id={fieldId} {...rest}` が `:95`（`:93` は `</label>`）。`data-testid` が入力欄に渡る事実は合っている。
- L4. `card.md` §4 の pytest は `test_delivery_address_rule.py` だけ。`test_invoice_pdf_address.py`（DB なし・設計 §6 で足す）と `test_order_shipping_details.py`（直す試験）も流すと手順 3 の確かめになる。`test_order_shipping_details.py` が DB を要するなら、「手元で動かなければ書いて CI で確かめる」の既存の文に任せてよい。
- L5. `RegisterPage.tsx` は今 692 行（`check:page-size` の上限 800 行・1回目の L6）。実装後に行数を見るようカードに1行足すとよい（直さなくても `npm run check:all` が止める）。
- L6. 1回目の L1・L8 ほかは、設計の改訂で反映済みか影響の無いもの。再指摘なし。

## 審査していないこと（未確認）

- pytest・vitest・e2e・`npm run check:all` は流していない。設計どおりに作った時に CI が緑になるかは未確認。
- 公開ページ（`/register`）で `company-forms.css` の `page-header` が実際に効くか、`h1` の見た目は、画面を開いていないので未確認（evaluator の撮影で確かめる前提）。
- `.field-w-xs` を付けた外枠 div の中の `TextFieldControl` が 80px いっぱいに広がるかは未確認（K2 の e2e で確かめる前提）。
- 本番の住所の数（decisions.md の表）は本番の読み取りが要るので追っていない。
