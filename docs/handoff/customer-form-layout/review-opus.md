# review-package-v1 — PR #5718（customer-form-layout 実装）

- 審査役: Claude Opus（reviewer・読むだけ）・2026-11-24
- 対象: `git diff origin/main...3943c9c75`（42 ファイル）。
- head の付け替え: PR の head は審査の途中で `a0a118a4e`（`71cae5cb7` の main を merge commit で取り込んだもの）に変わった。`git diff 3943c9c75 a0a118a4e -- backend frontend migrations .github scripts` は 0 行。`git diff 71cae5cb7...3943c9c75 -- backend frontend` と `git diff 71cae5cb7...a0a118a4e -- backend frontend` は同じ（diff で SAME）。**この判定は 3943c9c75 の製品差分に対するもので、a0a118a4e でも製品差分は同じ。**
- 照らし合わせたもの: decisions.md（D1〜D6）・kgi.md（K1〜K14）・design.md・card.md・review-architect-1/2.md・impl-report.md

## 判定: REQUEST_CHANGES（直すのは1か所・小さい）

止める理由は R1 の1件だけ。それ以外は設計・カードのとおりで、範囲から外れた変更は見つからなかった。

---

## R1（止める理由）受け口の決まりが、末尾に改行がある住所を通す

- 場所: `backend/app/schemas/base.py:43`（`re.compile(r"^[\x20-\x7E]*$")`）と `:50`（`.match(value)`）
- 【事実】Python の `$` は「文字列の最後」のほかに「最後の改行の直前」にも当たる。手元で実際に呼んで確かめた:
  - `validate_delivery_address_line('abc\n')` → `'abc\n'` が返る（断らない）
  - `AddressInput(address_type='delivery', address_line_1='x'*34+'\n')` → 通る
  - `OrderShippingDetailCreate(address1='Main St\n')` → 通る
  - `re.compile(r'^[\x20-\x7E]*$').fullmatch('abc\n')` → 当たらない（`fullmatch` なら断る）
- 【事実】画面側 `frontend/src/utils/addressRules.ts:3` の `/^[\x20-\x7E]*$/`（m フラグなし）は末尾の改行も断るので、受け口と画面で答えが違う。
- 起きること（例）: 画面を通さず `POST /api/v1/register/...` や `POST /api/v1/orders/{id}/shipping` に `"address1": "1-2 Main St\n"` を送ると保存される。設計 §2 の表（K6・K7・K13 の正本）は「改行・タブ…は断る」と書いており、K7 の「画面を通さず直接送っても受け付けない」に合わない。FedEx の1行に改行が入った住所が残る。
- 【事実】試験 `backend/tests/test_delivery_address_rule.py:43-45` は途中の改行（`"a\nb"`）だけを見ており、末尾の改行は見ていない。
- 原因: 設計 §3-1 のコードをそのまま写したもの（Generator の写し間違いではない。設計の書き漏れ）。
- 直し方の案: `base.py:50` を `_DELIVERY_ADDRESS_LINE_RE.fullmatch(value)` にする（または正規表現の末尾を `\Z` にする）。`test_delivery_address_rule.py` と `addressRules.test.ts` に `"abc\n"` → non_ascii / `addressRule.ascii` を1行ずつ足す。2ファイル数行で、他の道（3つの受け口）は同じ関数を使うので一緒に直る。

---

## 1. 範囲（設計・カードとの照合）

- 【事実】`git diff --stat origin/main...3943c9c75` の 42 ファイルは、設計 §5 の「触る」列・カード §2 の新しいファイル6つ・設計 PR から取り込んだ docs と台帳（`.claude-pipeline/active-work.d/release-customer-form-pc-layout-design.md`・ADR-126 追補・docs/adr/README.md・docs/specs/README.md・field-size 設計書）だけ。
- 【事実】触らないと書いたファイルの差分は 0: `migrations/`・`.github/`・`frontend/src/components/CountryCombobox.tsx`・`frontend/src/constants/countries.ts`・`backend/app/routers/registration_tokens.py`・`frontend/src/pages/company-detail/useCompanyDetail.ts` は stat に出ない。
- 【事実】backend の5ファイルは設計 §3-1〜§3-5 のコードと逐語で同じ（import の位置を含む）。frontend も §4-1〜§4-8 のとおり（`CountryCombobox.tsx` に `style={{` 残り0・写しの `function CountryCombobox` は削除・`field-w-xs`・`page-header`・`TwoColumn ratio="1:1" gap="4"`・`displayFn={(c) => c.dial}`・`optionLabelFn`）。
- impl-report 差異1（発送の型を手順1の commit に入れた）は commit の分け方だけで中身は設計どおり。問題なし。

## 2. 正しさ

### `_check_new_delivery_lines`（`backend/app/routers/companies.py:228-256`・D6/K12）
- 【事実】PATCH では `update_data = data.model_dump(exclude_unset=True, mode="python")` なので住所は dict・`address_type` は enum。`getattr(a_type, "value", a_type)` で `"delivery"` と比べられる。POST では `data.addresses` は `CompanyAddressInput` の列（`schemas/company.py:137` で `default_factory=list`。`None` にならない）。
- 【事実】今ある行の比べ方は住所1〜3だけ・`""` と `None` を同じとみなす。`CompanyAddressInput` は文字を削らない（strip なし）ので、画面が読んだ値をそのまま送り返せば一致する。
- 【事実】PATCH の確かめは `UPDATE companies` より前（`:584`）。POST は会社の INSERT の後（`:510`）だが、`get_db`（`backend/app/database.py:70-79`）が例外で rollback し、`db.commit()`（`:536`）より前で止まるので何も残らない。
- 【事実】SELECT は `company_id` だけで絞るが、その前に `SELECT … FROM companies WHERE id = :id` が無ければ 404 にしている（テナントの文脈の中）。他テナントの住所を読む道は増えていない。
- 設計 §7 で承知済みの抜け: 同じ会社の今ある決まり外の行と同じ文字の送り先を「2行目」として足すと受け口では通る。画面の窓は保存時に赤くするので画面からは入らない。止める理由にしない。

### 送り先の決まり（`backend/app/schemas/base.py`・`registration_token.py:116-122`・`order_shipping_detail.py:124-138`・D2）
- 【事実】`AddressInput` は `address_type == "delivery"` の時だけ確かめる（`Literal["billing","delivery"]`）。請求先は 36 文字でも通る（試験 `test_address_input_billing_36_ok`）。D2 どおり。
- 【事実】`AddressInput` は `RegisterRequest.addresses`（`:128`）・`AddAddressRequest.address`（`:162`）・`ChangeBillingRequest.address`（`:168`）の3つで使われ、3つの公開の受け口に効く。
- 【事実】発送は Create/Update だけに付き、`OrderShippingDetailResponse` には付かない（試験 `test_shipping_response_not_checked`）。
- 末尾の改行だけ R1。

### 見積書の住所3（`backend/app/routers/invoices.py:71-75`・`:112`・D4）
- 【事実】`_fetch_address_snapshot` の SELECT は既に `a.address_line_3` を読んでいる（`:91`）ので KeyError にならない。
- 【事実】請求書の PDF は写しに `address_line_1` のキーがあれば分けた値で描く（`backend/app/services/invoice_renderer.py:533-546`）ので、住所3が2回出ることはない。写しの `address` を読む所は `invoice_renderer.py:538`・`:625` だけ（`git grep`）。
- D4（見積に住所3を出す・6項目は出さないまま）と合う。

## 3. ルール

- ADR-027（i18n）【事実】`addressRule.ascii`・`addressRule.maxLength` が ja/en の両方にある。製品コード（試験とロケールを除く）の追加行に日本語の直書きは 0 件（追加行を `\p{Han}\p{Hiragana}\p{Katakana}` で検索）。
- ADR-067・ADR-144【事実】追加行の `[0-9]+px` と `#hex` は、tokens.css・field-size.css を除くと `CountryCombobox.css` の `border: 1px solid var(--border)` 1件だけ（設計 §9 K14 で除外と明記）。新しい幅は `--field-w-xs`・`--max-width-public-form` として tokens.css に登録。住所の欄は金型 `TextField`、State/ZIP は `TwoColumn`。
- ADR-072【事実】commit は増えていない。`companies.py:536-537`・`:648-649` の `commit()` → `reset_tenant_context()` はそのまま。新しい関数は SELECT と例外だけ。

## 4. 試験（設計 §6 との照合）

| 設計 §6 の行 | 有無 | 重さ |
|---|---|---|
| 決まりの関数・お客様の型・発送の型 | あり（`test_delivery_address_rule.py`） | 末尾の改行が抜け（R1） |
| お客様の受け口（`test_public_register_company.py` に 422/200） | **無い** | 軽い。【事実】カード手順1〜8に書かれておらず Generator は足していない（impl-report 差異5）。受け口の確かめは型（`AddressInput`）の中だけで、型の試験で 36 文字×・請求先○を見ている。受け口の道が `AddressInput` を使うことはコードで確認済み（上の §2）。止めない。別便で足すのが望ましい |
| 会社の受け口 ①②③ | あり（`test_companies.py`） | — |
| 見積書 | あり（3つ） | — |
| 既存試験の直し（`nasty_addr`） | あり | — |
| 画面の決まり | あり（`addressRules.test.ts`） | R1 の1行を足す |
| 社内の窓・発送の欄 | あり（`CompanyAddressModal.test.tsx` 4つ・`SharedButtonMigration.test.tsx` 1つ） | — |
| 国番号（K2） | あり（vitest＋e2e） | 191→190 は差異4のとおり件数を固定していないので問題なし |
| 画面の並び（e2e） | あり（B-3 書き換え・K1×3・K2・K5・K6〜K9） | CI では走らない（`e2e.yml` の `if: false`）。evaluator がクラウドで流す前提 |

## 5. 実装報告の「差異・注意」7点

| # | 中身 | 止める理由か |
|---|---|---|
| 1 | 発送の型を手順1の commit に | ならない（中身は設計どおり） |
| 2 | K13 の `git grep 'x20-'` に tcg の既存3行が出る | ならない。【事実】`tcg_analyzer_svc.py`・`tcg_keyword_lint.py` は今回触っていない。設計 §9 K13 の確かめ方を「今回の追加行」に絞るよう直すのが望ましい（docs だけ） |
| 3 | lint 警告 58 件（エラー0） | ならない。【未確認】変更前の件数は誰も数えていない。CI の lint の結果で判断する |
| 4 | 国は 190 件 | ならない |
| 5 | `test_public_register_company.py` に足していない | ならない（上の表） |
| 6 | DB の試験は手元 SQLite のみ | ならない。ただし Postgres の結果は CI 待ち。【事実】審査の時点で CI は 24 件が実行中で、緑はまだ出ていない |
| 7 | e2e は手元の Chromium・K5 の前後比べは未実施 | ならない（evaluator の担当） |

## 6. マージ前に要るもの（審査の外・事実だけ）

- 【事実】`gh pr checks 5718`（head a0a118a4e）で `process-artifacts gate` が fail。理由は「PR本文に `### GO記録` が無い」（frontend/src・backend/app/routers を含むため）。PO の「GO #5718」と転記が要る。
- 【事実】同時点で 24 件 pending・15 pass・8 skipping。

## 7. 気づき（止めない・情報）

- 注文ごとの発送の欄は保存のたびに住所1〜3を確かめる（`frontend/src/components/ShippingDetailPanel.tsx:290`）。今ある発送の行に決まり外の住所があると、追跡番号など別の欄だけ直す保存も画面で止まる。【事実】設計 §3-4 は本番 0 件（recon §3）を前提にしている。0 件である限り影響なし。
