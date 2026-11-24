"""送り先の住所1行の決まり（customer-address-form design §2・§6）。DB なし。"""

import pytest
from pydantic import ValidationError

from app.schemas.base import validate_delivery_address_line
from app.schemas.order_shipping_detail import (
    OrderShippingDetailCreate,
    OrderShippingDetailResponse,
    OrderShippingDetailUpdate,
)
from app.schemas.registration_token import AddressInput


def test_35_chars_ok():
    assert validate_delivery_address_line("x" * 35) == "x" * 35


def test_36_chars_too_long():
    with pytest.raises(ValueError, match="address_line_too_long"):
        validate_delivery_address_line("x" * 36)


def test_japanese_non_ascii():
    with pytest.raises(ValueError, match="address_line_non_ascii"):
        validate_delivery_address_line("東京")


def test_accent_non_ascii():
    with pytest.raises(ValueError, match="address_line_non_ascii"):
        validate_delivery_address_line("é")


def test_symbols_ok():
    assert validate_delivery_address_line("1-2 Main St, #3") == "1-2 Main St, #3"


def test_none_and_empty_ok():
    assert validate_delivery_address_line(None) is None
    assert validate_delivery_address_line("") == ""


def test_newline_rejected():
    with pytest.raises(ValueError, match="address_line_non_ascii"):
        validate_delivery_address_line("a\nb")


def test_kind_checked_before_length():
    with pytest.raises(ValueError, match="address_line_non_ascii"):
        validate_delivery_address_line("東京" * 36)


def test_address_input_delivery_36_rejected():
    with pytest.raises(ValidationError):
        AddressInput(address_type="delivery", address_line_1="x" * 36)


def test_address_input_billing_36_ok():
    a = AddressInput(address_type="billing", address_line_1="x" * 36)
    assert a.address_line_1 == "x" * 36


def test_shipping_create_36_rejected():
    with pytest.raises(ValidationError):
        OrderShippingDetailCreate(address1="x" * 36)


def test_shipping_update_non_ascii_rejected():
    with pytest.raises(ValidationError):
        OrderShippingDetailUpdate(address3="東京")


def test_shipping_update_without_address_ok():
    assert OrderShippingDetailUpdate(city="Tokyo").city == "Tokyo"


def test_shipping_response_not_checked():
    r = OrderShippingDetailResponse(
        id=1,
        order_id=1,
        tenant_id=1,
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
        address1="x" * 36,
    )
    assert r.address1 == "x" * 36
