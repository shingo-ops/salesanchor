# products-rls-stage2 recon

## RL-1: BASE
- origin/develop: c8547034f46c6402c5220f9425664712715618c0
- origin/main:    e07ee3a102655cbda5a6c9e9b0e3f7c5a00ef9b3

## RL-2: 段階2-a — dry-run 実証（本番・ROLLBACK保証）

dry-run スクリプト `/tmp/dryrun_products_rls_v2.sql` を本番 DB で実行（ROLLBACK 確約）。

実行ロール: `SET LOCAL SESSION AUTHORIZATION salesanchor_app`（jarvis セッション内で切替、rolsuper=f/rolbypassrls=f）

### 経路別結果

| 経路 | 操作 | 設定 | 期待 | 実測 |
|------|------|------|------|------|
| W-1a | INSERT shared | is_operator=true | 成功 | ○ |
| W-1b | INSERT tenant固有 | tenant_id=6 | 成功 | ○ |
| W-3a | UPDATE shared | is_operator=true | 成功 | ○ |
| W-3b | UPDATE tenant固有(自) | tenant_id=6 | 成功 | ○ |
| W-3c | UPDATE tenant固有(他) | tenant_id=7 | 拒否 | ○ |
| R-1a | SELECT shared | tenant_id=6 | 見える | ○ |
| R-1b | SELECT 他テナント固有 | tenant_id=6, row.tenant=7 | 見えない | ○ |
| R-1c | INSERT tenant固有（非運営） | is_operator='' | 拒否 | ○ |

### DR-2 本番無変更確認

```
$ ssh prod1 'docker exec astro-webapp-postgres-1 psql -U jarvis -d jarvis_db -c "SELECT relrowsecurity AS rls_on, relforcerowsecurity AS force_rls FROM pg_class WHERE relname='"'"'products'"'"' AND relnamespace='"'"'public'"'"'::regnamespace;"'
 rls_on | force_rls
--------+-----------
 f      | f
(1 row)
```

ROLLBACK 確認済み。本番 FORCE-RLS は未適用。

## RL-3: 段階2-b — salesanchor_app 権限確認（本番 READ-ONLY）

```
$ ssh prod1 'docker exec ... psql ... "SELECT rolname, rolsuper, rolbypassrls, rolcanlogin, rolinherit FROM pg_roles WHERE rolname='"'"'salesanchor_app'"'"';"'
 rolname         | rolsuper | rolbypassrls | rolcanlogin | rolinherit
-----------------+----------+--------------+-------------+------------
 salesanchor_app | f        | f            | t           | t
```

```
$ ssh prod1 '... "SELECT r.rolname, g.rolname AS member_of, g.rolsuper, g.rolbypassrls FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member JOIN pg_roles g ON g.oid=m.roleid WHERE r.rolname='"'"'salesanchor_app'"'"';"'
 member | member_of | rolsuper | rolbypassrls
--------+-----------+----------+--------------
(0 rows)
```

```
$ ssh prod1 '... "SELECT grantee, privilege_type FROM information_schema.role_table_grants WHERE table_schema='"'"'public'"'"' AND table_name='"'"'products'"'"' AND grantee IN ('"'"'salesanchor_app'"'"','"'"'PUBLIC'"'"') ORDER BY grantee, privilege_type;"'
     grantee     | privilege_type
-----------------+----------------
 salesanchor_app | DELETE
 salesanchor_app | INSERT
 salesanchor_app | SELECT
 salesanchor_app | UPDATE
(4 rows)
```

FORCE RLS 適用対象（rolbypassrls=f）。前例 translation_glossary と同一 grant（追加 GRANT 不要）。

## RL-4: 前例 — translation_glossary（ADR-SA-17）

```
$ ssh prod1 '... "SELECT grantee, privilege_type FROM information_schema.role_table_grants WHERE table_schema='"'"'public'"'"' AND table_name='"'"'translation_glossary'"'"' AND grantee IN ('"'"'salesanchor_app'"'"','"'"'PUBLIC'"'"') ORDER BY grantee, privilege_type;"'
     grantee     | privilege_type
-----------------+----------------
 salesanchor_app | DELETE
 salesanchor_app | INSERT
 salesanchor_app | SELECT
 salesanchor_app | UPDATE
(4 rows)

$ ssh prod1 '... "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname='"'"'translation_glossary'"'"' AND relnamespace='"'"'public'"'"'::regnamespace;"'
 relrowsecurity | relforcerowsecurity
----------------+---------------------
 t              | t
(1 row)
```

translation_glossary: rls=t / force=t 本番稼働中。grant 構成が public.products と同一。

## RL-5: 42501作業（PR #2604）との非衝突（TC-1〜5）

- PR #2604 `fix-tenant-create-tx-double-begin` MERGED 2026-06-26 10:01 JST → develop 投入済み
- migration: 0 本（`git diff --name-only 4f43bb3d...d793583a -- migrations/` → no output）
- `backend/app/auth/dependencies.py:419,436`: 変更なし（`git diff origin/main...73df3133 -- backend/app/auth/dependencies.py` → no output）
- FORCE ROW LEVEL / app.tenant_id 変更なし（grep 結果：対象行は既存コードのみ）

## RL-6: W-2 影響外確認（段階1 recon RL-6）

`backend/app/routers/purchase_orders.py:255`:
```sql
text("UPDATE products SET quantity = quantity + :qty ...")
```
`search_path = tenant_NNN, public` により `tenant_NNN.products` に解決。FORCE-RLS 対象外。

参照: `docs/handoff/products-rls-stage1/recon.md`

## RL-7: 段階1 develop マージ済み確認

マージコミット: `26f0ede9` (Merge PR #2602)
- `backend/app/routers/super_admin_inbound.py:252,320`: `set/reset_operator_context` 追加済み
- `backend/app/routers/parse_review.py:159,280`: `set/reset_operator_context` 追加済み

## RL-8: migration タイムスタンプ衝突なし

develop 最新: `migrations/20260626_000000_fix_v_company_stats_to_meta_messages.sql`
採番: `migrations/20260626_130000_force_rls_public_products.sql`（衝突なし）
