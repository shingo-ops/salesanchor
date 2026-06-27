# recon — modal-select-fields

**仕事名**: modal-select-fields
**日付**: 2026-06-26
**対象ADR**: ADR-073
**担当**: Codex

---

## 背景

一覧画面から開く小窓（モーダル）6 枚の生 `<select>` を、棚の `Select` に寄せる。
対象は 6 ファイル・7 画面で、DB 変更はない。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|---|---|
| `frontend/src/pages/leads/LeadFormFields.tsx:10` | `Select` を import 済み |
| `frontend/src/pages/leads/LeadFormFields.tsx:31-76` | `status` / `type` を `Select` 化 |
| `frontend/src/pages/deals/DealFormFields.tsx:9` | `Select` を import 済み |
| `frontend/src/pages/deals/DealFormFields.tsx:27-55` | `status` / `stage` を `Select` 化 |
| `frontend/src/pages/contacts/ContactFormFields.tsx:9` | `Select` を import 済み |
| `frontend/src/pages/contacts/ContactFormFields.tsx:31-84` | `company_id` / `status` を `Select` 化 |
| `frontend/src/pages/staff/StaffFormFields.tsx:9` | `Select` を import 済み |
| `frontend/src/pages/staff/StaffFormFields.tsx:30-80` | `role_id` / `status` を `Select` 化 |
| `frontend/src/pages/bots/BotFormFields.tsx:10` | `Select` を import 済み |
| `frontend/src/pages/bots/BotFormFields.tsx:32-80` | `purpose` / `status` / `owner_staff_id` を `Select` 化 |
| `frontend/src/pages/companies/CompanyFormFields.tsx:9` | `Select` を import 済み |
| `frontend/src/pages/companies/CompanyFormFields.tsx:23-45` | `status` を `Select` 化 |
| `frontend/src/components/Select.tsx:36-84` | 棚の `Select` 本体。`comp-field__select` と必須 `*` を持つ |
| `frontend/src/components/FormField.css:17-175` | `Select` の共通見た目。▽アイコン・右余白・必須 `*` の標準 |
| `frontend/src/pages/leads/LeadsPage.tsx:284-323` | LeadsPage モーダルで `LeadFormFields` を表示 |
| `frontend/src/pages/deals/DealsPage.tsx:244-284` | DealsPage モーダルで `DealFormFields` を表示 |
| `frontend/src/pages/contacts/ContactsPage.tsx:285-330` | ContactsPage モーダルで `ContactFormFields` を表示 |
| `frontend/src/pages/staff/StaffPage.tsx:223-265` | StaffPage モーダルで `StaffFormFields` を表示 |
| `frontend/src/pages/bots/BotsPage.tsx:215-257` | BotsPage モーダルで `BotFormFields` を表示 |
| `frontend/src/pages/bots/BotEditPage.tsx:71-84` | BotEditPage でも同じ `BotFormFields` を再利用 |
| `frontend/src/pages/companies/CompaniesPage.tsx:422-476` | CompaniesPage モーダルで `CompanyFormFields` を表示 |

---

## 画面対応表

| 画面 | 参照ファイル | 変更点 |
|---|---|---|
| LeadsPage モーダル | `frontend/src/pages/leads/LeadFormFields.tsx` | `status` / `type` を棚へ移行 |
| DealsPage モーダル | `frontend/src/pages/deals/DealFormFields.tsx` | `status` / `stage` を棚へ移行 |
| ContactsPage モーダル | `frontend/src/pages/contacts/ContactFormFields.tsx` | `company_id` / `status` を棚へ移行 |
| StaffPage モーダル | `frontend/src/pages/staff/StaffFormFields.tsx` | `role_id` / `status` を棚へ移行 |
| BotsPage モーダル | `frontend/src/pages/bots/BotFormFields.tsx` | `purpose` / `status` / `owner_staff_id` を棚へ移行 |
| BotEditPage フルページ | `frontend/src/pages/bots/BotEditPage.tsx` | BotFormFields 共通化のまま棚化が反映 |
| CompaniesPage モーダル | `frontend/src/pages/companies/CompanyFormFields.tsx` | `status` を棚へ移行 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | 必須 `*` の位置が変わるか | `Select` の標準ラベルで確認し、画面ごとにスクショで目視確認する | 解消済み |
| 2 | 右側の▽アイコンが文字に重ならないか | `FormField.css` の標準スタイルで本番画面を確認する | 解消済み |
| 3 | 7 画面すべてで崩れがないか | 画面ごとの before / after を撮る | 解消済み |

**未解決ゼロ確認**: 画面ごとの before / after スクリーンショットを取得済み
