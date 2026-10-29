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

def _transient_condition(alias: str) -> str:
    """一時的な断られ方（429・500・502・503・504・タイムアウト・レート制限）の条件。alias は extraction_attempts の別名。"""
    return f"""
    {alias}.phase = 'failed'
    AND (
        {alias}.validation_result->>'category' IN ('gemini_rate_limit', 'gemini_timeout')
        OR (
            {alias}.validation_result->>'category' = 'gemini_http_error'
            AND (
                {alias}.validation_result->>'raw' LIKE '%(HTTP 429)'
                OR {alias}.validation_result->>'raw' LIKE '%(HTTP 500)'
                OR {alias}.validation_result->>'raw' LIKE '%(HTTP 502)'
                OR {alias}.validation_result->>'raw' LIKE '%(HTTP 503)'
                OR {alias}.validation_result->>'raw' LIKE '%(HTTP 504)'
            )
        )
    )
"""


_TRANSIENT_CONDITION = f"""
    EXISTS (
        SELECT 1 FROM {TCG_SCHEMA}.extraction_attempts ea
        WHERE ea.extraction_job_id = ej.id
          AND {_transient_condition("ea")}
    )
"""

# tcg_extraction_recovery.find_given_up_api_error_jobs と同じ意味（置き換え済みの投稿・一時的でない断られ方は数えない）
_GIVEN_UP_CONDITION = f"""
    ej.status = 'error'
    AND ej.error_message = 'API_ERROR'
    AND sm.is_active = TRUE
    AND sm.superseded_by IS NULL
    AND {_transient_condition("latest")}
    AND (
        (SELECT COUNT(*) FROM {TCG_SCHEMA}.extraction_attempts ea2 WHERE ea2.extraction_job_id = ej.id) >= :max_attempts
        OR ej.created_at < NOW() - make_interval(hours => :lookback_hours)
    )
"""

_COUNT_SQL = text(f"""
SELECT
  count(*) AS transient_jobs,
  count(*) FILTER (WHERE ej.status = 'done') AS recovered_jobs,
  count(*) FILTER (WHERE {_GIVEN_UP_CONDITION}) AS given_up_jobs
FROM {TCG_SCHEMA}.extraction_jobs ej
LEFT JOIN {TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id
LEFT JOIN LATERAL (
    SELECT ea3.phase, ea3.validation_result
    FROM {TCG_SCHEMA}.extraction_attempts ea3
    WHERE ea3.extraction_job_id = ej.id
    ORDER BY ea3.started_at DESC, ea3.id DESC
    LIMIT 1
) latest ON true
WHERE ej.prompt_version LIKE :prefix
  AND ej.created_at > NOW() - make_interval(days => :days)
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
