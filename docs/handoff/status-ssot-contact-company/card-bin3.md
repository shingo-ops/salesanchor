# 実装カード 便3: 画面・サーバー・辞書が状態の表 public.customer_statuses を読む

- 設計: [design.md](design.md) §6（6-1・6-2・6-2-1・6-3・6-3-2・6-3-4・6-3-3・6-4）・§8 K4〜K7・K9・K11・K12・K14・K15・§9 未決4/5 の決定（設計 PR #5419 で審査 APPROVE）。調査: [recon.md](recon.md)。証拠: [evidence-hide-on-create.md](evidence-hide-on-create.md)・[evidence-merge-button.md](evidence-merge-button.md)。
- 前提（済み・事実）: 便1 PR #5422（表）・4行の投入・便2 PR #5434（外部キー）が本番に入り、読み取り鍵で K1（4行）・K2（外部キー10本・旧 CHECK 0本）を確かめた（2026-11-12）。
- PO の実装承認: 2026-11-12 のセッション冒頭の依頼「PRマージ、デプロイまで完走させてくれ」。§9 未決4・未決5 は PO「1」で決定済み。
- ブランチ: `release/status-ssot-bin3`（origin/main 0d58e6952 起点。Opus がこのカードを積んで push 済み）。この枝を取り込んで、その上に積む。PR は作らない（Opus が作る）。
- 行番号は origin/main 0d58e6952。設計の行番号は a88194893 / cee9633b9 のもので、数行ずれている所がある（例 statusPresentation.ts の contact・company の組は今 `:151-162`）。**行番号でなく中身で探す。**
- 試験は Mac で流さない。CI で確かめる。手元（クラウドの写し）で流してよいのは vitest の該当ファイル・`node scripts/check-ui-governance.js`・`python3 scripts/check-migration-value-writes.py repo`・`git grep` の数え上げだけ。
- **この便ではアプリのコードだけを変える。** `migrations/`・`scripts/run_all_migrations.sh`・`.github/workflows/`・`deploy.yml`・本番 `scripts/`（protected-tables.txt を除く）は触らない。触る必要が出たら `NEEDS_DECISION:` で止まる。
  - 設計の残り項目 `migrations/20261024_100300_create_ai_cloud_views.sql:366,388` の古い注釈は、この便では直さない（migration を含むと危険パスの PR になり、1リリース1テーマにも反するため。Opus 判断）。

## 決まり（全部の手順に共通）

- 4つの記号（active・inactive・archived・pending_dedup_review）を文字で書いてよいのは次の2ファイルだけ:
  - サーバー: `backend/app/services/customer_statuses.py`（新規）
  - 画面: `frontend/src/lib/customerStatuses.ts`（新規）
  - 例外: 試験ファイル・`frontend/src/utils/statusPresentation.ts` の contact・company の組の鍵（色の種類の表。ADR-120・設計 §2）・サーバーの列挙 `backend/app/schemas/company.py`・`backend/app/schemas/contact.py`（設計 §6-1 で残す）。
- 状態の**名前**（有効・無効・アーカイブ・重複確認待ち／Active…）はどこにも書かない。DB の name_ja・name_en から出す。辞書（ja/en.json）にも書かない。
- 画面の固定の文は t() のまま（ADR-027）。ja.json と en.json は同じキー。
- 画面の部品は金型（`components/` の Button・SelectControl 等）を使う。生の `<button>`・`<select>`・直の style・色の直値は書かない（ADR-144・ADR-067）。
- 迷ったら推測で決めず `NEEDS_DECISION:` で止まる。

## やること（この順）

### 1. 作業場所

`git fetch origin && git switch release/status-ssot-bin3`（クラウドの写しで）。`./scripts/dev/executor-preflight.sh` を流し、生出力を報告に貼る。[1/3] network と [2/3] gh auth の FAIL はクラウドでは起こるものとして先へ進む。[3/3] と [4/4] が OK でなければ `BLOCKED:`。台帳の札は作らない・commit しない（Opus が作る）。

最初に基準値を数えて報告に貼る（設計 K5・K6 の基準: 53件・41件）:

```bash
git grep -n -E '"(active|inactive|archived|pending_dedup_review)"' -- frontend/src/pages/contacts frontend/src/pages/companies frontend/src/pages/company-detail frontend/src/components/MergeCompanyModal.tsx frontend/src/components/MergeContactModal.tsx | grep -v className | wc -l
git grep -n -E 'customers\.status_(active|inactive|archived|pending_dedup)|contacts\.statusCode|statusPendingDedupOption' -- frontend/src | wc -l
```

### 2. サーバー: 読み口1か所（設計 §6-1）

1. 新しいファイル `backend/app/services/customer_statuses.py`。型は `backend/app/services/channel_masters.py:1-30` にそろえる（冒頭の説明・`Final` の定数・読む SQL をここだけに置く）。中身:
   - `CUSTOMER_STATUSES_TABLE: Final[str] = "public.customer_statuses"`
   - 記号の定数4つ: `STATUS_ACTIVE`・`STATUS_INACTIVE`・`STATUS_ARCHIVED`・`STATUS_PENDING_DEDUP_REVIEW`（値はそれぞれの記号）
   - `async def list_customer_statuses(db: AsyncSession) -> list[dict[str, Any]]`: `SELECT code, name_ja, name_en, sort_order, is_active, selectable_on_create FROM {CUSTOMER_STATUSES_TABLE} ORDER BY sort_order` の結果を dict の list で返す。
2. 新しいファイル `backend/app/routers/customer_statuses.py`: `GET /customer-statuses`。手本は `backend/app/routers/conv_logs.py:33-48`（`get_current_user`・`get_current_tenant`・`set_tenant_context` を同じに使う）。返すのは上の list そのまま。summary・tags は日本語の説明と `"customer-statuses"`。
3. `backend/app/main.py`: 他の router と同じ並びで import し、`app.include_router(customer_statuses.router, prefix="/api/v1", tags=["customer-statuses"])` を足す。**道は `/api/v1/customer-statuses`**（設計 §6-1 の `/api/customer-statuses` は他の API と同じ `/api/v1` を付けた形にそろえる。Opus 判断）。
4. 記号の直書きを定数に替える（設計 §6-1・§6-2 の最後から2つ目）:
   - `backend/app/routers/companies.py:765`（`== "archived"`）・`:980`（`== "pending_dedup_review"`）・`:982`（`SET status = 'active'` → `:status` の引数で `STATUS_ACTIVE` を渡す）・`:1019`（`= "active"`）
   - `backend/app/routers/duplicates.py:93`（`WHERE c.status != 'archived'` → `:archived` の引数）
5. 失敗の文（設計 §6-3-2・ADR-1071）: `backend/app/routers/companies.py:766-769` の detail を、理由コードの文字列 `"merge_target_archived"` に替える（状態コード 409 はそのまま）。`backend/tests/error_detail_baseline.json` の `"app/routers/companies.py"` の数を1下げる（今 8 → 7。下げてよいかは試験 `test_error_detail_baseline` の実物で確かめる。数が合わなければ実測値を報告して止まる）。
6. 契約の書き出し: `frontend/api-contract/openapi.json` を、このリポジトリの書き出し手順（`git grep -n 'openapi.json' -- scripts Makefile package.json frontend/package.json .github/workflows` で探す）で更新する。手順が見つからない・CI がずれを止める形なら、その事実を報告して止まる。

### 3. 画面: 記号の定数と読み口（設計 §6-2）

1. 新しいファイル `frontend/src/lib/customerStatuses.ts`:
   ```ts
   /** 会社・連絡先の状態の記号（DB public.customer_statuses の code）。記号を書いてよいのはこのファイルだけ（ADR-1076）。名前は書かない（DB の name_ja / name_en が正本）。 */
   export const CUSTOMER_STATUS_CODES = {
     active: "active",
     inactive: "inactive",
     archived: "archived",
     pendingDedupReview: "pending_dedup_review",
   } as const;
   export type CustomerStatusCode = (typeof CUSTOMER_STATUS_CODES)[keyof typeof CUSTOMER_STATUS_CODES];
   /** API GET /customer-statuses の1行 */
   export interface CustomerStatusRow { code: string; name_ja: string; name_en: string; sort_order: number; is_active: boolean; selectable_on_create: boolean; }
   ```
2. 新しいファイル `frontend/src/hooks/useCustomerStatuses.ts`:
   - 取り方は `useApiQuery<CustomerStatusRow[]>("/customer-statuses")`（`frontend/src/lib/query/apiQuery.ts:108`。ADR-1054 の唯一の取り方。`api.get` を直に呼ばない）。
   - 名前は `i18n.language` が `ja` で始まれば name_ja、そうでなければ name_en（`useTranslation()` の `i18n` を使う）。
   - 返すもの:
     - `isLoading: boolean`・`isError: boolean`
     - `options(mode: "create" | "edit", currentValue?: string): { value: string; label: string }[]` — sort_order 順。create は `is_active && selectable_on_create` の行、edit は `is_active` の行。edit で currentValue がその中に無く表にある行なら、その1行だけ加える（設計 §6-2）。読み込み中・失敗のときは空の配列。
     - `nameOf(code: string): string` — その記号の名前。表に無い・読み込み中なら記号をそのまま返す。
   - 記号で行を選び分ける書き方（`code !== "pending_dedup_review"` 等）を書かない。列 `selectable_on_create`・`is_active` だけで決める（K4・K14）。
3. 試験 `frontend/src/hooks/useCustomerStatuses.test.ts`（K14 (b)）: API の返事を偽物にし、(a) §4 の4行のとき create 3件・edit 4件、並びが sort_order 順 (b) 1行の selectable_on_create を FALSE に変えると create から消え edit に残る (c) is_active FALSE の行は両方から消えるが edit の currentValue がその行なら残る (d) 言語が en なら name_en。偽物の4行の値は試験の中に書いてよい（試験は例外）。

### 4. 画面: 7か所の選択肢（設計 §6-2-1）

設計 §6-2-1 の表の1〜7を、`useCustomerStatuses().options(mode)` から並べる形に直す。mode は表の「変更後の mode」のとおり（7 は `contactForm.id === null ? "create" : "edit"`）。edit では currentValue に今の値を渡す。

- 選択肢の部品は今使っている金型のまま（`SelectControl` 等。`frontend/src/pages/contacts/ContactEditPage.tsx:185-190` の `options={[...]}` の形）。
- 読み込み中は選択肢を空にし、失敗したら選択欄の下に `t("common.fetchError")` を出す（設計 §10 弊害1。新しいキーは作らない）。
- 新規作成の初期値 `"active"` は `CUSTOMER_STATUS_CODES.active` に替える（設計 §6-2 の値の直書きの一覧: `company-detail.types.ts`・`useCompanyDetail.ts`・`ContactEditPage.tsx`・`ContactsPage.tsx`・`CompaniesPage.tsx` の各所。中身で探す）。
- `form.status === "pending_dedup_review"` 等の動きの比較（解消の欄を出す条件など）は `CUSTOMER_STATUS_CODES.pendingDedupReview` に替える。
- `frontend/src/components/MergeCompanyModal.tsx:96`（`r.status !== "archived"`）も定数に替える。

### 5. 画面: 札（バッジ）と色（設計 §6-2・§6-2-1 の下）

1. `frontend/src/utils/statusPresentation.ts` の contact・company の組（今 `:151-162`）から `labelKey` だけ消す。bucket・badgeVariant は残す。
2. 札の名前を出している所（`git grep -n -E 'getStatusPresentation\("(contact|company)"' -- frontend/src` で探す）は、名前を `useCustomerStatuses().nameOf(code)` から出す。
3. 記号から CSS の組み名を作る4か所（`CompaniesPage.tsx`・`ContactsPage.tsx`・`CompanyContactsTab.tsx`・`CompanyDetailPage.tsx` の `` `status-${...}` `` の形。中身で探す）を、`getStatusPresentation(domain, code).badgeVariant` を使う `badge badge-<variant>` の共通の組に直す（例は statusPresentation.ts の `@example`）。
4. `frontend/src/components.css` の `status-active`・`status-inactive`・`status-archived`・`status-pending_dedup_review`（今 `:268-271` 付近）は、`git grep -n -E 'status-(active|inactive|archived|pending_dedup_review)' -- frontend/src` が CSS 自身と `frontend/src/pages/design-system/DesignSystemPage.tsx` だけになったのを確かめてから消す。DesignSystemPage の該当の見本も同じ共通の組に替える。他の画面が使っていたら消さずに報告する。
5. `frontend/src/pages/design-preview/sections/StatusSection.tsx` は contact・company の2組だけ名前を hook から出す（他の11組は今のまま）。

### 6. 辞書（設計 §6-2 の最後・§6-3・§6-3-2・§6-3-4）

1. 消すキー（ja/en 両方）: `customers.status_active`・`customers.status_inactive`・`customers.status_archived`・`customers.status_pending_dedup`・`contacts.statusPendingDedupOption`・`contacts.statusCode`（下の4キーごと）。**消す前に**、それぞれ `git grep -n '<キー>' -- frontend/src` で使う所が0件（辞書と試験を除く）になったのを確かめる。0件でないキーは消さずに報告する。`customers.status_active` 以外の名前の `status_active`（ja.json の別の画面のキー・`channels.status_*`・`products.status_*`）は触らない。
2. まとめる画面の文（設計 §6-3 の表の6キー）を表の「変更後（ja）」に直す。en は同じ意味の英語に直す（`master`・`pending_dedup_review`・`active`・`audit_logs` の語を使わない。`{{pending}}`・`{{active}}` はそのまま）。`mergeCompany.confirmDesc3` を出す所で `t("mergeCompany.confirmDesc3", { pending: nameOf(CUSTOMER_STATUS_CODES.pendingDedupReview), active: nameOf(CUSTOMER_STATUS_CODES.active) })` と名前を渡す。
3. 解消ボタンの文（設計 §6-3-4 の表）: `companies.dedupConfirmAsDistinct`・`contacts.confirmAsDistinctFull` を `{{active}}` 入りに直し、使う所（`CompanyBasicTab.tsx`・`ContactEditPage.tsx`）で `{ active: nameOf(CUSTOMER_STATUS_CODES.active) }` を渡す。`contacts.mergeAsDuplicate` は ja「重複としてマージ」・en「Merge as duplicate」。
4. `frontend/src/pages/company-detail/CompanyContactsTab.tsx:136` の `.replace("（担当者単位は未実装）", "")` を消し `t("contacts.mergeAsDuplicate")` だけにする。
5. 失敗の文（§6-3-2）: `frontend/src/lib/apiErrorReason.ts` の `API_ERROR_REASON_KEYS` の最後に `merge_target_archived: "apiError.mergeTargetArchived",` を足す。ja.json の apiError に「残す方の顧客は今の状態ではまとめられません。先に残す方の状態を変えてから、やり直してください。」、en.json に同じ意味の英語を足す。`frontend/src/lib/apiErrorReason.test.ts` と `backend/tests/test_api_error_reason_sync.py`（`test_table_rows_are_read` の期待の並び）に1行足す。

### 7. 担当者の編集画面の統合ボタン（設計 §9 未決5「1 つなぐ」）

設計 §9 未決5 の「1 つなぐ」の段落のとおり:

- `frontend/src/pages/contacts/ContactEditPage.tsx`（今 `:204-206`）の生 `<button ... disabled style=...>` を金型 `Button`（`variant="secondary" size="md" type="button"`）に替える。押すと `MergeContactModal` を開く。props は `open`・`companyId={contact.company_id}`・`source`（Contact の id・contact_code・display_name・surname・given_name）・`onMerged={(masterId) => navigate(\`/contacts/${masterId}/edit\`)}`・`onCancel`（閉じる）。手本は `frontend/src/pages/company-detail/CompanyContactsTab.tsx` の同じ窓の開き方。
- 試験 `frontend/src/components/FullPageFormButtonMigration.test.tsx`（今 `:171-205` の `retains the separate dedup action controls`）: `expect(merge.disabled).toBe(true)` の2か所を `false` に。`fireEvent.click(merge); expect(mock.patch).not.toHaveBeenCalled();` を「押すと窓の題 `mergeContact.title` が出て、patch は呼ばれない」に変え、窓を閉じてから先の手順へ進む。`getByRole('button', { name: 'contacts.mergeAsDuplicate' })` の行はそのまま。偽の GET（今 `:78-83`）に `/companies/41/contacts?per_page=100` → `[]` を1行足す（窓が開くと読む道。実際の道は MergeContactModal の実物で確かめる）。

### 8. 試験の偽の GET（想定分岐）

選択肢が `/customer-statuses` を読むようになるので、知らない道で例外を投げる偽の GET を持つ試験（例 `FullPageFormButtonMigration.test.tsx:78-83`）は落ちる。`git grep -l -E "Unexpected GET|mockImplementation\(async \(url" -- frontend/src` で該当の試験を探し、7か所の画面と札を描く試験の偽の GET に `/customer-statuses` → 4行（§4 の値。試験の中に書いてよい）を足す。4行を何度も書かないよう、試験用の共通の4行を `frontend/src/test/` 等の既存の試験の置き場（`git grep -l 'fixtures' -- frontend/src/test` 等で実物を確かめる）に1つだけ置き、各試験はそれを読む。`pending_dedup_review` の担当者の値が選択欄に出ることを確かめる試験（`field('common.status').value` が `'pending_dedup_review'`）は、edit の選択肢に4つ目があるので通る。

### 9. サーバーの試験（設計 §6-4・K14 (a)）

- `backend/tests/test_customer_statuses_pg.py`（便2 で作った PostgreSQL の試験）に足す:
  - `CompanyStatus`・`ContactStatus` の値の集合 ＝ 表の code の集合 ＝ `docs/handoff/status-ssot-contact-company/insert-customer-statuses.sql` の4行の code の集合。
  - `list_customer_statuses(db)` の各行に selectable_on_create があり、表の値と同じ（pending_dedup_review だけ FALSE）。
  - 可能なら API `GET /api/v1/customer-statuses` を同じ試験の型で呼ぶ（既存の PostgreSQL の試験で API を呼ぶ前例を `git grep -l 'AsyncClient\|TestClient' backend/tests/*_pg.py` で探す。前例が無ければサービス関数の試験だけにして報告に書く）。
- `backend/tests/test_companies.py`・`backend/tests/test_contacts.py` で、まとめる先がアーカイブのときの detail の文を比べている所があれば `merge_target_archived` に直す。

### 10. 見張り（設計 §6-4・§3 の最後・K12）

1. `scripts/migration-guard/protected-tables.txt` の最後に `customer_statuses` を足す。冒頭の経緯の注釈にも1行足す（`ADR-1076 便3 で customer_statuses を足した（30 表）`。数は実物を数えて書く）。足したあと `python3 scripts/check-migration-value-writes.py repo` が緑かを確かめる。赤なら止まって生出力を報告する（便1・便2 の migration は確認8 の全件走査の対象外のはず＝設計 §3）。
2. `scripts/check-ui-governance.js` に種別 `customerStatusLiteral` を足す: 見る所は `frontend/src/pages/contacts/`・`frontend/src/pages/companies/`・`frontend/src/pages/company-detail/`・`frontend/src/components/MergeCompanyModal.tsx`・`frontend/src/components/MergeContactModal.tsx`（.test.tsx は除く）。数えるのは `"active"`・`"inactive"`・`"archived"`・`"pending_dedup_review"`（シングルクォート・バッククォートも）のうち className の行でないもの。判定は既存の種別と同じ「HEAD の件数 > BASE の件数 なら赤」。ファイル冒頭の説明（検出対象の一覧）と赤のときの文（`:820` 付近の表）にも1行足す。既存の試験があれば（`git grep -l check-ui-governance -- scripts frontend`）同じ形で1件足す。

### 11. 確かめ（報告に生出力を貼る）

```bash
# K5: 0 件（定数ファイルは対象の外）
git grep -n -E '"(active|inactive|archived|pending_dedup_review)"' -- frontend/src/pages/contacts frontend/src/pages/companies frontend/src/pages/company-detail frontend/src/components/MergeCompanyModal.tsx frontend/src/components/MergeContactModal.tsx | grep -v className | grep -v '\.test\.' | wc -l
# K6: 0 件
git grep -n -E 'customers\.status_(active|inactive|archived|pending_dedup)|contacts\.statusCode|statusPendingDedupOption' -- frontend/src | wc -l
# K7: ja・en とも 0
for l in ja en; do jq -r '.mergeCompany[], .mergeContact[]' frontend/src/locales/$l.json | sed -E 's/\{\{[A-Za-z_]+\}\}//g' | grep -c -E 'master|pending_dedup_review|active|audit_logs'; done
# K15: 0 件
git grep -n -E 'active 化|\(activate\)|未実装|not implemented' -- frontend/src/locales/ja.json frontend/src/locales/en.json | grep -E 'dedupConfirmAsDistinct|confirmAsDistinctFull|mergeAsDuplicate' | wc -l
git grep -n 'replace("（' -- frontend/src/pages/company-detail/CompanyContactsTab.tsx | wc -l
# 名前の直書きが増えていない（4つの日本語名が画面のコードに無い）
git grep -n -E '有効|無効|アーカイブ|重複確認待ち' -- 'frontend/src/**/*.tsx' 'frontend/src/**/*.ts' ':!*.test.*' | wc -l   # 基準値を最初に数え、増えていないこと
# ja/en のキーが同じ
node -e "const a=require('./frontend/src/locales/ja.json'),b=require('./frontend/src/locales/en.json');const f=(o,p='')=>Object.entries(o).flatMap(([k,v])=>typeof v==='object'?f(v,p+k+'.'):[p+k]);const x=new Set(f(a)),y=new Set(f(b));console.log([...x].filter(k=>!y.has(k)).length,[...y].filter(k=>!x.has(k)).length)"
python3 scripts/check-migration-value-writes.py repo
cd frontend && npx vitest run src/hooks/useCustomerStatuses.test.ts src/components/FullPageFormButtonMigration.test.tsx src/lib/apiErrorReason.test.ts src/utils/statusPresentation.test.ts && npx tsc --noEmit -p . && npx eslint <変えたファイル>
```

基準値と違う数が出たら、直してから数え直す。直し方が設計に無いときは `NEEDS_DECISION:`。

### 12. commit と push

- 1つの commit でなくてよいが、`git add` は変えたファイルを名前で指定する（`git add -A` 禁止）。
- commit の文は英語の1行目＋日本語の本文。最後に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- `git push origin release/status-ssot-bin3`。`--force`・`--no-verify`・rebase・reset は禁止。pre-commit・pre-push の見張りに止められたら、言い換えずに生出力を報告して止まる。
- 最後の行は `DONE`・`BLOCKED: <理由>`・`NEEDS_DECISION: <問い>` のどれか。

## 触らない所

- `migrations/` 全部・`scripts/run_all_migrations.sh`・`.github/workflows/`・`backend/app/services/tenant.py`
- `backend/app/schemas/company.py`・`backend/app/schemas/contact.py` の列挙（残す・設計 §6-1）
- `backend/app/tasks/reports.py`（書き出しは記号のまま・設計 §6-3-3）
- 見込み客など他の12組の状態（設計 §9 未決1・2）
- `docs/handoff/status-ssot-contact-company/insert-customer-statuses.sql`（4行の正本）

## 戻し方

`git revert` で戻す（DB は変えないので画面とサーバーだけが戻る）。protected-tables.txt の1行も revert で戻る。

## 受入（Opus が確かめる）

| 基準 | 検証方法 |
|---|---|
| K4 7か所の選択肢 | 本番反映後に Chrome で設計 §6-2-1 の1〜7を開いて数える（保存しない）。作る 3つ・直す 4つ |
| K5・K6・K7・K15 | 上の §11 の命令の数が0 |
| K9 | PR の CI 全部緑 |
| K11 | apiErrorReason.test.ts・test_api_error_reason_sync.py が緑 |
| K12 | protected-tables.txt に customer_statuses・`check-migration-value-writes.py repo` 緑 |
| K14 | (a) サーバーの試験 (b) useCustomerStatuses.test.ts が緑 |
| 統合ボタン | Chrome で担当者の編集画面（重複確認待ちの担当者）で押せて窓が開く（まとめる操作はしない） |
