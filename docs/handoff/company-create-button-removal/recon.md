# recon: 顧客情報の「新規登録」ボタンを消す

調べた時点: 2026-11-21 21:52 JST・origin/main `c374c8651`

## 1. 既存 ADR の検索

- `git grep -n '新規登録' docs/adr/` → `docs/adr/ADR-097-sa-customer-registration-form.md:61-66`（§6 会社は画面から手で作らない・2026-11-21 PO 決定）。
  - 64 行目: 「顧客情報の画面の「新規登録」ボタン（リードなしで会社を手で作る道）は直さない。撤去する（撤去は別の便で行う）。」
  - 65 行目: 「リードなしで会社を作れるようにする（`lead_id` を任意にする・リードを自動で作る）変更もしない。」
- `docs/adr/FEATURE-INDEX.md` の会社の行（#5663 で補足に同じ決まりを記載済み）。
- 画面の決まり: ADR-027（文字は `t()` 経由・ja/en 同一キー）、ADR-144（金型の部品を使う）。今回は消すだけで、新しい部品・文字は足さない。

## 2. 消す対象（`frontend/src/pages/companies/CompaniesPage.tsx`・604 行）

| 行 | 中身 | 新規登録だけで使うか |
|---|---|---|
| `frontend/src/pages/companies/CompaniesPage.tsx:17` | `import { Modal }` | はい（使う所は 439 行の新規作成 Modal だけ） |
| `frontend/src/pages/companies/CompaniesPage.tsx:19` | `import { SelectControl }` | はい（513 行） |
| `frontend/src/pages/companies/CompaniesPage.tsx:30` | `import { TextareaControl }` | はい（505・522 行） |
| `frontend/src/pages/companies/CompaniesPage.tsx:37-` | `PHONE_RE`・`validatePhoneClient`（41 行に日本語直書きの例外コメント） | 実装役が消した後に grep で確かめる |
| `frontend/src/pages/companies/CompaniesPage.tsx:93-172` | `AddressFormState`・`emptyBilling`・`emptyDelivery`・`FormState`・`emptyForm`・`type Tab` | 同上 |
| `frontend/src/pages/companies/CompaniesPage.tsx:198-202` | `showCreate`・`createForm`・`activeTab`・`phoneError`・`addressesDirty` の状態 | はい |
| `frontend/src/pages/companies/CompaniesPage.tsx:227-321` | `handleCreateSubmit` | はい |
| `frontend/src/pages/companies/CompaniesPage.tsx:365-377` | `pageContentActions`（`hasPermission("customers.create")` のときだけ出る `+ {t("companies.newCompany")}` ボタン） | はい |
| `frontend/src/pages/companies/CompaniesPage.tsx:399` | `right={pageContentActions}` | はい |
| `frontend/src/pages/companies/CompaniesPage.tsx:438-567` | 新規作成 Modal（タブ・全項目） | はい |

残すもの: `frontend/src/pages/companies/CompaniesPage.tsx:322-` の編集保存、`frontend/src/pages/companies/CompaniesPage.tsx:568-` の編集 Drawer（`frontend/src/pages/companies/CompanyFormFields.tsx` を使う）、削除、一覧、検索。

## 3. 文字（i18n）

- `companies.newCompany` を使うのは `frontend/src/pages/companies/CompaniesPage.tsx` と `frontend/src/components/PageFormButtonMigration.test.tsx` だけ（`git grep -l 'companies\.newCompany' origin/main -- frontend/src`）。
- `frontend/src/locales/ja.json:1196` `"newCompany": "新規登録"`・`frontend/src/locales/en.json:1196` `"newCompany": "New Client Profile"`。
- `companyCodeLabel`（1243）・`branchNameLabel`（1246）・`countryCodeWithHint`（1247）は `CompaniesPage.tsx` だけが使う。新規作成 Modal の中だけかは、実装役が消した後に grep で確かめる。
- 動的に組み立てるキー（`` t(`companies.${...}`) ``）は 0 件（`git grep -n 't(\`companies\.' origin/main -- frontend/src`）。

## 4. 試験

- `frontend/src/components/PageFormButtonMigration.test.tsx`（223 行）が会社の新規作成を4か所で試している:
  - `frontend/src/components/PageFormButtonMigration.test.tsx:20` `configs.company.createTitle: 'companies.newCompany'`、`:26` `cases` が company×create を含む。
  - `frontend/src/components/PageFormButtonMigration.test.tsx:158` `it.each(['company', 'contact'])` の二重送信止めの試験。
  - `frontend/src/components/PageFormButtonMigration.test.tsx:185-204` 'company create validates telephone and preserves billing address payload'。
  - `frontend/src/components/PageFormButtonMigration.test.tsx:74-79` `expectedPayload` の会社の create 分。
- `frontend/src/lib/query/stage2Pages.test.tsx:14,44,183-190` は一覧と検索だけ。新規登録には触らない。
- `frontend/tests-e2e/horizontal-overflow.spec.ts:41`・`tests/prod-check/prod-ui.spec.ts:60-106` は一覧と詳細だけ。新規登録ボタンは使わない。
- `frontend/tsconfig*.json` は `noUnusedLocals: false`。使わなくなった名前は型検査では止まらない → 実装役が grep で数えて消す。

## 5. 裏側（触らない）

- `backend/app/routers/companies.py` の `POST /companies`（377 行付近）は `lead_id` 必須（無いと not_found:lead）。受信箱のフォームの道が使うので残す。
- `frontend/src/pages/contacts/ContactsPage.tsx` も `customers.create` を使うが、連絡先の新規登録は今回の対象外。

## 6. 本番の今の値（基準値）

- 2026-11-21 21:52 JST、`https://app.salesanchor.jp/` の `assets/main-BMUWQrJj.js` に `newCompany` が 4 回出る（`grep -o newCompany | wc -l` = 4。英・日の文字、ボタン、Modal の題）。
