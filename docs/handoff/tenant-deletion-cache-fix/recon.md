# recon — tenant-deletion-cache-fix

**仕事名**: tenant-deletion-cache-fix  
**日付**: 2026-06-14  
**対象ADR**: ADR-072  
**担当**: Hikky-dev

---

## 背景

PR #2149（テナント論理削除・物理削除 API）マージ後に、Redis テナントキャッシュが未削除のまま残る問題が判明。
論理削除後も最大 600 秒（TENANT_CACHE_TTL）の間、通常 API が `is_active=True` キャッシュを参照して通過する可能性がある。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/auth/dependencies.py:207` | `get_current_tenant` が `get_cached_tenant` を先に参照し、キャッシュヒット時は DB を確認しない |
| `backend/app/auth/dependencies.py:210` | キャッシュ内 `is_active=False` なら 403 を返す（キャッシュ内容に依存） |
| `backend/app/cache.py:16` | `TENANT_CACHE_TTL = 600`（10分） |
| `backend/app/cache.py:103` | `cache_tenant(tenant_id, is_active)` — `tenant:{tenant_id}` キーに TTL=600 で書き込む |
| `backend/app/cache.py:92` | `invalidate_tenant_cache(tenant_id)` — 今回追加した削除関数 |
| `backend/app/routers/super_admin_tenants.py:85` | 論理削除: `async with db.begin()` 終了後に `invalidate_tenant_cache` を呼ぶ位置 |
| `backend/app/routers/super_admin_tenants.py:168` | 物理削除: DROP SCHEMA 成功後に `invalidate_tenant_cache` を呼ぶ位置 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | Redis 未接続時の挙動 | `cache.py:92-99` の `if not r: return` で no-op が保証される | ✅ 解消済み |
| 2 | 物理削除後もキャッシュ削除が必要か | DROP SCHEMA 後に `public.tenants` 行も削除されるため、キャッシュが残ると次の `cache_tenant` 呼び出しが stale key を残す可能性あり → 必要 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
