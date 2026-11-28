"""書類に載せる会社情報（国内用・海外用）の口の試験（ADR-1061 便2-2c2b。design.md §3-4・§3-4b）。

- 国内用・海外用の行を片方ずつ丸ごと保存し、もう片方は変わらない。
- 決まり違いは 422 と欄ごとの理由（detail.fields）。保存しない。
- 登録が無のときは番号を送っても NULL で保存する。
- 保存のたびに監査の記録が1行残る（作った・直した）。
- ほかの会社の行は読まない。
- 都道府県名は試験に書かず、正本の seed ファイルから読む。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from sqlalchemy import text

_ROOT = Path(__file__).resolve().parents[2]
_PREF_SEED = _ROOT / "docs" / "handoff" / "viewer-contract-stage" / "data" / "prefectures.sql"
_PREF_ROW_RE = re.compile(r"^\s*\('(\d{2})',\s*'([^']+)',\s*'([^']+)',\s*(\d+)\),?$", re.M)
_URL = "/api/v1/admin/issuer-profiles"
_REG_NO = "T1234567890123"


async def _seed_prefectures(db_session) -> list[tuple[str, str, str, str]]:
    rows = _PREF_ROW_RE.findall(_PREF_SEED.read_text("utf-8"))
    for code, name_ja, name_en, sort_order in rows:
        await db_session.execute(
            text("INSERT OR IGNORE INTO prefectures (code, name_ja, name_en, sort_order) VALUES (:c, :j, :e, :s)"),
            {"c": code, "j": name_ja, "e": name_en, "s": int(sort_order)},
        )
    await db_session.commit()
    return rows


async def _seed_legacy(db_session) -> None:
    await db_session.execute(text(
        "INSERT INTO tenant_profile (company_name, company_name_en, address, phone, email, website, default_language) "
        "VALUES ('Legacy Co', 'Legacy Co EN', 'Legacy Street 1', '03-0000-0000', 'legacy@example.com', "
        "'https://legacy.example.com', 'ja')"
    ))
    await db_session.commit()


def _domestic(**over):
    body = {
        "company_name": "Domestic Co", "email": "info@example.com", "website": None,
        "country_code": "JP", "postal_code": "1000001", "prefecture_code": "13", "state_region": None,
        "city": "Chiyoda", "address1": "1-1", "address2": None, "phone": "0312345678",
        "is_invoice_registered": False, "registration_number": None,
    }
    body.update(over)
    return body


def _overseas(**over):
    body = {
        "company_name": "Overseas Co", "email": None, "website": None,
        "country_code": "US", "postal_code": "94105", "prefecture_code": None, "state_region": "CA",
        "city": "San Francisco", "address1": "1 Market St", "address2": None, "phone": "+14155550100",
        "is_invoice_registered": False, "registration_number": None,
    }
    body.update(over)
    return body


async def _count_rows(db_session) -> int:
    return (await db_session.execute(text("SELECT COUNT(*) FROM tenant_issuer_profiles"))).scalar_one()


async def test_get_returns_nulls_without_rows(client):
    resp = await client.get(_URL)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"domestic": None, "overseas": None, "legacy": None}


async def test_get_returns_legacy_values_when_region_row_missing(client, db_session):
    await _seed_legacy(db_session)
    resp = await client.get(_URL)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["domestic"] is None
    assert body["overseas"] is None
    assert body["legacy"]["company_name"] == "Legacy Co"
    assert body["legacy"]["email"] == "legacy@example.com"


async def test_put_creates_then_updates_with_audit(client, db_session):
    await _seed_prefectures(db_session)
    resp = await client.put(f"{_URL}/domestic", json=_domestic())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["region"] == "domestic"
    assert body["company_name"] == "Domestic Co"
    assert body["prefecture_code"] == "13"

    resp = await client.put(f"{_URL}/domestic", json=_domestic(company_name="Domestic Co 2"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["company_name"] == "Domestic Co 2"
    assert await _count_rows(db_session) == 1

    rows = (await db_session.execute(text(
        "SELECT action, old_data, new_data FROM audit_logs "
        "WHERE table_name = 'tenant_issuer_profiles' ORDER BY id"
    ))).all()
    assert [r[0] for r in rows] == ["create", "update"]
    assert rows[0][1] is None
    assert json.loads(rows[0][2])["company_name"] == "Domestic Co"
    assert json.loads(rows[1][1])["company_name"] == "Domestic Co"
    assert json.loads(rows[1][2])["company_name"] == "Domestic Co 2"


async def test_put_normalizes_spaces_case_and_empty(client, db_session):
    await _seed_prefectures(db_session)
    resp = await client.put(
        f"{_URL}/domestic",
        json=_domestic(company_name="  Domestic Co  ", country_code="jp", email=""),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["company_name"] == "Domestic Co"
    assert body["country_code"] == "JP"
    assert body["email"] is None


async def test_put_rejects_japan_rules_by_field(client, db_session):
    await _seed_prefectures(db_session)
    resp = await client.put(
        f"{_URL}/domestic",
        json=_domestic(postal_code="100-0001", phone="+81312345678", prefecture_code=None, state_region="Tokyo"),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["fields"] == {
        "postal_code": "postal_jp",
        "phone": "phone_jp",
        "prefecture_code": "required",
        "state_region": "must_be_empty",
    }
    assert await _count_rows(db_session) == 0


async def test_put_rejects_foreign_rules_by_field(client, db_session):
    await _seed_prefectures(db_session)
    resp = await client.put(
        f"{_URL}/overseas",
        json=_overseas(postal_code="9410#", phone="0312345678", prefecture_code="13"),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["fields"] == {
        "postal_code": "postal_foreign",
        "phone": "phone_foreign",
        "prefecture_code": "must_be_empty",
    }


async def test_put_rejects_missing_required_fields(client):
    resp = await client.put(
        f"{_URL}/overseas",
        json=_overseas(company_name="  ", country_code=None, city="", address1=None, phone=None),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["fields"] == {
        "company_name": "required",
        "country_code": "required",
        "city": "required",
        "address1": "required",
    }


async def test_put_rejects_unknown_codes(client, db_session):
    await _seed_prefectures(db_session)
    resp = await client.put(f"{_URL}/domestic", json=_domestic(prefecture_code="99"))
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["fields"] == {"prefecture_code": "unknown_code"}
    resp = await client.put(f"{_URL}/overseas", json=_overseas(country_code="ZZ"))
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["fields"] == {"country_code": "unknown_code"}


async def test_put_registration_number_rules(client, db_session):
    await _seed_prefectures(db_session)
    resp = await client.put(f"{_URL}/domestic", json=_domestic(is_invoice_registered=True, registration_number="T123"))
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["fields"] == {"registration_number": "registration_number"}
    resp = await client.put(f"{_URL}/domestic", json=_domestic(is_invoice_registered=True, registration_number=None))
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["fields"] == {"registration_number": "required"}

    resp = await client.put(f"{_URL}/domestic", json=_domestic(is_invoice_registered=True, registration_number=_REG_NO))
    assert resp.status_code == 200, resp.text
    assert resp.json()["registration_number"] == _REG_NO

    resp = await client.put(f"{_URL}/domestic", json=_domestic(is_invoice_registered=False, registration_number=_REG_NO))
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_invoice_registered"] is False
    assert resp.json()["registration_number"] is None
    row = (await db_session.execute(text(
        "SELECT registration_number FROM tenant_issuer_profiles WHERE region = 'domestic'"
    ))).first()
    assert row[0] is None


async def test_saving_one_region_keeps_the_other(client, db_session):
    await _seed_prefectures(db_session)
    assert (await client.put(f"{_URL}/domestic", json=_domestic())).status_code == 200
    assert (await client.put(f"{_URL}/overseas", json=_overseas())).status_code == 200
    assert (await client.put(f"{_URL}/domestic", json=_domestic(company_name="Domestic Co 3"))).status_code == 200

    body = (await client.get(_URL)).json()
    assert body["domestic"]["company_name"] == "Domestic Co 3"
    assert body["overseas"]["company_name"] == "Overseas Co"
    assert body["overseas"]["state_region"] == "CA"


async def test_other_tenant_rows_are_not_read(client, db_session):
    await _seed_prefectures(db_session)
    await db_session.execute(text(
        "INSERT INTO tenant_issuer_profiles (tenant_id, region, company_name, country_code, city, address1) "
        "VALUES (1000, 'domestic', 'Other Tenant Co', 'US', 'X', 'Y')"
    ))
    await db_session.commit()

    assert (await client.get(_URL)).json()["domestic"] is None
    assert (await client.put(f"{_URL}/domestic", json=_domestic())).status_code == 200
    rows = (await db_session.execute(text(
        "SELECT tenant_id, company_name FROM tenant_issuer_profiles WHERE region = 'domestic' ORDER BY tenant_id"
    ))).all()
    assert [tuple(r) for r in rows] == [(999, "Domestic Co"), (1000, "Other Tenant Co")]


async def test_unknown_region_is_422(client):
    resp = await client.put(f"{_URL}/x", json=_overseas())
    assert resp.status_code == 422


async def test_prefectures_list_comes_from_the_seed_in_order(client, db_session):
    rows = await _seed_prefectures(db_session)
    assert len(rows) == 47
    resp = await client.get("/api/v1/prefectures")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    expected = sorted(rows, key=lambda r: (int(r[3]), r[0]))
    assert [(p["code"], p["name_ja"], p["name_en"], p["sort_order"]) for p in body] == [
        (c, j, e, int(s)) for c, j, e, s in expected
    ]
