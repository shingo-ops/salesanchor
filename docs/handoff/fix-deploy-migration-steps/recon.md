# recon: fix-deploy-migration-steps

## 現在地
- .github/workflows/deploy.yml:444-466 — PR #3735 で誤った個別マイグレーションステップが追加された
- `scripts/run_all_migrations.sh`:750-753 — 正しいマイグレーション実行（run_sql 関数経由）は既に追記済み

## 問題
deploy.yml の2ステップが `/tmp/migrations/` パスを参照しているが、このパスは VPS 上に存在しない。
`scripts/run_all_migrations.sh` が正しく `docker exec -i postgres psql` ... stdin経由でSQLを渡すパターンで実行するため、個別ステップは不要かつ誤り。

## 変更前後
- 変更前: deploy.yml に `Migration - seed knowledge extraction vocab` と `Migration - create supplier_knowledge_links` の2ステップが存在（/tmp/migrations/ 参照・実行失敗）
- 変更後: 当該2ステップを削除（`scripts/run_all_migrations.sh` が正しく実行する）
