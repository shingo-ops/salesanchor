"""Synthetic decision responses only; no live LLM calls."""
from copy import deepcopy
from unittest.mock import Mock

import pytest

from app.services import tcg_work_comparison_svc as comparison
from app.services.tcg_work_reference import reference_digest as _rdigest

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


def mock_job_read(monkeypatch, snap):
    monkeypatch.setattr(comparison, "read_job_snapshot", lambda *a: deepcopy(snap))


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


@pytest.fixture
def lifetime_client(monkeypatch):
    """Record state without retaining Client, like the real SDK's Models object."""
    states = []
    settings = {"text": "ITEM_ID｜WORK_ID", "fail_at": None}

    class Response:
        def __init__(self, state):
            self.state = state

        @property
        def text(self):
            assert not self.state["closed"], "client closed before text was read"
            self.state["events"].append("text")
            if settings["fail_at"] == "text":
                raise ValueError("synthetic failure")
            return settings["text"]

    class Models:
        def __init__(self, state):
            self.state = state

        def generate_content(self, **kwargs):
            if self.state["closed"]:
                raise RuntimeError("closed_before_call")
            self.state["arguments"] = kwargs
            self.state["events"].append("generate")
            if settings["fail_at"] == "generate":
                raise ValueError("synthetic failure")
            return Response(self.state)

    class Client:
        def __init__(self, state):
            self.state = state
            self.models = Models(state)

        def close(self):
            if not self.state["closed"]:
                self.state["closed"] = True
                self.state["events"].append("close")

        def __del__(self):
            self.close()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    def factory():
        state = {"closed": False, "events": []}
        states.append(state)
        return Client(state)

    monkeypatch.setattr(comparison.gemini, "_get_genai_client", factory)
    return settings, states, factory


def test_client_fixture_detects_unretained_client(lifetime_client):
    _, states, factory = lifetime_client
    # This is the old adapter expression: the fake must detect its early close.
    with pytest.raises(RuntimeError, match="closed_before_call"):
        factory().models.generate_content()
    assert states[0]["events"] == ["close"]


@pytest.mark.parametrize("value", ["ITEM_ID｜WORK_ID", "", None])
def test_work_model_keeps_client_alive_until_text_read(lifetime_client, value):
    settings, states, _ = lifetime_client
    settings["text"] = value
    assert comparison.call_work_model("synthetic prompt") == (value or "")
    assert len(states) == 1
    state = states[0]
    assert state["closed"] and state["events"] == ["generate", "text", "close"]
    assert state["arguments"]["model"] == comparison.gemini._GEMINI_MODEL
    assert state["arguments"]["contents"] == "synthetic prompt"
    assert state["arguments"]["config"].temperature == 0


@pytest.mark.parametrize("stage", ["generate", "text"])
def test_work_model_closes_client_and_propagates_errors(lifetime_client, stage):
    settings, states, _ = lifetime_client
    settings["fail_at"] = stage
    with pytest.raises(ValueError, match="synthetic failure"):
        comparison.call_work_model("synthetic prompt")
    assert len(states) == 1 and states[0]["closed"]
    expected = ["generate", "close"] if stage == "generate" else ["generate", "text", "close"]
    assert states[0]["events"] == expected


# ---------------------------------------------------------------------------
# §25-3/25-4 A便 stale job comparison (9 groups)
# ---------------------------------------------------------------------------

STALE_PV = "raw-extraction-v4-work-id-p1"
# Nine distinct IDs that do not conflict with existing constants
ITEM_IDS = [f"00000000-0000-4000-8000-00000000000{i}" for i in range(1, 10)]


def job_snap(n_items: int = 1, resolved_work_id: str | None = ONE,
             corrupt_saved_sha: bool = False) -> dict:
    """Build a synthetic stale-job snapshot for compare_stale_job_snapshot tests."""
    saved_ref = deepcopy(REF)
    saved_sha = "0" * 64 if corrupt_saved_sha else _rdigest(saved_ref)
    items = [
        {"id": ITEM_IDS[i], "extraction_job_id": JOB, "raw_product_name": "EB01",
         "raw_unit": "BOX", "raw_work_name": "", "raw_work_source_line_span": "",
         "line_start": 1, "line_end": 1, "resolved_work_id": resolved_work_id}
        for i in range(n_items)
    ]
    analyses = [{"extraction_item_id": it["id"], "product_id": None, "pid_resolved": False}
                for it in items]
    job_record = {
        "id": JOB, "source_message_id": SOURCE, "status": "done",
        "prompt_version": STALE_PV,
        "work_reference_snapshot": saved_ref,
        "work_reference_sha256": saved_sha,
    }
    current_ref = deepcopy(REF)
    data = {
        "job_id": JOB,
        "job": job_record,
        "source": {"id": SOURCE, "is_active": True, "raw_text": "EB01 1BOX 1000円"},
        "items": items,
        "analyses": analyses,
        "masters": {},
        "context": {
            "product_ids": {"P1": PRODUCT}, "units": {"BOX": ["BOX", "箱系"]},
            "search": {"P1": ["EB01"]}, "exclude": {}, "categories": {"P1": "箱系"},
            "normalization": {}, "works": REF["works"],
            "work_ids": {"P1": ONE}, "classes": {"P1": "Box"},
        },
        "reference": current_ref,
        "saved_reference": saved_ref,
        "reference_diff": {
            "saved_sha256": saved_sha,
            "current_sha256": _rdigest(current_ref),
            "changed": False,
        },
    }
    return {"data": data, "sha256": comparison.fingerprint(data)}


# ① done job with 7 items → 7 candidates, non-adoptable, snapshot preserved
def test_stale_seven_items_all_candidates_created(monkeypatch):
    snap = job_snap(n_items=7)
    mock_job_read(monkeypatch, snap)
    original = deepcopy(snap)
    ids = [i["id"] for i in snap["data"]["items"]]
    model = Mock(return_value=comparison.HEADER + "\n" + "\n".join(f"{iid}｜{ONE}" for iid in ids))
    report = comparison.compare_stale_job_snapshot(snap, None, model_call=model)
    assert report["status"] == "comparison_complete_unverified"
    assert len(report["results"]) == 7
    assert report["model_calls"] == 1 and report["db_writes"] == 0
    assert report["adoptable"] is False
    for iid in ids:
        assert report["results"][iid]["candidate"] is not None
        assert report["results"][iid]["label"] == "unverified"
    assert snap == original  # snapshot not mutated


# ② old entry (compare_snapshot) still rejects a changed reference
def test_old_entry_rejects_changed_reference(monkeypatch):
    saved_ref = deepcopy(REF)
    saved_sha = _rdigest(saved_ref)
    different_ref = {
        "works": [{"id": OTHER, "display_name": "Gundam"}],
        "products": [{"code": "P1", "work_id": OTHER, "mark": "G1"}],
    }
    data = {
        "import_id": ITEM2,
        "sources": [{"id": SOURCE, "is_active": True, "raw_text": "EB01 1BOX 1000円"}],
        "jobs": [{"id": JOB, "source_message_id": SOURCE, "status": "done",
                  "prompt_version": STALE_PV,
                  "work_reference_snapshot": saved_ref,
                  "work_reference_sha256": saved_sha}],
        "items": [{"id": ITEM, "extraction_job_id": JOB, "raw_product_name": "EB01",
                   "raw_unit": "BOX", "raw_work_name": "", "raw_work_source_line_span": "",
                   "line_start": 1, "line_end": 1}],
        "analyses": [{"extraction_item_id": ITEM, "product_id": None, "pid_resolved": False}],
        "corrections": [],
        "reference": different_ref,
        "context": {
            "product_ids": {"P1": PRODUCT}, "units": {"BOX": ["BOX", "箱系"]},
            "search": {"P1": ["EB01"]}, "exclude": {}, "categories": {"P1": "箱系"},
            "normalization": {}, "works": saved_ref["works"],
            "work_ids": {"P1": ONE}, "classes": {"P1": "Box"},
        },
    }
    snap = seal(data)
    mock_read(monkeypatch, snap)
    model = Mock(side_effect=AssertionError("must not call"))
    with pytest.raises(comparison.ComparisonError, match="INVALID_SAVED_REFERENCE"):
        comparison.compare_snapshot(snap, None, model_call=model)
    model.assert_not_called()


# ③ corrupted fingerprint → SNAPSHOT_CORRUPTED before model (before unchanged())
def test_stale_corrupted_fingerprint_stops_before_model():
    snap = job_snap()
    snap["sha256"] = "0" * 64
    model = Mock(side_effect=AssertionError("must not call"))
    with pytest.raises(comparison.ComparisonError, match="SNAPSHOT_CORRUPTED"):
        comparison.compare_stale_job_snapshot(snap, None, model_call=model)
    model.assert_not_called()


# ③ corrupt saved SHA → INVALID_SAVED_REFERENCE (detected after unchanged() passes)
def test_stale_invalid_saved_reference_stops_before_model(monkeypatch):
    snap = job_snap(corrupt_saved_sha=True)
    mock_job_read(monkeypatch, snap)
    model = Mock(side_effect=AssertionError("must not call"))
    with pytest.raises(comparison.ComparisonError, match="INVALID_SAVED_REFERENCE"):
        comparison.compare_stale_job_snapshot(snap, None, model_call=model)
    model.assert_not_called()


# ④ bad model responses → response_rejected, not adopted
@pytest.mark.parametrize("bad_response", [
    "no header at all",
    comparison.HEADER + "\nextra｜｜third_column",
    comparison.HEADER,
    comparison.HEADER + "\nnot-a-uuid｜",
])
def test_stale_bad_response_is_rejected(bad_response, monkeypatch):
    snap = job_snap()
    mock_job_read(monkeypatch, snap)
    report = comparison.compare_stale_job_snapshot(snap, None, model_call=lambda _: bad_response)
    assert report["status"] == "response_rejected"
    assert report["adoptable"] is False and report["db_writes"] == 0
    assert report["results"][ITEM_IDS[0]]["candidate"] is None


# ⑤ snapshot data mutated during model call → SNAPSHOT_CORRUPTED post-call
def test_stale_mutation_after_model_call_stops(monkeypatch):
    snap = job_snap()
    mock_job_read(monkeypatch, snap)
    data = snap["data"]

    def corrupt_model(prompt):
        data["items"][0]["raw_product_name"] = "mutated"
        return comparison.HEADER + f"\n{data['items'][0]['id']}｜{ONE}"

    with pytest.raises(comparison.ComparisonError, match="SNAPSHOT_CORRUPTED"):
        comparison.compare_stale_job_snapshot(snap, None, model_call=corrupt_model)


# ⑥ model raises → MODEL_CALL_FAILED, exactly one call, no retry
def test_stale_model_exception_stops_without_retry(monkeypatch):
    call_count = [0]

    def failing_model(_prompt):
        call_count[0] += 1
        raise RuntimeError("synthetic failure")

    snap = job_snap()
    mock_job_read(monkeypatch, snap)
    with pytest.raises(comparison.ComparisonError, match="MODEL_CALL_FAILED"):
        comparison.compare_stale_job_snapshot(snap, None, model_call=failing_model)
    assert call_count[0] == 1


# ⑧ model payload carries fixed ITEM_ID + raw fields; resolved_work_id excluded
def test_stale_payload_excludes_resolved_work_id(monkeypatch):
    snap = job_snap(resolved_work_id=ONE)
    mock_job_read(monkeypatch, snap)
    captured: dict = {}

    def capture_model(prompt):
        import json
        payload = json.loads(prompt[len(comparison.PROMPT):])
        captured["payload"] = payload
        iid = snap["data"]["items"][0]["id"]
        return comparison.HEADER + f"\n{iid}｜{ONE}"

    comparison.compare_stale_job_snapshot(snap, None, model_call=capture_model)
    fixed = captured["payload"]["items"][0]
    assert "ITEM_ID" in fixed
    assert "resolved_work_id" not in fixed
    assert all(k.startswith("raw_") or k in {"ITEM_ID", "line_start", "line_end"} for k in fixed)


# No model_call → snapshot_ready, nothing adopted
def test_stale_no_model_returns_snapshot_ready(monkeypatch):
    snap = job_snap()
    mock_job_read(monkeypatch, snap)
    report = comparison.compare_stale_job_snapshot(snap, None)
    assert report["status"] == "snapshot_ready"
    assert report["model_calls"] == 0 and report["db_writes"] == 0 and report["adoptable"] is False
    assert report["results"][ITEM_IDS[0]]["candidate"] is None


# Over 7 items → TOO_MANY_ITEMS before unchanged()
def test_stale_over_seven_items_rejected():
    snap = job_snap(n_items=8)
    model = Mock(side_effect=AssertionError("must not call"))
    with pytest.raises(comparison.ComparisonError, match="TOO_MANY_ITEMS"):
        comparison.compare_stale_job_snapshot(snap, None, model_call=model)
    model.assert_not_called()


# Work conflict → work_conflict, no candidate set
def test_stale_work_conflict_stops_without_candidate(monkeypatch):
    data = job_snap()["data"]
    data["items"][0]["raw_product_name"] = "One Piece EB01"
    data["source"]["raw_text"] = "One Piece EB01 1BOX"
    data["context"]["works"] = [{"id": ONE, "display_name": "One Piece"}]
    snap = {"data": data, "sha256": comparison.fingerprint(data)}
    mock_job_read(monkeypatch, snap)
    iid = snap["data"]["items"][0]["id"]
    report = comparison.compare_stale_job_snapshot(
        snap, None, model_call=lambda _: comparison.HEADER + f"\n{iid}｜{OTHER}")
    assert report["status"] == "work_conflict"
    assert report["results"][iid]["candidate"] is None
