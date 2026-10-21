"""
要確認一覧の取得を1本にまとめる（便1, ADR-1023）: 今の道の SQL が1文字も変わらないことの証明。

実 DB は使わない。db.execute に渡された SQL 文字列を記録するだけの偽セッションで
fetch_analysis_results を呼び、実行された SQL 全文（実行順）の sha256 を比べる。
期待値は、変更を入れる前の origin/main（e3e1fd768）で同じ手順で記録した値。
"""
from __future__ import annotations

import hashlib
import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

pytestmark = pytest.mark.asyncio

ITEM_ID = "aaaaaaaa-0000-0000-0000-000000000001"

# (名前, fetch_analysis_results への引数)
CASES: list[tuple[str, dict]] = [
    ("all_5000", dict(status_tab="ALL", limit=5000)),
    ("needs_review_5000", dict(status_tab="NEEDS_REVIEW", limit=5000)),
    ("needs_review_20_offset20", dict(status_tab="NEEDS_REVIEW", limit=20, offset=20)),
    ("acked_20", dict(status_tab="ACKED", limit=20)),
    ("all_item_ids", dict(status_tab="ALL", limit=1, extraction_item_ids=[ITEM_ID])),
    (
        "needs_review_posted_desc_item_ids",
        dict(status_tab="NEEDS_REVIEW", limit=1, order="posted_desc", extraction_item_ids=[ITEM_ID]),
    ),
    (
        "acked_posted_desc_window",
        dict(status_tab="ACKED", limit=20, order="posted_desc", posted_within_hours=24),
    ),
]

# 変更前の origin/main (e3e1fd768) で記録した、実行された SQL 全文（実行順）の sha256
BASELINE_SHA256: dict[str, str] = {
    "all_5000": (
        "9800096406e4aa58a552095cb1f829b07dcc3b7f15bec9612c174dad3707aeda"
    ),
    "needs_review_5000": (
        "0e805161d6aae3afa69477c9845c88c436c262128f22d7a39b6834613389c6f4"
    ),
    "needs_review_20_offset20": (
        "0e805161d6aae3afa69477c9845c88c436c262128f22d7a39b6834613389c6f4"
    ),
    "acked_20": (
        "37a03ce5f4526aca771a54807ce27ef5b4e49b73b20e7173638e0bacd2da166c"
    ),
    "all_item_ids": (
        "f9a95f6199407b9b7f7c141c3e35f0bc38a31663599a5cd9b9119b1000f01926"
    ),
    "needs_review_posted_desc_item_ids": (
        "bf54ca2e17721e57fa22461becf36ab80bac4deca9f45a118f05333c76224356"
    ),
    "acked_posted_desc_window": (
        "37a03ce5f4526aca771a54807ce27ef5b4e49b73b20e7173638e0bacd2da166c"
    ),
}


class _FakeResult:
    def fetchall(self):
        return []

    def scalar_one(self):
        return 0


class RecordingSession:
    """db.execute に渡された SQL 文字列を記録するだけの偽セッション（SQLite 方言を名乗る）。"""

    def __init__(self) -> None:
        self.sqls: list[str] = []

    async def execute(self, stmt, params=None):
        self.sqls.append(str(stmt))
        return _FakeResult()

    async def run_sync(self, fn):
        return fn(None)

    def get_bind(self):
        class _Dialect:
            name = "sqlite"

        class _Bind:
            dialect = _Dialect()

        return _Bind()


async def record_sqls(kwargs: dict) -> list[str]:
    import inspect

    from app.services import tcg_analysis_review_svc as svc

    accepted = set(inspect.signature(svc.fetch_analysis_results).parameters)
    session = RecordingSession()
    await svc.fetch_analysis_results(session, **{k: v for k, v in kwargs.items() if k in accepted})
    return session.sqls


def digest(sqls: list[str]) -> str:
    return hashlib.sha256("\n--SQL--\n".join(sqls).encode("utf-8")).hexdigest()


@pytest.mark.parametrize("name,kwargs", CASES, ids=[c[0] for c in CASES])
async def test_current_path_sql_is_unchanged(name, kwargs):
    sqls = await record_sqls(kwargs)
    assert digest(sqls) == BASELINE_SHA256[name]


async def test_new_path_sql_shape_with_window():
    sqls = await record_sqls(
        dict(status_tab="NEEDS_REVIEW", limit=25, order="posted_desc", posted_within_hours=24)
    )
    # 新しい道は1本の SQL（件数・仕入元・本体を別々に取らない）+ 後続の補助問い合わせ
    main = next(s for s in sqls if "meta LEFT JOIN base" in s)
    assert "(sm.line_posted_at + interval '0 second') >= now() - make_interval(hours => :posted_within_hours)" in main
    assert "ORDER BY sm.line_posted_at DESC NULLS LAST, sm.id ASC," in main
    assert "base AS MATERIALIZED" in main
    assert not any("SELECT COUNT(*)" in s for s in sqls)


async def test_new_path_sql_shape_without_window():
    sqls = await record_sqls(dict(status_tab="NEEDS_REVIEW", limit=25, order="posted_desc"))
    main = next(s for s in sqls if "meta LEFT JOIN base" in s)
    assert "make_interval(hours => :posted_within_hours)" not in main
    assert "posted_within_hours" not in main
    assert "interval '0 second'" not in main


async def test_new_path_does_not_send_set_config_on_sqlite():
    sqls = await record_sqls(
        dict(status_tab="NEEDS_REVIEW", limit=25, order="posted_desc", posted_within_hours=24)
    )
    assert not any("set_config" in s or "current_setting" in s for s in sqls)
