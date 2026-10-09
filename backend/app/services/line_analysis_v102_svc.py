"""LINE解析の本番エンジン v102（Gemini が原文の行を書き写し、システムが商品・状態・価格・数量を決める）の本番部品。

設計: docs/handoff/v102-prod-switch/design.md §4-1・§4-2・§4-4・§4-5、実装カード: docs/handoff/v102-prod-switch/card-B.md
このファイルが v102 の本番部品の唯一の置き場。試作版の道具（app/tools/prompt_ab.py）は、ここから部品を読み込んで使う。

2段に分ける:
  - Gemini 段  run_v102_extraction: 指示書を DB から読み Gemini を呼ぶ。応答の件を extraction_items に保存する（判定しない）。
  - システム段 run_v102_analysis  : 保存済みの件から商品・単位・状態・価格・数量を決め analysis_results に書く（Gemini を呼ばない）。
どちらを使うかは環境変数 LINE_ANALYSIS_ENGINE（既定 v6）で決める。投稿ごとの版は extraction_jobs.prompt_version（`v102:` 始まり）に残る。
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services import tcg_analyzer_svc as analyzer
from app.services.extraction_judgement_svc import order_from_pattern
from app.services.gemini_extraction_svc import _GEMINI_MODEL, _classify_error, _safe_error_message
from app.services.gemini_raw_copy_v8 import build_prompt_v8, call_gemini_raw_copy_v8
from app.services.gemini_raw_copy_v101 import (
    V101_PROMPT_NAME_RE,
    V102_RESPONSE_SCHEMA,
    extract_v101_items,
    parse_v101_response,
    parse_v102_unsure,
)
from app.services.gemini_raw_copy_v102_context_work import MATCH_STATUS_MATCHED, MATCH_STATUS_MATCHED_CONTEXT
from app.services.gemini_raw_copy_v102_followup import MATCH_STATUS_MATCHED_FOLLOWUP
from app.services.gemini_raw_copy_v102_product_first import load_product_first_masters
from app.services.llm_budget import record_usage_event_sync
from app.services.tcg_extraction_record_svc import RecordError
from app.services.v102_human_decisions_svc import Decisions, load_v102_decisions

logger = logging.getLogger(__name__)

# --- 版の切り替え（定義はここだけ） ---------------------------------------------------------
ENGINE_ENV = "LINE_ANALYSIS_ENGINE"
ENGINE_V6 = "v6"
ENGINE_V102 = "v102"
V102_ENGINE_VERSION = "v102-f_c"  # analysis_results.engine_version
V102_THINKING_LEVEL = "high"  # PO 採用 2026-10-08（試作版の試験と同じ）
V102_PROMPT_KEY = "raw_copy_v101_f_c"  # public.extraction_prompt_config の prompt_key（既定の指示書）
V102_PROMPT_VERSION_PREFIX = "v102:"  # extraction_jobs.prompt_version の先頭。再解析はこれで v6 / v102 を見分ける
V102_PROMPT = V102_PROMPT_KEY  # 試作版 prompt_ab が使ってきた名前

# v102 で既定で外す、元からある仕入元ルールの欄（PO 2026-10-07：新2欄だけを読む形で採用確定）
LEGACY_SUPPLIER_FIELDS = (
    "extraction_price_format", "extraction_qty_format", "extraction_notes", "extraction_state_format",
    "extraction_order_pattern", "extraction_example_text", "extraction_ship_format",
)

_LEDGER_PURPOSE = "line_extraction"
_LEDGER_SDK = "google-genai"
_SOURCE_REF_PREFIX = "extraction_job:"
_PROMPT_HASH_LENGTH = 12

# 理由コード（このファイルが付けるもの）
REASON_RESPONSE_UNREADABLE = "response_unreadable"
REASON_EXTRACT_EXCEPTION = "extract_exception"
REASON_SEPARATOR = ","
# 人の判断で外す理由（condition_review で状態を決めたとき）
REASON_CONDITION_UNKNOWN = "condition_unknown"
REASON_CONDITION_MULTIPLE = "condition_multiple_candidates"
CONDITION_REVIEW_REASONS = (REASON_CONDITION_UNKNOWN, REASON_CONDITION_MULTIPLE)
# 人の判断で決めた印（analysis_results の pid_basis / condition_basis）
PID_BASIS_MANUAL = "MANUAL"
CONDITION_BASIS_MANUAL = "MANUAL_CONDITION_REVIEW"

# analysis_results の列の幅・精度（migrations/20260921_110000_pipeline_tables_public.sql）
_PID_BASIS_MAX = 100
_CONDITION_BASIS_MAX = 100
_NUMERIC_LIMIT = Decimal(10) ** 12  # NUMERIC(14,2)
_INT4_MAX = 2**31 - 1
_FLAG_SINGLE = "FLAG_SINGLE"
_FLAG_SINGLE_CODE = "CN0008"

_PROMPT_KEY_SQL = """
    SELECT prompt_text FROM public.extraction_prompt_config
    WHERE prompt_key = :key AND is_active = TRUE
"""


def get_engine() -> str:
    """本番の解析エンジン。環境変数が "v102" のときだけ v102、それ以外（未設定・空・不明値）は v6。不明値は警告を出す。"""
    value = os.environ.get(ENGINE_ENV, "").strip()
    if value == ENGINE_V102:
        return ENGINE_V102
    if value and value != ENGINE_V6:
        logger.warning("[line_analysis] %s=%r は不明な値のため %s で動かします", ENGINE_ENV, value, ENGINE_V6)
    return ENGINE_V6


def is_v102_prompt_version(prompt_version: object) -> bool:
    return isinstance(prompt_version, str) and prompt_version.startswith(V102_PROMPT_VERSION_PREFIX)


# ---------------------------------------------------------------------------
# 指示書・マスタ・仕入元ルール
# ---------------------------------------------------------------------------


def check_prompt_key_shape(prompt_key: str) -> None:
    """prompt_key の形の検査（本番の解析が使う名前・パス区切りを通さない）。DB には触れない。"""
    if not V101_PROMPT_NAME_RE.fullmatch(prompt_key):
        raise ValueError(f"--prompt-key は {V101_PROMPT_NAME_RE.pattern} の形だけ使えます: {prompt_key!r}")


def load_prompt_from_db(session: Session, prompt_key: str) -> str:
    """public.extraction_prompt_config の is_active な行の本文。形が違う・行が無い・本文が空なら ValueError。"""
    check_prompt_key_shape(prompt_key)
    row = session.execute(text(_PROMPT_KEY_SQL), {"key": prompt_key}).first()
    if row is None:
        raise ValueError(f"指示書の行が見つからない（無いか is_active でない）: {prompt_key}")
    body = row[0]
    if not isinstance(body, str) or not body.strip():
        raise ValueError(f"指示書の本文が空です: {prompt_key}")
    return body


def build_prompt_version(prompt_key: str, prompt_text: str) -> str:
    """extraction_jobs.prompt_version に残す値: `v102:<prompt_key>:<指示書本文の sha256 先頭12>`。"""
    digest = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:_PROMPT_HASH_LENGTH]
    return f"{V102_PROMPT_VERSION_PREFIX}{prompt_key}:{digest}"


def without_legacy_supplier_fields(supplier_context: dict | None) -> dict | None:
    """元からある7欄（LEGACY_SUPPLIER_FIELDS）を除いた写しを返す。元の辞書は変えない。None は None のまま。"""
    if supplier_context is None:
        return None
    return {k: v for k, v in supplier_context.items() if k not in LEGACY_SUPPLIER_FIELDS}


def effective_new_system_rules(new_system_rules: dict | None) -> dict | None:
    """v8 系にだけ渡す新2欄。値が全部空なら None。元の辞書は変えない。"""
    base = dict(new_system_rules or {})
    return base if any(base.values()) else None


def load_v102_masters(session: Session) -> tuple[dict, dict]:
    """(run_v102_pipeline に渡すマスタ, 単位 canonical → 単位 id)。読み取りのみ。商品・分類・状態の単位が空なら ValueError。

    試作版 prompt_ab._load_v10_masters(product_first=True) と同じ中身。prompt_ab が捨てている単位 id の索引も返す。
    """
    cond_entries = analyzer.load_condition_entries(session)
    status_entries = analyzer.load_status_master(session)
    (_pc, _ua, unit_canonical_to_uuid, _ca, cond_canonical_to_uuid, unit_alias_to_info) = analyzer.load_lookup_maps(session)
    masters = {
        "cond_entries": cond_entries, "cond_canonical_to_uuid": cond_canonical_to_uuid,
        "unit_alias_to_info": unit_alias_to_info, "status_entries": status_entries,
        "product_first": load_product_first_masters(session),
    }
    return masters, unit_canonical_to_uuid


# ---------------------------------------------------------------------------
# システム解析（応答テキスト → 件）。試作版 prompt_ab._v102_row_fields の本体
# ---------------------------------------------------------------------------


def _gemini_review(response_text: str, raw_text: str, extracted: list[dict]) -> list[dict]:
    """Gemini が unsure に書いた行（要確認）。システムの要確認（review・post_review）とは別に残す。"""
    price_lines = {it["price_line"] for it in extracted if isinstance(it.get("price_line"), int)}
    return parse_v102_unsure(response_text, len(raw_text.split("\n")), price_lines)


def _with_gemini_review(extracted: list[dict], unsure: list[dict]) -> list[dict]:
    """各件に gemini_review を付ける（既定 []）。price_line が unsure の candidates に入る件に gemini_unsure を足す。元の件は書き換えない。"""
    return [
        {
            **item,
            "gemini_review": [
                {"kind": u["kind"], "line": u["line"]}
                for u in unsure if u["kind"] == "gemini_unsure" and item.get("price_line") in u["candidates"]
            ],
        }
        for item in extracted
    ]


SOURCE_SYSTEM = "system"
SOURCE_GEMINI = "gemini"


def _with_source(element: dict, default: str = SOURCE_SYSTEM) -> dict:
    """要確認の要素に出どころ（source）を付ける。すでにあれば変えない。元の要素は書き換えない。"""
    return element if "source" in element else {**element, "source": default}


def _gemini_review_element(unsure_element: dict) -> dict:
    return {
        "line": unsure_element["line"], "kind": "gemini_unsure",
        "candidates": list(unsure_element["candidates"]), "source": SOURCE_GEMINI,
    }


def _invalid_unsure_post_review(unsure_element: dict) -> dict:
    """形が壊れた unsure（gemini_unsure_invalid）を post_review の要素に写す。見つけたのはシステム。原文の文字は載せない。"""
    out = {"kind": "gemini_unsure_invalid", "error": unsure_element.get("error")}
    for key in ("line", "candidates"):
        if key in unsure_element:
            out[key] = unsure_element[key]
    return {**out, "source": SOURCE_SYSTEM}


def _item_with_sources(item: dict, unsure: list[dict]) -> dict:
    """件の review の各要素に source を付け、price_line が候補に入る gemini_unsure を末尾に足す。件の gemini_review 欄はそのまま。"""
    added = [
        _gemini_review_element(u)
        for u in unsure if u.get("kind") == "gemini_unsure" and item.get("price_line") in u["candidates"]
    ]
    review = item.get("review")
    if review is None and not added:
        return item
    return {**item, "review": [*(_with_source(r) for r in (review or [])), *added]}


def _with_review_sources(fields: dict, unsure: list[dict]) -> dict:
    """要確認の出どころ（system／gemini）を v102_items の review と v102_flags の post_review に付ける。元の dict は書き換えない。"""
    flags = fields["v102_flags"]
    post_review = [
        *(_with_source(r) for r in flags.get("post_review", [])),
        *(_invalid_unsure_post_review(u) for u in unsure if u.get("kind") == "gemini_unsure_invalid"),
    ]
    new_flags = {**flags, "post_review": post_review} if post_review or "post_review" in flags else flags
    return {**fields, "v102_items": [_item_with_sources(it, unsure) for it in fields["v102_items"]], "v102_flags": new_flags}


def run_v102_pipeline(
    response_text: str, ctx, masters: dict, *, extract_items: Callable[..., tuple[list[dict], dict]] = extract_v101_items,
    fixed_products: dict[int, int] | None = None,
) -> dict:
    """v102 の行に足す v102_items（F1〜F6 あり・付け直しあり）・v102_flags。v101 の欄は書かない。失敗しても止めない。

    落とした件は捨てずに v102_items の最後に残し、読めない応答・例外は v102_flags["post_review"] に残す（設計 docs/handoff/v102-no-silent-drop/design.md）。
    ctx は raw_text と supplier_context を持つもの。extract_items は試験の道具（prompt_ab）からの差し替え用（既定は本番と同じ extract_v101_items）。
    fixed_products：人が決めた商品（受理した件の位置 → 商品 id）。空・None のときは extract_items に渡さない（結果は今と同じ）。
    """
    try:
        items, errors = parse_v101_response(
            response_text, ctx.raw_text, status_entries=masters["status_entries"], keep_rejected=True
        )
        order = order_from_pattern((ctx.supplier_context or {}).get("extraction_order_pattern"))
        fixed = {"fixed_products": fixed_products} if fixed_products else {}
        extracted, flags = extract_items(
            items, ctx.raw_text, order=order, reassign=True, v102_fixes=True, review_reasons=True, **masters, **fixed
        )
        if not items and errors:
            flags = {**flags, "post_review": [{"kind": "response_unreadable", "error": errors[0]["error"]}]}
        unsure = _gemini_review(response_text, ctx.raw_text, extracted)
        return _with_review_sources(
            {
                "v102_items": _with_gemini_review(extracted, unsure),
                "v102_flags": {**flags, "gemini_review": unsure},
            },
            unsure,
        )
    except Exception as exc:  # noqa: BLE001
        message = f"{type(exc).__name__}: {_safe_error_message(exc)}"
        return {
            "v102_items": [], "v102_items_error": message,
            "v102_flags": {
                "post_review": [{"kind": "extract_exception", "error": message, "source": SOURCE_SYSTEM}],
                "gemini_review": [],
            },
        }


# ---------------------------------------------------------------------------
# Gemini 段
# ---------------------------------------------------------------------------


def _is_plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _source_lines(item: object) -> list[int] | None:
    """件の lines。整数のリスト（INTEGER の範囲内）のときだけそのまま、それ以外は None。"""
    lines = item.get("lines") if isinstance(item, dict) else None
    if not isinstance(lines, list) or not all(_is_plain_int(n) and 0 <= n <= _INT4_MAX for n in lines):
        return None
    return list(lines)


def _raw_text_value(value: object) -> str | None:
    """price・quantity の保存形。文字列はそのまま、None は NULL、それ以外は JSON 文字列。"""
    if value is None or isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _parse_items(response_text: str) -> tuple[list | None, object]:
    """(Gemini の items, unsure)。応答が JSON でない・dict でない・items が list でないときは (None, None)。"""
    try:
        data = json.loads(response_text)
    except (json.JSONDecodeError, TypeError):
        return None, None
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return None, None
    return data["items"], data.get("unsure")


def _item_rows(items: list) -> list[dict]:
    """Gemini の items の i 番目ごとに1行（gemini_index=i）。判定しない。"""
    rows = []
    for index, item in enumerate(items):
        lines = _source_lines(item)
        rows.append({
            "gemini_index": index, "source_lines": lines,
            "line_start": min(lines) if lines else None, "line_end": max(lines) if lines else None,
            "raw_price": _raw_text_value(item.get("price") if isinstance(item, dict) else None),
            "raw_quantity": _raw_text_value(item.get("quantity") if isinstance(item, dict) else None),
        })
    return rows


def _record_usage(session: Session, result: dict, extraction_job_id: str, attempt_id: str | None) -> None:
    """応答を受けたら1回、llm_usage_events に書く（ADR-1004）。保存の成否に関わらず呼ぶ。台帳の失敗で抽出を止めない。"""
    try:
        record_usage_event_sync(
            session, purpose=_LEDGER_PURPOSE, model=_GEMINI_MODEL, sdk=_LEDGER_SDK, counts=result["usage_counts"],
            source_ref=f"{_SOURCE_REF_PREFIX}{extraction_job_id}", extraction_attempt_id=attempt_id,
        )
        session.commit()
    except Exception:  # noqa: BLE001
        session.rollback()
        logger.exception("[line_analysis] 費用の台帳に書けませんでした: job=%s", extraction_job_id)


def _call_gemini(session: Session, ctx, prompt_text: str, extraction_job_id: str, recorder) -> dict:
    """Gemini を呼ぶ。recorder があれば呼ぶ前に試行を記録し（job を running にする）、失敗は固定コードの RecordError にする。"""
    supplier_context = without_legacy_supplier_fields(ctx.supplier_context)
    new_rules = effective_new_system_rules(ctx.new_system_rules)
    if recorder is not None:
        recorder.before_send({
            "model": _GEMINI_MODEL,
            "contents": build_prompt_v8(
                ctx.raw_text, prompt_text=prompt_text, supplier_context=supplier_context,
                knowledge_links=ctx.knowledge_links, new_system_rules=new_rules,
            ),
            "config": {
                "thinking_level": V102_THINKING_LEVEL, "include_thoughts": True,
                "response_mime_type": "application/json", "response_json_schema": V102_RESPONSE_SCHEMA,
            },
        })
    session.commit()  # 外部呼び出しの間、DB の取引を持ち越さない
    try:
        return call_gemini_raw_copy_v8(
            ctx.raw_text, prompt_text=prompt_text, supplier_context=supplier_context,
            knowledge_links=ctx.knowledge_links, thinking_level=V102_THINKING_LEVEL, include_thoughts=True,
            use_schema=True, temperature=None, response_schema=V102_RESPONSE_SCHEMA, new_system_rules=new_rules,
        )
    except SoftTimeLimitExceeded:
        raise
    except Exception as exc:
        if recorder is None:
            raise
        recorder.record_error_detail({"raw": _safe_error_message(exc), "category": _classify_error(exc)})
        raise RecordError("API_ERROR") from None


def run_v102_extraction(session: Session, extraction_job_id: str, *, recorder=None) -> dict:
    """Gemini 段。指示書を DB から読んで Gemini を呼び、応答の件を extraction_items に保存し、extraction_jobs を更新する。

    判定はしない。recorder（AttemptRecorder）があれば、試行の記録（extraction_attempts）に乗せる。
    Gemini の呼び出しの失敗は呼び出し元へ送出する（recorder があれば RecordError("API_ERROR")）。
    戻り値: {"status": done/empty, "items_count", "prompt_version", "review_reasons"}。
    """
    from app.tasks.tcg_extraction import load_extraction_context  # noqa: PLC0415  循環 import を避ける

    ctx = load_extraction_context(session, extraction_job_id)
    if ctx is None:
        raise ValueError(f"extraction_job が見つかりません: {extraction_job_id}")
    prompt_text = load_prompt_from_db(session, V102_PROMPT_KEY)
    prompt_version = build_prompt_version(V102_PROMPT_KEY, prompt_text)
    if recorder is not None:
        recorder.prompt_version = prompt_version
    result = _call_gemini(session, ctx, prompt_text, extraction_job_id, recorder)

    response_text = result["response_text"]
    pending: Exception | None = None
    if recorder is not None:
        try:
            recorder.on_response(response_text)  # 費用は下の _record_usage だけが書く（二重に書かない）
        except Exception as exc:  # noqa: BLE001
            pending = exc
    _record_usage(session, result, extraction_job_id, recorder.id if recorder is not None else None)
    if pending is not None:
        raise pending

    items, unsure = _parse_items(response_text)
    rows = _item_rows(items or [])
    if recorder is not None:
        rows = [{**row, "id": r["extraction_item_id"]} for row, r in zip(rows, recorder.prepare_items(rows), strict=True)]
    schema = analyzer.TCG_SCHEMA
    session.execute(text(f"DELETE FROM {schema}.extraction_items WHERE extraction_job_id = :ej"), {"ej": extraction_job_id})
    for row in rows:
        session.execute(
            text(f"""
                INSERT INTO {schema}.extraction_items (
                    id, extraction_job_id, line_start, line_end, raw_price, raw_quantity,
                    source_lines, gemini_index, created_at
                ) VALUES (
                    :id, :ej, :line_start, :line_end, :raw_price, :raw_quantity,
                    CAST(:source_lines AS INTEGER[]), :gemini_index, now()
                )
            """),
            {**row, "id": row.get("id") or str(uuid.uuid4()), "ej": extraction_job_id},
        )
    if recorder is not None:
        recorder.complete(rows)
    status = "done" if rows else "empty"
    review_reasons = REASON_RESPONSE_UNREADABLE if items is None else None
    session.execute(
        text(f"""
            UPDATE {schema}.extraction_jobs
            SET status = :status, extracted_at = :extracted_at, prompt_version = :prompt_version, error_message = NULL,
                gemini_unsure = CAST(:unsure AS JSONB), review_reasons = :review_reasons
            WHERE id = :ej
        """),
        {
            "status": status, "extracted_at": datetime.now(timezone.utc), "prompt_version": prompt_version,
            "unsure": None if unsure is None else json.dumps(unsure, ensure_ascii=False),
            "review_reasons": review_reasons, "ej": extraction_job_id,
        },
    )
    session.commit()
    return {"status": status, "items_count": len(rows), "prompt_version": prompt_version, "review_reasons": review_reasons}


# ---------------------------------------------------------------------------
# システム段
# ---------------------------------------------------------------------------


class _MappingError(Exception):
    """v102 の件と extraction_items の行の対応が付かない。"""


def _kinds(entries: list[dict]) -> list[str]:
    return [e["kind"] for e in entries if isinstance(e, dict) and e.get("kind")]


def _join_unique(kinds: list[str]) -> str | None:
    """出た順で重複なしにカンマ結合。空なら None。"""
    unique = list(dict.fromkeys(kinds))
    return REASON_SEPARATOR.join(unique) if unique else None


def _response_from_rows(rows: list, gemini_unsure: object) -> str:
    """保存済みの件から、Gemini の応答と同じ形の JSON を組み立てる。"""
    body: dict = {"items": [{"lines": r.source_lines, "price": r.raw_price, "quantity": r.raw_quantity} for r in rows]}
    if gemini_unsure is not None:
        body["unsure"] = gemini_unsure
    return json.dumps(body, ensure_ascii=False)


def _lines_agree(item: dict, row: object) -> bool:
    """件の行番号が、対応する行の source_lines（Gemini 応答の lines）と合うか。

    F1・付け直しは件の lines を書き換える（価格の行は動かさない）ので、lines の全一致ではなく次で見る。
    price_line がある件は「price_line が source_lines に入る」、無い件は「lines と source_lines に共通の行がある」。
    どちらかの行番号が空なら照合しない。
    """
    source = getattr(row, "source_lines", None)
    if not source:
        return True
    price_line = item.get("price_line")
    if isinstance(price_line, int) and not isinstance(price_line, bool):
        return price_line in source
    lines = item.get("lines")
    if not isinstance(lines, list) or not lines:
        return True
    return bool(set(lines) & set(source))


def _map_to_rows(v102_items: list[dict], rows: list) -> list[tuple[dict, object]]:
    """v102 の件を extraction_items の行に対応付ける（gemini_index 順の rows を受ける）。

    落とした件（rejected）は自分の gemini_index を持つ。残りの件は Gemini の順を保つので、
    落とした件を除いた行を gemini_index の昇順に並べたものと、先頭から1対1で対応する。件数が合わなければ _MappingError。
    """
    by_index = {r.gemini_index: r for r in rows}
    rejected = [it for it in v102_items if it.get("rejected")]
    accepted = [it for it in v102_items if not it.get("rejected")]
    rejected_indexes = [it.get("gemini_index") for it in rejected]
    if len(v102_items) != len(rows) or any(i not in by_index for i in rejected_indexes) or len(set(rejected_indexes)) != len(rejected):
        raise _MappingError(f"件数が合いません: v102={len(v102_items)} extraction_items={len(rows)}")
    rest = [r for r in rows if r.gemini_index not in set(rejected_indexes)]
    if len(rest) != len(accepted):
        raise _MappingError(f"受理した件の数が合いません: v102={len(accepted)} extraction_items={len(rest)}")
    pairs = [*zip(rejected, (by_index[i] for i in rejected_indexes), strict=True), *zip(accepted, rest, strict=True)]
    for item, row in pairs:
        if not _lines_agree(item, row):
            raise _MappingError(f"行番号が合いません: gemini_index={row.gemini_index}")
    return pairs


def _bounded_number(value: object) -> object:
    """NUMERIC(14,2) に入らない値は None（価格が None の件は配信されない）。"""
    if value is None:
        return None
    try:
        return value if abs(Decimal(str(value))) < _NUMERIC_LIMIT else None
    except Exception:  # noqa: BLE001
        return None


def _condition_columns(canonical: str | None, masters: dict) -> tuple[str, int, bool]:
    """(condition_canonical, condition_id, 解けたか)。未解決（none・不明・マスタに無い）は v6 と同じ FLAG_SINGLE（CN0008）。"""
    entries, by_canonical = masters["cond_entries"], masters["cond_canonical_to_uuid"]
    cond_id = by_canonical.get(canonical) if canonical else None
    if cond_id is None and canonical:
        cond_id = next((e["cond_id"] for e in entries if e.get("canonical") == canonical), None)
    if cond_id is not None:
        return canonical, int(cond_id), True
    fallback = analyzer._find_cond_id(entries, _FLAG_SINGLE_CODE) or by_canonical.get(_FLAG_SINGLE)
    if fallback is None:
        raise _MappingError("FLAG_SINGLE の状態 id が引けません")
    return _FLAG_SINGLE, int(fallback), False


_RESOLVED_MATCH_STATUSES = (MATCH_STATUS_MATCHED, MATCH_STATUS_MATCHED_CONTEXT, MATCH_STATUS_MATCHED_FOLLOWUP)


def _analysis_values(item: dict, masters: dict, unit_ids: dict, work_ids: dict) -> dict:
    """v102 の1件 → analysis_results の列（設計 §4-4）。"""
    product_id = item.get("product_id")
    matched = product_id is not None and item.get("match_status") in _RESOLVED_MATCH_STATUSES
    unit = item.get("unit")
    unit_canonical = None if unit in (None, "none") else unit
    unit_id = unit_ids.get(unit_canonical) if unit_canonical else None
    condition = item.get("condition")
    condition_canonical, condition_id, _resolved = _condition_columns(None if condition in (None, "none") else condition, masters)
    reasons = _join_unique([*_kinds(item.get("review") or []), *_kinds(item.get("gemini_review") or [])])
    return {
        "product_id": product_id if matched else None, "pid_resolved": bool(matched),
        "pid_basis": f"V102:{item.get('match_status')}"[:_PID_BASIS_MAX],
        "unit_id": int(unit_id) if unit_id is not None else None, "unit_canonical": unit_canonical,
        "unit_resolved": unit_id is not None,
        "condition_id": condition_id, "condition_canonical": condition_canonical,
        "condition_basis": str(item.get("condition_basis") or "")[:_CONDITION_BASIS_MAX],
        "quantity_normalized": _bounded_number(item.get("quantity_normalized")),
        "price_normalized": _bounded_number(item.get("price_normalized")),
        "note_ja": None, "status": item.get("status"), "exclusion": item.get("status_effect"),
        "needs_review": reasons is not None, "review_reasons": reasons,
        "work_id": work_ids.get(product_id) if matched else None,
    }


_UPSERT_SQL = """
    INSERT INTO {schema}.analysis_results (
        id, extraction_item_id, product_id, pid_resolved, pid_basis, unit_id, unit_canonical, unit_resolved,
        condition_id, condition_canonical, condition_basis, quantity_normalized, price_normalized, note_ja,
        status, exclusion, needs_review, review_reasons, engine_version, computed_at, updated_at, work_id
    ) VALUES (
        :id, :extraction_item_id, :product_id, :pid_resolved, :pid_basis, :unit_id, :unit_canonical, :unit_resolved,
        :condition_id, :condition_canonical, :condition_basis, :quantity_normalized, :price_normalized, :note_ja,
        :status, :exclusion, :needs_review, :review_reasons, :engine_version, :computed_at, :updated_at, :work_id
    )
    ON CONFLICT (extraction_item_id) DO UPDATE SET
        product_id = EXCLUDED.product_id, pid_resolved = EXCLUDED.pid_resolved, pid_basis = EXCLUDED.pid_basis,
        unit_id = EXCLUDED.unit_id, unit_canonical = EXCLUDED.unit_canonical, unit_resolved = EXCLUDED.unit_resolved,
        condition_id = EXCLUDED.condition_id, condition_canonical = EXCLUDED.condition_canonical,
        condition_basis = EXCLUDED.condition_basis, quantity_normalized = EXCLUDED.quantity_normalized,
        price_normalized = EXCLUDED.price_normalized, note_ja = EXCLUDED.note_ja, status = EXCLUDED.status,
        exclusion = EXCLUDED.exclusion, needs_review = EXCLUDED.needs_review, review_reasons = EXCLUDED.review_reasons,
        engine_version = EXCLUDED.engine_version, computed_at = EXCLUDED.computed_at, updated_at = EXCLUDED.updated_at,
        work_id = EXCLUDED.work_id
"""


def _load_product_work_ids(session: Session, product_ids: list[int]) -> dict[int, int | None]:
    if not product_ids:
        return {}
    rows = session.execute(
        text("SELECT id, work_id FROM public.products WHERE id = ANY(:ids)"), {"ids": product_ids}
    ).fetchall()
    return {int(r[0]): (int(r[1]) if r[1] is not None else None) for r in rows}


def _set_job_review_reasons(session: Session, extraction_job_id: str, review_reasons: str | None) -> None:
    session.execute(
        text(f"UPDATE {analyzer.TCG_SCHEMA}.extraction_jobs SET review_reasons = :rr WHERE id = :ej"),
        {"rr": review_reasons, "ej": extraction_job_id},
    )


def _job_review_reasons(flags: dict) -> str | None:
    return _join_unique([*_kinds(flags.get("post_review") or []), *_kinds(flags.get("gemini_review") or [])])


def _split_reasons(reasons: str | None) -> list[str]:
    return [r for r in (reasons or "").split(REASON_SEPARATOR) if r]


def _load_condition_canonicals(session: Session, condition_ids: list[int]) -> dict[int, str]:
    if not condition_ids:
        return {}
    rows = session.execute(
        text("SELECT id, canonical FROM public.conditions WHERE id = ANY(:ids)"), {"ids": sorted(set(condition_ids))}
    ).fetchall()
    return {int(r[0]): str(r[1]) for r in rows}


def _apply_decisions(values: dict, item: dict, decision: Decisions | None, canonicals: dict[int, str]) -> dict:
    """人の判断を analysis_results の列に反映する（元の values は変えない）。

    商品を固定した件（結果の商品が判断と同じ）は pid_basis='MANUAL'。状態の判断がある件は condition を差し替え、
    理由 condition_unknown・condition_multiple_candidates を外す。確認済み（ack）の理由も外す。外した後に理由が空なら要確認を外す。
    """
    if decision is None or decision.is_empty:
        return values
    out = dict(values)
    drop: set[str] = set(decision.ack_codes)
    if decision.product_id is not None and values["pid_resolved"] and values["product_id"] == decision.product_id:
        out["pid_basis"] = PID_BASIS_MANUAL
    condition_name = canonicals.get(decision.condition_id) if decision.condition_id is not None else None
    if condition_name is not None:
        out.update(condition_id=decision.condition_id, condition_canonical=condition_name, condition_basis=CONDITION_BASIS_MANUAL)
        drop.update(CONDITION_REVIEW_REASONS)
    remaining = [r for r in _split_reasons(values["review_reasons"]) if r not in drop]
    out["review_reasons"] = REASON_SEPARATOR.join(remaining) if remaining else None
    out["needs_review"] = bool(remaining)
    return out


def _write_results(
    session: Session, extraction_job_id: str, pipeline: dict, rows: list, masters: dict, unit_ids: dict,
    decisions: dict[str, Decisions] | None = None,
) -> dict:
    decisions = decisions or {}
    v102_items = pipeline["v102_items"]
    if pipeline.get("v102_items_error") is not None:
        raise _MappingError(pipeline["v102_items_error"])
    pairs = _map_to_rows(v102_items, rows)
    matched_ids = [it["product_id"] for it, _ in pairs if it.get("product_id") is not None]
    work_ids = _load_product_work_ids(session, sorted(set(matched_ids)))
    canonicals = _load_condition_canonicals(session, [d.condition_id for d in decisions.values() if d.condition_id is not None])
    now = datetime.now(timezone.utc)
    stats = {"total": len(rows), "pid_resolved": 0, "unit_resolved": 0, "needs_review": 0}
    for item, row in pairs:
        values = _apply_decisions(
            _analysis_values(item, masters, unit_ids, work_ids), item, decisions.get(str(row.id)), canonicals
        )
        session.execute(
            text(_UPSERT_SQL.format(schema=analyzer.TCG_SCHEMA)),
            {**values, "id": str(uuid.uuid4()), "extraction_item_id": str(row.id), "engine_version": V102_ENGINE_VERSION,
             "computed_at": now, "updated_at": now},
        )
        stats["pid_resolved"] += int(values["pid_resolved"])
        stats["unit_resolved"] += int(values["unit_resolved"])
        stats["needs_review"] += int(values["needs_review"])
    _set_job_review_reasons(session, extraction_job_id, _job_review_reasons(pipeline["v102_flags"]))
    return stats


def _fixed_products(response_text: str, ctx, masters: dict, rows: list, decisions: dict[str, Decisions]) -> dict[int, int]:
    """人が決めた商品を、試作版の部品に渡す形（受理した件の位置 → 商品 id）にする。判断が無ければ空。

    位置は、落とした件（rejected）を除いた件を gemini_index の昇順に並べた順（_map_to_rows の対応と同じ）。
    """
    if not any(d.product_id is not None for d in decisions.values()):
        return {}
    items, _errors = parse_v101_response(
        response_text, ctx.raw_text, status_entries=masters["status_entries"], keep_rejected=True
    )
    rejected = {it["gemini_index"] for it in items if "rejected" in it}
    accepted = [r for r in rows if r.gemini_index not in rejected]
    return {
        position: decisions[str(row.id)].product_id
        for position, row in enumerate(accepted)
        if str(row.id) in decisions and decisions[str(row.id)].product_id is not None
    }


def _load_resolved_pairs(session: Session, extraction_job_id: str) -> list[tuple[int, int]]:
    """この投稿の今の (product_id, condition_id) の組。書き直す前に読み、is_current の付け直しに渡す。"""
    rows = session.execute(
        text(f"""
            SELECT DISTINCT ar.product_id, ar.condition_id
            FROM {analyzer.TCG_SCHEMA}.analysis_results ar
            JOIN {analyzer.TCG_SCHEMA}.extraction_items ei ON ei.id = ar.extraction_item_id
            WHERE ei.extraction_job_id = :ej AND ar.pid_resolved = TRUE AND ar.product_id IS NOT NULL
        """),
        {"ej": extraction_job_id},
    ).fetchall()
    return [(int(r[0]), int(r[1])) for r in rows]


FOLLOWUP_MAX_GAP_SECONDS = 3600  # 直前の投稿との時刻の差の上限（design §2-1）
FOLLOWUP_MAX_NONEMPTY_LINES = 10  # 今の投稿の空でない行数の上限（design §2-2）

_FOLLOWUP_CURRENT_SQL = """
    SELECT sm.supplier_channel_id, sm.line_posted_at, sm.raw_text
    FROM {schema}.extraction_jobs ej JOIN {schema}.source_messages sm ON sm.id = ej.source_message_id
    WHERE ej.id = :ej
"""
_FOLLOWUP_PREVIOUS_SQL = """
    SELECT prev.id, prev.raw_text, prev.line_posted_at
    FROM {schema}.source_messages prev
    WHERE prev.supplier_channel_id = :channel AND prev.line_posted_at < :posted_at
    ORDER BY prev.line_posted_at DESC, prev.id DESC
    LIMIT 1
"""


def load_followup_reference(session: Session, extraction_job_id: str) -> tuple[str, str] | None:
    """直前の投稿 (id, 原文)。同じ仕入元の、今の投稿より前で最も新しい1件（is_active は問わない）。

    時刻の差が FOLLOWUP_MAX_GAP_SECONDS 以下で、今の投稿の空でない行が FOLLOWUP_MAX_NONEMPTY_LINES 以下のときだけ返す。
    条件に合わないとき・直前の投稿が無いときは None。読み取りのみ。run_v102_analysis と prompt_ab_recompute が共通で呼ぶ。
    """
    schema = analyzer.TCG_SCHEMA
    current = session.execute(text(_FOLLOWUP_CURRENT_SQL.format(schema=schema)), {"ej": extraction_job_id}).first()
    if current is None or current.supplier_channel_id is None or current.line_posted_at is None:
        return None
    if sum(1 for line in (current.raw_text or "").split("\n") if line.strip()) > FOLLOWUP_MAX_NONEMPTY_LINES:
        return None
    previous = session.execute(
        text(_FOLLOWUP_PREVIOUS_SQL.format(schema=schema)),
        {"channel": current.supplier_channel_id, "posted_at": current.line_posted_at},
    ).first()
    if previous is None or previous.raw_text is None:
        return None
    if (current.line_posted_at - previous.line_posted_at).total_seconds() > FOLLOWUP_MAX_GAP_SECONDS:
        return None
    return str(previous.id), previous.raw_text


def masters_with_followup(masters: dict, followup_ref: tuple[str, str] | None) -> dict:
    """マスタに直前の投稿の参照を足した新しい辞書（run_v102_pipeline が extract_v101_items にそのまま渡す）。None なら元のまま。"""
    return masters if followup_ref is None else {**masters, "followup_ref": followup_ref}


def run_v102_analysis(session: Session, extraction_job_id: str) -> dict:
    """システム段。保存済みの件（extraction_items）から analysis_results を作る。Gemini を呼ばない。冪等。

    戻り値は analyze_extraction_job と同じ形のキー（total / pid_resolved / unit_resolved / needs_review）。
    v102 の処理の例外・件の対応付けの失敗は、extraction_jobs.review_reasons に extract_exception を残し、件は消さない（再送出しない）。
    マスタが空などの設定の誤りは呼び出し元へ送出する（黙って進まない）。
    """
    from app.tasks.tcg_extraction import load_extraction_context  # noqa: PLC0415  循環 import を避ける

    schema = analyzer.TCG_SCHEMA
    # 同じ投稿のやり直しが並行して走ると、判断の読み込みと書き込みが交差する。取引の最初に投稿ごとの鍵を取り、順番に走らせる
    session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": f"v102_analysis:{extraction_job_id}"})
    ctx = load_extraction_context(session, extraction_job_id)
    if ctx is None:
        raise ValueError(f"extraction_job が見つかりません: {extraction_job_id}")
    job = session.execute(
        text(f"SELECT gemini_unsure, review_reasons FROM {schema}.extraction_jobs WHERE id = :ej"), {"ej": extraction_job_id}
    ).one()
    rows = session.execute(
        text(f"""
            SELECT id, gemini_index, source_lines, raw_price, raw_quantity FROM {schema}.extraction_items
            WHERE extraction_job_id = :ej ORDER BY gemini_index NULLS LAST, created_at, id
        """),
        {"ej": extraction_job_id},
    ).fetchall()
    empty_stats = {"total": len(rows), "pid_resolved": 0, "unit_resolved": 0, "needs_review": 0}
    if not rows and REASON_RESPONSE_UNREADABLE in (job.review_reasons or "").split(REASON_SEPARATOR):
        return empty_stats  # 応答が読めなかった投稿の理由を、件が無いことの理由で上書きしない
    masters, unit_ids = load_v102_masters(session)
    try:
        if any(r.gemini_index is None for r in rows):
            raise _MappingError("gemini_index が無い件があります（v6 の件）")
        response_text = _response_from_rows(rows, job.gemini_unsure)
        decisions = load_v102_decisions(session, [str(r.id) for r in rows])
        fixed_products = _fixed_products(response_text, ctx, masters, rows, decisions)
        previous_pairs = _load_resolved_pairs(session, extraction_job_id)
        followup_masters = masters_with_followup(masters, load_followup_reference(session, extraction_job_id))
        pipeline = run_v102_pipeline(response_text, ctx, followup_masters, fixed_products=fixed_products)
        stats = _write_results(session, extraction_job_id, pipeline, rows, masters, unit_ids, decisions)
        session.commit()
    except Exception:  # noqa: BLE001
        session.rollback()
        logger.exception("[line_analysis] v102 のシステム段が失敗しました: job=%s", extraction_job_id)
        _set_job_review_reasons(session, extraction_job_id, REASON_EXTRACT_EXCEPTION)
        session.commit()
        return empty_stats
    analyzer._merge_supplier_products(session, extraction_job_id, schema, extra_pairs=previous_pairs)  # ADR-158（is_current）
    logger.info("[line_analysis] v102 job=%s stats=%s", extraction_job_id, stats)
    return stats
