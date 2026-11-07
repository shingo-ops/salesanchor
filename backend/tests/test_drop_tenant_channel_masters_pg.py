"""古い会社ごとの名簿 tenant_NNN.channel_masters を消す migration の PostgreSQL 試験（CI の使い捨て PostgreSQL 専用）。

migrations/20261107_180000_drop_tenant_channel_masters.sql の中身を読み込んで流す（書き写さない）。
消す前に 20260611 の migration で会社ごとの表を作り、消した後に表と連番が全 tenant_ スキーマから無いことを確かめる。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

pytestmark = pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required")

REPO_ROOT = Path(__file__).resolve().parents[2]
CREATE_MIGRATION = REPO_ROOT / "migrations" / "20260611_100000_create_channel_masters.sql"
DROP_MIGRATION = REPO_ROOT / "migrations" / "20261107_180000_drop_tenant_channel_masters.sql"

_COUNT_SQL = (
    r"SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
    r"WHERE c.relname IN ('channel_masters', 'channel_masters_id_seq') AND n.nspname ~ '^tenant_\d+$'"
)


def _count(connection) -> int:
    with connection.cursor() as cur:
        cur.execute(_COUNT_SQL)
        return cur.fetchone()[0]


def _run(connection, path: Path) -> None:
    with connection.cursor() as cur:
        cur.execute(path.read_text(encoding="utf-8"))


def test_drop_removes_tenant_channel_masters_and_sequences_idempotently(pg):
    connection, _, _ = pg
    with connection.cursor() as cur:
        cur.execute("CREATE SCHEMA tenant_9101; CREATE SCHEMA tenant_9102")

    _run(connection, CREATE_MIGRATION)
    with connection.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE c.relname = 'channel_masters' AND n.nspname IN ('tenant_9101', 'tenant_9102')"
        )
        assert cur.fetchone()[0] == 2
    # 消す前に在ったことの確かめ（2スキーマ × 表と連番 = 4 以上）
    assert _count(connection) >= 4

    _run(connection, DROP_MIGRATION)
    _run(connection, DROP_MIGRATION)  # 2回目もエラーにならない

    assert _count(connection) == 0
