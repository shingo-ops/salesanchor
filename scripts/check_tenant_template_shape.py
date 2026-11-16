#!/usr/bin/env python3
"""会社のひな形（create_tenant_schema）と、登録の移行を全件流した後の形の差を出す（段5 5-2・K5-2）。

流れ:
  1. 使い捨ての DB を作り、public の前準備をする（schema の無い会社の行は入れない）。
  2. create_tenant_schema で会社を 1 つ作る。
  3. 形を取る（前）。
  4. scripts/run_all_migrations.sh の登録の順に run_sql / run_py を全件流す。
  5. 形を取る（後）。
  6. 前と後の差を出す。差が 0 なら終了コード 0。1 件でもあれば全件を出して 1。

比べる物: 表・列（型・既定値・NOT NULL）・索引・制約（外部キーは指す表の置き場所つき）・
トリガ・RLS の印・方針・連番・関数・ビュー・権限（表と連番の relacl・スキーマの既定の権限）。

使い方（接続先は PGHOST・PGPORT・PGUSER・PGPASSWORD の環境変数。psql が PATH にあること）:
  PYTHONPATH=backend python3 scripts/check_tenant_template_shape.py [--db 名前] [--out-dir 出力先]

接続先は使い捨ての PostgreSQL だけにする。本番や共用の DB を指さない。
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import psycopg2

REPO_ROOT = Path(__file__).resolve().parents[1]
TENANT_ID = 3
SCHEMA = f"tenant_{TENANT_ID:03d}"
PLACEHOLDER = "{S}"

# 形の差の許す一覧。表単位（表の名前 1 つ）で書く。物ごとの名前は羅列しない。キーは表の名前、値は理由。
# 表に属する物（表・列・索引・制約・トリガ・方針・連番・権限）の差だけを許す。
# 入れてよいのは channel_masters の 1 表だけ（カード 5-2 第3版の決め1）。ほかを入れたくなったら止まって PO に聞く。
ALLOWED_TABLES: dict[str, str] = {
    "channel_masters": (
        "K6（docs/handoff/channel-master-shared/design.md）。登録の migrations/20260611_100000_create_channel_masters.sql が"
        "全会社に作るが、PR-C（ADR-1069）で消す予定。PR-C の合流後にこの行を外す"
    ),
}

# 前提が無くて落ちる移行（会社の形には関わらない）。キーは登録のファイル名、値は理由。
EXCLUDED_REGISTRY: dict[str, str] = {
    "migrations/072_add_retention_indexes.sql": "使い捨ての DB に public.auth_events が無い（会社の形に関わらない）",
    "migrations/20261101_130000_add_new_device_approval.sql": "使い捨ての DB に public.auth_events が無い（会社の形に関わらない）",
    "migrations/20260605_030000_create_salesanchor_app_role.sql": "本番の DB 名 jarvis_db を前提にしている（使い捨ての DB には無い。会社の形に関わらない）",
}

_REG_RE = re.compile(r"^run_(sql|py)[ \t]+(\S+)(.*)$")


def registry(path: Path | None = None) -> list[tuple[int, str, str, str]]:
    """scripts/run_all_migrations.sh の登録（行番号・種類・ファイル・残りの引数）。数え方は本体と同じ。"""
    path = path or (REPO_ROOT / "scripts/run_all_migrations.sh")
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = _REG_RE.match(line)
        if m:
            out.append((i, m.group(1), m.group(2), m.group(3).strip()))
    return out


# ───────────────────────── 形を取る ─────────────────────────

# 検索の順を空にして取る。会社の中も共用（public）も、必ず「置き場所.名前」で出る。
_SHAPE_SQL = {
    "表": """
        SELECT c.relname, c.relkind::text || '|rls=' || c.relrowsecurity::text || '|force=' || c.relforcerowsecurity::text
               || '|owner=' || pg_get_userbyid(c.relowner)
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %(s)s AND c.relkind IN ('r', 'p')
    """,
    "列": """
        SELECT c.relname || '.' || a.attname,
               format_type(a.atttypid, a.atttypmod) || '|notnull=' || a.attnotnull::text
               || '|default=' || coalesce(pg_get_expr(d.adbin, d.adrelid), '')
               || '|identity=' || a.attidentity::text || '|generated=' || a.attgenerated::text
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
        WHERE n.nspname = %(s)s AND c.relkind IN ('r', 'p') AND a.attnum > 0 AND NOT a.attisdropped
    """,
    "索引": """
        SELECT ic.relname, t.relname || '|' || pg_get_indexdef(i.indexrelid)
        FROM pg_index i
        JOIN pg_class ic ON ic.oid = i.indexrelid
        JOIN pg_class t ON t.oid = i.indrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = %(s)s
    """,
    "制約": """
        SELECT c.relname || '.' || k.conname,
               k.contype::text || '|' || pg_get_constraintdef(k.oid)
               || CASE WHEN k.contype = 'f'
                       THEN '|ref=' || rn.nspname || '.' || rc.relname ELSE '' END
        FROM pg_constraint k
        JOIN pg_class c ON c.oid = k.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        LEFT JOIN pg_class rc ON rc.oid = k.confrelid
        LEFT JOIN pg_namespace rn ON rn.oid = rc.relnamespace
        WHERE n.nspname = %(s)s
    """,
    "トリガ": """
        SELECT c.relname || '.' || g.tgname, pg_get_triggerdef(g.oid)
        FROM pg_trigger g
        JOIN pg_class c ON c.oid = g.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %(s)s AND NOT g.tgisinternal
    """,
    # 方針の条件は、public.current_tenant_id()（migrations/014 の包み関数）と
    # current_setting('app.tenant_id', true)::integer を同じ物として比べる（分け表 D1: 書き方だけ違い、同じ値を返す）。
    # ひな形は包み関数を前提にしない（会社を作る時点で public に無い環境がある）ので後者で書く。
    "方針": """
        SELECT c.relname || '.' || p.polname,
               p.polcmd::text || '|' || p.polpermissive::text || '|'
               || coalesce(array_to_string(ARRAY(
                    SELECT CASE WHEN r = 0 THEN 'public' ELSE pg_get_userbyid(r) END
                    FROM unnest(p.polroles) r ORDER BY 1), ','), '')
               || '|' || replace(coalesce(pg_get_expr(p.polqual, p.polrelid), ''),
                    'public.current_tenant_id()', '(current_setting(''app.tenant_id''::text, true))::integer')
               || '|' || replace(coalesce(pg_get_expr(p.polwithcheck, p.polrelid), ''),
                    'public.current_tenant_id()', '(current_setting(''app.tenant_id''::text, true))::integer')
        FROM pg_policy p
        JOIN pg_class c ON c.oid = p.polrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %(s)s
    """,
    "連番": """
        SELECT c.relname,
               format_type(s.seqtypid, NULL) || '|start=' || s.seqstart::text || '|inc=' || s.seqincrement::text
               || '|min=' || s.seqmin::text || '|max=' || s.seqmax::text || '|cycle=' || s.seqcycle::text
        FROM pg_sequence s
        JOIN pg_class c ON c.oid = s.seqrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %(s)s
    """,
    "関数": """
        SELECT p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')',
               md5(btrim(regexp_replace(p.prosrc, '[[:space:]]+', ' ', 'g'))) || '|secdef=' || p.prosecdef::text || '|vol=' || p.provolatile::text
        FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = %(s)s
    """,
    "ビュー": """
        SELECT c.relname, pg_get_viewdef(c.oid)
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %(s)s AND c.relkind IN ('v', 'm')
    """,
    "権限": """
        SELECT c.relkind::text || ':' || c.relname, coalesce(c.relacl::text, '')
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %(s)s AND c.relkind IN ('r', 'p', 'S', 'v', 'm')
    """,
    "既定の権限": """
        SELECT pg_get_userbyid(d.defaclrole) || '|' || d.defaclobjtype::text, d.defaclacl::text
        FROM pg_default_acl d JOIN pg_namespace n ON n.oid = d.defaclnamespace
        WHERE n.nspname = %(s)s
    """,
}


def take_shape(conn, schema: str = SCHEMA) -> dict[str, dict[str, str]]:
    """会社のスキーマの形を {種類: {名前: 中身}} で返す。スキーマ名は {S} に置き換える。"""
    shape: dict[str, dict[str, str]] = {}
    word = re.compile(rf"\b{re.escape(schema)}\b")
    conn.set_client_encoding("UTF8")
    with conn.cursor() as cur:
        cur.execute("SET search_path = ''")
        for kind, sql in _SHAPE_SQL.items():
            cur.execute(sql, {"s": schema})
            rows = cur.fetchall()
            shape[kind] = {word.sub(PLACEHOLDER, str(k)): word.sub(PLACEHOLDER, str(v)) for k, v in rows}
        cur.execute("RESET search_path")
    conn.commit()
    return shape


def table_of(kind: str, name: str, content: str, columns: dict[str, set[str]]) -> str | None:
    """形の 1 件が属する表の名前（表に属さない物は None）。"""
    if kind == "表":
        return name
    if kind in ("列", "制約", "トリガ", "方針"):
        return name.split(".", 1)[0]
    if kind == "索引":
        return content.split("|", 1)[0]
    if kind == "権限":
        rel = name.split(":", 1)[1]
        if name.startswith(("r:", "p:")):
            return rel
        name = rel  # 連番は下の判定へ
        kind = "連番"
    if kind == "連番":
        for table, cols in columns.items():
            if any(name == f"{table}_{c}_seq" for c in cols):
                return table
    return None


def diff_shapes(before: dict, after: dict, allowed: dict | None = None, used: set | None = None
                ) -> list[tuple[str, str, str, str, str]]:
    """前と後の差の全件。1 件は (種類, 名前, 分け, 前の中身, 後の中身)。許す一覧（表単位）の物は除く。

    used に渡した集合へ、実際に差を許した表の名前を入れる（使われなかった行を知らせるため）。
    """
    allowed = ALLOWED_TABLES if allowed is None else allowed
    columns: dict[str, set[str]] = {}
    for shp in (before, after):
        for key in shp.get("列", {}):
            t, c = key.split(".", 1)
            columns.setdefault(t, set()).add(c)
    out = []
    for kind in sorted(set(before) | set(after)):
        b, a = before.get(kind, {}), after.get(kind, {})
        for name in sorted(set(b) | set(a)):
            if name not in b:
                entry = (kind, name, "流した後だけ", "", a[name])
            elif name not in a:
                entry = (kind, name, "流す前だけ", b[name], "")
            elif b[name] != a[name]:
                entry = (kind, name, "中身が違う", b[name], a[name])
            else:
                continue
            table = table_of(kind, name, a.get(name, b.get(name, "")), columns)
            if table is not None and table in allowed:
                if used is not None:
                    used.add(table)
                continue
            out.append(entry)
    return out


def fk_rows(shape: dict) -> list[tuple[str, str, str]]:
    """外部キーの「表・外部キーの名前・指す表（置き場所つき）」。"""
    rows = []
    for name, content in shape.get("制約", {}).items():
        if content.startswith("f|"):
            table, conname = name.split(".", 1)
            rows.append((table, conname, content.rsplit("|ref=", 1)[1]))
    return sorted(rows)


def format_diff(diffs) -> str:
    lines = ["種類\t名前\t分け\t前\t後"]
    for kind, name, how, b, a in diffs:
        lines.append("\t".join([kind, name, how, b.replace("\n", "\\n"), a.replace("\n", "\\n")]))
    return "\n".join(lines) + "\n"


def write_shape(shape: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for kind, items in shape.items():
        body = "\n".join(f"{k}\t{v}".replace("\r", "") for k, v in sorted(items.items()))
        (out / f"{kind}.tsv").write_text(body + "\n", encoding="utf-8")


# ───────────────────────── 使い捨ての DB を用意する ─────────────────────────


def _env_conn(db: str) -> dict:
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": int(os.environ.get("PGPORT", "5432")),
        "user": os.environ.get("PGUSER", "jarvis"),
        "password": os.environ.get("PGPASSWORD", "testpass"),
        "dbname": db,
    }


def create_database(name: str) -> None:
    """使い捨ての DB を作る。すでにあれば止まる（本番や共用の DB を再利用しない）。"""
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,40}", name):
        raise ValueError(f"DB 名が不正: {name}")
    conn = psycopg2.connect(**_env_conn("postgres"))
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
        if cur.fetchone() is not None:
            raise RuntimeError(f"DB {name} はすでにある。使い捨ての名前を使うこと")
        cur.execute(f"CREATE DATABASE {name}")
    finally:
        conn.close()


def ensure_app_role() -> None:
    """本番にある利用者 salesanchor_app を、会社を作る前に用意する（無いと会社の表への権限が付かず、前と後で権限が違って見える）。"""
    conn = psycopg2.connect(**_env_conn("postgres"))
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app'")
        if cur.fetchone() is None:
            cur.execute("CREATE ROLE salesanchor_app LOGIN")
    finally:
        conn.close()


async def prepare_public_and_tenant(db: str) -> str:
    """public の前準備をして、create_tenant_schema で会社 1 つを作る。

    schema の無い会社の行（例 id 999）は入れない（登録の run_py が会社を id の順に回して落ちるため）。
    手本: backend/tests/rls_bootstrap.py の bootstrap_tenant_schema（同じ順。999 の行だけ入れない）。
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.services.tenant import create_tenant_schema
    from tests import rls_bootstrap as rb
    from tests.seed_data import customer_statuses_seed_sql

    c = _env_conn(db)
    url = f"postgresql+asyncpg://{c['user']}:{c['password']}@{c['host']}:{c['port']}/{db}"
    engine = create_async_engine(url, echo=False)
    try:
        await rb.bootstrap_public_products(engine)
        await rb.ensure_product_packagings(engine)
        async with engine.begin() as conn:
            await rb._bootstrap_public_shared(conn)
            await conn.execute(
                text("""
                    CREATE TABLE IF NOT EXISTS public.tenants (
                        id INTEGER PRIMARY KEY,
                        tenant_code VARCHAR(50) NOT NULL UNIQUE,
                        tenant_name VARCHAR(255) NOT NULL DEFAULT '',
                        company_name VARCHAR(255) NOT NULL DEFAULT '',
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        settings JSONB NOT NULL DEFAULT '{}'::jsonb
                    )
                """)
            )
            await conn.execute(
                text("""
                    CREATE TABLE IF NOT EXISTS public.users (
                        id INTEGER PRIMARY KEY,
                        tenant_id INTEGER NOT NULL,
                        username VARCHAR(255),
                        email VARCHAR(255),
                        full_name VARCHAR(255),
                        role VARCHAR(50) DEFAULT 'user',
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        is_super_admin BOOLEAN NOT NULL DEFAULT FALSE,
                        locale VARCHAR(10) NOT NULL DEFAULT 'ja',
                        theme VARCHAR(10) NOT NULL DEFAULT 'light'
                    )
                """)
            )
            raw = await conn.get_raw_connection()
            for filename in rb._PG_AFTER_TENANTS_MIGRATIONS:
                sql = (rb._MIGRATIONS_DIR / filename).read_text("utf-8").replace("BEGIN;", "").replace("COMMIT;", "")
                await raw.driver_connection.execute(sql)
            await conn.execute(text("SELECT set_config('app.is_operator', 'true', true)"))
            await conn.exec_driver_sql(customer_statuses_seed_sql())
            await conn.execute(text("SELECT set_config('app.is_operator', '', true)"))
            await conn.execute(
                text(
                    "INSERT INTO public.tenants (id, tenant_code, tenant_name, company_name, is_active) "
                    "VALUES (:i, :c, :c, :c, TRUE)"
                ),
                {"i": TENANT_ID, "c": SCHEMA},
            )
            schema = await create_tenant_schema(conn, TENANT_ID, admin_db=conn)
    finally:
        await engine.dispose()
    return schema


# ───────────────────────── 登録を全件流す ─────────────────────────


def _env_for_migration(db: str) -> dict:
    c = _env_conn(db)
    env = dict(os.environ)
    env.update({
        "PGHOST": c["host"], "PGPORT": str(c["port"]), "PGUSER": c["user"], "PGPASSWORD": c["password"],
        "PGDATABASE": db,
        "DATABASE_URL": f"postgresql://{c['user']}:{c['password']}@{c['host']}:{c['port']}/{db}",
        "MIGRATION_LOCK_TIMEOUT": "1s",
        "PGOPTIONS": "-c lock_timeout=1s",
        "PYTHONPATH": str(REPO_ROOT / "backend"),
    })
    return env


def _first_error(text_: str) -> str:
    lines = [x for x in text_.splitlines() if x.strip()]
    for x in lines:
        if "ERROR" in x or "Error" in x:
            return x.strip()[:300]
    return lines[-1].strip()[:300] if lines else ""


def run_registry(db: str, reg=None, log=print) -> list[tuple[int, str, str, int, float, str]]:
    """登録を順に全件流す。1 件は (行, 種類, ファイル, 終わりの番号, 秒, エラーの先頭)。"""
    reg = reg if reg is not None else registry()
    env = _env_for_migration(db)
    results = []
    for line, kind, target, extra in reg:
        t0 = time.time()
        if kind == "sql":
            with open(REPO_ROOT / target, "rb") as f:
                p = subprocess.run(
                    ["psql", "-v", "ON_ERROR_STOP=1"], stdin=f, cwd=REPO_ROOT, env=env,
                    capture_output=True, timeout=900,
                )
            rc, err = p.returncode, p.stderr.decode("utf-8", "replace")
        else:
            penv = dict(env)
            m = re.match(r"-e\s+(\w+)=(\S+)", extra)
            if m:
                penv[m.group(1)] = m.group(2)
            p = subprocess.run(
                [sys.executable, str(REPO_ROOT / "scripts/migration_py_entry.py"), str(REPO_ROOT / target)],
                cwd=REPO_ROOT / "backend", env=penv, capture_output=True, text=True, timeout=900,
            )
            rc, err = p.returncode, p.stderr
        secs = round(time.time() - t0, 1)
        results.append((line, kind, target, rc, secs, _first_error(err) if rc != 0 else ""))
        if rc != 0:
            log(f"registry line {line} {target} rc={rc}: {_first_error(err)}")
    return results


def unexpected_failures(results) -> list[tuple]:
    """外す一覧に無いのに落ちた移行。"""
    return [r for r in results if r[3] != 0 and r[2] not in EXCLUDED_REGISTRY]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="tenant_shape_check", help="使い捨ての DB の名前（すでにあれば止まる）")
    ap.add_argument("--out-dir", default=None, help="形・差・流した結果を書き出す場所（省略可）")
    args = ap.parse_args(argv)
    out = Path(args.out_dir) if args.out_dir else None

    ensure_app_role()
    create_database(args.db)
    schema = asyncio.run(prepare_public_and_tenant(args.db))
    assert schema == SCHEMA, schema

    conn = psycopg2.connect(**_env_conn(args.db))
    try:
        before = take_shape(conn)
        results = run_registry(args.db)
        after = take_shape(conn)
    finally:
        conn.close()

    bad = unexpected_failures(results)
    used_allowed: set[str] = set()
    diffs = diff_shapes(before, after, used=used_allowed)
    if out:
        write_shape(before, out / "before")
        write_shape(after, out / "after")
        (out / "diff.tsv").write_text(format_diff(diffs), encoding="utf-8")
        (out / "registry.tsv").write_text(
            "line\tkind\ttarget\trc\tsec\tfirst_error\n" + "\n".join("\t".join(map(str, r)) for r in results) + "\n",
            encoding="utf-8",
        )

    print(f"登録 {len(results)} 本（run_sql {sum(1 for r in results if r[1] == 'sql')}・run_py {sum(1 for r in results if r[1] == 'py')}）")
    for r in results:
        if r[3] != 0 and r[2] in EXCLUDED_REGISTRY:
            print(f"外す一覧で許した失敗: {r[2]}（{EXCLUDED_REGISTRY[r[2]]}）")
    for table in sorted(set(ALLOWED_TABLES) - used_allowed):
        print(f"知らせ: 許す一覧の行 {table} は使われなかった（差が出なかった）。外し忘れでないか確かめる: {ALLOWED_TABLES[table]}")
    rc = 0
    if bad:
        rc = 1
        print(f"FAIL: 外す一覧に無い移行が {len(bad)} 本落ちた")
        for r in bad:
            print(f"  行{r[0]} {r[2]} 終わりの番号={r[3]} {r[5]}")
    if diffs:
        rc = 1
        print(f"FAIL: 流す前と後で形が違う物が {len(diffs)} 件ある（ひな形を、流した後の形に合わせる）")
        print(format_diff(diffs), end="")
    if rc == 0:
        print("OK: 形の差 0")
    return rc


if __name__ == "__main__":
    sys.exit(main())
