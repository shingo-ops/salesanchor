"""比較表から直した値（数量・単価・単位・メモ・販売状況）の PostgreSQL を使わない試験。原文・値はすべて架空。

読み方（形が違う行は無視）、検査（override_rejection）、選択肢、重ね方（apply_value_overrides）、買取単位・〆の相手の扱い、
API（404 / 409 / 422 / 成功）、予約語、通知の表、一覧の manual_values。PostgreSQL を使う試験は test_v102_value_overrides_pg.py。
"""
from __future__ import annotations

import asyncio
import json
import logging
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import app.routers.item_corrections as router
import app.services.line_analysis_v102_svc as svc
import app.services.v102_human_decisions_svc as ds
from app.realtime.topics import SCOPE_GLOBAL, TOPIC_TCG_REVIEW, WRITE_ROUTE_TOPICS
from app.services import tcg_analysis_review_svc as review_svc
from app.services.v102_human_decisions_svc import Decisions, JobOfItem, ValueOverrides

UNIT_IDS = {"Sealed box": "11", "Case": "12"}
STATUS_ENTRIES = [
    {"canonical": "Sold out", "effect": "EXCLUDE"},
    {"canonical": "Pre-order", "effect": "OUTPUT"},
    {"canonical": "In Stock", "effect": "OUTPUT"},
    {"canonical": "In Stock", "effect": "DEFAULT"},
    {"canonical": "Heading", "effect": "HEADING"},
]


def body(value: object, v: int = 1) -> str:
    return json.dumps({"v": v, "value": value}, ensure_ascii=False)


def values_row(**over) -> dict:
    base = {
        "quantity_normalized": Decimal("3"), "price_normalized": Decimal("1000"), "unit_id": 11, "unit_canonical": "Sealed box",
        "unit_resolved": True, "note_ja": "元のメモ", "status": "In Stock", "exclusion": None,
        "needs_review": True, "review_reasons": "price_not_in_lines",
    }
    return {**base, **over}


# --- 読み方 ------------------------------------------------------------------------------------------


def test_value_overrides_reader_accepts_each_valid_field():
    latest = {
        ds.FIELD_OVERRIDE_QUANTITY: body("5"), ds.FIELD_OVERRIDE_PRICE: body("1200.5"), ds.FIELD_OVERRIDE_UNIT: body(" Case "),
        ds.FIELD_OVERRIDE_NOTE: body(""), ds.FIELD_OVERRIDE_STATUS: body("Sold out"),
    }
    got = ds._value_overrides(latest, "i")
    assert got == ValueOverrides(Decimal("5"), Decimal("1200.5"), "Case", "", "Sold out")
    assert got.is_empty is False


@pytest.mark.parametrize(
    "raw",
    [
        "not json", "[]", json.dumps({"v": 2, "value": "1"}), json.dumps({"v": 1}), json.dumps({"v": 1, "value": 1}),
        body("NaN"), body("Infinity"), body("-1"), body("1.001"), body("1000000000000"), body("abc"), body(""),
    ],
)
def test_value_overrides_reader_ignores_bad_numbers_and_shapes(raw, caplog):
    with caplog.at_level(logging.WARNING):
        got = ds._value_overrides({ds.FIELD_OVERRIDE_QUANTITY: raw, ds.FIELD_OVERRIDE_PRICE: raw}, "i")
    assert got.is_empty is True
    assert "無視します" in caplog.text


def test_value_overrides_reader_ignores_an_empty_unit_or_status():
    assert ds._value_overrides({ds.FIELD_OVERRIDE_UNIT: body("  "), ds.FIELD_OVERRIDE_STATUS: body("")}, "i").is_empty is True


def test_note_override_with_empty_string_is_not_empty():
    got = ds._value_overrides({ds.FIELD_OVERRIDE_NOTE: body("")}, "i")
    assert got.note == "" and got.is_empty is False


def test_decisions_is_empty_looks_at_values_too():
    assert Decisions().is_empty is True
    assert Decisions(values=ValueOverrides(note="")).is_empty is False


def test_format_decimal_never_uses_exponent():
    assert ds.format_decimal(Decimal("1000")) == "1000"
    assert ds.format_decimal(Decimal("1E+3")) == "1000"
    assert ds.format_decimal(Decimal("12.50")) == "12.5"
    assert ds.format_decimal(None) == ""


# --- 検査・選択肢 ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("quantity", "0"), ("quantity", "12"), ("price", "1000.25"), ("price", "999999999999.99"),
        ("unit", "Case"), ("status", "Sold out"), ("status", "Pre-order"), ("note", ""), ("note", "x" * 2000),
        ("override_price", "5"),
    ],
)
def test_override_rejection_accepts_valid_values(field, value):
    assert ds.override_rejection(field, value, UNIT_IDS, STATUS_ENTRIES) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("quantity", "NaN"), ("price", "Infinity"), ("quantity", "-1"), ("price", "1.001"), ("price", "1000000000000"),
        ("quantity", "abc"), ("quantity", ""), ("unit", "Pallet"), ("unit", ""), ("status", "Heading"), ("status", "Unknown"),
        ("note", "x" * 2001), ("name", "x"),
    ],
)
def test_override_rejection_refuses_bad_values_with_422(field, value):
    rejected = ds.override_rejection(field, value, UNIT_IDS, STATUS_ENTRIES)
    assert rejected is not None and rejected.status == 422


def test_options_and_rejection_use_the_same_sets():
    options = ds.override_options(UNIT_IDS, STATUS_ENTRIES)
    assert options == {"units": ["Case", "Sealed box"], "statuses": ["Sold out", "Pre-order", "In Stock"]}
    for unit in options["units"]:
        assert ds.override_rejection("unit", unit, UNIT_IDS, STATUS_ENTRIES) is None
    for status in options["statuses"]:
        assert ds.override_rejection("status", status, UNIT_IDS, STATUS_ENTRIES) is None


# --- 重ね方 ------------------------------------------------------------------------------------------


def test_apply_value_overrides_replaces_the_five_items_and_keeps_the_rest():
    values = values_row()
    out = ds.apply_value_overrides(values, ValueOverrides(Decimal("9"), Decimal("1500"), "Case", "新メモ", "Sold out"), UNIT_IDS, STATUS_ENTRIES)
    assert (out["quantity_normalized"], out["price_normalized"]) == (Decimal("9"), Decimal("1500"))
    assert (out["unit_canonical"], out["unit_id"], out["unit_resolved"]) == ("Case", 12, True)
    assert (out["note_ja"], out["status"], out["exclusion"]) == ("新メモ", "Sold out", "excluded")
    assert (out["needs_review"], out["review_reasons"]) == (True, "price_not_in_lines")  # 理由は変えない
    assert values["unit_canonical"] == "Sealed box"  # 元は変えない


def test_apply_value_overrides_empty_note_becomes_none_and_in_stock_clears_exclusion():
    out = ds.apply_value_overrides(
        values_row(status="Sold out", exclusion="excluded"), ValueOverrides(note="", status="In Stock"), UNIT_IDS, STATUS_ENTRIES
    )
    assert out["note_ja"] is None and out["status"] == "In Stock" and out["exclusion"] is None


def test_apply_value_overrides_without_overrides_returns_the_same_dict():
    values = values_row()
    assert ds.apply_value_overrides(values, ValueOverrides(), UNIT_IDS, STATUS_ENTRIES) is values


def test_apply_value_overrides_skips_values_gone_from_the_master_without_raising(caplog):
    values = values_row()
    with caplog.at_level(logging.WARNING):
        out = ds.apply_value_overrides(
            values, ValueOverrides(Decimal("2"), unit="Pallet", status="Retired"), UNIT_IDS, STATUS_ENTRIES
        )
    assert out["quantity_normalized"] == Decimal("2")  # 数字は重なる
    assert (out["unit_canonical"], out["unit_id"], out["status"], out["exclusion"]) == ("Sealed box", 11, "In Stock", None)
    assert "Pallet" in caplog.text and "Retired" in caplog.text


def test_status_available_by_human():
    available = Decisions(values=ValueOverrides(status="In Stock"))
    assert ds.status_available_by_human(available, STATUS_ENTRIES) is True
    assert ds.status_available_by_human(Decisions(values=ValueOverrides(status="Sold out")), STATUS_ENTRIES) is False
    assert ds.status_available_by_human(Decisions(values=ValueOverrides(status="Retired")), STATUS_ENTRIES) is False
    assert ds.status_available_by_human(Decisions(values=ValueOverrides(note="x")), STATUS_ENTRIES) is False
    assert ds.status_available_by_human(None, STATUS_ENTRIES) is False


# --- v102 本体での扱い -------------------------------------------------------------------------------


def _soldout_item() -> dict:
    return {"product_id": 42, "soldout_targets": [{"product_id": 42, "condition_id": 18}, {"product_id": 43, "condition_id": 11}]}


def test_extra_targets_stop_only_when_a_human_made_the_status_available():
    item, written = _soldout_item(), {"product_id": 42, "condition_id": 18}
    in_stock = Decisions(values=ValueOverrides(status="In Stock"))
    assert svc._extra_targets(written, item, in_stock, STATUS_ENTRIES) == []
    sold_out = Decisions(values=ValueOverrides(status="Sold out"))
    assert len(svc._extra_targets(written, item, sold_out, STATUS_ENTRIES)) == 1  # 在庫あり以外では止めない
    assert len(svc._extra_targets(written, item, Decisions(values=ValueOverrides(note="x")), STATUS_ENTRIES)) == 1
    assert len(svc._extra_targets(written, item, None, STATUS_ENTRIES)) == 1


def test_apply_decisions_does_not_apply_values_but_runs_for_value_only_decisions():
    values = values_row()
    decision = Decisions(values=ValueOverrides(note="x"))
    out = svc._apply_decisions(values, {}, decision, {})
    assert out["note_ja"] == "元のメモ"  # 値の上書きは _write_results の先頭で済む。ここでは重ねない


def test_buyback_units_exclude_items_with_a_human_unit_or_price(monkeypatch):
    captured = {}

    def fake_apply(_session, _items, base_values, _unit_ids, _posted_at, human_condition):
        captured["human"] = human_condition
        return base_values

    monkeypatch.setattr(svc, "apply_buyback_units", fake_apply)
    monkeypatch.setattr(svc, "is_buyback_candidate", lambda _item, _values: True)
    session = MagicMock()
    rows = [SimpleNamespace(id=f"r{i}") for i in range(5)]
    pairs = [({}, row) for row in rows]
    decisions = {
        "r0": Decisions(condition_id=1), "r1": Decisions(values=ValueOverrides(unit="Case")),
        "r2": Decisions(values=ValueOverrides(price=Decimal("5"))), "r3": Decisions(values=ValueOverrides(note="x")),
    }
    svc._buyback_units(session, pairs, [values_row() for _ in rows], {}, "job", decisions)
    assert captured["human"] == frozenset({0, 1, 2})


# --- API ---------------------------------------------------------------------------------------------

SOURCE = "6f1c2d3e-0000-4000-8000-000000000001"
OTHER_SOURCE = "6f1c2d3e-0000-4000-8000-000000000002"


@pytest.fixture
def env(monkeypatch):
    state = SimpleNamespace(job=JobOfItem("job-1", "v102:raw_copy_v101_f_ct:abc", SOURCE), saved=[], enqueued=[], reject=None)

    async def find(_db, _item):
        return state.job

    async def save(_db, **kwargs):
        if state.reject is not None:
            raise state.reject
        state.saved.append(kwargs)
        return 1

    monkeypatch.setattr(router, "find_job_of_item", find)
    monkeypatch.setattr(router, "save_value_override", save)
    monkeypatch.setattr(router, "enqueue_v102_reanalyze", state.enqueued.append)
    state.scheduled = []
    monkeypatch.setattr(router, "schedule_distribution", lambda: state.scheduled.append(1) or True)
    return state


def _call(field="price", value="1200", source=SOURCE):
    body_ = router.ValueOverrideRequest(source_message_id=source, field=field, value=value)
    user = SimpleNamespace(email="admin@example.com")
    return asyncio.run(router.save_item_value_override(str(uuid4()), body_, db=MagicMock(), current_user=user))


def test_value_override_success_saves_one_and_enqueues_once(env):
    result = _call()
    assert (result.ok, result.saved) == (True, 1)
    assert len(env.saved) == 1 and env.saved[0]["field"] == "price" and env.saved[0]["value"] == "1200"
    assert env.enqueued == ["job-1"] and env.scheduled == []


def test_value_override_v6_saves_and_schedules_distribution_once_without_reanalysis(env):
    env.job = JobOfItem("job-1", "raw-extraction-v6-rawcode-p1", SOURCE)
    result = _call(field="status", value="Sold out")
    assert (result.ok, result.saved) == (True, 1)
    assert len(env.saved) == 1 and env.saved[0]["field"] == "status"
    assert env.enqueued == [] and env.scheduled == [1]


@pytest.fixture
def corr_env(monkeypatch):
    """商品付け替え・状態の修正（/corrections）の呼び出し先を差し替える。"""
    state = SimpleNamespace(job_id=None, saved=1, enqueued=[], scheduled=[])

    async def job_of(_db, _item):
        return state.job_id

    async def save_corrections(_db, **_kwargs):
        return {"saved": state.saved}

    async def save_condition_review(_db, **_kwargs):
        return {"saved": state.saved}

    monkeypatch.setattr(router, "v102_job_id_of_item", job_of)
    monkeypatch.setattr(router, "save_corrections", save_corrections)
    monkeypatch.setattr(router, "save_condition_review", save_condition_review)
    monkeypatch.setattr(router, "enqueue_v102_reanalyze", state.enqueued.append)
    monkeypatch.setattr(router, "schedule_distribution", lambda: state.scheduled.append(1) or True)
    return state


def _correct(condition: bool = False):
    if condition:
        review = router.ConditionReviewRequest(
            request_id=uuid4(), expected_review_version="a" * 64, decision="correct", condition_id="5"
        )
        body_ = router.SaveCorrectionsRequest(source_message_id=SOURCE, condition_review=review)
    else:
        fields = [router.CorrectionField(field_name="product_id", system_value="1", human_value="2")]
        body_ = router.SaveCorrectionsRequest(source_message_id=SOURCE, fields=fields)
    user = SimpleNamespace(email="admin@example.com")
    return asyncio.run(router.save_item_corrections(str(uuid4()), body_, db=MagicMock(), current_user=user))


def test_product_reassign_v6_saved_schedules_distribution_once_without_reanalysis(corr_env):
    result = _correct()
    assert result.saved == 1
    assert corr_env.scheduled == [1] and corr_env.enqueued == []


def test_condition_review_v6_saved_schedules_distribution_once(corr_env):
    result = _correct(condition=True)
    assert result.saved == 1
    assert corr_env.scheduled == [1] and corr_env.enqueued == []


@pytest.mark.parametrize("condition", [False, True])
def test_v102_corrections_reanalyze_only_and_router_does_not_schedule_distribution(corr_env, monkeypatch, condition):
    corr_env.job_id = "job-1"

    async def no_invalid(_db, _values):
        return []

    monkeypatch.setattr(router, "invalid_product_values", no_invalid)
    _correct(condition)
    assert corr_env.enqueued == ["job-1"] and corr_env.scheduled == []


@pytest.mark.parametrize("condition", [False, True])
def test_corrections_saved_zero_schedules_nothing(corr_env, condition):
    corr_env.saved = 0
    _correct(condition)
    assert corr_env.scheduled == [] and corr_env.enqueued == []


def test_value_override_v6_rejects_source_mismatch_and_missing_without_scheduling(env):
    env.job = JobOfItem("job-1", "raw-extraction-v6-rawcode-p1", SOURCE)
    with pytest.raises(HTTPException) as caught:
        _call(source=OTHER_SOURCE)
    assert caught.value.status_code == 422 and env.saved == [] and env.scheduled == []
    env.job = None
    with pytest.raises(HTTPException) as caught:
        _call()
    assert caught.value.status_code == 404 and env.scheduled == []


@pytest.mark.parametrize(
    ("job", "source", "status"),
    [
        (None, SOURCE, 404),
        (JobOfItem("job-1", "v102:raw_copy_v101_f_ct:abc", SOURCE), OTHER_SOURCE, 422),
    ],
)
def test_value_override_rejections_write_nothing(env, job, source, status):
    env.job = job
    with pytest.raises(HTTPException) as caught:
        _call(source=source)
    assert caught.value.status_code == status
    assert env.saved == [] and env.enqueued == []


def test_lock_key_has_one_source_and_unchanged_string():
    import app.services.v102_transcription_svc as transcription  # noqa: PLC0415

    assert transcription.v102_analysis_lock_key is ds.v102_analysis_lock_key
    assert ds.v102_analysis_lock_key("J1") == "v102_analysis:J1"


def test_item_basic_rejection_does_not_check_version_but_item_rejection_does():
    v6 = JobOfItem("job-1", "raw-extraction-v6-rawcode-p1", SOURCE)
    assert ds.item_basic_rejection(v6, SOURCE) is None
    assert ds.item_basic_rejection(None, SOURCE).status == 404
    assert ds.item_basic_rejection(v6, OTHER_SOURCE).status == 422
    assert ds.item_rejection(v6, SOURCE).status == 409
    assert ds.item_rejection(v6, OTHER_SOURCE).status == 409


def test_value_override_service_rejection_becomes_422_and_enqueues_nothing(env):
    env.reject = ds.DecisionRejected(422, "Unknown unit: Pallet")
    with pytest.raises(HTTPException) as caught:
        _call(field="unit", value="Pallet")
    assert caught.value.status_code == 422 and "Pallet" in caught.value.detail
    assert env.enqueued == []


def test_value_override_request_validates_field_and_length():
    with pytest.raises(ValidationError):
        router.ValueOverrideRequest(source_message_id=uuid4(), field="name", value="x")
    with pytest.raises(ValidationError):
        router.ValueOverrideRequest(source_message_id=uuid4(), field="note", value="x" * 2001)


def test_corrections_reserves_override_field_names():
    for name in ds.OVERRIDE_FIELDS:
        with pytest.raises(ValidationError):
            router.SaveCorrectionsRequest(
                source_message_id=str(uuid4()), fields=[router.CorrectionField(field_name=name, human_value="1")]
            )
    ok = router.SaveCorrectionsRequest(
        source_message_id=str(uuid4()), fields=[router.CorrectionField(field_name="product_id", human_value="1")]
    )
    assert len(ok.fields) == 1


def test_value_options_returns_both_lists(monkeypatch):
    import app.services.tcg_analyzer_svc as analyzer

    monkeypatch.setattr(analyzer, "load_unit_canonical_ids", lambda _s: UNIT_IDS)
    monkeypatch.setattr(analyzer, "load_status_master", lambda _s: STATUS_ENTRIES)

    class FakeDb:
        async def run_sync(self, fn):
            return fn(None)

    result = asyncio.run(router.get_value_options(db=FakeDb(), current_user=SimpleNamespace(email="a@example.com")))
    assert result.units == ["Case", "Sealed box"] and result.statuses == ["Sold out", "Pre-order", "In Stock"]


def test_routes_are_super_admin_only_and_in_the_realtime_table():
    from app.auth.dependencies import require_super_admin

    paths = {(m, r.path): r for r in router.router.routes for m in r.methods}
    for key in (("POST", "/tcg/items/{extraction_item_id}/value-override"), ("GET", "/tcg/review/value-options")):
        assert any(d.call is require_super_admin for d in paths[key].dependant.dependencies)
    assert WRITE_ROUTE_TOPICS[("POST", "/api/v1/tcg/items/{extraction_item_id}/value-override")] == (TOPIC_TCG_REVIEW, SCOPE_GLOBAL)
    assert not any(method == "GET" for method, _ in WRITE_ROUTE_TOPICS)


# --- 一覧 --------------------------------------------------------------------------------------------


def test_manual_values_lists_only_the_fixed_items_in_the_shared_format():
    assert review_svc._manual_values(None) == {}
    assert review_svc._manual_values(Decisions(product_id=3)) == {}
    got = review_svc._manual_values(Decisions(values=ValueOverrides(Decimal("1E+3"), None, "Case", "", "Sold out")))
    assert got == {"quantity": "1000", "unit": "Case", "note": "", "status": "Sold out"}
