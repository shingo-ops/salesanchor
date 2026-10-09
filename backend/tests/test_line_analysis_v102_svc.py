"""LINE解析の本番エンジン v102（services/line_analysis_v102_svc.py）の単体試験。Gemini は呼ばない。DB は使わない。

応答・原文はすべて架空。PostgreSQL が要る試験は test_line_analysis_v102_pg.py。
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import app.services.line_analysis_v102_svc as svc
import app.tools.prompt_ab as pab
from app.services import tcg_analyzer_svc as analyzer
from app.tasks import tcg_extraction as task

_RAW = "商品A\n3BOX@1,000円\n商品B\n2BOX@2,000円"
_CTX = SimpleNamespace(raw_text=_RAW, supplier_context=None, knowledge_links=None, new_system_rules=None)
_MASTERS = {
    "cond_entries": [
        {"cond_id": "11", "code": "CN0003", "canonical": "Sealed box", "priority": 4, "app_kubun": "箱系",
         "search_kw": "未開封", "exclude_kw": "", "match_type": "KEYWORD", "effect": "OUTPUT"},
        {"cond_id": "18", "code": "CN0008", "canonical": "FLAG_SINGLE", "priority": 1, "app_kubun": "枚系,単位不明",
         "search_kw": "単品", "exclude_kw": "", "match_type": "KEYWORD", "effect": "OUTPUT"},
    ],
    "cond_canonical_to_uuid": {"Sealed box": "11", "FLAG_SINGLE": "18"},
    "status_entries": [],
    "unit_alias_to_info": {"BOX": ("BOX", "箱系")},
}


def _response(items: list[dict]) -> str:
    return json.dumps({"items": items}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# get_engine
# ---------------------------------------------------------------------------


def test_get_engine_is_v6_when_unset(monkeypatch):
    monkeypatch.delenv(svc.ENGINE_ENV, raising=False)
    assert svc.get_engine() == svc.ENGINE_V6


@pytest.mark.parametrize("value", ["", "v6", "V102", "x", " "])
def test_get_engine_is_v6_for_empty_v6_and_unknown_values(monkeypatch, value):
    monkeypatch.setenv(svc.ENGINE_ENV, value)
    assert svc.get_engine() == svc.ENGINE_V6


def test_get_engine_is_v102_only_for_exact_v102(monkeypatch):
    monkeypatch.setenv(svc.ENGINE_ENV, "v102")
    assert svc.get_engine() == svc.ENGINE_V102


def test_get_engine_warns_for_unknown_value(monkeypatch, caplog):
    monkeypatch.setenv(svc.ENGINE_ENV, "x")
    with caplog.at_level("WARNING"):
        svc.get_engine()
    assert any("x" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# 小さな部品
# ---------------------------------------------------------------------------


def test_prompt_version_has_v102_prefix_key_and_12_hex_of_sha256():
    version = svc.build_prompt_version("raw_copy_v101_f_c", "本文")
    prefix, key, digest = version.split(":")
    assert (prefix + ":", key) == (svc.V102_PROMPT_VERSION_PREFIX, "raw_copy_v101_f_c") and len(digest) == 12
    assert len(version) <= 50  # extraction_jobs.prompt_version は VARCHAR(50)
    assert svc.is_v102_prompt_version(version) and not svc.is_v102_prompt_version("raw-extraction-v6-rawcode-p1")
    assert not svc.is_v102_prompt_version(MagicMock()) and not svc.is_v102_prompt_version(None)


def test_legacy_supplier_fields_are_removed_without_changing_the_original():
    original = {**dict.fromkeys(svc.LEGACY_SUPPLIER_FIELDS, "v"), "extraction_default_unit": "BOX"}
    assert svc.without_legacy_supplier_fields(original) == {"extraction_default_unit": "BOX"}
    assert set(svc.LEGACY_SUPPLIER_FIELDS) <= set(original) and svc.without_legacy_supplier_fields(None) is None


def test_prompt_ab_keeps_the_moved_names():
    assert pab.V102_PROMPT == svc.V102_PROMPT_KEY == "raw_copy_v101_f_c"
    assert pab.load_prompt_from_db is svc.load_prompt_from_db and pab.LEGACY_SUPPLIER_FIELDS is svc.LEGACY_SUPPLIER_FIELDS


def test_pipeline_gives_the_same_result_as_prompt_ab_row_fields():
    response = _response([{"lines": [1, 2], "price": "1,000円", "quantity": "3"},
                          {"lines": [3], "price": "9,999円", "quantity": "1"},
                          {"lines": [3, 4], "price": "2,000円", "quantity": "2"}])
    assert svc.run_v102_pipeline(response, _CTX, _MASTERS) == pab._v102_row_fields(response, _CTX, _MASTERS)


# ---------------------------------------------------------------------------
# 件の対応付け
# ---------------------------------------------------------------------------


def _row(index: int | None, source_lines: list[int] | None = None):
    return SimpleNamespace(id=f"id{index}", gemini_index=index, source_lines=source_lines)


def test_map_to_rows_pairs_accepted_in_order_and_rejected_by_gemini_index():
    items = [{"name": "a"}, {"name": "c"}, {"rejected": "price_not_in_lines", "gemini_index": 1}]
    rows = [_row(0), _row(1), _row(2)]
    pairs = {item.get("name") or "rej": row.gemini_index for item, row in svc._map_to_rows(items, rows)}
    assert pairs == {"a": 0, "c": 2, "rej": 1}


@pytest.mark.parametrize("items", [
    [{"name": "a"}],  # 件数が足りない
    [{"name": "a"}, {"name": "b"}, {"name": "c"}],  # 件数が多い
    [{"name": "a"}, {"rejected": "x", "gemini_index": 7}],  # 無い gemini_index
    [{"name": "a"}, {"rejected": "x", "gemini_index": 1}, {"rejected": "x", "gemini_index": 1}],  # 重複
])
def test_map_to_rows_raises_when_counts_do_not_match(items):
    with pytest.raises(svc._MappingError):
        svc._map_to_rows(items, [_row(0), _row(1)])


def test_map_to_rows_raises_when_items_are_swapped():
    items = [{"name": "a", "price_line": 2, "lines": [1, 2]}, {"name": "b", "price_line": 4, "lines": [3, 4]}]
    rows = [_row(0, [3, 4]), _row(1, [1, 2])]
    with pytest.raises(svc._MappingError, match="gemini_index=0"):
        svc._map_to_rows(items, rows)


def test_map_to_rows_passes_when_f1_removed_a_heading_line_from_lines():
    items = [{"name": "a", "price_line": 3, "lines": [2, 3]}, {"name": "b", "price_line": 5, "lines": [4, 5]}]
    rows = [_row(0, [1, 2, 3]), _row(1, [1, 4, 5])]
    assert [row.gemini_index for _, row in svc._map_to_rows(items, rows)] == [0, 1]


def test_map_to_rows_passes_when_reassign_moved_an_ambiguous_line_to_another_item():
    items = [{"name": "a", "price_line": 2, "lines": [1, 2, 3]}, {"name": "b", "price_line": 5, "lines": [4, 5]}]
    rows = [_row(0, [1, 2]), _row(1, [3, 4, 5])]
    assert [row.gemini_index for _, row in svc._map_to_rows(items, rows)] == [0, 1]


def test_map_to_rows_without_price_line_needs_an_overlap():
    rows = [_row(0, [1, 2])]
    assert svc._map_to_rows([{"name": "a", "lines": [2, 3]}], rows)[0][1].gemini_index == 0
    with pytest.raises(svc._MappingError, match="gemini_index=0"):
        svc._map_to_rows([{"name": "a", "lines": [5, 6]}], rows)


def test_map_to_rows_checks_rejected_pairs_and_skips_empty_lines():
    rows = [_row(0, [1, 2]), _row(1, [3])]
    ok = [{"name": "a", "price_line": 3, "lines": [3]}, {"rejected": "x", "gemini_index": 0, "lines": [1]}]
    assert len(svc._map_to_rows(ok, rows)) == 2
    bad = [{"name": "a", "price_line": 3, "lines": [3]}, {"rejected": "x", "gemini_index": 0, "lines": [9]}]
    with pytest.raises(svc._MappingError, match="gemini_index=0"):
        svc._map_to_rows(bad, rows)
    assert len(svc._map_to_rows([{"name": "a", "lines": []}, {"name": "b", "price_line": 3}], [_row(0, []), _row(1, [3])])) == 2


# ---------------------------------------------------------------------------
# analysis_results の列
# ---------------------------------------------------------------------------


def _values(item: dict) -> dict:
    return svc._analysis_values(item, _MASTERS, {"BOX": 5}, {42: 3})


def test_unresolved_condition_falls_back_to_flag_single_cn0008():
    for condition in ("none", "不明", "Unknown canonical"):
        values = _values({"unit": "BOX", "condition": condition, "match_status": "unmatched"})
        assert (values["condition_canonical"], values["condition_id"]) == ("FLAG_SINGLE", 18)


def test_resolved_condition_unit_and_matched_product():
    values = _values({"unit": "BOX", "condition": "Sealed box", "product_id": 42, "match_status": "matched",
                      "price_normalized": 1000, "quantity_normalized": 3, "status": "Normal", "status_effect": None,
                      "review": [], "gemini_review": []})
    assert (values["condition_id"], values["unit_id"], values["unit_resolved"]) == (11, 5, True)
    assert (values["product_id"], values["pid_resolved"], values["work_id"], values["pid_basis"]) == (42, True, 3, "V102:matched")
    assert (values["needs_review"], values["review_reasons"], values["note_ja"]) == (False, None, None)


def test_matched_context_counts_as_resolved_and_unmatched_does_not():
    assert _values({"unit": "BOX", "product_id": 42, "match_status": "matched_context"})["pid_resolved"] is True
    ambiguous = _values({"unit": "BOX", "product_id": None, "match_status": "ambiguous"})
    assert (ambiguous["product_id"], ambiguous["pid_resolved"]) == (None, False)


def test_unit_none_gives_null_unit_and_unresolved():
    values = _values({"unit": "none", "condition": "none"})
    assert (values["unit_id"], values["unit_canonical"], values["unit_resolved"]) == (None, None, False)


def test_review_reasons_join_item_and_gemini_kinds_without_duplicates():
    values = _values({"unit": "BOX", "review": [{"kind": "unit_unknown"}, {"kind": "condition_unknown"}, {"kind": "unit_unknown"}],
                      "gemini_review": [{"kind": "gemini_unsure", "line": 2}]})
    assert values["review_reasons"] == "unit_unknown,condition_unknown,gemini_unsure" and values["needs_review"] is True


def test_quantity_not_in_text_kind_goes_to_review_reasons_and_needs_review():
    values = _values({"unit": "BOX", "review": [{"line": 2, "kind": "quantity_not_in_text", "field": "quantity", "copied": "30"}]})
    assert values["review_reasons"] == "quantity_not_in_text" and values["needs_review"] is True


def test_oversized_numbers_become_null():
    values = _values({"unit": "BOX", "price_normalized": 10**13, "quantity_normalized": 2})
    assert (values["price_normalized"], values["quantity_normalized"]) == (None, 2)


def test_job_review_reasons_join_post_review_then_gemini_review():
    flags = {"post_review": [{"kind": "no_items"}, {"kind": "possible_missing_item", "line": 3}, {"kind": "no_items"}],
             "gemini_review": [{"kind": "gemini_unsure_invalid"}]}
    assert svc._job_review_reasons(flags) == "no_items,possible_missing_item,gemini_unsure_invalid"
    assert svc._job_review_reasons({"post_review": [], "gemini_review": []}) is None


def test_extraction_rows_keep_skipped_lines_and_gemini_order():
    rows = svc._item_rows([
        {"lines": [1, 3], "price": "1,000円", "quantity": "2"},
        "not an object",
        {"lines": "bad", "price": 5, "quantity": None},
    ])
    assert [r["gemini_index"] for r in rows] == [0, 1, 2]
    assert (rows[0]["source_lines"], rows[0]["line_start"], rows[0]["line_end"]) == ([1, 3], 1, 3)
    assert (rows[1]["source_lines"], rows[1]["raw_price"]) == (None, None)
    assert (rows[2]["source_lines"], rows[2]["raw_price"], rows[2]["raw_quantity"]) == (None, "5", None)


def test_unreadable_responses_have_no_items():
    for text_ in ("not json", "[]", json.dumps({"items": "x"}), json.dumps({"other": []})):
        assert svc._parse_items(text_) == (None, None)
    assert svc._parse_items(json.dumps({"items": [], "unsure": [1]})) == ([], [1])


# ---------------------------------------------------------------------------
# 振り分け
# ---------------------------------------------------------------------------


def test_analyze_extraction_job_hands_v102_jobs_to_v102_analysis(monkeypatch):
    session = MagicMock()
    session.execute.return_value.scalar.return_value = "v102:raw_copy_v101_f_c:abcdef123456"
    called = MagicMock(return_value={"total": 1})
    monkeypatch.setattr(svc, "run_v102_analysis", called)
    assert analyzer.analyze_extraction_job(session, "job-1") == {"total": 1}
    called.assert_called_once_with(session, "job-1")


def test_analyze_extraction_job_does_not_hand_v6_jobs_to_v102(monkeypatch):
    session = MagicMock()
    session.execute.return_value.scalar.return_value = "raw-extraction-v6-rawcode-p1"
    called = MagicMock()
    monkeypatch.setattr(svc, "run_v102_analysis", called)
    analyzer.analyze_extraction_job(session, "job-1")  # 偽の session でも v6 の処理は最後まで進む。v102 が呼ばれないことだけ見る
    called.assert_not_called()


def _boom(*_a, **_k):
    raise AssertionError("v6 の経路に入った")


def test_default_engine_takes_the_v6_path(monkeypatch):
    monkeypatch.delenv(svc.ENGINE_ENV, raising=False)
    v102 = MagicMock()
    monkeypatch.setattr(task, "run_v102_extraction", v102)
    monkeypatch.setattr(task, "extract_message", MagicMock(side_effect=RuntimeError("v6 path")))
    with pytest.raises(RuntimeError, match="v6 path"):
        task._run_recorded_extraction(MagicMock(), "job", "raw", {}, MagicMock())
    v102.assert_not_called()


@pytest.mark.parametrize("status,expect_analysis", [("done", True), ("empty", True)])
def test_v102_engine_skips_v6_and_analyzes_done_and_empty_jobs(monkeypatch, status, expect_analysis):
    monkeypatch.setenv(svc.ENGINE_ENV, "v102")
    monkeypatch.setenv("TCG_AUTO_ANALYZE", "1")
    monkeypatch.setenv("TCG_AUTO_DISTRIBUTE", "0")
    monkeypatch.setattr(task, "extract_message", _boom)
    monkeypatch.setattr(task, "analyze_extraction_job", _boom)
    monkeypatch.setenv("EXTRACTION_SHADOW_ENABLED", "1")
    monkeypatch.setattr(task, "run_shadow_for_job", _boom)
    extraction = MagicMock(return_value={"status": status, "items_count": 2 if status == "done" else 0})
    analysis = MagicMock(return_value={"total": 2})
    monkeypatch.setattr(task, "run_v102_extraction", extraction)
    monkeypatch.setattr(task, "run_v102_analysis", analysis)
    recorder = MagicMock()
    result = task._run_recorded_extraction(MagicMock(), "job", "raw", {}, recorder)
    extraction.assert_called_once()
    assert extraction.call_args.kwargs["recorder"] is recorder
    assert analysis.called is expect_analysis
    assert result["status"] == status and result["analysis_stats"] == {"total": 2}


def test_v102_engine_does_not_analyze_without_the_auto_analyze_flag(monkeypatch):
    monkeypatch.setenv(svc.ENGINE_ENV, "v102")
    monkeypatch.delenv("TCG_AUTO_ANALYZE", raising=False)
    monkeypatch.setattr(task, "run_v102_extraction", MagicMock(return_value={"status": "done", "items_count": 1}))
    analysis = MagicMock()
    monkeypatch.setattr(task, "run_v102_analysis", analysis)
    result = task._run_recorded_extraction(MagicMock(), "job", "raw", {}, MagicMock())
    analysis.assert_not_called()
    assert result["analysis_stats"] is None


def test_v102_analysis_failure_is_reported_as_analysis_failed(monkeypatch):
    monkeypatch.setenv(svc.ENGINE_ENV, "v102")
    monkeypatch.setenv("TCG_AUTO_ANALYZE", "1")
    monkeypatch.setattr(task, "run_v102_extraction", MagicMock(return_value={"status": "done", "items_count": 1}))
    monkeypatch.setattr(task, "run_v102_analysis", MagicMock(side_effect=ValueError("masters empty")))
    session = MagicMock()
    result = task._run_recorded_extraction(session, "job", "raw", {}, MagicMock())
    assert result["analysis_stats"] == {"status": "error", "error_code": "ANALYSIS_FAILED"}
    session.rollback.assert_called()
