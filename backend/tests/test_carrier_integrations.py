"""配送キャリア接続テスト（carrier_credentials サービス + integrations ルーター）のテスト。

httpx と DB アクセスはモックする。
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services import carrier_credentials as svc


# ─────────────────────────────────────────────────────────────
# is_valid_carrier
# ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "carrier,expected",
    [("fedex", True), ("dhl", True), ("ups", True), ("yamato", False), ("", False)],
)
def test_is_valid_carrier(carrier, expected):
    assert svc.is_valid_carrier(carrier) is expected


# ─────────────────────────────────────────────────────────────
# test_connection（httpx モック）
# ─────────────────────────────────────────────────────────────
def _resp(status_code, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.json = MagicMock(return_value=json_body or {})
    return r


def test_fedex_token_success():
    with patch.object(svc.httpx, "post", return_value=_resp(200, {"access_token": "tok"})):
        out = svc.test_connection("fedex", "sandbox", "id", "secret")
    assert out["ok"] is True
    assert out["status_code"] == 200


def test_fedex_token_unauthorized():
    with patch.object(svc.httpx, "post", return_value=_resp(401, {"errors": []})):
        out = svc.test_connection("fedex", "sandbox", "id", "bad")
    assert out["ok"] is False
    assert out["status_code"] == 401
    assert "認証情報" in out["message"]


def test_ups_token_success():
    with patch.object(svc.httpx, "post", return_value=_resp(200, {"access_token": "t"})) as p:
        out = svc.test_connection("ups", "production", "id", "secret")
    assert out["ok"] is True
    # UPS は Basic ヘッダを使う
    _, kwargs = p.call_args
    assert kwargs["headers"]["Authorization"].startswith("Basic ")


def test_dhl_auth_ok_on_400():
    # 400（パラメータ不足だが認証は通過）→ 疎通OK
    with patch.object(svc.httpx, "get", return_value=_resp(400)):
        out = svc.test_connection("dhl", "sandbox", "key", "secret")
    assert out["ok"] is True


def test_dhl_auth_ng_on_401():
    with patch.object(svc.httpx, "get", return_value=_resp(401)):
        out = svc.test_connection("dhl", "sandbox", "key", "bad")
    assert out["ok"] is False
    assert out["status_code"] == 401


def test_connection_network_error():
    import httpx as real_httpx

    with patch.object(svc.httpx, "post", side_effect=real_httpx.ConnectError("boom")):
        out = svc.test_connection("fedex", "sandbox", "id", "secret")
    assert out["ok"] is False
    assert out["status_code"] is None


# ─────────────────────────────────────────────────────────────
# エンドポイント（DB/HTTP はモック）
# ─────────────────────────────────────────────────────────────
async def test_status_endpoint(client, monkeypatch):
    async def _status(db, tid, carrier):
        return {"configured": True, "environment": "sandbox"}

    monkeypatch.setattr(svc, "get_status", _status)
    resp = await client.get("/api/v1/integrations/carriers/fedex/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["carrier"] == "fedex"
    assert body["configured"] is True


async def test_status_invalid_carrier_404(client):
    resp = await client.get("/api/v1/integrations/carriers/yamato/status")
    assert resp.status_code == 404


async def test_save_credentials(client, monkeypatch):
    calls = {}

    async def _save(db, tid, carrier, cid, csec, env, uid):
        calls["carrier"] = carrier

    monkeypatch.setattr(svc, "save_credentials", _save)
    resp = await client.put(
        "/api/v1/integrations/carriers/ups/credentials",
        json={"client_id": "x", "client_secret": "y", "environment": "sandbox"},
    )
    assert resp.status_code == 204
    assert calls["carrier"] == "ups"


async def test_save_credentials_missing_fields(client):
    resp = await client.put(
        "/api/v1/integrations/carriers/ups/credentials",
        json={"client_id": "", "client_secret": "", "environment": "sandbox"},
    )
    assert resp.status_code == 400


async def test_test_connection_endpoint(client, monkeypatch):
    async def _creds(db, tid, carrier):
        return {"client_id": "x", "client_secret": "y", "environment": "sandbox"}

    monkeypatch.setattr(svc, "get_credentials", _creds)
    monkeypatch.setattr(svc, "test_connection", lambda *a, **k: {"ok": True, "status_code": 200, "message": "認証成功"})
    resp = await client.post("/api/v1/integrations/carriers/fedex/test-connection", json={})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


async def test_test_connection_not_configured(client, monkeypatch):
    async def _none(db, tid, carrier):
        return None

    monkeypatch.setattr(svc, "get_credentials", _none)
    resp = await client.post("/api/v1/integrations/carriers/dhl/test-connection", json={})
    assert resp.status_code == 400
