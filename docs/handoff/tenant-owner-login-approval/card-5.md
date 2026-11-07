# card: 便5 会社の列があるのに RLS の無い public の表を CI で見つける（K8）

状態: カード発行（Opus、2026-11-06）。PO の実装承認は 2026-11-06「1」（このまま作り始める）。設計: docs/handoff/tenant-owner-login-approval/design.md 便5。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret には触らない。PR は作らない（Opus が作る）。
基準: origin/main（このカードのコミットの親）。行番号はその時点のもの。ずれていたら「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で止まる）。

この便は 2 段で進める（design.md 便5「最初の数え方」）。このカードは **段1（数えて出すだけ）** だけを実装する。段2（許可一覧を埋めて落とす形にする）は、段1 の CI の生出力を Opus が1件ずつ確かめ、PO に報告してから、別のカードで頼む。段1 で許可一覧に表名を推測で入れてはいけない。

設計からの小さな変更（Opus 判断・記録）:
- 試験は design.md の「public.ci_rls_probe を共有の試験 DB に作る」ではなく、使い捨ての DB を作ってその中に作る（`backend/tests/ops/test_ai_job_assignments_db.py:101` の db fixture と同じ形）。理由: 共有の試験 DB には他の試験が作った表があり、並行の試験とぶつかる。使い捨てなら数が厳密に決まる。
- 許可一覧の場所 backend/app/ops/tenant_rls_allowlist.py は設計どおり。便6 が使う `BYPASSRLS_ROLES` も同じファイルに空で置く（便6 で中身を固定する）。

## 受領確認（最初の報告の 1 行目に書く）
RECEIVED tenant-owner-bin5 HEAD=（git rev-parse HEAD の 40 桁）

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝 `release/tenant-owner-bin5-public-rls-ci` を origin から取り、このカードが在ること。
- P2 次の 3 つのファイルがまだ無いこと: scripts/check_public_tenant_rls.py・backend/app/ops/tenant_rls_allowlist.py・backend/tests/test_check_public_tenant_rls.py。
- P3 `grep -c "python3 scripts/migration-dryrun-report.py run --db jarvis_report --rounds 2 --psql psql" .github/workflows/migration-test.yml` が 1。
- P4 `grep -c "              - 'scripts/migration-dryrun-report.py'" .github/workflows/migration-test.yml` が 1。
- P5 `backend/app/ops/__init__.py` が在る（中身は空でよい）。

## 1. 触るファイル
1. scripts/check_public_tenant_rls.py（新規）
2. backend/app/ops/tenant_rls_allowlist.py（新規）
3. backend/tests/test_check_public_tenant_rls.py（新規）
4. .github/workflows/migration-test.yml

触らない: migrations・backend/app のほかのファイル・.github のほかのファイル・scripts のほかのファイル・frontend。

## 2. 変更

### 2-1 backend/app/ops/tenant_rls_allowlist.py（新規・全文）
```python
"""会社の分け方（RLS）の許可一覧（ADR-1063 便5・便6）。

ここが唯一の正本。CI の点検（scripts/check_public_tenant_rls.py）と
本番の毎日点検（便6）の両方がこのファイルを読む。ほかの場所に写さない。

PUBLIC_TABLES_WITHOUT_RLS: public の表のうち、tenant_id 列を持つのに RLS を付けない表。
  表名 → 理由（空にしない。空なら CI の点検が落ちる）。
BYPASSRLS_ROLES: BYPASSRLS を持ってよい役。役名 → 理由（便6 で初回の観測を PO に報告してから固定する）。

この一覧の行を足すときは、なぜ RLS が要らないかを理由に書く。推測で足さない。
"""

from __future__ import annotations

PUBLIC_TABLES_WITHOUT_RLS: dict[str, str] = {}

BYPASSRLS_ROLES: dict[str, str] = {}
```

### 2-2 scripts/check_public_tenant_rls.py（新規・全文）
```python
#!/usr/bin/env python3
"""public の表のうち tenant_id 列を持つのに RLS の無いものを見つける（ADR-1063 便5・K8）。

使い方（CI。接続先は PGHOST・PGUSER・PGPASSWORD の環境変数で渡す）:
  PYTHONPATH=backend python3 scripts/check_public_tenant_rls.py --db jarvis_report [--report-only]

結果:
  - 許可一覧（backend/app/ops/tenant_rls_allowlist.py）の理由が空の行がある → 終了コード 1
  - 許可一覧に無い表が見つかった → 終了コード 1（--report-only のときは名前を出して 0）
  - それ以外 → 0
"""

from __future__ import annotations

import argparse
import sys

import psycopg2

from app.ops.tenant_rls_allowlist import PUBLIC_TABLES_WITHOUT_RLS

FIND_SQL = """
SELECT c.relname
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attname = 'tenant_id' AND NOT a.attisdropped
WHERE n.nspname = 'public'
  AND c.relkind IN ('r', 'p')
  AND NOT c.relrowsecurity
ORDER BY c.relname
"""


def find_tables_without_rls(conn) -> list[str]:
    """public の tenant_id 付きで RLS の無い表の名前（名前順）。"""
    with conn.cursor() as cur:
        cur.execute(FIND_SQL)
        return [row[0] for row in cur.fetchall()]


def empty_reasons(allowlist: dict[str, str]) -> list[str]:
    """理由が空（空白だけを含む）の行の表名。"""
    return sorted(name for name, reason in allowlist.items() if not reason.strip())


def run(conn, allowlist: dict[str, str], report_only: bool) -> int:
    blank = empty_reasons(allowlist)
    if blank:
        for name in blank:
            print(f"❌ 許可一覧の理由が空です: {name}")
        return 1

    found = find_tables_without_rls(conn)
    unexpected = [name for name in found if name not in allowlist]
    allowed = [name for name in found if name in allowlist]
    stale = sorted(name for name in allowlist if name not in found)

    print(f"public の tenant_id 付きで RLS の無い表: {len(found)} 件（許可一覧にある {len(allowed)} 件・無い {len(unexpected)} 件）")
    for name in allowed:
        print(f"  許可一覧にある: {name}")
    for name in unexpected:
        print(f"  許可一覧に無い: {name}")
    for name in stale:
        print(f"  （参考）許可一覧にあるが見つからない: {name}")

    if unexpected and not report_only:
        print("❌ 会社の列があるのに RLS の無い表があります。RLS を付けるか、理由を書いて backend/app/ops/tenant_rls_allowlist.py に足してください。")
        return 1
    if unexpected:
        print("（--report-only のため落としません）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="点検する DB の名前")
    parser.add_argument("--report-only", action="store_true", help="見つけても落とさず名前だけ出す")
    args = parser.parse_args(argv)
    conn = psycopg2.connect(dbname=args.db)
    try:
        return run(conn, PUBLIC_TABLES_WITHOUT_RLS, args.report_only)
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
```

### 2-3 backend/tests/test_check_public_tenant_rls.py（新規・全文）
```python
"""ADR-1063 便5（K8）: public の tenant_id 付きで RLS の無い表を見つける点検の試験（実 PostgreSQL が必要）。

使い捨ての DB を作り、その中に見本の表を作って確かめる。終わったら DB ごと消す。
R1: tenant_id 付き・RLS なしの表は見つかり、許可一覧に無ければ 1（落ちる見本）。
R2: 同じ表に RLS を付けると見つからず 0（通る見本）。
R3: 許可一覧に理由付きで入っていれば 0。
R4: 許可一覧の理由が空なら 1。
R5: --report-only なら見つけても 0。
R6: tenant_id の無い表・public 以外の表は数えない。
"""

from __future__ import annotations

import importlib.util
import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_public_tenant_rls.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("check_public_tenant_rls", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _psycopg_url(url: str, dbname: str | None = None) -> str:
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    if dbname:
        parts = urlsplit(url)
        url = urlunsplit(parts._replace(path="/" + dbname))
    return url


@pytest.fixture()
def conn():
    import psycopg2

    control = psycopg2.connect(_psycopg_url(ADMIN_PG_URL))
    control.autocommit = True
    name = f"rls_check_{uuid.uuid4().hex[:12]}"
    control.cursor().execute(f'CREATE DATABASE "{name}"')
    c = psycopg2.connect(_psycopg_url(ADMIN_PG_URL, name))
    c.autocommit = True
    try:
        yield c
    finally:
        c.close()
        control.cursor().execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        control.close()


def _exec(conn, sql: str) -> None:
    with conn.cursor() as cur:
        cur.execute(sql)


def test_r1_table_without_rls_fails(conn):
    mod = _load_script()
    _exec(conn, "CREATE TABLE public.ci_rls_probe (id int PRIMARY KEY, tenant_id int NOT NULL)")
    assert mod.find_tables_without_rls(conn) == ["ci_rls_probe"]
    assert mod.run(conn, {}, report_only=False) == 1


def test_r2_rls_enabled_passes(conn):
    mod = _load_script()
    _exec(conn, "CREATE TABLE public.ci_rls_probe (id int PRIMARY KEY, tenant_id int NOT NULL)")
    _exec(conn, "ALTER TABLE public.ci_rls_probe ENABLE ROW LEVEL SECURITY")
    assert mod.find_tables_without_rls(conn) == []
    assert mod.run(conn, {}, report_only=False) == 0


def test_r3_allowlisted_with_reason_passes(conn):
    mod = _load_script()
    _exec(conn, "CREATE TABLE public.ci_rls_probe (id int PRIMARY KEY, tenant_id int NOT NULL)")
    assert mod.run(conn, {"ci_rls_probe": "試験用の理由"}, report_only=False) == 0


def test_r4_blank_reason_fails(conn):
    mod = _load_script()
    assert mod.run(conn, {"ci_rls_probe": "   "}, report_only=False) == 1
    assert mod.run(conn, {"ci_rls_probe": ""}, report_only=True) == 1


def test_r5_report_only_does_not_fail(conn):
    mod = _load_script()
    _exec(conn, "CREATE TABLE public.ci_rls_probe (id int PRIMARY KEY, tenant_id int NOT NULL)")
    assert mod.run(conn, {}, report_only=True) == 0


def test_r6_only_public_tables_with_tenant_id(conn):
    mod = _load_script()
    _exec(conn, "CREATE TABLE public.ci_no_tenant (id int PRIMARY KEY)")
    _exec(conn, "CREATE SCHEMA ci_other")
    _exec(conn, "CREATE TABLE ci_other.ci_rls_probe (id int PRIMARY KEY, tenant_id int NOT NULL)")
    assert mod.find_tables_without_rls(conn) == []
```

### 2-4 .github/workflows/migration-test.yml（2 か所）

(1) 起動の条件（paths-filter）
変更前:
```
              - 'scripts/migration-dryrun-report.py'
              - '.github/workflows/migration-test.yml'
```
変更後:
```
              - 'scripts/migration-dryrun-report.py'
              - 'scripts/check_public_tenant_rls.py'
              - 'backend/app/ops/tenant_rls_allowlist.py'
              - '.github/workflows/migration-test.yml'
```

(2) 全件ドライランの直後に 1 手を足す
変更前（job migration-full-dryrun の最後の手の最後の行）:
```
          python3 scripts/migration-dryrun-report.py run --db jarvis_report --rounds 2 --psql psql
```
変更後（その直後、空行の前に足す。字下げは上の手と同じ）:
```
          python3 scripts/migration-dryrun-report.py run --db jarvis_report --rounds 2 --psql psql

      - name: 会社の列があるのに RLS の無い public の表を数える（ADR-1063 K8・段1 は数えて出すだけ）
        # 全件ドライランを流し終えた報告用 DB（jarvis_report）を見る。許可一覧は backend/app/ops/tenant_rls_allowlist.py の1か所。
        # 段1 は --report-only（名前を出すだけ）。段2 で一覧を確かめてから --report-only を外して落とす形にする。
        env:
          PGHOST: localhost
          PGUSER: jarvis
          PYTHONPATH: ${{ github.workspace }}/backend
        run: |
          python3 scripts/check_public_tenant_rls.py --db jarvis_report --report-only
```
（job の env に PGPASSWORD: testpass が既にあるので足さない。）

## 3. 確かめ（クラウドで実行し、生の出力を報告に貼る）
- V1 `python3 -c "import ast,sys; [ast.parse(open(p).read()) for p in sys.argv[1:]]" scripts/check_public_tenant_rls.py backend/app/ops/tenant_rls_allowlist.py backend/tests/test_check_public_tenant_rls.py` が何も出さず終わる。
- V2 `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/migration-test.yml'))"` が何も出さず終わる。
- V3 PostgreSQL が使えるなら `cd backend && RLS_ADMIN_DATABASE_URL=<使える URL> python3 -m pytest -q tests/test_check_public_tenant_rls.py`。使えなければ「未実行（PostgreSQL なし）」と書く（CI の pytest で確かめる）。
- V4 `cd backend && ruff check ../scripts/check_public_tenant_rls.py app/ops/tenant_rls_allowlist.py tests/test_check_public_tenant_rls.py`（ruff が入っていれば）。
- V5 `git diff --name-only origin/main...HEAD` が、このカードと作業の札と「1. 触るファイル」の 4 件だけ。

## 4. 終わったら
- コミットは 1 つ（メッセージ: `feat(ci): find public tenant tables without RLS, report-only (ADR-1063 bin5 step1)`）。push する。PR は作らない。
- 報告の最後の行は `DONE` か `BLOCKED: <理由>` か `NEEDS_DECISION: <問い>`。
