"""
自社在庫（own_inventory）サービス + API のテスト。

ADR SA-04/05: 2段階引当（reserve / release / ship）の動作検証。

テスト方針:
  - SQLite インメモリ DB を使用（conftest.py の db_session / client フィクスチャを流用）。
  - own_inventory テーブルは本テスト内でセットアップ（conftest のスコープ外）。
  - FOR UPDATE は conftest の before_cursor_execute フックが SQLite 用に除去済み。
  - GREATEST(0, ...) は SQLite 非対応のため、CASE WHEN ... END に変換済み（inventory_reservation.py 参照）。
  - GENERATED ALWAYS AS はSQLiteでCREATE TABLE時には非互換のため、
    テスト用テーブルでは available_qty を通常カラムとして定義し、
    サービス関数はカラムを直接更新しない（READ: physical - reserved で算出）。
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.inventory_reservation import (
    release_reservation,
    reserve_qty,
    ship_qty,
)


# ── テスト用テーブルセットアップ ────────────────────────────────────────────────

@pytest_asyncio.fixture
async def own_inventory_table(db_session: AsyncSession):
    """own_inventory テーブルをテスト用に作成し、サンプルデータを挿入する。

    SQLite 互換: GENERATED ALWAYS AS の代わりに通常カラムとして available_qty を定義。
    サービス関数は available_qty を直接更新しないため、整合性チェックは SELECT で算出する。
    """
    await db_session.execute(text("""
        CREATE TABLE IF NOT EXISTS own_inventory (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id    INTEGER NOT NULL,
            product_id   INTEGER NOT NULL DEFAULT 1,
            physical_qty INTEGER NOT NULL DEFAULT 0,
            reserved_qty INTEGER NOT NULL DEFAULT 0,
            available_qty INTEGER,
            unit_price   REAL,
            condition    TEXT,
            status       TEXT NOT NULL DEFAULT 'active',
            note_ja      TEXT,
            note_en      TEXT,
            antique_ledger_id INTEGER,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    # サンプルレコード: physical_qty=10, reserved_qty=3 → available=7
    await db_session.execute(text("""
        INSERT INTO own_inventory
            (tenant_id, product_id, physical_qty, reserved_qty, available_qty, status)
        VALUES (999, 1, 10, 3, 7, 'active')
    """))
    await db_session.flush()
    # ID を取得
    result = await db_session.execute(
        text("SELECT id FROM own_inventory WHERE tenant_id = 999 ORDER BY id DESC LIMIT 1")
    )
    inventory_id = result.scalar_one()
    yield inventory_id
    await db_session.execute(text("DELETE FROM own_inventory"))


# ── reserve_qty テスト ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reserve_qty_success(db_session: AsyncSession, own_inventory_table: int):
    """利用可能数(7)の範囲内(5)での引当は成功する。"""
    inventory_id = own_inventory_table

    await reserve_qty(db_session, inventory_id, qty=5, tenant_id=999)

    result = await db_session.execute(
        text("SELECT physical_qty, reserved_qty FROM own_inventory WHERE id = :id"),
        {"id": inventory_id},
    )
    row = result.fetchone()
    assert row.physical_qty == 10
    assert row.reserved_qty == 8  # 3 + 5


@pytest.mark.asyncio
async def test_reserve_qty_exact_available(db_session: AsyncSession, own_inventory_table: int):
    """利用可能数と同数の引当は成功する（available=7、qty=7）。"""
    inventory_id = own_inventory_table

    await reserve_qty(db_session, inventory_id, qty=7, tenant_id=999)

    result = await db_session.execute(
        text("SELECT physical_qty, reserved_qty FROM own_inventory WHERE id = :id"),
        {"id": inventory_id},
    )
    row = result.fetchone()
    assert row.reserved_qty == 10  # 3 + 7


@pytest.mark.asyncio
async def test_reserve_qty_insufficient(db_session: AsyncSession, own_inventory_table: int):
    """利用可能数(7)を超える引当(8)は ValueError を raise する。"""
    inventory_id = own_inventory_table

    with pytest.raises(ValueError, match="在庫不足"):
        await reserve_qty(db_session, inventory_id, qty=8, tenant_id=999)


@pytest.mark.asyncio
async def test_reserve_qty_not_found(db_session: AsyncSession, own_inventory_table: int):
    """存在しない ID の引当は ValueError を raise する。"""
    with pytest.raises(ValueError, match="見つかりません"):
        await reserve_qty(db_session, own_inventory_id=99999, qty=1, tenant_id=999)


@pytest.mark.asyncio
async def test_reserve_qty_invalid_qty(db_session: AsyncSession, own_inventory_table: int):
    """qty=0 は ValueError を raise する。"""
    inventory_id = own_inventory_table

    with pytest.raises(ValueError, match="1 以上"):
        await reserve_qty(db_session, inventory_id, qty=0, tenant_id=999)


# ── release_reservation テスト ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_release_reservation_success(db_session: AsyncSession, own_inventory_table: int):
    """引当解除: reserved_qty が qty だけ減る。"""
    inventory_id = own_inventory_table

    await release_reservation(db_session, inventory_id, qty=2, tenant_id=999)

    result = await db_session.execute(
        text("SELECT reserved_qty FROM own_inventory WHERE id = :id"),
        {"id": inventory_id},
    )
    row = result.fetchone()
    assert row.reserved_qty == 1  # 3 - 2


@pytest.mark.asyncio
async def test_release_reservation_clamps_to_zero(db_session: AsyncSession, own_inventory_table: int):
    """引当解除量が reserved_qty を超えても 0 にクランプされる。"""
    inventory_id = own_inventory_table

    # reserved_qty=3 に対して qty=100 を解除してもエラーにならず 0 になる
    await release_reservation(db_session, inventory_id, qty=100, tenant_id=999)

    result = await db_session.execute(
        text("SELECT reserved_qty FROM own_inventory WHERE id = :id"),
        {"id": inventory_id},
    )
    row = result.fetchone()
    assert row.reserved_qty == 0


# ── ship_qty テスト ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ship_qty_success(db_session: AsyncSession, own_inventory_table: int):
    """発送確定: physical_qty と reserved_qty が同時に qty だけ減る。"""
    inventory_id = own_inventory_table
    # initial: physical=10, reserved=3

    await ship_qty(db_session, inventory_id, qty=3, tenant_id=999)

    result = await db_session.execute(
        text("SELECT physical_qty, reserved_qty FROM own_inventory WHERE id = :id"),
        {"id": inventory_id},
    )
    row = result.fetchone()
    assert row.physical_qty == 7   # 10 - 3
    assert row.reserved_qty == 0   # GREATEST(0, 3 - 3)


@pytest.mark.asyncio
async def test_ship_qty_partial_reserved(db_session: AsyncSession, own_inventory_table: int):
    """発送数が reserved_qty より少ない場合: reserved_qty も qty だけ減る。"""
    inventory_id = own_inventory_table
    # initial: physical=10, reserved=3

    await ship_qty(db_session, inventory_id, qty=1, tenant_id=999)

    result = await db_session.execute(
        text("SELECT physical_qty, reserved_qty FROM own_inventory WHERE id = :id"),
        {"id": inventory_id},
    )
    row = result.fetchone()
    assert row.physical_qty == 9   # 10 - 1
    assert row.reserved_qty == 2   # GREATEST(0, 3 - 1)


@pytest.mark.asyncio
async def test_ship_qty_invalid_qty(db_session: AsyncSession, own_inventory_table: int):
    """qty=0 は ValueError を raise する。"""
    inventory_id = own_inventory_table

    with pytest.raises(ValueError, match="1 以上"):
        await ship_qty(db_session, inventory_id, qty=0, tenant_id=999)
