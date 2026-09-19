"""R1–R8: actual PostgreSQL roundtrip snapshots and bounded competing writers."""

import asyncio
import csv
import hashlib
import io
import json

import psycopg2
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.services import tcg_product_roundtrip_svc as svc
from tests import test_tcg_product_import_atomicity_pg as atomic_fixture
from tests.test_tcg_work_matching_integration import SCHEMA

atomic_pg = atomic_fixture.atomic_pg
pg = atomic_fixture.pg


def observe(connection, history=True):
    result = {}
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_jsonb(t) FROM public.products t ORDER BY t.id")
        result["products"] = cursor.fetchall()
        for table in ["product_search_keywords", "product_exclude_keywords"]:
            cursor.execute(f"SELECT to_jsonb(t) FROM {SCHEMA}.{table} t ORDER BY id")
            result[table] = cursor.fetchall()
        if history:
            for table in ["tcg_product_import_jobs", "tcg_product_import_rows"]:
                cursor.execute(f"SELECT to_jsonb(t) FROM {SCHEMA}.{table} t ORDER BY id")
                result[table] = cursor.fetchall()
    return result


def seed(connection, count=2):
    with connection.cursor() as cursor:
        for index in range(count):
            cursor.execute(
                "INSERT INTO public.products(product_code,name,name_en,mark,category_class,is_active,work_id) "
                "VALUES (%s,%s,%s,%s,'private category',false,(SELECT id FROM public.tcg_type_master WHERE code='one_piece')) RETURNING id",
                (
                    "RTSENT" if index == 0 else f"RT{index:03}",
                    f"商品{index}",
                    None if index == 0 else "",
                    None if index == 0 else "",
                ),
            )
            pid = cursor.fetchone()[0]
            for table in svc.WORDS.values():
                for position, word in [(3, ""), (7, ' =,全角＝\r\n"quote"'), (19, " duplicate "), (23, " duplicate ")]:
                    cursor.execute(
                        f"INSERT INTO {SCHEMA}.{table}(product_id,keyword,position) VALUES (%s,%s,%s)",
                        (pid, word, position),
                    )
        cursor.execute("UPDATE public.tcg_type_master SET is_active=false WHERE code='one_piece'")


def edit(raw, changes, *, single=False):
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline="")))
    for field, value in changes.items():
        rows[1][rows[0].index(field)] = svc.escape_cell(value)
    if single:
        rows = rows[:2]
    out = io.StringIO(newline="")
    csv.writer(out).writerows(rows)
    return out.getvalue().encode("utf-8-sig")


async def submit(db, raw):
    return await svc.commit_update(db, raw, "roundtrip.csv", "test", hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize("count", [2, 61])
def test_exact_unchanged_snapshot_and_filters(atomic_pg, monkeypatch, count):
    connection, url = atomic_pg
    monkeypatch.setattr(svc, "TCG_SCHEMA", SCHEMA)
    seed(connection, count)
    before = observe(connection, False)

    async def run():
        engine = create_async_engine(url)
        try:
            async with AsyncSession(engine) as db:
                raw = await svc.export_csv(db)
                assert len(svc.read_records(raw)) == count + 2
                empty = await svc.export_csv(db, "not found")
                assert len(svc.read_records(empty)) == 1
                with connection.cursor() as cur:
                    cur.execute("SELECT id FROM public.tcg_type_master WHERE code='one_piece'")
                    work = str(cur.fetchone()[0])
                selected = await svc.export_csv(db, "商品0", work)
                assert len(svc.read_records(selected)) == 2
                checked = await svc.preview_update(db, raw, "roundtrip.csv")
                assert checked["unchanged"] == count + 1 and checked["blocked"] == 0
                result = await submit(db, raw)
                assert result["created"] == result["updated"] == 0 and result["unchanged"] == count + 1
                assert observe(connection, False) == before
                receipt = observe(connection)
                with pytest.raises(svc.RoundtripError, match="ALREADY_IMPORTED"):
                    await submit(db, raw)
                assert observe(connection) == receipt
        finally:
            await engine.dispose()

    asyncio.run(run())


def test_all_editable_fields_and_words_preserve_identity(atomic_pg, monkeypatch):
    connection, url = atomic_pg
    monkeypatch.setattr(svc, "TCG_SCHEMA", SCHEMA)
    seed(connection)
    before = observe(connection, False)

    async def run():
        engine = create_async_engine(url)
        try:
            async with AsyncSession(engine) as db:
                original = await svc.export_csv(db, "商品")
                changes = {
                    "japanese_title": "編集商品",
                    "english_title": " new title ",
                    "mark": "=001",
                    "release_date": "2028-02-29",
                    "division_code": "DIV01",
                    "work_code": "pokemon_booster_box",
                    "manufacturer_code": "MK001",
                    "product_category_code": "PC_BOX",
                    "search_keywords": svc.encode_words([" a,b ", '"quoted"', "\r\nword", "＝1"]),
                    "exclude_keywords": "",
                }
                raw = edit(original, changes, single=True)
                result = await submit(db, raw)
                assert result["updated"] == 1 and result["created"] == 0
                exported = svc.read_records(await svc.export_csv(db))
                actual = {
                    row[0]: dict(zip(exported[0], map(svc.unescape_cell, row), strict=True)) for row in exported[1:]
                }
                code = svc.read_records(original)[1][0]
                for field, value in changes.items():
                    assert actual[code][field] == value
                after = observe(connection, False)
                with connection.cursor() as cursor:
                    cursor.execute("SELECT category_class FROM public.products WHERE product_code=%s", (code,))
                    assert cursor.fetchone()[0] == "ポケモンカード"
                    cursor.execute(
                        f"SELECT messages FROM {SCHEMA}.tcg_product_import_rows WHERE product_code=%s", (code,)
                    )
                    messages = {item["field"]: item for item in json.loads(cursor.fetchone()[0])}
                    original_row = dict(
                        zip(svc.COLUMNS, map(svc.unescape_cell, svc.read_records(original)[1]), strict=True)
                    )
                    for field, value in changes.items():
                        expected_before = (
                            svc.decode_words(original_row[field]) if field in svc.WORDS else original_row[field]
                        )
                        expected_after = svc.decode_words(value) if field in svc.WORDS else value
                        assert messages[field] == {"field": field, "before": expected_before, "after": expected_after}
                old = {row[0]["id"]: row[0] for row in before["products"]}
                for row in after["products"]:
                    product = row[0]
                    if product["product_code"] != code:
                        assert product == old[product["id"]]
                    for field in ["product_code", "id", "created_at"]:
                        assert product[field] == old[product["id"]][field]
                untouched = {pid for pid, p in old.items() if p["product_code"] != code}
                for table in svc.WORDS.values():
                    assert [r for r in before[table] if r[0]["product_id"] in untouched] == [
                        r for r in after[table] if r[0]["product_id"] in untouched
                    ]
                next_raw = await svc.export_csv(db, "商品")
                assert (await svc.preview_update(db, next_raw, "again.csv"))["unchanged"] == 2
        finally:
            await engine.dispose()

    asyncio.run(run())


def test_other_field_edit_keeps_inactive_reference_and_word_rows(atomic_pg, monkeypatch):
    connection, url = atomic_pg
    monkeypatch.setattr(svc, "TCG_SCHEMA", SCHEMA)
    seed(connection)
    before = observe(connection, False)

    async def run():
        engine = create_async_engine(url)
        try:
            async with AsyncSession(engine) as db:
                raw = edit(await svc.export_csv(db, "商品"), {"mark": "new"}, single=True)
                assert (await submit(db, raw))["updated"] == 1
            after = observe(connection, False)
            for table in svc.WORDS.values():
                assert after[table] == before[table]
            old = {r[0]["id"]: r[0] for r in before["products"]}
            for row in after["products"]:
                value = dict(row[0])
                value["mark"] = old[value["id"]]["mark"]
                assert value == old[value["id"]]
        finally:
            await engine.dispose()

    asyncio.run(run())


@pytest.mark.parametrize(
    "mode", ["title", "search", "exclude", "active", "hidden", "code", "unknown", "duplicate", "date", "reference"]
)
def test_stale_and_validation_write_nothing(atomic_pg, monkeypatch, mode):
    connection, url = atomic_pg
    monkeypatch.setattr(svc, "TCG_SCHEMA", SCHEMA)
    seed(connection)

    async def run():
        engine = create_async_engine(url)
        try:
            async with AsyncSession(engine) as db:
                raw = await svc.export_csv(db, "商品")
                await svc.preview_update(db, raw, "x.csv")
                with connection.cursor() as cursor:
                    if mode in ["search", "exclude"]:
                        cursor.execute(
                            f"UPDATE {SCHEMA}.product_{mode}_keywords SET keyword='changed' WHERE position=7"
                        )
                    elif mode in ["title", "active", "hidden"]:
                        assignment = {
                            "title": "name='changed'",
                            "active": "is_active=true",
                            "hidden": "required_output_value='changed'",
                        }[mode]
                        cursor.execute(f"UPDATE public.products SET {assignment} WHERE product_code LIKE 'RT%%'")
                if mode in ["unknown", "date", "reference"]:
                    raw = edit(
                        raw,
                        {
                            "code": {"product_code": "RT000"},
                            "unknown": {"product_code": "absent"},
                            "date": {"release_date": "2026-02-30"},
                            "reference": {"work_code": "absent"},
                        }[mode],
                    )
                if mode == "duplicate":
                    rows = svc.read_records(raw)
                    rows[2] = rows[1]
                    out = io.StringIO()
                    csv.writer(out).writerows(rows)
                    raw = out.getvalue().encode()
                if mode == "code":
                    rows = svc.read_records(raw)
                    rows[1][0], rows[2][0] = rows[2][0], rows[1][0]
                    out = io.StringIO()
                    csv.writer(out).writerows(rows)
                    raw = out.getvalue().encode()
                    checked = await svc.preview_update(db, raw, "swap.csv")
                    assert all(row["blocking"] == ["ROUNDTRIP_STALE"] for row in checked["rows"])
                before = observe(connection)
                with pytest.raises(svc.RoundtripError):
                    await submit(db, raw)
                assert observe(connection) == before
        finally:
            await engine.dispose()

    asyncio.run(run())


@pytest.mark.parametrize("mode", ["product", "words", "history", "commit_before", "commit_after", "cancel", "rollback"])
def test_atomic_failures_and_unknown_commit(atomic_pg, monkeypatch, mode):
    connection, url = atomic_pg
    monkeypatch.setattr(svc, "TCG_SCHEMA", SCHEMA)
    seed(connection)
    before = observe(connection)
    failure = asyncio.CancelledError("cancel") if mode == "cancel" else RuntimeError("injected")

    class Writer(AsyncSession):
        current = 0

        async def execute(self, statement, params=None, **kwargs):
            query = str(statement)
            if query.startswith("UPDATE public.products"):
                self.current += 1
            if self.current == 2 and (
                (mode in ["product", "cancel", "rollback"] and query.startswith("UPDATE public.products"))
                or (mode == "words" and query.startswith("INSERT INTO public.product_search_keywords"))
                or (mode == "history" and query.startswith(f"INSERT INTO {SCHEMA}.tcg_product_import_rows"))
            ):
                raise failure
            return await super().execute(statement, params, **kwargs)

        async def commit(self):
            if mode == "commit_before":
                raise failure
            await super().commit()
            if mode == "commit_after":
                raise failure

        async def rollback(self):
            await super().rollback()
            if mode == "rollback":
                raise RuntimeError("rollback response")

    async def run():
        engine = create_async_engine(url)
        try:
            async with Writer(engine) as db:
                records = svc.read_records(await svc.export_csv(db, "商品"))
                for row in records[1:]:
                    row[records[0].index("japanese_title")] = "Changed"
                    row[records[0].index("search_keywords")] = "new,word"
                    row[records[0].index("exclude_keywords")] = "excluded"
                out = io.StringIO()
                csv.writer(out).writerows(records)
                raw = out.getvalue().encode()
                with pytest.raises(type(failure)) as caught:
                    await submit(db, raw)
                assert caught.value is failure
            if mode == "commit_after":
                after = observe(connection)
                assert (
                    after != before
                    and len(after["tcg_product_import_jobs"]) == 1
                    and len(after["tcg_product_import_rows"]) == 2
                )
                seeded = [r for r in after["products"] if r[0]["product_code"].startswith("RT")]
                assert all(r[0]["name"] == "Changed" for r in seeded)
                for product in seeded:
                    pid = product[0]["id"]
                    assert sorted(
                        (r[0]["position"], r[0]["keyword"])
                        for r in after["product_search_keywords"]
                        if r[0]["product_id"] == pid
                    ) == [(1, "new"), (2, "word")]
                    assert [
                        (r[0]["position"], r[0]["keyword"])
                        for r in after["product_exclude_keywords"]
                        if r[0]["product_id"] == pid
                    ] == [(1, "excluded")]
                assert all(r[0]["result"] == "updated" for r in after["tcg_product_import_rows"])
                async with AsyncSession(engine) as retry:
                    with pytest.raises(svc.RoundtripError, match="ALREADY_IMPORTED"):
                        await submit(retry, raw)
                assert observe(connection) == after
            else:
                assert observe(connection) == before
        finally:
            await engine.dispose()

    asyncio.run(run())


@pytest.mark.parametrize("target", ["product", "keyword"])
def test_competing_writer_blocked_and_lock_released(atomic_pg, monkeypatch, target):
    connection, url = atomic_pg
    monkeypatch.setattr(svc, "TCG_SCHEMA", SCHEMA)
    seed(connection)

    def competing(blocked):
        with connection.cursor() as cursor:
            cursor.execute("SET lock_timeout='100ms'")
            query = (
                "UPDATE public.products SET mark='competing' WHERE product_code LIKE 'RT%'"
                if target == "product"
                else "INSERT INTO public.product_search_keywords(product_id,keyword,position) SELECT id,'competing',99 FROM public.products WHERE product_code LIKE 'RT%%'"
            )
            if blocked:
                with pytest.raises(psycopg2.errors.LockNotAvailable):
                    cursor.execute(query)
            else:
                cursor.execute(query)

    class Writer(AsyncSession):
        async def commit(self):
            await asyncio.wait_for(asyncio.to_thread(competing, True), 5)
            await super().commit()

    async def run():
        engine = create_async_engine(url)
        try:
            async with Writer(engine) as db:
                await submit(db, edit(await svc.export_csv(db, "商品"), {"japanese_title": "new"}))
            await asyncio.wait_for(asyncio.to_thread(competing, False), 5)
        finally:
            await engine.dispose()

    asyncio.run(run())
