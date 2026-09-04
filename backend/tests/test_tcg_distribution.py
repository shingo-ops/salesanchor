"""
DIST-01 Phase 2 テスト。

カバー:
  A. 安全装置ユニットテスト（同期関数・モック）
     #1/#2: spreadsheetId 不存在 → RuntimeError
     #2:    タブ不存在 → RuntimeError（自動作成しない）
     #4:    タブ名不一致 → RuntimeError
     #5:    DIST_ROW_LIMIT 超過 → RuntimeError
     #8:    再解析未完了 runs あり → 配信中止（run_id + started_at をエラーに含む）
  B. fetch_output_rows FLAG_SINGLE フィルター（バグ修正確認）
     include_flag_single=False → NOT LIKE 'FLAG_%' のみ
     include_flag_single=True  → FLAG_SINGLE を通す OR 条件を含む
  C. ルーター エンドポイント（認証・モック）
     認証なし → 401/403
     配信先 CRUD 正常系
     preview / run 正常系
     設定 CRUD 正常系
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

pytestmark = pytest.mark.asyncio

_TARGET_ID = "aaaaaaaa-0000-0000-0000-000000000001"

# ---------------------------------------------------------------------------
# A. 安全装置ユニットテスト
# ---------------------------------------------------------------------------


def test_verify_spreadsheet_id_not_found():
    """安全装置 #1/#2: SpreadsheetNotFound → RuntimeError"""
    import gspread
    from app.services.tcg_distribution_svc import _verify_spreadsheet_id

    gc = MagicMock()
    gc.open_by_key.side_effect = gspread.exceptions.SpreadsheetNotFound

    with pytest.raises(RuntimeError, match="安全装置 #1/#2"):
        _verify_spreadsheet_id(gc, "nonexistent-id")


def test_verify_spreadsheet_id_mismatch():
    """安全装置 #1: spreadsheetId 不一致 → RuntimeError"""
    from app.services.tcg_distribution_svc import _verify_spreadsheet_id

    gc = MagicMock()
    sh = MagicMock()
    sh.fetch_sheet_metadata.return_value = {
        "spreadsheetId": "actual-id",
        "properties": {"title": "test"},
    }
    gc.open_by_key.return_value = sh

    with pytest.raises(RuntimeError, match="安全装置 #1"):
        _verify_spreadsheet_id(gc, "expected-id")


def test_verify_spreadsheet_id_ok():
    """安全装置 #1: ID 一致 → sh を返す"""
    from app.services.tcg_distribution_svc import _verify_spreadsheet_id

    gc = MagicMock()
    sh = MagicMock()
    sh.fetch_sheet_metadata.return_value = {
        "spreadsheetId": "correct-id",
        "properties": {"title": "Inventory"},
    }
    gc.open_by_key.return_value = sh

    result = _verify_spreadsheet_id(gc, "correct-id")
    assert result is sh


def test_write_to_target_tab_not_found():
    """安全装置 #2: タブ不存在 → RuntimeError（自動作成しない）"""
    import gspread
    from app.services.tcg_distribution_svc import _write_to_target_sync

    gc = MagicMock()
    sh = MagicMock()
    sh.fetch_sheet_metadata.return_value = {
        "spreadsheetId": "sid",
        "properties": {"title": "T"},
    }
    gc.open_by_key.return_value = sh
    sh.worksheet.side_effect = gspread.exceptions.WorksheetNotFound

    creds = MagicMock()
    target = {"spreadsheet_id": "sid", "sheet_name": "NoSuchTab", "name": "test"}

    with patch("app.services.tcg_distribution_svc._log_sheet_permissions"):
        result = _write_to_target_sync(gc, creds, target, [])

    assert result["status"] == "error"
    assert "安全装置 #2" in result["error"]


def test_write_to_target_tab_name_mismatch():
    """安全装置 #4: タブ名不一致 → RuntimeError"""
    from app.services.tcg_distribution_svc import _write_to_target_sync

    gc = MagicMock()
    sh = MagicMock()
    sh.fetch_sheet_metadata.return_value = {
        "spreadsheetId": "sid",
        "properties": {"title": "T"},
    }
    ws = MagicMock()
    ws.title = "ActualTab"
    gc.open_by_key.return_value = sh
    sh.worksheet.return_value = ws

    creds = MagicMock()
    target = {"spreadsheet_id": "sid", "sheet_name": "ExpectedTab", "name": "test"}

    with patch("app.services.tcg_distribution_svc._log_sheet_permissions"):
        result = _write_to_target_sync(gc, creds, target, [])

    assert result["status"] == "error"
    assert "安全装置 #4" in result["error"]


def test_write_to_target_row_limit_exceeded():
    """安全装置 #5: DIST_ROW_LIMIT 超過 → error"""
    from app.services.tcg_distribution_svc import DIST_ROW_LIMIT, _write_to_target_sync

    gc = MagicMock()
    sh = MagicMock()
    sh.fetch_sheet_metadata.return_value = {
        "spreadsheetId": "sid",
        "properties": {"title": "T"},
    }
    ws = MagicMock()
    ws.title = "Sheet1"
    gc.open_by_key.return_value = sh
    sh.worksheet.return_value = ws

    creds = MagicMock()
    target = {"spreadsheet_id": "sid", "sheet_name": "Sheet1", "name": "test"}
    over_limit_rows = [["a"] * 11] * (DIST_ROW_LIMIT + 1)

    with patch("app.services.tcg_distribution_svc._log_sheet_permissions"):
        result = _write_to_target_sync(gc, creds, target, over_limit_rows)

    assert result["status"] == "error"
    assert "安全装置 #5" in result["error"]


def test_write_to_target_ok():
    """正常系: clear + append_rows が呼ばれ rows_written を返す"""
    from app.services.tcg_distribution_svc import DIST_HEADERS, _write_to_target_sync

    gc = MagicMock()
    sh = MagicMock()
    sh.fetch_sheet_metadata.return_value = {
        "spreadsheetId": "sid",
        "properties": {"title": "T"},
    }
    ws = MagicMock()
    ws.title = "Sheet1"
    gc.open_by_key.return_value = sh
    sh.worksheet.return_value = ws

    creds = MagicMock()
    target = {"spreadsheet_id": "sid", "sheet_name": "Sheet1", "name": "test"}
    rows = [["2026-09-03 10:00:00", "", "ピカチュウ", "", "NM", "500", "1", "", "", "2025-08-01", "Pokemon", "A社"]]

    with patch("app.services.tcg_distribution_svc._log_sheet_permissions"):
        result = _write_to_target_sync(gc, creds, target, rows)

    assert result["status"] == "ok"
    assert result["rows_written"] == 1
    ws.clear.assert_called_once()
    ws.append_rows.assert_called_once()
    written = ws.append_rows.call_args[0][0]
    assert written[0] == DIST_HEADERS  # ヘッダーが先頭
    assert written[1] == rows[0]


# ---------------------------------------------------------------------------
# A-8. 安全装置 #8: 再解析完了チェック（run_distribution サービスレベル）
# ---------------------------------------------------------------------------


async def test_run_distribution_blocks_when_pending_analysis_runs():
    """安全装置 #8: completed_at IS NULL の runs があれば配信を中止する。
    エラーメッセージに run_id と started_at が含まれること。"""
    from datetime import datetime, timezone

    from app.services.tcg_distribution_svc import run_distribution

    pending_run_id = "11111111-0000-0000-0000-000000000001"
    pending_started = datetime(2026, 9, 4, 0, 59, 0, tzinfo=timezone.utc)

    mock_row = {"id": pending_run_id, "started_at": pending_started}
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [mock_row]

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    result = await run_distribution(db)

    assert result["output_count"] == 0
    assert len(result["errors"]) == 1
    err_msg = result["errors"][0]["error"]
    assert pending_run_id in err_msg, f"run_id が含まれていない: {err_msg}"
    assert "2026-09-04T00:59:00" in err_msg, f"started_at が含まれていない: {err_msg}"
    assert "再解析未完了" in err_msg


async def test_run_distribution_proceeds_when_no_pending_runs():
    """安全装置 #8: pending runs がゼロなら配信ロジックへ進む（設定ロードを呼ぶ）。"""
    from app.services.tcg_distribution_svc import run_distribution

    # pending = 0
    mock_result_empty = MagicMock()
    mock_result_empty.mappings.return_value.all.return_value = []

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result_empty)

    with patch(
        "app.services.tcg_distribution_svc.load_distribution_settings",
        new=AsyncMock(return_value={"include_flag_single": "false"}),
    ), patch(
        "app.services.tcg_distribution_svc.fetch_output_rows",
        new=AsyncMock(return_value=[]),
    ), patch(
        "app.services.tcg_distribution_svc.list_targets",
        new=AsyncMock(return_value=[]),
    ):
        result = await run_distribution(db)

    # アクティブな配信先なし → errors に「配信先なし」エラーが入るが、#8 ではない
    assert result["output_count"] == 0
    assert all("再解析未完了" not in e["error"] for e in result["errors"])


# ---------------------------------------------------------------------------
# B. fetch_output_rows FLAG_SINGLE フィルター（バグ修正確認）
# ---------------------------------------------------------------------------


def test_fetch_output_rows_flag_filter_exclude():
    """include_flag_single=False → NOT LIKE 'FLAG_%' のみ（FLAG_SINGLE を含まない）"""
    import inspect
    from app.services.tcg_distribution_svc import fetch_output_rows

    src = inspect.getsource(fetch_output_rows)
    # include_flag_single=True 分岐で OR FLAG_SINGLE を通す実装が存在すること
    assert "OR ar.condition_canonical = 'FLAG_SINGLE'" in src
    # False 側は NOT LIKE のみ（AND != FLAG_SINGLE の古い実装がないこと）
    assert "AND ar.condition_canonical != 'FLAG_SINGLE'" not in src


# ---------------------------------------------------------------------------
# C. ルーター エンドポイント
# ---------------------------------------------------------------------------


@pytest.fixture
def super_admin_override():
    from app.main import app
    from app.auth.dependencies import require_super_admin

    async def _bypass():
        return type("User", (), {"email": "admin@example.com", "is_super_admin": True})()

    app.dependency_overrides[require_super_admin] = _bypass
    yield
    app.dependency_overrides.pop(require_super_admin, None)


async def _client():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---- 認証なし ----

async def test_list_targets_requires_auth():
    async with await _client() as c:
        r = await c.get("/api/v1/tcg/distribution/targets")
    assert r.status_code in (401, 403)


async def test_preview_requires_auth():
    async with await _client() as c:
        r = await c.get("/api/v1/tcg/distribution/preview")
    assert r.status_code in (401, 403)


async def test_run_requires_auth():
    async with await _client() as c:
        r = await c.post("/api/v1/tcg/distribution/run")
    assert r.status_code in (401, 403)


async def test_settings_requires_auth():
    async with await _client() as c:
        r = await c.get("/api/v1/tcg/distribution/settings")
    assert r.status_code in (401, 403)


# ---- list_targets ----

async def test_list_targets_ok(super_admin_override):
    with patch(
        "app.routers.tcg_distribution.svc.list_targets",
        new=AsyncMock(return_value=[{"id": _TARGET_ID, "name": "テスト配信先"}]),
    ):
        async with await _client() as c:
            r = await c.get("/api/v1/tcg/distribution/targets")
    assert r.status_code == 200
    assert r.json()[0]["name"] == "テスト配信先"


# ---- create_target ----

async def test_create_target_ok(super_admin_override):
    payload = {
        "id": _TARGET_ID,
        "name": "新配信先",
        "spreadsheet_id": "sid",
        "sheet_name": "Sheet1",
        "is_active": True,
        "sa_key_secret_name": "TCG_SHEETS_SA_KEY_FILE",
        "last_distributed_at": None,
        "last_distributed_count": None,
        "last_result": None,
        "created_at": "2026-09-03T00:00:00+00:00",
        "updated_at": "2026-09-03T00:00:00+00:00",
    }
    with patch(
        "app.routers.tcg_distribution.svc.create_target",
        new=AsyncMock(return_value=payload),
    ):
        async with await _client() as c:
            r = await c.post(
                "/api/v1/tcg/distribution/targets",
                json={"name": "新配信先", "spreadsheet_id": "sid", "sheet_name": "Sheet1"},
            )
    assert r.status_code == 201
    assert r.json()["name"] == "新配信先"


# ---- get_target 404 ----

async def test_get_target_not_found(super_admin_override):
    with patch(
        "app.routers.tcg_distribution.svc.get_target",
        new=AsyncMock(return_value=None),
    ):
        async with await _client() as c:
            r = await c.get(f"/api/v1/tcg/distribution/targets/{_TARGET_ID}")
    assert r.status_code == 404


# ---- soft_delete 404 ----

async def test_delete_target_not_found(super_admin_override):
    with patch(
        "app.routers.tcg_distribution.svc.soft_delete_target",
        new=AsyncMock(return_value=False),
    ):
        async with await _client() as c:
            r = await c.delete(f"/api/v1/tcg/distribution/targets/{_TARGET_ID}")
    assert r.status_code == 404


# ---- soft_delete 204 ----

async def test_delete_target_ok(super_admin_override):
    with patch(
        "app.routers.tcg_distribution.svc.soft_delete_target",
        new=AsyncMock(return_value=True),
    ):
        async with await _client() as c:
            r = await c.delete(f"/api/v1/tcg/distribution/targets/{_TARGET_ID}")
    assert r.status_code == 204


# ---- preview ----

async def test_preview_ok(super_admin_override):
    preview_data = {
        "output_count": 707,
        "note": "test",
        "exclusion": {"flag_series": 50, "pid_unresolved_only": 0, "unit_unresolved_only": 0, "both_unresolved": 0},
        "flag_gate": {"gate_status": "insufficient_samples"},
        "settings": {"include_flag_single": "false"},
    }
    with patch(
        "app.routers.tcg_distribution.svc.fetch_preview_data",
        new=AsyncMock(return_value=preview_data),
    ):
        async with await _client() as c:
            r = await c.get("/api/v1/tcg/distribution/preview")
    assert r.status_code == 200
    assert r.json()["output_count"] == 707


# ---- run_distribution_all ----

async def test_run_distribution_all_ok(super_admin_override):
    run_result = {
        "started_at": "2026-09-03T10:00:00+00:00",
        "output_count": 707,
        "results": [{"target_id": _TARGET_ID, "target_name": "test", "status": "ok", "rows_written": 707}],
        "errors": [],
    }
    with patch(
        "app.routers.tcg_distribution.svc.run_distribution",
        new=AsyncMock(return_value=run_result),
    ):
        async with await _client() as c:
            r = await c.post("/api/v1/tcg/distribution/run")
    assert r.status_code == 200
    assert r.json()["output_count"] == 707
    assert r.json()["errors"] == []


# ---- run_distribution specific target ----

async def test_run_distribution_target_ok(super_admin_override):
    run_result = {
        "started_at": "2026-09-03T10:00:00+00:00",
        "output_count": 707,
        "results": [{"target_id": _TARGET_ID, "status": "ok", "rows_written": 707}],
        "errors": [],
    }
    mock_run = AsyncMock(return_value=run_result)
    with patch("app.routers.tcg_distribution.svc.run_distribution", new=mock_run):
        async with await _client() as c:
            r = await c.post(f"/api/v1/tcg/distribution/run/{_TARGET_ID}")
    assert r.status_code == 200
    # target_id が正しく渡されること
    mock_run.assert_awaited_once()
    _, kwargs = mock_run.call_args
    assert kwargs["target_id"] == _TARGET_ID


# ---- list_settings ----

async def test_list_settings_ok(super_admin_override):
    settings = [
        {"key": "include_flag_single", "value": "false", "note": "...", "updated_at": "2026-09-03T00:00:00+00:00"}
    ]
    with patch(
        "app.routers.tcg_distribution.svc.list_settings",
        new=AsyncMock(return_value=settings),
    ):
        async with await _client() as c:
            r = await c.get("/api/v1/tcg/distribution/settings")
    assert r.status_code == 200
    assert r.json()[0]["key"] == "include_flag_single"


# ---- update_setting 404 ----

async def test_update_setting_not_found(super_admin_override):
    with patch(
        "app.routers.tcg_distribution.svc.update_setting",
        new=AsyncMock(return_value=None),
    ):
        async with await _client() as c:
            r = await c.put(
                "/api/v1/tcg/distribution/settings/nonexistent_key",
                json={"value": "true"},
            )
    assert r.status_code == 404


# ---- update_setting ok ----

async def test_update_setting_ok(super_admin_override):
    updated = {"key": "include_flag_single", "value": "true", "note": "...", "updated_at": "2026-09-03T01:00:00+00:00"}
    with patch(
        "app.routers.tcg_distribution.svc.update_setting",
        new=AsyncMock(return_value=updated),
    ):
        async with await _client() as c:
            r = await c.put(
                "/api/v1/tcg/distribution/settings/include_flag_single",
                json={"value": "true"},
            )
    assert r.status_code == 200
    assert r.json()["value"] == "true"
