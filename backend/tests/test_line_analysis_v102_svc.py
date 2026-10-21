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
    "ship_entries": [],
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
    version = svc.build_prompt_version("raw_copy_v101_f_ct", "本文")
    prefix, key, digest = version.split(":")
    assert (prefix + ":", key) == (svc.V102_PROMPT_VERSION_PREFIX, "raw_copy_v101_f_ct") and len(digest) == 12
    assert len(version) <= 50  # extraction_jobs.prompt_version は VARCHAR(50)
    assert svc.is_v102_prompt_version(version) and not svc.is_v102_prompt_version("raw-extraction-v6-rawcode-p1")
    assert not svc.is_v102_prompt_version(MagicMock()) and not svc.is_v102_prompt_version(None)


def test_legacy_supplier_fields_are_removed_without_changing_the_original():
    original = {**dict.fromkeys(svc.LEGACY_SUPPLIER_FIELDS, "v"), "extraction_default_unit": "BOX"}
    assert svc.without_legacy_supplier_fields(original) == {"extraction_default_unit": "BOX"}
    assert set(svc.LEGACY_SUPPLIER_FIELDS) <= set(original) and svc.without_legacy_supplier_fields(None) is None


def test_prompt_ab_keeps_the_moved_names():
    assert pab.V102_PROMPT == svc.V102_PROMPT_KEY == "raw_copy_v101_f_ct"
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


def _is_mismatch(item: dict) -> bool:
    return [r["kind"] for r in item.get("review", [])] == [svc.REASON_ITEM_MAPPING_MISMATCH]


def test_map_to_rows_pairs_each_row_with_the_item_of_the_same_gemini_index():
    # 便G：受理した件も落とした件も gemini_index（応答の位置）で行 rows[i] に当てる。順番は問わない
    items = [{"name": "c", "gemini_index": 2}, {"name": "a", "gemini_index": 0}, {"rejected": "price_not_in_lines", "gemini_index": 1}]
    rows = [_row(0), _row(1), _row(2)]
    pairs = {row.gemini_index: item.get("name") or "rej" for item, row in svc._map_to_rows(items, rows)}
    assert pairs == {0: "a", 1: "rej", 2: "c"}


@pytest.mark.parametrize("items", [
    [{"name": "a", "gemini_index": 0}],  # 件が足りない：行1だけ対応なし
    [{"name": "a", "gemini_index": 0}, {"name": "b"}],  # gemini_index が無い件：行1だけ対応なし
    [{"name": "a", "gemini_index": 0}, {"rejected": "x", "gemini_index": 7}],  # 範囲外の gemini_index：行1だけ対応なし
    [{"name": "a", "gemini_index": 0}, {"rejected": "x", "gemini_index": 1}, {"rejected": "x", "gemini_index": 1}],  # 重複：行1だけ
])
def test_map_to_rows_marks_only_the_unmatched_row(items):
    pairs = svc._map_to_rows(items, [_row(0), _row(1)])
    assert len(pairs) == 2 and pairs[0][0]["name"] == "a" and _is_mismatch(pairs[1][0])


def test_map_to_rows_does_not_raise_when_there_are_more_items_than_rows():
    items = [{"name": "a", "gemini_index": 0}, {"name": "b", "gemini_index": 1}, {"name": "c", "gemini_index": 2}]
    assert [item["name"] for item, _ in svc._map_to_rows(items, [_row(0), _row(1)])] == ["a", "b"]


def test_map_to_rows_marks_both_rows_when_items_are_swapped_and_leaves_the_rest():
    items = [{"name": "a", "price_line": 2, "lines": [1, 2], "gemini_index": 0},
             {"name": "b", "price_line": 4, "lines": [3, 4], "gemini_index": 1},
             {"name": "c", "price_line": 6, "lines": [5, 6], "gemini_index": 2}]
    rows = [_row(0, [3, 4]), _row(1, [1, 2]), _row(2, [5, 6])]
    pairs = svc._map_to_rows(items, rows)
    assert [_is_mismatch(item) for item, _ in pairs] == [True, True, False] and pairs[2][0]["name"] == "c"


def test_map_to_rows_passes_when_f1_removed_a_heading_line_from_lines():
    items = [{"name": "a", "price_line": 3, "lines": [2, 3], "gemini_index": 0},
             {"name": "b", "price_line": 5, "lines": [4, 5], "gemini_index": 1}]
    rows = [_row(0, [1, 2, 3]), _row(1, [1, 4, 5])]
    assert [item["name"] for item, _ in svc._map_to_rows(items, rows)] == ["a", "b"]


def test_map_to_rows_without_price_line_needs_an_overlap():
    rows = [_row(0, [1, 2])]
    assert svc._map_to_rows([{"name": "a", "lines": [2, 3], "gemini_index": 0}], rows)[0][0]["name"] == "a"
    assert _is_mismatch(svc._map_to_rows([{"name": "a", "lines": [5, 6], "gemini_index": 0}], rows)[0][0])


def test_map_to_rows_checks_rejected_pairs_and_skips_empty_lines():
    rows = [_row(0, [1, 2]), _row(1, [3])]
    ok = [{"name": "a", "price_line": 3, "lines": [3], "gemini_index": 1}, {"rejected": "x", "gemini_index": 0, "lines": [1]}]
    assert [_is_mismatch(item) for item, _ in svc._map_to_rows(ok, rows)] == [False, False]
    bad = [{"name": "a", "price_line": 3, "lines": [3], "gemini_index": 1}, {"rejected": "x", "gemini_index": 0, "lines": [9]}]
    assert [_is_mismatch(item) for item, _ in svc._map_to_rows(bad, rows)] == [True, False]
    empty = [{"name": "a", "lines": [], "gemini_index": 0}, {"name": "b", "price_line": 3, "gemini_index": 1}]
    assert [_is_mismatch(item) for item, _ in svc._map_to_rows(empty, [_row(0, []), _row(1, [3])])] == [False, False]


def test_mismatch_row_is_written_empty_with_the_reason_and_the_other_rows_normally():
    # 便G A16：対応が付かない行だけ、値は空（未解決の状態）＋ item_mapping_mismatch ＋ 要確認。他の行は通常どおり
    session = _write([{"unit": "BOX", "product_id": 42, "match_status": "matched", "price_normalized": 1000.0}, {"unit": "BOX"}], drop_index=1)
    first, second = _statements(session, "INSERT INTO public.analysis_results")
    assert (first["product_id"], first["price_normalized"], first["needs_review"]) == (42, 1000.0, False)
    assert (second["product_id"], second["unit_canonical"], second["price_normalized"], second["quantity_normalized"]) == (None, None, None, None)
    assert (second["condition_canonical"], second["review_reasons"], second["needs_review"], second["pid_resolved"]) == (
        "FLAG_SINGLE", "item_mapping_mismatch", True, False)


def test_value_out_of_range_adds_the_reason_and_needs_review():
    # 便G A15：10**12 以上は None にして理由を付ける。入力が None・範囲内なら付けない
    item = {"unit": "BOX", "price_normalized": 10.0**12, "quantity_normalized": 3.0}
    values = svc._analysis_values(item, _MASTERS, {"BOX": 5}, {})
    assert (values["price_normalized"], values["quantity_normalized"]) == (None, 3.0)
    assert (values["review_reasons"], values["needs_review"]) == ("value_out_of_range", True)
    ok = svc._analysis_values({"unit": "BOX", "price_normalized": 999999999999.0, "quantity_normalized": None}, _MASTERS, {"BOX": 5}, {})
    assert (ok["price_normalized"], ok["review_reasons"], ok["needs_review"]) == (999999999999.0, None, False)
    both = svc._analysis_values({"unit": "BOX", "price_normalized": 10**13, "quantity_normalized": 10**13, "review": [{"kind": "unit_unknown"}]},
                                _MASTERS, {"BOX": 5}, {})
    assert both["review_reasons"] == "unit_unknown,value_out_of_range"  # 理由は重複なしで連結


def test_pipeline_error_is_still_extract_exception_for_the_whole_post():
    # 便G A17：プログラムの例外は、従来どおり投稿全体を extract_exception にする
    def boom(*_args, **_kwargs):
        raise ValueError("boom")

    out = svc.run_v102_pipeline(_response([{"lines": [1, 2], "price": "1,000円", "quantity": "3"}]), _CTX, _MASTERS, extract_items=boom)
    assert out["v102_items"] == [] and out["v102_flags"]["post_review"][0]["kind"] == "extract_exception"


def test_pipeline_does_not_pass_ship_entries_to_extract_items():
    # 発送マスタは _analysis_values だけが使う。キーワード固定の extract_v101_items に渡すと TypeError で投稿全体が落ちる
    received: dict = {}

    def extract(items, raw, *, order, reassign, v102_fixes, review_reasons, gemini_trust, cond_entries,
                cond_canonical_to_uuid, unit_alias_to_info, status_entries, **kwargs):
        received.update(kwargs)
        return [], {}

    masters = {**_MASTERS, "ship_entries": [{"id": "NJ040"}], "ship_drop_entries": [{"id": "D1"}]}
    out = svc.run_v102_pipeline(_response([{"lines": [1, 2], "price": "1,000円", "quantity": "3"}]), _CTX, masters, extract_items=extract)

    assert "ship_entries" not in received
    assert "ship_drop_entries" not in received
    assert "post_review" not in out["v102_flags"]
    assert masters["ship_entries"] == [{"id": "NJ040"}]  # 元の masters は変えない


# ---------------------------------------------------------------------------
# analysis_results の列
# ---------------------------------------------------------------------------


def _values(item: dict) -> dict:
    return svc._analysis_values(item, _MASTERS, {"BOX": 5}, {42: 3})


def test_unresolved_condition_falls_back_to_flag_single_cn0008():
    for condition in ("none", "不明", "Unknown canonical"):
        values = _values({"unit": "BOX", "condition": condition, "match_status": "unmatched"})
        assert (values["condition_canonical"], values["condition_id"]) == ("FLAG_SINGLE", 18)


def test_error_condition_is_written_with_its_own_id_when_the_master_has_it():
    error_entry = {"cond_id": "26", "code": "CN0012", "canonical": "Error", "priority": 99, "app_kubun": "",
                   "search_kw": "", "exclude_kw": "", "match_type": "KEYWORD", "effect": "EXCLUDE"}
    masters = {**_MASTERS, "cond_entries": [*_MASTERS["cond_entries"], error_entry]}
    values = svc._analysis_values(
        {"unit": "BOX", "condition": "Error", "match_status": "unmatched", "review": [{"kind": "condition_unknown"}]},
        masters, {"BOX": 5}, {},
    )
    assert (values["condition_canonical"], values["condition_id"]) == ("Error", 26)
    assert values["needs_review"] is True and "condition_unknown" in values["review_reasons"]


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
    session.execute.return_value.scalar.return_value = "v102:raw_copy_v101_f_ct:abcdef123456"
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


def test_matched_followup_counts_as_resolved_with_its_own_basis():
    values = _values({"unit": "BOX", "product_id": 42, "match_status": "matched_followup"})
    assert (values["product_id"], values["pid_resolved"], values["pid_basis"]) == (42, True, "V102:matched_followup")


def test_matched_soldout_ref_counts_as_resolved_with_its_own_basis():
    values = _values({"unit": "BOX", "product_id": 42, "match_status": "matched_soldout_ref"})
    assert (values["product_id"], values["pid_resolved"], values["pid_basis"]) == (42, True, "V102:matched_soldout_ref")


def test_masters_with_followup_adds_soldout_posts_only_when_given():
    masters = {"a": 1}
    assert svc.masters_with_followup(masters, None) is masters
    assert svc.masters_with_followup(masters, None, ()) is masters
    assert svc.masters_with_followup(masters, ("m", "t"), ("p",)) == {"a": 1, "followup_ref": ("m", "t"), "soldout_posts": ("p",)}
    assert svc.masters_with_followup(masters, None, ("p",)) == {"a": 1, "soldout_posts": ("p",)}


# ---------------------------------------------------------------------------
# 〆の完売の相手（便2-2）：状態の引き継ぎと analysis_soldout_extra_targets への書き込み
# ---------------------------------------------------------------------------

_T = svc.CONDITION_BASIS_SOLDOUT_REF
_TARGETS = [
    {"product_id": 42, "condition_id": 11, "ref_message_id": "m1", "ref_line": 1},
    {"product_id": 42, "condition_id": 18, "ref_message_id": "m1", "ref_line": 2},
    {"product_id": 43, "condition_id": 11, "ref_message_id": "m1", "ref_line": 3},
]
_CANONICALS = {11: "Sealed box", 18: "FLAG_SINGLE"}


def _soldout_item(**extra) -> dict:
    return {"unit": "BOX", "condition": "none", "product_id": 42, "match_status": "matched_soldout_ref", "soldout_targets": _TARGETS, **extra}


def test_soldout_targets_overwrite_the_condition_with_the_first_target():
    item = _soldout_item()
    values = _values(item)
    assert values["condition_canonical"] == "FLAG_SINGLE"  # 〆の行の文字からは決まらない
    out = svc._apply_soldout_targets(values, item, None, _CANONICALS)
    assert (out["condition_id"], out["condition_canonical"], out["condition_basis"]) == (11, "Sealed box", "SOLDOUT_REF")
    assert out is not values and values["condition_id"] == 18 and values["condition_basis"] == ""  # 元は変えない


def test_soldout_target_that_is_an_excluded_condition_keeps_reasons_and_needs_review():
    item = _soldout_item(soldout_targets=[{"product_id": 42, "condition_id": 99, "ref_message_id": "m1", "ref_line": 1}])
    values = {**_values(item), "review_reasons": "condition_unknown", "needs_review": True}
    out = svc._apply_soldout_targets(values, item, None, {**_CANONICALS, 99: "Error"}, frozenset({99}))
    assert (out["condition_id"], out["condition_canonical"], out["condition_basis"]) == (99, "Error", "SOLDOUT_REF")
    assert (out["review_reasons"], out["needs_review"]) == ("condition_unknown", True)  # 決まっていない状態を引き継いだだけ
    without = svc._apply_soldout_targets(values, item, None, {**_CANONICALS, 99: "Error"})
    assert without["needs_review"] is False  # EXCLUDE の印が無ければ「決まった状態」扱い（効くのは excluded_ids）


def test_soldout_targets_do_nothing_without_targets_or_when_a_human_decided():
    values = _values(_soldout_item())
    plain = {k: v for k, v in _soldout_item().items() if k != "soldout_targets"}
    assert svc._apply_soldout_targets(values, plain, None, _CANONICALS) is values
    assert svc._apply_soldout_targets(values, {**plain, "soldout_targets": []}, None, _CANONICALS) is values
    for decision in (svc.Decisions(product_id=42), svc.Decisions(condition_id=18)):
        assert svc._apply_soldout_targets(values, _soldout_item(), decision, _CANONICALS) is values
    ack_only = svc.Decisions(ack_codes=frozenset({"x"}))  # 確認済みだけの判断は商品・状態の判断ではない
    assert svc._apply_soldout_targets(values, _soldout_item(), ack_only, _CANONICALS)["condition_basis"] == "SOLDOUT_REF"


def test_soldout_targets_keep_the_condition_when_the_canonical_is_unknown():
    values = _values(_soldout_item())
    assert svc._apply_soldout_targets(values, _soldout_item(), None, {}) is values


def test_extra_targets_are_the_targets_that_differ_from_the_written_row():
    item = _soldout_item()
    values = svc._apply_soldout_targets(_values(item), item, None, _CANONICALS)
    assert [(t["product_id"], t["condition_id"]) for t in svc._extra_targets(values, item, None)] == [(42, 18), (43, 11)]
    unresolved = _values(item)  # 状態を上書きできなかったとき（書いた行は 42・18）、先頭の相手 (42, 11) も表に入る
    assert [(t["product_id"], t["condition_id"]) for t in svc._extra_targets(unresolved, item, None)] == [(42, 11), (43, 11)]


def test_no_extra_targets_when_a_human_decided_or_there_is_no_target():
    item = _soldout_item()
    values = _values(item)
    assert svc._extra_targets(values, item, svc.Decisions(condition_id=11)) == []
    assert svc._extra_targets(values, {"product_id": 42}, None) == []


def test_stock_lines_come_from_source_lines_or_the_line_range():
    assert svc._stock_lines([3, 5], 1, 9) == frozenset({3, 5})
    assert svc._stock_lines(None, 2, 4) == frozenset({2, 3, 4})
    assert svc._stock_lines([], 2, 3) == frozenset({2, 3})
    assert svc._stock_lines(None, None, 4) == frozenset() and svc._stock_lines(None, 2, None) == frozenset()


class _FakeSession:
    """_write_results が発行する SQL を控える。読み取りは固定の行を返す。"""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append((sql, params or {}))
        rows = {"FROM public.products": [(42, 3), (43, 3)], "= :effect": [], "FROM public.conditions": [(11, "Sealed box"), (18, "FLAG_SINGLE")]}
        found = next((v for k, v in rows.items() if k in sql), [])
        return SimpleNamespace(fetchall=lambda: found, scalar_one=lambda: f"result-{sum('INSERT INTO' in c[0] and 'analysis_results' in c[0] for c in self.calls)}")


def _write(items: list[dict], decisions=None, drop_index: int | None = None) -> _FakeSession:
    rows = [SimpleNamespace(id=f"row{i}", gemini_index=i, source_lines=[i + 1]) for i in range(len(items))]
    numbered = [{"lines": [i + 1], "gemini_index": i, **it} for i, it in enumerate(items) if i != drop_index]  # 便G：gemini_index で行に当てる
    pipeline = {"v102_items": numbered, "v102_flags": {}}
    session = _FakeSession()
    svc._write_results(session, "job1", pipeline, rows, _MASTERS, {"BOX": 5}, decisions)
    return session


def _statements(session: _FakeSession, needle: str) -> list[dict]:
    return [params for sql, params in session.calls if needle in sql]


def test_write_results_deletes_old_extras_first_and_writes_one_row_per_extra_target():
    session = _write([_soldout_item()])
    order = [next(n for n in ("DELETE FROM", "INSERT INTO public.analysis_results", "INSERT INTO public.analysis_soldout_extra_targets") if n in sql)
             for sql, _ in session.calls if any(n in sql for n in ("DELETE FROM", "INSERT INTO"))]
    assert order[0] == "DELETE FROM" and order.count("INSERT INTO public.analysis_soldout_extra_targets") == 2
    upsert = _statements(session, "INSERT INTO public.analysis_results")[0]
    assert (upsert["condition_id"], upsert["condition_basis"], upsert["product_id"]) == (11, "SOLDOUT_REF", 42)
    extras = _statements(session, "analysis_soldout_extra_targets (")
    assert [(e["analysis_result_id"], e["product_id"], e["condition_id"], e["ref_message_id"], e["ref_line"]) for e in extras] == [
        ("result-1", 42, 18, "m1", 2), ("result-1", 43, 11, "m1", 3)]
    assert _statements(session, "DELETE FROM")[0] == {"ej": "job1"}


def test_write_results_writes_no_extra_rows_when_a_human_decided_or_no_target():
    decided = _write([_soldout_item()], {"row0": svc.Decisions(condition_id=18)})
    assert _statements(decided, "analysis_soldout_extra_targets (") == []
    assert _statements(decided, "INSERT INTO public.analysis_results")[0]["condition_basis"] == svc.CONDITION_BASIS_MANUAL
    plain = _write([{"unit": "BOX", "product_id": 42, "match_status": "matched"}])
    assert _statements(plain, "analysis_soldout_extra_targets (") == []
    assert len(_statements(plain, "DELETE FROM")) == 1  # 古い相手は、相手が無い件でも消す


def test_inheriting_the_stock_condition_drops_the_condition_review_reasons_only_when_overwritten():
    item = _soldout_item(review=[{"kind": "condition_unknown"}, {"kind": "unit_unknown"}, {"kind": "condition_multiple_candidates"}])
    values = _values(item)
    assert (values["review_reasons"], values["needs_review"]) == ("condition_unknown,unit_unknown,condition_multiple_candidates", True)
    out = svc._apply_soldout_targets(values, item, None, _CANONICALS)
    assert (out["review_reasons"], out["needs_review"]) == ("unit_unknown", True)  # 状態の理由だけ外れる
    only_condition = _soldout_item(review=[{"kind": "condition_unknown"}])
    cleared = svc._apply_soldout_targets(_values(only_condition), only_condition, None, _CANONICALS)
    assert (cleared["review_reasons"], cleared["needs_review"]) == (None, False)  # 空になれば要確認も外れる
    assert svc._apply_soldout_targets(values, item, None, {}) is values  # 上書きできなければ何も外さない


def test_inheriting_an_undecided_flag_condition_keeps_the_review_reasons():
    item = _soldout_item(review=[{"kind": "condition_unknown"}, {"kind": "unit_unknown"}])
    values = _values(item)
    targets = [{**_TARGETS[0], "condition_id": 18}, *_TARGETS[1:]]  # 先頭の相手が FLAG_SINGLE
    out = svc._apply_soldout_targets(values, {**item, "soldout_targets": targets}, None, _CANONICALS)
    assert (out["condition_id"], out["condition_canonical"], out["condition_basis"]) == (18, "FLAG_SINGLE", "SOLDOUT_REF")  # 状態はそろえる
    assert (out["review_reasons"], out["needs_review"]) == (values["review_reasons"], values["needs_review"]) == ("condition_unknown,unit_unknown", True)


def test_soldout_inherit_basis_is_written_when_the_item_carries_it():
    item = _soldout_item(soldout_target_basis="SOLDOUT_INHERIT")
    out = svc._apply_soldout_targets(_values(item), item, None, _CANONICALS)
    assert out["condition_basis"] == "SOLDOUT_INHERIT"


def test_soldout_ref_basis_stays_when_the_item_has_no_target_basis():
    item = _soldout_item()
    assert svc._apply_soldout_targets(_values(item), item, None, _CANONICALS)["condition_basis"] == "SOLDOUT_REF"


def test_soldout_inherit_does_not_override_a_human_decision():
    item = _soldout_item(soldout_target_basis="SOLDOUT_INHERIT")
    values = _values(item)
    assert svc._apply_soldout_targets(values, item, svc.Decisions(condition_id=18), _CANONICALS) is values


def test_price_basis_is_v102_yen_free_with_the_mark_and_none_without_and_review_is_unchanged():
    # 同じ件の2通り（印あり・なし）を比べる。印は needs_review・review_reasons に影響しない
    base = {"unit": "BOX", "product_id": 42, "match_status": "matched", "review": [{"kind": "unit_unknown"}]}
    marked = _values({**base, "price_basis": "yen_free"})
    plain = _values(base)
    assert marked["price_basis"] == "V102:yen_free" and plain["price_basis"] is None
    assert (marked["needs_review"], marked["review_reasons"]) == (plain["needs_review"], plain["review_reasons"])
    assert _values({**base, "price_basis": ""})["price_basis"] is None


def test_price_basis_is_cut_to_the_column_width():
    assert len(_values({"price_basis": "x" * 500})["price_basis"]) == svc._PRICE_BASIS_MAX


def test_write_results_binds_price_basis_into_the_insert():
    session = _write([{"unit": "BOX", "product_id": 42, "match_status": "matched", "price_basis": "yen_free"},
                      {"unit": "BOX", "product_id": 42, "match_status": "matched"}])
    first, second = _statements(session, "INSERT INTO public.analysis_results")
    assert (first["price_basis"], second["price_basis"]) == ("V102:yen_free", None)
    assert "price_basis = EXCLUDED.price_basis" in svc._UPSERT_SQL


# ---------------------------------------------------------------------------
# system_review_detail（段1：間の行の検知の記録）
# ---------------------------------------------------------------------------


def test_set_job_review_detail_binds_json_text_or_null():
    session = MagicMock()

    svc._set_job_review_detail(session, "job1", {"v": 1, "unmapped": 0})
    svc._set_job_review_detail(session, "job1", None)

    first, second = (call.args[1] for call in session.execute.call_args_list)
    assert json.loads(first["d"]) == {"v": 1, "unmapped": 0} and second["d"] is None
    assert "system_review_detail = CAST(:d AS jsonb)" in str(session.execute.call_args_list[0].args[0])


def test_analysis_failure_clears_system_review_detail_next_to_extract_exception(monkeypatch):
    session = MagicMock()
    session.execute.return_value.one.return_value = SimpleNamespace(gemini_unsure=None, review_reasons=None)
    session.execute.return_value.fetchall.return_value = [
        SimpleNamespace(id="item-0", gemini_index=0, source_lines=[1], raw_price="1,000円", raw_quantity="3")
    ]
    monkeypatch.setattr(task, "load_extraction_context", lambda _s, _j: _CTX)
    monkeypatch.setattr(svc, "load_v102_masters", lambda _s: (_MASTERS, {}))
    monkeypatch.setattr(svc, "load_v102_decisions", lambda _s, _ids: {})
    monkeypatch.setattr(svc, "_fixed_products", lambda *_a: {})
    monkeypatch.setattr(svc, "_load_resolved_pairs", lambda _s, _j: [])
    monkeypatch.setattr(svc, "load_followup_reference", lambda _s, _j: None)
    monkeypatch.setattr(svc, "load_soldout_ref_posts", lambda _s, _j: None)
    monkeypatch.setattr(svc, "masters_with_followup", lambda masters, *_a: masters)
    monkeypatch.setattr(svc, "run_v102_pipeline", MagicMock(side_effect=ValueError("boom")))
    calls: list[tuple] = []
    monkeypatch.setattr(svc, "_set_job_review_reasons", lambda _s, job, reasons: calls.append(("reasons", job, reasons)))
    monkeypatch.setattr(svc, "_set_job_review_detail", lambda _s, job, detail: calls.append(("detail", job, detail)))

    svc.run_v102_analysis(session, "job1")

    assert calls == [("reasons", "job1", svc.REASON_EXTRACT_EXCEPTION), ("detail", "job1", None)]


def _failing_analysis_setup(monkeypatch):
    """run_v102_analysis をシステム段の例外の経路に入れる（test_analysis_failure_clears... と同じ組み立て）。"""
    session = MagicMock()
    session.execute.return_value.one.return_value = SimpleNamespace(gemini_unsure=None, review_reasons=None)
    session.execute.return_value.fetchall.return_value = [
        SimpleNamespace(id="item-0", gemini_index=0, source_lines=[1], raw_price="1,000円", raw_quantity="3")
    ]
    monkeypatch.setattr(task, "load_extraction_context", lambda _s, _j: _CTX)
    monkeypatch.setattr(svc, "load_v102_masters", lambda _s: (_MASTERS, {}))
    monkeypatch.setattr(svc, "load_v102_decisions", lambda _s, _ids: {})
    monkeypatch.setattr(svc, "_fixed_products", lambda *_a: {})
    monkeypatch.setattr(svc, "_load_resolved_pairs", lambda _s, _j: [])
    monkeypatch.setattr(svc, "load_followup_reference", lambda _s, _j: None)
    monkeypatch.setattr(svc, "load_soldout_ref_posts", lambda _s, _j: None)
    monkeypatch.setattr(svc, "masters_with_followup", lambda masters, *_a: masters)
    monkeypatch.setattr(svc, "run_v102_pipeline", MagicMock(side_effect=ValueError("boom")))
    return session


def test_clearing_the_detail_on_failure_runs_inside_a_savepoint(monkeypatch):
    session = _failing_analysis_setup(monkeypatch)
    monkeypatch.setattr(svc, "_set_job_review_reasons", lambda *_a: None)
    monkeypatch.setattr(svc, "_set_job_review_detail", lambda *_a: None)

    svc.run_v102_analysis(session, "job1")

    session.begin_nested.assert_called_once()


def test_a_failed_detail_clear_only_logs_and_keeps_the_extract_exception_reason(monkeypatch, caplog):
    session = _failing_analysis_setup(monkeypatch)
    reasons: list[str] = []
    monkeypatch.setattr(svc, "_set_job_review_reasons", lambda _s, _j, value: reasons.append(value))
    monkeypatch.setattr(svc, "_set_job_review_detail", MagicMock(side_effect=RuntimeError("column missing")))

    with caplog.at_level("WARNING"):
        stats = svc.run_v102_analysis(session, "job1")

    assert reasons == [svc.REASON_EXTRACT_EXCEPTION] and stats["pid_resolved"] == 0
    assert session.commit.called and "system_review_detail" in caplog.text


# ---------------------------------------------------------------------------
# 段2a：取りこぼし疑い（gemini_gap_suspect）
# ---------------------------------------------------------------------------


def _gap_entry(index: int, lines: list[int], candidates: list[int]) -> dict:
    return {"gemini_index": index, "gap_lines": lines, "support_lines": lines, "candidates": candidates}


def _gap_items() -> list[dict]:
    return [
        {"gemini_index": 0, "price_line": 7, "match_status": "unmatched", "review": [{"kind": "product_not_in_master", "source": "system"}]},
        {"gemini_index": 1, "price_line": 9, "match_status": "matched", "product_id": 5},
        {"gemini_index": 2, "price_line": 11, "rejected": "item_shape_invalid", "match_status": "unmatched"},
        {"gemini_index": 3, "price_line": 13, "match_status": "unmatched"},
    ]


def test_gap_reason_is_appended_to_the_target_item_with_lines_and_candidates():
    items = _gap_items()
    detail = {"gap_name": [_gap_entry(0, [4, 5], [10, 11]), _gap_entry(3, [12], [])]}

    result = svc._with_gap_reasons(items, detail)

    assert result[0]["review"][-1] == {
        "kind": svc.REASON_GEMINI_GAP_SUSPECT, "line": 7, "lines": [4, 5], "candidates": [10, 11], "source": svc.SOURCE_SYSTEM,
    }
    assert [r["kind"] for r in result[0]["review"]] == ["product_not_in_master", "gemini_gap_suspect"]
    assert result[3]["review"] == [{
        "kind": "gemini_gap_suspect", "line": 13, "lines": [12], "candidates": [], "source": "system",
    }]


def test_gap_reason_leaves_other_items_rejected_items_and_the_inputs_unchanged():
    items = _gap_items()
    snapshot = json.loads(json.dumps(items))
    detail = {"gap_name": [_gap_entry(0, [4], [10]), _gap_entry(2, [8], [10]), _gap_entry(99, [1], [])]}
    detail_snapshot = json.loads(json.dumps(detail))

    result = svc._with_gap_reasons(items, detail)

    assert result[1] is items[1] and result[2] is items[2] and result[3] is items[3]
    assert items == snapshot and detail == detail_snapshot
    assert result is not items and result[0] is not items[0]


def test_gap_reason_ignores_entries_without_gemini_index():
    items = _gap_items()

    assert svc._with_gap_reasons(items, {"gap_name": [_gap_entry(None, [4], [])]}) == items


def test_gap_reason_returns_the_same_items_when_detail_is_none():
    items = _gap_items()

    assert svc._with_gap_reasons(items, None) is items


def test_gap_reason_failure_logs_and_returns_the_items_unchanged(caplog):
    items = _gap_items()

    with caplog.at_level("ERROR"):
        result = svc._with_gap_reasons(items, {"gap_name": [{"gemini_index": 0}]})  # gap_lines が無い＝例外

    assert result is items and "取りこぼし疑い" in caplog.text


def test_gap_reason_makes_the_item_needs_review_without_resolving_the_product():
    item = {"match_status": "unmatched", "product_id": None, "unit": "BOX", "price_normalized": 1000.0, "quantity_normalized": 3.0}
    [flagged] = svc._with_gap_reasons([{**item, "gemini_index": 0, "price_line": 7}], {"gap_name": [_gap_entry(0, [4], [10])]})

    before = svc._analysis_values(item, _MASTERS, {"BOX": 5}, {})
    after = svc._analysis_values(flagged, _MASTERS, {"BOX": 5}, {})

    assert before["needs_review"] is False
    assert after["needs_review"] is True and "gemini_gap_suspect" in after["review_reasons"].split(svc.REASON_SEPARATOR)
    assert after["pid_resolved"] is False and after["product_id"] is None
    assert after["pid_resolved"] == before["pid_resolved"] and after["product_id"] == before["product_id"]


def test_pipeline_gap_reason_matches_the_stage1_detail_and_does_not_change_the_detail(monkeypatch):
    ctx = SimpleNamespace(raw_text="商品A\n3BOX@1,000円", supplier_context=None, knowledge_links=None, new_system_rules=None)
    detail = {"post_review": [], "gap_price_qty": [], "gap_name": [_gap_entry(0, [1], [7])]}

    def extract(items, raw, **_kw):
        return [{"gemini_index": 0, "price_line": 2, "match_status": "unmatched", "review": []}], {}

    monkeypatch.setattr(svc, "_gap_detail", lambda *_a: detail)
    out = svc.run_v102_pipeline(_response([]), ctx, _MASTERS, extract_items=extract)

    [review] = out["v102_items"][0]["review"]
    assert review["lines"] == detail["gap_name"][0]["gap_lines"] and review["candidates"] == detail["gap_name"][0]["candidates"]
    assert out["v102_gap_detail"] is detail


# ---------------------------------------------------------------------------
# 便PO3：発送日の文字を備考（note_ja）へ
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ship, expected", [
    ("none", None),
    (None, None),
    (" ", None),
    ("発送日要相談", "発送日要相談"),
    ("入荷次第注文順に発送）", "入荷次第注文順に発送"),
    ("発送日要相談（国内のみ", "発送日要相談（国内のみ）"),
    ("【10/16発送】", "【10/16発送】"),
    ("※発送日相談 / ※移し替えて発送予定", "※発送日相談 / ※移し替えて発送予定"),
    ("a） / b（c", "a / b（c）"),
])
def test_ship_note(ship, expected):
    assert svc.ship_note(ship) == expected


def test_analysis_values_puts_ship_in_ship_ja_and_ship_en_and_leaves_note_ja_empty():
    ship_entries = [
        {"id": "NJ040", "label_ja": "入荷次第発送", "label_en": "Ships upon arrival", "label_template_en": "",
         "match_type": "LITERAL", "search_keywords": ["届き次第発送"], "exclude_keywords": [],
         "search_pattern": "", "label_template": ""},
    ]
    masters = {**_MASTERS, "ship_entries": ship_entries}
    base = {"unit": "BOX", "price_normalized": 1000.0, "quantity_normalized": 3.0}
    matched = svc._analysis_values({**base, "ship": "届き次第発送"}, masters, {"BOX": 5}, {})
    unmatched = svc._analysis_values({**base, "ship": "発送日要相談（国内のみ"}, masters, {"BOX": 5}, {})
    without = svc._analysis_values({**base, "ship": "none"}, masters, {"BOX": 5}, {})
    assert (matched["ship_ja"], matched["ship_en"], matched["note_ja"]) == ("入荷次第発送", "Ships upon arrival", None)
    assert (unmatched["ship_ja"], unmatched["ship_en"], unmatched["note_ja"]) == ("発送日要相談（国内のみ）", None, None)
    assert (without["ship_ja"], without["ship_en"], without["note_ja"]) == (None, None, None)
    keys = {"note_ja", "ship_ja", "ship_en"}
    assert {k: v for k, v in unmatched.items() if k not in keys} == {k: v for k, v in without.items() if k not in keys}


def test_upsert_sql_writes_ship_columns_in_all_three_places():
    assert "price_basis, ship_ja, ship_en" in svc._UPSERT_SQL
    assert ":price_basis, :ship_ja, :ship_en" in svc._UPSERT_SQL
    assert "ship_ja = EXCLUDED.ship_ja, ship_en = EXCLUDED.ship_en" in svc._UPSERT_SQL


def _run_extraction_with_result(monkeypatch, result: dict) -> MagicMock:
    session = MagicMock()
    recorder = MagicMock()
    recorder.prepare_items.return_value = []
    monkeypatch.setattr(task, "load_extraction_context", lambda _s, _j: _CTX)
    monkeypatch.setattr(svc, "load_prompt_from_db", lambda _s, _k: "prompt")
    monkeypatch.setattr(svc, "_call_gemini", lambda *_a: result)
    monkeypatch.setattr(svc, "_record_usage", lambda *_a: None)

    svc.run_v102_extraction(session, "job1", recorder=recorder)

    return recorder


def test_run_v102_extraction_hands_thought_summaries_to_the_recorder(monkeypatch):
    result = {"response_text": _response([]), "thought_summaries": ["考え1", "考え2"], "usage_counts": None}

    recorder = _run_extraction_with_result(monkeypatch, result)

    recorder.on_response.assert_called_once_with(result["response_text"], thought_summaries=["考え1", "考え2"])


def test_run_v102_extraction_hands_none_when_the_result_has_no_thought_summaries(monkeypatch):
    result = {"response_text": _response([]), "usage_counts": None}

    recorder = _run_extraction_with_result(monkeypatch, result)

    recorder.on_response.assert_called_once_with(result["response_text"], thought_summaries=None)


# ---------------------------------------------------------------------------
# 価格なし・数ありの件への価格の引き継ぎ（_inherit_price）。DB は使わず、読み取りの失敗と読まない条件だけを見る
# ---------------------------------------------------------------------------
class _SavepointSession:
    """begin_nested を使え、execute を控える。fail_on を含む SQL で例外を出す。"""

    def __init__(self, fail_on: str | None = None):
        self.calls: list[str] = []
        self.fail_on = fail_on

    def begin_nested(self):
        from contextlib import nullcontext

        return nullcontext()

    def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append(sql)
        if self.fail_on and self.fail_on in sql:
            raise RuntimeError("読み取りの失敗（試験用）")
        return SimpleNamespace(first=lambda: None)


def _inherit_values(**overrides) -> dict:
    return {
        "price_normalized": None, "quantity_normalized": 2, "product_id": 42, "pid_resolved": True,
        "condition_id": 11, "status": "In Stock", "price_basis": None, **overrides,
    }


def test_inherit_price_keeps_the_values_when_the_read_raises():
    session = _SavepointSession(fail_on="item_corrections")
    values = _inherit_values()

    result = svc._inherit_price(session, "job1", SimpleNamespace(id="row0", raw_price=None), values)

    assert result == values and result["price_normalized"] is None and result["price_basis"] is None


def test_inherit_price_keeps_the_values_when_begin_nested_raises():
    values = _inherit_values()

    result = svc._inherit_price(object(), "job1", SimpleNamespace(id="row0", raw_price=None), values)  # begin_nested が無い＝例外

    assert result == values


@pytest.mark.parametrize("raw_price", ["37万", " 65,000円 "])
def test_inherit_price_does_not_read_when_raw_price_is_written(raw_price):
    session = _SavepointSession()

    result = svc._inherit_price(session, "job1", SimpleNamespace(id="row0", raw_price=raw_price), _inherit_values())

    assert result["price_normalized"] is None and session.calls == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"price_normalized": 1000}, {"quantity_normalized": None}, {"product_id": None}, {"pid_resolved": False},
        {"condition_id": None}, {"status": svc.STATUS_SOLD_OUT},
    ],
)
def test_inherit_price_does_not_read_when_the_row_is_not_a_target(overrides):
    session = _SavepointSession()

    result = svc._inherit_price(session, "job1", SimpleNamespace(id="row0", raw_price=None), _inherit_values(**overrides))

    assert result == _inherit_values(**overrides) and session.calls == []


# ---- 規則13：同じ投稿の〆が在庫の件を Sold out にする（docs/handoff/v102-shime-same-post-stock/design.md §7 T1） ----
_SAME_POST_STATUS_ENTRIES = [{"canonical": "Sold out", "effect": "EXCLUDE"}]


def _same_post_values(status="In Stock", exclusion=None, product_id=440301, condition_id=14):
    return {"status": status, "exclusion": exclusion, "product_id": product_id, "condition_id": condition_id}


def _same_post_closer(start=1, end=4, raw_price=None, raw_quantity=None, condition_id=14, targets=None):
    item = {"soldout_targets": targets} if targets else {}
    row = SimpleNamespace(id="closer", line_start=start, line_end=end, raw_price=raw_price, raw_quantity=raw_quantity)
    return _same_post_values("Sold out", "excluded", condition_id=condition_id), (item, row)


def _same_post_stock(start=1, end=2, condition_id=14):
    row = SimpleNamespace(id="stock", line_start=start, line_end=end, raw_price="19,000円", raw_quantity="10個")
    return _same_post_values(condition_id=condition_id), ({}, row)


def _same_post_run(closer, stock, decisions=None):
    base_values = [closer[0], stock[0]]
    before = [dict(v) for v in base_values]
    out = svc._sell_out_stock_closed_in_the_same_post(
        [closer[1], stock[1]], base_values, decisions or {}, {}, _SAME_POST_STATUS_ENTRIES,
    )
    assert base_values == before  # 元の base_values は変えない
    return out


def test_same_post_closed_shime_without_price_sells_out_the_stock_in_range():  # ①ゆうきの形
    out = _same_post_run(_same_post_closer(1, 4), _same_post_stock(1, 2))
    assert (out[1]["status"], out[1]["exclusion"]) == ("Sold out", "excluded")
    assert out[0]["status"] == "Sold out"


def test_same_post_closed_keeps_the_stock_when_the_shime_has_its_own_price():  # ②倉田の形
    out = _same_post_run(_same_post_closer(1, 7, raw_price="¥7,000"), _same_post_stock(1, 11))
    assert (out[1]["status"], out[1]["exclusion"]) == ("In Stock", None)


@pytest.mark.parametrize("raw_price, raw_quantity", [("6,000円", None), (None, "400"), ("none", "5セット")])
def test_same_post_closed_keeps_the_stock_when_the_shime_has_a_price_or_quantity(raw_price, raw_quantity):  # ③
    out = _same_post_run(_same_post_closer(1, 4, raw_price=raw_price, raw_quantity=raw_quantity), _same_post_stock(1, 2))
    assert out[1]["status"] == "In Stock"


def test_same_post_closed_keeps_the_stock_when_the_condition_differs():  # ④
    out = _same_post_run(_same_post_closer(1, 4, condition_id=15), _same_post_stock(1, 2, condition_id=14))
    assert out[1]["status"] == "In Stock"


def test_same_post_closed_keeps_the_stock_outside_the_shime_range():  # ⑤
    out = _same_post_run(_same_post_closer(5, 6), _same_post_stock(1, 2))
    assert out[1]["status"] == "In Stock"


def test_same_post_closed_keeps_the_stock_when_a_human_set_its_status():  # ⑥
    decisions = {"stock": svc.Decisions(values=svc.ValueOverrides(status="In Stock"))}
    out = _same_post_run(_same_post_closer(1, 4), _same_post_stock(1, 2), decisions)
    assert (out[1]["status"], out[1]["exclusion"]) == ("In Stock", None)


def test_same_post_closed_does_not_use_a_shime_that_has_soldout_targets():  # ⑦
    out = _same_post_run(_same_post_closer(1, 4, targets=[{"condition_id": 14}]), _same_post_stock(1, 2))
    assert out[1]["status"] == "In Stock"


@pytest.mark.parametrize("human", [svc.Decisions(product_id=1), svc.Decisions(condition_id=14)])
def test_same_post_closed_keeps_the_stock_when_a_human_judged_it(human):  # ⑧
    out = _same_post_run(_same_post_closer(1, 4), _same_post_stock(1, 2), {"stock": human})
    assert out[1]["status"] == "In Stock"


@pytest.mark.parametrize("human", [svc.Decisions(product_id=1), svc.Decisions(condition_id=14)])
def test_same_post_closed_does_not_use_a_shime_that_a_human_judged(human):  # ⑨
    out = _same_post_run(_same_post_closer(1, 4), _same_post_stock(1, 2), {"closer": human})
    assert out[1]["status"] == "In Stock"


# ---------------------------------------------------------------------------
# 〆の件の単位を完売の相手から写す（design.md §13-3 C。(y)〜(cc)）
# ---------------------------------------------------------------------------

_SET_TARGETS = [{**t, "unit_id": 13, "unit_canonical": "Set"} for t in _TARGETS]


def _no_unit_values(**extra) -> dict:
    item = {"unit": "none", "condition": "none", "product_id": 42, "match_status": "matched_soldout_ref", "soldout_targets": _SET_TARGETS, **extra}
    values = _values(item)
    return item, {**values, "review_reasons": "unit_unknown", "needs_review": True}


def test_target_unit_is_copied_when_the_shime_has_no_unit_and_targets_agree():
    # (y)
    item, values = _no_unit_values()
    assert values["unit_id"] is None and values["unit_canonical"] is None
    out = svc._apply_soldout_targets(values, item, None, _CANONICALS)
    assert (out["unit_id"], out["unit_canonical"], out["unit_resolved"]) == (13, "Set", True)
    assert out["review_reasons"] is None and out["needs_review"] is False
    assert values["unit_id"] is None  # 元は変えない


def test_target_unit_is_not_copied_when_targets_have_two_units():
    # (z)
    item, values = _no_unit_values()
    item["soldout_targets"] = [_SET_TARGETS[0], {**_SET_TARGETS[1], "unit_id": 5, "unit_canonical": "BOX"}]
    out = svc._apply_soldout_targets(values, item, None, _CANONICALS)
    assert out["unit_id"] is None and "unit_unknown" in out["review_reasons"]


def test_target_unit_does_not_overwrite_a_unit_written_on_the_shime():
    # (aa)
    item = _soldout_item(soldout_targets=_SET_TARGETS)
    values = _values(item)
    out = svc._apply_soldout_targets(values, item, None, _CANONICALS)
    assert (out["unit_id"], out["unit_canonical"]) == (values["unit_id"], values["unit_canonical"]) == (5, "BOX")


def test_target_unit_is_not_copied_when_a_human_decided():
    # (bb)
    item, values = _no_unit_values()
    assert svc._apply_soldout_targets(values, item, svc.Decisions(condition_id=18), _CANONICALS) is values


def test_targets_without_a_unit_leave_the_values_as_before():
    # (cc)
    item, values = _no_unit_values(soldout_targets=_TARGETS)
    out = svc._apply_soldout_targets(values, item, None, _CANONICALS)
    assert out["unit_id"] is None and out["review_reasons"] == "unit_unknown"


def test_target_unit_is_copied_even_when_the_condition_name_is_unknown_and_keeps_other_reasons():
    item, values = _no_unit_values()
    values = {**values, "review_reasons": "unit_unknown,price_unresolved"}
    out = svc._apply_soldout_targets(values, item, None, {})
    assert out["unit_id"] == 13 and out["review_reasons"] == "price_unresolved" and out["needs_review"] is True


def test_stock_items_sql_reads_the_unit_columns():
    # (dd) 参照する投稿の保存済みの解析結果から単位を読む
    assert "ar.unit_id" in svc._STOCK_ITEMS_SQL and "unit_canonical" in svc._STOCK_ITEMS_SQL


def test_load_stock_items_carries_unit_id_none_and_13_into_the_stock_items():
    # (dd) DB は使わず、行の結果をスタブで返す
    def row(unit_id, unit_canonical):
        return SimpleNamespace(
            source_message_id="m1", source_lines=[3], line_start=3, line_end=3, product_id=5, condition_id=7,
            condition_canonical="New", unit_id=unit_id, unit_canonical=unit_canonical,
        )

    session = MagicMock()
    session.execute.return_value.fetchall.return_value = [row(None, ""), row(13, "Set")]
    found = svc._load_stock_items(session, ["m1"])
    none_item, set_item = found["m1"]
    assert none_item.unit_id is None and none_item.unit_canonical == ""
    assert set_item.unit_id == 13 and set_item.unit_canonical == "Set"
