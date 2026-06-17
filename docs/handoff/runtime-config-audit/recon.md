# runtime-config-audit recon

**日付**: 2026-06-17  
**担当**: Terminal CC（読み取り専用）  
**手法**: docker-compose.yml 静的解析 + VPS 実機 `docker inspect` による runtime env 確認

---

## §1 調査範囲

app コンテナ 4 本の env を比較し、「gateway コードが必要とする変数が gateway に無い」ケースを file:line で特定する。

- `backend` (FastAPI)
- `celery-worker` (Celery worker)
- `compose-beat` (Celery beat)
- `discord-gateway` (Discord Bot WebSocket)

---

## §2 各コンテナの実 runtime 環境変数（本番 VPS 2026-06-17 実機確認）

> 値はマスク。変数名のみ記載。取得コマンド: `docker inspect <container> --format '{{json .Config.Env}}'`

### backend (astro-webapp-backend-1)

| 変数名 | 用途 |
|--------|------|
| `DATABASE_URL` | メイン DB 接続 |
| `ADMIN_DATABASE_URL` | DDL/クロステナント専用 DB（未設定時 DATABASE_URL にフォールバック）|
| `REDIS_URL` | Redis 接続（パスワード込み形式）|
| `CELERY_BROKER_URL` | Celery ブローカー |
| `CELERY_RESULT_BACKEND` | Celery 結果バックエンド |
| `ENVIRONMENT` | `production` |
| `ALLOWED_ORIGINS` | CORS |
| `GCP_PROJECT_ID` | Firebase/GCP |
| `GOOGLE_APPLICATION_CREDENTIALS` | Firebase 認証 JSON パス |
| `GEMINI_API_KEY` | LLM（翻訳・在庫解析）|
| `ADMIN_NOTIFICATION_DISCORD_WEBHOOK` | 予算超過通知 Webhook |
| `DISCORD_BOT_TOKEN_4` | KPI 4〜7 用 Bot Token（backend → REST API 直接呼出し）|
| `META_VERIFY_TOKEN` | Meta Webhook 検証 |
| `META_APP_SECRET` | Meta App Secret |
| `META_APP_ID` | Meta App ID |
| `META_OAUTH_REDIRECT_URI` | Meta OAuth コールバック URL |
| `META_GRAPH_API_VERSION` | Graph API バージョン |
| `META_PAGE_ID` | Fallback tenant 紐付け |
| `META_PAGE_ACCESS_TOKEN` | Meta ページアクセストークン |
| `METADATA_FERNET_KEY` | tokens/secrets 暗号化キー |
| `ENFORCE_METADATA_FERNET_KEY` | Fernet 強制フラグ |
| `FRONTEND_BASE_URL` | メール内リンク生成 |
| `MFA_REQUIRED` | MFA 強制フラグ（`false`）|
| `SMOKE_SERVICE_TOKEN` | CI スモーク用バイパストークン |
| `SMOKE_SERVICE_EMAIL` | CI スモーク用サービスアカウント email |
| `GOOGLE_DRIVE_CLIENT_ID` | Google Drive OAuth |
| `GOOGLE_DRIVE_CLIENT_SECRET` | Google Drive OAuth |
| `GOOGLE_DRIVE_REDIRECT_URI` | Google Drive OAuth コールバック |
| `GOOGLE_DRIVE_SA_JSON_B64` | Drive サービスアカウント JSON (Base64) |
| `GOOGLE_CALENDAR_CLIENT_ID/SECRET/REDIRECT_URI` | Google Calendar OAuth |

### celery-worker (astro-webapp-celery-worker-1)

| 変数名 | 備考 |
|--------|------|
| `DATABASE_URL` | ✅ |
| `REDIS_URL` | ✅ |
| `CELERY_BROKER_URL` | ✅ |
| `CELERY_RESULT_BACKEND` | ✅ |
| `ENVIRONMENT` | ✅ |
| `GCP_PROJECT_ID` | ✅ |
| `GOOGLE_APPLICATION_CREDENTIALS` | ✅ |
| `REVIEW_MAIL_*`（IMAP_HOST/USER/PASSWORD/PORT + WEBHOOK/MENTION/WEBMAIL_URL）| `.env` 直接引き継ぎ |
| ~~GEMINI_API_KEY~~ | **❌ 欠落**（後述 §4 サイレント失敗）|

### celery-beat (astro-webapp-celery-beat-1)

| 変数名 | 備考 |
|--------|------|
| `DATABASE_URL` | ✅ |
| `REDIS_URL` | ✅ |
| `CELERY_BROKER_URL` | ✅ |
| `CELERY_RESULT_BACKEND` | ✅ |

`celery-beat` は定期タスクのスケジュール送信のみ。実行はすべて celery-worker 側。欠落なし。

### discord-gateway (astro-webapp-discord-gateway-1)

| 変数名 | 備考 |
|--------|------|
| `ENVIRONMENT` | ✅ |
| `DISCORD_GATEWAY_LOG_LEVEL` | ✅ |
| `DISCORD_BOT_TOKEN_4` | ✅ |
| `DISCORD_TENANT_CODE_4` | ✅ |
| ~~DATABASE_URL~~ | **❌ 欠落（CRITICAL）** |

---

## §3 gateway コードが必要とする変数 × gateway の欠落（差分分析）

### 判定基準

「**欠落+必要**」= gateway コードのモジュール import チェーンから到達でき、かつ欠落時に crash / データ損失を起こすもの。

| 変数名 | gateway コードの参照 | 欠落時の挙動 | 判定 |
|--------|---------------------|-------------|------|
| `DATABASE_URL` | `backend/app/database.py:8` — `os.getenv("DATABASE_URL", "postgresql+asyncpg://myapp_user:password@postgres:5432/myapp_db")` | fallback の `myapp_user` で auth 失敗。**全 DB ops クラッシュ**（`asyncpg.InvalidPasswordError` 確認済み）| **CRITICAL・欠落** |
| `REDIS_URL` | `backend/app/cache.py:11` — `os.getenv("REDIS_URL", "redis://redis:6379/0")` | `init_redis()` は `discord_gateway/main.py` では呼ばれない → `_redis = None` のまま → cache 関数すべて graceful no-op | **欠落・影響なし** |
| `GEMINI_API_KEY` | `backend/app/services/inventory_parser_llm.py:207` — lazy import（実行時のみ）| LLM 解析が `rule_only` に降格。crash なし。**ただし DATABASE_URL が先に壊れているため現状到達しない** | **欠落・降格のみ** |
| `ADMIN_NOTIFICATION_DISCORD_WEBHOOK` | `backend/app/services/discord_notifier.py:41` — lazy call | 未設定時は log warning を出して skip。crash なし | **欠落・影響なし** |
| `MFA_REQUIRED` / `SMOKE_SERVICE_*` / `GOOGLE_APPLICATION_CREDENTIALS` | `backend/app/auth/dependencies.py` — HTTP 認証フローのみ | gateway は HTTP エンドポイントを公開しない → これらは呼ばれない | **不要** |

### 結論: **「欠落+必要」は `DATABASE_URL` のみ**

---

## §4 他のサイレント失敗（ログ・実データ確認）

### celery-worker: GEMINI_API_KEY 未設定（翻訳タスク失敗）

- **証拠ログ**（2026-06-17 14:05:37 UTC）:
  ```
  WARNING ForkPoolWorker-2] [translation_task] non-fatal error message_id=...: GEMINI_API_KEY が未設定です。翻訳機能は無効化されます。
  INFO ForkPoolWorker-2] [translation_task] batch done: processed=0 skipped=0 failed=3
  ```
- **根本原因**: `docker-compose.yml` の `celery-worker` 定義に `GEMINI_API_KEY` が記載されていない（`backend` には記載あり）。
  - `docker-compose.yml:182-188` — celery-worker environment セクションに `GEMINI_API_KEY` なし
  - `docker-compose.yml:93` — `backend` には `- GEMINI_API_KEY=${GEMINI_API_KEY:-}` あり
- **影響**: `translate_pending_messages` タスクが翻訳を実行できずスキップ。Meta 受信メッセージの自動翻訳が無効。
- **severity**: HIGH（機能停止、ただし crash なし・DB 整合は維持）
- **修正**: `celery-worker` environment に `- GEMINI_API_KEY=${GEMINI_API_KEY:-}` を追加（**本 PR 外・別変更として分離**）

### Meta 受信: 直近 24h ゼロ

- **証拠**: `SELECT COUNT(*), MAX(created_at) FROM tenant_004.meta_messages WHERE platform='meta' AND created_at > NOW() - INTERVAL '24 hours'` → `0 / NULL`
- **全件**: `SELECT COUNT(*), MAX(created_at) FROM tenant_004.meta_messages` → `5 / 2026-06-10 04:42:20`（最終: 7日前）
- **判定**: **不明**。「実際に Meta DM が来ていない」か「webhook が届いていない」か区別できない。backend は 200 正常応答中（5xx なし）。Meta App Review 申請待ち期間中のため、実ユーザーからのメッセージが少ない可能性あり。
- **推奨**: Meta Webhook ダッシュボードでイベント配信ログを確認（PO 操作が必要）

### backend 5xx: なし

- **証拠**: `docker logs astro-webapp-backend-1 --since 1h` で 5xx ゼロ。401 が複数（Grafana からの未認証アクセス、正常）。

### Celery ヘルス

- **証拠**: `docker compose ps` で celery-worker/beat とも `Up 9 hours`。直近タスクは succeeded で終了している。

---

## §5 ギャップ（既知未実装）

| # | 項目 | 現状 | ADR 参照 |
|---|------|------|---------|
| G-1 | `bots.guild_count` / `bots.last_resume_failed_at` 拡張列 | コード・migration なし | ADR-009 M5 未着手 |
| G-2 | テナント越境拒否ロジック（`discord_user_id → tenant_id` 逆引き）| 明示的チェックなし | ADR-009 M5 未着手 |
| G-3 | Prometheus metrics（接続 gauge / heartbeat latency / reconnect counter）| コードなし | ADR-009 M6 未着手 |
| G-4 | Grafana Discord Gateway 専用パネル | JSON なし | ADR-009 M6 未着手 |
| G-5 | Gateway 切断 → Discord 直接通知（on_disconnect 内） | log のみ | ADR-009 M6 未着手 |
| G-6 | `on_resumed` 補完の対象範囲（3 guild 全チャンネル） | routing 未登録チャンネルも history fetch → Discord REST 過負荷リスク | ADR-009 将来改善候補 |

---

## §6 まとめ

| 優先度 | 項目 | 対象コンテナ | 修正の難易度 |
|--------|------|-------------|-------------|
| **CRITICAL** | `DATABASE_URL` 欠落 → 全 DB ops 失敗 | discord-gateway | docker-compose.yml 1 行追加 |
| **HIGH** | `GEMINI_API_KEY` 欠落 → 翻訳タスク全滅 | celery-worker | docker-compose.yml 1 行追加（別 PR）|
| **不明** | Meta 受信ゼロ（7 日間） | — | PO が Meta Webhook ダッシュボード確認必要 |
| **ギャップ** | ADR-009 M5/M6 未実装（`bots` 拡張・metrics）| discord-gateway | 別 ADR 起案後に実装 |
