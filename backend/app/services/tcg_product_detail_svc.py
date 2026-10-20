"""DETAIL-01: product details and atomic, revision-checked editing."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.product_packagings import (
    ALL_SOURCES,
    PackagingError,
    load_packaging_units,
    load_packagings,
    save_packagings,
    validate_packagings,
)
from app.services.tcg_product_code_collision_svc import find_code_collisions
from app.services.tcg_product_master_svc import (
    _validate_product_format,
    fetch_product_format_options,
    find_cleared_fields,
    format_matches_game,
    save_blank_confirmations,
)

# Step 4/5: TCG テーブルは public スキーマに移行済み
TCG_SCHEMA = "public"

LOOKUPS = {
    "manufacturer_id": "tcg_manufacturers",
}
# ADR-155 Phase 3B: product_category_id is now INTEGER FK to public.tcg_product_categories
# ADR-156 Phase 3A: product_kind_id is INTEGER FK to public.product_kinds
PUBLIC_INTEGER_LOOKUPS = {
    "product_category_id": "tcg_product_categories",
    "product_kind_id": "product_kinds",
}
# Name column override: tables that use "name" instead of "display_name"
PUBLIC_INTEGER_NAME_COL: dict[str, str] = {
    "product_kind_id": "name",
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


async def _snapshot(db: AsyncSession, product_id: int) -> dict[str, Any]:
    result = await db.execute(text(
        "SELECT row_to_json(p) AS product, "
        "COALESCE((SELECT json_agg(k ORDER BY k.position,k.id) "
        "FROM public.product_search_keywords k WHERE k.product_id=p.id), '[]'::json) AS search_keywords, "
        "COALESCE((SELECT json_agg(k ORDER BY k.position,k.id) "
        "FROM public.product_exclude_keywords k WHERE k.product_id=p.id), '[]'::json) AS exclude_keywords, "
        "COALESCE((SELECT json_agg(c.field_code ORDER BY c.field_code) "
        "FROM public.product_blank_confirmations c WHERE c.product_id=p.id), '[]'::json) AS blank_confirmations, "
        # ADR-1028 便4: 荷姿（revision と audit に入る。updated_at も入れるので、書けば revision が変わる）
        "(SELECT COALESCE(json_agg(json_build_object("
        "'unit_code', u.code, 'contained_unit_code', cu.code, 'contained_count', pk.contained_count, "
        "'count_source', pk.count_source, 'count_source_urls', pk.count_source_urls, "
        "'weight_kg', pk.weight_kg, 'weight_source', pk.weight_source, "
        "'weight_source_urls', pk.weight_source_urls, 'note', pk.note, 'updated_at', pk.updated_at) "
        "ORDER BY u.display_order, pk.id), '[]'::json) "
        "FROM public.product_packagings pk "
        "JOIN public.quantity_units u ON u.id = pk.unit_id "
        "LEFT JOIN public.quantity_units cu ON cu.id = pk.contained_unit_id "
        "WHERE pk.product_id = p.id) AS packagings "
        "FROM public.products p WHERE p.id=:pid"
    ), {"pid": product_id})
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
    # ADR-1020 便2a: 「調べたが無い」の印（項目名の配列）
    product["blank_confirmations"] = list(snapshot.get("blank_confirmations") or [])
    product["packagings"] = list(snapshot.get("packagings") or [])
    lookups = {}
    # work_id → public.type_master (INTEGER, SSOT)
    work_rows = await db.execute(text(
        "SELECT id::text AS id, name_ja AS name, is_active "
        "FROM public.type_master "
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
    # ADR-155 Phase 3B / ADR-156 Phase 3A: public INTEGER lookups
    for field, table in PUBLIC_INTEGER_LOOKUPS.items():
        name_col = PUBLIC_INTEGER_NAME_COL.get(field, "display_name")
        rows = await db.execute(text(
            f"SELECT id::text AS id,{name_col} AS name,is_active "
            f"FROM public.{table} "
            f"WHERE is_active=TRUE OR id=:selected ORDER BY {name_col},id"
        ), {"selected": product[field]})
        lookups[field] = [dict(row) for row in rows.mappings()]
    # ADR-1020 便2a: 細分類（紐づくゲーム付き）
    lookups["product_format_id"] = await fetch_product_format_options(db, selected=product.get("product_format_id"))
    return {
        "product": product, "revision": _revision(snapshot), "lookups": lookups,
        # 最上位に置く（lookups の key の完全一致を見る試験を壊さない）
        "packaging_units": await load_packaging_units(db),
        "packaging_sources": list(ALL_SOURCES),
    }


async def get_product_detail(db: AsyncSession, product_id: int) -> dict[str, Any]:
    return await _response(db, await _snapshot(db, product_id))


async def update_product_detail(
    db: AsyncSession, product_id: int, values: dict[str, Any], revision: str, actor: str,
    actor_user_id: Any = None,
) -> dict[str, Any]:
    """Serialize writes per product; reject stale drafts and roll back all failures."""
    try:
        await db.execute(text(
            "SELECT id FROM public.products WHERE id=:pid FOR UPDATE"
        ), {"pid": product_id})
        before = await _snapshot(db, product_id)
        if _revision(before) != revision:
            raise ProductDetailError(409, "PRODUCT_DETAIL_CONFLICT")
        product = before["product"]
        params = dict(values)
        params["release_date"] = date.fromisoformat(values["release_date"]) if values["release_date"] else None
        # 空の mark / english_title は NULL で保存する（新規作成 tcg_product_master_svc.py:418-419 と同じ表し方）
        params["mark"] = (values["mark"] or "").strip() or None
        params["english_title"] = (values["english_title"] or "").strip() or None
        params["pid"] = product["id"]
        params["category_class"] = product["category_class"]
        # work_id → public.type_master (INTEGER, SSOT); validated separately from LOOKUPS
        new_work_id = values.get("work_id")
        if new_work_id is not None and str(new_work_id) != str(product.get("work_id") or ""):
            try:
                new_work_id_int = int(new_work_id)
            except (TypeError, ValueError):
                raise ProductDetailError(422, "PRODUCT_DETAIL_INVALID_CLASSIFICATION")
            work_row = (await db.execute(text(
                "SELECT name_ja FROM public.type_master "
                "WHERE id=:id AND is_active=TRUE FOR SHARE"
            ), {"id": new_work_id_int})).one_or_none()
            if work_row is None:
                raise ProductDetailError(422, "PRODUCT_DETAIL_INVALID_CLASSIFICATION")
            params["category_class"] = work_row[0]
            params["work_id"] = new_work_id_int
        else:
            params["work_id"] = product.get("work_id")
        for field, table in LOOKUPS.items():
            selected = values.get(field)
            if selected == product.get(field):
                continue
            if selected is None:
                raise ProductDetailError(422, "PRODUCT_DETAIL_INVALID_CLASSIFICATION")
            row = (await db.execute(text(
                f"SELECT display_name FROM {TCG_SCHEMA}.{table} "
                "WHERE id=CAST(:id AS uuid) AND is_active=TRUE FOR SHARE"
            ), {"id": selected})).one_or_none()
            if row is None:
                raise ProductDetailError(422, "PRODUCT_DETAIL_INVALID_CLASSIFICATION")
        # ADR-155 Phase 3B / ADR-156 Phase 3A: validate public INTEGER lookups
        for field, table in PUBLIC_INTEGER_LOOKUPS.items():
            selected = values.get(field)
            if selected == product.get(field):
                continue
            if selected is None:
                raise ProductDetailError(422, "PRODUCT_DETAIL_INVALID_CLASSIFICATION")
            name_col = PUBLIC_INTEGER_NAME_COL.get(field, "display_name")
            row = (await db.execute(text(
                f"SELECT {name_col} FROM public.{table} "
                "WHERE id=:id AND is_active=TRUE FOR SHARE"
            ), {"id": selected})).one_or_none()
            if row is None:
                raise ProductDetailError(422, "PRODUCT_DETAIL_INVALID_CLASSIFICATION")
        # ADR-1020 便3: 値か印のあった項目を、印なしの空にする保存だけ止める（古い空欄は止めない）
        if product.get("tenant_id") is None:
            before_marks = list(before.get("blank_confirmations") or [])
            after_marks = (
                values["blank_confirmations"] if values.get("blank_confirmations") is not None else before_marks
            )
            cleared = find_cleared_fields(
                {
                    "name": product.get("name"), "name_en": product.get("name_en"),
                    "mark": product.get("mark"), "release_date": product.get("release_date"),
                    "search_keywords": [row["keyword"] for row in before["search_keywords"]],
                    "exclude_keywords": [row["keyword"] for row in before["exclude_keywords"]],
                    "work_id": product.get("work_id"),
                    "product_format_id": product.get("product_format_id"),
                    "product_category_id": product.get("product_category_id"),
                },
                before_marks,
                {
                    "name": values.get("japanese_title"), "name_en": params["english_title"],
                    "mark": params["mark"], "release_date": params["release_date"],
                    "search_keywords": values["search_keywords"],
                    "exclude_keywords": values["exclude_keywords"],
                    "work_id": params["work_id"],
                    "product_format_id": (
                        values["product_format_id"] if "product_format_id" in values
                        else product.get("product_format_id")
                    ),
                    "product_category_id": values.get("product_category_id"),
                },
                after_marks,
            )
            if cleared:
                raise ProductDetailError(422, "REQUIRED_FIELDS_CLEARED:" + ",".join(cleared))
        # ADR-1028 便4: 荷姿は共用の商品だけ。書く前に全部確かめる
        packagings = values.get("packagings")
        if packagings is not None:
            if product.get("tenant_id") is not None:
                raise ProductDetailError(422, "PACKAGING_SHARED_ONLY")
            try:
                validate_packagings(
                    packagings, (await load_packagings(db, [product["id"]])).get(product["id"], []),
                )
            except PackagingError as exc:
                raise ProductDetailError(422, exc.code) from exc
        await db.execute(text("SET LOCAL app.is_operator = 'true'"))
        await db.execute(text(
            "UPDATE public.products SET "
            "name=:japanese_title,name_en=:english_title,mark=:mark,"
            "release_date=CAST(:release_date AS date),"
            "product_kind_id=:product_kind_id,"
            "work_id=:work_id,manufacturer_id=CAST(:manufacturer_id AS uuid),"
            "product_category_id=:product_category_id,category_class=:category_class "
            "WHERE id=:pid"
        ), params)
        # ADR-1020 便1: 細分類（来たときだけ・D5）と印（D4）
        if "product_format_id" in values:
            try:
                await _validate_product_format(db, values["product_format_id"])
            except ValueError:
                raise ProductDetailError(422, "PRODUCT_DETAIL_INVALID_CLASSIFICATION")
            await db.execute(text(
                "UPDATE public.products SET product_format_id=:fid WHERE id=:pid"
            ), {"fid": values["product_format_id"], "pid": product["id"]})
        # ADR-1020 便2a: 細分類とゲームの照合（細分類か作品が変わったときだけ・D2）
        final_format_id = values["product_format_id"] if "product_format_id" in values else product.get("product_format_id")
        format_changed = "product_format_id" in values and values["product_format_id"] != product.get("product_format_id")
        work_changed = params["work_id"] != product.get("work_id")
        if (final_format_id is not None and params["work_id"] is not None
                and (format_changed or work_changed)
                and not await format_matches_game(db, final_format_id, params["work_id"])):
            raise ProductDetailError(422, "PRODUCT_DETAIL_FORMAT_GAME_MISMATCH")
        await save_blank_confirmations(
            db,
            product_id=product["id"],
            values={"name_en": params["english_title"], "mark": params["mark"],
                    "release_date": params["release_date"], "exclude_keywords": values["exclude_keywords"]},
            confirmations=set(values["blank_confirmations"]) if values.get("blank_confirmations") is not None else None,
            actor=actor,
        )
        for field, table in WORD_TABLES.items():
            words = values[field]
            if words == [row["keyword"] for row in before[field]]:
                continue
            await db.execute(text(
                f"DELETE FROM public.{table} WHERE product_id=:pid"
            ), {"pid": product["id"]})
            if words:
                await db.execute(text(
                    f"INSERT INTO public.{table} (product_id,keyword,position) "
                    "VALUES (:pid,:word,:position)"
                ), [{"pid": product["id"], "word": word, "position": position}
                    for position, word in enumerate(words, 1)])
        if packagings is not None:
            await save_packagings(db, product["id"], packagings, f"user:{actor_user_id}")
        after = await _snapshot(db, product_id)
        _audit_pid = str(uuid4())
        await db.execute(text(
            f"INSERT INTO {TCG_SCHEMA}.audit_log "
            "(table_name,record_id,action,changed_by,old_values,new_values) "
            "VALUES ('products',CAST(:pid AS uuid),'UPDATE',:actor,:old,:new)"
        ), {"pid": str(_audit_pid), "actor": actor[:100], "old": _json(before), "new": _json(after)})
        response = await _response(db, after)
        saved = response["product"]
        response["code_collisions"] = await find_code_collisions(
            db,
            product_code=saved.get("code"),
            mark=saved.get("mark"),
            name=saved.get("japanese_title") or "",
            search_keywords=saved.get("search_keywords") or [],
            exclude_keywords=saved.get("exclude_keywords") or [],
            exclude_product_id=saved["id"],
        )
        await db.commit()
        return response
    except BaseException:
        await db.rollback()
        raise
