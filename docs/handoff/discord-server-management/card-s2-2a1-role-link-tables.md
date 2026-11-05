# 実装カード: 第2段 2a-1 役割とロールをつなぐ列・消した番号を覚える表 2 つを作る（作るだけ・行は入れない・プログラムの動きは変えない）

- 設計: docs/handoff/discord-server-management/design.md S2-3 D2-1・D2-3・S2-5（Fable 審査 4 回目 APPROVE）
- PO 承認: 第2段 KGI 8〜16 と設計を承認（2026-11-06「1、推測は禁止して事実確認を怠らずに…確立したなら進める。」）。2a は移行を含むので、実装の開始前に PO の確認を取る（S2-11）。このカードは PO の確認のあとに渡す
- 分け方: 設計 S2-5 の 2a を 2 つに分けた（1 回に 1 つの変更）。2a-1＝表と列を作るだけ（このカード）。2a-2＝確認画面・反映・役割の削除のプログラム（別のカード。2a-1 のマージと本番反映のあとに作る）
- ブランチ: release/discord-own-server-s2-2a1（origin/main に第2段の設計の文書を足したもの。実際の先頭は Opus が依頼文で伝える）
- 触ってよいファイル（この 5 つと報告書 docs/handoff/discord-server-management/impl-report-s2-2a1.md だけ）:
  - migrations/20261106_150000_add_discord_role_link_tables.sql（新規）
  - scripts/run_all_migrations.sh（末尾に 2 行足すだけ）
  - backend/app/services/tenant.py（`_TENANT_TABLES_SQL` に §3 の 3 か所を足すだけ）
  - backend/tests/test_roles_system_key_ddl.py（31 行目の数を 2 → 3 にするだけ）
  - backend/tests/test_discord_role_link_ddl.py（新規）
  - 改訂1（§5-改訂1）だけで触ってよい: backend/tests/rls_bootstrap.py（`_TENANT_LOOP_MIGRATIONS` に 1 行足すだけ）、origin/main を取り込む merge commit
- 触らない: backend のほかのファイル（routers・services の他・conftest.py を含む）・frontend・i18n・openapi.json・ほかの migrations・scripts/setup_tenant.py・scripts/db/sync_tenant_schema.py・.github・deploy.yml・本番

## 読んだ節（guards/）

- docs/handoff/design-partner-card-ops/guards/00-common.md：報告は生出力・推測で埋めない → 報告書に生出力を貼る形にした
- docs/handoff/design-partner-card-ops/guards/03-file.md：触るファイルを列挙 → 上の 5 つと報告書だけ
- docs/handoff/design-partner-card-ops/guards/05-pr.md：PR は Opus が作る → 実行役は push まで
- docs/handoff/design-partner-card-ops/guards/07-migration.md：置くだけでは MIGRATION GUARD が落ちる → run_all_migrations.sh の末尾に登録する。採番は直近を実測（origin/main の最後は 20261106_120000）。migrations は CODEOWNERS 承認と GO の両方が要る（マージは Opus と PO 側）
  - deploy.yml は触らない。理由（origin/main で実測）: `.github/workflows/migration-guard.yml:132-133` は「deploy.yml の `< migrations/<名前>` か、run_all_migrations.sh の `migrations/<名前>` のどちらか」で合格にする。`.github/workflows/deploy.yml:228` は「新しい移行は deploy.yml ではなく run_all_migrations.sh に足す」と書く。`backend/AGENTS.md:34` の「deploy.yml 登録必須」は古い書き方で、今回は従わない。migration-guard.yml の 1 番目の点検（models.py に Column を足したら deploy.yml に migrate_ が要る）は models.py を触らないので動かない。CI が deploy.yml への登録を求めて落ちたら、deploy.yml を変えずに停止して NEEDS_DECISION: と生出力
- docs/handoff/design-partner-card-ops/guards/10-executor.md：作業前に preflight → 下の §0

## 受領確認

作業を始める前に、報告書の先頭に次の 3 行を書く:
- 受領確認: card-s2-2a1-role-link-tables.md を読んだ
- origin/release/discord-own-server-s2-2a1 の先頭 sha（git rev-parse の生出力）
- 触るファイルは 5 つと報告書だけ、と理解した

## §0 準備

- リポジトリの根で `./scripts/dev/executor-preflight.sh` を流し、生出力を報告書に貼る
  - クラウドで動かすとき: [1/3] network と [2/3] gh auth の FAIL は起こるものとして、生出力を貼るだけで先へ進む。[3/3] git config user.name と [4/4] origin/main が OK でなければ停止して BLOCKED（第1段 card-bin1a §0 と同じ扱い）
- `git fetch origin` のあと `release/discord-own-server-s2-2a1` を取り出す（新しく作らない）
- `ls migrations/ | sort | tail -3` の生出力を貼る。最後が `20261106_120000_create_discord_server_snapshot_tables.sql` でなければ、§1 の番号がそれより後かを確かめる（後でなければ停止）

## §1 migrations/20261106_150000_add_discord_role_link_tables.sql（新規）

中身はこのとおり（1 文字も変えない）:

```sql
-- discord-server-management 第2段 2a-1: アプリの役割と Discord のロールをつなぐ列と、消した番号を覚える表 2 つを作る（作るだけ・冪等）
--
-- 設計: docs/handoff/discord-server-management/design.md S2-3 D2-1・D2-3・S2-5
-- 中身（各テナントのスキーマ）:
--   roles.discord_role_id     アプリの役割につながる Discord のロールの番号（NULL 可。NULL でない値はテナント内で一意）
--   discord_retired_roles     消したアプリの役割の Discord のロールの番号（点検がこの番号のロールを登録した人から外すため）
--   discord_retired_members   消した・番号を変えたスタッフの元の Discord の番号（kick=true は自社サーバーから外す）
-- ADR-155: 構造変更のみ。値は入れない。行を入れる処理は 2a-2・2b で足す。
-- GRANT は ALTER DEFAULT PRIVILEGES（20260605_040000）で自動付与される。
-- 新しい会社のスキーマは backend/app/services/tenant.py の _TENANT_TABLES_SQL で同じ形に作る。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック（この順・各テナント）:
--   DROP TABLE IF EXISTS <tenant>.discord_retired_members;
--   DROP TABLE IF EXISTS <tenant>.discord_retired_roles;
--   DROP INDEX IF EXISTS <tenant>.uq_roles_discord_role_id;
--   ALTER TABLE <tenant>.roles DROP COLUMN IF EXISTS discord_role_id;

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_[0-9]+$'
        ORDER BY nspname
    LOOP
        -- roles テーブルが存在するスキーマのみ対象（20261005_150000 と同じ）
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = r.nspname AND tablename = 'roles'
        ) THEN
            CONTINUE;
        END IF;

        EXECUTE format(
            'ALTER TABLE %I.roles ADD COLUMN IF NOT EXISTS discord_role_id TEXT',
            r.nspname
        );
        EXECUTE format(
            'CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_discord_role_id ON %I.roles (discord_role_id) WHERE discord_role_id IS NOT NULL',
            r.nspname
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.discord_retired_roles (
                discord_role_id TEXT PRIMARY KEY,
                retired_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            )',
            r.nspname
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.discord_retired_members (
                discord_user_id TEXT PRIMARY KEY,
                kick            BOOLEAN NOT NULL,
                retired_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            )',
            r.nspname
        );
        EXECUTE format('COMMENT ON COLUMN %I.roles.discord_role_id IS %L', r.nspname,
            'つながる Discord のロールの番号（自社サーバー。NULL はまだつないでいない）');
        EXECUTE format('COMMENT ON TABLE %I.discord_retired_roles IS %L', r.nspname,
            '消したアプリの役割の Discord のロールの番号。点検が登録した人から外す');
        EXECUTE format('COMMENT ON TABLE %I.discord_retired_members IS %L', r.nspname,
            '消した・番号を変えたスタッフの元の Discord の番号。点検がロールを外し、kick=true なら自社サーバーから外す');
        EXECUTE format('COMMENT ON COLUMN %I.discord_retired_members.kick IS %L', r.nspname,
            'true = スタッフを消した（自社サーバーから外す）。false = 番号を変えた（ロールだけ外す）');
        EXECUTE format('COMMENT ON COLUMN %I.discord_retired_roles.discord_role_id IS %L', r.nspname,
            '消したアプリの役割につながっていた Discord のロールの番号');
        EXECUTE format('COMMENT ON COLUMN %I.discord_retired_roles.retired_at IS %L', r.nspname,
            'この番号を覚えた日時');
        EXECUTE format('COMMENT ON COLUMN %I.discord_retired_members.discord_user_id IS %L', r.nspname,
            '消した・番号を変えたスタッフの元の Discord の番号');
        EXECUTE format('COMMENT ON COLUMN %I.discord_retired_members.retired_at IS %L', r.nspname,
            'この番号を覚えた日時');
        RAISE NOTICE 'discord role link tables created/verified for schema: %', r.nspname;
    END LOOP;
END $$;
```

## §2 scripts/run_all_migrations.sh

ファイルの最後の `run_sql` の行は今これ（origin/main 1b2fdada6 で実測）:

```
run_sql migrations/20261106_120000_create_discord_server_snapshot_tables.sql
```

この行のすぐ次に 2 行足す（ほかは 1 文字も変えない）:

```
# discord-server-management 第2段 2a-1: roles に Discord のロールの番号の列、消した番号を覚える表 2 つを作る（作るだけ・冪等）
run_sql migrations/20261106_150000_add_discord_role_link_tables.sql
```

最後の run_sql がこの行でなかったら（ほかの PR が先に足していたら）、その最後の run_sql の次に足し、報告書にその行を書く。

## §3 backend/app/services/tenant.py（`_TENANT_TABLES_SQL` に 3 か所足すだけ）

新しい会社を作ったときにも同じ表ができるようにする（既存の会社は §1 の移行で作る）。行番号は origin/main 1b2fdada6 の実測。

(1) roles の列（505 行目 `    system_key TEXT,` のすぐ次に 1 行）:

変更前:
```
    system_key TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
```
変更後:
```
    system_key TEXT,
    discord_role_id TEXT,                   -- つながる Discord のロールの番号（discord-server-management 第2段）
    created_at TIMESTAMPTZ DEFAULT NOW(),
```

(2) 部分一意索引（510 行目 `CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_system_key ...` のすぐ次に 1 行）:

```
CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_discord_role_id ON {schema}.roles (discord_role_id) WHERE discord_role_id IS NOT NULL;
```

(3) 表 2 つ（1083 行目、notice_fallback_recipients の定義を閉じる `);` のすぐ次。1085 行目 `-- SA-02 / F3: チャネル統制マスタ` の前）:

変更前:
```
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- SA-02 / F3: チャネル統制マスタ（新規テナント初期シード対象）
```
変更後:
```
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- discord-server-management 第2段: 消したアプリの役割の Discord のロールの番号（点検が登録した人から外す）
CREATE TABLE IF NOT EXISTS {schema}.discord_retired_roles (
    discord_role_id TEXT PRIMARY KEY,
    retired_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- discord-server-management 第2段: 消した・番号を変えたスタッフの元の Discord の番号（kick=true は自社サーバーから外す）
CREATE TABLE IF NOT EXISTS {schema}.discord_retired_members (
    discord_user_id TEXT PRIMARY KEY,
    kick            BOOLEAN NOT NULL,
    retired_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- SA-02 / F3: チャネル統制マスタ（新規テナント初期シード対象）
```

- `_TENANT_TABLES_SQL` は `.format()` を通るので、`{` `}` を足さない（上の文には `{schema}` 以外の波かっこは無い）
- RLS（`_RLS_ENABLE_SQL`・`_RLS_POLICY_SQL`）には足さない。表に tenant_id 列が無く、スキーマで分かれている（先例: user_notices・notice_fallback_recipients も同じ）

## §4 backend/tests/test_roles_system_key_ddl.py（1 か所だけ）

(2) で `{schema}.roles (` が 1 つ増えるので、31 行目の数を直す。ほかは変えない（32〜37 行目は system_key の索引が先にある並びのまま通る）。

変更前:
```
    assert sql.count(marker) == 2  # roles の定義と、部分一意索引の ON {schema}.roles (system_key)
```
変更後:
```
    assert sql.count(marker) == 3  # roles の定義と、部分一意索引 2 つ（ON {schema}.roles (system_key) と (discord_role_id)）
```

## §5 backend/tests/test_discord_role_link_ddl.py（新規）

中身はこのとおり（先例 backend/tests/test_roles_system_key_ddl.py と同じ形。テナント番号 995 は origin/main の試験で未使用＝`git grep` で 909・925・954・991・992・993・996・997・998・999 だけが使われていることを確認済み）:

```python
"""discord-server-management 第2段 2a-1: roles.discord_role_id と、消した番号を覚える表 2 つの構造の試験。

- 単体（PostgreSQL 不要）: 新テナント用 DDL に列・部分一意索引・表 2 つが含まれ、移行ファイルが登録され、値を入れない。
- PG（CI で実行）: 新テナントを作ると列・索引・表があり、移行ファイルを 2 回流しても変わらない。
  ゲートは CI が実際に設定する RLS_ADMIN_DATABASE_URL（test_roles_system_key_ddl.py と同じ形）。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.services import tenant as tenant_service
from tests.rls_bootstrap import bootstrap_tenant_schema, tenant_schema_lock

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = "20261106_150000_add_discord_role_link_tables.sql"
_TENANT_ID = 995
_SCHEMA = f"tenant_{_TENANT_ID:03d}"


def _block(sql: str, marker: str) -> str:
    """marker の直後から、最初の ');' までを返す（表の列定義）。"""
    assert sql.count(marker) == 1, marker
    body = sql.split(marker)[1]
    return body[: body.index(");")]


def test_tenant_ddl_has_discord_role_id_and_retired_tables():
    sql = tenant_service._TENANT_TABLES_SQL
    roles_block = sql.split("{schema}.roles (")[1]
    roles_block = roles_block[: roles_block.index(");")]
    assert "discord_role_id TEXT," in roles_block
    assert (
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_discord_role_id ON {schema}.roles (discord_role_id)"
        " WHERE discord_role_id IS NOT NULL;"
    ) in sql

    retired_roles = _block(sql, "{schema}.discord_retired_roles (")
    assert "discord_role_id TEXT PRIMARY KEY" in retired_roles
    assert "retired_at      TIMESTAMPTZ NOT NULL DEFAULT now()" in retired_roles

    retired_members = _block(sql, "{schema}.discord_retired_members (")
    assert "discord_user_id TEXT PRIMARY KEY" in retired_members
    assert "kick            BOOLEAN NOT NULL" in retired_members
    assert "retired_at      TIMESTAMPTZ NOT NULL DEFAULT now()" in retired_members


def test_migration_file_exists_and_is_registered():
    migration = _REPO_ROOT / "migrations" / _MIGRATION
    assert migration.is_file()
    body = migration.read_text(encoding="utf-8")
    assert "ADD COLUMN IF NOT EXISTS discord_role_id TEXT" in body
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_discord_role_id" in body
    assert "CREATE TABLE IF NOT EXISTS %I.discord_retired_roles" in body
    assert "CREATE TABLE IF NOT EXISTS %I.discord_retired_members" in body
    runner = (_REPO_ROOT / "scripts" / "run_all_migrations.sh").read_text(encoding="utf-8")
    lines = [line for line in runner.splitlines() if line.startswith("run_sql ")]
    assert lines.count(f"run_sql migrations/{_MIGRATION}") == 1


def test_migration_writes_no_values():
    """ADR-155: 構造変更のみ（INSERT / UPDATE / DELETE を含まない）。"""
    body = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
    code = "\n".join(
        line for line in body.splitlines() if not line.strip().startswith("--")
    ).upper()
    for word in ("INSERT ", "UPDATE ", "DELETE "):
        assert word not in code


async def _shape(conn) -> dict:
    columns = await conn.execute(
        text(
            "SELECT table_name, column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_schema = :s AND ("
            " (table_name = 'roles' AND column_name = 'discord_role_id')"
            " OR table_name IN ('discord_retired_roles', 'discord_retired_members'))"
            " ORDER BY table_name, column_name"
        ),
        {"s": _SCHEMA},
    )
    index = await conn.execute(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE schemaname = :s AND indexname = 'uq_roles_discord_role_id'"
        ),
        {"s": _SCHEMA},
    )
    return {"columns": [tuple(row) for row in columns.all()], "index": index.scalar_one()}


@pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_new_tenant_has_link_tables_and_migration_is_idempotent():
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    try:
        async with tenant_schema_lock(admin_engine, _TENANT_ID):
            schema_name = await bootstrap_tenant_schema(admin_engine, _TENANT_ID)
            assert schema_name == _SCHEMA
            async with admin_engine.connect() as conn:
                before = await _shape(conn)  # 新しい会社の作り方（tenant.py）で作った形
            migration_sql = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
            async with admin_engine.begin() as conn:
                await conn.exec_driver_sql(migration_sql)  # 1 回目
                await conn.exec_driver_sql(migration_sql)  # 2 回目（冪等）
            async with admin_engine.connect() as conn:
                after = await _shape(conn)
            assert before == after
            assert after["columns"] == [
                ("discord_retired_members", "discord_user_id", "text", "NO"),
                ("discord_retired_members", "kick", "boolean", "NO"),
                ("discord_retired_members", "retired_at", "timestamp with time zone", "NO"),
                ("discord_retired_roles", "discord_role_id", "text", "NO"),
                ("discord_retired_roles", "retired_at", "timestamp with time zone", "NO"),
                ("roles", "discord_role_id", "text", "YES"),
            ]
            assert "UNIQUE" in after["index"]
            assert "WHERE (discord_role_id IS NOT NULL)" in after["index"]
    finally:
        async with admin_engine.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))
        await admin_engine.dispose()
```

## §6 確かめ（生出力を報告書に貼る）

- `bash -n scripts/run_all_migrations.sh` の生出力（何も出なければ「出力なし」と書く）
- `grep -n "20261106_150000_add_discord_role_link_tables" scripts/run_all_migrations.sh` の生出力（1 行だけのはず）
- `grep -n "discord_role_id\|discord_retired" backend/app/services/tenant.py` の生出力（5 行のはず: roles の列 1・索引 1・CREATE TABLE 2・discord_retired_roles の `discord_role_id TEXT PRIMARY KEY` 1。今の origin/main では 0 行。数が違えば停止して NEEDS_DECISION: と生出力）
- `cd backend && python -m pytest tests/test_discord_role_link_ddl.py tests/test_roles_system_key_ddl.py -q` の生出力（PostgreSQL が無ければ PG の 2 件は skipped になる。単体の 6 件（新しい試験 3 件＋既存の試験 3 件）が passed であること）
- `python scripts/check_schema_catchup_sync.py` の生出力（リポジトリの根で。setup_tenant.py・sync_tenant_schema.py は触っていないので変わらないはず）
- `git diff --stat origin/main` の生出力（第2段の設計の文書 5 つ・このカード・§1〜§5 の 5 つ・報告書のほかに無いこと）
- 手元に PostgreSQL があれば、§5 の PG の試験を TEST_PG_URL を付けて流し生出力を貼る。無ければ「PostgreSQL なし・CI の pytest と schema-check に任せる」と書く
- `BASE_SHA=$(git merge-base HEAD origin/main) HEAD_SHA=$(git rev-parse HEAD) python3 scripts/check_test_schema_dup.py; echo rc=$?` の生出力（リポジトリの根で。rc=0 であること。rc=1 なら停止して BLOCKED: と生出力）

## §5-改訂1（2026-11-06・PR 審査で見つかったカードの不備）

- 【事実】初版の §5 は `_block` の区切りに `"CREATE TABLE IF NOT EXISTS {schema}.discord_retired_roles ("` と `..._members (` を渡していた。assert の外の文字列なので、CI「test-schema-dup gate」（`scripts/check_test_schema_dup.py`）が本番の表の定義の写しとして 2 件数え、赤になった（`backend/tests/test_discord_role_link_ddl.py (0 -> 2)`、Opus が手元で同じ rc=1 を再現）。
- 直し: 区切りを `"{schema}.discord_retired_roles ("`・`"{schema}.discord_retired_members ("` にする（§5 は改訂済み）。tenant.py の中でそれぞれ 1 回だけ出る（Opus が `grep -c` で 1・1 を確認）ので、`_block` の `count == 1` はそのまま成り立つ。
- 【事実】PR を出したあと、origin/main に bb38918d7・b81375897 が入った。`backend/tests/test_roles_system_key_ddl.py` が次のように変わっている。
  - テナント番号を 997 から 995 に変えた。
  - 移行は `_apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)` で 1 つのテナントだけに絞って流す。
  - 片付けの DROP SCHEMA は `public_bootstrap_lock` の中で流す。
  - 同時に流したときのぶつかり（実装報告の DeadlockDetectedError と同じ種類）を止める直しである。
  - 本 PR の新しい試験も 995 を使っているので、同じ番号が重なる。CI「guard-authoring/evaluation」は、PR の土台より main が先に進んだため error になっている。

### 改訂1 の作業（この順に。触るのは 3 ファイルだけ）

（１）`git fetch origin main` のあと `git merge --no-ff origin/main`（merge commit。rebase・force push はしない）。
- 重なるのは `backend/tests/test_roles_system_key_ddl.py` だけのはず。
- 直し方: origin/main の側をそのまま取る。そのうえで、`assert sql.count(marker) == 2` の 1 か所だけを `== 3` にする。
- 同じ行の末尾の説明は `# roles の定義・部分一意索引 2 つ（system_key・discord_role_id）` にする。
- ほかのファイルが重なったら、直さずに停止する。NEEDS_DECISION: と `git status` の生出力を返す。

（２）`backend/tests/rls_bootstrap.py` の `_TENANT_LOOP_MIGRATIONS` に 1 行足す。
- 場所は `"20261005_150000_add_roles_system_key.sql": 1,` のすぐ次。
- 足す行: `"20261106_150000_add_discord_role_link_tables.sql": 1,`
- この移行に、テナントを選ぶ条件は 1 か所しかない。Opus が `_TENANT_LOOP_SELECTOR_RE` と同じ正規表現で数え、1 だった。

（３）`backend/tests/test_discord_role_link_ddl.py` を次のとおりにする。
- import を `from tests.rls_bootstrap import (_apply_migration_on_conn, bootstrap_tenant_schema, public_bootstrap_lock, tenant_schema_lock,)` にする（origin/main の test_roles_system_key_ddl.py と同じ並び・括弧の書き方）。
- `_TENANT_ID = 995` を `_TENANT_ID = 994` にする。直前の行に `# 995 は test_roles_system_key_ddl.py が使うため、試験・移行のどこにも無い 994 を使う` を書く。Opus が backend/tests と migrations を grep し、994 は 0 件だった。
- `_block` の 2 つの区切りは §5（改訂済み）のとおりにする。
- PG の試験の本体は、origin/main の `test_new_tenant_has_system_key_and_migration_is_idempotent` と同じ形にする。
  - `tenant_schema_lock` の中を `try:`／`finally:` にする。
  - 移行の 2 回流しは `await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)` を 2 回にする（`exec_driver_sql(migration_sql)` と `migration_sql = ...` の行は消す）。
  - finally は `async with public_bootstrap_lock(admin_engine):` の中で `DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE` を流す。
  - 外側の finally には `await admin_engine.dispose()` だけを残す。
  - `before`／`after` の比べ方と assert は変えない。
- ファイルの最後に、単体の試験を 1 つ足す（origin/main の `test_roles_migration_is_scoped_to_own_tenant` と同じ形）。

```python
def test_link_migration_is_scoped_to_own_tenant():
    from tests.rls_bootstrap import _scope_tenant_migration

    sql = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
    scoped = _scope_tenant_migration(sql, _MIGRATION, _SCHEMA)
    assert scoped.count(f"AND nspname = '{_SCHEMA}'") == 1
    assert scoped != sql
```

### 改訂1 の確かめ（生出力を報告書の「改訂1」節に貼る）

- `git log --oneline -3` と `git merge-base --is-ancestor origin/main HEAD; echo rc=$?`（rc=0 であること）
- `cd backend && python -m pytest tests/test_discord_role_link_ddl.py tests/test_roles_system_key_ddl.py -q`。PostgreSQL が無ければ PG の 2 件は skipped になる。単体はすべて passed であること。
- 手元に PostgreSQL があれば、2 つの PG の試験を TEST_PG_URL 付きで流す。直列で 1 回、`-n 4 --dist=loadfile` で 3 回。ぶつかりが出なければよい。無ければ「PostgreSQL なし・CI に任せる」と書く。
- §6 の最後の行（check_test_schema_dup.py の rc=0）
- `cd backend && ruff check tests/test_discord_role_link_ddl.py tests/test_roles_system_key_ddl.py tests/rls_bootstrap.py`
- `git diff --name-only origin/main...HEAD` の生出力（PR #5174 の 13 ファイル＋`backend/tests/rls_bootstrap.py` の 14 ファイルであること）

### 改訂1 の保存

- merge commit の文は git の既定のまま。
- 直しの commit の文: `test: scope 2a-1 PG test to its own tenant and drop CREATE TABLE markers (schema-dup gate, xdist)`
- `git push origin release/discord-own-server-s2-2a1` を単独で流す。PR はもうある（#5174）ので作らない。
- 報告書 `docs/handoff/discord-server-management/impl-report-s2-2a1.md` の最後に「改訂1」節を足し、同じ commit に入れる。

## §7 保存

- commit の文: `feat(db): roles に Discord のロールの番号の列、消した番号を覚える表 2 つを足す（discord-server-management 第2段 2a-1）`
- commit のあと `git log --oneline -3` の生出力を報告書に貼る
- `git push origin release/discord-own-server-s2-2a1`（単独で流す）。PR は作らない（Opus が作る）
- 報告書の最後に、push 後の `git rev-parse HEAD` の生出力

## 想定分岐（停止の条件）

- preflight が失敗した → 停止。BLOCKED: と生出力（クラウドでは [1/3][2/3] の FAIL を除く。§0 のとおり）
- migrations/ に 20261106_150000 で始まるファイルが既にある、または最後の移行の番号が 20261106_150000 より後 → 停止。BLOCKED: とファイル名
- run_all_migrations.sh の末尾の形が「run_sql migrations/…」の並びでない → 停止。BLOCKED: と末尾 20 行
- tenant.py の 505・510・1083 行目が §3 の「変更前」と違う（ほかの PR が先に変えた）→ 書いてある文の位置で同じ場所が一意に見つかればそこに足し、報告書に実際の行番号を書く。見つからない・2 か所あるなら停止。NEEDS_DECISION: と該当の前後 10 行
- test_roles_system_key_ddl.py 31 行目が §4 の「変更前」と違う → 停止。NEEDS_DECISION: と前後 10 行
- 試験が落ちた → 直そうとしてカードの外のファイルを変えない。停止して BLOCKED: と生出力
- 触ってよいファイル以外を変えたくなった → 変えずに停止。NEEDS_DECISION: と理由
- push が拒否された → 言い換えて再試行しない。停止して BLOCKED: と生出力

報告の最後の行は DONE / BLOCKED: 理由 / NEEDS_DECISION: 理由 のどれか 1 つ。

END OF CARD
