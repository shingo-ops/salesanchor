"""閲覧者の請求先フォーム（viewer-customer-sheet 便2）。

鍵（purpose='billing_form'）を作る唯一の入口は issue_billing_form_token。管理画面の「請求先フォームを送る」だけがここを呼ぶ
（viewer_signup.py の replace_signup_code と同じ形）。commit はしない（呼び出し側が commit する）。
鍵は DB に sha256 だけ保存する。ログに鍵・宛名・住所・電話を出さない。
"""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.viewer_admin import ViewerAdminError

BILLING_FORM_TTL = timedelta(days=3)  # ADR-1061 §3-2
PURPOSE = "billing_form"
# フォームを送れる・開ける・保存できる状態（契約手続き中と本契約。ADR-1061 §3-1）
FORM_STATUSES = ("contracting", "active")

_POSTAL_RE = re.compile(r"^[0-9]{7}$")
_PHONE_RE = re.compile(r"^[0-9]{10,11}$")
_SEPARATORS = re.compile(r"[\s\-‐‑–—ー－]")  # 空白・ハイフン類を外す


class BillingInvalid(ValueError):
    """項目が決まりに合わない。args[0] は項目名。"""


def normalize_digits(raw: str) -> str:
    """ハイフンと空白を外し、全角数字を半角にする。"""
    return _SEPARATORS.sub("", raw).translate(str.maketrans("０１２３４５６７８９", "0123456789"))


def clean_profile(
    party_type: str,
    bill_to_name: str,
    contact_name: str | None,
    postal_code: str,
    address: str,
    phone: str,
    invoice_email: str | None,
) -> dict:
    """DB の CHECK と同じ決まりで検査して整える。合わなければ BillingInvalid(項目名)。"""
    if party_type not in ("company", "individual"):
        raise BillingInvalid("party_type")
    name = bill_to_name.strip()
    if not 1 <= len(name) <= 100:
        raise BillingInvalid("bill_to_name")
    contact = (contact_name or "").strip() or None
    if contact is not None and len(contact) > 50:
        raise BillingInvalid("contact_name")
    if party_type == "company" and contact is None:
        raise BillingInvalid("contact_name")
    postal = normalize_digits(postal_code)
    if not _POSTAL_RE.match(postal):
        raise BillingInvalid("postal_code")
    addr = address.strip()
    if not 1 <= len(addr) <= 200:
        raise BillingInvalid("address")
    tel = normalize_digits(phone)
    if not _PHONE_RE.match(tel):
        raise BillingInvalid("phone")
    mail = (invoice_email or "").strip() or None
    if mail is not None and (not 3 <= len(mail) <= 254 or "@" not in mail):
        raise BillingInvalid("invoice_email")
    return {
        "party_type": party_type,
        "bill_to_name": name,
        "contact_name": contact,
        "postal_code": postal,
        "address": addr,
        "phone": tel,
        "invoice_email": mail,
    }


def token_sha256(raw: str) -> bytes:
    return hashlib.sha256(raw.encode()).digest()


async def issue_billing_form_token(db: AsyncSession, viewer_id: int, *, actor_user_id: int) -> tuple[str, datetime]:
    """請求先フォームの鍵の唯一の作り口。契約手続き中（contracting）と本契約（active）の人だけ。

    名簿に無ければ ViewerAdminError("not_found")、FORM_STATUSES でなければ ViewerAdminError("conflict")。
    同じ人の古い billing_form の鍵を消してから1本作り、(鍵, 期限) を返す。
    契約手続き中の人は、見られる期限を max(今の期限, 鍵の期限) にする（短くしない。ADR-1061 §3-2）。
    送った記録 form_sent を viewer_status_changes に残す（actor='po'・actor_user_id は押した人）。
    """
    row = (
        await db.execute(
            text("SELECT status, trial_expires_at FROM public.viewer_accounts WHERE id = :id FOR UPDATE"),
            {"id": viewer_id},
        )
    ).first()
    if row is None:
        raise ViewerAdminError("not_found")
    if row.status not in FORM_STATUSES:
        raise ViewerAdminError("conflict")
    await db.execute(
        text("DELETE FROM public.viewer_login_tokens WHERE viewer_account_id = :id AND purpose = 'billing_form'"),
        {"id": viewer_id},
    )
    now = datetime.now(timezone.utc)
    raw = secrets.token_urlsafe(32)
    expires_at = now + BILLING_FORM_TTL
    await db.execute(
        text(
            "INSERT INTO public.viewer_login_tokens (viewer_account_id, token_sha256, purpose, expires_at) "
            "VALUES (:id, :h, 'billing_form', :exp)"
        ),
        {"id": viewer_id, "h": token_sha256(raw), "exp": expires_at},
    )
    from_expires = row.trial_expires_at
    if from_expires is not None and from_expires.tzinfo is None:
        from_expires = from_expires.replace(tzinfo=timezone.utc)
    to_expires = from_expires
    if row.status == "contracting":
        to_expires = expires_at if from_expires is None else max(from_expires, expires_at)
        await db.execute(
            text("UPDATE public.viewer_accounts SET trial_expires_at = :exp, updated_at = :now WHERE id = :id"),
            {"exp": to_expires, "now": now, "id": viewer_id},
        )
    await db.execute(
        text(
            "INSERT INTO public.viewer_status_changes "
            "(viewer_id, action, from_status, to_status, from_expires_at, to_expires_at, "
            "extend_days, actor, actor_user_id, created_at) "
            "VALUES (:vid, 'form_sent', :st, :st, :from_expires, :to_expires, NULL, 'po', :uid, :now)"
        ),
        {
            "vid": viewer_id,
            "st": row.status,
            "from_expires": from_expires,
            "to_expires": to_expires,
            "uid": actor_user_id,
            "now": now,
        },
    )
    return raw, expires_at


_PROFILE_COLUMNS = (
    "party_type, bill_to_name, contact_name, postal_code, address, phone, invoice_email, updated_at"
)


async def get_profile(db: AsyncSession, viewer_id: int) -> dict | None:
    row = (
        await db.execute(
            text(f"SELECT {_PROFILE_COLUMNS} FROM public.viewer_billing_profiles WHERE viewer_account_id = :id"),
            {"id": viewer_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def peek_token(db: AsyncSession, raw: str) -> int | None:
    """鍵を使い切らずに確かめる。有効で FORM_STATUSES の人なら viewer_account_id、それ以外は None。"""
    row = (
        await db.execute(
            text(
                "SELECT t.viewer_account_id FROM public.viewer_login_tokens t "
                "JOIN public.viewer_accounts a ON a.id = t.viewer_account_id "
                "WHERE t.token_sha256 = :h AND t.purpose = 'billing_form' "
                "AND t.expires_at > :now AND a.status IN :statuses"
            ).bindparams(bindparam("statuses", expanding=True)),
            {"h": token_sha256(raw), "now": datetime.now(timezone.utc), "statuses": list(FORM_STATUSES)},
        )
    ).first()
    return None if row is None else int(row.viewer_account_id)


async def consume_token(db: AsyncSession, raw: str) -> int | None:
    """鍵を使い切る（DELETE … RETURNING）。有効だった鍵の viewer_account_id、無効なら None。"""
    row = (
        await db.execute(
            text(
                "DELETE FROM public.viewer_login_tokens "
                "WHERE token_sha256 = :h AND purpose = 'billing_form' AND expires_at > :now "
                "RETURNING viewer_account_id"
            ),
            {"h": token_sha256(raw), "now": datetime.now(timezone.utc)},
        )
    ).first()
    return None if row is None else int(row.viewer_account_id)


async def is_active(db: AsyncSession, viewer_id: int) -> bool:
    row = (
        await db.execute(
            text("SELECT status FROM public.viewer_accounts WHERE id = :id"), {"id": viewer_id}
        )
    ).first()
    return row is not None and row.status in FORM_STATUSES


async def upsert_profile(db: AsyncSession, viewer_id: int, values: dict) -> None:
    await db.execute(
        text(
            "INSERT INTO public.viewer_billing_profiles "
            "(viewer_account_id, party_type, bill_to_name, contact_name, postal_code, address, phone, invoice_email) "
            "VALUES (:id, :party_type, :bill_to_name, :contact_name, :postal_code, :address, :phone, :invoice_email) "
            "ON CONFLICT (viewer_account_id) DO UPDATE SET "
            "party_type = EXCLUDED.party_type, bill_to_name = EXCLUDED.bill_to_name, "
            "contact_name = EXCLUDED.contact_name, postal_code = EXCLUDED.postal_code, "
            "address = EXCLUDED.address, phone = EXCLUDED.phone, invoice_email = EXCLUDED.invoice_email, "
            "updated_at = now()"
        ),
        {"id": viewer_id, **values},
    )
