---
mode: handoff
---

# Q1 ひな形の会社に登録全件を流す（使い捨ての DB `q1_db`）

本報告はカード 前調査 5-2a の実行結果である。

- 読んだ commit: `39b73e9b7b2fec00426ec708e471eaf0c9de3d22`（`origin/main`。手順2で `git rev-parse HEAD` と `git rev-parse origin/main` が同じ値だった）
- 作業場所: `/root/worktrees/salesanchor/release-migration-template-5-2a`（枝 `release/migration-template-5-2a`）
- 設計との食い違い: 無し（`design.md` §5-6 に従った。カードの登録の本数 404（run_sql 378・run_py 26）と実測が一致）。

## 手順2〜5の記録

```
git fetch origin
bash scripts/new-worktree.sh release/migration-template-5-2a
git rev-parse HEAD        -> 39b73e9b7b2fec00426ec708e471eaf0c9de3d22
git rev-parse origin/main -> 39b73e9b7b2fec00426ec708e471eaf0c9de3d22
```

### 手順3（preflight。出力の全文）
```
== executor preflight (identity=shingo-cc, mode=fix) ==
[1/3] network -> api.github.com
  [FAIL] GitHub API に到達不可。Mac回線ではなく実行役サンドボックスの通信OFFが濃厚。
       => Codexをネット有効で起動 (信頼repo内: codex --sandbox danger-full-access / または config の network_access=true)
[2/3] gh auth = shingo-cc
  [warn] gh の active account が shingo-cc でない。gh auth switch で切り替え試行...
  [FAIL] gh auth switch --hostname github.com --user shingo-cc に失敗。gh auth status --active で現状を確認。
[3/3] git config user.name = shingo-cc
  [OK]   git user.name を shingo-cc に設定
[4/4] long-lived branch -> origin/main
  [OK]   origin/main は存在
==============================================
PREFLIGHT FAIL — 上の対策を実施し再実行(深追いしない)
```
（カードの指示どおり、`gh auth switch` で落ちたことを記録して続けた。）

### 手順4・4b
- `ls /usr/lib/postgresql/` → `16`。`postgres --version` → `postgres (PostgreSQL) 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)`。
- 実行者が root のため `initdb` は OS の `postgres` 利用者で流した: `initdb -D /tmp/recon/pgdata -U postgres --auth=trust`、`pg_ctl -D /tmp/recon/pgdata -o "-p 55432 -k /tmp/recon" -l /tmp/recon/pg.log start`。接続先は `localhost:55432` だけ。
- Python: `python3.12 -m venv /tmp/recon/venv` → `pip install -r requirements.txt -r requirements-dev.txt`（成功）→ `pip check` → `No broken requirements found.`。python は `/tmp/recon/venv/bin/python` だけを使った。

### 手順5（利用者。試験の中で作った。`card-5-0b` の最終版と同じ）
- `jarvis`: SUPERUSER・LOGIN・パスワード `testpass`
- `salesanchor_app`: LOGIN・NOSUPERUSER・NOCREATEDB・NOBYPASSRLS
- `ai_unmask_owner`: NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION BYPASSRLS（`migrations/20261031_210000_create_ops_case.sql:180-189` が求める属性。前の調べ `common.md` の「手順5の補足」と同じ）

## 使った命令（全文）
```
cd /root/worktrees/salesanchor/release-migration-template-5-2a/backend && /tmp/recon/venv/bin/python -m pytest /tmp/recon/test_5_2a.py -x -s -p no:cacheprovider > /tmp/recon/q1-pytest.out 2>&1
```
結果: `1 passed in 21.35s`。

## 試験のファイル `/tmp/recon/test_5_2a.py` の全文（commit しない）

```python
"""前調査 5-2a の試験（使い捨ての PostgreSQL 16 / localhost:55432 だけにつなぐ）。

Q1: ひな形で作った会社 tenant_003 に、登録の全件を流し、形を取る。
流し方: cd backend && /tmp/recon/venv/bin/python -m pytest /tmp/recon/test_5_2a.py -x -s
"""
from __future__ import annotations

import asyncio
import os
import re
import subprocess
import time
from pathlib import Path

import psycopg2
import pytest

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ.setdefault("ADMIN_DATABASE_URL", os.environ["DATABASE_URL"])

from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

ROOT = Path("/root/worktrees/salesanchor/release-migration-template-5-2a")
REC = ROOT / "docs/handoff/migration-runner-redesign/recon-5-2a"
OUT = Path("/tmp/recon/out")
OUT.mkdir(parents=True, exist_ok=True)
HOST = "localhost"
PORT = 55432
PGBIN = "/usr/lib/postgresql/16/bin"
VENV_BIN = "/tmp/recon/venv/bin"
DB = "q1_db"


def dsn(db: str, user: str = "jarvis") -> str:
    return f"host={HOST} port={PORT} dbname={db} user={user}"


def sa_url(db: str) -> str:
    return f"postgresql+asyncpg://jarvis:testpass@{HOST}:{PORT}/{db}"


SHAPE_QUERIES = {
    "columns": "SELECT c.relname, count(*) AS n, string_agg(a.attname||'|'||format_type(a.atttypid,a.atttypmod)||'|'||a.attnotnull::text||'|'||coalesce(replace(pg_get_expr(d.adbin,d.adrelid),'tenant_003','X'),''), ' ;; ' ORDER BY a.attname) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum WHERE n.nspname='tenant_003' AND c.relkind IN ('r','p') AND a.attnum>0 AND NOT a.attisdropped GROUP BY 1 ORDER BY 1 LIMIT 150",
    "indexes": "SELECT t.relname, count(*) AS n, string_agg(replace(pg_get_indexdef(i.indexrelid),'tenant_003','X'), ' ;; ' ORDER BY ic.relname) FROM pg_index i JOIN pg_class ic ON ic.oid=i.indexrelid JOIN pg_class t ON t.oid=i.indrelid JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname='tenant_003' GROUP BY 1 ORDER BY 1 LIMIT 150",
    "constraints": "SELECT c.relname, count(*) AS n, string_agg(k.conname||'|'||k.contype::text||'|'||replace(pg_get_constraintdef(k.oid),'tenant_003','X'), ' ;; ' ORDER BY k.conname) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=k.connamespace WHERE n.nspname='tenant_003' GROUP BY 1 ORDER BY 1 LIMIT 150",
    "triggers": "SELECT c.relname, count(*) AS n, string_agg(replace(pg_get_triggerdef(g.oid),'tenant_003','X'), ' ;; ' ORDER BY g.tgname) FROM pg_trigger g JOIN pg_class c ON c.oid=g.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='tenant_003' AND NOT g.tgisinternal GROUP BY 1 ORDER BY 1 LIMIT 150",
    "policies": "SELECT c.relname, count(*) AS n, string_agg(p.polname||'|'||p.polcmd::text||'|'||p.polpermissive::text||'|'||coalesce(array_to_string(ARRAY(SELECT CASE WHEN r=0 THEN 'public' ELSE pg_get_userbyid(r) END FROM unnest(p.polroles) r ORDER BY 1),','),'')||'|'||coalesce(replace(pg_get_expr(p.polqual,p.polrelid),'tenant_003','X'),'')||'|'||coalesce(replace(pg_get_expr(p.polwithcheck,p.polrelid),'tenant_003','X'),''), ' ;; ' ORDER BY p.polname) FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='tenant_003' GROUP BY 1 ORDER BY 1 LIMIT 150",
    "table_flags": "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity, pg_get_userbyid(c.relowner), c.relacl::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='tenant_003' AND c.relkind IN ('r','p') ORDER BY 1 LIMIT 150",
    "sequences": "SELECT c.relname, format_type(s.seqtypid,NULL), s.seqstart, s.seqincrement, s.seqcycle, c.relacl::text FROM pg_sequence s JOIN pg_class c ON c.oid=s.seqrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='tenant_003' ORDER BY 1 LIMIT 150",
    "functions": "SELECT p.proname, pg_get_function_identity_arguments(p.oid), md5(replace(p.prosrc,'tenant_003','X')), p.prosecdef FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='tenant_003' ORDER BY 1 LIMIT 150",
    "views": "SELECT c.relname, md5(replace(pg_get_viewdef(c.oid),'tenant_003','X')), c.relacl::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='tenant_003' AND c.relkind='v' ORDER BY 1 LIMIT 150",
}
HEADERS = {
    "columns": ["relname", "n", "string_agg"],
    "indexes": ["relname", "n", "string_agg"],
    "constraints": ["relname", "n", "string_agg"],
    "triggers": ["relname", "n", "string_agg"],
    "policies": ["relname", "n", "string_agg"],
    "table_flags": ["relname", "relrowsecurity", "relforcerowsecurity", "pg_get_userbyid", "relacl"],
    "sequences": ["relname", "format_type", "seqstart", "seqincrement", "seqcycle", "relacl"],
    "functions": ["proname", "pg_get_function_identity_arguments", "md5", "prosecdef"],
    "views": ["relname", "md5", "relacl"],
}


def _cell(v) -> str:
    if v is None:
        return ""
    return str(v).replace("\n", "\\n").replace("\t", "\\t")


def write_shape(outdir: Path, results: dict) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, rows in results.items():
        lines = ["\t".join(HEADERS[name])]
        for r in rows:
            lines.append("\t".join(_cell(x) for x in r))
        (outdir / f"{name}.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
        counts[name] = len(rows)
    return counts


def shape_sync(db: str, schema: str, outdir: Path) -> dict:
    conn = psycopg2.connect(dsn(db))
    try:
        cur = conn.cursor()
        res = {}
        for name, q in SHAPE_QUERIES.items():
            cur.execute(q.replace("tenant_003", schema))
            res[name] = cur.fetchall()
    finally:
        conn.close()
    return write_shape(outdir, res)


def scalar(sql: str, db: str, user: str = "jarvis"):
    conn = psycopg2.connect(dsn(db, user))
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute(sql)
        return cur.fetchall()
    finally:
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def roles():
    conn = psycopg2.connect(dsn("postgres", "postgres"))
    conn.autocommit = True
    cur = conn.cursor()
    stmts = [
        ("jarvis", "CREATE ROLE jarvis WITH SUPERUSER LOGIN PASSWORD 'testpass'"),
        ("salesanchor_app", "CREATE ROLE salesanchor_app WITH LOGIN PASSWORD 'apppass' NOSUPERUSER NOCREATEDB NOBYPASSRLS"),
        ("ai_unmask_owner", "CREATE ROLE ai_unmask_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION BYPASSRLS"),
    ]
    for rolname, stmt in stmts:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (rolname,))
        if cur.fetchone() is None:
            cur.execute(stmt)
    cur.execute("SELECT rolname, rolsuper, rolcanlogin FROM pg_roles WHERE rolname IN ('jarvis','salesanchor_app','ai_unmask_owner') ORDER BY 1")
    print("ROLES", cur.fetchall())
    conn.close()


def create_db(name: str) -> None:
    conn = psycopg2.connect(dsn("postgres"))
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,))
    if cur.fetchone() is not None:
        raise RuntimeError(f"DB {name} は既にある")
    cur.execute(f"CREATE DATABASE {name}")
    conn.close()


def mig_env(extra: dict | None = None) -> dict:
    env = dict(os.environ)
    env["PATH"] = f"{VENV_BIN}:{PGBIN}:/usr/bin:/bin"
    env.pop("PYTHONPATH", None)
    env.update({
        "PGHOST": HOST, "PGPORT": str(PORT), "PGUSER": "jarvis", "PGPASSWORD": "testpass", "PGDATABASE": DB,
        "DATABASE_URL": f"postgresql://jarvis:testpass@{HOST}:{PORT}/{DB}",
        "MIGRATION_LOCK_TIMEOUT": "1s",
        "PGOPTIONS": "-c lock_timeout=1s",
    })
    if extra:
        env.update(extra)
    return env


def registry():
    """scripts/run_all_migrations.sh:51 と同じ数え方（行の先頭が run_sql か run_py で、その後に空白）。"""
    out = []
    for i, ln in enumerate((ROOT / "scripts/run_all_migrations.sh").read_text(encoding="utf-8").splitlines(), 1):
        m = re.match(r"^run_(sql|py)[ \t]+(\S+)(.*)$", ln)
        if m:
            out.append((i, m.group(1), m.group(2), m.group(3).strip()))
    return out


def first_err(text_: str) -> str:
    lines = [x for x in text_.splitlines() if x.strip()]
    for x in lines:
        if "ERROR" in x or "Error" in x:
            return x.strip()[:300]
    return (lines[-1].strip()[:300] if lines else "")


def run_sql_file(rel: str, env: dict, extra_args: list[str] | None = None, stdin_rel: str | None = None):
    cmd = [f"{PGBIN}/psql", "-v", "ON_ERROR_STOP=1"] + (extra_args or [])
    with open(ROOT / rel, "rb") as f:
        return subprocess.run(cmd, stdin=f, cwd=ROOT, env=env, capture_output=True, timeout=900)


def test_q1_template_plus_all():
    create_db(DB)
    from tests import rls_bootstrap as rb

    reg = registry()
    n_sql = sum(1 for r in reg if r[1] == "sql")
    n_py = sum(1 for r in reg if r[1] == "py")
    print("Q1 registry count", len(reg), "sql", n_sql, "py", n_py)

    async def prep():
        eng = create_async_engine(sa_url(DB), echo=False)
        try:
            await rb.bootstrap_public_products(eng)
            await rb.ensure_product_packagings(eng)
            schema = await rb.bootstrap_tenant_schema(eng, 3)
            assert schema == "tenant_003"
        finally:
            await eng.dispose()

    asyncio.run(prep())

    ids = scalar("SELECT id FROM public.tenants ORDER BY id", DB)
    schemas = scalar("SELECT nspname FROM pg_namespace WHERE nspname LIKE 'tenant\\_%' ORDER BY 1", DB)
    pre = f"tenants.id\t{[r[0] for r in ids]}\ntenant_ schemas\t{[r[0] for r in schemas]}\n"
    (OUT / "q1-pre.txt").write_text(pre, encoding="utf-8")
    print("Q1 PRE", pre)
    pre_counts = shape_sync(DB, "tenant_003", OUT / "q1-shape-before-all")
    print("Q1 shape before all", pre_counts)

    logdir = OUT / "q1-logs"
    logdir.mkdir(parents=True, exist_ok=True)
    backend = ROOT / "backend"
    rows = []
    for ln, kind, target, extra in reg:
        t0 = time.time()
        rc2 = ""
        err = ""
        if kind == "sql":
            p = run_sql_file(target, mig_env())
            rc1 = p.returncode
            so, se = p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")
            (logdir / f"{ln}-1.log").write_text(so + "\n--- stderr ---\n" + se, encoding="utf-8")
            if rc1 != 0:
                err = first_err(se)
        else:
            env = mig_env()
            m = re.match(r"-e\s+(\w+)=(\S+)", extra)
            if m:
                env[m.group(1)] = m.group(2)
            cmd = [f"{VENV_BIN}/python", str(ROOT / "scripts/migration_py_entry.py"), str(ROOT / target)]
            p = subprocess.run(cmd, cwd=backend, env=env, capture_output=True, text=True, timeout=900)
            rc1 = p.returncode
            (logdir / f"{ln}-1.log").write_text(p.stdout + "\n--- stderr ---\n" + p.stderr, encoding="utf-8")
            if rc1 != 0:
                err = first_err(p.stderr)
                env2 = dict(env)
                env2["PYTHONPATH"] = str(backend)
                p2 = subprocess.run(cmd, cwd=backend, env=env2, capture_output=True, text=True, timeout=900)
                rc2 = str(p2.returncode)
                (logdir / f"{ln}-2.log").write_text(p2.stdout + "\n--- stderr ---\n" + p2.stderr, encoding="utf-8")
                if p2.returncode != 0:
                    err = err + "  ||  2回目: " + first_err(p2.stderr)
        secs = round(time.time() - t0, 1)
        rows.append((ln, kind, target, rc1, rc2, secs, err.replace("\t", " ")))
        print("Q1", ln, kind, target, "rc1=", rc1, "rc2=", rc2, f"{secs}s", "|", err[:120])

    # 本体の終わりの手順（run_all_migrations.sh:230-273 の EXIT の trap）と同じ3つ
    trap_items = [
        ("sql", "migrations/20261017_130100_create_ai_ro_views.sql", ["-v", "VERBOSITY=terse"], "-c statement_timeout=30s"),
        ("sql", "migrations/20261024_100300_create_ai_cloud_views.sql", ["-v", "VERBOSITY=terse"], "-c statement_timeout=30s"),
        ("cmd", "SELECT ops_case.grant_unmask_owner();", ["-v", "VERBOSITY=terse", "-c", "SELECT ops_case.grant_unmask_owner();"], "-c statement_timeout=30s"),
    ]
    trows = []
    for idx, (kind, target, args, opts) in enumerate(trap_items, 1):
        t0 = time.time()
        env = mig_env({"PGOPTIONS": opts})
        if kind == "sql":
            p = run_sql_file(target, env, extra_args=args)
        else:
            p = subprocess.run([f"{PGBIN}/psql", "-v", "ON_ERROR_STOP=1"] + args, cwd=ROOT, env=env, capture_output=True, timeout=900)
        se = p.stderr.decode("utf-8", "replace")
        (logdir / f"trap-{idx}.log").write_text(p.stdout.decode("utf-8", "replace") + "\n--- stderr ---\n" + se, encoding="utf-8")
        secs = round(time.time() - t0, 1)
        err = first_err(se) if p.returncode != 0 else ""
        trows.append((f"trap{idx}", "trap", target, p.returncode, "", secs, err.replace("\t", " ")))
        print("Q1 TRAP", idx, target, "rc=", p.returncode, f"{secs}s", "|", err[:120])

    allrows = rows + trows
    (OUT / "q1-result.tsv").write_text(
        "line\tkind\ttarget\trc1\trc2\tsec\tfirst_error\n" + "\n".join("\t".join(map(str, r)) for r in allrows) + "\n",
        encoding="utf-8")
    (OUT / "q1-counts.txt").write_text(f"registry\t{len(reg)}\nsql\t{n_sql}\npy\t{n_py}\n", encoding="utf-8")
    counts = shape_sync(DB, "tenant_003", REC / "q1-shape")
    print("Q1 shape after all counts", counts)
    (OUT / "q1-shape-counts.txt").write_text(str(counts), encoding="utf-8")
```

## 流す前の記録（`public.tenants` の id の一覧・`tenant_` で始まる schema の一覧）
```
tenants.id	[3, 999]
tenant_ schemas	['tenant_003']
```

- 補足（事実）: `public.tenants` には id 3 のほかに id 999 の行がある（`bootstrap_tenant_schema` の前準備が入れる行と思われる。出どころは未確認）。schema は `tenant_003` だけで、`tenant_999` の schema は無い。下の run_py の落ちはこれに当たる。

## 登録の本数

- 試験が `scripts/run_all_migrations.sh:51` と同じ数え方（行の先頭が `run_sql`/`run_py` でその後に空白）で数えた値: 合計 404・run_sql 378・run_py 26。Opus の値（404・378・26）と一致。
- 下の表の行数: sql 378・py 26（一致）。`trap` は別の3行。

## 通った本数・落ちた本数

| 種類 | 登録の本数 | 通った | 落ちた |
|---|---|---|---|
| run_sql | 378 | 375 | 3 |
| run_py | 26 | 14（うち流し直しで通った1本を含む） | 12 |
| 合計 | 404 | 389 | 15 |
| trap（別枠） | 3 | 3 | 0 |

## 落ちた本の名前の一覧（15本）

| 登録の行 | 種類 | ファイル名 | 終わりの番号 | 流し直し | エラーの先頭の1行 |
|---|---|---|---|---|---|
| 287 | py | scripts/migrate_meta.py | 1 | 1 | asyncpg.exceptions.InvalidSchemaNameError: schema "tenant_999" does not exist  \|\|  2回目: asyncpg.exceptions.InvalidSchemaNameError: schema "tenant_999" does not exist |
| 318 | py | scripts/migrate_meta_inbox_phase1d.py | 1 | 1 | 2026-11-15 23:15:45,175 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:45,559 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 320 | py | scripts/migrate_meta_page_routing.py | 1 | 1 | 2026-11-15 23:15:46,270 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:46,704 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 321 | py | scripts/migrate_meta_messages_page_id.py | 1 | 1 | 2026-11-15 23:15:47,058 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:47,407 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 324 | py | scripts/migrate_adr015_lead_foundation.py | 1 | 1 | 2026-11-15 23:15:47,778 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:48,158 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 342 | py | scripts/migrate_adr021_sprint2_financials.py | 1 | 1 | 2026-11-15 23:15:48,524 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:48,899 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 343 | py | scripts/migrate_adr021_sprint3_shipping.py | 1 | 1 | 2026-11-15 23:15:49,305 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:49,675 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 344 | py | scripts/migrate_adr021_sprint4_purchase.py | 1 | 1 | 2026-11-15 23:15:50,036 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:50,383 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 345 | py | scripts/migrate_adr021_sprint5_commissions.py | 1 | 1 | 2026-11-15 23:15:50,811 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:51,189 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 354 | py | scripts/migrate_adr041_granted_scopes.py | 1 | 1 | 2026-11-15 23:15:52,225 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:52,559 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 357 | py | scripts/migrate_009_phase4_tenant_tables.py | 1 | 1 | ✗ tenant_999 migration 009 FAILED: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: ✗ tenant_999 migration 009 FAILED: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 358 | py | scripts/migrate_011_phase5_tenant_tables.py | 1 | 1 | ✗ tenant_999 migration 011 FAILED: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: ✗ tenant_999 migration 011 FAILED: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 369 | sql | migrations/072_add_retention_indexes.sql | 3 |  | ERROR:  relation "public.auth_events" does not exist |
| 530 | sql | migrations/20260605_030000_create_salesanchor_app_role.sql | 3 |  | ERROR:  database "jarvis_db" does not exist |
| 1209 | sql | migrations/20261101_130000_add_new_device_approval.sql | 3 |  | ERROR:  relation "public.auth_events" does not exist |

- 流し直し（`PYTHONPATH=<backend の絶対パス>`）で通った本: `:657 scripts/migrate_20260621_020000_backfill_lead_country.py`（1回目 `ModuleNotFoundError: No module named 'app'`・2回目 0）。
- 前の調べで落ちた `:342`〜`:345`（`tenant_001.orders` が無い）は、今回は `tenant_999` の schema が無いというエラーで落ちた（同じ本が落ちた理由が違う）。

## 全件の表（登録の行番号／種類／ファイル名／終わりの番号／流し直しの終わりの番号／かかった秒／エラーの先頭の1行）

| 登録の行 | 種類 | ファイル名 | 終わりの番号 | 流し直しの終わりの番号 | 秒 | エラーの先頭の1行 |
|---|---|---|---|---|---|---|
| 220 | sql | migrations/20261024_100200_drop_ai_cloud_views.sql | 0 |  | 0.0 |  |
| 224 | sql | migrations/20261017_125900_drop_ai_ro_views.sql | 0 |  | 0.0 |  |
| 287 | py | scripts/migrate_meta.py | 1 | 1 | 0.8 | asyncpg.exceptions.InvalidSchemaNameError: schema "tenant_999" does not exist  \|\|  2回目: asyncpg.exceptions.InvalidSchemaNameError: schema "tenant_999" does not exist |
| 288 | sql | migrations/013_add_meta_webhook_idempotency.sql | 0 |  | 0.0 |  |
| 291 | sql | migrations/014_create_current_tenant_id_function.sql | 0 |  | 0.0 |  |
| 292 | sql | migrations/018_extend_permissions_with_menu_grain.sql | 0 |  | 0.0 |  |
| 293 | sql | migrations/023_fix_system_admin_is_system_flag.sql | 0 |  | 0.0 |  |
| 294 | sql | migrations/024_add_staff_bots_permissions.sql | 0 |  | 0.0 |  |
| 295 | sql | migrations/025_resync_owner_admin_all_permissions.sql | 0 |  | 0.0 |  |
| 298 | sql | migrations/026_create_customer_contact_channels.sql | 0 |  | 0.0 |  |
| 299 | sql | migrations/027_backfill_customer_contact_channels.sql | 0 |  | 0.0 |  |
| 302 | sql | migrations/028_create_companies.sql | 0 |  | 0.0 |  |
| 303 | sql | migrations/029_create_contacts.sql | 0 |  | 0.0 |  |
| 304 | sql | migrations/030_create_company_contact_subtables.sql | 0 |  | 0.0 |  |
| 305 | sql | migrations/031_create_customer_migration_map.sql | 0 |  | 0.0 |  |
| 306 | sql | migrations/032_add_company_contact_to_downstream.sql | 0 |  | 0.0 |  |
| 307 | sql | migrations/033_drop_companies_is_individual.sql | 0 |  | 0.0 |  |
| 308 | sql | migrations/034_add_unique_new_contact_id_to_customer_migration_map.sql | 0 |  | 0.0 |  |
| 309 | sql | migrations/035_drop_customer_id_from_downstream.sql | 0 |  | 0.0 |  |
| 310 | sql | migrations/036_drop_customer_migration_map.sql | 0 |  | 0.0 |  |
| 311 | sql | migrations/037_add_pending_dedup_review_to_contacts_check.sql | 0 |  | 0.0 |  |
| 312 | sql | migrations/038_add_products_phase1c_columns.sql | 0 |  | 0.0 |  |
| 315 | sql | migrations/039_create_data_deletion_logs.sql | 0 |  | 0.0 |  |
| 318 | py | scripts/migrate_meta_inbox_phase1d.py | 1 | 1 | 0.8 | 2026-11-15 23:15:45,175 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:45,559 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 319 | py | scripts/migrate_meta_inbox_phase1d_sprint4.py | 0 |  | 0.3 |  |
| 320 | py | scripts/migrate_meta_page_routing.py | 1 | 1 | 0.8 | 2026-11-15 23:15:46,270 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:46,704 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 321 | py | scripts/migrate_meta_messages_page_id.py | 1 | 1 | 0.7 | 2026-11-15 23:15:47,058 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:47,407 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 324 | py | scripts/migrate_adr015_lead_foundation.py | 1 | 1 | 0.8 | 2026-11-15 23:15:47,778 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:48,158 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 342 | py | scripts/migrate_adr021_sprint2_financials.py | 1 | 1 | 0.8 | 2026-11-15 23:15:48,524 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:48,899 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 343 | py | scripts/migrate_adr021_sprint3_shipping.py | 1 | 1 | 0.8 | 2026-11-15 23:15:49,305 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:49,675 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 344 | py | scripts/migrate_adr021_sprint4_purchase.py | 1 | 1 | 0.7 | 2026-11-15 23:15:50,036 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:50,383 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 345 | py | scripts/migrate_adr021_sprint5_commissions.py | 1 | 1 | 0.8 | 2026-11-15 23:15:50,811 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:51,189 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 346 | py | scripts/migrate_adr021_remove_confirmed_status.py | 0 |  | 0.3 |  |
| 349 | py | scripts/migrate_meta_messages_message_id_to_text.py | 0 |  | 0.3 |  |
| 350 | sql | migrations/053_add_users_locale.sql | 0 |  | 0.0 |  |
| 351 | sql | migrations/054_add_users_theme.sql | 0 |  | 0.0 |  |
| 354 | py | scripts/migrate_adr041_granted_scopes.py | 1 | 1 | 0.7 | 2026-11-15 23:15:52,225 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: 2026-11-15 23:15:52,559 [ERROR] ✗ tenant_999 失敗: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 357 | py | scripts/migrate_009_phase4_tenant_tables.py | 1 | 1 | 0.8 | ✗ tenant_999 migration 009 FAILED: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: ✗ tenant_999 migration 009 FAILED: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 358 | py | scripts/migrate_011_phase5_tenant_tables.py | 1 | 1 | 0.7 | ✗ tenant_999 migration 011 FAILED: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist  \|\|  2回目: ✗ tenant_999 migration 011 FAILED: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.InvalidSchemaNameError'>: schema "tenant_999" does not exist |
| 361 | py | scripts/migrate_inventory_sprint1.py | 0 |  | 0.5 |  |
| 362 | py | scripts/migrate_inventory_sprint2.py | 0 |  | 0.4 |  |
| 363 | py | scripts/migrate_inventory_sprint5_to_7.py | 0 |  | 0.4 |  |
| 364 | py | scripts/migrate_inventory_sprint8.py | 0 |  | 0.3 |  |
| 365 | py | scripts/migrate_inventory_sprint9.py | 0 |  | 0.4 |  |
| 368 | sql | migrations/071_create_data_access_events.sql | 0 |  | 0.0 |  |
| 369 | sql | migrations/072_add_retention_indexes.sql | 3 |  | 0.0 | ERROR:  relation "public.auth_events" does not exist |
| 372 | py | scripts/migrate_073_lead_status.py | 0 |  | 0.3 |  |
| 373 | py | scripts/migrate_074_rename_english_name_to_nickname.py | 0 |  | 0.4 |  |
| 374 | sql | migrations/075_create_goals.sql | 0 |  | 0.0 |  |
| 375 | sql | migrations/076_add_google_calendar_config.sql | 0 |  | 0.0 |  |
| 376 | sql | migrations/077_calendar_sync_mode_and_webhook_subscriptions.sql | 0 |  | 0.0 |  |
| 377 | sql | migrations/078_create_calendar_events_tenant.sql | 0 |  | 0.0 |  |
| 378 | py | scripts/migrate_20260620_080000_calendar_category_backfill.py | 0 |  | 0.3 |  |
| 379 | sql | migrations/080_phase_b_migration.sql | 0 |  | 0.0 |  |
| 382 | sql | migrations/081_create_inventory.sql | 0 |  | 0.0 |  |
| 383 | sql | migrations/082_extend_products_box_attributes.sql | 0 |  | 0.0 |  |
| 384 | sql | migrations/083_add_staff_phone.sql | 0 |  | 0.0 |  |
| 385 | sql | migrations/084_add_unit_to_inventory.sql | 0 |  | 0.0 |  |
| 386 | sql | migrations/20260620_010000_create_inventory_aggregation_rules.sql | 0 |  | 0.0 |  |
| 387 | sql | migrations/20260622_020000_add_inventory_raw_condition.sql | 0 |  | 0.0 |  |
| 388 | sql | migrations/20260623_010000_add_inventory_axes_columns.sql | 0 |  | 0.0 |  |
| 389 | sql | migrations/20260623_040000_make_inventory_condition_nullable.sql | 0 |  | 0.0 |  |
| 390 | sql | migrations/20260623_020000_create_inventory_offer_v2_unique_key.sql | 0 |  | 0.0 |  |
| 395 | sql | migrations/20260623_020000_drop_products_category_classification.sql | 0 |  | 0.0 |  |
| 396 | sql | migrations/085_create_tcg_type_master.sql | 0 |  | 0.0 |  |
| 397 | sql | migrations/086_seed_additional_tcg_types.sql | 0 |  | 0.0 |  |
| 398 | sql | migrations/087_create_supplier_prompts.sql | 0 |  | 0.0 |  |
| 401 | sql | migrations/090_add_lead_contact_links.sql | 0 |  | 0.0 |  |
| 402 | sql | migrations/091_add_leads_discord_messaging_columns.sql | 0 |  | 0.0 |  |
| 403 | sql | migrations/092_add_meta_messages_discord_index.sql | 0 |  | 0.0 |  |
| 404 | sql | migrations/093_rename_order_statuses.sql | 0 |  | 0.0 |  |
| 405 | sql | migrations/094_create_message_translations.sql | 0 |  | 0.0 |  |
| 406 | sql | migrations/20260623_040000_add_tenant_id_to_message_translations.sql | 0 |  | 0.0 |  |
| 407 | sql | migrations/095_add_lead_social_links.sql | 0 |  | 0.0 |  |
| 408 | sql | migrations/096_add_deal_lead_source.sql | 0 |  | 0.0 |  |
| 411 | sql | migrations/097_create_company_discord.sql | 0 |  | 0.0 |  |
| 412 | sql | migrations/098_migrate_customer_discord_to_company_discord.sql | 0 |  | 0.0 |  |
| 413 | sql | migrations/099_add_discord_guild_config.sql | 0 |  | 0.0 |  |
| 416 | sql | migrations/100_add_meta_messages_image_columns.sql | 0 |  | 0.0 |  |
| 419 | sql | migrations/20260601_140000_drop_customers_tables.sql | 0 |  | 0.0 |  |
| 420 | sql | migrations/20260602_000000_add_products_central_columns.sql | 0 |  | 0.0 |  |
| 421 | sql | migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql | 0 |  | 0.0 |  |
| 422 | sql | migrations/20260602_020000_add_products_tcg_type.sql | 0 |  | 0.0 |  |
| 423 | sql | migrations/20260602_030000_add_products_unit.sql | 0 |  | 0.0 |  |
| 424 | sql | migrations/20260602_040000_backfill_products_unit_condition_from_inbound.sql | 0 |  | 0.0 |  |
| 425 | sql | migrations/20260602_120000_add_discord_ticket_config.sql | 0 |  | 0.0 |  |
| 428 | sql | migrations/20260602_150000_add_discord_scale_channels.sql | 0 |  | 0.0 |  |
| 431 | sql | migrations/20260602_160000_add_discord_role_names.sql | 0 |  | 0.0 |  |
| 434 | sql | migrations/20260602_170000_add_products_master_label_columns.sql | 0 |  | 0.0 |  |
| 437 | sql | migrations/20260602_180000_add_inventory_offer_type_ship_timing.sql | 0 |  | 0.0 |  |
| 440 | sql | migrations/20260602_190000_create_user_inventory_filters.sql | 0 |  | 0.0 |  |
| 443 | sql | migrations/20260602_200000_add_discord_config_connected_by_staff.sql | 0 |  | 0.0 |  |
| 453 | sql | migrations/20260603_000000_add_products_product_kind.sql | 0 |  | 0.0 |  |
| 456 | sql | migrations/20260603_010000_add_suppliers_line_and_address.sql | 0 |  | 0.0 |  |
| 459 | sql | migrations/20260604_050000_add_tenant_policy_columns.sql | 0 |  | 0.0 |  |
| 462 | sql | migrations/20260603_030000_seed_dragonball_products.sql | 0 |  | 0.0 |  |
| 465 | sql | migrations/20260603_040000_add_products_set_type.sql | 0 |  | 0.0 |  |
| 470 | sql | migrations/20260604_020000_backfill_products_shipping_defaults.sql | 0 |  | 0.0 |  |
| 473 | sql | migrations/20260604_030000_add_quote_invoice_item_overseas_columns.sql | 0 |  | 0.0 |  |
| 476 | sql | migrations/20260604_040000_seed_tcg_products_8series.sql | 0 |  | 0.0 |  |
| 479 | sql | migrations/20260604_050000_add_orders_paid_at.sql | 0 |  | 0.0 |  |
| 482 | sql | migrations/20260604_060000_add_lost_reason_code.sql | 0 |  | 0.0 |  |
| 485 | sql | migrations/20260604_070000_deprecate_columns.sql | 0 |  | 0.0 |  |
| 488 | sql | migrations/20260604_140000_create_own_inventory.sql | 0 |  | 0.0 |  |
| 489 | sql | migrations/20260604_150000_add_inventory_source_kind.sql | 0 |  | 0.0 |  |
| 492 | sql | migrations/20260604_110000_create_ingestion_jobs.sql | 0 |  | 0.0 |  |
| 493 | sql | migrations/20260604_120000_create_parse_logs.sql | 0 |  | 0.0 |  |
| 494 | sql | migrations/20260604_130000_create_supplier_parse_stats_view.sql | 0 |  | 0.0 |  |
| 497 | sql | migrations/20260604_090000_create_conversation_logs.sql | 0 |  | 0.0 |  |
| 498 | sql | migrations/20260604_100000_create_company_stats_view.sql | 0 |  | 0.0 |  |
| 501 | sql | migrations/20260604_080000_create_registration_tokens.sql | 0 |  | 0.0 |  |
| 504 | sql | migrations/20260604_160000_add_invoice_snapshot_columns.sql | 0 |  | 0.0 |  |
| 507 | sql | migrations/20260604_090000_create_link_templates.sql | 0 |  | 0.0 |  |
| 508 | sql | migrations/20260604_100000_add_guild_id_to_contact_channels.sql | 0 |  | 0.0 |  |
| 512 | sql | migrations/20260604_170000_create_product_attribute_masters.sql | 0 |  | 0.0 |  |
| 515 | sql | migrations/20260604_180000_analytics_agent_a_tables.sql | 0 |  | 0.0 |  |
| 518 | sql | migrations/20260604_220000_create_translation_glossary.sql | 0 |  | 0.0 |  |
| 521 | sql | migrations/20260605_000000_add_products_display_order.sql | 0 |  | 0.0 |  |
| 524 | sql | migrations/20260605_010000_rls_translation_glossary.sql | 0 |  | 0.0 |  |
| 527 | sql | migrations/20260605_020000_fix_translation_glossary_rls_cast.sql | 0 |  | 0.0 |  |
| 530 | sql | migrations/20260605_030000_create_salesanchor_app_role.sql | 3 |  | 0.0 | ERROR:  database "jarvis_db" does not exist |
| 533 | sql | migrations/20260605_040000_grant_salesanchor_app_tenant_schemas.sql | 0 |  | 0.0 |  |
| 536 | sql | migrations/20260606_010000_add_google_drive_config.sql | 0 |  | 0.0 |  |
| 539 | sql | migrations/20260607_000000_fix_rls_policy_variable_name.sql | 0 |  | 0.0 |  |
| 542 | py | scripts/migrate_adr109_status_codes.py | 0 |  | 0.3 |  |
| 545 | sql | migrations/20260607_120000_create_lead_channels.sql | 0 |  | 0.0 |  |
| 548 | py | scripts/migrate_adr119_lead_channels_backfill.py | 0 |  | 0.3 |  |
| 551 | sql | migrations/20260608_080000_add_carrier_credentials.sql | 0 |  | 0.0 |  |
| 554 | sql | migrations/20260609_090000_add_carrier_credentials_rls.sql | 0 |  | 0.0 |  |
| 558 | sql | migrations/20260609_100000_add_carrier_account_number.sql | 0 |  | 0.0 |  |
| 561 | sql | migrations/20260610_071110_add_paypal_config.sql | 0 |  | 0.0 |  |
| 564 | sql | migrations/20260611_010000_fix_owner_role_color.sql | 0 |  | 0.0 |  |
| 567 | sql | migrations/20260611_020000_add_invoice_paypal_columns.sql | 0 |  | 0.0 |  |
| 570 | sql | migrations/20260611_100000_create_channel_masters.sql | 0 |  | 0.0 |  |
| 573 | sql | migrations/20260611_110000_extend_order_shipping_for_ship_api.sql | 0 |  | 0.0 |  |
| 576 | sql | migrations/20260611_120000_add_conv_log_manual_columns.sql | 0 |  | 0.0 |  |
| 580 | sql | migrations/20260611_130000_fix_v_company_stats_deleted_at.sql | 0 |  | 0.0 |  |
| 583 | sql | migrations/20260611_140000_add_conv_log_is_manual.sql | 0 |  | 0.0 |  |
| 586 | sql | migrations/20260611_150000_add_paypal_webhook_id.sql | 0 |  | 0.0 |  |
| 589 | sql | migrations/20260612_090000_extend_registration_tokens_change_billing.sql | 0 |  | 0.0 |  |
| 592 | sql | migrations/20260612_131520_add_invoice_copypdf.sql | 0 |  | 0.0 |  |
| 595 | sql | migrations/20260612_200000_fedex_creds_unique_env.sql | 0 |  | 0.0 |  |
| 598 | sql | migrations/20260612_100000_add_contact_channel_unique.sql | 0 |  | 0.0 |  |
| 601 | sql | migrations/20260612_110000_add_company_discord_guild_id.sql | 0 |  | 0.0 |  |
| 604 | sql | migrations/20260612_154322_create_paypal_disputes.sql | 0 |  | 0.0 |  |
| 607 | sql | migrations/20260612_050000_backfill_invoice_timestamps.sql | 0 |  | 0.0 |  |
| 610 | sql | migrations/20260612_120000_fix_company_stats_ssot.sql | 0 |  | 0.0 |  |
| 613 | sql | migrations/20260612_150000_drop_password_hash.sql | 0 |  | 0.0 |  |
| 618 | sql | migrations/20260613_010000_funnel_deals_closed_at.sql | 0 |  | 0.0 |  |
| 621 | sql | migrations/20260613_020000_funnel_close_reasons.sql | 0 |  | 0.0 |  |
| 624 | sql | migrations/20260613_030000_funnel_leads_initiative_channel.sql | 0 |  | 0.0 |  |
| 627 | sql | migrations/20260613_040000_funnel_goals_kpi_extend.sql | 0 |  | 0.0 |  |
| 630 | sql | migrations/20260613_050000_funnel_purchase_cost_nullable.sql | 0 |  | 0.0 |  |
| 633 | sql | migrations/20260614_030000_add_carrier_test_result.sql | 0 |  | 0.0 |  |
| 636 | sql | migrations/20260614_040137_add_tenant_deletion_audit.sql | 0 |  | 0.0 |  |
| 639 | sql | migrations/20260614_100000_create_sales_form_tables.sql | 0 |  | 0.0 |  |
| 642 | sql | migrations/20260615_235900_seed_pokemon_mega_products.sql | 0 |  | 0.0 |  |
| 645 | sql | migrations/20260616_000000_fix_tcg_type_dedup.sql | 0 |  | 0.0 |  |
| 648 | sql | migrations/20260621_010000_create_countries_master.sql | 0 |  | 0.0 |  |
| 651 | sql | migrations/20260622_010000_add_meta_messages_master_history_columns.sql | 0 |  | 0.0 |  |
| 654 | sql | migrations/20260622_020000_migrate_conv_only_into_meta_messages.sql | 0 |  | 0.0 |  |
| 657 | py | scripts/migrate_20260621_020000_backfill_lead_country.py | 1 | 0 | 0.6 | ModuleNotFoundError: No module named 'app' |
| 661 | sql | migrations/20260623_060000_add_products_tcg_type_fk.sql | 0 |  | 0.0 |  |
| 664 | sql | migrations/20260623_100000_rls_message_translations.sql | 0 |  | 0.0 |  |
| 667 | sql | migrations/20260624_120000_backfill_meta_messages_original_language.sql | 0 |  | 0.0 |  |
| 670 | sql | migrations/20260624_140000_converge_inventory_v2.sql | 0 |  | 0.0 |  |
| 673 | sql | migrations/20260626_100000_add_outbound_draft_message_link.sql | 0 |  | 0.0 |  |
| 676 | sql | migrations/20260626_120000_add_unique_guild_id_to_tenant_discord_config.sql | 0 |  | 0.0 |  |
| 679 | sql | migrations/20260626_130000_force_rls_public_products.sql | 0 |  | 0.0 |  |
| 682 | sql | migrations/20260627_120000_add_tenant_features_table.sql | 0 |  | 0.0 |  |
| 685 | sql | migrations/20260629_010000_backfill_inventory_unit_from_products.sql | 0 |  | 0.0 |  |
| 688 | sql | migrations/20260628_170000_add_app_fx_rates.sql | 0 |  | 0.0 |  |
| 691 | sql | migrations/20260703_010000_txn_backbone_ben1a.sql | 0 |  | 0.0 |  |
| 694 | sql | migrations/20260629_020000_drop_products_condition_unit.sql | 0 |  | 0.0 |  |
| 697 | sql | migrations/20260703_020000_conv_backbone_ben1b.sql | 0 |  | 0.0 |  |
| 698 | sql | migrations/20260715_100000_add_conversation_logs_lead_fk.sql | 0 |  | 0.0 |  |
| 700 | sql | migrations/20260718_100000_leads_add_deal_columns.sql | 0 |  | 0.0 |  |
| 703 | sql | migrations/20260720_100000_orders_deal_id_drop_not_null.sql | 0 |  | 0.0 |  |
| 704 | sql | migrations/20260721_100000_close_reasons_quotes_add_lead_id.sql | 0 |  | 0.0 |  |
| 705 | sql | migrations/20260721_120000_close_reasons_quotes_leadid_notnull.sql | 0 |  | 0.0 |  |
| 706 | sql | migrations/20260723_120000_dcr_dealid_nullable.sql | 0 |  | 0.0 |  |
| 709 | sql | migrations/20260703_030000_order_items_ben2.sql | 0 |  | 0.0 |  |
| 712 | sql | migrations/20260724_074500_drop_orders_deal_id.sql | 0 |  | 0.0 |  |
| 715 | sql | migrations/20260724_131500_quotes_drop_deal_id.sql | 0 |  | 0.0 |  |
| 718 | sql | migrations/20260724_170000_dcr_drop_deal_id.sql | 0 |  | 0.0 |  |
| 721 | sql | migrations/20260726_180000_leads_drop_converted_deal_id.sql | 0 |  | 0.0 |  |
| 724 | sql | migrations/20260729_043520_drop_deals.sql | 0 |  | 0.0 |  |
| 727 | sql | migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql | 0 |  | 0.0 |  |
| 730 | sql | migrations/20260922_050000_fix_phase2c_fk_drop_only.sql | 0 |  | 0.0 |  |
| 733 | sql | migrations/20260831_110000_create_tcg_analysis_tables_t004.sql | 0 |  | 0.0 |  |
| 736 | sql | migrations/20260901_090000_add_condition_resolution_columns.sql | 0 |  | 0.0 |  |
| 739 | sql | migrations/20260901_120000_add_unit_inference_columns_t004.sql | 0 |  | 0.0 |  |
| 742 | sql | migrations/20260902_100000_create_lead_attachments.sql | 0 |  | 0.0 |  |
| 745 | sql | migrations/20260902_110000_tcg_classification_masters.sql | 0 |  | 0.0 |  |
| 748 | sql | migrations/20260902_110100_tcg_products_classification_ids.sql | 0 |  | 0.0 |  |
| 752 | sql | migrations/20260903_120000_tcg_unit_evidence_rules_t004.sql | 0 |  | 0.0 |  |
| 755 | sql | migrations/20260903_130000_tcg_note_master_t004.sql | 0 |  | 0.0 |  |
| 757 | sql | migrations/20260903_150000_tcg_status_master_t004.sql | 0 |  | 0.0 |  |
| 760 | sql | migrations/20260903_160000_tcg_normalization_rules_t004.sql | 0 |  | 0.0 |  |
| 763 | sql | migrations/20260903_180000_tcg_products_mark_en_t004.sql | 0 |  | 0.0 |  |
| 766 | sql | migrations/20260903_170000_item_corrections_t004.sql | 0 |  | 0.0 |  |
| 769 | sql | migrations/20260903_190000_tcg_normalization_rules_nr0136.sql | 0 |  | 0.0 |  |
| 772 | sql | migrations/20260903_200000_tcg_distribution_targets_t004.sql | 0 |  | 0.0 |  |
| 775 | sql | migrations/20260903_210000_tcg_distribution_settings_t004.sql | 0 |  | 0.0 |  |
| 778 | sql | migrations/20260903_220000_create_tcg_analysis_history_t004.sql | 0 |  | 0.0 |  |
| 779 | sql | migrations/20260904_160000_tcg_magazine_promo_products_t004.sql | 0 |  | 0.0 |  |
| 780 | sql | migrations/20260905_010000_tcg_pokemon_master_batch1_t004.sql | 0 |  | 0.0 |  |
| 781 | sql | migrations/20260905_020000_tcg_fix_product_names_t004.sql | 0 |  | 0.0 |  |
| 784 | sql | migrations/20260905_140000_import_jobs_review_stage_t004.sql | 0 |  | 0.0 |  |
| 787 | sql | migrations/20260905_120000_register_15_suppliers_t004.sql | 0 |  | 0.0 |  |
| 790 | sql | migrations/20260905_150000_record_manual_supplier_fixes_t004.sql | 0 |  | 0.0 |  |
| 794 | sql | migrations/20260906_120000_create_tcg_tables_t001.sql | 0 |  | 0.0 |  |
| 797 | sql | migrations/20260906_230000_redact_extraction_error_keys_t004.sql | 0 |  | 0.0 |  |
| 800 | sql | migrations/20260907_100000_tcg_note_master_expand_t004.sql | 0 |  | 0.0 |  |
| 801 | sql | migrations/20260907_120000_tcg_dist_stale_jobs_terminate_t004.sql | 0 |  | 0.0 |  |
| 804 | sql | migrations/20260907_140000_tcg_keyword_hygiene_t004.sql | 0 |  | 0.0 |  |
| 807 | sql | migrations/20260906_130000_create_tcg_product_import_history_t004.sql | 0 |  | 0.0 |  |
| 810 | sql | migrations/20260906_130100_create_tcg_product_import_history_t001.sql | 0 |  | 0.0 |  |
| 813 | sql | migrations/20260925_120000_add_product_exclude_keywords.sql | 0 |  | 0.0 |  |
| 821 | sql | migrations/20260908_130000_tcg_sp0136_requeue_extraction_t004.sql | 0 |  | 0.0 |  |
| 822 | sql | migrations/20260908_170000_tcg_keyword_v4_t004.sql | 0 |  | 0.0 |  |
| 825 | sql | migrations/20260908_210000_tcg_sp0136_supersede_old_message_t004.sql | 0 |  | 0.0 |  |
| 828 | sql | migrations/20260909_000000_public_products_phase2b_columns.sql | 0 |  | 0.0 |  |
| 831 | sql | migrations/20260909_130000_tcg_note_b2_t004.sql | 0 |  | 0.0 |  |
| 834 | sql | migrations/20260910_010000_tcg_import_message_links.sql | 0 |  | 0.0 |  |
| 837 | sql | migrations/20260910_160000_tcg_work_evidence.sql | 0 |  | 0.0 |  |
| 838 | sql | migrations/20260910_160100_tcg_normal_deck_coro_exclusion.sql | 0 |  | 0.0 |  |
| 839 | sql | migrations/20260910_170000_tcg_keyword_false_positive_guards.sql | 0 |  | 0.0 |  |
| 840 | sql | migrations/20260910_180000_tcg_interrupted_jobs_recovery_t004.sql | 0 |  | 0.0 |  |
| 841 | sql | migrations/20260910_200000_tcg_condition_note_delivery_t004.sql | 0 |  | 0.0 |  |
| 842 | sql | migrations/20260912_020000_tcg_resolved_work_id.sql | 0 |  | 0.0 |  |
| 843 | sql | migrations/20260912_160000_line_import_devices.sql | 0 |  | 0.0 |  |
| 844 | sql | migrations/20260912_170000_line_supplier_source_names.sql | 0 |  | 0.0 |  |
| 847 | sql | migrations/20260913_010000_seed_dragonball_products_v2.sql | 0 |  | 0.0 |  |
| 848 | sql | migrations/20260913_020000_seed_onepiece_products.sql | 0 |  | 0.0 |  |
| 849 | sql | migrations/20260913_030000_seed_unregistered_products.sql | 0 |  | 0.0 |  |
| 850 | sql | migrations/20260913_150000_tcg_empty_box_condition.sql | 0 |  | 0.0 |  |
| 851 | sql | migrations/20260913_200000_tcg_cardset_exclusion.sql | 0 |  | 0.0 |  |
| 852 | sql | migrations/20260913_210000_tcg_cardset_bundle_registration.sql | 0 |  | 0.0 |  |
| 855 | sql | migrations/20260914_080000_add_abbreviation_keywords_t004.sql | 0 |  | 0.0 |  |
| 858 | sql | migrations/20260914_010000_tcg_extraction_attempts.sql | 0 |  | 0.0 |  |
| 861 | sql | migrations/20260914_140000_unify_tcg_products_to_public.sql | 0 |  | 0.0 |  |
| 865 | sql | migrations/20260922_040000_fix_phase2c_fk_blocker.sql | 0 |  | 0.0 |  |
| 868 | sql | migrations/20260915_010000_drop_tcg_products_phase2c.sql | 0 |  | 0.0 |  |
| 871 | sql | migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql | 0 |  | 0.0 |  |
| 874 | sql | migrations/20260916_120000_phase_c_drop_tcg_uuid.sql | 0 |  | 0.0 |  |
| 877 | sql | migrations/20260916_130000_work_id_not_null.sql | 0 |  | 0.0 |  |
| 880 | sql | migrations/20260917_010000_add_product_code_to_extraction.sql | 0 |  | 0.0 |  |
| 883 | sql | migrations/20260917_000000_create_analysis_rule_tables.sql | 0 |  | 0.0 |  |
| 886 | sql | migrations/20260917_020000_supplier_ssot_migration.sql | 0 |  | 0.0 |  |
| 889 | sql | migrations/20260918_030000_supplier_ssot_phase2.sql | 0 |  | 0.0 |  |
| 892 | sql | migrations/20260919_010000_master_ssot_work_id_recast.sql | 0 |  | 0.0 |  |
| 895 | sql | migrations/20260919_015000_fix_view_to_table_rename.sql | 0 |  | 0.0 |  |
| 898 | sql | migrations/20260919_020000_master_ssot_public_tables.sql | 0 |  | 0.1 |  |
| 901 | sql | migrations/20260919_030000_master_ssot_fk_work_id.sql | 0 |  | 0.0 |  |
| 904 | sql | migrations/20260919_190000_fix_extraction_work_id_type.sql | 0 |  | 0.0 |  |
| 907 | sql | migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql | 0 |  | 0.0 |  |
| 910 | sql | migrations/20260920_020000_supplier_line_name_unique.sql | 0 |  | 0.0 |  |
| 913 | sql | migrations/20260920_040000_conditions_ssot_phase1.sql | 0 |  | 0.0 |  |
| 916 | sql | migrations/20260920_030000_units_add_tenant_id.sql | 0 |  | 0.0 |  |
| 919 | sql | migrations/20260920_050000_status_master_add_tenant_id.sql | 0 |  | 0.0 |  |
| 922 | sql | migrations/20260920_060000_note_master_tenant_id.sql | 0 |  | 0.0 |  |
| 925 | sql | migrations/20260920_070000_product_categories_tenant_id.sql | 0 |  | 0.0 |  |
| 928 | sql | migrations/20260920_120000_analysis_rule_public_tables.sql | 0 |  | 0.1 |  |
| 931 | sql | migrations/20260920_130000_create_product_classification.sql | 0 |  | 0.0 |  |
| 934 | sql | migrations/20260921_010000_drop_analysis_rule_tables.sql | 0 |  | 0.1 |  |
| 937 | sql | migrations/20260921_060000_create_product_kinds.sql | 0 |  | 0.0 |  |
| 938 | sql | migrations/20260921_070000_rename_tcg_type_master_to_type_master.sql | 0 |  | 0.0 |  |
| 939 | sql | migrations/20260921_080000_product_lines_add_type_id.sql | 0 |  | 0.0 |  |
| 940 | sql | migrations/20260921_090000_create_condition_definitions.sql | 0 |  | 0.0 |  |
| 941 | sql | migrations/20260921_100000_add_analysis_master_fk.sql | 0 |  | 0.0 |  |
| 944 | sql | migrations/20260921_110000_pipeline_tables_public.sql | 0 |  | 0.1 |  |
| 947 | sql | migrations/20260921_050000_drop_tenant004_pipeline_tables.sql | 0 |  | 0.0 |  |
| 950 | sql | migrations/20260921_120000_add_products_product_kind_id.sql | 0 |  | 0.0 |  |
| 953 | sql | migrations/20260924_040000_seed_knowledge_extraction_vocab.sql | 0 |  | 0.0 |  |
| 956 | sql | migrations/20260924_050000_create_supplier_knowledge_links.sql | 0 |  | 0.0 |  |
| 959 | sql | migrations/20260921_130000_drop_tenant004_master_copies.sql | 0 |  | 0.0 |  |
| 962 | sql | migrations/20260921_140000_product_classification_masters.sql | 0 |  | 0.0 |  |
| 965 | sql | migrations/20260922_000000_create_buyback_tables.sql | 0 |  | 0.0 |  |
| 968 | sql | migrations/20260922_010000_product_format_kind_id_and_products_type_master_id.sql | 0 |  | 0.0 |  |
| 971 | sql | migrations/20260922_030000_product_format_game_links.sql | 0 |  | 0.0 |  |
| 974 | sql | migrations/20260922_020000_create_rule_test_tables.sql | 0 |  | 0.0 |  |
| 977 | sql | migrations/20260922_060000_product_unit_condition_infra.sql | 0 |  | 0.0 |  |
| 980 | sql | migrations/20260922_080000_rename_line_analysis_tables.sql | 0 |  | 0.0 |  |
| 983 | sql | migrations/20260923_010000_product_formats_add_type_master_id.sql | 0 |  | 0.0 |  |
| 986 | sql | migrations/20260923_030000_promote_remaining_tcg_tables.sql | 0 |  | 0.0 |  |
| 989 | sql | migrations/20260923_040000_update_device_tcg_schema.sql | 0 |  | 0.0 |  |
| 992 | sql | migrations/20260923_050000_add_indexes_public_analysis_results.sql | 0 |  | 0.0 |  |
| 995 | sql | migrations/20260923_120000_add_work_id_to_analysis_results.sql | 0 |  | 0.0 |  |
| 998 | sql | migrations/20260924_000000_create_buyback_alert_rules.sql | 0 |  | 0.0 |  |
| 1001 | sql | migrations/20260924_010000_add_supplier_extraction_rules.sql | 0 |  | 0.0 |  |
| 1004 | sql | migrations/20260924_030000_add_extraction_example_text.sql | 0 |  | 0.0 |  |
| 1007 | sql | migrations/20260924_100000_buyback_product_matching.sql | 0 |  | 0.0 |  |
| 1011 | sql | migrations/20260924_110000_fix_analysis_run_snapshots_unit_condition_type.sql | 0 |  | 0.0 |  |
| 1014 | sql | migrations/20260924_060000_cleanup_supplier_name_duplicates.sql | 0 |  | 0.0 |  |
| 1017 | sql | migrations/20260924_120000_add_analysis_results_is_current.sql | 0 |  | 0.0 |  |
| 1020 | sql | migrations/20260925_010000_conditions_add_match_type.sql | 0 |  | 0.0 |  |
| 1023 | sql | migrations/20260925_020000_conditions_add_def_unit_note.sql | 0 |  | 0.0 |  |
| 1026 | sql | migrations/20260926_010000_add_raw_product_code.sql | 0 |  | 0.0 |  |
| 1029 | sql | migrations/20260926_080000_create_extraction_prompt_config.sql | 0 |  | 0.0 |  |
| 1032 | sql | migrations/20260926_080100_fix_product_code_dash.sql | 0 |  | 0.0 |  |
| 1035 | sql | migrations/20260927_120000_add_max_age_hours_setting.sql | 0 |  | 0.0 |  |
| 1038 | sql | migrations/20260927_130000_add_extraction_token_cost_columns.sql | 0 |  | 0.0 |  |
| 1041 | sql | migrations/20260927_100000_create_meta_message_reactions.sql | 0 |  | 0.0 |  |
| 1044 | sql | migrations/20260928_100000_delete_skip_condition_rules.sql | 0 |  | 0.0 |  |
| 1047 | sql | migrations/20260928_110000_create_extraction_shadow_tables.sql | 0 |  | 0.0 |  |
| 1050 | sql | migrations/20260929_120000_fix_source_messages_received_at.sql | 0 |  | 0.0 |  |
| 1053 | sql | migrations/20260930_120000_drop_supplier_prompts.sql | 0 |  | 0.0 |  |
| 1056 | sql | migrations/20260930_130000_set_discord_welcome_template_english.sql | 0 |  | 0.0 |  |
| 1059 | sql | migrations/20260930_150000_create_llm_usage_events.sql | 0 |  | 0.0 |  |
| 1062 | sql | migrations/20260930_160000_backfill_llm_usage_events.sql | 0 |  | 0.0 |  |
| 1065 | sql | migrations/20261001_120000_add_staff_avatar_token.sql | 0 |  | 0.0 |  |
| 1068 | sql | migrations/20261001_150000_create_discord_channel_webhooks.sql | 0 |  | 0.0 |  |
| 1071 | sql | migrations/20261002_160000_create_payment_fee_settings.sql | 0 |  | 0.0 |  |
| 1074 | sql | migrations/20261002_180000_comment_payment_fee_settings_columns.sql | 0 |  | 0.0 |  |
| 1077 | sql | migrations/20261002_170000_drop_discord_inventory_tables.sql | 0 |  | 0.0 |  |
| 1080 | sql | migrations/20261003_100000_create_app_fx_rate_history.sql | 0 |  | 0.0 |  |
| 1083 | sql | migrations/20261005_150000_add_roles_system_key.sql | 0 |  | 0.0 |  |
| 1086 | sql | migrations/20261006_170200_add_supplier_new_system_rules.sql | 0 |  | 0.0 |  |
| 1089 | sql | migrations/20261008_100000_create_line_unit_ignore_phrases.sql | 0 |  | 0.0 |  |
| 1092 | sql | migrations/20261009_100000_type_master_match_by_code.sql | 0 |  | 0.0 |  |
| 1095 | sql | migrations/20261009_150000_type_master_code_only_match.sql | 0 |  | 0.0 |  |
| 1098 | sql | migrations/20261009_180000_v102_engine_columns.sql | 0 |  | 0.0 |  |
| 1101 | sql | migrations/20261009_200000_create_review_reason_codes.sql | 0 |  | 0.0 |  |
| 1104 | sql | migrations/20261010_120000_create_analysis_soldout_extra_targets.sql | 0 |  | 0.0 |  |
| 1107 | sql | migrations/20261011_150000_add_analysis_results_price_basis.sql | 0 |  | 0.0 |  |
| 1110 | sql | migrations/20261012_100000_add_extraction_jobs_system_review_detail.sql | 0 |  | 0.0 |  |
| 1113 | sql | migrations/20261012_200000_add_extraction_attempts_thought_summaries.sql | 0 |  | 0.0 |  |
| 1116 | sql | migrations/20261012_210000_add_tcg_distribution_targets_review_sheet_name.sql | 0 |  | 0.0 |  |
| 1119 | sql | migrations/20261013_100000_repoint_companies_sales_rep_to_users.sql | 0 |  | 0.0 |  |
| 1122 | sql | migrations/20261013_110000_repoint_person_columns_to_users.sql | 0 |  | 0.0 |  |
| 1125 | sql | migrations/20261013_120000_staff_user_id_not_null.sql | 0 |  | 0.0 |  |
| 1128 | sql | migrations/20261013_130000_staff_role_id_nullable.sql | 0 |  | 0.0 |  |
| 1131 | sql | migrations/20261013_140000_add_analysis_results_ship_ja_ship_en.sql | 0 |  | 0.0 |  |
| 1134 | sql | migrations/20261013_140100_add_tcg_note_master_label_template_en.sql | 0 |  | 0.0 |  |
| 1137 | sql | migrations/20261013_150000_staff_email_from_users.sql | 0 |  | 0.0 |  |
| 1140 | sql | migrations/20261013_160000_add_self_hosted_auth_tables.sql | 0 |  | 0.0 |  |
| 1143 | sql | migrations/20261013_180000_drop_extraction_shadow_tables.sql | 0 |  | 0.0 |  |
| 1146 | sql | migrations/20261015_090000_add_leads_assignment_opened_at.sql | 0 |  | 0.0 |  |
| 1148 | sql | migrations/20261015_130000_add_permissions_rls.sql | 0 |  | 0.0 |  |
| 1149 | sql | migrations/20261016_010000_add_google_config_rls.sql | 0 |  | 0.0 |  |
| 1150 | sql | migrations/20261016_020000_add_suppliers_rls.sql | 0 |  | 0.0 |  |
| 1153 | sql | migrations/20261016_150000_add_viewer_accounts.sql | 0 |  | 0.0 |  |
| 1156 | sql | migrations/20261016_100000_create_ops_incident_tables.sql | 0 |  | 0.0 |  |
| 1158 | sql | migrations/20261016_160000_add_paypal_regtoken_write_rls.sql | 0 |  | 0.0 |  |
| 1160 | sql | migrations/20261016_170000_add_tenants_write_rls.sql | 0 |  | 0.0 |  |
| 1162 | sql | migrations/20261016_180000_add_users_write_rls.sql | 0 |  | 0.0 |  |
| 1165 | sql | migrations/20261016_190000_create_product_blank_confirmations.sql | 0 |  | 0.0 |  |
| 1168 | sql | migrations/20261017_100000_add_viewer_discord_config.sql | 0 |  | 0.0 |  |
| 1170 | sql | migrations/20261017_120000_line_conditions_value_rank.sql | 0 |  | 0.0 |  |
| 1172 | sql | migrations/20261017_130000_create_ai_reader_role.sql | 0 |  | 0.0 |  |
| 1174 | sql | migrations/20261017_140000_create_analysis_error_report_tables.sql | 0 |  | 0.0 |  |
| 1176 | sql | migrations/20261017_210000_drop_products_type_master_id.sql | 0 |  | 0.0 |  |
| 1178 | sql | migrations/20261017_220000_add_analysis_results_bundle_size.sql | 0 |  | 0.0 |  |
| 1180 | sql | migrations/20261017_220100_add_line_units_display_names.sql | 0 |  | 0.0 |  |
| 1182 | sql | migrations/20261018_100000_create_product_packagings.sql | 0 |  | 0.0 |  |
| 1184 | sql | migrations/20261018_110000_drop_products_tcg_type.sql | 0 |  | 0.0 |  |
| 1185 | sql | migrations/20261019_100000_line_conditions_value_group_add_promo_single.sql | 0 |  | 0.0 |  |
| 1187 | sql | migrations/20261020_100000_line_conditions_value_group_add_booklet.sql | 0 |  | 0.0 |  |
| 1189 | sql | migrations/20261020_110000_line_conditions_value_group_add_supply.sql | 0 |  | 0.0 |  |
| 1191 | sql | migrations/20261020_120000_create_viewer_message_templates.sql | 0 |  | 0.0 |  |
| 1193 | sql | migrations/20261022_100000_products_format_in_work_fk.sql | 0 |  | 0.0 |  |
| 1195 | sql | migrations/20261022_110000_product_formats_drop_type_master_id.sql | 0 |  | 0.0 |  |
| 1197 | sql | migrations/20261023_180000_create_accuracy_gold.sql | 0 |  | 0.0 |  |
| 1199 | sql | migrations/20261024_100000_create_ai_cloud_meta.sql | 0 |  | 0.0 |  |
| 1201 | sql | migrations/20261024_100100_create_ai_reader_cloud_role.sql | 0 |  | 0.0 |  |
| 1203 | sql | migrations/20261031_200000_add_passkey_enroll_prompt_skips.sql | 0 |  | 0.0 |  |
| 1205 | sql | migrations/20261031_210000_create_ops_case.sql | 0 |  | 0.1 |  |
| 1207 | sql | migrations/20261101_120000_enable_secretary_chat_tenant4.sql | 0 |  | 0.0 |  |
| 1209 | sql | migrations/20261101_130000_add_new_device_approval.sql | 3 |  | 0.0 | ERROR:  relation "public.auth_events" does not exist |
| 1211 | sql | migrations/20261102_090000_add_user_push_subscriptions.sql | 0 |  | 0.0 |  |
| 1213 | sql | migrations/20261103_120000_create_ai_job_assignments.sql | 0 |  | 0.0 |  |
| 1215 | sql | migrations/20261103_150000_create_user_notices.sql | 0 |  | 0.0 |  |
| 1217 | sql | migrations/20261103_200000_add_google_calendar_import_sync.sql | 0 |  | 0.0 |  |
| 1219 | sql | migrations/20261104_220000_add_tcg_distribution_targets_viewer_account_id.sql | 0 |  | 0.0 |  |
| 1221 | sql | migrations/20261105_100000_tenant_discord_config_purpose.sql | 0 |  | 0.0 |  |
| 1223 | sql | migrations/20261105_120000_create_viewer_billing_profiles.sql | 0 |  | 0.0 |  |
| 1225 | sql | migrations/20261106_100000_tenant_discord_config_purpose_pk.sql | 0 |  | 0.0 |  |
| 1227 | sql | migrations/20261104_161223_add_calendar_events_meet_url.sql | 0 |  | 0.0 |  |
| 1229 | sql | migrations/20261106_120000_create_discord_server_snapshot_tables.sql | 0 |  | 0.0 |  |
| 1231 | sql | migrations/20261106_140000_add_login_request_admin_requested_at.sql | 0 |  | 0.0 |  |
| 1233 | sql | migrations/20261106_150000_add_discord_role_link_tables.sql | 0 |  | 0.0 |  |
| 1235 | sql | migrations/20261106_190000_create_public_channel_masters.sql | 0 |  | 0.0 |  |
| 1237 | sql | migrations/20261106_210000_add_notification_channels_blueprint_key.sql | 0 |  | 0.0 |  |
| 1239 | sql | migrations/20261107_100000_add_inventory_movements_rls.sql | 0 |  | 0.0 |  |
| 1241 | sql | migrations/20261107_110000_add_discord_server_records_rls.sql | 0 |  | 0.0 |  |
| 1243 | sql | migrations/20261107_120000_create_staff_join_invites.sql | 0 |  | 0.0 |  |
| 1245 | sql | migrations/20261107_130000_add_users_password_must_change.sql | 0 |  | 0.0 |  |
| 1247 | sql | migrations/20261107_140000_add_discord_config_rls.sql | 0 |  | 0.0 |  |
| 1249 | sql | migrations/20261107_150000_add_google_webhook_subscriptions_rls.sql | 0 |  | 0.0 |  |
| 1251 | sql | migrations/20261107_160000_add_tenant_budget_settings_rls.sql | 0 |  | 0.0 |  |
| 1253 | sql | migrations/20261108_100000_rebuild_company_stats_on_meta_messages.sql | 0 |  | 0.0 |  |
| 1255 | sql | migrations/20261109_200000_drop_staff_firebase_uid.sql | 0 |  | 0.0 |  |
| 1257 | sql | migrations/20261111_120000_add_codex_secretary_choices.sql | 0 |  | 0.0 |  |
| 1259 | sql | migrations/20261112_120000_create_public_customer_statuses.sql | 0 |  | 0.0 |  |
| 1261 | sql | migrations/20261112_130000_add_viewer_contracting_status.sql | 0 |  | 0.0 |  |
| 1263 | sql | migrations/20261112_140000_customer_status_fk.sql | 0 |  | 0.0 |  |
| 1265 | sql | migrations/20261112_150000_create_viewer_contract_public_tables.sql | 0 |  | 0.0 |  |
| 1267 | sql | migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql | 0 |  | 0.0 |  |
| 1269 | sql | migrations/20261112_170000_add_calendar_events_recurrence.sql | 0 |  | 0.0 |  |
| 1271 | sql | migrations/20261113_100000_create_secretary_rules.sql | 0 |  | 0.0 |  |
| 1274 | sql | migrations/20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql | 0 |  | 0.0 |  |
| 1276 | sql | migrations/20261113_200000_add_ops_case_report_kind.sql | 0 |  | 0.0 |  |
| 1279 | sql | migrations/20261115_100000_add_payment_method_versioning.sql | 0 |  | 0.0 |  |
| trap1 | trap | migrations/20261017_130100_create_ai_ro_views.sql | 0 |  | 0.2 |  |
| trap2 | trap | migrations/20261024_100300_create_ai_cloud_views.sql | 0 |  | 0.3 |  |
| trap3 | trap | SELECT ops_case.grant_unmask_owner(); | 0 |  | 1.1 |  |

（trap の行の「登録の行」は `trap1`〜`trap3`。本体の終わりの手順 `run_all_migrations.sh:230-273` の順: (1) `create_ai_ro_views.sql` (2) `create_ai_cloud_views.sql` (3) `SELECT ops_case.grant_unmask_owner();`。VERBOSITY=terse・statement_timeout=30s を付けて流した。）

## `q1-shape/` の9ファイルの合計（`prod003/` と同じ数え方）

| 種類 | 本番 003 | ひな形の直後（`p01-shape/after-bootstrap/`） | 全件の後（`q1-shape/`） |
|---|---|---|---|
| 表 | 79 | 53 | 75 |
| 列 | 1006 | 641 | 973 |
| 索引 | 256 | 140 | 235 |
| 制約 | 264 | 181 | 254 |
| トリガ | 28 | 18 | 29 |
| 方針 | 64 | 42 | 61 |
| 連番 | 72 | 44 | 66 |
| 関数 | 15 | 5 | 15 |
| ビュー | 2 | 1 | 2 |

（数え方: 表＝`table_flags` の行数、列・索引・制約・トリガ・方針＝2列目の和、連番・関数・ビュー＝行数。）

## 補足（偏差）
- `run_sql` は `psql -v ON_ERROR_STOP=1` にファイルを標準入力で渡した。`PGOPTIONS=-c lock_timeout=1s`・`PGHOST=localhost`・`PGPORT=55432`・`PGUSER=jarvis`・`PGDATABASE=q1_db`。ロック競合の流し直し（`SQL_RETRY_*`）と `sleep` は再現していない（単独の DB のため）。
- 各本の出力の全文は `/tmp/recon/out/q1-logs/`（commit しない）。

