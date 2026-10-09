# recon: fix-migration-lock-timeout

## 調査日
2026-09-24

## 問題

デプロイ run 35954610924 のログ:
```
>>> [188/289] psql < migrations/20260922_050000_fix_phase2c_fk_drop_only.sql
BEGIN
2026/09/24 04:24:19 Run Command Timeout
```
`04:15:20` BEGIN → `04:24:19` タイムアウト = 約9分ブロック。

## 対象ファイル

- `migrations/20260922_050000_fix_phase2c_fk_drop_only.sql:10-18`（BEGIN〜COMMIT）

## 本番DB確認結果

```
-- analysis_results_product_id_fkey の存在確認
SELECT conname FROM pg_constraint WHERE conname = 'analysis_results_product_id_fkey';
→ 0 rows
```

制約は存在しない。`DROP CONSTRAINT IF EXISTS` はロック取得後に即完了する。

## 原因

`ALTER TABLE ... DROP CONSTRAINT` は ACCESS EXCLUSIVE ロックを要求する。
`SET lock_timeout` がないため、Celeryタスク等が `analysis_results` を保持している間は
タイムアウトまで無制限に待機し、`command_timeout: 10m`（deploy.yml）に引っかかる。

## 既存ADR確認

- `git grep -i docs/adr/ -e "lock_timeout"` → ヒットなし
- ADR-082: run_all_migrations.sh SSoT（本 migration はここで管理）

## 変更前後

| | 変更前 | 変更後 |
|---|---|---|
| ロックタイムアウト | なし（無制限） | 30秒 |
| 文ステートメントタイムアウト | なし | 60秒 |
| DDL変更 | なし | なし |
| 冪等性 | 変わらず | 変わらず |
