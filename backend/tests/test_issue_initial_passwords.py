"""初回パスワード発行スクリプト（ADR-1013 便4b）のテスト。

SQLite 版: 件数・書き込み・2 回目 0 件・全取り消し・平文が残らないこと（K11）。
PostgreSQL 版（RLS）: RLS_TEST_DATABASE_URL（salesanchor_app 接続）が無いと skip（F26）。
どの試験も外側の取引を commit せず、最後に取り消す（DB に行を残さない）。
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.auth.passwords import verify_password
from scripts import issue_initial_passwords as mod

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest_asyncio.fixture
async def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "USERS_TABLE", "users_t")
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'u.db'}")
    async with eng.connect() as c:
        await c.execute(text(
            "CREATE TABLE users_t (id INTEGER PRIMARY KEY, email TEXT, is_active BOOLEAN,"
            " password_argon2_hash TEXT, password_changed_at TIMESTAMP,"
            " failed_login_count INTEGER DEFAULT 0, locked_until TIMESTAMP)"
        ))
        await c.execute(text(
            "INSERT INTO users_t (id, email, is_active, password_argon2_hash) VALUES "
            "(1,'a@example.com',1,NULL),(2,'b@example.com',1,NULL),"
            "(3,'c@example.com',0,NULL),(4,'d@example.com',1,'$argon2id$existing')"
        ))
        await c.commit()  # 試験の土台（一時ファイルの DB）。試験本体の書き込みは commit しない
        yield c
        await c.rollback()
    await eng.dispose()


async def _hashes(c):
    return dict((await c.execute(text("SELECT id, password_argon2_hash FROM users_t"))).all())


async def test_dry_run_returns_count_and_writes_nothing(conn):
    n, issued = await mod.issue(conn, apply=False)
    assert n == 2 and issued == []
    h = await _hashes(conn)
    assert h[1] is None and h[2] is None and h[3] is None and h[4] == "$argon2id$existing"


async def test_apply_issues_for_each_target_and_second_run_is_zero(conn):
    n, issued = await mod.issue(conn, apply=True)
    assert n == 2 and len(issued) == 2
    h = await _hashes(conn)
    for uid, _email, plain in issued:
        assert len(plain) == 20
        assert verify_password(h[uid], plain)
    assert h[3] is None and h[4] == "$argon2id$existing"  # 停止中・設定済みは触らない
    n2, issued2 = await mod.issue(conn, apply=True)
    assert n2 == 0 and issued2 == []


async def test_abort_when_an_update_hits_zero_rows_and_rollback_undoes_all(conn):
    # id 1 を更新すると id 2 が別の値で埋まる仕掛け → id 2 の UPDATE が 0 行になる
    await conn.execute(text(
        "CREATE TRIGGER t_fill AFTER UPDATE OF password_argon2_hash ON users_t "
        "WHEN NEW.id = 1 BEGIN UPDATE users_t SET password_argon2_hash = 'x' WHERE id = 2; END"
    ))
    with pytest.raises(mod.IssueAborted):
        await mod.issue(conn, apply=True)
    await conn.rollback()  # main がやること
    h = await _hashes(conn)
    assert h[1] is None and h[2] is None


async def test_no_plaintext_in_logs_or_files(conn, caplog, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with caplog.at_level(logging.DEBUG):
        _n, issued = await mod.issue(conn, apply=True)
    assert len(issued) == 2
    for _uid, _email, plain in issued:
        assert plain not in caplog.text
        for f in tmp_path.rglob("*"):
            if f.is_file():
                assert plain.encode() not in f.read_bytes()


def test_module_runs_with_dash_m_and_help():
    r = subprocess.run(
        [sys.executable, "-m", "scripts.issue_initial_passwords", "--help"],
        cwd=BACKEND_DIR, capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "--apply" in r.stdout


def test_main_without_apply_prints_count_to_stderr_only(tmp_path, monkeypatch, capsys):
    import sqlite3
    db = tmp_path / "m.db"
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE users_t (id INTEGER PRIMARY KEY, email TEXT, is_active BOOLEAN, password_argon2_hash TEXT)")
    c.execute("INSERT INTO users_t VALUES (1,'a@example.com',1,NULL)")
    c.commit()
    c.close()
    monkeypatch.setattr(mod, "USERS_TABLE", "users_t")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    assert mod.main([]) == 0
    cap = capsys.readouterr()
    assert cap.out == "" and "1" in cap.err
    c = sqlite3.connect(db)
    assert c.execute("SELECT password_argon2_hash FROM users_t").fetchone()[0] is None
    c.close()


# ── RLS（PostgreSQL・salesanchor_app 接続）。F26 の型 ─────────────────────
_APP_URL = os.getenv("RLS_TEST_DATABASE_URL")
_rls = pytest.mark.skipif(not _APP_URL, reason="RLS_TEST_DATABASE_URL が未設定（PostgreSQL 専用テスト）")
_IDS = (910001, 910002)


@_rls
async def test_rls_operator_context_required_then_applied_then_second_run_zero():
    """K7。外側の取引の中で、試験用の利用者を作り、確かめたら最後に取り消す（行は残らない）。"""
    eng = create_async_engine(_APP_URL, connect_args={"prepared_statement_cache_size": 0})
    try:
        async with eng.connect() as c:
            await c.begin()
            try:
                await c.execute(text("SELECT set_config('app.is_operator', 'true', true)"))
                for i, uid in enumerate(_IDS, 1):
                    await c.execute(
                        text(
                            "INSERT INTO public.users (id, tenant_id, username, email, is_active) "
                            "VALUES (:id, 999, :u, :e, true)"
                        ),
                        {"id": uid, "u": f"b4b-rls-{i}", "e": f"b4b-rls-{i}@example.com"},
                    )
                # 運営の文脈なし → UPDATE が 0 行 → 中止
                await c.execute(text("SELECT set_config('app.is_operator', '', true)"))
                await c.execute(text("SELECT set_config('app.tenant_id', '', true)"))
                with pytest.raises(mod.IssueAborted):
                    await mod.issue(c, apply=True, operator_context=False)
                # 運営の文脈あり → 試験用の 2 人を含めて書ける
                n, issued = await mod.issue(c, apply=True)
                emails = [e for _i, e, _p in issued]
                assert n >= 2 and len(issued) == n
                assert "b4b-rls-1@example.com" in emails and "b4b-rls-2@example.com" in emails
                # 2 回目は 0 件
                n2, issued2 = await mod.issue(c, apply=True)
                assert n2 == 0 and issued2 == []
            finally:
                await c.rollback()
    finally:
        await eng.dispose()
