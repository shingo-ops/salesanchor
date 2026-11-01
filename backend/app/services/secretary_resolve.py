"""ADR-1056 段2: チャット秘書の名前探し（読み取りだけ）。

今のセッションの会社の文脈のまま読む（新しい接続を作らない・app.is_operator を立てない）。
会社: backend/app/routers/companies.py の一覧の検索と同じ表・列・条件。最大 5 件。
担当者: 会社が 1 件に決まったときだけ、その会社の中で routers/contacts.py と同じ表・列。最大 5 件。
名前が null なら探さず空。
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

MAX_CANDIDATES = 5


async def resolve_names(
    db: AsyncSession,
    tenant_id: int,  # noqa: ARG001 - 会社の絞り込みは RLS とセッションの文脈が行う（引数は呼び出し側の契約）
    company_name: str | None,
    contact_name: str | None,
) -> dict[str, list[dict]]:
    companies: list[dict] = []
    contacts: list[dict] = []

    if company_name and company_name.strip():
        result = await db.execute(
            text("""
                SELECT id, name
                FROM companies
                WHERE company_code ILIKE :search
                   OR name ILIKE :search
                   OR normalized_name ILIKE :search
                   OR billing_display_name ILIKE :search
                ORDER BY updated_at DESC
                LIMIT :limit
            """),
            {"search": f"%{company_name.strip()}%", "limit": MAX_CANDIDATES},
        )
        companies = [{"id": r[0], "name": r[1]} for r in result.fetchall()]

    if contact_name and contact_name.strip() and len(companies) == 1:
        result = await db.execute(
            text("""
                SELECT id, display_name
                FROM contacts
                WHERE (contact_code ILIKE :search OR display_name ILIKE :search
                       OR primary_email ILIKE :search OR primary_phone ILIKE :search
                       OR surname ILIKE :search OR given_name ILIKE :search)
                  AND company_id = :company_id
                ORDER BY is_primary_contact DESC, updated_at DESC
                LIMIT :limit
            """),
            {
                "search": f"%{contact_name.strip()}%",
                "company_id": companies[0]["id"],
                "limit": MAX_CANDIDATES,
            },
        )
        contacts = [{"id": r[0], "name": r[1]} for r in result.fetchall()]

    return {"companies": companies, "contacts": contacts}
