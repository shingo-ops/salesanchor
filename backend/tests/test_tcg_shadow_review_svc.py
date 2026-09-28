"""tcg_shadow_review_svc の単体テスト（DB はモック、design.md PR-D）。"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.services.tcg_shadow_review_svc import (
    KeywordPreviewProductNotFound,
    fetch_bottlenecks,
    fetch_shadow_results,
    preview_keyword_change,
)

pytestmark = pytest.mark.asyncio


class _Row:
    """dict風アクセス(row["k"])と属性アクセス(row.k)の両方に対応する簡易フェイク行。"""

    def __init__(self, **kw):
        self._kw = kw
        for k, v in kw.items():
            setattr(self, k, v)

    def __getitem__(self, key):
        return self._kw[key]

    def get(self, key, default=None):
        return self._kw.get(key, default)


class _Mappings:
    def __init__(self, rows):
        self._rows = rows

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def mappings(self):
        return _Mappings(self._rows)


def _mock_db(results: list[_Result]) -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=results)
    return db


class TestFetchShadowResults:
    async def test_returns_items_with_block_text_and_candidate_names(self):
        # Arrange
        count_result = _Result([_Row(total=1)])
        main_result = _Result(
            [
                _Row(
                    id="r1", line_start=1, line_end=1, raw_product_name="商品A",
                    raw_price="100円", raw_unit="枚", raw_quantity="1", raw_state="未使用",
                    raw_ship="none", match_status="ambiguous", product_id=None, work_id=None,
                    review_items=[{"item": "product", "reason": "候補2件", "candidates": [1, 2]}],
                    needs_review=True, created_at=datetime(2026, 9, 28, tzinfo=timezone.utc),
                    raw_text="商品A", supplier_id=5, supplier_name="仕入元A",
                )
            ]
        )
        names_result = _Result([_Row(id=1, name="商品X"), _Row(id=2, name="商品Y")])
        db = _mock_db([count_result, main_result, names_result])

        # Act
        result = await fetch_shadow_results(db, needs_review=True, offset=0, limit=20)

        # Assert
        assert result["total"] == 1
        item = result["items"][0]
        assert item["block_text"] == "商品A"
        assert item["review_items"][0]["candidates"] == [
            {"product_id": 1, "product_name": "商品X"},
            {"product_id": 2, "product_name": "商品Y"},
        ]
        assert item["supplier_name"] == "仕入元A"

    async def test_no_candidates_skips_name_lookup(self):
        # Arrange
        count_result = _Result([_Row(total=0)])
        main_result = _Result([])
        db = _mock_db([count_result, main_result])

        # Act
        result = await fetch_shadow_results(db)

        # Assert
        assert result["items"] == []
        assert result["total"] == 0
        assert db.execute.await_count == 2  # 商品名クエリは呼ばれない


class TestFetchBottlenecks:
    async def test_returns_supplier_and_item_breakdown(self):
        # Arrange
        by_supplier = _Result(
            [_Row(supplier_id=1, supplier_name="仕入元A", total=10, matched=6, needs_review_count=4)]
        )
        by_item = _Result(
            [_Row(supplier_id=1, supplier_name="仕入元A", item="product", count=3)]
        )
        db = _mock_db([by_supplier, by_item])

        # Act
        result = await fetch_bottlenecks(db, days=7)

        # Assert
        assert result["days"] == 7
        assert result["by_supplier"][0]["matched_ratio"] == 0.6
        assert result["by_item"][0]["item"] == "product"


class TestPreviewKeywordChange:
    async def test_no_db_write_and_counts_transitions(self):
        # Arrange: 商品1件・ブロック1件（unmatched -> matched に変わる想定）
        products_result = _Result(
            [
                _Row(
                    id=1, product_code=None, mark=None, work_id=None,
                    search_keywords=(), exclude_keywords=(),
                )
            ]
        )
        blocks_result = _Result(
            [_Row(line_start=1, line_end=1, match_status="unmatched", raw_text="商品A")]
        )
        db = _mock_db([products_result, blocks_result])

        # Act
        result = await preview_keyword_change(db, product_id=1, kind="search", keyword="商品A")

        # Assert
        assert result["checked"] == 1
        assert result["transitions"] == {"unmatched→matched": 1}
        db.commit.assert_not_called()

    async def test_product_not_found_raises(self):
        # Arrange
        products_result = _Result([])
        db = _mock_db([products_result])

        # Act / Assert
        with pytest.raises(KeywordPreviewProductNotFound):
            await preview_keyword_change(db, product_id=999, kind="search", keyword="x")

    async def test_empty_keyword_raises_value_error(self):
        # Arrange
        db = _mock_db([])

        # Act / Assert
        with pytest.raises(ValueError):
            await preview_keyword_change(db, product_id=1, kind="search", keyword="   ")
