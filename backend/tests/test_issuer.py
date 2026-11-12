"""請求書・見積書の発行元の読み方の試験（ADR-1061 便2-2c2a。design.md §3-4・A40 の一部）。

- 発行元の地域は、請求書を作るときの請求先の国で決まり、あとから会社の住所を変えても変わらない。
- 請求先の国が無いときは作らずに 422 "bill_to_country" を返す。
- 発行元の表にその地域の行があればそれだけを読み、無いときだけ旧来の会社情報の表を読む。
- 登録番号は請求書だけに載り、見積書には載らない。
- 都道府県名・国名は試験に書かず、正本（都道府県の seed ファイル・国の表）から読む。
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pytest
from sqlalchemy import text

from app.services.invoice_renderer import render_invoice_pdf, render_quote_pdf
from app.services.issuer import decide_issuer_region, format_issuer_address, get_issuer
from tests.test_invoices import _create_approved_quote, _create_company_contact

_ROOT = Path(__file__).resolve().parents[2]
_APP = _ROOT / "backend" / "app"
_PREF_SEED = _ROOT / "docs" / "handoff" / "viewer-contract-stage" / "data" / "prefectures.sql"
_PREF_ROW_RE = re.compile(r"^\s*\('(\d{2})',\s*'([^']+)',\s*'([^']+)',\s*(\d+)\),?$", re.M)
_A40_RE = re.compile(
    r'\{[A-Za-z_]+\}\.tenant_profile\b|"tenant_profile"\s*\)|\bFROM\s+tenant_profile\b'
    r"|\bINTO\s+tenant_profile\b|\bUPDATE\s+tenant_profile\b",
    re.I,
)
_REG_NO = "T1234567890123"


def _extract_text(pdf_bytes: bytes) -> str:
    try:
        from pdfminer.high_level import extract_text
    except ImportError:
        pytest.skip("pdfminer.six 未インストール (requirements.txt 適用要)")
    return extract_text(io.BytesIO(pdf_bytes))


def _invoice_data() -> dict:
    return {
        "invoice_code": "IN-0001-01",
        "issued_at": "2026-11-12T00:00:00",
        "ship_to_snapshot": None,
        "bill_to_snapshot": None,
        "items": [{"name_en": "Item", "quantity": 1, "unit_price": 10.0, "subtotal": 10.0, "hs_code": None}],
        "subtotal": 10.0,
        "shipping_fee": 0.0,
        "tax_amount": 0.0,
        "total_amount": 10.0,
        "currency": "USD",
        "duty_amount": None,
        "fx_rate_snapshot": None,
        "notes": None,
    }


def _quote_data() -> dict:
    return {
        "quote_code": "QT-0001",
        "created_at": "2026-11-12T00:00:00",
        "ship_to_snapshot": None,
        "bill_to_snapshot": None,
        "items": [{"name_en": "Item", "quantity": 1, "unit_price": 10.0, "subtotal": 10.0, "hs_code": None}],
        "subtotal": 10.0,
        "shipping_fee": 0.0,
        "tax_amount": 0.0,
        "total_amount": 10.0,
        "currency": "USD",
        "notes": None,
    }


async def _insert_issuer(db, region: str, *, company_name: str, email, country_code: str,
                         prefecture_code=None, postal_code=None, registered: bool = False,
                         registration_number=None):
    await db.execute(
        text(
            "INSERT INTO tenant_issuer_profiles (tenant_id, region, company_name, email, website,"
            " country_code, postal_code, prefecture_code, state_region, city, address1, address2,"
            " phone, is_invoice_registered, registration_number)"
            " VALUES (999, :region, :company_name, :email, NULL, :country_code, :postal_code,"
            " :prefecture_code, NULL, :city, :address1, NULL, :phone, :registered, :registration_number)"
        ),
        {
            "region": region,
            "company_name": company_name,
            "email": email,
            "country_code": country_code,
            "postal_code": postal_code,
            "prefecture_code": prefecture_code,
            "city": "CityA",
            "address1": "Street1",
            "phone": "0312345678",
            "registered": registered,
            "registration_number": registration_number,
        },
    )


async def _insert_legacy(db):
    await db.execute(
        text(
            "INSERT INTO tenant_profile (company_name, company_name_en, address, phone, email, website)"
            " VALUES (:n, :ne, :a, :p, :e, :w)"
        ),
        {"n": "Legacy Co", "ne": "Legacy Co EN", "a": "Legacy Address", "p": "0000",
         "e": "legacy@example.com", "w": "legacy.example.com"},
    )


async def _company_with_billing(client, name: str, country):
    """既定の請求先の住所を持つ会社（country=None なら国の無い請求先・"none" なら請求先なし）"""
    company_id, contact_id = await _create_company_contact(client, name, country=None)
    if country != "none":
        address = {"address_type": "billing", "is_default": True}
        if country is not None:
            address["country_code"] = country
        res = await client.patch(f"/api/v1/companies/{company_id}", json={"addresses": [address]})
        assert res.status_code == 200, res.text
    return company_id, contact_id


async def _invoice_count(db) -> int:
    return (await db.execute(text("SELECT COUNT(*) FROM invoices"))).scalar_one()


# ---------------------------------------------------------------------------
# 単体: 地域の決め方・住所の書き方
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("snapshot", "expected"),
    [
        ({"country": "JP"}, "domestic"),
        ({"country": "jp"}, "domestic"),
        ({"country": " jp "}, "domestic"),
        ({"country": "US"}, "overseas"),
        (None, None),
        ({}, None),
        ({"country": None}, None),
        ({"country": ""}, None),
    ],
)
def test_decide_issuer_region(snapshot, expected):
    assert decide_issuer_region(snapshot) == expected


def test_format_issuer_address_jp():
    row = {"country_code": "JP", "postal_code": "1000001", "city": "C", "address1": "A1", "address2": None}
    assert format_issuer_address(row, "P", None) == "〒100-0001 PCA1"
    row["address2"] = "B2"
    assert format_issuer_address(row, "P", None) == "〒100-0001 PCA1 B2"


def test_format_issuer_address_overseas():
    row = {"country_code": "US", "postal_code": "94105", "state_region": "CA", "city": "SF",
           "address1": "1 Main St", "address2": None}
    assert format_issuer_address(row, None, "Countryname") == "1 Main St, SF, CA 94105, Countryname"


async def test_get_issuer_rejects_unknown_region(db_session):
    with pytest.raises(ValueError):
        await get_issuer(db_session, 999, "x")


# ---------------------------------------------------------------------------
# 単体: 印刷（登録番号は請求書だけ）
# ---------------------------------------------------------------------------

def test_invoice_pdf_prints_registration_number_only_when_set():
    with_no = _extract_text(render_invoice_pdf(_invoice_data(), {"name": "Issuer A", "registration_number": _REG_NO}))
    assert "Registration No.: " + _REG_NO in with_no
    without = _extract_text(render_invoice_pdf(_invoice_data(), {"name": "Issuer A", "registration_number": None}))
    assert "Registration No." not in without


def test_quote_pdf_never_prints_registration_number():
    out = _extract_text(render_quote_pdf(_quote_data(), {"name": "Issuer A", "registration_number": _REG_NO}))
    assert "Issuer A" in out
    assert _REG_NO not in out


# ---------------------------------------------------------------------------
# 発行元の読み方（DB）
# ---------------------------------------------------------------------------

async def test_get_issuer_reads_region_row_with_prefecture_and_registration(db_session):
    code, name_ja, name_en, sort_order = _PREF_ROW_RE.findall(_PREF_SEED.read_text("utf-8"))[12]
    assert code == "13"
    await db_session.execute(
        text("INSERT OR IGNORE INTO prefectures (code, name_ja, name_en, sort_order) VALUES (:c, :j, :e, :s)"),
        {"c": code, "j": name_ja, "e": name_en, "s": int(sort_order)},
    )
    await _insert_legacy(db_session)
    await _insert_issuer(db_session, "domestic", company_name="Domestic Issuer", email=None,
                         country_code="JP", prefecture_code="13", postal_code="1000001",
                         registered=True, registration_number=_REG_NO)
    issuer = await get_issuer(db_session, 999, "domestic")
    assert issuer["name"] == "Domestic Issuer"
    assert issuer["address"] == f"〒100-0001 {name_ja}CityAStreet1"
    assert issuer["registration_number"] == _REG_NO
    assert issuer["legacy"] is False
    # 行がある地域では空の欄を旧来の表で埋めない
    assert issuer["email"] == ""
    pdf = _extract_text(render_invoice_pdf(_invoice_data(), issuer))
    assert "Domestic Issuer" in pdf
    assert _REG_NO in pdf
    assert "legacy@example.com" not in pdf


async def test_get_issuer_registration_hidden_when_not_registered(db_session):
    await _insert_issuer(db_session, "domestic", company_name="Domestic Issuer", email="d@example.com",
                         country_code="JP", postal_code="1000001",
                         registered=False, registration_number=_REG_NO)
    issuer = await get_issuer(db_session, 999, "domestic")
    assert issuer["registration_number"] is None


async def test_get_issuer_overseas_uses_country_table_name(db_session):
    country_name = (await db_session.execute(
        text("SELECT name FROM countries WHERE code = 'US'")
    )).scalar_one()
    await _insert_issuer(db_session, "overseas", company_name="Overseas Issuer", email="o@example.com",
                         country_code="US", postal_code="94105")
    issuer = await get_issuer(db_session, 999, "overseas")
    assert issuer["name"] == "Overseas Issuer"
    assert issuer["address"].endswith(country_name)
    assert issuer["registration_number"] is None
    # 見積書は海外用の行を使う（invoices.py の呼び出しは下のソース検査で確かめる）
    out = _extract_text(render_quote_pdf(_quote_data(), issuer))
    assert "Overseas Issuer" in out


async def test_get_issuer_falls_back_to_legacy_only_without_row(db_session):
    await _insert_legacy(db_session)
    await _insert_issuer(db_session, "domestic", company_name="Domestic Issuer", email=None,
                         country_code="JP", postal_code="1000001",
                         registered=True, registration_number=_REG_NO)
    overseas = await get_issuer(db_session, 999, "overseas")
    assert overseas["name"] == "Legacy Co"
    assert overseas["email"] == "legacy@example.com"
    assert overseas["registration_number"] is None
    assert overseas["legacy"] is True
    pdf = _extract_text(render_invoice_pdf(_invoice_data(), overseas))
    assert "Legacy Co" in pdf
    assert _REG_NO not in pdf


async def test_get_issuer_without_any_row_returns_blank(db_session):
    issuer = await get_issuer(db_session, 999, "domestic")
    assert issuer == {"name": "", "address": "", "phone": "", "email": "", "website": "",
                      "registration_number": None, "legacy": True}


# ---------------------------------------------------------------------------
# 請求書を作るときの地域の決定（2つの作り方）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(("country", "expected"), [("JP", "domestic"), ("jp", "domestic"), ("US", "overseas")])
async def test_direct_create_stores_region(client, country, expected):
    company_id, contact_id = await _company_with_billing(client, f"地域{country}", country)
    res = await client.post("/api/v1/invoices", json={
        "company_id": company_id, "contact_id": contact_id,
        "items": [{"product_name": "P", "quantity": 1, "unit_price": "10.00"}],
    })
    assert res.status_code == 201, res.text
    assert res.json()["issuer_region"] == expected


@pytest.mark.parametrize(("country", "expected"), [("JP", "domestic"), ("US", "overseas")])
async def test_from_quote_stores_region(client, country, expected):
    company_id, contact_id = await _company_with_billing(client, f"見積地域{country}", country)
    quote_id = await _create_approved_quote(client, company_id, contact_id)
    res = await client.post(f"/api/v1/invoices/from-quote/{quote_id}")
    assert res.status_code == 201, res.text
    assert res.json()["issuer_region"] == expected


@pytest.mark.parametrize("country", ["none", None])
async def test_direct_create_without_bill_to_country_is_422(client, db_session, country):
    company_id, contact_id = await _company_with_billing(client, "国なし直接", country)
    before = await _invoice_count(db_session)
    res = await client.post("/api/v1/invoices", json={
        "company_id": company_id, "contact_id": contact_id,
        "items": [{"product_name": "P", "quantity": 1, "unit_price": "10.00"}],
    })
    assert res.status_code == 422, res.text
    assert res.json()["detail"] == "bill_to_country"
    assert await _invoice_count(db_session) == before


@pytest.mark.parametrize("country", ["none", None])
async def test_from_quote_without_bill_to_country_is_422(client, db_session, country):
    company_id, contact_id = await _company_with_billing(client, "国なし見積", country)
    quote_id = await _create_approved_quote(client, company_id, contact_id)
    before = await _invoice_count(db_session)
    res = await client.post(f"/api/v1/invoices/from-quote/{quote_id}")
    assert res.status_code == 422, res.text
    assert res.json()["detail"] == "bill_to_country"
    assert await _invoice_count(db_session) == before


async def test_region_does_not_follow_later_address_change(client):
    company_id, contact_id = await _company_with_billing(client, "あとで変える会社", "JP")
    res = await client.post("/api/v1/invoices", json={
        "company_id": company_id, "contact_id": contact_id,
        "items": [{"product_name": "P", "quantity": 1, "unit_price": "10.00"}],
    })
    assert res.status_code == 201, res.text
    invoice_id = res.json()["id"]
    upd = await client.patch(f"/api/v1/companies/{company_id}", json={
        "addresses": [{"address_type": "billing", "country_code": "US", "is_default": True}],
    })
    assert upd.status_code == 200, upd.text
    got = await client.get(f"/api/v1/invoices/{invoice_id}")
    assert got.status_code == 200
    assert got.json()["issuer_region"] == "domestic"


# ---------------------------------------------------------------------------
# ソース検査（A40: 旧来の会社情報の表を読むのは決まった場所だけ）
# ---------------------------------------------------------------------------

def test_a40_tenant_profile_readers_are_limited():
    hits: dict[str, int] = {}
    for p in sorted(_APP.rglob("*.py")):
        n = sum(1 for line in p.read_text("utf-8").splitlines() if _A40_RE.search(line))
        if n:
            hits[str(p.relative_to(_APP))] = n
    assert set(hits) == {
        "routers/tenant_profile.py",
        "services/tenant.py",
        "services/po_renderer.py",
        "services/label_validation.py",
        "services/issuer.py",
    }
    assert hits["services/issuer.py"] == 1


def test_invoice_router_reads_issuer_through_get_issuer():
    src = (_APP / "routers" / "invoices.py").read_text("utf-8")
    assert src.count('get_issuer(db, tenant_id, row["issuer_region"] or "overseas")') == 2
    assert src.count('get_issuer(db, tenant_id, "overseas")') == 1
    assert "_fetch_tenant_profile" not in src
    assert "_get_tenant_schema" not in src
    assert src.count('detail="bill_to_country"') == 2
