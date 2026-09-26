"""Real PostgreSQL: read order, unchanged data, and pagination across all consumers.

The imported fixture permits only disposable CI PostgreSQL databases. No live
Sheets, source-message rewrite, or production credentials are used.
"""
import asyncio
from collections import Counter
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.services import tcg_analysis_review_svc as review
from app.services import tcg_distribution_svc as distribution
from app.services import tcg_import_progress as progress
from tests.test_tcg_condition_review import pg as condition_pg
from tests.test_tcg_condition_review import request, save, seed

# Reuse the existing isolated-CI database fixture with its safety checks intact.
pg = condition_pg

STATES = (
    "Case", "Damaged case", "Sealed box", "Damaged sealed box", "No shrink box",
    "Opened box", "Unsearched pack", "Searched pack",
)
MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


def link_import(pg, entries):
    job = str(uuid4())
    with pg["connection"].cursor() as cursor:
        cursor.execute("INSERT INTO public.import_jobs(id,filename,raw_sha256,messages_linked_at) "
                       "VALUES (%s,'order-test.txt',%s,now())", (job, uuid4().hex * 2))
        for entry in entries:
            cursor.execute("INSERT INTO public.import_job_messages "
                           "(import_job_id,source_message_id,relation_kind) VALUES (%s,%s,'created')",
                           (job, entry["smid"]))
    return job


def fetch(pg, import_id, *, limit=500, offset=0):
    async def run():
        engine = create_async_engine(pg["url"])
        try:
            async with AsyncSession(engine) as db:
                return (
                    await review.fetch_analysis_results(db, limit=limit, offset=offset),
                    await progress.read_items(db, import_id, limit, offset, "all"),
                    await distribution.fetch_output_rows(db),
                )
        finally:
            await engine.dispose()
    return asyncio.run(run())


def snapshot(pg):
    with pg["connection"].cursor() as cursor:
        result = {}
        for table in ("analysis_results", "extraction_items", "source_messages"):
            cursor.execute(f"SELECT to_jsonb(t) FROM public.{table} t ORDER BY id")
            result[table] = cursor.fetchall()
        return result


def test_release_product_condition_price_and_all_page_boundaries(pg):
    products = []
    with pg["connection"].cursor() as cursor:
        for n, date in enumerate(("2026-10-16", "2026-10-16", "2026-09-16", None)):
            cursor.execute("INSERT INTO public.products "
                           "(product_code,name,release_date,category_class,is_active,work_id,product_category_id) "
                           "SELECT %s,'Same title',%s,category_class,true,work_id,product_category_id "
                           "FROM public.products WHERE id=%s RETURNING id",
                           (f"PM09{n+10}", date, pg["product"]))
            products.append(str(cursor.fetchone()[0]))
        cursor.execute("INSERT INTO public.suppliers(supplier_code,name,line_name,supplier_type,is_active) "
                       "VALUES ('SP-09999','Earlier Supplier','Earlier Supplier','corporate',true) RETURNING id")
        supplier = cursor.fetchone()[0]
        cursor.execute("INSERT INTO public.supplier_channels(supplier_id,channel,is_active) "
                       "VALUES (%s,'line',true) RETURNING id", (supplier,))
        channel = str(cursor.fetchone()[0])
    entries = []
    for price in (1000, 9, 100):
        for state in reversed(STATES):
            for product_index in (3, 1, 0, 2):
                token = f"{product_index}:{STATES.index(state)}:{price}"
                item = seed(pg, name="Same title", reasons="", product_id=products[product_index],
                            condition_id=pg["normal"], condition_canonical=state,
                            condition_basis="TEST", price_normalized=price, note_ja=token)
                if price != 100:
                    with pg["connection"].cursor() as cursor:
                        cursor.execute("UPDATE public.source_messages SET supplier_channel_id=%s WHERE id=%s",
                                       (channel, item["smid"]))
                entries.append(item)
    import_id = link_import(pg, entries)
    before = snapshot(pg)
    expected = [f"{p}:{s}:{v}" for p in range(4) for s in range(8) for v in (9, 100, 1000)]
    reviewed, imported, output = fetch(pg, import_id)
    assert reviewed["total"] == imported["total"] == len(output) == len(expected) == 96
    assert [r["system"]["note"] for r in reviewed["items"]] == expected
    assert [r["note_ja"] for r in imported["items"]] == expected
    assert [r[7] for r in output] == expected
    assert all(len(r) == 12 for r in output)
    assert all("sort_ordinal" not in r for r in imported["items"])
    assert Counter(r["extraction_item_id"] for r in reviewed["items"]) == Counter(e["eid"] for e in entries)
    assert Counter(r["id"] for r in imported["items"]) == Counter(e["eid"] for e in entries)
    assert len({r["system"]["product_uuid"] for r in reviewed["items"]}) == 4
    assert all(r["gemini"]["span"] == "L1-1" for r in reviewed["items"])
    for page_size in (7, 25, 50):
        review_pages, import_pages = [], []
        for offset in range(0, 96, page_size):
            rp, ip, _ = fetch(pg, import_id, limit=page_size, offset=offset)
            review_pages.extend(rp["items"])
            import_pages.extend(ip["items"])
        assert review_pages == reviewed["items"]
        assert import_pages == imported["items"]
    assert snapshot(pg) == before


def test_unknown_state_missing_values_and_inactive_source_remain(pg):
    entries = []
    for state, price, resolved in (("Case", 100, True), ("Case", None, True),
                                   ("Empty box", 50, True), ("Searched pack", 9, False)):
        entries.append(seed(pg, name="Test Booster", reasons="", condition_id=pg["normal"],
                            condition_canonical=state, price_normalized=price,
                            product_id=pg["product"] if resolved else None, pid_resolved=resolved,
                            note_ja=f"{state}:{price}:{resolved}"))
    inactive = seed(pg, name="Inactive", reasons="", condition_canonical="Case", condition_id=pg["normal"])
    entries.append(inactive)
    pending = {"smid": str(uuid4()), "job": str(uuid4()), "eid": str(uuid4())}
    with pg["connection"].cursor() as cursor:
        cursor.execute("UPDATE public.source_messages SET is_active=false WHERE id=%s", (inactive["smid"],))
        # ADR-158: delivery visibility is now controlled by ar.is_current (not sm.is_active).
        # Mark the inactive source's analysis_result as not current so fetch_output_rows excludes it.
        cursor.execute("UPDATE public.analysis_results SET is_current=false WHERE extraction_item_id=%s",
                       (inactive["eid"],))
        cursor.execute("INSERT INTO public.source_messages(id,raw_text,raw_sha256,is_active) "
                       "VALUES (%s,'pending',%s,true)", (pending["smid"], uuid4().hex * 2))
        cursor.execute("INSERT INTO public.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'done')",
                       (pending["job"], pending["smid"]))
        cursor.execute("INSERT INTO public.extraction_items(id,extraction_job_id,raw_product_name) "
                       "VALUES (%s,%s,'pending')", (pending["eid"], pending["job"]))
    entries.append(pending)
    import_id = link_import(pg, entries)
    before = snapshot(pg)
    reviewed, imported, output = fetch(pg, import_id)
    assert reviewed["total"] == 4
    assert imported["total"] == 6
    assert set(r["id"] for r in imported["items"]) == {e["eid"] for e in entries}
    assert [r["extraction_item_id"] for r in reviewed["items"]] == [e["eid"] for e in entries[:4]]
    assert imported["items"][-1]["id"] == pending["eid"]
    assert imported["items"][-1]["analysis_result_id"] is None
    assert len(output) == 1 and output[0][7] == "Case:100:True"
    assert snapshot(pg) == before


def test_same_price_uuid_tiebreak_and_current_confirmed_condition(pg):
    with pg["connection"].cursor() as cursor:
        cursor.execute("INSERT INTO public.conditions(code,canonical,priority,app_kubun,is_active) "
                       "VALUES ('CN0098','Case',1,'箱系',true) RETURNING id")
        case_id = str(cursor.fetchone()[0])
    confirmed = seed(pg, name="Test Booster", reasons="", condition_id=pg["normal"],
                     condition_canonical="Searched pack", note_ja="confirmed-case")
    save(pg, confirmed, request(pg, confirmed, decision="correct", target=case_id))
    with pg["connection"].cursor() as cursor:
        # The current acknowledgement takes precedence over a stale stored label.
        cursor.execute("UPDATE public.analysis_results SET condition_canonical='Searched pack' "
                       "WHERE extraction_item_id=%s", (confirmed["eid"],))
    ties = [seed(pg, name="Test Booster", reasons="", condition_id=pg["normal"],
                 condition_canonical="Sealed box", note_ja=str(i)) for i in range(3)]
    import_id = link_import(pg, [confirmed, *ties])
    before = snapshot(pg)
    reviewed, imported, output = fetch(pg, import_id)
    expected = [confirmed["eid"], *sorted(e["eid"] for e in ties)]
    assert [r["extraction_item_id"] for r in reviewed["items"]] == expected
    assert [r["id"] for r in imported["items"]] == expected
    assert reviewed["items"][0]["system"]["condition"] == "Case"
    assert output[0][4] == "Case" and output[0][7] == "confirmed-case"
    assert snapshot(pg) == before


def test_larger_result_set_public_pages_and_read_only_delivery(pg):
    """Measure real queries over 4,097 rows; this is not production telemetry."""
    import json
    import warnings

    from psycopg2.extras import execute_values
    from sqlalchemy import text

    baseline = seed(pg, name="Test Booster", reasons="", condition_id=pg["normal"],
                    condition_canonical="Case", note_ja="baseline")
    entries = [{"smid": str(uuid4()), "job": str(uuid4()), "eid": str(uuid4())}
               for _ in range(4096)]
    expected = [(0, 10, baseline["eid"], "baseline")]
    with pg["connection"].cursor() as cursor:
        cursor.execute("SELECT supplier_channel_id,raw_text,raw_sha256,received_at "
                       "FROM public.source_messages WHERE id=%s", (baseline["smid"],))
        source = cursor.fetchone()
        execute_values(cursor, "INSERT INTO public.source_messages "
                       "(id,supplier_channel_id,raw_text,raw_sha256,received_at,is_active) VALUES %s",
                       [(e["smid"], *source, True) for e in entries])
        execute_values(cursor, "INSERT INTO public.extraction_jobs "
                       "(id,source_message_id,status) VALUES %s",
                       [(e["job"], e["smid"], "done") for e in entries])
        execute_values(cursor, "INSERT INTO public.extraction_items "
                       "(id,extraction_job_id,line_start,line_end,raw_product_name,raw_quantity,raw_price,raw_unit) VALUES %s",
                       [(e["eid"], e["job"], 1, 1, "Test Booster", "1", "10", "Box") for e in entries])
        values = []
        for n, entry in enumerate(entries):
            rank, price = n % 8, (n * 17) % 1000 + 1
            expected.append((rank, price, entry["eid"], str(n)))
            values.append((entry["eid"], pg["product"], True, "EXACT", pg["unit"], "Box", True,
                           pg["normal"], STATES[rank], "TEST", 1, price, str(n), "active", False, "test"))
        execute_values(cursor, "INSERT INTO public.analysis_results "
                       "(extraction_item_id,product_id,pid_resolved,pid_basis,unit_id,unit_canonical,unit_resolved,"
                       "condition_id,condition_canonical,condition_basis,quantity_normalized,price_normalized,"
                       "note_ja,status,needs_review,engine_version) VALUES %s", values)
    import_id = link_import(pg, [baseline, *entries])
    statistics = {}
    with pg["connection"].cursor() as cursor:
        for phase in ("before_analyze", "after_analyze"):
            if phase == "after_analyze":
                # Prepare planner statistics only in the disposable fixture DB.
                # This does not change production settings or the 10-second bound.
                for table in ("source_messages", "extraction_jobs", "extraction_items", "analysis_results",
                              "import_jobs", "import_job_messages", "item_corrections",
                              "supplier_channels"):
                    cursor.execute(f"ANALYZE public.{table}")
                cursor.execute("ANALYZE public.products")
                cursor.execute("ANALYZE public.conditions")
            cursor.execute("SELECT relname,reltuples FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                           "WHERE n.nspname='public' AND relname IN "
                           "('source_messages','extraction_jobs','extraction_items','analysis_results') ORDER BY relname")
            statistics[phase] = cursor.fetchall()
    before = snapshot(pg)
    plans = []

    async def run():
        engine = create_async_engine(pg["url"])
        try:
            async with AsyncSession(engine) as db:
                await db.execute(text("SET TRANSACTION READ ONLY"))
                await db.execute(text("SET LOCAL statement_timeout = '10s'"))
                assert (await db.execute(text("SHOW transaction_read_only"))).scalar_one() == "on"

                class MeasuredSession:
                    consumer = ""

                    async def execute(self, statement, parameters=None):
                        estimated = (await db.execute(text("EXPLAIN (FORMAT JSON) " + str(statement)),
                                                       parameters)).scalar_one()[0]
                        try:
                            result = await db.execute(statement, parameters)
                        except Exception:
                            warnings.warn("RESULT_ORDER_QUERY_TIMEOUT_PLAN " + json.dumps({
                                "consumer": self.consumer, "statistics": statistics,
                                "plan": estimated}), UserWarning, stacklevel=2)
                            raise
                        explanation = await db.execute(text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) "
                                                            + str(statement)), parameters)
                        plan = explanation.scalar_one()[0]
                        plans.append({"consumer": self.consumer,
                                      "limit": (parameters or {}).get("limit"),
                                      "offset": (parameters or {}).get("offset"),
                                      "execution_ms": plan["Execution Time"],
                                      "planning_ms": plan["Planning Time"],
                                      "actual_rows": plan["Plan"]["Actual Rows"]})
                        return result

                measured = MeasuredSession()
                measured.consumer = "review"
                reviewed = [await review.fetch_analysis_results(measured, limit=500, offset=offset)
                            for offset in (0, 4000)]
                measured.consumer = "import"
                imported = [await progress.read_items(measured, import_id, 100, offset, "all")
                            for offset in (0, 4000)]
                measured.consumer = "distribution"
                output = await distribution.fetch_output_rows(measured)
                return reviewed, imported, output
        finally:
            await engine.dispose()

    reviewed, imported, output = asyncio.run(run())
    expected.sort()
    assert len(output) == 4097
    for offset, review_page, import_page in zip((0, 4000), reviewed, imported):
        assert review_page["total"] == import_page["total"] == 4097
        assert [r["extraction_item_id"] for r in review_page["items"]] == [r[2] for r in expected[offset:offset+500]]
        assert [r["id"] for r in import_page["items"]] == [r[2] for r in expected[offset:offset+100]]
    assert [r[7] for r in output] == [r[3] for r in expected]
    assert snapshot(pg) == before
    assert {p["consumer"] for p in plans} == {"review", "import", "distribution"}
    # pytest-xdist does not forward worker stdout; a warning preserves the
    # bounded measurements in the existing CI log without changing CI settings.
    warnings.warn("RESULT_ORDER_QUERY_PLANS " + json.dumps({"rows": 4097, "sources": 4097,
                  "transaction_read_only": True, "statement_timeout_ms": 10000,
                  "measurement": "EXPLAIN ANALYZE after each query; warm cache; isolated CI",
                  "statistics": statistics, "plans": plans}), UserWarning, stacklevel=1)
