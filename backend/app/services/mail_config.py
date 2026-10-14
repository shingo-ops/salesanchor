"""メール送信の設定の読み取り口（ADR-1013 便3・PO 決定 y1）。

SMTP_* と MAIL_FROM を読むのはこのファイルだけ。毎回 os.getenv で読む（テストで差し替えるため・キャッシュしない）。
空文字は「未設定」と同じに扱う（deploy.yml は未登録の Secret を空文字で .env に書くため）。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

DEFAULT_SMTP_PORT = 587
DEFAULT_CONTACT_NOTIFY_EMAIL = "support@salesanchor.jp"


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    user: str
    password: str = field(repr=False)
    mail_from: str


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def smtp_settings() -> SmtpSettings | None:
    """HOST・USER・PASSWORD・MAIL_FROM がそろっていれば設定を返す。1つでも空なら None（送らずログだけ）。"""
    host, user, password, mail_from = _env("SMTP_HOST"), _env("SMTP_USER"), _env("SMTP_PASSWORD"), _env("MAIL_FROM")
    if not (host and user and password and mail_from):
        return None
    port_raw = _env("SMTP_PORT")
    port = int(port_raw) if port_raw.isdigit() else DEFAULT_SMTP_PORT
    return SmtpSettings(host=host, port=port, user=user, password=password, mail_from=mail_from)


def contact_notify_email() -> str:
    return _env("CONTACT_NOTIFY_EMAIL") or DEFAULT_CONTACT_NOTIFY_EMAIL
