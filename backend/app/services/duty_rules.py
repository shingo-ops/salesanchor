"""関税の額の決まりを読む・足す・直す・消す（invoice-create-portfolio 便B・design.md §3-3）。

- 表は会社ごとのスキーマの tenant_duty_rules と tenant_duty_rule_components（便Aで作成済み）。
- ここでは commit しない。commit と取引の後始末は呼ぶ側（routers/duty_rules.py）が行う。
- 同じ国・同じ送料の会社で、有効な決まりの期間が重なるときは DutyRuleOverlap を上げる（K18）。
  - 送料の会社は schemas/duty_rules.py で小文字・空白なしにそろえてから来る。空は NULL（どの会社でも）。
  - NULL どうしも同じとみなす（IS NOT DISTINCT FROM）。
  - 直すときは自分の行を比べる相手から外す。
  - 同時に足したときの取りこぼしを防ぐため、会社と国ごとの取引ロックを取ってから調べる（PostgreSQL のみ）。
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import is_postgresql, tenant_table_ref
from app.schemas.duty_rules import DutyRuleIn

_RULE_COLS = (
    "id, destination_country_code, carrier, label, effective_from, effective_to, "
    "source_url, note, is_active, created_at, updated_at"
)
_COMPONENT_COLS = "id, rule_id, sort_order, label, base, rate_pct, min_amount, max_amount, amount_currency"


class DutyRuleNotFound(Exception):
    """指定の決まりがこの会社に無い。"""


class DutyCountryInvalid(Exception):
    """国の表（public.countries）に有効な国として無い。"""


class DutyRuleOverlap(Exception):
    """同じ国・同じ送料の会社で、有効な決まりの期間が重なる。"""

    def __init__(self, rule_ids: list[int]) -> None:
        super().__init__("duty_rule_overlap")
        self.rule_ids = rule_ids


def _dec(value: Any) -> str | None:
    return None if value is None else str(value)


def _component_out(row: Any) -> dict:
    return {
        "id": row["id"],
        "sort_order": row["sort_order"],
        "label": row["label"],
        "base": row["base"],
        "rate_pct": _dec(row["rate_pct"]),
        "min_amount": _dec(row["min_amount"]),
        "max_amount": _dec(row["max_amount"]),
        "amount_currency": row["amount_currency"],
    }


def _rule_out(row: Any, components: list[dict]) -> dict:
    return {
        "id": row["id"],
        "destination_country_code": (row["destination_country_code"] or "").strip(),
        "carrier": row["carrier"],
        "label": row["label"],
        "effective_from": row["effective_from"],
        "effective_to": row["effective_to"],
        "source_url": row["source_url"],
        "note": row["note"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "components": components,
    }


async def _components_by_rule(db: AsyncSession, tenant_id: int, rule_ids: list[int]) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {rid: [] for rid in rule_ids}
    if not rule_ids:
        return out
    comps = tenant_table_ref(db, tenant_id, "tenant_duty_rule_components")
    if is_postgresql(db):
        result = await db.execute(
            text(f"SELECT {_COMPONENT_COLS} FROM {comps} "
                 "WHERE rule_id = ANY(CAST(:ids AS INTEGER[])) ORDER BY rule_id, sort_order, id"),
            {"ids": rule_ids},
        )
    else:
        placeholders = ", ".join(f":id{i}" for i in range(len(rule_ids)))
        result = await db.execute(
            text(f"SELECT {_COMPONENT_COLS} FROM {comps} "
                 f"WHERE rule_id IN ({placeholders}) ORDER BY rule_id, sort_order, id"),
            {f"id{i}": rid for i, rid in enumerate(rule_ids)},
        )
    for row in result.mappings().all():
        out.setdefault(row["rule_id"], []).append(_component_out(row))
    return out


async def list_duty_rules(db: AsyncSession, tenant_id: int) -> list[dict]:
    """この会社の決まりを国・送料の会社・始まりの日の順で返す（中身の行つき）。"""
    rules = tenant_table_ref(db, tenant_id, "tenant_duty_rules")
    result = await db.execute(
        text(f"SELECT {_RULE_COLS} FROM {rules} "
             "ORDER BY destination_country_code, carrier NULLS FIRST, effective_from, id"),
    )
    rows = result.mappings().all()
    comps = await _components_by_rule(db, tenant_id, [r["id"] for r in rows])
    return [_rule_out(r, comps.get(r["id"], [])) for r in rows]


async def get_duty_rule(db: AsyncSession, tenant_id: int, rule_id: int) -> dict:
    rules = tenant_table_ref(db, tenant_id, "tenant_duty_rules")
    result = await db.execute(
        text(f"SELECT {_RULE_COLS} FROM {rules} WHERE id = :id"),
        {"id": rule_id},
    )
    row = result.mappings().first()
    if row is None:
        raise DutyRuleNotFound()
    comps = await _components_by_rule(db, tenant_id, [rule_id])
    return _rule_out(row, comps.get(rule_id, []))


async def _check_country(db: AsyncSession, country_code: str) -> None:
    result = await db.execute(
        text("SELECT 1 FROM public.countries WHERE code = :code AND is_active = TRUE"),
        {"code": country_code},
    )
    if result.first() is None:
        raise DutyCountryInvalid()


async def _lock_and_check_overlap(db: AsyncSession, tenant_id: int, body: DutyRuleIn, exclude_id: int) -> None:
    """期間の重なりを調べる。重なる相手の id を DutyRuleOverlap で返す。"""
    if is_postgresql(db):
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"),
            {"k": f"duty_rules:{int(tenant_id)}:{body.destination_country_code}"},
        )
    if not body.is_active:
        # 使わない決まりは請求書の計算に出ないので、重なりを調べない（D6）
        return
    rules = tenant_table_ref(db, tenant_id, "tenant_duty_rules")
    result = await db.execute(
        text(f"""
            SELECT id FROM {rules}
            WHERE destination_country_code = :country
              AND carrier IS NOT DISTINCT FROM CAST(:carrier AS VARCHAR)
              AND is_active = TRUE
              AND id <> :exclude_id
              AND effective_from <= COALESCE(CAST(:to_date AS DATE), DATE '9999-12-31')
              AND COALESCE(effective_to, DATE '9999-12-31') >= CAST(:from_date AS DATE)
            ORDER BY id
        """),
        {
            "country": body.destination_country_code,
            "carrier": body.carrier,
            "exclude_id": exclude_id,
            "from_date": body.effective_from,
            "to_date": body.effective_to,
        },
    )
    ids = [r[0] for r in result.all()]
    if ids:
        raise DutyRuleOverlap(ids)


async def _insert_components(db: AsyncSession, tenant_id: int, rule_id: int, body: DutyRuleIn) -> None:
    comps = tenant_table_ref(db, tenant_id, "tenant_duty_rule_components")
    for index, comp in enumerate(body.components):
        await db.execute(
            text(f"""
                INSERT INTO {comps}
                    (rule_id, tenant_id, sort_order, label, base, rate_pct, min_amount, max_amount, amount_currency)
                VALUES (:rule_id, :tenant_id, :sort_order, :label, :base, :rate_pct, :min_amount, :max_amount,
                        :amount_currency)
            """),
            {
                "rule_id": rule_id,
                "tenant_id": int(tenant_id),
                "sort_order": index,
                "label": comp.label,
                "base": comp.base,
                "rate_pct": comp.rate_pct,
                "min_amount": comp.min_amount,
                "max_amount": comp.max_amount,
                "amount_currency": comp.amount_currency,
            },
        )


async def create_duty_rule(db: AsyncSession, tenant_id: int, body: DutyRuleIn) -> dict:
    await _check_country(db, body.destination_country_code)
    await _lock_and_check_overlap(db, tenant_id, body, exclude_id=0)
    rules = tenant_table_ref(db, tenant_id, "tenant_duty_rules")
    result = await db.execute(
        text(f"""
            INSERT INTO {rules}
                (tenant_id, destination_country_code, carrier, label, effective_from, effective_to,
                 source_url, note, is_active)
            VALUES (:tenant_id, :country, :carrier, :label, :from_date, :to_date, :source_url, :note, :is_active)
            RETURNING id
        """),
        {
            "tenant_id": int(tenant_id),
            "country": body.destination_country_code,
            "carrier": body.carrier,
            "label": body.label,
            "from_date": body.effective_from,
            "to_date": body.effective_to,
            "source_url": body.source_url,
            "note": body.note,
            "is_active": body.is_active,
        },
    )
    rule_id = int(result.scalar_one())
    await _insert_components(db, tenant_id, rule_id, body)
    return await get_duty_rule(db, tenant_id, rule_id)


async def update_duty_rule(db: AsyncSession, tenant_id: int, rule_id: int, body: DutyRuleIn) -> tuple[dict, dict]:
    """直す。戻り値は（直す前, 直した後）。中身の行は丸ごと置き換える。"""
    before = await get_duty_rule(db, tenant_id, rule_id)
    await _check_country(db, body.destination_country_code)
    await _lock_and_check_overlap(db, tenant_id, body, exclude_id=rule_id)
    rules = tenant_table_ref(db, tenant_id, "tenant_duty_rules")
    comps = tenant_table_ref(db, tenant_id, "tenant_duty_rule_components")
    await db.execute(
        text(f"""
            UPDATE {rules}
            SET destination_country_code = :country, carrier = :carrier, label = :label,
                effective_from = :from_date, effective_to = :to_date, source_url = :source_url,
                note = :note, is_active = :is_active, updated_at = now()
            WHERE id = :id
        """),
        {
            "id": rule_id,
            "country": body.destination_country_code,
            "carrier": body.carrier,
            "label": body.label,
            "from_date": body.effective_from,
            "to_date": body.effective_to,
            "source_url": body.source_url,
            "note": body.note,
            "is_active": body.is_active,
        },
    )
    await db.execute(text(f"DELETE FROM {comps} WHERE rule_id = :id"), {"id": rule_id})
    await _insert_components(db, tenant_id, rule_id, body)
    after = await get_duty_rule(db, tenant_id, rule_id)
    return before, after


async def delete_duty_rule(db: AsyncSession, tenant_id: int, rule_id: int) -> dict:
    """消す。戻り値は消す前の中身（監査の記録に使う）。中身の行は表の ON DELETE CASCADE で消える。"""
    before = await get_duty_rule(db, tenant_id, rule_id)
    rules = tenant_table_ref(db, tenant_id, "tenant_duty_rules")
    await db.execute(text(f"DELETE FROM {rules} WHERE id = :id"), {"id": rule_id})
    return before


async def get_duty_incoterms(db: AsyncSession, tenant_id: int) -> str | None:
    """関税の条件の正本 tenant_settings.duty_incoterms を読む（design.md §3-6）。行が無いときは None。"""
    result = await db.execute(
        text("SELECT duty_incoterms FROM public.tenant_settings WHERE tenant_id = :tenant_id"),
        {"tenant_id": int(tenant_id)},
    )
    row = result.first()
    return None if row is None else row[0]
