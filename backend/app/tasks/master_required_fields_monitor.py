"""ADR-1020 便4c: 共用商品の入れ忘れ件数と「調べたが無い」の印の件数を、毎週管理者用の Discord に送る。

0 件でも毎週送る（届かない＝止まった、と区別するため）。DB は読むだけ。
読む表のうち public.products は共用の行（tenant_id IS NULL）をテナント設定なしで読め、
印の表は SELECT が USING (true)、検索・除外ワードの表は RLS なし（2026-10-17 本番で確認）。
"""
import asyncio
import logging
import os
from datetime import datetime, timezone

import httpx
from celery import shared_task
from sqlalchemy import text

logger = logging.getLogger(__name__)

_WEBHOOK_ENV = "ADMIN_NOTIFICATION_DISCORD_WEBHOOK"

# 便3（必須の検査）を本番に出した時刻。これ以降に作られた共用商品を「止める仕組みのあと」として数える
_SINCE = datetime(2026, 10, 17, 1, 38, tzinfo=timezone.utc)

_FIELDS = ("name", "name_en", "mark", "release_date", "search_keywords",
           "exclude_keywords", "work_id", "product_format_id", "product_category_id")

_COUNT_SQL = text("""
WITH p AS (
  SELECT * FROM public.products WHERE tenant_id IS NULL AND created_at >= :since
), c AS (
  SELECT product_id, field_code FROM public.product_blank_confirmations
)
SELECT
  count(*) AS new_rows,
  count(*) FILTER (WHERE coalesce(trim(name), '') = '') AS name,
  count(*) FILTER (WHERE coalesce(trim(name_en), '') = '' AND NOT EXISTS (SELECT 1 FROM c WHERE c.product_id = p.id AND c.field_code = 'name_en')) AS name_en,
  count(*) FILTER (WHERE coalesce(trim(mark), '') = '' AND NOT EXISTS (SELECT 1 FROM c WHERE c.product_id = p.id AND c.field_code = 'mark')) AS mark,
  count(*) FILTER (WHERE release_date IS NULL AND NOT EXISTS (SELECT 1 FROM c WHERE c.product_id = p.id AND c.field_code = 'release_date')) AS release_date,
  count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM public.product_search_keywords k WHERE k.product_id = p.id AND trim(k.keyword) != '')) AS search_keywords,
  count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM public.product_exclude_keywords k WHERE k.product_id = p.id AND trim(k.keyword) != '') AND NOT EXISTS (SELECT 1 FROM c WHERE c.product_id = p.id AND c.field_code = 'exclude_keywords')) AS exclude_keywords,
  count(*) FILTER (WHERE work_id IS NULL) AS work_id,
  count(*) FILTER (WHERE product_format_id IS NULL) AS product_format_id,
  count(*) FILTER (WHERE product_category_id IS NULL) AS product_category_id
FROM p
""")

_MARKS_SQL = text("SELECT field_code, count(*) FROM public.product_blank_confirmations GROUP BY field_code ORDER BY field_code")


async def _post_discord(content: str) -> None:
    url = (os.getenv(_WEBHOOK_ENV) or "").strip()
    if not url:
        logger.warning("%s is not set; skip master required fields report", _WEBHOOK_ENV)
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json={"content": content[:1800], "username": "共用商品 必須項目 週次"})
        if res.status_code >= 400:
            logger.warning("master required fields report: discord status %s", res.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("master required fields report: discord error %s", type(exc).__name__)


def build_message(counts: dict, marks: list[tuple[str, int]]) -> str:
    ng = {f: int(counts.get(f) or 0) for f in _FIELDS}
    total_ng = sum(ng.values())
    head = "✅" if total_ng == 0 else "⚠️"
    lines = [
        f"{head} 共用商品の必須9項目（ADR-1020）: 便3反映後に作られた共用商品 {int(counts.get('new_rows') or 0)} 件",
        "空のまま・印なしの件数: " + " / ".join(f"{f} {n}" for f, n in ng.items()),
        "「調べたが無い」の印: " + (" / ".join(f"{code} {int(n)}" for code, n in marks) if marks else "0 件"),
    ]
    return "\n".join(lines)


async def _run_report() -> dict:
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        row = (await db.execute(_COUNT_SQL, {"since": _SINCE})).mappings().one()
        marks = [(r[0], r[1]) for r in (await db.execute(_MARKS_SQL)).all()]
    counts = dict(row)
    await _post_discord(build_message(counts, marks))
    return {"counts": counts, "marks": marks}


@shared_task(name="app.tasks.master_required_fields_monitor.report_master_required_fields")
def report_master_required_fields() -> dict:
    from app.database import engine

    try:
        return asyncio.run(_run_report())
    finally:
        asyncio.run(engine.dispose())
