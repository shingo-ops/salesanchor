"""PayPal 決済テスト用 test-invoice エンドポイントのテスト。

対応 AC: design.md #2(live拒否)/#3(未接続400)/#4(会社・担当者 find-or-create 再利用)。
DB は conftest の SQLite、PayPal 呼び出し(get_credentials/create_and_send_invoice)はモック。
ADR-101 改訂 2026-06-12: Invoicing 方式へ移行（create_order→create_and_send_invoice）。
"""

from app.services import paypal_payments as svc


async def test_test_invoice_live_rejected(client, monkeypatch):
    """live 環境では 400（実課金防止）。"""
    async def _creds(db, tid):
        return {"client_id": "x", "client_secret": "y", "environment": "live"}

    monkeypatch.setattr(svc, "get_credentials", _creds)
    resp = await client.post("/api/v1/integrations/paypal/test-invoice", json={})
    assert resp.status_code == 400
    assert "sandbox" in resp.json()["detail"]


async def test_test_invoice_not_configured(client, monkeypatch):
    """PayPal 未接続では 400。"""
    async def _none(db, tid):
        return None

    monkeypatch.setattr(svc, "get_credentials", _none)
    resp = await client.post("/api/v1/integrations/paypal/test-invoice", json={})
    assert resp.status_code == 400


async def test_test_invoice_success_and_dedup(client, monkeypatch):
    """sandbox でテスト請求書＋PayPal 請求書送付。2回呼んでも会社/担当者は再利用（重複作成しない）。"""
    async def _creds(db, tid):
        return {"client_id": "x", "client_secret": "y", "environment": "sandbox"}

    monkeypatch.setattr(svc, "get_credentials", _creds)
    monkeypatch.setattr(
        svc, "create_and_send_invoice",
        lambda *a, **k: {"ok": True, "paypal_invoice_id": "INV2-TEST",
                         "recipient_view_url": "https://sandbox.paypal/x",
                         "status_code": 200, "message": "OK"},
    )

    r1 = await client.post("/api/v1/integrations/paypal/test-invoice", json={})
    assert r1.status_code == 200, r1.text
    b1 = r1.json()
    assert b1["approval_url"] == "https://sandbox.paypal/x"
    assert b1["amount"] == 100
    assert b1["currency"] == "JPY"

    r2 = await client.post("/api/v1/integrations/paypal/test-invoice", json={})
    assert r2.status_code == 200, r2.text
    # 2回目は別請求書（採番が進む）だが会社/担当者は再利用される
    assert r2.json()["invoice_id"] != b1["invoice_id"]


async def test_test_invoice_create_failure_502(client, monkeypatch):
    """create_and_send_invoice 失敗時は 502（請求書は commit されない）。"""
    async def _creds(db, tid):
        return {"client_id": "x", "client_secret": "y", "environment": "sandbox"}

    monkeypatch.setattr(svc, "get_credentials", _creds)
    monkeypatch.setattr(
        svc, "create_and_send_invoice",
        lambda *a, **k: {"ok": False, "paypal_invoice_id": None, "recipient_view_url": None,
                         "status_code": 500, "message": "fail"},
    )
    resp = await client.post("/api/v1/integrations/paypal/test-invoice", json={})
    assert resp.status_code == 502
