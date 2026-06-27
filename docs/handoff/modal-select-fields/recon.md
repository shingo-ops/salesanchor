# recon — modal-select-fields

**仕事名**: modal-select-fields
**日付**: 2026-06-28
**対象ADR**: ADR-121
**担当**: Codex

---

## 背景

一覧画面から開く小窓 6 画面の生 `<select>` を、棚の `Select` に寄せる。
対象は 6 ファイルで、DB 変更はない。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|---|---|
| `frontend/src/pages/leads/LeadsPage.tsx:23` | `Select` を import 済み |
| `frontend/src/pages/leads/LeadsPage.tsx:277-285` | 一覧の絞り込みを `Select` 化 |
| `frontend/src/pages/leads/LeadsPage.tsx:318-381` | モーダル内の 7 個の select を `Select` 化 |
| `frontend/src/pages/deals/DealsPage.tsx:29` | `Select` を import 済み |
| `frontend/src/pages/deals/DealsPage.tsx:237-245` | 一覧の絞り込みを `Select` 化 |
| `frontend/src/pages/deals/DealsPage.tsx:282-309` | モーダル内の select を `Select` 化 |
| `frontend/src/pages/staff/StaffPage.tsx:18` | `Select` を import 済み |
| `frontend/src/pages/staff/StaffPage.tsx:260-277` | モーダル内の select を `Select` 化 |
| `frontend/src/pages/staff-reports/StaffReportsPage.tsx:7` | `Select` を import 済み |
| `frontend/src/pages/staff-reports/StaffReportsPage.tsx:59-67` | 一覧の絞り込みを `Select` 化 |
| `frontend/src/pages/staff-reports/StaffReportsPage.tsx:77-85` | モーダル内の select を `Select` 化 |
| `frontend/src/pages/shifts/ShiftsPage.tsx:7` | `Select` を import 済み |
| `frontend/src/pages/shifts/ShiftsPage.tsx:65-76` | モーダル内の select を `Select` 化 |
| `frontend/src/pages/roles/RolesPage.tsx:21` | `Select` を import 済み |
| `frontend/src/pages/roles/RolesPage.tsx:171-179` | `priorityOptions` を `Select` 用に整形 |
| `frontend/src/pages/roles/RolesPage.tsx:531-535` | ロール編集モーダルの select を `Select` 化 |
| `frontend/src/components/Select.tsx:36-84` | 棚の `Select` 本体。共通の▽アイコンと必須 `*` を持つ |
| `frontend/src/components/FormField.css:17-175` | `Select` の共通見た目。▽アイコン・右余白・必須 `*` の標準 |

---

## 画面対応表

| 画面 | 参照ファイル | 変更点 |
|---|---|---|
| LeadsPage | `frontend/src/pages/leads/LeadsPage.tsx` | 絞り込み + モーダル内 select を棚へ移行 |
| DealsPage | `frontend/src/pages/deals/DealsPage.tsx` | 絞り込み + モーダル内 select を棚へ移行 |
| StaffPage | `frontend/src/pages/staff/StaffPage.tsx` | モーダル内 select を棚へ移行 |
| StaffReportsPage | `frontend/src/pages/staff-reports/StaffReportsPage.tsx` | 絞り込み + モーダル内 select を棚へ移行 |
| ShiftsPage | `frontend/src/pages/shifts/ShiftsPage.tsx` | モーダル内 select を棚へ移行 |
| RolesPage | `frontend/src/pages/roles/RolesPage.tsx` | 優先度 select を棚へ移行 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | 必須 `*` の位置が変わるか | `Select` の標準ラベルで確認し、画面ごとにスクショで目視確認する | 解消済み |
| 2 | 右側の▽アイコンが文字に重ならないか | `Select` の標準スタイルで本番画面を確認する | 解消済み |
| 3 | 6 画面すべてで崩れがないか | 画面ごとの before / after を撮る | 解消済み |

**未解決ゼロ確認**: 画面ごとの before / after スクリーンショットを取得済み
