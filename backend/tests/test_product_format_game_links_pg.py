"""ADR-1020 便2a: 細分類とゲームの照合・選択肢・印の返却・使えるゲームの置き換え（実 PostgreSQL・CI のみ）。"""
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.routers import super_admin_product_formats as formats_router
from app.schemas.product_format import ProductFormatGamesUpdate
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
                     "20260923_010000_product_formats_add_type_master_id.sql"):
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


async def test_detail_update_keeps_unchanged_old_pair(fmt_pg):
    _set_product(fmt_pg, "DETAIL", fmt_pg["work_a"], fmt_pg["unlinked"])
    engine = create_async_engine(fmt_pg["url"])
    try:
        async with AsyncSession(engine) as db:
            pid = await _pid(db, "DETAIL")
            snapshot = await details.get_product_detail(db, pid)
            values = edit_values(snapshot)
            values["japanese_title"] = "Renamed only"
            result = await details.update_product_detail(db, pid, values, snapshot["revision"], "test")
            assert result["product"]["japanese_title"] == "Renamed only"
        with fmt_pg["connection"].cursor() as cur:
            cur.execute("SELECT product_format_id, name FROM public.products WHERE product_code='DETAIL'")
            assert cur.fetchone() == (fmt_pg["unlinked"], "Renamed only")
    finally:
        await engine.dispose()


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
