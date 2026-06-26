"""
lang_judge.judge_recipient_language のユニットテスト。

テスト一覧:
  - test_judge_returns_confident_en_when_3_en_records: 英語 3 件 → confident=True, language="en"
  - test_judge_returns_confident_ja_when_3_ja_records: 日本語 3 件 → confident=True, language="ja"
  - test_judge_returns_not_confident_when_2_records: 2 件以下 → confident=False, language=None
  - test_judge_returns_empty_when_no_records: 0 件 → confident=False, language=None, total_records=0
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_db_execute_mock(first_row, total_count: int) -> AsyncMock:
    """db.execute() の返値を差し替えるヘルパー。

    judge_recipient_language は execute() を 2 回呼ぶ:
      1 回目: 多数派言語取得 → first_row を返す
      2 回目: 全件カウント取得 → total_count を返す
    """
    call_count = 0

    async def fake_execute(query, params=None):
        nonlocal call_count
        call_count += 1
        result_mock = MagicMock()
        if call_count == 1:
            # 1回目: 多数派言語 (language, cnt) を返す
            result_mock.first.return_value = first_row
        else:
            # 2回目: 全件カウントを返す
            total_row_mock = MagicMock()
            total_row_mock.__getitem__ = lambda _, i: total_count
            result_mock.first.return_value = total_row_mock
        return result_mock

    db = AsyncMock()
    db.execute.side_effect = fake_execute
    return db


@pytest.mark.asyncio
async def test_judge_returns_confident_en_when_3_en_records():
    """英語 inbound が 3 件あれば confident=True, language='en' を返す。"""
    from app.services.lang_judge import judge_recipient_language

    first_row = MagicMock()
    first_row.__getitem__ = lambda _, i: "en"  # row[0] = language
    db = _make_db_execute_mock(first_row=first_row, total_count=3)

    result = await judge_recipient_language(db=db, tenant_id=6, lead_id=1)

    assert result.language == "en"
    assert result.total_records == 3
    assert result.confident is True


@pytest.mark.asyncio
async def test_judge_returns_confident_ja_when_3_ja_records():
    """日本語 inbound が 3 件あれば confident=True, language='ja' を返す。"""
    from app.services.lang_judge import judge_recipient_language

    first_row = MagicMock()
    first_row.__getitem__ = lambda _, i: "ja"
    db = _make_db_execute_mock(first_row=first_row, total_count=5)

    result = await judge_recipient_language(db=db, tenant_id=6, lead_id=2)

    assert result.language == "ja"
    assert result.total_records == 5
    assert result.confident is True


@pytest.mark.asyncio
async def test_judge_returns_not_confident_when_2_records():
    """inbound が 2 件以下なら confident=False, language=None を返す。"""
    from app.services.lang_judge import judge_recipient_language

    first_row = MagicMock()
    first_row.__getitem__ = lambda _, i: "en"
    db = _make_db_execute_mock(first_row=first_row, total_count=2)

    result = await judge_recipient_language(db=db, tenant_id=6, lead_id=3)

    assert result.language is None
    assert result.total_records == 2
    assert result.confident is False


@pytest.mark.asyncio
async def test_judge_returns_empty_when_no_records():
    """inbound が 0 件なら language=None, total_records=0, confident=False を返す。

    execute().first() が None を返すケース（UNION ALL 結果が空）。
    """
    from app.services.lang_judge import judge_recipient_language

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.first.return_value = None  # 0件
    db.execute.return_value = result_mock

    result = await judge_recipient_language(db=db, tenant_id=6, lead_id=4)

    assert result.language is None
    assert result.total_records == 0
    assert result.confident is False
    # 0件時は2回目のexecuteは呼ばれない
    assert db.execute.call_count == 1
