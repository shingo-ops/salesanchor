"""ADR-1020 便1: 9項目の検査関数と、入口の型（DB なし）。"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.routers.tcg_product_import import CreateProductBody, ProductDetailUpdate
from app.services.tcg_product_master_svc import REQUIRED_FIELDS, check_required_fields


def _all_filled() -> dict:
    return {
        "name": "商品", "name_en": "Product", "mark": "SV1", "release_date": "2026-01-01",
        "search_keywords": "a,b", "exclude_keywords": "a,b",
        "work_id": 1, "product_format_id": 2, "product_category_id": 3,
    }


def test_all_filled_returns_empty():
    assert check_required_fields(_all_filled(), set()) == []


def test_all_blank_returns_nine_in_order():
    assert check_required_fields({}, set()) == list(REQUIRED_FIELDS)


def test_confirmation_allows_only_four_fields():
    result = check_required_fields({}, set(REQUIRED_FIELDS))
    assert result == ["name", "search_keywords", "work_id", "product_format_id", "product_category_id"]


def test_comma_only_keywords_are_blank():
    values = _all_filled()
    values["search_keywords"] = " , "
    assert check_required_fields(values, set()) == ["search_keywords"]


def test_create_body_rejects_unknown_confirmation():
    minimal = {
        "japanese_title": "商品", "product_kind_id": "1", "work_id": "1",
        "manufacturer_id": "m", "product_category_id": "1",
    }
    CreateProductBody(**minimal, blank_confirmations=["name_en"])
    with pytest.raises(ValidationError):
        CreateProductBody(**minimal, blank_confirmations=["name"])


def test_detail_update_omits_unsent_optional_fields():
    payload = ProductDetailUpdate(
        revision="a" * 64, japanese_title="商品", english_title="", mark="",
        release_date=None, manufacturer_id=None, product_category_id=None,
        search_keywords=[], exclude_keywords=[],
    )
    assert "product_format_id" not in payload.model_fields_set
    assert "blank_confirmations" not in payload.model_fields_set
