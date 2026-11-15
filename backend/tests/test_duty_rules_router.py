"""関税の額の決まりの入口の試験（invoice-create-portfolio 便B・K18・K20）。

中身の SQL は test_duty_rules_pg.py で本物の PostgreSQL に当てる。ここでは入口の形・権限・監査の記録・失敗の形を見る。
"""
from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.services import duty_rules as svc

BASE = "/api/v1/admin/duty-rules"

_RULE = {
    "id": 7,
    "destination_country_code": "US",
    "carrier": "fedex",
    "label": "US DDP FedEx",
    "effective_from": datetime.date(2026, 1, 1),
    "effective_to": None,
    "source_url": "https://www.fedex.com/en-us/billing/duty-tax.html",
    "note": None,
    "is_active": True,
    "created_at": None,
    "updated_at": None,
    "components": [
        {"id": 1, "sort_order": 0, "label": "Duty", "base": "subtotal", "rate_pct": "15.0000",
         "min_amount": None, "max_amount": None, "amount_currency": None},
    ],
}

_BODY = {
    "destination_country_code": " us ",
    "carrier": " FedEx ",
    "label": "US DDP FedEx",
    "effective_from": "2026-01-01",
    "effective_to": "",
    "source_url": "https://www.fedex.com/en-us/billing/duty-tax.html",
    "components": [{"label": "Duty", "base": "subtotal", "rate_pct": "15"}],
}


@pytest.fixture
def audit():
    mock = AsyncMock()
    with patch("app.routers.duty_rules.record_audit_log", mock):
        yield mock


@pytest.mark.asyncio
async def test_list_returns_rules(client, audit):
    with patch.object(svc, "list_duty_rules", AsyncMock(return_value=[_RULE])):
        res = await client.get(BASE)
    assert res.status_code == 200
    assert res.json()[0]["carrier"] == "fedex"
    assert res.json()[0]["components"][0]["rate_pct"] == "15.0000"
    audit.assert_not_called()


@pytest.mark.asyncio
async def test_options_returns_incoterms_currencies_and_bases(client, audit):
    with patch.object(svc, "get_duty_incoterms", AsyncMock(return_value="DDP")), \
            patch("app.routers.duty_rules.list_invoice_currencies", AsyncMock(return_value=["JPY", "USD"])):
        res = await client.get(f"{BASE}/options")
    assert res.status_code == 200
    assert res.json() == {
        "duty_incoterms": "DDP",
        "currencies": ["JPY", "USD"],
        "bases": ["subtotal", "subtotal_shipping", "subtotal_shipping_prior"],
    }


@pytest.mark.asyncio
async def test_options_404_when_tenant_settings_missing(client, audit):
    with patch.object(svc, "get_duty_incoterms", AsyncMock(return_value=None)):
        res = await client.get(f"{BASE}/options")
    assert res.status_code == 404
    assert res.json()["detail"] == {"code": "tenant_settings_missing"}


@pytest.mark.asyncio
async def test_create_normalizes_and_records_audit(client, audit):
    create = AsyncMock(return_value=_RULE)
    with patch.object(svc, "create_duty_rule", create):
        res = await client.post(BASE, json=_BODY)
    assert res.status_code == 201
    body = create.await_args.args[2]
    assert body.destination_country_code == "US"
    assert body.carrier == "fedex"
    assert body.effective_to is None
    assert audit.await_count == 1
    assert audit.await_args.args[3] == "create"
    assert audit.await_args.args[4] == "tenant_duty_rules"


@pytest.mark.asyncio
async def test_create_blank_carrier_becomes_null(client, audit):
    create = AsyncMock(return_value={**_RULE, "carrier": None})
    with patch.object(svc, "create_duty_rule", create):
        res = await client.post(BASE, json={**_BODY, "carrier": "   "})
    assert res.status_code == 201
    assert create.await_args.args[2].carrier is None


@pytest.mark.asyncio
async def test_create_overlap_returns_409_with_ids(client, audit):
    with patch.object(svc, "create_duty_rule", AsyncMock(side_effect=svc.DutyRuleOverlap([3, 5]))):
        res = await client.post(BASE, json=_BODY)
    assert res.status_code == 409
    assert res.json()["detail"] == {"code": "duty_rule_overlap", "rule_ids": [3, 5]}
    audit.assert_not_called()


@pytest.mark.asyncio
async def test_create_unknown_country_returns_422(client, audit):
    with patch.object(svc, "create_duty_rule", AsyncMock(side_effect=svc.DutyCountryInvalid())):
        res = await client.post(BASE, json=_BODY)
    assert res.status_code == 422
    assert res.json()["detail"] == {"code": "duty_country"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "patch_body",
    [
        {"source_url": "fedex.com/duty"},
        {"source_url": ""},
        {"components": []},
        {"effective_from": "2026-02-01", "effective_to": "2026-01-01"},
        {"components": [{"label": "Duty", "base": "total", "rate_pct": "1"}]},
        {"components": [{"label": "Fee", "base": "subtotal", "rate_pct": "0", "min_amount": "10"}]},
        {"components": [{"label": "Fee", "base": "subtotal", "rate_pct": "0", "min_amount": "10",
                         "max_amount": "5", "amount_currency": "USD"}]},
    ],
)
async def test_create_rejects_bad_input(client, audit, patch_body):
    create = AsyncMock(return_value=_RULE)
    with patch.object(svc, "create_duty_rule", create):
        res = await client.post(BASE, json={**_BODY, **patch_body})
    assert res.status_code == 422
    create.assert_not_called()
    audit.assert_not_called()


@pytest.mark.asyncio
async def test_update_records_before_and_after(client, audit):
    after = {**_RULE, "label": "US DDP FedEx 2026"}
    with patch.object(svc, "update_duty_rule", AsyncMock(return_value=(_RULE, after))):
        res = await client.put(f"{BASE}/7", json=_BODY)
    assert res.status_code == 200
    assert res.json()["label"] == "US DDP FedEx 2026"
    assert audit.await_count == 1
    kwargs = audit.await_args.kwargs
    assert audit.await_args.args[3] == "update"
    assert kwargs["old_data"]["label"] == "US DDP FedEx"
    assert kwargs["new_data"]["label"] == "US DDP FedEx 2026"


@pytest.mark.asyncio
async def test_update_not_found_returns_404(client, audit):
    with patch.object(svc, "update_duty_rule", AsyncMock(side_effect=svc.DutyRuleNotFound())):
        res = await client.put(f"{BASE}/99", json=_BODY)
    assert res.status_code == 404
    assert res.json()["detail"] == {"code": "duty_rule_not_found"}
    audit.assert_not_called()


@pytest.mark.asyncio
async def test_update_overlap_returns_409(client, audit):
    with patch.object(svc, "update_duty_rule", AsyncMock(side_effect=svc.DutyRuleOverlap([8]))):
        res = await client.put(f"{BASE}/7", json=_BODY)
    assert res.status_code == 409
    assert res.json()["detail"]["rule_ids"] == [8]


@pytest.mark.asyncio
async def test_delete_returns_204_and_records_audit(client, audit):
    with patch.object(svc, "delete_duty_rule", AsyncMock(return_value=_RULE)):
        res = await client.delete(f"{BASE}/7")
    assert res.status_code == 204
    assert audit.await_count == 1
    assert audit.await_args.args[3] == "delete"
    assert audit.await_args.kwargs["old_data"]["id"] == 7


@pytest.mark.asyncio
async def test_delete_not_found_returns_404(client, audit):
    with patch.object(svc, "delete_duty_rule", AsyncMock(side_effect=svc.DutyRuleNotFound())):
        res = await client.delete(f"{BASE}/99")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_view_only_can_read_but_not_write(client, audit):
    view_only = AsyncMock(return_value={"tenant.profile.view"})
    create = AsyncMock(return_value=_RULE)
    with patch("app.auth.dependencies.load_user_permissions", new=view_only), \
            patch.object(svc, "list_duty_rules", AsyncMock(return_value=[])), \
            patch.object(svc, "create_duty_rule", create), \
            patch.object(svc, "delete_duty_rule", AsyncMock(return_value=_RULE)):
        assert (await client.get(BASE)).status_code == 200
        assert (await client.post(BASE, json=_BODY)).status_code == 403
        assert (await client.put(f"{BASE}/7", json=_BODY)).status_code == 403
        assert (await client.delete(f"{BASE}/7")).status_code == 403
    create.assert_not_called()
    audit.assert_not_called()


def test_duty_bases_match_migration_check():
    """基準の並びの正本（DutyBase）が表の CHECK と同じ3つであること。"""
    from pathlib import Path

    from app.schemas.duty_rules import DUTY_BASES

    root = Path(__file__).resolve().parents[2]
    sql = (root / "migrations" / "20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql").read_text(
        encoding="utf-8"
    )
    for base in DUTY_BASES:
        assert f"'{base}'" in sql
    assert DUTY_BASES == ("subtotal", "subtotal_shipping", "subtotal_shipping_prior")
