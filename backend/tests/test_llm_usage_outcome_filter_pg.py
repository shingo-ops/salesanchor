"""ADR-1058 段1a-2: 使用の記録の集計は成功の行（outcome='ok'）だけを数える（本物の PostgreSQL）。

失敗の行（outcome='failed'・error_code あり・cost_usd NULL）は段1b から書かれる。
集計に入れると回数がずれ、再抽出の道具は「費用が NULL の行がある」で止まってしまう。
DB は共有の pg fixture（CI の使い捨て PostgreSQL。段1a の migration 済み）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import app.tools.prompt_ab as pab
from app.routers.tcg_analysis_dashboard import _EVENT_FX_CTE, _LEDGER_OK_JOIN
from app.tools import reextract_v6_with_v102 as reextract
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

_INSERT = (
    "INSERT INTO public.llm_usage_events "
    "(purpose, model, sdk, cost_usd, source_ref, extraction_attempt_id, outcome, error_code) "
    "VALUES ('line_extraction', 'gemini-3.1-flash-lite', 'google-genai', %s, %s, %s, %s, %s)"
)


def _add_ok(conn, *, source_ref=None, attempt_id=None) -> None:
    """成功の行（outcome='ok'・error_code NULL・cost_usd 2）。autocommit の接続なので入れた時点で確定する。"""
    with conn.cursor() as cur:
        cur.execute(_INSERT, (2, source_ref, attempt_id, "ok", None))


def _add_failed(conn, *, source_ref=None, attempt_id=None) -> None:
    """失敗の行（本番と同じ outcome='failed'・error_code='timeout'・cost_usd NULL）。"""
    with conn.cursor() as cur:
        cur.execute(_INSERT, (None, source_ref, attempt_id, "failed", "timeout"))


def _apply_fx_history_tables(conn) -> None:
    """_EVENT_FX_CTE が読む為替の2表を作る（共有の pg fixture は作らないため。本番と同じ migration を流す）。"""
    with conn.cursor() as cur:
        for name in ("20260628_170000_add_app_fx_rates.sql", "20261003_100000_create_app_fx_rate_history.sql"):
            cur.execute((MIGRATIONS / name).read_text())


def test_event_fx_cte_counts_only_ok_rows(pg):  # noqa: F811
    conn, engine, _url = pg
    _apply_fx_history_tables(conn)
    _add_ok(conn)
    _add_failed(conn)
    with Session(engine) as s:  # 入れた後の別の取引で集計する（NOW() は取引の始まりの時刻）
        row = s.execute(
            text(f"WITH event_fx AS ({_EVENT_FX_CTE}) SELECT count(*), sum(cost_usd) FROM event_fx"),
            {"days": 1},
        ).one()
    assert (row[0], row[1]) == (1, 2)


def test_ledger_ok_join_does_not_multiply_or_drop_attempts(pg):  # noqa: F811
    conn, engine, _url = pg
    both = str(uuid4())
    only_failed = str(uuid4())
    _add_ok(conn, attempt_id=both)
    _add_failed(conn, attempt_id=both)
    _add_failed(conn, attempt_id=only_failed)
    query = text(
        "SELECT count(*), count(ue.id), coalesce(sum(ue.cost_usd), 0) "
        "FROM (SELECT CAST(:aid AS uuid) AS id) AS ea "
        f"LEFT JOIN public.llm_usage_events ue ON {_LEDGER_OK_JOIN}"
    )
    with Session(engine) as s:
        # 成功と失敗が1行ずつ: 試行は1つのまま（2行に増えない）・数えるのは成功の1行・費用は 2
        assert tuple(s.execute(query, {"aid": both}).one()) == (1, 1, 2)
        # 失敗の行だけ: 試行の行は落ちない・結ばれる行は 0・費用は 0
        assert tuple(s.execute(query, {"aid": only_failed}).one()) == (1, 0, 0)


def test_prompt_ab_ledger_totals_ignore_failed_rows(pg):  # noqa: F811
    conn, engine, _url = pg
    _add_ok(conn, source_ref="prompt_ab:F")
    _add_failed(conn, source_ref="prompt_ab:F")
    with Session(engine) as s:
        totals = pab.fetch_ledger_totals(s, "prompt_ab:F")
    assert totals.rows == 1
    assert totals.null_cost_rows == 0
    assert totals.cost_usd == 2


def test_reextract_total_cost_ignores_failed_rows(pg):  # noqa: F811
    conn, engine, _url = pg
    since = datetime.now(timezone.utc) - timedelta(minutes=1)
    job = str(uuid4())
    _add_ok(conn, source_ref=f"extraction_job:{job}")
    _add_failed(conn, source_ref=f"extraction_job:{job}")
    with Session(engine) as s:
        # 失敗の行の NULL を数えない（NULL の件数 0 ＝道具が止まらない）
        assert reextract.total_cost(s, [job], since) == (Decimal("2"), 0)
