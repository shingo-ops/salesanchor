"""Product CSV round trips; design §21. This module does not run at edit time."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tcg_product_import_svc import CSV_COLUMNS, LOOKUP_ARGS, LOOKUP_TABLES
from app.tcg_config import TCG_SCHEMA

COLUMNS = ["product_code", "revision", *CSV_COLUMNS]
MAX_BYTES = 2 * 1024 * 1024
WORDS = {"search_keywords": "product_search_keywords", "exclude_keywords": "product_exclude_keywords"}
# Phase 3 SSOT: these lookup tables moved to public schema (INTEGER PK).
# Keys match the LOOKUP_TABLES keys whose backing table is now in public.
_PUBLIC_LOOKUP_TABLES: set[str] = {"product_category_code"}


class RoundtripError(ValueError):
    def __init__(self, code: str, status: int = 422):
        super().__init__(code)
        self.status = status


def needs_escape(value: str) -> bool:
    return value.startswith(("'", "\t", "\r", "\n")) or value.lstrip().startswith(
        ("=", "+", "-", "@", "＝", "＋", "－", "＠")
    )


def escape_cell(value: str) -> str:
    return "'" + value if needs_escape(value) else value


def unescape_cell(value: str) -> str:
    return value[1:] if value.startswith("'") and needs_escape(value[1:]) else value


def encode_words(words: list[str]) -> str:
    if not words:
        return ""
    out = io.StringIO(newline="")
    csv.writer(out, lineterminator="\r\n").writerow(words)
    return out.getvalue()[:-2]


def decode_words(value: str) -> list[str]:
    if not value:
        return []
    rows = parse_text(value)
    if len(rows) != 1:
        raise RoundtripError("ROUNDTRIP_KEYWORDS_INVALID")
    return rows[0]


def parse_text(value: str) -> list[list[str]]:
    # This synchronous section has no await; retain the legacy parser's limit.
    previous = csv.field_size_limit()
    try:
        csv.field_size_limit(MAX_BYTES)
        return list(csv.reader(io.StringIO(value, newline=""), strict=True))
    finally:
        csv.field_size_limit(previous)


def read_records(raw: bytes) -> list[list[str]]:
    if len(raw) > MAX_BYTES:
        raise RoundtripError("PRODUCT_IMPORT_FILE_TOO_LARGE", 413)
    try:
        return parse_text(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise RoundtripError("ROUNDTRIP_CSV_INVALID") from exc


def is_update(raw: bytes) -> bool:
    records = read_records(raw)
    return bool(records and any(c in records[0] for c in ("product_code", "revision")))


def revision(snapshot: dict) -> str:
    canonical = json.dumps(
        {"schema": TCG_SCHEMA, "product": snapshot["product"], **{key: snapshot[key] for key in WORDS}},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "v1:" + hashlib.sha256(canonical.encode()).hexdigest()


async def snapshots(db: AsyncSession, query: str = "", work_id: str | None = None) -> list[dict]:
    # One statement produces the complete product/words/reference snapshot.
    joins = []
    references = []
    # work_code → public.tcg_type_master (SSOT, INTEGER PK)
    joins.append("LEFT JOIN public.tcg_type_master work ON work.id=p.work_id")
    references.append("'work_code', work.code")
    for field, table in LOOKUP_TABLES.items():
        alias = field.removesuffix("_code")
        # Phase 3 SSOT: tcg_product_categories moved to public (INTEGER PK);
        # public.products.product_category_id is now INTEGER.
        schema_prefix = "public" if field in _PUBLIC_LOOKUP_TABLES else TCG_SCHEMA
        joins.append(f"LEFT JOIN {schema_prefix}.{table} {alias} ON {alias}.id=p.{LOOKUP_ARGS[field]}")
        references.append(f"'{field}', {alias}.code")
    keyword_sql = []
    for field, table in WORDS.items():
        keyword_sql.append(
            f"COALESCE((SELECT jsonb_agg(to_jsonb(k) ORDER BY k.position,k.id) "
            f"FROM public.{table} k WHERE k.product_id=p.id),'[]'::jsonb) AS {field}"
        )
    work_id_int = int(work_id) if work_id else None
    result = await db.execute(
        text(
            f"SELECT to_jsonb(p) AS product, jsonb_build_object({','.join(references)}) AS refs, "
            f"{','.join(keyword_sql)} FROM public.products p {' '.join(joins)} "
            "WHERE (p.name ILIKE :like OR p.name_en ILIKE :like OR p.mark ILIKE :like OR p.product_code ILIKE :like) "
            "AND (CAST(:work_id AS INTEGER) IS NULL OR p.work_id = CAST(:work_id AS INTEGER)) "
            "ORDER BY p.release_date DESC NULLS LAST,p.product_code DESC"
        ),
        {"like": "%" + query.strip() + "%", "work_id": work_id_int},
    )
    return [dict(row) for row in result.mappings().all()]


# public.products のカラム名 → CSV CSV_COLUMNS 名へのマッピング
_PRODUCT_FIELD_MAP = {
    "code": "product_code",
    "japanese_title": "name",
    "english_title": "name_en",
}


_ALL_REF_COLUMNS = {"work_code", *LOOKUP_TABLES}


def values(snapshot: dict) -> dict[str, str]:
    product = snapshot["product"]
    result = {}
    for field in CSV_COLUMNS:
        if field in WORDS or field in _ALL_REF_COLUMNS:
            continue
        # CSV フィールド名と public.products カラム名が異なる場合はマップする
        product_field = _PRODUCT_FIELD_MAP.get(field, field)
        result[field] = str(product.get(product_field) or "")
    result.update({key: str(snapshot["refs"].get(key) or "") for key in _ALL_REF_COLUMNS})
    result.update({key: encode_words([word["keyword"] for word in snapshot[key]]) for key in WORDS})
    return {"product_code": product["product_code"], "revision": revision(snapshot), **result}


async def export_csv(db: AsyncSession, query: str = "", work_id: str | None = None) -> bytes:
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\r\n", quoting=csv.QUOTE_ALL)
    writer.writerow(COLUMNS)
    for snapshot in await snapshots(db, query, work_id):
        row = values(snapshot)
        writer.writerow([escape_cell(row[key]) for key in COLUMNS])
    raw = out.getvalue().encode("utf-8-sig")
    if len(raw) > MAX_BYTES:
        raise RoundtripError("ROUNDTRIP_EXPORT_TOO_LARGE", 413)
    return raw


async def inspect_update(db: AsyncSession, raw: bytes, filename: str) -> tuple[dict, list[dict]]:
    records = read_records(raw)
    response: dict[str, Any] = {
        "filename": filename,
        "digest": hashlib.sha256(raw).hexdigest(),
        "mode": "update",
        "file_errors": [],
        "total": 0,
        "ok": 0,
        "blocked": 0,
        "updated": 0,
        "unchanged": 0,
        "rows": [],
    }
    if not records or records[0] != COLUMNS:
        response["file_errors"] = ["CSV_HEADER_MISMATCH"]
        return response, []
    if len(records) == 1:
        response["file_errors"] = ["CSV_EMPTY"]
        return response, []
    current = {s["product"]["product_code"]: s for s in await snapshots(db)}
    references = {}
    # work_code → public.tcg_type_master (SSOT, INTEGER PK)
    work_result = await db.execute(text("SELECT to_jsonb(r) FROM public.tcg_type_master r WHERE r.is_active=TRUE"))
    references["work_code"] = {row[0]["code"]: row[0] for row in work_result.fetchall()}
    for field, table in LOOKUP_TABLES.items():
        # Phase 3 SSOT: tcg_product_categories moved to public (INTEGER PK).
        schema_prefix = "public" if field in _PUBLIC_LOOKUP_TABLES else TCG_SCHEMA
        result = await db.execute(text(f"SELECT to_jsonb(r) FROM {schema_prefix}.{table} r WHERE r.is_active=TRUE"))
        references[field] = {row[0]["code"]: row[0] for row in result.fetchall()}
    plans = []
    seen = set()
    for number, record in enumerate(records[1:], 1):
        response["total"] += 1
        if len(record) != len(COLUMNS):
            response["file_errors"].append(f"CSV_COLUMN_COUNT_MISMATCH_ROW_{number}")
            continue
        row = dict(zip(COLUMNS, (unescape_cell(v) for v in record), strict=True))
        item: dict[str, Any] = {
            "row_no": str(number),
            "japanese_title": row["japanese_title"],
            "mark": row["mark"],
            "product_code": row["product_code"],
            "action": "unchanged",
            "changes": [],
            "blocking": [],
            "warnings": [],
        }
        errors = item["blocking"]
        code = row["product_code"]
        if code in seen:
            errors.append("ROUNDTRIP_DUPLICATE_CODE")
        seen.add(code)
        snapshot = current.get(code)
        plan: dict[str, Any] = {"row": item, "sets": {}, "words": {}}
        if snapshot is None:
            errors.append("ROUNDTRIP_UNKNOWN_CODE")
        elif row["revision"] != revision(snapshot):
            errors.append("ROUNDTRIP_STALE")
        else:
            plan["id"] = snapshot["product"]["id"]
            old = values(snapshot)
            for field in CSV_COLUMNS:
                if row[field] == old[field]:
                    continue
                before: str | list[str] = old[field]
                after: str | list[str] = row[field]
                if field in WORDS:
                    before = [w["keyword"] for w in snapshot[field]]
                    try:
                        after = decode_words(row[field])
                    except (csv.Error, RoundtripError):
                        errors.append("ROUNDTRIP_KEYWORDS_INVALID")
                        continue
                    if before == after:
                        continue
                    if any(not word.strip() for word in after):
                        errors.append("ROUNDTRIP_KEYWORDS_INVALID")
                    plan["words"][field] = after
                elif field in references:  # work_code + LOOKUP_TABLES
                    ref = references[field].get(row[field])
                    if ref is None:
                        errors.append(f"UNKNOWN_{field.upper()}_{row[field]}")
                    else:
                        plan["sets"][LOOKUP_ARGS[field]] = ref["id"]
                        if field == "work_code":
                            plan["sets"]["category_class"] = ref.get("name_ja") or ref.get("display_name", "")
                else:
                    if field == "japanese_title" and not row[field].strip():
                        errors.append("JAPANESE_TITLE_REQUIRED")
                    # CSV フィールド名を public.products カラム名にマッピング
                    db_field = _PRODUCT_FIELD_MAP.get(field, field)
                    plan["sets"][db_field] = row[field] or None
                    if field == "release_date" and row[field]:
                        try:
                            parsed_date = date.fromisoformat(row[field])
                            if parsed_date.isoformat() != row[field]:
                                raise ValueError("date format")
                            plan["sets"][db_field] = parsed_date
                        except ValueError:
                            errors.append("RELEASE_DATE_FORMAT")
                item["changes"].append({"field": field, "before": before, "after": after})
            if item["changes"]:
                item["action"] = "updated"
        response["rows"].append(item)
        response["blocked" if errors else "ok"] += 1
        if not errors:
            response[item["action"]] += 1
        plans.append(plan)
    return response, plans


async def preview_update(db: AsyncSession, raw: bytes, filename: str) -> dict:
    checked, _ = await inspect_update(db, raw, filename)
    return checked


async def commit_update(db: AsyncSession, raw: bytes, filename: str, executed_by: str, confirmed_digest: str) -> dict:
    try:
        if hashlib.sha256(raw).hexdigest() != confirmed_digest:
            raise RoundtripError("PRODUCT_IMPORT_DIGEST_MISMATCH", 409)
        await db.execute(text("SET LOCAL lock_timeout = '5s'"))
        await db.execute(text("SET LOCAL statement_timeout = '30s'"))
        await db.execute(
            text(
                "LOCK TABLE public.products, "
                "public.product_search_keywords, public.product_exclude_keywords "
                "IN SHARE ROW EXCLUSIVE MODE"
            )
        )
        await db.execute(
            text(f"LOCK TABLE {', '.join(f'{TCG_SCHEMA}.{table}' for table in LOOKUP_TABLES.values())} IN SHARE MODE")
        )
        prior = await db.execute(
            text(f"SELECT id FROM {TCG_SCHEMA}.tcg_product_import_jobs WHERE raw_sha256=:digest"),
            {"digest": confirmed_digest},
        )
        if prior.fetchone():
            raise RoundtripError("ROUNDTRIP_ALREADY_IMPORTED", 409)
        checked, plans = await inspect_update(db, raw, filename)
        if checked["file_errors"] or checked["blocked"]:
            stale = any("ROUNDTRIP_STALE" in row["blocking"] for row in checked["rows"])
            raise RoundtripError("ROUNDTRIP_STALE" if stale else "ROUNDTRIP_VALIDATION", 409 if stale else 422)
        job = await db.execute(
            text(
                f"INSERT INTO {TCG_SCHEMA}.tcg_product_import_jobs "
                "(filename,raw_sha256,total_rows,created_rows,skipped_rows,executed_by,status,completed_at) "
                "VALUES (:filename,:digest,:total,0,:unchanged,:actor,'ok',NOW()) RETURNING id"
            ),
            {
                "filename": filename,
                "digest": confirmed_digest,
                "total": checked["total"],
                "unchanged": checked["unchanged"],
                "actor": executed_by,
            },
        )
        job_id = str(job.scalar_one())
        for plan in plans:
            if plan["sets"]:
                assignments = []
                for field in plan["sets"]:
                    cast = (
                        f"CAST(:{field} AS INTEGER)"
                        if field in ("work_id", "product_category_id")
                        else f"CAST(:{field} AS uuid)"
                        if field in LOOKUP_ARGS.values()
                        else f"CAST(:{field} AS date)"
                        if field == "release_date"
                        else f":{field}"
                    )
                    assignments.append(f"{field}={cast}")
                await db.execute(text("SET LOCAL app.is_operator = 'true'"))
                await db.execute(
                    text(
                        f"UPDATE public.products SET {','.join(assignments)} WHERE id=:product_id"
                    ),
                    {**plan["sets"], "product_id": plan["id"]},
                )
            for field, words in plan["words"].items():
                await replace_words(db, plan["id"], WORDS[field], words)
            row = plan["row"]
            await db.execute(
                text(
                    f"INSERT INTO {TCG_SCHEMA}.tcg_product_import_rows "
                    "(job_id,row_no,japanese_title,mark,result,product_code,messages) "
                    "VALUES(CAST(:job AS uuid),:row_no,:title,:mark,:result,:code,:messages)"
                ),
                {
                    "job": job_id,
                    "row_no": int(row["row_no"]),
                    "title": row["japanese_title"],
                    "mark": row["mark"],
                    "result": row["action"],
                    "code": row["product_code"],
                    "messages": json.dumps(row["changes"], ensure_ascii=False),
                },
            )
        await db.commit()
        return {**checked, "job_id": job_id, "created": 0, "skipped": 0}
    except BaseException as original:
        try:
            await db.rollback()
        except BaseException as rollback_error:
            raise original from rollback_error
        raise


async def replace_words(db: AsyncSession, product_id: int, table: str, words: list[str]) -> None:
    """Replace only the selected product's edited keyword side, without commit."""
    if table not in ("product_search_keywords", "product_exclude_keywords"):
        raise ValueError("Invalid keyword table")
    await db.execute(
        text(f"DELETE FROM public.{table} WHERE product_id=:product_id"),
        {"product_id": product_id},
    )
    for position, word in enumerate(words, 1):
        await db.execute(
            text(
                f"INSERT INTO public.{table}(product_id,keyword,position) "
                "VALUES (:product_id,:keyword,:position)"
            ),
            {"product_id": product_id, "keyword": word, "position": position},
        )
