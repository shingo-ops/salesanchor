"""ADR-1027 便3: バルク系のまとめ売りの見張り。件数を毎週月曜に管理者用の Discord へ送る。

0 件でも毎週送る（届かない＝止まった、と区別するため）。DB は読むだけ（public の表を直接読む）。
区分の値と理由コードは定数を import して SQL のバインド引数で渡す（文字列の直書き禁止）。
"""
import asyncio
import logging
import os

import httpx
from celery import shared_task
from sqlalchemy import text

from app.services.gemini_raw_copy_v102_product_first import PRODUCT_KUBUN_BULK
from app.services.line_analysis_v102_svc import (
    REASON_BULK_PRICE_BASIS_UNKNOWN,
    REASON_BUNDLE_UNVERIFIED,
)

logger = logging.getLogger(__name__)

_WEBHOOK_ENV = "ADMIN_NOTIFICATION_DISCORD_WEBHOOK"

# docs/handoff/bundle-sale/design.md 便3 の基準値。2026-10-22 測定
BASELINE_PRICE_UNKNOWN = 14
BASELINE_ALL_BUNDLE_UNVERIFIED = 5

_COUNT_SQL = text("""
WITH cur AS (
  SELECT ar.review_reasons, pc.kubun_type
  FROM public.analysis_results ar
  LEFT JOIN public.products p ON p.id = ar.product_id
  LEFT JOIN public.tcg_product_categories pc ON pc.id = p.product_category_id
  WHERE ar.is_current
)
SELECT
  count(*) FILTER (WHERE kubun_type = :bulk) AS bulk_rows,
  count(*) FILTER (WHERE kubun_type = :bulk AND ',' || coalesce(review_reasons,'') || ',' LIKE '%,' || :r_price || ',%') AS bulk_price_basis_unknown,
  count(*) FILTER (WHERE kubun_type = :bulk AND ',' || coalesce(review_reasons,'') || ',' LIKE '%,' || :r_bundle || ',%') AS bulk_bundle_unverified,
  count(*) FILTER (WHERE ',' || coalesce(review_reasons,'') || ',' LIKE '%,' || :r_bundle || ',%') AS all_bundle_unverified
FROM cur
""")


def _params() -> dict:
    return {
        "bulk": PRODUCT_KUBUN_BULK,
        "r_price": REASON_BULK_PRICE_BASIS_UNKNOWN,
        "r_bundle": REASON_BUNDLE_UNVERIFIED,
    }


async def _post_discord(content: str) -> None:
    url = (os.getenv(_WEBHOOK_ENV) or "").strip()
    if not url:
        logger.warning("%s is not set; skip bundle bulk report", _WEBHOOK_ENV)
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json={"content": content[:1800], "username": "バルク系まとめ売り 週次"})
        if res.status_code >= 400:
            logger.warning("bundle bulk report: discord status %s", res.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("bundle bulk report: discord error %s", type(exc).__name__)


def build_message(counts: dict) -> str:
    bulk_rows = int(counts.get("bulk_rows") or 0)
    price = int(counts.get("bulk_price_basis_unknown") or 0)
    bulk_bundle = int(counts.get("bulk_bundle_unverified") or 0)
    all_bundle = int(counts.get("all_bundle_unverified") or 0)
    icon = "⚠️" if (price > BASELINE_PRICE_UNKNOWN or bulk_bundle > 0) else "✅"
    lines = [
        f"{icon} バルク系のまとめ売り 週次（ADR-1027）",
        f"現行のバルク系（全エンジン）: {bulk_rows}行",
        f"・値段の基準が読めない: {price}行（基準 {BASELINE_PRICE_UNKNOWN}）",
        f"・まとめ数を確かめられない: {bulk_bundle}行（基準 0）",
        f"参考・全区分のまとめ数を確かめられない: {all_bundle}行（商品が決まっていない行を含む・基準 {BASELINE_ALL_BUNDLE_UNVERIFIED}）",
    ]
    return "\n".join(lines)


async def _run_report() -> dict:
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        row = (await db.execute(_COUNT_SQL, _params())).mappings().one()
    counts = dict(row)
    await _post_discord(build_message(counts))
    return {"counts": counts}


@shared_task(name="app.tasks.bundle_bulk_monitor.report_bundle_bulk")
def report_bundle_bulk() -> dict:
    from app.database import engine

    try:
        return asyncio.run(_run_report())
    finally:
        asyncio.run(engine.dispose())
