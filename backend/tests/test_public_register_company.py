"""
ADR-097 §3: 公開の登録フォーム送信で、会社が無いリードには会社を自動で作る。
"""
import pytest
from sqlalchemy import text

from app.services.registration_token import _compute_hash
from tests.helpers_txn import create_company, create_lead


@pytest.fixture(autouse=True)
def _sqlite_token_shims(monkeypatch, db_session):
    """試験の SQLite では expires_at が文字列・NOW() が無いため、トークンの検証と使用済み印だけ差し替える。
    会社作り以降の処理（register_customer 本体）は本物のまま動かす。"""

    async def fake_verify(db, raw_token):
        row = (
            await db.execute(
                text("SELECT id, tenant_id, lead_id, type FROM registration_tokens WHERE token_hash = :h"),
                {"h": _compute_hash(raw_token)},
            )
        ).mappings().first()
        return dict(row) if row else None

    async def fake_mark_used(db, token_id):
        await db.execute(
            text("UPDATE registration_tokens SET used_at = CURRENT_TIMESTAMP WHERE id = :id"), {"id": token_id}
        )

    monkeypatch.setattr("app.routers.registration_tokens.verify_token", fake_verify)
    monkeypatch.setattr("app.routers.registration_tokens.mark_token_used", fake_mark_used)


async def _issue_token(client, lead_id: int) -> str:
    r = await client.post("/api/v1/registration-tokens", json={"lead_id": lead_id, "type": "register"})
    assert r.status_code in (200, 201), r.text
    return r.json()["token"]


def _form(token: str) -> dict:
    return {
        "token": token,
        "addresses": [
            {
                "address_type": "billing",
                "is_default": True,
                "name": "Acme Billing",
                "address_line_1": "1 Main St",
                "country_code": "US",
            },
            {
                "address_type": "delivery",
                "is_default": True,
                "name": "Acme Delivery",
                "address_line_1": "2 Dock Rd",
                "country_code": "US",
            },
        ],
        "billing_display_name": "Acme Billing",
        "contact_name": "Taro",
        "contact_email": "taro@example.com",
    }


async def _count(db_session, sql: str, **params) -> int:
    return (await db_session.execute(text(sql), params)).scalar_one()


class TestPublicRegisterCreatesCompany:
    async def test_creates_company_when_lead_has_none(self, client, db_session):
        lead_id = await create_lead(client, "顧客太郎")
        await db_session.execute(
            text("UPDATE leads SET company_name = :n WHERE id = :id"), {"n": "Acme Inc", "id": lead_id}
        )
        await db_session.commit()
        token = await _issue_token(client, lead_id)

        res = await client.post("/api/v1/public/register", json=_form(token))
        assert res.status_code == 200, res.text

        rows = (
            await db_session.execute(
                text("SELECT id, name, company_code FROM companies WHERE lead_id = :l"), {"l": lead_id}
            )
        ).all()
        assert len(rows) == 1
        cid, name, code = rows[0]
        assert name == "Acme Inc"
        assert code.startswith("CO-") and not code.startswith("CO-PEND")
        assert await _count(db_session, "SELECT COUNT(*) FROM company_addresses WHERE company_id = :c", c=cid) == 2
        assert await _count(db_session, "SELECT COUNT(*) FROM contacts WHERE company_id = :c", c=cid) == 1

    async def test_existing_company_is_reused(self, client, db_session):
        lead_id = await create_lead(client, "既存顧客")
        cid = await create_company(client, lead_id)
        token = await _issue_token(client, lead_id)

        res = await client.post("/api/v1/public/register", json=_form(token))
        assert res.status_code == 200, res.text

        assert await _count(db_session, "SELECT COUNT(*) FROM companies WHERE lead_id = :l", l=lead_id) == 1
        assert await _count(db_session, "SELECT COUNT(*) FROM company_addresses WHERE company_id = :c", c=cid) == 2
        assert await _count(db_session, "SELECT COUNT(*) FROM contacts WHERE company_id = :c", c=cid) == 1

    async def test_name_falls_back_to_customer_name(self, client, db_session):
        lead_id = await create_lead(client, "顧客花子")
        await db_session.execute(text("UPDATE leads SET company_name = '' WHERE id = :id"), {"id": lead_id})
        await db_session.commit()
        token = await _issue_token(client, lead_id)

        res = await client.post("/api/v1/public/register", json=_form(token))
        assert res.status_code == 200, res.text

        name = (
            await db_session.execute(text("SELECT name FROM companies WHERE lead_id = :l"), {"l": lead_id})
        ).scalar_one()
        assert name == "顧客花子"
