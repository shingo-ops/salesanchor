"""PayPal Invoicing 方式（ADR-101 改訂 2026-06-12）のテスト。

service 層（create_and_send_invoice / get_invoice_status）は httpx をモックして単離検証。
router 層（issue_paypal_link）は client + DB（SQLite）で email 必須・成功経路を検証。
対応 AC: design.md #1（create→send→recipient_view_url）/#2（status=PAID 判定）/#3（email無し400）。
"""

from unittest.mock import MagicMock, patch

from app.services import paypal_payments as svc


def _resp(status_code, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.json = MagicMock(return_value=json_body or {})
    return r


# ── create_and_send_invoice ────────────────────────────────────
_CREATE_OK = {"id": "INV2-AAAA-BBBB-CCCC-DDDD"}
_SEND_OK = {"links": [
    {"rel": "self", "href": "https://x/self"},
    {"rel": "recipient-view", "href": "https://www.sandbox.paypal.com/invoice/p/#INV2"},
]}


def test_create_and_send_invoice_success():
    # GET 詳細から invoicer_view_url（発行者ビュー・原本ワンクリック用）を取得する
    get_body = {"detail": {"metadata": {
        "recipient_view_url": "https://www.sandbox.paypal.com/invoice/p/#INV2",
        "invoicer_view_url": "https://www.sandbox.paypal.com/invoice/s/#INV2",
    }}}
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "post", side_effect=[_resp(201, _CREATE_OK), _resp(200, _SEND_OK)]) as p, \
         patch.object(svc.httpx, "get", return_value=_resp(200, get_body)):
        out = svc.create_and_send_invoice(
            "sandbox", "id", "sec",
            invoice_number="IN-0001-01", currency="JPY", amount=1000,
            recipient_email="buyer@example.com", reference="4:123",
        )
    assert out["ok"] is True
    assert out["paypal_invoice_id"] == "INV2-AAAA-BBBB-CCCC-DDDD"
    assert out["recipient_view_url"] == "https://www.sandbox.paypal.com/invoice/p/#INV2"
    assert out["invoicer_view_url"] == "https://www.sandbox.paypal.com/invoice/s/#INV2"
    # create body: reference / invoice_number / 送付先 email / JPY 整数値
    create_kwargs = p.call_args_list[0].kwargs["json"]
    assert create_kwargs["detail"]["reference"] == "4:123"
    assert create_kwargs["detail"]["invoice_number"] == "IN-0001-01"
    assert create_kwargs["primary_recipients"][0]["billing_info"]["email_address"] == "buyer@example.com"
    assert create_kwargs["items"][0]["unit_amount"]["value"] == "1000"
    # 2 番目の呼び出しは send（send_to_recipient=True）
    send_kwargs = p.call_args_list[1].kwargs["json"]
    assert send_kwargs["send_to_recipient"] is True


def test_create_and_send_invoice_recipient_view_via_get_fallback():
    """send レスポンスに recipient-view が無ければ GET の metadata から取得する。"""
    get_body = {"detail": {"metadata": {"recipient_view_url": "https://pay/from-get"}}}
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "post", side_effect=[_resp(201, _CREATE_OK), _resp(202, {})]), \
         patch.object(svc.httpx, "get", return_value=_resp(200, get_body)):
        out = svc.create_and_send_invoice(
            "sandbox", "id", "sec",
            invoice_number="IN-0002-01", currency="USD", amount=10,
            recipient_email="b@example.com", reference="4:9",
        )
    assert out["ok"] is True
    assert out["recipient_view_url"] == "https://pay/from-get"


def test_create_and_send_invoice_create_http_error():
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "post", return_value=_resp(400, {"name": "VALIDATION_ERROR"})):
        out = svc.create_and_send_invoice(
            "sandbox", "id", "sec",
            invoice_number="IN-1", currency="JPY", amount=1000,
            recipient_email="b@example.com", reference="4:1",
        )
    assert out["ok"] is False
    assert out["status_code"] == 400
    assert out["paypal_invoice_id"] is None


def test_create_and_send_invoice_send_http_error():
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "post", side_effect=[_resp(201, _CREATE_OK), _resp(422, {})]):
        out = svc.create_and_send_invoice(
            "sandbox", "id", "sec",
            invoice_number="IN-1", currency="JPY", amount=1000,
            recipient_email="b@example.com", reference="4:1",
        )
    assert out["ok"] is False
    assert out["status_code"] == 422
    # 作成はできているので id は返る（送付のみ失敗）
    assert out["paypal_invoice_id"] == "INV2-AAAA-BBBB-CCCC-DDDD"


def test_create_and_send_invoice_token_fail_401():
    with patch.object(svc, "_get_token", return_value=None):
        out = svc.create_and_send_invoice(
            "sandbox", "id", "bad",
            invoice_number="IN-1", currency="JPY", amount=1000,
            recipient_email="b@example.com", reference="4:1",
        )
    assert out["ok"] is False
    assert out["status_code"] == 401


# ── get_invoice_status ─────────────────────────────────────────
def test_get_invoice_status_paid_extracts_fee():
    body = {
        "status": "PAID",
        "payments": {"transactions": [{"paypal_fee": {"value": "3.30"}}]},
    }
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "get", return_value=_resp(200, body)):
        out = svc.get_invoice_status("sandbox", "id", "sec", "INV2-1")
    assert out["ok"] is True
    assert out["paid"] is True
    assert out["fee"] == "3.30"


def test_get_invoice_status_sent_not_paid():
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "get", return_value=_resp(200, {"status": "SENT"})):
        out = svc.get_invoice_status("sandbox", "id", "sec", "INV2-1")
    assert out["ok"] is True
    assert out["paid"] is False


def test_get_invoice_status_http_error():
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "get", return_value=_resp(404, {})):
        out = svc.get_invoice_status("sandbox", "id", "sec", "INV2-1")
    assert out["ok"] is False
    assert out["status_code"] == 404


# ── register_webhook が INVOICING.INVOICE.PAID を購読 ──────────
def test_register_webhook_subscribes_invoicing_paid_and_disputes():
    """入金（INVOICING.INVOICE.PAID）＋ケース3種（CUSTOMER.DISPUTE.*）を購読する（Inc4 Step A）。"""
    created = {"id": "WH-1"}
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc, "_find_existing_webhook", return_value=None), \
         patch.object(svc.httpx, "post", return_value=_resp(201, created)) as p:
        out = svc.register_webhook("sandbox", "id", "sec", "https://api/webhook")
    assert out["ok"] is True
    assert out["webhook_id"] == "WH-1"
    names = {e["name"] for e in p.call_args.kwargs["json"]["event_types"]}
    assert names == {
        "INVOICING.INVOICE.PAID",
        "CUSTOMER.DISPUTE.CREATED",
        "CUSTOMER.DISPUTE.UPDATED",
        "CUSTOMER.DISPUTE.RESOLVED",
    }


# ── router: issue_paypal_link（email 必須・成功経路） ───────────
async def _company_contact(client, *, email=None):
    co = await client.post("/api/v1/companies", json={"name": "Invoicingテスト会社"})
    assert co.status_code == 201, co.text
    company_id = co.json()["id"]
    payload = {"company_id": company_id, "display_name": "担当"}
    if email is not None:
        payload["primary_email"] = email
    ct = await client.post("/api/v1/contacts", json=payload)
    assert ct.status_code == 201, ct.text
    return company_id, ct.json()["id"]


async def _issued_invoice(client, company_id, contact_id):
    inv = await client.post("/api/v1/invoices", json={
        "company_id": company_id, "contact_id": contact_id,
        "items": [{"product_name": "商品", "quantity": 1, "unit_price": "1000.00"}],
    })
    assert inv.status_code == 201, inv.text
    invoice_id = inv.json()["id"]
    issued = await client.post(f"/api/v1/invoices/{invoice_id}/issue")
    assert issued.status_code == 200, issued.text
    return invoice_id


async def test_issue_paypal_link_requires_email(client):
    """email 未登録 contact の請求書は PayPal 請求書を発行できない（400）。"""
    company_id, contact_id = await _company_contact(client, email=None)
    invoice_id = await _issued_invoice(client, company_id, contact_id)
    resp = await client.post(f"/api/v1/invoices/{invoice_id}/paypal-link")
    assert resp.status_code == 400
    assert "メールアドレス" in resp.json()["detail"]


async def test_issue_paypal_link_success(client, monkeypatch):
    """email 有り＋creds 有りで Invoicing を発行し paypal_order_id/approval_url を保存。"""
    company_id, contact_id = await _company_contact(client, email="buyer@example.com")
    invoice_id = await _issued_invoice(client, company_id, contact_id)

    async def _creds(db, tid):
        return {"client_id": "x", "client_secret": "y", "environment": "sandbox"}

    monkeypatch.setattr(svc, "get_credentials", _creds)
    monkeypatch.setattr(svc, "create_and_send_invoice", lambda *a, **k: {
        "ok": True, "paypal_invoice_id": "INV2-ZZZZ", "recipient_view_url": "https://pay/zzz",
        "invoicer_view_url": "https://merchant/zzz",
        "status_code": 200, "message": "OK",
    })
    # 写しPDF 生成は別テストで検証済み。ここでは保存→取得経路を検証するため bytes を返すよう mock。
    import app.routers.invoices as inv_mod

    async def _fake_copy(*a, **k):
        return b"%PDF-1.4 paypal copy"
    monkeypatch.setattr(inv_mod, "_render_paypal_copy_pdf", _fake_copy)
    resp = await client.post(f"/api/v1/invoices/{invoice_id}/paypal-link")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["paypal_order_id"] == "INV2-ZZZZ"
    assert body["paypal_approval_url"] == "https://pay/zzz"
    # ADR-101改訂(2) Inc1: 発行者ビューURLが保存される
    assert body["paypal_invoicer_view_url"] == "https://merchant/zzz"
    # 写しPDF が自動保存され、専用 endpoint で取得できる（reportlab 生成）
    pdf = await client.get(f"/api/v1/invoices/{invoice_id}/paypal-copy-pdf")
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:4] == b"%PDF"


async def test_paypal_copy_pdf_404_when_not_issued(client):
    """PayPal 未発行の請求書は写しPDFが無いので 404。"""
    company_id, contact_id = await _company_contact(client, email="buyer@example.com")
    invoice_id = await _issued_invoice(client, company_id, contact_id)
    resp = await client.get(f"/api/v1/invoices/{invoice_id}/paypal-copy-pdf")
    assert resp.status_code == 404


async def test_issue_paypal_link_copy_pdf_failure_non_fatal(client, monkeypatch):
    """写しPDF 生成が失敗してもリンク発行は成功する（致命にしない）。"""
    company_id, contact_id = await _company_contact(client, email="buyer@example.com")
    invoice_id = await _issued_invoice(client, company_id, contact_id)

    async def _creds(db, tid):
        return {"client_id": "x", "client_secret": "y", "environment": "sandbox"}

    monkeypatch.setattr(svc, "get_credentials", _creds)
    monkeypatch.setattr(svc, "create_and_send_invoice", lambda *a, **k: {
        "ok": True, "paypal_invoice_id": "INV2-ERR", "recipient_view_url": "https://pay/e",
        "invoicer_view_url": "https://merchant/e", "status_code": 200, "message": "OK",
    })
    # 写しPDF レンダリングを例外化
    import app.routers.invoices as inv_mod
    monkeypatch.setattr(inv_mod, "render_invoice_pdf",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("render boom")))
    resp = await client.post(f"/api/v1/invoices/{invoice_id}/paypal-link")
    assert resp.status_code == 200, resp.text
    assert resp.json()["paypal_order_id"] == "INV2-ERR"
    # 写しPDF は保存されていない → 404
    pdf = await client.get(f"/api/v1/invoices/{invoice_id}/paypal-copy-pdf")
    assert pdf.status_code == 404


# ── renderer: 写しPDF（PayPal 写し注記＋QR）────────────────────────
def test_render_invoice_pdf_with_paypal_copy():
    from app.services.invoice_renderer import render_invoice_pdf

    invoice_data = {
        "invoice_code": "IN-0001-01", "issued_at": None,
        "items": [{"product_name": "X", "quantity": 1, "unit_price": 1000, "subtotal": 1000}],
        "subtotal": 1000, "shipping_fee": 0, "tax_amount": 0, "total_amount": 1000,
        "currency": "JPY",
    }
    out = render_invoice_pdf(invoice_data, {"name": "T"},
                             paypal_copy={"pp_invoice_number": "INV2-1",
                                          "original_url": "https://pay/x"})
    assert isinstance(out, (bytes, bytearray))
    assert out[:4] == b"%PDF"


# ── Inc4 Step B: dispute webhook 受信→紐づけ表示 ──────────────────
async def _seed_paypal_config(db_session, tenant_id=999, webhook_id="WH-1"):
    from sqlalchemy import text
    # テスト DB は commit が永続するため冪等（OR REPLACE）にする
    await db_session.execute(text(
        "INSERT OR REPLACE INTO tenant_paypal_config "
        "(tenant_id, client_id_encrypted, client_secret_encrypted, environment, webhook_id) "
        "VALUES (:t, 'x', 'y', 'sandbox', :w)"
    ), {"t": tenant_id, "w": webhook_id})
    await db_session.commit()


def _mock_paypal_creds(monkeypatch):
    async def _creds(db, tid):
        return {"client_id": "x", "client_secret": "y", "environment": "sandbox"}

    async def _wid(db, tid):
        return "WH-1"

    monkeypatch.setattr(svc, "get_credentials", _creds)
    monkeypatch.setattr(svc, "get_webhook_id", _wid)


def _dispute_event(invoice_number, dispute_id="PP-D-1", status="OPEN"):
    return {
        "event_type": "CUSTOMER.DISPUTE.CREATED",
        "resource": {
            "dispute_id": dispute_id,
            "status": status,
            "reason": "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
            "dispute_amount": {"value": "100.00", "currency_code": "USD"},
            "disputed_transactions": [
                {"invoice_number": invoice_number, "seller_transaction_id": "TXN-1"}
            ],
        },
    }


async def test_dispute_webhook_creates_and_links(client, db_session, monkeypatch):
    """署名OK → paypal_disputes に upsert＋invoice_number で請求書に紐づけ→ endpoint で取得。"""
    company_id, contact_id = await _company_contact(client, email="b@example.com")
    invoice_id = await _issued_invoice(client, company_id, contact_id)
    inv = (await client.get(f"/api/v1/invoices/{invoice_id}")).json()
    invoice_number = inv["invoice_number"]

    await _seed_paypal_config(db_session)
    _mock_paypal_creds(monkeypatch)
    monkeypatch.setattr(svc, "verify_webhook", lambda *a, **k: True)

    resp = await client.post("/api/v1/integrations/paypal/webhook",
                             json=_dispute_event(invoice_number, dispute_id="PP-D-CREATE"))
    assert resp.status_code == 200, resp.text

    got = (await client.get(f"/api/v1/invoices/{invoice_id}/paypal-disputes")).json()
    assert len(got) == 1
    assert got[0]["dispute_id"] == "PP-D-CREATE"
    assert got[0]["status"] == "OPEN"
    assert got[0]["amount"] == 100.0
    assert got[0]["currency"] == "USD"


async def test_dispute_webhook_idempotent_update(client, db_session, monkeypatch):
    """同一 dispute_id の UPDATED は status を更新（冪等・二重作成しない）。"""
    company_id, contact_id = await _company_contact(client, email="b@example.com")
    invoice_id = await _issued_invoice(client, company_id, contact_id)
    invoice_number = (await client.get(f"/api/v1/invoices/{invoice_id}")).json()["invoice_number"]
    await _seed_paypal_config(db_session)
    _mock_paypal_creds(monkeypatch)
    monkeypatch.setattr(svc, "verify_webhook", lambda *a, **k: True)

    await client.post("/api/v1/integrations/paypal/webhook",
                      json=_dispute_event(invoice_number, dispute_id="PP-D-IDEM"))
    ev = _dispute_event(invoice_number, dispute_id="PP-D-IDEM", status="RESOLVED")
    ev["event_type"] = "CUSTOMER.DISPUTE.RESOLVED"
    await client.post("/api/v1/integrations/paypal/webhook", json=ev)

    got = (await client.get(f"/api/v1/invoices/{invoice_id}/paypal-disputes")).json()
    assert len(got) == 1  # 二重作成されない
    assert got[0]["status"] == "RESOLVED"


async def test_dispute_webhook_invalid_signature_400(client, db_session, monkeypatch):
    """どのテナントでも署名が通らない → 400（保存しない）。"""
    await _seed_paypal_config(db_session)
    _mock_paypal_creds(monkeypatch)
    monkeypatch.setattr(svc, "verify_webhook", lambda *a, **k: False)
    resp = await client.post("/api/v1/integrations/paypal/webhook",
                             json=_dispute_event("IN-9999-01"))
    assert resp.status_code == 400


async def test_invoice_paid_webhook_still_works(client, monkeypatch):
    """既存の INVOICING.INVOICE.PAID 経路がディスパッチャ化後も対象外でなく処理される（非破壊）。"""
    # reference 解析不能（資料不足）でも 200（無視）で返ることを確認＝ディスパッチ自体は動く
    resp = await client.post("/api/v1/integrations/paypal/webhook",
                             json={"event_type": "INVOICING.INVOICE.PAID", "resource": {}})
    assert resp.status_code == 200


async def test_webhook_unknown_event_ignored(client):
    """対象外イベントは 200 で無視。"""
    resp = await client.post("/api/v1/integrations/paypal/webhook",
                             json={"event_type": "SOME.OTHER.EVENT", "resource": {}})
    assert resp.status_code == 200
