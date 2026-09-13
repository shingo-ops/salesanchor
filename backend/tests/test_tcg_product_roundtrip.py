"""Roundtrip codecs, HTTP dispatch, identity and transaction contracts (R1–R7)."""

import asyncio
import copy
import csv
import hashlib
import io
from datetime import date
from itertools import product
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, UploadFile

from app.services import tcg_product_roundtrip_svc as svc


def snapshot():
    return {
        "product": {
            "id": "00000000-0000-4000-8000-000000000001",
            "code": "PM001",
            "japanese_title": "商品",
            "mark": None,
            "english_title": "",
            "release_date": None,
            "is_active": False,
            "required_output_value": "private",
        },
        "refs": dict.fromkeys(svc.LOOKUP_TABLES),
        "search_keywords": [{"id": "a", "product_id": "p", "keyword": ' word,"quote"\r\n', "position": 7}],
        "exclude_keywords": [{"id": "b", "product_id": "p", "keyword": "", "position": 19}],
    }


def file_for(snap, **changes):
    row = svc.values(snap)
    row.update(changes)
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(svc.COLUMNS)
    writer.writerow([svc.escape_cell(row[key]) for key in svc.COLUMNS])
    return out.getvalue().encode("utf-8-sig")


def test_codecs_keep_exact_words_and_spreadsheet_prefixes():
    tokens = ["", " ", "日本語", "a,b", 'a"b', "\r\n", "\t", "=1+1", "+2", "-3", "@x", "'", "＝1", "＋2", "－3", "＠x"]
    for a, b in product(tokens, repeat=2):
        value = a + b
        encoded = svc.escape_cell(value)
        assert svc.unescape_cell(encoded) == value
        if svc.needs_escape(value):
            assert encoded.startswith("'")
        assert svc.decode_words(svc.encode_words([a, b])) == [a, b]
    assert svc.decode_words("") == []
    assert svc.decode_words(svc.encode_words([""])) == [""]


def test_large_cell_limit_and_failure_restore():
    limit = csv.field_size_limit()
    assert svc.read_records(b"a" * svc.MAX_BYTES) == [["a" * svc.MAX_BYTES]]
    assert csv.field_size_limit() == limit
    for raw in (b'"unterminated', b"\xff"):
        with pytest.raises(svc.RoundtripError):
            svc.read_records(raw)
        assert csv.field_size_limit() == limit
    with pytest.raises(svc.RoundtripError) as error:
        svc.read_records(b"a" * (svc.MAX_BYTES + 1))
    assert error.value.status == 413


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["2028-02-29", ""])
async def test_date_binding_uses_python_date_while_preview_stays_iso(monkeypatch, value):
    snap = snapshot()
    snap["product"]["release_date"] = "2026-01-01"
    monkeypatch.setattr(svc, "snapshots", AsyncMock(return_value=[snap]))
    db = AsyncMock()
    db.execute.return_value.fetchall = lambda: []
    checked, plans = await svc.inspect_update(db, file_for(snap, release_date=value), "date.csv")
    assert checked["blocked"] == 0
    assert plans[0]["sets"]["release_date"] == (date(2028, 2, 29) if value else None)
    assert checked["rows"][0]["changes"] == [{"field": "release_date", "before": "2026-01-01", "after": value}]


@pytest.mark.parametrize(
    "part,field,value",
    [
        ("product", "is_active", True),
        ("product", "id", "other"),
        ("product", "required_output_value", "changed"),
        ("search_keywords", "position", 8),
        ("exclude_keywords", "keyword", "different"),
        ("search_keywords", "id", "new"),
    ],
)
def test_revision_covers_all_stored_identity(part, field, value):
    original = snapshot()
    changed = copy.deepcopy(original)
    target = changed[part] if part == "product" else changed[part][0]
    target[field] = value
    assert svc.revision(original) != svc.revision(changed)


@pytest.mark.asyncio
async def test_export_and_unchanged_preview_large_cells(monkeypatch):
    snap = snapshot()
    snap["product"]["english_title"] = "x" * 150000
    monkeypatch.setattr(svc, "snapshots", AsyncMock(return_value=[snap]))
    db = AsyncMock()
    db.execute.return_value.fetchall = lambda: []
    raw = await svc.export_csv(db)
    assert raw.startswith(b'\xef\xbb\xbf"product_code"') and raw.endswith(b"\r\n")
    checked, plans = await svc.inspect_update(db, raw, "export.csv")
    assert checked["unchanged"] == 1 and checked["blocked"] == 0
    assert plans[0]["sets"] == plans[0]["words"] == {}
    snap["product"]["english_title"] = "x" * svc.MAX_BYTES
    with pytest.raises(svc.RoundtripError) as error:
        await svc.export_csv(db)
    assert error.value.status == 413


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change,error",
    [
        ({"product_code": ""}, "ROUNDTRIP_UNKNOWN_CODE"),
        ({"revision": "old"}, "ROUNDTRIP_STALE"),
        ({"japanese_title": "  "}, "JAPANESE_TITLE_REQUIRED"),
        ({"release_date": "2026-02-30"}, "RELEASE_DATE_FORMAT"),
        ({"work_code": "absent"}, "UNKNOWN_WORK_CODE_absent"),
        ({"search_keywords": "   "}, "ROUNDTRIP_KEYWORDS_INVALID"),
    ],
)
async def test_invalid_updates_are_read_only(monkeypatch, change, error):
    snap = snapshot()
    monkeypatch.setattr(svc, "snapshots", AsyncMock(return_value=[snap]))
    db = AsyncMock()
    db.execute.return_value.fetchall = lambda: []
    checked = await svc.preview_update(db, file_for(snap, **change), "x.csv")
    assert error in checked["rows"][0]["blocking"]
    db.commit.assert_not_called()
    db.rollback.assert_not_called()
    assert all(str(call.args[0]).startswith("SELECT") for call in db.execute.call_args_list)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [RuntimeError("write"), asyncio.CancelledError("cancel")])
async def test_failure_rolls_back_and_preserves_original(failure):
    db = AsyncMock()
    db.execute.side_effect = failure
    with pytest.raises(type(failure)) as caught:
        await svc.commit_update(db, b"raw", "x.csv", "user", hashlib.sha256(b"raw").hexdigest())
    assert caught.value is failure
    db.rollback.assert_awaited_once()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_http_export_and_update_dispatch(monkeypatch):
    from app.routers import tcg_product_import as router

    db = AsyncMock()
    actor = type("Actor", (), {"email": "test@example.invalid", "id": "id"})()
    monkeypatch.setattr(svc, "export_csv", AsyncMock(return_value=b"\xef\xbb\xbfdata\r\n"))
    response = await router.export_products("query", None, db, actor)
    assert response.body == b"\xef\xbb\xbfdata\r\n" and response.headers["cache-control"] == "no-store"
    assert "tcg-products-update.csv" in response.headers["content-disposition"]
    monkeypatch.setattr(svc, "commit_update", AsyncMock(return_value={"mode": "update"}))
    raw = file_for(snapshot())
    assert await router.commit_import_endpoint(UploadFile(io.BytesIO(raw), filename="x.csv"), "digest", db, actor) == {
        "mode": "update"
    }
    svc.commit_update.assert_awaited_once_with(db, raw, "x.csv", actor.email, "digest")
    for raw in (b'"broken', b"\xff"):
        with pytest.raises(HTTPException) as error:
            await router.preview_import(UploadFile(io.BytesIO(raw), filename="x.csv"), db, actor)
        assert error.value.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("admin", [None, False, True])
async def test_http_export_real_authorization(monkeypatch, admin):
    from app.models import User
    from tests.test_tcg_product_import import _client, _user_dependencies

    export = AsyncMock(return_value=b"csv")
    monkeypatch.setattr(svc, "export_csv", export)
    if admin is None:
        async with await _client() as client:
            response = await client.get("/api/v1/tcg/products/export")
        assert response.status_code in (401, 403)
    else:
        with _user_dependencies(User(id=1, email="test@example.invalid", is_super_admin=admin)):
            async with await _client() as client:
                response = await client.get("/api/v1/tcg/products/export")
        assert response.status_code == (200 if admin else 403)
    if admin:
        export.assert_awaited_once()
    else:
        export.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_header_still_dispatches_legacy_service(monkeypatch):
    from app.routers import tcg_product_import as router
    from tests.test_tcg_product_import import _CSV, _PREVIEW

    legacy = AsyncMock(return_value=_PREVIEW)
    monkeypatch.setattr(router, "preview", legacy)
    update = AsyncMock()
    monkeypatch.setattr(svc, "preview_update", update)
    result = await router.preview_import(UploadFile(io.BytesIO(_CSV), filename="old.csv"), None, None)
    assert result == _PREVIEW
    legacy.assert_awaited_once_with(None, _CSV, "old.csv")
    update.assert_not_awaited()
