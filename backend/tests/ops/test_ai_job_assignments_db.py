"""ADR-1058 段1a: AI の担当の表3つと使用の記録の列 outcome・error_code の migration のテスト（実 PostgreSQL が必要）。

使い捨て DB を作り、migration を本物のファイルで適用して確かめる。
(a) 行の数と初めの担当。
(b) 流し直しで、画面で変えた担当が初めの値に戻らない。
(c) 後の migration が CHECK を広げていても、流し直しで値が消えず、例外も出ない。
(d) 履歴は足すだけ（書き換え・消し・TRUNCATE は例外。users を消した時の changed_by の NULL 化だけ通る）。
(e) outcome と error_code の組み合わせの決まり。
(f) 読む関数 get_ai_assignment（秘1）。
ai_reader / ai_reader_cloud はクラスタ共通のロールなので、このテストが作った場合だけ最後に消す。
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)

_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"
_AI_READER_SQL = "20261017_130000_create_ai_reader_role.sql"
_META_SQL = "20261024_100000_create_ai_cloud_meta.sql"
_ROLE_SQL = "20261024_100100_create_ai_reader_cloud_role.sql"
_PIPELINE_PUBLIC_SQL = "20260921_110000_pipeline_tables_public.sql"
_LLM_USAGE_SQL = "20260930_150000_create_llm_usage_events.sql"
_AI_JOB_SQL = "20261103_120000_create_ai_job_assignments.sql"

_JOB_KEYS = (
    "line_extraction",
    "translation_inbound",
    "translation_inbound_escalation",
    "translation_outbound",
    "secretary_intent",
)
_EXPECTED_ASSIGNMENTS = {
    "line_extraction": ("gemini", "gemini-3.1-flash-lite"),
    "translation_inbound": ("gemini", "gemini-3.5-flash-lite"),
    "translation_inbound_escalation": ("gemini", "gemini-3.5-flash-lite"),
    "translation_outbound": ("gemini", "gemini-3.5-flash-lite"),
    "secretary_intent": ("claude", "sonnet"),
}


def _psycopg_url(url: str, dbname: str | None = None) -> str:
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    if dbname:
        parts = urlsplit(url)
        url = urlunsplit(parts._replace(path="/" + dbname))
    return url


def _read(fname: str) -> str:
    return (_MIGRATIONS_DIR / fname).read_text("utf-8")


class _Cluster:
    """クラスタ共通のロールを、このテストが作った場合だけ消すための記録。"""

    def __init__(self, control):
        self.control = control
        cur = control.cursor()
        self.existed = {}
        for r in ("ai_reader", "ai_reader_cloud"):
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (r,))
            self.existed[r] = cur.fetchone() is not None

    def cleanup(self):
        cur = self.control.cursor()
        for r in ("ai_reader_cloud", "ai_reader"):
            if not self.existed[r]:
                cur.execute(f"DROP ROLE IF EXISTS {r}")


@pytest.fixture(scope="module")
def cluster():
    import psycopg2

    control = psycopg2.connect(_psycopg_url(ADMIN_PG_URL))
    control.autocommit = True
    c = _Cluster(control)
    try:
        yield c
    finally:
        c.cleanup()
        control.close()


@pytest.fixture()
def db(cluster):
    """専用の DB。migration を 4-1 と同じ順（段1a の前まで）で流した状態。終わったら消す。"""
    import psycopg2
    from sqlalchemy.ext.asyncio import create_async_engine

    from tests.rls_bootstrap import bootstrap_tenant_schema

    name = f"ai_job_assign_{uuid.uuid4().hex[:12]}"
    cur = cluster.control.cursor()
    cur.execute(f'CREATE DATABASE "{name}"')
    conn = psycopg2.connect(_psycopg_url(ADMIN_PG_URL, name))
    conn.autocommit = True
    try:
        c = conn.cursor()
        c.execute(_read(_AI_READER_SQL))
        c.execute(_read(_ROLE_SQL))
        c.execute(_read(_META_SQL))
        url = _psycopg_url(ADMIN_PG_URL, name).replace("postgresql://", "postgresql+asyncpg://", 1)

        async def build():
            eng = create_async_engine(url)
            try:
                await bootstrap_tenant_schema(eng, 1)
            finally:
                await eng.dispose()

        asyncio.run(build())
        c.execute(_read(_PIPELINE_PUBLIC_SQL))
        c.execute(_read(_LLM_USAGE_SQL))
        yield conn
    finally:
        conn.close()
        cur = cluster.control.cursor()
        cur.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


def _rows(conn, sql, params=None):
    c = conn.cursor()
    c.execute(sql, params)
    return c.fetchall()


def _count(conn, table):
    return _rows(conn, f"SELECT count(*) FROM public.{table}")[0][0]


def _choice_id(conn, job_key, provider, model):
    rows = _rows(
        conn,
        "SELECT id FROM public.ai_job_choices WHERE job_key = %s AND provider = %s AND model = %s",
        (job_key, provider, model),
    )
    assert len(rows) == 1, (job_key, provider, model, rows)
    return rows[0][0]


def _assignment(conn, job_key):
    return _rows(
        conn,
        "SELECT c.provider, c.model FROM public.ai_job_assignments a"
        " JOIN public.ai_job_choices c ON c.id = a.choice_id WHERE a.job_key = %s",
        (job_key,),
    )[0]


def _constraint_def(conn, name):
    return _rows(
        conn,
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint"
        " WHERE conrelid = 'public.llm_usage_events'::regclass AND conname = %s",
        (name,),
    )[0][0]


def _fails(conn, sql, params=None):
    """この文が例外になることを確かめる（接続は自動確定なので、後の文に影響しない）。"""
    import psycopg2

    c = conn.cursor()
    with pytest.raises(psycopg2.Error):
        c.execute(sql, params)


def _insert_usage(conn, outcome=None, error_code=None, purpose="line_extraction", sdk="google-genai"):
    cols = ["purpose", "model", "sdk"]
    vals = [purpose, "m", sdk]
    if outcome is not None:
        cols.append("outcome")
        vals.append(outcome)
    cols.append("error_code")
    vals.append(error_code)
    marks = ", ".join(["%s"] * len(cols))
    conn.cursor().execute(f"INSERT INTO public.llm_usage_events ({', '.join(cols)}) VALUES ({marks})", vals)


def test_a_row_counts_and_initial_assignments(db):
    c = db.cursor()
    c.execute(_read(_AI_JOB_SQL))
    assert _count(db, "ai_job_choices") == 17
    assert _count(db, "ai_job_assignments") == 5
    assert _count(db, "ai_job_assignment_history") == 0
    for job_key in _JOB_KEYS:
        assert _assignment(db, job_key) == _EXPECTED_ASSIGNMENTS[job_key], job_key


def test_b_rerun_keeps_changed_assignment(db):
    c = db.cursor()
    c.execute(_read(_AI_JOB_SQL))
    flash_id = _choice_id(db, "translation_outbound", "gemini", "gemini-2.5-flash")
    c.execute(
        "UPDATE public.ai_job_assignments SET choice_id = %s WHERE job_key = 'translation_outbound'",
        (flash_id,),
    )
    c.execute(_read(_AI_JOB_SQL))
    assert _assignment(db, "translation_outbound") == ("gemini", "gemini-2.5-flash")
    assert _count(db, "ai_job_choices") == 17
    assert _count(db, "ai_job_assignments") == 5
    assert _count(db, "ai_job_assignment_history") == 0


def test_c_rerun_keeps_values_added_by_later_migrations(db):
    c = db.cursor()
    c.execute(_read(_AI_JOB_SQL))

    purposes = (
        "'line_extraction', 'line_extraction_shadow', 'inventory_parse_fallback', 'translation_inbound',"
        " 'translation_inbound_escalation', 'translation_outbound', 'secretary_intent', 'test_future_purpose'"
    )
    c.execute("ALTER TABLE public.llm_usage_events DROP CONSTRAINT llm_usage_events_purpose_check")
    c.execute(
        "ALTER TABLE public.llm_usage_events ADD CONSTRAINT llm_usage_events_purpose_check"
        f" CHECK (purpose IN ({purposes}))"
    )
    _insert_usage(db, purpose="test_future_purpose")
    c.execute(_read(_AI_JOB_SQL))
    assert "test_future_purpose" in _constraint_def(db, "llm_usage_events_purpose_check")

    sdks = "'google-genai', 'google-generativeai', 'codex-cli', 'claude-code', 'test_future_sdk'"
    c.execute("ALTER TABLE public.llm_usage_events DROP CONSTRAINT llm_usage_events_sdk_check")
    c.execute(f"ALTER TABLE public.llm_usage_events ADD CONSTRAINT llm_usage_events_sdk_check CHECK (sdk IN ({sdks}))")
    _insert_usage(db, sdk="test_future_sdk")
    c.execute(_read(_AI_JOB_SQL))
    assert "test_future_sdk" in _constraint_def(db, "llm_usage_events_sdk_check")
    assert "test_future_purpose" in _constraint_def(db, "llm_usage_events_purpose_check")


def test_d_history_is_append_only(db):
    c = db.cursor()
    c.execute(_read(_AI_JOB_SQL))
    old_id = _choice_id(db, "translation_outbound", "gemini", "gemini-3.5-flash-lite")
    new_id = _choice_id(db, "translation_outbound", "gemini", "gemini-2.5-flash")
    c.execute("INSERT INTO public.users (id, email) VALUES (1001, 'ai-job-a@example.test')")
    c.execute(
        "INSERT INTO public.ai_job_assignment_history (job_key, old_choice_id, new_choice_id, changed_by)"
        " VALUES ('translation_outbound', %s, %s, 1001)",
        (old_id, new_id),
    )
    assert _count(db, "ai_job_assignment_history") == 1

    _fails(db, "UPDATE public.ai_job_assignment_history SET job_key = 'translation_inbound'")
    _fails(db, "DELETE FROM public.ai_job_assignment_history")
    _fails(db, "TRUNCATE public.ai_job_assignment_history")
    assert _count(db, "ai_job_assignment_history") == 1

    # users を消すと、履歴は消えず changed_by だけが NULL になる
    c.execute("DELETE FROM public.users WHERE id = 1001")
    rows = _rows(db, "SELECT job_key, old_choice_id, new_choice_id, changed_by FROM public.ai_job_assignment_history")
    assert rows == [("translation_outbound", old_id, new_id, None)]


def test_e_outcome_and_error_code(db):
    c = db.cursor()
    c.execute(_read(_AI_JOB_SQL))
    _fails(
        db,
        "INSERT INTO public.llm_usage_events (purpose, model, sdk, outcome, error_code)"
        " VALUES ('line_extraction', 'm', 'google-genai', 'ok', 'timeout')",
    )
    _fails(
        db,
        "INSERT INTO public.llm_usage_events (purpose, model, sdk, outcome, error_code)"
        " VALUES ('line_extraction', 'm', 'google-genai', 'failed', NULL)",
    )
    _fails(
        db,
        "INSERT INTO public.llm_usage_events (purpose, model, sdk, outcome, error_code)"
        " VALUES ('line_extraction', 'm', 'google-genai', 'failed', 'bad_code')",
    )
    assert _count(db, "llm_usage_events") == 0

    _insert_usage(db)
    assert _rows(db, "SELECT outcome, error_code FROM public.llm_usage_events") == [("ok", None)]
    _insert_usage(db, outcome="failed", error_code="timeout")
    assert _count(db, "llm_usage_events") == 2


def test_f_get_ai_assignment_reads_choice_and_raises_when_missing(db):
    """秘1: 読む関数が担当表から provider・model を返し、行が無ければ例外（既定値に逃げない）。"""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.services.ai_assignment import AiAssignment, AiAssignmentMissing, get_ai_assignment

    c = db.cursor()
    c.execute(_read(_AI_JOB_SQL))
    url = _psycopg_url(ADMIN_PG_URL, db.info.dbname).replace("postgresql://", "postgresql+asyncpg://", 1)

    async def read(job_key):
        eng = create_async_engine(url)
        try:
            async with AsyncSession(eng) as s:
                return await get_ai_assignment(s, job_key)
        finally:
            await eng.dispose()

    assert asyncio.run(read("secretary_intent")) == AiAssignment("claude", "sonnet")
    assert asyncio.run(read("line_extraction")) == AiAssignment("gemini", "gemini-3.1-flash-lite")
    c.execute("DELETE FROM public.ai_job_assignments WHERE job_key = 'secretary_intent'")
    with pytest.raises(AiAssignmentMissing):
        asyncio.run(read("secretary_intent"))
