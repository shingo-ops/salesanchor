"""CSV row atomicity in isolated CI PostgreSQL databases; never live input.

Each parametrized case gets the existing pg fixture's independent database.
Observe durable data from its separate psycopg2 connection, not the writer.
No skip or relaxed fixture guard: local execution without CI PostgreSQL fails.
"""
import asyncio
import csv
import io
import os

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.services import tcg_product_import_svc as importer
from app.services import tcg_product_master_svc as master
from tests import test_tcg_work_matching_integration as work_fixture

pg = work_fixture.pg
SCHEMA = work_fixture.SCHEMA
HISTORY = "20260906_130000_create_tcg_product_import_history_t004.sql"


def csv_input():
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(importer.CSV_COLUMNS)
    for n in range(1, 45):
        writer.writerow([f"ATOMIC{n:02}", f"原子商品{n:02}", "", "",
                         f"検索語{n:02},別名{n:02}", f"除外語{n:02}",
                         "DIV01", "one_piece", "MK002", "PC_BOX"])
    return out.getvalue().encode("utf-8")


@pytest.fixture
def atomic_pg(pg, monkeypatch):
    connection, _, async_url = pg
    # Retain all of the imported fixture's guards; the URL is its new test DB,
    # never the administration DB or a production tenant.
    assert os.getenv("GITHUB_ACTIONS") == "true"
    assert async_url.host in ("localhost", "127.0.0.1")
    assert async_url.database.startswith("tcg_work_test_")
    assert SCHEMA == "tenant_901"
    for module in (master, importer):
        monkeypatch.setattr(module, "TCG_SCHEMA", SCHEMA)
    with connection.cursor() as cur:
        cur.execute((work_fixture.MIGRATIONS / HISTORY).read_text().replace("tenant_004", SCHEMA))
        work_fixture.provision(cur, "tenant_990")
        cur.execute(work_fixture._rewire_keyword_fks("tenant_990"))
        cur.execute((work_fixture.MIGRATIONS / HISTORY).read_text().replace("tenant_004", "tenant_990"))
        cur.execute("INSERT INTO public.products (product_code,name,category_class,is_active) VALUES ('SENTINEL','unchanged','Box',true) RETURNING id")
        product_id = cur.fetchone()[0]
        for table in ("product_search_keywords", "product_exclude_keywords"):
            cur.execute(f"INSERT INTO tenant_990.{table}(product_id,keyword,position) VALUES (%s,'unchanged',1)", (product_id,))
        cur.execute("INSERT INTO tenant_990.tcg_product_import_jobs(filename,raw_sha256,total_rows) VALUES ('sentinel.csv',%s,1) RETURNING id", ("0" * 64,))
        job_id = cur.fetchone()[0]
        cur.execute("INSERT INTO tenant_990.tcg_product_import_rows(job_id,row_no,japanese_title,result,product_code) VALUES (%s,1,'unchanged','created','SENTINEL')", (job_id,))
    before = sentinel_snapshot(connection)
    yield connection, async_url
    assert sentinel_snapshot(connection) == before


def sentinel_snapshot(connection):
    """All stored columns in the other tenant's real product/word/history tables."""
    rows = {}
    with connection.cursor() as cur:
        cur.execute("SELECT row_to_json(t) FROM public.products t WHERE t.product_code='SENTINEL' ORDER BY t.id")
        rows["tcg_products"] = cur.fetchall()
        assert len(rows["tcg_products"]) == 1
        for table in ("product_search_keywords", "product_exclude_keywords",
                      "tcg_product_import_jobs", "tcg_product_import_rows"):
            cur.execute(f"SELECT row_to_json(t) FROM tenant_990.{table} t ORDER BY id")
            rows[table] = cur.fetchall()
            assert len(rows[table]) == 1
    return rows


def observe(connection):
    """Independent committed view of every product/word/receipt/job, C1/C9."""
    with connection.cursor() as cur:
        cur.execute(f"SELECT p.name AS japanese_title,p.id::text AS code FROM public.products p WHERE p.name LIKE '原子商品%%' ORDER BY p.name")
        products = dict(cur.fetchall())
        words = {}
        for table in ("product_search_keywords", "product_exclude_keywords"):
            cur.execute(f"SELECT p.name,k.keyword,k.position FROM public.{table} k JOIN public.products p ON p.id=k.product_id ORDER BY p.name,k.position")
            words[table] = cur.fetchall()
        cur.execute(f"SELECT row_no,japanese_title,result,product_code FROM {SCHEMA}.tcg_product_import_rows ORDER BY row_no")
        rows = cur.fetchall()
        cur.execute(f"SELECT total_rows,created_rows,skipped_rows,status FROM {SCHEMA}.tcg_product_import_jobs")
        jobs = cur.fetchall()
        cur.execute("SELECT name FROM public.products WHERE product_code='SENTINEL'")
        assert cur.fetchall() == [("unchanged",)]
    return products, words, rows, jobs


def assert_contents(snapshot, created, errors=(), skipped=(), *, completed=False):
    products, words, rows, jobs = snapshot
    assert set(products) == {f"原子商品{n:02}" for n in created}
    assert words["product_search_keywords"] == [
        (f"原子商品{n:02}", word, pos) for n in sorted(created)
        for pos, word in enumerate([f"検索語{n:02}", f"別名{n:02}"], 1)]
    assert words["product_exclude_keywords"] == [
        (f"原子商品{n:02}", f"除外語{n:02}", 1) for n in sorted(created)]
    expected = [(n, f"原子商品{n:02}", "created", products[f"原子商品{n:02}"]) for n in created]
    expected += [(n, f"原子商品{n:02}", "error", None) for n in errors]
    expected += [(n, f"原子商品{n:02}", "skipped", None) for n in skipped]
    assert rows == sorted(expected)
    if completed:
        assert jobs == [(44, len(created), len(errors) + len(skipped), "ok")]
    else:
        assert jobs == [(44, 0, 0, "running")]


class InjectedFailure(RuntimeError):
    pass


def failing_session(connection, mode, target):
    class Writer(AsyncSession):
        current = 0
        pending_created = False

        async def execute(self, statement, params=None, **kwargs):
            query = str(statement)
            # These services may only touch the intended tenant's tables.
            for table in ("tcg_product_import_jobs", "tcg_product_import_rows"):
                if table in query:
                    assert f"{SCHEMA}.{table}" in query
            # product_search_keywords and product_exclude_keywords are now in public schema (SSOT Phase 3)
            for table in ("product_search_keywords", "product_exclude_keywords"):
                if table in query:
                    assert f"public.{table}" in query
            if "INSERT INTO public.products" in query:
                self.current = int(params["japanese_title"].removeprefix("原子商品"))
                if self.current == target:
                    if mode == "before_value":
                        raise ValueError("before product insert")
                    if mode == "cancel":
                        raise asyncio.CancelledError("cancelled creation")
                    if mode == "collision":
                        params = dict(params, code="PM0001")
            if self.current == target and "SELECT id FROM public.products WHERE id" in query:
                if mode in ("verify_value", "rollback_failure"):
                    raise ValueError("post-write verification")
            if f"INSERT INTO {SCHEMA}.tcg_product_import_rows" in query:
                self.pending_created = params["kind"] == "created"
                if int(params["row_no"]) == target:
                    if mode == "history" or mode == "blocked_history":
                        raise ValueError("receipt insert")
            if mode == "finish" and f"UPDATE {SCHEMA}.tcg_product_import_jobs" in query:
                raise InjectedFailure("finish job")
            return await super().execute(statement, params, **kwargs)

        async def commit(self):
            if self.pending_created:
                # Writer sees its uncommitted product+words; independent reader
                # must still see only the previously committed rows.
                before = observe(connection)
                assert f"原子商品{self.current:02}" not in before[0]
                assert self.current not in [r[0] for r in before[2]]
                if self.current == target and mode == "commit_before":
                    raise InjectedFailure("before row commit")
            pending = self.pending_created
            await super().commit()
            self.pending_created = False
            if pending and self.current == target and mode == "commit_after":
                raise InjectedFailure("commit acknowledgement lost")

        async def rollback(self):
            if mode == "rollback_failure" and self.current == target:
                raise InjectedFailure("rollback failed")
            self.pending_created = False
            return await super().rollback()
    return Writer


async def import_once(connection, url, mode, target):
    ae = create_async_engine(url)
    try:
        async with failing_session(connection, mode, target)(ae) as session:
            return await importer.commit_import(session, csv_input(), "atomic.csv", "ci-test")
    finally:
        await ae.dispose()


@pytest.mark.asyncio
async def test_atomic_normal_44_products_words_receipts_and_counters(atomic_pg):
    connection, url = atomic_pg
    result = await import_once(connection, url, "normal", 0)
    assert (result["total"], result["created"], result["skipped"]) == (44, 44, 0)
    assert_contents(observe(connection), range(1, 45), completed=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("target", range(1, 45))
@pytest.mark.parametrize("mode", ["before_value", "verify_value", "history", "commit_before", "commit_after"])
async def test_atomic_each_failure_position(atomic_pg, mode, target):
    connection, url = atomic_pg
    if mode in ("before_value", "verify_value"):
        result = await import_once(connection, url, mode, target)
        assert (result["created"], result["skipped"]) == (43, 1)
        assert_contents(observe(connection), [n for n in range(1, 45) if n != target], [target], completed=True)
    else:
        error = ValueError if mode == "history" else InjectedFailure
        with pytest.raises(error):
            await import_once(connection, url, mode, target)
        count = target if mode == "commit_after" else target - 1
        assert_contents(observe(connection), range(1, count + 1))
        # No automatic retries; explicit same digest is also rejected, including
        # unknown commit responses. Neither product nor receipt may be added.
        before = observe(connection)
        with pytest.raises(IntegrityError):
            await import_once(connection, url, "normal", 0)
        assert observe(connection) == before


@pytest.mark.asyncio
async def test_atomic_finish_failure_and_same_digest_not_restarted(atomic_pg):
    connection, url = atomic_pg
    with pytest.raises(InjectedFailure, match="finish"):
        await import_once(connection, url, "finish", 0)
    assert_contents(observe(connection), range(1, 45))
    before = observe(connection)
    with pytest.raises(IntegrityError):
        await import_once(connection, url, "normal", 0)
    assert observe(connection) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,error", [("cancel", asyncio.CancelledError), ("rollback_failure", ValueError),
                                       ("collision", IntegrityError)])
async def test_atomic_cancel_rollback_failure_and_number_collision_stop(atomic_pg, mode, error):
    connection, url = atomic_pg
    with pytest.raises(error) as caught:
        await import_once(connection, url, mode, 2)
    if mode == "rollback_failure":
        assert isinstance(caught.value.__cause__, InjectedFailure)
    assert_contents(observe(connection), [1])


@pytest.mark.asyncio
@pytest.mark.parametrize("history_fails", [False, True])
async def test_atomic_blocked_row_receipt(atomic_pg, monkeypatch, history_fails):
    connection, url = atomic_pg
    real_preview = importer.preview
    async def preview(*args):
        checked = await real_preview(*args)
        checked["rows"][1]["blocking"].append("synthetic blocking row")
        return checked
    monkeypatch.setattr(importer, "preview", preview)
    if history_fails:
        with pytest.raises(ValueError, match="receipt"):
            await import_once(connection, url, "blocked_history", 2)
        assert_contents(observe(connection), [1])
    else:
        result = await import_once(connection, url, "normal", 0)
        assert (result["created"], result["skipped"]) == (43, 1)
        assert_contents(observe(connection), [n for n in range(1, 45) if n != 2], skipped=[2], completed=True)


@pytest.mark.asyncio
async def test_atomic_old_internal_commit_is_detected_by_same_contract(atomic_pg, monkeypatch):
    connection, url = atomic_pg
    current_create = master.create_product
    async def old_boundary(db, **kwargs):
        # Recreate only the old internal-commit boundary, not a second matcher
        # or importer implementation. The current caller still asks for False.
        assert kwargs.pop("commit") is False
        return await current_create(db, **kwargs)
    monkeypatch.setattr(master, "create_product", old_boundary)
    # Use one row to isolate the original post-write ValueError defect, without
    # triggering the writer's normal-row visibility guard on later rows.
    real_preview = importer.preview
    real_parse = importer.parse_rows
    async def preview(*args):
        result = await real_preview(*args)
        result["rows"] = result["rows"][:1]
        return result
    monkeypatch.setattr(importer, "preview", preview)
    monkeypatch.setattr(importer, "parse_rows", lambda raw: (real_parse(raw)[0][:1], []))
    await import_once(connection, url, "verify_value", 1)
    snapshot = observe(connection)
    assert set(snapshot[0]) == {"原子商品01"}
    assert snapshot[2] == [(1, "原子商品01", "error", None)]
    with pytest.raises(AssertionError):
        assert_contents(snapshot, [], errors=[1], completed=True)
