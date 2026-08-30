"""
MIG-04 Phase 3: Gemini 抽出サービス。

RawExtractionV2.js (GAS) の RAW_EXTRACTION_V2_PROMPT_TEXT を Python に移植し、
Gemini 3.6 Flash で LINE メッセージから商品明細を抽出する。

設計:
  - google-genai SDK (新) を使用
  - temperature=0 で冪等性を確保
  - GEMINI_API_KEY 環境変数必須
  - 同期 API (models.generate_content) を使用（Celery タスク内から呼ぶため）
"""
from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# プロンプト定数
# ---------------------------------------------------------------------------

PROMPT_VERSION = "raw-extraction-v2-p1"

PROMPT_TEXT = (
    "あなたは原文から事実だけを抽出する。分類、翻訳、要約、ID付与、正準化、状態の推測は禁止。"
    "入力行の先頭にある[L0001]形式のLine IDはSystemが付与した位置情報である。新しいIDを作らず、入力にあるIDだけを使え。"
    "各商品明細を1行ずつ、次の7列を全角パイプで区切って出力せよ。"
    "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN\n"
    "RAW_PRODUCT_NAME: 原文にある商品名。RAW_QUANTITY: 原文にある数量。RAW_PRICE: 原文にある価格。"
    "RAW_UNIT: 数量に直接対応する単位・販売形態だけ。通貨は絶対に入れない。原文に単位がなければ空欄。"
    "RAW_STATE: 原文にある状態語だけ。なければ空欄。RAW_MEMO: その商品の補足として原文にある語だけ。なければ空欄。"
    "RAW_SOURCE_LINE_SPAN: 商品明細に対応する入力Line IDの連続範囲をL0001-L0002形式で返せ。"
    "商品名と数量・価格が別の物理行なら、それらを含む最小の連続範囲を返せ。"
    "Category、product_id、Conditionの正準値、Status、Note_JA、Note_EN、FLAG、route、その他のIDは出力禁止。"
    "1行目は必ずRAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPANと出力せよ。"
    "ヘッダー以外の説明文、Markdown、JSONは出力禁止。"
)

# 全角パイプ区切り
_PIPE = "｜"

# RAW_SOURCE_LINE_SPAN パターン: L0001-L0002 または L0001
_SPAN_RE = re.compile(r"^L(\d+)(?:-L(\d+))?$")


# ---------------------------------------------------------------------------
# ユーティリティ: 行アノテーション
# ---------------------------------------------------------------------------


def annotate_lines(raw_text: str) -> list[dict]:
    """各行に L0001 形式の Line ID を付与する。"""
    lines = raw_text.split("\n")
    return [{"id": f"L{i + 1:04d}", "text": line} for i, line in enumerate(lines)]


def format_prompt_input(raw_text: str) -> str:
    """raw_text を [L0001] 行テキスト 形式に変換してプロンプト入力を作る。"""
    annotated = annotate_lines(raw_text)
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

_GEMINI_MODEL = "gemini-3.6-flash"


def call_gemini_extraction(raw_text: str) -> str:
    """
    Gemini API を呼び出し、抽出結果テキスト（パイプ区切り表）を返す。

    モデル: gemini-3.6-flash（GAS 側デフォルトと同一）
    temperature: 0
    同期 SDK (models.generate_content) を使用。

    Raises:
        RuntimeError: GEMINI_API_KEY 未設定 / API 呼び出し失敗
    """
    from google.genai import types as genai_types  # type: ignore[import-untyped]

    client = _get_genai_client()

    prompt_input = format_prompt_input(raw_text)
    full_prompt = f"{PROMPT_TEXT}\n\n{prompt_input}"

    logger.info(
        "[gemini_extraction] calling Gemini API, model=%s text_len=%d",
        _GEMINI_MODEL,
        len(raw_text),
    )

    try:
        response = client.models.generate_content(
            model=_GEMINI_MODEL,
            contents=full_prompt,
            config=genai_types.GenerateContentConfig(temperature=0),
        )
    except Exception as exc:
        logger.exception("[gemini_extraction] API call failed: %s", exc)
        raise RuntimeError(f"Gemini API 呼び出し失敗: {exc}") from exc

    result_text = getattr(response, "text", "") or ""
    logger.info(
        "[gemini_extraction] API response received, response_len=%d", len(result_text)
    )
    return result_text


# ---------------------------------------------------------------------------
# パース: パイプ区切りテーブル → items リスト
# ---------------------------------------------------------------------------


def parse_extraction_response(response_text: str, raw_text: str) -> list[dict]:
    """
    Gemini の出力テキスト（パイプ区切りテーブル）をパースして items リストを返す。

    戻り値: [
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
    """
    max_line = len(raw_text.split("\n"))
    items: list[dict] = []
    header_seen = False

    for line_raw in response_text.split("\n"):
        line = line_raw.strip()
        if not line:
            continue

        # ヘッダー行をスキップ
        if not header_seen:
            if "RAW_PRODUCT_NAME" in line:
                header_seen = True
            continue

        cols = line.split(_PIPE)
        if len(cols) != 7:
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
        ) = [c.strip() for c in cols]

        # RAW_SOURCE_LINE_SPAN パース
        span_m = _SPAN_RE.match(raw_span.strip())
        if span_m:
            line_start = int(span_m.group(1))
            line_end = int(span_m.group(2)) if span_m.group(2) else line_start
        else:
            # パース不能の span は警告のみ、先頭行扱いで続行
            logger.warning(
                "[gemini_extraction] unparseable span: %r", raw_span
            )
            line_start = 1
            line_end = 1

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
            }
        )

    return items


# ---------------------------------------------------------------------------
# エントリポイント: 1 通のメッセージを抽出
# ---------------------------------------------------------------------------


def extract_message(raw_text: str) -> dict:
    """
    1 通の raw_text を Gemini で抽出する。

    戻り値:
      {
        "status": "done" | "empty" | "error",
        "prompt_version": PROMPT_VERSION,
        "items": [...],
        "raw_response": str,
        "error_message": str | None,
      }
    """
    try:
        response_text = call_gemini_extraction(raw_text)
        items = parse_extraction_response(response_text, raw_text)
        status = "done" if items else "empty"
        return {
            "status": status,
            "prompt_version": PROMPT_VERSION,
            "items": items,
            "raw_response": response_text,
            "error_message": None,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("[gemini_extraction] extract_message failed: %s", exc)
        return {
            "status": "error",
            "prompt_version": PROMPT_VERSION,
            "items": [],
            "raw_response": "",
            "error_message": str(exc),
        }


__all__ = [
    "PROMPT_VERSION",
    "PROMPT_TEXT",
    "call_gemini_extraction",
    "parse_extraction_response",
    "extract_message",
    "annotate_lines",
    "format_prompt_input",
]
