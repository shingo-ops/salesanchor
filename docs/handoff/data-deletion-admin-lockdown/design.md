# design.md — ③-b(2) data_deletion ADMIN_DATABASE_URL 専用化

**対象ADR**: ADR-SA-18
**recon**: docs/handoff/data-deletion-admin-lockdown/recon.md

## 外部・過去事例の参照と我々への応用

該当なし。今回の変更は、既存の least-privilege 方針を `data_deletion` に適用し、通常接続への silent fallback を止める実装である。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| `ADMIN_DATABASE_URL` が必須である | `backend/tests/test_data_deletion_helpers.py` の fail-loud テスト |
| 管理者接続へ優先的に切り替わる | `backend/tests/test_data_deletion_helpers.py` の engine 再読込テスト |
| backend / celery-worker / celery-beat へ管理者接続が注入される | `docker-compose.yml` の environment 確認 |
| pytest が通る | `pytest backend/tests/test_data_deletion_helpers.py backend/tests/test_tenant_deletion.py backend/tests/test_celery.py -q --no-cov` |
