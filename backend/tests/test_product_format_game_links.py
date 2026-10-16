"""ADR-1020 便2a: 細分類マスタの「使えるゲーム」の入力・応答の形（DB なし）。"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.product_format import ProductFormatGamesUpdate, ProductFormatResponse


def test_games_body_rejects_unknown_field():
    with pytest.raises(ValidationError):
        ProductFormatGamesUpdate(game_ids=[1], alias="x")


def test_games_body_limits_length():
    with pytest.raises(ValidationError):
        ProductFormatGamesUpdate(game_ids=list(range(201)))


def test_response_defaults_game_ids_empty():
    now = datetime(2026, 10, 17)
    res = ProductFormatResponse(id=1, code="c", name="n", created_at=now, updated_at=now)
    assert res.game_ids == []
