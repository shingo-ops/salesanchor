"""請求書 PDF の支払方法の区切りと税率の添え書き（invoice-create-portfolio 便C・K12。DB なし）。

reportlab の Canvas の drawString / drawRightString を包み、描かれた文字を集めて確かめる。
"""
from __future__ import annotations

import pytest
from reportlab.pdfgen import canvas as rl_canvas

from app.services.invoice_renderer import render_invoice_pdf


@pytest.fixture
def drawn(monkeypatch):
    """描かれた文字を list に集める。"""
    texts: list[str] = []
    orig_string = rl_canvas.Canvas.drawString
    orig_right = rl_canvas.Canvas.drawRightString

    def _string(self, x, y, text, *a, **k):
        texts.append(str(text))
        return orig_string(self, x, y, text, *a, **k)

    def _right(self, x, y, text, *a, **k):
        texts.append(str(text))
        return orig_right(self, x, y, text, *a, **k)

    monkeypatch.setattr(rl_canvas.Canvas, "drawString", _string)
    monkeypatch.setattr(rl_canvas.Canvas, "drawRightString", _right)
    return texts


def _invoice(**overrides) -> dict:
    data = {
        "invoice_code": "IN-0001-01",
        "issued_at": "2026-11-15T00:00:00",
        "ship_to_snapshot": None,
        "bill_to_snapshot": None,
        "items": [{"name_en": "Test Item", "quantity": 1, "unit_price": 1000.0, "subtotal": 1000.0, "hs_code": None}],
        "subtotal": 1000.0,
        "shipping_fee": 0.0,
        "tax_amount": 0.0,
        "total_amount": 1000.0,
        "currency": "JPY",
        "duty_amount": None,
        "fx_rate_snapshot": None,
        "notes": None,
    }
    data.update(overrides)
    return data


def test_h1_bank_version_is_printed(drawn):
    payment = {
        "method_type": "bank", "display_name": "Main", "bank_name": "Test Bank", "bank_branch": None,
        "account_type": None, "account_number": "1234567", "account_holder": "Test Holder", "swift_code": None,
    }
    pdf = render_invoice_pdf(_invoice(payment=payment), {})
    assert isinstance(pdf, bytes) and len(pdf) > 0
    assert "Payment:" in drawn
    assert "Account number: 1234567" in drawn
    assert "Bank: Test Bank" in drawn


def test_h2_tax_label_carries_the_rate(drawn):
    render_invoice_pdf(_invoice(tax_amount=600.0, total_amount=1600.0, tax_rate_percent=10.0), {})
    assert "Tax (10%):" in drawn
    drawn.clear()
    render_invoice_pdf(_invoice(tax_amount=600.0, total_amount=1600.0, tax_rate_percent=None), {})
    assert "Tax:" in drawn
    assert "Tax (10%):" not in drawn


def test_h3_wise_and_paypal_versions(drawn):
    wise = {
        "method_type": "wise", "display_name": "Wise USD", "account_holder": "Holder",
        "wise_email": "a@example.com", "bank_name": None, "swift_bic": None, "iban": None,
    }
    render_invoice_pdf(_invoice(payment=wise), {})
    assert "Wise email: a@example.com" in drawn
    assert not any(t.startswith("IBAN") for t in drawn)
    drawn.clear()
    render_invoice_pdf(_invoice(payment={"method_type": "paypal"}), {})
    assert "Payment:" in drawn
    assert "PayPal" in drawn


def test_h4_without_payment_nothing_is_printed(drawn):
    render_invoice_pdf(_invoice(payment=None), {})
    assert "Payment:" not in drawn
