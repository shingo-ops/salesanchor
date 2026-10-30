"""初回パスワード発行スクリプト（ADR-1013 便4b）のテスト。

SQLite 版: conftest の users（public.users は users に置き換わる）を使う。表は作らない。
  件数・書き込み・2 回目 0 件・全取り消し・平文が残らないこと（K11）。
  試験の書き込みは commit せず、最後に session.rollback() で取り消す。
PostgreSQL 版（RLS）: test_users_rls.py の使い捨て DB（本物の migration を当てる）を使い回し、
  salesanchor_app の接続で確かめる（F26・K7）。環境変数が無いと skip。
"""
from __future__ import annotations

import logging
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text

from app.auth.passwords import verify_password
from scripts import issue_initial_passwords as mod
from tests.test_users_rls import ADMIN_PG_URL, APP_PG_URL, _TENANT_A, _fresh

BACKEND_DIR = Path(__file__).resolve().parent.parent

# 試験用の利用者（id は DB に採番させる。他の試験の固定 id と重ならない）
_SPEC = {
    "a": (1, None),  # 発行対象
    "b": (1, None),  # 発行対象
    "c": (0, None),  # 停止中
    "d": (1, "$argon2id$existing"),  # 設定済み
}


async def _seed(session):
    """session の取引の中に試験用の利用者を入れる。commit しない。(conn, {名前: id}) を返す。"""
    ids = {}
    for name, (active, h) in _SPEC.items():
        r = await session.execute(
            text(
                "INSERT INTO users (tenant_id, email, is_active, password_argon2_hash) "
                "VALUES (999, :e, :a, :h)"
            ),
            {"e": f"b4b-{name}-{uuid.uuid4().hex}@example.com", "a": active, "h": h},
        )
        ids[name] = r.lastrowid
    return await session.connection(), ids


async def _hashes(conn, ids):
    """自分が入れた id の行だけを見る。"""
    rows = (await conn.execute(
        text("SELECT id, password_argon2_hash FROM users WHERE id IN (:a, :b, :c, :d)"),
        {k: v for k, v in zip("abcd", ids.values())},
    )).all()
    return dict(rows)


async def test_dry_run_returns_count_and_writes_nothing(db_session):
    base, _ = await mod.issue(await db_session.connection(), apply=False)
    conn, ids = await _seed(db_session)
    n, issued = await mod.issue(conn, apply=False)
    assert n == base + 2 and issued == []
    h = await _hashes(conn, ids)
    assert h[ids["a"]] is None and h[ids["b"]] is None and h[ids["c"]] is None
    assert h[ids["d"]] == "$argon2id$existing"
    await db_session.rollback()


async def test_apply_issues_for_each_target_and_second_run_is_zero(db_session):
    conn, ids = await _seed(db_session)
    n, issued = await mod.issue(conn, apply=True)
    assert n == len(issued) and n >= 2
    got = {uid for uid, _e, _p in issued}
    assert {ids["a"], ids["b"]} <= got and not ({ids["c"], ids["d"]} & got)
    h = await _hashes(conn, ids)
    for uid, _email, plain in issued:
        assert len(plain) == 20
        assert verify_password((await conn.execute(
            text("SELECT password_argon2_hash FROM users WHERE id = :i"), {"i": uid})).scalar(), plain)
    assert h[ids["a"]] and h[ids["b"]]  # 自分の対象 2 人に設定された
    assert h[ids["c"]] is None and h[ids["d"]] == "$argon2id$existing"  # 停止中・設定済みは触らない
    n2, issued2 = await mod.issue(conn, apply=True)
    assert n2 == 0 and issued2 == []
    await db_session.rollback()


class _ZeroRowsOnSecondUpdate:
    """2 回目の UPDATE が 0 行だった状況を作る（他者が先に設定した場合）。"""

    def __init__(self, conn):
        self._conn = conn
        self.dialect = conn.dialect
        self._updates = 0

    async def execute(self, stmt, params=None):
        if str(stmt).lstrip().upper().startswith("UPDATE"):
            self._updates += 1
            if self._updates == 2:
                return SimpleNamespace(rowcount=0)
        return await self._conn.execute(stmt, params) if params is not None else await self._conn.execute(stmt)


async def test_abort_when_an_update_hits_zero_rows_and_rollback_undoes_all(db_session):
    conn, ids = await _seed(db_session)
    with pytest.raises(mod.IssueAborted):
        await mod.issue(_ZeroRowsOnSecondUpdate(conn), apply=True)
    await db_session.rollback()  # main がやること
    h = await _hashes(await db_session.connection(), ids)
    assert h == {}  # 試験用の利用者ごと取り消されている（1 人目の書き込みも残らない）
    await db_session.rollback()


async def test_no_plaintext_in_logs_or_files(db_session, caplog, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    conn, _ids = await _seed(db_session)
    with caplog.at_level(logging.DEBUG):
        _n, issued = await mod.issue(conn, apply=True)
    assert len(issued) >= 2
    for _uid, _email, plain in issued:
        assert plain not in caplog.text
        for f in tmp_path.rglob("*"):
            if f.is_file():
                assert plain.encode() not in f.read_bytes()
    await db_session.rollback()


def test_module_runs_with_dash_m_and_help():
    r = subprocess.run(
        [sys.executable, "-m", "scripts.issue_initial_passwords", "--help"],
        cwd=BACKEND_DIR, capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "--apply" in r.stdout


async def test_run_without_apply_prints_count_to_stderr_only_and_writes_nothing(db_session, test_engine, monkeypatch, capsys):
    before = (await (await db_session.connection()).execute(
        text("SELECT count(*) FROM users WHERE password_argon2_hash IS NOT NULL"))).scalar()
    await db_session.rollback()
    # 共有のメモリ DB を使うため、エンジンの作成を差し替え、dispose は何もしない
    shared = SimpleNamespace(connect=test_engine.connect, dispose=AsyncMock())
    monkeypatch.setattr(mod, "create_async_engine", lambda *a, **k: shared)
    assert await mod._run("sqlite+aiosqlite:///:memory:", False) == 0
    cap = capsys.readouterr()
    assert cap.out == "" and "対象" in cap.err
    after = (await (await db_session.connection()).execute(
        text("SELECT count(*) FROM users WHERE password_argon2_hash IS NOT NULL"))).scalar()
    assert after == before
    await db_session.rollback()


# ── RLS（PostgreSQL・salesanchor_app 接続）。test_users_rls.py の使い捨て DB を使い回す ─────
@pytest.mark.skipif(
    not ADMIN_PG_URL or not APP_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL 未設定)。",
)
async def test_rls_operator_context_required_then_applied_then_second_run_zero():
    """K7。使い捨て DB で、運営の文脈なしなら中止、ありなら件数分、2 回目は 0 件。"""
    async with _fresh() as (admin_engine, app_engine):
        async with admin_engine.begin() as c:
            for uid in (9101, 9102):
                await c.execute(
                    text(
                        "INSERT INTO public.users (id, tenant_id, username, email, is_active) "
                        "VALUES (:id, :t, :u, :e, true)"
                    ),
                    {"id": uid, "t": _TENANT_A, "u": f"b4b-{uid}", "e": f"b4b-{uid}@example.com"},
                )
        # 運営の文脈なし → UPDATE が 0 行 → 中止（全部取り消し）
        async with app_engine.connect() as c:
            await c.begin()
            with pytest.raises(mod.IssueAborted):
                await mod.issue(c, apply=True, operator_context=False)
            await c.rollback()
        async with admin_engine.connect() as ac:
            hs = (await ac.execute(text(
                "SELECT count(*) FROM public.users WHERE id IN (9101, 9102) AND password_argon2_hash IS NOT NULL"))).scalar()
            assert hs == 0  # 取り消され、試験用 2 人は NULL のまま
        # 運営の文脈あり → 試験用の 2 人を含めて書ける。2 回目は 0 件
        async with app_engine.connect() as c:
            await c.begin()
            n, issued = await mod.issue(c, apply=True)
            ids = {uid for uid, _e, _p in issued}
            assert n == len(issued) and {9101, 9102} <= ids
            n2, issued2 = await mod.issue(c, apply=True)
            assert n2 == 0 and issued2 == []
            await c.rollback()
