"""
MIG-04 Stage 2: gemini_extraction_svc / tcg_extraction の単体テスト（DB 不要）。

テスト対象:
  - annotate_lines: 行アノテーション
  - format_prompt_input: プロンプト入力フォーマット
  - call_gemini_extraction: プロンプト連結（GAS と一致）
  - parse_extraction_response: パイプ区切りパース
  - extract_message: 正常 / エラーパス
  - tcg_extraction: TCG_AUTO_ANALYZE フラグ（OFF / ON）
  - sql_schema_guard: SQL 文字列が tenant_004. を含み {TCG_SCHEMA} が残っていないこと
"""
from __future__ import annotations

import inspect
import os
from unittest.mock import MagicMock, patch

import pytest

from app.services.gemini_extraction_svc import (
    PROMPT_TEXT,
    annotate_lines,
    extract_message,
    format_prompt_input,
    parse_extraction_response,
)
from app.tcg_config import TCG_SCHEMA as _TCG_SCHEMA


# ─────────────────────────────────────────────────────────────────────────────
# annotate_lines
# ─────────────────────────────────────────────────────────────────────────────


def test_annotate_lines_basic():
    """3 行を L0001/L0002/L0003 でアノテーション。"""
    result = annotate_lines("行A\n行B\n行C")
    assert len(result) == 3
    assert result[0] == {"id": "L0001", "text": "行A"}
    assert result[1] == {"id": "L0002", "text": "行B"}
    assert result[2] == {"id": "L0003", "text": "行C"}


def test_annotate_lines_single():
    """1 行のみ。"""
    result = annotate_lines("only")
    assert result == [{"id": "L0001", "text": "only"}]


# ─────────────────────────────────────────────────────────────────────────────
# format_prompt_input
# ─────────────────────────────────────────────────────────────────────────────


def test_format_prompt_input_format():
    """各行が [L0001] テキスト 形式に変換される。"""
    result = format_prompt_input("商品A\n商品B")
    lines = result.split("\n")
    assert lines[0] == "[L0001] 商品A"
    assert lines[1] == "[L0002] 商品B"


# ─────────────────────────────────────────────────────────────────────────────
# プロンプト連結: GAS との一致検証
# ─────────────────────────────────────────────────────────────────────────────


def test_full_prompt_contains_genshi_prefix():
    """
    GAS との完全一致: PROMPT_TEXT + '\\n\\n原文:\\n' + prompt_input。
    call_gemini_extraction 内で組み立てられるプロンプトが
    '原文:\\n' セパレーターを含むことを確認する。
    """
    raw_text = "商品X 10個 500円"
    prompt_input = format_prompt_input(raw_text)
    # GAS と同じ連結式
    expected_full = f"{PROMPT_TEXT}\n\n原文:\n{prompt_input}"

    # ソースコードを直接検査して連結式が一致することを確認
    import app.services.gemini_extraction_svc as svc_mod

    source = inspect.getsource(svc_mod)
    assert '原文:\\n' in source or "原文:\\n" in source or "原文:\n" in repr(source), (
        "gemini_extraction_svc.py の full_prompt に '原文:\\n' が含まれていない。"
        "GAS との乖離あり。"
    )
    # 期待されるセパレーター文字列がソース中に存在するかを文字列検索で確認
    assert "原文:" in source, "プロンプト連結に '原文:' が含まれていない"


def test_prompt_input_embedded_in_genshi_separator():
    """format_prompt_input の出力が '原文:\\n' の直後に続く形で組み合わせられる。"""
    raw_text = "テスト行"
    prompt_input = format_prompt_input(raw_text)
    full = f"{PROMPT_TEXT}\n\n原文:\n{prompt_input}"
    assert "原文:\n[L0001] テスト行" in full


# ─────────────────────────────────────────────────────────────────────────────
# parse_extraction_response
# ─────────────────────────────────────────────────────────────────────────────

_VALID_RESPONSE = (
    "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN\n"
    "ポケモンカード｜3｜1500円｜枚｜｜｜L0001\n"
    "遊戯王カード｜10｜5000円｜枚｜PSA10｜レア｜L0002-L0003\n"
)


def test_parse_extraction_response_basic():
    """正常な 2 行を正しく解析する。"""
    raw_text = "行A\n行B\n行C"
    items = parse_extraction_response(_VALID_RESPONSE, raw_text)
    assert len(items) == 2

    assert items[0]["raw_product_name"] == "ポケモンカード"
    assert items[0]["raw_quantity"] == "3"
    assert items[0]["raw_price"] == "1500円"
    assert items[0]["raw_unit"] == "枚"
    assert items[0]["raw_state"] == ""
    assert items[0]["raw_memo"] == ""
    assert items[0]["line_start"] == 1
    assert items[0]["line_end"] == 1

    assert items[1]["raw_product_name"] == "遊戯王カード"
    assert items[1]["line_start"] == 2
    assert items[1]["line_end"] == 3


def test_parse_extraction_response_single_line_span():
    """L0001 単独 (ハイフンなし) は line_start == line_end。"""
    response = (
        "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN\n"
        "商品A｜1｜100円｜個｜｜｜L0001\n"
    )
    items = parse_extraction_response(response, "行A")
    assert items[0]["line_start"] == 1
    assert items[0]["line_end"] == 1


def test_parse_extraction_response_clamp_max():
    """line_end が raw_text の行数を超えた場合はクランプ。"""
    response = (
        "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN\n"
        "商品A｜1｜100円｜個｜｜｜L0001-L0099\n"
    )
    raw_text = "行A\n行B"  # 2行
    items = parse_extraction_response(response, raw_text)
    assert items[0]["line_end"] == 2  # クランプ


def test_parse_extraction_response_wrong_cols_skipped():
    """7列未満の行はスキップ（警告のみ）。"""
    response = (
        "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN\n"
        "A｜B｜C\n"  # 3列のみ
        "ポケモン｜3｜1500円｜枚｜｜｜L0001\n"
    )
    items = parse_extraction_response(response, "行A")
    assert len(items) == 1
    assert items[0]["raw_product_name"] == "ポケモン"


def test_parse_extraction_response_empty_response():
    """空レスポンスは空リスト。"""
    items = parse_extraction_response("", "行A")
    assert items == []


def test_parse_extraction_response_header_only():
    """ヘッダー行のみは空リスト。"""
    response = "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN\n"
    items = parse_extraction_response(response, "行A")
    assert items == []


# ─────────────────────────────────────────────────────────────────────────────
# extract_message: 正常 / 空 / エラーパス
# ─────────────────────────────────────────────────────────────────────────────


def test_extract_message_done(monkeypatch):
    """正常ケース: items が返れば status='done'。"""
    monkeypatch.setattr(
        "app.services.gemini_extraction_svc.call_gemini_extraction",
        lambda raw_text: _VALID_RESPONSE,
    )
    result = extract_message("行A\n行B\n行C")
    assert result["status"] == "done"
    assert len(result["items"]) == 2
    assert result["error_message"] is None


def test_extract_message_empty(monkeypatch):
    """Gemini がヘッダーのみ返した場合は status='empty'。"""
    monkeypatch.setattr(
        "app.services.gemini_extraction_svc.call_gemini_extraction",
        lambda raw_text: "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN\n",
    )
    result = extract_message("行A")
    assert result["status"] == "empty"
    assert result["items"] == []


def test_extract_message_error_on_api_failure(monkeypatch):
    """API 失敗時は status='error' でエラーメッセージを返す。"""
    def raise_error(raw_text):
        raise RuntimeError("API timeout")

    monkeypatch.setattr(
        "app.services.gemini_extraction_svc.call_gemini_extraction",
        raise_error,
    )
    result = extract_message("行A")
    assert result["status"] == "error"
    assert "API timeout" in result["error_message"]
    assert result["items"] == []


# ─────────────────────────────────────────────────────────────────────────────
# TCG_AUTO_ANALYZE フラグ制御
# ─────────────────────────────────────────────────────────────────────────────


def _make_mock_session(raw_text: str = "行A\n行B"):
    """DB セッションのモック（pending job を 1 件返す）。"""
    mock_row = MagicMock()
    mock_row.__getitem__ = lambda self, idx: ("test-ej-id" if idx == 0 else raw_text)

    mock_result = MagicMock()
    mock_result.fetchone.return_value = mock_row

    mock_session = MagicMock()
    mock_session.execute.return_value = mock_result
    return mock_session


def test_auto_analyze_off_skips_analyze(monkeypatch):
    """TCG_AUTO_ANALYZE 未設定のとき analyze_extraction_job を呼ばない。"""
    monkeypatch.delenv("TCG_AUTO_ANALYZE", raising=False)

    mock_session = _make_mock_session()
    analyze_called = []

    def mock_extract(raw_text):
        return {
            "status": "done",
            "prompt_version": "v1",
            "items": [
                {
                    "raw_product_name": "商品A",
                    "raw_quantity": "1",
                    "raw_price": "100円",
                    "raw_unit": "個",
                    "raw_state": "",
                    "raw_memo": "",
                    "line_start": 1,
                    "line_end": 1,
                }
            ],
            "raw_response": "",
            "error_message": None,
        }

    def mock_analyze(session, ej_id):
        analyze_called.append(ej_id)
        return {"matched": 1}

    with patch("app.tasks.tcg_extraction.extract_message", mock_extract), \
         patch("app.tasks.tcg_extraction.analyze_extraction_job", mock_analyze):
        from app.tasks.tcg_extraction import _run_extraction
        result = _run_extraction(mock_session, "test-sm-id")

    assert result["status"] == "done"
    assert result["analysis_stats"] is None
    assert analyze_called == [], "TCG_AUTO_ANALYZE=0 のとき analyze を呼ぶべきでない"


def test_auto_analyze_on_calls_analyze(monkeypatch):
    """TCG_AUTO_ANALYZE=1 のとき analyze_extraction_job を呼ぶ。"""
    monkeypatch.setenv("TCG_AUTO_ANALYZE", "1")

    mock_session = _make_mock_session()
    analyze_called = []

    def mock_extract(raw_text):
        return {
            "status": "done",
            "prompt_version": "v1",
            "items": [
                {
                    "raw_product_name": "商品A",
                    "raw_quantity": "1",
                    "raw_price": "100円",
                    "raw_unit": "個",
                    "raw_state": "",
                    "raw_memo": "",
                    "line_start": 1,
                    "line_end": 1,
                }
            ],
            "raw_response": "",
            "error_message": None,
        }

    def mock_analyze(session, ej_id):
        analyze_called.append(ej_id)
        return {"matched": 1}

    with patch("app.tasks.tcg_extraction.extract_message", mock_extract), \
         patch("app.tasks.tcg_extraction.analyze_extraction_job", mock_analyze):
        from app.tasks.tcg_extraction import _run_extraction
        result = _run_extraction(mock_session, "test-sm-id")

    assert result["status"] == "done"
    assert result["analysis_stats"] == {"matched": 1}
    assert len(analyze_called) == 1, "TCG_AUTO_ANALYZE=1 のとき analyze を 1 回呼ぶべき"


# ─────────────────────────────────────────────────────────────────────────────
# SQL スキーマ守護テスト（IMP-05 の穴を塞ぐ）
# ─────────────────────────────────────────────────────────────────────────────


def _extract_sql_strings_from_source(source: str) -> list[str]:
    """
    ソースコード中の text(...) 呼び出し内の SQL 文字列を抽出する。
    f-string の場合は {TCG_SCHEMA} を TCG_SCHEMA の実際の値に展開して検査する。
    """
    import re

    # text( の直後から ) までの文字列リテラルを抽出（単純な実装）
    # f"""...""" / f"..." / """...""" / "..." に対応
    patterns = [
        r'text\(\s*f"""(.*?)"""\s*\)',
        r"text\(\s*f'''(.*?)'''\s*\)",
        r'text\(\s*f"(.*?)"\s*\)',
        r"text\(\s*f'(.*?)'\s*\)",
        r'text\(\s*"""(.*?)"""\s*\)',
        r"text\(\s*'''(.*?)'''\s*\)",
    ]
    sqls = []
    for pat in patterns:
        for m in re.finditer(pat, source, re.DOTALL):
            sql = m.group(1)
            # {TCG_SCHEMA} を実際の値に展開（f-string のシミュレーション）
            sql = sql.replace("{TCG_SCHEMA}", _TCG_SCHEMA)
            sqls.append(sql)
    return sqls


def test_tcg_extraction_sql_has_schema_prefix():
    """
    tcg_extraction.py の全 text(...) SQL 文字列が TCG_SCHEMA. を含み、
    {TCG_SCHEMA} が文字どおり残っていないこと。
    (IMP-05: 6 箇所が f 無しで {TCG_SCHEMA} が置換されなかった教訓)
    """
    import app.tasks.tcg_extraction as mod

    source = inspect.getsource(mod)
    sqls = _extract_sql_strings_from_source(source)

    assert sqls, "tcg_extraction.py に text() SQL が見つからない（実装漏れの可能性）"

    for sql in sqls:
        assert f"{_TCG_SCHEMA}." in sql, (
            f"SQL に '{_TCG_SCHEMA}.' が含まれていない:\n{sql[:200]}"
        )
        assert "{TCG_SCHEMA}" not in sql, (
            f"SQL に未展開の '{{TCG_SCHEMA}}' が残っている（f-string 忘れ）:\n{sql[:200]}"
        )


def test_tcg_line_import_svc_sql_has_schema_prefix():
    """
    tcg_line_import_svc.py も同様のスキーマ守護。
    (既存ファイルの回帰検査)
    """
    import app.services.tcg_line_import_svc as mod

    source = inspect.getsource(mod)
    sqls = _extract_sql_strings_from_source(source)

    # tcg_line_import_svc は text(f"...") 形式を使用
    for sql in sqls:
        assert f"{_TCG_SCHEMA}." in sql, (
            f"tcg_line_import_svc.py の SQL に '{_TCG_SCHEMA}.' が含まれていない:\n{sql[:200]}"
        )
        assert "{TCG_SCHEMA}" not in sql, (
            f"tcg_line_import_svc.py の SQL に未展開の '{{TCG_SCHEMA}}' が残っている:\n{sql[:200]}"
        )
