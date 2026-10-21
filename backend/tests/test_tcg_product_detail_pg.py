"""DETAIL-01 read/write contracts in disposable PostgreSQL only."""
import asyncio
import csv
import hashlib
import io
import json
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.auth.dependencies import get_current_user
from app.routers import tcg_product_import as routes
from app.services import tcg_product_detail_svc as details
from app.services import tcg_product_master_svc as master
from app.services import tcg_product_roundtrip_svc as roundtrip
from tests import test_tcg_product_list_pg as fixtures
from tests import test_tcg_work_matching_integration as durable
from tests.rls_bootstrap import provision_packagings_sync

product_db = fixtures.product_db
pytestmark = fixtures.pytestmark


async def _pid(db, code: str) -> int:
    """Resolve product_code to integer id for tests."""
    row = (await db.execute(text("SELECT id FROM public.products WHERE product_code=:c"), {"c": code})).fetchone()
    assert row is not None, f"product_code {code!r} not found"
    return int(row[0])


@pytest_asyncio.fixture
async def detail_db(product_db, monkeypatch):
    db, schema = product_db
    monkeypatch.setattr(details, "TCG_SCHEMA", schema)
    await db.execute(text(
        "INSERT INTO public.products "
        "(product_code,name,name_en,mark,category_class,is_active,required_output_value) "
        "VALUES ('DETAIL','Japanese','English detail','MODEL-DETAIL','Original',false,'Keep this')"
    ))
    await db.execute(text(
        "INSERT INTO public.product_search_keywords(product_id,keyword,position) "
        "SELECT id,'Alpha, Beta',1 FROM public.products WHERE product_code='DETAIL'"
    ))
    await db.execute(text(
        "INSERT INTO public.product_exclude_keywords(product_id,keyword,position) "
        "SELECT id,'Exclude one',1 FROM public.products WHERE product_code='DETAIL'"
    ))
    return db, schema


async def test_detail_contains_stored_values_words_and_revision(detail_db):
    db, schema = detail_db
    pid = await _pid(db, "DETAIL")
    before = await details.get_product_detail(db, pid)
    product = before["product"]
    assert product["japanese_title"] == "Japanese"
    assert product["english_title"] == "English detail"
    assert product["is_active"] is False
    assert product["required_output_value"] == "Keep this"
    assert product["search_keywords"] == ["Alpha, Beta"]
    assert product["exclude_keywords"] == ["Exclude one"]
    assert len(before["revision"]) == 64
    assert before["revision"] == (await details.get_product_detail(db, pid))["revision"]
    assert set(before["lookups"]) == {"product_kind_id", "work_id", "manufacturer_id", "product_category_id",
                                      "product_format_id"}
    await db.execute(text(
        "INSERT INTO public.product_exclude_keywords(product_id,keyword,position) "
        "SELECT id,'Exclude two',2 FROM public.products WHERE product_code='DETAIL'"
    ))
    assert before["revision"] != (await details.get_product_detail(db, pid))["revision"]


@pytest.mark.parametrize("query", ["english DETAIL", "MODEL-DETAIL"])
async def test_list_finds_english_and_mark_with_both_counts(detail_db, query):
    db, _ = detail_db
    result = await routes.list_products(query=query, limit=50, offset=0, work_id=None, db=db, _user={})
    assert result.total == 1
    assert result.items[0].keyword_count == 1
    assert result.items[0].exclude_keyword_count == 1
    assert result.items[0].english_title == "English detail"


@pytest.mark.parametrize("is_admin,use_missing,status", [(True, False, 200), (True, True, 404), (False, False, 403)])
async def test_detail_route_uses_actual_admin_dependency(detail_db, is_admin, use_missing, status):
    db, _ = detail_db
    pid = await _pid(db, "DETAIL")
    route_id = 999999 if use_missing else pid
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    app.dependency_overrides[routes.get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(is_super_admin=is_admin)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/tcg/products/detail/{route_id}")
    assert response.status_code == status


pg = durable.pg


@pytest.fixture
def edit_pg(pg, monkeypatch):
    connection, _, url = pg
    for module in (details, master, routes):
        monkeypatch.setattr(module, "TCG_SCHEMA", durable.SCHEMA)
    with connection.cursor() as cur:
        provision_packagings_sync(cur)  # ADR-1028 便4: 荷姿の表と 4 単位（詳細サービスが読む）
        for code in ("DETAIL", "SENTINEL"):
            cur.execute(
                "INSERT INTO public.products "
                "(product_code,name,category_class,is_active,required_output_value) "
                "VALUES (%s,'Original','Keep category',true,'Keep output') RETURNING id", (code,))
            pid = cur.fetchone()[0]
            for table in details.WORD_TABLES.values():
                cur.execute(f"INSERT INTO {durable.SCHEMA}.{table}(product_id,keyword,position) "
                            "VALUES (%s,'Alpha, Beta',1)", (pid,))
        cur.execute(f"INSERT INTO {durable.SCHEMA}.source_messages(raw_text,raw_sha256,is_active) "
                    "VALUES ('fixture',%s,true) RETURNING id", ("0" * 64,))
        smid = cur.fetchone()[0]
        cur.execute(f"INSERT INTO {durable.SCHEMA}.extraction_jobs(source_message_id,status) "
                    "VALUES (%s,'done') RETURNING id", (smid,))
        job = cur.fetchone()[0]
        cur.execute(f"INSERT INTO {durable.SCHEMA}.extraction_items(extraction_job_id) VALUES (%s) RETURNING id", (job,))
        item = cur.fetchone()[0]
        cur.execute("SELECT id FROM public.conditions LIMIT 1")
        cond_id = cur.fetchone()[0]
        cur.execute(f"INSERT INTO {durable.SCHEMA}.analysis_results "
                    "(extraction_item_id,product_id,pid_resolved,unit_resolved,needs_review,engine_version,condition_id) "
                    "SELECT %s,id,true,false,true,'fixture',%s FROM public.products WHERE product_code='DETAIL'", (item, cond_id))
        durable.provision(cur, "tenant_990")
        cur.execute("INSERT INTO tenant_990.tcg_products(code,japanese_title,category_class,is_active) "
                    "VALUES ('DETAIL','Other tenant','Other',true) RETURNING id")
        other_pid = cur.fetchone()[0]
        for table in details.WORD_TABLES.values():
            cur.execute(f"INSERT INTO tenant_990.{table}(product_id,keyword,position) VALUES (%s,'Other',1)", (other_pid,))
    def other_rows():
        with connection.cursor() as cur:
            rows = {}
            for table in ("tcg_products", *details.WORD_TABLES.values(), "audit_log"):
                cur.execute(f"SELECT row_to_json(t) FROM tenant_990.{table} t ORDER BY id")
                rows[table] = cur.fetchall()
            return rows
    before = other_rows()
    yield connection, url
    assert other_rows() == before


def observed(connection):
    with connection.cursor() as cur:
        result = {}
        cur.execute("SELECT row_to_json(t) FROM public.products t ORDER BY t.id")
        result["products"] = [r[0] for r in cur.fetchall()]
        for table in (*details.WORD_TABLES.values(), "audit_log", "analysis_results"):
            cur.execute(f"SELECT row_to_json(t) FROM {durable.SCHEMA}.{table} t ORDER BY id")
            result[table] = [r[0] for r in cur.fetchall()]
        return result


def edit_values(snapshot):
    p = snapshot["product"]
    return {field: (p.get(field) or "") if field in ("english_title", "mark") else p.get(field)
            for field in ("japanese_title", "english_title", "mark", "release_date", *details.LOOKUPS,
                          *details.PUBLIC_INTEGER_LOOKUPS, *details.WORD_TABLES)}


async def test_edit_commits_details_words_audit_and_preserves_identity(edit_pg):
    connection, url = edit_pg
    before = observed(connection)
    engine = create_async_engine(url)
    try:
        async with AsyncSession(engine) as db:
            pid = await _pid(db, "DETAIL")
            snapshot = await details.get_product_detail(db, pid)
            values = edit_values(snapshot)
            values.update(japanese_title="Edited", english_title="English edited", mark="MODEL",
                          release_date="2026-09-14", search_keywords=["A, B", "C"], exclude_keywords=[],
                          blank_confirmations=["exclude_keywords"])  # ADR-1020 便3: 除外ワードを空にするには印が要る
            result = await details.update_product_detail(db, pid, values, snapshot["revision"], "ci-reviewer")
        after = observed(connection)
        product = result["product"]
        assert product["id"] == snapshot["product"]["id"]
        assert product["code"] == "DETAIL" and product["required_output_value"] == "Keep output"
        assert product["category_class"] == "Keep category" and product["is_active"] is True
        assert product["release_date"] == "2026-09-14" and product["mark"] == "MODEL"
        assert product["english_title"] == "English edited"
        assert product["search_keywords"] == ["A, B", "C"] and product["exclude_keywords"] == []
        assert result["revision"] != snapshot["revision"]
        sentinel = next(p for p in before["products"] if p["product_code"] == "SENTINEL")
        assert sentinel in after["products"]
        for table in details.WORD_TABLES.values():
            assert [r for r in before[table] if r["product_id"] == sentinel["id"]] == [
                r for r in after[table] if r["product_id"] == sentinel["id"]]
        assert after["analysis_results"] == before["analysis_results"]
        assert len(after["audit_log"]) == 1
        audit = after["audit_log"][0]
        assert audit["changed_by"] == "ci-reviewer"
        import uuid as _uuid_mod; _uuid_mod.UUID(audit["record_id"])  # valid UUID
        assert json.loads(audit["old_values"])["product"]["name"] == "Original"
        assert json.loads(audit["new_values"])["product"]["name"] == "Edited"
    finally:
        await engine.dispose()


async def test_empty_mark_and_english_title_are_saved_as_null_and_values_kept(edit_pg):
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        async with AsyncSession(engine) as db:
            pid = await _pid(db, "DETAIL")
            snapshot = await details.get_product_detail(db, pid)
            values = edit_values(snapshot)
            values.update(mark="  ", english_title="")
            result = await details.update_product_detail(db, pid, values, snapshot["revision"], "test")
            row = (await db.execute(text("SELECT mark, name_en, name FROM public.products WHERE id=:p"), {"p": pid})).one()
            assert row.mark is None and row.name_en is None and row.name == "Original"
            assert result["product"]["mark"] is None and result["product"]["english_title"] is None
            # 値ありはそのまま、NULL のまま再保存しても audit の変更前後に mark の差は出ない
            snapshot = await details.get_product_detail(db, pid)
            values = edit_values(snapshot)
            values.update(mark="KEEP", english_title="Kept EN")
            await details.update_product_detail(db, pid, values, snapshot["revision"], "test")
            row = (await db.execute(text("SELECT mark, name_en FROM public.products WHERE id=:p"), {"p": pid})).one()
            assert row.mark == "KEEP" and row.name_en == "Kept EN"
    finally:
        await engine.dispose()


async def test_unchanged_words_keep_row_ids_and_stale_edit_is_rejected(edit_pg):
    connection, url = edit_pg
    before = observed(connection)
    engine = create_async_engine(url)
    try:
        async with AsyncSession(engine) as db:
            pid = await _pid(db, "DETAIL")
            snapshot = await details.get_product_detail(db, pid)
            values = edit_values(snapshot)
            values["english_title"] = "Change only title"
            await details.update_product_detail(db, pid, values, snapshot["revision"], "test")
            after = observed(connection)
            for table in details.WORD_TABLES.values():
                assert after[table] == before[table]
            with pytest.raises(details.ProductDetailError) as caught:
                await details.update_product_detail(db, pid, values, snapshot["revision"], "test")
            assert caught.value.status == 409
            assert observed(connection) == after
    finally:
        await engine.dispose()


@pytest.mark.parametrize("stage", ["words", "audit", "commit", "cancel"])
async def test_failed_edit_rolls_back_product_words_and_audit(edit_pg, stage):
    connection, url = edit_pg
    before = observed(connection)
    with connection.cursor() as _cur:
        _cur.execute("SELECT id FROM public.products WHERE product_code='DETAIL'")
        _pid_int = int(_cur.fetchone()[0])
    class FailingSession(AsyncSession):
        async def execute(self, statement, params=None, **kwargs):
            query = str(statement)
            if stage in ("words", "cancel") and "INSERT INTO" in query and "product_search_keywords" in query:
                if stage == "cancel":
                    raise asyncio.CancelledError()
                raise RuntimeError("injected keyword failure")
            if stage == "audit" and "INSERT INTO" in query and "audit_log" in query:
                raise RuntimeError("injected audit failure")
            return await super().execute(statement, params, **kwargs)

        async def commit(self):
            if stage == "commit":
                raise RuntimeError("injected commit failure")
            return await super().commit()
    engine = create_async_engine(url)
    try:
        async with FailingSession(engine) as db:
            snapshot = await details.get_product_detail(db, _pid_int)
            values = edit_values(snapshot)
            values.update(japanese_title="Must roll back", search_keywords=["Replacement"], exclude_keywords=[],
                          blank_confirmations=["exclude_keywords"])  # ADR-1020 便3: 除外ワードを空にするには印が要る
            with pytest.raises(asyncio.CancelledError if stage == "cancel" else RuntimeError):
                await details.update_product_detail(db, _pid_int, values, snapshot["revision"], "test")
        assert observed(connection) == before
    finally:
        await engine.dispose()


async def test_simultaneous_edits_have_one_winner(edit_pg):
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        async with AsyncSession(engine) as reader:
            pid = await _pid(reader, "DETAIL")
            snapshot = await details.get_product_detail(reader, pid)
        async def write(title):
            async with AsyncSession(engine) as db:
                values = edit_values(snapshot)
                values["japanese_title"] = title
                try:
                    return await details.update_product_detail(db, pid, values, snapshot["revision"], "test")
                except details.ProductDetailError as exc:
                    return exc.status
        results = await asyncio.gather(write("First"), write("Second"))
        assert sum(isinstance(result, dict) for result in results) == 1
        assert results.count(409) == 1
        assert len(observed(connection)["audit_log"]) == 1
    finally:
        await engine.dispose()


async def test_keyword_addition_invalidates_open_draft(edit_pg):
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        async with AsyncSession(engine) as reader:
            pid = await _pid(reader, "DETAIL")
            snapshot = await details.get_product_detail(reader, pid)
        async with AsyncSession(engine) as writer:
            assert await master.add_search_keyword(writer, product_id=pid, new_keyword="Added") == {"ok": True}
        before = observed(connection)
        async with AsyncSession(engine) as writer:
            with pytest.raises(details.ProductDetailError) as caught:
                await details.update_product_detail(writer, pid, edit_values(snapshot), snapshot["revision"], "test")
            assert caught.value.status == 409
        assert observed(connection) == before
    finally:
        await engine.dispose()


@pytest.mark.parametrize("field,value", [
    ("japanese_title", " "), ("release_date", "2026-02-30"), ("release_date", "20260914"),
    ("work_id", "invalid"), ("search_keywords", [""]), ("exclude_keywords", ["x"] * 1001),
    ("code", "forbidden"), ("is_active", False),
])
async def test_update_rejects_invalid_payload_before_writing(detail_db, field, value):
    db, _ = detail_db
    pid = await _pid(db, "DETAIL")
    snapshot = await details.get_product_detail(db, pid)
    payload = dict(edit_values(snapshot), revision=snapshot["revision"])
    payload[field] = value
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[routes.get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(is_super_admin=True, email="test", id="test")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(f"/tcg/products/detail/{pid}", json=payload)
    assert response.status_code == 422
    assert (await details.get_product_detail(db, pid))["revision"] == snapshot["revision"]


@pytest.mark.parametrize("admin,use_missing,status", [(True, False, 200), (False, False, 403), (True, True, 404)])
async def test_update_route_and_real_permission_dependency(edit_pg, admin, use_missing, status):
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        async with AsyncSession(engine) as db:
            pid = await _pid(db, "DETAIL")
            route_id = 999999 if use_missing else pid
            snapshot = await details.get_product_detail(db, pid)
            payload = dict(edit_values(snapshot), revision=snapshot["revision"], english_title="Via HTTP")
            app = FastAPI()
            app.include_router(routes.router)
            app.dependency_overrides[routes.get_db] = lambda: db
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
                is_super_admin=admin, email="http-test", id="test")
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.put(f"/tcg/products/detail/{route_id}", json=payload)
            assert response.status_code == status
            assert len(observed(connection)["audit_log"]) == (1 if status == 200 else 0)
    finally:
        await engine.dispose()


async def test_classification_change_derives_work_name_and_rejects_unknown(edit_pg):
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        async with AsyncSession(engine) as db:
            pid = await _pid(db, "DETAIL")
            snapshot = await details.get_product_detail(db, pid)
            values = edit_values(snapshot)
            selected = snapshot["lookups"]["work_id"][0]
            values["work_id"] = selected["id"]
            updated = await details.update_product_detail(db, pid, values, snapshot["revision"], "test")
            assert updated["product"]["category_class"] == selected["name"]
            before = observed(connection)
            values["work_id"] = "00000000-0000-0000-0000-000000000000"
            with pytest.raises(details.ProductDetailError) as caught:
                await details.update_product_detail(db, pid, values, updated["revision"], "test")
            assert caught.value.status == 422
            assert observed(connection) == before
    finally:
        await engine.dispose()


async def test_lost_commit_response_keeps_one_atomic_change_and_stale_retry_fails(edit_pg):
    connection, url = edit_pg
    with connection.cursor() as _cur:
        _cur.execute("SELECT id FROM public.products WHERE product_code='DETAIL'")
        _pid_int = int(_cur.fetchone()[0])
    class LostResponse(AsyncSession):
        async def commit(self):
            await super().commit()
            raise RuntimeError("commit response lost")
    engine = create_async_engine(url)
    try:
        async with LostResponse(engine) as db:
            snapshot = await details.get_product_detail(db, _pid_int)
            values = edit_values(snapshot)
            values.update(japanese_title="Committed", search_keywords=["Replacement"], exclude_keywords=["New exclusion"])
            with pytest.raises(RuntimeError, match="response lost"):
                await details.update_product_detail(db, _pid_int, values, snapshot["revision"], "test")
        after = observed(connection)
        assert len(after["audit_log"]) == 1
        async with AsyncSession(engine) as reader:
            current = await details.get_product_detail(reader, _pid_int)
            assert current["product"]["japanese_title"] == "Committed"
            assert current["product"]["search_keywords"] == ["Replacement"]  # ADR-1020 便3: 検索ワードは印で空にできない
            assert current["product"]["exclude_keywords"] == ["New exclusion"]
            with pytest.raises(details.ProductDetailError) as caught:
                await details.update_product_detail(reader, _pid_int, values, snapshot["revision"], "test")
            assert caught.value.status == 409
        assert observed(connection) == after
    finally:
        await engine.dispose()


@pytest.mark.parametrize("query", ["english DETAIL", "MODEL-DETAIL"])
async def test_export_matches_english_and_model_list_filter(detail_db, monkeypatch, query):
    db, schema = detail_db
    monkeypatch.setattr(roundtrip, "TCG_SCHEMA", schema)
    result = await routes.list_products(query=query, limit=50, offset=0, work_id=None, db=db, _user={})
    raw = await roundtrip.export_csv(db, query)
    records = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    pid = await _pid(db, "DETAIL")
    assert [row["product_id"] for row in records] == [str(item.id) for item in result.items] == [str(pid)]


@pytest.mark.parametrize("csv_first", [True, False])
async def test_detail_and_csv_reject_each_others_stale_drafts(edit_pg, monkeypatch, csv_first):
    connection, url = edit_pg
    monkeypatch.setattr(roundtrip, "TCG_SCHEMA", durable.SCHEMA)
    with connection.cursor() as cur:
        cur.execute((durable.MIGRATIONS / "20260906_130000_create_tcg_product_import_history_t004.sql").read_text().replace("tenant_004", durable.SCHEMA))
    engine = create_async_engine(url)
    try:
        async with AsyncSession(engine) as db:
            pid = await _pid(db, "DETAIL")
            snapshot = await details.get_product_detail(db, pid)
            raw = await roundtrip.export_csv(db)
        records = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
        title_index = records[0].index("english_title")
        for row in records[1:]:
            if row[0] == str(pid):
                row[title_index] = "CSV change"
        out = io.StringIO(newline="")
        csv.writer(out).writerows(records)
        edited = out.getvalue().encode("utf-8-sig")
        digest = hashlib.sha256(edited).hexdigest()
        values = edit_values(snapshot)
        values["english_title"] = "Drawer change"
        async with AsyncSession(engine) as db:
            if csv_first:
                await roundtrip.commit_update(db, edited, "edit.csv", "test", digest)
            else:
                await details.update_product_detail(db, pid, values, snapshot["revision"], "test")
        before = observed(connection)
        async with AsyncSession(engine) as db:
            with pytest.raises(details.ProductDetailError if csv_first else roundtrip.RoundtripError) as caught:
                if csv_first:
                    await details.update_product_detail(db, pid, values, snapshot["revision"], "test")
                else:
                    await roundtrip.commit_update(db, edited, "edit.csv", "test", digest)
            assert caught.value.status == 409
        assert observed(connection) == before
    finally:
        await engine.dispose()


async def test_clearing_value_without_mark_is_rejected(edit_pg):
    """ADR-1020 便3: 値のあった型番を印なしで空にする保存は 422。印があれば保存でき、印の表に 1 行できる。"""
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        async with AsyncSession(engine) as db:
            pid = await _pid(db, "DETAIL")
            snapshot = await details.get_product_detail(db, pid)
            values = edit_values(snapshot)
            values.update(mark="MODEL")
            saved = await details.update_product_detail(db, pid, values, snapshot["revision"], "test")
        async with AsyncSession(engine) as db:
            values = edit_values(saved)
            values.update(mark="")
            with pytest.raises(details.ProductDetailError) as caught:
                await details.update_product_detail(db, pid, values, saved["revision"], "test")
            assert caught.value.status == 422
            assert str(caught.value) == "REQUIRED_FIELDS_CLEARED:mark"
        with connection.cursor() as cur:
            cur.execute("SELECT mark FROM public.products WHERE id=%s", (pid,))
            assert cur.fetchone()[0] == "MODEL"
        async with AsyncSession(engine) as db:
            values = edit_values(saved)
            values.update(mark="", blank_confirmations=["mark"])
            await details.update_product_detail(db, pid, values, saved["revision"], "test")
        with connection.cursor() as cur:
            cur.execute("SELECT field_code FROM public.product_blank_confirmations WHERE product_id=%s", (pid,))
            assert cur.fetchall() == [("mark",)]
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# ADR-1028 便4: 詳細の荷姿（packagings）
# ---------------------------------------------------------------------------

OFFICIAL = "https://example.com/official"


def _row(unit, **kw):
    base = {"unit_code": unit, "contained_count": None, "count_source": None, "count_source_urls": [],
            "weight_kg": None, "weight_source": None, "weight_source_urls": [], "note": None}
    base.update(kw)
    return base


def _by_unit(rows):
    # 単位の表示順は試験の DB と本番で逆なので、並びでなく unit_code をキーにして比べる
    return {r["unit_code"]: r for r in rows}


def _detail_pid(connection):
    with connection.cursor() as cur:
        cur.execute("SELECT id FROM public.products WHERE product_code='DETAIL'")
        return int(cur.fetchone()[0])


async def _put_packagings(engine, pid, packagings, actor_user_id=7):
    async with AsyncSession(engine) as db:
        snapshot = await details.get_product_detail(db, pid)
        values = edit_values(snapshot)
        if packagings is not None:
            values["packagings"] = packagings
        return await details.update_product_detail(
            db, pid, values, snapshot["revision"], "ci", actor_user_id=actor_user_id)


def _db_rows(connection, pid):
    with connection.cursor() as cur:
        cur.execute(
            "SELECT u.code, cu.code, pk.contained_count, pk.count_source, pk.count_source_urls, pk.weight_kg, "
            "pk.weight_source, pk.weight_source_urls, pk.note, pk.updated_by, pk.updated_at "
            "FROM public.product_packagings pk JOIN public.quantity_units u ON u.id=pk.unit_id "
            "LEFT JOIN public.quantity_units cu ON cu.id=pk.contained_unit_id WHERE pk.product_id=%s ORDER BY u.code",
            (pid,))
        return cur.fetchall()


async def test_detail_exposes_packagings_units_and_sources(edit_pg):
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        pid = _detail_pid(connection)
        async with AsyncSession(engine) as db:
            detail = await details.get_product_detail(db, pid)
        assert detail["product"]["packagings"] == []
        assert [(u["code"], u["contained_code"]) for u in detail["packaging_units"]] == [
            ("CASE", "BOX"), ("BOX", "PACK"), ("PACK", "CARD")]
        assert {"name", "name_en", "contained_name", "contained_name_en"} <= set(detail["packaging_units"][0])
        assert detail["packaging_sources"] == ["official", "official_store", "retailer", "measured", "legacy"]
        assert "packaging_units" not in detail["lookups"]
    finally:
        await engine.dispose()


async def test_packagings_insert_update_same_value_and_delete(edit_pg):
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        pid = _detail_pid(connection)
        rows = [
            _row("CASE", contained_count=12, count_source="official", count_source_urls=[OFFICIAL],
                 weight_kg="1.5", weight_source="measured", note=" memo "),
            _row("BOX", contained_count=10, count_source="retailer",
                 count_source_urls=["https://a.example/1", "https://b.example/2"]),
        ]
        saved = await _put_packagings(engine, pid, rows)
        got = _by_unit(saved["product"]["packagings"])
        assert got["CASE"]["contained_unit_code"] == "BOX" and got["CASE"]["contained_count"] == 12
        assert got["CASE"]["note"] == "memo" and got["CASE"]["weight_kg"] == 1.5
        assert got["BOX"]["contained_unit_code"] == "PACK"
        db_rows = {r[0]: r for r in _db_rows(connection, pid)}
        assert db_rows["CASE"][9] == "user:7" and db_rows["BOX"][9] == "user:7"
        # 同じ値: 書かない。updated_at も変わらない
        again = await _put_packagings(engine, pid, rows)
        assert {r[0]: r[10] for r in _db_rows(connection, pid)} == {k: v[10] for k, v in db_rows.items()}
        assert _by_unit(again["product"]["packagings"]) == _by_unit(saved["product"]["packagings"])
        # 変更: UPDATE
        rows[0]["contained_count"] = 24
        rows[0]["count_source_urls"] = [OFFICIAL, "https://example.com/2"]
        changed = await _put_packagings(engine, pid, rows)
        assert _by_unit(changed["product"]["packagings"])["CASE"]["contained_count"] == 24
        assert changed["revision"] != saved["revision"]
        # 数・重さ・メモがすべて空 -> 行が消える。元から無い単位(PACK)の空行は何もしない
        cleared = await _put_packagings(engine, pid, [_row("CASE"), _row("PACK")])
        assert [r[0] for r in _db_rows(connection, pid)] == ["BOX"]
        assert [r["unit_code"] for r in cleared["product"]["packagings"]] == ["BOX"]
    finally:
        await engine.dispose()


async def test_packagings_not_sent_leaves_rows_alone(edit_pg):
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        pid = _detail_pid(connection)
        await _put_packagings(engine, pid, [_row("CASE", weight_kg="2", weight_source="measured")])
        before = _db_rows(connection, pid)
        await _put_packagings(engine, pid, None)
        assert _db_rows(connection, pid) == before
    finally:
        await engine.dispose()


@pytest.mark.parametrize("rows,code", [
    ([_row("CARD", contained_count=1, count_source="measured")], "PACKAGING_UNKNOWN_UNIT"),
    ([_row("CASE", weight_kg="1", weight_source="measured"), _row("CASE")], "PACKAGING_DUPLICATE_UNIT"),
    ([_row("CASE", contained_count=3)], "PACKAGING_SOURCE_MISMATCH"),
    ([_row("CASE", count_source="measured")], "PACKAGING_SOURCE_MISMATCH"),
    ([_row("CASE", count_source_urls=[OFFICIAL])], "PACKAGING_SOURCE_MISMATCH"),
    ([_row("CASE", contained_count=3, count_source="official")], "PACKAGING_URLS_REQUIRED"),
    ([_row("CASE", contained_count=3, count_source="retailer", count_source_urls=[OFFICIAL])],
     "PACKAGING_URLS_REQUIRED"),
    ([_row("CASE", contained_count=3, count_source="official", count_source_urls=[OFFICIAL, OFFICIAL])],
     "PACKAGING_DUPLICATE_URL"),
    ([_row("CASE", contained_count=3, count_source="official", count_source_urls=["ftp://x"])],
     "PACKAGING_INVALID_URL"),
    ([_row("CASE", contained_count=3, count_source="official", count_source_urls=["https://a b"])],
     "PACKAGING_INVALID_URL"),
    ([_row("CASE", contained_count=3, count_source="official", count_source_urls=["https://" + "a" * 2050])],
     "PACKAGING_INVALID_URL"),
    ([_row("CASE", contained_count=3, count_source="legacy")], "PACKAGING_LEGACY_NOT_ALLOWED"),
    ([_row("CASE", note="memo only")], "PACKAGING_NOTE_WITHOUT_VALUE"),
])
async def test_packagings_rejected_with_code_and_nothing_written(edit_pg, rows, code):
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        pid = _detail_pid(connection)
        before = observed(connection)
        with pytest.raises(details.ProductDetailError) as caught:
            await _put_packagings(engine, pid, rows)
        assert caught.value.status == 422 and str(caught.value) == code
        assert observed(connection) == before
        assert _db_rows(connection, pid) == []
    finally:
        await engine.dispose()


async def test_packagings_legacy_kept_only_when_value_unchanged(edit_pg):
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        pid = _detail_pid(connection)
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO public.product_packagings (product_id, unit_id, weight_kg, weight_source) "
                "SELECT %s, id, 2.5, 'legacy' FROM public.quantity_units WHERE code='CASE'", (pid,))
        # 値が同じなら legacy のまま保存できる（数を足しても重さの legacy は保たれる）
        kept = await _put_packagings(engine, pid, [
            _row("CASE", weight_kg="2.500", weight_source="legacy",
                 contained_count=6, count_source="measured")])
        assert _by_unit(kept["product"]["packagings"])["CASE"]["weight_source"] == "legacy"
        # 値を変えて legacy のまま -> 422
        with pytest.raises(details.ProductDetailError) as caught:
            await _put_packagings(engine, pid, [
                _row("CASE", weight_kg="3", weight_source="legacy", contained_count=6, count_source="measured")])
        assert str(caught.value) == "PACKAGING_LEGACY_NOT_ALLOWED"
    finally:
        await engine.dispose()


async def test_packagings_on_tenant_product_rejected(edit_pg):
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO public.products (product_code,name,category_class,is_active,required_output_value,tenant_id) "
                "VALUES ('TENANTP','T','c',true,'x',1) RETURNING id")
            pid = cur.fetchone()[0]
        with pytest.raises(details.ProductDetailError) as caught:
            await _put_packagings(engine, pid, [_row("CASE", weight_kg="1", weight_source="measured")])
        assert caught.value.status == 422 and str(caught.value) == "PACKAGING_SHARED_ONLY"
    finally:
        await engine.dispose()


async def test_packaging_only_change_invalidates_open_draft(edit_pg):
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        pid = _detail_pid(connection)
        async with AsyncSession(engine) as db:
            stale = await details.get_product_detail(db, pid)
        await _put_packagings(engine, pid, [_row("BOX", weight_kg="1", weight_source="measured")])
        async with AsyncSession(engine) as db:
            with pytest.raises(details.ProductDetailError) as caught:
                await details.update_product_detail(db, pid, edit_values(stale), stale["revision"], "ci")
        assert caught.value.status == 409
    finally:
        await engine.dispose()


@pytest.mark.parametrize("stage", ["packaging_insert", "audit"])
async def test_failed_packaging_save_rolls_back_product_fields_too(edit_pg, stage):
    connection, url = edit_pg
    pid = _detail_pid(connection)

    class FailingSession(AsyncSession):
        async def execute(self, statement, params=None, **kwargs):
            query = str(statement)
            if stage == "packaging_insert" and "INSERT INTO public.product_packagings" in query:
                raise RuntimeError("injected packaging failure")
            if stage == "audit" and "INSERT INTO" in query and "audit_log" in query:
                raise RuntimeError("injected audit failure")
            return await super().execute(statement, params, **kwargs)

    before = observed(connection)
    engine = create_async_engine(url)
    try:
        async with FailingSession(engine) as db:
            snapshot = await details.get_product_detail(db, pid)
            values = edit_values(snapshot)
            values.update(japanese_title="Must roll back",
                          packagings=[_row("CASE", weight_kg="1", weight_source="measured")])
            with pytest.raises(RuntimeError):
                await details.update_product_detail(db, pid, values, snapshot["revision"], "ci", actor_user_id=1)
        assert observed(connection) == before
        assert _db_rows(connection, pid) == []
    finally:
        await engine.dispose()


async def test_audit_log_contains_packagings(edit_pg):
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        pid = _detail_pid(connection)
        await _put_packagings(engine, pid, [_row("PACK", contained_count=5, count_source="measured")])
        audit = observed(connection)["audit_log"][0]
        assert json.loads(audit["old_values"])["packagings"] == []
        new = json.loads(audit["new_values"])["packagings"]
        assert new[0]["unit_code"] == "PACK" and new[0]["contained_unit_code"] == "CARD"
        assert new[0]["contained_count"] == 5 and new[0]["count_source"] == "measured"
    finally:
        await engine.dispose()


async def test_sources_match_db_check_and_units_match_legacy_fields(edit_pg):
    from app.services import product_packagings as pk

    connection, _ = edit_pg
    with connection.cursor() as cur:
        cur.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname IN ('product_packagings_count_source_check','product_packagings_weight_source_check')")
        defs = [r[0] for r in cur.fetchall()]
    assert len(defs) == 2
    for definition in defs:
        for code in pk.ALL_SOURCES:
            assert f"'{code}'" in definition
    editable = dict(pk.EDITABLE_UNITS)
    for unit, kind, contained in pk.LEGACY_FIELDS.values():
        if kind == "count":
            assert editable[unit] == contained


def test_packaging_in_rejects_out_of_range_values():
    from pydantic import ValidationError

    ok = routes.PackagingIn(unit_code="CASE", contained_count=1000000, weight_kg="99999.999")
    assert ok.contained_count == 1000000
    for bad in ({"contained_count": 0}, {"contained_count": 1000001}, {"weight_kg": "0"},
                {"weight_kg": "100000"}, {"weight_kg": "1.2345"}, {"note": "x" * 1001}, {"bogus": 1}):
        with pytest.raises(ValidationError):
            routes.PackagingIn(unit_code="CASE", **bad)
