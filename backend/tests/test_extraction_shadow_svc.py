"""extraction_shadow_svc の単体テスト（DB 不要、Gemini はモック）。

設計: docs/handoff/gemini-extract-role-split/design.md PR-C
"""
from __future__ import annotations

from unittest.mock import MagicMock

from app.services.extraction_judgement_svc import ProductEntry
from app.services.extraction_shadow_svc import run_shadow_for_job

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
        assert row["needs_review"] is False
        assert row["verify_failures"] == []
        session.commit.assert_called_once()


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
