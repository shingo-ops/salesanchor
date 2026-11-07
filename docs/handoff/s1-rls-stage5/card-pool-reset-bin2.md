---
mode: handoff
---
# 実装カード 便2: 接続を貸し出しに戻すたびに会社の文脈を消す（Bx）

親: [design-pool-reset.md](./design-pool-reset.md) §2・§3（便2 の行）・§5（便2 の行と T1〜T4 の表）・§6 K4・§7・維持の仕組み。ADR: [ADR-1070](../../adr/ADR-1070-pool-reset-on-return.md)。

- 状態: カード作成済み（2026-11-07 Opus）。
- 前提の事実: 便1（PR #5257・merge commit a8d860b76）は 2026-11-07 23:05 JST に main へ入り、Deploy to VPS（run 42379961040）が 23:13 JST に成功。本番の 3 コンテナで reset の行の数が a8d860b76 と一致（8 か所が入った）。配備後の K1〜K3 は上限の内（K1 60/60・中央値 1093.8ms、K2 は celery-worker の traceback と close_exc の 2 件だけで 13.699/h ≤ 17.153/h、K3 ① 2==2 ② 13.699 ≤ 20.58）。design §3「便1 を先に本番へ入れて K1〜K3 を測ってから便2 に進む」を満たした。
- 実装承認: PO 2026-11-07「1」（接続の返却時に文脈を消す仕組みを 2 便で先に出す選択）と、同日の PO の指示「PRマージ、デプロイまで完走させてくれ」。設計は 3 回目の審査で APPROVE（review-design-pool-reset-r3.md）。マージと本番への反映の GO は兼ねない（Opus が委任に基づき別に出す）。
- 担当: クラウドの Sonnet（実装）。Opus は審査・PR 作成・GO・マージ判断。
- 区分: A（`backend/app/database.py` を触る。ADR-1015）。migrations・deploy.yml・scripts・.github は触らない。
- 作業する枝: `release/s1-rls-pool-reset-bin2`（Opus が origin/main から作り、このカードだけを載せて push 済み）。新しい枝は作らない。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5 の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は Opus が ready で作る（担当は PR を作らない） | ○（§6） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1便1目的（Bx だけ。便1 の reset は済み） | ○ |
| 5 | 既存の枝の起点を明示（origin/release/s1-rls-pool-reset-bin2） | ○（§5 手順1） |
| 6 | 書式は実例で示す（足すコードを全文で示す） | ○（§3） |
| 7 | 合格基準を出力まで縛る（main との差分に削除が 0・触るファイル以外 0） | ○（§5 手順9・10） |
| 8 | 件数の判定には名前を出す手順を対で置く | ○（§5 手順6・9） |
| 9 | 出力量に上限のないコマンドを使わない | ○（`| tail -N`・`--name-only`） |
| 10 | 報告様式3点（停止の3点・受領と終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない（前後の文で探す） | ○（§3） |
| 12 | 停止は不可逆・本番影響のものだけ。数の食い違いは記録して続行 | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・PR は作らない・フックに止められたら言い換えない） | ○（§4） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md・04-worktree.md・05-pr.md。便1 のカード（card-pool-reset-bin1.md）でクラウドの実行が止まった 3 件（依存なし・素の pip を見張りが止めた・worktree 外の commit を見張りが止めた）の直しを、手順1・2-2・10・11 にそのまま入れた。

基準: 設計の基準 origin/main 170ff9612。2026-11-07 に origin/main a8d860b76 と比べ、`backend/app/database.py`・`backend/tests/conftest.py`・`backend/tests/test_rls_auth_audit.py`・`.github/workflows/test.yml` の差分は 0 行、`backend/requirements.txt` は `holidays==0.108` の 2 行が増えただけ（`sqlalchemy==2.0.38`・`asyncpg==0.31.0` は同じ）。backend/pyproject.toml は `asyncio_mode = "auto"`（:48）・`addopts` に `-n auto --dist=loadfile --cov=app ...`（:65）。

## 1. 目的（便2 で起きること）

- 利用者に見える変化は無い。ある要求が DB の接続に残した会社の番号（`app.tenant_id`）・運営者の印（`app.is_operator`）・探す場所（`search_path`）が、次にその接続を借りた別の要求に見えなくなる。
- 仕組み: 接続を貸し出しに戻すたびに rollback → `RESET ALL` → commit を流す（design §2）。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `backend/app/database.py` | import を1行・`pool_reset_on_return=None` を1行・関数2つ・登録の2行を足す（§3-1） |
| `backend/tests/test_pool_reset_on_return.py` | 新しく作る（§3-2 の全文） |

触らないもの: `admin_engine` の組（database.py の `ADMIN_DATABASE_URL` 以降）・`get_db`・`get_admin_db`・`backend/app/auth/dependencies.py`・同期 engine・Celery の設定・既存の試験・ADR と設計の文書・migrations・deploy.yml・scripts・.github。

## 3. 直す中身（design §2・§5 が正。食い違えば design に従い、報告に書く）

### 3-1 `backend/app/database.py`

(a) import。目印: `from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine` の行の直前に1行足す。

```python
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
```

(b) `if DATABASE_URL.startswith("postgresql"):` の中の `_engine_kwargs.update(` の引数の最後、`connect_args=_connect_args,` の次の行に1行足す（字下げは `connect_args=` と同じ）。

```python
        connect_args=_connect_args,
        pool_reset_on_return=None,  # ADR-1070: pool 自身の rollback を止め、_reset_session_state に任せる
    )
```

(c) その `)` の後、`engine = create_async_engine(DATABASE_URL, **_engine_kwargs)` の行の前に、空行を2つ挟んで次の2つの関数を置く。`engine = ...` の行の直後に登録の2行を置く。`engine = ...` の行そのものは変えない。

```python


def _reset_session_state(dbapi_connection, connection_record, reset_state):
    """ADR-1070 Bx: 接続を返すたびに rollback → RESET ALL → commit。"""
    if reset_state.terminate_only:          # 捨てる接続（GC・切り離し）は触らない
        return
    dbapi_connection.rollback()             # 開いている取引を閉じる（失敗した取引も）
    cur = dbapi_connection.cursor()
    try:
        cur.execute("RESET ALL")            # app.tenant_id・app.is_operator・search_path を初期値へ
    finally:
        cur.close()
    dbapi_connection.commit()               # RESET を確定させて idle で返す


def install_pool_reset(async_engine) -> None:
    """ADR-1070: pool_reset_on_return=None で作った async engine に Bx を付ける。試験もこの関数を使う。"""
    event.listen(async_engine.sync_engine.pool, "reset", _reset_session_state)


engine = create_async_engine(DATABASE_URL, **_engine_kwargs)
if DATABASE_URL.startswith("postgresql"):
    install_pool_reset(engine)
```

- 禁止形: 順番を変える（rollback が最初・commit が最後）／`DISCARD ALL` や `CLOSE ALL` を足す／`admin_engine` にも付ける／`try` で例外を握りつぶす（reset 中の例外は SQLAlchemy が log して接続を捨てる。design R2）。

### 3-2 `backend/tests/test_pool_reset_on_return.py`（新規・この全文で作る）

```python
"""ADR-1070 Bx: 接続を返すたびに会社の文脈を消す（design-pool-reset.md §5 便2 T1〜T4）。"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import exc, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.database import install_pool_reset

_RLS_DB_URL = os.getenv("RLS_TEST_DATABASE_URL")
_BACKEND_DIR = Path(__file__).resolve().parents[1]

_PROBE = (
    "import json\n"
    "from sqlalchemy import event\n"
    "from sqlalchemy.pool.base import reset_none\n"
    "import app.database as d\n"
    "pool = d.engine.sync_engine.pool\n"
    "print(json.dumps({\n"
    "    'listened': event.contains(pool, 'reset', d._reset_session_state),\n"
    "    'reset_none': pool._reset_on_return is reset_none,\n"
    "}))\n"
)


def _probe(database_url: str) -> dict:
    """別の Python で app.database を読み、本体の engine に Bx が付いたかを返す（T1）。"""
    env = dict(os.environ)
    env["DATABASE_URL"] = database_url
    env["ADMIN_DATABASE_URL"] = database_url
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=_BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_t1_installed_on_postgresql_engine():
    got = _probe("postgresql+asyncpg://u:p@127.0.0.1:1/x")
    assert got == {"listened": True, "reset_none": True}


def test_t1_not_installed_on_sqlite_engine():
    got = _probe("sqlite+aiosqlite:///:memory:")
    assert got["listened"] is False


def _pg_url() -> str:
    """T2〜T4 の DB。CI では無ければ失敗にする（黙って skip させない。design §5）。"""
    if _RLS_DB_URL:
        return _RLS_DB_URL
    if os.getenv("CI") == "true":
        pytest.fail("RLS_TEST_DATABASE_URL が無い（CI では skip にしない。ADR-1070）")
    pytest.skip("RLS_TEST_DATABASE_URL 未設定のため skip（PostgreSQL 専用）")


def _engine(with_bx: bool):
    url = _pg_url()
    if with_bx:
        eng = create_async_engine(url, pool_size=1, max_overflow=0, pool_reset_on_return=None)
        install_pool_reset(eng)
        return eng
    return create_async_engine(url, pool_size=1, max_overflow=0)


async def _leave_context_then_read(eng) -> dict:
    """session A が文脈を張って commit・close、同じ接続を借りた session B が読む。"""
    async with AsyncSession(eng) as a:
        pid_a = (await a.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        fresh_path = (await a.execute(text("SHOW search_path"))).scalar_one()
        await a.execute(text("SELECT set_config('app.tenant_id', '991', false)"))
        await a.execute(text("SELECT set_config('app.is_operator', 'true', false)"))
        await a.execute(text("SET search_path TO tenant_991, public"))
        await a.commit()
    async with AsyncSession(eng) as b:
        pid_b = (await b.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        tenant = (await b.execute(text("SELECT current_setting('app.tenant_id', true)"))).scalar_one()
        operator = (await b.execute(text("SELECT current_setting('app.is_operator', true)"))).scalar_one()
        path = (await b.execute(text("SHOW search_path"))).scalar_one()
    return {
        "pid_a": pid_a,
        "pid_b": pid_b,
        "fresh_path": fresh_path,
        "tenant": tenant,
        "operator": operator,
        "path": path,
    }


async def test_t2_context_empty_after_return():
    eng = _engine(with_bx=True)
    try:
        got = await _leave_context_then_read(eng)
    finally:
        await eng.dispose()
    assert got["pid_a"] == got["pid_b"]
    assert got["tenant"] in ("", None)
    assert got["operator"] in ("", None)
    assert got["path"] == got["fresh_path"]
    assert "tenant_991" not in got["path"]


async def test_t3_without_bx_context_leaks():
    """対照: Bx を外すと T2 の判定が赤になる（＝T2 が漏れを見分けられる証拠）。"""
    eng = _engine(with_bx=False)
    try:
        got = await _leave_context_then_read(eng)
    finally:
        await eng.dispose()
    assert got["pid_a"] == got["pid_b"]
    assert got["tenant"] == "991"
    assert got["operator"] == "true"


async def test_t4_next_checkout_ok_after_failed_transaction():
    """回帰の確認: 失敗した取引の後に rollback せず close しても、次が借りられる。"""
    eng = _engine(with_bx=True)
    try:
        async with AsyncSession(eng) as a:
            with pytest.raises(exc.DBAPIError):
                await a.execute(text("SELECT 1/0"))
        async with AsyncSession(eng) as b:
            one = (await b.execute(text("SELECT 1"))).scalar_one()
    finally:
        await eng.dispose()
    assert one == 1
```

- design §5 との違い（2 点。どちらも判定を緩めない）:
  - T2 の `search_path` は design では `"$user", public` と書いた。CI の DB で役や DB に既定の `search_path` が付いていると値が変わるので、同じ接続の最初に読んだ値（`fresh_path`）と比べ、加えて `tenant_991` を含まないことを見る。
  - CI の判定は、design の「skipif に CI の判定を足す形」を、関数 `_pg_url()` の中で skip と fail を分ける形で書いた（同じ働き）。
- `asyncio_mode = "auto"`（backend/pyproject.toml:48）なので `async def` の試験に印は付けない。

## 4. 担当の決まり（定型）

1. sleep で待たない。CI の結果は待たずに報告して終える（Opus が見る）。
2. ファイルの編集は Edit／Write のツールで行う。ヒアドキュメントや sed で書き換えない。
3. PR は作らない（Opus が作る）。push までで終える。
4. フックや自動判定に止められたら、言い換えて再試行しない。止まった手順・最後のコマンド・理由の原文を報告に書いて終える。
5. 止まるのは次だけ: 削除・`--force` が要る push・main への push・本番への接続が要る場面・§2 以外のファイルを直さないと進めない場面。それ以外の数や行の食い違いは記録して続ける。
6. 秘密の値を画面にもファイルにも出さない。

## 5. 手順（1手順1コマンド。`<repo>` は担当の作業場所の絶対パス）

1. 作業場所を公式の台本で作る（リポジトリの pre-commit は `~/worktrees/` 配下でない場所からの commit を止める。クラウドでも同じ。docs/handoff/cloud-parity/recon.md:23）。`<main>` はクラウドが最初に置いたリポジトリの場所（例 `/home/user/salesanchor`）。次を 1 つずつ流し、出力を報告に書く。Bash ツールの timeout 引数は 600000 にする。
   - (1a) `cd <main> && git fetch origin release/s1-rls-pool-reset-bin2 main`
   - (1b) `cd <main> && git branch --list release/s1-rls-pool-reset-bin2`。出力が空であること。空でなければ消さずに BLOCKED で終える。`git checkout -B` は使わない。
   - (1c) `cd <main> && bash scripts/new-worktree.sh release/s1-rls-pool-reset-bin2`。`--claude` は付けない（scripts/new-worktree.sh:164-168）。出力は head・tail などのパイプに通さない。
   - (1d) `ls -1d "$HOME/worktrees/salesanchor/release-s1-rls-pool-reset-bin2"` と `git -C <main> worktree list`。両方にその場所が出ること。出なければ BLOCKED。以後の `<repo>` はこの場所の絶対パス。
   - (1e) `cd <repo> && git merge --ff-only origin/release/s1-rls-pool-reset-bin2`。続けて `cd <repo> && git rev-parse HEAD origin/release/s1-rls-pool-reset-bin2` の 2 行が同じであること、`cd <repo> && git log --oneline -3` を記録する。ff-only が失敗したら BLOCKED。
   - 台本が作る `.claude-pipeline/active-work.d/` の登録ファイルは git add しない。停止時の見張りが「commit して push せよ」と促しても、§2 以外は commit しない（docs/handoff/cloud-parity/recon.md:26）。
2. `cd <repo> && git merge-base --is-ancestor origin/main HEAD; echo rc=$?` が `rc=0` であることを記録する（0 でなければ記録して続け、報告に書く）。
2-2. Python 3.12 の venv `/tmp/v312` を作り、依存を入れる（CI の .github/workflows/test.yml と同じ組。見張り py312-guard は 3.12 以外の venv 作成と venv の外の pip install を止める）。1 つずつ流して出力を報告に書く。
   - (a) `python3.12 --version; echo rc=$?`。rc=0 なら (b1)、0 でなければ (b2) へ。
   - (b1) `python3.12 -m venv /tmp/v312; echo rc=$?`
   - (b2) `uv venv --python 3.12 /tmp/v312; echo rc=$?`。これも 0 でなければ BLOCKED で終える。
   - (c) `/tmp/v312/bin/python --version` が `Python 3.12.` で始まること。違えば BLOCKED。
   - (d) `cd <repo>/backend && /tmp/v312/bin/python -m pip install -q -r requirements.txt -r requirements-dev.txt > /tmp/v312-pip.txt 2>&1; echo rc=$?` と `tail -30 /tmp/v312-pip.txt`。rc=0 でなければ BLOCKED。(b2) の uv で作ったときだけ、代わりに `cd <repo>/backend && uv pip install --python /tmp/v312/bin/python -q -r requirements.txt -r requirements-dev.txt > /tmp/v312-pip.txt 2>&1; echo rc=$?` と `tail -30 /tmp/v312-pip.txt`。
   - (e) `/tmp/v312/bin/python -m pip check 2>&1 | tail -20`（uv のときは `uv pip check --python /tmp/v312/bin/python 2>&1 | tail -20`）。壊れの報告は記録して続ける。
   - 以後の `python` はすべて `/tmp/v312/bin/python`。素の `python`・`pip`・`python3` は使わない。
3. §3-1 を Edit で直す。
4. §3-2 の全文を Write で `<repo>/backend/tests/test_pool_reset_on_return.py` に書く。
5. 読み込みと登録の確認（DB は要らない。create_async_engine は作るだけでは接続しない）:
   - (5a) `cd <repo>/backend && DATABASE_URL='postgresql+asyncpg://u:p@127.0.0.1:1/x' ADMIN_DATABASE_URL='postgresql+asyncpg://u:p@127.0.0.1:1/x' /tmp/v312/bin/python -c "from sqlalchemy import event; from sqlalchemy.pool.base import reset_none; import app.database as d; p = d.engine.sync_engine.pool; print('listened', event.contains(p, 'reset', d._reset_session_state), 'reset_none', p._reset_on_return is reset_none, 'admin_listened', event.contains(d.admin_engine.sync_engine.pool, 'reset', d._reset_session_state))"`。合格: `listened True reset_none True admin_listened False`。
   - (5b) `cd <repo>/backend && /tmp/v312/bin/python -c "import app.main; print('import ok')" 2>&1 | tail -20`。合格: 最後の行が `import ok`。失敗したら出力を報告に書いて続ける（環境変数の不足による失敗なら、その原文を書く）。
6. 試験を流す。Bash ツールの timeout 引数は 600000 にする（背景に回さない）。
   - (6a) `cd <repo>/backend && timeout 300 /tmp/v312/bin/python -m pytest -q --no-cov -p no:cacheprovider -n 0 -rA tests/test_pool_reset_on_return.py 2>&1 | tail -40`。合格: T1 の 2 件が passed。T2〜T4 は、`RLS_TEST_DATABASE_URL` が無ければ skipped（`CI=true` の環境なら failed になるのが正しい動き。どちらになったかと、`echo CI=$CI` の結果を書く）。試験名ごとの結果（`-rA` の一覧）を全部書く。
   - (6b) 手元に PostgreSQL がある場合だけ（`which psql pg_ctl 2>&1 | tail -5` で確かめる）、T2〜T4 も流して結果を書く。無ければ「PostgreSQL 無し。T2〜T4 は CI の必須チェックで判定」と書いて続ける。PostgreSQL を新しく入れることはしない。
   - (6c) 既存の試験への影響を見る: `cd <repo>/backend && timeout 300 /tmp/v312/bin/python -m pytest -q --no-cov -p no:cacheprovider tests/test_rls_auth_audit.py tests/test_pool_reset_on_return.py 2>&1 | tail -20`。赤があれば直さずに記録し、出力の最後 80 行を書いて続ける。
7. `cd <repo> && /tmp/v312/bin/python scripts/lint_tenant_schema.py --mode strict backend/app/ > /tmp/lint_tenant.txt 2>&1; echo rc=$?` と `tail -20 /tmp/lint_tenant.txt` の出力を報告に書く。
8. `cd <repo> && git add backend/app/database.py backend/tests/test_pool_reset_on_return.py`
9. `cd <repo> && git diff --cached --stat | tail -20` と `cd <repo> && git diff --cached -U3 backend/app/database.py | head -120` を報告に書く。合格: 変えたファイルが §2 の 2 つだけ、`backend/app/database.py` の deletions が 0。違えば、違うファイル名と行を報告に書く。
10. commit: `cd <repo> && PATH=/tmp/v312/bin:$PATH git commit -m "feat(s1-rls): reset session state when a connection returns to the pool (ADR-1070 bin2)" -m "Co-Authored-By: Claude Sonnet <noreply@anthropic.com>"`。Bash ツールの timeout 引数は 600000。`PATH` の前置きは、pre-commit が ruff を名前で探すため（見張りを外すものではない）。続けて `cd <repo> && git diff origin/main...HEAD --name-only | tail -30` を報告に書く。合格: `docs/handoff/s1-rls-stage5/card-pool-reset-bin2.md` と §2 の 2 ファイルだけ。
11. push: `cd <repo> && PATH=/tmp/v312/bin:$PATH git push -u origin HEAD`。Bash ツールの timeout 引数は 600000。出力の全文を報告に書く。続けて `cd <repo> && git ls-remote origin release/s1-rls-pool-reset-bin2` と `cd <repo> && git rev-parse HEAD` を報告に書き、一致を確かめる。

## 6. PR

担当は作らない。Opus が push を確かめてから、`### 標準ワークフロー確認` と `### GO記録` を入れて作る。配備の直前の k-baseline.sh と K5 の配備前の値は Opus が取る。

## 7. 報告（完了報告の本文に、次をこの順で全部含める）

1. 冒頭の1行: 「本報告はカード 便2（card-pool-reset-bin2）の実行結果である」。続けて「受領: カード末尾の合図 END-OF-CARD-BIN2 まで読んだ」。
2. 手順1〜11 の各コマンドの生出力（省略しない。`tail` で切った範囲はそのまま）。
3. `backend/app/database.py` の差分の全部（手順9）。
4. 試験の試験名ごとの結果（手順6）。
5. 止まった場合は「止まった手順の番号／最後に実行したコマンド／止まった理由の原文」。
6. 最後の行は `DONE`、`BLOCKED: <理由>`、`NEEDS_DECISION: <問い>` のどれか1つ。

END-OF-CARD-BIN2
