"""注記マスタの match_type 検査（STATE_LITERAL 許可・CSV 取り込みの検査）。DB 不使用。"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.routers import note_master as tenant_router
from app.routers import super_admin_note_master as admin_router
from app.schemas.central_masters import (
    TcgNoteMasterCreate,
    TcgNoteMasterResponse,
    TcgNoteMasterUpdate,
)

_BASE = {"label_ja": "跡痕あり", "label_en": "Mark", "priority": 1}
_HEADER = "label_ja,label_en,enabled,priority"


def _response(match_type: str) -> TcgNoteMasterResponse:
    return TcgNoteMasterResponse(
        id=148, created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1), match_type=match_type, **_BASE
    )


def test_t1_response_accepts_state_literal():
    assert _response("STATE_LITERAL").match_type == "STATE_LITERAL"


def test_t2_create_and_update_accept_state_literal():
    assert TcgNoteMasterCreate(match_type="STATE_LITERAL", **_BASE).match_type == "STATE_LITERAL"
    assert TcgNoteMasterUpdate(match_type="STATE_LITERAL").match_type == "STATE_LITERAL"


@pytest.mark.parametrize("mt", ["LITERAL", "REGEX", "DEFAULT"])
def test_t3_existing_types_still_pass(mt):
    assert _response(mt).match_type == mt
    assert TcgNoteMasterCreate(match_type=mt, **_BASE).match_type == mt
    assert TcgNoteMasterUpdate(match_type=mt).match_type == mt


def test_t4_bogus_rejected_and_update_none_ok():
    with pytest.raises(ValidationError):
        _response("BOGUS")
    with pytest.raises(ValidationError):
        TcgNoteMasterCreate(match_type="BOGUS", **_BASE)
    with pytest.raises(ValidationError):
        TcgNoteMasterUpdate(match_type="BOGUS")
    assert TcgNoteMasterUpdate(match_type=None).match_type is None


@pytest.mark.parametrize("mod", [tenant_router, admin_router])
def test_t5_csv_match_type(mod):
    ok = f"{_HEADER},match_type\nA,a,true,1,STATE_LITERAL\nB,b,true,2,\n".encode()
    rows, errors = mod._parse_note_master(ok)
    assert errors == []
    assert [r["match_type"] for r in rows] == ["STATE_LITERAL", "LITERAL"]

    no_col = f"{_HEADER}\nA,a,true,1\n".encode()
    rows, errors = mod._parse_note_master(no_col)
    assert errors == []
    assert rows[0]["match_type"] == "LITERAL"

    bad = f"{_HEADER},match_type\nA,a,true,1,BOGUS\n".encode()
    rows, errors = mod._parse_note_master(bad)
    assert rows == []
    assert errors[0].startswith("L2: invalid match_type 'BOGUS'")
