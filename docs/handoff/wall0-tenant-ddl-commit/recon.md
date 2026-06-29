# recon — 壁0修正（テナント作成 42P01）

**日時**: 2026-06-29
**ブランチ**: feature/morimoto/wall0-ddl-commit

## ADR 検索結果

- `git grep -i "admin_db\|tenant_schema\|SA-18" docs/adr/` → ADR-018 (RLS), ADR-072 (reset_tenant_context)
- SA-18 Phase2 を導入したコミット: `0df1d291` (feat: SA-18 Phase2 — admin engine 分離, 2026-06-06, PR #1696)
- 壁1（SAVEPOINT 修正）: `73df3133` (fix(admin): テナント作成トランザクション二重開始解消, PR #2604)

## 確定事実（生 recon 出力から）

| # | 事実 | 根拠 (file:line) |
|---|------|-----------------|
| 1 | `create_tenant_schema` は DDL を admin_db で実行するが commit しない | `backend/app/services/tenant.py:1601,1611-1669` |
| 2 | `seed_system_roles(db, ...)` は DDL commit 前に `tenant_X.roles` を参照 → 42P01 | `backend/app/services/tenant.py:1657` |
| 3 | `admin.py` は `db.commit()` のみ・`admin_db.commit()` を呼ばない | `backend/app/routers/admin.py:84,86` |
| 4 | 本番: `ADMIN_DATABASE_URL` 未設定 → admin_engine も同 URL だが別コネクション | VPS env grep |
| 5 | SA-18 Phase2（2026-06-06）以降 本番テナント作成 0 件（最新=2026-05-14） | 本番 DB クエリ |
| 6 | 孤立スキーマは 0 件（既存テナントは全員 Phase2 前に作成済み） | 本番 DB クエリ |
| 7 | `seed_system_roles` は RLS 用 `app.tenant_id` セッション変数を必要とする | 実機確認: 42501 roles INSERT |
| 8 | `SET LOCAL` はバインド変数を受け付けない → `set_config()` を使うべき | PG ドキュメント |

## 変更対象ファイル

- `backend/app/services/tenant.py:1654-1707` — `create_tenant_schema` の DML フェーズ前後
- 新規: `docs/handoff/wall0-tenant-ddl-commit/recon.md`（本ファイル）
- 新規: `docs/handoff/wall0-tenant-ddl-commit/design.md`

## 触らないもの

- `backend/app/routers/admin.py` — 3-3 の検討結果、`get_admin_db` 依存解決で admin_db は自動 close される
- `backend/app/database.py` — admin_engine 設定変更は不要
- tenant_004 (HIGH LIFE JPN) — 検証対象外
