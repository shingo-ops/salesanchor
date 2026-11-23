# recon: 登録フォームの別の配送先に「いつもの配送先」印が付かない

基準: origin/main fc20983a4（2026-11-24 取得）。

## 1. 既存 ADR の検索

- `git grep -n is_default docs/adr/ADR-127-registration-post-forms.md`: 住所追加（add_address）は delivery 固定・`is_default=false` 固定（48 行）。請求先変更は降格＋INSERT（40 行・70 行）。
- ADR-126（新規登録フォーム）・ADR-097（会社の自動生成）に、登録時の配送先の is_default を決めた文は無い（`git grep -n is_default docs/adr/ADR-126*.md docs/adr/ADR-097*.md` が 0 件）。

## 2. 観測（実物）

- `frontend/src/pages/register/RegisterPage.tsx:62` `is_default: type === "billing",` — 配送先の空欄の初期値は false。
- `frontend/src/pages/register/RegisterPage.tsx:179-199` 「配送先住所を登録する」を選ぶと、配送先をそのまま（is_default=false）送る。
- `frontend/src/pages/register/RegisterPage.tsx:200-206` 「請求先と同じ住所に送る」を選ぶと、請求先を写して `is_default: true` で送る。
- `backend/app/routers/registration_tokens.py:305-347` `register_customer` は送られた `addr.is_default` をそのまま保存する（337 行）。
- `backend/app/schemas/registration_token.py:79` `is_default: bool = False`。

## 3. 「いつもの配送先」を読む場所（影響）

- `backend/app/tasks/reports.py:63` 会社の書き出しの配送先列は `da.is_default = TRUE` の行だけを読む → 印が無いと空欄。
- `backend/app/routers/companies.py:843-865` 会社のまとめは default の配送先を見て降格する。
- `frontend/src/pages/companies/CompaniesPage.tsx:100` 一覧は `is_default` が無ければ先頭の行を出す（印が無くても表示される）。

## 4. 本番の実測（reader・2026-11-24）

配送先のある会社の数 / そのうち default の配送先がある会社の数:

| tenant | 配送先あり | default あり |
|---|---|---|
| 001（テスト） | 2 | 1 |
| 003 | 0 | 0 |
| 004 | 49 | 49 |
| 005 | 0 | 0 |
| 006 | 0 | 0 |

印の無い会社は tenant_001 の試験で作った 1 件だけ（2026-11-23 に Opus が Chrome で「配送先住所を登録する」を選んで送信）。過去データの直しは不要。
