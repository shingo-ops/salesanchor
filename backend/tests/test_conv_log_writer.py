"""SA-02 Stage 1: conv_log_writer の単体テスト。

検証項目:
  1. モジュールの import が通る（循環依存なし）
  2. write_conversation_log のシグネチャが設計 doc と合致している
  3. 冪等キー: ON CONFLICT 節が SQL に含まれる（grep 検証）
  4. direction バリデーション: 'inbound' / 'outbound' 以外の値をスキップできる構造か
  5. _get_company_id_for_lead: AsyncMock で None を返す（案件なしの場合）
  6. _get_contact_id_for_lead: AsyncMock で None を返す（contact なしの場合）
  7. _get_contact_id_for_lead: contact がある場合 id を返す
  8. write_conversation_log: AsyncMock セッションで正常パスが通る
  9. write_conversation_log: 重複（RETURNING id が NULL）のとき None を返す
  10. write_conversation_log: lead_id=None でも company_id / contact_id 検索を呼ばない
  11. write_conversation_log: 呼び出し元が contact_id を明示した場合はそのまま INSERT される
  12. write_conversation_log: contact_id 省略時に _get_contact_id_for_lead が呼ばれる

実行:
    pytest backend/tests/test_conv_log_writer.py -v
"""
from __future__ import annotations

import inspect
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. インポートが通る
# ---------------------------------------------------------------------------
def test_import():
    from app.services.conv_log_writer import (
        write_conversation_log,
        _get_company_id_for_lead,
        _get_contact_id_for_lead,
    )
    assert callable(write_conversation_log)
    assert callable(_get_company_id_for_lead)
    assert callable(_get_contact_id_for_lead)


# ---------------------------------------------------------------------------
# 2. write_conversation_log のシグネチャ確認
# ---------------------------------------------------------------------------
def test_signature_has_required_params():
    from app.services.conv_log_writer import write_conversation_log

    sig = inspect.signature(write_conversation_log)
    params = set(sig.parameters.keys())
    required = {
        "db", "tenant_id", "lead_id", "channel_type",
        "direction", "occurred_at",
    }
    assert required.issubset(params), f"不足パラメータ: {required - params}"
    assert "contact_id" in params, "contact_id パラメータがない"


# ---------------------------------------------------------------------------
# 3. ON CONFLICT 節が SQL に含まれる（冪等保証の静的確認）
# ---------------------------------------------------------------------------
def test_sql_has_on_conflict():
    src = (
        Path(__file__).resolve().parents[1]
        / "app" / "services" / "conv_log_writer.py"
    )
    content = src.read_text(encoding="utf-8")
    assert "ON CONFLICT (external_message_id)" in content
    assert "DO NOTHING" in content
    assert "contact_id" in content


# ---------------------------------------------------------------------------
# 4. direction は 'inbound' / 'outbound' が使用される
# ---------------------------------------------------------------------------
def test_direction_values_in_callers():
    """webhook.py と dm_writer.py で正しい direction・エラーログが実装されているか grep で確認。"""
    repo_root = Path(__file__).resolve().parents[2]

    webhook_py = repo_root / "backend" / "app" / "routers" / "webhook.py"
    content = webhook_py.read_text(encoding="utf-8")
    assert 'direction="inbound"' in content, "webhook.py: inbound が見当たらない"
    assert 'direction="outbound"' in content, "webhook.py: outbound（エコー）が見当たらない"
    # エラーログにチャネル・ext_id が含まれていること
    assert "channel=%s" in content, "webhook.py: エラーログにチャネル情報がない"
    assert "ext_id=%s" in content, "webhook.py: エラーログに ext_id がない"

    dm_writer_py = repo_root / "backend" / "app" / "discord_gateway" / "dm_writer.py"
    dm_content = dm_writer_py.read_text(encoding="utf-8")
    assert 'direction="inbound"' in dm_content, "dm_writer.py: inbound が見当たらない"
    assert "ext_id=%s" in dm_content, "dm_writer.py: エラーログに ext_id がない"


# ---------------------------------------------------------------------------
# 5. _get_company_id_for_lead: 案件なしのとき None を返す
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_company_id_no_deal():
    from app.services.conv_log_writer import _get_company_id_for_lead

    mock_result = MagicMock()
    mock_result.first.return_value = None

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    result = await _get_company_id_for_lead(db, lead_id=42)
    assert result is None


# ---------------------------------------------------------------------------
# 6. _get_contact_id_for_lead: contact なしのとき None を返す
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_contact_id_no_contact():
    from app.services.conv_log_writer import _get_contact_id_for_lead

    mock_result = MagicMock()
    mock_result.first.return_value = None

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    result = await _get_contact_id_for_lead(db, lead_id=42)
    assert result is None


# ---------------------------------------------------------------------------
# 7. _get_contact_id_for_lead: contact がある場合 id を返す
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_contact_id_found():
    from app.services.conv_log_writer import _get_contact_id_for_lead

    mock_result = MagicMock()
    mock_result.first.return_value = (55,)  # contacts.id = 55

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    result = await _get_contact_id_for_lead(db, lead_id=10)
    assert result == 55


# ---------------------------------------------------------------------------
# 8. write_conversation_log: 正常パス（新規挿入）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_write_conversation_log_success():
    from app.services.conv_log_writer import write_conversation_log

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = 101  # 挿入された id

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    with (
        patch(
            "app.services.conv_log_writer._get_company_id_for_lead",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.services.conv_log_writer._get_contact_id_for_lead",
            new=AsyncMock(return_value=None),
        ),
    ):
        result = await write_conversation_log(
            db,
            tenant_id=1,
            lead_id=10,
            channel_type="messenger",
            channel_identity="12345",
            direction="inbound",
            sender="12345",
            content_text="hello",
            external_message_id="mid.abc123",
            occurred_at=datetime(2026, 6, 11, 10, 0, 0, tzinfo=timezone.utc),
        )

    assert result == 101
    db.execute.assert_called_once()


# ---------------------------------------------------------------------------
# 9. write_conversation_log: 重複スキップ時は None を返す
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_write_conversation_log_duplicate_returns_none():
    from app.services.conv_log_writer import write_conversation_log

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # ON CONFLICT DO NOTHING

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    with (
        patch(
            "app.services.conv_log_writer._get_company_id_for_lead",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.services.conv_log_writer._get_contact_id_for_lead",
            new=AsyncMock(return_value=None),
        ),
    ):
        result = await write_conversation_log(
            db,
            tenant_id=1,
            lead_id=10,
            channel_type="messenger",
            channel_identity="12345",
            direction="inbound",
            sender="12345",
            content_text="hello",
            external_message_id="mid.abc123",  # 重複 id
            occurred_at=datetime(2026, 6, 11, 10, 0, 0, tzinfo=timezone.utc),
        )

    assert result is None


# ---------------------------------------------------------------------------
# 10. write_conversation_log: lead_id=None で両ヘルパーを呼ばない
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_write_conversation_log_no_lead_id():
    from app.services.conv_log_writer import write_conversation_log

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = 200

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    with (
        patch(
            "app.services.conv_log_writer._get_company_id_for_lead",
            new=AsyncMock(return_value=None),
        ) as mock_get_company,
        patch(
            "app.services.conv_log_writer._get_contact_id_for_lead",
            new=AsyncMock(return_value=None),
        ) as mock_get_contact,
    ):
        await write_conversation_log(
            db,
            tenant_id=1,
            lead_id=None,
            channel_type="messenger",
            channel_identity="unknown",
            direction="inbound",
            occurred_at=datetime(2026, 6, 11, 10, 0, 0, tzinfo=timezone.utc),
        )

    mock_get_company.assert_not_called()
    mock_get_contact.assert_not_called()


# ---------------------------------------------------------------------------
# 11. write_conversation_log: 呼び出し元が contact_id を明示した場合はそのまま渡される
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_write_conversation_log_explicit_contact_id():
    from app.services.conv_log_writer import write_conversation_log

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = 300

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    with (
        patch(
            "app.services.conv_log_writer._get_company_id_for_lead",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.services.conv_log_writer._get_contact_id_for_lead",
            new=AsyncMock(return_value=None),
        ) as mock_get_contact,
    ):
        await write_conversation_log(
            db,
            tenant_id=1,
            lead_id=10,
            channel_type="messenger",
            direction="inbound",
            occurred_at=datetime(2026, 6, 11, 10, 0, 0, tzinfo=timezone.utc),
            contact_id=77,  # 明示
        )

    # 明示した場合は自動解決ヘルパーを呼ばない
    mock_get_contact.assert_not_called()
    # INSERT に contact_id=77 が渡されている
    call_params = db.execute.call_args[0][1]
    assert call_params["contact_id"] == 77


# ---------------------------------------------------------------------------
# 12. write_conversation_log: contact_id 省略時に _get_contact_id_for_lead が呼ばれる
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_write_conversation_log_auto_resolves_contact_id():
    from app.services.conv_log_writer import write_conversation_log

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = 400

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    with (
        patch(
            "app.services.conv_log_writer._get_company_id_for_lead",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.services.conv_log_writer._get_contact_id_for_lead",
            new=AsyncMock(return_value=88),
        ) as mock_get_contact,
    ):
        await write_conversation_log(
            db,
            tenant_id=1,
            lead_id=10,
            channel_type="messenger",
            direction="inbound",
            occurred_at=datetime(2026, 6, 11, 10, 0, 0, tzinfo=timezone.utc),
            # contact_id 省略
        )

    mock_get_contact.assert_called_once()
    # INSERT に自動解決された contact_id=88 が渡されている
    call_params = db.execute.call_args[0][1]
    assert call_params["contact_id"] == 88
