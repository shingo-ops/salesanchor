"""replay_master_addition の単体テスト（DB 非依存。中核 evaluate と純粋関数を検証する）。

設計: docs/handoff/buyback-master-addition/design.md
"""
from __future__ import annotations

from unittest.mock import MagicMock

from app.services.extraction_judgement_svc import ProductEntry
from scripts import replay_master_addition as replay

WORK_A = 10
WORK_B = 99
EXISTING_ID = 1
RAW_UNRELATED = "全然関係ない商品 ABC\n価格 100円"


def _legacy_context(*, search=None, exclude=None, work_id=WORK_A):
    search = search if search is not None else {"1": ["ピカチュウ"]}
    return {
        "product_ids": {pid: int(pid) for pid in search},
        "units": {}, "search": search, "exclude": exclude or {}, "categories": {},
        "normalization": {}, "work_ids": {pid: str(work_id) for pid in search}, "classes": {},
    }


def _entries(search=("ピカチュウ",)):
    return [ProductEntry(id=EXISTING_ID, product_code=None, mark=None, work_id=WORK_A,
                         search_keywords=tuple(search), exclude_keywords=())]


def _candidate(*, title="昔の商品", keywords=("ゲンガー",), work_id=WORK_A, mark="", exclude=()):
    row = {"row_no": "1", "japanese_title": title, "english_title": "", "mark": mark, "work_code": "PKM",
           "product_category_code": "BOX", "search_keywords": ",".join(keywords),
           "exclude_keywords": ",".join(exclude)}
    work_map = {} if work_id is None else {"PKM": work_id}
    return replay.build_candidates([row], work_map, {"BOX": "Box"})


def _inputs(*, raw_text="ピカチュウ ex 1BOX 5000円", search=None, entries=None, shadow_text=None, work_id=WORK_A):
    item = {"id": "item-1", "line_start": 1, "line_end": 1, "raw_product_name": "ピカチュウ",
            "raw_unit": "", "raw_state": "", "raw_memo": "", "raw_work_name": None,
            "raw_work_span": None, "raw_work_source_line_span": None, "resolved_work_id": work_id,
            "source_id": "src-1"}
    block = {"id": "src-1:1-1", "text": raw_text}
    return {
        "legacy_context": _legacy_context(search=search), "valid_work_ids": {WORK_A},
        "entries": entries if entries is not None else _entries(), "works": [],
        "items": [item], "raw_texts": {"src-1": raw_text}, "message_blocks": [block],
        "shadow_blocks": [{"id": "shadow-1", "text": shadow_text if shadow_text is not None else raw_text}],
    }


def _run(candidates, inputs, file_errors=()):
    return replay.evaluate(candidates=candidates, file_errors=file_errors, days=90, inputs=inputs)


class TestCaseAUnrelatedCandidate:
    def test_unrelated_candidate_changes_nothing_and_exits_zero(self):
        # Arrange
        candidates = _candidate(keywords=("ゲンガー",))
        # Act
        report = _run(candidates, _inputs())
        # Assert
        assert report["gate_counts"] == {
            "gate1": 0, "legacy_gate2": 0, "legacy_gate3": 0,
            "new_gate2_shadow_results_pre_maintenance": 0, "new_gate2_raw_message_blocks": 0, "new_gate3": 0,
        }
        assert report["exit_code"] == 0


class TestCaseBSharedKeyword:
    def test_candidate_sharing_existing_keyword_is_detected_in_gate1_and_gate2(self):
        # Arrange
        candidates = _candidate(keywords=("ピカチュウ",))
        # Act
        report = _run(candidates, _inputs())
        # Assert
        assert report["gate1"]["keyword_overlaps"][0]["kind"] == replay.OVERLAP_EQUAL
        assert report["gate_counts"]["gate1"] == 1
        assert report["legacy"]["gate2"]["changed_count"] == 1
        assert report["new"]["gate2_raw_message_blocks"]["changed_count"] == 1
        assert report["exit_code"] == 1

    def test_containing_and_contained_keywords_are_classified(self):
        # Arrange
        contained = _candidate(keywords=("ピカ",))
        containing = _candidate(keywords=("ピカチュウ ex",))
        # Act
        kinds = {
            replay.check_keyword_overlaps(contained, {"1": ["ピカチュウ"]})[0]["kind"],
            replay.check_keyword_overlaps(containing, {"1": ["ピカチュウ"]})[0]["kind"],
        }
        # Assert
        assert kinds == {replay.OVERLAP_CONTAINED_IN, replay.OVERLAP_CONTAINS}


class TestCaseCInvalidWorkId:
    def test_null_work_id_is_detected(self):
        # Arrange
        candidates = _candidate(work_id=None)
        # Act
        report = _run(candidates, _inputs())
        # Assert
        assert len(report["gate1"]["invalid_work_id"]) == 1
        assert report["exit_code"] == 1

    def test_work_id_not_in_active_reference_is_detected(self):
        # Arrange
        candidates = _candidate(work_id=12345)
        # Act
        invalid = replay.check_work_ids(candidates, {WORK_A})
        # Assert
        assert [c["work_id"] for c in invalid] == [12345]


class TestCaseDRawTextHit:
    def test_raw_text_containing_candidate_name_is_counted_in_gate3(self):
        # Arrange
        candidates = _candidate(title="昔の商品", keywords=("ゲンガー",))
        inputs = _inputs(raw_text="昔の商品 1BOX 3000円", shadow_text=RAW_UNRELATED)
        # Act
        report = _run(candidates, inputs)
        # Assert
        assert report["legacy"]["gate3"]["count"] == 1
        assert report["new"]["gate3"]["count"] == 1
        assert report["exit_code"] == 1


class TestNewSystemOnlyChange:
    def test_candidate_changing_new_result_but_not_legacy_is_detected(self):
        # Arrange: 旧解析は作品IDで絞る（WORK_B の候補は除外）。新解析は作品で絞らないので ambiguous になる。
        candidates = _candidate(keywords=("ピカチュウ",), work_id=WORK_B)
        # Act
        report = _run(candidates, _inputs())
        # Assert
        assert report["legacy"]["gate2"]["changed_count"] == 0
        assert report["new"]["gate2_raw_message_blocks"]["changed_count"] == 1
        change = report["new"]["gate2_raw_message_blocks"]["changes"][0]
        assert (change["before"]["status"], change["after"]["status"]) == ("matched", "ambiguous")
        assert report["gate_counts"]["new_gate2_raw_message_blocks"] == 1
        assert report["exit_code"] == 1

    def test_shadow_blocks_are_reported_separately_from_raw_message_blocks(self):
        # Arrange: 過去の shadow ブロックだけが影響を受ける
        candidates = _candidate(keywords=("ピカチュウ",), work_id=WORK_B)
        inputs = {**_inputs(raw_text=RAW_UNRELATED), "shadow_blocks": [{"id": "s", "text": "ピカチュウ 1BOX"}]}
        # Act
        report = _run(candidates, inputs)
        # Assert
        assert report["gate_counts"]["new_gate2_shadow_results_pre_maintenance"] == 1
        assert report["gate_counts"]["new_gate2_raw_message_blocks"] == 0

    def test_status_transition_unmatched_to_matched_counts_as_change(self):
        # Arrange
        candidates = _candidate(keywords=("ゲンガー",))
        # Act
        result = replay.replay_new([{"id": "b", "text": "ゲンガー 1BOX"}], _entries(),
                                   [*_entries(), candidates[0].entry()])
        # Assert
        assert result["changed_count"] == 1
        assert result["changes"][0]["before"]["status"] == "unmatched"
        assert result["changes"][0]["after"]["status"] == "matched"


class TestReadOnlySession:
    def test_open_readonly_session_sets_read_only_and_operator_and_rolls_back(self, monkeypatch):
        # Arrange
        session = MagicMock()
        session.__enter__.return_value = session
        session.execute.return_value.scalar_one.return_value = "on"
        monkeypatch.setattr(replay, "Session", lambda engine: session)
        # Act
        with replay.open_readonly_session(object()):
            pass
        # Assert
        executed = [str(call.args[0]) for call in session.execute.call_args_list]
        assert executed[0] == "SET TRANSACTION READ ONLY"
        assert executed[1] == "SET LOCAL app.is_operator = 'true'"
        session.rollback.assert_called_once()
