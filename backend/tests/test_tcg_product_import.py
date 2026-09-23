"""IMPORT-01: 商品マスタ CSV 取り込み API テスト。"""
from __future__ import annotations

import os
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
pytestmark = pytest.mark.asyncio

_HEADER = (
    "mark,japanese_title,english_title,release_date,"
    "search_keywords,exclude_keywords,"
    "division_code,work_code,manufacturer_code,product_category_code\n"
)
_ROW = "FB09,DUAL EVOLUTION,Dual Evolution,2026-03-14,DE,,DIV01,IP003,MK002,PC_BOX\n"
_CSV = (_HEADER + _ROW).encode("utf-8")
_PREVIEW = {"filename": "sample.csv", "digest": "d" * 64, "file_errors": [], "total": 1, "ok": 1, "blocked": 0, "rows": [{"row_no": "1", "japanese_title": "DUAL EVOLUTION", "mark": "FB09", "blocking": [], "warnings": []}]}


async def _client():
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@patch("app.routers.tcg_product_import.commit_import", new_callable=AsyncMock)
async def test_preview_requires_auth(mock_commit):
    async with await _client() as client:
        res = await client.post("/api/v1/tcg/products/import/preview", files={"file": ("sample.csv", _CSV, "text/csv")})
    assert res.status_code in (401, 403)
    mock_commit.assert_not_awaited()


@patch("app.routers.tcg_product_import.commit_import", new_callable=AsyncMock)
async def test_commit_requires_auth(mock_commit):
    async with await _client() as client:
        res = await client.post("/api/v1/tcg/products/import/commit", files={"file": ("sample.csv", _CSV, "text/csv")}, data={"confirmed_digest": "d" * 64})
    assert res.status_code in (401, 403)
    mock_commit.assert_not_awaited()


async def test_list_requires_auth():
    async with await _client() as client:
        res = await client.get("/api/v1/tcg/products/list")
    assert res.status_code in (401, 403)


@patch("app.routers.tcg_product_import.preview", new_callable=AsyncMock)
async def test_preview_returns_rows(mock_preview):
    mock_preview.return_value = _PREVIEW
    from app.auth.dependencies import require_super_admin
    from app.database import get_db
    from app.main import app
    from app.models import User
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[require_super_admin] = lambda: User(id=1, email="qa@example.com", is_super_admin=True)
    app.dependency_overrides[get_db] = lambda: None
    try:
        async with await _client() as client:
            res = await client.post("/api/v1/tcg/products/import/preview", files={"file": ("sample.csv", _CSV, "text/csv")})
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["blocked"] == 0
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@patch("app.routers.tcg_product_import.commit_import", new_callable=AsyncMock)
@patch("app.routers.tcg_product_import.preview", new_callable=AsyncMock)
async def test_commit_rejects_digest_mismatch(mock_preview, mock_commit):
    mock_preview.return_value = _PREVIEW
    from app.auth.dependencies import require_super_admin
    from app.database import get_db
    from app.main import app
    from app.models import User
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[require_super_admin] = lambda: User(id=1, email="qa@example.com", is_super_admin=True)
    app.dependency_overrides[get_db] = lambda: None
    try:
        async with await _client() as client:
            res = await client.post("/api/v1/tcg/products/import/commit", files={"file": ("sample.csv", _CSV, "text/csv")}, data={"confirmed_digest": "x" * 64})
        assert res.status_code == 409
        mock_commit.assert_not_awaited()
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


async def test_preview_rejects_non_csv():
    from app.auth.dependencies import require_super_admin
    from app.database import get_db
    from app.main import app
    from app.models import User
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[require_super_admin] = lambda: User(id=1, email="qa@example.com", is_super_admin=True)
    app.dependency_overrides[get_db] = lambda: None
    try:
        async with await _client() as client:
            res = await client.post("/api/v1/tcg/products/import/preview", files={"file": ("sample.txt", _CSV, "text/plain")})
        assert res.status_code == 422
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@contextmanager
def _user_dependencies(user):
    """Keep the real authorization dependency and restore every prior override."""
    from app.auth.dependencies import get_current_user, require_super_admin
    from app.database import get_db
    from app.main import app

    original = app.dependency_overrides.copy()
    app.dependency_overrides.pop(require_super_admin, None)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: None
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)


@pytest.mark.parametrize(
    ("email", "user_id", "executed_by"),
    [("qa@example.com", 1, "qa@example.com"), ("", 1, "1"), ("", None, "")],
)
@patch("app.routers.tcg_product_import.commit_import", new_callable=AsyncMock)
@patch("app.routers.tcg_product_import.preview", new_callable=AsyncMock)
async def test_commit_with_real_user(mock_preview, mock_commit, email, user_id, executed_by):
    from app.models import User

    mock_preview.return_value = _PREVIEW
    result = {"job_id": "receipt", "filename": "sample.csv", "total": 1, "created": 1, "skipped": 0}
    mock_commit.return_value = result
    with _user_dependencies(User(id=user_id, email=email, is_super_admin=True)):
        async with await _client() as client:
            res = await client.post(
                "/api/v1/tcg/products/import/commit",
                files={"file": ("sample.csv", _CSV, "text/csv")},
                data={"confirmed_digest": _PREVIEW["digest"]},
            )
        assert res.status_code == 200
        assert res.json() == result
        mock_preview.assert_awaited_once_with(None, _CSV, "sample.csv")
        mock_commit.assert_awaited_once_with(None, _CSV, "sample.csv", executed_by)


@pytest.mark.parametrize("endpoint", ["preview", "commit"])
@patch("app.routers.tcg_product_import.commit_import", new_callable=AsyncMock)
@patch("app.routers.tcg_product_import.preview", new_callable=AsyncMock)
async def test_non_admin_is_rejected_by_real_dependency(mock_preview, mock_commit, endpoint):
    from app.models import User

    with _user_dependencies(User(id=1, email="qa@example.com", is_super_admin=False)):
        async with await _client() as client:
            res = await client.post(
                "/api/v1/tcg/products/import/" + endpoint,
                files={"file": ("sample.csv", _CSV, "text/csv")},
                data={"confirmed_digest": _PREVIEW["digest"]},
            )
        assert res.status_code == 403
        mock_preview.assert_not_awaited()
        mock_commit.assert_not_awaited()


@pytest.mark.parametrize(
    ("filename", "raw", "detail"),
    [
        ("sample.txt", _CSV, "PRODUCT_IMPORT_NOT_CSV"),
        ("sample.csv", b"", "PRODUCT_IMPORT_EMPTY_FILE"),
        ("sample.csv", b"\xff", "PRODUCT_IMPORT_NOT_UTF8"),
    ],
)
@patch("app.routers.tcg_product_import.commit_import", new_callable=AsyncMock)
@patch("app.routers.tcg_product_import.preview", new_callable=AsyncMock)
async def test_commit_rejects_invalid_file(mock_preview, mock_commit, filename, raw, detail):
    from app.models import User

    with _user_dependencies(User(id=1, email="qa@example.com", is_super_admin=True)):
        async with await _client() as client:
            res = await client.post(
                "/api/v1/tcg/products/import/commit",
                files={"file": (filename, raw, "text/csv")},
                data={"confirmed_digest": _PREVIEW["digest"]},
            )
        assert res.status_code == 422
        assert res.json()["detail"] == detail
        mock_preview.assert_not_awaited()
        mock_commit.assert_not_awaited()


@patch("app.routers.tcg_product_import.commit_import", new_callable=AsyncMock)
@patch("app.routers.tcg_product_import.preview", new_callable=AsyncMock)
async def test_commit_rejects_file_errors(mock_preview, mock_commit):
    from app.models import User

    mock_preview.return_value = {**_PREVIEW, "file_errors": ["CSV_COLUMN_MISMATCH"]}
    with _user_dependencies(User(id=1, email="qa@example.com", is_super_admin=True)):
        async with await _client() as client:
            res = await client.post(
                "/api/v1/tcg/products/import/commit",
                files={"file": ("sample.csv", _CSV, "text/csv")},
                data={"confirmed_digest": _PREVIEW["digest"]},
            )
        assert res.status_code == 422
        assert res.json()["detail"] == ["CSV_COLUMN_MISMATCH"]
        mock_commit.assert_not_awaited()



@pytest.fixture
def atomic_service(monkeypatch):
    from types import SimpleNamespace

    from app.services import tcg_product_import_svc as importer
    from app.services import tcg_product_master_svc as master

    checked = {"row_no": "1", "japanese_title": "商品", "mark": "", "blocking": [], "warnings": []}
    monkeypatch.setattr(importer, "preview", AsyncMock(return_value={
        "file_errors": [], "digest": "d" * 64, "total": 1, "rows": [checked]}))
    monkeypatch.setattr(importer, "load_lookup_maps", AsyncMock(return_value={}))
    monkeypatch.setattr(importer, "parse_rows", lambda raw: ([{"row_no": "1"}], []))
    monkeypatch.setattr(importer, "build_payload", lambda row, lookups: {})
    monkeypatch.setattr(importer, "start_job", AsyncMock(return_value="job"))
    monkeypatch.setattr(importer, "finish_job", AsyncMock())
    monkeypatch.setattr(importer, "record_row", AsyncMock())
    monkeypatch.setattr(master, "create_product", AsyncMock(return_value={"ok": True, "product_id": "1"}))
    db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
    return importer, master, db, checked


async def test_atomic_row_commit_and_counter_order(atomic_service):
    importer, master, db, checked = atomic_service
    async def receipt(*args, **kwargs):
        db.commit.assert_not_awaited()
        assert kwargs == {"commit": False}
    importer.record_row.side_effect = receipt
    result = await importer.commit_import(db, b"", "rows.csv", "test")
    master.create_product.assert_awaited_once_with(db, force=True, commit=False)
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()
    assert (result["created"], result["skipped"]) == (1, 0)
    importer.finish_job.assert_awaited_once_with(db, "job", 1, 0, "ok")


@pytest.mark.parametrize("blocking", [False, True])
async def test_atomic_rejected_row_receipt_before_counter(atomic_service, blocking):
    importer, master, db, checked = atomic_service
    if blocking:
        checked["blocking"] = ["blocked"]
    else:
        master.create_product.side_effect = ValueError("creation")
    async def receipt(*args, **kwargs):
        assert args[3] == (importer.RESULT_SKIPPED if blocking else importer.RESULT_ERROR)
        assert not kwargs
        assert db.rollback.await_count == (0 if blocking else 1)
        importer.finish_job.assert_not_awaited()
    importer.record_row.side_effect = receipt
    result = await importer.commit_import(db, b"", "rows.csv", "test")
    assert (result["created"], result["skipped"]) == (0, 1)
    if blocking:
        master.create_product.assert_not_awaited()
    importer.finish_job.assert_awaited_once_with(db, "job", 0, 1, "ok")


@pytest.mark.parametrize("phase", ["create_sql", "created_receipt", "commit", "blocked_receipt", "error_receipt", "cancel"])
@pytest.mark.parametrize("rollback_fails", [False, True])
async def test_atomic_stop_preserves_original_exception(atomic_service, phase, rollback_fails):
    import asyncio

    from sqlalchemy.exc import SQLAlchemyError

    importer, master, db, checked = atomic_service
    failure = asyncio.CancelledError("cancel") if phase == "cancel" else (
        SQLAlchemyError("sql") if phase == "create_sql" else ValueError(phase))
    if phase in ("create_sql", "cancel"):
        master.create_product.side_effect = failure
    elif phase == "commit":
        db.commit.side_effect = failure
    else:
        if phase == "blocked_receipt":
            checked["blocking"] = ["blocked"]
        elif phase == "error_receipt":
            master.create_product.side_effect = ValueError("creation")
        importer.record_row.side_effect = failure
    rollback_error = RuntimeError("rollback")
    if rollback_fails:
        # The first rollback for a creation ValueError succeeds, then the error
        # receipt itself fails. A rollback failure must retain that failure.
        db.rollback.side_effect = [None, rollback_error] if phase == "error_receipt" else rollback_error
    with pytest.raises(type(failure)) as caught:
        await importer.commit_import(db, b"", "rows.csv", "test")
    assert caught.value is failure
    assert db.rollback.await_count == (2 if phase == "error_receipt" else 1)
    if rollback_fails:
        assert caught.value.__cause__ is rollback_error
    importer.finish_job.assert_not_awaited()
    assert master.create_product.await_count <= 1


async def test_atomic_creation_value_error_with_failed_rollback_does_not_record(atomic_service):
    importer, master, db, _ = atomic_service
    original = ValueError("verification")
    master.create_product.side_effect = original
    rollback_error = RuntimeError("rollback")
    db.rollback.side_effect = rollback_error
    with pytest.raises(ValueError) as caught:
        await importer.commit_import(db, b"", "rows.csv", "test")
    assert caught.value is original and caught.value.__cause__ is rollback_error
    importer.record_row.assert_not_awaited()
    importer.finish_job.assert_not_awaited()
    db.rollback.assert_awaited_once()


@pytest.mark.parametrize("commit", [None, False, True])
async def test_record_row_commit_flag_defaults_to_true(commit):
    from types import SimpleNamespace

    from app.services.tcg_product_import_svc import record_row

    db = SimpleNamespace(execute=AsyncMock(), commit=AsyncMock())
    checked = {"row_no": "1", "japanese_title": "商品", "mark": ""}
    options = {} if commit is None else {"commit": commit}
    await record_row(db, "job", checked, "created", "1", "", **options)
    db.execute.assert_awaited_once()
    assert db.commit.await_count == (0 if commit is False else 1)


@pytest.mark.parametrize("commit", [None, False, True])
@pytest.mark.parametrize("verify_fails", [False, True])
async def test_create_product_commit_flag_and_legacy_postcheck(monkeypatch, commit, verify_fails):
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from app.services import tcg_product_master_svc as master

    def result(row):
        return SimpleNamespace(fetchone=MagicMock(return_value=row))
    db = SimpleNamespace(commit=AsyncMock())
    calls = 0
    async def execute(query, params=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            return result(SimpleNamespace(name_ja="ワンピース"))
        if calls == 3:
            return result(SimpleNamespace(id="1", int_id=1))
        if calls == 6:
            assert db.commit.await_count == (0 if commit is False else 1)
            return result(None if verify_fails else SimpleNamespace(id=1))
        return result(None)
    db.execute = AsyncMock(side_effect=execute)
    monkeypatch.setattr(master, "check_duplicates", AsyncMock(return_value={"candidates": []}))
    monkeypatch.setattr(master, "_next_pm_code", AsyncMock(return_value="PM0001"))
    args = dict(extraction_item_id="", source_message_id="", product_kind_id=1, work_id=1,
                manufacturer_id="m", product_category_id="c", japanese_title="商品", release_date=None,
                search_keywords="検索", exclude_keywords="除外")
    if commit is not None:
        args["commit"] = commit
    if verify_fails:
        with pytest.raises(ValueError, match="POST_WRITE_GATE"):
            await master.create_product(db, **args)
    else:
        assert await master.create_product(db, **args) == {"ok": True, "product_id": "1"}
    assert db.commit.await_count == (0 if commit is False else 1)
