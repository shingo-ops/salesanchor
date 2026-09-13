"""DETAIL-01 read/write contracts in disposable PostgreSQL only."""
import asyncio
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
from tests import test_tcg_product_list_pg as fixtures
from tests import test_tcg_work_matching_integration as durable

product_db = fixtures.product_db
pytestmark = fixtures.pytestmark


@pytest_asyncio.fixture
async def detail_db(product_db, monkeypatch):
    db, schema = product_db
    monkeypatch.setattr(details, "TCG_SCHEMA", schema)
    await db.execute(text(
        f"INSERT INTO {schema}.tcg_products "
        "(code,japanese_title,english_title,mark,category_class,is_active,required_output_value) "
        "VALUES ('DETAIL','Japanese','English detail','MODEL-DETAIL','Original',false,'Keep this')"
    ))
    await db.execute(text(
        f"INSERT INTO {schema}.product_search_keywords(product_id,keyword,position) "
        f"SELECT id,'Alpha, Beta',1 FROM {schema}.tcg_products WHERE code='DETAIL'"
    ))
    await db.execute(text(
        f"INSERT INTO {schema}.product_exclude_keywords(product_id,keyword,position) "
        f"SELECT id,'Exclude one',1 FROM {schema}.tcg_products WHERE code='DETAIL'"
    ))
    return db, schema


async def test_detail_contains_stored_values_words_and_revision(detail_db):
    db, schema = detail_db
    before = await details.get_product_detail(db, "DETAIL")
    product = before["product"]
    assert product["japanese_title"] == "Japanese"
    assert product["english_title"] == "English detail"
    assert product["is_active"] is False
    assert product["required_output_value"] == "Keep this"
    assert product["search_keywords"] == ["Alpha, Beta"]
    assert product["exclude_keywords"] == ["Exclude one"]
    assert len(before["revision"]) == 64
    assert before["revision"] == (await details.get_product_detail(db, "DETAIL"))["revision"]
    assert set(before["lookups"]) == {"division_id", "work_id", "manufacturer_id", "product_category_id"}
    await db.execute(text(
        f"INSERT INTO {schema}.product_exclude_keywords(product_id,keyword,position) "
        f"SELECT id,'Exclude two',2 FROM {schema}.tcg_products WHERE code='DETAIL'"
    ))
    assert before["revision"] != (await details.get_product_detail(db, "DETAIL"))["revision"]


@pytest.mark.parametrize("query", ["english DETAIL", "MODEL-DETAIL"])
async def test_list_finds_english_and_mark_with_both_counts(detail_db, query):
    db, _ = detail_db
    result = await routes.list_products(query=query, limit=50, offset=0, work_id=None, db=db, _user={})
    assert result.total == 1
    assert result.items[0].keyword_count == 1
    assert result.items[0].exclude_keyword_count == 1
    assert result.items[0].english_title == "English detail"


@pytest.mark.parametrize("is_admin,code,status", [(True, "DETAIL", 200), (True, "missing", 404), (False, "DETAIL", 403)])
async def test_detail_route_uses_actual_admin_dependency(detail_db, is_admin, code, status):
    db, _ = detail_db
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    app.dependency_overrides[routes.get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(is_super_admin=is_admin)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/tcg/products/detail/" + code)
    assert response.status_code == status


pg = durable.pg


@pytest.fixture
def edit_pg(pg, monkeypatch):
    connection, _, url = pg
    for module in (details, master, routes):
        monkeypatch.setattr(module, "TCG_SCHEMA", durable.SCHEMA)
    with connection.cursor() as cur:
        for code in ("DETAIL", "SENTINEL"):
            cur.execute(f"INSERT INTO {durable.SCHEMA}.tcg_products "
                        "(code,japanese_title,category_class,is_active,required_output_value) "
                        "VALUES (%s,'Original','Keep category',true,'Keep output') RETURNING id", (code,))
            pid = cur.fetchone()[0]
            for table in details.WORD_TABLES.values():
                cur.execute(f"INSERT INTO {durable.SCHEMA}.{table}(product_id,keyword,position) "
                            "VALUES (%s,'Alpha, Beta',1)", (pid,))
    return connection, url


def observed(connection):
    with connection.cursor() as cur:
        result = {}
        for table in ("tcg_products", *details.WORD_TABLES.values(), "audit_log"):
            cur.execute(f"SELECT row_to_json(t) FROM {durable.SCHEMA}.{table} t ORDER BY id")
            result[table] = [r[0] for r in cur.fetchall()]
        return result


def edit_values(snapshot):
    p = snapshot["product"]
    return {field: (p.get(field) or "") if field in ("english_title", "mark") else p.get(field)
            for field in ("japanese_title", "english_title", "mark", "release_date", *details.LOOKUPS,
                          *details.WORD_TABLES)}


async def test_edit_commits_details_words_audit_and_preserves_identity(edit_pg):
    connection, url = edit_pg
    before = observed(connection)
    engine = create_async_engine(url)
    try:
        async with AsyncSession(engine) as db:
            snapshot = await details.get_product_detail(db, "DETAIL")
            values = edit_values(snapshot)
            values.update(japanese_title="Edited", english_title="English edited", mark="MODEL",
                          release_date="2026-09-14", search_keywords=["A, B", "C"], exclude_keywords=[])
            result = await details.update_product_detail(db, "DETAIL", values, snapshot["revision"], "ci-reviewer")
        after = observed(connection)
        product = result["product"]
        assert product["id"] == snapshot["product"]["id"]
        assert product["code"] == "DETAIL" and product["required_output_value"] == "Keep output"
        assert product["category_class"] == "Keep category" and product["is_active"] is True
        assert product["release_date"] == "2026-09-14" and product["mark"] == "MODEL"
        assert product["english_title"] == "English edited"
        assert product["search_keywords"] == ["A, B", "C"] and product["exclude_keywords"] == []
        assert result["revision"] != snapshot["revision"]
        sentinel = next(p for p in before["tcg_products"] if p["code"] == "SENTINEL")
        assert sentinel in after["tcg_products"]
        for table in details.WORD_TABLES.values():
            assert [r for r in before[table] if r["product_id"] == sentinel["id"]] == [
                r for r in after[table] if r["product_id"] == sentinel["id"]]
        assert len(after["audit_log"]) == 1
        audit = after["audit_log"][0]
        assert audit["changed_by"] == "ci-reviewer" and audit["record_id"] == product["id"]
        assert json.loads(audit["old_values"])["product"]["japanese_title"] == "Original"
        assert json.loads(audit["new_values"])["product"]["japanese_title"] == "Edited"
    finally:
        await engine.dispose()


async def test_unchanged_words_keep_row_ids_and_stale_edit_is_rejected(edit_pg):
    connection, url = edit_pg
    before = observed(connection)
    engine = create_async_engine(url)
    try:
        async with AsyncSession(engine) as db:
            snapshot = await details.get_product_detail(db, "DETAIL")
            values = edit_values(snapshot)
            values["english_title"] = "Change only title"
            await details.update_product_detail(db, "DETAIL", values, snapshot["revision"], "test")
            after = observed(connection)
            for table in details.WORD_TABLES.values():
                assert after[table] == before[table]
            with pytest.raises(details.ProductDetailError) as caught:
                await details.update_product_detail(db, "DETAIL", values, snapshot["revision"], "test")
            assert caught.value.status == 409
            assert observed(connection) == after
    finally:
        await engine.dispose()


@pytest.mark.parametrize("stage", ["words", "audit", "commit", "cancel"])
async def test_failed_edit_rolls_back_product_words_and_audit(edit_pg, stage):
    connection, url = edit_pg
    before = observed(connection)
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
            snapshot = await details.get_product_detail(db, "DETAIL")
            values = edit_values(snapshot)
            values.update(japanese_title="Must roll back", search_keywords=["Replacement"], exclude_keywords=[])
            with pytest.raises(asyncio.CancelledError if stage == "cancel" else RuntimeError):
                await details.update_product_detail(db, "DETAIL", values, snapshot["revision"], "test")
        assert observed(connection) == before
    finally:
        await engine.dispose()


async def test_simultaneous_edits_have_one_winner(edit_pg):
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        async with AsyncSession(engine) as reader:
            snapshot = await details.get_product_detail(reader, "DETAIL")
        async def write(title):
            async with AsyncSession(engine) as db:
                values = edit_values(snapshot)
                values["japanese_title"] = title
                try:
                    return await details.update_product_detail(db, "DETAIL", values, snapshot["revision"], "test")
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
            snapshot = await details.get_product_detail(reader, "DETAIL")
        async with AsyncSession(engine) as writer:
            assert await master.add_search_keyword(writer, product_code="DETAIL", new_keyword="Added") == {"ok": True}
        before = observed(connection)
        async with AsyncSession(engine) as writer:
            with pytest.raises(details.ProductDetailError) as caught:
                await details.update_product_detail(writer, "DETAIL", edit_values(snapshot), snapshot["revision"], "test")
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
    snapshot = await details.get_product_detail(db, "DETAIL")
    payload = dict(edit_values(snapshot), revision=snapshot["revision"])
    payload[field] = value
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[routes.get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(is_super_admin=True, email="test", id="test")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put("/tcg/products/detail/DETAIL", json=payload)
    assert response.status_code == 422
    assert (await details.get_product_detail(db, "DETAIL"))["revision"] == snapshot["revision"]


@pytest.mark.parametrize("admin,code,status", [(True, "DETAIL", 200), (False, "DETAIL", 403), (True, "missing", 404)])
async def test_update_route_and_real_permission_dependency(edit_pg, admin, code, status):
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        async with AsyncSession(engine) as db:
            snapshot = await details.get_product_detail(db, "DETAIL")
            payload = dict(edit_values(snapshot), revision=snapshot["revision"], english_title="Via HTTP")
            app = FastAPI()
            app.include_router(routes.router)
            app.dependency_overrides[routes.get_db] = lambda: db
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
                is_super_admin=admin, email="http-test", id="test")
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.put("/tcg/products/detail/" + code, json=payload)
            assert response.status_code == status
            assert len(observed(connection)["audit_log"]) == (1 if status == 200 else 0)
    finally:
        await engine.dispose()


async def test_classification_change_derives_work_name_and_rejects_unknown(edit_pg):
    connection, url = edit_pg
    engine = create_async_engine(url)
    try:
        async with AsyncSession(engine) as db:
            snapshot = await details.get_product_detail(db, "DETAIL")
            values = edit_values(snapshot)
            selected = snapshot["lookups"]["work_id"][0]
            values["work_id"] = selected["id"]
            updated = await details.update_product_detail(db, "DETAIL", values, snapshot["revision"], "test")
            assert updated["product"]["category_class"] == selected["name"]
            before = observed(connection)
            values["work_id"] = "00000000-0000-0000-0000-000000000000"
            with pytest.raises(details.ProductDetailError) as caught:
                await details.update_product_detail(db, "DETAIL", values, updated["revision"], "test")
            assert caught.value.status == 422
            assert observed(connection) == before
    finally:
        await engine.dispose()


async def test_lost_commit_response_keeps_one_atomic_change_and_stale_retry_fails(edit_pg):
    connection, url = edit_pg
    class LostResponse(AsyncSession):
        async def commit(self):
            await super().commit()
            raise RuntimeError("commit response lost")
    engine = create_async_engine(url)
    try:
        async with LostResponse(engine) as db:
            snapshot = await details.get_product_detail(db, "DETAIL")
            values = edit_values(snapshot)
            values.update(japanese_title="Committed", search_keywords=[], exclude_keywords=["New exclusion"])
            with pytest.raises(RuntimeError, match="response lost"):
                await details.update_product_detail(db, "DETAIL", values, snapshot["revision"], "test")
        after = observed(connection)
        assert len(after["audit_log"]) == 1
        async with AsyncSession(engine) as reader:
            current = await details.get_product_detail(reader, "DETAIL")
            assert current["product"]["japanese_title"] == "Committed"
            assert current["product"]["search_keywords"] == []
            assert current["product"]["exclude_keywords"] == ["New exclusion"]
            with pytest.raises(details.ProductDetailError) as caught:
                await details.update_product_detail(reader, "DETAIL", values, snapshot["revision"], "test")
            assert caught.value.status == 409
        assert observed(connection) == after
    finally:
        await engine.dispose()
