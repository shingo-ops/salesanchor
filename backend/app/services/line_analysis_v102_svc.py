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
from dataclasses import replace as dataclass_replace
from datetime import date, datetime, timezone
from decimal import Decimal

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services import tcg_analyzer_svc as analyzer
from app.services.extraction_judgement_svc import build_cond_terms, order_from_pattern
from app.services.gemini_extraction_svc import _GEMINI_MODEL, _classify_error, _safe_error_message
from app.services.gemini_raw_copy_v8 import build_prompt_v8, call_gemini_raw_copy_v8
from app.services.gemini_raw_copy_v101 import (
    _NONE as _SHIP_NONE,
)
from app.services.gemini_raw_copy_v101 import (
    V101_PROMPT_NAME_RE,
    V102_RESPONSE_SCHEMA,
    extract_v101_items,
    parse_v101_response,
    parse_v102_unsure,
)
from app.services.gemini_raw_copy_v102_context_work import MATCH_STATUS_MATCHED, MATCH_STATUS_MATCHED_CONTEXT
from app.services.gemini_raw_copy_v102_followup import MATCH_STATUS_MATCHED_FOLLOWUP
from app.services.gemini_raw_copy_v102_product_first import (
    PRODUCT_KUBUN_BOOKLET,
    PRODUCT_KUBUN_BULK,
    PRODUCT_KUBUN_PROMO_PACK,
    PRODUCT_KUBUN_SINGLE,
    PRODUCT_KUBUN_SUPPLY,
    VALUE_GROUP_BOOKLET,
    VALUE_GROUP_PROMO_PACK,
    VALUE_GROUP_SINGLE,
    VALUE_GROUP_SUPPLY,
    load_product_first_masters,
    with_cond_terms,
)
from app.services.gemini_raw_copy_v102_soldout_ref import (
    MATCH_STATUS_MATCHED_SOLDOUT_REF,
    SoldItem,
    SoldoutRefPost,
    StockItem,
)
from app.services.llm_budget import record_usage_event_sync
from app.services.tcg_condition_review_svc import (  # noqa: F401  REASON_* は他モジュールが line_analysis_v102_svc から読む
    CONDITION_EFFECT_EXCLUDE,
    CONDITION_REVIEW_REASONS,
    REASON_CONDITION_MULTIPLE,
    REASON_CONDITION_UNKNOWN,
    condition_effect_sql,
)
from app.services.tcg_extraction_record_svc import RecordError
from app.services.v102_bulk_price_svc import DECISION_PIECE
from app.services.v102_bulk_price_svc import convert as convert_bulk_price
from app.services.v102_bundle_svc import KIND_DECIDED, detect_bundle, split_unit_words
from app.services.v102_buyback_unit_svc import apply_buyback_units
from app.services.v102_buyback_unit_svc import is_candidate as is_buyback_candidate
from app.services.v102_gap_lines import build_gap_detail, to_stored_detail
from app.services.v102_human_decisions_svc import (
    FIELD_V102_PRICE,
    Decisions,
    ValueOverrides,
    apply_value_overrides,
    load_v102_decisions,
    status_available_by_human,
    v102_analysis_lock_key,
)
from app.services.v102_status_context import posted_jst_date
from app.services.v102_unit_price_check_svc import REASON_UNIT_PRICE_MISMATCH, Candidate, find_mismatches

logger = logging.getLogger(__name__)

# --- 版の切り替え（定義はここだけ） ---------------------------------------------------------
ENGINE_ENV = "LINE_ANALYSIS_ENGINE"
ENGINE_V6 = "v6"
ENGINE_V102 = "v102"
V102_ENGINE_VERSION = "v102-f_ct"  # analysis_results.engine_version
V102_THINKING_LEVEL = "high"  # PO 採用 2026-10-08（試作版の試験と同じ）
V102_PROMPT_KEY = "raw_copy_v101_f_ct"  # public.extraction_prompt_config の prompt_key（既定の指示書）
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
REASON_VALUE_OUT_OF_RANGE = "value_out_of_range"  # 価格・数量が NUMERIC(14,2) に入らず None にした（便G）
REASON_ITEM_MAPPING_MISMATCH = "item_mapping_mismatch"  # この行に対応する v102 の件が無い・行番号が合わない（便G）
REASON_GEMINI_GAP_SUSPECT = "gemini_gap_suspect"  # 件の間の行を Gemini が使わず、商品が決まらなかった（段2a。段1の記録の gap_name の件）
REASON_BUNDLE_UNVERIFIED = "bundle_unverified"  # まとめ売りらしいが、まとめの数が本文で決まらない（ADR-1027。値は Gemini の読みのまま。人の「このままで良い」で外せる）
REASON_BULK_PRICE_BASIS_UNKNOWN = "bulk_price_basis_unknown"  # バルク系で、価格が1枚の値段かセットの値段か原文から決まらない（便2。配信しない）
MAPPING_MISMATCH_MATCH_STATUS = "unmapped"  # 対応が付かない行の pid_basis（V102:unmapped）
REASON_SEPARATOR = ","
# REASON_UNIT_PRICE_MISMATCH（単位と価格が相場と合わない・便UP）は v102_unit_price_check_svc が定義し、_write_results が付ける
# 人の判断で外す理由（condition_review で状態を決めたとき）
# 値は tcg_condition_review_svc の1か所（保存時の除去と同じ集合）。ここは import して使う
# 人の判断で決めた印（analysis_results の pid_basis / condition_basis）
PID_BASIS_MANUAL = "MANUAL"
CONDITION_BASIS_MANUAL = "MANUAL_CONDITION_REVIEW"
# 〆の件が、参照した在庫の行の状態を引き継いだ印（analysis_results の condition_basis）
CONDITION_BASIS_SOLDOUT_REF = "SOLDOUT_REF"
STATUS_SOLD_OUT = "Sold out"  # 〆の件の status（analysis_results.status）。完売の相手にしない

# analysis_results の列の幅・精度（migrations/20260921_110000_pipeline_tables_public.sql）
_PID_BASIS_MAX = 100
_CONDITION_BASIS_MAX = 100
_PRICE_BASIS_MAX = 100
_NUMERIC_LIMIT = Decimal(10) ** 12  # NUMERIC(14,2)
_INT4_MAX = 2**31 - 1
_FLAG_SINGLE = "FLAG_SINGLE"
# 状態が決まっていない印: canonical がこの接頭辞（FLAG_SINGLE 等）、または conditions.effect が EXCLUDE（Error。配信しない状態）
CONDITION_UNDECIDED_PREFIX = "FLAG_"
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


# masters の中で発送日（ship_ja）の書き方を持つキー。解析の部品（extract_v101_items）には渡さない
_SHIP_ENTRIES_KEY = "ship_entries"
_SHIP_DROP_KEY = "ship_drop_entries"


def load_v102_masters(session: Session) -> tuple[dict, dict]:
    """(run_v102_pipeline に渡すマスタ, 単位 canonical → 単位 id)。読み取りのみ。商品・分類・状態の単位が空なら ValueError。

    試作版 prompt_ab._load_v10_masters(product_first=True) と同じ中身。prompt_ab が捨てている単位 id の索引も返す。
    """
    all_entries = analyzer.load_condition_entries(session, include_scoped_groups=True)
    # ADR-1031：single / promo_pack 群の行は、シングル系・プロモパック系の判定だけが使う。通常の cond_entries には入れない
    cond_entries = [e for e in all_entries if e.get("value_group") not in analyzer.SCOPED_VALUE_GROUPS]
    scoped_entries = {
        group: tuple(e for e in all_entries if e.get("value_group") == group) for group in analyzer.SCOPED_VALUE_GROUPS
    }
    status_entries = analyzer.load_status_master(session)
    (_pc, _ua, unit_canonical_to_uuid, _ca, cond_canonical_to_uuid, unit_alias_to_info) = analyzer.load_lookup_maps(session)
    masters = {
        "cond_entries": cond_entries, "cond_canonical_to_uuid": cond_canonical_to_uuid,
        "unit_alias_to_info": unit_alias_to_info, "status_entries": status_entries,
        # 除外ワードの判定に使う状態の合図の語は cond_entries から一度だけ作る（新しい表・設定値は持たない）
        "product_first": dataclass_replace(
            with_cond_terms(load_product_first_masters(session), build_cond_terms(cond_entries)),
            scoped_cond_entries=scoped_entries,
        ),
        _SHIP_ENTRIES_KEY: analyzer.load_ship_master(session),
        _SHIP_DROP_KEY: analyzer.load_ship_drop_master(session),
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


def _gap_detail(fields: dict, ctx, masters: dict) -> dict | None:
    """間の行の検知の記録（段1）。件・要確認・照合の結果は読むだけで変えない。失敗しても解析は止めず None にする。"""
    try:
        return build_gap_detail(
            fields["v102_items"], ctx.raw_text.split("\n"), masters.get("product_first"),
            fields["v102_flags"].get("post_review") or [],
        )
    except Exception:  # noqa: BLE001
        logger.exception("[line_analysis] 間の行の検知の記録を作れませんでした（解析の結果には影響しません）")
        return None


def _gap_reason_element(entry: dict, item: dict) -> dict:
    return {
        "kind": REASON_GEMINI_GAP_SUSPECT, "line": item.get("price_line"),
        "lines": list(entry["gap_lines"]), "candidates": list(entry["candidates"]), "source": SOURCE_SYSTEM,
    }


def _with_gap_reasons(items: list[dict], detail: dict | None) -> list[dict]:
    """段1の記録（gap_name）の件に、要確認の理由 gemini_gap_suspect を review の最後に1つ足す（段2a）。純粋：元の件・一覧は変えない。

    detail が None なら items をそのまま返す。rejected の件・gemini_index が引けない件は変えない。失敗しても解析は止めず items をそのまま返す。
    """
    if detail is None:
        return items
    try:
        by_index = {e["gemini_index"]: e for e in detail["gap_name"] if e.get("gemini_index") is not None}
        return [
            item if "rejected" in item or item.get("gemini_index") not in by_index
            else {**item, "review": [*(item.get("review") or []), _gap_reason_element(by_index[item["gemini_index"]], item)]}
            for item in items
        ]
    except Exception:  # noqa: BLE001
        logger.exception("[line_analysis] 取りこぼし疑いの理由を足せませんでした（件はそのままにします）")
        return items


def run_v102_pipeline(
    response_text: str, ctx, masters: dict, *, extract_items: Callable[..., tuple[list[dict], dict]] = extract_v101_items,
    fixed_products: dict[int, int] | None = None,
) -> dict:
    """v102 の行に足す v102_items（F2〜F6 あり・F1 と迷う行の付け直しは廃止・価格数量は Gemini の写しを採る。便G）・v102_flags。v101 の欄は書かない。失敗しても止めない。

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
        # 発送マスタは配信用の ship_ja を作る側（_analysis_values）だけが使う。extract_items はキーワード固定なので渡さない
        extraction_masters = {k: v for k, v in masters.items() if k not in (_SHIP_ENTRIES_KEY, _SHIP_DROP_KEY)}
        extracted, flags = extract_items(
            items, ctx.raw_text, order=order, reassign=False, v102_fixes=True, review_reasons=True, gemini_trust=True,
            **extraction_masters, **fixed
        )
        if not items and errors:
            flags = {**flags, "post_review": [{"kind": "response_unreadable", "error": errors[0]["error"]}]}
        unsure = _gemini_review(response_text, ctx.raw_text, extracted)
        fields = _with_review_sources(
            {
                "v102_items": _with_gemini_review(extracted, unsure),
                "v102_flags": {**flags, "gemini_review": unsure},
            },
            unsure,
        )
        detail = _gap_detail(fields, ctx, masters)  # 理由を足す前の件から作る（段1の記録は変えない）
        return {**fields, "v102_items": _with_gap_reasons(fields["v102_items"], detail), "v102_gap_detail": detail}
    except Exception as exc:  # noqa: BLE001
        message = f"{type(exc).__name__}: {_safe_error_message(exc)}"
        return {
            "v102_items": [], "v102_items_error": message,
            "v102_flags": {
                "post_review": [{"kind": "extract_exception", "error": message, "source": SOURCE_SYSTEM}],
                "gemini_review": [],
            },
            "v102_gap_detail": None,
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
            # 費用は下の _record_usage だけが書く（二重に書かない）。思考要約は応答と同じ行に保存
            recorder.on_response(response_text, thought_summaries=result.get("thought_summaries"))
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


def _mapping_mismatch_item() -> dict:
    """対応が付かない行に書く値（値は空・未解決の状態・理由 item_mapping_mismatch）。"""
    return {"match_status": MAPPING_MISMATCH_MATCH_STATUS, "review": [{"kind": REASON_ITEM_MAPPING_MISMATCH, "source": SOURCE_SYSTEM}]}


def _items_by_position(v102_items: list[dict]) -> dict[int, dict]:
    """v102 の件を gemini_index（応答の中の位置）で引く表。位置が整数でない・重複する件は入れない（その行は対応なしになる）。"""
    seen: dict[int, dict] = {}
    duplicated: set[int] = set()
    for item in v102_items:
        index = item.get("gemini_index")
        if not _is_plain_int(index):
            continue
        if index in seen:
            duplicated.add(index)
        seen[index] = item
    return {i: it for i, it in seen.items() if i not in duplicated}


def _map_to_rows(v102_items: list[dict], rows: list) -> list[tuple[dict, object]]:
    """v102 の件を extraction_items の行に gemini_index で対応付ける（rows は gemini_index 昇順）。

    応答は rows の順に作る（_response_from_rows）ので、応答の位置 i の件は rows[i] に当たる。
    対応する件が無い行・行番号が合わない組は、その行だけ「値は空＋ item_mapping_mismatch」の件にする（他の行は通常どおり）。
    """
    by_position = _items_by_position(v102_items)
    pairs: list[tuple[dict, object]] = []
    for position, row in enumerate(rows):
        item = by_position.get(position)
        pairs.append((item if item is not None and _lines_agree(item, row) else _mapping_mismatch_item(), row))
    return pairs


def _bounded_number(value: object) -> object:
    """NUMERIC(14,2) に入らない値は None（価格が None の件は配信されない）。"""
    if value is None:
        return None
    try:
        return value if abs(Decimal(str(value))) < _NUMERIC_LIMIT else None
    except Exception:  # noqa: BLE001
        return None


# 商品の分類 → 状態の群（ADR-1031）。「PSA10」は single と promo_pack の2行あるので、状態の名前から id を引くときは群の中で引く
_SCOPED_GROUP_OF_KUBUN = {
    PRODUCT_KUBUN_SINGLE: VALUE_GROUP_SINGLE,
    PRODUCT_KUBUN_PROMO_PACK: VALUE_GROUP_PROMO_PACK,
    PRODUCT_KUBUN_BOOKLET: VALUE_GROUP_BOOKLET,
    PRODUCT_KUBUN_SUPPLY: VALUE_GROUP_SUPPLY,
}


def _scoped_condition_id(canonical: str | None, product_category: str | None, masters: dict) -> int | None:
    """シングル系・プロモパック系の件の状態 id を、その群の行の中で引く。群の行が無い・名前が無いときは None。"""
    group = _SCOPED_GROUP_OF_KUBUN.get(product_category or "")
    if not canonical or group is None:
        return None
    rows = masters["product_first"].scoped_cond_entries.get(group, ())
    return next((int(e["cond_id"]) for e in rows if e.get("canonical") == canonical), None)


def _condition_columns(
    canonical: str | None, masters: dict, product_category: str | None = None,
) -> tuple[str, int, bool]:
    """(condition_canonical, condition_id, 解けたか)。未解決（none・不明・マスタに無い）は v6 と同じ FLAG_SINGLE（CN0008）。

    product_category がシングル系・プロモパック系なら、その群の行の中で名前から id を引く（ADR-1031）。
    """
    scoped_id = _scoped_condition_id(canonical, product_category, masters)
    if scoped_id is not None:
        return canonical, scoped_id, True
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


_RESOLVED_MATCH_STATUSES = (
    MATCH_STATUS_MATCHED, MATCH_STATUS_MATCHED_CONTEXT, MATCH_STATUS_MATCHED_FOLLOWUP, MATCH_STATUS_MATCHED_SOLDOUT_REF,
)


_SHIP_SEPARATOR = " / "
_BRACKET_PAIRS = (("（", "）"), ("(", ")"), ("【", "】"), ("「", "」"), ("［", "］"), ("[", "]"))


def _balance_brackets(text_: str) -> str:
    """開きの無い閉じは消し、閉じが足りない開きには末尾に対の閉じを足す。前後の空白は除く。"""
    for opener, closer in _BRACKET_PAIRS:
        depth, kept = 0, []
        for ch in text_:
            if ch == closer and depth == 0:
                continue
            depth += (ch == opener) - (ch == closer)
            kept.append(ch)
        text_ = "".join(kept) + closer * depth
    return text_.strip()


def ship_note(ship: str | None) -> str | None:
    """発送日の文字 → 備考（note_ja）。無い・none は None。片側だけ残った括弧は直す（便PO3）。"""
    if ship is None or not ship.strip() or ship.strip() == _SHIP_NONE:
        return None
    parts = [_balance_brackets(part) for part in ship.split(_SHIP_SEPARATOR)]
    return _SHIP_SEPARATOR.join(p for p in parts if p) or None


def _analysis_values(item: dict, masters: dict, unit_ids: dict, work_ids: dict) -> dict:
    """v102 の1件 → analysis_results の列（設計 §4-4）。"""
    product_id = item.get("product_id")
    matched = product_id is not None and item.get("match_status") in _RESOLVED_MATCH_STATUSES
    unit = item.get("unit")
    unit_canonical = None if unit in (None, "none") else unit
    unit_id = unit_ids.get(unit_canonical) if unit_canonical else None
    condition = item.get("condition")
    condition_canonical, condition_id, _resolved = _condition_columns(
        None if condition in (None, "none") else condition, masters, item.get("product_category")
    )
    quantity = _bounded_number(item.get("quantity_normalized"))
    price = _bounded_number(item.get("price_normalized"))
    out_of_range = [
        REASON_VALUE_OUT_OF_RANGE
        for raw, bounded in ((item.get("quantity_normalized"), quantity), (item.get("price_normalized"), price))
        if raw is not None and bounded is None
    ]
    ship_ja, ship_en = analyzer.build_ship_labels(
        ship_note(item.get("ship")), masters[_SHIP_ENTRIES_KEY], masters.get(_SHIP_DROP_KEY, ())
    )
    reasons = _join_unique([*_kinds(item.get("review") or []), *_kinds(item.get("gemini_review") or []), *out_of_range])
    return {
        "product_id": product_id if matched else None, "pid_resolved": bool(matched),
        "pid_basis": f"V102:{item.get('match_status')}"[:_PID_BASIS_MAX],
        "unit_id": int(unit_id) if unit_id is not None else None, "unit_canonical": unit_canonical,
        "unit_resolved": unit_id is not None,
        "condition_id": condition_id, "condition_canonical": condition_canonical,
        "condition_basis": str(item.get("condition_basis") or "")[:_CONDITION_BASIS_MAX],
        "quantity_normalized": quantity,
        "price_normalized": price,
        "note_ja": None, "ship_ja": ship_ja, "ship_en": ship_en,
        "status": item.get("status"), "exclusion": item.get("status_effect"),
        "needs_review": reasons is not None, "review_reasons": reasons,
        "work_id": work_ids.get(product_id) if matched else None,
        "price_basis": f"V102:{item['price_basis']}"[:_PRICE_BASIS_MAX] if item.get("price_basis") else None,
        "bundle_size": None,  # まとめ売りと決まった行だけ _apply_bundle が入れる（ADR-1027）
    }


_UPSERT_SQL = """
    INSERT INTO {schema}.analysis_results (
        id, extraction_item_id, product_id, pid_resolved, pid_basis, unit_id, unit_canonical, unit_resolved,
        condition_id, condition_canonical, condition_basis, quantity_normalized, price_normalized, note_ja,
        status, exclusion, needs_review, review_reasons, engine_version, computed_at, updated_at, work_id,
        price_basis, ship_ja, ship_en, bundle_size
    ) VALUES (
        :id, :extraction_item_id, :product_id, :pid_resolved, :pid_basis, :unit_id, :unit_canonical, :unit_resolved,
        :condition_id, :condition_canonical, :condition_basis, :quantity_normalized, :price_normalized, :note_ja,
        :status, :exclusion, :needs_review, :review_reasons, :engine_version, :computed_at, :updated_at, :work_id,
        :price_basis, :ship_ja, :ship_en, :bundle_size
    )
    ON CONFLICT (extraction_item_id) DO UPDATE SET
        product_id = EXCLUDED.product_id, pid_resolved = EXCLUDED.pid_resolved, pid_basis = EXCLUDED.pid_basis,
        unit_id = EXCLUDED.unit_id, unit_canonical = EXCLUDED.unit_canonical, unit_resolved = EXCLUDED.unit_resolved,
        condition_id = EXCLUDED.condition_id, condition_canonical = EXCLUDED.condition_canonical,
        condition_basis = EXCLUDED.condition_basis, quantity_normalized = EXCLUDED.quantity_normalized,
        price_normalized = EXCLUDED.price_normalized, note_ja = EXCLUDED.note_ja, status = EXCLUDED.status,
        exclusion = EXCLUDED.exclusion, needs_review = EXCLUDED.needs_review, review_reasons = EXCLUDED.review_reasons,
        engine_version = EXCLUDED.engine_version, computed_at = EXCLUDED.computed_at, updated_at = EXCLUDED.updated_at,
        work_id = EXCLUDED.work_id, price_basis = EXCLUDED.price_basis,
        ship_ja = EXCLUDED.ship_ja, ship_en = EXCLUDED.ship_en, bundle_size = EXCLUDED.bundle_size
    RETURNING id
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


def _set_job_review_detail(session: Session, extraction_job_id: str, detail: dict | None) -> None:
    """extraction_jobs.system_review_detail を上書きする（解析のたびに。detail が None なら NULL）。"""
    session.execute(
        text(f"UPDATE {analyzer.TCG_SCHEMA}.extraction_jobs SET system_review_detail = CAST(:d AS jsonb) WHERE id = :ej"),
        {"d": json.dumps(detail, ensure_ascii=False) if detail is not None else None, "ej": extraction_job_id},
    )


def _clear_job_review_detail(session: Session, extraction_job_id: str) -> None:
    """例外の経路で古い明細を NULL にする。SAVEPOINT の中で行い、失敗しても警告だけ残して review_reasons の更新を巻き込まない。"""
    try:
        with session.begin_nested():
            _set_job_review_detail(session, extraction_job_id, None)
    except Exception:  # noqa: BLE001
        logger.warning("[line_analysis] system_review_detail を NULL にできませんでした: job=%s", extraction_job_id, exc_info=True)


def _stored_review_detail(pipeline: dict, pairs: list[tuple[dict, object]]) -> dict | None:
    """書く値（版 1）。件は _map_to_rows が付けた対応（gemini_index → 行の id）で extraction_item_id に置き換える。"""
    detail = pipeline.get("v102_gap_detail")
    if detail is None:
        return None
    item_ids = {item["gemini_index"]: row.id for item, row in pairs if _is_plain_int(item.get("gemini_index"))}
    return to_stored_detail(detail, item_ids)


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


def _load_excluded_condition_ids(session: Session, condition_ids: list[int]) -> frozenset[int]:
    """effect='EXCLUDE'（配信しない状態。Error）の状態 id。"""
    if not condition_ids:
        return frozenset()
    rows = session.execute(
        text(f"SELECT id FROM public.conditions WHERE id = ANY(:ids) AND {condition_effect_sql('conditions')} = :effect"),
        {"ids": sorted(set(condition_ids)), "effect": CONDITION_EFFECT_EXCLUDE},
    ).fetchall()
    return frozenset(int(r[0]) for r in rows)


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


def _has_human_judgement(decision: Decisions | None) -> bool:
    """商品または状態の人の判断があるか（確認済みの印だけの判断は含まない）。"""
    return decision is not None and (decision.product_id is not None or decision.condition_id is not None)


# 単位不明の理由（gemini_raw_copy_v101._REVIEW_UNIT_UNKNOWN と同じ値。前例 v102_buyback_unit_svc.py:42）
REASON_UNIT_UNKNOWN = "unit_unknown"


def _with_target_unit(values: dict, targets: list[dict]) -> dict:
    """〆の件に単位が無く、完売の相手の単位が1種類に決まるとき、その単位を写して unit_unknown を外す（元の values は変えない。design.md §13-3 C）。"""
    units = {(t.get("unit_id"), t.get("unit_canonical") or "") for t in targets}
    if values["unit_id"] is not None or values["unit_canonical"] is not None or len(units) != 1:
        return values
    (unit_id, unit_canonical), = units
    if unit_id is None or not unit_canonical:
        return values
    remaining = [r for r in _split_reasons(values["review_reasons"]) if r != REASON_UNIT_UNKNOWN]
    return {
        **values, "unit_id": int(unit_id), "unit_canonical": unit_canonical, "unit_resolved": True,
        "review_reasons": REASON_SEPARATOR.join(remaining) if remaining else None, "needs_review": bool(remaining),
    }


def _apply_soldout_targets(
    values: dict, item: dict, decision: Decisions | None, canonicals: dict[int, str],
    excluded_ids: frozenset[int] = frozenset(),
) -> dict:
    """〆の件の状態を、先頭の完売の相手の状態にする（元の values は変えない）。単位が無い件は、相手の単位が1種類なら写す（§13-3 C）。

    相手が無い件・人の判断（商品または状態）がある件は上書きしない（何も外さない）。状態の名前が引けない件は状態の理由を外さない（単位の写しは先に済む）。
    上書きしたときは、人の状態判断（_apply_decisions）と同じ理由 CONDITION_REVIEW_REASONS を外し、空になれば要確認を外す。
    """
    targets = item.get("soldout_targets") or []
    if not targets or _has_human_judgement(decision):
        return values
    values = _with_target_unit(values, targets)
    condition_id = targets[0]["condition_id"]
    canonical = canonicals.get(condition_id)
    if canonical is None:
        return values
    basis = item.get("soldout_target_basis") or CONDITION_BASIS_SOLDOUT_REF
    overwritten = {**values, "condition_id": condition_id, "condition_canonical": canonical, "condition_basis": basis}
    if canonical.startswith(CONDITION_UNDECIDED_PREFIX) or condition_id in excluded_ids:
        return overwritten  # 決まっていない状態を引き継いだだけなので、状態の理由も needs_review も変えない（単位の写しの分は済んでいる）
    remaining = [r for r in _split_reasons(values["review_reasons"]) if r not in CONDITION_REVIEW_REASONS]
    return {**overwritten, "review_reasons": REASON_SEPARATOR.join(remaining) if remaining else None, "needs_review": bool(remaining)}


def _extra_targets(values: dict, item: dict, decision: Decisions | None, status_entries: list[dict] | None = None) -> list[dict]:
    """analysis_soldout_extra_targets に書く相手：書いた行の (商品, 状態) と違う相手。

    相手が無い件・人の判断がある件・人が販売状況を在庫あり側に直した件は空（ほかの商品の is_current を落とさない）。
    """
    targets = item.get("soldout_targets") or []
    if not targets or _has_human_judgement(decision) or status_available_by_human(decision, status_entries or []):
        return []
    written = (values["product_id"], values["condition_id"])
    return [t for t in targets if (t["product_id"], t["condition_id"]) != written]


_DELETE_EXTRA_TARGETS_SQL = """
    DELETE FROM {schema}.analysis_soldout_extra_targets WHERE analysis_result_id IN (
        SELECT ar.id FROM {schema}.analysis_results ar
        JOIN {schema}.extraction_items ei ON ei.id = ar.extraction_item_id
        WHERE ei.extraction_job_id = :ej
    )
"""
_INSERT_EXTRA_TARGET_SQL = """
    INSERT INTO {schema}.analysis_soldout_extra_targets (analysis_result_id, product_id, condition_id, ref_message_id, ref_line)
    VALUES (:analysis_result_id, :product_id, :condition_id, :ref_message_id, :ref_line)
"""


def _soldout_condition_ids(pairs: list[tuple[dict, object]]) -> list[int]:
    return [it["soldout_targets"][0]["condition_id"] for it, _ in pairs if it.get("soldout_targets")]


def _write_extra_targets(session: Session, result_id: str, extras: list[dict]) -> None:
    for target in extras:
        session.execute(
            text(_INSERT_EXTRA_TARGET_SQL.format(schema=analyzer.TCG_SCHEMA)),
            {"analysis_result_id": result_id, "product_id": target["product_id"], "condition_id": target["condition_id"],
             "ref_message_id": target["ref_message_id"], "ref_line": target["ref_line"]},
        )


def _buyback_units(
    session: Session, pairs: list, base_values: list[dict], unit_ids: dict, extraction_job_id: str, decisions: dict[str, Decisions],
) -> list[dict]:
    """単位も状態も語が無い件を、買取価格との比で Sealed box / Case に決める（便BB）。失敗したらこの投稿では決めない。"""
    if not any(is_buyback_candidate(item, values) for (item, _row), values in zip(pairs, base_values)):
        return base_values  # 対象が無ければ DB も SAVEPOINT も使わない
    try:
        with session.begin_nested():  # SAVEPOINT。補助 SQL の失敗で解析の保存全体の取引を壊さない
            human_condition = frozenset(  # 状態の判断がある件と、単位か価格を人が直した件は、買取価格では決めない
                i for i, (_item, row) in enumerate(pairs)
                if (d := decisions.get(str(row.id))) is not None
                and (d.condition_id is not None or d.values.unit is not None or d.values.price is not None)
            )
            return apply_buyback_units(session, [item for item, _row in pairs], base_values, unit_ids, human_condition)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[buyback_unit] 買取価格による単位・状態の判定に失敗したので、この投稿では判定をしません: job=%s error=%r", extraction_job_id, exc)
        return base_values


def _unit_price_mismatches(session: Session, extraction_job_id: str, base_values: list[dict]) -> frozenset[int]:
    """単位と価格が相場と合わない件の位置（便UP）。商品・単位・価格が揃った件だけを相場と比べる。"""
    candidates = [
        Candidate(key=index, product_id=int(v["product_id"]), unit=str(v["unit_canonical"]), price=Decimal(str(v["price_normalized"])))
        for index, v in enumerate(base_values)
        if v["pid_resolved"] and v["product_id"] is not None and v["unit_canonical"] and v["price_normalized"] is not None
        and v.get("bundle_size") is None  # まとめの値段と1個の値段を混ぜない（ADR-1027）
    ]
    if not candidates:
        return frozenset()
    try:
        with session.begin_nested():  # SAVEPOINT。補助 SQL の失敗で解析の保存全体の取引を壊さない
            source_message_id = session.execute(
                text(f"SELECT source_message_id::text FROM {analyzer.TCG_SCHEMA}.extraction_jobs WHERE id = :ej"), {"ej": extraction_job_id}
            ).scalar_one()
            return find_mismatches(session, analyzer.TCG_SCHEMA, candidates, source_message_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[unit_price_check] 単位と価格の確認に失敗したので、この投稿では確認をしません: job=%s error=%r", extraction_job_id, exc)
        return frozenset()


_PIECE_UNIT = "Piece"
_PRICE_BASIS_BULK_PIECE = "V102:bulk:piece"


def _source_block(raw_text: str | None, row: object) -> str:
    """件の原文ブロック。source_lines（無ければ line_start〜line_end）の行（1始まり）を改行でつなぐ。得られなければ空。"""
    if not raw_text:
        return ""
    lines = raw_text.split("\n")
    numbers = _stock_lines(getattr(row, "source_lines", None), getattr(row, "line_start", None), getattr(row, "line_end", None))
    return "\n".join(lines[n - 1] for n in sorted(numbers) if 1 <= n <= len(lines))


def _as_float(value: object) -> float | None:
    return float(value) if value is not None else None  # type: ignore[arg-type]


def _bulk_review(values: dict) -> dict:
    reasons = _join_unique([*_split_reasons(values["review_reasons"]), REASON_BULK_PRICE_BASIS_UNKNOWN])
    return {**values, "review_reasons": reasons, "needs_review": True}


def _apply_bundle(values: dict, block: str, unit_words: dict[str, str], set_words: frozenset[str], unit_ids: dict) -> dict:
    """まとめ売り（N単位セット）を読む（ADR-1027。規則は v102_bundle_svc）。全ての行に当てる。

    決まった: bundle_size=N、単位を中身の単位にそろえる。値段・数量は Gemini の読みのまま（割らない・掛けない）。
    決まらない: 値は変えず、理由 bundle_unverified で要確認にする。当たりなしは values をそのまま返す。
    """
    result = detect_bundle(block, unit_words, set_words, values["price_normalized"], values["quantity_normalized"])
    if result is None:
        return values
    unit_id = unit_ids.get(result.unit) if result.kind == KIND_DECIDED and result.unit else None
    if result.kind != KIND_DECIDED or unit_id is None:  # 中身の単位の id が引けないときも決めない（id を作らない）
        reasons = _join_unique([*_split_reasons(values["review_reasons"]), REASON_BUNDLE_UNVERIFIED])
        return {**values, "review_reasons": reasons, "needs_review": True}
    return {**values, "bundle_size": result.n, "unit_canonical": result.unit, "unit_id": int(unit_id), "unit_resolved": True}


def _apply_bulk_price(values: dict, item: dict, block: str, unit_ids: dict) -> dict:
    """バルク系の価格を1枚の値段にそろえる（便2。規則は v102_bulk_price_svc）。バルク系以外・商品が決まらない行・まとめ売りと決まった行は values をそのまま返す。

    piece は価格・数量そのまま（単位 Piece）、決まらない行と set は理由を足して要確認にする（set の換算は ADR-1027 で置き換え）。
    """
    if item.get("product_category") != PRODUCT_KUBUN_BULK or not values["pid_resolved"] or values.get("bundle_size") is not None:
        return values
    result = convert_bulk_price(block, _as_float(values["price_normalized"]), _as_float(values["quantity_normalized"]))
    piece_id = unit_ids.get(_PIECE_UNIT)
    if result.decision != DECISION_PIECE or piece_id is None:
        return _bulk_review(values)  # set（R' で決まらなかったセットの印は割って保存しない）と Piece の id が引けないときも決めない
    unit = {"unit_canonical": _PIECE_UNIT, "unit_id": int(piece_id), "unit_resolved": True}
    return {**values, **unit, "price_basis": _PRICE_BASIS_BULK_PIECE}


def _without_bulk_reason_if_human_priced(values: dict, decision: Decisions | None) -> dict:
    """人が価格か数量を直した行は、価格の決まらない理由を外す（人が決めたため。ほかの理由は残す）。"""
    if decision is None or (decision.values.price is None and decision.values.quantity is None):
        return values
    reasons = _split_reasons(values["review_reasons"])
    if REASON_BULK_PRICE_BASIS_UNKNOWN not in reasons:
        return values
    kept = _join_unique([r for r in reasons if r != REASON_BULK_PRICE_BASIS_UNKNOWN])
    return {**values, "review_reasons": kept, "needs_review": kept is not None}


def _with_unit_price_reason(values: dict, is_mismatch: bool) -> dict:
    """理由 unit_price_mismatch を末尾に足す（元の values は変えない）。人の「このままで良い」は _apply_decisions が外す。"""
    if not is_mismatch:
        return values
    reasons = _split_reasons(values["review_reasons"])
    return {**values, "review_reasons": REASON_SEPARATOR.join([*reasons, REASON_UNIT_PRICE_MISMATCH]), "needs_review": True}


def _has_raw_value(raw) -> bool:
    """仕入元が値を書いているか（空・none は書いていない）。"""
    return raw is not None and str(raw).strip().lower() not in ("", "none")


def _sell_out_stock_closed_in_the_same_post(
    pairs: list, base_values: list[dict], decisions: dict[str, Decisions], unit_ids: dict, status_entries: list[dict],
) -> list[dict]:
    """規則13（docs/handoff/v102-shime-same-post-stock/design.md §3）：同じ投稿の〆が範囲に含む、同じ商品・状態の在庫の件を Sold out にする。

    〆は自分の価格・数量が無く、引き継ぎ先も無いものだけ。人が判断した件は〆にも在庫にも使わない。元の base_values は変えない。
    """
    closers = [
        (values["product_id"], values["condition_id"], getattr(row, "line_start", None), getattr(row, "line_end", None))
        for values, (item, row) in zip(base_values, pairs)
        if values["status"] == STATUS_SOLD_OUT and values["exclusion"] == "excluded"
        and not _has_raw_value(getattr(row, "raw_price", None)) and not _has_raw_value(getattr(row, "raw_quantity", None))
        and not item.get("soldout_targets")
        and not _has_human_judgement(decisions.get(str(row.id)))
        and None not in (values["product_id"], values["condition_id"], getattr(row, "line_start", None), getattr(row, "line_end", None))
    ]
    if not closers:
        return base_values
    out = []
    for values, (_item, row) in zip(base_values, pairs):
        decision = decisions.get(str(row.id))
        start_line, end_line = getattr(row, "line_start", None), getattr(row, "line_end", None)
        closed = (
            values["status"] != STATUS_SOLD_OUT and values["exclusion"] is None
            and (decision is None or decision.values.status is None)
            and not _has_human_judgement(decision)
            and start_line is not None and end_line is not None
            and any(
                pid == values["product_id"] and cid == values["condition_id"] and start <= start_line and end_line <= end
                for pid, cid, start, end in closers
            )
        )
        out.append(apply_value_overrides(values, ValueOverrides(status=STATUS_SOLD_OUT), unit_ids, status_entries) if closed else values)
    return out


def _write_results(
    session: Session, extraction_job_id: str, pipeline: dict, rows: list, masters: dict, unit_ids: dict,
    decisions: dict[str, Decisions] | None = None, raw_text: str | None = None,
) -> dict:
    decisions = decisions or {}
    v102_items = pipeline["v102_items"]
    if pipeline.get("v102_items_error") is not None:
        raise _MappingError(pipeline["v102_items_error"])
    pairs = _map_to_rows(v102_items, rows)
    matched_ids = [it["product_id"] for it, _ in pairs if it.get("product_id") is not None]
    work_ids = _load_product_work_ids(session, sorted(set(matched_ids)))
    condition_ids = [d.condition_id for d in decisions.values() if d.condition_id is not None]
    target_ids = [*condition_ids, *_soldout_condition_ids(pairs)]
    canonicals = _load_condition_canonicals(session, target_ids)
    excluded_ids = _load_excluded_condition_ids(session, target_ids)
    now = datetime.now(timezone.utc)
    stats = {"total": len(rows), "pid_resolved": 0, "unit_resolved": 0, "needs_review": 0}
    session.execute(text(_DELETE_EXTRA_TARGETS_SQL.format(schema=analyzer.TCG_SCHEMA)), {"ej": extraction_job_id})  # やり直しで古い相手を消す
    base_values = [_analysis_values(item, masters, unit_ids, work_ids) for item, _row in pairs]
    unit_words, set_words = split_unit_words({a: info[0] for a, info in (masters.get("unit_alias_to_info") or {}).items()})
    blocks = [_source_block(raw_text, row) for _item, row in pairs]  # 原文ブロックは投稿の raw_text から。追加の問い合わせなし
    base_values = [_apply_bundle(values, block, unit_words, set_words, unit_ids) for values, block in zip(base_values, blocks)]  # ADR-1027：全ての行
    base_values = [  # 便2：バルク系の価格を1枚の値段に（まとめ売りと決まった行は通らない）
        _apply_bulk_price(values, item, block if item.get("product_category") == PRODUCT_KUBUN_BULK else "", unit_ids)
        for values, (item, _row), block in zip(base_values, pairs, blocks)
    ]
    status_entries = masters["status_entries"]  # load_status_master を呼び直さない（例外時に rollback するため）
    base_values = [  # 人が直した値（数量・単価・単位・メモ・販売状況）。買取単位・単位と価格の確認は、この人の値で判定する
        _without_bulk_reason_if_human_priced(apply_value_overrides(values, d.values, unit_ids, status_entries), d)
        if (d := decisions.get(str(row.id))) is not None else values
        for values, (_item, row) in zip(base_values, pairs)
    ]
    base_values = _buyback_units(session, pairs, base_values, unit_ids, extraction_job_id, decisions)  # 便BB。便UP の確認はこの後の単位・状態で走る
    base_values = _sell_out_stock_closed_in_the_same_post(pairs, base_values, decisions, unit_ids, status_entries)  # 規則13
    mismatches = _unit_price_mismatches(session, extraction_job_id, base_values)
    for index, (item, row) in enumerate(pairs):
        decision = decisions.get(str(row.id))
        values = _apply_soldout_targets(
            _apply_decisions(_with_unit_price_reason(base_values[index], index in mismatches), item, decision, canonicals),
            item, decision, canonicals, excluded_ids,
        )
        values = _inherit_price(session, extraction_job_id, row, values, item.get("product_category") == PRODUCT_KUBUN_BULK)
        result_id = session.execute(
            text(_UPSERT_SQL.format(schema=analyzer.TCG_SCHEMA)),
            {**values, "id": str(uuid.uuid4()), "extraction_item_id": str(row.id), "engine_version": V102_ENGINE_VERSION,
             "computed_at": now, "updated_at": now},
        ).scalar_one()
        _write_extra_targets(session, result_id, _extra_targets(values, item, decision, status_entries))
        stats["pid_resolved"] += int(values["pid_resolved"])
        stats["unit_resolved"] += int(values["unit_resolved"])
        stats["needs_review"] += int(values["needs_review"])
    _set_job_review_reasons(session, extraction_job_id, _job_review_reasons(pipeline["v102_flags"]))
    _set_job_review_detail(session, extraction_job_id, _stored_review_detail(pipeline, pairs))
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
    """この投稿の今の (product_id, condition_id) の組（〆の完売の相手の組を含む）。書き直す前に読み、is_current の付け直しに渡す。"""
    rows = session.execute(
        text(f"""
            SELECT ar.product_id, ar.condition_id
            FROM {analyzer.TCG_SCHEMA}.analysis_results ar
            JOIN {analyzer.TCG_SCHEMA}.extraction_items ei ON ei.id = ar.extraction_item_id
            WHERE ei.extraction_job_id = :ej AND ar.pid_resolved = TRUE AND ar.product_id IS NOT NULL
            UNION
            SELECT et.product_id, et.condition_id
            FROM {analyzer.TCG_SCHEMA}.analysis_soldout_extra_targets et
            JOIN {analyzer.TCG_SCHEMA}.analysis_results ar ON ar.id = et.analysis_result_id
            JOIN {analyzer.TCG_SCHEMA}.extraction_items ei ON ei.id = ar.extraction_item_id
            WHERE ei.extraction_job_id = :ej
        """),
        {"ej": extraction_job_id},
    ).fetchall()
    return [(int(r[0]), int(r[1])) for r in rows]


def _load_current_pairs(session: Session, extraction_job_id: str) -> list[tuple[int, int]]:
    """ADR-1032: 書き直す前に、この投稿の行で is_current=TRUE だった (product_id, condition_id) の組。復活止めの「前から現行」の控え。"""
    rows = session.execute(
        text(f"""
            SELECT DISTINCT ar.product_id, ar.condition_id
            FROM {analyzer.TCG_SCHEMA}.analysis_results ar
            JOIN {analyzer.TCG_SCHEMA}.extraction_items ei ON ei.id = ar.extraction_item_id
            WHERE ei.extraction_job_id = :ej AND ar.pid_resolved = TRUE AND ar.product_id IS NOT NULL
              AND ar.is_current = TRUE
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


SOLDOUT_REF_MAX_GAP_SECONDS = 172800  # 〆の件が参照する過去の投稿との時刻の差の上限＝48時間（design v102-shime-inventory-ref §2-2）

_SOLDOUT_REF_POSTS_SQL = """
    SELECT id, line_posted_at, raw_text
    FROM {schema}.source_messages
    WHERE supplier_channel_id = :channel AND line_posted_at < :posted_at
      AND line_posted_at >= :posted_at - make_interval(secs => :gap)
    ORDER BY line_posted_at DESC, id DESC
"""


def load_soldout_ref_posts(session: Session, extraction_job_id: str) -> tuple[SoldoutRefPost, ...]:
    """〆の件が参照する過去の投稿（新しい順）。同じ仕入元の、今の投稿より前で SOLDOUT_REF_MAX_GAP_SECONDS 以内（is_active は問わない）。

    今の投稿の仕入元・時刻が無いとき・該当が無いときは空。読み取りのみ。run_v102_analysis と prompt_ab_recompute が共通で呼ぶ。
    """
    schema = analyzer.TCG_SCHEMA
    current = session.execute(text(_FOLLOWUP_CURRENT_SQL.format(schema=schema)), {"ej": extraction_job_id}).first()
    if current is None or current.supplier_channel_id is None or current.line_posted_at is None:
        return ()
    rows = session.execute(
        text(_SOLDOUT_REF_POSTS_SQL.format(schema=schema)),
        {"channel": current.supplier_channel_id, "posted_at": current.line_posted_at, "gap": SOLDOUT_REF_MAX_GAP_SECONDS},
    ).fetchall()
    ids = [str(r.id) for r in rows]
    stock, sold = _load_stock_items(session, ids), _load_sold_items(session, ids)
    return tuple(
        SoldoutRefPost(str(r.id), r.line_posted_at, r.raw_text or "", stock.get(str(r.id), ()), sold.get(str(r.id), ())) for r in rows
    )


PRICE_BASIS_INHERIT_PREFIX = "INHERIT:"
INHERIT_PRICE_MAX_GAP_SECONDS = SOLDOUT_REF_MAX_GAP_SECONDS  # 48時間。〆の参照と同じ測り方

_INHERIT_PRICE_SQL = """
    SELECT ar.id, ar.price_normalized
    FROM {schema}.analysis_results ar
    JOIN {schema}.extraction_items ei ON ei.id = ar.extraction_item_id
    JOIN {schema}.extraction_jobs ej ON ej.id = ei.extraction_job_id
    JOIN {schema}.source_messages sm ON sm.id = ej.source_message_id
    WHERE sm.supplier_channel_id = :channel
      AND ar.product_id = :product_id AND ar.condition_id = :condition_id
      AND ar.price_normalized IS NOT NULL
      AND ar.bundle_size IS NULL
      AND ar.status IS DISTINCT FROM :sold_out
      AND (ar.price_basis IS NULL OR ar.price_basis NOT LIKE :inherit_like)
      AND sm.line_posted_at < :posted_at
      AND sm.line_posted_at >= :posted_at - make_interval(secs => :gap)
      AND ej.id = (SELECT j2.id FROM {schema}.extraction_jobs j2 WHERE j2.source_message_id = ej.source_message_id
                   ORDER BY j2.created_at DESC, j2.id DESC LIMIT 1)
    ORDER BY sm.line_posted_at DESC, ei.line_start DESC NULLS LAST, ar.id DESC
    LIMIT 1
"""
_PRICE_CORRECTION_SQL = """
    SELECT human_value FROM {schema}.item_corrections
    WHERE extraction_item_id::text = :item_id AND field_name = :field
    ORDER BY corrected_at DESC, id DESC LIMIT 1
"""


def _inherit_price(session: Session, extraction_job_id: str, row, values: dict, is_bulk: bool = False) -> dict:
    """価格なし・数ありの件に、同じ仕入元・同じ商品×状態の前の価格（48時間以内）を引き継ぐ。失敗したら引き継がない。

    バルク系は引き継がない（別サイズのセット価格が混ざる。便2）。
    """
    if (
        is_bulk
        or values.get("bundle_size") is not None  # まとめ売りの行には引き継がない（ADR-1027）
        or values["price_normalized"] is not None
        or values["quantity_normalized"] is None
        or values["product_id"] is None
        or not values["pid_resolved"]
        or values["condition_id"] is None
        or values["status"] == STATUS_SOLD_OUT
    ):
        return values
    if _has_raw_value(getattr(row, "raw_price", None)):
        return values  # 仕入元が価格を書いている（読めなかっただけ）。古い価格で隠さない
    schema = analyzer.TCG_SCHEMA
    try:
        with session.begin_nested():  # SAVEPOINT。補助 SQL の失敗で解析の保存全体の取引を壊さない
            correction = session.execute(
                text(_PRICE_CORRECTION_SQL.format(schema=schema)), {"item_id": str(row.id), "field": FIELD_V102_PRICE}
            ).first()
            if correction is not None and (correction.human_value or "") == "":
                return values  # 人が価格を消した
            current = session.execute(text(_FOLLOWUP_CURRENT_SQL.format(schema=schema)), {"ej": extraction_job_id}).first()
            if current is None or current.supplier_channel_id is None or current.line_posted_at is None:
                return values
            src = session.execute(
                text(_INHERIT_PRICE_SQL.format(schema=schema)),
                {
                    "channel": current.supplier_channel_id, "product_id": values["product_id"], "condition_id": values["condition_id"],
                    "sold_out": STATUS_SOLD_OUT, "inherit_like": PRICE_BASIS_INHERIT_PREFIX + "%",
                    "posted_at": current.line_posted_at, "gap": INHERIT_PRICE_MAX_GAP_SECONDS,
                },
            ).first()
            if src is None:
                return values
            return {
                **values, "price_normalized": src.price_normalized,
                "price_basis": f"{PRICE_BASIS_INHERIT_PREFIX}{src.id}"[:_PRICE_BASIS_MAX],
            }
    except Exception as exc:  # noqa: BLE001
        logger.warning("[inherit_price] 前の価格の引き継ぎに失敗したので、この件は価格なしのまま保存します: job=%s error=%r", extraction_job_id, exc)
        return values


_STOCK_ITEMS_SQL = """
    SELECT ej.source_message_id, ei.source_lines, ei.line_start, ei.line_end, ar.product_id, ar.condition_id,
           COALESCE(ar.condition_canonical, '') AS condition_canonical,
           ar.unit_id, COALESCE(ar.unit_canonical, '') AS unit_canonical
    FROM {schema}.extraction_jobs ej
    JOIN {schema}.extraction_items ei ON ei.extraction_job_id = ej.id
    JOIN {schema}.analysis_results ar ON ar.extraction_item_id = ei.id
    WHERE ej.source_message_id = ANY(CAST(:ids AS uuid[]))
      AND ej.id = (SELECT j2.id FROM {schema}.extraction_jobs j2 WHERE j2.source_message_id = ej.source_message_id
                   ORDER BY j2.created_at DESC, j2.id DESC LIMIT 1)
      AND ar.pid_resolved = TRUE AND ar.product_id IS NOT NULL AND ar.condition_id IS NOT NULL
      AND ar.status IS DISTINCT FROM :sold_out
    ORDER BY ej.source_message_id, ei.line_start NULLS LAST, ei.gemini_index NULLS LAST, ei.id
"""


_SOLD_ITEMS_SQL = """
    SELECT ej.source_message_id, ar.product_id, COALESCE(ar.condition_canonical, '') AS condition_canonical
    FROM {schema}.extraction_jobs ej
    JOIN {schema}.extraction_items ei ON ei.extraction_job_id = ej.id
    JOIN {schema}.analysis_results ar ON ar.extraction_item_id = ei.id
    WHERE ej.source_message_id = ANY(CAST(:ids AS uuid[]))
      AND ej.id = (SELECT j2.id FROM {schema}.extraction_jobs j2 WHERE j2.source_message_id = ej.source_message_id
                   ORDER BY j2.created_at DESC, j2.id DESC LIMIT 1)
      AND ar.pid_resolved = TRUE AND ar.product_id IS NOT NULL AND ar.condition_id IS NOT NULL
      AND ar.status = :sold_out
    ORDER BY ej.source_message_id, ei.line_start NULLS LAST, ei.gemini_index NULLS LAST, ei.id
"""


def _stock_lines(source_lines: list[int] | None, line_start: int | None, line_end: int | None) -> frozenset[int]:
    """件の行番号：source_lines があればその集合、無ければ line_start〜line_end（どちらかが NULL なら空）。"""
    if source_lines:
        return frozenset(int(n) for n in source_lines)
    if line_start is None or line_end is None:
        return frozenset()
    return frozenset(range(int(line_start), int(line_end) + 1))


def _load_stock_items(session: Session, message_ids: list[str]) -> dict[str, tuple[StockItem, ...]]:
    """規則11：参照する投稿ごとの、その投稿の最新の job の保存済みの解析結果（商品が決まり、'Sold out' でない件）。読み取りのみ。"""
    if not message_ids:
        return {}
    rows = session.execute(
        text(_STOCK_ITEMS_SQL.format(schema=analyzer.TCG_SCHEMA)), {"ids": message_ids, "sold_out": STATUS_SOLD_OUT}
    ).fetchall()
    found: dict[str, list[StockItem]] = {}
    for r in rows:
        found.setdefault(str(r.source_message_id), []).append(
            StockItem(
                _stock_lines(r.source_lines, r.line_start, r.line_end), int(r.product_id), int(r.condition_id),
                str(r.condition_canonical or ""), int(r.unit_id) if r.unit_id is not None else None, str(r.unit_canonical or ""),
            )
        )
    return {k: tuple(v) for k, v in found.items()}


def _load_sold_items(session: Session, message_ids: list[str]) -> dict[str, tuple[SoldItem, ...]]:
    """規則12：参照する投稿ごとの、その投稿の最新の job の保存済みの解析結果のうち 'Sold out' で商品と状態が決まった件。読み取りのみ。"""
    if not message_ids:
        return {}
    rows = session.execute(
        text(_SOLD_ITEMS_SQL.format(schema=analyzer.TCG_SCHEMA)), {"ids": message_ids, "sold_out": STATUS_SOLD_OUT}
    ).fetchall()
    found: dict[str, list[SoldItem]] = {}
    for r in rows:
        found.setdefault(str(r.source_message_id), []).append(SoldItem(int(r.product_id), str(r.condition_canonical or "")))
    return {k: tuple(v) for k, v in found.items()}


def masters_with_followup(
    masters: dict, followup_ref: tuple[str, str] | None, soldout_posts: tuple[SoldoutRefPost, ...] = (),
    posted_date: date | None = None,
) -> dict:
    """マスタに直前の投稿の参照・〆の件が参照する過去の投稿・投稿日（便PO）を足した新しい辞書（run_v102_pipeline が extract_v101_items にそのまま渡す）。無ければ元のまま。"""
    extra = {
        **({"followup_ref": followup_ref} if followup_ref is not None else {}),
        **({"soldout_posts": soldout_posts} if soldout_posts else {}),
    }
    base = masters
    if posted_date is not None and masters.get("product_first") is not None:
        base = {**masters, "product_first": dataclass_replace(masters["product_first"], posted_date=posted_date)}
    return {**base, **extra} if extra else base


_POSTED_AT_SQL = """
    SELECT sm.line_posted_at
    FROM {schema}.extraction_jobs ej JOIN {schema}.source_messages sm ON sm.id = ej.source_message_id
    WHERE ej.id = :ej
"""


def load_posted_date(session: Session, extraction_job_id: str) -> date | None:
    """投稿日（source_messages.line_posted_at の JST の日付）。投稿・時刻が無いときは None。読み取りのみ。run_v102_analysis と prompt_ab_recompute が共通で呼ぶ。"""
    row = session.execute(text(_POSTED_AT_SQL.format(schema=analyzer.TCG_SCHEMA)), {"ej": extraction_job_id}).first()
    return posted_jst_date(row.line_posted_at) if row is not None else None


def run_v102_analysis(session: Session, extraction_job_id: str) -> dict:
    """システム段。保存済みの件（extraction_items）から analysis_results を作る。Gemini を呼ばない。冪等。

    戻り値は analyze_extraction_job と同じ形のキー（total / pid_resolved / unit_resolved / needs_review）。
    v102 の処理の例外・件の対応付けの失敗は、extraction_jobs.review_reasons に extract_exception を残し、件は消さない（再送出しない）。
    マスタが空などの設定の誤りは呼び出し元へ送出する（黙って進まない）。
    """
    from app.tasks.tcg_extraction import load_extraction_context  # noqa: PLC0415  循環 import を避ける

    schema = analyzer.TCG_SCHEMA
    # 同じ投稿のやり直しが並行して走ると、判断の読み込みと書き込みが交差する。取引の最初に投稿ごとの鍵を取り、順番に走らせる
    session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": v102_analysis_lock_key(extraction_job_id)})
    ctx = load_extraction_context(session, extraction_job_id)
    if ctx is None:
        raise ValueError(f"extraction_job が見つかりません: {extraction_job_id}")
    job = session.execute(
        text(f"SELECT gemini_unsure, review_reasons FROM {schema}.extraction_jobs WHERE id = :ej"), {"ej": extraction_job_id}
    ).one()
    rows = session.execute(
        text(f"""
            SELECT id, gemini_index, source_lines, line_start, line_end, raw_price, raw_quantity FROM {schema}.extraction_items
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
        # ADR-1032: 書き直す前（_write_results より前）に「現行だった組」を控える。前の行が無ければ None（控え無し）
        prior_current = _load_current_pairs(session, extraction_job_id) if previous_pairs else None
        followup_masters = masters_with_followup(
            masters, load_followup_reference(session, extraction_job_id), load_soldout_ref_posts(session, extraction_job_id),
            load_posted_date(session, extraction_job_id),
        )
        pipeline = run_v102_pipeline(response_text, ctx, followup_masters, fixed_products=fixed_products)
        stats = _write_results(session, extraction_job_id, pipeline, rows, masters, unit_ids, decisions, ctx.raw_text)
        session.commit()
    except Exception:  # noqa: BLE001
        session.rollback()
        logger.exception("[line_analysis] v102 のシステム段が失敗しました: job=%s", extraction_job_id)
        _set_job_review_reasons(session, extraction_job_id, REASON_EXTRACT_EXCEPTION)
        _clear_job_review_detail(session, extraction_job_id)
        session.commit()
        return empty_stats
    analyzer._merge_supplier_products(  # ADR-158（is_current）+ ADR-1032（復活止め）
        session, extraction_job_id, schema, extra_pairs=previous_pairs, prior_current_pairs=prior_current,
    )
    logger.info("[line_analysis] v102 job=%s stats=%s", extraction_job_id, stats)
    return stats
