"""PayPal webhook（登録・署名検証）＋ create_order custom_id のサービステスト。

httpx はモック。対応 AC: design.md #1（登録）/#2（既存再利用）/#3（検証）/#4（custom_id）。
"""

from unittest.mock import MagicMock, patch

from app.services import paypal_payments as svc


def _resp(status_code, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.json = MagicMock(return_value=json_body or {})
    return r


# ── register_webhook ───────────────────────────────────────────
def test_register_webhook_success():
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "post", return_value=_resp(201, {"id": "WH-1"})):
        out = svc.register_webhook("sandbox", "id", "sec", "https://api/x/webhook")
    assert out["ok"] is True
    assert out["webhook_id"] == "WH-1"


def test_register_webhook_existing_reuses_id():
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "post",
                      return_value=_resp(400, {"name": "WEBHOOK_URL_ALREADY_EXISTS"})), \
         patch.object(svc.httpx, "get", return_value=_resp(200, {"webhooks": [
             {"id": "OTHER", "url": "https://api/y/webhook"},
             {"id": "WH-EXIST", "url": "https://api/x/webhook"},
         ]})):
        out = svc.register_webhook("sandbox", "id", "sec", "https://api/x/webhook")
    assert out["ok"] is True
    assert out["webhook_id"] == "WH-EXIST"


def test_register_webhook_token_fail():
    with patch.object(svc, "_get_token", return_value=None):
        out = svc.register_webhook("sandbox", "id", "bad", "https://api/x/webhook")
    assert out["ok"] is False
    assert out["webhook_id"] is None


# ── verify_webhook ─────────────────────────────────────────────
def test_verify_webhook_success():
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "post", return_value=_resp(200, {"verification_status": "SUCCESS"})):
        ok = svc.verify_webhook("sandbox", "id", "sec", "WH-1",
                                "t", "tm", "c", "a", "s", {"x": 1})
    assert ok is True


def test_verify_webhook_failure():
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "post", return_value=_resp(200, {"verification_status": "FAILURE"})):
        ok = svc.verify_webhook("sandbox", "id", "sec", "WH-1",
                                "t", "tm", "c", "a", "s", {"x": 1})
    assert ok is False


def test_verify_webhook_token_fail_returns_false():
    with patch.object(svc, "_get_token", return_value=None):
        ok = svc.verify_webhook("sandbox", "id", "bad", "WH-1",
                                "t", "tm", "c", "a", "s", {"x": 1})
    assert ok is False


# ── create_order custom_id ─────────────────────────────────────
def test_create_order_includes_custom_id():
    order_ok = {"id": "O-1", "links": [{"rel": "approve", "href": "https://x"}]}
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "post", return_value=_resp(201, order_ok)) as p:
        svc.create_order("sandbox", "id", "sec", 1000, "JPY", "INV-1",
                         "https://r", "https://c", "4:123")
    _, kwargs = p.call_args
    assert kwargs["json"]["purchase_units"][0]["custom_id"] == "4:123"


def test_create_order_without_custom_id_omits_it():
    order_ok = {"id": "O-1", "links": [{"rel": "approve", "href": "https://x"}]}
    with patch.object(svc, "_get_token", return_value="tok"), \
         patch.object(svc.httpx, "post", return_value=_resp(201, order_ok)) as p:
        svc.create_order("sandbox", "id", "sec", 1000, "JPY", "INV-1", "https://r", "https://c")
    _, kwargs = p.call_args
    assert "custom_id" not in kwargs["json"]["purchase_units"][0]
