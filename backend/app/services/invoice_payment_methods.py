"""請求書の支払方法の候補と版（invoice-create-portfolio 便C・design.md §3-2・§3-4・§3-8・ADR-1079）。

正本: 振込先の表（tenant_invoice_payment_methods と詳細2表）と public.tenant_paypal_config。
- 候補＝今の版（superseded_by_id と deleted_at が NULL）・is_active・発行元の地域が同じ・詳細の行がある。
- Wise は wise_currency が請求書の通貨と同じものだけを受ける（候補の一覧は全部を返し、画面が絞る）。
- 口座番号は load_payment_version（PDF だけが呼ぶ）でだけ読む。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import tenant_table_ref


class PaymentMethodInvalid(Exception):
    """候補に無い支払方法（422 payment_method）。"""


async def _has_paypal(db: AsyncSession, tenant_id: int) -> bool:
    result = await db.execute(
        text("SELECT 1 FROM public.tenant_paypal_config WHERE tenant_id = :tid"),
        {"tid": int(tenant_id)},
    )
    return result.first() is not None


async def list_payment_choices(db: AsyncSession, tenant_id: int, region: str | None) -> list[dict]:
    """draft-context に返す候補（id・method_type・display_name・wise_currency）。region が None なら空。"""
    if region is None:
        return []
    methods = tenant_table_ref(db, tenant_id, "tenant_invoice_payment_methods")
    bank = tenant_table_ref(db, tenant_id, "tenant_invoice_payment_bank")
    wise = tenant_table_ref(db, tenant_id, "tenant_invoice_payment_wise")
    result = await db.execute(
        text(f"""
            SELECT m.id, m.method_type, m.display_name, w.wise_currency
            FROM {methods} m
            LEFT JOIN {bank} b ON b.payment_method_id = m.id
            LEFT JOIN {wise} w ON w.payment_method_id = m.id
            WHERE m.region = :region
              AND m.is_active = TRUE
              AND m.superseded_by_id IS NULL
              AND m.deleted_at IS NULL
              AND ((m.method_type = 'bank' AND b.payment_method_id IS NOT NULL)
                OR (m.method_type = 'wise' AND w.payment_method_id IS NOT NULL))
            ORDER BY m.sort_order, m.id
        """),
        {"region": region},
    )
    choices = [
        {
            "id": r["id"],
            "method_type": r["method_type"],
            "display_name": r["display_name"],
            "wise_currency": (r["wise_currency"].strip() if r["wise_currency"] else None) if r["method_type"] == "wise" else None,
        }
        for r in result.mappings().all()
    ]
    if await _has_paypal(db, tenant_id):
        choices.append({"id": None, "method_type": "paypal", "display_name": None, "wise_currency": None})
    return choices


def _accepts(choice: dict, method_type: str, method_id: int | None, currency: str) -> bool:
    if choice["method_type"] != method_type or choice["id"] != method_id:
        return False
    if method_type == "wise":
        return (choice["wise_currency"] or "").upper() == currency.upper()
    return True


async def resolve_payment_ref(
    db: AsyncSession, tenant_id: int, *, method_type: str, method_id: int | None, region: str | None, currency: str,
) -> tuple[str, int | None]:
    """受けた支払方法を確かめ、(payment_method の文字, payment_method_id) を返す。候補に無ければ PaymentMethodInvalid。"""
    choices = await list_payment_choices(db, tenant_id, region)
    if not any(_accepts(c, method_type, method_id, currency) for c in choices):
        raise PaymentMethodInvalid()
    return method_type, method_id


async def is_current_choice(
    db: AsyncSession, tenant_id: int, *, payment_method_id: int, region: str, currency: str,
) -> bool:
    """発行の前の確かめ（design.md §3-4 の発行の行）。payment_method_id の版が今も候補にあるか。"""
    choices = await list_payment_choices(db, tenant_id, region)
    return any(
        c["id"] == payment_method_id and _accepts(c, c["method_type"], payment_method_id, currency)
        for c in choices
    )


async def load_payment_label(db: AsyncSession, tenant_id: int, payment_method_id: int | None) -> dict | None:
    """詳細の道に返す表示（display_name・method_type）。古い版も読む。口座番号は読まない。"""
    if payment_method_id is None:
        return None
    methods = tenant_table_ref(db, tenant_id, "tenant_invoice_payment_methods")
    result = await db.execute(
        text(f"SELECT method_type, display_name FROM {methods} WHERE id = :id"),
        {"id": payment_method_id},
    )
    row = result.mappings().first()
    return None if row is None else {"method_type": row["method_type"], "display_name": row["display_name"]}


async def load_payment_version(db: AsyncSession, tenant_id: int, payment_method_id: int) -> dict | None:
    """PDF に描く版の中身（古い版・消した版でもその版を読む。design.md §3-7）。無ければ None。"""
    methods = tenant_table_ref(db, tenant_id, "tenant_invoice_payment_methods")
    bank = tenant_table_ref(db, tenant_id, "tenant_invoice_payment_bank")
    wise = tenant_table_ref(db, tenant_id, "tenant_invoice_payment_wise")
    result = await db.execute(
        text(f"""
            SELECT m.method_type, m.display_name,
                   b.account_holder AS bank_account_holder, b.bank_name AS bank_bank_name,
                   b.bank_branch, b.bank_account_type, b.bank_account_number, b.swift_code,
                   w.account_holder AS wise_account_holder, w.wise_email, w.iban, w.swift_bic,
                   w.bank_name AS wise_bank_name
            FROM {methods} m
            LEFT JOIN {bank} b ON b.payment_method_id = m.id
            LEFT JOIN {wise} w ON w.payment_method_id = m.id
            WHERE m.id = :id
        """),
        {"id": payment_method_id},
    )
    row = result.mappings().first()
    if row is None:
        return None
    if row["method_type"] == "bank" and row["bank_account_number"] is not None:
        return {
            "method_type": "bank", "display_name": row["display_name"],
            "bank_name": row["bank_bank_name"], "bank_branch": row["bank_branch"],
            "account_type": row["bank_account_type"], "account_number": row["bank_account_number"],
            "account_holder": row["bank_account_holder"], "swift_code": row["swift_code"],
        }
    if row["method_type"] == "wise" and row["wise_account_holder"] is not None:
        return {
            "method_type": "wise", "display_name": row["display_name"],
            "account_holder": row["wise_account_holder"], "wise_email": row["wise_email"],
            "bank_name": row["wise_bank_name"], "swift_bic": row["swift_bic"], "iban": row["iban"],
        }
    return None
