"""要確認タブへの出力（段1）。DB・Google は呼ばない。設計: docs/handoff/review-sheet-export/design.md §4-5。"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.services.tcg_review_sheet_svc import (  # noqa: E402
    REVIEW_SHEET_HEADERS,
    build_review_rows,
    write_review_sheet_sync,
)

LABELS = {"pid_unresolved": "商品を特定できない", "gemini_gap_suspect": "間の行が使われていない"}
RAW = "見出し\nピカチュウ BOX 5,000円 在庫3\n備考の行\n別の行"


def _item(**over) -> dict:
    item = {
        "extraction_item_id": "11111111-0000-0000-0000-000000000001",
        "source_message_id": "22222222-0000-0000-0000-000000000001",
        "provider": "A社",
        "posted_at": datetime(2026, 10, 12, 3, 5, tzinfo=timezone.utc),
        "raw_text": RAW,
        "gemini": {"name": "ピカチュウ", "quantity": "3", "price": "5,000円", "unit": "BOX",
                   "state": "", "memo": "", "span": "L2-3"},
        "system": {"product_title": "ピカチュウBOX", "condition": "Sealed", "unit": "Box"},
        "review_reason_details": [
            {"code": "pid_unresolved", "source": "system", "fix_stage": "analysis", "ackable": True},
            {"code": "gemini_gap_suspect", "source": "system", "fix_stage": "extraction", "ackable": True},
        ],
        "gap_suspect": {
            "gap_lines": [14, 15],
            "candidates": [{"product_id": "1", "name": "商品X"}, {"product_id": "2", "name": "商品Y"}],
        },
    }
    item.update(over)
    return item


def test_build_review_rows_fills_every_column():
    rows = build_review_rows([_item()], LABELS)
    assert rows == [[
        "2026-10-12 12:05",
        "A社",
        "L2-3",
        "ピカチュウ BOX 5,000円 在庫3\n備考の行",
        "5,000円",
        "3",
        "ピカチュウBOX",
        "Sealed",
        "Box",
        "商品を特定できない、間の行が使われていない",
        "L14、L15",
        "商品X、商品Y",
        "11111111-0000-0000-0000-000000000001",
    ]]
    assert len(rows[0]) == len(REVIEW_SHEET_HEADERS) == 13


def test_build_review_rows_without_candidates_or_product():
    item = _item(gap_suspect=None, posted_at=None,
                 system={"product_title": "", "condition": "", "unit": ""})
    row = build_review_rows([item], LABELS)[0]
    assert row[0] == ""
    assert row[6:9] == ["", "", ""]
    assert row[10:12] == ["", ""]


def test_build_review_rows_unknown_code_is_kept_as_is():
    item = _item(review_reason_details=[{"code": "brand_new_code"}, {"code": "pid_unresolved"}])
    assert build_review_rows([item], LABELS)[0][9] == "brand_new_code、商品を特定できない"


def test_build_review_rows_unreadable_span_gives_empty_source():
    item = _item(gemini={"name": "", "quantity": "", "price": "", "unit": "", "state": "", "memo": "", "span": ""})
    row = build_review_rows([item], LABELS)[0]
    assert row[2] == "" and row[3] == ""


def test_build_review_rows_returns_new_list_and_does_not_touch_items():
    items = [_item()]
    snapshot = repr(items)
    build_review_rows(items, LABELS)
    assert repr(items) == snapshot


# ---- 書き込み（安全装置は配信と同じ _write_tab_sync を通る）----

def _sheet(tab_title: str = "要確認"):
    gc = MagicMock()
    sh = MagicMock()
    sh.fetch_sheet_metadata.return_value = {"spreadsheetId": "sid", "properties": {"title": "T"}}
    ws = MagicMock()
    ws.title = tab_title
    gc.open_by_key.return_value = sh
    sh.worksheet.return_value = ws
    return gc, sh, ws


TARGET = {"id": "t1", "name": "配信テスト", "spreadsheet_id": "sid", "sheet_name": "在庫集計",
          "review_sheet_name": "要確認"}


def test_write_review_sheet_writes_review_tab_with_review_headers():
    gc, sh, ws = _sheet()
    rows = build_review_rows([_item()], LABELS)
    with patch("app.services.tcg_distribution_svc._log_sheet_permissions"):
        result = write_review_sheet_sync(gc, MagicMock(), TARGET, rows)
    assert result == {"status": "ok", "rows_written": 1}
    sh.worksheet.assert_called_once_with("要確認")
    ws.clear.assert_called_once()
    written = ws.append_rows.call_args[0][0]
    assert written[0] == REVIEW_SHEET_HEADERS and written[1] == rows[0]
    assert ws.append_rows.call_args.kwargs["value_input_option"] == "RAW"


def test_write_review_sheet_stops_when_tab_is_missing_and_never_creates_it():
    import gspread

    gc, sh, ws = _sheet()
    sh.worksheet.side_effect = gspread.exceptions.WorksheetNotFound
    with patch("app.services.tcg_distribution_svc._log_sheet_permissions"):
        result = write_review_sheet_sync(gc, MagicMock(), TARGET, [])
    assert result["status"] == "error" and "安全装置 #2" in result["error"]
    sh.add_worksheet.assert_not_called()
    ws.clear.assert_not_called()


def test_write_review_sheet_tab_name_mismatch_stops():
    gc, sh, ws = _sheet(tab_title="別のタブ")
    with patch("app.services.tcg_distribution_svc._log_sheet_permissions"):
        result = write_review_sheet_sync(gc, MagicMock(), TARGET, [])
    assert result["status"] == "error" and "安全装置 #4" in result["error"]
    ws.clear.assert_not_called()


def test_write_review_sheet_row_limit_stops():
    from app.services.tcg_distribution_svc import DIST_ROW_LIMIT

    gc, sh, ws = _sheet()
    with patch("app.services.tcg_distribution_svc._log_sheet_permissions"):
        result = write_review_sheet_sync(gc, MagicMock(), TARGET, [["x"]] * (DIST_ROW_LIMIT + 1))
    assert result["status"] == "error" and "安全装置 #5" in result["error"]
    ws.clear.assert_not_called()


def test_write_review_sheet_without_tab_name_does_not_touch_the_sheet():
    gc, sh, ws = _sheet()
    result = write_review_sheet_sync(gc, MagicMock(), dict(TARGET, review_sheet_name=None), [])
    assert result["status"] == "error"
    gc.open_by_key.assert_not_called()


# ---- run_distribution ----

def _db_without_pending():
    empty = MagicMock()
    empty.mappings.return_value.all.return_value = []
    db = AsyncMock()
    db.execute = AsyncMock(return_value=empty)
    return db


async def _run(targets, *, review_result=None, review_collect=None, dist_write=None):
    """配信を、Google・DB 抜きで1回走らせる。戻り値: (結果, 各モック)。"""
    from app.services import tcg_distribution_svc as svc

    mocks = {
        "dist_write": dist_write or MagicMock(return_value={"status": "ok", "rows_written": 2}),
        "review_write": MagicMock(return_value=review_result or {"status": "ok", "rows_written": 1}),
        "collect": review_collect or AsyncMock(return_value=[["row"]]),
        "record": AsyncMock(),
        "notify": AsyncMock(),
    }
    with patch.dict(os.environ, {"TCG_SHEETS_SA_KEY_FILE": "/dev/null"}), \
         patch.object(svc, "load_distribution_settings",
                      new=AsyncMock(return_value={"include_flag_single": "false", "max_age_hours": "48"})), \
         patch.object(svc, "fetch_output_rows", new=AsyncMock(return_value=[["a"], ["b"]])), \
         patch.object(svc, "list_targets", new=AsyncMock(return_value=targets)), \
         patch.object(svc, "_build_gspread_client", return_value=MagicMock()), \
         patch("google.oauth2.service_account.Credentials.from_service_account_file", return_value=MagicMock()), \
         patch.object(svc, "_write_to_target_sync", mocks["dist_write"]), \
         patch("app.services.tcg_review_sheet_svc.write_review_sheet_sync", mocks["review_write"]), \
         patch("app.services.tcg_review_sheet_svc.collect_review_rows", mocks["collect"]), \
         patch.object(svc, "_record_distribution_result", mocks["record"]), \
         patch.object(svc, "_notify_distribution_failure", mocks["notify"]), \
         patch.object(svc.asyncio, "sleep", new=AsyncMock()):
        result = await svc.run_distribution(_db_without_pending())
    return result, mocks


def _target(name: str, review_sheet_name):
    return {"id": f"id-{name}", "name": name, "spreadsheet_id": "sid", "sheet_name": "在庫集計",
            "review_sheet_name": review_sheet_name, "is_active": True}


@pytest.mark.asyncio
async def test_run_distribution_does_not_write_review_tab_when_review_sheet_name_is_null():
    result, m = await _run([_target("A", None), _target("B", None)])
    m["collect"].assert_not_called()
    m["review_write"].assert_not_called()
    assert [r["status"] for r in result["results"]] == ["ok", "ok"] and result["errors"] == []


@pytest.mark.asyncio
async def test_run_distribution_writes_review_tab_only_for_targets_with_a_tab_name_and_fetches_once():
    result, m = await _run([_target("A", None), _target("B", "要確認"), _target("C", "要確認")])
    assert m["collect"].await_count == 1  # 一覧の取得は1回の配信で1回だけ
    assert [c.args[2]["name"] for c in m["review_write"].call_args_list] == ["B", "C"]
    assert [r["status"] for r in result["results"]] == ["ok", "ok", "ok"] and result["errors"] == []
    m["notify"].assert_not_called()


@pytest.mark.asyncio
async def test_run_distribution_result_is_unchanged_when_review_write_fails():
    ok_result, _ = await _run([_target("B", None)])
    result, m = await _run([_target("B", "要確認")], review_result={"status": "error", "error": "タブ無し"})
    assert result["results"] == ok_result["results"]
    assert result["errors"] == []
    assert [c.args[2] for c in m["record"].call_args_list] == ["ok"]  # 配信履歴は ok のまま
    notified = m["notify"].call_args.args[1]
    assert notified[0]["target_name"] == "B（要確認タブ）" and notified[0]["error"] == "タブ無し"


@pytest.mark.asyncio
async def test_run_distribution_result_is_unchanged_when_review_fetch_raises():
    result, m = await _run([_target("B", "要確認")], review_collect=AsyncMock(side_effect=RuntimeError("DB落ち")))
    assert result["results"][0]["status"] == "ok" and result["errors"] == []
    m["review_write"].assert_not_called()
    assert m["notify"].call_args.args[1][0]["error"] == "DB落ち"


@pytest.mark.asyncio
async def test_run_distribution_skips_review_tab_when_delivery_write_failed():
    result, m = await _run(
        [_target("B", "要確認")], dist_write=MagicMock(return_value={"status": "error", "error": "配信NG"})
    )
    m["collect"].assert_not_called()
    m["review_write"].assert_not_called()
    assert result["results"] == [] and result["errors"][0]["error"] == "配信NG"
