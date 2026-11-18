"""請求書の PDF の宛名（invoice-portfolio R1・design-v2 K4。DB なし）。

reportlab の Canvas の drawString を包み、描かれた文字を集めて確かめる。
"""
from __future__ import annotations

import pytest
from reportlab.pdfgen import canvas as rl_canvas

from app.routers.invoices import _quote_pdf_address
from app.services.invoice_renderer import render_invoice_pdf, render_quote_pdf

_OLD = {
    "company_name": "Old Co", "billing_display_name": None, "label": None, "postal_code": "100-0001",
    "address": "Line A Line B", "city": "Chiyoda", "state": "Tokyo", "country": "JP", "phone": "03-0000",
}
_NEW = dict(
    _OLD,
    recipient_name="Recv Person", email="r@example.com", tax_id="TX-1",
    address_line_1="Line A", address_line_2="Line B", address_line_3="Line C",
)


@pytest.fixture
def drawn(monkeypatch):
    texts: list[str] = []
    orig = rl_canvas.Canvas.drawString

    def _string(self, x, y, text, *a, **k):
        texts.append(str(text))
        return orig(self, x, y, text, *a, **k)

    monkeypatch.setattr(rl_canvas.Canvas, "drawString", _string)
    return texts


def _invoice(snap: dict) -> dict:
    return {
        "invoice_code": "IN-0001-01", "issued_at": "2026-11-17T00:00:00",
        "ship_to_snapshot": snap, "bill_to_snapshot": None,
        "items": [{"name_en": "Test Item", "quantity": 1, "unit_price": 1000.0, "subtotal": 1000.0, "hs_code": None}],
        "subtotal": 1000.0, "shipping_fee": 0.0, "tax_amount": 0.0, "total_amount": 1000.0,
        "currency": "JPY", "duty_amount": None, "fx_rate_snapshot": None, "notes": None,
    }


def _quote(snap: dict) -> dict:
    return {
        "quote_code": "QT-0001", "created_at": "2026-11-17T00:00:00",
        "ship_to_snapshot": snap, "bill_to_snapshot": None,
        "items": [{"name_en": "Test Item", "quantity": 1, "unit_price": 1000.0, "subtotal": 1000.0, "hs_code": None}],
        "subtotal": 1000.0, "shipping_fee": 0.0, "total_amount": 1000.0, "currency": "JPY", "notes": None,
    }


def test_k4_new_copy_prints_split_address(drawn):
    render_invoice_pdf(_invoice(_NEW), {})
    for want in ("Recv Person", "Line A", "Line B", "Line C", "Chiyoda, Tokyo, 100-0001", "Tax ID: TX-1", "Email: r@example.com"):
        assert want in drawn, want
    assert "Line A Line B" not in drawn


def test_k4_old_copy_prints_as_before(drawn):
    render_invoice_pdf(_invoice(_OLD), {})
    assert "Line A Line B" in drawn
    assert "Chiyoda, Tokyo, 100-0001" not in drawn
    assert not any(t.startswith("Tax ID:") or t.startswith("Email:") for t in drawn)


def test_k4_quote_pdf_is_unchanged(drawn):
    stripped = _quote_pdf_address(_NEW)
    assert stripped == _OLD
    assert _quote_pdf_address(None) is None
    render_quote_pdf(_quote(_OLD), {})
    before = list(drawn)
    drawn.clear()
    render_quote_pdf(_quote(stripped), {})
    assert drawn == before
