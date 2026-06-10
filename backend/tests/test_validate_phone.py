"""ADR-126: validate_phone regex union pattern tests.

Tests the three patterns:
  1. +\\d{6,15}  — E.164 international (e.g., +376367830 Andorra 9-digit)
  2. \\d{10,15}  — Legacy DB-compat without + (e.g., 15551234567)
  3. 0\\d{9,10}  — Japan domestic (e.g., 09012345678)

Plus rejection of too-short values and edge cases.
"""

import pytest

from app.schemas.base import validate_phone


class TestValidatePhoneE164:
    """Pattern 1: +\\d{6,15} (international with +)."""

    def test_andorra_9_digit(self) -> None:
        """ADR-126 AC: +376367830 (9 digits after +) must pass."""
        assert validate_phone("+376367830") == "+376367830"

    def test_japan_international(self) -> None:
        assert validate_phone("+819012345678") == "+819012345678"

    def test_us_international(self) -> None:
        assert validate_phone("+15551234567") == "+15551234567"

    def test_minimum_6_digits(self) -> None:
        """E.164 minimum: country code (1) + subscriber (5) = 6 digits."""
        assert validate_phone("+123456") == "+123456"

    def test_maximum_15_digits(self) -> None:
        """E.164 maximum: 15 digits."""
        assert validate_phone("+123456789012345") == "+123456789012345"

    def test_too_short_5_digits_rejected(self) -> None:
        """5 digits after + is below E.164 minimum."""
        with pytest.raises(ValueError):
            validate_phone("+12345")

    def test_too_long_16_digits_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_phone("+1234567890123456")

    def test_strips_formatting(self) -> None:
        """Spaces, hyphens, and parentheses are stripped before validation."""
        assert validate_phone("+81 90-1234-5678") == "+819012345678"
        assert validate_phone("+1 (555) 123-4567") == "+15551234567"


class TestValidatePhoneLegacyCompat:
    """Pattern 2: \\d{10,15} (legacy DB values without +)."""

    def test_us_without_plus(self) -> None:
        """ADR-126 AC: 15551234567 (11 digits, no +) must pass."""
        assert validate_phone("15551234567") == "15551234567"

    def test_10_digits(self) -> None:
        assert validate_phone("1234567890") == "1234567890"

    def test_15_digits(self) -> None:
        assert validate_phone("123456789012345") == "123456789012345"


class TestValidatePhoneJapanDomestic:
    """Pattern 3: 0\\d{9,10} (Japan domestic)."""

    def test_mobile(self) -> None:
        """ADR-126 AC: 09012345678 must pass."""
        assert validate_phone("09012345678") == "09012345678"

    def test_landline(self) -> None:
        assert validate_phone("0312345678") == "0312345678"

    def test_with_hyphens(self) -> None:
        assert validate_phone("090-1234-5678") == "09012345678"

    def test_too_short(self) -> None:
        with pytest.raises(ValueError):
            validate_phone("012345678")


class TestValidatePhoneRejections:
    """Values that should be rejected."""

    def test_too_short_12345(self) -> None:
        """ADR-126 AC: 12345 (5 digits) must be rejected."""
        with pytest.raises(ValueError):
            validate_phone("12345")

    def test_empty_string(self) -> None:
        """Empty string should raise."""
        with pytest.raises(ValueError):
            validate_phone("")

    def test_none_returns_none(self) -> None:
        assert validate_phone(None) is None

    def test_letters_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_phone("abcdefghij")

    def test_plus_only_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_phone("+")

    def test_9_digits_no_leading_zero_rejected(self) -> None:
        """9 digits without leading 0 or + doesn't match any pattern."""
        with pytest.raises(ValueError):
            validate_phone("123456789")


class TestRegisterRequestFields:
    """ADR-126: RegisterRequest has billing_display_name and payment_recipient_name."""

    def test_fields_exist(self) -> None:
        from app.schemas.registration_token import RegisterRequest

        fields = RegisterRequest.model_fields
        assert "billing_display_name" in fields
        assert "payment_recipient_name" in fields

    def test_optional_fields(self) -> None:
        """Both fields should be optional (None by default)."""
        from app.schemas.registration_token import RegisterRequest

        req = RegisterRequest(
            token="test-token",
            contact_name="Test User",
            contact_email="test@example.com",
        )
        assert req.billing_display_name is None
        assert req.payment_recipient_name is None

    def test_fields_accept_values(self) -> None:
        from app.schemas.registration_token import RegisterRequest

        req = RegisterRequest(
            token="test-token",
            contact_name="Test User",
            contact_email="test@example.com",
            billing_display_name="My Store Inc.",
            payment_recipient_name="John Doe",
        )
        assert req.billing_display_name == "My Store Inc."
        assert req.payment_recipient_name == "John Doe"
