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
        "app.tasks.fx_rate_updater",     # 為替レート SSOT: USD/JPY を1日2回更新
        "app.tasks.tcg_mirror",          # MIG-05 Task 3: TCG マスタミラーシート 日次書き出し
        "app.tasks.tcg_extraction",      # MIG-04 Stage 2: Gemini 抽出タスク
        "app.tasks.tcg_import_discard",  # REVIEW-STAGE: 期限切れ保留ジョブの破棄
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
    # ADR-110: 未翻訳受信メッセージのバッチ翻訳（15分ごと）
    "translate-pending-messages": {
        "task": "app.tasks.translation.translate_pending_messages",
        "schedule": 900.0,  # 15分
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
    # 為替レート SSOT: USD/JPY を毎日 AM6:00 JST に取得して public.app_fx_rates に UPSERT
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
}
