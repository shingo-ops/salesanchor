"""状態マスタの effect・match_type に予約の手がかりの値（便PO）を入れても、一覧・作成・PATCH が落ちず、従来の値の扱いが変わらないこと。

DB には触れない（偽のセッションが行を返す）。super_admin_status_master と status_master の両方を呼ぶ。
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.routers import status_master as tenant_router
from app.routers import super_admin_status_master as admin_router
from app.schemas.central_masters import TcgStatusMasterCreate, TcgStatusMasterResponse, TcgStatusMasterUpdate
from app.services import tcg_status_values as values

_NOW = datetime(2026, 10, 12, tzinfo=timezone.utc)
_NEW_PAIRS = [
    ("HEADING", "REGEX"), ("DATE_AHEAD", "REGEX"), ("RELEASE_AHEAD", "RELEASE"),
]
_OLD_PAIRS = [("OUTPUT", "REGEX"), ("OUTPUT", "LITERAL"), ("OUTPUT", "DEFAULT"), ("EXCLUDE", "LITERAL")]


def _db_row(effect, match_type, row_id=1):
    return {
        "id": row_id, "status_id": f"ST{row_id:04d}", "canonical": "Pre-order", "search_pattern": "予約", "exclude_pattern": "",
        "priority": 10, "enabled": True, "note": "", "match_type": match_type, "effect": effect,
        "created_at": _NOW, "updated_at": _NOW,
    }


class _Mappings:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return _Mappings(self._rows)


class _FakeDb:
    def __init__(self, rows):
        self._rows = rows
        self.committed = False

    async def execute(self, *_args, **_kwargs):
        return _Result(self._rows)

    async def commit(self):
        self.committed = True


@pytest.fixture(autouse=True)
def _no_tenant_reset(monkeypatch):
    async def _noop(*_a, **_k):
        return None

    monkeypatch.setattr(tenant_router, "reset_tenant_context", _noop)


def test_allowed_values_come_from_the_single_constants():
    from app.schemas import central_masters

    assert central_masters._VALID_EFFECTS is values.VALID_EFFECTS
    assert central_masters._VALID_MATCH_TYPES is values.VALID_MATCH_TYPES
    assert {"OUTPUT", "EXCLUDE"} <= values.VALID_EFFECTS and {"REGEX", "LITERAL", "DEFAULT"} <= values.VALID_MATCH_TYPES


@pytest.mark.parametrize(("effect", "match_type"), _NEW_PAIRS + _OLD_PAIRS)
def test_response_accepts_old_and_new_values(effect, match_type):
    assert TcgStatusMasterResponse(**_db_row(effect, match_type)).effect == effect


@pytest.mark.parametrize(("effect", "match_type"), [("UNKNOWN", "REGEX"), ("OUTPUT", "UNKNOWN")])
def test_unknown_values_are_still_rejected(effect, match_type):
    with pytest.raises(ValidationError):
        TcgStatusMasterResponse(**_db_row(effect, match_type))


@pytest.mark.parametrize(("effect", "match_type"), _NEW_PAIRS)
@pytest.mark.asyncio
async def test_admin_list_survives_new_values(effect, match_type):
    out = await admin_router.list_status_master(q=None, page=1, per_page=100, db=_FakeDb([_db_row(effect, match_type), _db_row("OUTPUT", "DEFAULT", 2)]))
    assert [r.effect for r in out] == [effect, "OUTPUT"]


@pytest.mark.parametrize(("effect", "match_type"), _NEW_PAIRS)
@pytest.mark.asyncio
async def test_tenant_list_survives_new_values(effect, match_type):
    out = await tenant_router.list_status_master(
        page=1, per_page=100, search=None, db=_FakeDb([_db_row(effect, match_type)]), tenant_id=1, current_user=None,
    )
    assert out[0].match_type == match_type


@pytest.mark.parametrize(("effect", "match_type"), _NEW_PAIRS)
@pytest.mark.asyncio
async def test_create_and_patch_accept_new_values_in_both_routers(effect, match_type):
    body = {"status_id": "ST0900", "canonical": "Pre-order", "priority": 10, "match_type": match_type, "effect": effect}
    row = _db_row(effect, match_type)
    admin_created = await admin_router.create_status_master(TcgStatusMasterCreate(**body), db=_FakeDb([row]), current_user=None)
    tenant_created = await tenant_router.create_status_master(
        TcgStatusMasterCreate(**body), db=_FakeDb([row]), tenant_id=1, current_user=None
    )
    patch = TcgStatusMasterUpdate(effect=effect, match_type=match_type)
    admin_patched = await admin_router.update_status_master(1, patch, db=_FakeDb([row]))
    tenant_patched = await tenant_router.update_status_master(1, patch, db=_FakeDb([row]), tenant_id=1, current_user=None)
    assert {admin_created.effect, tenant_created.effect, admin_patched.effect, tenant_patched.effect} == {effect}


@pytest.mark.parametrize(("effect", "match_type"), _OLD_PAIRS)
def test_create_still_accepts_old_values(effect, match_type):
    body = {"status_id": "ST0901", "canonical": "Sold out", "priority": 1, "match_type": match_type, "effect": effect}
    assert TcgStatusMasterCreate(**body).effect == effect


def test_admin_preview_does_not_fail_on_release_match_type():
    out = admin_router._preview_match("RELEASE", "", "x")
    assert out.matched is False
