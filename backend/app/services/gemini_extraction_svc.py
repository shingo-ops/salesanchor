"""
MIG-04 Stage 2: Gemini 抽出サービス。

RawExtractionV2.js (GAS) の RAW_EXTRACTION_V2_PROMPT_TEXT を Python に移植し、
Gemini 3.6 Flash で LINE メッセージから商品明細を抽出する。

設計:
  - google-genai SDK (新) を使用
  - temperature=0 で冪等性を確保
  - GEMINI_API_KEY 環境変数必須
  - 同期 API (models.generate_content) を使用（Celery タスク内から呼ぶため）

既存APIとの互換:
  - プロンプト連結: PROMPT_TEXT + '\\n\\n原文:\\n' + input（v3では作品マスタ参照を追加）
  - モデル: gemini-3.6-flash / temperature=0
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

from celery.exceptions import SoftTimeLimitExceeded

from app.services.tcg_extraction_record_svc import RecordError
from app.services.tcg_work_reference import (
    WORK_ID_PROMPT_VERSION,
    reference_json,
    validate_product_id,
    validate_work_id,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 絵文字除去
# ---------------------------------------------------------------------------

# Unicode Emoji ranges — covers emoticons, symbols, pictographs, transport,
# flags, and supplemental symbols commonly found in LINE messages.
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # misc symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # geometric shapes extended
    "\U0001F800-\U0001F8FF"  # supplemental arrows-C
    "\U0001F900-\U0001F9FF"  # supplemental symbols & pictographs
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols & pictographs extended-A
    "\U00002702-\U000027B0"  # dingbats
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # zero width joiner
    "\U000020E3"             # combining enclosing keycap
    "\U00002600-\U000026FF"  # misc symbols (but preserve ◆●■ etc.)
    "\U00002700-\U000027BF"  # dingbats
    "\U0000231A-\U0000231B"  # watch, hourglass
    "\U000023E9-\U000023F3"  # media control
    "\U000023F8-\U000023FA"  # media control
    "]+",
    flags=re.UNICODE,
)


def strip_emoji(text: str) -> str:
    """Remove emoji from text before sending to Gemini.

    Preserves line structure (newlines) so L0001-style line IDs remain aligned.
    Common CJK symbols used in inventory lists (◆●■▲ etc.) are NOT removed.
    """
    return _EMOJI_RE.sub("", text)


# ---------------------------------------------------------------------------
# プロンプトバージョン
# ---------------------------------------------------------------------------

PROMPT_VERSION = "raw-extraction-v3-work-p1"

# ---------------------------------------------------------------------------
# DB からプロンプト設定を取得（DB 必須・フォールバックなし）
# ---------------------------------------------------------------------------

_SYNC_DB_URL = os.getenv("DATABASE_URL", "").replace(
    "postgresql+asyncpg://", "postgresql://"
)


def _load_db_prompts() -> tuple[str, str]:
    """
    public.extraction_prompt_config からアクティブなプロンプトを取得する。
    DB接続失敗またはプロンプト未登録の場合は RuntimeError を発生させる。
    """
    if not _SYNC_DB_URL:
        raise RuntimeError(
            "抽出プロンプト設定エラー: DATABASE_URL が未設定です。"
            "extraction_prompt_config テーブルからプロンプトを読み取れません。"
        )
    try:
        from sqlalchemy import create_engine
        from sqlalchemy import text as sa_text
        engine = create_engine(_SYNC_DB_URL, echo=False, pool_pre_ping=True)
        with engine.connect() as conn:
            rows = conn.execute(
                sa_text(
                    "SELECT prompt_key, prompt_text FROM public.extraction_prompt_config "
                    "WHERE is_active = TRUE"
                )
            ).mappings().all()
    except Exception as exc:
        raise RuntimeError(
            f"抽出プロンプト設定エラー: DBからプロンプトを読み取れません: {exc}"
        ) from exc

    prompts: dict[str, str] = {}
    for row in rows:
        key = row["prompt_key"]
        txt = row["prompt_text"]
        if txt:
            prompts[key] = txt

    base_text = prompts.get("base_extraction")
    work_id_text = prompts.get("work_id_extraction")

    if not base_text:
        raise RuntimeError(
            "抽出プロンプト設定エラー: base_extraction プロンプトがDBに登録されていないか無効です。"
            "管理画面 > 解析状況 > 抽出プロンプト設定 から登録してください。"
        )
    if not work_id_text:
        raise RuntimeError(
            "抽出プロンプト設定エラー: work_id_extraction プロンプトがDBに登録されていないか無効です。"
            "管理画面 > 解析状況 > 抽出プロンプト設定 から登録してください。"
        )
    return base_text, work_id_text


# 全角パイプ区切り
_PIPE = "｜"

# RAW_SOURCE_LINE_SPAN パターン: L0001-L0002 または L0001
_SPAN_RE = re.compile(r"^L(\d+)(?:-L(\d+))?$")

# ---------------------------------------------------------------------------
# セキュリティ: エラーメッセージ sanitize
# ---------------------------------------------------------------------------

_HTTP_STATUS_RE = re.compile(r"\b([45]\d{2})\b")

_HTTP_REASONS: dict[int, str] = {
    400: "リクエストエラー",
    401: "認証エラー",
    403: "アクセス拒否",
    429: "レート制限超過",
    500: "サーバーエラー",
    503: "サービス利用不可",
}


def _safe_error_message(exc: Exception) -> str:
    """例外からAPIキーを除いた安全なエラーメッセージを生成する。

    HTTPステータスコードが検出できる場合は「理由 (HTTP NNN)」形式を返す。
    それ以外は key= パターンを伏せ字にする。
    """
    msg = str(exc)
    m = _HTTP_STATUS_RE.search(msg)
    if m:
        code = int(m.group(1))
        reason = _HTTP_REASONS.get(code, "HTTPエラー")
        return f"{reason} (HTTP {code})"
    return re.sub(r"key=[^\s&'\"<>]+", "(APIキー省略)", msg)


def _classify_error(exc: Exception) -> str:
    """Classify a Gemini API exception into a category for diagnostics."""
    msg = str(exc)
    if re.search(r"\b429\b", msg) or "RESOURCE_EXHAUSTED" in msg:
        return "gemini_rate_limit"
    if re.search(r"\b[45]\d{2}\b", msg):
        return "gemini_http_error"
    if "timeout" in msg.lower() or "deadline" in msg.lower():
        return "gemini_timeout"
    return "gemini_unknown"


# ---------------------------------------------------------------------------
# ユーティリティ: 行アノテーション
# ---------------------------------------------------------------------------


def annotate_lines(raw_text: str) -> list[dict]:
    """各行に L0001 形式の Line ID を付与する。"""
    lines = raw_text.split("\n")
    return [{"id": f"L{i + 1:04d}", "text": line} for i, line in enumerate(lines)]


def format_prompt_input(raw_text: str) -> str:
    """raw_text を [L0001] 行テキスト 形式に変換してプロンプト入力を作る。"""
    cleaned = strip_emoji(raw_text)
    annotated = annotate_lines(cleaned)
    return "\n".join(f'[{item["id"]}] {item["text"]}' for item in annotated)


# ---------------------------------------------------------------------------
# Gemini SDK 初期化
# ---------------------------------------------------------------------------


def _get_genai_client():
    """google.genai.Client を生成して返す。"""
    try:
        from google import genai  # type: ignore[import-untyped]
        from google.genai import types as _types  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "google-genai がインストールされていません: pip install google-genai"
        ) from exc
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY が未設定です。Gemini 抽出は実行できません。"
        )
    return genai.Client(api_key=api_key)


# ---------------------------------------------------------------------------
# コア: Gemini API 呼び出し
# ---------------------------------------------------------------------------

_GEMINI_MODEL = "gemini-3.1-flash-lite"


def _build_supplier_context_note(supplier_context: dict, knowledge_links: list[dict] | None = None) -> str:
    """仕入元抽出ルール辞書をプロンプト注入用テキストに変換する。

    Args:
        supplier_context: 仕入元抽出ルール辞書（extraction_price_format 等）
        knowledge_links: supplier_knowledge_links + knowledge_rules の結合行リスト。
                         各要素は {"category": str, "pattern": str, "normalized_to": str|None}
    """
    import json as _json

    _PATTERN_MAP = {
        "quantity": "[数量]",
        "unit": "[単位]",
        "price": "[価格]",
        "status": "[状態]",
        "@": "@",
        "yen": "円",
        "yen_prefix": "￥",
        "space": " ",
        "dot": "・",
        "newline": "\n",
        "slash": "/",
        "stock_label": "在庫",
        "none": "",
    }

    parts = []
    label_map = {
        "extraction_price_format": "価格フォーマット",
        "extraction_qty_format": "数量フォーマット",
        "extraction_default_unit": "デフォルト単位",
        "extraction_notes": "補足ルール",
        "extraction_state_format": "状態フォーマット",
    }
    for key, label in label_map.items():
        val = supplier_context.get(key)
        if val:
            parts.append(f"- {label}: {val}")

    # extraction_order_pattern: JSON配列（新形式）または文字列（旧形式）
    order_pattern = supplier_context.get("extraction_order_pattern", "")
    if order_pattern:
        try:
            tokens = _json.loads(order_pattern)
            if isinstance(tokens, list):
                human_pattern = "".join(_PATTERN_MAP.get(tok, tok) for tok in tokens)
                parts.append(f"- 明細行のフォーマット: {human_pattern}")
            else:
                parts.append(f"- 注文パターン: {order_pattern}")
        except (_json.JSONDecodeError, TypeError):
            parts.append(f"- 注文パターン: {order_pattern}")
    lines = []
    if parts:
        lines.append("【仕入元固有の抽出ルール】")
        lines.extend(parts)
    if supplier_context.get("extraction_example_text"):
        lines.append("以下はこの仕入元の典型的なメッセージ例です。この書き方パターンを参考にして解析してください：")
        lines.append(supplier_context["extraction_example_text"])

    # Knowledge リンクからの注入
    if knowledge_links:
        delimiters = [lnk["pattern"] for lnk in knowledge_links if lnk["category"] == "block_delimiter"]
        status_kws = [
            (lnk["pattern"], lnk.get("normalized_to") or "")
            for lnk in knowledge_links if lnk["category"] == "status_keyword"
        ]

        if delimiters:
            lines.append(f"商品ブロックの区切り記号: {', '.join(delimiters)}")
            lines.append("上記の記号で始まる行が各商品ブロックの開始です。")
        if status_kws:
            status_parts = [f"「{kw}」→{norm}" for kw, norm in status_kws]
            lines.append(f"ステータス判定: {', '.join(status_parts)}")

    if not lines:
        return ""
    return "\n".join(lines)


def call_gemini_extraction(
    raw_text: str, works: list[dict] | None = None, *,
    work_reference: dict | None = None,
    recorder=None,
    supplier_context: dict | None = None,
    knowledge_links: list[dict] | None = None,
) -> str:
    """
    Gemini API を呼び出し、抽出結果テキスト（パイプ区切り表）を返す。

    モデル: gemini-3.6-flash（GAS 側デフォルトと同一）
    temperature: 0
    プロンプト連結: PROMPT_TEXT + '\\n\\n原文:\\n' + prompt_input（v3では作品マスタ参照を追加）
    同期 SDK (models.generate_content) を使用。

    Args:
        supplier_context: 仕入元抽出ルール辞書。指定された場合プロンプトに注入する。
        knowledge_links: supplier_knowledge_links + knowledge_rules 結合行リスト。
                         各要素は {"category": str, "pattern": str, "normalized_to": str|None}

    Raises:
        RuntimeError: GEMINI_API_KEY 未設定 / API 呼び出し失敗
    """
    from google.genai import types as genai_types  # type: ignore[import-untyped]

    # DB からアクティブプロンプトを取得（フォールバック: ハードコード定数）
    db_base_prompt, db_work_id_prompt = _load_db_prompts()

    prompt_input = format_prompt_input(raw_text)
    # v3作品参照の付加前の原文連結: PROMPT_TEXT + '\n\n原文:\n' + input
    work_names = [
        {"display_name": w["display_name"], "alt_name": w.get("alt_name")}
        for w in (works or []) if w.get("is_active", True)
    ]
    import json

    reference = json.dumps(work_names, ensure_ascii=False)

    # 仕入元ルール注入（指定がある場合のみ）
    supplier_note = (
        _build_supplier_context_note(supplier_context, knowledge_links=knowledge_links)
        if supplier_context
        else (_build_supplier_context_note({}, knowledge_links=knowledge_links) if knowledge_links else "")
    )
    supplier_section = f"\n{supplier_note}\n" if supplier_note else ""

    full_prompt = f"{db_base_prompt}{supplier_section}\n作品マスタ（参照値）:{reference}\n\n原文:\n{prompt_input}"

    if work_reference is not None:
        full_prompt = (f"{db_work_id_prompt}{supplier_section}\n商品・作品マスタ（参照値）:"
                       f"{reference_json(work_reference)}\n\n原文:\n{prompt_input}")

    payload: dict[str, Any] = {"model": _GEMINI_MODEL, "contents": full_prompt, "config": {"temperature": 0}}
    if recorder is not None:
        recorder.before_send(payload)
    client = _get_genai_client()

    logger.info(
        "[gemini_extraction] calling Gemini API, model=%s text_len=%d",
        _GEMINI_MODEL,
        len(raw_text),
    )

    try:
        response = client.models.generate_content(
            model=payload["model"],
            contents=payload["contents"],
            config=genai_types.GenerateContentConfig(**payload["config"]),
        )
    except SoftTimeLimitExceeded:
        raise
    except Exception as exc:
        if recorder is not None:
            detail = _safe_error_message(exc)
            recorder.record_error_detail({"raw": detail, "category": _classify_error(exc)})
            raise RecordError("API_ERROR") from None
        logger.exception("[gemini_extraction] API call failed: %s", _safe_error_message(exc))
        raise RuntimeError(f"Gemini API 呼び出し失敗: {_safe_error_message(exc)}") from exc

    result_text = getattr(response, "text", "") or ""
    # トークン数取得
    usage = getattr(response, "usage_metadata", None)
    input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
    output_tokens = int(getattr(usage, "response_token_count", 0) or 0)
    if recorder is not None:
        recorder.on_response(result_text, input_tokens=input_tokens, output_tokens=output_tokens)
    logger.info(
        "[gemini_extraction] API response received, response_len=%d", len(result_text)
    )
    return result_text


# ---------------------------------------------------------------------------
# パース: パイプ区切りテーブル → items リスト
# ---------------------------------------------------------------------------


def parse_extraction_response(
    response_text: str, raw_text: str, *, version: int = 2,
) -> tuple[list[dict], list[dict]]:
    """
    Gemini の出力テキスト（パイプ区切りテーブル）をパースして items リストと parse_errors リストを返す。

    戻り値: (items, parse_errors)
      items: [
        {
          "raw_product_name": str,
          "raw_quantity": str,
          "raw_price": str,
          "raw_unit": str,
          "raw_state": str,
          "raw_memo": str,
          "line_start": int,  # 1-based
          "line_end": int,    # 1-based
        },
        ...
      ]
      parse_errors: [
        {"line": str, "error": str},
        ...
      ]

    ヘッダー欠落（v3+）は全体エラーとして ValueError を送出する（データ行の部分保存とは別）。
    データ行のパースエラーは parse_errors に追加して続行する。
    """
    if version not in (2, 3, 4, 5, 6):
        raise ValueError("Unsupported extraction format")
    expected_columns = {2: 7, 3: 9, 4: 10, 5: 11, 6: 12}[version]
    header = "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN"
    if version >= 3:
        header += "｜RAW_WORK_NAME｜RAW_WORK_SOURCE_LINE_SPAN"
    if version == 4:
        header += "｜RESOLVED_WORK_ID"
    if version == 5:
        header += "｜RESOLVED_WORK_ID｜RESOLVED_PRODUCT_CODE"
    if version == 6:
        header += "｜RESOLVED_WORK_ID｜RESOLVED_PRODUCT_CODE｜RAW_PRODUCT_CODE"
    max_line = len(raw_text.split("\n"))
    items: list[dict] = []
    parse_errors: list[dict] = []
    header_seen = False

    for line_raw in response_text.split("\n"):
        line = line_raw.strip()
        if not line:
            continue

        # ヘッダー行をスキップ
        if not header_seen:
            if version >= 3 and line != header:
                raise ValueError(f"v{version} extraction header must contain the exact {expected_columns} columns")
            if "RAW_PRODUCT_NAME" in line:
                header_seen = True
            continue

        try:
            cols = line.split(_PIPE)
            if len(cols) != expected_columns:
                if version >= 3:
                    raise ValueError(f"v{version} extraction expected {expected_columns} columns, got {len(cols)}")
                logger.warning(
                    "[gemini_extraction] schema error: expected 7 cols, got %d: %r",
                    len(cols),
                    line[:120],
                )
                continue

            (
                raw_product_name,
                raw_quantity,
                raw_price,
                raw_unit,
                raw_state,
                raw_memo,
                raw_span,
            ) = [c.strip() for c in cols[:7]]
            raw_work_name = cols[7].strip() if version >= 3 else None
            raw_work_span = cols[8].strip() if version >= 3 else None

            # RAW_SOURCE_LINE_SPAN パース
            span_m = _SPAN_RE.match(raw_span.strip())
            if span_m:
                line_start = int(span_m.group(1))
                line_end = int(span_m.group(2)) if span_m.group(2) else line_start
            else:
                if version >= 3:
                    # Shape only: never include customer text or model output in errors/logs.
                    detail = ""
                    if version in (4, 5, 6):
                        brackets = "[" in raw_span or "]" in raw_span
                        alphabet = all(c in "L0123456789-" for c in raw_span)
                        detail = f" (length={len(raw_span)}, brackets={brackets}, allowed_chars={alphabet})"
                    raise ValueError(f"v{version} extraction has an invalid product source span{detail}")
                # パース不能の span は警告のみ、先頭行扱いで続行
                logger.warning(
                    "[gemini_extraction] unparseable span: %r", raw_span
                )
                line_start = 1
                line_end = 1

            if version >= 3 and not (1 <= line_start <= line_end <= max_line):
                raise ValueError("v3 extraction product source span is outside the source")
            # 旧7列の位置補正を維持。v3の作品根拠は補正せず保存し、解析時に検証する。
            # クランプ
            line_start = max(1, min(line_start, max_line))
            line_end = max(line_start, min(line_end, max_line))

            items.append(
                {
                    "raw_product_name": raw_product_name,
                    "raw_quantity": raw_quantity,
                    "raw_price": raw_price,
                    "raw_unit": raw_unit,
                    "raw_state": raw_state,
                    "raw_memo": raw_memo,
                    "line_start": line_start,
                    "line_end": line_end,
                    "raw_work_name": raw_work_name,
                    "raw_work_source_line_span": raw_work_span,
                    "resolved_work_id": (cols[9].strip() or None) if version in (4, 5, 6) else None,
                    "resolved_product_code": (cols[10].strip() or None) if version in (5, 6) else None,
                    "raw_product_code": (cols[11].strip() or None) if version == 6 else None,
                }
            )
        except ValueError as exc:
            parse_errors.append({"line": line, "error": str(exc)})
            continue

    if version >= 3 and not header_seen:
        raise ValueError("v3 extraction response has no header")
    return items, parse_errors


# ---------------------------------------------------------------------------
# エントリポイント: 1 通のメッセージを抽出
# ---------------------------------------------------------------------------


def extract_message(
    raw_text: str, works: list[dict] | None = None, *,
    work_reference: dict | None = None,
    recorder=None,
    supplier_context: dict | None = None,
    knowledge_links: list[dict] | None = None,
) -> dict:
    """
    1 通の raw_text を Gemini で抽出する。

    Args:
        raw_text: 抽出対象の原文テキスト
        works: 作品リスト（オプション）
        work_reference: 作品参照（オプション、指定時 v5 形式を使用）
        recorder: AttemptRecorder（オプション）
        supplier_context: 仕入元ごとの抽出ルール辞書（オプション）
            extraction_price_format, extraction_qty_format,
            extraction_order_pattern, extraction_default_unit,
            extraction_notes を含む dict
        knowledge_links: supplier_knowledge_links + knowledge_rules 結合行リスト（オプション）
            各要素は {"category": str, "pattern": str, "normalized_to": str|None}

    戻り値:
      {
        "status": "done" | "empty" | "error",
        "prompt_version": PROMPT_VERSION,
        "items": [...],
        "raw_response": str,
        "error_message": str | None,
        "parse_errors": [...],
      }
    """
    prompt_version = WORK_ID_PROMPT_VERSION if work_reference is not None else PROMPT_VERSION
    response_text = ""
    error_code = "API_ERROR"
    try:
        kwargs = {"recorder": recorder} if recorder is not None else {}
        if supplier_context:
            kwargs["supplier_context"] = supplier_context
        if knowledge_links:
            kwargs["knowledge_links"] = knowledge_links
        if work_reference is None:
            response_text = call_gemini_extraction(raw_text, works=works, **kwargs)
        else:
            response_text = call_gemini_extraction(raw_text, works=works, work_reference=work_reference, **kwargs)
        error_code = "INVALID_RESPONSE"
        items, parse_errors = parse_extraction_response(response_text, raw_text, version=6 if work_reference is not None else 3)
        if work_reference is not None:
            for item in items:
                item["resolved_work_id"] = validate_work_id(item["resolved_work_id"], work_reference)
                item["resolved_product_code"] = validate_product_id(item.get("resolved_product_code"), work_reference)
                # raw_product_code is passed through as-is (no validation against reference)
        if items:
            status = "done"
        elif parse_errors:
            status = "error"
        else:
            status = "empty"
        error_message = None
        if parse_errors:
            error_message = f"PARTIAL_PARSE_ERRORS({len(parse_errors)}): " + "; ".join(
                e["error"] for e in parse_errors[:3]
            )
        return {
            "status": status,
            "prompt_version": prompt_version,
            "items": items,
            "raw_response": response_text if recorder is not None else "",
            "error_message": error_message,
            "parse_errors": parse_errors,
        }
    except SoftTimeLimitExceeded:
        raise
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, RecordError):
            error_code = str(exc)
        if recorder is None:
            logger.exception("[gemini_extraction] extract_message failed: %s", _safe_error_message(exc))
        else:
            logger.error("extraction_attempt=%s code=%s", recorder.id, error_code)
        return {
            "status": "error",
            "prompt_version": prompt_version,
            "items": [],
            "raw_response": response_text if recorder is not None else "",
            "error_message": error_code if recorder is not None else _safe_error_message(exc),
            "error_code": error_code,
        }


__all__ = [
    "PROMPT_VERSION",
    "call_gemini_extraction",
    "parse_extraction_response",
    "extract_message",
    "annotate_lines",
    "format_prompt_input",
    "strip_emoji",
    "_safe_error_message",
    "_classify_error",
]
