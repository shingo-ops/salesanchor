"""extraction_shadow_svc の単体テスト（DB 不要、Gemini はモック）。

設計: docs/handoff/gemini-extract-role-split/design.md PR-C
"""
from __future__ import annotations

from unittest.mock import MagicMock

from app.services.extraction_judgement_svc import ProductEntry
from app.services.extraction_shadow_svc import run_shadow_for_job
from app.services.llm_budget import UsageCounts

_RAW_COPY_HEADER_LINE = (
    "RAW_PRODUCT_NAME｜RAW_PRICE｜RAW_UNIT｜RAW_QUANTITY｜RAW_STATE｜RAW_SHIP｜RAW_MULTI｜"
    "RAW_SOURCE_LINE_SPAN｜RAW_HEADING_LINE_SPAN"
)


def _product(id_=1, product_code=None, mark=None, work_id=None, search_keywords=(), exclude_keywords=()):
    return ProductEntry(
        id=id_, product_code=product_code, mark=mark, work_id=work_id,
        search_keywords=tuple(search_keywords), exclude_keywords=tuple(exclude_keywords),
    )


def _patch_common(monkeypatch, *, products, raw_copy_response, raw_copy_side_effect=None):
    import app.services.extraction_shadow_svc as svc

    if raw_copy_side_effect is not None:
        monkeypatch.setattr(svc, "call_gemini_raw_copy", raw_copy_side_effect)
    else:
        monkeypatch.setattr(
            svc, "call_gemini_raw_copy",
            lambda raw_text, **kw: {"response_text": raw_copy_response, "input_tokens": 1, "output_tokens": 1},
        )
    monkeypatch.setattr(svc, "load_product_entries", lambda session: products)
    monkeypatch.setattr(svc, "load_condition_entries", lambda session: [])
    monkeypatch.setattr(svc, "load_status_master", lambda session: [])
    monkeypatch.setattr(svc, "load_note_master", lambda session: [])
    monkeypatch.setattr(svc, "load_lookup_maps", lambda session: ({}, {}, {}, {}, {}, {}))
    return svc


def _mock_session():
    session = MagicMock()
    return session


class TestRunShadowForJobMatched:
    def test_single_block_matches_by_search_keyword(self, monkeypatch):
        # Arrange
        raw_text = "商品A 1500円 3枚 未使用"
        response = (
            _RAW_COPY_HEADER_LINE + "\n"
            "商品A｜1500円｜枚｜3｜未使用｜none｜none｜L0001｜none\n"
        )
        product = _product(id_=1, work_id=7, search_keywords=("商品A",))
        svc = _patch_common(monkeypatch, products=[product], raw_copy_response=response)
        session = _mock_session()
        inserted_results = {}

        def fake_insert_run(session, **kwargs):
            return "run-1"

        def fake_insert_results(session, run_id, results):
            inserted_results["run_id"] = run_id
            inserted_results["results"] = results

        monkeypatch.setattr(svc, "insert_shadow_run", fake_insert_run)
        monkeypatch.setattr(svc, "insert_shadow_results", fake_insert_results)

        # Act
        result = run_shadow_for_job(
            session, "ej-1", raw_text=raw_text, supplier_context=None, knowledge_links=None,
        )

        # Assert
        assert result["status"] == "completed"
        assert result["blocks"] == 1
        row = inserted_results["results"][0]
        assert row["match_status"] == "matched"
        assert row["product_id"] == 1
        assert row["work_id"] == 7
        # 単位の別名が空の環境なので「3枚」の 3 は目印なしで補われ、数量は確認に回る（quantity_unmarked）。
        assert row["needs_review"] is True
        assert row["review_items"] == [
            {"item": "price_qty", "reason": "quantity_unmarked", "candidates": []}
        ]
        assert row["verify_failures"] == []
        session.commit.assert_called_once()


class TestRunShadowForJobUsageLedger:
    """ADR-1004: insert_shadow_run は tokens/cost を書かず、代わりに
    record_usage_event_sync(purpose='line_extraction_shadow') に1行書く。
    design.md §3-2: 応答が無い失敗は行を作らない。"""

    def test_completed_run_writes_one_ledger_row_with_run_id(self, monkeypatch):
        # Arrange
        raw_text = "商品A 1500円 3枚 未使用"
        response = (
            _RAW_COPY_HEADER_LINE + "\n"
            "商品A｜1500円｜枚｜3｜未使用｜none｜none｜L0001｜none\n"
        )
        product = _product(id_=1, work_id=7, search_keywords=("商品A",))
        svc = _patch_common(
            monkeypatch, products=[product], raw_copy_response=response,
            raw_copy_side_effect=lambda raw_text, **kw: {
                "response_text": response,
                "input_tokens": 100, "output_tokens": 40,
                "usage_counts": UsageCounts(prompt_tokens=100, candidates_tokens=40),
            },
        )
        session = _mock_session()
        monkeypatch.setattr(svc, "insert_shadow_run", lambda session, **kwargs: "run-tokens")
        monkeypatch.setattr(svc, "insert_shadow_results", lambda session, run_id, results: None)
        recorded = {}

        def fake_record(session, **kwargs):
            recorded.update(kwargs)
            return "usage-event-1"

        monkeypatch.setattr(svc, "record_usage_event_sync", fake_record)

        # Act
        result = run_shadow_for_job(
            session, "ej-tokens", raw_text=raw_text, supplier_context=None, knowledge_links=None,
        )

        # Assert
        assert result["status"] == "completed"
        assert recorded["purpose"] == "line_extraction_shadow"
        assert recorded["extraction_shadow_run_id"] == "run-tokens"
        assert recorded["counts"].prompt_tokens == 100
        assert recorded["counts"].candidates_tokens == 40

    def test_failed_run_still_writes_ledger_row_when_gemini_call_succeeded(self, monkeypatch):
        # Arrange: Gemini 呼び出しは成功したがパースに失敗するケース（usage は分かっている）
        svc = _patch_common(
            monkeypatch, products=[], raw_copy_response="not a valid header at all",
            raw_copy_side_effect=lambda raw_text, **kw: {
                "response_text": "not a valid header at all",
                "input_tokens": 30, "output_tokens": 5,
                "usage_counts": UsageCounts(prompt_tokens=30, candidates_tokens=5),
            },
        )
        session = _mock_session()
        monkeypatch.setattr(svc, "insert_shadow_run", lambda session, **kwargs: "run-fail-tokens")
        recorded = {}

        def fake_record(session, **kwargs):
            recorded.update(kwargs)
            return "usage-event-2"

        monkeypatch.setattr(svc, "record_usage_event_sync", fake_record)

        # Act
        result = run_shadow_for_job(
            session, "ej-fail-tokens", raw_text="行A", supplier_context=None, knowledge_links=None,
        )

        # Assert
        assert result["status"] == "failed"
        assert result["error_code"] == "PARSE_FAILED"
        assert recorded["extraction_shadow_run_id"] == "run-fail-tokens"
        assert recorded["counts"].prompt_tokens == 30

    def test_failed_run_writes_no_ledger_row_when_gemini_call_itself_failed(self, monkeypatch):
        # Arrange: Gemini 呼び出し自体が失敗 -> usage 不明。行を作らない（design.md: 推測で作らない）。
        import app.services.extraction_shadow_svc as svc

        def raise_gemini(raw_text, **kw):
            raise RuntimeError("Gemini API 呼び出し失敗")

        monkeypatch.setattr(svc, "call_gemini_raw_copy", raise_gemini)
        session = _mock_session()
        monkeypatch.setattr(svc, "insert_shadow_run", lambda session, **kwargs: "run-fail-no-tokens")
        record_calls = []
        monkeypatch.setattr(
            svc, "record_usage_event_sync",
            lambda session, **kwargs: record_calls.append(kwargs) or "usage-event-3",
        )

        # Act
        result = run_shadow_for_job(
            session, "ej-fail-no-tokens", raw_text="行A", supplier_context=None, knowledge_links=None,
        )

        # Assert
        assert result["status"] == "failed"
        assert result["error_code"] == "GEMINI_CALL_FAILED"
        assert record_calls == []


class TestRunShadowForJobAmbiguousUnmatched:
    def test_ambiguous_when_two_products_match(self, monkeypatch):
        # Arrange
        raw_text = "商品A 商品B 1500円"
        response = (
            _RAW_COPY_HEADER_LINE + "\n"
            "商品｜1500円｜枚｜1｜none｜none｜none｜L0001｜none\n"
        )
        p1 = _product(id_=1, search_keywords=("商品A",))
        p2 = _product(id_=2, search_keywords=("商品B",))
        svc = _patch_common(monkeypatch, products=[p1, p2], raw_copy_response=response)
        session = _mock_session()
        captured = {}
        monkeypatch.setattr(svc, "insert_shadow_run", lambda session, **kw: "run-2")
        monkeypatch.setattr(
            svc, "insert_shadow_results",
            lambda session, run_id, results: captured.update(results=results),
        )

        # Act
        result = run_shadow_for_job(
            session, "ej-2", raw_text=raw_text, supplier_context=None, knowledge_links=None,
        )

        # Assert
        assert result["status"] == "completed"
        row = captured["results"][0]
        assert row["match_status"] == "ambiguous"
        assert row["product_id"] is None
        assert row["needs_review"] is True
        assert row["review_items"][0]["item"] == "product"

    def test_unmatched_when_no_product_matches(self, monkeypatch):
        # Arrange
        raw_text = "謎の商品 1500円"
        response = (
            _RAW_COPY_HEADER_LINE + "\n"
            "謎の商品｜1500円｜枚｜1｜none｜none｜none｜L0001｜none\n"
        )
        p1 = _product(id_=1, search_keywords=("該当なし",))
        svc = _patch_common(monkeypatch, products=[p1], raw_copy_response=response)
        session = _mock_session()
        captured = {}
        monkeypatch.setattr(svc, "insert_shadow_run", lambda session, **kw: "run-3")
        monkeypatch.setattr(
            svc, "insert_shadow_results",
            lambda session, run_id, results: captured.update(results=results),
        )

        # Act
        run_shadow_for_job(
            session, "ej-3", raw_text=raw_text, supplier_context=None, knowledge_links=None,
        )

        # Assert
        row = captured["results"][0]
        assert row["match_status"] == "unmatched"
        assert row["needs_review"] is True


class TestRunShadowForJobVerifyFailure:
    def test_verify_copied_failure_marks_needs_review(self, monkeypatch):
        # Arrange: Gemini が原文に無い価格を書き写した（検証失敗）
        raw_text = "商品A 未使用"
        response = (
            _RAW_COPY_HEADER_LINE + "\n"
            "商品A｜9999999円｜枚｜1｜未使用｜none｜none｜L0001｜none\n"
        )
        product = _product(id_=1, search_keywords=("商品A",))
        svc = _patch_common(monkeypatch, products=[product], raw_copy_response=response)
        session = _mock_session()
        captured = {}
        monkeypatch.setattr(svc, "insert_shadow_run", lambda session, **kw: "run-4")
        monkeypatch.setattr(
            svc, "insert_shadow_results",
            lambda session, run_id, results: captured.update(results=results),
        )

        # Act
        run_shadow_for_job(
            session, "ej-4", raw_text=raw_text, supplier_context=None, knowledge_links=None,
        )

        # Assert
        row = captured["results"][0]
        assert "raw_price" in row["verify_failures"]
        assert row["needs_review"] is True
        assert any(item["item"] == "verify_copied" for item in row["review_items"])


class TestRunShadowForJobExceptionIsolation:
    def test_gemini_call_failure_is_recorded_and_does_not_raise(self, monkeypatch):
        # Arrange
        import app.services.extraction_shadow_svc as svc

        def raise_gemini(raw_text, **kw):
            raise RuntimeError("Gemini API 呼び出し失敗")

        monkeypatch.setattr(svc, "call_gemini_raw_copy", raise_gemini)
        recorded = {}
        monkeypatch.setattr(
            svc, "insert_shadow_run",
            lambda session, **kw: recorded.update(kw) or "run-fail",
        )
        session = _mock_session()

        # Act
        result = run_shadow_for_job(
            session, "ej-5", raw_text="行A", supplier_context=None, knowledge_links=None,
        )

        # Assert: 例外は伝播せず、failed として記録される
        assert result["status"] == "failed"
        assert result["error_code"] == "GEMINI_CALL_FAILED"
        assert recorded["status"] == "failed"
        session.commit.assert_called_once()

    def test_parse_failure_is_recorded_and_does_not_raise(self, monkeypatch):
        # Arrange
        svc = _patch_common(
            monkeypatch, products=[], raw_copy_response="not a valid header at all",
        )
        recorded = {}
        monkeypatch.setattr(
            svc, "insert_shadow_run",
            lambda session, **kw: recorded.update(kw) or "run-fail",
        )
        session = _mock_session()

        # Act
        result = run_shadow_for_job(
            session, "ej-6", raw_text="行A", supplier_context=None, knowledge_links=None,
        )

        # Assert
        assert result["status"] == "failed"
        assert result["error_code"] == "PARSE_FAILED"
        session.commit.assert_called_once()

    def test_persist_failure_rolls_back_and_does_not_raise(self, monkeypatch):
        # Arrange: 判定は成功するが永続化（insert_shadow_run）で例外
        raw_text = "商品A 未使用"
        response = (
            _RAW_COPY_HEADER_LINE + "\n"
            "商品A｜100円｜枚｜1｜未使用｜none｜none｜L0001｜none\n"
        )
        product = _product(id_=1, search_keywords=("商品A",))
        svc = _patch_common(monkeypatch, products=[product], raw_copy_response=response)

        def raise_insert(session, **kw):
            raise RuntimeError("relation \"extraction_shadow_runs\" does not exist")

        monkeypatch.setattr(svc, "insert_shadow_run", raise_insert)
        session = _mock_session()

        # Act
        result = run_shadow_for_job(
            session, "ej-7", raw_text=raw_text, supplier_context=None, knowledge_links=None,
        )

        # Assert
        assert result["status"] == "failed"
        assert result["error_code"] == "JUDGEMENT_FAILED"
        session.rollback.assert_called_once()


class TestInsertShadowResultsShape:
    def test_deletes_existing_run_results_before_insert(self, monkeypatch):
        # Arrange
        from app.services.extraction_shadow_svc import insert_shadow_results

        session = _mock_session()
        results = [
            {
                "line_start": 1, "line_end": 1, "match_status": "matched", "needs_review": False,
            }
        ]

        # Act
        insert_shadow_results(session, "run-x", results)

        # Assert: 最初の execute が DELETE、その後 INSERT が呼ばれる
        first_call_sql = str(session.execute.call_args_list[0].args[0])
        assert "DELETE FROM public.extraction_shadow_results" in first_call_sql
        assert session.execute.call_count == 2  # DELETE + 1件分のINSERT


# ---------------------------------------------------------------------------
# 価格・数量の決定と、ルールのない仕入元の試運転スキップ（設計 追補2）
# ---------------------------------------------------------------------------

import pytest  # noqa: E402

from app.services.extraction_shadow_svc import (  # noqa: E402
    _VERIFY_FIELDS,
    _judge_block,
    has_required_supplier_rule,
)

_FULL_RULE = {
    "extraction_price_format": "円",
    "extraction_qty_format": "在庫",
    "extraction_order_pattern": '["price","@","quantity"]',
}


class TestHasRequiredSupplierRule:
    def test_true_when_all_three_filled(self):
        assert has_required_supplier_rule(_FULL_RULE) is True

    @pytest.mark.parametrize("missing", list(_FULL_RULE))
    @pytest.mark.parametrize("empty_value", [None, "", "  \n"])
    def test_false_when_any_of_three_is_blank(self, missing, empty_value):
        context = {**_FULL_RULE, missing: empty_value}
        assert has_required_supplier_rule(context) is False

    def test_false_when_context_is_none_or_empty(self):
        assert has_required_supplier_rule(None) is False
        assert has_required_supplier_rule({}) is False


def test_verify_fields_include_raw_quantity():
    assert "raw_quantity" in _VERIFY_FIELDS


def _judge(block_text_value, item, *, unit_aliases=("BOX",), order=None):
    return _judge_block(
        {
            "line_start": 1, "line_end": 1, "raw_product_name": "商品A", "raw_unit": "",
            "raw_state": "", "raw_ship": "", "raw_multi": "", "raw_price": "", "raw_quantity": "",
            **item,
        },
        block_text_value,
        products=[], cond_entries=[], cond_canonical_to_uuid={}, unit_alias_to_info={},
        status_entries=[], note_entries=[], unit_aliases=unit_aliases, order=order,
    )


class TestJudgeBlockPriceQty:
    def test_confirmed_values_are_normalized_without_price_qty_review_item(self):
        row = _judge("商品A 27,500×18BOX", {"raw_price": "27,500", "raw_quantity": "18BOX"})
        assert (row["price_normalized"], row["quantity_normalized"]) == (27500, 18)
        assert all(item["item"] != "price_qty" for item in row["review_items"])
        assert row["evidence"]["price_qty"]["basis"] == "marker"

    def test_adds_price_qty_review_item_when_values_are_ambiguous(self):
        row = _judge("10900@152", {"raw_price": "10900", "raw_quantity": "152"}, order=None)
        items = [i for i in row["review_items"] if i["item"] == "price_qty"]
        assert items == [{"item": "price_qty", "reason": "no_order_rule", "candidates": []}]
        assert row["needs_review"] is True
        assert row["price_normalized"] is None and row["quantity_normalized"] is None
        assert row["evidence"]["price_qty"]["reasons"] == ["no_order_rule"]

    def test_order_from_rule_decides_price_and_quantity(self):
        row = _judge("10900@152", {"raw_price": "10900", "raw_quantity": "152"}, order="price_first")
        assert (row["price_normalized"], row["quantity_normalized"]) == (10900, 152)
        assert row["evidence"]["price_qty"]["basis"] == "rule"


def _judge_with_product(raw_text, item, line_span, heading_span):
    return _judge_block(
        {
            "line_start": line_span[0], "line_end": line_span[1],
            "heading_line_start": heading_span[0], "heading_line_end": heading_span[1],
            "raw_product_name": "", "raw_unit": "", "raw_state": "", "raw_ship": "",
            "raw_multi": "", "raw_price": "", "raw_quantity": "",
            **item,
        },
        raw_text,
        products=[_product(id_=7, search_keywords=("スノーハザード",))],
        cond_entries=[], cond_canonical_to_uuid={}, unit_alias_to_info={},
        status_entries=[], note_entries=[], unit_aliases=("BOX",), order=None,
    )


_HEADING_NAME = "拡張パック「スノーハザード」(SV2P)"


class TestJudgeBlockProductName:
    def test_heading_only_name_matches_and_requires_review(self):
        raw = f"■{_HEADING_NAME}\n3BOX@13,300円[通常品]"
        row = _judge_with_product(raw, {"raw_product_name": _HEADING_NAME}, (2, 2), (1, 1))
        assert row["match_status"] == "matched"
        assert row["product_id"] == 7
        assert row["evidence"]["name_source"] == "HEADING"
        assert row["needs_review"] is True
        assert {"item": "product_heading", "reason": "heading_name", "candidates": []} in row["review_items"]

    def test_name_in_block_keeps_current_result(self):
        raw = "■見出し\nスノーハザード 3BOX@13,300円"
        row = _judge_with_product(raw, {"raw_product_name": "スノーハザード"}, (2, 2), (1, 1))
        assert row["match_status"] == "matched"
        assert row["evidence"]["name_source"] == "BLOCK"
        assert all(i["item"] != "product_heading" for i in row["review_items"])

    def test_name_missing_from_raw_text_stays_unmatched(self):
        raw = "■見出し\n3BOX@13,300円"
        row = _judge_with_product(raw, {"raw_product_name": "スノーハザード"}, (2, 2), (1, 1))
        assert row["match_status"] == "unmatched"
        assert row["evidence"]["name_source"] == "NONE"
