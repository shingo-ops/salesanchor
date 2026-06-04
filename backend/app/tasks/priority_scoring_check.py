"""
ADR-107 (SA-14) §13 安全装置 — 月次定期チェック Celery タスク。

ADR-025 3点セット ② 定期バッチ の実装。
Celery Beat により毎月1日 AM2:00 JST に全テナント分実行する。

チェック内容 (check_priority_scoring_state.py に委譲):
  1. 較正の鮮度（最終較正日 + 蓄積件数）
  2. 入力データ量（メッセージ数・成約/失注件数）
  3. 確信度分布（低確信度割合 >50% で警告）
  4. スコア分布（最有望 >90% で警告）
  5. ドリフト検知（直近30日 vs 前期 ±20pp 閾値）
  6. 自己成就監視（最有望 vs 要観察の実際成約率差が縮小していないか）

失敗時: discord_notifier 経由で ADMIN_NOTIFICATION_DISCORD_WEBHOOK に通知。
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from celery import shared_task

logger = logging.getLogger(__name__)

# check_priority_scoring_state.py は scripts/ に置かれているため、
# Celery コンテナ内 /app/scripts/ をインポートパスに追加する
_SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


@shared_task(
    name="app.tasks.priority_scoring_check.run_priority_scoring_check",
    bind=True,
    max_retries=2,
    default_retry_delay=600,  # 10分後にリトライ
    acks_late=True,
)
def run_priority_scoring_check(self, tenant_id: int | None = None) -> dict:
    """
    全テナント（または指定テナント）の優先度スコアリング状態を検証する。

    ADR-107 §D「ADR-025 3点セット ② 定期バッチ」として月次実行。
    check_priority_scoring_state.py の main() ロジックを Celery タスクとして呼び出す。

    Args:
        tenant_id: 対象テナントID。None の場合は全テナント。

    Returns:
        {"ok": bool, "checked_tenants": int, "failed_checks": list[str]}
    """
    try:
        # check_priority_scoring_state は standalone スクリプトとして設計されているため、
        # 内部関数を直接インポートして呼び出す（sys.exit を回避）
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "check_priority_scoring_state",
            str(_SCRIPTS_DIR / "check_priority_scoring_state.py"),
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("check_priority_scoring_state.py が見つかりません")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[attr-defined]

        import psycopg2
        import psycopg2.extras

        dsn = os.environ.get("DATABASE_URL", "").replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        if not dsn:
            raise RuntimeError("DATABASE_URL が未設定")

        conn = psycopg2.connect(dsn)
        conn.autocommit = True
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            if tenant_id is not None:
                tenant_ids = [tenant_id]
            else:
                cur.execute(
                    "SELECT id FROM public.tenants WHERE is_active = TRUE ORDER BY id"
                )
                tenant_ids = [r["id"] for r in cur.fetchall()]

            all_ok = True
            failed_checks: list[str] = []

            for tid in tenant_ids:
                schema = f"tenant_{tid:03d}"
                cur.execute(f"SET search_path = {schema}, public")
                cur.execute(f"SET app.tenant_id = '{tid}'")

                results = module.run_all_checks(cur, tid)
                failed = [r for r in results if not r.ok]

                for r in results:
                    status = "✅" if r.ok else "❌"
                    logger.info(
                        "[priority_check][tenant_%03d] %s %s: %s",
                        tid, status, r.name, r.message,
                    )

                if failed:
                    all_ok = False
                    failed_checks.extend(
                        f"tenant_{tid:03d}/{r.name}" for r in failed
                    )
                    # 固有通知関数があるチェックは個別 Discord 通知
                    _dispatch_notifications(module, tid, failed)

        finally:
            try:
                cur.close()
                conn.close()
            except Exception:  # noqa: BLE001
                pass

        logger.info(
            "[priority_check] 完了: tenants=%d, ok=%s, failed=%s",
            len(tenant_ids), all_ok, len(failed_checks),
        )
        return {
            "ok": all_ok,
            "checked_tenants": len(tenant_ids),
            "failed_checks": failed_checks,
        }

    except Exception as exc:
        logger.exception("[priority_check] タスク失敗: %s", exc)
        # Discord 通知（較正失敗扱い）
        _notify_task_failure(str(exc))
        raise self.retry(exc=exc)


def _dispatch_notifications(module: object, tenant_id: int, failed: list) -> None:
    """
    失敗チェックに対応する ADR-107 固有通知関数を呼び出す。
    check_priority_scoring_state._NOTIFIER_AVAILABLE が True の場合のみ実行。
    """
    notifier_available = getattr(module, "_NOTIFIER_AVAILABLE", False)
    if not notifier_available:
        return

    notify_data_insufficient = getattr(module, "notify_priority_data_insufficient", None)
    notify_drift = getattr(module, "notify_priority_drift_detected", None)
    notify_calibration = getattr(module, "notify_priority_calibration_failed", None)

    for r in failed:
        try:
            if r.name == "data_volume" and notify_data_insufficient:
                asyncio.run(notify_data_insufficient(
                    tenant_id,
                    message_count=r.details.get("message_count", 0),
                    deal_count=r.details.get("deal_count", 0),
                ))
            elif r.name == "drift" and notify_drift:
                asyncio.run(notify_drift(
                    tenant_id,
                    period_days=30,
                    tier_shift_pp=r.details.get("max_shift_pp", 0.0),
                    tier_name=r.details.get("worst_tier", ""),
                ))
            elif r.name == "calibration_freshness" and notify_calibration:
                asyncio.run(notify_calibration(tenant_id, r.message))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[priority_check] 通知関数呼び出し失敗: %s %s", r.name, exc
            )


def _notify_task_failure(error_message: str) -> None:
    """タスク自体の失敗を Discord に通知する。"""
    try:
        from app.services.discord_notifier import notify_priority_calibration_failed

        # tenant_id=-1 はタスクレベル失敗（テナント固有でない）のシグナル
        asyncio.run(
            notify_priority_calibration_failed(
                -1,
                f"[Celery タスク失敗] run_priority_scoring_check: {error_message[:200]}",
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[priority_check] タスク失敗通知自体が失敗: %s", exc)
