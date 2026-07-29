# recon.md — deals-perms-rename

## origin/main SHA
`2aaf07a940118dfbcc27235308fc9cd6ca4ba8e9`（git fetch 後確認）

## 既存ADR検索結果
- `docs/adr/ADR-121`: deals廃止 全体計画（便A〜E）
- `docs/adr/ADR-072`: reset_tenant_context 必須ルール（deals廃止 scope外）
- deals-perms-rename は ADR-121 §C の「reservation: deals-perms-rename」として予約済み

## 実測（前 recon カード 2026-07-29 実測値）

### 本番 DB: public.permissions の deals.* 行
```
     key      | resource | action |  description   
--------------+----------+--------+----------------
 deals.create | deals    | create | 案件の登録
 deals.delete | deals    | delete | 案件の削除
 deals.update | deals    | update | 案件情報の編集
 deals.view   | deals    | view   | 案件一覧の閲覧
(4 rows)

id: deals.view=17, deals.create=18, deals.update=19, deals.delete=20
```

### 本番 DB: role_permissions の deals.* 付与（全テナント）
```
 schema_name | deals_rows
-------------+------------
 tenant_001  |         14
 tenant_003  |         14
 tenant_004  |         14
 tenant_005  |         14
 tenant_006  |         14
合計: 70行
```

役割別内訳（全テナント共通）:
- CS: deals.view
- オーナー: deals.create / delete / update / view
- システム管理者: deals.create / delete / update / view
- マネージャー: deals.update / view
- 営業: deals.create / update / view

### FK制約実測
```sql
constraint_name                     | delete_rule
-------------------------------------+-------------
 role_permissions_permission_id_fkey | CASCADE
```
- `role_permissions.permission_id` → `public.permissions.id` ON DELETE CASCADE
- role_permissions 以外に public.permissions を参照する FK: 0件

## コード側参照箇所（origin/main・git grep 実測）

| ファイル | 行 | 内容 |
|---|---|---|
| `backend/app/services/tenant.py:75` | マネージャー付与 | `"deals.view", "deals.update"` |
| `backend/app/services/tenant.py:103` | 営業付与 | `"deals.view", "deals.create", "deals.update"` |
| `backend/app/services/tenant.py:127` | CS付与 | `"deals.view"` |
| `backend/tests/conftest.py:1433` | ALL_TEST_PERMISSIONS | `"deals.view", "deals.create", "deals.update", "deals.delete"` |
| `frontend/tests-e2e/utils/common-mocks.ts:21` | E2Eモック | `"deals.view"` |
| `migrations/002_add_permissions_master.sql:45-48` | INSERT 定義 | deals.view/create/update/delete |

## deals.* をチェックするエンドポイント（origin/main）
- `require_permission("deals.*")` ゼロ件（便C PR#3129 で deals.py 削除済み）
- DesktopShell.tsx / RolesPage.tsx の deals.view 参照も便C で除去済み

## migration 002 の管理方式
- `002_add_permissions_master.sql` は `run_all_migrations.sh` に未登録（デプロイ時実行なし）
- `migrate_phase1.py` と `rls_bootstrap.py` からのみ参照（fresh setup・テスト）
- 002 を直接編集することで fresh setup に deals.* が入らなくなる
- 既存テナント分は新規削除 migration（20260729_170000_drop_deals_permissions.sql）で対応
