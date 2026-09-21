# design: fix-migration-guards-batch

## 変更内容
|基準|検証方法|
|---|---|
|migration 229 通過|デプロイログで ERROR なし|
|全 277 migration 完了|deploy.yml Run database migrations ステップ成功|

## 外部・過去事例の参照と我々への応用
該当なし（内部マイグレーションガード追加）。過去 PR #3651 で同様のパターン（schema 存在ガード）を採用済み。今回はその方針を踏襲する。

## 維持の仕組み
守り手: run_all_migrations.sh の冪等性。CI の migration-guard チェック。
