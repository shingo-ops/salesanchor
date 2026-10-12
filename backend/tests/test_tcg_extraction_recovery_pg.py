"""
抽出ジョブの停滞回収タスクの PostgreSQL 受け入れテスト。

design: docs/handoff/extraction-job-recovery/design.md §C (T1, T2)

pg フィクスチャは disposable CI PostgreSQL サービス限定
（GITHUB_ACTIONS=="true" 前提。ローカル実行は不可 — 既存の *_pg.py と同じ制約）。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import sessionmaker

from app.tasks import tcg_extraction_recovery as recovery
from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401

_NOW = datetime.now(timezone.utc)


def _insert_job(connection, *, status, created_at):
    sid, jid = str(uuid4()), str(uuid4())
    with connection.cursor() as cur:
        cur.execute(
            f"""INSERT INTO {SCHEMA}.source_messages
                (id, supplier_channel_id, raw_text, raw_sha256, is_active, received_at)
                SELECT %s, id, %s, %s, true, now() FROM {SCHEMA}.supplier_channels LIMIT 1""",
            (sid, "テスト原文", uuid4().hex),
        )
        cur.execute(
            f"""INSERT INTO {SCHEMA}.extraction_jobs (id, source_message_id, status, created_at)
                VALUES (%s, %s, %s, %s)""",
            (jid, sid, status, created_at),
        )
    return sid, jid


def _insert_attempt(connection, job_id, source_message_id, *, started_at):
    with connection.cursor() as cur:
        cur.execute(
            f"""INSERT INTO {SCHEMA}.extraction_attempts
                (id, extraction_job_id, source_message_id, started_at, phase,
                 input_sha256, input_bytes, requested_model, prompt_version)
                VALUES (%s, %s, %s, %s, 'started', %s, 1, 'synthetic-model', 'v1')""",
            (str(uuid4()), job_id, source_message_id, started_at, uuid4().hex),
        )


def _sync_session(pg):
    _, engine, _ = pg
    return sessionmaker(engine)()


class TestRecoverStaleRunningJobsPg:
    def test_fresh_running_job_is_untouched(self, pg, monkeypatch):
        """T1: attempt started_at が15分未満の running ジョブは対象外"""
        monkeypatch.setattr(recovery, "TCG_SCHEMA", SCHEMA)
        connection, _, _ = pg
        sid, jid = _insert_job(connection, status="running", created_at=_NOW - timedelta(minutes=30))
        _insert_attempt(connection, jid, sid, started_at=_NOW - timedelta(minutes=5))

        session = _sync_session(pg)
        try:
            result = recovery.recover_stale_running_jobs(session)
        finally:
            session.close()

        assert jid not in result

    def test_stale_running_job_is_recovered_to_pending(self, pg, monkeypatch):
        """T2: attempt started_at が15分以上前の running ジョブは pending に戻る"""
        monkeypatch.setattr(recovery, "TCG_SCHEMA", SCHEMA)
        connection, _, _ = pg
        sid, jid = _insert_job(connection, status="running", created_at=_NOW - timedelta(minutes=30))
        _insert_attempt(connection, jid, sid, started_at=_NOW - timedelta(minutes=20))

        session = _sync_session(pg)
        try:
            result = recovery.recover_stale_running_jobs(session)
        finally:
            session.close()

        assert jid in result
        with connection.cursor() as cur:
            cur.execute(f"SELECT status FROM {SCHEMA}.extraction_jobs WHERE id = %s", (jid,))
            assert cur.fetchone()[0] == "pending"

    def test_stale_running_job_without_attempt_uses_created_at(self, pg, monkeypatch):
        """attempt が無い running ジョブは created_at を基準にする"""
        monkeypatch.setattr(recovery, "TCG_SCHEMA", SCHEMA)
        connection, _, _ = pg
        _sid, jid = _insert_job(connection, status="running", created_at=_NOW - timedelta(minutes=20))

        session = _sync_session(pg)
        try:
            result = recovery.recover_stale_running_jobs(session)
        finally:
            session.close()

        assert jid in result


class TestFindStalePendingJobIdsPg:
    def test_fresh_pending_job_is_excluded(self, pg, monkeypatch):
        """T1: created_at が15分未満の pending ジョブは対象外"""
        monkeypatch.setattr(recovery, "TCG_SCHEMA", SCHEMA)
        connection, _, _ = pg
        _sid, jid = _insert_job(connection, status="pending", created_at=_NOW - timedelta(minutes=5))

        session = _sync_session(pg)
        try:
            result = recovery.find_stale_pending_job_ids(session)
        finally:
            session.close()

        assert jid not in result

    def test_stale_pending_job_without_attempt_is_included(self, pg, monkeypatch):
        """T2: created_at が15分以上前で attempt が無い pending ジョブは対象"""
        monkeypatch.setattr(recovery, "TCG_SCHEMA", SCHEMA)
        connection, _, _ = pg
        _sid, jid = _insert_job(connection, status="pending", created_at=_NOW - timedelta(minutes=20))

        session = _sync_session(pg)
        try:
            result = recovery.find_stale_pending_job_ids(session)
        finally:
            session.close()

        assert jid in result

    def test_pending_job_with_recent_attempt_is_excluded(self, pg, monkeypatch):
        """created_at は古いが、直近に attempt が始まっている pending ジョブは対象外"""
        monkeypatch.setattr(recovery, "TCG_SCHEMA", SCHEMA)
        connection, _, _ = pg
        sid, jid = _insert_job(connection, status="pending", created_at=_NOW - timedelta(minutes=30))
        _insert_attempt(connection, jid, sid, started_at=_NOW - timedelta(minutes=2))

        session = _sync_session(pg)
        try:
            result = recovery.find_stale_pending_job_ids(session)
        finally:
            session.close()

        assert jid not in result

    def test_max_recover_per_run_caps_result(self, pg, monkeypatch):
        """T3: MAX_RECOVER_PER_RUN を超える対象があっても上限件数だけ返す"""
        monkeypatch.setattr(recovery, "TCG_SCHEMA", SCHEMA)
        monkeypatch.setattr(recovery, "MAX_RECOVER_PER_RUN", 2)
        connection, _, _ = pg
        for _ in range(3):
            _insert_job(connection, status="pending", created_at=_NOW - timedelta(minutes=20))

        session = _sync_session(pg)
        try:
            result = recovery.find_stale_pending_job_ids(session)
        finally:
            session.close()

        assert len(result) == 2
