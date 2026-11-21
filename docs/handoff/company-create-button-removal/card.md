# 実装カード: 顧客情報の「新規登録」ボタンを消す

- 区分: B-1（`frontend/src/` と試験だけ）
- 枝: `release/company-create-button-removal`（設計 docs はこの枝に入っている。同じ枝に足す）
- 設計: `docs/handoff/company-create-button-removal/design.md`・recon: 同 `recon.md`

## 1. 作業前の点検

- `git -C <wt> log --oneline -1` が設計のコミットであること。
- `frontend/src/pages/companies/CompaniesPage.tsx` が 604 行、17 行が `import { Modal }`、365 行が `const pageContentActions = hasPermission("customers.create") ? (` であること。違えば止めて BLOCKED。

## 2. 触るもの／触らないもの

- 触る: `frontend/src/pages/companies/CompaniesPage.tsx`、`frontend/src/components/PageFormButtonMigration.test.tsx`、`frontend/src/locales/ja.json`、`frontend/src/locales/en.json`。
- 触らない: それ以外の全部（特に `frontend/src/pages/companies/CompanyFormFields.tsx`・`frontend/src/pages/contacts/ContactsPage.tsx`・`backend/`）。

## 3. 手順

### 3-1 CompaniesPage.tsx

1. 消す: 198-202 行の5つの状態、227-321 行 `handleCreateSubmit`、365-377 行 `pageContentActions`、399 行 `right={pageContentActions}`（属性ごと）、438-567 行の新規作成 Modal（コメント行から閉じタグまで）。
2. 続けて、次の名前を1つずつ `grep -nw <名前> frontend/src/pages/companies/CompaniesPage.tsx` で数え、定義の行しか出ないものを消す: `Modal` `SelectControl` `TextareaControl` `PHONE_RE` `validatePhoneClient` `AddressFormState` `emptyBilling` `emptyDelivery` `FormState` `emptyForm` `Tab` `FormEvent` `toNull` `submitting` `setSubmitting`。1つ消したら残りを数え直す（連鎖して使われなくなるため）。
3. 編集 Drawer・編集保存・削除・一覧の行は1字も変えない。迷ったら消さずに NEEDS_DECISION。

### 3-2 PageFormButtonMigration.test.tsx

1. `cases` を `... .filter(c => !(c.kind === 'company' && c.mode === 'create'))` にする。
2. `it.each(['company', 'contact'] as const)('%s create locks ...` を `['contact'] as const` にする。
3. `it('company create validates telephone and preserves billing address payload', ...)` を丸ごと消す。
4. `expectedPayload` の会社の create 分（`return mode === 'edit' ? common : { ...common, name_en: ...}`）を `return common;` にする。`configs.company.createTitle` は残してよい（足す試験で使う）。
5. 足す（describe の中の最後）:
   ```tsx
   it('company page has no create button even with every permission', async () => {
     render(<MemoryRouter><CompaniesPage /></MemoryRouter>);
     await screen.findByText('Fixture company', { exact: true });
     expect(screen.queryByRole('button', { name: /companies\.newCompany/ })).toBeNull();
     expect(screen.queryByRole('dialog', { name: 'companies.newCompany' })).toBeNull();
   });
   ```

### 3-3 文字

- `companies.newCompany`・`companyCodeLabel`・`branchNameLabel`・`countryCodeWithHint` と、3-1 で消した Modal の中にあった `companies.*` キーを1つずつ `git grep -c "companies\.<key>\b" -- frontend/src` で数える。0 件のキーだけ ja.json と en.json の両方から消す（ただし試験ファイルが使う `newCompany` は試験の文字列なので、ja/en からは消す）。1 件以上なら残す。

## 4. 確かめ（全部の生出力を残す）

- `cd frontend && npx tsc`（package.json の build と同じ）・`npx eslint src/pages/companies/CompaniesPage.tsx src/components/PageFormButtonMigration.test.tsx`・`npx vitest run src/components/PageFormButtonMigration.test.tsx src/lib/query/stage2Pages.test.tsx`・`node scripts/check-i18n-missing-keys.js`。
- `git diff --numstat` を出す。
- 1つでも失敗したら直してよいのは 3 の範囲だけ。範囲外が要るなら BLOCKED。

## 5. 送り方

- 1 コミット。`git -C <wt> push origin release/company-create-button-removal`。PR は作らない（Opus が作る）。
- 最後の行は `DONE` か `BLOCKED: <理由>` か `NEEDS_DECISION: <問い>`。
