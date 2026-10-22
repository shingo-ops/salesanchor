"""bundle_title_sql の英語タイトル（ADR-1027 便4）を PostgreSQL で実行して確かめる。値はすべて架空。

(a) bundle_size あり・name_en あり → 「<name_en> <n> <unit> Set」（今と同じ）
(b) bundle_size あり・name_en NULL → ''
(c) bundle_size あり・name_en '' → ''（空白だけも同じ）
(d) bundle_size なし・name_en あり → name_en（NULL のときも ''）
CI の使い捨て PostgreSQL 専用（テーブルは作らず、VALUES だけで式を評価する）。
"""
from __future__ import annotations

import os

import psycopg2
import pytest
from sqlalchemy.engine import make_url

from app.services import tcg_distribution_svc as dist

pytestmark = pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required")


def _english(bundle_size, name_en, unit_name_en="Piece"):
    url = make_url(os.environ["RLS_ADMIN_DATABASE_URL"])
    assert url.host in ("localhost", "127.0.0.1") and url.database == "jarvis_test_db"
    _, en = dist.bundle_title_sql()
    sql = (
        f"SELECT {en} FROM (SELECT %s::int AS bundle_size, %s::text AS unit_canonical) ar, "
        "(SELECT %s::text AS name_en) p, (SELECT %s::text AS name_en, NULL::text AS canonical) lu"
    )
    conn = psycopg2.connect(dbname=url.database, host=url.host, port=url.port, user=url.username, password=url.password)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (bundle_size, None, name_en, unit_name_en))
            return cur.fetchone()[0]
    finally:
        conn.close()


def test_a_bundle_with_name_en_is_unchanged():
    assert _english(100, "Some Box") == "Some Box 100 Piece Set"


@pytest.mark.parametrize("name_en", [None, "", "   "])
def test_b_c_bundle_with_blank_name_en_is_empty(name_en):
    assert _english(100, name_en) == ("" if name_en is None or name_en == "" else name_en)


def test_d_non_bundle_returns_name_en():
    assert _english(None, "Some Box") == "Some Box"
    assert _english(None, None) == ""
