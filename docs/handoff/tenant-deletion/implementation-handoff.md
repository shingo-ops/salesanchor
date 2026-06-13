# implementation-handoff.md — テナント削除機能

- 根拠 recon: `docs/handoff/tenant-deletion/recon.md`
- 根拠 design: `docs/handoff/tenant-deletion/design.md`
- 日付: 2026-06-14
- 担当: shingo-cc → 実装: Claude Code (feature/morimoto/tenant-deletion-impl)

---

## 1. 目的 / KGI

super_admin が特定テナントを安全に論理削除・物理削除できる backend API を実装する。

| # | KGI | 検証方法 |
|---|-----|---------|
| KGI-1 | `super_admin` のみが削除 API を呼べる | 非 super_admin → 403 |
| KGI-2 | 論理削除後、対象テナントの API アクセスが 403 | `is_active=False` 後に任意 EP → 403 |
| KGI-3 | 物理削除後、`tenant_NNN` スキーマが存在しない | `pg_namespace` で schema 不在確認 |
| KGI-4 | 物理削除後、`public.tenants` / `public.users` の整合が崩れない | PostgreSQL 実機テストで CASCADE FK 動作確認 |
| KGI-5 | 削除操作の中央監査ログが DROP 後も残る | `public.tenant_deletion_audit` に行が残る |
| KGI-6 | PostgreSQL 実機テストが全 PASS | `RLS_TEST_DATABASE_URL` 使用の pytest PASS |

---

## 2. 対象範囲と対象外

**対象（今回実装）**:
- `backend/app/routers/super_admin_tenants.py` 新規作成
- `migrations/YYYYMMDD_HHMMSS_add_tenant_deletion_audit.sql` 新規作成
- `backend/app/main.py` — router import & include_router 追加
- `scripts/run_all_migrations.sh` — migration 追記
- `scripts/backup_tenant_before_drop.sh` 新規作成
- `backend/tests/test_tenant_deletion.py` 新規作成
- `backend/tests/conftest.py` — SQLite rewrite / test table setup / cleanup 追加
- `.github/workflows/migration-test.yml` — SQLite セットアップに `public.tenant_deletion_audit` / `public.tenants` 最小 CREATE TABLE 追加
- `backend/app/tasks/reports.py` — 呼び出し元 is_active ガード確認・必要なら修正

**対象外（今回実装しない）**:
- フロントエンド（削除ボタン・管理画面）— Phase 4
- Firebase ユーザー無効化（`firebase_admin.auth.update_user`）— Phase 4
- `deleted_at` カラム追加 — Phase 4
- `public.tenants` CASCADE FK の設定変更

---

## 3. 根拠まとめ

| 設計判断 | 根拠 |
|---------|------|
| `admin.router` を使わない | `main.py:204-207` でルーターレベルに `get_current_tenant` + `get_current_admin` が付与されており、public schema 操作に不適 |
| `super_admin_tenants.py` 新設 | `super_admin_dex.py` 等の既存パターンに準拠（`prefix="/api/v1"` + EP レベルで `require_super_admin`） |
| `reset_tenant_context()` 不使用 | `get_current_tenant` を付けない設計のため tenant context は設定されない。`get_db` finally 句がクリアする |
| DROP → commit → DELETE の順 | DELETE 先行で DROP 失敗するとスキーマが残り手動リカバリ困難（recon A-3 作成フロー逆順） |
| `await admin_db.commit()` 明示 | `get_admin_db()` は成功時 commit なし・AUTOCOMMIT 未設定（recon C-9）。DDL 永続化を明示的に保証 |
| `public.tenant_deletion_audit` | テナントスキーマを DROP すると audit_logs も消える（recon D-12）。DROP 後も記録が残る public schema に設置 |
| confirm = `"DELETE:{tenant_code}"` | Heroku 方式の誤操作防止（design.md §8） |
| PostgreSQL 実機テスト必須 | SQLite では `DROP SCHEMA CASCADE` 不可（recon E-15） |

---

## 4. 変更対象ファイル一覧

| ファイル | 種別 | 危険変更 |
|---------|------|---------|
| `backend/app/routers/super_admin_tenants.py` | **新規** | - |
| `backend/app/main.py` | **修正**（import + include_router 追加） | - |
| `migrations/20260614_120000_add_tenant_deletion_audit.sql` | **新規** | ✅ PO GO 必要 |
| `scripts/run_all_migrations.sh` | **修正**（末尾に run_sql 追記） | ✅ PO GO 必要 |
| `scripts/backup_tenant_before_drop.sh` | **新規** | ✅ PO GO 必要 |
| `backend/tests/test_tenant_deletion.py` | **新規** | - |
| `backend/tests/conftest.py` | **修正**（SQLite rewrite / test table setup / cleanup 追加） | - |
| `.github/workflows/migration-test.yml` | **修正**（SQLite セットアップに `public.tenant_deletion_audit` / `public.tenants` 最小 CREATE を追加） | ⚠️ CI 設定変更 |
| `backend/app/tasks/reports.py` | **条件修正**（呼び出し元に is_active ガードが必要な場合のみ） | - |

> **PO GO まで feature ブランチ `feature/morimoto/tenant-deletion-impl` で待機。**  
> develop / main へのマージは PO の GO コメント（`GO: Shingo YYYY-MM-DD`）確認後のみ。

---

## 5. ファイルごとの実装方針

### 5-1. `backend/app/routers/super_admin_tenants.py`（新規）

`super_admin_dex.py:38` のパターンを踏襲。

```python
"""
super_admin 用テナント論理削除 / 物理削除 API。

API:
  DELETE /api/v1/super-admin/tenants/{tenant_id}          — 論理削除
  DELETE /api/v1/super-admin/tenants/{tenant_id}/physical — 物理削除
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_admin_db, get_db

router = APIRouter()


class TenantDeleteRequest(BaseModel):
    confirm: str  # "DELETE:{tenant_code}" の完全一致を要求


# ── 論理削除 ──────────────────────────────────────────────────────────────
@router.delete(
    "/super-admin/tenants/{tenant_id}",
    dependencies=[Depends(require_super_admin)],
)
async def delete_tenant_logical(
    tenant_id: int,
    body: TenantDeleteRequest,
    current_user=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    # SELECT〜UPDATE〜audit INSERT を同一トランザクション内に収める
    # （トランザクション外で SELECT すると TOCTOU になるため）
    async with db.begin():
        # テナント取得（ロック不要だがトランザクション内で確認）
        row = (
            await db.execute(
                text("SELECT id, tenant_code, tenant_name, is_active FROM public.tenants WHERE id = :id"),
                {"id": tenant_id},
            )
        ).mappings().one_or_none()
        if not row:
            raise HTTPException(404, "テナントが見つかりません")

        # confirm 文字列チェック（誤操作防止）
        if body.confirm != f"DELETE:{row['tenant_code']}":
            raise HTTPException(400, f"confirm 文字列不一致。期待値: DELETE:{row['tenant_code']}")

        if not row["is_active"]:
            raise HTTPException(400, "すでに論理削除済みです")

        # is_active を False に
        await db.execute(
            text("UPDATE public.tenants SET is_active = FALSE WHERE id = :id"),
            {"id": tenant_id},
        )
        # 中央監査ログ（succeeded 直書き）
        await db.execute(
            text("""
                INSERT INTO public.tenant_deletion_audit
                    (tenant_id, tenant_code, tenant_name, mode, status, actor_id, actor_email,
                     executed_at, completed_at)
                VALUES
                    (:tenant_id, :tenant_code, :tenant_name, 'logical', 'succeeded',
                     :actor_id, :actor_email, NOW(), NOW())
            """),
            {
                "tenant_id": tenant_id,
                "tenant_code": row["tenant_code"],
                "tenant_name": row["tenant_name"],
                "actor_id": current_user.id,
                "actor_email": current_user.email,
            },
        )
    # get_current_tenant を使わない設計のため reset_tenant_context() 不要
    # get_db finally 句が context をクリアする

    return {"status": "ok", "tenant_id": tenant_id, "mode": "logical"}


# ── 物理削除 ──────────────────────────────────────────────────────────────
@router.delete(
    "/super-admin/tenants/{tenant_id}/physical",
    dependencies=[Depends(require_super_admin)],
)
async def delete_tenant_physical(
    tenant_id: int,
    body: TenantDeleteRequest,
    current_user=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
    admin_db: AsyncSession = Depends(get_admin_db),
) -> dict:
    # 1. 対象確認
    row = (
        await db.execute(
            text("SELECT id, tenant_code, tenant_name, is_active FROM public.tenants WHERE id = :id"),
            {"id": tenant_id},
        )
    ).mappings().one_or_none()
    if not row:
        raise HTTPException(404, "テナントが見つかりません")

    # confirm 文字列チェック
    if body.confirm != f"DELETE:{row['tenant_code']}":
        raise HTTPException(400, f"confirm 文字列不一致。期待値: DELETE:{row['tenant_code']}")

    # 論理削除済みであることを確認（物理削除は論理削除後のみ）
    if row["is_active"]:
        raise HTTPException(400, "論理削除（is_active=False）が先に必要です")

    schema_name = f"tenant_{tenant_id:03d}"

    # スキーマ名は整数から生成しているが、念のため英数字のみを確認
    if not schema_name.replace("_", "").isalnum():
        raise HTTPException(400, "不正な tenant_id")

    # 3. 監査ログ: status=started を DROP 前に記録
    audit_result = await db.execute(
        text("""
            INSERT INTO public.tenant_deletion_audit
                (tenant_id, tenant_code, tenant_name, mode, status, actor_id, actor_email, executed_at)
            VALUES
                (:tenant_id, :tenant_code, :tenant_name, 'physical', 'started',
                 :actor_id, :actor_email, NOW())
            RETURNING id
        """),
        {
            "tenant_id": tenant_id,
            "tenant_code": row["tenant_code"],
            "tenant_name": row["tenant_name"],
            "actor_id": current_user.id,
            "actor_email": current_user.email,
        },
    )
    audit_id = audit_result.scalar_one()
    await db.commit()
    # reset_tenant_context() 不要（get_current_tenant なし）

    try:
        # 4. DROP SCHEMA CASCADE
        await admin_db.execute(
            text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")  # noqa: S608
        )
        # 5. admin_db を明示 commit（get_admin_db に success-commit がないため必須）
        await admin_db.commit()

        # 6. public.tenants DELETE（CASCADE → public.users 連鎖削除）
        async with db.begin():
            await db.execute(
                text("DELETE FROM public.tenants WHERE id = :id"),
                {"id": tenant_id},
            )

        # 7. 監査ログ: status=succeeded + completed_at
        async with db.begin():
            await db.execute(
                text("""
                    UPDATE public.tenant_deletion_audit
                    SET status = 'succeeded', completed_at = NOW()
                    WHERE id = :id
                """),
                {"id": audit_id},
            )

    except Exception as exc:
        # 失敗時: 監査ログを failed に更新
        try:
            async with db.begin():
                await db.execute(
                    text("""
                        UPDATE public.tenant_deletion_audit
                        SET status = 'failed', error_message = :err, completed_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": audit_id, "err": str(exc)[:2000]},
                )
        except Exception:
            pass
        raise

    return {"status": "ok", "tenant_id": tenant_id, "mode": "physical", "schema_dropped": schema_name}
```

**ポイント**:
- `get_current_tenant` を依存に入れない → tenant context は設定されない → `reset_tenant_context()` 不要
- `schema_name` は `f"tenant_{tenant_id:03d}"` で整数から生成（インジェクション対策）
- `admin_db.commit()` を DROP 後に明示（recon C-9 対応）
- 監査ログを `try` の外（3）で先行 INSERT し、`except` で `failed` に更新

---

### 5-2. `backend/app/main.py`（修正）

#### import 追加

`main.py` の既存 super_admin import ブロック（`main.py:79-87` 周辺）に追記:

```python
# 既存
from app.routers import (
    ...
    super_admin_tcg,
    super_admin_tenants,   # ← この行を追加（アルファベット順）
)
```

#### include_router 追加

`main.py` の super_admin ブロック末尾（`super_admin_phase_switch` の後）に追記:

```python
# テナント論理削除 / 物理削除
app.include_router(
    super_admin_tenants.router, prefix="/api/v1", tags=["super-admin"],
)
```

---

### 5-3. `migrations/20260614_120000_add_tenant_deletion_audit.sql`（新規・⚠️危険変更）

```sql
-- テナント削除操作の中央監査ログテーブル新設
-- public スキーマに配置するため DROP SCHEMA 後も記録が残る
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

**ファイル名のタイムスタンプ**: 作業開始直前の `date +%Y%m%d_%H%M%S` で確定すること（並行衝突防止）。

---

### 5-4. `scripts/run_all_migrations.sh`（修正・⚠️危険変更）

末尾の `echo "✅ 全マイグレーション完了"` ブロック **直前**に追記:

```bash
# テナント削除 中央監査ログ（public.tenant_deletion_audit 新設）
run_sql migrations/20260614_120000_add_tenant_deletion_audit.sql
```

> `backend/CLAUDE.md` の migration 登録ルール: 登録漏れは本番 500 エラーの原因（PR #1277 の前例）。
> ファイル名は migration SQL ファイルと完全一致させること。

---

### 5-5. `scripts/backup_tenant_before_drop.sh`（新規・⚠️危険変更）

```bash
#!/usr/bin/env bash
# backup_tenant_before_drop.sh — 物理削除前のテナントスキーマバックアップ
#
# 使用例:
#   TENANT_ID=4 DATABASE_URL=postgresql+asyncpg://... bash scripts/backup_tenant_before_drop.sh
#   TENANT_ID=4 PG_DUMP_DATABASE_URL=postgresql://...  bash scripts/backup_tenant_before_drop.sh
#
# pg_dump は libpq URL（postgresql://...）を要求する。
# SQLAlchemy の URL（postgresql+asyncpg://...）は直接渡せないため変換する。
# PG_DUMP_DATABASE_URL が設定されていればそれを優先し、変換不要の URL を直接指定できる。
set -euo pipefail

TENANT_ID="${TENANT_ID:?TENANT_ID 環境変数が必要です}"

# PG_DUMP_DATABASE_URL が設定されていればそれを使用。なければ DATABASE_URL を変換。
RAW_DATABASE_URL="${PG_DUMP_DATABASE_URL:-${DATABASE_URL:?DATABASE_URL or PG_DUMP_DATABASE_URL is required}}"
# postgresql+asyncpg:// → postgresql:// に変換（pg_dump が認識できる形式）
DUMP_DATABASE_URL="${RAW_DATABASE_URL/postgresql+asyncpg:/postgresql:}"

SCHEMA_NAME="tenant_$(printf '%03d' "${TENANT_ID}")"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_FILE="/tmp/${SCHEMA_NAME}_pre_drop_${TIMESTAMP}.sql"

echo "バックアップ開始: schema=${SCHEMA_NAME}, 出力=${OUTPUT_FILE}"
pg_dump -n "${SCHEMA_NAME}" "${DUMP_DATABASE_URL}" > "${OUTPUT_FILE}"
echo "✅ バックアップ完了: ${OUTPUT_FILE}"
echo "保存場所: /tmp/ はコンテナ再起動で消えます。ホスト側に退避してください。"
```

---

### 5-6. `.github/workflows/migration-test.yml`（修正・⚠️ CI 設定変更）

`backend/CLAUDE.md` の migration-test 拡充ルール:  
「migration が操作するテーブルが migration-test.yml セットアップになければ最小定義を追加すること」

追加箇所: `migration-test.yml` 内の PostgreSQL セットアップ SQL ブロック（既存の `public.tenants` INSERT がある行の近く）に以下を追加:

```sql
-- テナント削除 中央監査ログ新設 migration のテスト用テーブル
CREATE TABLE IF NOT EXISTS public.tenant_deletion_audit (
    id            SERIAL PRIMARY KEY,
    tenant_id     INTEGER NOT NULL,
    tenant_code   TEXT NOT NULL,
    tenant_name   TEXT NOT NULL,
    mode          TEXT NOT NULL,
    status        TEXT NOT NULL,
    actor_id      INTEGER,
    actor_email   TEXT NOT NULL,
    executed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at  TIMESTAMPTZ,
    error_message TEXT,
    meta          JSONB
);
```

---

### 5-7. `backend/tests/test_tenant_deletion.py`（新規）

詳細は §6 テスト計画を参照。

---

### 5-8. `backend/app/tasks/reports.py`（条件修正）

**調査方針**: `reports.py:187` の `export_csv(tenant_id: int, ...)` を呼ぶ Celery タスク投入箇所を grep で特定し、呼び出し前に is_active チェックがあるか確認する。

```bash
# 調査コマンド
grep -rn "export_csv\|delay.*export\|apply_async.*export" backend/app/tasks/ backend/app/routers/ --include="*.py"
```

- 呼び出し元でテナントの `is_active` を確認している → 対応不要
- 呼び出し元で確認していない → 呼び出し元に以下を追加:

```python
# 呼び出し前に is_active 確認
tenant = await db.get(Tenant, tenant_id)
if not tenant or not tenant.is_active:
    return  # 論理削除済みテナントにはエンキューしない
```

---

## 6. テスト計画

### 6-0. SQLite テスト実現のための前提作業（conftest.py と migration-test.yml）

#### 問題

現行 `conftest.py:68-85` の `rewrite_ilike_for_sqlite` リスナーは  
`public.users` / `public.permissions` 等は rewrite するが、  
`public.tenants` と `public.tenant_deletion_audit` は**対象外**。  
SQLite にはスキーマプレフィックスがないため、これらのテーブルに `public.` 付きでアクセスすると  
`no such table: public.tenants` エラーになる。

#### 対策: conftest.py に 3 件追加（プルリクのスコープに含める）

**① rewrite リスナーへの追加**（`conftest.py:68-85` の `rewrite_ilike_for_sqlite` 関数内）:

```python
# 既存ブロックの末尾 " FOR UPDATE" 置換の直前に追加
if "public.tenants" in statement:
    statement = statement.replace("public.tenants", "tenants")
if "public.tenant_deletion_audit" in statement:
    statement = statement.replace("public.tenant_deletion_audit", "tenant_deletion_audit")
```

**② `setup_test_db` セッション fixture へのテーブル作成追加**  
（`conftest.py:91-` の `setup_test_db` の `async with test_engine.begin() as conn:` ブロック末尾）:

```python
# テナント削除テスト用: tenants テーブル（public. は rewrite で除去済み）
await conn.execute(text("""
    CREATE TABLE IF NOT EXISTS tenants (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_code TEXT NOT NULL UNIQUE,
        tenant_name TEXT NOT NULL DEFAULT '',
        company_name TEXT NOT NULL DEFAULT '',
        is_active INTEGER NOT NULL DEFAULT 1
    )
"""))

# テナント削除 中央監査ログ（public. は rewrite で除去済み）
await conn.execute(text("""
    CREATE TABLE IF NOT EXISTS tenant_deletion_audit (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id     INTEGER NOT NULL,
        tenant_code   TEXT NOT NULL,
        tenant_name   TEXT NOT NULL,
        mode          TEXT NOT NULL,
        status        TEXT NOT NULL,
        actor_id      INTEGER,
        actor_email   TEXT NOT NULL,
        executed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at  TIMESTAMP,
        error_message TEXT,
        meta          TEXT
    )
"""))
```

**③ `db_session` fixture の cleanup DELETE への追加**  
既存 conftest は `db_session` fixture の finally 節で明示 DELETE によりテーブルを掃除する方式。  
追加しないとテスト間でデータが残り、テスト順序依存のエラーが発生する。

`db_session` fixture の `yield` 後 cleanup ブロック（`DELETE FROM ...` が並んでいる箇所）に以下を追加:

```python
await db_session.execute(text("DELETE FROM tenant_deletion_audit"))
await db_session.execute(text("DELETE FROM tenants"))
await db_session.commit()
```

> `DELETE FROM tenants` は他テストが利用中のテナント行（id=999 等）も消す可能性があるため、  
> `tenant_deletion_audit` の DELETE より後に実行し、既存テストで INSERT している id=999 の行は  
> `INSERT OR IGNORE` で再挿入しているか確認すること。  
> もし既存テストが `tenants` テーブルを参照するなら `WHERE id > 90` 等のスコープ限定も検討。

#### migration-test.yml への追加

`.github/workflows/migration-test.yml` のセットアップ SQL ブロックにも同様の最小 CREATE TABLE を追加する  
（`backend/CLAUDE.md` の migration-test 拡充ルール）。  
migration-test.yml は migration が操作するテーブルをセットアップするための CI 設定ファイル。既存の `public.tenants` や `public.users` のセットアップ箇所を参考に追記すること。

---

### 6-1. SQLite テスト（CI で常時実行）

#### fixture 設計

現行の `client` fixture（`conftest.py:1282`）は `_mock_user()` を返す。  
`_mock_user()` には `is_super_admin` が設定されていない → `require_super_admin` が `getattr(current_user, "is_super_admin", False)` で `False` を返し 403 になる。

**テストファイル内にローカル fixture を定義する方針**:

```python
# backend/tests/test_tenant_deletion.py
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from unittest.mock import patch


def _make_super_admin_user():
    """is_super_admin=True のテスト用ユーザー"""
    from app.models import User
    user = User()
    user.id = 888
    user.tenant_id = None  # super_admin は tenant に紐付かない
    user.username = "superadmin"
    user.email = "superadmin@example.com"
    user.role = "super_admin"
    user.is_active = True
    user.is_super_admin = True
    return user


def _make_normal_user():
    """is_super_admin=False（デフォルト）のテスト用ユーザー"""
    from app.models import User
    user = User()
    user.id = 999
    user.tenant_id = 999
    user.username = "normaluser"
    user.email = "normal@example.com"
    user.role = "admin"
    user.is_active = True
    # is_super_admin は設定しない → getattr で False
    return user


@pytest_asyncio.fixture
async def super_admin_client(db_session):
    """
    is_super_admin=True のユーザーで認証された HTTP クライアント。
    require_super_admin を通過させるために get_current_user を override する。
    """
    from app.main import app
    from app.auth.dependencies import get_current_user, get_current_tenant
    from app.database import get_db

    super_admin = _make_super_admin_user()

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return super_admin

    async def override_get_current_tenant():
        return None  # super_admin EP は get_current_tenant を使わない

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def normal_client(db_session):
    """
    is_super_admin が設定されていないユーザーで認証された HTTP クライアント。
    require_super_admin に 403 を返させるために使用。
    """
    from app.main import app
    from app.auth.dependencies import get_current_user, get_current_tenant
    from app.database import get_db

    normal_user = _make_normal_user()

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return normal_user

    async def override_get_current_tenant():
        return 999

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
```

#### テストケース

```python
# ── 権限ガード: normal_client は 403 ─────────────────────────────────────

@pytest.mark.asyncio
async def test_logical_delete_requires_super_admin(normal_client: AsyncClient):
    """非 super_admin は 403"""
    resp = await normal_client.delete(
        "/api/v1/super-admin/tenants/1",
        json={"confirm": "DELETE:test-corp"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_physical_delete_requires_super_admin(normal_client: AsyncClient):
    """非 super_admin は 403"""
    resp = await normal_client.delete(
        "/api/v1/super-admin/tenants/1/physical",
        json={"confirm": "DELETE:test-corp"},
    )
    assert resp.status_code == 403


# ── confirm バリデーション ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logical_delete_wrong_confirm(super_admin_client: AsyncClient, db_session):
    """confirm 文字列不一致で 400"""
    # SQLite: public. は conftest rewrite で除去済み → tenants テーブル
    await db_session.execute(
        text("INSERT OR IGNORE INTO tenants (id, tenant_name, tenant_code, is_active) VALUES (97, 'Test', 'test-97', 1)")
    )
    await db_session.commit()

    resp = await super_admin_client.delete(
        "/api/v1/super-admin/tenants/97",
        json={"confirm": "WRONG"},
    )
    assert resp.status_code == 400


# ── 論理削除成功 ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logical_delete_success(super_admin_client: AsyncClient, db_session):
    """is_active=False になること・監査ログが記録されること"""
    # SQLite: public. rewrite により tenants / tenant_deletion_audit テーブルへアクセス
    await db_session.execute(
        text("INSERT OR IGNORE INTO tenants (id, tenant_name, tenant_code, is_active) VALUES (99, 'Test', 'test-99', 1)")
    )
    await db_session.commit()

    resp = await super_admin_client.delete(
        "/api/v1/super-admin/tenants/99",
        json={"confirm": "DELETE:test-99"},
    )
    assert resp.status_code == 200
    assert resp.json()["mode"] == "logical"

    # is_active が 0（False）になっていること
    row = (await db_session.execute(
        text("SELECT is_active FROM tenants WHERE id = 99")
    )).one()
    assert not row.is_active

    # 監査ログ記録
    audit = (await db_session.execute(
        text("SELECT mode, status FROM tenant_deletion_audit WHERE tenant_id = 99")
    )).one()
    assert audit.mode == "logical"
    assert audit.status == "succeeded"


@pytest.mark.asyncio
async def test_logical_delete_already_deleted(super_admin_client: AsyncClient, db_session):
    """すでに論理削除済みテナントは 400"""
    await db_session.execute(
        text("INSERT OR IGNORE INTO tenants (id, tenant_name, tenant_code, is_active) VALUES (98, 'Test', 'test-98', 0)")
    )
    await db_session.commit()

    resp = await super_admin_client.delete(
        "/api/v1/super-admin/tenants/98",
        json={"confirm": "DELETE:test-98"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_physical_delete_requires_logical_first(super_admin_client: AsyncClient, db_session):
    """is_active=True のテナントへの物理削除は 400"""
    await db_session.execute(
        text("INSERT OR IGNORE INTO tenants (id, tenant_name, tenant_code, is_active) VALUES (96, 'Test', 'test-96', 1)")
    )
    await db_session.commit()

    resp = await super_admin_client.delete(
        "/api/v1/super-admin/tenants/96/physical",
        json={"confirm": "DELETE:test-96"},
    )
    assert resp.status_code == 400
```

### 6-2. PostgreSQL 実機テスト（`RLS_TEST_DATABASE_URL` 必須）

`test_tenant_schema_integrity.py:52-54` の skip ガードパターンを踏襲:

```python
import os
import pytest

_RLS_DB_URL = os.getenv("RLS_TEST_DATABASE_URL")
_SKIP_NO_PG = pytest.mark.skipif(not _RLS_DB_URL, reason="RLS_TEST_DATABASE_URL が未設定")

_ADMIN_URL = os.getenv(
    "RLS_ADMIN_DATABASE_URL",
    "postgresql+asyncpg://jarvis:testpass@localhost:5432/jarvis_test_db",
)
```

| テストケース | 確認内容 |
|------------|---------|
| `test_cross_schema_fk_exists` | `tenant_NNN.role_permissions.permission_id → public.permissions(id)` FK が pg_constraint に存在する（recon C-8 実機証拠） |
| `test_ddl_persistence_after_commit` | `DROP SCHEMA` + `admin_db.commit()` 後に `pg_namespace` でスキーマ不在を確認（recon C-9 要確認事項の実証） |
| `test_drop_cascade_fk_removed` | DROP 後に該当 FK が pg_constraint から消えることを確認 |
| `test_public_tables_unaffected` | DROP 後に `public.permissions` / `public.users` が存在することを確認 |
| `test_physical_delete_schema_gone` | 物理削除 EP 呼び出し後 `pg_namespace` → 0行 |
| `test_physical_delete_public_tenant_gone` | `public.tenants WHERE id = N` → 0行 |
| `test_audit_log_survives_drop` | DROP 後も `public.tenant_deletion_audit` に行が残る |
| `test_logical_delete_blocks_api` | `is_active=False` 後に通常 EP → 403 |

---

## 7. テストコマンド

```bash
# SQLite テスト（CI 相当）
cd backend
pytest tests/test_tenant_deletion.py -v

# PostgreSQL 実機テスト（ローカル or CI の PG 環境）
RLS_TEST_DATABASE_URL="postgresql+asyncpg://jarvis_app:apppass@localhost:5432/jarvis_test_db" \
RLS_ADMIN_DATABASE_URL="postgresql+asyncpg://jarvis:testpass@localhost:5432/jarvis_test_db" \
  pytest tests/test_tenant_deletion.py -v -k "pg"

# lint チェック
make lint

# 全チェック（lint + pytest）
make check
```

---

## 8. 受け入れ基準

| # | 基準 | 判定方法 |
|---|-----|---------|
| AC-1 | 非 super_admin → 403 | SQLite テスト PASS |
| AC-2 | confirm 不一致 → 400 | SQLite テスト PASS |
| AC-3 | 論理削除後 is_active=False 確認 | SQLite テスト PASS |
| AC-4 | 論理削除後 audit 行（succeeded）確認 | SQLite テスト PASS |
| AC-5 | 物理削除は論理削除後のみ（is_active=True で 400） | SQLite テスト PASS |
| AC-6 | DROP 後スキーマ不在 | PostgreSQL 実機テスト PASS |
| AC-7 | public.tenants / public.users 整合 | PostgreSQL 実機テスト PASS |
| AC-8 | audit 行が DROP 後も残存 | PostgreSQL 実機テスト PASS |
| AC-9 | migration が全テナントに適用可能 | `scripts/run_all_migrations.sh` で適用確認 |
| AC-10 | `make lint` PASS | lint チェック |

---

## 9. 想定リスクと対策

| リスク | 対策 |
|--------|------|
| DROP 後に public.tenants DELETE が失敗 → スキーマ消えたのに registry が残る | audit status=started → except で failed に更新。スキーマは消えているが `is_active=false` のままなので API は遮断済み。手動で `DELETE FROM public.tenants WHERE id=N` で復旧可能 |
| admin_db の commit() が DDL を永続化しないケース（asyncpg のバージョン依存） | PostgreSQL 実機テスト `test_ddl_persistence_after_commit` で実証。FAIL なら isolation_level="AUTOCOMMIT" 接続に切り替える（design.md §4 案 B に切替） |
| schema_name インジェクション | `tenant_id` は `int` 型で受け取り、`f"tenant_{tenant_id:03d}"` で生成。追加で `isalnum()` チェック |
| reports.py が論理削除後テナントに CSV エクスポートを実行 | 呼び出し元 grep 調査で確認。必要なら is_active ガードを追加（§5-7） |
| migration の deploy.yml 登録漏れ → 本番 500 | `scripts/run_all_migrations.sh` への追記で対応（`deploy.yml` は `run_all_migrations.sh` を呼ぶだけ・PR #1277 の前例）。`migration-guard.yml` が CI でブロック |
| `migration-test.yml` に `public.tenant_deletion_audit` がない | migration-test.yml のセットアップ SQL に最小 CREATE TABLE を追加（`backend/CLAUDE.md` migration-test 拡充ルール） |

---

## 10. ブランチ・PO GO ルール（ADR-135 準拠）

```
feature/morimoto/tenant-deletion-impl   ← 実装ブランチ
  ↓ PR 作成後、Evaluator PASS + Reviewer APPROVE
  ↓ PO GO（「GO: Shingo YYYY-MM-DD」コメント）確認後のみ
develop → main
```

**develop にマージ = 本番投入可の宣言**（ADR-135）。  
migration / deploy.yml / 本番 scripts を含む本 PR は PO GO が出るまで feature ブランチで待機する。

---

## 11. Claude Code への実装指示

以下の順序で実装すること。各ステップ完了後に `make lint` を通過させてから次に進む。

### Step 1: migration ファイル作成 + CI 設定

1. 現在時刻で migration ファイル名を確定: `date +%Y%m%d_%H%M%S`
2. `migrations/<TIMESTAMP>_add_tenant_deletion_audit.sql` を作成（§5-3 の SQL をそのまま使用）
3. `scripts/run_all_migrations.sh` の末尾 `echo "✅ 全マイグレーション完了"` ブロック直前に `run_sql migrations/<TIMESTAMP>_add_tenant_deletion_audit.sql` を追記
4. `.github/workflows/migration-test.yml` のセットアップ SQL に `public.tenant_deletion_audit` の最小 CREATE TABLE を追加（§5-6）

### Step 2: conftest.py 更新

**SQLite テストを通すために必須。**

1. `backend/tests/conftest.py:68-85` の `rewrite_ilike_for_sqlite` 関数内に追記（§6-0 ①）:
   ```python
   if "public.tenants" in statement:
       statement = statement.replace("public.tenants", "tenants")
   if "public.tenant_deletion_audit" in statement:
       statement = statement.replace("public.tenant_deletion_audit", "tenant_deletion_audit")
   ```
2. `backend/tests/conftest.py` の `setup_test_db` セッション fixture（`async with test_engine.begin() as conn:` ブロック末尾）に `tenants` と `tenant_deletion_audit` の CREATE TABLE を追加（§6-0 ②）
3. `backend/tests/conftest.py` の `db_session` fixture の cleanup DELETE ブロックに追加（§6-0 ③）:
   ```python
   await db_session.execute(text("DELETE FROM tenant_deletion_audit"))
   await db_session.execute(text("DELETE FROM tenants"))
   await db_session.commit()
   ```

### Step 3: super_admin_tenants.py 作成

1. `backend/app/routers/super_admin_tenants.py` を §5-1 の内容で作成
2. `backend/app/main.py` に import と include_router を追加（§5-2）
3. `make lint` PASS を確認

### Step 4: backup スクリプト作成

1. `scripts/backup_tenant_before_drop.sh` を §5-5 の内容で作成
2. `chmod +x scripts/backup_tenant_before_drop.sh`

### Step 5: reports.py 調査・修正

1. 以下を実行して呼び出し元を特定:
   ```bash
   grep -rn "export_csv\|delay.*export\|apply_async.*export" backend/app/tasks/ backend/app/routers/ --include="*.py"
   ```
2. 呼び出し元で is_active チェックがなければ追加（§5-8）

### Step 6: テスト作成

1. `backend/tests/test_tenant_deletion.py` を §6-1 の内容で作成（`super_admin_client` / `normal_client` fixture 含む）
2. SQLite テストを実行して全 PASS を確認:
   ```bash
   cd backend && pytest tests/test_tenant_deletion.py -v
   ```
3. PostgreSQL 実機テスト（§6-2）を追加
4. `make check` PASS を確認

### Step 7: コミット & PR 作成

```bash
# worktree 準備（CLAUDE.md 必須手順）
bash scripts/new-worktree.sh feature/morimoto/tenant-deletion-impl --claude

# 実装後（.github/workflows/migration-test.yml と backend/tests/conftest.py を忘れずに追加）
git add backend/app/routers/super_admin_tenants.py \
        backend/app/main.py \
        migrations/<TIMESTAMP>_add_tenant_deletion_audit.sql \
        scripts/run_all_migrations.sh \
        scripts/backup_tenant_before_drop.sh \
        backend/tests/test_tenant_deletion.py \
        backend/tests/conftest.py \
        .github/workflows/migration-test.yml
# reports.py を修正した場合は追加
git commit -m "feat: テナント論理削除・物理削除 API 実装（super_admin_tenants.py）"

# PR 作成
gh pr create \
  --title "feat: テナント論理削除・物理削除 API（super_admin_tenants.py）" \
  --body "..."
```

**PR body 必須セクション**（`process-artifacts gate` の check 対象）:

```markdown
### 標準ワークフロー確認
- [x] recon.md: docs/handoff/tenant-deletion/recon.md（feature/morimoto/tenant-deletion-recon ブランチ）
- [x] design.md: docs/handoff/tenant-deletion/design.md（同ブランチ）
- [x] ADR 検索済み（recon §ADR検索結果 参照）
```
