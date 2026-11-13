# 実装カード 便5: まとめる画面の後始末（状態の名前・権限・まとめたあとの試験）

- 設計: [design.md](design.md) §16（K18・K19・K20）。前提の事実は §16-2。
- PO の実装承認: 2026-11-12 のセッション冒頭の依頼「PRマージ、デプロイまで完走させてくれ」と、2026-11-13 の「1」（残りの候補の設計に入る）。危険 PR ではない（migrations・deploy.yml・本番 scripts を含まない・ADR-136 の対象外）。
- ブランチ: `release/status-ssot-followups`（Opus がこのカードを積んで push 済み）。この枝の上に積んで push する。PR は作らない（Opus が作る）。
- 試験は Mac で流さない。クラウドで `cd frontend && npm ci && npx vitest run --config vitest.unit.config.ts --project unit <ファイル>` を流してよい。流せないときはその事実を書き、CI で確かめる。行番号は origin/main cee15756b。
- 変える・作るのは下の8ファイルだけ。サーバー・DB・辞書（ja.json・en.json）・openapi.json は変えない。

## やること（この順）

1. 作業場所を公式の台本で作る（リポジトリの pre-commit は `~/worktrees/` 配下でない場所からの commit を「worktree 外での作業は禁止」で止める。クラウドでも同じ。docs/handoff/cloud-parity/recon.md:23。2026-11-13 08:26 JST の1回目はこれを入れ忘れて commit で止まった）。`<main>` はクラウドが最初に置いた場所（例 `/home/user/salesanchor`）。1 つずつ流し、出力を報告に書く。
   - (1a) `cd <main> && git fetch origin release/status-ssot-followups main`
   - (1b) `cd <main> && git branch --list release/status-ssot-followups`。空であること。空でなければ消さずに `BLOCKED:`（`git checkout -B` は使わない）。
   - (1c) `cd <main> && bash scripts/new-worktree.sh release/status-ssot-followups`。`--claude` は付けない。出力はパイプに通さない。
   - (1d) `cd <main> && git worktree list`。`$HOME/worktrees/salesanchor/release-status-ssot-followups` が出ること。出なければ `BLOCKED:`。以後の `<repo>` はこの絶対パス。
   - (1e) `cd <repo> && git merge --no-edit origin/release/status-ssot-followups`（ff でなく合わせの commit になってよい）。続けて `cd <repo> && git merge-base --is-ancestor origin/release/status-ssot-followups HEAD; echo rc=$?` が `rc=0` であること。衝突したら `git merge --abort` をして `BLOCKED:`。
   - (1f) `cd <repo> && ./scripts/dev/executor-preflight.sh`。生出力を報告に貼る。クラウドでは [1/3] network と [2/3] gh auth の FAIL は起こるものとして先へ進む。[3/3] と [4/4] が OK でなければ `BLOCKED:`。台帳の札は作らない（台本が作った .claude-pipeline/active-work.d/ の未追跡ファイルは commit しない）。
   - 以後のやること 2〜11 はすべて `<repo>` の中で行う。push は `git push origin HEAD:release/status-ssot-followups` を単独で流す。

2. `frontend/src/components/MergeCompanyModal.tsx:239`（K18）:
   - 変更前: `                            {c.status}`
   - 変更後: `                            {customerStatuses.nameOf(c.status)}`
   - ほかの行は変えない（`customerStatuses` は `:55` で取り済み）。

3. `frontend/src/pages/contacts/ContactEditPage.tsx`（K19）:
   - (a) `:23` `import { useCustomerStatuses } from "../../hooks/useCustomerStatuses";` の直前に1行足す:
     ```
     import { usePermissions } from "../../hooks/usePermissions";
     ```
   - (b) `:97` `  const [mergeOpen, setMergeOpen] = useState(false);` の直後に2行足す:
     ```
       const { hasPermission } = usePermissions();
       const canMerge = hasPermission("customers.delete");
     ```
     （置く場所は、ほかの hook と同じく早い return より前であること。早い return があってその後ろになるなら、`useState` の並びのいちばん後ろに置き、場所を報告に書く）
   - (c) `:205-207` の Button を次に変える（会社の同じ欄 `CompanyBasicTab.tsx:142-152` と同じ形）:
     - 変更前:
       ```
                       <Button variant="secondary" size="md" type="button" onClick={() => setMergeOpen(true)}>
                         {t("contacts.mergeAsDuplicate")}
                       </Button>
       ```
     - 変更後:
       ```
                       <Button
                         variant="secondary"
                         size="md"
                         type="button"
                         onClick={() => setMergeOpen(true)}
                         disabled={!canMerge}
                         title={canMerge ? "" : t("companies.dedupMergeNoPermission")}
                       >
                         {t("contacts.mergeAsDuplicate")}
                       </Button>
       ```

4. `frontend/src/pages/company-detail/CompanyContactsTab.tsx`（K19）:
   - (a) Props（`:27` `  canEdit: boolean;` の直後）に1行足す:
     ```
       /** 担当者をまとめてよいか（customers.delete・サーバーの merge と同じ決まり） */
       canMerge: boolean;
     ```
   - (b) `:42` `  company, contacts, canEdit,` を `  company, contacts, canEdit, canMerge,` にする。
   - (c) `:136-138` の行のまとめるボタンを `{canMerge && ( … )}` で包む:
     - 変更前:
       ```
                             <Button size="sm" variant="secondary" onClick={() => openMergeModal(c)}>
                               {t("contacts.mergeAsDuplicate")}
                             </Button>
       ```
     - 変更後:
       ```
                             {canMerge && (
                               <Button size="sm" variant="secondary" onClick={() => openMergeModal(c)}>
                                 {t("contacts.mergeAsDuplicate")}
                               </Button>
                             )}
       ```
   - (d) `:234` `          onRequestMerge={handleRequestMerge}` を `          onRequestMerge={canMerge ? handleRequestMerge : undefined}` にする（`ContactChannelForm.tsx:253` は渡されないときボタンを出さない）。

5. `frontend/src/pages/company-detail/CompanyDetailPage.tsx:161`（K19）: `          canEdit={canEdit}`（CompanyContactsTab の中の行）の直後に `          canMerge={canMerge}` を1行足す。`canMerge` は `:41` にある。ほかのタブの `canEdit` の行は変えない。

6. `frontend/src/components/FullPageFormButtonMigration.test.tsx`（既存の試験を通すため）:
   - `beforeEach` の偽の GET（`:79-86`）の `if (url === '/customer-statuses') return CUSTOMER_STATUS_TEST_ROWS;` の直後に1行足す:
     ```
         if (url === '/me/permissions') return { permissions: ['customers.delete'] };
     ```
   - `:184` と `:209` の `expect(merge.disabled).toBe(false);` は、権限の取得を待つため `await waitFor(() => expect(merge.disabled).toBe(false));` にする（審査の推奨。確かめる中身は同じ）。ほかは変えない。

7. 新しい試験 `frontend/src/pages/contacts/ContactEditPageMerge.test.tsx`（K19・K20）。既存の `FullPageFormButtonMigration.test.tsx` の `afterEach` は `mock.post` が呼ばれないことを確かめるので、まとめる試験は別のファイルにする。
   - 頭（mock・LocationProbe・`contact` の形）は `FullPageFormButtonMigration.test.tsx:1-31` と同じ書き方にする。違いは次だけ:
     - 状態は `pending_dedup_review` で始める。
     - 偽の GET: `/contacts/52`→`{ ...contact, status: 'pending_dedup_review' }`、`/contacts/53`→`{ ...contact, id: 53, contact_code: 'C53', surname: 'Master fixture', status: 'active' }`、`/companies?per_page=100`→`[{ id: 41, name: 'Fixture company', company_code: 'CO41' }]`、`/customer-statuses`→`CUSTOMER_STATUS_TEST_ROWS`、`/me/permissions`→`{ permissions }`（試験ごとに変える変数）、`/companies/41/contacts?per_page=100`→`[{ id: 53, contact_code: 'C53', display_name: null, surname: 'Master fixture', given_name: null, status: 'active' }]`。知らない道は例外を投げる。
     - `afterEach` は `cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals();` と `expect(fetch).not.toHaveBeenCalled()`・`expect(mock.patch).not.toHaveBeenCalled()`・`expect(mock.delete).not.toHaveBeenCalled()`。
     - 画面は `MemoryRouter initialEntries={['/contacts/52/edit']}` と `<Route path="/contacts/:id/edit" element={<ContactEditPage />} />`。
   - 試験1「権限が無いと押せず理由が出る」: `permissions = []`。画面を出し、`await waitFor` で権限の取得を待ってから、`getByRole('button', { name: 'contacts.mergeAsDuplicate' })` が `disabled === true`、`title === 'companies.dedupMergeNoPermission'`。押しても `mergeContact.title` の窓は出ない（`queryByRole('dialog')` が null）。
   - 試験2「まとめると窓が閉じ、残した側の編集画面へ移る」: `permissions = ['customers.delete']`、`mock.post.mockResolvedValue({})`。`await waitFor` でボタンが `disabled === false` になるのを待つ → 押す → `findByText('mergeContact.title')` → `within(dialog).getByRole('radio')` を押す → `mergeContact.nextStep` を押す → 名前が `mergeContact.executeLabel` のボタンを押す。そのあと `waitFor` で (a) `mock.post` が `('/contacts/53/merge', { loser_id: 52, reason: null })` で1回だけ呼ばれた (b) `queryByRole('dialog')` が null (c) `getByTestId('location').textContent` が `/contacts/53/edit`。
   - ボタンや窓の名前が上と合わないとき（例: 実行ボタンの名前）は、`MergeContactModal.tsx` の実物に合わせ、合わせた点を報告に書く。試験の中身（何を確かめるか）は変えない。

8. 新しい試験 `frontend/src/components/MergeCompanyModal.test.tsx`（K18）:
   - mock は `FullPageFormButtonMigration.test.tsx:10-14` と同じ書き方。偽の GET: `/customer-statuses`→`CUSTOMER_STATUS_TEST_ROWS`、`/companies?per_page=100`→`[{ id: 2, name: 'Other company', company_code: 'CO2', status: 'active' }, { id: 1, name: 'Source company', company_code: 'CO1', status: 'pending_dedup_review' }]`。
   - `<MergeCompanyModal open source={{ id: 1, name: 'Source company', company_code: 'CO1' }} onMerged={vi.fn()} onCancel={vi.fn()} />` を出す。
   - 確かめる: `await findByText('有効')` がある。`queryByText('active', { exact: true })` が null。`afterEach` で `cleanup(); queryClient.clear();`。

9. 新しい試験 `frontend/src/pages/company-detail/CompanyContactsTab.test.tsx`（K19）:
   - mock は同じ書き方。偽の GET は `/customer-statuses` だけ（ほかは例外）。
   - 担当者1人（`id: 52, contact_code: 'C52', surname: 'Fixture contact', status: 'pending_dedup_review'` ほか型に要る項目は null）、会社 `{ id: 41, name: 'Fixture company', company_code: 'CO41', ... }`（型に要る項目は `as Company` で足りる分だけ）、関数の props は `vi.fn()`、`contactModalOpen={false}`。
   - 試験1: `canEdit` true・`canMerge` false → `queryByRole('button', { name: 'contacts.mergeAsDuplicate' })` が null。`common.edit` のボタンはある。
   - 試験2: `canEdit` true・`canMerge` true → そのボタンがある。

10. 確かめ（報告に生出力を貼る）:
    - `git grep -n -E '^[[:space:]]*\{[A-Za-z_]+\.status\}[[:space:]]*$|>\{[A-Za-z_]+\.status\}<' -- frontend/src/pages/contacts frontend/src/pages/companies frontend/src/pages/company-detail frontend/src/components/MergeCompanyModal.tsx frontend/src/components/MergeContactModal.tsx` が0件。
    - `git grep -n 'onRequestMerge={handleRequestMerge}' -- frontend/src` が0件。
    - 新しい3ファイルと既存の `FullPageFormButtonMigration.test.tsx` を vitest で流した結果（流せたとき）。
    - `cd frontend && npx tsc --noEmit -p .`（流せたとき）と `npx eslint <変えた8ファイル>`（流せたとき）。
    - 消したら落ちることの確認（1回だけ・commit しない）: 手順2 を元に戻すと `MergeCompanyModal.test.tsx` が落ちる。手順4(c) の `canMerge &&` を消すと `CompanyContactsTab.test.tsx` の試験1が落ちる。結果を報告に書き、元に戻す。
    - `git diff origin/main --stat` が下の8ファイルと設計・カード・台帳の札だけ。
11. commit（`feat(customer-status): 便5 まとめる画面の状態の名前と権限（ADR-1076 design §16）` と Co-Authored-By）して push。最後の行は `DONE` か `BLOCKED: <理由>` か `NEEDS_DECISION: <問い>`。

## 変える・作る8ファイル

- frontend/src/components/MergeCompanyModal.tsx
- frontend/src/pages/contacts/ContactEditPage.tsx
- frontend/src/pages/company-detail/CompanyContactsTab.tsx
- frontend/src/pages/company-detail/CompanyDetailPage.tsx
- frontend/src/components/FullPageFormButtonMigration.test.tsx
- frontend/src/pages/contacts/ContactEditPageMerge.test.tsx（新規）
- frontend/src/components/MergeCompanyModal.test.tsx（新規）
- frontend/src/pages/company-detail/CompanyContactsTab.test.tsx（新規）

## 想定される分岐

- `CompanyContactsTab` を使う場所が `CompanyDetailPage.tsx` 以外にもあり、型の確かめで `canMerge` が足りないと出た: その場所の `canEdit` の行の直後にも `canMerge` を渡す。値は、その画面に `hasPermission("customers.delete")` があればそれ、無ければ `NEEDS_DECISION:` で止める。
- `ContactEditPage.tsx` の hook の並びに早い return があり、手順3(b) の場所に置けない: 手順3(b) の括弧のとおり。
- 試験で `useAuth` が要ると出た: `FullPageFormButtonMigration.test.tsx` がどう出しているか（Provider なし）を真似る。真似ても動かなければ `BLOCKED:`。
- 試験のどれかが、カードのとおりに書いても落ちる（画面の実物と合わない）: 何が合わないかを生出力で書き `NEEDS_DECISION:`。確かめる中身を弱めない。
- 金型（`components/` の Button 等）以外の部品・色の直値・辞書に無い文を足しそうになった: 足さずに `NEEDS_DECISION:`。
