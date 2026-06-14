# recon: review@salesanchor.jp 新着メール → Discord通知

## ADR 検索結果

- `git grep -i "imap\|mail.monitor\|review_mail" docs/adr/` → 0件（既存設計なし）
- `docs/adr/FEATURE-INDEX.md` 参照 → メール監視・IMAP に該当エントリなし
- 既存 ADR 該当なし（grep 済み）

## ファイル確認（file:line）

### 1. STANDARD-WORKFLOW.md

- `docs/STANDARD-WORKFLOW.md:24` — Phase 2 recon: file:line 引用が必須
- `docs/STANDARD-WORKFLOW.md:19` — 3フェーズ: KGI設定→recon→設計

### 2. Celery 定義

- `backend/app/celery_app.py:21-33` — `include=["app.tasks.dashboard", ...]` にモジュール列挙
- `backend/app/celery_app.py:52` — `celery_app.conf.beat_schedule = {` で定期タスク登録
- `backend/app/celery_app.py:108-111` — `translate-pending-messages` エントリ（300.0 秒間隔の例）
- `backend/app/celery_app.py:14` — `CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")`

### 3. Discord通知サービス

- `backend/app/services/discord_notifier.py:40-41` — `_get_webhook_url()` → `ADMIN_NOTIFICATION_DISCORD_WEBHOOK` を読む
- `backend/app/services/discord_notifier.py:45-65` — `_post_discord_webhook()` は private async。本タスクは sync パスで実装（imaplib が sync のため）
- `backend/app/services/discord_notifier.py:1-23` — モジュールコメント: webhook 未設定 → no-op、POST 失敗 → ログのみ

### 4. .env.example

- `.env.example:100` — `ADMIN_NOTIFICATION_DISCORD_WEBHOOK=` 既存エントリあり → 新 Secret 不要
- `.env.example:34-39` — Redis / Celery の設定例（REDIS_URL, CELERY_BROKER_URL等）

### 5. docker-compose.yml

- `docker-compose.yml:94` — backend サービス: `ADMIN_NOTIFICATION_DISCORD_WEBHOOK=${ADMIN_NOTIFICATION_DISCORD_WEBHOOK:-}` 渡し済み
- `docker-compose.yml:177-212` — **celery-worker サービス**: `ADMIN_NOTIFICATION_DISCORD_WEBHOOK` が **未渡し**（ギャップ）
- `docker-compose.yml:184` — celery-worker は `REDIS_URL` を受け取っている
- `docker-compose.yml:214-242` — celery-beat: スケジューラーのみ、実行は celery-worker

### 6. deploy.yml

- `.github/workflows/deploy.yml:227` — `sed -i ... -e '/^ADMIN_NOTIFICATION_DISCORD_WEBHOOK=/d'`
- `.github/workflows/deploy.yml:252` — `ADMIN_NOTIFICATION_DISCORD_WEBHOOK=${{ secrets.ADMIN_NOTIFICATION_DISCORD_WEBHOOK }}` を .env に append
- → **deploy.yml 変更不要**（既存 Secret を再利用）

### 7. 既存タスクパターン（参照実装）

- `backend/app/tasks/translation.py:23-40` — `@celery_app.task(name="...", bind=True)` → `asyncio.run()` ラッパーパターン
- `backend/app/tasks/dashboard.py:45-47` — sync Redis クライアント: `redis.from_url(REDIS_URL, decode_responses=True)`
- `backend/app/tasks/sa02_recon_monitor.py:28-39` — Discord POST: `httpx.AsyncClient().post()` パターン

## ギャップ・不明点

| 項目 | 内容 | 対応 |
|------|------|------|
| celery-worker 環境変数 | `ADMIN_NOTIFICATION_DISCORD_WEBHOOK` が celery-worker に未渡し | `docker-compose.yml` に追加（Secret 追加不要・既存値を貫通させる） |
| IMAP 認証情報 | `REVIEW_MAIL_IMAP_PASSWORD` は GitHub Secret 管理か VPS 手動か | **PO が VPS .env に手動設定**（新 Secret 追加・deploy.yml 変更なし） |
| 既存 ADR | メール監視の ADR なし | 新規 ADR 不要（既存 Celery/Discord パターンを踏襲） |

## 不変条件確認

- migration 不要: Redis で通知済み管理（DB 変更なし）
- deploy.yml 変更不要: 既存 ADMIN_NOTIFICATION_DISCORD_WEBHOOK を再利用
- 新 GitHub Secret 不要: 上記と同理由
- IMAP 認証情報: VPS .env に手動追加（危険変更ではなく PO 作業）
