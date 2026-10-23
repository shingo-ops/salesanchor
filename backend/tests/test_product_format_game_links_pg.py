"""ADR-1020 便2a: 細分類とゲームの照合・選択肢・印の返却・使えるゲームの置き換え（実 PostgreSQL・CI のみ）。"""
from pathlib import Path

import psycopg2.errors
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.routers import super_admin_product_formats as formats_router
from app.schemas.product_format import ProductFormatCreate, ProductFormatGamesUpdate, ProductFormatUpdate
from app.services import tcg_product_detail_svc as details
from app.services import tcg_product_master_svc as master
from tests import test_tcg_product_list_pg as fixtures
from tests.test_tcg_product_detail_pg import _pid, edit_pg, edit_values  # noqa: F401
from tests.test_tcg_work_matching_integration import pg  # noqa: F401

pytestmark = fixtures.pytestmark

_MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


@pytest.fixture
def fmt_pg(edit_pg):  # noqa: F811
    """作品2つ・細分類2つ（片方だけ作品Aに紐づけ、alias あり）。後片付けで作った行を消す。"""
    connection, url = edit_pg
    with connection.cursor() as cur:
        for name in ("20260922_030000_product_format_game_links.sql",
                     "20260923_010000_product_formats_add_type_master_id.sql",
                     "20261022_100000_products_format_in_work_fk.sql",  # ADR-1038 便2: 複合 FK
                     "20261022_110000_product_formats_drop_type_master_id.sql"):  # ADR-1038 便3b: 旧列を落とす
            cur.execute((_MIGRATIONS / name).read_text())
        cur.execute("SELECT id FROM public.type_master WHERE is_active ORDER BY id LIMIT 2")
        work_a, work_b = [r[0] for r in cur.fetchall()]
        cur.execute("INSERT INTO public.product_formats(code,name,display_order) "
                    "VALUES ('T2A_LINKED','T2A linked',1) RETURNING id")
        linked = cur.fetchone()[0]
        cur.execute("INSERT INTO public.product_formats(code,name,display_order) "
                    "VALUES ('T2A_UNLINKED','T2A unlinked',2) RETURNING id")
        unlinked = cur.fetchone()[0]
        cur.execute("INSERT INTO public.product_format_game_links(format_id,type_master_id,alias) "
                    "VALUES (%s,%s,'keep-me')", (linked, work_a))
    ctx = {"connection": connection, "url": url, "work_a": work_a, "work_b": work_b,
           "linked": linked, "unlinked": unlinked}
    yield ctx
    with connection.cursor() as cur:
        cur.execute("UPDATE public.products SET product_format_id=NULL WHERE product_format_id = ANY(%s)",
                    ([linked, unlinked],))
        cur.execute("DELETE FROM public.product_formats WHERE id = ANY(%s)", ([linked, unlinked],))


def _set_product(ctx, code, work_id=None, format_id=None):
    with ctx["connection"].cursor() as cur:
        cur.execute("UPDATE public.products SET work_id=%s, product_format_id=%s WHERE product_code=%s",
                    (work_id, format_id, code))


def _links(ctx, format_id):
    with ctx["connection"].cursor() as cur:
        cur.execute("SELECT type_master_id, alias FROM public.product_format_game_links "
                    "WHERE format_id=%s ORDER BY type_master_id", (format_id,))
        return cur.fetchall()


async def test_validate_accepts_linked_and_rejects_unlinked(fmt_pg):
    engine = create_async_engine(fmt_pg["url"])
    try:
        async with AsyncSession(engine) as db:
            await master._validate_product_format(db, fmt_pg["linked"], work_id=fmt_pg["work_a"])
            with pytest.raises(ValueError, match="PRODUCT_FORMAT_GAME_MISMATCH"):
                await master._validate_product_format(db, fmt_pg["unlinked"], work_id=fmt_pg["work_a"])
            with pytest.raises(ValueError, match="PRODUCT_FORMAT_GAME_MISMATCH"):
                await master._validate_product_format(db, fmt_pg["linked"], work_id=fmt_pg["work_b"])
            await master._validate_product_format(db, fmt_pg["unlinked"], work_id=None)
    finally:
        await engine.dispose()


async def test_format_options_include_game_ids_and_selected_inactive(fmt_pg):
    engine = create_async_engine(fmt_pg["url"])
    try:
        async with AsyncSession(engine) as db:
            options = {o["id"]: o for o in await master.fetch_product_format_options(db)}
            assert options[str(fmt_pg["linked"])]["game_ids"] == [str(fmt_pg["work_a"])]
            assert options[str(fmt_pg["unlinked"])]["game_ids"] == []
            with fmt_pg["connection"].cursor() as cur:
                cur.execute("UPDATE public.product_formats SET is_active=FALSE WHERE id=%s", (fmt_pg["unlinked"],))
            hidden = {o["id"] for o in await master.fetch_product_format_options(db)}
            assert str(fmt_pg["unlinked"]) not in hidden
            shown = {o["id"]: o for o in await master.fetch_product_format_options(db, selected=fmt_pg["unlinked"])}
            assert shown[str(fmt_pg["unlinked"])]["is_active"] is False
    finally:
        await engine.dispose()


async def test_detail_get_returns_confirmations_and_format_lookup(fmt_pg):
    engine = create_async_engine(fmt_pg["url"])
    try:
        async with AsyncSession(engine) as db:
            pid = await _pid(db, "DETAIL")
            with fmt_pg["connection"].cursor() as cur:
                cur.execute("INSERT INTO public.product_blank_confirmations(product_id,field_code,confirmed_by) "
                            "VALUES (%s,'mark','test')", (pid,))
            detail = await details.get_product_detail(db, pid)
            assert detail["product"]["blank_confirmations"] == ["mark"]
            assert "product_format_id" in detail["lookups"]
    finally:
        await engine.dispose()


async def test_revision_changes_when_confirmation_changes(fmt_pg):
    engine = create_async_engine(fmt_pg["url"])
    try:
        async with AsyncSession(engine) as db:
            pid = await _pid(db, "DETAIL")
            before = await details.get_product_detail(db, pid)
            with fmt_pg["connection"].cursor() as cur:
                cur.execute("INSERT INTO public.product_blank_confirmations(product_id,field_code,confirmed_by) "
                            "VALUES (%s,'mark','test')", (pid,))
            after = await details.get_product_detail(db, pid)
            assert before["revision"] != after["revision"]
    finally:
        await engine.dispose()


async def test_detail_update_rejects_unlinked_format_change(fmt_pg):
    _set_product(fmt_pg, "DETAIL", fmt_pg["work_a"], fmt_pg["linked"])
    engine = create_async_engine(fmt_pg["url"])
    try:
        async with AsyncSession(engine) as db:
            pid = await _pid(db, "DETAIL")
            snapshot = await details.get_product_detail(db, pid)
            values = edit_values(snapshot)
            values.update(japanese_title="Should not save", product_format_id=fmt_pg["unlinked"])
            with pytest.raises(details.ProductDetailError) as caught:
                await details.update_product_detail(db, pid, values, snapshot["revision"], "test")
            assert caught.value.status == 422
            assert str(caught.value) =="PRODUCT_DETAIL_FORMAT_GAME_MISMATCH"
        with fmt_pg["connection"].cursor() as cur:
            cur.execute("SELECT product_format_id, name FROM public.products WHERE product_code='DETAIL'")
            assert cur.fetchone() == (fmt_pg["linked"], "Original")
    finally:
        await engine.dispose()


def test_db_rejects_pair_not_in_links(fmt_pg):
    """ADR-1038 便2: links に無い組を products に直接書くと DB が拒否する（旧 keeps_unchanged_old_pair の置き換え）。"""
    _set_product(fmt_pg, "DETAIL", fmt_pg["work_a"], fmt_pg["linked"])
    with pytest.raises(psycopg2.errors.ForeignKeyViolation):
        _set_product(fmt_pg, "DETAIL", fmt_pg["work_a"], fmt_pg["unlinked"])
    with pytest.raises(psycopg2.errors.ForeignKeyViolation):
        _set_product(fmt_pg, "DETAIL", fmt_pg["work_b"], fmt_pg["linked"])
    assert _row(fmt_pg)[:2] == (fmt_pg["work_a"], fmt_pg["linked"])


def test_db_allows_pair_with_null_side(fmt_pg):
    """MATCH SIMPLE: 片方が NULL なら照合しない。"""
    _set_product(fmt_pg, "DETAIL", None, fmt_pg["unlinked"])
    assert _row(fmt_pg)[:2] == (None, fmt_pg["unlinked"])
    _set_product(fmt_pg, "DETAIL", fmt_pg["work_b"], None)
    assert _row(fmt_pg)[:2] == (fmt_pg["work_b"], None)
    _set_product(fmt_pg, "DETAIL", None, None)
    assert _row(fmt_pg)[:2] == (None, None)


def test_db_rejects_removing_link_in_use(fmt_pg):
    """使われている組の links 行を直接消すと DB が拒否する。使われていなければ消せる。"""
    _set_product(fmt_pg, "DETAIL", fmt_pg["work_a"], fmt_pg["linked"])
    sql = "DELETE FROM public.product_format_game_links WHERE format_id=%s AND type_master_id=%s"
    with fmt_pg["connection"].cursor() as cur:
        with pytest.raises(psycopg2.errors.ForeignKeyViolation):
            cur.execute(sql, (fmt_pg["linked"], fmt_pg["work_a"]))
    assert _links(fmt_pg, fmt_pg["linked"]) == [(fmt_pg["work_a"], "keep-me")]
    _set_product(fmt_pg, "DETAIL", None, None)
    with fmt_pg["connection"].cursor() as cur:
        cur.execute(sql, (fmt_pg["linked"], fmt_pg["work_a"]))
    assert _links(fmt_pg, fmt_pg["linked"]) == []


def test_physical_delete_of_format_in_use_is_rejected(fmt_pg):
    """ADR-1038 便2 試験(4): 使われている細分類の物理削除は FK が拒否する。

    links の CASCADE 削除が fk_products_format_in_work に止められる（CI の実測）。
    拒否後も products・formats・links は元のまま。ON DELETE は変えない。
    """
    _set_product(fmt_pg, "DETAIL", fmt_pg["work_a"], fmt_pg["linked"])
    with fmt_pg["connection"].cursor() as cur:
        with pytest.raises(psycopg2.errors.ForeignKeyViolation):
            cur.execute("DELETE FROM public.product_formats WHERE id=%s", (fmt_pg["linked"],))
        cur.execute("SELECT work_id, product_format_id FROM public.products WHERE product_code='DETAIL'")
        assert cur.fetchone() == (fmt_pg["work_a"], fmt_pg["linked"])
        cur.execute("SELECT count(*) FROM public.product_formats WHERE id=%s", (fmt_pg["linked"],))
        assert cur.fetchone()[0] == 1
    assert _links(fmt_pg, fmt_pg["linked"]) == [(fmt_pg["work_a"], "keep-me")]


async def test_replace_games_adds_and_removes_links(fmt_pg):
    engine = create_async_engine(fmt_pg["url"])
    try:
        async with AsyncSession(engine) as db:
            body = ProductFormatGamesUpdate(game_ids=[fmt_pg["work_a"], fmt_pg["work_b"]])
            res = await formats_router.replace_product_format_games(fmt_pg["linked"], body, db)
            assert res.game_ids == sorted([fmt_pg["work_a"], fmt_pg["work_b"]])
            assert [g for g, _ in _links(fmt_pg, fmt_pg["linked"])] == sorted([fmt_pg["work_a"], fmt_pg["work_b"]])
            body = ProductFormatGamesUpdate(game_ids=[fmt_pg["work_a"]])
            res = await formats_router.replace_product_format_games(fmt_pg["linked"], body, db)
            assert res.game_ids == [fmt_pg["work_a"]]
            assert _links(fmt_pg, fmt_pg["linked"]) == [(fmt_pg["work_a"], "keep-me")]
    finally:
        await engine.dispose()


async def test_replace_games_blocks_removal_in_use(fmt_pg):
    _set_product(fmt_pg, "DETAIL", fmt_pg["work_a"], fmt_pg["linked"])
    engine = create_async_engine(fmt_pg["url"])
    try:
        async with AsyncSession(engine) as db:
            body = ProductFormatGamesUpdate(game_ids=[fmt_pg["work_b"]])
            with pytest.raises(HTTPException) as caught:
                await formats_router.replace_product_format_games(fmt_pg["linked"], body, db)
            assert caught.value.status_code == 409
            assert caught.value.detail == "PRODUCT_FORMAT_GAME_IN_USE"
        assert _links(fmt_pg, fmt_pg["linked"]) == [(fmt_pg["work_a"], "keep-me")]
    finally:
        await engine.dispose()


def _add_link(ctx, format_id, work_id):
    with ctx["connection"].cursor() as cur:
        cur.execute("INSERT INTO public.product_format_game_links(format_id,type_master_id) VALUES (%s,%s)",
                    (format_id, work_id))


def _row(ctx):
    with ctx["connection"].cursor() as cur:
        cur.execute("SELECT work_id, product_format_id, name FROM public.products WHERE product_code='DETAIL'")
        return cur.fetchone()


async def test_detail_update_changes_work_and_format_together(fmt_pg):
    _set_product(fmt_pg, "DETAIL", fmt_pg["work_a"], fmt_pg["linked"])
    _add_link(fmt_pg, fmt_pg["unlinked"], fmt_pg["work_b"])  # 後片付けは fmt_pg が format 行ごと消す（links は FK で連動）
    engine = create_async_engine(fmt_pg["url"])
    try:
        async with AsyncSession(engine) as db:
            pid = await _pid(db, "DETAIL")
            snapshot = await details.get_product_detail(db, pid)
            values = edit_values(snapshot)
            values.update(work_id=fmt_pg["work_b"], product_format_id=fmt_pg["unlinked"])
            await details.update_product_detail(db, pid, values, snapshot["revision"], "test")
        assert _row(fmt_pg)[:2] == (fmt_pg["work_b"], fmt_pg["unlinked"])
    finally:
        await engine.dispose()


async def test_detail_update_rejects_work_change_without_format(fmt_pg):
    _set_product(fmt_pg, "DETAIL", fmt_pg["work_a"], fmt_pg["linked"])
    engine = create_async_engine(fmt_pg["url"])
    try:
        async with AsyncSession(engine) as db:
            pid = await _pid(db, "DETAIL")
            snapshot = await details.get_product_detail(db, pid)
            values = edit_values(snapshot)
            values.update(work_id=fmt_pg["work_b"], japanese_title="Should not save")
            assert "product_format_id" not in values
            with pytest.raises(details.ProductDetailError) as caught:
                await details.update_product_detail(db, pid, values, snapshot["revision"], "test")
            assert caught.value.status == 422
            assert str(caught.value) == "PRODUCT_DETAIL_FORMAT_GAME_MISMATCH"
        assert _row(fmt_pg) == (fmt_pg["work_a"], fmt_pg["linked"], "Original")
    finally:
        await engine.dispose()


async def test_detail_update_rejects_mismatch_before_write(fmt_pg):
    _set_product(fmt_pg, "DETAIL", fmt_pg["work_a"], fmt_pg["linked"])
    engine = create_async_engine(fmt_pg["url"])
    try:
        async with AsyncSession(engine) as db:
            pid = await _pid(db, "DETAIL")
            snapshot = await details.get_product_detail(db, pid)
            values = edit_values(snapshot)
            values.update(work_id=fmt_pg["work_b"], product_format_id=fmt_pg["linked"],
                          japanese_title="Should not save")
            with pytest.raises(details.ProductDetailError) as caught:
                await details.update_product_detail(db, pid, values, snapshot["revision"], "test")
            assert caught.value.status == 422
            assert str(caught.value) == "PRODUCT_DETAIL_FORMAT_GAME_MISMATCH"
        assert _row(fmt_pg) == (fmt_pg["work_a"], fmt_pg["linked"], "Original")
    finally:
        await engine.dispose()


# ADR-1038 便3a/3b: API は旧列 type_master_id を受け取っても無視し、返さない（列は便3b で落とした。送っても保存できる）
async def test_create_ignores_legacy_type_master_id_and_does_not_return_it(fmt_pg):
    body = ProductFormatCreate.model_validate(
        {"code": "T3A_CREATE", "name": "T3A create", "type_master_id": fmt_pg["work_b"]})
    engine = create_async_engine(fmt_pg["url"])
    created = None
    try:
        async with AsyncSession(engine) as db:
            res = await formats_router.create_product_format(body, db)
            created = res.id
        assert "type_master_id" not in res.model_dump()
    finally:
        await engine.dispose()
        if created is not None:
            with fmt_pg["connection"].cursor() as cur:
                cur.execute("DELETE FROM public.product_formats WHERE id=%s", (created,))


async def test_update_ignores_legacy_type_master_id_and_list_does_not_return_it(fmt_pg):
    body = ProductFormatUpdate.model_validate(
        {"name": "T3A renamed", "type_master_id": fmt_pg["work_b"]})
    engine = create_async_engine(fmt_pg["url"])
    try:
        async with AsyncSession(engine) as db:
            res = await formats_router.update_product_format(fmt_pg["linked"], body, db)
            assert res.name == "T3A renamed"
            assert "type_master_id" not in res.model_dump()
            listed = await formats_router.list_product_formats(is_active=None, page=1, per_page=500, db=db)
            assert all("type_master_id" not in r.model_dump() for r in listed)
    finally:
        await engine.dispose()
