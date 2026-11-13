"""請求書・見積書の PDF に載せる発行元（自社）の情報を読む（ADR-1061 便2-2c2a）。

- 正本は会社ごとの発行元の表（国内向け・海外向けの 2 行まで）。
- その地域の行が無いときだけ、旧来の会社情報の表（1 行）から読む（移行の間の予備）。
- 行がある地域では、空の欄を旧来の表で埋めない（混ぜると正本が 2 か所になるため）。
"""

from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import tenant_table_ref

ISSUER_REGIONS = ("domestic", "overseas")


def decide_issuer_region(bill_to_snapshot: Mapping[str, Any] | None) -> str | None:
    """請求先の写しの国から発行元の地域を決める。国が無いときは None。"""
    if not bill_to_snapshot:
        return None
    country = bill_to_snapshot.get("country")
    if not isinstance(country, str) or not country.strip():
        return None
    return "domestic" if country.strip().upper() == "JP" else "overseas"


def format_issuer_address(row: Mapping[str, Any], prefecture_name: str | None, country_name: str | None) -> str:
    """発行元の住所を 1 行にする。日本は〒・都道府県から、海外は通りから国へ。"""
    city = row.get("city") or ""
    address1 = row.get("address1") or ""
    address2 = row.get("address2") or ""
    if row.get("country_code") == "JP":
        postal = row.get("postal_code") or ""
        head = f"〒{postal[:3]}-{postal[3:]} " if postal else ""
        line = f"{head}{prefecture_name or ''}{city}{address1}"
        return f"{line} {address2}" if address2 else line
    tail = f"{row.get('state_region') or ''} {row.get('postal_code') or ''}".strip()
    return ", ".join(p for p in [address1, address2, city, tail, country_name or ""] if p)


async def get_issuer(db: AsyncSession, tenant_id: int, region: str) -> dict:
    """発行元の情報を返す。キー: name, address, phone, email, website, registration_number, legacy。"""
    if region not in ISSUER_REGIONS:
        raise ValueError(f"unknown issuer region: {region}")
    profiles = tenant_table_ref(db, tenant_id, "tenant_issuer_profiles")
    result = await db.execute(
        text(f"""
            SELECT p.company_name, p.email, p.website, p.country_code, p.postal_code,
                   p.state_region, p.city, p.address1, p.address2, p.phone,
                   p.is_invoice_registered, p.registration_number,
                   pr.name_ja AS prefecture_name, co.name AS country_name
            FROM {profiles} p
            LEFT JOIN public.prefectures pr ON pr.code = p.prefecture_code
            LEFT JOIN public.countries co ON co.code = p.country_code
            WHERE p.region = :region
            ORDER BY p.id
            LIMIT 1
        """),
        {"region": region},
    )
    row = result.mappings().first()
    if row:
        return {
            "name": row["company_name"],
            "address": format_issuer_address(row, row["prefecture_name"], row["country_name"]),
            "phone": row["phone"] or "",
            "email": row["email"] or "",
            "website": row["website"] or "",
            "registration_number": row["registration_number"] if row["is_invoice_registered"] else None,
            "legacy": False,
        }
    legacy = tenant_table_ref(db, tenant_id, "tenant_profile")
    result = await db.execute(
        text(f"""
            SELECT company_name, company_name_en, address, phone, email, website
            FROM {legacy}
            ORDER BY id LIMIT 1
        """),
    )
    old = result.mappings().first()
    if not old:
        return {"name": "", "address": "", "phone": "", "email": "", "website": "",
                "registration_number": None, "legacy": True}
    return {
        "name": old["company_name"] or old["company_name_en"] or "",
        "address": old["address"] or "",
        "phone": old["phone"] or "",
        "email": old["email"] or "",
        "website": old["website"] or "",
        "registration_number": None,
        "legacy": True,
    }
