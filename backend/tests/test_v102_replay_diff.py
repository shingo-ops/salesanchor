"""v102_replay_diff.replay が、計算（run_v102_pipeline）の前に DB の取引を閉じることの単体試験。DB は使わない偽物で、呼ばれた順を 1 つの列に記録する。"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services import line_analysis_v102_svc as svc
from app.tasks import tcg_extraction as task
from app.tools import v102_replay_diff as rd


@pytest.fixture
def seq(monkeypatch, tmp_path):
    """列（呼ばれた順）・偽物の session・計算の偽物を用意する。"""
    calls: list[str] = []
    session = MagicMock()

    def execute(stmt, *a, **k):
        calls.append("execute")
        result = MagicMock()
        result.one.return_value = SimpleNamespace(gemini_unsure=None, review_reasons=None)
        result.fetchall.return_value = [SimpleNamespace(id="i1")]
        return result

    session.execute.side_effect = execute
    session.commit.side_effect = lambda: calls.append("commit")
    session.rollback.side_effect = lambda: calls.append("rollback")

    def compute(*a, **k):
        calls.append("compute")
        return {"v102_items": []}

    ns = SimpleNamespace(calls=calls, session=session, compute=MagicMock(side_effect=compute), out=tmp_path / "o.jsonl")
    monkeypatch.setattr(svc, "_call_gemini", svc._call_gemini)  # disable_gemini が書き換えた分を戻すため
    monkeypatch.setattr(task, "load_extraction_context", lambda s, j: object())
    monkeypatch.setattr(svc, "load_v102_masters", lambda s: ({"x": 1}, []))
    monkeypatch.setattr(svc, "_response_from_rows", lambda rows, unsure: "resp")
    monkeypatch.setattr(svc, "load_v102_decisions", lambda s, ids: {})
    monkeypatch.setattr(svc, "_fixed_products", lambda *a, **k: {})
    monkeypatch.setattr(svc, "load_followup_reference", lambda s, j: None)
    monkeypatch.setattr(svc, "load_soldout_ref_posts", lambda s, j: ())
    monkeypatch.setattr(svc, "load_posted_date", lambda s, j: None)
    monkeypatch.setattr(svc, "masters_with_followup", lambda m, *a: m)
    monkeypatch.setattr(svc, "run_v102_pipeline", ns.compute)
    return ns


def test_transaction_is_closed_right_before_each_compute(seq):
    # Act
    stats = rd.replay(seq.session, ["p1", "p2"], seq.out)
    # Assert
    assert stats["errors"] == 0
    idx = [i for i, c in enumerate(seq.calls) if c == "compute"]
    assert len(idx) == 2
    for i in idx:
        assert seq.calls[i - 1] == "rollback"  # rollback と compute の間に execute は無い


def test_idle_limit_is_set_first(seq):
    # Act
    rd.replay(seq.session, ["p1"], seq.out)
    # Assert
    assert seq.calls[:4] == ["execute", "commit", "execute", "rollback"]


def test_idle_limit_is_set_again_after_a_failed_post_and_next_post_is_processed(seq):
    # Arrange
    def compute(*a, **k):
        seq.calls.append("compute")
        if seq.compute.call_count == 1:
            raise RuntimeError("boom")
        return {"v102_items": []}

    seq.compute.side_effect = compute
    # Act
    stats = rd.replay(seq.session, ["p1", "p2"], seq.out)
    # Assert
    assert (stats["posts"], stats["errors"]) == (2, 1)
    assert seq.compute.call_count == 2  # 2 件目も処理された
    first = seq.calls.index("compute")
    # 失敗の後に SET の execute と commit がもう一度呼ばれる
    after = seq.calls[first + 1:]
    assert any(after[i] == "execute" and after[i + 1] == "commit" for i in range(len(after) - 1))
