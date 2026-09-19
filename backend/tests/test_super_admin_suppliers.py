"""Super-admin suppliers + supplier_discord_routing CRUD テスト。

spec.md v1.1 F2 (Sprint 2) / AC2.5:
  - supplier_type 切替 (individual / corporate)
  - discord_routing 紐付け
  - UNIQUE(discord_guild_id, discord_channel_id) 検証

実 PostgreSQL 必須。
"""
from __future__ import annotations

import csv
import hashlib
import io
import os
import uuid

import pytest

TEST_PG_URL = os.getenv("TEST_PG_URL")

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not TEST_PG_URL,
        reason="実 PostgreSQL 環境が必要 (TEST_PG_URL 未設定)。",
    ),
]


@pytest.fixture
async def engine():
    from sqlalchemy.ext.asyncio import create_async_engine
    eng = create_async_engine(TEST_PG_URL, echo=False)
    yield eng
    await eng.dispose()


async def test_supplier_type_check_constraint(engine):
    """AC1.7 + AC2.5: 不正な supplier_type は CHECK 制約で 23514。"""
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    async with engine.connect() as conn:
        exists = (await conn.execute(text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='suppliers'"
        ))).scalar_one_or_none()
    if not exists:
        pytest.skip("public.suppliers 未作成 (migration 056 が必要)")

    raised = False
    try:
        async with engine.begin() as conn:
            await conn.execute(text("""
                INSERT INTO public.suppliers (name, supplier_type, default_language)
                VALUES ('test_invalid_type', 'INVALID', 'ja')
            """))
    except IntegrityError as exc:
        raised = True
        # check_violation = 23514
        assert "23514" in str(exc.orig) or "check" in str(exc.orig).lower()
    assert raised


async def test_supplier_discord_routing_unique(engine):
    """AC2.5: UNIQUE(discord_guild_id, discord_channel_id) で重複不可。"""
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    async with engine.connect() as conn:
        exists = (await conn.execute(text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='supplier_discord_routing'"
        ))).scalar_one_or_none()
    if not exists:
        pytest.skip("public.supplier_discord_routing 未作成 (migration 060 が必要)")

    # supplier 用意
    sup_name = f"test_supplier_ac2_5_{uuid.uuid4().hex[:6]}"
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            INSERT INTO public.suppliers (name, supplier_type, default_language)
            VALUES (:n, 'corporate', 'ja')
            RETURNING id
        """), {"n": sup_name})
        sup_id = result.scalar_one()

    g_id = f"g_{uuid.uuid4().hex[:10]}"
    c_id = f"c_{uuid.uuid4().hex[:10]}"

    async with engine.begin() as conn:
        await conn.execute(text("""
            INSERT INTO public.supplier_discord_routing
                (supplier_id, discord_guild_id, discord_channel_id, is_active)
            VALUES (:sid, :g, :c, TRUE)
        """), {"sid": sup_id, "g": g_id, "c": c_id})

    raised = False
    try:
        async with engine.begin() as conn:
            # 同じ supplier、同じ guild/channel で再 insert → UNIQUE 違反
            await conn.execute(text("""
                INSERT INTO public.supplier_discord_routing
                    (supplier_id, discord_guild_id, discord_channel_id, is_active)
                VALUES (:sid, :g, :c, TRUE)
            """), {"sid": sup_id, "g": g_id, "c": c_id})
    except IntegrityError as exc:
        raised = True
        assert "23505" in str(exc.orig) or "duplicate" in str(exc.orig).lower()

    assert raised, "UNIQUE 制約が動作していない"

    # cleanup
    async with engine.begin() as conn:
        await conn.execute(text(
            "DELETE FROM public.supplier_discord_routing WHERE supplier_id = :sid"
        ), {"sid": sup_id})
        await conn.execute(text(
            "DELETE FROM public.suppliers WHERE id = :sid"
        ), {"sid": sup_id})


# ---------------------------------------------------------------------------
# CSV Export / Import tests
# ---------------------------------------------------------------------------

def _build_csv(rows: list[dict]) -> bytes:
    """Build CSV bytes from a list of dicts. First dict defines headers."""
    buf = io.StringIO()
    if not rows:
        return b""
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


async def _setup_central_supplier(conn, suffix: str) -> int:
    """Insert a central supplier (tenant_id IS NULL) and return its id."""
    from sqlalchemy import text as t
    result = await conn.execute(t("""
        INSERT INTO public.suppliers
            (name, supplier_type, default_language, is_active, tenant_id)
        VALUES (:name, 'corporate', 'ja', TRUE, NULL)
        RETURNING id
    """), {"name": f"Central Supplier {suffix}"})
    sup_id = result.scalar_one()
    await conn.execute(t("""
        UPDATE public.suppliers SET supplier_code = :code WHERE id = :id
    """), {"code": f"SP-{sup_id:05d}", "id": sup_id})
    return sup_id


async def _cleanup_suppliers(conn, ids: list[int]) -> None:
    from sqlalchemy import text as t
    for sid in ids:
        await conn.execute(t("DELETE FROM public.suppliers WHERE id = :id"), {"id": sid})


async def test_export_csv(engine):
    """CSVエクスポートでtenant_id IS NULLかつis_active=TRUEの仕入元のみ返る。"""
    from sqlalchemy import text as t
    from sqlalchemy.ext.asyncio import AsyncSession

    async with engine.connect() as conn:
        exists = (await conn.execute(t(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='suppliers'"
        ))).scalar_one_or_none()
    if not exists:
        pytest.skip("public.suppliers 未作成 (migration が必要)")

    suffix = uuid.uuid4().hex[:6]
    async with engine.begin() as conn:
        sup_id = await _setup_central_supplier(conn, suffix)

    try:
        # Call the export endpoint function directly
        from app.routers.super_admin_suppliers import export_suppliers_csv

        async with AsyncSession(engine) as session:
            response = await export_suppliers_csv(db=session)

        assert response.media_type == "text/csv"
        assert "attachment" in response.headers.get("content-disposition", "")
        assert "suppliers.csv" in response.headers.get("content-disposition", "")

        content = response.body.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        assert reader.fieldnames is not None
        assert "supplier_code" in reader.fieldnames
        assert "name" in reader.fieldnames
        assert "is_active" in reader.fieldnames

        rows = list(reader)
        names = [r["name"] for r in rows]
        assert f"Central Supplier {suffix}" in names

    finally:
        async with engine.begin() as conn:
            await _cleanup_suppliers(conn, [sup_id])


async def test_import_preview(engine):
    """プレビューでバリデーション結果が返り、DBは変更されない。"""
    from sqlalchemy import text as t

    async with engine.connect() as conn:
        exists = (await conn.execute(t(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='suppliers'"
        ))).scalar_one_or_none()
    if not exists:
        pytest.skip("public.suppliers 未作成 (migration が必要)")

    suffix = uuid.uuid4().hex[:6]
    csv_data = _build_csv([
        {
            "supplier_code": "",
            "name": f"Preview Supplier {suffix}",
            "supplier_type": "corporate",
            "line_name": "",
            "contact_name": "Test Contact",
            "email": "",
            "phone": "",
            "postal_code": "",
            "prefecture": "",
            "city": "",
            "address1": "",
            "address2": "",
            "notes": "",
            "is_active": "true",
        }
    ])

    from io import BytesIO

    from fastapi import UploadFile
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.routers.super_admin_suppliers import import_suppliers_preview

    upload = UploadFile(filename="test.csv", file=BytesIO(csv_data))

    async with AsyncSession(engine) as session:
        result = await import_suppliers_preview(file=upload, db=session)

    assert "digest" in result
    assert result["total"] == 1
    assert result["inserts"] == 1
    assert result["updates"] == 0
    assert result["errors"] == []
    assert len(result["preview_rows"]) == 1
    assert result["preview_rows"][0]["name"] == f"Preview Supplier {suffix}"

    # Confirm DB was NOT changed
    async with engine.connect() as conn:
        row = (await conn.execute(t(
            "SELECT id FROM public.suppliers WHERE name = :n AND tenant_id IS NULL"
        ), {"n": f"Preview Supplier {suffix}"})).fetchone()
    assert row is None, "Preview must not write to DB"


async def test_import_commit(engine):
    """確定でtenant_id=NULLのデータが書き込まれる。"""
    from sqlalchemy import text as t

    async with engine.connect() as conn:
        exists = (await conn.execute(t(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='suppliers'"
        ))).scalar_one_or_none()
    if not exists:
        pytest.skip("public.suppliers 未作成 (migration が必要)")

    suffix = uuid.uuid4().hex[:6]
    csv_data = _build_csv([
        {
            "supplier_code": "",
            "name": f"Commit Supplier {suffix}",
            "supplier_type": "individual",
            "line_name": "",
            "contact_name": "",
            "email": "",
            "phone": "",
            "postal_code": "",
            "prefecture": "",
            "city": "",
            "address1": "",
            "address2": "",
            "notes": "committed via test",
            "is_active": "true",
        }
    ])
    digest = _sha256(csv_data)

    from io import BytesIO

    from fastapi import UploadFile
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.routers.super_admin_suppliers import import_suppliers_commit

    upload = UploadFile(filename="test.csv", file=BytesIO(csv_data))

    async with AsyncSession(engine) as session:
        result = await import_suppliers_commit(file=upload, digest=digest, db=session)

    assert result["inserted"] == 1
    assert result["updated"] == 0
    assert result["errors"] == []

    # Verify row exists in DB
    async with engine.connect() as conn:
        row = (await conn.execute(t(
            "SELECT id, supplier_code, notes, tenant_id FROM public.suppliers "
            "WHERE name = :n AND tenant_id IS NULL"
        ), {"n": f"Commit Supplier {suffix}"})).mappings().fetchone()
    assert row is not None, "Row must be inserted into DB"
    assert row["tenant_id"] is None
    assert row["supplier_code"] is not None
    assert row["supplier_code"].startswith("SP-")
    assert row["notes"] == "committed via test"

    # cleanup
    async with engine.begin() as conn:
        await _cleanup_suppliers(conn, [row["id"]])


async def test_import_upsert(engine):
    """supplier_code一致で更新、新規はINSERT。"""
    from sqlalchemy import text as t

    async with engine.connect() as conn:
        exists = (await conn.execute(t(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='suppliers'"
        ))).scalar_one_or_none()
    if not exists:
        pytest.skip("public.suppliers 未作成 (migration が必要)")

    suffix = uuid.uuid4().hex[:6]
    async with engine.begin() as conn:
        existing_id = await _setup_central_supplier(conn, f"upsert_{suffix}")

    # Get the auto-generated supplier_code
    async with engine.connect() as conn:
        row = (await conn.execute(t(
            "SELECT supplier_code FROM public.suppliers WHERE id = :id"
        ), {"id": existing_id})).fetchone()
    existing_code = row[0]

    csv_data = _build_csv([
        # Update row: existing supplier_code + changed contact_name
        {
            "supplier_code": existing_code,
            "name": f"Central Supplier upsert_{suffix}",
            "supplier_type": "",
            "line_name": "",
            "contact_name": "Updated Contact",
            "email": "",
            "phone": "",
            "postal_code": "",
            "prefecture": "",
            "city": "",
            "address1": "",
            "address2": "",
            "notes": "",
            "is_active": "",
        },
        # Insert row: no supplier_code
        {
            "supplier_code": "",
            "name": f"New Supplier upsert_{suffix}",
            "supplier_type": "individual",
            "line_name": "",
            "contact_name": "",
            "email": "",
            "phone": "",
            "postal_code": "",
            "prefecture": "",
            "city": "",
            "address1": "",
            "address2": "",
            "notes": "",
            "is_active": "true",
        },
    ])
    digest = _sha256(csv_data)

    from io import BytesIO

    from fastapi import UploadFile
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.routers.super_admin_suppliers import import_suppliers_commit

    upload = UploadFile(filename="test.csv", file=BytesIO(csv_data))

    async with AsyncSession(engine) as session:
        result = await import_suppliers_commit(file=upload, digest=digest, db=session)

    assert result["inserted"] == 1
    assert result["updated"] == 1
    assert result["errors"] == []

    # Verify existing supplier was updated
    async with engine.connect() as conn:
        updated = (await conn.execute(t(
            "SELECT contact_name FROM public.suppliers WHERE id = :id"
        ), {"id": existing_id})).fetchone()
    assert updated is not None
    assert updated[0] == "Updated Contact"

    # Verify new supplier was inserted
    async with engine.connect() as conn:
        new_row = (await conn.execute(t(
            "SELECT id, supplier_code FROM public.suppliers "
            "WHERE name = :n AND tenant_id IS NULL"
        ), {"n": f"New Supplier upsert_{suffix}"})).mappings().fetchone()
    assert new_row is not None

    # cleanup
    async with engine.begin() as conn:
        await _cleanup_suppliers(conn, [existing_id, new_row["id"]])


async def test_import_validation_errors(engine):
    """不正データで行番号付きエラーが返る。"""
    from sqlalchemy import text as t

    async with engine.connect() as conn:
        exists = (await conn.execute(t(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='suppliers'"
        ))).scalar_one_or_none()
    if not exists:
        pytest.skip("public.suppliers 未作成 (migration が必要)")

    # Row 2: missing name (no supplier_code either)
    # Row 3: invalid supplier_type
    # Row 4: invalid is_active
    csv_data = _build_csv([
        {
            "supplier_code": "",
            "name": "",
            "supplier_type": "",
            "line_name": "",
            "contact_name": "",
            "email": "",
            "phone": "",
            "postal_code": "",
            "prefecture": "",
            "city": "",
            "address1": "",
            "address2": "",
            "notes": "",
            "is_active": "",
        },
        {
            "supplier_code": "",
            "name": "Bad Type Supplier",
            "supplier_type": "unknown_type",
            "line_name": "",
            "contact_name": "",
            "email": "",
            "phone": "",
            "postal_code": "",
            "prefecture": "",
            "city": "",
            "address1": "",
            "address2": "",
            "notes": "",
            "is_active": "",
        },
        {
            "supplier_code": "",
            "name": "Bad Active Supplier",
            "supplier_type": "corporate",
            "line_name": "",
            "contact_name": "",
            "email": "",
            "phone": "",
            "postal_code": "",
            "prefecture": "",
            "city": "",
            "address1": "",
            "address2": "",
            "notes": "",
            "is_active": "maybe",
        },
    ])

    from io import BytesIO

    from fastapi import UploadFile
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.routers.super_admin_suppliers import import_suppliers_preview

    upload = UploadFile(filename="test.csv", file=BytesIO(csv_data))

    async with AsyncSession(engine) as session:
        result = await import_suppliers_preview(file=upload, db=session)

    assert len(result["errors"]) == 3
    # Each error must include line number
    for err in result["errors"]:
        assert err.startswith("L"), f"Error must start with line number: {err}"
    error_text = " ".join(result["errors"])
    assert "L2" in error_text  # missing name
    assert "L3" in error_text  # invalid supplier_type
    assert "L4" in error_text  # invalid is_active


async def test_import_digest_mismatch(engine):
    """プレビュー後にファイルを変更するとcommitが409を返す。"""
    from sqlalchemy import text as t

    async with engine.connect() as conn:
        exists = (await conn.execute(t(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='suppliers'"
        ))).scalar_one_or_none()
    if not exists:
        pytest.skip("public.suppliers 未作成 (migration が必要)")

    suffix = uuid.uuid4().hex[:6]
    original_csv = _build_csv([
        {
            "supplier_code": "",
            "name": f"Digest Test {suffix}",
            "supplier_type": "corporate",
            "line_name": "",
            "contact_name": "",
            "email": "",
            "phone": "",
            "postal_code": "",
            "prefecture": "",
            "city": "",
            "address1": "",
            "address2": "",
            "notes": "",
            "is_active": "true",
        }
    ])
    # Simulate file modified after preview
    modified_csv = _build_csv([
        {
            "supplier_code": "",
            "name": f"Modified Supplier {suffix}",
            "supplier_type": "corporate",
            "line_name": "",
            "contact_name": "",
            "email": "",
            "phone": "",
            "postal_code": "",
            "prefecture": "",
            "city": "",
            "address1": "",
            "address2": "",
            "notes": "",
            "is_active": "true",
        }
    ])
    original_digest = _sha256(original_csv)

    from io import BytesIO

    import pytest as _pytest
    from fastapi import UploadFile
    from sqlalchemy.ext.asyncio import AsyncSession
    from starlette.exceptions import HTTPException as StarletteHTTPException

    from app.routers.super_admin_suppliers import import_suppliers_commit

    # Submit modified file with original digest → should get 409
    upload = UploadFile(filename="test.csv", file=BytesIO(modified_csv))

    with _pytest.raises(StarletteHTTPException) as exc_info:
        async with AsyncSession(engine) as session:
            await import_suppliers_commit(file=upload, digest=original_digest, db=session)

    assert exc_info.value.status_code == 409
    assert "DIGEST_MISMATCH" in exc_info.value.detail
