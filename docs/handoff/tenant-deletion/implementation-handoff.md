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
    # テナント取得
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

    async with db.begin():
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
# 使用例: TENANT_ID=4 DATABASE_URL=... bash scripts/backup_tenant_before_drop.sh
set -euo pipefail

TENANT_ID="${TENANT_ID:?TENANT_ID 環境変数が必要です}"
DATABASE_URL="${DATABASE_URL:?DATABASE_URL 環境変数が必要です}"

SCHEMA_NAME="tenant_$(printf '%03d' "${TENANT_ID}")"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_FILE="/tmp/${SCHEMA_NAME}_pre_drop_${TIMESTAMP}.sql"

echo "バックアップ開始: schema=${SCHEMA_NAME}, 出力=${OUTPUT_FILE}"
pg_dump -n "${SCHEMA_NAME}" "${DATABASE_URL}" > "${OUTPUT_FILE}"
echo "✅ バックアップ完了: ${OUTPUT_FILE}"
echo "保存場所: /tmp/ はコンテナ再起動で消えます。ホスト側に退避してください。"
```

---

### 5-6. `backend/tests/test_tenant_deletion.py`（新規）

詳細は §6 テスト計画を参照。

---

### 5-7. `backend/app/tasks/reports.py`（条件修正）

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

### 6-1. SQLite テスト（CI で常時実行）

```python
# backend/tests/test_tenant_deletion.py

import pytest
from httpx import AsyncClient

# ── 権限ガード ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logical_delete_requires_super_admin(client: AsyncClient):
    """非 super_admin は 403"""
    resp = await client.delete(
        "/api/v1/super-admin/tenants/1",
        json={"confirm": "DELETE:test-corp"},
        headers={"Authorization": "Bearer <normal_user_token>"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_physical_delete_requires_super_admin(client: AsyncClient):
    """非 super_admin は 403"""
    resp = await client.delete(
        "/api/v1/super-admin/tenants/1/physical",
        json={"confirm": "DELETE:test-corp"},
        headers={"Authorization": "Bearer <normal_user_token>"},
    )
    assert resp.status_code == 403


# ── confirm バリデーション ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logical_delete_wrong_confirm(client: AsyncClient, super_admin_token: str):
    """confirm 文字列不一致で 400"""
    resp = await client.delete(
        "/api/v1/super-admin/tenants/1",
        json={"confirm": "WRONG"},
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert resp.status_code == 400


# ── 論理削除成功（SQLite でも DB 操作範囲は public.tenants のみ）───────────

@pytest.mark.asyncio
async def test_logical_delete_success(client: AsyncClient, super_admin_token: str, db_session):
    """is_active=False になること・監査ログが記録されること"""
    # テスト用テナント挿入
    await db_session.execute(
        text("INSERT INTO public.tenants (id, tenant_name, tenant_code, is_active) VALUES (99, 'Test', 'test-99', TRUE)")
    )
    await db_session.commit()

    resp = await client.delete(
        "/api/v1/super-admin/tenants/99",
        json={"confirm": "DELETE:test-99"},
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["mode"] == "logical"

    # is_active が False になっていること
    row = (await db_session.execute(
        text("SELECT is_active FROM public.tenants WHERE id = 99")
    )).one()
    assert row.is_active is False

    # 監査ログ記録
    audit = (await db_session.execute(
        text("SELECT mode, status FROM public.tenant_deletion_audit WHERE tenant_id = 99")
    )).one()
    assert audit.mode == "logical"
    assert audit.status == "succeeded"


@pytest.mark.asyncio
async def test_logical_delete_already_deleted(client: AsyncClient, super_admin_token: str, db_session):
    """すでに論理削除済みテナントは 400"""
    await db_session.execute(
        text("INSERT INTO public.tenants (id, tenant_name, tenant_code, is_active) VALUES (98, 'Test', 'test-98', FALSE)")
    )
    await db_session.commit()

    resp = await client.delete(
        "/api/v1/super-admin/tenants/98",
        json={"confirm": "DELETE:test-98"},
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert resp.status_code == 400
```

### 6-2. PostgreSQL 実機テスト（`RLS_TEST_DATABASE_URL` 必須）

`test_tenant_schema_integrity.py` の skip ガードパターン（line 52-54）を踏襲:

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

### Step 1: migration ファイル作成

1. 現在時刻で migration ファイル名を確定: `date +%Y%m%d_%H%M%S`
2. `migrations/<TIMESTAMP>_add_tenant_deletion_audit.sql` を作成（§5-3 の SQL をそのまま使用）
3. `scripts/run_all_migrations.sh` の末尾 `echo "✅ 全マイグレーション完了"` ブロック直前に `run_sql migrations/<TIMESTAMP>_add_tenant_deletion_audit.sql` を追記
4. `.github/workflows/migration-test.yml` のセットアップ SQL に `public.tenant_deletion_audit` の最小 CREATE TABLE を追加

### Step 2: super_admin_tenants.py 作成

1. `backend/app/routers/super_admin_tenants.py` を§5-1 の内容で作成
2. `backend/app/main.py` に import と include_router を追加（§5-2）
3. `make lint` PASS を確認

### Step 3: backup スクリプト作成

1. `scripts/backup_tenant_before_drop.sh` を§5-5 の内容で作成
2. `chmod +x scripts/backup_tenant_before_drop.sh`

### Step 4: reports.py 調査・修正

1. 以下を実行して呼び出し元を特定:
   ```bash
   grep -rn "export_csv\|delay.*export\|apply_async.*export" backend/app/tasks/ backend/app/routers/ --include="*.py"
   ```
2. 呼び出し元で is_active チェックがなければ追加（§5-7）

### Step 5: テスト作成

1. `backend/tests/test_tenant_deletion.py` を§6-1 の内容で作成
2. SQLite テストを実行して全 PASS を確認:
   ```bash
   cd backend && pytest tests/test_tenant_deletion.py -v
   ```
3. PostgreSQL 実機テスト（§6-2）を追加
4. `make check` PASS を確認

### Step 6: コミット & PR 作成

```bash
# worktree 準備（CLAUDE.md 必須手順）
bash scripts/new-worktree.sh feature/morimoto/tenant-deletion-impl --claude

# 実装後
git add backend/app/routers/super_admin_tenants.py \
        backend/app/main.py \
        migrations/<TIMESTAMP>_add_tenant_deletion_audit.sql \
        scripts/run_all_migrations.sh \
        scripts/backup_tenant_before_drop.sh \
        backend/tests/test_tenant_deletion.py
# reports.py を修正した場合は追加
git commit -m "feat: テナント論理削除・物理削除 API 実装（super_admin_tenants.py）"

# PR 作成（develop ではなく main 向け、またはブランチポリシーに従う）
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
