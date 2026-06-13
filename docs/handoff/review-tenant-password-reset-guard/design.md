# review-tenant-password-reset-guard — design

**recon**: docs/handoff/review-tenant-password-reset-guard/recon.md

## 問題

`setup_review_tenant.py` は既存 Firebase ユーザーが存在しても毎回 `password = generate_password()` → `_firebase_update_password()` を実行していた。  
`_seed_demo_customers()` が customers テーブル（ADR-089 で廃止済み）を参照してクラッシュした場合、Firebase パスワードだけが変更されて結果ファイルが書かれない状態になっていた（2026-06-13 インシデント）。

## 設計方針

| 基準 | 検証方法 |
|------|----------|
| 既存ユーザー + 通常実行でパスワード変更なし | `_firebase_get_uid()` が non-None かつ `reset_password=False` のとき `_firebase_update_password` 未呼出し |
| `ALLOW_REVIEW_TENANT_PASSWORD_RESET=1` 時のみリセット | `_password_reset_requested()` → `generate_password()` → `_firebase_update_password()` の順で呼ばれる |
| customers テーブル参照なし | `rg "customers" scripts/setup_review_tenant.py` → 0 件 |
| password_hash 列参照なし | `rg "password_hash" scripts/setup_review_tenant.py` → 0 件 |

## 変更点

1. **`_password_reset_requested()`** 関数追加：`ALLOW_REVIEW_TENANT_PASSWORD_RESET == "1"` を返す
2. **Firebase 分岐ロジック変更**（`main()` step 3）：
   - 既存ユーザーあり + フラグなし → `password update skipped` ログのみ
   - 既存ユーザーあり + フラグあり → `generate_password()` + `_firebase_update_password()`
   - 新規ユーザー → `generate_password()` + `_firebase_create_user()`（従来通り）
3. **`_setup_user()` 修正**：`password_hash` 引数・UPDATE 句を削除
4. **`_seed_demo_customers()` 削除**（ADR-089: customers 廃止 + QA Smoke 側に移管）
5. **`DEMO_CUSTOMERS` 定数削除**（`_seed_demo_customers` と共に不要）
6. **`_write_result_file()` 修正**：`new_password=None` の場合 "unchanged" を出力
7. **`_firebase_update_password()` ログ強化**：WARNING レベルに昇格、フラグ名を明示

## 外部事例

Firebase Admin SDK の `update_user(password=...)` は冪等だが副作用が大きい（既存セッション無効化）。  
パスワード変更を明示 opt-in にすることは Firebase ベストプラクティスと一致する。

## 継続事項

- Demo companies (DEMO-001..007) が Meta review / QA smoke で必要な場合、  
  `scripts/qa/seed-tenant.sql` に `companies` テーブルへの INSERT を追加する（別 PR）。
- `docs/runbooks/review-tenant-operations.md` にパスワード管理フローを追記。
