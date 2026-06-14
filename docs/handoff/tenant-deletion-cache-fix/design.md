# design — tenant-deletion-cache-fix

**仕事名**: tenant-deletion-cache-fix  
**日付**: 2026-06-14  
**対象ADR**: ADR-072  
**recon**: docs/handoff/tenant-deletion-cache-fix/recon.md  
**担当**: Hikky-dev

---

## 背景と問題

PR #2149 のコードレビュー指摘。論理削除時に Redis `tenant:{tenant_id}` キャッシュ（TTL=600s）が未削除のため、
`get_current_tenant`（`backend/app/auth/dependencies.py:207`）がキャッシュを先に参照し、
論理削除後最大 10 分間は通常 API が通過するリスクがあった。

KGI「論理削除後、対象テナントのAPIアクセスが403」に反するため修正必須。

---

## 設計方針

論理削除・物理削除の成功確定後（DB commit 後）に `invalidate_tenant_cache(tenant_id)` を呼び、
Redis の `tenant:{tenant_id}` キーを即時削除する。

- Redis 未接続時は no-op（`get_redis()` が None の場合は処理をスキップ）
- 削除失敗（Redis エラー）は `logger.warning` のみ（論理削除自体は成功済みのため例外不要）

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 論理削除 API 呼び出し後に `tenant:{tenant_id}` が Redis から削除される | `test_logical_delete_invalidates_cache` で `invalidate_tenant_cache(id)` が awaited されることを確認 |
| 物理削除 API 呼び出し後に `tenant:{tenant_id}` が Redis から削除される | `test_physical_delete_invalidates_cache` で `invalidate_tenant_cache(id)` が awaited されることを確認 |
| Redis 未接続時に論理削除・物理削除が失敗しない | `invalidate_tenant_cache` の `if not r: return` を `backend/app/cache.py:94-95` で確認 |
| 既存の 9 テストが引き続き通過する | pytest 11 passed |

---

## 外部・過去事例の参照と我々への応用

**事例: Rails の after_commit キャッシュ削除パターン**

ActiveRecord の `after_commit` フックで `Rails.cache.delete(key)` を呼ぶパターンは広く使われる。
論理削除（`discarded_at` 付与）の直後にキャッシュを削除し、次リクエストで DB を再確認させる。
我々の FastAPI 実装でも同様に「DB commit 後にキャッシュ削除」の順序を採用する（DB の確定を先行させることで一貫性を保つ）。

**適用**: `async with db.begin()` ブロック終了 = DB commit 後に `await invalidate_tenant_cache(tenant_id)` を呼ぶことで、DB と Redis の状態乖離を最小化する。
