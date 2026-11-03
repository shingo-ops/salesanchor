"""Google カレンダー知らせの受け口（receive_webhook）の試験（ADR-1059 便2）。

合言葉が合うと取り込み作業を Celery に積み、合わない・sync は積まない。常に 200。
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("METADATA_FERNET_KEY", Fernet.generate_key().decode())


def _request(headers: dict):
    req = MagicMock()
    req.headers = headers
    return req


@pytest.mark.asyncio
async def test_matching_token_enqueues_and_returns_200():
    from app.routers.google_calendar import receive_webhook

    headers = {
        "X-Goog-Channel-ID": "ch1",
        "X-Goog-Resource-State": "exists",
        "X-Goog-Channel-Token": "secret",
    }
    with patch(
        "app.services.google_webhook.verify_channel", AsyncMock(return_value=7)
    ) as verify, patch(
        "app.tasks.google_calendar_sync.sync_google_calendar_tenant.delay"
    ) as delay:
        resp = await receive_webhook(_request(headers), db=AsyncMock())

    assert resp.status_code == 200
    verify.assert_awaited_once()
    assert verify.await_args.args[1:] == ("ch1", "secret")
    delay.assert_called_once_with(7)


@pytest.mark.asyncio
async def test_wrong_token_does_not_enqueue_and_returns_200():
    from app.routers.google_calendar import receive_webhook

    headers = {
        "X-Goog-Channel-ID": "ch1",
        "X-Goog-Resource-State": "exists",
        "X-Goog-Channel-Token": "wrong",
    }
    with patch(
        "app.services.google_webhook.verify_channel", AsyncMock(return_value=None)
    ), patch("app.tasks.google_calendar_sync.sync_google_calendar_tenant.delay") as delay:
        resp = await receive_webhook(_request(headers), db=AsyncMock())

    assert resp.status_code == 200
    delay.assert_not_called()


@pytest.mark.asyncio
async def test_sync_state_is_ignored_and_returns_200():
    from app.routers.google_calendar import receive_webhook

    headers = {
        "X-Goog-Channel-ID": "ch1",
        "X-Goog-Resource-State": "sync",
        "X-Goog-Channel-Token": "secret",
    }
    with patch(
        "app.services.google_webhook.verify_channel", AsyncMock(return_value=7)
    ) as verify, patch(
        "app.tasks.google_calendar_sync.sync_google_calendar_tenant.delay"
    ) as delay:
        resp = await receive_webhook(_request(headers), db=AsyncMock())

    assert resp.status_code == 200
    verify.assert_not_awaited()
    delay.assert_not_called()
