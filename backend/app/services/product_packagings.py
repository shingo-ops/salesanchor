"""ADR-1028 便3: 商品の荷姿（public.product_packagings）と、古い4項目の対応。

応答の4項目（boxes_per_case・packs_per_box・box_weight_kg・case_weight_kg）は、
名前と型を変えずに荷姿の表から組み立てる。その対応はこのファイルの1か所だけに書く
（商品 API と在庫検索の両方がここを使う）。古い4列（public.products）には書かない・読まない。
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# 項目名 -> (単位 code, "count"=入数 / "weight"=重さ, 入数のときの中の単位 code)
LEGACY_FIELDS: dict[str, tuple[str, str, str | None]] = {
    "boxes_per_case": ("CASE", "count", "BOX"),
    "case_weight_kg": ("CASE", "weight", None),
    "packs_per_box": ("BOX", "count", "PACK"),
    "box_weight_kg": ("BOX", "weight", None),
}

_SAVE_UNITS = ("CASE", "BOX")


def legacy_field_sql(field: str, product_id_expr: str) -> str:
    """古い4項目のうち1つぶんを、荷姿の表から取り出すスカラー副問い合わせ（SQL 文字列）にする。"""
    unit_code, kind, contained_code = LEGACY_FIELDS[field]
    if kind == "count":
        return (
            "(SELECT pk.contained_count FROM public.product_packagings pk "
            "JOIN public.quantity_units u ON u.id = pk.unit_id "
            "JOIN public.quantity_units cu ON cu.id = pk.contained_unit_id "
            f"WHERE pk.product_id = {product_id_expr} "
            f"AND u.code = '{unit_code}' AND cu.code = '{contained_code}')"
        )
    return (
        "(SELECT pk.weight_kg FROM public.product_packagings pk "
        "JOIN public.quantity_units u ON u.id = pk.unit_id "
        f"WHERE pk.product_id = {product_id_expr} "
        f"AND u.code = '{unit_code}')"
    )


async def load_packagings(db: AsyncSession, product_ids: list[int]) -> dict[int, list[dict]]:
    """商品ごとの荷姿の行（単位ごと）をまとめて1回で読む。"""
    if not product_ids:
        return {}
    result = await db.execute(
        text(
            "SELECT pk.product_id, u.code AS unit_code, cu.code AS contained_unit_code, "
            "pk.contained_count, pk.count_source, pk.count_source_urls, "
            "pk.weight_kg, pk.weight_source, pk.weight_source_urls, pk.note, pk.updated_at "
            "FROM public.product_packagings pk "
            "JOIN public.quantity_units u ON u.id = pk.unit_id "
            "LEFT JOIN public.quantity_units cu ON cu.id = pk.contained_unit_id "
            "WHERE pk.product_id = ANY(:ids) "
            "ORDER BY pk.product_id, u.display_order, u.id"
        ),
        {"ids": list(product_ids)},
    )
    out: dict[int, list[dict]] = {}
    for r in result.mappings().all():
        out.setdefault(r["product_id"], []).append({
            "unit_code": r["unit_code"],
            "contained_unit_code": r["contained_unit_code"],
            "contained_count": r["contained_count"],
            "count_source": r["count_source"],
            "count_source_urls": list(r["count_source_urls"] or []),
            "weight_kg": r["weight_kg"],
            "weight_source": r["weight_source"],
            "weight_source_urls": list(r["weight_source_urls"] or []),
            "note": r["note"],
            "updated_at": r["updated_at"],
        })
    return out


def _same(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return Decimal(str(a)) == Decimal(str(b))


def _expect_one(result, what: str) -> None:
    # RLS で黙って 0 行になるのを見逃さない
    if result.rowcount != 1:
        raise RuntimeError(f"product_packagings {what} affected {result.rowcount} rows (expected 1)")


async def save_legacy_fields(db: AsyncSession, product_id: int, fields: dict, updated_by: str) -> None:
    """古い4項目で送られた値を荷姿の表へ書く。fields は送られた項目だけ。"""
    if not fields:
        return
    unit_rows = (await db.execute(
        text("SELECT code, id FROM public.quantity_units WHERE code IN ('CASE','BOX','PACK')")
    )).all()
    ids = {code: uid for code, uid in unit_rows}
    if not {"CASE", "BOX", "PACK"} <= set(ids):
        raise RuntimeError("public.quantity_units に CASE / BOX / PACK が揃っていません")

    for unit_code in _SAVE_UNITS:
        sent = {f: v for f, v in fields.items() if LEGACY_FIELDS[f][0] == unit_code}
        if not sent:
            continue
        row = (await db.execute(
            text(
                "SELECT pk.id, pk.contained_count, cu.code AS contained_code, pk.weight_kg "
                "FROM public.product_packagings pk "
                "LEFT JOIN public.quantity_units cu ON cu.id = pk.contained_unit_id "
                "WHERE pk.product_id = :pid AND pk.unit_id = :uid FOR UPDATE OF pk"
            ),
            {"pid": product_id, "uid": ids[unit_code]},
        )).mappings().first()

        count_field = next((f for f in sent if LEGACY_FIELDS[f][1] == "count"), None)
        weight_field = next((f for f in sent if LEGACY_FIELDS[f][1] == "weight"), None)
        cur_count = row["contained_count"] if row is not None else None
        cur_weight = row["weight_kg"] if row is not None else None
        count_change = weight_change = False
        if count_field is not None:
            contained_code = LEGACY_FIELDS[count_field][2]
            legacy_now = cur_count if row is not None and row["contained_code"] == contained_code else None
            count_change = not _same(sent[count_field], legacy_now)
        if weight_field is not None:
            weight_change = not _same(sent[weight_field], cur_weight)
        if not (count_change or weight_change):
            continue

        new_count = sent[count_field] if count_change else cur_count
        new_weight = sent[weight_field] if weight_change else cur_weight
        empty = new_count is None and new_weight is None

        if row is None:
            if empty:
                continue
            cols = ["product_id", "unit_id", "updated_by"]
            vals = [":pid", ":uid", ":by"]
            params: dict = {"pid": product_id, "uid": ids[unit_code], "by": updated_by}
            if count_change and sent[count_field] is not None:
                cols += ["contained_unit_id", "contained_count", "count_source", "count_source_urls"]
                vals += [":cuid", ":cnt", "'legacy'", "'{}'::text[]"]
                params["cuid"] = ids[LEGACY_FIELDS[count_field][2]]
                params["cnt"] = sent[count_field]
            if weight_change and sent[weight_field] is not None:
                cols += ["weight_kg", "weight_source", "weight_source_urls"]
                vals += [":wt", "'legacy'", "'{}'::text[]"]
                params["wt"] = sent[weight_field]
            _expect_one(
                await db.execute(
                    text(f"INSERT INTO public.product_packagings ({', '.join(cols)}) VALUES ({', '.join(vals)})"),
                    params,
                ),
                "INSERT",
            )
            continue

        if empty:
            _expect_one(
                await db.execute(
                    text("DELETE FROM public.product_packagings WHERE id = :id"), {"id": row["id"]}
                ),
                "DELETE",
            )
            continue

        sets = ["updated_by = :by"]
        params = {"id": row["id"], "by": updated_by}
        if count_change:
            if sent[count_field] is None:
                sets += [
                    "contained_unit_id = NULL", "contained_count = NULL",
                    "count_source = NULL", "count_source_urls = '{}'::text[]",
                ]
            else:
                sets += [
                    "contained_unit_id = :cuid", "contained_count = :cnt",
                    "count_source = 'legacy'", "count_source_urls = '{}'::text[]",
                ]
                params["cuid"] = ids[LEGACY_FIELDS[count_field][2]]
                params["cnt"] = sent[count_field]
        if weight_change:
            if sent[weight_field] is None:
                sets += ["weight_kg = NULL", "weight_source = NULL", "weight_source_urls = '{}'::text[]"]
            else:
                sets += ["weight_kg = :wt", "weight_source = 'legacy'", "weight_source_urls = '{}'::text[]"]
                params["wt"] = sent[weight_field]
        _expect_one(
            await db.execute(
                text(f"UPDATE public.product_packagings SET {', '.join(sets)} WHERE id = :id"), params
            ),
            "UPDATE",
        )
