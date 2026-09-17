"""
CARD-ANALYSIS-RULE-P4-DISTRIBUTION: 配信統合試験。

カバー:
  - 安全装置#8c: analysis_rule_runs pending/running中は配信が中止されること（C96）
  - リトライ: 1回目失敗→2回目成功のケースで配信が完了すること（C96）
  - リトライ上限: 4回連続失敗でエラー記録されること（C96）
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_mock_mapping(**kwargs):
    """mappings().all() / .first() が返す行モックを作る。"""
    row = MagicMock()
    row.__getitem__ = lambda self, key: kwargs.get(key)
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


def _execute_result_empty():
    """mappings().all() が空リストを返す execute 結果モック。"""
    r = MagicMock()
    r.mappings.return_value.all.return_value = []
    r.mappings.return_value.first.return_value = None
    r.scalar.return_value = 0
    return r


def _execute_result_rows(rows: list[dict]):
    """mappings().all() が指定行リストを返す execute 結果モック。"""
    r = MagicMock()
    mock_rows = [_make_mock_mapping(**row) for row in rows]
    r.mappings.return_value.all.return_value = mock_rows
    r.mappings.return_value.first.return_value = mock_rows[0] if mock_rows else None
    r.scalar.return_value = len(mock_rows)
    return r


def _build_mock_db(execute_side_effects: list):
    """
    複数回の db.execute() 呼び出しに対して順番に結果を返すモック DB を作る。

    execute_side_effects: 各呼び出しで返す execute 結果モックのリスト。
    リストを使い切った後は最後の要素を繰り返す。
    """
    db = AsyncMock()
    call_counts = {"n": 0}
    results = execute_side_effects

    async def _execute(*args, **kwargs):
        idx = min(call_counts["n"], len(results) - 1)
        call_counts["n"] += 1
        return results[idx]

    db.execute.side_effect = _execute
    db.commit = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# テスト 1: 安全装置#8c — analysis_rule_runs pending/running 中は配信を中止
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", ["pending", "running"])
async def test_safety_guard_8c_blocks_distribution(state: str):
    """
    analysis_rule_runs に pending または running の行が1件以上あれば
    run_distribution が即座にエラーを返し、シート書き込みを行わないこと。
    """
    from app.services.tcg_distribution_svc import run_distribution

    run_id = str(uuid.uuid4())
    started = datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc)

    # execute 呼び出し順:
    #   1. 安全装置#8: analysis_runs → 空
    #   2. 安全装置#8b: extraction_jobs → 空
    #   3. 安全装置#8c: analysis_rule_runs → 1件返す（state=pending/running）
    db = _build_mock_db([
        _execute_result_empty(),    # #8: analysis_runs
        _execute_result_empty(),    # #8b: extraction_jobs
        _execute_result_rows([      # #8c: analysis_rule_runs
            {"id": run_id, "started_at": started},
        ]),
    ])

    with patch("app.services.tcg_distribution_svc._build_gspread_client") as mock_gc:
        result = await run_distribution(db)

    # シート書き込みは呼ばれない
    mock_gc.assert_not_called()

    # エラーが1件返ること
    assert result["output_count"] == 0
    assert len(result["errors"]) == 1
    assert "安全装置 #8c" in result["errors"][0]["error"]
    assert result["results"] == []


async def test_safety_guard_8c_passes_when_no_pending_rule_runs():
    """
    analysis_rule_runs に pending/running 行がなければ
    安全装置#8c を通過し、配信処理が続行すること。
    （後続処理で SA 認証を試みる段階まで進むことで通過を確認する）
    """
    from app.services.tcg_distribution_svc import run_distribution

    # execute 呼び出し順:
    #   1. #8: analysis_runs → 空
    #   2. #8b: extraction_jobs → 空
    #   3. #8c: analysis_rule_runs → 空
    #   4. load_distribution_settings → 空（settings なし）
    #   5. fetch_output_rows → 空（データなし）
    db = _build_mock_db([
        _execute_result_empty(),  # #8
        _execute_result_empty(),  # #8b
        _execute_result_empty(),  # #8c
        _execute_result_empty(),  # load_distribution_settings
        _execute_result_empty(),  # fetch_output_rows
    ])

    # SA 認証で RuntimeError（TCG_SHEETS_SA_KEY_FILE 未設定）が出るところまで進む
    # → #8c はブロックしていないことを確認
    result = await run_distribution(db)

    # #8c によるブロックでないこと（#8c エラーメッセージを含まない）
    for err in result.get("errors", []):
        assert "安全装置 #8c" not in err.get("error", "")


# ---------------------------------------------------------------------------
# テスト 2: リトライ — 1回目失敗→2回目成功で配信完了
# ---------------------------------------------------------------------------


async def test_retry_success_on_second_attempt():
    """
    _write_to_target_sync が1回目 error、2回目 ok を返す場合、
    run_distribution が最終的に success を返すこと。
    """
    from app.services.tcg_distribution_svc import run_distribution

    target = {
        "id": str(uuid.uuid4()),
        "name": "テスト配信先",
        "spreadsheet_id": "SPREAD001",
        "sheet_name": "在庫",
        "is_active": True,
        "sa_key_secret_name": "TCG_SHEETS_SA_KEY_FILE",
    }

    # execute 呼び出し順:
    #   1. #8: analysis_runs → 空
    #   2. #8b: extraction_jobs → 空
    #   3. #8c: analysis_rule_runs → 空
    #   4. load_distribution_settings → 空
    #   5. fetch_output_rows（SELECT）
    #   6. list_targets または get_target
    #   7. _record_distribution_result（UPDATE）
    db_results = [
        _execute_result_empty(),  # #8
        _execute_result_empty(),  # #8b
        _execute_result_empty(),  # #8c
        _execute_result_empty(),  # load_distribution_settings
        _execute_result_empty(),  # fetch_output_rows
        _execute_result_rows([target]),  # list_targets
        _execute_result_empty(),  # _record_distribution_result UPDATE
        _execute_result_empty(),  # commit後の追加呼び出し余裕
    ]
    db = _build_mock_db(db_results)

    write_call_count = {"n": 0}

    def _mock_write_sync(gc, creds, tgt, rows):
        write_call_count["n"] += 1
        if write_call_count["n"] == 1:
            return {"status": "error", "error": "APIタイムアウト"}
        return {"status": "ok", "rows_written": 0}

    with (
        patch("app.services.tcg_distribution_svc._build_gspread_client") as mock_build_gc,
        patch("app.services.tcg_distribution_svc._write_to_target_sync", side_effect=_mock_write_sync),
        patch("os.getenv", return_value="/dummy/key.json"),
        patch("google.oauth2.service_account.Credentials.from_service_account_file"),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_build_gc.return_value = MagicMock()
        result = await run_distribution(db)

    # 2回呼ばれたこと
    assert write_call_count["n"] == 2

    # 最終結果は success
    assert len(result["results"]) == 1
    assert result["results"][0]["status"] == "ok"
    assert result["errors"] == []


# ---------------------------------------------------------------------------
# テスト 3: リトライ上限 — 4回連続失敗でエラー記録
# ---------------------------------------------------------------------------


async def test_retry_exhausted_records_error():
    """
    _write_to_target_sync が4回連続 error を返す場合、
    run_distribution がエラーを記録し Discord 通知を試みること。
    """
    from app.services.tcg_distribution_svc import run_distribution

    target = {
        "id": str(uuid.uuid4()),
        "name": "テスト配信先",
        "spreadsheet_id": "SPREAD001",
        "sheet_name": "在庫",
        "is_active": True,
        "sa_key_secret_name": "TCG_SHEETS_SA_KEY_FILE",
    }

    db_results = [
        _execute_result_empty(),       # #8
        _execute_result_empty(),       # #8b
        _execute_result_empty(),       # #8c
        _execute_result_empty(),       # load_distribution_settings
        _execute_result_empty(),       # fetch_output_rows
        _execute_result_rows([target]),# list_targets
        _execute_result_empty(),       # _record_distribution_result UPDATE
        _execute_result_empty(),       # commit後余裕
    ]
    db = _build_mock_db(db_results)

    write_call_count = {"n": 0}

    def _mock_write_always_fail(gc, creds, tgt, rows):
        write_call_count["n"] += 1
        return {"status": "error", "error": "永続的な書き込みエラー"}

    discord_called = {"n": 0}

    async def _mock_notify(db, errors, output_count):
        discord_called["n"] += 1

    with (
        patch("app.services.tcg_distribution_svc._build_gspread_client") as mock_build_gc,
        patch("app.services.tcg_distribution_svc._write_to_target_sync", side_effect=_mock_write_always_fail),
        patch("app.services.tcg_distribution_svc._notify_distribution_failure", side_effect=_mock_notify),
        patch("os.getenv", return_value="/dummy/key.json"),
        patch("google.oauth2.service_account.Credentials.from_service_account_file"),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_build_gc.return_value = MagicMock()
        result = await run_distribution(db)

    # ちょうど4回呼ばれたこと（リトライ上限）
    assert write_call_count["n"] == 4

    # エラーが記録されること
    assert len(result["errors"]) == 1
    assert "永続的な書き込みエラー" in result["errors"][0]["error"]
    assert result["results"] == []

    # Discord 通知が呼ばれること
    assert discord_called["n"] == 1
