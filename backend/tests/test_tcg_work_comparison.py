"""Synthetic decision responses only; no live LLM calls."""
from copy import deepcopy
from unittest.mock import Mock

import pytest

from app.services import tcg_work_comparison_svc as comparison

ONE = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"
ITEM = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ITEM2 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
SOURCE = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
JOB = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
PRODUCT = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
REF = {"works": [{"id": ONE, "display_name": "One Piece"}, {"id": OTHER, "display_name": "Gundam"}],
       "products": [{"code": "P1", "work_id": ONE, "mark": "EB01"}]}


@pytest.fixture(autouse=True)
def no_live(monkeypatch):
    monkeypatch.setattr(comparison.gemini, "_get_genai_client", Mock(side_effect=AssertionError("Live model forbidden")))


def snapshot():
    data = {
        "import_id": ITEM2,
        "sources": [{"id": SOURCE, "is_active": True, "raw_text": "EB01 1BOX 1000円"}],
        "jobs": [{"id": JOB, "source_message_id": SOURCE, "status": "done", "prompt_version": "raw-extraction-v3-work-p1"}],
        "items": [{"id": ITEM, "extraction_job_id": JOB, "raw_product_name": "EB01", "raw_unit": "BOX",
                   "raw_work_name": "", "raw_work_source_line_span": "", "line_start": 1, "line_end": 1}],
        "analyses": [{"extraction_item_id": ITEM, "product_id": None, "pid_resolved": False}], "corrections": [],
        "reference": deepcopy(REF),
        "context": {"product_ids": {"P1": PRODUCT}, "units": {"BOX": ["BOX", "箱系"]}, "search": {"P1": ["EB01"]},
                    "exclude": {}, "categories": {"P1": "箱系"}, "normalization": {}, "works": REF["works"],
                    "work_ids": {"P1": ONE}, "classes": {"P1": "Box"}},
    }
    return seal(data)


def seal(data):
    return {"data": data, "sha256": comparison.fingerprint(data)}


def mock_read(monkeypatch, snap):
    monkeypatch.setattr(comparison, "read_snapshot", lambda *a: deepcopy(snap))


def test_reordered_ids_and_null_work_are_accepted():
    result = comparison.parse_decisions(comparison.HEADER + f"\n{ITEM2}｜\n{ITEM}｜{ONE}", [ITEM, ITEM2], REF)
    assert result == {ITEM2: None, ITEM: ONE}


@pytest.mark.parametrize("body", [
    "", f"{ITEM}｜{ONE}\n{ITEM}｜{ONE}", f"{ITEM2}｜{ONE}", f"{ITEM}｜{PRODUCT}",
    f"{ITEM}｜not-uuid", f"{ITEM}｜{ONE}｜RAW", f"{ITEM}｜{ONE}\nExplanation", "invalid-id｜",
])
def test_bad_response_rejected(body):
    with pytest.raises(comparison.ComparisonError):
        comparison.parse_decisions(comparison.HEADER + "\n" + body, [ITEM], REF)


@pytest.mark.parametrize("response", ["```\nITEM_ID｜WORK_ID", "ITEM_ID|WORK_ID", "Explanation\nITEM_ID｜WORK_ID"])
def test_bad_header_rejected(response):
    with pytest.raises(comparison.ComparisonError, match="INVALID_HEADER"):
        comparison.parse_decisions(response, [ITEM], REF)


def test_fixed_raw_comparison_cannot_auto_adopt(monkeypatch):
    snap = snapshot()
    original = deepcopy(snap)
    mock_read(monkeypatch, snap)
    model = Mock(return_value=comparison.HEADER + f"\n{ITEM}｜{ONE}")
    report = comparison.compare_snapshot(snap, None, model_call=model)
    assert report["status"] == "comparison_complete_unverified"
    assert report["items"][ITEM]["saved"]["product_id"] is None
    assert report["items"][ITEM]["control"]["product_id"] is None
    assert report["items"][ITEM]["candidate"]["product_id"] == PRODUCT
    assert report["items"][ITEM]["label"] == "unverified"
    assert report["adoptable"] is False and report["db_writes"] == 0
    assert snap == original
    assert '"ITEM_ID"' in model.call_args.args[0]
    assert '"resolved_work_id"' not in model.call_args.args[0]


def test_control_mismatch_stops_before_model(monkeypatch):
    data = snapshot()["data"]
    data["analyses"][0].update(product_id=PRODUCT, pid_resolved=True)
    snap = seal(data)
    mock_read(monkeypatch, snap)
    model = Mock(side_effect=AssertionError("not allowed"))
    report = comparison.compare_snapshot(snap, None, model_call=model)
    assert report["status"] == "control_mismatch" and report["mismatches"] == [ITEM]
    model.assert_not_called()


def test_corrected_items_are_not_sent(monkeypatch):
    data = snapshot()["data"]
    data["corrections"] = [{"extraction_item_id": ITEM}]
    snap = seal(data)
    mock_read(monkeypatch, snap)
    model = Mock(side_effect=AssertionError("not allowed"))
    report = comparison.compare_snapshot(snap, None, model_call=model)
    assert report["corrected_items"] == [ITEM] and not report["items"]
    model.assert_not_called()


def test_changed_snapshot_stops_before_model(monkeypatch):
    snap = snapshot()
    changed = deepcopy(snap)
    changed["data"]["items"][0]["raw_product_name"] = "changed"
    mock_read(monkeypatch, seal(changed["data"]))
    model = Mock()
    with pytest.raises(comparison.ComparisonError, match="INPUT_CHANGED"):
        comparison.compare_snapshot(snap, None, model_call=model)
    model.assert_not_called()


def test_response_error_preserved_privately_without_candidate(monkeypatch, caplog):
    snap = snapshot()
    mock_read(monkeypatch, snap)
    report = comparison.compare_snapshot(snap, None, model_call=lambda _: "PRIVATE_RESPONSE")
    assert report["status"] == "response_rejected"
    assert report["rejected_response"] == "PRIVATE_RESPONSE"
    assert "PRIVATE_RESPONSE" not in caplog.text
    assert report["items"][ITEM]["candidate"] is None and not report["adoptable"]


def test_explicit_conflict_is_not_adopted(monkeypatch):
    data = snapshot()["data"]
    data["items"][0]["raw_product_name"] = "One Piece EB01"
    data["sources"][0]["raw_text"] = "One Piece EB01 1BOX"
    snap = seal(data)
    mock_read(monkeypatch, snap)
    report = comparison.compare_snapshot(snap, None, model_call=lambda _: comparison.HEADER + f"\n{ITEM}｜{OTHER}")
    assert report["status"] == "work_conflict"
    assert report["items"][ITEM]["candidate"] is None


def test_same_names_are_associated_only_by_item_id(monkeypatch):
    data = snapshot()["data"]
    item = deepcopy(data["items"][0]); item["id"] = ITEM2
    data["items"].append(item)
    data["analyses"].append({"extraction_item_id": ITEM2, "product_id": None, "pid_resolved": False})
    snap = seal(data)
    mock_read(monkeypatch, snap)
    report = comparison.compare_snapshot(snap, None, model_call=lambda _: comparison.HEADER + f"\n{ITEM2}｜\n{ITEM}｜{ONE}")
    assert report["items"][ITEM]["candidate"]["product_id"] == PRODUCT
    assert report["items"][ITEM2]["candidate"]["product_id"] is None
