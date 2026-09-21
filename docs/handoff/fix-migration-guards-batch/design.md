# design: fix-migration-guards-batch

## 変更内容
|基準|検証方法|
|---|---|
|migration 229 通過|デプロイログで ERROR なし|
|全 277 migration 完了|deploy.yml Run database migrations ステップ成功|

## 外部事例
該当なし（内部マイグレーションガード追加）

## 守り手
run_all_migrations.sh の冪等性。CI の migration-guard。
