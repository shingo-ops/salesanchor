"""
POST /api/v1/staff の staff_code 自動採番テスト。

本番障害（2026-10-01）: 仮コード "EMP-PENDING-<uuid32>"(44文字) が
staff.staff_code VARCHAR(20) を超え StringDataRightTruncationError → 500。
SQLite は長さを強制しないため、仮コード長は単体テストで直接守る。
"""

import re

import pytest
from sqlalchemy import text

from app.routers.staff import STAFF_CODE_MAX_LENGTH, _new_placeholder_code

STAFF_CODE_PATTERN = re.compile(r"^EMP-\d{5}$")


def test_placeholder_code_fits_varchar_20():
    assert STAFF_CODE_MAX_LENGTH == 20
    assert len(_new_placeholder_code()) <= STAFF_CODE_MAX_LENGTH


def test_placeholder_code_is_unique():
    assert len({_new_placeholder_code() for _ in range(1000)}) == 1000


async def _seed_role(db_session):
    await db_session.execute(text("""
        INSERT INTO roles (id, tenant_id, name, color, priority, is_system)
        VALUES (1, 999, 'staff', '#888888', 0, FALSE)
    """))
    await db_session.commit()


def _body(email: str, **extra):
    return {
        "surname_jp": "山田", "given_name_jp": "太郎",
        "surname_en": "Yamada", "given_name_en": "Taro",
        "primary_email": email, "role_id": 1, **extra,
    }


@pytest.mark.asyncio
async def test_create_staff_auto_numbers_sequentially(client, db_session):
    await _seed_role(db_session)

    first = await client.post("/api/v1/staff", json=_body("auto1@example.com"))
    second = await client.post("/api/v1/staff", json=_body("auto2@example.com"))

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    codes = [first.json()["staff_code"], second.json()["staff_code"]]
    assert all(STAFF_CODE_PATTERN.match(c) for c in codes)
    assert codes[0] != codes[1]
    assert codes == [f"EMP-{first.json()['id']:05d}", f"EMP-{second.json()['id']:05d}"]


@pytest.mark.asyncio
async def test_create_staff_ignores_client_staff_code(client, db_session):
    await _seed_role(db_session)

    res = await client.post("/api/v1/staff", json=_body("ign@example.com", staff_code="CUSTOM-1"))

    assert res.status_code == 201, res.text
    assert STAFF_CODE_PATTERN.match(res.json()["staff_code"])
