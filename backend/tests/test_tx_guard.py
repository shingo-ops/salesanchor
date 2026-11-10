"""_tx_guard（計算の前に取引を閉じる・取引の待ち時間の上限を置く）の単体試験。DB は使わず、呼ばれた順を記録する偽物の session で確かめる。"""
from __future__ import annotations

from unittest.mock import MagicMock

from app.tools import _tx_guard


def _session(calls: list, scalar_value="30s"):
    session = MagicMock()

    def execute(stmt, *a, **k):
        calls.append(("execute", str(stmt)))
        result = MagicMock()
        result.scalar.return_value = scalar_value
        return result

    session.execute.side_effect = execute
    session.commit.side_effect = lambda: calls.append(("commit", ""))
    session.rollback.side_effect = lambda: calls.append(("rollback", ""))
    return session


def test_set_idle_tx_limit_sets_commits_shows_then_rolls_back_in_order():
    # Arrange
    calls: list = []
    session = _session(calls, scalar_value="30s")
    # Act
    value = _tx_guard.set_idle_tx_limit(session)
    # Assert
    assert [c[0] for c in calls] == ["execute", "commit", "execute", "rollback"]
    assert "idle_in_transaction_session_timeout = '30s'" in calls[0][1]
    assert "SHOW idle_in_transaction_session_timeout" in calls[2][1]
    assert value == "30s"


def test_release_before_compute_rolls_back_once():
    # Arrange
    session = MagicMock()
    # Act
    _tx_guard.release_before_compute(session)
    # Assert
    assert session.rollback.call_count == 1
