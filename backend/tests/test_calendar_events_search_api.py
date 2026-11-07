from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.routers.calendar import search_events


@pytest.mark.asyncio
async def test_a1_search_passes_trimmed_query_and_no_range():
    user = SimpleNamespace(id=7)
    db = MagicMock()
    with patch("app.routers.calendar.cal_svc.list_events", new=AsyncMock(return_value=[{"id": 1}])) as mock_list:
        result = await search_events(q="  商談 ", tenant_id=1, user=user, db=db)
    assert result == {"events": [{"id": 1}]}
    mock_list.assert_awaited_once()
    kwargs = mock_list.await_args.kwargs
    assert kwargs["title_query"] == "商談"
    assert kwargs["limit"] == 50
    assert kwargs["user_id"] == 7
    assert "start" not in kwargs
    assert "end" not in kwargs


@pytest.mark.asyncio
async def test_a2_blank_query_is_422():
    user = SimpleNamespace(id=7)
    with pytest.raises(HTTPException) as exc:
        await search_events(q="   ", tenant_id=1, user=user, db=MagicMock())
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_a3_length_limit_101_rejected_100_ok():
    user = SimpleNamespace(id=7)
    with pytest.raises(HTTPException) as exc:
        await search_events(q="あ" * 101, tenant_id=1, user=user, db=MagicMock())
    assert exc.value.status_code == 422
    with patch("app.routers.calendar.cal_svc.list_events", new=AsyncMock(return_value=[])):
        result = await search_events(q="あ" * 100, tenant_id=1, user=user, db=MagicMock())
    assert result == {"events": []}
