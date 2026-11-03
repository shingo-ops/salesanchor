# 便2 調査メモ（schedule-gcal-import）

- 調査日: 2026-11-03 / 読んだ元: origin/main（0ab7262d6）/ 設計: `docs/handoff/schedule-gcal-import/design.md` §4 便2
- パスはリポジトリ直下からの相対（`backend/app/...`）。コードは直していない。

## Q1 backend/app/services/google_webhook.py の全関数（292 行）

| 関数 | 行 | 役目 |
|---|---|---|
| `_get_webhook_address` | 44-46 | 環境変数 `API_BASE_URL` + `_WEBHOOK_PATH` で知らせの宛先 URL を作る |
| `register_webhook` | 54-119 | `events().watch` で知らせのチャンネルを登録し `google_webhook_subscriptions` に UPSERT |
| `stop_webhook` | 127-158 | `channels().stop` で止め、購読行を DELETE |
| `get_tenant_by_channel` | 166-186 | channel_id から `(tenant_id, schema名)` を返す |
| `handle_webhook_notification` | 194-259 | 知らせの受け取り。Google から読み、`upsert_from_google` を回す |
| `renew_expiring_webhooks` | 267-292 | 期限 48 時間以内の購読を `register_webhook` で登録し直す |

- 知らせの受け取り（`handle_webhook_notification`）: `backend/app/services/google_webhook.py:194`。`sync` 状態は無視（206-208）、不明 channel は warning で戻る（210-213）、`set_tenant_context`（218）。
- Google からの読み方（直近30分の方式）: `backend/app/services/google_webhook.py:229-241`
  ```
  # 直近30分の変更を取得（差分同期）
  updated_min = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
  events_result = await asyncio.to_thread(
      service.events().list(calendarId="primary", updatedMin=updated_min,
                            singleEvents=True, showDeleted=True).execute)
  ```
  ページ送り（nextPageToken）の処理は無し（`items` だけ読む。246 行）。`nextSyncToken` の保存も無し。
- `_is_app_origin`: 定義は `backend/app/services/calendar_service.py:76-94`（google_webhook.py には無い）。呼び出しは `calendar_service.py:392`。
  ```
  "SELECT 1 FROM calendar_events WHERE google_event_id = :gid"
  " AND sync_origin_id LIKE 'app:" + str(tenant_id) + ":%'" " LIMIT 1"
  ```
- 知らせの登録: `backend/app/services/google_webhook.py:75-86`（`events().watch` の body は `id`・`type="web_hook"`・`address`・`expiration`。**`token` は無し**）。保存は 95-112 の UPSERT（`ON CONFLICT (tenant_id) DO UPDATE`）。`sync_token`・`channel_token_hash` 列は未登場。
- `renew_expiring_webhooks`: `backend/app/services/google_webhook.py:267-292`。`expiration < now+48h` の `tenant_id` を `public.google_webhook_subscriptions` から取り、各 `register_webhook`。**呼び出し元（beat・タスク）は無し**（使った grep: `grep -rn "renew_expiring_webhooks" backend/app` → 定義のみ。テストは `backend/tests/test_calendar_service.py:654-`）。
- `channels.stop`: **有り**。`backend/app/services/google_webhook.py:145-149`（`stop_webhook` 内のみ）。`register_webhook` は既存チャンネルを stop せず UPSERT で上書き（docstring 58 行は「stop → 新規登録」と書くが実装に stop 呼び出しは無い。75-112 を読んだ事実）。古いチャンネルを止める処理は無し。

## Q2 backend/app/services/calendar_service.py `upsert_from_google`（376-463）

- 定義: `backend/app/services/calendar_service.py:376`。全文は 376-463（要点を行付きで抜粋）。
  - 387 付近: `google_event_id = google_event.get("id")`、無ければ return
  - 392 付近: `if await _is_app_origin(db, google_event_id, tenant_id): return`
  - 397-404: `status == "cancelled"` → `DELETE FROM calendar_events WHERE google_event_id = :gid` → commit
  - 410-420: `is_all_day = "date" in start`、`start_dt = start.get("dateTime") or start.get("date")`（**文字列のまま渡す**。datetime 化・日本時間化は無し）、start/end 欠けは warning で return
  - 421: `origin_id = f"google:{tenant_id}:{google_event_id}"`
  - 423-457 INSERT（`ON CONFLICT` は 435）:
    ```
    " ('shared', :title, :desc, :loc, :start, :end, :all_day,"
    "  :gid, :gcal_id, 'google', 'synced', :origin, NOW())"
    " ON CONFLICT (google_event_id) DO UPDATE SET title=..., description=..., location=...,"
    "   start_datetime=..., end_datetime=..., is_all_day=..., sync_status='synced', last_synced_at=NOW()"
    " WHERE calendar_events.google_event_id = :gid"
    ```
    `gcal_id` は固定 `"primary"`（454）。
  - 458: `await db.commit()`（commit 後の `reset_tenant_context` は呼んでいない）
- 設計との差: `calendar_type` は `'shared'` 固定（設計は `personal`）、`user_id`・`created_by_user_id` は入れていない、`ON CONFLICT (google_event_id)` は部分索引と一致しない（Q7 参照、一意索引自体が現状無い）。

## Q3 Google API の呼び方

- 使うもの: googleapiclient（httpx ではない）。`backend/app/services/google_calendar.py:304` `from googleapiclient.discovery import build`、330 `service = build("calendar", "v3", credentials=creds, cache_discovery=False)`。同期呼び出しは `asyncio.to_thread(...execute)` で包む（例 `google_webhook.py:234`）。
- 資格情報の取り方: `backend/app/services/google_calendar.py:303-331` `_get_service(db, tenant_id)`。`tenant_google_calendar_config` から `access_token_encrypted, refresh_token_encrypted, token_expiry` を SELECT（309-314）→ `_refresh_if_needed`（320）→ `encryption.decrypt`（327）→ `_build_credentials`（329）。接続なしは `RuntimeError("Google Calendar が接続されていません")`（317）。
- 更新: `backend/app/services/google_calendar.py:252-300` `_refresh_if_needed`。期限切れなら `creds.refresh(Request())`（`asyncio.to_thread`、270）→ `UPDATE tenant_google_calendar_config SET access_token_encrypted, token_expiry`（279-294）→ `commit` と `reset_tenant_context`（295-296）。
- `_build_credentials`: `backend/app/services/google_calendar.py:226-238`（`google.oauth2.credentials.Credentials`、`token_uri="https://oauth2.googleapis.com/token"`）。
- events.list を呼ぶ関数が2つ:
  - `backend/app/services/google_calendar.py:348-374` `get_events`（`timeMin`/`timeMax`/`singleEvents=True`/`orderBy="startTime"`/`maxResults=500`。`calendarId` は `get_calendar_id`＝設定の `calendar_id` 既定 `primary`、334-345）。ページ送りは無し。
  - `backend/app/services/google_webhook.py:234-241`（Q1）。
- 書き込み側（触らない）: `create_event` 377、`update_event` 392、`delete_event` 407（google_calendar.py）。

## Q4 知らせの受け口・方式の口

- 受け口: `backend/app/routers/google_calendar.py:386-391`
  ```
  @public_router.post("/google-calendar/webhook", tags=["google-calendar"], include_in_schema=False)
  async def receive_webhook(request: Request, db: AsyncSession = Depends(get_db)):
  ```
  `public_router` は 44 行（認証なし）。`backend/app/main.py:672` `app.include_router(google_calendar.public_router, prefix="/api/v1", ...)`。実 URL は `/api/v1/google-calendar/webhook`（`google_webhook.py:37`）。
  本体 391-418: `X-Goog-Channel-ID`・`X-Goog-Resource-State` を読む（401-402）。**`X-Goog-Channel-Token` は読んでいない**。channel_id 無しは 200 を返す。`handle_webhook_notification` を同期的に await（411）。例外は握って常に 200。**Celery に積む処理は無し**。
- `_ACCEPTED_SYNC_MODES` の使用箇所（`grep -rn "_ACCEPTED_SYNC_MODES" backend`）:
  - `backend/app/routers/calendar.py:44` 定義 `_ACCEPTED_SYNC_MODES = ("write_only", "none")`（43 行に ADR-1057 のコメント）
  - `backend/app/routers/calendar.py:504` `if body.sync_mode not in _ACCEPTED_SYNC_MODES:` → 422「Google の予定をアプリへ取り込む設定は使えません（ADR-1057）」
  - 使用はこの2箇所のみ（定義 + 判定）。`_VALID_SYNC_MODES`（42）は別。
- 方式を変えたとき登録する処理: `backend/app/routers/calendar.py:490-530` `PATCH /calendar/sync-mode` の `update_sync_mode`（490 デコレータ、491 定義）。UPDATE → `reset_tenant_context` → 523-527 付近（登録 525・停止 527）:
  ```
  if body.sync_mode in ("bidirectional", "read_only"):
      await webhook_svc.register_webhook(db, tenant_id)
  else:
      await webhook_svc.stop_webhook(db, tenant_id)
  ```
- 既存の試験: `backend/tests/test_calendar_owner_api.py:126`（取り込み方式が 422 になること）。ここは便2で書き換わる。
- 接続し直し・切断の口で webhook を扱うか: `grep -rn "register_webhook\|stop_webhook" backend/app` で上記以外の呼び出しを確認していない（未確認。便2実装役が確かめる）。

## Q5 知らせの宛先 URL・合言葉に関わる設定（環境変数名のみ）

- `API_BASE_URL`（`backend/app/services/google_webhook.py:45` の `os.getenv("API_BASE_URL", "https://api.salesanchor.jp")`。docstring 19 行）。
- Google の資格情報側: `GOOGLE_CALENDAR_CLIENT_ID`・`GOOGLE_CALENDAR_CLIENT_SECRET`・`GOOGLE_CALENDAR_REDIRECT_URI`（`backend/app/services/google_calendar.py:52, 59, 66`）。
- 合言葉（channel token）用の設定: **無し**（使った grep: `grep -rn "Channel-Token\|channel_token\|CHANNEL_TOKEN" backend/app` → 0 件。設計は登録時に乱数で作り sha256 だけ保存する案なので環境変数は不要の見込み）。

## Q6 Celery

- beat の書き方: `backend/app/celery_app.py:67` `celery_app.conf.beat_schedule = {` の辞書。タスクの置き場は 21-48 の `include=[...]` に module 名を足す。既存の1件の例（`backend/app/celery_app.py:208-211`）:
  ```
  "ai-ops-celery-heartbeat": {
      "task": "app.tasks.ai_ops_heartbeat.celery_heartbeat",
      "schedule": 60.0,  # 1分
  },
  ```
  他に `crontab(...)`（72 行）の例あり。タイムゾーンは `Asia/Tokyo`（55）。
- 会社ごとに `public.tenants` を回す既存の定期作業:
  - 非同期版: `backend/app/tasks/sa02_recon_monitor.py:48-86` `_run_daily_recon`。`async with AsyncSessionLocal() as db`（58）→ `SELECT id FROM public.tenants WHERE is_active = true ORDER BY id`（61 付近）→ ループ内で `await set_tenant_context(db, tenant_id)`（70）→ `finally: await clear_tenant_context(db)`（90）。`clear_tenant_context` の定義は `backend/app/auth/dependencies.py:437`。**`reset_tenant_context` を使うタスクは無し**（使った grep: `grep -rn "reset_tenant_context" backend/app/tasks` → 0 件）。`reset_tenant_context` は commit 後に張り直す関数（`backend/app/auth/dependencies.py:415`）。`set_tenant_context` は 353。
  - 同期版: `backend/app/tasks/avatar.py:98-103` `_select_tenant_ids`（`SELECT id FROM tenants WHERE is_active = true`）、`258-` `refresh_all_avatars`、ループ内 `set_tenant_context_sync(session, tenant_id)`（301、定義 `dependencies.py:378`）。
  - 非同期を Celery から呼ぶ型: `backend/app/tasks/viewer_share_flag_monitor.py:89-95` `@shared_task(name=...)` の同期関数が `asyncio.run(_run_report())`、`finally: asyncio.run(engine.dispose())`。
- Celery の失敗の見張り: `backend/app/celery_app.py:239-247`（`task_failure` シグナルで `record_task_failure(task名)`）→ `backend/app/celery_health.py:56`（Redis キー `ai_ops:celery:task_failures`、23 行）→ Prometheus アラート `CeleryTaskFailuresHigh`（`monitoring/prometheus/alert_rules.yml:195-196`、同じタスクが1時間に3回以上）。手順書 `docs/runbooks/alerts.md`。
- 未登録の点検: `backend/tests/test_celery_beat_registered.py:14-25` `test_every_beat_task_is_registered`（`include` の module を import し、beat_schedule の `task` 名が `celery_app.tasks` に有ることを確かめる）。新タスクは `include` に module を足さないとここで落ちる。
- ほか: heartbeat の見張り `backend/app/celery_app.py:207-211` と `backend/tests/test_celery_health.py:104`。

## Q7 migrations

- 最新10件（`ls migrations | tail -10`）。名前は `YYYYMMDD_HHMMSS_<英語の小文字_snake>.sql`:
  ```
  20261024_100000_create_ai_cloud_meta.sql
  20261024_100100_create_ai_reader_cloud_role.sql
  20261024_100200_drop_ai_cloud_views.sql
  20261024_100300_create_ai_cloud_views.sql
  20261031_200000_add_passkey_enroll_prompt_skips.sql
  20261031_210000_create_ops_case.sql
  20261101_120000_enable_secretary_chat_tenant4.sql
  20261101_130000_add_new_device_approval.sql
  20261102_090000_add_user_push_subscriptions.sql
  20261103_120000_create_ai_job_assignments.sql
  ```
  （全 413 件。古いものは `078_...` のように連番）。流れる順は `scripts/run_all_migrations.sh`（例 `:377` に `run_sql migrations/078_create_calendar_events_tenant.sql`）。新ファイルがそこに書き足しを要するかは未確認（最新の `2026*` 件が `run_all_migrations.sh` に列挙されているかを便2実装役が確かめる）。
- 全テナントの表に索引を足す既存例（DO ブロックで `tenant_NNN` を回す）:
  - `migrations/078_create_calendar_events_tenant.sql:23-33`（`DO $calendar_events_create$` … `FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$'`）、索引は `EXECUTE format('CREATE INDEX IF NOT EXISTS idx_calendar_events_google_id ON %I.calendar_events (google_event_id) WHERE google_event_id IS NOT NULL', schema_rec.nspname)`（77-81）。**既存はこの通常（非一意）の部分索引だけ**。一意索引は無し（使った grep: `grep -n "UNIQUE" migrations/078_create_calendar_events_tenant.sql` → 0 件）。
  - `migrations/20261015_090000_add_leads_assignment_opened_at.sql:39-50`（`DO $$` + `pg_namespace` ループ + `information_schema` で守る。再実行の安全性の説明が 9-20 行）。
  - `migrations/20260927_100000_create_meta_message_reactions.sql:70`（`CREATE INDEX IF NOT EXISTS idx_mmr_tenant ON %I.meta_message_reactions (tenant_id)`）。
  - `migrations/20260621_020000_add_schedule_calendar_category_and_owner_settings.sql:28`（`IF to_regclass(format('%I.calendar_events', ...)) IS NULL THEN CONTINUE`）で表が無いテナントを飛ばす型。
  - 毎デプロイ全件再実行される（ADR-1005 / 上の 20261015 ファイル 9-12 行）ので `IF NOT EXISTS` 必須。
- 新しいテナントの表を作る仕組み: `backend/app/services/tenant.py:1635` `create_tenant_schema`、DDL は `_TENANT_TABLES_SQL`（`get_tenant_tables_sql` は 1805）。**`calendar_events` は `tenant.py` に出てこない**（使った grep: `grep -n "calendar" backend/app/services/tenant.py` → 0 件）。つまり新テナントの `calendar_events` は `tenant.py` ではなく migration 078 を `run_all_migrations.sh` が既存の全 `tenant_*` に流すことで出来る。便2で足す索引は migration 側の DO ブロックで全 `tenant_*` に付く（`tenant.py` への追記が要る場所は見つからず）。`calendar_events` 自体の RLS 設定は見つからず（使った grep: `grep -rn "calendar_events" migrations | grep -i "POLICY\|ROW LEVEL"` → 0 件）。
- lock_timeout の決まり（ADR-1037）: `docs/adr/ADR-1037-migration-lock-timeout.md:12-` What 1「`scripts/run_all_migrations.sh` の run_sql で流す SQL は、接続ごとに `lock_timeout=1s` を付けて流す（`docker exec -e PGOPTIONS`）」2「deadlock / lock timeout で落ちたら3秒あけて流し直す（合計40回）」。値の正本は同スクリプトの `SQL_LOCK_TIMEOUT` ほか4行。ファイル内で書く例:
  - `migrations/20261031_210000_create_ops_case.sql:231` `SET lock_timeout = '2s'`（関数定義の属性）
  - `migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql:9` `SET LOCAL lock_timeout = '5s';`（ADR-1037 は「対象外」としている 8 ファイルの型）
  - 一意索引を作る migration に `SET LOCAL lock_timeout` を書いた既存例は未確認。

## Q8 3つの表の列

- `public.google_webhook_subscriptions`（`migrations/077_calendar_sync_mode_and_webhook_subscriptions.sql:25-33`）:
  ```
  id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
  channel_id VARCHAR(255) NOT NULL, resource_id VARCHAR(255),
  calendar_id VARCHAR(255) NOT NULL DEFAULT 'primary',
  expiration TIMESTAMP WITH TIME ZONE NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
  ```
  索引: `idx_..._expiration`（36-37）、`UNIQUE idx_..._channel_id`（40-41）。`sync_token`・`channel_token_hash` 列は無し（使った grep: `grep -rn "sync_token\|channel_token_hash" migrations backend/app` → 0 件）。RLS は無し（設計の本番読み取りと同じ。migrations 内に `google_webhook_subscriptions` の RLS 文は無し。`grep` で `20261024_100300_create_ai_cloud_views.sql:98` の AI 用ビューの記載のみ）。
- `public.tenant_google_calendar_config`: 作成 `migrations/076_add_google_calendar_config.sql:14-24`
  ```
  id SERIAL PK, tenant_id INTEGER NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
  access_token_encrypted TEXT NOT NULL, refresh_token_encrypted TEXT NOT NULL,
  token_expiry TIMESTAMPTZ, calendar_id TEXT NOT NULL DEFAULT 'primary',
  connected_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  connected_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
  ```
  追加列 `sync_mode VARCHAR(20) NOT NULL DEFAULT 'bidirectional'` + CHECK（`077...sql:19-22`、値は bidirectional/read_only/write_only/none）。ほかの ALTER は無し（`grep -rn "ALTER TABLE.*tenant_google_calendar_config" migrations` は 077 と RLS の 2 件のみ）。RLS 強制: `migrations/20261016_010000_add_google_config_rls.sql:2-9`（`ENABLE`・`FORCE`、ポリシーは `tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER`）。
- `{tenant}.calendar_events`（`migrations/078_create_calendar_events_tenant.sql:44-66`）:
  ```
  id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
  calendar_type VARCHAR(10) NOT NULL DEFAULT 'shared' CHECK (IN ('shared','personal')),
  title VARCHAR(500) NOT NULL, description TEXT, location TEXT,
  start_datetime TIMESTAMPTZ NOT NULL, end_datetime TIMESTAMPTZ NOT NULL,
  is_all_day BOOLEAN NOT NULL DEFAULT FALSE, google_event_id VARCHAR(255), google_calendar_id VARCHAR(255),
  source VARCHAR(10) NOT NULL DEFAULT 'app' CHECK (IN ('app','google')),
  sync_status VARCHAR(10) DEFAULT 'synced' CHECK (IN ('synced','pending','failed')),
  sync_origin_id VARCHAR(500), last_synced_at TIMESTAMPTZ,
  created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
  created_at/updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  ```
  追加列 `category VARCHAR(50) NOT NULL DEFAULT 'meeting'`（`migrations/20260621_020000_add_schedule_calendar_category_and_owner_settings.sql:33-34`）。索引 078 の 71-93: `idx_calendar_events_range`、`idx_calendar_events_google_id`（部分・非一意）、`idx_calendar_events_sync_origin`、`idx_calendar_events_user_type`。

## Q9 既存の試験

- `backend/tests/test_calendar_service.py`（calendar_service + google_webhook の単体、DB はモック）:
  - `TestIsAppOrigin`（157）: アプリ起源の判定が真/偽になる
  - `TestUpsertFromGoogle`（432）: id 無し→何もしない(434)、cancelled→DELETE(441)、アプリ起源→スキップ(455)、通常→upsert(471)、start/end 不正→スキップ(491)、終日→upsert(512)
  - `TestGetWebhookAddress`（537）: `API_BASE_URL` の既定・上書き・末尾スラッシュ除去
  - `TestGetTenantByChannel`（558）: 見つからない→None、見つかる→(tenant, schema)
  - `TestHandleWebhookNotification`（577）: sync 状態は無視(579)、不明 channel は早期 return(587)
  - `TestRegisterWebhook`（596）: Google 未接続でスキップ(598)、watch 失敗でスキップ(608)
  - `TestStopWebhook`（622）: 購読が無ければ戻る(624)、停止して行を消す(633)
  - `TestRenewExpiringWebhooks`（654）: 期限切れ 0 件→0(656)、期限切れ→登録し直す(664)
  - `TestHandleWebhookNotificationExists`（686）: exists 状態で Google 未接続の扱い
- `backend/tests/test_calendar_owner_api.py`: `update_sync_mode` が取り込み方式（bidirectional/read_only）を 422 にする(126)、write_only は stop_webhook を呼ぶ(142)、none(158) ほか予定の持ち主・個人予定の 404(183, 196)・calendar_type 変更(208-236)。
- `backend/tests/test_event_loop_nonblocking.py:112`: `handle_webhook_notification` が遅い events.list の間もイベントループを止めない（`asyncio.to_thread` の確認）。
- `backend/tests/test_tenant_admin_ssot.py:185`: `PATCH /api/v1/calendar/sync-mode` が管理者専用のルートであること。`TestCalendarEventOwnership`(97): 予定の更新・削除の権限。
- `backend/tests/test_google_calendar.py`: OAuth の state 発行/消費(81-117)、認可 URL(146, 163)、トークン期限判定(41-55)。events.list の試験は無し。
- `backend/tests/test_google_config_rls.py`: 接続設定 2 表の会社別 RLS（実 PostgreSQL、`tests.rls_bootstrap` を使う）。
- `backend/tests/test_celery_beat_registered.py:14` / `test_celery.py:31` / `test_celery_health.py:104`: beat の登録、`include` の module、heartbeat の登録。
- 見つからなかった試験: 同期の「sync_token / 410 全部読み直し」「channel token の照合」「`google_webhook_subscriptions` の実 DB 試験」（使った grep: `grep -rln "sync_token\|Channel-Token" backend/tests` → 0 件）。

## 見つからなかった項目（まとめ）

1. `renew_expiring_webhooks` を呼ぶ beat・タスク（定義と試験のみ）
2. `sync_token` / `channel_token_hash` 列、`X-Goog-Channel-Token` の読み取り、合言葉用の環境変数
3. `calendar_events.google_event_id` の一意索引（非一意の部分索引のみ）
4. `reset_tenant_context` を使う既存の Celery タスク（`clear_tenant_context` 型の `sa02_recon_monitor.py` はある）
5. `tenant.py` の `_TENANT_TABLES_SQL` に `calendar_events` が無い（新テナント用に索引を足す場所は migration 側のみ）
6. 一意索引の migration で `lock_timeout` を書いた既存例
7. 接続・切断の口から `register_webhook`/`stop_webhook` を呼ぶ箇所の有無（未確認）、`run_all_migrations.sh` への新ファイル登録の要否（未確認）
8. `events.list` のページ送り・`nextSyncToken` の既存処理
