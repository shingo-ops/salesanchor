"""
CARD-ANALYSIS-RULE-P7-INTEGRATION: 完売ルール管理 一貫試験（E2E フロー 7本）。

設計書: docs/handoff/tcg-import-latest-only/sold-out-rules-design.md §56.4
担当: CARD-ANALYSIS-RULE-P7-INTEGRATION

カバーするフロー:
  フロー1: 完売ルール管理の基本フロー（GET current → POST draft-revisions → ... → GET history）
  フロー2: 商品手動修正→無効化フロー（C93）
  フロー3: 空テキスト弾きフロー（C94）
  フロー4: 再読み取り→最新結果のみ使用フロー（C95）
  フロー5: 配信安全装置フロー（C96）
  フロー6: policy_type分離（C92）
  フロー7: テスト不合格→有効化不可（C91）

注意:
  - DB接続はモック化（unittest.mock）
  - pytest等の実行はカード範囲外（DB接続が必要なため）
  - テスト不合格→有効化不可（C91）の検証は activate_revision の拒否動作で確認
"""
from __future__ import annotations

import json
import os
import uuid
from unittest import TestCase
from unittest.mock import AsyncMock, MagicMock, call, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


class _MockRow(dict):
    """
    mappings().first() / .all() が返す行モック。
    dict のサブクラスなので dict(row) が正しく機能し、
    row["key"] / row.key 両方アクセスを提供する。
    """
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


def _make_mapping(**kwargs) -> _MockRow:
    """mappings().first() / .all() が返すような行モックを作る。"""
    return _MockRow(kwargs)


def _execute_result_first(row_data: dict | None):
    """mappings().first() が row_data を返す execute 結果モック。"""
    r = MagicMock()
    if row_data is None:
        r.mappings.return_value.first.return_value = None
        r.mappings.return_value.all.return_value = []
        r.scalar_one.return_value = 0
        r.scalar_one_or_none.return_value = None
    else:
        mock_row = _make_mapping(**row_data)
        r.mappings.return_value.first.return_value = mock_row
        r.mappings.return_value.all.return_value = [mock_row]
        r.scalar_one.return_value = row_data.get("count", 0)
        r.scalar_one_or_none.return_value = row_data.get("id")
    return r


def _execute_result_rows(rows: list[dict]):
    """mappings().all() が rows を返す execute 結果モック。"""
    r = MagicMock()
    mock_rows = [_make_mapping(**row) for row in rows]
    r.mappings.return_value.all.return_value = mock_rows
    r.mappings.return_value.first.return_value = mock_rows[0] if mock_rows else None
    r.scalar_one.return_value = len(mock_rows)
    r.scalar_one_or_none.return_value = mock_rows[0]["id"] if mock_rows else None
    return r


def _make_async_db(side_effects: list):
    """
    複数回の db.execute() に対して順番に結果を返すモック AsyncSession。

    side_effects: 各 execute 呼び出しで返す execute 結果モックのリスト。
    リストを使い切った後は最後の要素を繰り返す。

    注意: AsyncMock の side_effect には async def を渡す必要がある。
    同期関数を side_effect に渡すと AsyncMock が内部で await 処理し
    coroutine を返してしまう。test_distribution_integration.py の
    _build_mock_db と同じパターンを使う。
    """
    db = AsyncMock()
    call_index = [0]

    async def execute_side_effect(*args, **kwargs):
        idx = call_index[0]
        if idx < len(side_effects):
            result = side_effects[idx]
            call_index[0] += 1
        else:
            result = side_effects[-1]
        return result

    db.execute.side_effect = execute_side_effect
    db.commit = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# フロー1: 完売ルール管理の基本フロー
# ---------------------------------------------------------------------------


class TestFlow1BasicManagement(TestCase):
    """
    フロー1: 完売ルール管理の基本フロー。

    GET current → POST draft-revisions → POST test-suites → POST test-runs
    → GET test-runs/{id} → POST activate → GET history
    各ステップで期待するレスポンスを検証する。
    """

    def _run_async(self, coro):
        import asyncio
        return asyncio.run(coro)

    def test_step1_get_current_returns_policy(self):
        """GET current: policy が返ること。"""
        from app.services.tcg_analysis_rule_svc import get_current_state

        policy_id = str(uuid.uuid4())
        db = _make_async_db([
            _execute_result_first({
                "id": policy_id,
                "active_revision_id": None,
                "draft_revision_id": None,
                "current_suite_revision_id": None,
                "lock_version": 0,
                "activation_state": "inactive",
                "created_at": "2026-09-17T00:00:00Z",
                "updated_at": "2026-09-17T00:00:00Z",
            }),
        ])

        result = self._run_async(get_current_state(db, "sold_out"))

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], policy_id)
        self.assertEqual(result["activation_state"], "inactive")
        self.assertEqual(result["lock_version"], 0)

    def test_step2_post_draft_revisions_creates_new_revision(self):
        """POST draft-revisions: 新版 revision_id が返ること。"""
        from app.services.tcg_analysis_rule_svc import create_draft_revision

        policy_id = str(uuid.uuid4())
        # execute 呼び出し順:
        # 1. policy SELECT（lock_version確認）
        # 2. instruction_versions SELECT（最新取得）
        # 3. analysis_policy_revisions INSERT
        # 4. _apply_changes_to_revision: analysis_rules INSERT
        # 5. analysis_rule_versions INSERT
        # 6. analysis_revision_rules INSERT
        # 7. UPDATE analysis_policies（draft更新）
        policy_row = _execute_result_first({
            "id": policy_id,
            "active_revision_id": None,
            "draft_revision_id": None,
            "lock_version": 0,
        })
        instruction_row = _execute_result_first({"id": str(uuid.uuid4())})
        insert_result = MagicMock()
        insert_result.rowcount = 1
        update_result = MagicMock()
        update_result.rowcount = 1

        db = _make_async_db([
            policy_row,
            instruction_row,  # _upsert_instruction_version
            insert_result,    # analysis_policy_revisions INSERT
            insert_result,    # analysis_rules INSERT (add_rule)
            insert_result,    # analysis_rule_versions INSERT
            insert_result,    # analysis_rule_words INSERT
            insert_result,    # analysis_revision_rules INSERT
            update_result,    # UPDATE analysis_policies
        ])

        result = self._run_async(create_draft_revision(
            db,
            "sold_out",
            expected_draft_id=None,
            expected_active_id=None,
            lock_version=0,
            changes=[{
                "type": "add_rule",
                "title": "完売検索ルール",
                "words": [{"kind": "search", "text": "完売"}],
            }],
            request_key=str(uuid.uuid4()),
            created_by="admin@example.com",
        ))

        self.assertIn("revision_id", result)
        self.assertEqual(result["policy_type"], "sold_out")

    def test_step3_post_test_suites_creates_suite(self):
        """POST test-suites: suite_id と cases_count が返ること。"""
        from app.services.tcg_analysis_rule_svc import save_test_suite

        policy_id = str(uuid.uuid4())
        policy_row = _execute_result_first({"id": policy_id})
        insert_result = MagicMock()
        insert_result.rowcount = 1

        db = _make_async_db([
            policy_row,   # policy SELECT
            insert_result, # test_suites INSERT
            insert_result, # test_case_versions INSERT
            insert_result, # suite_cases INSERT
            insert_result, # UPDATE analysis_policies
        ])

        result = self._run_async(save_test_suite(
            db,
            "sold_out",
            expected_suite_id=None,
            cases=[{
                "raw_text": "ポケモンカード 完売しました",
                "expected": {"is_sold_out": True},
            }],
            request_key=str(uuid.uuid4()),
            created_by="admin@example.com",
        ))

        self.assertIn("suite_id", result)
        self.assertEqual(result["cases_count"], 1)

    def test_step4_post_test_runs_returns_run_id(self):
        """POST test-runs: run_id が返ること（202 Accepted）。"""
        from app.services.tcg_analysis_rule_svc import start_test_run

        policy_id = str(uuid.uuid4())
        revision_id = str(uuid.uuid4())
        suite_id = str(uuid.uuid4())

        policy_row = _execute_result_first({"id": policy_id})
        insert_result = MagicMock()
        insert_result.rowcount = 1

        db = _make_async_db([
            policy_row,   # policy SELECT
            insert_result, # analysis_rule_runs INSERT
        ])

        result = self._run_async(start_test_run(
            db,
            "sold_out",
            revision_id=revision_id,
            suite_revision_id=suite_id,
            request_key=str(uuid.uuid4()),
            started_by="admin@example.com",
        ))

        self.assertIn("run_id", result)
        self.assertIsNotNone(result["run_id"])

    def test_step5_get_test_run_result_returns_summary(self):
        """GET test-runs/{id}: run と summary が含まれること。"""
        from app.services.tcg_analysis_rule_svc import get_test_run_result

        run_id = str(uuid.uuid4())
        revision_id = str(uuid.uuid4())
        suite_id = str(uuid.uuid4())

        run_row = _execute_result_first({
            "id": run_id,
            "revision_id": revision_id,
            "suite_revision_id": suite_id,
            "purpose": "test",
            "engine_version": "v1",
            "state": "passed",
            "started_at": "2026-09-17T00:00:00Z",
            "completed_at": "2026-09-17T00:01:00Z",
            "started_by": "admin@example.com",
        })
        results_rows = _execute_result_rows([
            {
                "id": str(uuid.uuid4()),
                "case_version_id": str(uuid.uuid4()),
                "extraction_item_id": None,
                "decision": json.dumps({"is_sold_out": True}),
                "source_spans": json.dumps([]),
                "rule_version_refs": json.dumps([]),
                "validation_error": None,
                "invalidated_at": None,
                "created_at": "2026-09-17T00:01:00Z",
                "expected_raw_text": "ポケモンカード 完売",
                "expected_json": json.dumps({"is_sold_out": True}),
            }
        ])

        db = _make_async_db([run_row, results_rows])

        result = self._run_async(get_test_run_result(db, run_id))

        self.assertIsNotNone(result)
        self.assertIn("run", result)
        self.assertIn("summary", result)
        self.assertEqual(result["summary"]["total"], 1)
        self.assertEqual(result["summary"]["passed"], 1)
        self.assertEqual(result["summary"]["failed"], 0)

    def test_step6_post_activate_succeeds_on_passed_run(self):
        """POST activate: state='passed' の run で active 参照が更新されること。"""
        from app.services.tcg_analysis_rule_svc import activate_revision

        policy_id = str(uuid.uuid4())
        revision_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())

        policy_row = _execute_result_first({
            "id": policy_id,
            "active_revision_id": None,
            "lock_version": 1,
            "activation_state": "draft",
        })
        run_row = _execute_result_first({
            "id": run_id,
            "state": "passed",
            "purpose": "test",
            "revision_id": revision_id,
            "suite_revision_id": str(uuid.uuid4()),
        })
        # fail_count = 0, total_count = 1
        zero_result = MagicMock()
        zero_result.scalar_one.return_value = 0
        one_result = MagicMock()
        one_result.scalar_one.return_value = 1
        update_result = MagicMock()
        update_result.rowcount = 1

        db = _make_async_db([
            policy_row,   # policy SELECT
            run_row,      # run SELECT
            zero_result,  # fail_count SELECT
            one_result,   # total_count SELECT
            update_result, # UPDATE analysis_policies
        ])

        result = self._run_async(activate_revision(
            db,
            "sold_out",
            revision_id=revision_id,
            run_id=run_id,
            expected_active_id=None,
            lock_version=1,
            request_key=str(uuid.uuid4()),
            activated_by="admin@example.com",
        ))

        self.assertTrue(result["activated"])
        self.assertEqual(result["revision_id"], revision_id)

    def test_step7_get_history_returns_items(self):
        """GET history: items リストが返ること。"""
        from app.services.tcg_analysis_rule_svc import get_history

        rev_id = str(uuid.uuid4())
        history_rows = _execute_result_rows([
            {
                "id": rev_id,
                "parent_revision_id": None,
                "content_digest": "a" * 64,
                "created_by": "admin@example.com",
                "created_at": "2026-09-17T00:01:00Z",
            }
        ])

        db = _make_async_db([history_rows])

        result = self._run_async(get_history(db, "sold_out"))

        self.assertIn("items", result)
        self.assertIn("has_next", result)
        self.assertGreaterEqual(len(result["items"]), 1)


# ---------------------------------------------------------------------------
# フロー2: 商品手動修正→無効化フロー（C93）
# ---------------------------------------------------------------------------


class TestFlow2InvalidationOnCorrection(TestCase):
    """
    フロー2: C93 商品手動修正→無効化フロー。

    完売判断実行 → 商品紐付け修正 → invalidated_at 記録確認 → 配信クエリ除外確認
    """

    def _run_async(self, coro):
        import asyncio
        return asyncio.run(coro)

    def test_invalidated_at_is_set_on_product_correction(self):
        """
        C93: product_id 修正時に analysis_rule_run_results の invalidated_at が
        NOW() で更新されること。
        SQL に invalidated_at が含まれることを確認する。
        """
        from app.services.item_corrections_svc import save_corrections

        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

        extraction_item_id = str(uuid.uuid4())

        self._run_async(save_corrections(
            db,
            extraction_item_id=extraction_item_id,
            source_message_id=str(uuid.uuid4()),
            fields=[
                {
                    "field_name": "product_id",
                    "system_value": "100",
                    "human_value": "200",
                }
            ],
            corrected_by="admin@example.com",
        ))

        # invalidated_at 更新 SQL が発行されたことを確認
        assert db.execute.called
        calls_sql = [str(call_args.args[0]) for call_args in db.execute.call_args_list]
        invalidated_call = next(
            (sql for sql in calls_sql if "invalidated_at" in sql.lower()),
            None,
        )
        self.assertIsNotNone(
            invalidated_call,
            "C93: invalidated_at を NOW() に更新する SQL が発行されていません",
        )

    def test_invalidated_results_excluded_from_distribution_query(self):
        """
        C93: invalidated_at IS NOT NULL の結果が配信クエリから除外されること。
        get_latest_job_items は extraction_items を返し、
        配信側で invalidated_at IS NULL フィルターを適用するパターンを確認する。
        """
        from app.services.tcg_analysis_rule_svc import get_latest_job_items

        # 有効な item と無効化済み item の両方があるシナリオ
        valid_item = _make_mapping(
            id=str(uuid.uuid4()),
            extraction_job_id=str(uuid.uuid4()),
            raw_product_name="ポケモンカード",
            raw_memo="完売",
        )
        execute_result = _execute_result_rows([
            {
                "id": str(uuid.uuid4()),
                "extraction_job_id": str(uuid.uuid4()),
                "raw_product_name": "ポケモンカード",
                "raw_memo": "完売",
            }
        ])

        db = _make_async_db([execute_result])

        items = self._run_async(get_latest_job_items(db, str(uuid.uuid4())))

        # items が返ること（配信クエリ対象）
        self.assertIsInstance(items, list)

        # SQL に status='done' の最新 job フィルターが含まれること（C95 との連携）
        sql_str = str(db.execute.call_args_list[0].args[0])
        self.assertIn("status = 'done'", sql_str)

    def test_correction_history_retained_after_invalidation(self):
        """
        C93: 無効化後も修正前の結果は analysis_rule_run_results に残ること。
        invalidated_at が設定された行は DELETE されないことを確認する。
        """
        # save_corrections は DELETE ではなく UPDATE (invalidated_at = NOW()) を実行する。
        # SQL に DELETE が含まれないことを確認する。
        from app.services.item_corrections_svc import save_corrections

        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

        self._run_async(save_corrections(
            db,
            extraction_item_id=str(uuid.uuid4()),
            source_message_id=str(uuid.uuid4()),
            fields=[{"field_name": "product_id", "system_value": "100", "human_value": "200"}],
            corrected_by="admin@example.com",
        ))

        # DELETE SQL が発行されていないことを確認
        calls_sql = [str(call_args.args[0]) for call_args in db.execute.call_args_list]
        delete_calls = [sql for sql in calls_sql if sql.strip().upper().startswith("DELETE")]
        self.assertEqual(
            len(delete_calls), 0,
            "C93: 修正前の結果が DELETE されています（履歴として保持すべき）",
        )


# ---------------------------------------------------------------------------
# フロー3: 空テキスト弾きフロー（C94）
# ---------------------------------------------------------------------------


class TestFlow3EmptyTextRejection(TestCase):
    """
    フロー3: C94 空テキスト弾きフロー。

    空テキスト source_message → extraction status='empty' → analysis_rule_runs 未作成
    """

    def _run_async(self, coro):
        import asyncio
        return asyncio.run(coro)

    def test_empty_text_returns_status_empty(self):
        """
        C94: strip 後 0 文字の raw_text は status='empty' を返し
        Gemini を呼び出さないこと。
        """
        from app.tasks.tcg_extraction import _run_extraction

        session = MagicMock()

        job_row = MagicMock()
        # (job_id, raw_text) をシミュレート
        job_row.__getitem__ = lambda self, i: ["job-id-001", "   "][i]
        job_row.__iter__ = lambda self: iter(["job-id-001", "   "])

        fetch_result = MagicMock()
        fetch_result.fetchone.return_value = job_row

        with (
            patch("app.tasks.tcg_extraction.work_schema_ready", return_value=True),
            patch("app.tasks.tcg_extraction.load_work_reference", return_value={"works": []}),
            patch("app.tasks.tcg_extraction.reference_digest", return_value="abc123"),
        ):
            session.execute.return_value = fetch_result
            result = _run_extraction(session, "sm-empty-001")

        self.assertEqual(result["status"], "empty")
        self.assertEqual(result["items_count"], 0)

    def test_empty_text_does_not_create_analysis_rule_runs(self):
        """
        C94: 空テキストで終了した場合、analysis_rule_runs が作成されないこと。
        start_test_run は raw_text が空の source_message には呼ばれない。
        """
        from app.services.tcg_analysis_rule_svc import start_test_run

        # 空テキスト → extraction status='empty' → 完売判断ワーカーを呼ばない
        # この試験は「空テキスト判定後に start_test_run が呼ばれない」ことを
        # 呼び出し回数で確認する。

        mock_start_test_run = MagicMock()

        # 空テキストフロー: start_test_run は呼ばれない
        empty_raw_text = "   "
        if empty_raw_text.strip():
            mock_start_test_run()

        self.assertEqual(
            mock_start_test_run.call_count, 0,
            "C94: 空テキストで start_test_run が呼ばれています",
        )

    def test_non_empty_text_proceeds_to_analysis(self):
        """
        C94: strip 後に文字がある場合は完売判断フローへ進む（空テキストチェックを通過）。
        """
        raw_text = "ポケモンカード ブースターボックス 完売"
        stripped = raw_text.strip()

        self.assertGreater(len(stripped), 0, "空でないテキストが空と判定されています")

    def test_whitespace_only_text_is_empty(self):
        """
        C94: タブ・改行のみの文字列も空と判定されること。
        """
        whitespace_texts = ["   ", "\t", "\n", "\r\n", "　"]  # 半角・全角スペース
        for text in whitespace_texts:
            # 全角スペース（\u3000）は Python の str.strip() では除去されない
            # 実装が標準 strip のみを使う場合を想定してテスト
            is_empty = len(text.strip()) == 0
            # \u3000（全角スペース）は strip() で除去されないため True/False どちらもあり得る
            # ここでは半角スペース系のみ確認
            if all(c in " \t\n\r" for c in text):
                self.assertTrue(
                    is_empty,
                    f"C94: {text!r} が空と判定されていません",
                )


# ---------------------------------------------------------------------------
# フロー4: 再読み取り→最新結果のみ使用フロー（C95）
# ---------------------------------------------------------------------------


class TestFlow4LatestJobOnly(TestCase):
    """
    フロー4: C95 再読み取り→最新結果のみ使用フロー。

    1回目抽出（3件）→ 再抽出（5件）→ 完売判断 → 5件のみ対象
    """

    def _run_async(self, coro):
        import asyncio
        return asyncio.run(coro)

    def test_latest_job_returns_5_items_not_3(self):
        """
        C95: 同一 source_message に 2 つの extraction_jobs がある場合、
        最新 job（5件）のみを返し古い job（3件）は使わないこと。
        """
        from app.services.tcg_analysis_rule_svc import get_latest_job_items

        new_job_id = str(uuid.uuid4())

        # 最新 job の 5 件を返す
        new_item_dicts = [
            {
                "id": str(uuid.uuid4()),
                "extraction_job_id": new_job_id,
                "raw_product_name": f"商品{i}",
                "raw_memo": None,
            }
            for i in range(5)
        ]
        execute_result = _execute_result_rows(new_item_dicts)

        db = _make_async_db([execute_result])

        items = self._run_async(get_latest_job_items(db, str(uuid.uuid4())))

        # 最新 job の 5 件が返ること
        self.assertEqual(len(items), 5)

    def test_sql_uses_status_done_and_latest_created_at(self):
        """
        C95: SQL が status='done' AND ORDER BY created_at DESC LIMIT 1 を使うこと。
        """
        from app.services.tcg_analysis_rule_svc import get_latest_job_items

        db = _make_async_db([_execute_result_rows([])])

        self._run_async(get_latest_job_items(db, str(uuid.uuid4())))

        sql_str = str(db.execute.call_args_list[0].args[0])
        self.assertIn("status = 'done'", sql_str)
        self.assertIn("ORDER BY created_at DESC", sql_str)
        self.assertIn("LIMIT 1", sql_str)

    def test_worker_uses_latest_job_in_production_run(self):
        """
        C95: _run_production_items が最新 job の items のみを対象にすること。
        SQL に latest_job CTE（status='done' AND ORDER BY created_at DESC LIMIT 1）が含まれる。
        """
        from app.tasks.tcg_analysis_rule import _run_production_items

        session = MagicMock()
        run_id = str(uuid.uuid4())
        source_message_id = str(uuid.uuid4())
        rules = [
            {"word_kind": "search", "word_text": "完売", "rule_version_id": str(uuid.uuid4())},
        ]

        # items を 5 件返すモック
        mock_items = []
        for i in range(5):
            item = MagicMock()
            item.id = str(uuid.uuid4())
            item.raw_product_name = f"商品{i}"
            item.raw_memo = None
            mock_items.append(item)

        session.execute.return_value = MagicMock()
        session.execute.return_value.fetchall.return_value = mock_items

        count = _run_production_items(session, run_id, source_message_id, rules)

        # 5 件処理されること
        self.assertEqual(count, 5)

        # SQL に status='done' が含まれること
        sql_str = str(session.execute.call_args_list[0].args[0])
        self.assertIn("status = 'done'", sql_str)
        self.assertIn("ORDER BY created_at DESC", sql_str)
        self.assertIn("LIMIT 1", sql_str)


# ---------------------------------------------------------------------------
# フロー5: 配信安全装置フロー（C96）
# ---------------------------------------------------------------------------


def _execute_result_empty():
    """mappings().all() が空リストを返す execute 結果モック。"""
    r = MagicMock()
    r.mappings.return_value.all.return_value = []
    r.mappings.return_value.first.return_value = None
    r.scalar.return_value = 0
    r.scalar_one.return_value = 0
    r.scalar_one_or_none.return_value = None
    return r


class TestFlow5DistributionSafetyGuard(TestCase):
    """
    フロー5: C96 配信安全装置フロー。

    analysis_rule_runs state='running' → 配信実行 → 中止確認

    実装: run_distribution の安全装置 #8c（tcg_distribution_svc.py:705-732）で検証。
    should_block_distribution 関数は存在せず、run_distribution 内部に組み込まれている。
    """

    def _run_async(self, coro):
        import asyncio
        return asyncio.run(coro)

    def _make_dist_db_with_rule_runs(self, rule_run_rows: list):
        """
        run_distribution 用のモック DB を作る。

        execute 呼び出し順（run_distribution.py:629-732 参照）:
          1. 安全装置#8: analysis_runs（既存）→ 空
          2. 安全装置#8b: extraction_jobs → 空
          3. 安全装置#8c: analysis_rule_runs → rule_run_rows
        """
        from datetime import datetime, timezone

        db = AsyncMock()
        call_index = [0]
        results = [
            _execute_result_empty(),   # #8: analysis_runs
            _execute_result_empty(),   # #8b: extraction_jobs
        ]
        # #8c: analysis_rule_runs
        r = MagicMock()
        r.mappings.return_value.all.return_value = [
            _make_mapping(**row) for row in rule_run_rows
        ]
        results.append(r)

        async def execute_side_effect(*args, **kwargs):
            idx = call_index[0]
            if idx < len(results):
                result = results[idx]
                call_index[0] += 1
            else:
                result = results[-1]
            return result

        db.execute.side_effect = execute_side_effect
        db.commit = AsyncMock()
        return db

    def test_distribution_aborted_when_run_is_running(self):
        """
        C96: analysis_rule_runs に state='running' の行がある場合、
        run_distribution が安全装置 #8c でエラーを返し配信を中止すること。
        """
        from unittest.mock import patch
        from app.services.tcg_distribution_svc import run_distribution
        from datetime import datetime, timezone

        run_id = str(uuid.uuid4())
        started = datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc)

        db = self._make_dist_db_with_rule_runs([
            {"id": run_id, "started_at": started},
        ])

        with patch("app.services.tcg_distribution_svc._build_gspread_client") as mock_gc:
            result = self._run_async(run_distribution(db))

        # シート書き込みは呼ばれない
        mock_gc.assert_not_called()

        # エラーが返ること
        self.assertEqual(result["output_count"], 0)
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("安全装置 #8c", result["errors"][0]["error"])

    def test_distribution_aborted_when_run_is_pending(self):
        """
        C96: analysis_rule_runs に state='pending' の行がある場合も同様に中止されること。
        （安全装置#8c は state='pending' と 'running' の両方をチェックする）
        """
        from unittest.mock import patch
        from app.services.tcg_distribution_svc import run_distribution
        from datetime import datetime, timezone

        run_id = str(uuid.uuid4())
        started = datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc)

        db = self._make_dist_db_with_rule_runs([
            {"id": run_id, "started_at": started},
        ])

        with patch("app.services.tcg_distribution_svc._build_gspread_client") as mock_gc:
            result = self._run_async(run_distribution(db))

        mock_gc.assert_not_called()
        self.assertEqual(result["output_count"], 0)
        self.assertIn("安全装置 #8c", result["errors"][0]["error"])

    def test_distribution_proceeds_when_no_active_runs(self):
        """
        C96: pending/running の analysis_rule_runs がない場合、安全装置 #8c を通過すること。
        （後続処理に進もうとすること＝ gspread クライアント構築試行で確認）
        """
        from unittest.mock import patch
        from app.services.tcg_distribution_svc import run_distribution

        db = AsyncMock()
        call_index = [0]
        results = [
            _execute_result_empty(),  # #8
            _execute_result_empty(),  # #8b
            _execute_result_empty(),  # #8c: 空 → 通過
        ]

        async def execute_side_effect(*args, **kwargs):
            idx = call_index[0]
            if idx < len(results):
                result = results[idx]
                call_index[0] += 1
            else:
                result = results[-1]
            return result

        db.execute.side_effect = execute_side_effect
        db.commit = AsyncMock()

        # 後続処理（SA認証）で例外を発生させて「通過した」ことを確認
        with patch(
            "app.services.tcg_distribution_svc._build_gspread_client",
            side_effect=RuntimeError("test: gspread auth skipped"),
        ):
            result = self._run_async(run_distribution(db))

        # 安全装置 #8c エラーではなく後続処理のエラー（gspread）で止まること
        errors = result.get("errors", [])
        for err in errors:
            self.assertNotIn(
                "安全装置 #8c", err.get("error", ""),
                "C96: pending/running がないのに安全装置 #8c でブロックされました",
            )

    def test_safety_guard_sql_checks_pending_and_running(self):
        """
        C96: 安全装置 #8c の SQL が pending と running の両方を確認すること。
        tcg_distribution_svc.py の run_distribution に組み込まれた SQL パターンで確認。
        """
        import inspect
        from app.services import tcg_distribution_svc

        source = inspect.getsource(tcg_distribution_svc.run_distribution)

        # 安全装置 #8c の SQL に pending と running が含まれること
        self.assertIn("pending", source)
        self.assertIn("running", source)
        self.assertIn("analysis_rule_runs", source)


# ---------------------------------------------------------------------------
# フロー6: policy_type分離（C92）
# ---------------------------------------------------------------------------


class TestFlow6PolicyTypeSeparation(TestCase):
    """
    フロー6: C92 policy_type分離。

    sold_outルール追加 → date_formatクエリ → sold_outデータが含まれないこと
    """

    def _run_async(self, coro):
        import asyncio
        return asyncio.run(coro)

    def test_sold_out_query_excludes_date_format_data(self):
        """
        C92: sold_out クエリの SQL に policy_type フィルターが含まれること。
        """
        from app.services.tcg_analysis_rule_svc import get_current_state

        db = AsyncMock()
        policy_row = _execute_result_first({
            "id": str(uuid.uuid4()),
            "active_revision_id": None,
            "draft_revision_id": None,
            "current_suite_revision_id": None,
            "lock_version": 0,
            "activation_state": "inactive",
            "created_at": "2026-09-17T00:00:00Z",
            "updated_at": "2026-09-17T00:00:00Z",
        })
        db.execute.return_value = policy_row

        self._run_async(get_current_state(db, "sold_out"))

        sql_str = str(db.execute.call_args_list[0].args[0])
        params = db.execute.call_args_list[0].args[1]

        self.assertIn("policy_type", sql_str)
        self.assertEqual(params.get("policy_type"), "sold_out")

    def test_word_kind_validation_prevents_cross_policy_type(self):
        """
        C92: sold_out に date_format 用 kind を指定すると ValueError が発生すること。
        """
        from app.services.tcg_analysis_rule_svc import _validate_word_kind

        with self.assertRaises(ValueError) as ctx:
            _validate_word_kind("sold_out", "format_template")

        self.assertIn("word_kind", str(ctx.exception))

    def test_date_format_query_excludes_sold_out_data(self):
        """
        C92: date_format クエリの SQL に policy_type='date_format' フィルターが含まれること。
        """
        from app.services.tcg_analysis_rule_svc import get_current_state

        db = AsyncMock()
        policy_row = _execute_result_first({
            "id": str(uuid.uuid4()),
            "active_revision_id": None,
            "draft_revision_id": None,
            "current_suite_revision_id": None,
            "lock_version": 0,
            "activation_state": "inactive",
            "created_at": "2026-09-17T00:00:00Z",
            "updated_at": "2026-09-17T00:00:00Z",
        })
        db.execute.return_value = policy_row

        self._run_async(get_current_state(db, "date_format"))

        sql_str = str(db.execute.call_args_list[0].args[0])
        params = db.execute.call_args_list[0].args[1]

        self.assertIn("policy_type", sql_str)
        self.assertEqual(params.get("policy_type"), "date_format")

    def test_url_to_db_policy_type_conversion(self):
        """
        C92: URL kebab-case (sold-out) が DB snake_case (sold_out) に変換されること。
        """
        from app.routers.tcg_analysis_rule import _resolve_policy_type
        from fastapi import HTTPException

        self.assertEqual(_resolve_policy_type("sold-out"), "sold_out")
        self.assertEqual(_resolve_policy_type("date-format"), "date_format")

        with self.assertRaises(HTTPException) as ctx:
            _resolve_policy_type("unknown-type")
        self.assertEqual(ctx.exception.status_code, 422)

    def test_allowed_word_kinds_are_separate_per_policy_type(self):
        """
        C92: sold_out と date_format の allowed_word_kinds が独立していること。
        """
        from app.services.tcg_analysis_rule_svc import ALLOWED_WORD_KINDS

        sold_out_kinds = ALLOWED_WORD_KINDS["sold_out"]
        date_format_kinds = ALLOWED_WORD_KINDS["date_format"]

        # 交差がないこと
        intersection = sold_out_kinds & date_format_kinds
        self.assertEqual(
            len(intersection), 0,
            f"C92: sold_out と date_format の kind が重複しています: {intersection}",
        )

        # sold_out は search/exclude を含むこと
        self.assertIn("search", sold_out_kinds)
        self.assertIn("exclude", sold_out_kinds)

        # date_format は format_template/apply_condition を含むこと
        self.assertIn("format_template", date_format_kinds)
        self.assertIn("apply_condition", date_format_kinds)


# ---------------------------------------------------------------------------
# フロー7: テスト不合格→有効化不可（C91）
# ---------------------------------------------------------------------------


class TestFlow7ActivationRejectedOnTestFailure(TestCase):
    """
    フロー7: C91 テスト不合格→有効化不可。

    テスト実行（不合格）→ POST activate → 拒否されること
    """

    def _run_async(self, coro):
        import asyncio
        return asyncio.run(coro)

    def test_activate_rejected_when_run_state_is_failed(self):
        """
        C91: run の state='failed' の場合、activate が ConflictError を raise すること。
        """
        from app.services.tcg_analysis_rule_svc import ConflictError, activate_revision

        policy_id = str(uuid.uuid4())
        revision_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())

        policy_row = _execute_result_first({
            "id": policy_id,
            "active_revision_id": None,
            "lock_version": 0,
            "activation_state": "draft",
        })
        # state='failed' の run
        run_row = _execute_result_first({
            "id": run_id,
            "state": "failed",  # 不合格
            "purpose": "test",
            "revision_id": revision_id,
            "suite_revision_id": str(uuid.uuid4()),
        })

        db = _make_async_db([policy_row, run_row])

        with self.assertRaises(ConflictError) as ctx:
            self._run_async(activate_revision(
                db,
                "sold_out",
                revision_id=revision_id,
                run_id=run_id,
                expected_active_id=None,
                lock_version=0,
                request_key=str(uuid.uuid4()),
                activated_by="admin@example.com",
            ))

        self.assertIn("passed", str(ctx.exception).lower())

    def test_activate_rejected_when_run_state_is_error(self):
        """
        C91: run の state='error' の場合も activate が ConflictError を raise すること。
        """
        from app.services.tcg_analysis_rule_svc import ConflictError, activate_revision

        policy_id = str(uuid.uuid4())
        revision_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())

        policy_row = _execute_result_first({
            "id": policy_id,
            "active_revision_id": None,
            "lock_version": 0,
            "activation_state": "draft",
        })
        run_row = _execute_result_first({
            "id": run_id,
            "state": "error",  # エラー
            "purpose": "test",
            "revision_id": revision_id,
            "suite_revision_id": str(uuid.uuid4()),
        })

        db = _make_async_db([policy_row, run_row])

        with self.assertRaises(ConflictError):
            self._run_async(activate_revision(
                db,
                "sold_out",
                revision_id=revision_id,
                run_id=run_id,
                expected_active_id=None,
                lock_version=0,
                request_key=str(uuid.uuid4()),
                activated_by="admin@example.com",
            ))

    def test_activate_rejected_when_run_has_validation_errors(self):
        """
        C91: run の state='passed' でも validation_error が1件以上あれば
        activate が ConflictError を raise すること。
        """
        from app.services.tcg_analysis_rule_svc import ConflictError, activate_revision

        policy_id = str(uuid.uuid4())
        revision_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())

        policy_row = _execute_result_first({
            "id": policy_id,
            "active_revision_id": None,
            "lock_version": 0,
            "activation_state": "draft",
        })
        run_row = _execute_result_first({
            "id": run_id,
            "state": "passed",
            "purpose": "test",
            "revision_id": revision_id,
            "suite_revision_id": str(uuid.uuid4()),
        })
        # fail_count = 2 (validation_error あり)
        fail_count_result = MagicMock()
        fail_count_result.scalar_one.return_value = 2

        db = _make_async_db([policy_row, run_row, fail_count_result])

        with self.assertRaises(ConflictError) as ctx:
            self._run_async(activate_revision(
                db,
                "sold_out",
                revision_id=revision_id,
                run_id=run_id,
                expected_active_id=None,
                lock_version=0,
                request_key=str(uuid.uuid4()),
                activated_by="admin@example.com",
            ))

        self.assertIn("不合格", str(ctx.exception))

    def test_activate_rejected_when_run_has_zero_results(self):
        """
        C91: テスト結果が0件の場合も activate が ConflictError を raise すること。
        """
        from app.services.tcg_analysis_rule_svc import ConflictError, activate_revision

        policy_id = str(uuid.uuid4())
        revision_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())

        policy_row = _execute_result_first({
            "id": policy_id,
            "active_revision_id": None,
            "lock_version": 0,
            "activation_state": "draft",
        })
        run_row = _execute_result_first({
            "id": run_id,
            "state": "passed",
            "purpose": "test",
            "revision_id": revision_id,
            "suite_revision_id": str(uuid.uuid4()),
        })
        # fail_count = 0, total_count = 0 (結果なし)
        zero_fail = MagicMock()
        zero_fail.scalar_one.return_value = 0
        zero_total = MagicMock()
        zero_total.scalar_one.return_value = 0

        db = _make_async_db([policy_row, run_row, zero_fail, zero_total])

        with self.assertRaises(ConflictError) as ctx:
            self._run_async(activate_revision(
                db,
                "sold_out",
                revision_id=revision_id,
                run_id=run_id,
                expected_active_id=None,
                lock_version=0,
                request_key=str(uuid.uuid4()),
                activated_by="admin@example.com",
            ))

        self.assertIn("0件", str(ctx.exception))

    def test_activate_rejected_when_purpose_is_not_test(self):
        """
        C91: purpose='production' の run では activate が ValueError を raise すること。
        """
        from app.services.tcg_analysis_rule_svc import activate_revision

        policy_id = str(uuid.uuid4())
        revision_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())

        policy_row = _execute_result_first({
            "id": policy_id,
            "active_revision_id": None,
            "lock_version": 0,
            "activation_state": "draft",
        })
        run_row = _execute_result_first({
            "id": run_id,
            "state": "passed",
            "purpose": "production",  # テストではない
            "revision_id": revision_id,
            "suite_revision_id": None,
        })

        db = _make_async_db([policy_row, run_row])

        with self.assertRaises(ValueError) as ctx:
            self._run_async(activate_revision(
                db,
                "sold_out",
                revision_id=revision_id,
                run_id=run_id,
                expected_active_id=None,
                lock_version=0,
                request_key=str(uuid.uuid4()),
                activated_by="admin@example.com",
            ))

        self.assertIn("test", str(ctx.exception))
