# design — 壁0修正（テナント作成 42P01: tenant_X.roles 不可視）

**作成日**: 2026-06-29
**対象**: `backend/app/services/tenant.py: create_tenant_schema`
**種別**: 危険変更（本番DB トランザクション制御）
**緊急度**: 低（6/6 以降テナント作成 0 件・未使用経路）
**参照**: recon.md（本 handoff）/ SA-18 Phase2 #1696 / 壁1修正 #2604 #2657

## 0. KGI

`POST /api/v1/admin/tenants` が:
1. 42P01（tenant_X.roles 不可視）で落ちない
2. 42501（RLS 権限エラー）で落ちない
3. schema・roles・channel_masters・tenant_settings の4つが作成される
4. 途中失敗でも `tenant_<id>` スキーマが本番に残らない（孤立ゼロ維持）

## 1. 根本原因

`create_tenant_schema` は admin_db（別セッション）で全 DDL を実行するが、
DML（seed_*）を別セッション db で実行する前に admin_db を commit していない。
PostgreSQL は他コネクションの未コミット DDL を見せないため 42P01 になる（壁0）。

また、seed_* は `salesanchor_app` で RLS 付きテーブルに INSERT するが、
セッション変数 `app.tenant_id` が設定されていないため 42501 になる（壁2）。

## 2. 修正内容（`backend/app/services/tenant.py`）

### 壁0: DDL を全部終わらせてから commit（step5 trigger を step4 DML より前に移動）

```
変更前の順序:
  step1-3c: DDL via admin_db
  step4:    seed_system_roles(db)   ← 42P01（テーブル不可視）
  step4b:   seed_default_channel_masters(db)
  step5:    trigger DDL via admin_db
  step6:    tenant_settings INSERT (SAVEPOINT)

変更後の順序:
  step1-3c: DDL via admin_db
  step5:    trigger DDL via admin_db  ← 移動（DDL を一箇所に集約）
  ---       await ddl_db.commit()     ← ★新規（admin_db is not None の場合のみ）
  step4:    set_config('app.tenant_id', tid)  ← ★新規（壁2）
            seed_system_roles(db)
  step4b:   seed_default_channel_masters(db)
  step6:    tenant_settings INSERT (SAVEPOINT)
```

### 壁2: RLS 用セッション変数を設定

```python
await db.execute(
    text("SELECT set_config('app.tenant_id', :tid, true)"),
    {"tid": str(safe_id)},
)
```

`SET LOCAL app.tenant_id = :tid` はバインド変数不可のため `set_config()` を使用。
第3引数 `true` = トランザクション内のみ有効（commit/rollback でリセット）。

### 孤立ゼロガード

DDL commit 後に DML が失敗した場合、スキーマが孤立する。
`except Exception:` で `DROP SCHEMA IF EXISTS {schema_name} CASCADE` を実行して解消。

## 3. dry-run 検証結果（2026-06-29 本番コンテナ）

```
FRESH-RUN 20260629T143123Z [BLOCK-1] 正常系 tenant_9903
  roles: 7 / channel_masters: 6 / tenant_settings: 1
  BLOCK-1 RESULT: GREEN ✓

FRESH-RUN 20260629T143124Z [BLOCK-2] 異常系（孤立ゼロ） tenant_9904
  [orphan-guard] DROP tenant_9904 OK
  schema_exists after failure: False
  BLOCK-2 RESULT: GREEN ✓

OVERALL: GREEN ✓ 壁0+壁2 突破確認
```

## 4. 本番反映手順

1. PR create (base=main) → Reviewer + Evaluator APPROVE
2. Shingo: GO記録 PR 本文記入 + マージ前 main SHA バックアップ記録
3. deploy.yml 起動確認
4. 使い捨てテナントで `POST /api/v1/admin/tenants` → HTTP 201
5. 孤立スキーマがないことを pg_namespace で確認
6. 検証テナントをガード付き物理削除

## 5. 境界

- `admin.py` は変更しない（admin_db は FastAPI DI で自動 close）
- 壁2（壁1 SAVEPOINT）はコード上既修正済み（#2604）、到達確認は §4 で行う
- tenant_004 不可触
