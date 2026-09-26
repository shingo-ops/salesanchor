# recon: Select金型 SelectControl pilot (#2666)

## 対象ADR
ADR-067, ADR-144

## 現在地把握

### 変更ファイル

- `frontend/src/components/Select.tsx:1` — SelectControl（bare）を既存 Select wrapper と同ファイルに分離追加
- `frontend/src/components/FormField.css:1` — SelectControl 用スタイル追加（CSS変数準拠）
- `frontend/src/components/Select.stories.tsx:1` — SelectControl の Storybook story 追加
- `frontend/src/pages/invoices/InvoicesPage.tsx:1` — filter-bar の select 1か所を SelectControl へ差し替え（パイロット）
- `tasks/todo.md:13` — Select 本体分離 + InvoicesPage パイロット 作業記録

### 既存構造

- `frontend/src/components/Select.tsx` — 旧 Select wrapper（FormField 連携）がそのまま残存
- `frontend/src/pages/invoices/InvoicesPage.tsx` — filter-bar に生 select が複数使用されていた
