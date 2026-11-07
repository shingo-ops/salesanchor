from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from app.routers.calendar import list_holidays


@pytest.mark.asyncio
async def test_a1_november_returns_two():
    result = await list_holidays(start=date(2026, 11, 1), end=date(2026, 12, 1), lang="ja", tenant_id=1)
    assert [h["date"] for h in result["holidays"]] == ["2026-11-03", "2026-11-23"]


@pytest.mark.asyncio
async def test_a2_end_not_after_start_is_422():
    with pytest.raises(HTTPException) as exc:
        await list_holidays(start=date(2026, 11, 5), end=date(2026, 11, 5), lang="ja", tenant_id=1)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_a3_range_limit_401_rejected_400_ok():
    start = date(2026, 1, 1)
    with pytest.raises(HTTPException) as exc:
        await list_holidays(start=start, end=start + timedelta(days=401), lang="ja", tenant_id=1)
    assert exc.value.status_code == 422
    result = await list_holidays(start=start, end=start + timedelta(days=400), lang="ja", tenant_id=1)
    assert len(result["holidays"]) > 0
