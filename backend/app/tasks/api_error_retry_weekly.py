"""ADR-1050: 解析の一時的な失敗の送り直しの件数を毎週月曜に管理者用の Discord へ送る。

0 件でも毎週送る（届かない＝止まった、と区別するため）。DB は読むだけ。
設計: docs/handoff/api-error-retry-governance/design.md B
"""
import asyncio
import logging

from celery import shared_task
from sqlalchemy import text

from app.services.discord_notifier import _get_webhook_url, _post_discord_webhook
from app.tasks.tcg_extraction_recovery import (
    API_ERROR_RETRY_LOOKBACK_HOURS,
    API_ERROR_RETRY_MAX_ATTEMPTS,
    TCG_SCHEMA,
)

logger = logging.getLogger(__name__)

WEEKLY_DAYS = 7
ATTENTION_TRANSIENT_JOBS = 20

_TRANSIENT_CONDITION = """
    EXISTS (
        SELECT 1 FROM {schema}.extraction_attempts ea
        WHERE ea.extraction_job_id = ej.id
          AND ea.phase = 'failed'
          AND (
              ea.validation_result->>'category' IN ('gemini_rate_limit', 'gemini_timeout')
              OR (
                  ea.validation_result->>'category' = 'gemini_http_error'
                  AND (
                      ea.validation_result->>'raw' LIKE '%(HTTP 429)'
                      OR ea.validation_result->>'raw' LIKE '%(HTTP 500)'
                      OR ea.validation_result->>'raw' LIKE '%(HTTP 502)'
                      OR ea.validation_result->>'raw' LIKE '%(HTTP 503)'
                      OR ea.validation_result->>'raw' LIKE '%(HTTP 504)'
                  )
              )
          )
    )
""".format(schema=TCG_SCHEMA)

_GIVEN_UP_CONDITION = """
    ej.status = 'error'
    AND ej.error_message = 'API_ERROR'
    AND (
        (SELECT COUNT(*) FROM {schema}.extraction_attempts ea2 WHERE ea2.extraction_job_id = ej.id) >= :max_attempts
        OR ej.created_at < NOW() - (:lookback_hours || ' hours')::interval
    )
""".format(schema=TCG_SCHEMA)

_COUNT_SQL = text(f"""
SELECT
  count(*) AS transient_jobs,
  count(*) FILTER (WHERE ej.status = 'done') AS recovered_jobs,
  count(*) FILTER (WHERE {_GIVEN_UP_CONDITION}) AS given_up_jobs
FROM {TCG_SCHEMA}.extraction_jobs ej
WHERE ej.prompt_version LIKE :prefix
  AND ej.created_at > NOW() - (:days || ' days')::interval
  AND {_TRANSIENT_CONDITION}
""")


def _params() -> dict:
    from app.services.line_analysis_v102_svc import V102_PROMPT_VERSION_PREFIX

    return {
        "prefix": V102_PROMPT_VERSION_PREFIX + "%",
        "days": WEEKLY_DAYS,
        "max_attempts": API_ERROR_RETRY_MAX_ATTEMPTS,
        "lookback_hours": API_ERROR_RETRY_LOOKBACK_HOURS,
    }


def build_message(counts: dict) -> str:
    transient = int(counts.get("transient_jobs") or 0)
    recovered = int(counts.get("recovered_jobs") or 0)
    given_up = int(counts.get("given_up_jobs") or 0)
    attention = given_up >= 1 or transient >= ATTENTION_TRANSIENT_JOBS
    icon = "⚠️ 要調査" if attention else "✅"
    return "\n".join([
        f"{icon} 解析の送り直し 週次（ADR-1050）",
        f"直前{WEEKLY_DAYS}日に一時的に断られた投稿: {transient} 件",
        f"・送り直しで解析が終わった: {recovered} 件",
        f"・3回送り直しても終わらなかった: {given_up} 件",
    ])


async def _run_report() -> dict:
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        row = (await db.execute(_COUNT_SQL, _params())).mappings().one()
    counts = dict(row)
    url = _get_webhook_url()
    if not url:
        logger.warning("ADMIN_NOTIFICATION_DISCORD_WEBHOOK is not set; skip api error retry weekly report")
        return {"counts": counts, "sent": False}
    sent = await _post_discord_webhook(url, build_message(counts))
    return {"counts": counts, "sent": sent}


@shared_task(name="app.tasks.api_error_retry_weekly.report_api_error_retry_weekly")
def report_api_error_retry_weekly() -> dict:
    from app.database import engine

    try:
        return asyncio.run(_run_report())
    finally:
        asyncio.run(engine.dispose())
