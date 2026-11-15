---
mode: handoff
---
# 前調査 5-0b：共通（手順2〜5・試験のファイル全文・比べる台本の全文）

本報告はカード 前調査 5-0b の実行結果である。

- 読んだ commit: `d0f0a52544167df5e255cee6b00c50704474bd96`（`release/migration-skip-applied-5-0`。手順2で `git rev-parse HEAD` と `git rev-parse origin/release/migration-skip-applied-5-0` が同じ値だった）
- 作業場所: `/root/worktrees/salesanchor/release-migration-skip-applied-5-0`
- 注: カードは各 md の先頭に試験のファイルの全文を貼るよう指示しているが、4項目で同じファイル1本を使ったため、全文は本ファイルに1回だけ貼り、`p01.md`・`p08.md`・`p09.md`・`p10-trial.md` の先頭からここを指す（偏差として報告に書く）。

## 手順2〜5の記録

### 手順2（作業場所）
```
git fetch origin
bash scripts/new-worktree.sh release/migration-skip-applied-5-0
cd /root/worktrees/salesanchor/release-migration-skip-applied-5-0 && git switch -C release/migration-skip-applied-5-0 origin/release/migration-skip-applied-5-0
git rev-parse HEAD            -> d0f0a52544167df5e255cee6b00c50704474bd96
git rev-parse origin/release/migration-skip-applied-5-0 -> d0f0a52544167df5e255cee6b00c50704474bd96
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
（カードの「`gh auth switch` で落ちるのは前と同じ。記録して続ける」に従い、続行した。）

### 手順4（使い捨ての PostgreSQL 16）
- `ls /usr/lib/postgresql/` → `16`
- クラウドの実行者が root のため、`initdb` は `postgres` 利用者（OS）で流した: `initdb -D <dir> -U postgres --auth=trust`、`pg_ctl -D <dir> -o "-p 55432 -k /tmp/recon" -l <log> start`。
- `postgres --version` → `postgres (PostgreSQL) 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)`
- 接続先は `localhost:55432` だけ。
- クラスタは3回作り直した（削除の命令は使えないので、古い `pgdata`・`pgdata2` はそのまま残し、止めて、新しい `pgdata3` を同じ 55432 で立てた）。
  - `pgdata`（1回目）: P1・P9 は通った。P8 の step 9 が `ai_unmask_owner already exists with unexpected attributes` で落ちた（下の「手順5の補足」）。
  - `pgdata2`（2回目）: 手順5の役を直して全項目をやり直した。ただし形の出力が本番の読み取りの出力と書式が違った（値の中の改行を `\n` の2文字にしていなかった）ので、比べられなかった。
  - `pgdata3`（3回目・本報告の数字はすべてこれ）: 書式を直して `p01`→`p08`→`p09`→`p10` を1回の pytest で通した（`4 passed in 26.06s`）。

### 手順4b（Python 3.12 の venv）
```
cd <作業場所>/backend && python3.12 -m venv /tmp/recon/venv
/tmp/recon/venv/bin/pip install -r requirements.txt -r requirements-dev.txt > /tmp/recon/pip.txt 2>&1
tail -5 /tmp/recon/pip.txt   -> 末尾は "Successfully installed CacheControl-0.14.4 Pillow-12.3.0 ... yarl-1.25.1"（要約: 全部入った）
/tmp/recon/venv/bin/pip check -> No broken requirements found.
```
python は `/tmp/recon/venv/bin/python`（Python 3.12.3）だけを使った。

### 手順5（利用者。試験の中で作った）
`.github/workflows/test.yml:204` の `CREATE ROLE salesanchor_app WITH LOGIN PASSWORD 'apppass' NOSUPERUSER NOCREATEDB NOBYPASSRLS;` を引用して同じに作った。`migration-test.yml` の `migration-full-dryrun` は役を作らない（`DATABASE_URL` は `postgresql://jarvis:testpass@localhost:5432/jarvis_db`・`PGPASSWORD: testpass`。:1475-1477）。
- `jarvis`: SUPERUSER・LOGIN・パスワード `testpass`
- `salesanchor_app`: LOGIN・NOSUPERUSER・NOCREATEDB・NOBYPASSRLS（パスワード `apppass`）
- `ai_unmask_owner`: NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION BYPASSRLS
- 試験が出した確認: `ROLES [('ai_unmask_owner', False, False), ('jarvis', True, True), ('salesanchor_app', False, True)]`（役名, rolsuper, rolcanlogin）

#### 手順5の補足（カードの指示から変えた所と、その理由）
- カードの指示どおり `ai_unmask_owner` を属性なしの NOLOGIN で作った1回目は、P8 の step 9（全件ドライラン）の `migrations/20261031_210000_create_ops_case.sql:189` で `ERROR:  ai_unmask_owner already exists with unexpected attributes; stop and report` になった（`:180-189` は、同名の役があるとき `NOT r.rolbypassrls` なら止める）。1周目・2周目とも 377 成功・1 失敗。
- 本物の CI は役を先に作らず、この移行が `CREATE ROLE ai_unmask_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION BYPASSRLS` で作る（`:180-182`）。そのため2回目以降は、移行が求める属性（BYPASSRLS つき）で作った。これはカードの「CI がほかにも利用者を作っていたら」の範囲を超えて、役の属性を移行に合わせた変更である。
- 1回目の失敗の記録（step の表と終わりの番号）は `p08.md` の「1回目（役の属性が違った回）」に残した。

## 試験のファイル `/tmp/recon/test_5_0b.py` の全文（commit しない。最終版）

```python
"""前調査 5-0b の試験（使い捨ての PostgreSQL 16 / localhost:55432 だけにつなぐ）。

P1 / P8 / P9 / P10 を1つのファイルにまとめる。結果は /tmp/recon/out/ に書く。
流し方: cd backend && /tmp/recon/venv/bin/python -m pytest /tmp/recon/test_5_0b.py -x -s -k <p01|p08|p09|p10>
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
import yaml

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ.setdefault("ADMIN_DATABASE_URL", os.environ["DATABASE_URL"])

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

ROOT = Path("/root/worktrees/salesanchor/release-migration-skip-applied-5-0")
OUT = Path("/tmp/recon/out")
OUT.mkdir(parents=True, exist_ok=True)
HOST = "localhost"
PORT = 55432
PGBIN = "/usr/lib/postgresql/16/bin"
VENV_BIN = "/tmp/recon/venv/bin"


def dsn(db: str, user: str = "jarvis") -> str:
    return f"host={HOST} port={PORT} dbname={db} user={user}"


def sa_url(db: str) -> str:
    return f"postgresql+asyncpg://jarvis:testpass@{HOST}:{PORT}/{db}"


# ---------------------------------------------------------------- 形の9本の問い合わせ（prod003/README.md と同じ）
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
    # 本番の読み取りの出力（prod003/）は、値の中の改行を文字どおりの「\n」で持つので、同じにする
    return str(v).replace("\n", "\\n").replace("\t", "\\t")


def _write_shape(outdir: Path, schema: str, results: dict[str, list]) -> dict[str, int]:
    outdir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, rows in results.items():
        lines = ["\t".join(HEADERS[name])]
        for r in rows:
            lines.append("\t".join(_cell(x) for x in r))
        (outdir / f"{name}.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
        counts[name] = len(rows)
    return counts


def shape_sync(db: str, schema: str, outdir: Path) -> dict[str, int]:
    conn = psycopg2.connect(dsn(db))
    try:
        cur = conn.cursor()
        res = {}
        for name, q in SHAPE_QUERIES.items():
            cur.execute(q.replace("tenant_003", schema))
            res[name] = cur.fetchall()
    finally:
        conn.close()
    return _write_shape(outdir, schema, res)


async def shape_async(conn, schema: str, outdir: Path) -> dict[str, int]:
    res = {}
    for name, q in SHAPE_QUERIES.items():
        r = await conn.exec_driver_sql(q.replace("tenant_003", schema))
        res[name] = [tuple(x) for x in r.fetchall()]
    return _write_shape(outdir, schema, res)


# ---------------------------------------------------------------- 共通: 利用者・DB
def admin_exec(sql: str, db: str = "postgres", user: str = "postgres") -> None:
    conn = psycopg2.connect(dsn(db, user))
    conn.autocommit = True
    try:
        conn.cursor().execute(sql)
    finally:
        conn.close()


def admin_scalar(sql: str, db: str = "postgres", user: str = "jarvis"):
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
    """手順5: jarvis（SUPERUSER・LOGIN・testpass）・salesanchor_app（LOGIN）・ai_unmask_owner（NOLOGIN）。"""
    conn = psycopg2.connect(dsn("postgres", "postgres"))
    conn.autocommit = True
    cur = conn.cursor()
    stmts = [
        ("jarvis", "CREATE ROLE jarvis WITH SUPERUSER LOGIN PASSWORD 'testpass'"),
        ("salesanchor_app", "CREATE ROLE salesanchor_app WITH LOGIN PASSWORD 'apppass' NOSUPERUSER NOCREATEDB NOBYPASSRLS"),
        # 20261031_210000_create_ops_case.sql :180-189 が求める属性（NOLOGIN・BYPASSRLS・ほかは無し）に合わせる
        ("ai_unmask_owner", "CREATE ROLE ai_unmask_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION BYPASSRLS"),
    ]
    for rolname, stmt in stmts:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (rolname,))
        if cur.fetchone() is None:
            cur.execute(stmt)
    cur.execute("SELECT rolname, rolsuper, rolcanlogin FROM pg_roles WHERE rolname IN ('jarvis','salesanchor_app','ai_unmask_owner') ORDER BY 1")
    print("ROLES", cur.fetchall())
    conn.close()


def create_db(name: str, template: str | None = None) -> None:
    conn = psycopg2.connect(dsn("postgres"))
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,))
    if cur.fetchone() is not None:
        raise RuntimeError(f"DB {name} は既にある")
    cur.execute(f'CREATE DATABASE {name}' + (f" TEMPLATE {template}" if template else ""))
    conn.close()


# ================================================================ P1
def test_p01_template_tenant():
    create_db("p1_db")
    from tests import rls_bootstrap as rb  # 作業場所の backend/tests（変えない）

    outdir_create = OUT / "p01-shape" / "after-create"
    outdir_boot = OUT / "p01-shape" / "after-bootstrap"
    captured = {}
    original = rb.create_tenant_schema

    async def wrapped(conn, tenant_id, admin_db=None):
        schema = await original(conn, tenant_id, admin_db=admin_db)
        captured["counts"] = await shape_async(conn, schema, outdir_create)
        return schema

    async def run():
        eng = create_async_engine(sa_url("p1_db"), echo=False)
        try:
            # 前準備の順は backend/tests/test_inventory_aggregated.py:164（bootstrap_public_products）と
            # rls_bootstrap.py:111-149（ensure_product_packagings）に合わせる
            await rb.bootstrap_public_products(eng)
            await rb.ensure_product_packagings(eng)
            rb.create_tenant_schema = wrapped
            try:
                schema = await rb.bootstrap_tenant_schema(eng, 3)
            finally:
                rb.create_tenant_schema = original
            assert schema == "tenant_003"
        finally:
            await eng.dispose()

    asyncio.run(run())
    c2 = shape_sync("p1_db", "tenant_003", outdir_boot)
    print("P1 after-create counts", captured.get("counts"))
    print("P1 after-bootstrap counts", c2)
    # 連番・索引・制約の有無は diff 台本と md で ○× にする


# ================================================================ P8
def load_job_steps():
    wf = yaml.safe_load((ROOT / ".github/workflows/migration-test.yml").read_text(encoding="utf-8"))
    job = wf["jobs"]["migration-full-dryrun"]
    return job, job["steps"]


STEP_NAMES = [
    "ベーススキーマを作成（全件ドライラン用）",
    "Sprint 1 マイグレーションを適用（タイムスタンプ SQL の前提条件）",
    "suppliers.tenant_id を最小定義で追加（本番 phase2 相当）",
    "廃止列前提検出（leads.source ガードなし参照を禁止）",
    "ADR-119 バックフィルスクリプトを source 廃止済みスキーマで実行",
    "報告用 DB を作る（ここまでの状態のコピー。全件ドライラン（報告のみ）が使う）",
    "1周目：全 run_sql migration を順次実行（新規適用）",
    "2周目：全 run_sql migration を再実行（冪等性チェック＝再デプロイ安全性）",
    "全件ドライラン（失敗したら止める）：登録された全ファイル − 除外一覧",
]


def yml_line(name: str) -> int:
    for i, ln in enumerate((ROOT / ".github/workflows/migration-test.yml").read_text(encoding="utf-8").splitlines(), 1):
        if i >= 1453 and ln.strip() == f"- name: {name}":
            return i
    return -1


ANALYSIS_TABLES = [
    "analysis_execution_profile_versions", "analysis_instruction_versions", "analysis_policies",
    "analysis_policy_revisions", "analysis_revision_rules", "analysis_rule_run_results", "analysis_rule_runs",
    "analysis_rule_versions", "analysis_rule_words", "analysis_rules", "analysis_suite_cases",
    "analysis_test_case_versions", "analysis_test_suites",
]


def count_analysis(db: str) -> tuple[int, list[str]]:
    rows = admin_scalar(
        "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='tenant_001' AND c.relkind='r' AND c.relname = ANY(ARRAY['" + "','".join(ANALYSIS_TABLES) + "']) ORDER BY 1",
        db=db,
    )
    names = [r[0] for r in rows]
    return len(names), names


def ci_env(extra: dict | None = None) -> dict:
    env = dict(os.environ)
    env["PATH"] = f"{VENV_BIN}:{PGBIN}:/usr/bin:/bin"
    env.update({"PGHOST": HOST, "PGPORT": str(PORT), "PGUSER": "jarvis", "PGPASSWORD": "testpass",
                "DATABASE_URL": f"postgresql://jarvis:testpass@{HOST}:{PORT}/jarvis_db"})
    if extra:
        env.update(extra)
    return env


def test_p08_ci_dryrun():
    create_db("jarvis_db")
    job, steps = load_job_steps()
    by_name = {s.get("name"): s for s in steps}
    table = []
    logdir = OUT / "p08-steps"
    logdir.mkdir(parents=True, exist_ok=True)
    failed = False
    for idx, name in enumerate(STEP_NAMES, 1):
        s = by_name[name]
        stepenv = {k: str(v).replace("${{ github.workspace }}", str(ROOT)) for k, v in (s.get("env") or {}).items()}
        t0 = time.time()
        p = subprocess.run(["bash", "-e", "-c", s["run"]], cwd=ROOT, env=ci_env(stepenv),
                           capture_output=True, text=True, timeout=2400)
        secs = time.time() - t0
        (logdir / f"{idx:02d}.log").write_text(p.stdout + "\n--- stderr ---\n" + p.stderr, encoding="utf-8")
        table.append((idx, yml_line(name), name, p.returncode, round(secs, 1)))
        print("P8 STEP", idx, yml_line(name), name, "rc=", p.returncode, f"{secs:.1f}s")
        if p.returncode != 0:
            print("P8 STEP FAILED tail:\n", (p.stdout + p.stderr)[-3000:])
            failed = True
            break
    (OUT / "p08-steps.tsv").write_text("\n".join("\t".join(map(str, r)) for r in table) + "\n", encoding="utf-8")
    # 形は途中で落ちても取れるところまで取る
    dbs = [r[0] for r in admin_scalar("SELECT datname FROM pg_database")]
    if "jarvis_report" in dbs:
        has = admin_scalar("SELECT 1 FROM pg_namespace WHERE nspname='tenant_001'", db="jarvis_report")
        if has:
            print("P8 shape counts", shape_sync("jarvis_report", "tenant_001", OUT / "p08-shape"))
        before_n, before_names = count_analysis("jarvis_report")
        print("P8 analysis tables before rerun:", before_n, before_names)
        mig = "migrations/20260917_000000_create_analysis_rule_tables.sql"
        t0 = time.time()
        p = subprocess.run(["psql", "-d", "jarvis_report", "-v", "ON_ERROR_STOP=1", "-f", str(ROOT / mig)],
                           cwd=ROOT, env=ci_env(), capture_output=True, text=True, timeout=600)
        print("P8 rerun", mig, "rc=", p.returncode, f"{time.time()-t0:.1f}s")
        print("P8 rerun output:", (p.stdout + p.stderr)[-1500:])
        after_n, after_names = count_analysis("jarvis_report")
        print("P8 analysis tables after rerun:", after_n, after_names)
        (OUT / "p08-analysis13.txt").write_text(
            f"before\t{before_n}\t{','.join(before_names)}\nrerun_rc\t{p.returncode}\nafter\t{after_n}\t{','.join(after_names)}\n"
            + "rerun_output\n" + (p.stdout + p.stderr), encoding="utf-8")
    assert not failed, "P8 は途中で落ちた（記録は /tmp/recon/out/p08-steps.tsv）"


# ================================================================ P9
def test_p09_commit_inside_transaction():
    create_db("p9_db")
    admin_exec("CREATE TABLE public.google_webhook_subscriptions (id serial PRIMARY KEY, tenant_id integer)", db="p9_db", user="jarvis")
    target = ROOT / "migrations/20261107_150000_add_google_webhook_subscriptions_rls.sql"
    body = target.read_text(encoding="utf-8")
    log: list[str] = []
    result: dict = {}

    async def run():
        eng = create_async_engine(sa_url("p9_db"), echo=False)
        try:
            try:
                async with eng.begin() as conn:
                    raw = await conn.get_raw_connection()
                    raw.driver_connection.add_log_listener(lambda c, m: log.append(f"{getattr(m,'severity','?')}: {getattr(m,'message',m)}"))
                    await conn.execute(text("CREATE TABLE public.p9_probe_a (id int)"))
                    await raw.driver_connection.execute(body)
                    await conn.execute(text("CREATE TABLE public.p9_probe_b (id int)"))
                    await conn.execute(text("SELECT 1/0"))
            except Exception as e:  # 取引の枠が巻き戻しを試みる
                result["error"] = f"{type(e).__name__}: {str(e).splitlines()[0]}"
        finally:
            await eng.dispose()

    asyncio.run(run())
    rows = admin_scalar(
        "SELECT (SELECT count(*) FROM pg_class WHERE relname='p9_probe_a' AND relnamespace='public'::regnamespace),"
        "(SELECT count(*) FROM pg_class WHERE relname='p9_probe_b' AND relnamespace='public'::regnamespace),"
        "(SELECT relrowsecurity::text||'/'||relforcerowsecurity::text FROM pg_class WHERE relname='google_webhook_subscriptions' AND relnamespace='public'::regnamespace),"
        "(SELECT string_agg(polname, ',' ORDER BY polname) FROM pg_policy WHERE polrelid='public.google_webhook_subscriptions'::regclass)",
        db="p9_db",
    )
    out = f"error\t{result.get('error')}\nnotices\t{log}\nprobe_a,probe_b,rls/force,policies\t{rows}\n"
    (OUT / "p09-result.txt").write_text(out, encoding="utf-8")
    print("P9", out)


# ================================================================ P10
def run_py_entries():
    out = []
    for i, ln in enumerate((ROOT / "scripts/run_all_migrations.sh").read_text(encoding="utf-8").splitlines(), 1):
        m = re.match(r"^run_py\s+(\S+)(.*)$", ln)
        if m:
            out.append((i, m.group(1), m.group(2).strip()))
    return out


def test_p10_run_py():
    create_db("p10_db", template="jarvis_report")
    entries = run_py_entries()
    assert len(entries) == 26, len(entries)
    backend = ROOT / "backend"
    rows = []
    base_env = ci_env({"DATABASE_URL": f"postgresql://jarvis:testpass@{HOST}:{PORT}/p10_db", "MIGRATION_LOCK_TIMEOUT": "1s"})
    base_env.pop("PYTHONPATH", None)
    logdir = OUT / "p10-logs"
    logdir.mkdir(parents=True, exist_ok=True)
    for ln, script, extra in entries:
        env = dict(base_env)
        m = re.match(r"-e\s+(\w+)=(\S+)", extra)
        if m:
            env[m.group(1)] = m.group(2)
        cmd = [f"{VENV_BIN}/python", str(ROOT / "scripts/migration_py_entry.py"), str(ROOT / script)]
        t0 = time.time()
        p1 = subprocess.run(cmd, cwd=backend, env=env, capture_output=True, text=True, timeout=900)
        s1 = time.time() - t0
        (logdir / f"{ln}-1.log").write_text(p1.stdout + "\n--- stderr ---\n" + p1.stderr, encoding="utf-8")
        rc2 = ""
        first = ""
        if p1.returncode != 0:
            errtxt = (p1.stderr.strip().splitlines() or [""])
            first = errtxt[-1]
            env2 = dict(env)
            env2["PYTHONPATH"] = str(backend)
            p2 = subprocess.run(cmd, cwd=backend, env=env2, capture_output=True, text=True, timeout=900)
            rc2 = str(p2.returncode)
            (logdir / f"{ln}-2.log").write_text(p2.stdout + "\n--- stderr ---\n" + p2.stderr, encoding="utf-8")
            if p2.returncode != 0:
                first2 = (p2.stderr.strip().splitlines() or [""])[-1]
                first = first + "  ||  2回目: " + first2
        rows.append((ln, script, p1.returncode, rc2, first, round(s1, 1)))
        print("P10", ln, script, "rc1=", p1.returncode, "rc2=", rc2, "|", first[:160])
    (OUT / "p10-result.tsv").write_text(
        "line\tscript\trc1\trc2\tfirst_error_line\tsec1\n" + "\n".join("\t".join(map(str, r)) for r in rows) + "\n",
        encoding="utf-8")
```

## 比べる台本 `/tmp/recon/diff_shape.py` の全文

```python
"""形の比べ台本（DB にはつながない）。

使い方: python -I diff_shape.py <本番のフォルダ> <使い捨てのフォルダ> [--tables-file <表名を1行ずつ書いたファイル>]
出力: markdown（差の全件の表 → 種類ごとの件数の表）。
--tables-file を付けると、その表に属する差に「印=T」を付け、印の無い差だけの表も出す。
"""
import re
import sys
from pathlib import Path

SEP = " ;; "


def read_tsv(path: Path):
    lines = path.read_text(encoding="utf-8").split("\n")
    rows = [ln.split("\t") for ln in lines[1:] if ln != ""]
    return rows


def parse(folder: Path):
    """種類 -> {キー: (表示名, 表, 中身)}"""
    out = {}
    # 列
    d = {}
    for r in read_tsv(folder / "columns.tsv"):
        table = r[0]
        for item in r[2].split(SEP):
            name = item.split("|")[0]
            d[(table, name)] = (f"{table}.{name}", table, item)
    out["列"] = d
    # 索引
    d = {}
    for r in read_tsv(folder / "indexes.tsv"):
        table = r[0]
        for item in r[2].split(SEP):
            m = re.search(r"INDEX (\S+) ON", item)
            name = m.group(1)
            d[name] = (name, table, item)
    out["索引"] = d
    # 制約
    d = {}
    for r in read_tsv(folder / "constraints.tsv"):
        table = r[0]
        for item in r[2].split(SEP):
            name = item.split("|")[0]
            d[(table, name)] = (f"{name} (表 {table})", table, item)
    out["制約"] = d
    # トリガ
    d = {}
    for r in read_tsv(folder / "triggers.tsv"):
        table = r[0]
        for item in r[2].split(SEP):
            m = re.search(r"TRIGGER (\S+) ", item)
            name = m.group(1)
            d[(table, name)] = (f"{name} (表 {table})", table, item)
    out["トリガ"] = d
    # 方針
    d = {}
    for r in read_tsv(folder / "policies.tsv"):
        table = r[0]
        for item in r[2].split(SEP):
            name = item.split("|")[0]
            d[(table, name)] = (f"{table}.{name}", table, item)
    out["方針"] = d
    # 表の印
    d = {}
    for r in read_tsv(folder / "table_flags.tsv"):
        d[r[0]] = (r[0], r[0], "|".join(r[1:]))
    out["表の印"] = d
    # 連番
    d = {}
    for r in read_tsv(folder / "sequences.tsv"):
        d[r[0]] = (r[0], None, "|".join(r[1:]))
    out["連番"] = d
    # 関数
    d = {}
    for r in read_tsv(folder / "functions.tsv"):
        key = f"{r[0]}({r[1]})"
        d[key] = (key, None, "|".join(r[2:]))
    out["関数"] = d
    # ビュー
    d = {}
    for r in read_tsv(folder / "views.tsv"):
        d[r[0]] = (r[0], None, "|".join(r[1:]))
    out["ビュー"] = d
    return out


def cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def main():
    args = sys.argv[1:]
    tables = set()
    if "--tables-file" in args:
        i = args.index("--tables-file")
        tables = {ln.strip() for ln in Path(args[i + 1]).read_text(encoding="utf-8").splitlines() if ln.strip()}
        del args[i:i + 2]
    prod = parse(Path(args[0]))
    disp = parse(Path(args[1]))
    kinds = list(prod.keys())

    def table_of(kind, key, entry):
        t = entry[1]
        if t is None and kind == "連番":
            name = entry[0]
            for tb in tables:
                if name.startswith(tb + "_"):
                    return tb
        return t

    diffs = []  # (種類, 分け方, 名前, 本番の中身, 使い捨ての中身, 印)
    counts = {}
    for kind in kinds:
        p, d = prod[kind], disp[kind]
        only_p = only_d = diff = 0
        for key in sorted(set(p) | set(d), key=lambda k: str(k)):
            pe, de = p.get(key), d.get(key)
            e = pe or de
            mark = "T" if (tables and table_of(kind, key, e) in tables) else ""
            if pe and not de:
                only_p += 1
                diffs.append((kind, "本番だけ", e[0], pe[2], "", mark))
            elif de and not pe:
                only_d += 1
                diffs.append((kind, "使い捨てだけ", e[0], "", de[2], mark))
            elif pe[2] != de[2]:
                diff += 1
                diffs.append((kind, "中身が違う", e[0], pe[2], de[2], mark))
        counts[kind] = (len(p), len(d), only_p, only_d, diff)

    def emit(rows, title):
        print(f"\n## {title}（{len(rows)}件）\n")
        print("| 種類 | 分け方 | 名前 | 本番の中身 | 使い捨ての中身 | 印 |")
        print("|---|---|---|---|---|---|")
        for r in rows:
            print("| " + " | ".join(cell(x) for x in r) + " |")

    emit(diffs, "差の全件")
    if tables:
        others = [r for r in diffs if r[5] != "T"]
        emit(others, "差のうち、指定した表に属さない物")
    print("\n## 種類ごとの件数\n")
    print("| 種類 | 本番の数 | 使い捨ての数 | 本番だけ | 使い捨てだけ | 中身が違う |")
    print("|---|---|---|---|---|---|")
    tot = [0] * 5
    for kind in kinds:
        c = counts[kind]
        print(f"| {kind} | " + " | ".join(str(x) for x in c) + " |")
        tot = [a + b for a, b in zip(tot, c)]
    print("| 合計 | " + " | ".join(str(x) for x in tot) + " |")
    if tables:
        print("\n### 指定した表に属さない差の件数\n")
        print("| 種類 | 本番だけ | 使い捨てだけ | 中身が違う |")
        print("|---|---|---|---|")
        for kind in kinds:
            c = {"本番だけ": 0, "使い捨てだけ": 0, "中身が違う": 0}
            for r in diffs:
                if r[0] == kind and r[5] != "T":
                    c[r[1]] += 1
            print(f"| {kind} | {c['本番だけ']} | {c['使い捨てだけ']} | {c['中身が違う']} |")


if __name__ == "__main__":
    main()
```

## P8 の「30 表」の一覧 `/tmp/recon/tables30.txt`（`recon-5-0-opus-prod.md` §4-1 から写した）

```
analysis_results
analysis_run_snapshots
analysis_runs
audit_log
condition_aliases
conditions
extraction_attempts
extraction_items
extraction_jobs
import_job_messages
import_jobs
item_corrections
item_notes
product_exclude_keywords
product_search_keywords
products_logistics
source_messages
supplier_channels
tcg_distribution_settings
tcg_distribution_targets
tcg_major_categories
tcg_manufacturers
tcg_product_categories
tcg_product_import_jobs
tcg_product_import_rows
tcg_series
tenant_suppliers
unit_aliases
units
unparsed_lines
```
