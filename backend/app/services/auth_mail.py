"""ログイン関連のメール（ADR-1013 便3・ADR-1019 段4a-1）。パスワード再設定メール（アプリ用・閲覧ページ用）。

BackgroundTasks から呼ぶ同期関数。DB には触らない。
ログ・例外文に reset_url・鍵・宛先の全文を出さない。
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.services.mail_config import smtp_settings

logger = logging.getLogger(__name__)

RESET_SUBJECT = "【Sales Anchor】パスワード再設定 / Password reset"

_RESET_BODY = """Sales Anchor のパスワード再設定の申請を受け付けました。
下のリンクから 30 分以内に新しいパスワードを設定してください。

{reset_url}

このリンクは 1 回だけ使えます。
心当たりがない場合は、このメールを破棄してください。パスワードは変わりません。

---------------------------------------------
We received a request to reset your Sales Anchor password.
Please set a new password within 30 minutes using the link below.

{reset_url}

This link can be used only once.
If you did not request this, please ignore this email. Your password will not change.
---------------------------------------------

Sales Anchor
"""


INVITE_SUBJECT = "【Sales Anchor】初回パスワードの設定 / Set your Sales Anchor password"

_INVITE_BODY = """Sales Anchor のアカウントが作成されました。
下のリンクから 72 時間以内に最初のパスワードを設定してください。

{reset_url}

このリンクは 1 回だけ使えます。
心当たりがない場合は、このメールを破棄してください。

---------------------------------------------
A Sales Anchor account has been created for you.
Please set your first password within 72 hours using the link below.

{reset_url}

This link can be used only once.
If you did not expect this, please ignore this email.
---------------------------------------------

Sales Anchor
"""


VIEWER_RESET_SUBJECT = "【Sales Anchor】在庫閲覧ページのパスワード再発行 / Inventory viewer password reset"

_VIEWER_RESET_BODY = """Sales Anchor 在庫閲覧ページのパスワード再発行の申請を受け付けました。
下のリンクから 30 分以内に新しいパスワードを設定してください。

{reset_url}

このリンクは 1 回だけ使えます。
心当たりがない場合は、このメールを破棄してください。パスワードは変わりません。

---------------------------------------------
We received a request to reset your Sales Anchor inventory viewer password.
Please set a new password within 30 minutes using the link below.

{reset_url}

This link can be used only once.
If you did not request this, please ignore this email. Your password will not change.
---------------------------------------------

Sales Anchor
"""


def _mask_addr(addr: str) -> str:
    """`@` の前を伏せる（例 t***@gmail.com）。"""
    local, sep, domain = addr.partition("@")
    if not sep:
        return "***"
    return f"{local[:1]}***@{domain}"


def _send_reset_mail(to_addr: str, reset_url: str, subject: str, body: str) -> None:
    """再設定メールの送信部（アプリ用・閲覧ページ用で共通）。例外は外に出さずログに残す。"""
    settings = smtp_settings()
    if settings is None:
        logger.info("[auth_mail] SMTP not configured, skipping password reset mail")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.mail_from
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.attach(MIMEText(body.format(reset_url=reset_url), "plain", "utf-8"))

        with smtplib.SMTP(settings.host, settings.port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.user, settings.password)
            smtp.send_message(msg)
        logger.info("[auth_mail] password reset mail sent (to=%s)", _mask_addr(to_addr))
    except Exception as e:  # noqa: BLE001
        # 例外文に宛先・URL・パスワードが入り得るため、型名だけを残す
        logger.error("[auth_mail] password reset mail failed (to=%s): %s", _mask_addr(to_addr), type(e).__name__)


def send_password_reset_email(to_addr: str, reset_url: str) -> None:
    """BackgroundTasks から呼ぶ同期関数。例外は外に出さずログに残す（応答はもう返っている）。"""
    _send_reset_mail(to_addr, reset_url, RESET_SUBJECT, _RESET_BODY)


def send_invite_email(to_addr: str, reset_url: str) -> None:
    """初回設定メール（ADR-1013 便4a）。BackgroundTasks から呼ぶ。"""
    _send_reset_mail(to_addr, reset_url, INVITE_SUBJECT, _INVITE_BODY)


def send_viewer_password_reset_email(to_addr: str, reset_url: str) -> None:
    """閲覧ページ用の再発行メール（ADR-1019）。BackgroundTasks から呼ぶ。"""
    _send_reset_mail(to_addr, reset_url, VIEWER_RESET_SUBJECT, _VIEWER_RESET_BODY)


NEW_DEVICE_SUBJECT = "【Sales Anchor】新しい機械からのログイン / Login from a new device"

_NEW_DEVICE_BODY = """Sales Anchor に、新しい機械からのログインがありました。

日時（日本時間）: {when}
機械: {device}
場所の目安: {location}
{note}
心当たりがなければ、いつもの機械でアプリを開いて「私ではない」を押し、パスワードを変えてください。
このメールにリンクはありません。

---------------------------------------------
There was a login to Sales Anchor from a new device.

Time (JST): {when}
Device: {device}
Approximate location: {location}

If this was not you, open the app on a device you usually use, press "This is not me", and change your password.
This email contains no links.
---------------------------------------------

{geo_credit}
Sales Anchor
"""

GEO_CREDIT = "IP Geolocation by DB-IP"  # リンクは入れない（メールにリンクを入れない決まり）


def send_new_device_mail(
    to_addr: str, *, when: str, device: str, location: str | None, note: str | None = None
) -> None:
    """新しい機械からのログインの知らせ（ADR-1055 K2）。BackgroundTasks から呼ぶ同期関数。

    リンクを入れない。パスワード・番号・Cookie の値は入れない。失敗しても外に出さずログに残す。
    """
    settings = smtp_settings()
    if settings is None:
        logger.info("[auth_mail] SMTP not configured, skipping new device mail")
        return
    try:
        body = _NEW_DEVICE_BODY.format(
            when=when,
            device=device,
            location=location or "不明 / unknown",
            note=(note + "\n") if note else "",
            geo_credit=GEO_CREDIT if location else "",
        )
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.mail_from
        msg["To"] = to_addr
        msg["Subject"] = NEW_DEVICE_SUBJECT
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP(settings.host, settings.port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.user, settings.password)
            smtp.send_message(msg)
        logger.info("[auth_mail] new device mail sent (to=%s)", _mask_addr(to_addr))
    except Exception as e:  # noqa: BLE001
        logger.error("[auth_mail] new device mail failed (to=%s): %s", _mask_addr(to_addr), type(e).__name__)
