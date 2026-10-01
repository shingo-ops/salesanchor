"""Gemini 書き写し v8（比較試験用）の単体試験。

設計: docs/handoff/gemini-v8/design.md §2・§3・§4・§5
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import app.services.gemini_extraction_svc as gem
import app.services.gemini_raw_copy_v8 as v8

# --- format_prompt_input_v8 ---------------------------------------------------


def test_format_prompt_input_v8_keeps_delimiter_emoji_and_strips_others():
    # Arrange
    raw = "\U0001F4E6商品A\n✅在庫あり\n■見出し"
    # Act
    out = v8.format_prompt_input_v8(raw, {"\U0001F4E6"})
    # Assert
    assert out.split("\n")[0] == "[L0001] \U0001F4E6商品A"
    assert out.split("\n")[1] == "[L0002] 在庫あり"
    assert out.split("\n")[2] == "[L0003] ■見出し"


def test_format_prompt_input_v8_keeps_line_count_and_format_like_v7():
    raw = "a\n\n\U0001F600b\nc"
    out = v8.format_prompt_input_v8(raw, set())
    assert len(out.split("\n")) == len(raw.split("\n"))
    # keep_chars が空なら既存の format_prompt_input と同じ出力になる
    assert out == gem.format_prompt_input(raw)


# --- build_supplier_note_v8 ---------------------------------------------------

_CTX = {
    "extraction_price_format": "税込円",
    "extraction_qty_format": "@の後",
    "extraction_default_unit": "BOX",
    "extraction_notes": "補足",
    "extraction_state_format": "[]内",
    "extraction_order_pattern": json.dumps(["quantity", "unit", "@", "price"]),
    "extraction_example_text": "例文",
}
_LINKS = [
    {"category": "block_delimiter", "pattern": "■", "normalized_to": None},
    {"category": "status_keyword", "pattern": "完売", "normalized_to": "sold_out"},
]


def test_build_supplier_note_v8_omits_default_unit_only():
    note_v8 = v8.build_supplier_note_v8(_CTX, _LINKS)
    only_block = [lnk for lnk in _LINKS if lnk["category"] == "block_delimiter"]
    note_v7 = gem._build_supplier_context_note(_CTX, knowledge_links=only_block)
    assert "デフォルト単位" not in note_v8
    assert "デフォルト単位" in note_v7
    expected = "\n".join(ln for ln in note_v7.split("\n") if "デフォルト単位" not in ln)
    assert note_v8 == expected


def test_build_supplier_note_v8_drops_status_keyword_and_keeps_delimiter():
    note = v8.build_supplier_note_v8(_CTX, _LINKS)
    assert "商品ブロックの区切り記号: ■" in note
    assert "ステータス判定" not in note


def test_build_supplier_note_v8_appends_ship_format_like_v7():
    ctx = {**_CTX, "extraction_ship_format": "M/D"}
    note = v8.build_supplier_note_v8(ctx, _LINKS)
    assert note.endswith("\n- 発送日フォーマット: M/D")
    only_ship = v8.build_supplier_note_v8({"extraction_ship_format": "M/D"}, None)
    assert only_ship == "【仕入元固有の抽出ルール】\n- 発送日フォーマット: M/D"


def test_build_supplier_note_v8_does_not_mutate_input():
    ctx = dict(_CTX)
    v8.build_supplier_note_v8(ctx, _LINKS)
    assert ctx == _CTX


def test_build_supplier_note_v8_empty_context_is_empty():
    assert v8.build_supplier_note_v8({}, None) == ""


def test_keep_chars_from_links_uses_block_delimiter_patterns_only():
    assert v8.keep_chars_from_links(_LINKS) == {"■"}
    assert v8.keep_chars_from_links(None) == set()


# --- parse_v8_response --------------------------------------------------------

_RAW = "\n".join(f"line{i}" for i in range(1, 11))  # 10 行


def _item(start, end, h_start=None, h_end=None, **over):
    base = {
        "product_name": "P", "price": "100円", "unit": "BOX", "quantity": "1", "state": "none",
        "ship": "none", "source_line_start": start, "source_line_end": end,
        "heading_line_start": h_start, "heading_line_end": h_end, "multi_note": "none",
    }
    return {**base, **over}


def _resp(*items):
    return json.dumps({"items": list(items)}, ensure_ascii=False)


def test_parse_v8_response_accepts_valid_items_and_maps_to_v7_keys():
    items, errors = v8.parse_v8_response(_resp(_item(3, 3, 1, 1), _item(5, 6, 1, 1)), _RAW)
    assert errors == []
    assert len(items) == 2
    assert items[0]["raw_product_name"] == "P"
    assert items[0]["raw_price"] == "100円"
    assert items[0]["line_start"] == 3 and items[0]["line_end"] == 3
    assert items[0]["heading_line_start"] == 1 and items[0]["heading_line_end"] == 1


def test_parse_v8_response_null_heading_is_allowed():
    items, errors = v8.parse_v8_response(_resp(_item(3, 3)), _RAW)
    assert errors == []
    assert items[0]["heading_line_start"] is None


@pytest.mark.parametrize("start,end", [(0, 2), (3, 11), (5, 4), (-1, 1)])
def test_parse_v8_response_detects_out_of_range(start, end):
    items, errors = v8.parse_v8_response(_resp(_item(start, end)), _RAW)
    assert items == []
    assert len(errors) == 1
    assert errors[0]["index"] == 0
    assert "範囲" in errors[0]["error"]


def test_parse_v8_response_detects_overlap_with_own_heading():
    items, errors = v8.parse_v8_response(_resp(_item(2, 4, 2, 2)), _RAW)
    assert items == []
    assert "見出し" in errors[0]["error"]


def test_parse_v8_response_detects_overlap_with_other_items_heading():
    items, errors = v8.parse_v8_response(_resp(_item(3, 3, 1, 1), _item(1, 2, None, None)), _RAW)
    assert len(items) == 1
    assert errors[0]["index"] == 1
    assert "見出し" in errors[0]["error"]


def test_parse_v8_response_detects_overlap_with_other_item():
    items, errors = v8.parse_v8_response(_resp(_item(3, 5), _item(5, 6)), _RAW)
    assert len(items) == 1
    assert errors[0]["index"] == 1
    assert "重なり" in errors[0]["error"]


def test_parse_v8_response_detects_missing_required_field():
    bad = _item(3, 3)
    del bad["price"]
    items, errors = v8.parse_v8_response(_resp(bad, _item(4, 4)), _RAW)
    assert len(items) == 1
    assert errors[0]["index"] == 0
    assert "price" in errors[0]["error"]


def test_parse_v8_response_detects_wrong_type():
    items, errors = v8.parse_v8_response(_resp(_item("3", 3)), _RAW)
    assert items == []
    assert "source_line_start" in errors[0]["error"]


def test_parse_v8_response_broken_json_is_single_whole_error():
    items, errors = v8.parse_v8_response("{not json", _RAW)
    assert items == []
    assert len(errors) == 1
    assert errors[0]["index"] is None
    assert "JSON" in errors[0]["error"]


def test_parse_v8_response_without_items_array_is_whole_error():
    items, errors = v8.parse_v8_response('{"foo": 1}', _RAW)
    assert items == []
    assert len(errors) == 1 and errors[0]["index"] is None


# --- call_gemini_raw_copy_v8 --------------------------------------------------


def _fake_response(parts, usage=None):
    cand = SimpleNamespace(content=SimpleNamespace(parts=parts))
    return SimpleNamespace(
        candidates=[cand], text="".join(p.text for p in parts if not p.thought), usage_metadata=usage
    )


def _usage():
    return SimpleNamespace(
        prompt_token_count=100, candidates_token_count=20, thoughts_token_count=7,
        total_token_count=127, cached_content_token_count=None, tool_use_prompt_token_count=None,
        model_dump=lambda **kw: {"prompt_token_count": 100, "thoughts_token_count": 7},
    )


@pytest.fixture
def client(monkeypatch):
    cli = MagicMock()
    parts = [
        SimpleNamespace(text="考え中の要約", thought=True),
        SimpleNamespace(text='{"items": []}', thought=False),
    ]
    cli.models.generate_content.return_value = _fake_response(parts, _usage())
    monkeypatch.setattr(gem, "_get_genai_client", lambda: cli)
    return cli


def _call(**over):
    kw = dict(
        prompt_text="PROMPT", supplier_context=_CTX, knowledge_links=_LINKS,
        thinking_level="LOW", include_thoughts=True, use_schema=True, temperature=None,
    )
    kw.update(over)
    return v8.call_gemini_raw_copy_v8("a\nb", **kw)


def test_call_v8_config_omits_temperature_and_sets_schema_and_thinking(client):
    _call()
    cfg = client.models.generate_content.call_args.kwargs["config"]
    assert cfg.temperature is None
    assert cfg.response_mime_type == "application/json"
    assert cfg.response_json_schema == v8.V8_RESPONSE_SCHEMA
    assert cfg.thinking_config.include_thoughts is True
    assert cfg.thinking_config.thinking_level.value == "LOW"


def test_call_v8_config_passes_temperature_when_given(client):
    _call(temperature=0.5)
    assert client.models.generate_content.call_args.kwargs["config"].temperature == 0.5


def test_call_v8_without_schema_and_level(client):
    _call(use_schema=False, thinking_level=None, include_thoughts=False)
    cfg = client.models.generate_content.call_args.kwargs["config"]
    assert cfg.response_mime_type is None
    assert cfg.response_json_schema is None
    assert cfg.thinking_config.thinking_level is None
    assert cfg.thinking_config.include_thoughts is False


def test_call_v8_separates_thought_parts_from_response_text(client):
    out = _call()
    assert out["response_text"] == '{"items": []}'
    assert out["thought_summaries"] == ["考え中の要約"]


def test_call_v8_returns_usage_raw_and_counts(client):
    out = _call()
    assert out["usage_raw"]["thoughts_token_count"] == 7
    assert out["usage_counts"].prompt_tokens == 100
    assert out["usage_counts"].thoughts_tokens == 7


def test_call_v8_prompt_contains_note_without_default_unit_and_numbered_input(client):
    _call()
    contents = client.models.generate_content.call_args.kwargs["contents"]
    assert contents.startswith("PROMPT")
    assert "デフォルト単位" not in contents
    assert "[L0001] a" in contents and "[L0002] b" in contents
    assert client.models.generate_content.call_args.kwargs["model"] == gem._GEMINI_MODEL


def test_call_v8_api_failure_raises_runtime_error(client):
    client.models.generate_content.side_effect = Exception("boom")
    with pytest.raises(RuntimeError):
        _call()


def test_usage_raw_falls_back_to_listing_missing_attrs_when_not_dumpable():
    usage = SimpleNamespace(prompt_token_count=5)
    raw = v8.usage_to_dict(usage)
    assert raw["prompt_token_count"] == 5
    assert "thoughts_token_count" in raw["_missing_attrs"]


def test_prompt_file_exists_and_has_placeholders_free_text():
    text = v8.load_v8_prompt()
    assert "書き写し担当" in text
    assert "source_line_start" in text
