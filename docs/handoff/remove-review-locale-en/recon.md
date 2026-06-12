# recon: review@salesanchor.jp locale 強制 en 解除

## 問題

`migrations/053_add_users_locale.sql` に `UPDATE public.users SET locale = 'en' WHERE email = 'review@salesanchor.jp'` が含まれており、`scripts/run_all_migrations.sh` がデプロイのたびにこのファイルを実行するため、DB を手動で `ja` に戻しても次のデプロイで `en` に上書きされる。

## 根拠ファイル

- `migrations/053_add_users_locale.sql:4` — locale カラム追加 ALTER TABLE（削除対象の UPDATE はここに存在していた）
- `scripts/run_all_migrations.sh:124` — 053 が毎デプロイ実行されることの確認
- `frontend/src/contexts/LocaleContext.tsx:43` — ログイン後に `/staff/me` から locale を取得して上書きする仕組み
- `backend/app/routers/staff.py:79` — `_fetch_locale()`: `public.users.locale` を返す

## 対象 ADR

ADR-027 (`docs/adr/ADR-027-ui-internationalization.md`)
