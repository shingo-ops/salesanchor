"""
async 経路の同期 I/O がイベントループを塞がないことの検証。

方式: 重い処理を time.sleep(0.3) に差し替え、対象コルーチンと
「0.01 秒ごとに数えるコルーチン」を asyncio.gather で同時に走らせる。
ループが塞がれていなければ 0.3 秒の間に 10 回以上数えられる。
"""

from __future__ import annotations

import asyncio
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

from cryptography.fernet import Fernet

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("METADATA_FERNET_KEY", Fernet.generate_key().decode())

BLOCK_SECONDS = 0.3
TICK_SECONDS = 0.01
MIN_TICKS = 10


def _slow(result=None):
    """BLOCK_SECONDS 同期スリープして result を返す関数。"""

    def _fn(*_args, **_kwargs):
        time.sleep(BLOCK_SECONDS)
        return result

    return _fn


async def _ticker(stop: asyncio.Event) -> int:
    count = 0
    while not stop.is_set():
        await asyncio.sleep(TICK_SECONDS)
        count += 1
    return count


async def _count_ticks_during(coro) -> int:
    """coro の実行中にループが回った回数を返す。"""
    stop = asyncio.Event()

    async def _runner():
        try:
            await coro
        finally:
            stop.set()

    ticks, _ = await asyncio.gather(_ticker(stop), _runner())
    return ticks


async def test_submit_contact_does_not_block_loop():
    from app.routers.contact import submit_contact

    data = MagicMock()
    with patch("app.routers.contact._send_notification", _slow()):
        ticks = await _count_ticks_during(submit_contact(data))

    assert ticks >= MIN_TICKS


async def test_render_po_pdf_for_does_not_block_loop():
    from app.services.po_renderer import render_po_pdf_for

    with patch(
        "app.services.po_renderer.gather_po_render_data",
        AsyncMock(return_value=MagicMock()),
    ), patch("app.services.po_renderer.render_po_pdf", _slow(b"%PDF")):
        ticks = await _count_ticks_during(render_po_pdf_for(MagicMock(), 1, "tenant_001"))

    assert ticks >= MIN_TICKS


async def test_get_events_does_not_block_loop():
    from app.services.google_calendar import get_events

    service = MagicMock()
    service.events.return_value.list.return_value.execute = _slow({"items": []})

    with patch(
        "app.services.google_calendar._get_service", AsyncMock(return_value=service)
    ), patch(
        "app.services.google_calendar.get_calendar_id", AsyncMock(return_value="primary")
    ):
        ticks = await _count_ticks_during(
            get_events(MagicMock(), 1, time_min="2026-01-01T00:00:00Z", time_max="2026-01-31T00:00:00Z")
        )

    assert ticks >= MIN_TICKS


async def test_upload_pdf_does_not_block_loop():
    from app.services.google_drive_oauth import upload_pdf

    service = MagicMock()
    service.files.return_value.create.return_value.execute = _slow({"id": "f1", "name": "a.pdf"})

    with patch(
        "app.services.google_drive_oauth._get_drive_service", AsyncMock(return_value=service)
    ):
        ticks = await _count_ticks_during(upload_pdf(MagicMock(), 1, b"%PDF", "a.pdf"))

    assert ticks >= MIN_TICKS


async def test_handle_webhook_notification_does_not_block_loop():
    from app.services.google_webhook import handle_webhook_notification

    service = MagicMock()
    service.events.return_value.list.return_value.execute = _slow({"items": []})

    with patch(
        "app.services.google_webhook.get_tenant_by_channel",
        AsyncMock(return_value=(1, "tenant_001")),
    ), patch(
        "app.services.google_webhook.set_tenant_context", AsyncMock()
    ), patch(
        "app.services.google_calendar._get_service", AsyncMock(return_value=service)
    ):
        ticks = await _count_ticks_during(
            handle_webhook_notification(MagicMock(), "ch1", "exists")
        )

    assert ticks >= MIN_TICKS


async def test_import_line_export_android_parse_does_not_block_loop():
    from app.services.tcg_line_import_svc import import_line_export

    async def _execute(stmt, params=None):
        result = MagicMock()
        result.fetchone.return_value = None
        result.fetchall.return_value = []
        return result

    db = MagicMock()
    db.execute = _execute
    db.commit = AsyncMock()

    with patch("app.services.tcg_line_import_svc.parse_android_export", _slow([])):
        ticks = await _count_ticks_during(
            import_line_export(
                db=db,
                filename="test.txt",
                export_text="x",
                uploaded_by=None,
                window_hours=0,
                source_format="android",
            )
        )

    assert ticks >= MIN_TICKS


async def test_get_current_user_verify_id_token_does_not_block_loop():
    from fastapi import HTTPException

    from app.auth.dependencies import get_current_user

    request = MagicMock()
    cred = MagicMock()
    cred.credentials = "tok"

    with patch("app.auth.dependencies._init_firebase"), patch(
        "app.auth.dependencies._get_client_ip", return_value="1.2.3.4"
    ), patch("app.auth.dependencies._SMOKE_SERVICE_TOKEN", ""), patch(
        "app.auth.dependencies.is_token_blacklisted", AsyncMock(return_value=False)
    ), patch(
        "app.auth.dependencies.get_cached_jwt", AsyncMock(return_value=None)
    ), patch(
        "app.auth.dependencies.check_auth_rate_limit", AsyncMock(return_value=False)
    ), patch(
        "app.auth.dependencies.record_auth_failure", AsyncMock()
    ), patch(
        "app.auth.dependencies.firebase_auth.verify_id_token", _slow({})
    ):

        async def _call():
            try:
                await get_current_user(request, cred, MagicMock())
            except HTTPException:
                pass  # verify 後の処理は対象外。判定はティック数のみ。

        ticks = await _count_ticks_during(_call())

    assert ticks >= MIN_TICKS
