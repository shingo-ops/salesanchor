"""v102 の人の判断（便D1）の PostgreSQL を使わない試験。原文・応答はすべて架空。

D-K6（60秒の間に5回直しても配信は1回）、判断の反映（_apply_decisions）、固定の位置づくり、review-ack API の 422 / 409 / 成功。
PostgreSQL を使う試験は test_v102_human_decisions_pg.py。
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

import app.routers.item_corrections as router
import app.services.line_analysis_v102_svc as svc
import app.services.v102_human_decisions_svc as decisions_svc
from app.services.v102_human_decisions_svc import Decisions, JobOfItem
from app.tasks import tcg_extraction as tasks


class FakeRedis:
    """SET NX EX だけを真似る。キーがあれば取れない。"""

    def __init__(self) -> None:
        self.keys: dict[str, str] = {}
        self.calls: list[dict] = []

    def set(self, key, value, nx=False, ex=None):
        self.calls.append({"key": key, "nx": nx, "ex": ex})
        if nx and key in self.keys:
            return None
        self.keys[key] = value
        return True

    def delete(self, key):
        self.keys.pop(key, None)


@pytest.fixture
def distribution(monkeypatch):
    redis = FakeRedis()
    task = MagicMock()
    monkeypatch.setattr(tasks, "_get_redis_client", lambda: redis)
    monkeypatch.setattr(tasks, "scheduled_distribution_task", task)
    monkeypatch.setenv("TCG_AUTO_DISTRIBUTE", "1")
    return SimpleNamespace(redis=redis, task=task)


def test_k6_five_corrections_in_a_row_schedule_one_distribution(distribution):
    results = [tasks.schedule_distribution() for _ in range(5)]
    assert results == [True, False, False, False, False]
    distribution.task.apply_async.assert_called_once_with(countdown=60)
    assert distribution.redis.calls[0] == {"key": "tcg:distribution:scheduled", "nx": True, "ex": 600}


def test_correction_after_the_scheduled_distribution_started_schedules_a_new_one(distribution):
    assert tasks.schedule_distribution() is True
    assert tasks.schedule_distribution() is False  # 予約済みの間の直しは積まない
    tasks._release_distribution_schedule()  # 配信タスクは開始の直前にキーを消す
    assert tasks.schedule_distribution() is True  # 開始後の直しは新しい予約
    assert distribution.task.apply_async.call_count == 2


def test_failed_enqueue_releases_the_key_so_the_next_correction_can_schedule(distribution):
    distribution.task.apply_async.side_effect = ConnectionError("broker down")
    assert tasks.schedule_distribution() is False
    assert tasks.DISTRIBUTION_SCHEDULE_KEY not in distribution.redis.keys
    distribution.task.apply_async.side_effect = None
    assert tasks.schedule_distribution() is True


def test_missing_task_releases_the_key(distribution, monkeypatch):
    monkeypatch.setattr(tasks, "scheduled_distribution_task", None)
    assert tasks.schedule_distribution() is False
    assert tasks.DISTRIBUTION_SCHEDULE_KEY not in distribution.redis.keys


def test_redis_client_has_socket_timeouts(monkeypatch):
    import redis

    seen = {}
    monkeypatch.setattr(redis, "from_url", lambda url, **kwargs: seen.update(kwargs))
    tasks._get_redis_client()
    assert seen["socket_timeout"] == 2 and seen["socket_connect_timeout"] == 2


def test_schedule_distribution_does_nothing_unless_auto_distribute_is_on(distribution, monkeypatch):
    monkeypatch.setenv("TCG_AUTO_DISTRIBUTE", "0")
    assert tasks.schedule_distribution() is False
    assert distribution.redis.calls == []
    distribution.task.apply_async.assert_not_called()


def test_schedule_distribution_survives_redis_failure(distribution, monkeypatch):
    def broken():
        raise ConnectionError("redis down")

    monkeypatch.setattr(tasks, "_get_redis_client", broken)
    assert tasks.schedule_distribution() is False
    distribution.task.apply_async.assert_not_called()


def test_reanalyze_skips_non_v102_jobs(monkeypatch):
    session = MagicMock()
    session.execute.return_value.first.return_value = ("raw-extraction-v6-rawcode-p1",)
    monkeypatch.setattr(tasks, "_get_sync_session", lambda: session)
    analysis = MagicMock()
    monkeypatch.setattr(tasks, "run_v102_analysis", analysis)
    schedule = MagicMock()
    monkeypatch.setattr(tasks, "schedule_distribution", schedule)
    result = tasks.reanalyze_v102_job("job-1")
    assert result["status"] == "skipped"
    analysis.assert_not_called()
    schedule.assert_not_called()


def test_reanalyze_runs_analysis_then_schedules_for_v102(monkeypatch):
    session = MagicMock()
    session.execute.return_value.first.return_value = ("v102:raw_copy_v101_f_c:abc",)
    monkeypatch.setattr(tasks, "_get_sync_session", lambda: session)
    analysis = MagicMock(return_value={"total": 1})
    monkeypatch.setattr(tasks, "run_v102_analysis", analysis)
    monkeypatch.setattr(tasks, "schedule_distribution", MagicMock(return_value=True))
    result = tasks.reanalyze_v102_job("job-1")
    analysis.assert_called_once_with(session, "job-1")
    assert result == {"extraction_job_id": "job-1", "status": "reanalyzed", "analysis_stats": {"total": 1}, "scheduled": True}


# --- 試作版へ渡す引数（K2: 判断が無いときは今と同じ呼び出し） --------------------------------------------


def _pipeline_ctx():
    return SimpleNamespace(raw_text="商品A\n3BOX@1,000円", supplier_context=None)


def _run_pipeline_with_spy(fixed_products):
    spy = MagicMock(return_value=([], {"possible_missing_item": []}))
    svc.run_v102_pipeline(
        '{"items": [{"lines": [1, 2], "price": "1,000円", "quantity": "3"}]}', _pipeline_ctx(),
        {"status_entries": []}, extract_items=spy, fixed_products=fixed_products,
    )
    return spy


@pytest.mark.parametrize("fixed", [None, {}])
def test_k2_pipeline_does_not_pass_fixed_products_when_there_is_none(fixed):
    assert "fixed_products" not in _run_pipeline_with_spy(fixed).call_args.kwargs


def test_pipeline_passes_fixed_products_when_given():
    assert _run_pipeline_with_spy({0: 7}).call_args.kwargs["fixed_products"] == {0: 7}


def _row(index: int) -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), gemini_index=index)


def test_fixed_products_position_skips_rejected_items(monkeypatch):
    rows = [_row(0), _row(1), _row(2)]
    parsed = [{"lines": [1]}, {"lines": [3]}, {"rejected": "x", "gemini_index": 1}]
    monkeypatch.setattr(svc, "parse_v101_response", lambda *_a, **_k: (parsed, []))
    decisions = {str(rows[2].id): Decisions(product_id=9), str(rows[1].id): Decisions(condition_id=3)}
    result = svc._fixed_products("{}", _pipeline_ctx(), {"status_entries": []}, rows, decisions)
    assert result == {1: 9}  # 受理した件は rows[0]・rows[2] の2件。rows[2] は位置 1


def test_fixed_products_middle_item_with_a_rejected_one_before_it(monkeypatch):
    rows = [_row(0), _row(1), _row(2), _row(3)]  # gemini_index 0 が落とされた件。受理: 1, 2, 3 → 位置 0, 1, 2
    parsed = [{"lines": [1]}, {"lines": [2]}, {"lines": [3]}, {"rejected": "x", "gemini_index": 0}]
    monkeypatch.setattr(svc, "parse_v101_response", lambda *_a, **_k: (parsed, []))
    result = svc._fixed_products("{}", _pipeline_ctx(), {"status_entries": []}, rows, {str(rows[2].id): Decisions(product_id=5)})
    assert result == {1: 5}  # 真ん中(gemini_index 2)の位置は 1


def test_fixed_products_is_empty_without_product_decisions():
    assert svc._fixed_products("{}", _pipeline_ctx(), {"status_entries": []}, [_row(0)], {}) == {}


# --- 判断の反映 -------------------------------------------------------------------------------------


def _values(**over):
    base = {
        "product_id": None, "pid_resolved": False, "pid_basis": "V102:unmatched", "condition_id": 1,
        "condition_canonical": "FLAG_SINGLE", "condition_basis": "R4", "needs_review": True,
        "review_reasons": "product_not_in_master,condition_unknown,price_not_in_lines",
    }
    return {**base, **over}


def test_apply_decisions_without_decision_returns_values_unchanged():
    values = _values()
    assert svc._apply_decisions(values, {}, None, {}) is values
    assert svc._apply_decisions(values, {}, Decisions(), {}) is values


def test_apply_decisions_marks_manual_product_and_keeps_other_reasons():
    values = _values(product_id=7, pid_resolved=True, pid_basis="V102:matched")
    out = svc._apply_decisions(values, {}, Decisions(product_id=7), {})
    assert out["pid_basis"] == "MANUAL" and out["needs_review"] is True
    assert values["pid_basis"] == "V102:matched"  # 元は変えない


def test_apply_decisions_does_not_mark_manual_when_product_was_not_fixed():
    values = _values(product_id=None, pid_resolved=False)
    assert svc._apply_decisions(values, {}, Decisions(product_id=7), {})["pid_basis"] == "V102:unmatched"


def test_apply_decisions_condition_replaces_columns_and_drops_condition_reasons():
    out = svc._apply_decisions(_values(), {}, Decisions(condition_id=5), {5: "Sealed box"})
    assert (out["condition_id"], out["condition_canonical"], out["condition_basis"]) == (5, "Sealed box", "MANUAL_CONDITION_REVIEW")
    assert out["review_reasons"] == "product_not_in_master,price_not_in_lines"


def test_apply_decisions_ack_drops_codes_and_clears_review_when_empty():
    out = svc._apply_decisions(
        _values(review_reasons="price_not_in_lines"), {}, Decisions(ack_codes=frozenset({"price_not_in_lines"})), {}
    )
    assert out["review_reasons"] is None and out["needs_review"] is False


# --- review-ack API ---------------------------------------------------------------------------------


SOURCE = str(uuid4())


@pytest.fixture
def ack_env(monkeypatch):
    env = SimpleNamespace(job=JobOfItem("job-1", "v102:raw_copy_v101_f_c:abc", SOURCE), saved=[], enqueued=[])

    async def reasons(_db):
        return {"price_not_in_lines": ("system", "extraction")}

    async def find(_db, _item):
        return env.job

    async def save(_db, **kwargs):
        env.saved.append(kwargs)
        return 1

    monkeypatch.setattr(router, "load_review_reason_codes", reasons)
    monkeypatch.setattr(router, "find_job_of_item", find)
    monkeypatch.setattr(router, "save_review_ack", save)
    monkeypatch.setattr(router, "enqueue_v102_reanalyze", env.enqueued.append)
    return env


def _call_ack(codes, source=SOURCE):
    body = router.ReviewAckRequest(source_message_id=source, codes=codes)
    user = SimpleNamespace(email="admin@example.com")
    return asyncio.run(router.save_item_review_ack(str(uuid4()), body, db=MagicMock(), current_user=user))


def test_review_ack_unregistered_code_is_422_and_writes_nothing(ack_env):
    with pytest.raises(HTTPException) as caught:
        _call_ack(["not_a_code"])
    assert caught.value.status_code == 422
    assert ack_env.saved == [] and ack_env.enqueued == []


def test_review_ack_v6_item_is_409(ack_env):
    ack_env.job = JobOfItem("job-1", "raw-extraction-v6-rawcode-p1", SOURCE)
    with pytest.raises(HTTPException) as caught:
        _call_ack(["price_not_in_lines"])
    assert caught.value.status_code == 409
    assert ack_env.saved == [] and ack_env.enqueued == []


def test_review_ack_source_message_mismatch_is_422(ack_env):
    with pytest.raises(HTTPException) as caught:
        _call_ack(["price_not_in_lines"], source=str(uuid4()))
    assert caught.value.status_code == 422
    assert ack_env.saved == [] and ack_env.enqueued == []


def test_review_ack_missing_item_is_404(ack_env):
    ack_env.job = None
    with pytest.raises(HTTPException) as caught:
        _call_ack(["price_not_in_lines"])
    assert caught.value.status_code == 404


def test_review_ack_success_saves_one_and_enqueues_once(ack_env):
    result = _call_ack(["price_not_in_lines", "price_not_in_lines"])
    assert (result.ok, result.saved) == (True, 1)
    assert len(ack_env.saved) == 1 and ack_env.saved[0]["codes"] == ["price_not_in_lines"]
    assert ack_env.enqueued == ["job-1"]


def test_review_ack_request_rejects_empty_codes():
    with pytest.raises(ValueError):
        router.ReviewAckRequest(source_message_id=uuid4(), codes=[])


def test_ack_codes_reader_accepts_only_version_1_lists():
    assert decisions_svc._ack_codes('{"v":1,"codes":["a","b"]}', "i") == frozenset({"a", "b"})
    for bad in ('{"v":2,"codes":["a"]}', '{"v":1,"codes":"a"}', '{"v":1,"codes":[1]}', "not json", "[]"):
        assert decisions_svc._ack_codes(bad, "i") == frozenset()


# --- /corrections の商品の検査（v102 の件だけ） ------------------------------------------------------


@pytest.fixture
def corrections_env(monkeypatch):
    env = SimpleNamespace(job_id="job-1", invalid=[], saved=[], enqueued=[])

    async def job_of(_db, _item):
        return env.job_id

    async def invalid(_db, _values):
        return env.invalid

    async def save(_db, **kwargs):
        env.saved.append(kwargs)
        return {"saved": len(kwargs["fields"])}

    monkeypatch.setattr(router, "v102_job_id_of_item", job_of)
    monkeypatch.setattr(router, "invalid_product_values", invalid)
    monkeypatch.setattr(router, "save_corrections", save)
    monkeypatch.setattr(router, "enqueue_v102_reanalyze", env.enqueued.append)
    return env


def _call_corrections():
    body = router.SaveCorrectionsRequest(
        source_message_id=str(uuid4()), fields=[router.CorrectionField(field_name="product_id", human_value="123")]
    )
    user = SimpleNamespace(email="admin@example.com")
    return asyncio.run(router.save_item_corrections(str(uuid4()), body, db=MagicMock(), current_user=user))


def test_v102_item_with_inactive_product_is_422_and_writes_nothing(corrections_env):
    corrections_env.invalid = ["123"]
    with pytest.raises(HTTPException) as caught:
        _call_corrections()
    assert caught.value.status_code == 422
    assert corrections_env.saved == [] and corrections_env.enqueued == []


def test_v6_item_skips_the_product_check_and_does_not_enqueue(corrections_env):
    corrections_env.job_id = None
    corrections_env.invalid = ["123"]  # v6 では検査しない
    assert _call_corrections().saved == 1
    assert corrections_env.enqueued == []


def test_v102_item_with_valid_product_saves_and_enqueues_once(corrections_env):
    assert _call_corrections().saved == 1
    assert corrections_env.enqueued == ["job-1"]


# --- 固定した件は context_work で変わらない -----------------------------------------------------------


def test_context_work_leaves_a_fixed_matched_item_alone():
    from app.services.gemini_raw_copy_v102_context_work import decide_by_context

    items = [
        {"product_id": 1, "match_status": "matched", "price_line": 1},
        {"product_id": 2, "match_status": "matched", "price_line": 2},  # 人が固定した件(matched)
        {"product_id": 3, "match_status": "matched", "price_line": 3},
    ]
    assert decide_by_context(items, []) == {}  # ambiguous だけが対象。matched の固定した件は決め直されない
