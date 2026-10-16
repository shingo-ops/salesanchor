"""閲覧専用アカウントの毎日の掃除 purge_viewer_accounts の試験（ADR-1019 Q7・段4a-1）。

実 PostgreSQL（CI の使い捨て DB。pg fixture）に migration を流して確かめる。SQLite・mock は使わない。
本番や共有の DB には接続しない（pg fixture が localhost の jarvis_test_db だけを許す）。
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from tests.rls_bootstrap import _ensure_public_users
from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

needs_ci_pg = pytest.mark.skipif(
    os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required"
)


def _prepare(conn, async_url):
    async def _run():
        engine = create_async_engine(async_url, echo=False)
        try:
            async with engine.begin() as aconn:
                await _ensure_public_users(aconn)
        finally:
            await engine.dispose()

    asyncio.run(_run())
    cur = conn.cursor()
    cur.execute((MIGRATIONS / "20261016_150000_add_viewer_accounts.sql").read_text())
    return cur


def _account(cur, email, status, *, trial_days_ago=None, created_days_ago=0):
    cur.execute(
        "INSERT INTO public.viewer_accounts (email, line_name, status, trial_expires_at, created_at) "
        "VALUES (%s, 'n', %s, "
        "CASE WHEN %s::int IS NULL THEN NULL ELSE NOW() - make_interval(days => %s::int) END, "
        "NOW() - make_interval(days => %s::int)) RETURNING id",
        (email, status, trial_days_ago, trial_days_ago, created_days_ago),
    )
    return cur.fetchone()[0]


def _suspend_record(cur, vid, days_ago):
    cur.execute(
        "INSERT INTO public.viewer_status_changes (viewer_id, action, actor, created_at) "
        "VALUES (%s, 'suspend', 'po', NOW() - make_interval(days => %s::int))",
        (vid, days_ago),
    )


def _event(cur, vid, days_ago):
    cur.execute(
        "INSERT INTO public.viewer_login_events (viewer_id, event_type, client_ip, created_at) "
        "VALUES (%s, 'login_succeeded', '10.0.0.1', NOW() - make_interval(days => %s::int))",
        (vid, days_ago),
    )


def _emails(cur):
    cur.execute("SELECT email FROM public.viewer_accounts ORDER BY email")
    return [r[0] for r in cur.fetchall()]


def _run_purge(engine):
    from app.tasks import maintenance

    with patch.object(maintenance, "_get_sync_engine", return_value=engine):
        return maintenance.purge_viewer_accounts()


def test_task_is_registered_and_scheduled():
    from app.celery_app import celery_app
    from app.tasks import maintenance

    assert maintenance.purge_viewer_accounts.name == "app.tasks.maintenance.purge_viewer_accounts"
    entry = celery_app.conf.beat_schedule["purge-viewer-accounts"]
    assert entry["task"] == "app.tasks.maintenance.purge_viewer_accounts"


@needs_ci_pg
def test_trial_expired_91_days_is_deleted_89_days_stays(pg):  # noqa: F811
    conn, engine, async_url = pg
    cur = _prepare(conn, async_url)
    _account(cur, "t91@x.com", "trial", trial_days_ago=91)
    _account(cur, "t89@x.com", "trial", trial_days_ago=89)
    _account(cur, "active@x.com", "active", created_days_ago=400)
    result = _run_purge(engine)
    assert result["trial_expired"] == 1
    assert _emails(cur) == ["active@x.com", "t89@x.com"]


@needs_ci_pg
def test_suspended_by_suspend_record_age(pg):  # noqa: F811
    conn, engine, async_url = pg
    cur = _prepare(conn, async_url)
    s91 = _account(cur, "s91@x.com", "suspended")
    s89 = _account(cur, "s89@x.com", "suspended")
    _account(cur, "snorecord@x.com", "suspended", created_days_ago=400)  # suspend の記録が無い行は消えない
    _suspend_record(cur, s91, 91)
    _suspend_record(cur, s89, 89)
    result = _run_purge(engine)
    assert result["suspended"] == 1
    assert _emails(cur) == ["s89@x.com", "snorecord@x.com"]


@needs_ci_pg
def test_pending_older_than_7_days_is_deleted_trial_stays(pg):  # noqa: F811
    conn, engine, async_url = pg
    cur = _prepare(conn, async_url)
    _account(cur, "p8@x.com", "pending", created_days_ago=8)
    _account(cur, "p6@x.com", "pending", created_days_ago=6)
    _account(cur, "trial8@x.com", "trial", trial_days_ago=-5, created_days_ago=8)  # 期限内の trial は残る
    result = _run_purge(engine)
    assert result["pending"] == 1
    assert _emails(cur) == ["p6@x.com", "trial8@x.com"]


@needs_ci_pg
def test_deleting_account_cascades_and_old_login_events_are_purged(pg):  # noqa: F811
    conn, engine, async_url = pg
    cur = _prepare(conn, async_url)
    gone = _account(cur, "gone@x.com", "trial", trial_days_ago=95)
    keep = _account(cur, "keep@x.com", "active")
    _event(cur, gone, 1)
    _suspend_record(cur, gone, 100)
    cur.execute(
        "INSERT INTO public.viewer_login_tokens (viewer_account_id, token_sha256, purpose, expires_at) "
        "VALUES (%s, decode(repeat('ab', 32), 'hex'), 'password_reset', NOW() + interval '30 minutes')",
        (gone,),
    )
    _event(cur, keep, 91)
    _event(cur, keep, 89)
    result = _run_purge(engine)
    assert result["trial_expired"] == 1 and result["login_events"] == 1
    for table, col in (
        ("viewer_login_events", "viewer_id"),
        ("viewer_status_changes", "viewer_id"),
        ("viewer_login_tokens", "viewer_account_id"),
    ):
        cur.execute(f"SELECT count(*) FROM public.{table} WHERE {col} = %s", (gone,))
        assert cur.fetchone()[0] == 0, table
    cur.execute("SELECT count(*) FROM public.viewer_login_events WHERE viewer_id = %s", (keep,))
    assert cur.fetchone()[0] == 1  # 89日前は残り、91日前は消える
