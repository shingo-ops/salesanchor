"""買取価格変動アラートチェッカー。ADR-157

スクレイパー実行後に呼び出され、アクティブなルールに対して
直近2回の price_log を比較し、閾値超過時に Discord 通知を送る。
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def check_alerts() -> int:
    """全アクティブルールをチェックし、発火した件数を返す。"""
    fired = 0
    async with AsyncSessionLocal() as db:
        await db.execute(text("SET LOCAL app.is_operator = 'true'"))

        # アクティブルールを取得
        rules = (
            await db.execute(
                text("""
                    SELECT id, name, card_game, shop_code, product_type,
                           shop_product_id, direction, threshold_pct,
                           price_grade, last_notified_at, cooldown_minutes
                    FROM public.buyback_alert_rules
                    WHERE is_active = true
                """)
            )
        ).mappings().all()

        if not rules:
            logger.info("[buyback_alert] アクティブルール 0 件、スキップ")
            return 0

        now = datetime.now(timezone.utc)

        for rule in rules:
            # クールダウン判定
            if rule["last_notified_at"]:
                cooldown_until = rule["last_notified_at"] + timedelta(
                    minutes=rule["cooldown_minutes"]
                )
                if now < cooldown_until:
                    continue

            # 対象商品の直近2回の価格を取得
            conditions = []
            params: dict = {"grade": rule["price_grade"]}
            if rule["shop_product_id"]:
                conditions.append("bsp.id = :product_id")
                params["product_id"] = rule["shop_product_id"]
            if rule["card_game"]:
                conditions.append("bsp.card_game = :card_game")
                params["card_game"] = rule["card_game"]
            if rule["shop_code"]:
                conditions.append("bsp.shop_code = :shop_code")
                params["shop_code"] = rule["shop_code"]
            if rule["product_type"]:
                conditions.append("bsp.product_type = :product_type")
                params["product_type"] = rule["product_type"]

            where = ("AND " + " AND ".join(conditions)) if conditions else ""
            grade_col = rule["price_grade"]

            # 各商品の直近2回の価格を取得
            price_changes = (
                await db.execute(
                    text(f"""
                        WITH ranked AS (
                            SELECT bpl.shop_product_id, bpl.{grade_col}, bpl.fetched_at,
                                   bsp.product_name, bsp.shop_code,
                                   ROW_NUMBER() OVER (
                                       PARTITION BY bpl.shop_product_id
                                       ORDER BY bpl.fetched_at DESC
                                   ) as rn
                            FROM public.buyback_price_logs bpl
                            JOIN public.buyback_shop_products bsp ON bsp.id = bpl.shop_product_id
                            WHERE bpl.{grade_col} IS NOT NULL {where}
                        )
                        SELECT
                            r1.shop_product_id, r1.product_name, r1.shop_code,
                            r1.{grade_col} as current_price,
                            r2.{grade_col} as previous_price
                        FROM ranked r1
                        JOIN ranked r2 ON r2.shop_product_id = r1.shop_product_id AND r2.rn = 2
                        WHERE r1.rn = 1
                          AND r1.{grade_col} != r2.{grade_col}
                          AND r2.{grade_col} > 0
                    """),
                    params,
                )
            ).mappings().all()

            threshold = float(rule["threshold_pct"])
            alerts_for_rule: list[dict] = []

            for row in price_changes:
                current = row["current_price"]
                previous = row["previous_price"]
                change_pct = ((current - previous) / previous) * 100

                direction = rule["direction"]
                if direction == "down" and change_pct >= 0:
                    continue
                if direction == "up" and change_pct <= 0:
                    continue

                if abs(change_pct) >= threshold:
                    alerts_for_rule.append({
                        "product_name": row["product_name"],
                        "shop_code": row["shop_code"],
                        "current_price": current,
                        "previous_price": previous,
                        "change_pct": round(change_pct, 1),
                    })

            if alerts_for_rule:
                await _send_alert_notification(rule, alerts_for_rule)
                # last_notified_at 更新
                await db.execute(
                    text("""
                        UPDATE public.buyback_alert_rules
                        SET last_notified_at = now()
                        WHERE id = :rule_id
                    """),
                    {"rule_id": rule["id"]},
                )
                await db.commit()
                fired += 1
                logger.info(
                    "[buyback_alert] ルール '%s' 発火: %d 件",
                    rule["name"],
                    len(alerts_for_rule),
                )

    return fired


async def _send_alert_notification(rule: dict, alerts: list[dict]) -> None:
    """Discord webhook で通知を送信する。"""
    import os

    import httpx

    webhook_url = os.environ.get("ADMIN_NOTIFICATION_DISCORD_WEBHOOK")
    if not webhook_url:
        logger.warning("[buyback_alert] ADMIN_NOTIFICATION_DISCORD_WEBHOOK 未設定、通知スキップ")
        return

    direction_label = {"down": "下落", "up": "上昇", "both": "変動"}
    dir_text = direction_label.get(rule["direction"], "変動")

    lines = []
    for a in alerts[:10]:  # 最大10件
        arrow = "📉" if a["change_pct"] < 0 else "📈"
        lines.append(
            f"{arrow} **{a['product_name']}** ({a['shop_code']})\n"
            f"  ¥{a['previous_price']:,} → ¥{a['current_price']:,} ({a['change_pct']:+.1f}%)"
        )

    if len(alerts) > 10:
        lines.append(f"... 他 {len(alerts) - 10} 件")

    description = "\n".join(lines)
    embed = {
        "title": f"🔔 買取価格{dir_text}アラート: {rule['name']}",
        "description": description,
        "color": 0xE74C3C if rule["direction"] == "down" else 0x2ECC71,
        "footer": {"text": f"閾値: {rule['threshold_pct']}% | グレード: {rule['price_grade']}"},
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json={"embeds": [embed]})
            resp.raise_for_status()
    except Exception:
        logger.exception("[buyback_alert] Discord 通知送信失敗")
