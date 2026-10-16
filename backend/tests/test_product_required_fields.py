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


# ---------------------------------------------------------------------------
# ADR-1020 便3: 新規登録と「空に戻す」更新を止める
# ---------------------------------------------------------------------------


def _create_args(**changes) -> dict:
    args = {
        "japanese_title": "商品", "english_title": "Product", "mark": "SV1", "release_date": "2026-01-01",
        "search_keywords": "a,b", "exclude_keywords": "c", "work_id": 1, "product_format_id": 2,
        "product_category_id": 3, "blank_confirmations": [],
    }
    args.update(changes)
    return args


def test_missing_for_create_lists_all_missing_in_order():
    from app.services.tcg_product_master_svc import missing_for_create

    assert missing_for_create({}) == list(REQUIRED_FIELDS)


def test_missing_for_create_accepts_blank_confirmations():
    from app.services.tcg_product_master_svc import missing_for_create

    args = _create_args(
        english_title="", mark="", release_date=None, exclude_keywords="",
        blank_confirmations=["name_en", "mark", "release_date", "exclude_keywords"],
    )
    assert missing_for_create(args) == []


def test_find_cleared_fields_only_newly_missing():
    from app.services.tcg_product_master_svc import find_cleared_fields

    before = {**_all_filled(), "mark": "SV1", "name_en": ""}
    after = {**_all_filled(), "mark": "", "name_en": ""}
    assert find_cleared_fields(before, [], after, []) == ["mark"]


def test_find_cleared_fields_mark_keeps_blank():
    from app.services.tcg_product_master_svc import find_cleared_fields

    before = _all_filled()
    after = {**_all_filled(), "exclude_keywords": []}
    assert find_cleared_fields(before, [], after, ["exclude_keywords"]) == []


@pytest.mark.asyncio
async def test_create_product_rejects_missing_before_db():
    from unittest.mock import AsyncMock

    from app.services import tcg_product_master_svc as master

    db = AsyncMock()
    with pytest.raises(ValueError) as error:
        await master.create_product(
            db, extraction_item_id="", source_message_id="", product_kind_id=1, work_id=1,
            manufacturer_id="m", product_category_id="c", japanese_title="商品",
            release_date="2026-01-01", search_keywords="a", exclude_keywords="b", mark="SV1",
            english_title="", product_format_id=None,
        )
    message = str(error.value)
    assert message.startswith("REQUIRED_FIELDS_MISSING:name_en,")
    assert "product_format_id" in message
    db.execute.assert_not_called()
