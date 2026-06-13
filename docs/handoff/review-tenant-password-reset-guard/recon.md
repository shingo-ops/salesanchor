# review-tenant-password-reset-guard — recon

## 既存 ADR 検索結果

- `docs/adr/ADR-028-meta-app-review-tenant.md` — tenant-review 作成の根拠
- `docs/adr/ADR-089-deprecate-customers-unify-to-companies.md` — customers テーブル廃止
- `docs/adr/ADR-138` 相当（password_hash 廃止・Firebase 専一認証）: PR #2067 で実装済み

## 根拠 file:line

### 問題のある実装（修正前）

- `scripts/setup_review_tenant.py:466` — 既存ユーザー検出後も無条件で `_firebase_update_password()` を呼ぶ
- `scripts/setup_review_tenant.py:379` — `FROM customers WHERE` → customers は ADR-089 で廃止済み
- `scripts/setup_review_tenant.py:388` — `INSERT INTO customers` → 同上
- `scripts/setup_review_tenant.py:277` — `_setup_user()` シグネチャに `password_hash` 引数（廃止済み列）

### DB 実態確認

- `public.users` に `password_hash` 列は存在しない（ADR-138 / PR #2067 で DROP 済み）
- `tenant_006.customers` テーブルは存在しない（ADR-089 で DROP 済み）
- `tenant_006.companies` は存在し `company_code` / `name` カラムを持つ

### 修正後の想定動作

- `scripts/setup_review_tenant.py:main()` — `_password_reset_requested()` で分岐
- `scripts/setup_review_tenant.py:_password_reset_requested()` — `ALLOW_REVIEW_TENANT_PASSWORD_RESET=1` チェック
- `scripts/setup_review_tenant.py:_firebase_update_password()` — 明示フラグ時のみ呼ばれる
