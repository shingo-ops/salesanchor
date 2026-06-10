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
# get_status: フィールド別登録ヒント
# ─────────────────────────────────────────────────────────────
def test_account_number_hint_masking():
    """末尾3桁マスクが正しく生成される。"""
    # 6桁以上のアカウント番号 → ******XXX
    acct = "123456789"
    suffix = acct[-3:]
    hint = f"******{suffix}"
    assert hint == "******789"


def test_account_number_hint_short():
    """短いアカウント番号でも末尾3桁を返す（存在する分だけ）。"""
    acct = "01"
    suffix = acct[-3:]  # 全体
    hint = f"******{suffix}"
    assert hint == "******01"


# ─────────────────────────────────────────────────────────────
# エンドポイント（DB/HTTP はモック）
# ─────────────────────────────────────────────────────────────
async def test_status_endpoint_configured(client, monkeypatch):
    """登録済み時: フィールド別ヒントが含まれる。"""
    async def _status(db, tid, carrier):
        return {
            "configured": True,
            "environment": "production",
            "client_id_hint": "test-api-key-id",
            "secret_configured": True,
            "account_number_hint": "******011",
        }

    monkeypatch.setattr(svc, "get_status", _status)
    resp = await client.get("/api/v1/integrations/carriers/fedex/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["carrier"] == "fedex"
    assert body["configured"] is True
    assert body["client_id_hint"] == "test-api-key-id"
    assert body["secret_configured"] is True
    assert body["account_number_hint"] == "******011"


async def test_status_endpoint_not_configured(client, monkeypatch):
    """未登録時: ヒントは None / False。"""
    async def _status(db, tid, carrier):
        return {
            "configured": False,
            "environment": "production",
            "client_id_hint": None,
            "secret_configured": False,
            "account_number_hint": None,
        }

    monkeypatch.setattr(svc, "get_status", _status)
    resp = await client.get("/api/v1/integrations/carriers/dhl/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is False
    assert body["client_id_hint"] is None
    assert body["secret_configured"] is False
    assert body["account_number_hint"] is None


async def test_status_invalid_carrier_404(client):
    resp = await client.get("/api/v1/integrations/carriers/yamato/status")
    assert resp.status_code == 404


async def test_save_credentials(client, monkeypatch):
    calls = {}

    async def _save(db, tid, carrier, cid, csec, env, uid, account_number=None):
        calls["carrier"] = carrier
        calls["env"] = env
        calls["account_number"] = account_number

    monkeypatch.setattr(svc, "save_credentials", _save)
    resp = await client.put(
        "/api/v1/integrations/carriers/ups/credentials",
        json={"client_id": "x", "client_secret": "y"},
    )
    assert resp.status_code == 204
    assert calls["carrier"] == "ups"
    assert calls["account_number"] is None  # 未指定時は None


async def test_save_forces_production_environment(client, monkeypatch):
    """リクエストの environment フィールドを無視し、常に production で保存する。"""
    calls = {}

    async def _save(db, tid, carrier, cid, csec, env, uid, account_number=None):
        calls["env"] = env

    monkeypatch.setattr(svc, "save_credentials", _save)
    resp = await client.put(
        "/api/v1/integrations/carriers/fedex/credentials",
        json={"client_id": "x", "client_secret": "y", "environment": "sandbox"},
    )
    assert resp.status_code == 204
    assert calls["env"] == "production"  # sandbox を渡しても production に上書きされる


async def test_save_credentials_missing_fields(client):
    resp = await client.put(
        "/api/v1/integrations/carriers/ups/credentials",
        json={"client_id": "", "client_secret": "", "environment": "sandbox"},
    )
    assert resp.status_code == 400


async def test_save_with_account_number(client, monkeypatch):
    """account_number が指定された場合は保存されること。"""
    calls = {}

    async def _save(db, tid, carrier, cid, csec, env, uid, account_number=None):
        calls["account_number"] = account_number

    monkeypatch.setattr(svc, "save_credentials", _save)
    resp = await client.put(
        "/api/v1/integrations/carriers/fedex/credentials",
        json={"client_id": "id", "client_secret": "sec", "account_number": "123456011"},
    )
    assert resp.status_code == 204
    assert calls["account_number"] == "123456011"


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
