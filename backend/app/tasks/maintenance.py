"""
メンテナンス定期タスク。

- 監査ログアーカイブ: 90日以上前のログを削除（テナントスキーマ）
- データアクセスイベント削除: 60日以上前を削除（public スキーマ）
- 認証イベント削除: 90日以上前を削除（public スキーマ）

Celery Beat により毎日深夜に実行。
"""

import logging
import os
import time

from celery import shared_task
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import set_tenant_context_sync

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "").replace(
    "postgresql+asyncpg://", "postgresql://"
)

# 保持期間（環境変数で上書き可能）
AUDIT_LOG_RETENTION_DAYS = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "90"))
DATA_ACCESS_RETENTION_DAYS = int(os.getenv("DATA_ACCESS_RETENTION_DAYS", "60"))
AUTH_EVENT_RETENTION_DAYS = int(os.getenv("AUTH_EVENT_RETENTION_DAYS", "90"))

# 閲覧専用ページ（ADR-1019 Q7）。環境変数にしない（プライバシーポリシーの記載と揃えるため）
VIEWER_RETENTION_DAYS = 90  # 期限切れ trial・停止 suspended を消すまで
VIEWER_PENDING_DAYS = 7  # 申込のまま確認されない pending を消すまで
VIEWER_LOGIN_EVENT_RETENTION_DAYS = 90

# バッチ削除サイズ（1トランザクションあたりの最大削除件数）
# 5000件 × ~10ms/commit ≒ 50ms ロック → 並行INSERTへの影響を最小化
_BATCH_SIZE = int(os.getenv("RETENTION_BATCH_SIZE", "5000"))

# バッチ間スリープ（ms）: autovacuum・他クエリにCPUを譲る
_BATCH_SLEEP_MS = int(os.getenv("RETENTION_BATCH_SLEEP_MS", "100"))


def _get_sync_engine():
    """同期SQLAlchemyエンジンを返す（テスト時のモック差し替えポイント）。"""
    return create_engine(DATABASE_URL, echo=False)


def _delete_in_batches(table: str, interval: str) -> int:
    """指定テーブルから古いレコードをバッチ分割で安全に削除する。

    - 1バッチ = _BATCH_SIZE 件ずつコミット（ロック保持時間を短縮）
    - バッチ間に _BATCH_SLEEP_MS ms スリープ（autovacuum・他クエリへ処理を譲る）
    - `table` は必ず呼び出し元でハードコード定数から選択すること（SQLi防止）

    根拠（外部事例）:
    - 単発DELETE は100GB規模で最大5時間ロック・900%クエリ劣化（実事例）
    - バッチ1000〜5000件 × スリープで影響を2〜3%に抑制
    - Discord: 保持ポリシー未整備で€800,000 GDPR制裁

    Returns:
        削除した総件数
    """
    engine = _get_sync_engine()
    Session = sessionmaker(engine)
    total_deleted = 0
    batch_num = 0

    while True:
        with Session() as session:
            result = session.execute(
                text(f"""
                    DELETE FROM {table}
                    WHERE id IN (
                        SELECT id FROM {table}
                        WHERE created_at < NOW() - INTERVAL :interval
                        ORDER BY created_at ASC
                        LIMIT :batch_size
                    )
                """),
                {"interval": interval, "batch_size": _BATCH_SIZE},
            )
            session.commit()

        count = result.rowcount if result.rowcount >= 0 else 0
        total_deleted += count
        batch_num += 1

        if count < _BATCH_SIZE:
            # 削除対象がバッチサイズ未満 → 残件なし、終了
            break

        logger.info(
            "%s: バッチ %d 完了 %d件削除（累計 %d件）",
            table, batch_num, count, total_deleted,
        )
        time.sleep(_BATCH_SLEEP_MS / 1000.0)

    return total_deleted


@shared_task(
    name="app.tasks.maintenance.archive_audit_logs",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def archive_audit_logs():
    """全テナントの90日以上前の監査ログを削除する（テナントスキーマ）。"""
    engine = _get_sync_engine()
    Session = sessionmaker(engine)

    with Session() as session:
        result = session.execute(
            text("SELECT id FROM tenants WHERE is_active = true")
        )
        tenant_ids = [row[0] for row in result]

    total_deleted = 0
    for tenant_id in tenant_ids:
        try:
            with Session() as session:
                set_tenant_context_sync(session, tenant_id)

                result = session.execute(text(f"""
                    DELETE FROM audit_logs
                    WHERE created_at < NOW() - INTERVAL '{AUDIT_LOG_RETENTION_DAYS} days'
                """))
                deleted = result.rowcount if result.rowcount >= 0 else 0
                session.commit()

                if deleted > 0:
                    total_deleted += deleted
                    logger.info(
                        "テナント %d: 監査ログ %d件を削除", tenant_id, deleted
                    )
        except Exception:
            logger.exception("テナント %d の監査ログアーカイブに失敗", tenant_id)

    logger.info("監査ログアーカイブ完了: 合計 %d件 削除", total_deleted)
    return {"deleted": total_deleted, "tenants_processed": len(tenant_ids)}


@shared_task(
    name="app.tasks.maintenance.purge_data_access_events",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def purge_data_access_events():
    """public.data_access_events の 60日以上前のレコードをバッチ分割で削除する。

    保持期間60日の根拠:
    - GDPR 最低30日 + セキュリティインシデント調査余裕（30日超は珍しくない）
    - SOC2/ISO27001 推奨の最低保持期間を上回る
    """
    interval = f"{DATA_ACCESS_RETENTION_DAYS} days"
    deleted = _delete_in_batches("public.data_access_events", interval)
    logger.info("data_access_events: 合計 %d件 削除（保持期間 %d日）", deleted, DATA_ACCESS_RETENTION_DAYS)
    return {"deleted": deleted}


@shared_task(
    name="app.tasks.maintenance.purge_auth_events",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def purge_auth_events():
    """public.auth_events の 90日以上前のレコードをバッチ分割で削除する。

    保持期間90日の根拠:
    - SOC2・ISO27001 推奨の認証ログ保持期間
    - auth_events は data_access_events より発生頻度が低い
    """
    interval = f"{AUTH_EVENT_RETENTION_DAYS} days"
    deleted = _delete_in_batches("public.auth_events", interval)
    logger.info("auth_events: 合計 %d件 削除（保持期間 %d日）", deleted, AUTH_EVENT_RETENTION_DAYS)
    return {"deleted": deleted}


@shared_task(
    name="app.tasks.maintenance.purge_viewer_accounts",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def purge_viewer_accounts():
    """閲覧専用アカウントの毎日の掃除（ADR-1019 Q7）。public の表なのでテナント文脈は使わない。

    1. 期限切れから 90 日たった trial  2. 停止（suspend 記録）から 90 日たった suspended
    3. 7 日たった pending  4. 90 日より古いログイン記録
    アカウントを消すと、ログイン記録・状態履歴・鍵は CASCADE で一緒に消える。
    件数だけログに出す（email は出さない）。
    """
    engine = _get_sync_engine()
    Session = sessionmaker(engine)
    with Session() as session:
        trial_expired = session.execute(
            text(f"""
                DELETE FROM public.viewer_accounts
                WHERE status = 'trial' AND trial_expires_at < NOW() - INTERVAL '{VIEWER_RETENTION_DAYS} days'
            """)
        ).rowcount
        suspended = session.execute(
            text(f"""
                DELETE FROM public.viewer_accounts a
                WHERE a.status = 'suspended'
                  AND (
                      SELECT max(c.created_at) FROM public.viewer_status_changes c
                      WHERE c.viewer_id = a.id AND c.action = 'suspend'
                  ) < NOW() - INTERVAL '{VIEWER_RETENTION_DAYS} days'
            """)
        ).rowcount
        pending = session.execute(
            text(f"""
                DELETE FROM public.viewer_accounts
                WHERE status = 'pending' AND created_at < NOW() - INTERVAL '{VIEWER_PENDING_DAYS} days'
            """)
        ).rowcount
        session.commit()
    login_events = _delete_in_batches(
        "public.viewer_login_events", f"{VIEWER_LOGIN_EVENT_RETENTION_DAYS} days"
    )
    result = {
        "trial_expired": max(trial_expired, 0),
        "suspended": max(suspended, 0),
        "pending": max(pending, 0),
        "login_events": login_events,
    }
    logger.info("viewer_accounts 掃除: %s", result)
    return result


# 新しい機械の許可（ADR-1055）。環境変数にしない（設計書 A-2「片付け」の値）
LOGIN_REQUEST_RETENTION_DAYS = 90  # 許可依頼を残す日数
DEVICE_UNUSED_DAYS = 180  # この日数使わない機械は失効扱い（devices.py の DEVICE_IDLE_DAYS と同じ）
DEVICE_AFTER_REVOKE_DAYS = 90  # 取り消し・失効扱いから消すまで


@shared_task(
    name="app.tasks.maintenance.purge_new_device_records",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def purge_new_device_records():
    """90日より古い許可依頼と、取り消し・180日未使用から90日たった機械を消す（ADR-1055 A-2「片付け」）。

    public の表なのでテナント文脈は使わない。件数だけログに出す。
    """
    engine = _get_sync_engine()
    Session = sessionmaker(engine)
    with Session() as session:
        requests_deleted = session.execute(
            text(
                "DELETE FROM public.auth_login_requests "
                "WHERE created_at < NOW() - make_interval(days => :d)"
            ),
            {"d": LOGIN_REQUEST_RETENTION_DAYS},
        ).rowcount
        devices_deleted = session.execute(
            text(
                "DELETE FROM public.user_trusted_devices "
                "WHERE (revoked_at IS NOT NULL AND revoked_at < NOW() - make_interval(days => :after)) "
                "   OR (revoked_at IS NULL AND COALESCE(last_used_at, created_at) "
                "       < NOW() - make_interval(days => :unused + :after))"
            ),
            {"after": DEVICE_AFTER_REVOKE_DAYS, "unused": DEVICE_UNUSED_DAYS},
        ).rowcount
        session.commit()
    result = {"login_requests": max(requests_deleted, 0), "devices": max(devices_deleted, 0)}
    logger.info("新しい機械の許可の片付け: %s", result)
    return result


@shared_task(
    name="app.tasks.maintenance.expire_login_requests",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
)
def expire_login_requests():
    """期限切れの pending を expired にする（5分ごと・ADR-1055）。

    決まった人の、ほかのいつもの機械の小窓も閉じるため、人宛ての合図（auth.login_request）を送る。
    合図の失敗は無視する（fail-open）。
    """
    from app.realtime.publisher import publish_user_change_sync
    from app.realtime.topics import TOPIC_AUTH_LOGIN_REQUEST

    engine = _get_sync_engine()
    Session = sessionmaker(engine)
    with Session() as session:
        rows = session.execute(
            text(
                "UPDATE public.auth_login_requests SET status = 'expired', decided_at = NOW() "
                "WHERE status = 'pending' AND expires_at < NOW() RETURNING user_id"
            )
        ).fetchall()
        session.commit()
    user_ids = sorted({int(r[0]) for r in rows})
    for uid in user_ids:
        publish_user_change_sync(uid, TOPIC_AUTH_LOGIN_REQUEST)
    logger.info("許可依頼の期限切れ: %d件（%d人）", len(rows), len(user_ids))
    return {"expired": len(rows), "users": len(user_ids)}


def _geoip_url(year: int, month: int) -> str:
    return f"https://download.db-ip.com/free/dbip-city-lite-{year:04d}-{month:02d}.mmdb.gz"


@shared_task(name="app.tasks.maintenance.refresh_geoip_db")
def refresh_geoip_db():
    """場所の目安の元データ（DB-IP City Lite・MMDB）を取り込む（毎月3日・ADR-1055 D9）。

    一時ファイルに落として rename で入れ替える。落とせなくても認証は止めない（例外は外に出さず結果に書く）。
    書き先はコードの既定の場所（worker は GEOIP_DB_PATH を受け取らない）。
    """
    import gzip
    import shutil
    from datetime import datetime, timezone
    from pathlib import Path

    import requests

    from app.auth import geo

    dest = Path(geo.DEFAULT_GEOIP_PATH)
    now = datetime.now(timezone.utc)
    candidates = [(now.year, now.month)]
    prev_year, prev_month = (now.year, now.month - 1) if now.month > 1 else (now.year - 1, 12)
    candidates.append((prev_year, prev_month))
    last_error = "unknown"
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".tmp")
        for year, month in candidates:
            try:
                resp = requests.get(_geoip_url(year, month), stream=True, timeout=(10, 120))
                if resp.status_code != 200:
                    last_error = f"http_{resp.status_code}"
                    continue
                with tmp.open("wb") as out, gzip.GzipFile(fileobj=resp.raw) as gz:
                    shutil.copyfileobj(gz, out)
                tmp.replace(dest)
                logger.info("geoip: %04d-%02d を取り込み（%d バイト）", year, month, dest.stat().st_size)
                return {"status": "ok", "month": f"{year:04d}-{month:02d}", "bytes": dest.stat().st_size}
            except Exception as e:  # noqa: BLE001
                last_error = type(e).__name__
    except Exception as e:  # noqa: BLE001
        last_error = type(e).__name__
    logger.warning("geoip: 取り込みに失敗（認証は止めない）: %s", last_error)
    return {"status": "failed", "error": last_error}


def _geoip_missing_on_start(**_kwargs) -> None:
    """worker の起動時にファイルが無ければ、1回だけ取りに行く。失敗しても何もしない。"""
    try:
        from pathlib import Path

        from app.auth import geo

        if not Path(geo.DEFAULT_GEOIP_PATH).exists():
            refresh_geoip_db.delay()
    except Exception:  # noqa: BLE001
        logger.warning("geoip: 起動時の取り込みの依頼に失敗（認証は止めない）")


try:
    from celery.signals import worker_ready

    worker_ready.connect(_geoip_missing_on_start, weak=False)
except Exception:  # noqa: BLE001
    pass


@shared_task(
    name="app.tasks.maintenance.purge_expired_inventory_offers",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def purge_expired_inventory_offers():
    """public.inventory の expires_at を過ぎた仕入元オファーを物理削除する。

    在庫オファーは時間失効モデル (QA 2026-05-30 / ひとしさん):
    - F6 承認時に expires_at = offered_at + 18h を付与（_upsert_inventory_offer）。
    - 本タスクが期限切れ行を削除する。中央在庫 (products.stock_quantity) は触らない。
    - expires_at IS NULL の行（手動の恒久オファー等）は対象外。

    _delete_in_batches は created_at 基準のため、expires_at 基準の本タスクは
    専用ループでバッチ削除する（バッチサイズ・スリープは共通定数を流用）。
    """
    engine = _get_sync_engine()
    Session = sessionmaker(engine)
    total_deleted = 0
    batch_num = 0

    while True:
        with Session() as session:
            result = session.execute(
                text("""
                    DELETE FROM public.inventory
                    WHERE id IN (
                        SELECT id FROM public.inventory
                        WHERE expires_at IS NOT NULL AND expires_at < NOW()
                        ORDER BY expires_at ASC
                        LIMIT :batch_size
                    )
                """),
                {"batch_size": _BATCH_SIZE},
            )
            session.commit()

        count = result.rowcount if result.rowcount >= 0 else 0
        total_deleted += count
        batch_num += 1

        if count < _BATCH_SIZE:
            break

        logger.info(
            "inventory offers: バッチ %d 完了 %d件削除（累計 %d件）",
            batch_num, count, total_deleted,
        )
        time.sleep(_BATCH_SLEEP_MS / 1000.0)

    logger.info("inventory offers: 合計 %d件 失効削除", total_deleted)
    return {"deleted": total_deleted}
