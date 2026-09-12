"""Work-ID-only contract. All model responses are synthetic; no Gemini requests."""
from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services import gemini_extraction_svc as gemini
from app.services import tcg_analyzer_svc as analyzer
from app.services.tcg_work_reference import reference_digest, validate_work_id
from app.tasks import tcg_extraction as extraction

ONE = "11111111-1111-4111-8111-111111111111"
GUNDAM = "22222222-2222-4222-8222-222222222222"
REF = {"works": [{"id": ONE, "display_name": "One Piece"}, {"id": GUNDAM, "display_name": "Gundam"}],
       "products": [{"code": "P1", "work_id": ONE, "mark": "OP-01"}]}
HEADER = "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN｜RAW_WORK_NAME｜RAW_WORK_SOURCE_LINE_SPAN｜RESOLVED_WORK_ID"


@pytest.fixture(autouse=True)
def no_live_gemini(monkeypatch):
    def forbidden():
        pytest.fail("Live Gemini is forbidden before deployment")
    monkeypatch.setattr(gemini, "_get_genai_client", forbidden)


def test_work_id_separate_from_verbatim(monkeypatch):
    response = HEADER + "\n◆OP-01｜2｜1,000円｜BOX｜未開封｜翌日発送｜L0001｜｜｜" + ONE
    monkeypatch.setattr(gemini, "call_gemini_extraction", lambda *a, **k: response)
    result = gemini.extract_message("◆OP-01 2BOX 1,000円 未開封 翌日発送", work_reference=REF)
    assert result["status"] == "done"
    item = result["items"][0]
    assert item["raw_product_name"] == "◆OP-01"
    assert item["raw_quantity"] == "2" and item["raw_price"] == "1,000円"
    assert item["raw_state"] == "未開封" and item["raw_memo"] == "翌日発送"
    assert item["raw_work_name"] == "" and item["raw_work_source_line_span"] == ""
    assert item["resolved_work_id"] == ONE


@pytest.mark.parametrize("bad", ["not-a-uuid", str(uuid4()), "IP002"])
def test_unknown_or_invalid_id_rejects_whole_response(monkeypatch, bad):
    response = HEADER + "\nOP-01｜1｜100｜BOX｜｜｜L0001｜｜｜" + ONE
    response += "\nEB01｜1｜100｜BOX｜｜｜L0001｜｜｜" + bad
    monkeypatch.setattr(gemini, "call_gemini_extraction", lambda *a, **k: response)
    result = gemini.extract_message("OP-01 EB01", work_reference=REF)
    assert result["status"] == "error" and result["items"] == []


def test_unknown_is_not_guessed(monkeypatch):
    response = HEADER + "\nEB01｜1｜100｜BOX｜｜｜L0001｜｜｜"
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


def test_digest_tracks_content_and_uuid_membership():
    assert reference_digest(REF) == reference_digest(dict(reversed(list(REF.items()))))
    assert reference_digest(REF) != reference_digest({**REF, "products": []})
    assert validate_work_id(None, REF) is None
    assert validate_work_id(ONE, REF) == ONE


@pytest.mark.parametrize("suffix", ["｜extra", ""])
def test_ten_columns_enforced(suffix):
    # Nine or eleven columns, never ten.
    row = "X｜1｜100｜BOX｜｜｜L0001｜｜"
    if suffix:
        row += "｜" + ONE + suffix
    with pytest.raises(ValueError):
        gemini.parse_extraction_response(HEADER + "\n" + row, "X", version=4)


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
    session.execute.return_value.fetchone.return_value = ("job", "OP-01")
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
