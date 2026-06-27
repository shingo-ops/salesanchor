# recon — migrate-edit-pages-select

**仕事名**: migrate-edit-pages-select
**日付**: 2026-06-26
**対象ADR**: ADR-073
**担当**: Hikky-dev

---

## 背景

リード編集（LeadEditPage）で完了した生 `<select>` → 棚 `<Select>` 移行を、
同型のフルページ編集フォーム3画面（商談・連絡先・スタッフ）に横展開する。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/deals/DealEditPage.tsx:160` | 移行前: `<select>` 通貨フィールド（変更対象） |
| `frontend/src/pages/deals/DealEditPage.tsx:14` | `import { Select }` 追加済み |
| `frontend/src/pages/contacts/ContactEditPage.tsx:141` | 移行前: `<select required>` 会社フィールド（変更対象） |
| `frontend/src/pages/contacts/ContactEditPage.tsx:14` | `import { Select }` 追加済み |
| `frontend/src/pages/staff/StaffEditPage.tsx:178` | 移行前: `<select required>` ロールフィールド（変更対象） |
| `frontend/src/pages/staff/StaffEditPage.tsx:14` | `import { Select }` 追加済み |
| `frontend/src/components/Select.tsx:36` | 棚の Select コンポーネント（金型） |
| `docs/adr/ADR-073-design-system-kgi-rubric.md:1` | ADR-073 — デザインシステム KGI ルーブリック |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | ContactEditPage の会社選択肢ラベル `（）` が ESLint に引っかかるか | ローカル lint 確認 → `（）` は全角括弧で `no-japanese-literal` ルール対象外 | ✅ 解消済み |
| 2 | required な `<select>` の `placeholder` の扱い | Select.tsx:74 確認 → `placeholder` 指定時は `disabled` option として先頭に挿入 | ✅ 解消済み |
| 3 | `form-group` ラッパー div を外して comp-field に変わることで既存スタイルが崩れないか | STEP-3 Playwright 比較確認済み | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
