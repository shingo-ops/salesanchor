"""「既存顧客」への自動切り替え（ADR-1091）。

リードの段階が existing_customer になるのは、次の 3 つがそろったときだけ。
  ① 登録が済んでいる: その人の会社に既定の請求先がある
  ② そのリードの会社がある（companies.lead_id）
  ③ その会社に支払い済みの記録がある（invoices.paid_at か orders.paid_at）

判定の条件はこのファイルの 1 か所だけに書く。ほかの場所に同じ条件を写さない。
commit は呼び元がする（呼んだ側の取引の中で動く）。
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import is_postgresql, tenant_table_ref
from app.services.audit import record_audit_log

logger = logging.getLogger(__name__)


async def is_registration_completed(db: AsyncSession, tenant_id: int, lead_id: int) -> bool:
    """① 登録が済んでいる（その人の会社に既定の請求先がある）。"""
    ca = tenant_table_ref(db, tenant_id, "company_addresses")
    c = tenant_table_ref(db, tenant_id, "companies")
    return bool(
        await db.scalar(
            text(
                f"SELECT EXISTS("
                f"  SELECT 1 FROM {ca} ca"
                f"  JOIN {c} c ON c.id = ca.company_id"
                f"  WHERE c.lead_id = :lead_id"
                f"  AND ca.address_type = 'billing'"
                f"  AND ca.is_default = TRUE"
                f")"
            ),
            {"lead_id": lead_id},
        )
    )


async def _all_three_conditions_met(db: AsyncSession, tenant_id: int, lead_id: int) -> bool:
    """3 つの条件を 1 本の SQL で確かめる（② は会社の状態を問わない）。"""
    ca = tenant_table_ref(db, tenant_id, "company_addresses")
    c = tenant_table_ref(db, tenant_id, "companies")
    inv = tenant_table_ref(db, tenant_id, "invoices")
    od = tenant_table_ref(db, tenant_id, "orders")
    return bool(
        await db.scalar(
            text(
                f"SELECT EXISTS("
                f"  SELECT 1 FROM {c} c"
                f"  WHERE c.lead_id = :lead_id"
                f"  AND EXISTS ("
                f"    SELECT 1 FROM {ca} ca"
                f"    WHERE ca.company_id = c.id"
                f"    AND ca.address_type = 'billing'"
                f"    AND ca.is_default = TRUE)"
                f"  AND ("
                f"    EXISTS (SELECT 1 FROM {inv} i"
                f"            WHERE i.company_id = c.id AND i.paid_at IS NOT NULL)"
                f"    OR EXISTS (SELECT 1 FROM {od} o"
                f"            WHERE o.company_id = c.id AND o.paid_at IS NOT NULL)"
                f"  )"
                f")"
            ),
            {"lead_id": lead_id},
        )
    )


async def promote_lead_if_customer(
    db: AsyncSession,
    tenant_id: int,
    lead_id: int | None,
    *,
    actor_user_id: int | None,
    via: str,
    company_id: int | None = None,
    invoice_id: int | None = None,
    order_id: int | None = None,
) -> bool:
    """3 つがそろっていれば、リードを existing_customer にする。切り替えたら True。

    判定の失敗は SAVEPOINT だけ戻して False を返す（呼び元の入金・登録の記録は残す）。
    lead_id が None のときは invoice_id → order_id → company_id の順で lead_id を引く
    （引く処理の失敗も同じ SAVEPOINT の中で止まり、呼び元の入金記録は残る）。
    """
    if lead_id is None and invoice_id is None and order_id is None and company_id is None:
        return False
    try:
        async with db.begin_nested():
            if lead_id is None:
                if invoice_id is not None:
                    lead_id = await lead_id_of_invoice(db, tenant_id, invoice_id)
                elif order_id is not None:
                    lead_id = await lead_id_of_order(db, tenant_id, order_id)
                elif company_id is not None:
                    lead_id = await lead_id_of_company(db, tenant_id, company_id)
                if lead_id is None:
                    return False
            leads = tenant_table_ref(db, tenant_id, "leads")
            lock_sql = f"SELECT id FROM {leads} WHERE id = :lead_id"
            if is_postgresql(db):
                lock_sql += " FOR UPDATE"
            if (await db.execute(text(lock_sql), {"lead_id": lead_id})).first() is None:
                return False
            if not await _all_three_conditions_met(db, tenant_id, lead_id):
                return False
            result = await db.execute(
                text(
                    f"UPDATE {leads} SET status = 'existing_customer', updated_at = NOW() "
                    f"WHERE id = :lead_id AND status <> 'existing_customer'"
                ),
                {"lead_id": lead_id},
            )
            if not result.rowcount:
                return False
            if actor_user_id is not None:
                await record_audit_log(
                    db=db,
                    tenant_id=tenant_id,
                    user_id=actor_user_id,
                    action="auto_convert",
                    table_name="leads",
                    record_id=lead_id,
                    new_data={"status": "existing_customer", "via": via},
                )
            else:
                logger.info(
                    "[customer_conversion] auto_convert tenant=%s lead=%s via=%s",
                    tenant_id,
                    lead_id,
                    via,
                )
            return True
    except Exception:  # noqa: BLE001
        logger.error(
            "[customer_conversion] 判定に失敗 tenant=%s lead=%s via=%s",
            tenant_id,
            lead_id,
            via,
            exc_info=True,
        )
        return False


async def lead_id_of_invoice(db: AsyncSession, tenant_id: int, invoice_id: int) -> int | None:
    """請求書の会社 → companies.lead_id。"""
    inv = tenant_table_ref(db, tenant_id, "invoices")
    cid = await db.scalar(text(f"SELECT company_id FROM {inv} WHERE id = :iid"), {"iid": invoice_id})
    return await lead_id_of_company(db, tenant_id, cid)


async def lead_id_of_order(db: AsyncSession, tenant_id: int, order_id: int) -> int | None:
    """注文の会社 → companies.lead_id。"""
    od = tenant_table_ref(db, tenant_id, "orders")
    cid = await db.scalar(text(f"SELECT company_id FROM {od} WHERE id = :oid"), {"oid": order_id})
    return await lead_id_of_company(db, tenant_id, cid)


async def lead_id_of_company(db: AsyncSession, tenant_id: int, company_id: int | None) -> int | None:
    """会社から lead_id を求める（呼ぶ道が使う）。"""
    if company_id is None:
        return None
    c = tenant_table_ref(db, tenant_id, "companies")
    return await db.scalar(text(f"SELECT lead_id FROM {c} WHERE id = :cid"), {"cid": company_id})
