"""
Contact Form Endpoint — LP問い合わせ受付

POST /api/v1/contact
- 認証不要（salesanchor.jp LP から送信）
- 入力: name, email, company
- 動作: 管理者メール(support@salesanchor.jp)に転送、SMTP未設定時はログのみ
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from app.schemas.base import validate_email_loose
from app.services.mail_config import contact_notify_email, smtp_settings

router = APIRouter()
logger = logging.getLogger(__name__)


class ContactRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=3, max_length=255)
    company: str = Field(..., min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email_loose(v)


def _send_notification(data: ContactRequest) -> None:
    settings = smtp_settings()
    if settings is None:
        logger.info(
            "[contact] SMTP not configured — contact request received: "
            f"name={data.name!r} email={data.email!r} company={data.company!r}"
        )
        return

    subject = f"[Sales Anchor] Early Access Request — {data.company}"
    body = f"""Early access request received from the LP.

Name:    {data.name}
Email:   {data.email}
Company: {data.company}

---
Reply to: {data.email}
"""

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.mail_from
    msg["To"] = contact_notify_email()
    msg["Reply-To"] = data.email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(settings.host, settings.port, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(settings.user, settings.password)
        smtp.send_message(msg)


@router.post("/contact")
async def submit_contact(data: ContactRequest):
    """LP問い合わせフォーム受付。管理者へメール転送して200を返す。"""
    try:
        await asyncio.to_thread(_send_notification, data)
    except Exception:
        logger.exception("[contact] failed to send notification email")
        # メール送信失敗でも受付成功として返す（UX優先・ログで補完）

    logger.info(
        f"[contact] received: name={data.name!r} email={data.email!r} "
        f"company={data.company!r}"
    )
    return {"status": "received"}
