"""要確認の一覧を CSV で出し、直した CSV をアプリに戻す（出力 → 内容確認 → 反映）。

設計: docs/handoff/review-csv-roundtrip/design.md §4。前例: tcg_product_roundtrip_svc（2段・digest・数式注入の対策・2MiB）。
- 一覧の正本: fetch_analysis_results(status_tab=NEEDS_REVIEW)。列は REVIEW_SHEET_HEADERS の 13 列 + 入力 2 列 + 版。
- 入力できるのは 1 行につき「正しい商品の番号(product_code)」か「このままで良い(○)」のどちらか一方。
- 検査は v102_human_decisions_svc の product_rejection / review_ack_rejection（画面の API と同じ関数）。
- 保存は save_corrections / save_review_ack（画面で直したときと同じ記録）。CSV 自体は保存しない。
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.item_corrections_svc import save_corrections
from app.services.review_reason_codes_svc import load_review_reason_codes
from app.services.tcg_analysis_review_svc import fetch_analysis_results
from app.services.tcg_distribution_svc import DIST_ROW_LIMIT
from app.services.tcg_product_roundtrip_svc import RoundtripError, escape_cell, read_records
from app.services.tcg_review_sheet_svc import REVIEW_SHEET_HEADERS, build_review_rows, load_review_reason_labels
from app.services.v102_human_decisions_svc import (
    FIELD_PRODUCT_ID,
    find_job_of_item,
    invalid_product_values,
    product_rejection,
    review_ack_rejection,
    save_review_ack,
)
from app.tasks.tcg_extraction import enqueue_v102_reanalyze

logger = logging.getLogger(__name__)

COL_PRODUCT_CODE = "正しい商品の番号"
COL_ACK = "このままで良い"
COL_REVISION = "版"
CSV_COLUMNS = [*REVIEW_SHEET_HEADERS, COL_PRODUCT_CODE, COL_ACK, COL_REVISION]
ITEM_ID_COLUMN = "件の番号"
ACK_MARKS = frozenset({"○", "〇", "◯"})
FIRST_DATA_LINE = 2  # 見出しが 1 行目

KIND_PRODUCT = "product"
KIND_ACK = "ack"

# 行ごとのエラーコード（画面が t() で文言にする）
ERR_ROW_SHAPE = "REVIEW_CSV_ROW_SHAPE"
ERR_NOT_NEEDS_REVIEW = "REVIEW_CSV_NOT_NEEDS_REVIEW"
ERR_STALE = "REVIEW_CSV_STALE_REVISION"
ERR_BOTH = "REVIEW_CSV_BOTH_INPUTS"
ERR_BAD_MARK = "REVIEW_CSV_BAD_ACK_MARK"
ERR_NOT_V102 = "REVIEW_CSV_NOT_V102"
ERR_CODE_NOT_FOUND = "REVIEW_CSV_PRODUCT_CODE_NOT_FOUND"
ERR_CODE_AMBIGUOUS = "REVIEW_CSV_PRODUCT_CODE_AMBIGUOUS"
ERR_NO_ACKABLE = "REVIEW_CSV_NO_ACKABLE_REASON"
ERR_REJECTED = "REVIEW_CSV_REJECTED"
ERR_DUPLICATE = "REVIEW_CSV_DUPLICATE_ITEM"
# ファイル全体のエラー（RoundtripError のコード）
FILE_HEADER = "REVIEW_CSV_HEADER_MISMATCH"
FILE_DIGEST = "REVIEW_CSV_DIGEST_MISMATCH"


def item_revision(item: dict) -> str:
    """その件の今の状態の版。extraction_item_id・review_reasons・product_id を決まった順でつないだ SHA256。"""
    reasons = ",".join(d["code"] for d in item.get("review_reason_details", []))
    joined = "\n".join([item["extraction_item_id"], reasons, item["system"].get("product_uuid", "")])
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


async def _fetch_items(db: AsyncSession) -> list[dict]:
    data = await fetch_analysis_results(db, status_tab="NEEDS_REVIEW", limit=DIST_ROW_LIMIT)
    return data["items"]


def _write_csv(rows: list[list[str]]) -> bytes:
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        writer.writerow([escape_cell(cell) for cell in row])
    return ("﻿" + out.getvalue()).encode("utf-8")


async def export_csv(db: AsyncSession) -> bytes:
    """要確認の一覧を CSV(UTF-8 BOM 付き)にする。入力 2 列は空、版は件ごとの今の状態。"""
    items = await _fetch_items(db)
    base_rows = build_review_rows(items, load_review_reason_labels())
    rows = [[*base, "", "", item_revision(item)] for base, item in zip(base_rows, items, strict=True)]
    return _write_csv(rows)


# ---------------------------------------------------------------------------
# 内容確認（DB に書かない）
# ---------------------------------------------------------------------------


def _error(line: int, item_id: str, code: str, detail: str = "") -> dict:
    return {"line": line, "extraction_item_id": item_id, "code": code, "detail": detail}


def _read_rows(raw: bytes) -> list[dict[str, str]]:
    records = read_records(raw)
    if not records or records[0] != CSV_COLUMNS:
        raise RoundtripError(FILE_HEADER)
    rows = []
    for number, record in enumerate(records[1:], start=FIRST_DATA_LINE):
        if len(record) != len(CSV_COLUMNS):
            rows.append({"_line": str(number), "_shape": "bad"})
            continue
        rows.append({"_line": str(number), **dict(zip(CSV_COLUMNS, record, strict=True))})
    return rows


async def _product_ids_by_code(db: AsyncSession, codes: set[str]) -> dict[str, list[int]]:
    if not codes:
        return {}
    result = await db.execute(
        text("SELECT product_code, id FROM public.products WHERE product_code = ANY(:codes)"),
        {"codes": sorted(codes)},
    )
    found: dict[str, list[int]] = {}
    for row in result.fetchall():
        found.setdefault(row[0], []).append(int(row[1]))
    return found


def _classify_row(row: dict[str, str], items: dict[str, dict]) -> tuple[dict | None, dict | None]:
    """行 → (入力のある行の要約, 行のエラー)。入力が無い行は (None, None)。商品の番号の引きと保存前の検査はあとで行う。"""
    line = int(row["_line"])
    if "_shape" in row:
        return None, _error(line, "", ERR_ROW_SHAPE)
    code = row[COL_PRODUCT_CODE].strip()
    mark = row[COL_ACK].strip()
    if not code and not mark:
        return None, None
    item_id = row[ITEM_ID_COLUMN].strip()
    item = items.get(item_id)
    if item is None:
        return None, _error(line, item_id, ERR_NOT_NEEDS_REVIEW)
    if row[COL_REVISION].strip() != item_revision(item):
        return None, _error(line, item_id, ERR_STALE)
    if code and mark:
        return None, _error(line, item_id, ERR_BOTH)
    if mark and mark not in ACK_MARKS:
        return None, _error(line, item_id, ERR_BAD_MARK)
    if not item.get("is_v102"):
        return None, _error(line, item_id, ERR_NOT_V102)
    return {"line": line, "item": item, "code": code}, None


async def _validate_product(db: AsyncSession, entry: dict, ids_by_code: dict[str, list[int]]) -> tuple[dict | None, dict | None]:
    line, item, code = entry["line"], entry["item"], entry["code"]
    item_id = item["extraction_item_id"]
    ids = ids_by_code.get(code, [])
    if not ids:
        return None, _error(line, item_id, ERR_CODE_NOT_FOUND, code)
    if len(ids) > 1:
        return None, _error(line, item_id, ERR_CODE_AMBIGUOUS, code)
    product_id = str(ids[0])
    rejected = product_rejection(await invalid_product_values(db, [product_id]))
    if rejected is not None:
        return None, _error(line, item_id, ERR_REJECTED, rejected.message)
    return {"extraction_item_id": item_id, "kind": KIND_PRODUCT, "value": product_id, "code": code}, None


async def _validate_ack(db: AsyncSession, entry: dict, registered: dict) -> tuple[dict | None, dict | None]:
    line, item = entry["line"], entry["item"]
    item_id = item["extraction_item_id"]
    codes = [d["code"] for d in item.get("review_reason_details", []) if d["ackable"]]
    if not codes:
        return None, _error(line, item_id, ERR_NO_ACKABLE)
    found = await find_job_of_item(db, item_id)
    rejected = review_ack_rejection(codes, registered, found, item["source_message_id"])
    if rejected is not None:
        return None, _error(line, item_id, ERR_REJECTED, rejected.message)
    return {"extraction_item_id": item_id, "kind": KIND_ACK, "value": ",".join(codes), "code": ""}, None


def _digest(applies: list[dict]) -> str:
    canonical = json.dumps(
        sorted(({k: a[k] for k in ("extraction_item_id", "kind", "value")} for a in applies), key=lambda a: a["extraction_item_id"]),
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _inspect(db: AsyncSession, raw: bytes) -> dict[str, Any]:
    rows = _read_rows(raw)
    items = {item["extraction_item_id"]: item for item in await _fetch_items(db)}
    entries: list[dict] = []
    errors: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        entry, error = _classify_row(row, items)
        if error is not None:
            errors.append(error)
        elif entry is not None:
            item_id = entry["item"]["extraction_item_id"]
            if item_id in seen:
                errors.append(_error(entry["line"], item_id, ERR_DUPLICATE))
            else:
                seen.add(item_id)
                entries.append(entry)
    ids_by_code = await _product_ids_by_code(db, {e["code"] for e in entries if e["code"]})
    registered = await load_review_reason_codes(db) if any(not e["code"] for e in entries) else {}
    applies: list[dict] = []
    for entry in entries:
        if entry["code"]:
            apply, error = await _validate_product(db, entry, ids_by_code)
        else:
            apply, error = await _validate_ack(db, entry, registered)
        if error is not None:
            errors.append(error)
        else:
            applies.append({**apply, "_item": entry["item"], "line": entry["line"]})
    errors.sort(key=lambda e: e["line"])
    return {"total_rows": len(rows), "applies": applies, "errors": errors}


def _public_apply(apply: dict) -> dict:
    item = apply["_item"]
    return {
        "line": apply["line"], "extraction_item_id": apply["extraction_item_id"], "kind": apply["kind"],
        "product_code": apply["code"], "name": item["gemini"].get("name", ""),
    }


async def preview(db: AsyncSession, raw: bytes) -> dict[str, Any]:
    """内容確認。DB には書かない。反映する件・エラーの件と理由・digest を返す。"""
    checked = await _inspect(db, raw)
    return {
        "total_rows": checked["total_rows"],
        "applies": [_public_apply(a) for a in checked["applies"]],
        "errors": checked["errors"],
        "digest": _digest(checked["applies"]),
    }


# ---------------------------------------------------------------------------
# 反映
# ---------------------------------------------------------------------------


async def _save_one(db: AsyncSession, apply: dict, corrected_by: str) -> None:
    item = apply["_item"]
    item_id, source = apply["extraction_item_id"], item["source_message_id"]
    if apply["kind"] == KIND_PRODUCT:
        await save_corrections(
            db, extraction_item_id=item_id, source_message_id=source, corrected_by=corrected_by,
            fields=[{"field_name": FIELD_PRODUCT_ID, "system_value": item["system"].get("product_uuid", ""), "human_value": apply["value"]}],
        )
    else:
        await save_review_ack(
            db, extraction_item_id=item_id, source_message_id=source, codes=apply["value"].split(","), corrected_by=corrected_by,
        )


async def commit(db: AsyncSession, raw: bytes, confirmed_digest: str, corrected_by: str) -> dict[str, Any]:
    """検査をやり直し、digest が確認時と違えば 409 で止めて何も書かない。同じなら既存の関数で 1 件ずつ保存し、投稿ごとに再解析を 1 回積む。"""
    checked = await _inspect(db, raw)
    if _digest(checked["applies"]) != confirmed_digest:
        raise RoundtripError(FILE_DIGEST, 409)
    saved = 0
    failed: list[dict] = []
    job_ids: dict[str, None] = {}
    for apply in checked["applies"]:
        try:
            await _save_one(db, apply, corrected_by)
        except Exception:  # noqa: BLE001  1件の失敗で残りを止めない。理由は記録して画面に返す
            await db.rollback()
            logger.warning("[review_csv] save failed: item=%s", apply["extraction_item_id"], exc_info=True)
            failed.append(_error(apply["line"], apply["extraction_item_id"], "REVIEW_CSV_SAVE_FAILED"))
            continue
        saved += 1
        found = await find_job_of_item(db, apply["extraction_item_id"])
        if found is not None:
            job_ids.setdefault(found.job_id)
    for job_id in job_ids:
        enqueue_v102_reanalyze(job_id)
    return {"saved": saved, "failed": failed, "reanalyze_jobs": len(job_ids), "errors": checked["errors"]}
