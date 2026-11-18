# card: 便6 本番の毎日点検（会社の分け方が崩れていないかを毎日 Discord へ・K9）

状態: カード発行（Opus、2026-11-19）。PO の実装承認は 2026-11-06「1. このまま作り始める」（設計 docs/handoff/tenant-owner-login-approval/design.md 全体）と 2026-11-19「1」（6〜8段目の再開）。
審査: 2026-11-19 クラウドの設計審査役（Opus）が REVISE。指摘4件（A8 の差し替え方・V5 の整形の確かめ・CI の点検の起動条件・試験 B の取引）をこの版で直した。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret には触らない。PR は作らない（Opus が作る）。
基準: 枝 release/tenant-owner-bin6-daily-check（origin/main 9871793e910d552f74e01d398b15dcbd2f2815bd から作成、このカードのコミットを足したもの）。行番号はその時点のもの。ずれていたら「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で止まる）。

設計の節: design.md「### 便6: 本番の毎日点検（K9）」。

本番の今の値（Opus、2026-11-19 00:39〜00:40 JST、読取の道 ADR-1024 の生出力）:
- RLS を飛び越せる役（`rolbypassrls OR rolsuper`）: ai_unmask_owner（BYPASSRLS・ログイン不可）と jarvis（superuser・BYPASSRLS・ログイン可）の 2 件。
- アプリの接続: salesanchor_app（application_name salesanchor_backend 20 本と名札なし 1 本）。上の 2 件に salesanchor_app は入っていない。
- public の tenant_id 付きで RLS の無い表: 11 件。許可一覧 PUBLIC_TABLES_WITHOUT_RLS の 11 件と同じ名前。
→ 初回の点検は「黄（一覧未固定）」になる見込み。役の一覧を許可一覧に固定するのは、初回の Discord の結果を Opus が読み、PO に報告した後の別の小さな PR（設計どおり。このカードでは BYPASSRLS_ROLES を空のまま残す）。

設計からの小さな変更（Opus 判断・記録）:
- 項目2 の「BYPASSRLS を持つ役」を「BYPASSRLS または superuser の役」にする。理由: PostgreSQL では superuser は BYPASSRLS の印が無くても RLS を飛び越す。守りたいのは「RLS を飛び越せる役が増えないこと」なので両方を数える。本番の今の値ではどちらで数えても同じ 2 件。
- 「一致」の判定は、CI の点検（scripts/check_public_tenant_rls.py）と同じにする。許可一覧に無いものが増えたら赤。許可一覧にあるのに見つからないもの（RLS を付けた・役を消した）は（参考）として書くだけで赤にしない。理由: 減る向きは守りが強くなる向きで、CI と判定を分けるとデータの読み方が 2 通りになる。
- 表を探す SQL は、CI の点検の FIND_SQL を新しいファイル backend/app/ops/tenant_rls_checks.py に移し、CI の点検と毎日点検の両方がそこから読む。理由: 同じ SQL を 2 か所に書かない（データと配線を 1 か所に）。

## 読んだ節（docs/handoff/design-partner-card-ops/guards/）と照合（Opus、2026-11-19）
- 00-common.md: プレースホルダを残さない → 名前・時刻・文はすべて書き切った。停止の報告経路は「4. 終わったら」に書いた。
- 02-db.md: 本番 DB には触らない。試験は CI と同じ使い捨ての DB（実 PostgreSQL）で行う。
- 03-file.md: 既存ファイルの一部の書き換えは「変更前／変更後」の逐語で示し、変更前の文は 2026-11-19 にこの枝で実測した（P2〜P6）。
- 10-executor.md: 実行役はクラウドの Sonnet（CC 系）。カードに無い確認は足さず、外れたら停止する。

## 受領確認（最初の報告の 1 行目に書く）
RECEIVED tenant-owner-bin6-daily-check HEAD=（git rev-parse HEAD の 40 桁）

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝 `release/tenant-owner-bin6-daily-check` を origin から取り、このカード（docs/handoff/tenant-owner-login-approval/card-6.md）が在ること。
- P2 `grep -c "^BYPASSRLS_ROLES: dict\[str, str\] = {}$" backend/app/ops/tenant_rls_allowlist.py` が 1。
- P3 `grep -c '^FIND_SQL = """$' scripts/check_public_tenant_rls.py` が 1。
- P4 `grep -c '"app.tasks.discord_own_staff_sync",  # discord-server-management 第2段 2b' backend/app/celery_app.py` が 1。
- P5 `ls backend/app/ops/tenant_rls_checks.py backend/app/tasks/tenant_isolation_daily_check.py backend/tests/test_tenant_isolation_daily_check.py` が 3 つとも「No such file」。
- P6 `grep -c "^RLS_PROBE_TABLE_DDL = " backend/tests/conftest.py` が 1。
- P7 `grep -c "^              - 'backend/app/ops/tenant_rls_allowlist.py'$" .github/workflows/migration-test.yml` が 1。

## 1. 触るファイル
1. backend/app/ops/tenant_rls_checks.py（新規）
2. scripts/check_public_tenant_rls.py（FIND_SQL を import に替えるだけ）
3. backend/app/tasks/tenant_isolation_daily_check.py（新規）
4. backend/app/celery_app.py（include に 1 行・時間割に 1 項目）
5. backend/tests/test_tenant_isolation_daily_check.py（新規）
6. .github/workflows/migration-test.yml（起動の条件の一覧に 1 行足すだけ）

触らない: backend/app/ops/tenant_rls_allowlist.py（BYPASSRLS_ROLES は空のまま）・migrations・.github（migration-test.yml の 1 行のほかは触らない）・frontend・docs・ほかの backend/app と scripts と backend/tests のファイル（conftest.py も変えない。既存の RLS_PROBE_TABLE_DDL を import して使う）。

## 2. 変更

### 2-1 backend/app/ops/tenant_rls_checks.py（新規・全文）
```python
"""会社の分け方（RLS）の点検で使う SQL（ADR-1063 便5・便6）。

ここが唯一の正本。CI の点検（scripts/check_public_tenant_rls.py）と
本番の毎日点検（backend/app/tasks/tenant_isolation_daily_check.py）の両方がここを読む。ほかの場所に写さない。
許可一覧は backend/app/ops/tenant_rls_allowlist.py。
"""

from __future__ import annotations

# public の表のうち tenant_id 列を持つのに RLS の無いもの（名前順）。
PUBLIC_TABLES_WITHOUT_RLS_SQL = """
SELECT c.relname
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attname = 'tenant_id' AND NOT a.attisdropped
WHERE n.nspname = 'public'
  AND c.relkind IN ('r', 'p')
  AND NOT c.relrowsecurity
ORDER BY c.relname
"""

# 今つないでいる役の名前と、superuser・BYPASSRLS の印。
CURRENT_ROLE_SQL = """
SELECT rolname, rolsuper, rolbypassrls
FROM pg_roles
WHERE rolname = current_user
"""

# RLS を飛び越せる役（BYPASSRLS の印を持つ役と superuser。superuser は印が無くても RLS を飛び越す）。
RLS_BYPASS_ROLES_SQL = """
SELECT rolname
FROM pg_roles
WHERE rolbypassrls OR rolsuper
ORDER BY rolname
"""
```

### 2-2 scripts/check_public_tenant_rls.py
(1) 変更前:
```python
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
```
変更後:
```python
from app.ops.tenant_rls_allowlist import PUBLIC_TABLES_WITHOUT_RLS
from app.ops.tenant_rls_checks import PUBLIC_TABLES_WITHOUT_RLS_SQL as FIND_SQL
```
ほかの行は変えない（`cur.execute(FIND_SQL)` はそのまま動く）。

### 2-3 backend/app/tasks/tenant_isolation_daily_check.py（新規・全文）
```python
"""ADR-1063 便6（K9）: 会社の分け方（RLS）が本番で崩れていないかを毎日点検し、管理者用 Discord に送る。

見るもの（設計 docs/handoff/tenant-owner-login-approval/design.md「便6」）:
  1. アプリの接続している役が superuser でも BYPASSRLS でもない。
  2. RLS を飛び越せる役（BYPASSRLS・superuser）が、許可一覧 BYPASSRLS_ROLES に無いものを含まない。
     許可一覧が空の間は「黄（一覧未固定）」で、見つけた役の名前を書くだけ。
  3. public の tenant_id 付きで RLS の無い表が、許可一覧 PUBLIC_TABLES_WITHOUT_RLS に無いものを含まない。
緑のときも毎日 1 通送る（届かない＝止まっている、と区別するため）。鍵・接続の文字列は書かない。DB は読むだけ。
判定は CI の点検（scripts/check_public_tenant_rls.py）と同じ: 許可一覧に無いものが増えたら赤、減ったものは（参考）。
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx
from celery import shared_task
from sqlalchemy import text

from app.ops.tenant_rls_allowlist import BYPASSRLS_ROLES, PUBLIC_TABLES_WITHOUT_RLS
from app.ops.tenant_rls_checks import (
    CURRENT_ROLE_SQL,
    PUBLIC_TABLES_WITHOUT_RLS_SQL,
    RLS_BYPASS_ROLES_SQL,
)

logger = logging.getLogger(__name__)

_WEBHOOK_ENV = "ADMIN_NOTIFICATION_DISCORD_WEBHOOK"

_HEAD = {
    "green": "✅ 会社の分け方の毎日点検（ADR-1063 K9）: 3 項目とも合格",
    "yellow": "🟡 会社の分け方の毎日点検（ADR-1063 K9）: 役の許可一覧が未固定（項目2 は名前を書くだけ）",
    "red": "🔴 会社の分け方の毎日点検（ADR-1063 K9）: 崩れあり",
}


async def collect(conn) -> dict:
    """DB から 3 項目の材料を読む。conn は SQLAlchemy の非同期接続。"""
    me = (await conn.execute(text(CURRENT_ROLE_SQL))).one()
    roles = [row[0] for row in (await conn.execute(text(RLS_BYPASS_ROLES_SQL))).all()]
    tables = [row[0] for row in (await conn.execute(text(PUBLIC_TABLES_WITHOUT_RLS_SQL))).all()]
    return {
        "current_role": me[0],
        "current_super": bool(me[1]),
        "current_bypass": bool(me[2]),
        "bypass_roles": roles,
        "tables": tables,
    }


def judge(
    facts: dict, role_allowlist: dict[str, str], table_allowlist: dict[str, str]
) -> tuple[str, list[str], list[str]]:
    """(色, 崩れた項目, 参考) を返す。色は green / yellow / red。"""
    broken: list[str] = []
    notes: list[str] = []
    if facts["current_super"] or facts["current_bypass"]:
        broken.append(f"項目1: アプリの接続している役 {facts['current_role']} が RLS を飛び越せる")
    unpinned = not role_allowlist
    if not unpinned:
        extra_roles = sorted(set(facts["bypass_roles"]) - set(role_allowlist))
        gone_roles = sorted(set(role_allowlist) - set(facts["bypass_roles"]))
        if extra_roles:
            broken.append("項目2: 許可一覧に無い RLS を飛び越せる役: " + ", ".join(extra_roles))
        if gone_roles:
            notes.append("（参考）許可一覧にあるが見つからない役: " + ", ".join(gone_roles))
    extra_tables = sorted(set(facts["tables"]) - set(table_allowlist))
    gone_tables = sorted(set(table_allowlist) - set(facts["tables"]))
    if extra_tables:
        broken.append("項目3: 許可一覧に無い RLS の無い表: " + ", ".join(extra_tables))
    if gone_tables:
        notes.append("（参考）許可一覧にあるが見つからない表: " + ", ".join(gone_tables))
    if broken:
        color = "red"
    elif unpinned:
        color = "yellow"
    else:
        color = "green"
    return color, broken, notes


def build_message(color: str, broken: list[str], notes: list[str], facts: dict) -> str:
    roles = facts["bypass_roles"]
    lines = [
        _HEAD[color],
        f"アプリの接続している役: {facts['current_role']}",
        f"RLS を飛び越せる役: {len(roles)} 件（{', '.join(roles) if roles else 'なし'}）",
        f"RLS の無い表: {len(facts['tables'])} 件（許可一覧 {len(PUBLIC_TABLES_WITHOUT_RLS)} 件）",
    ]
    lines.extend(broken)
    lines.extend(notes)
    return "\n".join(lines)


async def _post_discord(content: str) -> None:
    url = (os.getenv(_WEBHOOK_ENV) or "").strip()
    if not url:
        logger.warning("%s is not set; skip tenant isolation daily check report", _WEBHOOK_ENV)
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json={"content": content[:1800], "username": "会社の分け方 毎日点検"})
        if res.status_code >= 400:
            logger.warning("tenant isolation daily check: discord status %s", res.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("tenant isolation daily check: discord error %s", type(exc).__name__)


async def _run_check() -> dict:
    from app.database import engine

    try:
        async with engine.connect() as conn:
            facts = await collect(conn)
    except Exception as exc:  # noqa: BLE001
        # 点検が動けなかったことも毎日の 1 通で知らせる（届かない日と区別するため）。中身の文は書かない。
        await _post_discord(f"🔴 会社の分け方の毎日点検（ADR-1063 K9）: 点検が動けなかった（{type(exc).__name__}）")
        raise
    color, broken, notes = judge(facts, BYPASSRLS_ROLES, PUBLIC_TABLES_WITHOUT_RLS)
    await _post_discord(build_message(color, broken, notes, facts))
    return {"color": color, "broken": broken, "notes": notes, "facts": facts}


@shared_task(name="app.tasks.tenant_isolation_daily_check.run_tenant_isolation_daily_check")
def run_tenant_isolation_daily_check() -> dict:
    from app.database import engine

    try:
        return asyncio.run(_run_check())
    finally:
        asyncio.run(engine.dispose())
```

### 2-4 backend/app/celery_app.py
(1) include。変更前:
```python
        "app.tasks.discord_own_staff_sync",  # discord-server-management 第2段 2b: 自社サーバーのスタッフのロールの点検
    ],
```
変更後:
```python
        "app.tasks.discord_own_staff_sync",  # discord-server-management 第2段 2b: 自社サーバーのスタッフのロールの点検
        "app.tasks.tenant_isolation_daily_check",  # ADR-1063 便6: 会社の分け方（RLS）の毎日点検
    ],
```
(2) 時間割。変更前:
```python
    "discord-own-staff-sync": {
        "task": "app.tasks.discord_own_staff_sync.sync_all_own_servers",
        "schedule": 300.0,  # 5分
    },
}
```
変更後:
```python
    "discord-own-staff-sync": {
        "task": "app.tasks.discord_own_staff_sync.sync_all_own_servers",
        "schedule": 300.0,  # 5分
    },
    # ADR-1063 便6（K9）: 会社の分け方（RLS）が崩れていないかを毎日 09:05 JST に管理者用 Discord へ（緑でも送る）
    "tenant-isolation-daily-check": {
        "task": "app.tasks.tenant_isolation_daily_check.run_tenant_isolation_daily_check",
        "schedule": crontab(hour=9, minute=5),
    },
}
```

### 2-6 .github/workflows/migration-test.yml
理由: 表を探す SQL の正本が tenant_rls_checks.py に移るため。この 1 行が無いと、SQL だけを変える PR で実 DB の全件ドライランの点検が動かない。
変更前:
```yaml
              - 'scripts/check_public_tenant_rls.py'
              - 'backend/app/ops/tenant_rls_allowlist.py'
```
変更後:
```yaml
              - 'scripts/check_public_tenant_rls.py'
              - 'backend/app/ops/tenant_rls_allowlist.py'
              - 'backend/app/ops/tenant_rls_checks.py'
```
字下げは前後の行と同じ空白 14 個。ほかの行は変えない。

### 2-7 新しい 3 ファイルの整形
2-1・2-3・2-5 の新しいファイルだけに `ruff check --fix` と `ruff format`（line-length は backend/pyproject.toml の 120）をかけてよい。既存のファイル（celery_app.py・check_public_tenant_rls.py）には ruff format をかけない（もとから整形に合っていない所があり、かけると範囲の外まで変わる）。

### 2-5 backend/tests/test_tenant_isolation_daily_check.py（新規）
次の試験を書く。CREATE TABLE の文は書かない（test-schema-dup gate が数えるため）。表は `from tests.conftest import RLS_PROBE_TABLE_DDL` を使う。

A. DB なしで動く試験（いつも走る）:
- A1 judge: 項目1〜3 がすべて問題なし・役の許可一覧が空でない → `("green", [], [])`。
- A2 judge: 役の許可一覧が空 → 色が "yellow"、broken が空。
- A3 judge: current_super が True → "red"、broken の 1 つが「項目1:」で始まる。current_bypass が True でも同じ。
- A4 judge: 役の許可一覧が空でなく、そこに無い役がある → "red"・「項目2:」とその役の名前。許可一覧にあって見つからない役 → notes に「（参考）許可一覧にあるが見つからない役」・色は赤にならない。
- A5 judge: 表の許可一覧に無い表 → "red"・「項目3:」とその表の名前。許可一覧にあって見つからない表 → notes だけ。
- A6 judge: 役の許可一覧が空でも、項目1 か 3 が崩れていれば "red"（黄より赤が勝つ）。
- A7 build_message: 1 行目が色ごとに "✅" / "🟡" / "🔴" で始まり、2 行目に役の名前、3 行目に役の件数と名前、4 行目に表の件数が出る。
- A8 _run_check: `app.tasks.tenant_isolation_daily_check.collect` を AsyncMock で差し替え（facts を返す）、`_post_discord` を AsyncMock で差し替えて、1 回だけ呼ばれ、渡された文の 1 行目が judge の色と合うこと。engine は `patch("app.database.engine", fake_engine)` でモジュールの名前ごと差し替える（AsyncEngine の connect は読み取り専用で patch.object できない。前例 backend/tests/test_master_required_fields_monitor.py:48 もモジュールの名前を差し替えている）。fake_engine は MagicMock で、`fake_engine.connect.return_value` に `__aenter__`（AsyncMock、偽の接続を返す）と `__aexit__`（AsyncMock、False を返す）を持たせる。_run_check は関数の中で `from app.database import engine` するので、この差し替えが効く。
- A9 _run_check: collect が例外を投げたら `_post_discord` が「点検が動けなかった」を含む文で 1 回呼ばれ、例外がそのまま上に出る。
- A10 時間割: `from app.celery_app import celery_app` で、`celery_app.conf.beat_schedule["tenant-isolation-daily-check"]` の task が "app.tasks.tenant_isolation_daily_check.run_tenant_isolation_daily_check"、schedule が `crontab(hour=9, minute=5)` と等しい。`"app.tasks.tenant_isolation_daily_check"` が `celery_app.conf.include` に入っている。

B. 実 PostgreSQL の試験（`ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")` が無ければ skip。作り方は backend/tests/test_check_public_tenant_rls.py の使い捨て DB の作り方に合わせる。非同期接続は URL の頭を `postgresql+asyncpg://` にして create_async_engine で作り、終わったら dispose する）:
- B1 使い捨て DB で RLS_PROBE_TABLE_DDL を流す → collect の tables に "ci_rls_probe" が入り、judge（表の許可一覧が空）が "red"・「項目3:」。`ALTER TABLE public.ci_rls_probe ENABLE ROW LEVEL SECURITY` の後 → tables に入らない。
- B2 役の名前を `ci_bypass_` に uuid の頭 12 文字を足したものにして `CREATE ROLE` その名前 `NOLOGIN BYPASSRLS` → collect の bypass_roles に入る。judge の役の許可一覧を「その役を除いた bypass_roles（空なら {"ci_placeholder": "試験"}）」にすると "red"・「項目2:」とその役の名前。finally で `DROP ROLE IF EXISTS`。
- B3 役の名前を `ci_plain_` に uuid の頭 12 文字を足したものにして `CREATE ROLE` その名前 `NOLOGIN` と `GRANT` その名前 `TO CURRENT_USER` → 同じ接続で `SET ROLE` その名前 の後の collect が current_role=その名前・current_super=False・current_bypass=False で、judge に項目1 の崩れが無い。`RESET ROLE` の後の collect の current_super/current_bypass は、`SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user` の結果と同じ。finally で `RESET ROLE` と `DROP ROLE IF EXISTS`。
- 役は全 DB 共通なので、名前は必ず uuid 付きにし、finally で必ず消す（ほかの試験とぶつからないため）。
- 取引の扱い: B2・B3 の接続は `conn = await engine.connect()` の直後に `conn = await conn.execution_options(isolation_level="AUTOCOMMIT")` にする（CREATE ROLE・GRANT・SET ROLE が 1 文ずつ確定し、途中で失敗しても取引が止まったままにならない）。finally の `DROP ROLE IF EXISTS` は、その接続を閉じた後に、新しい AUTOCOMMIT の接続を開いて流す（B3 で SET ROLE したままの接続から消さないため）。

## 3. 確かめ（クラウドで実行し、生の出力を報告に貼る）
- V1 `grep -c 'CREATE TABLE' backend/tests/test_tenant_isolation_daily_check.py` が 0。`BASE_SHA=$(git merge-base origin/main HEAD) HEAD_SHA=$(git rev-parse HEAD) python3 scripts/check_test_schema_dup.py` の終了コードが 0。
- V2 `grep -c 'SELECT c.relname' scripts/check_public_tenant_rls.py` が 0、`grep -rn 'SELECT c.relname' backend/app scripts` が backend/app/ops/tenant_rls_checks.py の 1 件だけ。
- V3 `cd backend && python3 -c "from app.celery_app import celery_app as c; e=c.conf.beat_schedule['tenant-isolation-daily-check']; print(e['task'], e['schedule'])"` の出力に `app.tasks.tenant_isolation_daily_check.run_tenant_isolation_daily_check` と `<crontab: 5 9 * * *` が出る。
- V4 `cd backend && python3 -c "from app.ops.tenant_rls_allowlist import BYPASSRLS_ROLES as B; print(B)"` が `{}`。
- V5 `cd backend && ruff check app/ops/tenant_rls_checks.py app/tasks/tenant_isolation_daily_check.py tests/test_tenant_isolation_daily_check.py` と、同じ 3 ファイルの `ruff format --check` がどちらも 0（ruff が入っていなければ「未実行」と書く）。既存の 2 ファイルは format の確かめに入れない。
- V6 `cd backend && python3 -m pytest -q tests/test_tenant_isolation_daily_check.py tests/test_check_public_tenant_rls.py tests/test_master_required_fields_monitor.py`。A の試験が全部通ること。PostgreSQL が使えるなら RLS_ADMIN_DATABASE_URL に使える接続先を入れて B も通すこと。使えなければ B は skip のままでよく、「B は未実行（PostgreSQL なし）」と書く（CI の pytest で確かめる）。
- V7 自分のコミットを `git log -1 --format=%H` で確かめ、`git diff --name-only HEAD~1 HEAD` が「1. 触るファイル」の 6 件だけ。`git diff HEAD~1 HEAD -- .github/workflows/migration-test.yml` が足した 1 行だけ。

## 4. 終わったら
- コミットは 1 つ（メッセージ: `feat(ops): daily tenant isolation check to admin Discord (ADR-1063 bin6)`）。push する。PR は作らない。
- 報告の最後の行は `DONE`、または `BLOCKED:` に続けて理由、または `NEEDS_DECISION:` に続けて問い。
- 停止するとき（実装前点検が外れた・確かめが期待と違う・カードに無い判断が要る）は、そこで作業を止め、報告の最後の行を `BLOCKED:` か `NEEDS_DECISION:` にして Opus に返す。推測で続けない。

END OF CARD
