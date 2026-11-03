# 予定表の前提の不具合直しの実装カード（シフトの読み込み・登録で、日付と時刻を文字のまま DB に渡してサーバーの誤り（500）になるのを直す）

- 対象: docs/handoff/line-like-speed/design.md §3-4-20。ADR-1054 段 3 の 7 回目（予定表 /schedule）の前提。速さの直しではなく、範囲の外の不具合直し（docs/STANDARD-WORKFLOW.md §5「低リスクのコード」の自律クラフト。記録は design §3-4-20）。
- 根拠の写し: S=origin/main 17c791b711064a5c772a3ca3535f2965d8a4d206。行番号はすべてこの sha。
- 実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。PR は作らない。出力には上限を付ける。待つために sleep を使わない。
- 状態: 第 1 版（2026-11-04 設計担当 Claude Opus）。
- 受領確認: 実装役は着手の最初の報告に「シフトの直しのカード 第 1 版を受け取った・S=17c791b71」と書く。

## 0. 観測した事実（設計担当とクラウドの調べ担当が確かめた）
- F1 本番の GET /api/v1/shifts?date_from&date_to が 500（design §3-4 の予定表の基準の回・design.md:274）。
- F2 S backend/app/routers/shifts.py:52-53 は date_from・date_to を `str` で受け、:63・:65 で text() の :df・:dt にそのまま渡す。表の shift_date は DATE（S migrations/011_add_phase5_tenant_tables.sql:12）、start_time・end_time は TIME（:13-14）、created_at は TIMESTAMPTZ（:17）。接続は postgresql+asyncpg（S backend/app/database.py:8）。
- F3 クラウドの調べ担当（2026-11-04 00:05 JST・origin/main ea5c0faf8）が、本番と同じ版（asyncpg 0.31.0・SQLAlchemy 2.0.38・pydantic 2.10.6・PostgreSQL 16.15）の使い捨て PostgreSQL で再現した。str の '2026-11-01' を渡すと `asyncpg.exceptions.DataError: invalid input for query argument $1: '2026-11-01' ('str' object has no attribute 'toordinal')`。datetime.date を渡すと通る。
- F4 同じ調べで、S shifts.py:33-42 の ShiftResponse（shift_date・start_time・end_time・created_at が str）に、DB が返す datetime.date を入れると `ValidationError: Input should be a valid string [type=string_type]`。本番の tenant_001 のシフトは 0 行（設計担当が本番の読むだけの道で数えた）なので今は表に出ていないが、1 行でも入ると GET は同じく 500 になる。
- F5 同じく S shifts.py:24-30 の ShiftCreate は shift_date・start_time・end_time を str で受け、:83-84 で DATE・TIME 列へそのまま渡す（F3 と同じ形。登録も PostgreSQL では通らない）。
- F6 今ある試験 S backend/tests/test_shifts.py は SQLite で走る（S backend/tests/conftest.py:18）。試験用の shifts 表は日付・時刻が TEXT（S conftest.py:1313-1326）なので、F3〜F5 は CI で見えない。
- F7 監査の記録（S backend/app/services/audit.py:304-305）は `json.dumps(..., default=str)` で、date・time を入れても通る。
- F8 画面は応答の文字を使う: 予定表は `parseDateTime(shift_date, start_time)`（S frontend/src/pages/schedule/schedule-utils.ts:75-77。"HH:MM" と "HH:MM:SS" の両方を読む）、シフトの画面は値をそのまま表に出す（S frontend/src/pages/shifts/ShiftsPage.tsx:89-105）。送る値は "YYYY-MM-DD" と "HH:MM"（S ShiftsPage.tsx:36）。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | backend/app/routers/shifts.py | 日付・時刻を str で受け、そのまま DB に渡し、str の型で返す | date・time・datetime の型で受けて返す（§4-A） |
| 2 | backend/tests/test_shifts.py | 時刻の応答 "09:00" を確かめる | "09:00:00" を確かめる・誤った日付は 422 を足す（§4-B） |
| 3 | backend/tests/conftest.py | SQLite に time を渡せない | time を "HH:MM:SS" の文字で渡す変換を足す（§4-C の 2 か所） |
| 4 | backend/tests/test_shifts_pg.py | 無い | 新しく作る。本物の PostgreSQL で読み込み・登録を確かめる（§4-D 全文） |
| 5 | docs/handoff/line-like-speed/batch3g-shifts-card.md | 無い | このカード（設計担当。実装役は触らない） |
| 6 | docs/handoff/line-like-speed/design.md | §3-4-19-a まで | §3-4-20 を書き足し済み（設計担当。実装役は触らない） |

## 2. 触らない範囲
- frontend/・migrations/・.github/workflows/・scripts/・deploy.yml は触らない。表の定義は変えない。
- shifts.py の SQL の文・権限（require_permission）・監査の記録・reset_tenant_context・削除（delete_shift）は変えない。
- conftest.py は §4-C の 2 か所だけ。ほかの試験は変えない。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) `git diff --stat 17c791b711064a5c772a3ca3535f2965d8a4d206 origin/main -- backend/app/routers/shifts.py backend/tests/test_shifts.py backend/tests/conftest.py | tail -5` が空か。空でなければ停止して BLOCKED: で出力を報告する。
- (b) §4 の「変更前」の文が、書かれた行にそのままあること。無い・2 か所以上の時は直さずに停止して BLOCKED: で `grep -n` の出力を報告する。
- (c) SQLite の試験（test_shifts.py）が §4-B の後に落ちたら、試験をさらに書き換えて通さない。停止して NEEDS_DECISION: で生の出力を返す。特に、SQLite が返す created_at の文字（"YYYY-MM-DD HH:MM:SS" の形）を datetime として読めずに落ちた時はこの分岐。
- (d) test_shifts_pg.py は GITHUB_ACTIONS=true でしか走らない（今ある *_pg.py と同じ）。クラウドでは skip されることを確かめるだけでよい（skipped と出る）。本物の PostgreSQL での結果は PR の CI の pytest-run で見る（設計担当）。
- (e) 試験の中で生の `SET search_path` を書かない（S backend/app/auth/dependencies.py:360-361 の決まり）。search_path は set_tenant_context で設定する。

## 4-A. #1 backend/app/routers/shifts.py
A1. S :3 と :5 の間（空行の :4）の後に、次の import を足す。変更前（:5）:
```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
```
変更後:
```python
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, status
```
A2. S :26-28。変更前:
```python
    shift_date: str = Field(min_length=10, max_length=10)
    start_time: str = Field(min_length=5, max_length=8)
    end_time: str = Field(min_length=5, max_length=8)
```
変更後（"YYYY-MM-DD"・"HH:MM"・"HH:MM:SS" を今までどおり受ける。形の誤りは 422 になる）:
```python
    shift_date: date
    start_time: time
    end_time: time
```
A3. S :36-38 と :41。変更前:
```python
    shift_date: str
    start_time: str
    end_time: str
```
変更後:
```python
    shift_date: date
    start_time: time
    end_time: time
```
変更前（:41）:
```python
    created_at: str
```
変更後:
```python
    created_at: datetime | None
```
A4. S :52-53。変更前:
```python
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
```
変更後:
```python
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
```
A5. ほかの行（SQL の文・:61-68 の組み立て・:83-85 の渡し方・:93 の model_dump）は変えない。型が変わったので、そのまま date・time が DB に渡る。

## 4-B. #2 backend/tests/test_shifts.py
B1. S :36-37。変更前:
```python
        assert data["start_time"] == "09:00"
        assert data["end_time"] == "18:00"
```
変更後（応答は時刻の型で "HH:MM:SS" になる。本番の PostgreSQL の TIME と同じ形）:
```python
        assert data["start_time"] == "09:00:00"
        assert data["end_time"] == "18:00:00"
```
B2. ファイルの最後（S :71 の後）に、空行 1 行を挟んで次を足す（クラスの中・4 字下げ）:
```python

    async def test_list_shifts_invalid_date_is_422(self, client):
        """日付の形が誤っている時は DB に渡さず 422 を返す"""
        res = await client.get("/api/v1/shifts", params={"date_from": "2026-13-01"})
        assert res.status_code == 422

    async def test_create_shift_invalid_time_is_422(self, client):
        """時刻の形が誤っている時は DB に渡さず 422 を返す"""
        res = await client.post("/api/v1/shifts", json={**_SHIFT_BASE, "start_time": "25:00"})
        assert res.status_code == 422
```

## 4-C. #3 backend/tests/conftest.py
S :272 と :283 の 2 か所（どちらも S :270 の set_sqlite_compat の中）。S の conftest.py は先頭で datetime を import していない（S :14-43 の import に無い）。
C1. 変更前（S :272）:
```python
        import sqlite3
```
変更後:
```python
        import datetime
        import sqlite3
```
C2. 変更前（S :283）:
```python
        sqlite3.register_adapter(list, json.dumps)
```
変更後（date と datetime は sqlite3 の今の扱いのまま）:
```python
        sqlite3.register_adapter(list, json.dumps)
        # shifts の start_time・end_time（PostgreSQL では TIME）に datetime.time を渡すための互換
        sqlite3.register_adapter(datetime.time, lambda t: t.isoformat())
```

## 4-D. #4 backend/tests/test_shifts_pg.py（新しく作る・全文）
```python
# ruff: noqa: F811
"""シフト API（backend/app/routers/shifts.py）の日付・時刻の受け渡しを実 PostgreSQL で固定する試験（CI の使い捨て PostgreSQL 専用）。

本番の GET /api/v1/shifts?date_from&date_to が 500 だった（asyncpg が DATE 列の引数に str を受け付けない）。
SQLite の試験（test_shifts.py）は日付・時刻の列が TEXT なので見えない。ここでは shifts 表を
migrations/011_add_phase5_tenant_tables.sql の「シフト管理」の区間をそのまま読み込んで作る（表の定義を書き写さない）。

P1: 期間で読むと 200 相当の結果が返り、期間の外の行は入らない・応答の JSON の形
P2: 登録すると DATE・TIME の列に入り、応答は date・time の形
"""
from __future__ import annotations

import asyncio
import os
from datetime import date, time
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.auth.dependencies import set_tenant_context
from app.routers import shifts as router
from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

pytestmark = pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required")

REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE5_PATH = REPO_ROOT / "migrations" / "011_add_phase5_tenant_tables.sql"
TENANT_ID = int(SCHEMA.rsplit("_", 1)[-1])
_SHIFTS_BANNER = "-- === シフト管理 ===\n"
_SHIFTS_END_BANNER = "-- === ERP連携ログ ===\n"


def _shifts_table_sql() -> str:
    text_all = PHASE5_PATH.read_text(encoding="utf-8")
    start = text_all.index(_SHIFTS_BANNER)
    end = text_all.index(_SHIFTS_END_BANNER, start)
    return text_all[start:end].replace("{schema}", SCHEMA).replace("{tenant_id}", str(TENANT_ID))


def _create_shifts(connection) -> None:
    with connection.cursor() as cur:
        cur.execute(_shifts_table_sql())
        cur.execute(
            f"INSERT INTO {SCHEMA}.shifts (tenant_id, user_id, shift_date, start_time, end_time) VALUES "
            f"({TENANT_ID}, 1, '2026-11-02', '09:00', '18:00'), ({TENANT_ID}, 1, '2026-12-01', '10:00', '19:00')"
        )


def _run(pg_fixture, call):
    async def _go():
        engine = create_async_engine(pg_fixture[2])
        try:
            async with AsyncSession(engine) as db:
                await set_tenant_context(db, TENANT_ID)
                return await call(db)
        finally:
            await engine.dispose()

    return asyncio.run(_go())


def test_p1_list_by_period_uses_date_parameters(pg):
    _create_shifts(pg[0])

    async def call(db):
        return await router.list_shifts(
            user_id=None, date_from=date(2026, 11, 1), date_to=date(2026, 11, 7),
            db=db, tenant_id=TENANT_ID, current_user=SimpleNamespace(id=1),
        )

    result = _run(pg, call)
    assert [r.shift_date for r in result] == [date(2026, 11, 2)]
    dumped = result[0].model_dump(mode="json")
    assert dumped["shift_date"] == "2026-11-02"
    assert dumped["start_time"] == "09:00:00"
    assert dumped["end_time"] == "18:00:00"
    assert dumped["created_at"] is not None


def test_p2_create_writes_date_and_time_columns(pg, monkeypatch):
    _create_shifts(pg[0])

    async def _no_audit(**_kwargs):
        return None

    monkeypatch.setattr(router, "record_audit_log", _no_audit)
    data = router.ShiftCreate(user_id=2, shift_date="2026-11-03", start_time="09:00", end_time="18:00")

    async def call(db):
        return await router.create_shift(data=data, db=db, tenant_id=TENANT_ID, current_user=SimpleNamespace(id=1))

    created = _run(pg, call)
    assert created.shift_date == date(2026, 11, 3)
    assert created.start_time == time(9, 0)
    assert created.end_time == time(18, 0)
```

## 4-M. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. クラウドの決まりどおり、作業場所を作り、push 済みの枝の先頭に合わせる（設計担当が §1 #5・#6 を push 済み）。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-batch3g-shifts
  cd <W> && git fetch origin release/line-like-speed-batch3g-shifts
  cd <W> && git switch -C release/line-like-speed-batch3g-shifts origin/release/line-like-speed-batch3g-shifts
  cd <W> && git rev-parse HEAD origin/release/line-like-speed-batch3g-shifts
  （2 行が同じことを確かめる。違えば BLOCKED:。main は取り込まない。reset・rebase・force・merge・pull は使わない）
  cd <W> && git fetch origin main
  cd <W> && git diff --stat 17c791b711064a5c772a3ca3535f2965d8a4d206 origin/main -- backend/app/routers/shifts.py backend/tests/test_shifts.py backend/tests/conftest.py | tail -5
手順2. Python 3.12 の venv を作り、backend の依存を入れる（py312-guard の決まり）。
  cd <W>/backend && python3.12 -m venv /tmp/b3g-venv
  cd <W>/backend && /tmp/b3g-venv/bin/pip install -q -r requirements.txt -r requirements-dev.txt > /tmp/b3g-pip.txt 2>&1
  cd <W> && tail -3 /tmp/b3g-pip.txt
  cd <W>/backend && /tmp/b3g-venv/bin/python -m pytest -q -p no:cacheprovider -o addopts="" tests/test_shifts.py > /tmp/b3g-before.txt 2>&1
  cd <W> && tail -5 /tmp/b3g-before.txt
  （変える前に 6 件 passed であること。）
手順3. §4-A〜§4-D のとおり #1〜#4 を直す・作る。各ファイルを直す前に §4 の「変更前」の文を `grep -n` で確かめる（§3(b)）。
手順4. 試験と lint を流す。
  cd <W>/backend && /tmp/b3g-venv/bin/python -m pytest -q -p no:cacheprovider -o addopts="" tests/test_shifts.py tests/test_shifts_pg.py > /tmp/b3g-after.txt 2>&1
  cd <W> && tail -8 /tmp/b3g-after.txt
  （test_shifts.py の 8 件 passed・test_shifts_pg.py の 2 件 skipped であること。）
  cd <W>/backend && /tmp/b3g-venv/bin/python -m ruff check app/routers/shifts.py tests/test_shifts.py tests/test_shifts_pg.py tests/conftest.py > /tmp/b3g-ruff.txt 2>&1
  cd <W> && tail -5 /tmp/b3g-ruff.txt
  cd <W> && python3.12 scripts/check_test_schema_dup.py > /tmp/b3g-dup.txt 2>&1
  cd <W> && tail -5 /tmp/b3g-dup.txt
  （0 件の指摘であること。引数が要ると言われたら、出力をそのまま報告に書き、その検査は CI に任せる。）
手順5. 変わったファイルが §1 の #1〜#4 だけか確かめる。
  cd <W> && git status --short | head -10
  cd <W> && git diff origin/release/line-like-speed-batch3g-shifts | head -200
手順6. commit する。
  cd <W> && git add backend/app/routers/shifts.py backend/tests/test_shifts.py backend/tests/conftest.py backend/tests/test_shifts_pg.py
  cd <W> && git commit -m "fix: シフトの日付・時刻を型で受けて渡し、PostgreSQLで500になるのを直す（予定表の前提）"
手順7. push する（--no-verify は使わない。push の前の検査が × なら直してから push。fast-forward でないと断られたら BLOCKED:）。
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/line-like-speed-batch3g-shifts
手順8. 報告を返す。PR は作らない。1 つの発言は 600 文字以内で番号付きに分ける。手順ごとの tail の出力（生のまま）と §3(a)〜(e) の結果を書く。最後の行は DONE・BLOCKED: <理由>・NEEDS_DECISION: <理由> のどれか。

## 4. GO と承認・PO の操作
- PO の実装承認: 2026-11-03 PO「つぎを進める」（残りの遅い画面の予定表を直す流れ）。この不具合はその前提で、docs/STANDARD-WORKFLOW.md §5 の低リスクのコード（バグ修正）として設計担当が記録して進める。
- 触るのは backend の画面の受け口 1 個と試験だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。マージは PO の委任に基づき設計担当（Claude Opus）が、審査役の APPROVE と確認がすべて pass の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| C1 | 本物の PostgreSQL で、期間で読める（P1）・登録できる（P2） | PR の CI の pytest-run が success で、そのログに test_shifts_pg.py の 2 件 passed（skipped でない） |
| C2 | SQLite の試験 8 件・全部の試験・lint が通る | /tmp/b3g-after.txt・b3g-ruff.txt と PR の確認がすべて pass |
| C3 | 変わったのは §1 の 6 ファイルだけ。SQL の文・権限・削除は変わっていない | gh pr diff --name-only と diff |
| C4 | マージの後、deploy が成功し、毎朝の画面の記録を手で 1 回動かすと /schedule の 5xx が 0 件 | deploy.yml の結論 success と、prod-ui-check の要約の /schedule の行（設計担当） |
| C5 | 本番で GET /api/v1/shifts?date_from&date_to が 200 で、tenant_001 の 0 行と同じく空の一覧 | C4 の記録の 5xx 0 件と、本番の読むだけの道で tenant_001 のシフトが 0 行のまま（設計担当） |
