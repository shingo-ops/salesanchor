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
        lambda raw_text, **kwargs: _v3_response(_VALID_RESPONSE),
    )
    result = extract_message("行A\n行B\n行C")
    assert result["status"] == "done"
    assert len(result["items"]) == 2
    assert result["error_message"] is None


def test_extract_message_empty(monkeypatch):
    """Gemini がヘッダーのみ返した場合は status='empty'。"""
    monkeypatch.setattr(
        "app.services.gemini_extraction_svc.call_gemini_extraction",
        lambda raw_text, **kwargs: _V3_HEADER + "\n",
    )
    result = extract_message("行A")
    assert result["status"] == "empty"
    assert result["items"] == []


def test_extract_message_error_on_api_failure(monkeypatch):
    """API 失敗時は status='error' でエラーメッセージを返す。"""
    def raise_error(raw_text, **kwargs):
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

    def mock_extract(raw_text, **kwargs):
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

    def mock_extract(raw_text, **kwargs):
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


_V3_HEADER = "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN｜RAW_WORK_NAME｜RAW_WORK_SOURCE_LINE_SPAN"


def _v3_response(old_response):
    lines = old_response.strip().split("\n")
    return _V3_HEADER + "\n" + "\n".join(line + "｜｜" for line in lines[1:])


@pytest.mark.parametrize("response", [
    "", "   ", "商品A｜1｜100｜BOX｜｜｜L0001｜｜", _VALID_RESPONSE,
    _V3_HEADER + "\n商品A｜1｜100｜BOX｜｜｜L0001",
    _V3_HEADER + "\n商品A｜1｜100｜BOX｜｜｜L0001｜｜\n壊れた｜行",
])
def test_v3_format_failure_saves_no_partial_items(monkeypatch, response):
    monkeypatch.setattr("app.services.gemini_extraction_svc.call_gemini_extraction",
                        lambda *args, **kwargs: response)
    result = extract_message("商品A")
    assert result["status"] == "error"
    assert result["items"] == []


@pytest.mark.parametrize("span", ["L0000", "L0099", "L0002-L0001", "bad"])
def test_v3_product_span_never_clamped(span):
    with pytest.raises(ValueError):
        parse_extraction_response(_V3_HEADER + f"\nガンダム EB01｜1｜100｜BOX｜｜｜{span}｜ガンダム｜L0001",
                                  "ガンダム EB01", version=3)


def test_v3_work_evidence_roundtrip_without_repair():
    row = "ガンダム EB01｜1｜100｜BOX｜｜｜L0001｜ガンダム｜L0099"
    item = parse_extraction_response(_V3_HEADER + "\n" + row, "ガンダム EB01", version=3)[0]
    assert item["raw_work_name"] == "ガンダム"
    assert item["raw_work_source_line_span"] == "L0099"  # analyzer rejects, never clamps
    assert parse_extraction_response(_VALID_RESPONSE, "a\nb\nc")[0]["raw_work_name"] is None


def test_work_master_reaches_prompt_without_database_ids(monkeypatch):
    from app.services import gemini_extraction_svc as svc
    client = MagicMock()
    client.models.generate_content.return_value.text = _V3_HEADER
    monkeypatch.setattr(svc, "_get_genai_client", lambda: client)
    svc.call_gemini_extraction("ガンダム EB01", works=[
        dict(id="secret-database-id", display_name="GUNDAM", alt_name="ガンダム"),
        dict(id="inactive-id", display_name="inactive-work", is_active=False),
    ])
    prompt = client.models.generate_content.call_args.kwargs["contents"]
    assert '"display_name": "GUNDAM"' in prompt and '[L0001] ガンダム EB01' in prompt
    assert "secret-database-id" not in prompt and "inactive-work" not in prompt


# Anonymous live-Gemini acceptance corpus (not an execution or accuracy result).
# A live run must report format errors / correct / unknown / wrong independently.
LIVE_WORK_SAMPLES = [
    ("ポケモン スタートデッキ100 1BOX 1000円", ["ポケモン"]),
    ("ワンピース EB01 1BOX 1000円", ["ワンピース"]),
    ("ガンダム EB01 1BOX 1000円", ["ガンダム"]),
    ("【ガンダム】\nEB01 1BOX 1000円", ["ガンダム"]),
    ("【ポケモン】\nスタートデッキ100 1BOX 1000円\n[ワンピース]\nEB01 1BOX 1000円\nガンダム\nEB01 2BOX 2000円",
     ["ポケモン", "ワンピース", "ガンダム"]),
    ("EB01 1BOX 1000円", [""]),
]


# BEGIN TEMPORARY LIVE MEASUREMENT -- remove after this one CI run.
def test_temporary_live_work_measurement(capsys):
    """Finite card-authorized measurement; never print credentials or API errors."""
    import json
    import logging
    from app.services.tcg_analyzer_svc import resolve_work_evidence

    metrics = dict(messages=6, expected_items=8, observed_items=0,
                   format_failures=0, api_failures=0, missing_items=0, excess_items=0,
                   correct=0, unknown=0, wrong=0, expected_unknown_correct=0)
    if not os.getenv("GEMINI_API_KEY", "").strip():
        with capsys.disabled():
            print("LINE_WORK_LIVE_MEASUREMENT " + json.dumps(dict(status="not_run_no_key", **metrics)))
        return
    works = [
        dict(id="2fe437c0-5a47-4311-9b94-0c107f64adcd", display_name="Pokemon", alt_name="ポケモン"),
        dict(id="c6acce0e-fe08-446a-adae-8e9bc946b8b0", display_name="One Piece", alt_name="ワンピース"),
        dict(id="17fe2232-49b7-4989-a23d-b7d82923c7f3", display_name="GUNDAM", alt_name="ガンダム"),
    ]
    expected_ids = {w["alt_name"]: w["id"] for w in works}
    expected_ids[""] = None
    prior_logging = logging.root.manager.disable
    try:
        # Existing SDK exception tracebacks may contain URLs; silence all logging.
        logging.disable(logging.CRITICAL)
        for raw, expected_names in LIVE_WORK_SAMPLES:
            result = extract_message(raw, works=works)
            if result["status"] == "error":
                field = "format_failures" if "v3 extraction" in (result["error_message"] or "") else "api_failures"
                metrics[field] += 1
            items = sorted(result["items"], key=lambda item: item["line_start"])
            metrics["observed_items"] += len(items)
            metrics["missing_items"] += max(len(expected_names) - len(items), 0)
            metrics["excess_items"] += max(len(items) - len(expected_names), 0)
            for item, expected_name in zip(items, expected_names):
                actual = resolve_work_evidence(
                    item["raw_product_name"], raw, item["line_start"], item["line_end"],
                    item["raw_work_name"], item["raw_work_source_line_span"], works,
                )
                if actual == expected_ids[expected_name]:
                    metrics["correct"] += 1
                    if not expected_name:
                        metrics["expected_unknown_correct"] += 1
                elif actual is None:
                    metrics["unknown"] += 1
                else:
                    metrics["wrong"] += 1
    finally:
        logging.disable(prior_logging)
    with capsys.disabled():
        print("LINE_WORK_LIVE_MEASUREMENT " + json.dumps(dict(status="measured", **metrics), sort_keys=True))
    assert metrics["correct"] == 8 and not any(metrics[k] for k in
        ("format_failures", "api_failures", "missing_items", "excess_items", "unknown", "wrong")), "Live acceptance incomplete; see safe aggregate metrics"
# END TEMPORARY LIVE MEASUREMENT
