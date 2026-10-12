"""型番の重なり警告を、各入口（新規・更新・CSV 新規・CSV 更新）が返すことの試験。

判定そのものは test_tcg_product_code_collision_svc.py。ここでは入口ごとの配線だけを見る。
update_product_detail の実 DB 試験は test_tcg_product_code_collision_pg.py（CI の PG で実行）。
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import tcg_product_import_svc as importer
from app.services import tcg_product_master_svc as master
from app.services import tcg_product_roundtrip_svc as roundtrip
from tests.test_tcg_product_roundtrip import file_for, snapshot

pytestmark = pytest.mark.asyncio

COLLISION = {
    "product_id": "5",
    "name": "相手",
    "work_name": "作品",
    "matched_value": "ST01",
    "matched_field": "mark",
    "suggest_add_to_this": ["相手"],
    "suggest_add_to_other": ["自分"],
    "already_excluded_by_this": [],
    "already_excluded_by_other": [],
}


async def test_create_product_returns_code_collisions_without_blocking(monkeypatch):
    def result(row):
        return SimpleNamespace(fetchone=MagicMock(return_value=row))

    calls = 0

    async def execute(query, params=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            return result(SimpleNamespace(name_ja="ワンピース"))
        if calls == 3:
            return result(SimpleNamespace(id="1", int_id=77))
        if calls == 7:
            return result(SimpleNamespace(id=77))
        return result(None)

    db = SimpleNamespace(execute=AsyncMock(side_effect=execute), commit=AsyncMock())
    finder = AsyncMock(return_value=[COLLISION])
    monkeypatch.setattr(master, "check_duplicates", AsyncMock(return_value={"candidates": []}))
    monkeypatch.setattr(master, "_next_pm_code", AsyncMock(return_value="PM0100"))
    monkeypatch.setattr(master, "find_code_collisions", finder)

    out = await master.create_product(
        db, extraction_item_id="", source_message_id="", product_kind_id=1, work_id=1,
        manufacturer_id="m", product_category_id="c", japanese_title=" 新商品 ",
        release_date=None, search_keywords="語1, 語2,", exclude_keywords="除1", mark="ST01",
    )

    assert out == {"ok": True, "product_id": "77", "code_collisions": [COLLISION]}
    kwargs = finder.await_args.kwargs
    assert kwargs["mark"] == "ST01"
    assert kwargs["name"] == "新商品"
    assert kwargs["search_keywords"] == ["語1", "語2"]
    assert kwargs["exclude_keywords"] == ["除1"]
    assert kwargs["exclude_product_id"] == 77


async def test_csv_new_preview_adds_one_warning_per_colliding_product(monkeypatch):
    row = {
        "row_no": "1", "mark": "ST-01", "japanese_title": "新商品", "english_title": "",
        "release_date": "2026-01-01", "search_keywords": "語1", "exclude_keywords": "除1",
    }
    finder = AsyncMock(return_value=[COLLISION, {**COLLISION, "product_id": "9"}])
    monkeypatch.setattr(importer, "parse_rows", lambda raw: ([row], []))
    monkeypatch.setattr(importer, "load_lookup_maps", AsyncMock(return_value={}))
    monkeypatch.setattr(importer, "load_keyword_owners", AsyncMock(return_value={}))
    monkeypatch.setattr(importer, "build_payload", lambda r, lookups: {})
    monkeypatch.setattr(importer, "validate_row_dynamic", AsyncMock(return_value=[]))
    monkeypatch.setattr(importer, "find_code_collisions", finder)

    out = await importer.preview(object(), b"x", "a.csv")

    checked = out["rows"][0]
    assert "MARK_ALREADY_USED_BY_5" in checked["warnings"]
    assert "MARK_ALREADY_USED_BY_9" in checked["warnings"]
    assert [c["product_id"] for c in checked["code_collisions"]] == ["5", "9"]
    assert checked["blocking"] == []
    assert finder.await_args.kwargs["mark"] == "ST-01"
    assert finder.await_args.kwargs["exclude_keywords"] == ["除1"]


async def test_csv_new_preview_has_empty_collisions_when_none(monkeypatch):
    row = {
        "row_no": "1", "mark": "", "japanese_title": "新商品", "english_title": "",
        "release_date": "", "search_keywords": "語1", "exclude_keywords": "",
    }
    monkeypatch.setattr(importer, "parse_rows", lambda raw: ([row], []))
    monkeypatch.setattr(importer, "load_lookup_maps", AsyncMock(return_value={}))
    monkeypatch.setattr(importer, "load_keyword_owners", AsyncMock(return_value={}))
    monkeypatch.setattr(importer, "build_payload", lambda r, lookups: {})
    monkeypatch.setattr(importer, "validate_row_dynamic", AsyncMock(return_value=[]))
    monkeypatch.setattr(importer, "find_code_collisions", AsyncMock(return_value=[]))

    out = await importer.preview(object(), b"x", "a.csv")

    assert out["rows"][0]["code_collisions"] == []
    assert not any(w.startswith("MARK_ALREADY_USED_BY_") for w in out["rows"][0]["warnings"])
    assert "MARK_EMPTY" in out["rows"][0]["warnings"]


async def test_old_mark_lookup_is_gone():
    assert not hasattr(importer, "load_existing_marks")


async def test_csv_update_warns_only_when_mark_changes(monkeypatch):
    snap = snapshot()
    finder = AsyncMock(return_value=[COLLISION])
    monkeypatch.setattr(roundtrip, "snapshots", AsyncMock(return_value=[snap]))
    monkeypatch.setattr(roundtrip, "find_code_collisions", finder)
    db = AsyncMock()
    db.execute.return_value.fetchall = lambda: []

    changed, _ = await roundtrip.inspect_update(db, file_for(snap, mark="ST01"), "m.csv")
    row = changed["rows"][0]
    assert row["warnings"] == ["MARK_ALREADY_USED_BY_5"]
    assert row["code_collisions"] == [COLLISION]
    assert finder.await_args.kwargs["mark"] == "ST01"
    assert finder.await_args.kwargs["exclude_product_id"] == snap["product"]["id"]

    finder.reset_mock()
    other, _ = await roundtrip.inspect_update(db, file_for(snap, english_title="x"), "e.csv")
    assert other["rows"][0]["warnings"] == []
    assert other["rows"][0]["code_collisions"] == []
    finder.assert_not_awaited()
