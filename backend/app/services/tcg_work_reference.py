"""Versioned product reference for Gemini's work-ID-only decision."""
from __future__ import annotations

import hashlib
import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

WORK_ID_PROMPT_VERSION = "raw-extraction-v4-work-id-p2"
WORK_ID_PROMPT_VERSIONS = frozenset({"raw-extraction-v4-work-id-p1", WORK_ID_PROMPT_VERSION})


def reference_json(reference: dict) -> str:
    return json.dumps(reference, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def reference_digest(reference: dict) -> str:
    return hashlib.sha256(reference_json(reference).encode("utf-8")).hexdigest()


def work_ids(reference: dict) -> set[str]:
    return {str(UUID(work["id"])) for work in reference["works"]}


def validate_work_id(value: str | None, reference: dict) -> str | None:
    if not value:
        return None
    canonical = str(UUID(value))
    if canonical not in work_ids(reference):
        raise ValueError("Work ID is not in the supplied reference")
    return canonical


def load_work_reference(session: Session, schema: str) -> dict:
    """One statement sees a consistent snapshot; no network call holds its transaction."""
    row = session.execute(text(f"""
        SELECT jsonb_build_object(
          'works', (SELECT COALESCE(jsonb_agg(jsonb_build_object(
            'id', s.id, 'display_name', s.display_name, 'alt_name', s.alt_name)
            ORDER BY s.id), '[]'::jsonb)
            FROM {schema}.tcg_series s WHERE s.is_active),
          'products', (SELECT COALESCE(jsonb_agg(jsonb_build_object(
            'code', p.code, 'japanese_title', p.japanese_title,
            'english_title', p.english_title, 'mark', p.mark, 'work_id', p.work_id,
            'search_keywords', (SELECT COALESCE(jsonb_agg(k.keyword ORDER BY k.position, k.keyword), '[]'::jsonb)
                FROM {schema}.product_search_keywords k WHERE k.product_id=p.id),
            'exclude_keywords', (SELECT COALESCE(jsonb_agg(k.keyword ORDER BY k.position, k.keyword), '[]'::jsonb)
                FROM {schema}.product_exclude_keywords k WHERE k.product_id=p.id))
            ORDER BY p.code), '[]'::jsonb)
            FROM {schema}.tcg_products p WHERE p.is_active))
    """)).scalar_one()
    ids = work_ids(row)
    if not row["products"] or not ids:
        raise ValueError("Product/work reference is empty")
    if any(str(p["work_id"]) not in ids for p in row["products"]):
        raise ValueError("Active product has no active work reference")
    return row
