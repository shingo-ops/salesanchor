"""
Celery アプリケーション定義。

ブローカー: Redis DB1
結果バックエンド: Redis DB2
タイムゾーン: Asia/Tokyo
"""

import os

from celery import Celery
from celery.schedules import crontab

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")

celery_app = Celery(
    "salesanchor",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.dashboard",
        "app.tasks.data_deletion",
        "app.tasks.email_tasks",
        "app.tasks.maintenance",
        "app.tasks.avatar",
        "app.tasks.refresh_meta_tokens",
        "app.tasks.reports",
        "app.tasks.verify_meta_subscriptions",
        "app.tasks.priority_scoring_check",
        "app.tasks.translation",  # ADR-110: 翻訳バックグラウンドタスク
        "app.tasks.sa02_recon_monitor",  # SA-02 §10: 並走期間 日次突合
        "app.tasks.review_mail_monitor",  # review@salesanchor.jp 新着メール → Discord 通知
        "app.tasks.ops_mail_monitor",  # さくらの点検・障害のメール → 運用 Discord（outage-recovery-watch 便3）
        "app.tasks.fx_rate_updater",     # 為替レート SSOT: USD/JPY を1日2回更新
        "app.tasks.tcg_mirror",          # MIG-05 Task 3: TCG マスタミラーシート 日次書き出し
        "app.tasks.tcg_extraction",      # MIG-04 Stage 2: Gemini 抽出タスク
        "app.tasks.tcg_extraction_recovery",  # 抽出ジョブの停滞回収（design: docs/handoff/extraction-job-recovery/design.md）
        "app.tasks.tcg_import_discard",  # REVIEW-STAGE: 期限切れ保留ジョブの破棄
        "app.tasks.rule_test",           # Rule Test System: ルールテスト実行
        "app.tasks.buyback_scraper",     # ADR-157: 買取相場ログ（シンソク + 買取ホムラ）
        "app.tasks.ai_ops_heartbeat",  # ADR-1012 段階1 便5: celery の止まりの見張り
        "app.tasks.viewer_inventory_cache",  # ADR-1019 段2: 閲覧ページの在庫の作り置き
        "app.tasks.master_required_fields_monitor",  # ADR-1020 便4c: 共用商品の必須項目の週次件数
        "app.tasks.bundle_bulk_monitor",  # ADR-1027 便3: バルク系のまとめ売りの週次件数
        "app.tasks.api_error_retry_weekly",  # ADR-1050: 解析の送り直しの週次件数
        "app.tasks.viewer_share_flag_monitor",  # ADR-1019 段6: 閲覧者の使い回しの疑いを運用 Discord へ
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Tokyo",
    enable_utc=True,
    # タスク結果の有効期限: 24時間
    result_expires=86400,
    # ワーカーがタスクをプリフェッチしすぎないようにする
    worker_prefetch_multiplier=1,
    # タスクの再試行設定
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# 定期タスクのスケジュール
celery_app.conf.beat_schedule = {
    # 顧客アバター画像URLを毎日AM2:00 JSTに全テナント分一括更新
    # Meta Platform Terms: 24h超のキャッシュ禁止 → Redis TTL=23h と組み合わせて準拠
    "refresh-all-avatars": {
        "task": "app.tasks.avatar.refresh_all_avatars",
        "schedule": crontab(hour=2, minute=0),
    },
    # ダッシュボードKPIを10分ごとに全テナント分計算
    "refresh-dashboard-kpis": {
        "task": "app.tasks.dashboard.refresh_all_tenant_kpis",
        "schedule": 600.0,  # 10分
    },
    # 監査ログアーカイブを毎日AM4:00に実行
    "archive-old-audit-logs": {
        "task": "app.tasks.maintenance.archive_audit_logs",
        "schedule": crontab(hour=4, minute=0),
    },
    # Meta Page Access Token を毎日AM3:00 JSTにリフレッシュ（Phase 1-E F1-S2）
    "refresh-meta-page-tokens": {
        "task": "app.tasks.refresh_meta_tokens.refresh_all_meta_page_tokens",
        "schedule": crontab(hour=3, minute=0),
    },
    # Meta 接続レコードの整合性（暗号鍵 + Meta 側 subscribed_apps）を毎日AM4:30 JSTに検証（ADR-024）
    "verify-meta-subscriptions": {
        "task": "app.tasks.verify_meta_subscriptions.verify_all_meta_subscriptions",
        "schedule": crontab(hour=4, minute=30),
    },
    # data_access_events の保持ポリシー（60日超を毎日 AM5:00 に削除）
    # バッチ分割削除でロック競合・WAL肥大を防止
    # 根拠: GDPR 30日+ セキュリティインシデント調査余裕 = 60日
    "purge-data-access-events": {
        "task": "app.tasks.maintenance.purge_data_access_events",
        "schedule": crontab(hour=5, minute=0),
    },
    # auth_events の保持ポリシー（90日超を毎日 AM5:30 に削除）
    # 30分ずらすことで data_access_events タスクとの重複実行を防止
    # 根拠: SOC2・ISO27001 推奨の認証ログ保持期間
    "purge-auth-events": {
        "task": "app.tasks.maintenance.purge_auth_events",
        "schedule": crontab(hour=5, minute=30),
    },
    # 閲覧専用ページの掃除（期限切れ trial／停止／pending／ログイン記録・毎日 AM5:45・ADR-1019 Q7）
    "purge-viewer-accounts": {
        "task": "app.tasks.maintenance.purge_viewer_accounts",
        "schedule": crontab(hour=5, minute=45),
    },
    # 仕入元オファー (public.inventory) の時間失効: expires_at を過ぎた行を 30分ごとに削除
    # QA 2026-05-30: F6 承認時に expires_at=offered_at+18h を付与する時間失効モデル。
    # 30分粒度なので実際の寿命は 18h〜18.5h。在庫数 (stock_quantity) は触らない。
    "purge-expired-inventory-offers": {
        "task": "app.tasks.maintenance.purge_expired_inventory_offers",
        "schedule": 1800.0,  # 30分
    },
    # ADR-107 §13 安全装置 — 優先度スコアリング月次定期チェック（毎月1日 AM2:00 JST）
    # 較正鮮度・データ量・確信度分布・スコア分布・ドリフト・自己成就監視の6点を全テナントに実施。
    # 失敗時は discord_notifier 経由で ADMIN_NOTIFICATION_DISCORD_WEBHOOK に通知。
    # ADR-025 3点セット ② 定期バッチ に相当。
    "priority-scoring-monthly-check": {
        "task": "app.tasks.priority_scoring_check.run_priority_scoring_check",
        "schedule": crontab(hour=2, minute=0, day_of_month=1),
    },
    # ADR-110: 翻訳健全性チェック + Discord 通知（1時間ごと）
    "check-translation-health": {
        "task": "app.tasks.translation.check_translation_health",
        "schedule": crontab(minute=0),  # 毎時0分
    },
    # SA-02 §10: 並走期間 日次突合（meta_messages vs conversation_logs）毎日 AM8:00 JST
    # 差異あり → Discord 通知。差異ゼロ → INFO ログのみ。
    # 並走終了（段階2移行完了 + 読み取り切替後14日）後にこのエントリを削除すること。
    "sa02-daily-recon": {
        "task": "app.tasks.sa02_recon_monitor.run_sa02_daily_recon",
        "schedule": crontab(hour=8, minute=0),  # JST 8:00（timezone=Asia/Tokyo が適用済み）
    },
    # review@salesanchor.jp の INBOX を 5 分ごとに確認して新着を Discord 通知
    # 未設定（REVIEW_MAIL_IMAP_HOST 等）の場合は no-op で安全スキップ
    "review-mail-discord-notifier": {
        "task": "app.tasks.review_mail_monitor.check_review_mail_inbox",
        "schedule": 300.0,  # 5分
    },
    # 運用の受け箱を 5 分ごとに確認し、さくらの点検・障害のメールを運用 Discord へ（outage-recovery-watch 便3）
    # 未設定（OPS_MAIL_IMAP_USER 等）の場合は no-op で安全スキップ
    "ops-mail-discord-notifier": {
        "task": "app.tasks.ops_mail_monitor.check_ops_mail_inbox",
        "schedule": 300.0,  # 5分
    },
    # 為替レート SSOT: USD/JPY を毎日 AM6:00 JST に取得して public.app_fx_rate_history に追記
    # （ADR-148 2026-10-03 追記: public.app_fx_rates へのUPSERTから履歴テーブルへの追記専用INSERTに切替）
    # 外部 API: open.er-api.com（API キー不要）。失敗時は前回値を残して警告ログのみ。
    "update-fx-rate-morning": {
        "task": "app.tasks.fx_rate_updater.update_usd_jpy_rate",
        "schedule": crontab(hour=6, minute=0),  # JST 6:00（timezone=Asia/Tokyo が適用済み）
    },
    # 為替レート SSOT: USD/JPY を毎日 PM6:00 JST にも取得（夕方レート反映）
    "update-fx-rate-evening": {
        "task": "app.tasks.fx_rate_updater.update_usd_jpy_rate",
        "schedule": crontab(hour=18, minute=0),  # JST 18:00
    },
    # MIG-05 Task 3: TCG マスタミラーシート 日次書き出し（AM02:00 JST）
    # 書き込み先: spreadsheetId 1IBIpge6Qz2arq93OHmRFnCGBMj2kVhrgEjtY8c5ecus（固定）
    # 自動作成なし・TCG_SHEETS_SA_KEY_FILE 未設定時はスキップ
    "tcg-mirror-daily-write": {
        "task": "app.tasks.tcg_mirror.run_tcg_mirror_write",
        "schedule": crontab(hour=2, minute=30),  # JST 02:30（refresh-all-avatars の30分後）
    },
    # REVIEW-STAGE: 24h 超過の pending_review ジョブを discarded に更新（1時間ごと）
    # pending_messages（JSONB）を NULL にして監査行は残す
    "discard-stale-pending-import-jobs": {
        "task": "app.tasks.tcg_import_discard.discard_stale_pending_jobs",
        "schedule": crontab(minute=0),  # 毎時0分
    },
    # ADR-157: 外部買取店（シンソク + 買取ホムラ）の買取価格を 1日3回取得（JST 10:00/13:00/22:00）
    # public.buyback_shop_products / public.buyback_price_logs に蓄積
    "fetch-buyback-prices": {
        "task": "buyback.fetch_all_prices",
        "schedule": crontab(minute=0, hour="1,4,13"),
    },
    # 抽出ジョブの停滞回収（10分ごと）
    # design: docs/handoff/extraction-job-recovery/design.md §B
    # デプロイ時の強制コンテナ削除等で running/pending のまま取り残された
    # extraction_jobs を回収する。
    "recover-stale-extraction-jobs": {
        "task": "tcg.recover_stale_extraction_jobs",
        "schedule": 600.0,  # 10分
    },

    # ADR-1012 段階1 便5: 1 分ごとの heartbeat（見張り CeleryHeartbeatStale が読む）
    "ai-ops-celery-heartbeat": {
        "task": "app.tasks.ai_ops_heartbeat.celery_heartbeat",
        "schedule": 60.0,  # 1分
    },
    # ADR-1019 段2: 閲覧ページの在庫の作り置き（1分ごと）
    "refresh-viewer-inventory": {
        "task": "app.tasks.viewer_inventory_cache.refresh_viewer_inventory",
        "schedule": 60.0,
    },
    # ADR-1020 便4c: 共用商品の必須9項目の入れ忘れ件数と印の件数を毎週月曜 09:00 に管理者用 Discord へ
    "report-master-required-fields-weekly": {
        "task": "app.tasks.master_required_fields_monitor.report_master_required_fields",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),
    },
    # ADR-1027 便3: バルク系の値段基準不明・まとめ数未確認の件数を毎週月曜 09:05 に管理者用 Discord へ
    "report-bundle-bulk-weekly": {
        "task": "app.tasks.bundle_bulk_monitor.report_bundle_bulk",
        "schedule": crontab(hour=9, minute=5, day_of_week=1),
    },
    # ADR-1050: 解析の一時的な失敗の送り直しの件数を毎週月曜 09:10 に管理者用 Discord へ
    "report-api-error-retry-weekly": {
        "task": "app.tasks.api_error_retry_weekly.report_api_error_retry_weekly",
        "schedule": crontab(hour=9, minute=10, day_of_week=1),
    },
    # ADR-1019 段6: 閲覧者の使い回しの疑いが新しく出たら運用の Discord へ（1時間ごと・同じ知らせは30日送らない）
    "notify-viewer-share-flags-hourly": {
        "task": "app.tasks.viewer_share_flag_monitor.notify_viewer_share_flags",
        "schedule": crontab(minute=15),  # 毎時15分（interval だと deploy の再起動で計測が初めからになるため）
    },
}

# ADR-1012 段階1 便5: タスクの失敗をタスク名ごとに数える（見張り CeleryTaskFailuresHigh が読む）
from celery.signals import task_failure  # noqa: E402

from app.celery_health import record_task_failure  # noqa: E402


@task_failure.connect
def _count_task_failure(sender=None, **kwargs):
    record_task_failure(getattr(sender, "name", None) or "unknown")


# ADR-1012 段階3 便D: コンテナの健康診断が読む印を worker が 30 秒ごとに更新する
# （beat は docker-compose.yml の -S app.celery_alive:AliveScheduler で更新する）
from app.celery_alive import WorkerAliveStep  # noqa: E402

celery_app.steps["worker"].add(WorkerAliveStep)
