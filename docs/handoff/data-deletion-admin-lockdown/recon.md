# recon.md — data_deletion ADMIN_DATABASE_URL 隔離

## 前提

- `backend/app/tasks/data_deletion.py:36-59` で管理者接続の解決と module-level engine 初期化を行う。
- `docker-compose.yml:64-67` / `183-186` / `236-239` で backend / celery-worker / celery-beat に `ADMIN_DATABASE_URL` を注入する。
- `backend/tests/conftest.py:16-19` で pytest の import-time guard を SQLite に向ける。
- `backend/tests/test_data_deletion_helpers.py:32-77` で `ADMIN_DATABASE_URL` 優先・fail-loud・engine 解決を確認する。

## 確認結果

1. `backend/app/tasks/data_deletion.py` は `ADMIN_DATABASE_URL` が空なら `RuntimeError` を投げ、`DATABASE_URL` へ silent fallback しない。
2. compose では backend / celery-worker / celery-beat へ `ADMIN_DATABASE_URL` を配るため、アプリ起動と task 実行時に同じ管理者接続を明示できる。
3. テストでは `ADMIN_DATABASE_URL` 未設定時に失敗すること、`postgresql+asyncpg://` が sync URL に正規化されることを確認済み。
