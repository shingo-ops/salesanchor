"""_extract_first_attachment のユニットテスト。

実際の Discord 接続は不要。plain object でシミュレートする。
"""
from __future__ import annotations

import pytest

from app.discord_gateway.ticket_channel_writer import _extract_first_attachment


class _Attachment:
    def __init__(self, url: str, content_type: str) -> None:
        self.url = url
        self.content_type = content_type


class _Message:
    def __init__(self, attachments: list) -> None:
        self.attachments = attachments


def test_no_attachments_returns_none_none():
    msg = _Message(attachments=[])
    assert _extract_first_attachment(msg) == (None, None)


def test_image_png_returns_image_kind():
    att = _Attachment(url="https://cdn.discordapp.com/a.png", content_type="image/png")
    msg = _Message(attachments=[att])
    assert _extract_first_attachment(msg) == ("https://cdn.discordapp.com/a.png", "image")


def test_pdf_returns_file_kind():
    att = _Attachment(url="https://cdn.discordapp.com/b.pdf", content_type="application/pdf")
    msg = _Message(attachments=[att])
    assert _extract_first_attachment(msg) == ("https://cdn.discordapp.com/b.pdf", "file")


def test_empty_content_type_returns_file_kind():
    att = _Attachment(url="https://cdn.discordapp.com/c.bin", content_type="")
    msg = _Message(attachments=[att])
    assert _extract_first_attachment(msg) == ("https://cdn.discordapp.com/c.bin", "file")


def test_empty_url_returns_none_none():
    att = _Attachment(url="", content_type="image/jpeg")
    msg = _Message(attachments=[att])
    assert _extract_first_attachment(msg) == (None, None)
