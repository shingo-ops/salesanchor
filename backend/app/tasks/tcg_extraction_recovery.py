"""
抽出ジョブの停滞回収タスク。

design: docs/handoff/extraction-job-recovery/design.md §B

デプロイ時の強制コンテナ削除（.github/workflows/deploy.yml）や、
異常終了したワーカーによって、extraction_jobs が running/pending のまま
取り残されることがある。この beat タスクは10分ごとに実行し、
一定時間動きがないジョブを回収する。

回収の条件（根拠は design.md §A: 直近7日の attempt 所要時間は最大 31.9 秒、
tcg.extract_source_message の time_limit=330 秒）:
  (a) running のジョブ: 最新 attempt の started_at（無ければ created_at）から
      STALE_RUNNING_MINUTES 分以上たったものを pending に戻す。
  (b) pending のジョブ: created_at から STALE_PENDING_MINUTES 分以上たち、
      最新 attempt が無いか STALE_PENDING_MINUTES 分以上前に始まったものだけを、
      retry_extraction の手順4（extract_source_message_task.apply_async）と
      同じ方法で再投入する（対象外の pending ジョブを巻き込まない）。

新しい表・列は増やさない。既存の extraction_jobs.status と
extraction_attempts だけで判定する。
"""
from __future__ import annotations

import asyncio
import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

TCG_SCHEMA = "public"

# design.md §B: 15分。time_limit=330秒（5.5分）の倍以上の余裕を取る。
STALE_RUNNING_MINUTES = 15
STALE_PENDING_MINUTES = 15
# design.md §B: retry_extraction 内部の _MAX_JOBS=50 と一致させる。
MAX_RECOVER_PER_RUN = 50
# retry_extraction 内部の _COUNTDOWN_STEP と同じ値（backend/app/services/tcg_diagnostics_svc.py）。
# 件数×3秒の countdown で Celery への一斉投入を分散させる。
_COUNTDOWN_STEP = 3

_DATABASE_URL = os.getenv("DATABASE_URL", "").replace(
    "postgresql+asyncpg://", "postgresql://"
)


def _get_sync_engine():
    return create_engine(_DATABASE_URL, echo=False)


def recover_stale_running_jobs(session) -> list[str]:
    """
    running のまま STALE_RUNNING_MINUTES 分以上動きがないジョブを pending に戻す。

    最新 attempt の started_at（無ければ extraction_jobs.created_at）を基準にする。
    最大 MAX_RECOVER_PER_RUN 件、古いものから。

    Returns:
        pending に戻したジョブ ID のリスト（文字列）
    """
    rows = session.execute(
        text(
            f"""
            SELECT ej.id
            FROM {TCG_SCHEMA}.extraction_jobs ej
            LEFT JOIN LATERAL (
                SELECT ea.started_at
                FROM {TCG_SCHEMA}.extraction_attempts ea
                WHERE ea.extraction_job_id = ej.id
                ORDER BY ea.started_at DESC, ea.id DESC
                LIMIT 1
            ) latest_attempt ON true
            WHERE ej.status = 'running'
              AND COALESCE(latest_attempt.started_at, ej.created_at)
                  < NOW() - (:stale_minutes || ' minutes')::interval
            ORDER BY COALESCE(latest_attempt.started_at, ej.created_at) ASC
            LIMIT :max_recover
            """
        ),
        {"stale_minutes": STALE_RUNNING_MINUTES, "max_recover": MAX_RECOVER_PER_RUN},
    ).fetchall()

    job_ids = [str(row[0]) for row in rows]
    if not job_ids:
        return []

    session.execute(
        text(
            f"""
            UPDATE {TCG_SCHEMA}.extraction_jobs
            SET status = 'pending'
            WHERE id = ANY(CAST(:ids AS uuid[]))
              AND status = 'running'
            """
        ),
        {"ids": job_ids},
    )
    session.commit()
    return job_ids


def find_stale_pending_job_ids(session) -> list[str]:
    """
    pending のまま STALE_PENDING_MINUTES 分以上たった、再投入すべきジョブを探す。

    created_at から STALE_PENDING_MINUTES 分以上たち、
    最新 attempt が無いか STALE_PENDING_MINUTES 分以上前に始まったものが対象。
    最大 MAX_RECOVER_PER_RUN 件、古いものから。
    """
    rows = session.execute(
        text(
            f"""
            SELECT ej.id
            FROM {TCG_SCHEMA}.extraction_jobs ej
            LEFT JOIN LATERAL (
                SELECT ea.started_at
                FROM {TCG_SCHEMA}.extraction_attempts ea
                WHERE ea.extraction_job_id = ej.id
                ORDER BY ea.started_at DESC, ea.id DESC
                LIMIT 1
            ) latest_attempt ON true
            WHERE ej.status = 'pending'
              AND ej.created_at < NOW() - (:stale_minutes || ' minutes')::interval
              AND (
                  latest_attempt.started_at IS NULL
                  OR latest_attempt.started_at < NOW() - (:stale_minutes || ' minutes')::interval
              )
            ORDER BY ej.created_at ASC
            LIMIT :max_recover
            """
        ),
        {"stale_minutes": STALE_PENDING_MINUTES, "max_recover": MAX_RECOVER_PER_RUN},
    ).fetchall()
    return [str(row[0]) for row in rows]


async def _reenqueue_stale_pending_jobs(job_ids: list[str]) -> dict[str, int]:
    """
    停滞している pending ジョブ（job_ids）だけを再投入する。

    retry_extraction（backend/app/services/tcg_diagnostics_svc.py）の
    scope="pending" 経路は status='pending' の全件を対象にしてしまい、
    正常にキューで待っている新しいジョブまで巻き込んで二重投入する恐れがある
    （設計担当レビュー指摘）。そのため retry_extraction 自体は呼ばず、
    その手順4（extract_source_message_task.apply_async(
    args=(source_message_id,), countdown=i*_COUNTDOWN_STEP)）と同じ方法だけを
    踏襲し、対象は find_stale_pending_job_ids が返した job_ids に限定する。
    ステータスは変えない（pending のまま。retry_extraction の error→pending
    リセットはここでは行わない＝そもそも対象は既に pending）。

    tcg_extraction.py:610-642 (auto_distribute_after_analysis_task) と同じ
    パターンで、ワンショットの非同期エンジン/セッションを使う。
    """
    if not job_ids:
        return {"enqueued": 0, "skipped": 0}

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.database import DATABASE_URL  # noqa: PLC0415
    from app.tasks.tcg_extraction import extract_source_message_task  # noqa: PLC0415

    if extract_source_message_task is None:
        raise RuntimeError("Celery is not available (task not registered).")

    _connect_args: dict = {
        "prepared_statement_cache_size": 0,
        "server_settings": {"application_name": "salesanchor_celery_extraction_recovery"},
    }
    _engine = create_async_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=0,
        connect_args=_connect_args,
    )
    _Session = async_sessionmaker(_engine, expire_on_commit=False)
    try:
        async with _Session() as db:
            # 対象を再取得: id = ANY(:ids) AND status = 'pending' で絞り込み、
            # find_stale_pending_job_ids 実行後に状態が変わった行を除外する。
            rows = (
                await db.execute(
                    text(
                        f"""
                        SELECT id, source_message_id
                        FROM {TCG_SCHEMA}.extraction_jobs
                        WHERE id = ANY(CAST(:ids AS uuid[]))
                          AND status = 'pending'
                        ORDER BY created_at ASC
                        """
                    ),
                    {"ids": job_ids},
                )
            ).fetchall()

            source_message_ids = [str(row.source_message_id) for row in rows]
            for i, sm_id in enumerate(source_message_ids):
                extract_source_message_task.apply_async(
                    args=(sm_id,),
                    countdown=i * _COUNTDOWN_STEP,
                )
            return {"enqueued": len(rows), "skipped": len(job_ids) - len(rows)}
    finally:
        await _engine.dispose()


# 解析段の失敗（extraction_jobs.error_message='ANALYSIS_FAILED'）を1回だけ自動でやり直す。
# 設計: docs/handoff/analysis-failed-record/design.md。新しい列・migration なし。
ANALYSIS_RETRY_MIN_AGE_MINUTES = 5
MAX_ANALYSIS_RETRY_PER_RUN = 20


def retry_analysis_failed_jobs(session) -> list[str]:
    """解析失敗の v102 job を 'ANALYSIS_FAILED_RETRIED' に書き換えてから再解析タスクを積む（1 job 1 回だけ）。

    書き換えが 1 件更新されたときだけ積む。やり直しも失敗したら RETRIED のまま残り、再び拾わない。
    """
    from app.services.line_analysis_v102_svc import V102_PROMPT_VERSION_PREFIX  # noqa: PLC0415

    rows = session.execute(
        text(
            f"""
            SELECT ej.id
            FROM {TCG_SCHEMA}.extraction_jobs ej
            WHERE ej.status = 'done'
              AND ej.error_message = 'ANALYSIS_FAILED'
              AND ej.prompt_version LIKE :prefix
              AND ej.extracted_at < NOW() - (:min_age || ' minutes')::interval
            ORDER BY ej.extracted_at ASC
            LIMIT :max_retry
            """
        ),
        {
            "prefix": V102_PROMPT_VERSION_PREFIX + "%",
            "min_age": ANALYSIS_RETRY_MIN_AGE_MINUTES,
            "max_retry": MAX_ANALYSIS_RETRY_PER_RUN,
        },
    ).fetchall()

    enqueued: list[str] = []
    for row in rows:
        job_id = str(row[0])
        updated = session.execute(
            text(
                f"UPDATE {TCG_SCHEMA}.extraction_jobs SET error_message = 'ANALYSIS_FAILED_RETRIED' "
                "WHERE id = :ej AND error_message = 'ANALYSIS_FAILED'"
            ),
            {"ej": job_id},
        )
        session.commit()
        if updated.rowcount != 1:
            continue
        try:
            from app.tasks.tcg_extraction import v102_reanalyze_after_correction_task  # noqa: PLC0415

            if v102_reanalyze_after_correction_task is None:
                continue
            v102_reanalyze_after_correction_task.delay(job_id)
            enqueued.append(job_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[tcg_extraction_recovery] 解析やり直しの投入に失敗: ej=%s err=%s", job_id, type(exc).__name__)
    logger.info("[tcg_extraction_recovery] 解析失敗のやり直し: 対象%d件 投入%d件", len(rows), len(enqueued))
    return enqueued


# 一時的に断られた解析（extraction_jobs.error_message='API_ERROR'）を数分後に自動で送り直す。
# 設計: docs/handoff/api-error-auto-retry/design.md B。新しい列・migration なし。
API_ERROR_RETRY_MIN_AGE_MINUTES = 5
API_ERROR_RETRY_MAX_ATTEMPTS = 3
API_ERROR_RETRY_LOOKBACK_HOURS = 24
MAX_API_ERROR_RETRY_PER_RUN = 20


def retry_transient_api_error_jobs(session) -> list[str]:
    """一時的な断られ方で error になった v102 job を、items を消して pending に戻し、その id を返す（投入は呼び出し側）。

    置き換え済みの投稿・永続的な失敗・試行3回以上は対象外。戻しの UPDATE が 1 行のときだけ id を集める。
    """
    from app.services.line_analysis_v102_svc import V102_PROMPT_VERSION_PREFIX  # noqa: PLC0415

    rows = session.execute(
        text(
            f"""
            SELECT ej.id
            FROM {TCG_SCHEMA}.extraction_jobs ej
            JOIN {TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id
            JOIN LATERAL (
                SELECT ea.phase, ea.finished_at, ea.validation_result
                FROM {TCG_SCHEMA}.extraction_attempts ea
                WHERE ea.extraction_job_id = ej.id
                ORDER BY ea.started_at DESC, ea.id DESC
                LIMIT 1
            ) latest_attempt ON true
            WHERE ej.status = 'error'
              AND ej.error_message = 'API_ERROR'
              AND ej.prompt_version LIKE :prefix
              AND ej.created_at > NOW() - (:lookback_hours || ' hours')::interval
              AND sm.is_active = TRUE
              AND sm.superseded_by IS NULL
              AND latest_attempt.phase = 'failed'
              AND latest_attempt.finished_at < NOW() - (:min_age || ' minutes')::interval
              AND (
                  latest_attempt.validation_result->>'category' IN ('gemini_rate_limit', 'gemini_timeout')
                  OR (
                      latest_attempt.validation_result->>'category' = 'gemini_http_error'
                      AND (
                          latest_attempt.validation_result->>'raw' LIKE '%(HTTP 429)'
                          OR latest_attempt.validation_result->>'raw' LIKE '%(HTTP 500)'
                          OR latest_attempt.validation_result->>'raw' LIKE '%(HTTP 502)'
                          OR latest_attempt.validation_result->>'raw' LIKE '%(HTTP 503)'
                          OR latest_attempt.validation_result->>'raw' LIKE '%(HTTP 504)'
                      )
                  )
              )
              AND (
                  SELECT COUNT(*) FROM {TCG_SCHEMA}.extraction_attempts ea2
                  WHERE ea2.extraction_job_id = ej.id
              ) < :max_attempts
            ORDER BY ej.created_at ASC
            LIMIT :max_retry
            """
        ),
        {
            "prefix": V102_PROMPT_VERSION_PREFIX + "%",
            "lookback_hours": API_ERROR_RETRY_LOOKBACK_HOURS,
            "min_age": API_ERROR_RETRY_MIN_AGE_MINUTES,
            "max_attempts": API_ERROR_RETRY_MAX_ATTEMPTS,
            "max_retry": MAX_API_ERROR_RETRY_PER_RUN,
        },
    ).fetchall()

    reset_ids: list[str] = []
    for row in rows:
        job_id = str(row[0])
        try:
            # 手動の送り直し（tcg_diagnostics_svc.retry_extraction）と同じ手順: items を消してから pending に戻す
            session.execute(
                text(f"DELETE FROM {TCG_SCHEMA}.extraction_items WHERE extraction_job_id = :ej"),
                {"ej": job_id},
            )
            updated = session.execute(
                text(
                    f"UPDATE {TCG_SCHEMA}.extraction_jobs SET status = 'pending' "
                    "WHERE id = :ej AND status = 'error' AND error_message = 'API_ERROR'"
                ),
                {"ej": job_id},
            )
            if updated.rowcount != 1:
                session.rollback()
                continue
            session.commit()
            reset_ids.append(job_id)
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            logger.exception("[tcg_extraction_recovery] 一時的な失敗の送り直しに失敗: ej=%s err=%s", job_id, type(exc).__name__)
    return reset_ids


def _run_recovery() -> dict:
    engine = _get_sync_engine()
    try:
        Session = sessionmaker(engine)
        with Session() as session:
            recovered_running_ids = recover_stale_running_jobs(session)
            stale_pending_ids = find_stale_pending_job_ids(session)
            analysis_retry_ids = retry_analysis_failed_jobs(session)
            api_error_retry_ids = retry_transient_api_error_jobs(session)
    finally:
        engine.dispose()

    # 停滞 pending と、いま pending に戻した id を重複なく（順は保って）1回で投入する
    enqueue_ids = list(dict.fromkeys([*stale_pending_ids, *api_error_retry_ids]))
    reenqueue_result = {"enqueued": 0, "skipped": 0}
    if enqueue_ids:
        reenqueue_result = asyncio.run(_reenqueue_stale_pending_jobs(enqueue_ids))
    logger.info(
        "[tcg_extraction_recovery] 一時的な失敗の送り直し: 対象%d件 投入%d件",
        len(api_error_retry_ids), reenqueue_result.get("enqueued", 0),
    )

    result = {
        "recovered_running_count": len(recovered_running_ids),
        "recovered_running_ids": recovered_running_ids,
        "stale_pending_count": len(stale_pending_ids),
        "stale_pending_ids": stale_pending_ids,
        "reenqueued": reenqueue_result.get("enqueued", 0),
        "reenqueue_skipped": reenqueue_result.get("skipped", 0),
        "analysis_retry_count": len(analysis_retry_ids),
        "api_error_retry_count": len(api_error_retry_ids),
    }

    if recovered_running_ids or stale_pending_ids:
        logger.warning(
            "[tcg_extraction_recovery] running->pending: %d件 %s / "
            "pending 再投入対象: %d件 %s / 実際に再投入: %d件",
            len(recovered_running_ids),
            recovered_running_ids,
            len(stale_pending_ids),
            stale_pending_ids,
            reenqueue_result.get("enqueued", 0),
        )
    return result


# ---------------------------------------------------------------------------
# Celery タスク定義 (Redis 未起動時は登録のみ)
# ---------------------------------------------------------------------------

try:
    from app.celery_app import celery_app

    @celery_app.task(
        name="tcg.recover_stale_extraction_jobs",
        bind=True,
        max_retries=1,
        default_retry_delay=60,
        time_limit=180,
        soft_time_limit=150,
    )
    def recover_stale_extraction_jobs_task(self) -> dict:
        """
        Celery タスク: 停滞した extraction_jobs を回収する。

        beat_schedule により10分ごとに実行される。
        Redis 起動時のみ .delay() で非同期実行可能。
        """
        try:
            return _run_recovery()
        except Exception as exc:
            logger.exception("[tcg_extraction_recovery] task failed: %s", exc)
            raise self.retry(exc=exc) from exc

except Exception as _celery_init_err:  # noqa: BLE001
    # Redis 未起動 / Celery 初期化失敗時はタスクなしでモジュールのみ提供
    logger.warning(
        "[tcg_extraction_recovery] Celery task registration skipped: %s",
        _celery_init_err,
    )
