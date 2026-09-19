"""DETAIL-01: product details and atomic, revision-checked editing."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.tcg_config import TCG_SCHEMA

LOOKUPS = {
    "division_id": "tcg_major_categories",
    "manufacturer_id": "tcg_manufacturers",
    "product_category_id": "tcg_product_categories",
}
WORD_TABLES = {
    "search_keywords": "product_search_keywords",
    "exclude_keywords": "product_exclude_keywords",
}


class ProductDetailError(ValueError):
    def __init__(self, status: int, code: str):
        super().__init__(code)
        self.status = status


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


async def _snapshot(db: AsyncSession, code: str) -> dict[str, Any]:
    result = await db.execute(text(
        f"SELECT row_to_json(p) AS product, "
        f"COALESCE((SELECT json_agg(k ORDER BY k.position,k.id) "
        f"FROM {TCG_SCHEMA}.product_search_keywords k WHERE k.product_id=p.id), '[]'::json) AS search_keywords, "
        f"COALESCE((SELECT json_agg(k ORDER BY k.position,k.id) "
        f"FROM {TCG_SCHEMA}.product_exclude_keywords k WHERE k.product_id=p.id), '[]'::json) AS exclude_keywords "
        f"FROM public.products p WHERE p.product_code=:code"
    ), {"code": code})
    row = result.mappings().one_or_none()
    if row is None:
        raise ProductDetailError(404, "PRODUCT_DETAIL_NOT_FOUND")
    return dict(row)


def _revision(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(_json(snapshot).encode("utf-8")).hexdigest()


async def _response(db: AsyncSession, snapshot: dict[str, Any]) -> dict[str, Any]:
    product = dict(snapshot["product"])
    # API backward compatibility: public.products columns → API field names
    # id is now the INTEGER PK; expose as string for API compatibility
    if "id" in product:
        product["id"] = str(product["id"])
    if "name" in product:
        product["japanese_title"] = product.pop("name")
    if "name_en" in product:
        product["english_title"] = product.pop("name_en")
    if "product_code" in product:
        product["code"] = product.pop("product_code")
    for field in WORD_TABLES:
        product[field] = [row["keyword"] for row in snapshot[field]]
    lookups = {}
    # work_id → public.tcg_type_master (INTEGER, SSOT)
    work_rows = await db.execute(text(
        "SELECT id::text AS id, name_ja AS name, is_active "
        "FROM public.tcg_type_master "
        "WHERE is_active = TRUE OR id = :selected "
        "ORDER BY name_ja, id"
    ), {"selected": product["work_id"]})
    lookups["work_id"] = [dict(row) for row in work_rows.mappings()]
    # Other lookups (tenant_004, UUID)
    for field, table in LOOKUPS.items():
        rows = await db.execute(text(
            f"SELECT id::text AS id,display_name AS name,is_active "
            f"FROM {TCG_SCHEMA}.{table} "
            "WHERE is_active=TRUE OR id=CAST(:selected AS uuid) ORDER BY display_name,id"
        ), {"selected": product[field]})
        lookups[field] = [dict(row) for row in rows.mappings()]
    return {"product": product, "revision": _revision(snapshot), "lookups": lookups}


async def get_product_detail(db: AsyncSession, code: str) -> dict[str, Any]:
    return await _response(db, await _snapshot(db, code))


async def update_product_detail(
    db: AsyncSession, code: str, values: dict[str, Any], revision: str, actor: str,
) -> dict[str, Any]:
    """Serialize writes per product; reject stale drafts and roll back all failures."""
    try:
        await db.execute(text(
            "SELECT id FROM public.products WHERE product_code=:code FOR UPDATE"
        ), {"code": code})
        before = await _snapshot(db, code)
        if _revision(before) != revision:
            raise ProductDetailError(409, "PRODUCT_DETAIL_CONFLICT")
        product = before["product"]
        params = dict(values)
        params["release_date"] = date.fromisoformat(values["release_date"]) if values["release_date"] else None
        params["pid"] = product["id"]
        params["category_class"] = product["category_class"]
        for field, table in LOOKUPS.items():
            selected = values[field]
            if selected == product[field]:
                continue
            if selected is None:
                raise ProductDetailError(422, "PRODUCT_DETAIL_INVALID_CLASSIFICATION")
            row = (await db.execute(text(
                f"SELECT display_name FROM {TCG_SCHEMA}.{table} "
                "WHERE id=CAST(:id AS uuid) AND is_active=TRUE FOR SHARE"
            ), {"id": selected})).one_or_none()
            if row is None:
                raise ProductDetailError(422, "PRODUCT_DETAIL_INVALID_CLASSIFICATION")
            if field == "work_id":
                params["category_class"] = row[0]
        await db.execute(text("SET LOCAL app.is_operator = 'true'"))
        await db.execute(text(
            "UPDATE public.products SET "
            "name=:japanese_title,name_en=:english_title,mark=:mark,"
            "release_date=CAST(:release_date AS date),division_id=CAST(:division_id AS uuid),"
            "work_id=CAST(:work_id AS uuid),manufacturer_id=CAST(:manufacturer_id AS uuid),"
            "product_category_id=CAST(:product_category_id AS uuid),category_class=:category_class "
            "WHERE id=:pid"
        ), params)
        for field, table in WORD_TABLES.items():
            words = values[field]
            if words == [row["keyword"] for row in before[field]]:
                continue
            await db.execute(text(
                f"DELETE FROM {TCG_SCHEMA}.{table} WHERE product_id=:pid"
            ), {"pid": product["id"]})
            if words:
                await db.execute(text(
                    f"INSERT INTO {TCG_SCHEMA}.{table} (product_id,keyword,position) "
                    "VALUES (:pid,:word,:position)"
                ), [{"pid": product["id"], "word": word, "position": position}
                    for position, word in enumerate(words, 1)])
        after = await _snapshot(db, code)
        _audit_pid = str(uuid4())
        await db.execute(text(
            f"INSERT INTO {TCG_SCHEMA}.audit_log "
            "(table_name,record_id,action,changed_by,old_values,new_values) "
            "VALUES ('products',CAST(:pid AS uuid),'UPDATE',:actor,:old,:new)"
        ), {"pid": str(_audit_pid), "actor": actor[:100], "old": _json(before), "new": _json(after)})
        response = await _response(db, after)
        await db.commit()
        return response
    except BaseException:
        await db.rollback()
        raise
