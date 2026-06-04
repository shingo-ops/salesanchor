"""ADR-107 (ADR-SA-14) 状態検証スクリプト（ADR-025 ② 定期バッチ）。

月次バッチ（月初）または新規成約/失注が累計10件追加されたタイミングで実行する。
psycopg2 同期接続で動作（stdlib のみ・追加依存なし）。

チェック内容:
  1. 較正の鮮度（最終較正日 + 蓄積件数）
  2. 入力データ量（メッセージ数・成約/失注件数）
  3. 確信度分布（低確信度割合が閾値超なら警告）
  4. スコア分布（極端な偏りがないか）
  5. ドリフト検知（直近30日 vs 前期 ±20pp 閾値）
  6. 自己成就監視（最有望 vs 要観察の実際成約率差が縮小していないか）

使用例:
  python scripts/check_priority_scoring_state.py [--tenant-id 1]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import httpx
import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# --- 閾値定数 ---
DATA_WARN_MESSAGES = 20
DATA_WARN_DEALS = 5
CALIBRATION_STALE_DAYS = 35          # 月次+5日の余裕
LOW_CONFIDENCE_WARN_PCT = 50         # 低確信度割合 >50% で警告
TIER_DRIFT_WARN_PP = 20.0            # ティア割合の前期比変化 ±20pp で警告
SELF_FULFILLMENT_WARN_RATIO = 0.5    # 最有望と要観察の成約率差が期待値の50%未満で警告


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


def check_calibration_freshness(cur: Any, tenant_id: int) -> CheckResult:
    """最終較正日 + 蓄積件数の確認。"""
    cur.execute(
        """
        SELECT calibrated_at, win_sample_size, loss_sample_size, is_cold_start
        FROM tenant_calibrations
        WHERE tenant_id = %s
        ORDER BY calibrated_at DESC
        LIMIT 1
        """,
        (tenant_id,),
    )
    row = cur.fetchone()
    if row is None:
        return CheckResult(
            "calibration_freshness", False,
            "較正レコードが存在しません（cold start）",
            {"is_cold_start": True},
        )

    age_days = (datetime.utcnow() - row["calibrated_at"].replace(tzinfo=None)).days
    stale = age_days > CALIBRATION_STALE_DAYS
    return CheckResult(
        "calibration_freshness", not stale,
        f"最終較正: {age_days}日前 / 成約{row['win_sample_size']}件 失注{row['loss_sample_size']}件",
        {
            "age_days": age_days,
            "win_n": row["win_sample_size"],
            "loss_n": row["loss_sample_size"],
            "is_cold_start": row["is_cold_start"],
        },
    )


def check_data_volume(cur: Any, tenant_id: int) -> CheckResult:
    """メッセージ数・成約/失注件数の確認。"""
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM message_labels WHERE tenant_id = %s",
        (tenant_id,),
    )
    msg_count = cur.fetchone()["cnt"]

    cur.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE i.status != 'cancelled') AS won_count,
            COUNT(*) FILTER (WHERE d.status = 'lost' OR d.lost_reason IS NOT NULL) AS lost_count
        FROM leads l
        LEFT JOIN invoices i ON i.lead_id = l.id
        LEFT JOIN deals d ON d.lead_id = l.id
        WHERE l.tenant_id = %s
        """,
        (tenant_id,),
    )
    deal_row = cur.fetchone()
    deal_count = (deal_row["won_count"] or 0) + (deal_row["lost_count"] or 0)

    insufficient = msg_count < DATA_WARN_MESSAGES or deal_count < DATA_WARN_DEALS
    return CheckResult(
        "data_volume", not insufficient,
        f"メッセージ{msg_count}件（閾値{DATA_WARN_MESSAGES}）/ 成約+失注{deal_count}件（閾値{DATA_WARN_DEALS}）",
        {"message_count": msg_count, "deal_count": deal_count},
    )


def check_confidence_distribution(cur: Any, tenant_id: int) -> CheckResult:
    """低確信度割合が閾値超なら警告。"""
    cur.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE confidence < 0.3) * 100.0 / NULLIF(COUNT(*), 0) AS low_pct,
            COUNT(*) AS total
        FROM customer_scores
        WHERE tenant_id = %s
        """,
        (tenant_id,),
    )
    row = cur.fetchone()
    if row["total"] == 0:
        return CheckResult("confidence_distribution", True, "スコアなし（計算対象なし）")

    low_pct = float(row["low_pct"] or 0)
    over = low_pct > LOW_CONFIDENCE_WARN_PCT
    return CheckResult(
        "confidence_distribution", not over,
        f"低確信度割合: {low_pct:.1f}%（閾値{LOW_CONFIDENCE_WARN_PCT}%）",
        {"low_confidence_pct": low_pct, "total_scores": row["total"]},
    )


def check_score_distribution(cur: Any, tenant_id: int) -> CheckResult:
    """スコア分布が極端に偏っていないか確認。"""
    cur.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE tier = '要観察') AS watching,
            COUNT(*) FILTER (WHERE tier = '有望')   AS promising,
            COUNT(*) FILTER (WHERE tier = '最有望') AS top,
            COUNT(*)                                 AS total
        FROM customer_scores
        WHERE tenant_id = %s
        """,
        (tenant_id,),
    )
    row = cur.fetchone()
    if row["total"] == 0:
        return CheckResult("score_distribution", True, "スコアなし")

    top_pct = row["top"] * 100.0 / row["total"]
    all_top = top_pct >= 90
    return CheckResult(
        "score_distribution", not all_top,
        f"要観察:{row['watching']} / 有望:{row['promising']} / 最有望:{row['top']}",
        {"watching": row["watching"], "promising": row["promising"], "top": row["top"]},
    )


def check_drift(cur: Any, tenant_id: int) -> CheckResult:
    """直近30日と前30〜60日のスコア分布を比較。±20pp 超で警告。"""
    now = datetime.utcnow()
    period1_end = now
    period1_start = now - timedelta(days=30)
    period2_end = period1_start
    period2_start = now - timedelta(days=60)

    def tier_dist(start: datetime, end: datetime) -> dict[str, float]:
        cur.execute(
            """
            SELECT tier, COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER(), 0) AS pct
            FROM customer_scores
            WHERE tenant_id = %s AND scored_at BETWEEN %s AND %s
            GROUP BY tier
            """,
            (tenant_id, start, end),
        )
        return {r["tier"]: float(r["pct"] or 0) for r in cur.fetchall()}

    dist1 = tier_dist(period1_start, period1_end)
    dist2 = tier_dist(period2_start, period2_end)

    if not dist1 and not dist2:
        return CheckResult("drift", True, "十分なデータなし（ドリフト計算スキップ）")

    max_shift = 0.0
    worst_tier = ""
    for tier in ["要観察", "有望", "最有望"]:
        shift = abs(dist1.get(tier, 0) - dist2.get(tier, 0))
        if shift > max_shift:
            max_shift = shift
            worst_tier = tier

    over = max_shift > TIER_DRIFT_WARN_PP
    return CheckResult(
        "drift", not over,
        f"最大ドリフト: {worst_tier} {max_shift:.1f}pp（閾値±{TIER_DRIFT_WARN_PP}pp）",
        {"max_shift_pp": max_shift, "worst_tier": worst_tier, "dist_current": dist1},
    )


def check_self_fulfillment(cur: Any, tenant_id: int) -> CheckResult:
    """
    最有望スコア客と要観察スコア客の実際成約率差を確認。
    差が期待値の50%未満に縮小したら自己成就の兆候として警告。
    """
    cur.execute(
        """
        SELECT
            cs.tier,
            COUNT(*) FILTER (WHERE i.status != 'cancelled') * 100.0
                / NULLIF(COUNT(*), 0) AS actual_win_pct,
            COUNT(*) AS total
        FROM customer_scores cs
        JOIN leads l ON l.id = cs.lead_id
        LEFT JOIN invoices i ON i.lead_id = l.id
        WHERE cs.tenant_id = %s
          AND cs.tier IN ('最有望', '要観察')
        GROUP BY cs.tier
        """,
        (tenant_id,),
    )
    rows = {r["tier"]: r for r in cur.fetchall()}

    if "最有望" not in rows or "要観察" not in rows:
        return CheckResult("self_fulfillment", True, "比較データ不足（スキップ）")

    top_pct = float(rows["最有望"]["actual_win_pct"] or 0)
    watch_pct = float(rows["要観察"]["actual_win_pct"] or 0)
    gap = top_pct - watch_pct

    # ナイーブな期待差分: 最有望>=50%、要観察<=20% → 期待差30pp
    expected_gap = 30.0
    warn = gap < expected_gap * SELF_FULFILLMENT_WARN_RATIO

    return CheckResult(
        "self_fulfillment", not warn,
        f"最有望成約率:{top_pct:.1f}% / 要観察成約率:{watch_pct:.1f}% / 差:{gap:.1f}pp（期待差{expected_gap}pp）",
        {"top_win_pct": top_pct, "watching_win_pct": watch_pct, "gap": gap},
    )


def run_all_checks(cur: Any, tenant_id: int) -> list[CheckResult]:
    checkers = [
        check_calibration_freshness,
        check_data_volume,
        check_confidence_distribution,
        check_score_distribution,
        check_drift,
        check_self_fulfillment,
    ]
    results = []
    for checker in checkers:
        try:
            results.append(checker(cur, tenant_id))
        except Exception as exc:  # noqa: BLE001
            results.append(CheckResult(
                checker.__name__, False,
                f"チェック実行エラー: {exc}",
            ))
    return results


def _post_discord(url: str, content: str) -> None:
    try:
        resp = httpx.post(url, json={"content": content[:1800]}, timeout=10.0)
        if resp.status_code >= 400:
            logger.warning("Discord POST failed: %s", resp.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Discord POST error: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="ADR-107 状態検証スクリプト")
    parser.add_argument("--tenant-id", type=int, default=None,
                        help="対象テナントID（省略時は全テナント）")
    args = parser.parse_args()

    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        logger.error("DATABASE_URL が未設定")
        sys.exit(1)

    webhook_url = os.environ.get("ADMIN_NOTIFICATION_DISCORD_WEBHOOK", "")

    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if args.tenant_id:
        tenant_ids = [args.tenant_id]
    else:
        cur.execute("SELECT id FROM public.tenants WHERE is_active = TRUE ORDER BY id")
        tenant_ids = [r["id"] for r in cur.fetchall()]

    all_ok = True
    for tenant_id in tenant_ids:
        schema = f"tenant_{tenant_id:03d}"
        cur.execute(f"SET search_path = {schema}, public")
        cur.execute(f"SET app.tenant_id = '{tenant_id}'")

        results = run_all_checks(cur, tenant_id)
        failed = [r for r in results if not r.ok]

        for r in results:
            status = "✅" if r.ok else "❌"
            logger.info("[tenant_%03d] %s %s: %s", tenant_id, status, r.name, r.message)

        if failed and webhook_url:
            lines = [f":bar_chart: **ADR-107 状態チェック失敗** (tenant_id={tenant_id})"]
            for r in failed:
                lines.append(f"- ❌ `{r.name}`: {r.message}")
            _post_discord(webhook_url, "\n".join(lines))
            all_ok = False

    cur.close()
    conn.close()
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
