"""ADR-1025 便2: 再解析のあとの照合（関数だけ・DB はモック）。"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.services import analysis_error_report_verify as v  # noqa: E402

_REPORTED = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)


def _f(name, expected, missing=False):
    return {"field_name": name, "expected_value": expected, "expected_missing_product": missing}


def test_quantity_100_equals_100_00():
    from decimal import Decimal

    assert v.match_field("quantity", 100, Decimal("100.00")) is True


def test_price_difference_mismatch():
    from decimal import Decimal

    assert v.match_field("price", 1200, Decimal("1300.00")) is False


def test_null_actual_mismatch():
    assert v.match_field("quantity", 3, None) is False
    assert v.match_field("price", 3, None) is False


def test_note_order_independent_match():
    assert v.match_field("note", ["未開封", "傷あり"], "傷あり, 未開封") is True


def test_note_extra_or_missing_word_mismatch():
    assert v.match_field("note", ["未開封"], "未開封,傷あり") is False
    assert v.match_field("note", ["未開封", "傷あり"], "未開封") is False


def test_note_both_empty_match():
    assert v.match_field("note", [], None) is True
    assert v.match_field("note", [], "") is True


def test_product_normal_match_and_mismatch():
    assert v.match_field("product_id", 5, 5) is True
    assert v.match_field("product_id", "5", 5) is True
    assert v.match_field("product_id", 5, 6) is False
    assert v.match_field("product_id", 5, None) is False


def test_missing_product_null_matches():
    assert v.match_field("product_id", None, None, expected_missing_product=True, reported_at=_REPORTED) is True


def test_missing_product_created_after_report_matches():
    after = _REPORTED + timedelta(hours=1)
    assert v.match_field(
        "product_id", None, 9, expected_missing_product=True, reported_at=_REPORTED, product_created_at=after,
    ) is True


def test_missing_product_existing_before_report_mismatch():
    before = _REPORTED - timedelta(days=30)
    assert v.match_field(
        "product_id", None, 9, expected_missing_product=True, reported_at=_REPORTED, product_created_at=before,
    ) is False


def test_string_fields_exact_match():
    assert v.match_field("unit", "BOX", "BOX") is True
    assert v.match_field("condition", "新品", "中古") is False
    assert v.match_field("status", "Sold out", None) is False


def test_build_verdict_all_match_resolved():
    verdict, results = v.build_verdict([_f("quantity", 3), _f("unit", "BOX")], {"quantity": 3, "unit": "BOX"})
    assert verdict == "resolved"
    assert [r["match"] for r in results] == [True, True]


def test_build_verdict_one_mismatch_unresolved():
    verdict, results = v.build_verdict([_f("quantity", 3), _f("unit", "BOX")], {"quantity": 3, "unit": "PACK"})
    assert verdict == "unresolved"
    assert [r["match"] for r in results] == [True, False]


def test_reanalyze_failed_records_verified_and_unresolved():
    """再解析が成功でないとき: 照合せず verified(reanalyze_failed) と unresolved を残し、通知しない。"""
    session = MagicMock()
    report = {"id": "r1", "report_code": "ER-000001", "extraction_item_id": "i1",
              "extraction_job_id": "j1", "reported_at": _REPORTED}
    session.execute.return_value.mappings.return_value.first.return_value = report
    session.execute.return_value.mappings.return_value.all.return_value = [_f("quantity", 3)]
    out = v.run_reanalyze_and_verify(
        "r1", reanalyze=lambda job_id: {"status": "skipped"}, session_factory=lambda: session,
    )
    assert out == {"report_code": "ER-000001", "result": "reanalyze_failed", "status": "unresolved"}
    params = [c.args[1] for c in session.execute.call_args_list if len(c.args) > 1]
    verified = [p for p in params if p.get("kind") == "verified"]
    assert len(verified) == 1
    assert '"result": "reanalyze_failed"' in verified[0]["payload"]
    assert any(p.get("st") == "unresolved" for p in params)
    assert any(p.get("kind") == "notify_failed" for p in params)


def test_reanalyze_failed_still_notifies(monkeypatch):
    session = MagicMock()
    report = {"id": "r1", "report_code": "ER-000001", "extraction_item_id": "i1",
              "extraction_job_id": "j1", "reported_at": _REPORTED}
    session.execute.return_value.mappings.return_value.first.return_value = report
    session.execute.return_value.mappings.return_value.all.return_value = [_f("quantity", 3)]
    notify = MagicMock(return_value=("123", None))
    monkeypatch.setattr(v.discord_notifier, "notify_analysis_error_report_verified", notify)
    v.run_reanalyze_and_verify("r1", reanalyze=lambda job_id: {"status": "skipped"}, session_factory=lambda: session)
    notify.assert_called_once_with("ER-000001", "reanalyze_failed", [])
    params = [c.args[1] for c in session.execute.call_args_list if len(c.args) > 1]
    assert any(p.get("kind") == "notified" for p in params)


def test_notify_body_for_reanalyze_failed(monkeypatch):
    from app.services import discord_notifier

    monkeypatch.setenv("ANALYSIS_ERROR_REPORT_DISCORD_WEBHOOK", "https://discord.example/webhook")
    with patch("app.services.discord_notifier.httpx.Client") as client_cls:
        post = client_cls.return_value.__enter__.return_value.post
        post.return_value = type("R", (), {"status_code": 200, "json": lambda self: {"id": "1"}})()
        discord_notifier.notify_analysis_error_report_verified("ER-000001", "reanalyze_failed", [])
        assert post.call_args.kwargs["json"]["content"] == "誤り報告 ER-000001 照合: 再解析できず（未解決）"
