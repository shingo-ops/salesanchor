# ③-b(1) translation maintenance jobs tenant context recon

## 何を直すか

- `backend/app/tasks/translation.py:181-247` で各 tenant の batch 処理に `set_tenant_context` / `reset_tenant_context` / `clear_tenant_context` を追加した。
- `backend/app/services/translation_monitor.py:59-106` で `check_translation_health()` の DB 参照前後に tenant context を追加した。
- `backend/app/tasks/sa02_recon_monitor.py:68-88` で日次突合の tenant ループに tenant context を追加した。

## テスト

- `backend/tests/test_translation_task_context.py:17-90`
- `backend/tests/test_translation_monitor.py:51-112`
- `backend/tests/test_sa02_recon_monitor.py:18-58`

## 補足

- 今回は RLS を有効化しないため、挙動は変えない。
- data_deletion.py は対象外。
