# design.md — テナント削除機能

- 対応 recon: `docs/handoff/tenant-deletion/recon.md`
- 日付: 2026-06-14
- 担当: shingo-cc
- スコープ: backend API のみ（UI は今回対象外）

---

## 1. KGI / 受け入れ基準

| # | 基準 | 検証方法 |
|---|------|---------|
| KGI-1 | `super_admin` のみがテナント削除 API を呼べる | `require_super_admin` 付き EP に非 super_admin が POST → 403 を確認 |
| KGI-2 | 論理削除後、対象テナントの通常 API アクセスが 403 になる | `is_active=False` 設定後、テナントユーザーで任意 EP を呼び → 403 確認 |
| KGI-3 | 物理削除後、`tenant_NNN` スキーマが存在しない | `pg_namespace` で schema 不在を確認 |
| KGI-4 | 物理削除後、`public.tenants` / `public.users` の整合が崩れない | CASCADE FK 動作を PostgreSQL 実機で確認 |
| KGI-5 | 削除操作の中央監査ログが DROP 後も残る | `public.tenant_deletion_audit` に行が残ることを確認 |
| KGI-6 | PostgreSQL 実機テストで DROP SCHEMA / FK / DDL 永続化を確認 | `RLS_TEST_DATABASE_URL` 使用の pytest で全テスト PASS |
| KGI-7 | UI なし | フロントエンドに変更なし・確認不要 |

---

## 2. ADR 方針

### 2-1. 新規 ADR 起案の要否

**結論: design.md 内で PO 決定事項として扱い、実装 PR のマージ後に ADR 起案する。**

理由:
- 本機能は super_admin 専用の運用ツール（エンドユーザー向け機能ではない）
- 設計論点は本 design.md に集約し、PO の GO を受けてから実装する
- 実装完了後、本 design.md を ADR 草稿として昇格させる

### 2-2. 既存 ADR との関係

| ADR | 適用方針 |
|-----|---------|
| ADR-023（スタッフ3層同期） | Firebase 無効化パターンの参照元。今回は **Firebase 無効化を Phase 3 スコープ外** とする（後述 2-3） |
| ADR-034（テナント migration 自動化） | 作成フロー逆順の設計根拠として参照 |
| ADR-036（スキーマ整合性） | 削除後の整合性テストを `test_tenant_schema_integrity.py` パターンで追加 |
| ADR-072（tenant_context reset） | **super_admin_tenants.py には適用しない。** `get_current_tenant` を付けない設計のため tenant context は設定されず、`reset_tenant_context()` は不要。`get_db` finally 句が context をクリアする |
| ADR-131（context 自動リセット） | ADR-072 と同様に不適用 |

### 2-3. Firebase 無効化の要否（PO 決定事項）

**Phase 3 スコープ外。** 理由と根拠:

- `is_active=False` を設定すると `get_current_tenant()` が全ルートで 403 を返す（recon A-2）
- Firebase JWT は期限切れまで有効だが、毎リクエストで `Tenant.is_active` を確認するため  
  JWT が有効でも API アクセスは遮断される
- Firebase SDK での `update_user(uid, disabled=True)` は全ユーザーの UID 列挙が必要で複雑
- MVP では DB 側遮断で十分。Firebase 無効化は Phase 4 で検討

**PO 確認事項**: Firebase 側を無効化しないことで問題が生じる業務ユースケースがあればフラグを立てること。

---

## 3. 実装方針

### 3-1. ルーター配置

**新規ファイル: `backend/app/routers/super_admin_tenants.py`**

理由:
- `admin.router` は `main.py:204-207` で `Depends(get_current_tenant)` + `Depends(get_current_admin)` がルーターレベルで付与されている
- テナント削除は public schema 操作のため `get_current_tenant` を付けない設計が必要
- 既存の `super_admin_*` 系（`super_admin_dex.py` 等）は `prefix="/api/v1"` + エンドポイントレベルで `require_super_admin` を付与するパターン — 同パターンに揃える

**main.py への追加登録**（既存 super-admin ブロックに追記）:

```python
# main.py
from app.routers import super_admin_tenants
app.include_router(super_admin_tenants.router, prefix="/api/v1", tags=["super-admin"])
```

### 3-2. エンドポイント設計

```
DELETE /api/v1/super-admin/tenants/{tenant_id}
  Depends: require_super_admin（エンドポイントレベル）
  Body: { "confirm": "DELETE:{tenant_code}" }

DELETE /api/v1/super-admin/tenants/{tenant_id}/physical
  Depends: require_super_admin（エンドポイントレベル）
  Body: { "confirm": "DELETE:{tenant_code}" }
```

- 論理削除 EP: `is_active=False` のみ（可逆）
- 物理削除 EP: logical 済みを前提に DROP SCHEMA CASCADE（不可逆）
- `confirm` フィールド: 誤操作防止のため `"DELETE:{tenant_code}"` 文字列一致を必須とする

### 3-3. 論理削除

**採用案: `is_active=False` のみ（MVP）。`deleted_at` カラムは今回追加しない。**

| 案 | 内容 | 工数 | 判定 |
|----|------|------|------|
| **A（採用）** | `is_active=False` のみ | migration 不要 | ✅ MVP |
| B | `deleted_at TIMESTAMPTZ` カラムを追加 | additive migration 必要 | Phase 4 |

`deleted_at` が不要な理由:
- 削除時刻は中央監査ログ（`public.tenant_deletion_audit`）に記録する
- `is_active=False` でアクセス遮断は即座に有効
- migration を増やすと deploy.yml 変更が必要になり PO GO フローが複雑になる

**実装スケッチ**:

```python
# backend/app/routers/super_admin_tenants.py
router = APIRouter()

@router.delete(
    "/super-admin/tenants/{tenant_id}",
    dependencies=[Depends(require_super_admin)],
)
async def delete_tenant_logical(tenant_id: int, body: TenantDeleteRequest, ...):
    if body.confirm != f"DELETE:{tenant.tenant_code}":
        raise HTTPException(400, "confirm 文字列不一致")
    async with db.begin():
        tenant.is_active = False
        await _record_deletion_audit(
            db, tenant, mode="logical", status="succeeded", actor=current_user
        )
    # reset_tenant_context() は不要（super_admin_tenants.py は get_current_tenant なし）
    # → get_db finally 句が context をクリア
```

### 3-4. 物理削除

**推奨実行順序**（DROP 失敗時のリカバリを考慮）:

| ステップ | 内容 | 失敗時の状態 |
|---------|------|------------|
| 1 | 対象確認（is_active=False 確認・schema 存在確認） | 中断 → 再試行可 |
| 2 | バックアップ取得（`pg_dump -n tenant_NNN`） | 中断 → 再試行可 |
| 3 | 中央監査ログ `status=started` を記録（DROP 前） | 記録後に DROP 失敗 → `failed` で更新 |
| 4 | `DROP SCHEMA tenant_NNN CASCADE` | 失敗 → tenant は `is_active=false` のまま残存・再試行可 |
| 5 | `await admin_db.commit()` | — |
| 6 | `DELETE FROM public.tenants WHERE id = :id`（CASCADE で public.users も削除） | — |
| 7 | 中央監査ログ `status=succeeded` + `completed_at=NOW()` に更新 | — |

**この順序の根拠**:
- DROP（4）→ public.tenants DELETE（6）の順にする理由: DELETE 先行で DROP が失敗した場合、registry/users だけ消えてスキーマが残る状態になり手動リカバリが困難になる
- DROP 失敗時は tenant が `is_active=false` のまま残るため再試行可能（is_active=false なので API アクセスは遮断済み）

**対象確認 SQL（READ ONLY）**:

```sql
SELECT id, tenant_code, tenant_name, is_active
FROM public.tenants
WHERE id = :tenant_id;
```

**DROP 前バックアップ**:

```bash
# scripts/backup_tenant_before_drop.sh （新規作成）
pg_dump -n tenant_NNN $DATABASE_URL > /tmp/tenant_NNN_pre_drop_$(date +%Y%m%d_%H%M%S).sql
```

**DROP ドライラン**（`DROP` は実行せず対象テーブル一覧を確認）:

```sql
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname = 'tenant_004'
ORDER BY tablename;
```

**実装スケッチ**:

```python
@router.delete(
    "/super-admin/tenants/{tenant_id}/physical",
    dependencies=[Depends(require_super_admin)],
)
async def delete_tenant_physical(tenant_id: int, body: TenantDeleteRequest, ...):
    # 1. 対象確認
    if body.confirm != f"DELETE:{tenant.tenant_code}":
        raise HTTPException(400)
    if not tenant or tenant.is_active:
        raise HTTPException(400, "論理削除が先に必要です")
    schema_name = f"tenant_{tenant_id:03d}"

    # 3. 監査ログ physical_started（DROP 前に記録）
    audit_id = await _record_deletion_audit(
        db, tenant, mode="physical", status="started", actor=current_user
    )
    await db.commit()
    # reset_tenant_context() は不要（super_admin_tenants.py は get_current_tenant なし）

    try:
        # 4-5. DROP SCHEMA + 明示 commit（§4 採用案 A）
        await admin_db.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        await admin_db.commit()

        # 6. public.tenants DELETE（CASCADE → public.users 連鎖削除）
        async with db.begin():
            await db.execute(text("DELETE FROM public.tenants WHERE id = :id"), {"id": tenant_id})

        # 7. 監査ログ succeeded
        await _update_audit_status(db, audit_id, status="succeeded")
        await db.commit()

    except Exception as exc:
        await _update_audit_status(db, audit_id, status="failed", error=str(exc))
        await db.commit()
        raise
```

### 3-5. 中央監査ログ保全（`public.tenant_deletion_audit`）

新規テーブルが必要（migration 対象 — §6 参照）。

```sql
CREATE TABLE IF NOT EXISTS public.tenant_deletion_audit (
    id              SERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL,
    tenant_code     TEXT NOT NULL,
    tenant_name     TEXT NOT NULL,
    mode            TEXT NOT NULL CHECK (mode IN ('logical', 'physical')),
    status          TEXT NOT NULL CHECK (status IN ('started', 'succeeded', 'failed')),
    actor_id        INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
    actor_email     TEXT NOT NULL,
    executed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    meta            JSONB
);
```

- `status`: 物理削除の開始 / 成功 / 失敗を区別（論理削除は `succeeded` 直書き）
- `completed_at`: DROP + DELETE 完了時刻（started → succeeded/failed で更新）
- `error_message`: DROP 失敗時の例外メッセージを保存
- テナントスキーマとは独立した `public` スキーマに保持 → DROP 後も記録が残る
- `actor_id` は `ON DELETE SET NULL`（actor ユーザー削除時も監査行は残る）

### 3-6. reports.py 呼び出し元確認

recon B-5 で `reports.py:187` の `export_csv(tenant_id: int, ...)` に is_active フィルタがないことを確認した。

**対応**: 論理削除後に `is_active=False` テナントの Celery タスクがエンキューされる経路を実装時に確認し、必要なら呼び出し元でガードを追加する。実装 PR のスコープとして含める。

---

## 4. トランザクション / DDL 設計

recon C-9 の確認事項: `admin_db`（`get_admin_db()`）は成功時 `commit()` なし・`AUTOCOMMIT` 未設定。

### 選択肢比較

| 案 | 内容 | メリット | デメリット |
|----|------|---------|-----------|
| **A（採用）** | `await admin_db.commit()` を DROP 後に明示実行 | 既存パターン最小変更・意図が明確 | commit 漏れのリスク（レビューで担保） |
| B | DROP 専用に `isolation_level="AUTOCOMMIT"` 接続を使う | DDL セマンティクスが明確 | 接続管理の複雑化・既存 admin_db と別建て |
| C | 補償トランザクション（DROP 失敗時のリカバリ手順） | 最も安全 | 実装複雑・Phase 3 MVP には過剰 |

**採用: 案 A — `await admin_db.commit()` 明示実行。**

理由:
- DROP SCHEMA は本質的に不可逆（トランザクション内でも PostgreSQL は DDL をロールバックできる場合があるが、実機依存）
- 明示 commit でコードの意図を明確にする
- 案 B は接続管理が増える。案 C は Phase 3 MVP として過剰
- コードレビューで commit 行を確認することで担保する

**DDL 実行パターン（確定）**:

```python
# DROP SCHEMA は admin_db セッションで実行 + 明示 commit
await admin_db.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
await admin_db.commit()
```

---

## 5. テスト計画

### 5-1. SQLite 単体テスト

- 論理削除 EP: `is_active=False` になること
- `require_super_admin` ガード: 非 super_admin で 403
- `confirm` フィールド不一致で 400

### 5-2. PostgreSQL 実機テスト（`RLS_TEST_DATABASE_URL` 必須）

先例: `backend/tests/test_tenant_schema_integrity.py`（`RLS_TEST_DATABASE_URL` 指定時のみ実行）

| テストケース | 確認内容 |
|------------|---------|
| **DDL 永続化確認** | `await admin_db.commit()` 後に `pg_namespace` でスキーマ存在を確認（C-9 要確認事項の実証） |
| **pg_constraint FK 確認** | `tenant_NNN → public.permissions/users` FK が存在することを確認（C-8 実機証拠） |
| **DROP CASCADE 後 FK 消去** | DROP 後に pg_constraint から該当 FK 行が消えることを確認 |
| **public 側への影響なし** | `public.permissions` / `public.users` が DROP 後も残ることを確認 |
| **論理削除後 403** | `is_active=False` 後に認証 EP 呼び → 403 |
| **物理削除後 schema 不在** | `SELECT nspname FROM pg_namespace WHERE nspname = 'tenant_NNN'` → 0行 |
| **中央監査ログ残存** | `public.tenant_deletion_audit` に行が残ること |
| **super_admin 以外 403** | `require_super_admin` が非 super_admin をブロック |
| **confirm 文字列不一致 400** | 誤操作防止ガードの動作確認 |

### 5-3. テストファイル配置

```
backend/tests/test_tenant_deletion.py   # 新規
  - SQLite テスト（論理削除・権限ガード・confirm バリデーション）
  - PostgreSQL 実機テスト（`RLS_TEST_DATABASE_URL` skip guard）
```

---

## 6. 危険変更の扱い

### migration

`public.tenant_deletion_audit` テーブル新設が必要（additive migration — 新規 public table 追加のため許可範囲内）。

- ファイル命名: `migrations/YYYYMMDD_HHMMSS_add_tenant_deletion_audit.sql`
- `deploy.yml` への追記必須（migration-guard が検知）
- **PO GO 必要**: migration を含む PR のため develop マージ前に PO 承認が必要

### DROP SCHEMA

- 物理削除は不可逆。実装 PR は feature ブランチで待機
- develop / main へのマージは PO GO 後
- 本番実行前に `pg_dump -n tenant_NNN` によるバックアップを必須手順とする

### ブランチ待機ルール（ADR-135 準拠）

```
feature/morimoto/tenant-deletion-impl
  ↓ PO GO 後のみ
develop → main
```

---

## 7. 実装タスク一覧（Phase 3）

| # | タスク | 危険変更 |
|---|--------|---------|
| T-1 | `public.tenant_deletion_audit` migration 作成 + deploy.yml 追記 | ✅ PO GO 必要 |
| T-2 | 論理削除 EP 実装（`DELETE /api/v1/super-admin/tenants/{tenant_id}`） | - |
| T-3 | 物理削除 EP 実装（`DELETE /api/v1/super-admin/tenants/{tenant_id}/physical`） | ✅ DROP 含む |
| T-4 | `scripts/backup_tenant_before_drop.sh` 新規作成 | ✅ PO GO 必要 |
| T-5 | `reports.py` 呼び出し元の is_active ガード確認・必要なら修正 | - |
| T-6 | `test_tenant_deletion.py` 作成（SQLite + PostgreSQL 実機） | - |

---

## 8. 外部事例

| 事例 | 内容 | 参照 |
|------|------|------|
| Stripe テナント削除 | 即時削除は行わず 30 日間の猶予期間（logical delete）後に物理削除を自動実行 | 公式ドキュメント |
| GitHub Organization 削除 | 90 日間リカバリ可能（soft delete）+ 完全削除は人間の確認付き | GitHub Help |
| Heroku アプリ削除 | アプリ名を入力させる確認フォーム（誤操作防止）+ 即時削除 | Heroku Dev Center |

**今回の参照決定**: confirm 文字列（`"DELETE:{tenant_code}"`）は Heroku 方式を採用。  
猶予期間（Stripe/GitHub 方式）は今回は設けず、論理削除と物理削除を分離したエンドポイントで代替する。
