from __future__ import annotations

"""成約/商談化の判定用 SQL ヘルパー。

成約定義はトラックBの正本として、lead → companies.lead_id → orders を辿る。
商談化（converted_deal_id）は別概念として残すため、ここでは受注ベースの
判定式だけを共有する。
"""


def lead_has_successful_order_sql(lead_alias: str = "l") -> str:
    """lead が非 cancelled の order を持つ company を持つかを SQL 式で返す。"""
    return (
        "EXISTS ("
        "SELECT 1 "
        "FROM companies c "
        "JOIN orders o ON o.company_id = c.id "
        f"WHERE c.lead_id = {lead_alias}.id "
        "AND o.status != 'cancelled'"
        ")"
    )


def lead_has_successful_invoice_sql(lead_alias: str = "l") -> str:
    """lead が非 voided の invoice を持つ company を持つかを SQL 式で返す。"""
    return (
        "EXISTS ("
        "SELECT 1 "
        "FROM companies c "
        "JOIN invoices i ON i.company_id = c.id "
        f"WHERE c.lead_id = {lead_alias}.id "
        "AND i.status != 'voided'"
        ")"
    )
