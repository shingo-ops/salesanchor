"""試しの道具（読み取りだけ）が、計算や Gemini 待ちの間に DB の取引を開いたままにしないための共通の関数。

設計: docs/handoff/replay-tx-release/design.md §3 C4
- release_before_compute: 計算・外の呼び出しの前に取引を閉じる（読み取りだけなので rollback。取引が無ければ何もしない）
- set_idle_tx_limit: 開いた取引の中で待つ時間の上限を、この接続にだけ置く（commit で確定させる）
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

IDLE_TX_LIMIT_SECONDS = 30


def release_before_compute(session: Session) -> None:
    session.rollback()


def set_idle_tx_limit(session: Session, seconds: int = IDLE_TX_LIMIT_SECONDS) -> str:
    session.execute(text(f"SET idle_in_transaction_session_timeout = '{int(seconds)}s'"))
    session.commit()
    value = session.execute(text("SHOW idle_in_transaction_session_timeout")).scalar()
    session.rollback()
    logger.info("[tx_guard] idle_in_transaction_session_timeout=%s", value)
    return str(value)
