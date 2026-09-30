"""
試運転（Shadow run, PR-C）: Gemini＝書き写し専任（v7）＋システム＝判定 を1ジョブ分実行する。

design: docs/handoff/gemini-extract-role-split/design.md PR-C
  - EXTRACTION_SHADOW_ENABLED（既定無効）が有効な時だけ、本番の抽出・解析が
    終わった後にこのモジュールを呼ぶ（backend/app/tasks/tcg_extraction.py）。
  - ジョブの原文・仕入元の情報・knowledge_links は、呼び出し元
    （_run_extraction）が本番用に既に読み込んだ値をそのまま受け取る。
    新しいクエリは作らない（クエリ複製回避）。
  - 書き込み先は public.extraction_shadow_runs / public.extraction_shadow_results
    （PR-B1 migration）。migration 未適用の環境では INSERT が失敗するため、
    例外は本モジュール内で吸収し、本番フローには一切伝播しない。
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.extraction_judgement_svc import (
    MatchResult,
    ProductEntry,
    block_text,
    match_product,
    verify_copied,
)
from app.services.extraction_judgement_svc import (
    ship_timing as judge_ship_timing,
)
from app.services.gemini_extraction_svc import call_gemini_raw_copy, parse_raw_copy_response
from app.services.llm_budget import UsageCounts, record_usage_event_sync
from app.services.tcg_analyzer_svc import (
    _parse_numeric,
    build_note_ja,
    load_condition_entries,
    load_lookup_maps,
    load_note_master,
    load_status_master,
    resolve_condition_v2,
    resolve_status_v2,
    resolve_unit_v2,
)
from app.services.tcg_work_reference import RAW_COPY_PROMPT_VERSION

logger = logging.getLogger(__name__)

_REQUESTED_MODEL = "gemini-3.1-flash-lite"
_PROMPT_KEY = "raw_copy_extraction"

# verify_copied で照合する Gemini 書き写し値のうち、原文検証の対象にするフィールド。
_VERIFY_FIELDS = ("raw_price", "raw_state", "raw_ship")


# ---------------------------------------------------------------------------
# 商品リストのロード（PR-A ProductEntry 形）
# ---------------------------------------------------------------------------


def load_product_entries(session: Session) -> list[ProductEntry]:
    """判定用の商品リストを読む（public.products の有効な全件）。

    design.md §4-1: 対象は public.products の有効な全件（解析用の別マスタは作らない）。
    """
    rows = session.execute(
        text(
            """
            SELECT p.id, p.product_code, p.mark, p.work_id,
                   (SELECT COALESCE(array_agg(k.keyword ORDER BY k.position, k.keyword), ARRAY[]::text[])
                    FROM public.product_search_keywords k WHERE k.product_id = p.id) AS search_keywords,
                   (SELECT COALESCE(array_agg(k.keyword ORDER BY k.position, k.keyword), ARRAY[]::text[])
                    FROM public.product_exclude_keywords k WHERE k.product_id = p.id) AS exclude_keywords
            FROM public.products p
            WHERE p.is_active = TRUE
            """
        )
    ).fetchall()
    return [
        ProductEntry(
            id=int(r[0]),
            product_code=r[1],
            mark=r[2],
            work_id=int(r[3]) if r[3] is not None else None,
            search_keywords=tuple(r[4] or ()),
            exclude_keywords=tuple(r[5] or ()),
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# 永続化（extraction_shadow_runs / extraction_shadow_results）
# ---------------------------------------------------------------------------


def insert_shadow_run(
    session: Session,
    *,
    extraction_job_id: str,
    prompt_key: str,
    engine_version: str,
    requested_model: str,
    input_bytes: int | None,
    response_text: str | None,
    status: str,
    error_code: str | None = None,
    error_detail: str | None = None,
    started_at: datetime | None = None,
) -> str:
    """extraction_shadow_runs に1行 INSERT して run_id を返す（PR-B1 migration 前提）。

    ADR-1004: input_tokens/output_tokens/cost_usd は本 PR 以降 llm_usage_events 台帳が
    SSOT。ここでは書き込まない（列は残置、NULL のまま）。呼び出し元が run_id を受けて
    record_usage_event_sync(purpose='line_extraction_shadow', extraction_shadow_run_id=run_id)
    を呼ぶこと。
    """
    run_id = str(uuid.uuid4())
    session.execute(
        text(
            """
            INSERT INTO public.extraction_shadow_runs
                (id, extraction_job_id, prompt_key, engine_version, requested_model,
                 input_bytes, response_text, status, error_code, error_detail,
                 started_at, finished_at)
            VALUES
                (:id, :extraction_job_id, :prompt_key, :engine_version, :requested_model,
                 :input_bytes, :response_text, :status, :error_code, :error_detail,
                 COALESCE(:started_at, now()), now())
            """
        ),
        {
            "id": run_id,
            "extraction_job_id": extraction_job_id,
            "prompt_key": prompt_key,
            "engine_version": engine_version,
            "requested_model": requested_model,
            "input_bytes": input_bytes,
            "response_text": response_text,
            "status": status,
            "error_code": error_code,
            "error_detail": error_detail,
            "started_at": started_at,
        },
    )
    return run_id


def insert_shadow_results(session: Session, run_id: str, results: list[dict[str, Any]]) -> None:
    """extraction_shadow_results を run 単位で DELETE してから再 INSERT する（冪等）。"""
    import json as _json

    session.execute(
        text("DELETE FROM public.extraction_shadow_results WHERE run_id = :run_id"),
        {"run_id": run_id},
    )
    for block_index, r in enumerate(results):
        session.execute(
            text(
                """
                INSERT INTO public.extraction_shadow_results
                    (id, run_id, block_index, line_start, line_end,
                     heading_line_start, heading_line_end,
                     raw_product_name, raw_price, raw_unit, raw_quantity, raw_state, raw_ship, raw_multi,
                     product_id, work_id, condition_id, quantity_normalized, price_normalized,
                     ship_offer_type, ship_timing, note_ja, status, exclusion,
                     match_status, needs_review, review_items, evidence, verify_failures)
                VALUES
                    (:id, :run_id, :block_index, :line_start, :line_end,
                     :heading_line_start, :heading_line_end,
                     :raw_product_name, :raw_price, :raw_unit, :raw_quantity, :raw_state, :raw_ship, :raw_multi,
                     :product_id, :work_id, :condition_id, :quantity_normalized, :price_normalized,
                     :ship_offer_type, :ship_timing, :note_ja, :status, :exclusion,
                     :match_status, :needs_review, :review_items, :evidence, :verify_failures)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "block_index": block_index,
                "line_start": r["line_start"],
                "line_end": r["line_end"],
                "heading_line_start": r.get("heading_line_start"),
                "heading_line_end": r.get("heading_line_end"),
                "raw_product_name": r.get("raw_product_name"),
                "raw_price": r.get("raw_price"),
                "raw_unit": r.get("raw_unit"),
                "raw_quantity": r.get("raw_quantity"),
                "raw_state": r.get("raw_state"),
                "raw_ship": r.get("raw_ship"),
                "raw_multi": r.get("raw_multi"),
                "product_id": r.get("product_id"),
                "work_id": r.get("work_id"),
                "condition_id": r.get("condition_id"),
                "quantity_normalized": r.get("quantity_normalized"),
                "price_normalized": r.get("price_normalized"),
                "ship_offer_type": r.get("ship_offer_type"),
                "ship_timing": r.get("ship_timing"),
                "note_ja": r.get("note_ja"),
                "status": r.get("status"),
                "exclusion": r.get("exclusion"),
                "match_status": r["match_status"],
                "needs_review": r["needs_review"],
                "review_items": _json.dumps(r.get("review_items") or []),
                "evidence": _json.dumps(r.get("evidence") or {}),
                "verify_failures": _json.dumps(r.get("verify_failures") or []),
            },
        )


# ---------------------------------------------------------------------------
# 判定: 1ブロック分
# ---------------------------------------------------------------------------


def _judge_block(
    block_item: dict,
    raw_text: str,
    *,
    products: list[ProductEntry],
    cond_entries: list[dict],
    cond_canonical_to_uuid: dict,
    unit_alias_to_info: dict,
    status_entries: list[dict],
    note_entries: list[dict],
) -> dict:
    """1ブロック（v7の書き写し1行）をシステム判定し、shadow_results 用の1行を返す。"""
    block = block_text(raw_text, block_item["line_start"], block_item["line_end"])

    match: MatchResult = match_product(block, products)

    _unit_canonical, kubun, _unit_resolved = resolve_unit_v2(block_item["raw_unit"], unit_alias_to_info)
    _cond_canonical, condition_id, _basis = resolve_condition_v2(
        block_item["raw_state"],
        block_item["raw_product_name"],
        kubun,
        cond_entries,
        cond_canonical_to_uuid,
        raw_memo=block,
    )
    status_canonical, exclusion = resolve_status_v2(block_item["raw_state"], status_entries, raw_memo=block)
    note_ja = build_note_ja(block, note_entries, raw_state=block_item["raw_state"])
    ship_offer_type, ship_timing_value = judge_ship_timing(block)

    verify_failures = [
        field_name
        for field_name in _VERIFY_FIELDS
        if not verify_copied(block_item.get(field_name, ""), block)
    ]

    review_items: list[dict] = []
    if match.status != "matched":
        review_items.append(
            {"item": "product", "reason": match.reason, "candidates": list(match.candidates)}
        )
    if verify_failures:
        review_items.append(
            {"item": "verify_copied", "reason": ",".join(verify_failures), "candidates": []}
        )

    needs_review = match.status != "matched" or bool(verify_failures)

    return {
        "line_start": block_item["line_start"],
        "line_end": block_item["line_end"],
        "heading_line_start": block_item.get("heading_line_start"),
        "heading_line_end": block_item.get("heading_line_end"),
        "raw_product_name": block_item["raw_product_name"],
        "raw_price": block_item["raw_price"],
        "raw_unit": block_item["raw_unit"],
        "raw_quantity": block_item["raw_quantity"],
        "raw_state": block_item["raw_state"],
        "raw_ship": block_item["raw_ship"],
        "raw_multi": block_item["raw_multi"],
        "product_id": match.product_id,
        "work_id": match.work_id,
        "condition_id": condition_id,
        "quantity_normalized": _parse_numeric(block_item["raw_quantity"]),
        "price_normalized": _parse_numeric(block_item["raw_price"]),
        "ship_offer_type": ship_offer_type,
        "ship_timing": ship_timing_value,
        "note_ja": note_ja,
        "status": status_canonical,
        "exclusion": exclusion,
        "match_status": match.status,
        "needs_review": needs_review,
        "review_items": review_items,
        "evidence": {"basis": match.basis},
        "verify_failures": verify_failures,
    }


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------


def run_shadow_for_job(
    session: Session,
    extraction_job_id: str,
    *,
    raw_text: str,
    supplier_context: dict | None,
    knowledge_links: list[dict] | None,
) -> dict:
    """v7 呼び出し＋システム判定を1ジョブ分実行し、shadow の表に書く。

    例外はすべてここで吸収する。本番の extraction_jobs / analysis_results には
    一切書き込まず、呼び出し元（tcg_extraction._run_extraction）にも例外を
    伝播しない（design.md PR-C: 「例外が起きても本番には伝えない」）。
    """
    input_bytes = len(raw_text.encode("utf-8"))
    started_at = datetime.now(timezone.utc)

    try:
        raw_copy = call_gemini_raw_copy(
            raw_text, supplier_context=supplier_context, knowledge_links=knowledge_links
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("[extraction_shadow] gemini call failed ej=%s: %s", extraction_job_id, exc)
        return _record_failed_run(
            session, extraction_job_id, input_bytes, None, "GEMINI_CALL_FAILED", str(exc),
            started_at=started_at,
        )

    response_text = raw_copy["response_text"]
    usage_counts: UsageCounts = raw_copy.get("usage_counts") or UsageCounts()

    try:
        blocks, parse_errors = parse_raw_copy_response(response_text, raw_text)
    except Exception as exc:  # noqa: BLE001
        logger.error("[extraction_shadow] parse failed ej=%s: %s", extraction_job_id, exc)
        return _record_failed_run(
            session, extraction_job_id, input_bytes, response_text, "PARSE_FAILED", str(exc),
            usage_counts=usage_counts, started_at=started_at,
        )

    try:
        products = load_product_entries(session)
        cond_entries = load_condition_entries(session)
        status_entries = load_status_master(session)
        note_entries = load_note_master(session)
        (_pc, _ua, _uc, _ca, cond_canonical_to_uuid, unit_alias_to_info) = load_lookup_maps(session)

        results = [
            _judge_block(
                block_item,
                raw_text,
                products=products,
                cond_entries=cond_entries,
                cond_canonical_to_uuid=cond_canonical_to_uuid,
                unit_alias_to_info=unit_alias_to_info,
                status_entries=status_entries,
                note_entries=note_entries,
            )
            for block_item in blocks
        ]

        run_id = insert_shadow_run(
            session,
            extraction_job_id=extraction_job_id,
            prompt_key=_PROMPT_KEY,
            engine_version=RAW_COPY_PROMPT_VERSION,
            requested_model=_REQUESTED_MODEL,
            input_bytes=input_bytes,
            response_text=response_text,
            status="completed",
            started_at=started_at,
        )
        record_usage_event_sync(
            session,
            purpose="line_extraction_shadow",
            model=_REQUESTED_MODEL,
            sdk="google-genai",
            counts=usage_counts,
            extraction_shadow_run_id=run_id,
        )
        insert_shadow_results(session, run_id, results)
        session.commit()
        return {
            "status": "completed",
            "run_id": run_id,
            "blocks": len(results),
            "parse_errors": len(parse_errors),
        }
    except Exception:  # noqa: BLE001
        session.rollback()
        logger.exception("[extraction_shadow] judgement/persist failed ej=%s", extraction_job_id)
        return {"status": "failed", "error_code": "JUDGEMENT_FAILED"}


def _record_failed_run(
    session: Session,
    extraction_job_id: str,
    input_bytes: int,
    response_text: str | None,
    error_code: str,
    error_detail: str,
    *,
    usage_counts: UsageCounts | None = None,
    started_at: datetime | None = None,
) -> dict:
    """Gemini 呼び出し／パース失敗を failed run として記録する（記録自体の失敗も吸収）。

    usage_counts が None なのは呼び出し自体が失敗した場合（応答が無く usage 不明）。
    その場合は llm_usage_events に行を作らない（design.md: 推測で作らない）。
    """
    try:
        run_id = insert_shadow_run(
            session,
            extraction_job_id=extraction_job_id,
            prompt_key=_PROMPT_KEY,
            engine_version=RAW_COPY_PROMPT_VERSION,
            requested_model=_REQUESTED_MODEL,
            input_bytes=input_bytes,
            response_text=response_text,
            status="failed",
            error_code=error_code,
            error_detail=error_detail[:2000],
            started_at=started_at,
        )
        if usage_counts is not None:
            record_usage_event_sync(
                session,
                purpose="line_extraction_shadow",
                model=_REQUESTED_MODEL,
                sdk="google-genai",
                counts=usage_counts,
                extraction_shadow_run_id=run_id,
            )
        session.commit()
    except Exception:  # noqa: BLE001
        session.rollback()
        logger.exception(
            "[extraction_shadow] failed to record failed run ej=%s code=%s",
            extraction_job_id,
            error_code,
        )
    return {"status": "failed", "error_code": error_code}


__all__ = [
    "load_product_entries",
    "insert_shadow_run",
    "insert_shadow_results",
    "run_shadow_for_job",
]
