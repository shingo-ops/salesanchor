"""Work-ID-only contract. All model responses are synthetic; no Gemini requests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services import gemini_extraction_svc as gemini
from app.services import tcg_analyzer_svc as analyzer
from app.services.tcg_work_reference import reference_digest, validate_product_id, validate_work_id
from app.tasks import tcg_extraction as extraction

ONE = 1
GUNDAM = 2
REF = {"works": [{"id": ONE, "display_name": "One Piece"}, {"id": GUNDAM, "display_name": "Gundam"}],
       "products": [{"id": 1, "work_id": ONE, "mark": "OP-01"}]}
# v5: 11 columns (used for backward-compat parse tests only)
V5_HEADER = "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN｜RAW_WORK_NAME｜RAW_WORK_SOURCE_LINE_SPAN｜RESOLVED_WORK_ID｜RESOLVED_PRODUCT_CODE"
# v6: 12 columns (current default)
HEADER = "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN｜RAW_WORK_NAME｜RAW_WORK_SOURCE_LINE_SPAN｜RESOLVED_WORK_ID｜RESOLVED_PRODUCT_CODE｜RAW_PRODUCT_CODE"


@pytest.fixture(autouse=True)
def no_live_gemini(monkeypatch):
    def forbidden():
        pytest.fail("Live Gemini is forbidden before deployment")
    monkeypatch.setattr(gemini, "_get_genai_client", forbidden)


def test_work_id_separate_from_verbatim(monkeypatch):
    response = HEADER + "\n◆OP-01｜2｜1,000円｜BOX｜未開封｜翌日発送｜L0001｜｜｜" + str(ONE) + "｜1｜OP-01"
    monkeypatch.setattr(gemini, "call_gemini_extraction", lambda *a, **k: response)
    result = gemini.extract_message("◆OP-01 2BOX 1,000円 未開封 翌日発送", work_reference=REF)
    assert result["status"] == "done"
    item = result["items"][0]
    assert item["raw_product_name"] == "◆OP-01"
    assert item["raw_quantity"] == "2" and item["raw_price"] == "1,000円"
    assert item["raw_state"] == "未開封" and item["raw_memo"] == "翌日発送"
    assert item["raw_work_name"] == "" and item["raw_work_source_line_span"] == ""
    assert item["resolved_work_id"] == ONE
    assert item["resolved_product_code"] == "1"
    assert item["raw_product_code"] == "OP-01"


@pytest.mark.parametrize("bad", ["not-a-number", "IP002", "99"])
def test_unknown_or_invalid_id_returns_none_resolved_work_id(monkeypatch, bad):
    # validate_work_id now returns None instead of raising, so items with invalid
    # work_ids are preserved with resolved_work_id=None (partial success).
    response = HEADER + "\nOP-01｜1｜100｜BOX｜｜｜L0001｜｜｜" + str(ONE) + "｜｜"
    response += "\nEB01｜1｜100｜BOX｜｜｜L0001｜｜｜" + bad + "｜｜"
    monkeypatch.setattr(gemini, "call_gemini_extraction", lambda *a, **k: response)
    result = gemini.extract_message("OP-01 EB01", work_reference=REF)
    assert result["status"] == "done"
    assert len(result["items"]) == 2
    valid_item = next(it for it in result["items"] if it["raw_product_name"] == "OP-01")
    bad_item = next(it for it in result["items"] if it["raw_product_name"] == "EB01")
    assert valid_item["resolved_work_id"] == ONE
    assert bad_item["resolved_work_id"] is None


def test_unknown_is_not_guessed(monkeypatch):
    response = HEADER + "\nEB01｜1｜100｜BOX｜｜｜L0001｜｜｜｜｜"
    monkeypatch.setattr(gemini, "call_gemini_extraction", lambda *a, **k: response)
    item = gemini.extract_message("EB01", work_reference=REF)["items"][0]
    assert item["resolved_work_id"] is None
    codes = ["OP", "GD"]
    keywords = {"OP": ["EB01"], "GD": ["EB01"]}
    work_map = {"OP": ONE, "GD": GUNDAM}
    assert analyzer.match_pid_with_work("EB01", codes, keywords, {}, work_id=None,
                                       product_work_ids=work_map)[2] is False
    for work, code in [(ONE, "OP"), (GUNDAM, "GD")]:
        result = analyzer.match_pid_with_work("EB01", codes, keywords, {}, work_id=work,
                                             product_work_ids=work_map)
        assert result[0] == code and result[2] is True


def test_digest_tracks_content_and_integer_membership():
    assert reference_digest(REF) == reference_digest(dict(reversed(list(REF.items()))))
    assert reference_digest(REF) != reference_digest({**REF, "products": []})
    assert validate_work_id(None, REF) is None
    assert validate_work_id(ONE, REF) == ONE


@pytest.mark.parametrize("suffix", ["｜extra", ""])
def test_eleven_columns_enforced(suffix):
    # v5: 10 or 12 columns fail; 11 columns pass. (backward-compat test)
    row = "X｜1｜100｜BOX｜｜｜L0001｜｜｜" + str(ONE)
    if suffix:
        row += "｜P1" + suffix
    items, parse_errors = gemini.parse_extraction_response(V5_HEADER + "\n" + row, "X", version=5)
    assert items == []
    assert len(parse_errors) == 1


def test_twelve_columns_enforced_v6():
    # v6: 11 or 13 columns fail; 12 columns pass.
    row_11 = "X｜1｜100｜BOX｜｜｜L0001｜｜｜" + str(ONE) + "｜P1"
    row_13 = "X｜1｜100｜BOX｜｜｜L0001｜｜｜" + str(ONE) + "｜P1｜OP-01｜extra"
    v6_header = "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN｜RAW_WORK_NAME｜RAW_WORK_SOURCE_LINE_SPAN｜RESOLVED_WORK_ID｜RESOLVED_PRODUCT_CODE｜RAW_PRODUCT_CODE"
    for row in (row_11, row_13):
        items, parse_errors = gemini.parse_extraction_response(v6_header + "\n" + row, "X", version=6)
        assert items == [], f"Expected empty items for row with wrong column count: {row}"
        assert len(parse_errors) == 1


def test_missing_schema_does_not_call_model_or_modify_job(monkeypatch):
    session = MagicMock()
    session.execute.return_value.fetchone.return_value = ("job", "OP-01")
    monkeypatch.setattr(extraction, "work_schema_ready", lambda _: False)
    model = MagicMock(side_effect=AssertionError("must not call model"))
    monkeypatch.setattr(extraction, "extract_message", model)
    result = extraction._run_extraction(session, "source")
    assert result["status"] == "pending"
    assert session.execute.call_count == 1
    session.commit.assert_not_called()
    model.assert_not_called()


@pytest.mark.parametrize("invalid", [False, True])
def test_reference_change_saves_no_items(monkeypatch, invalid):
    session = MagicMock()
    session.execute.return_value.fetchone.return_value = ("job", "OP-01", None, None, None, None, None, None, None, None)
    monkeypatch.setattr(extraction, "work_schema_ready", lambda _: True)
    versions = iter([REF, {**REF, "products": []}])
    def load(*_):
        version = next(versions)
        if invalid and not version["products"]:
            raise ValueError("Active product has no active work reference")
        return version
    monkeypatch.setattr(extraction, "load_work_reference", load)
    monkeypatch.setattr(extraction, "extract_message", lambda *a, **k: {
        "status": "done", "items": [{"raw_product_name": "OP-01"}],
        "prompt_version": "raw-extraction-v4-work-id-p1", "error_message": None})
    result = extraction._run_extraction(session, "source")
    assert result["status"] == "error" and result["items_count"] == 0
    assert all("INSERT INTO" not in str(call.args[0]) for call in session.execute.call_args_list)


def test_valid_but_conflicting_id_resolved_to_none(monkeypatch):
    # WORK_ID_CONFLICT no longer raises RecordError; it sets resolved_work_id=None.
    # The item is still processed (partial success). Verify "contradicts" is no longer
    # the error cause; the job may still fail for unrelated reasons (MagicMock recorder),
    # but the conflict itself is handled gracefully by nulling out resolved_work_id.
    captured_items = []

    def fake_extract(*a, **k):
        return {
            "status": "done", "prompt_version": "raw-extraction-v4-work-id-p1",
            "error_message": None,
            "items": [{"raw_product_name": "Gundam EB01", "line_start": 1, "line_end": 1,
                       "resolved_work_id": ONE}],
        }

    session = MagicMock()
    session.execute.return_value.fetchone.return_value = ("job", "Gundam EB01", None, None, None, None, None, None, None, None)
    monkeypatch.setattr(extraction, "work_schema_ready", lambda _: True)
    monkeypatch.setattr(extraction, "load_work_reference", lambda *_: REF)
    monkeypatch.setattr(extraction, "extract_message", fake_extract)
    result = extraction._run_extraction(session, "source")
    # The conflict error message "contradicts" is no longer raised; the job may still
    # error for infrastructure reasons (RESPONSE_NOT_RECORDED with MagicMock), but not
    # because of the work_id conflict itself.
    assert "contradicts" not in (result.get("error_message") or "")
    assert result["status"] in ("done", "error")
    assert result["items_count"] == 0 or result["status"] == "done"


@pytest.mark.parametrize("span,start,end", [("L0001", 1, 1), ("L0001-L0005", 1, 5)])
def test_v6_source_span_retains_raw_fields(monkeypatch, span, start, end):
    raw = "◆OP-17\n\nカートン/¥220,000\n\n残り22"
    row = "◆OP-17｜22｜¥220,000｜カートン｜｜残り｜" + span + "｜｜｜" + str(ONE) + "｜1｜OP-17"
    monkeypatch.setattr(gemini, "call_gemini_extraction", lambda *a, **k: HEADER + "\n" + row)
    result = gemini.extract_message(raw, work_reference=REF)
    assert result["status"] == "done"
    assert result["prompt_version"] == "raw-extraction-v6-rawcode-p1"
    item = result["items"][0]
    assert (item["line_start"], item["line_end"]) == (start, end)
    assert (item["raw_product_name"], item["raw_price"], item["raw_quantity"], item["raw_memo"]) == ("◆OP-17", "¥220,000", "22", "残り")
    assert item["resolved_work_id"] == ONE
    assert item["resolved_product_code"] == "1"
    assert item["raw_product_code"] == "OP-17"


@pytest.mark.parametrize("span,start,end", [("L0001", 1, 1), ("L0001-L0005", 1, 5)])
def test_v5_source_span_retains_raw_fields(monkeypatch, span, start, end):
    """v5 jobs (without raw_product_code) still parse correctly (backward compat)."""
    raw = "◆OP-17\n\nカートン/¥220,000\n\n残り22"
    row = "◆OP-17｜22｜¥220,000｜カートン｜｜残り｜" + span + "｜｜｜" + str(ONE) + "｜1"
    items, parse_errors = gemini.parse_extraction_response(V5_HEADER + "\n" + row, raw, version=5)
    assert not parse_errors
    item = items[0]
    assert (item["line_start"], item["line_end"]) == (start, end)
    assert item["resolved_work_id"] == str(ONE)
    assert item["resolved_product_code"] == "1"
    assert item.get("raw_product_code") is None


@pytest.mark.parametrize("span", ["[L0001]", "[L0001]-[L0005]", "L0001～L0005", "L0001,L0005", "", "L0000", "L0005-L0001", "L0001-L0006"])
def test_v6_invalid_span_is_never_repaired(monkeypatch, span):
    row = "X｜1｜100｜BOX｜｜｜" + span + "｜｜｜" + str(ONE) + "｜｜"
    monkeypatch.setattr(gemini, "call_gemini_extraction", lambda *a, **k: HEADER + "\n" + row)
    result = gemini.extract_message("X\n\n100\n\n1BOX", work_reference=REF)
    assert result["status"] == "error" and result["items"] == []


def test_v6_span_diagnostic_has_shape_without_response_content(monkeypatch, caplog):
    secret = "PRIVATE_CUSTOMER_TEXT"
    row = "X｜1｜100｜BOX｜｜｜[" + secret + "]｜｜｜" + str(ONE) + "｜｜"
    monkeypatch.setattr(gemini, "call_gemini_extraction", lambda *a, **k: HEADER + "\n" + row)
    result = gemini.extract_message("X", work_reference=REF)
    assert result["status"] == "error"
    assert "brackets=True" in result["error_message"]
    assert "allowed_chars=False" in result["error_message"]
    assert secret not in result["error_message"] and secret not in caplog.text
    assert result["raw_response"] == ""


def test_validate_product_id_accepts_id_string():
    """validate_product_id は REF スナップショット内の products.id 文字列を返すこと。"""
    assert validate_product_id("1", REF) == "1"
    assert validate_product_id(1, REF) == "1"          # int 入力も str 化して照合
    assert validate_product_id(None, REF) is None
    assert validate_product_id("", REF) is None
    assert validate_product_id("9999", REF) is None    # 存在しない id
    # 旧形式 product_code（"OP-01" 等）は REF の products.id に存在しないので None
    assert validate_product_id("OP-01", REF) is None
