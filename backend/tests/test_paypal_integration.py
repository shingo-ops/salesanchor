"""PayPal 決済連携（paypal_payments サービス + integrations ルーター）のテスト。

httpx と DB アクセスはモックする。
"""

from unittest.mock import MagicMock, patch

from app.services import paypal_payments as svc


def _resp(status_code, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.json = MagicMock(return_value=json_body or {})
    return r


# ─────────────────────────────────────────────────────────────
# test_connection（httpx モック）
# ─────────────────────────────────────────────────────────────
def test_token_success():
    with patch.object(svc.httpx, "post", return_value=_resp(200, {"access_token": "tok"})) as p:
        out = svc.test_connection("sandbox", "id", "secret")
    assert out["ok"] is True
    assert out["status_code"] == 200
    # sandbox の base URL を使う
    args, _ = p.call_args
    assert "api-m.sandbox.paypal.com" in args[0]


def test_token_live_base_url():
    with patch.object(svc.httpx, "post", return_value=_resp(200, {"access_token": "t"})) as p:
        svc.test_connection("live", "id", "secret")
    args, _ = p.call_args
    assert "api-m.paypal.com" in args[0]


def test_token_unauthorized():
    with patch.object(svc.httpx, "post", return_value=_resp(401, {"error": "invalid_client"})):
        out = svc.test_connection("sandbox", "id", "bad")
    assert out["ok"] is False
    assert out["status_code"] == 401
    assert "認証情報" in out["message"]


def test_connection_network_error():
    import httpx as real_httpx

    with patch.object(svc.httpx, "post", side_effect=real_httpx.ConnectError("boom")):
        out = svc.test_connection("sandbox", "id", "secret")
    assert out["ok"] is False
    assert out["status_code"] is None


# ─────────────────────────────────────────────────────────────
# エンドポイント（DB/HTTP はモック）
# ─────────────────────────────────────────────────────────────
async def test_status_endpoint(client, monkeypatch):
    async def _status(db, tid):
        return {"configured": True, "environment": "sandbox"}

    monkeypatch.setattr(svc, "get_status", _status)
    resp = await client.get("/api/v1/integrations/paypal/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is True
    assert body["environment"] == "sandbox"


async def test_save_credentials(client, monkeypatch):
    calls = {}

    async def _save(db, tid, cid, csec, env, uid):
        calls["env"] = env

    monkeypatch.setattr(svc, "save_credentials", _save)
    resp = await client.put(
        "/api/v1/integrations/paypal/credentials",
        json={"client_id": "x", "client_secret": "y", "environment": "live"},
    )
    assert resp.status_code == 204
    assert calls["env"] == "live"


async def test_save_credentials_missing_fields(client):
    resp = await client.put(
        "/api/v1/integrations/paypal/credentials",
        json={"client_id": "", "client_secret": "", "environment": "sandbox"},
    )
    assert resp.status_code == 400


async def test_test_connection_endpoint(client, monkeypatch):
    async def _creds(db, tid):
        return {"client_id": "x", "client_secret": "y", "environment": "sandbox"}

    monkeypatch.setattr(svc, "get_credentials", _creds)
    monkeypatch.setattr(svc, "test_connection", lambda *a, **k: {"ok": True, "status_code": 200, "message": "認証成功"})
    resp = await client.post("/api/v1/integrations/paypal/test-connection", json={})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


async def test_test_connection_not_configured(client, monkeypatch):
    async def _none(db, tid):
        return None

    monkeypatch.setattr(svc, "get_credentials", _none)
    resp = await client.post("/api/v1/integrations/paypal/test-connection", json={})
    assert resp.status_code == 400
