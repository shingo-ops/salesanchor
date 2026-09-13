"""_save_attachment_to_disk のユニットテスト。

実ネットワーク・実ファイルシステムを使わず httpx と Path.write_bytes を
monkeypatch で差し替える。
"""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.discord_gateway.ticket_channel_writer import _save_attachment_to_disk


# ---------------------------------------------------------------------------
# ヘルパー: httpx.AsyncClient のモック
# ---------------------------------------------------------------------------

def _make_response(status_code: int, content: bytes = b"", content_type: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.headers = {"content-type": content_type} if content_type else {}
    return resp


def _patch_httpx(response: MagicMock):
    """httpx.AsyncClient.get を差し替えるコンテキストマネージャを返す。"""
    client_mock = AsyncMock()
    client_mock.__aenter__ = AsyncMock(return_value=client_mock)
    client_mock.__aexit__ = AsyncMock(return_value=False)
    client_mock.get = AsyncMock(return_value=response)
    return patch(
        "app.discord_gateway.ticket_channel_writer.httpx.AsyncClient",
        return_value=client_mock,
    )


# ---------------------------------------------------------------------------
# テスト
# ---------------------------------------------------------------------------

import app.discord_gateway.ticket_channel_writer as _writer_mod


def _patch_root(monkeypatch, tmp_path: Path):
    """_ATTACHMENT_ROOT モジュール変数を tmp_path に差し替える。"""
    monkeypatch.setattr(_writer_mod, "_ATTACHMENT_ROOT", str(tmp_path))


@pytest.mark.asyncio
async def test_save_attachment_success(tmp_path: Path, monkeypatch):
    """200 レスポンスで (rel_path, bytes, content_type) を返す。"""
    _patch_root(monkeypatch, tmp_path)
    content = b"fake-image-data"
    resp = _make_response(200, content, "image/png")

    with _patch_httpx(resp):
        rel_path, size, ctype = await _save_attachment_to_disk(
            tenant_id=1,
            lead_id=42,
            message_id="msg001",
            url="https://cdn.discordapp.com/attachments/x/y/img.png",
            filename="img.png",
        )

    assert rel_path == "tenant_001/lead_42/msg001.png"
    assert size == len(content)
    assert ctype == "image/png"
    saved = tmp_path / "tenant_001" / "lead_42" / "msg001.png"
    assert saved.exists()
    assert saved.read_bytes() == content


@pytest.mark.asyncio
async def test_save_attachment_404_returns_none(tmp_path: Path, monkeypatch):
    """404 レスポンスで (None, None, None) を返す（例外は上げない）。"""
    _patch_root(monkeypatch, tmp_path)
    resp = _make_response(404)

    with _patch_httpx(resp):
        result = await _save_attachment_to_disk(
            tenant_id=1,
            lead_id=42,
            message_id="msg002",
            url="https://cdn.discordapp.com/x",
            filename="img.png",
        )

    assert result == (None, None, None)


@pytest.mark.asyncio
async def test_save_attachment_exception_returns_none(tmp_path: Path, monkeypatch):
    """ネットワーク例外で (None, None, None) を返す（例外は上げない）。"""
    _patch_root(monkeypatch, tmp_path)

    client_mock = AsyncMock()
    client_mock.__aenter__ = AsyncMock(return_value=client_mock)
    client_mock.__aexit__ = AsyncMock(return_value=False)
    client_mock.get = AsyncMock(side_effect=Exception("network error"))

    with patch(
        "app.discord_gateway.ticket_channel_writer.httpx.AsyncClient",
        return_value=client_mock,
    ):
        result = await _save_attachment_to_disk(
            tenant_id=1,
            lead_id=42,
            message_id="msg003",
            url="https://cdn.discordapp.com/x",
            filename="img.png",
        )

    assert result == (None, None, None)


@pytest.mark.asyncio
async def test_save_attachment_extension_extraction(tmp_path: Path, monkeypatch):
    """ファイル名の拡張子が正しく rel_path に含まれる（.jpg）。"""
    _patch_root(monkeypatch, tmp_path)
    resp = _make_response(200, b"jpeg-data", "image/jpeg")

    with _patch_httpx(resp):
        rel_path, _, _ = await _save_attachment_to_disk(
            tenant_id=3,
            lead_id=99,
            message_id="msgABC",
            url="https://cdn.discordapp.com/x",
            filename="photo.jpg",
        )

    assert rel_path == "tenant_003/lead_99/msgABC.jpg"


@pytest.mark.asyncio
async def test_save_attachment_no_filename_gives_no_ext(tmp_path: Path, monkeypatch):
    """filename=None のとき rel_path に拡張子が付かない。"""
    _patch_root(monkeypatch, tmp_path)
    resp = _make_response(200, b"data", "application/octet-stream")

    with _patch_httpx(resp):
        rel_path, _, _ = await _save_attachment_to_disk(
            tenant_id=5,
            lead_id=7,
            message_id="msgXYZ",
            url="https://cdn.discordapp.com/x",
            filename=None,
        )

    assert rel_path == "tenant_005/lead_7/msgXYZ"
