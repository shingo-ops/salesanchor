"""Tests for tcg_work_reference validate functions — partial success behaviour."""
from __future__ import annotations

import pytest

from app.services.tcg_work_reference import validate_product_code, validate_work_id

REFERENCE = {
    "works": [{"id": 1, "name": "Pokemon"}, {"id": 2, "name": "One Piece"}],
    "products": [{"code": "PKM-001", "name": "Test"}, {"code": "OP-001", "name": "Test2"}],
}


# ---------------------------------------------------------------------------
# validate_work_id
# ---------------------------------------------------------------------------


def test_validate_work_id_valid_returns_int():
    assert validate_work_id(1, REFERENCE) == 1


def test_validate_work_id_string_valid_returns_int():
    assert validate_work_id("2", REFERENCE) == 2


def test_validate_work_id_none_returns_none():
    assert validate_work_id(None, REFERENCE) is None


def test_validate_work_id_empty_string_returns_none():
    assert validate_work_id("", REFERENCE) is None


def test_validate_work_id_missing_returns_none():
    """work_id not in reference must return None instead of raising."""
    result = validate_work_id(999, REFERENCE)
    assert result is None


def test_validate_work_id_non_integer_returns_none():
    """Non-integer string must return None instead of raising."""
    result = validate_work_id("abc", REFERENCE)
    assert result is None


def test_validate_work_id_missing_does_not_raise():
    """Regression: ValueError must no longer propagate."""
    try:
        validate_work_id(99999, REFERENCE)
    except ValueError:
        pytest.fail("validate_work_id raised ValueError for missing ID — partial success broken")


# ---------------------------------------------------------------------------
# validate_product_code
# ---------------------------------------------------------------------------


def test_validate_product_code_valid_returns_code():
    assert validate_product_code("PKM-001", REFERENCE) == "PKM-001"


def test_validate_product_code_none_returns_none():
    assert validate_product_code(None, REFERENCE) is None


def test_validate_product_code_empty_returns_none():
    assert validate_product_code("", REFERENCE) is None


def test_validate_product_code_missing_returns_none():
    """product_code not in reference must return None instead of raising."""
    result = validate_product_code("NONEXISTENT-999", REFERENCE)
    assert result is None


def test_validate_product_code_missing_does_not_raise():
    """Regression: ValueError must no longer propagate."""
    try:
        validate_product_code("DOES-NOT-EXIST", REFERENCE)
    except ValueError:
        pytest.fail("validate_product_code raised ValueError for missing code — partial success broken")
