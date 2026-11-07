"""pool_reset_measure.py — 調査用の台本（製品コードではない）。

使い捨ての PostgreSQL（localhost）だけに接続する。本番・secret には触らない。
使い方: KURL=postgresql+asyncpg://kapp:kapp@127.0.0.1:5432/kmeasure python pool_reset_measure.py <m1|m2|m3|m4|m5|m6|m7|all>
候補: none（何もしない）/ A / B / Bx（recon-pool-reset.md の「候補」参照）
"""
import asyncio
import logging
import os
import statistics
import sys
import time
import warnings

import asyncpg  # noqa: F401
import psycopg2
import sqlalchemy
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

KURL = os.environ.get("KURL", "postgresql+asyncpg://kapp:kapp@127.0.0.1:5432/kmeasure")
SYNC_URL = KURL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
MON_DSN = KURL.replace("postgresql+asyncpg://", "postgresql://")
CANDS = ["none", "A", "B", "Bx"]

# database.py:13-16 と同じ connect_args（ADR-065 / SA-18）
PROD_CONNECT_ARGS = {
    "prepared_statement_cache_size": 0,
    "server_settings": {"application_name": "salesanchor_backend"},
}

_mon = psycopg2.connect(MON_DSN)
_mon.autocommit = True


def mon(pid):
    """返却直後の pg_stat_activity を生の値で返す。"""
    cur = _mon.cursor()
    cur.execute(
        "select state, (xact_start is not null) as in_xact, application_name, left(query, 40) "
        "from pg_stat_activity where pid = %s",
        (pid,),
    )
    r = cur.fetchone()
    return {"state": r[0], "xact_open": r[1], "app": r[2], "last_query": r[3]} if r else None


# ───────── 候補の組み込み ─────────
def _handler(cand):
    def h(dbapi_conn, record, reset_state):
        if reset_state.terminate_only:
            return
        if cand == "A":
            cur = dbapi_conn.cursor()
            cur.execute("RESET ALL")
            cur.close()
        else:  # B / Bx
            dbapi_conn.rollback()
            cur = dbapi_conn.cursor()
            cur.execute("RESET ALL")
            cur.close()
            if cand == "Bx":
                dbapi_conn.commit()
    return h


def make_async_engine(cand, pool_size=1, max_overflow=0, connect_args=None, **kw):
    args = dict(
        pool_size=pool_size, max_overflow=max_overflow, pool_pre_ping=True,
        pool_recycle=3600, pool_timeout=30,
        connect_args=connect_args if connect_args is not None else PROD_CONNECT_ARGS,
    )
    args.update(kw)
    if cand in ("B", "Bx"):
        args["pool_reset_on_return"] = None
    eng = create_async_engine(KURL, **args)
    if cand != "none":
        event.listen(eng.sync_engine.pool, "reset", _handler(cand))
    return eng


def make_sync_engine(cand, pool_size=1, max_overflow=0, **kw):
    args = dict(pool_size=pool_size, max_overflow=max_overflow)
    args.update(kw)
    if cand in ("B", "Bx"):
        args["pool_reset_on_return"] = None
    eng = sqlalchemy.create_engine(SYNC_URL, **args)
    if cand != "none":
        event.listen(eng.pool, "reset", _handler(cand))
    return eng


READ_SQL = (
    "select pg_backend_pid(), current_setting('app.is_operator', true), "
    "current_setting('app.tenant_id', true), current_setting('search_path'), "
    "current_setting('application_name')"
)


# ───────── dependencies.py と同じ形の関数（async） ─────────
async def clear_tenant_context(s):  # dependencies.py:403-405
    await s.execute(text("SET search_path = public"))
    await s.execute(text("SET app.tenant_id = ''"))
    await s.execute(text("SET app.is_operator = ''"))


async def set_tenant_context(s, tid):  # dependencies.py:274-281
    await s.execute(text(f"SET search_path = tenant_{tid:03d}, public"))
    await s.execute(text(f"SET app.tenant_id = '{tid}'"))
    await s.execute(text("SET app.is_operator = ''"))


async def read_async(maker):
    async with maker() as s:
        r = (await s.execute(text(READ_SQL))).one()
    pid = r[0]
    return {"pid": pid, "is_operator": r[1], "tenant_id": r[2], "search_path": r[3], "app": r[4]}, mon(pid)


async def get_db_like(maker, body):
    """database.py:46-61 と同じ形。"""
    async with maker() as s:
        try:
            await body(s)
        except Exception:
            await s.rollback()
        finally:
            await clear_tenant_context(s)


async def scen_async(maker):
    out = []
    base, st = await read_async(maker)
    pid = base["pid"]
    out.append(("0 baseline", base, mon(pid)))

    async def b1(s):
        await s.execute(text("SET app.is_operator = 'true'"))
        await s.commit()
        await s.execute(text("SET app.is_operator = ''"))  # reset_operator_context

    async def b1b(s):
        await s.execute(text("SET app.is_operator = 'true'"))
        await s.commit()
        await s.execute(text("SET app.is_operator = ''"))
        await clear_tenant_context(s)
        await s.commit()

    async def b2(s):
        await s.execute(text("SET app.is_operator = 'true'"))
        await s.execute(text("SET app.is_operator = ''"))

    async def b3(s):
        await s.execute(text("SET app.is_operator = 'true'"))
        await s.rollback()
        raise RuntimeError("x")

    async def b4(s):
        await s.execute(text("SET app.tenant_id = '5'"))
        await s.commit()

    for name, body in [("1 set true->commit->reset->clear->close", b1),
                       ("1b after manual clear+commit", b1b),
                       ("2 set true->(no commit)->reset->clear->close", b2),
                       ("3 set true->rollback->raise->clear->close", b3),
                       ("4 tenant_id=5->commit->clear->close", b4)]:
        await get_db_like(maker, body)
        st_ret = mon(pid)  # 返却直後（次の checkout の前）
        nxt, st_after_read = await read_async(maker)
        out.append((name, nxt, st_ret, st_after_read))
    return out


async def m1():
    for cand in CANDS:
        eng = make_async_engine(cand)
        maker = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        print(f"--- m1 async cand={cand}")
        for row in await scen_async(maker):
            print("  ", row[0])
            print("     read   :", row[1])
            print("     返却直後:", row[2])
            if len(row) > 3:
                print("     読後    :", row[3])
        await eng.dispose()


async def m2():
    for cand in CANDS:
        eng = make_async_engine(cand)
        maker = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        async def b(s):
            await s.execute(text("SET app.is_operator = 'true'"))
            await s.execute(text("SET application_name = 'hacked'"))
            await s.commit()
        await get_db_like(maker, b)
        r, st = await read_async(maker)
        async with maker() as s:
            one = (await s.execute(text("show application_name"))).scalar()
        print(f"--- m2 cand={cand} read={r} show_application_name={one!r} pg_stat={st}")
        await eng.dispose()


async def m3():
    for label, ca in [("prod(cache=0)", PROD_CONNECT_ARGS), ("default-cache", {"server_settings": {"application_name": "salesanchor_backend"}})]:
        for cand in CANDS:
            eng = make_async_engine(cand, connect_args=ca)
            res = []
            for i in range(6):
                try:
                    async with eng.connect() as c:
                        await c.execute(text("SET app.is_operator = 'true'"))
                        await c.commit()
                        v = (await c.execute(text("select cast(:x as int) + cast(:y as int)"), {"x": i, "y": 1})).scalar()
                    res.append(v)
                except Exception as e:  # noqa: BLE001
                    res.append(f"ERR {type(e).__name__}: {str(e)[:80]}")
            print(f"--- m3 {label} cand={cand} results={res}")
            await eng.dispose()


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.rows = []
    def emit(self, r):
        self.rows.append(f"{r.levelname} {r.name}: {r.getMessage()[:160]}")


async def m4():
    for cand in CANDS:
        for case in ["rollback_after_error", "close_without_rollback_after_error", "invalidate"]:
            cap = _Cap()
            lg = logging.getLogger("sqlalchemy")
            lg.addHandler(cap)
            lg.setLevel(logging.WARNING)
            eng = make_async_engine(cand)
            maker = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
            exc_out = None
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                try:
                    async with maker() as s:
                        if case == "invalidate":
                            c = await s.connection()
                            await c.execute(text("select 1"))
                            await c.invalidate()
                        else:
                            try:
                                await s.execute(text("select 1/0"))
                            except Exception:
                                if case == "rollback_after_error":
                                    await s.rollback()
                except Exception as e:  # noqa: BLE001
                    exc_out = f"{type(e).__name__}: {str(e)[:100]}"
            after = None
            try:
                async with eng.connect() as c:
                    after = (await c.execute(text("select 1"))).scalar()
            except Exception as e:  # noqa: BLE001
                after = f"ERR {type(e).__name__}: {str(e)[:100]}"
            print(f"--- m4 cand={cand} case={case} close_exc={exc_out} warnings={[str(x.message)[:100] for x in w]} logs={cap.rows} next_checkout_select1={after}")
            lg.removeHandler(cap)
            await eng.dispose()


async def m5():
    for cand in CANDS:
        eng = make_async_engine(cand)
        for _ in range(50):
            async with eng.connect() as c:
                await c.execute(text("select 1"))
        ts = []
        for _ in range(1000):
            t = time.perf_counter()
            async with eng.connect() as c:
                await c.execute(text("select 1"))
            ts.append((time.perf_counter() - t) * 1000)
        ts.sort()
        print(f"--- m5 cand={cand} n=1000 median_ms={statistics.median(ts):.3f} p95_ms={ts[int(len(ts)*0.95)-1]:.3f} mean_ms={statistics.mean(ts):.3f}")
        await eng.dispose()


# ───────── m6 同期（psycopg2） ─────────
def read_sync(maker):
    with maker() as s:
        r = s.execute(text(READ_SQL)).one()
    return {"pid": r[0], "is_operator": r[1], "tenant_id": r[2], "search_path": r[3], "app": r[4]}, mon(r[0])


def get_db_like_sync(maker, body):
    with maker() as s:
        try:
            body(s)
        except Exception:
            s.rollback()
        finally:
            s.execute(text("SET search_path = public"))
            s.execute(text("SET app.tenant_id = ''"))
            s.execute(text("SET app.is_operator = ''"))


def m6():
    for pre_ping in (False, True):
        for cand in CANDS:
            eng = make_sync_engine(cand, pool_pre_ping=pre_ping)
            maker = sessionmaker(eng, class_=Session, expire_on_commit=False)
            print(f"--- m6 sync(psycopg2) cand={cand} pool_pre_ping={pre_ping}")
            try:
                base, _ = read_sync(maker)
            except Exception as e:  # noqa: BLE001
                print("   0 baseline ERR", type(e).__name__, str(e)[:120])
                eng.dispose()
                continue
            pid = base["pid"]
            print("   0 baseline:", base, mon(pid))

            def b1(s):
                s.execute(text("SET app.is_operator = 'true'")); s.commit(); s.execute(text("SET app.is_operator = ''"))
            def b2(s):
                s.execute(text("SET app.is_operator = 'true'")); s.execute(text("SET app.is_operator = ''"))
            def b3(s):
                s.execute(text("SET app.is_operator = 'true'")); s.rollback(); raise RuntimeError("x")
            def b4(s):
                s.execute(text("SET app.tenant_id = '5'")); s.commit()
            for name, body in [("1 set true->commit->reset->clear->close", b1),
                               ("2 set true->(no commit)->reset->clear->close", b2),
                               ("3 set true->rollback->raise->clear->close", b3),
                               ("4 tenant_id=5->commit->clear->close", b4)]:
                try:
                    get_db_like_sync(maker, body)
                    st_ret = mon(pid)
                    nxt, st2 = read_sync(maker)
                    print("  ", name); print("     read   :", nxt); print("     返却直後:", st_ret); print("     読後    :", st2)
                except Exception as e:  # noqa: BLE001
                    print("  ", name, "ERR", type(e).__name__, str(e)[:140].replace("\n", " "), "| 返却直後:", mon(pid))
                    break
            eng.dispose()


# ───────── m7 ─────────
async def warm(eng, n, tid=777):
    conns = [await eng.connect() for _ in range(n)]
    for c in conns:
        await c.execute(text(f"SET search_path = tenant_{tid:03d}, public"))
        await c.execute(text(f"SET app.tenant_id = '{tid}'"))
        await c.commit()
    for c in conns:
        await c.close()


async def m7():
    for ps, mo in [(1, 0), (2, 0), (20, 10)]:
        for cand in ["none", "Bx"]:
            eng = make_async_engine(cand, pool_size=ps, max_overflow=mo)
            maker = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
            nwarm = min(5, ps)
            trials = []
            for _ in range(20):
                await warm(eng, nwarm)
                async with maker() as s:
                    await set_tenant_context(s, 5)  # dependencies.py:274-281
                    pid_set = (await s.execute(text("select pg_backend_pid()"))).scalar()
                    await s.commit()
                    r = (await s.execute(text(READ_SQL))).one()  # 同じ session・文脈の入れ直し無し
                trials.append({"pid_set": pid_set, "pid_after": r[0], "op": r[1], "tid": r[2], "sp": r[3]})
            n = len(trials)
            print(f"--- m7 pool_size={ps} max_overflow={mo} cand={cand} warm={nwarm} trials={n}")
            print(f"    pid同じ={sum(t['pid_set']==t['pid_after'] for t in trials)}/{n}  tenant_id=5が残る={sum(t['tid']=='5' for t in trials)}/{n}  "
                  f"別テナント777が見えた={sum(t['tid']=='777' for t in trials)}/{n}  文脈が空={sum(t['tid'] in (None, '') for t in trials)}/{n}  "
                  f"search_path=tenant_005={sum(t['sp'].startswith('tenant_005') for t in trials)}/{n}")
            print("    1回目の生の値:", trials[0])
            print("    全回の tenant_id:", [t["tid"] for t in trials])
            await eng.dispose()


async def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    print("sqlalchemy", sqlalchemy.__version__, "asyncpg", asyncpg.__version__, "psycopg2", psycopg2.__version__)
    c = _mon.cursor(); c.execute("select version()"); print(c.fetchone()[0])
    tbl = {"m1": m1, "m2": m2, "m3": m3, "m4": m4, "m5": m5, "m7": m7}
    for k in ["m1", "m2", "m3", "m4", "m5", "m6", "m7"]:
        if which in (k, "all"):
            if k == "m6":
                m6()
            else:
                await tbl[k]()


if __name__ == "__main__":
    asyncio.run(main())
