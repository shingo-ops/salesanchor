"""Versioned product reference for Gemini's work-ID-only decision."""
from __future__ import annotations

import hashlib
import json
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

WORK_ID_PROMPT_VERSION = "raw-extraction-v6-rawcode-p1"
WORK_ID_PROMPT_VERSIONS = frozenset({"raw-extraction-v4-work-id-p1", "raw-extraction-v4-work-id-p2", "raw-extraction-v5-product-p1", WORK_ID_PROMPT_VERSION})
# Prompt versions that include resolved_product_code (Gemini v5 and later).
PRODUCT_ID_PROMPT_VERSIONS = frozenset({"raw-extraction-v5-product-p1", WORK_ID_PROMPT_VERSION})
# Prompt versions that include raw_product_code (Gemini v6 and later).
RAW_CODE_PROMPT_VERSIONS = frozenset({WORK_ID_PROMPT_VERSION})


def reference_json(reference: dict) -> str:
    return json.dumps(reference, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def reference_digest(reference: dict) -> str:
    return hashlib.sha256(reference_json(reference).encode("utf-8")).hexdigest()


def work_ids(reference: dict) -> set[int]:
    return {int(work["id"]) for work in reference["works"]}


def validate_work_id(value: str | int | None, reference: dict) -> int | None:
    if value is None or value == "":
        return None
    try:
        canonical = int(value)
    except (TypeError, ValueError):
        logger.warning("validate_work_id: non-integer value %r, returning None", value)
        return None
    if canonical not in work_ids(reference):
        logger.warning("validate_work_id: %d not in reference, returning None", canonical)
        return None
    return canonical


def product_ids(reference: dict) -> set[str]:
    """Return the set of product id strings present in the reference."""
    return {str(p["id"]) for p in reference["products"] if p.get("id") is not None}


# Keep legacy alias for callers that still use product_codes()
def product_codes(reference: dict) -> set[str]:
    return product_ids(reference)


def validate_product_id(value: str | int | None, reference: dict) -> str | None:
    """Validate that value is a products.id string present in the reference."""
    if value is None or value == "":
        return None
    str_val = str(value)
    if str_val not in product_ids(reference):
        logger.warning("validate_product_id: %r not in reference, returning None", str_val)
        return None
    return str_val


# Keep legacy alias for callers that still use validate_product_code()
def validate_product_code(value: str | None, reference: dict) -> str | None:
    return validate_product_id(value, reference)


def load_work_reference(session: Session, schema: str) -> dict:
    """One statement sees a consistent snapshot; no network call holds its transaction."""
    row = session.execute(text("""
        SELECT jsonb_build_object(
          'works', (SELECT COALESCE(jsonb_agg(jsonb_build_object(
            'id', s.id, 'display_name', s.name_ja, 'alt_name', s.name_en)
            ORDER BY s.id), '[]'::jsonb)
            FROM public.type_master s WHERE s.is_active),
          'products', (SELECT COALESCE(jsonb_agg(jsonb_build_object(
            'id', p.id::text, 'japanese_title', p.name,
            'english_title', p.name_en, 'mark', p.mark, 'work_id', p.work_id,
            'search_keywords', (SELECT COALESCE(jsonb_agg(k.keyword ORDER BY k.position, k.keyword), '[]'::jsonb)
                FROM public.product_search_keywords k WHERE k.product_id=p.id),
            'exclude_keywords', (SELECT COALESCE(jsonb_agg(k.keyword ORDER BY k.position, k.keyword), '[]'::jsonb)
                FROM public.product_exclude_keywords k WHERE k.product_id=p.id))
            ORDER BY p.id), '[]'::jsonb)
            FROM public.products p WHERE p.is_active))
    """)).scalar_one()
    ids = work_ids(row)
    if not row["products"] or not ids:
        raise ValueError("Product/work reference is empty")
    if any(p["work_id"] not in ids for p in row["products"]):
        raise ValueError("Active product has no active work reference")
    return row
