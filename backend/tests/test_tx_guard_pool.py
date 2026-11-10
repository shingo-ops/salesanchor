"""試しの道具の接続上限が、本物のプールの返却・作り直しを通しても残ることの試験（本物の PostgreSQL・CI 専用）。

設計: docs/handoff/replay-tx-release/design.md §14 K5'
"""
from __future__ import annotations

from unittest.mock import MagicMock

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from app.tools import _tx_guard
from app.tools._tx_guard import IDLE_TX_LIMIT_SECONDS, install_idle_tx_listener, set_idle_tx_limit
from tests.test_tcg_work_matching_integration import pg as pg_fixture

pg = pg_fixture  # 共有 fixture（本物の migration 済み DB。CI 専用）

_EXPECTED = f"{IDLE_TX_LIMIT_SECONDS}s"


def _read(engine):
    """接続を取り、pid と上限の値を読んで返す。"""
    with engine.connect() as conn:
        pid = conn.execute(text("SELECT pg_backend_pid()")).scalar()
        value = conn.execute(text("SHOW idle_in_transaction_session_timeout")).scalar()
    return pid, value


def test_limit_survives_pool_return_and_invalidate_on_real_postgres(pg):
    _conn, _pg_engine, url = pg
    engine = create_engine(url.set(drivername="postgresql+psycopg2"), pool_size=1, max_overflow=0)
    install_idle_tx_listener(engine)
    try:
        pid1, value1 = _read(engine)
        assert value1 == _EXPECTED

        pid2, value2 = _read(engine)
        assert pid2 == pid1  # プールの使い回し
        assert value2 == _EXPECTED

        with engine.connect() as conn:
            conn.invalidate()
        pid3, value3 = _read(engine)
        assert pid3 != pid2  # 新しい接続
        assert value3 == _EXPECTED
    finally:
        event.remove(engine, "connect", _tx_guard._on_connect_set_idle_limit)
        engine.dispose()


def test_listener_registered_once_on_real_engine_on_real_postgres(pg, monkeypatch):
    _conn, _pg_engine, url = pg
    engine = create_engine(url.set(drivername="postgresql+psycopg2"), pool_size=1, max_overflow=0)
    listen_spy = MagicMock(wraps=event.listen)
    monkeypatch.setattr(_tx_guard.event, "listen", listen_spy)
    try:
        with Session(engine) as s:
            set_idle_tx_limit(s)
            set_idle_tx_limit(s)
        assert event.contains(engine, "connect", _tx_guard._on_connect_set_idle_limit)
        assert listen_spy.call_count == 1
    finally:
        event.remove(engine, "connect", _tx_guard._on_connect_set_idle_limit)
        engine.dispose()
