"""ADR-1077 便2b: 決まり帳の読み書き（app/services/secretary_rules.py）を本物の PostgreSQL で試す
（design.md §11 の R1・R3・R4・R5・21 件目が入らない）。

PG（CI の使い捨て DB。pg fixture）。アプリの役割 salesanchor_app で、口と同じ set_tenant_context の会社文脈で呼ぶ。
表は本物の migration を流して作る（tests/test_secretary_rules_tables_pg.py の _setup）。テストデータはすべて架空。
"""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.auth.dependencies import set_tenant_context
from app.services import secretary_rules as sr
from tests.test_secretary_rules_tables_pg import INSERT_RULE, _seed, _setup, needs_ci_pg
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture


def _engine(conn):
    url = make_url(os.environ["RLS_TEST_DATABASE_URL"]).set(
        database=conn.info.dbname, drivername="postgresql+asyncpg"
    )
    return create_async_engine(url, poolclass=NullPool)


async def _in_tenant(engine, tenant_id, fn, *, commit=True):
    """会社の文脈を張った 1 つの取引で fn(session) を呼ぶ。例外のときは戻して投げ直す。"""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        await set_tenant_context(session, tenant_id)
        try:
            result = await fn(session)
        except BaseException:
            await session.rollback()
            raise
        if commit:
            await session.commit()
        else:
            await session.rollback()
        return result


def _add_approved(cur, tenant_id, n):
    for i in range(n):
        cur.execute(INSERT_RULE, (tenant_id, "approved", f"fake rule {i}", tenant_id, "2026-11-12T02:00:00Z"))


def _one_id(cur, tenant_id, status):
    cur.execute(
        "SELECT id FROM public.secretary_rules WHERE tenant_id = %s AND status = %s ORDER BY id LIMIT 1",
        (tenant_id, status),
    )
    return cur.fetchone()[0]


def _approved_count(cur, tenant_id):
    cur.execute(
        "SELECT count(*) FROM public.secretary_rules WHERE tenant_id = %s AND status = 'approved'", (tenant_id,)
    )
    return cur.fetchone()[0]


@needs_ci_pg
def test_approved_texts_are_own_tenant_in_decided_order(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    _seed(cur)
    cur.execute(INSERT_RULE, (999, "approved", "first rule", 999, "2026-11-11T00:00:00Z"))
    cur.execute(INSERT_RULE, (999, "approved", "second rule", 999, "2026-11-12T01:00:00Z"))

    async def main():
        engine = _engine(conn)
        try:
            own = await _in_tenant(engine, 999, lambda s: sr.list_approved_rule_texts(s, 999), commit=False)
            other = await _in_tenant(engine, 999, lambda s: sr.list_approved_rule_texts(s, 998), commit=False)
            return own, other
        finally:
            await engine.dispose()

    own, other = asyncio.run(main())
    assert own == ["first rule", "fake rule", "second rule"]  # 候補（fake candidate）とほかの会社は入らない
    assert other == []


@needs_ci_pg
def test_lists_are_own_tenant_only(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    _seed(cur)

    async def main():
        engine = _engine(conn)
        try:
            cands = await _in_tenant(engine, 999, lambda s: sr.list_rules(s, 999, "candidate"), commit=False)
            approved = await _in_tenant(engine, 999, lambda s: sr.list_rules(s, 999, "approved"), commit=False)
            with pytest.raises(ValueError):
                await _in_tenant(engine, 999, lambda s: sr.list_rules(s, 999, "rejected"), commit=False)
            return cands, approved
        finally:
            await engine.dispose()

    cands, approved = asyncio.run(main())
    assert [(r.status, r.rule_text) for r in cands] == [("candidate", "fake candidate")]
    assert [(r.status, r.rule_text) for r in approved] == [("approved", "fake rule")]


@needs_ci_pg
def test_feedback_approve_remove_reject_flow(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    _seed(cur)
    other_tenant_rule = _one_id(cur, 998, "candidate")

    async def main():
        engine = _engine(conn)
        try:
            cand = await _in_tenant(
                engine, 999, lambda s: sr.add_candidate(s, 999, 999, "", "fake source", "invoice", None)
            )
            assert cand.status == "candidate" and cand.rule_text == "" and cand.decided_at is None
            approved = await _in_tenant(
                engine, 999, lambda s: sr.approve_candidate(s, 999, cand.id, 999, "fake approved")
            )
            assert approved.status == "approved" and approved.rule_text == "fake approved"
            assert approved.decided_at is not None
            texts = await _in_tenant(engine, 999, lambda s: sr.list_approved_rule_texts(s, 999), commit=False)
            assert "fake approved" in texts
            removed = await _in_tenant(engine, 999, lambda s: sr.remove_rule(s, 999, cand.id, 999))
            assert removed.status == "removed"
            texts = await _in_tenant(engine, 999, lambda s: sr.list_approved_rule_texts(s, 999), commit=False)
            assert "fake approved" not in texts  # R4: 外すと次の頼みから送らない
            with pytest.raises(sr.RuleWrongStatus):
                await _in_tenant(engine, 999, lambda s: sr.remove_rule(s, 999, cand.id, 999))
            with pytest.raises(sr.RuleWrongStatus):
                await _in_tenant(engine, 999, lambda s: sr.approve_candidate(s, 999, cand.id, 999, "x"))

            idea = await _in_tenant(
                engine, 999, lambda s: sr.add_candidate(s, 999, 999, "fake idea", "fake source 2", "event", "r")
            )
            rejected = await _in_tenant(engine, 999, lambda s: sr.reject_candidate(s, 999, idea.id, 999))
            assert rejected.status == "rejected"
            with pytest.raises(sr.RuleWrongStatus):
                await _in_tenant(engine, 999, lambda s: sr.reject_candidate(s, 999, idea.id, 999))

            for rule_id in (other_tenant_rule, 999999):  # ほかの会社の番号は「無い」と同じ
                with pytest.raises(sr.RuleNotFound):
                    await _in_tenant(engine, 999, lambda s: sr.approve_candidate(s, 999, rule_id, 999, "x"))
                with pytest.raises(sr.RuleNotFound):
                    await _in_tenant(engine, 999, lambda s: sr.reject_candidate(s, 999, rule_id, 999))
                with pytest.raises(sr.RuleNotFound):
                    await _in_tenant(engine, 999, lambda s: sr.remove_rule(s, 999, rule_id, 999))
            return cand.id
        finally:
            await engine.dispose()

    rule_id = asyncio.run(main())
    cur.execute("SELECT status, decided_by FROM public.secretary_rules WHERE id = %s", (rule_id,))
    assert cur.fetchone() == ("removed", 999)
    cur.execute("SELECT status FROM public.secretary_rules WHERE id = %s", (other_tenant_rule,))
    assert cur.fetchone() == ("candidate",)  # ほかの会社の行は変わらない


@needs_ci_pg
def test_twenty_approved_refuses_more(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    _seed(cur)
    _add_approved(cur, 999, 19)  # _seed の 1 件と合わせて 20 件
    cand_id = _one_id(cur, 999, "candidate")
    approved_id = _one_id(cur, 999, "approved")

    async def main():
        engine = _engine(conn)
        try:
            with pytest.raises(sr.RulesFull):
                await _in_tenant(engine, 999, lambda s: sr.add_approved_rule(s, 999, 999, "fake 21"))
            with pytest.raises(sr.RulesFull):
                await _in_tenant(engine, 999, lambda s: sr.approve_candidate(s, 999, cand_id, 999, "fake 21"))
            with pytest.raises(sr.RuleNotFound):
                await _in_tenant(engine, 999, lambda s: sr.approve_candidate(s, 999, 999999, 999, "x"))
            with pytest.raises(sr.RuleWrongStatus):
                await _in_tenant(engine, 999, lambda s: sr.approve_candidate(s, 999, approved_id, 999, "x"))
            # 上限は会社ごと（998 は 1 件なので入る）
            other = await _in_tenant(engine, 998, lambda s: sr.add_approved_rule(s, 998, 998, "fake other"))
            assert other.status == "approved"
        finally:
            await engine.dispose()

    asyncio.run(main())
    assert _approved_count(cur, 999) == 20
    assert _approved_count(cur, 998) == 2
    cur.execute("SELECT created_by, decided_by FROM public.secretary_rules WHERE rule_text = %s", ("fake other",))
    assert cur.fetchone() == (998, 998)  # R1: 決めた人が入る


@needs_ci_pg
def test_two_approvals_at_once_stop_at_twenty(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    _seed(cur)
    _add_approved(cur, 999, 18)  # _seed の 1 件と合わせて 19 件

    async def main():
        engine = _engine(conn)
        added = asyncio.Event()

        async def first():
            async with AsyncSession(engine) as s:
                await set_tenant_context(s, 999)
                await sr.add_approved_rule(s, 999, 999, "fake 20th A")
                added.set()
                await asyncio.sleep(0.5)  # 鍵を持ったまま待つ（2 本目はこの間 鍵で待たされる）
                await s.commit()

        async def second():
            await added.wait()
            async with AsyncSession(engine) as s:
                await set_tenant_context(s, 999)
                try:
                    await sr.add_approved_rule(s, 999, 999, "fake 20th B")
                except sr.RulesFull:
                    await s.rollback()
                    return "full"
                await s.commit()
                return "added"

        try:
            _, result = await asyncio.gather(first(), second())
            return result
        finally:
            await engine.dispose()

    assert asyncio.run(main()) == "full"
    assert _approved_count(cur, 999) == 20
