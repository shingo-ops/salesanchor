# recon — Google カレンダー → アプリの取り込みに関わる既存の全部

基準: origin/main d61da2805（2026-11-03 fetch 後）。コードは変えていない。本番 DB は見ていない（本番の件数は schedule-gcal-connect の recon の記述を引用するだけで、今回は再確認していない＝未確認）。
行番号は origin/main 時点。パスはリポジトリ直下から。

## 0. 結論の要約（事実のみ）
- 取り込みの部品（受口・差分取得・upsert・期限更新の関数）は全部コードにある。ただし**入口は 1 つだけ**で、ADR-1057 の決定で塞がれている（§2）。
- 期限更新 `renew_expiring_webhooks` は**試験以外から呼ぶ所が無い**（§5）。Celery の定期作業にも登録が無い（§4）。
- `upsert_from_google` の `ON CONFLICT (google_event_id)` に対応する UNIQUE 制約・UNIQUE インデックスは、migrations 内に見つからない（§6）。
- `GET /calendar/events` は type 無しだと全件を返し、誰の予定が見えるかの絞りは画面側だけ（§7）。取り込んだ予定は `calendar_type='shared'` で入る。

## 1. webhook 受口
- `backend/app/routers/google_calendar.py:386-416` `POST /google-calendar/webhook`（public_router・Bearer なし）。ヘッダー `X-Goog-Channel-ID`（:401）・`X-Goog-Resource-State`（:402）だけを読む。channel_id が空なら 200 で無視（:404-406）。`handle_webhook_notification` を呼び、例外は握りつぶして常に 200（:410-416）。
- 登録: `backend/app/main.py:672`（public_router を /api/v1 に認証なしで登録）。
- 受口の認証・検証: Google からの通知の真正性を確かめる処理（X-Goog-Channel-Token の照合など）は `backend/app/services/google_webhook.py` / `backend/app/routers/google_calendar.py` に**見当たらない**（`register_webhook` の body に token を入れていない: `backend/app/services/google_webhook.py:77-86`）。channel_id を知っていれば誰でも POST できる構造。
- 閲覧者トークン拒否の許可リストに入っている: `backend/tests/test_viewer_isolation.py:53`。リアルタイム配信の対象外（_PENDING）: `backend/app/realtime/topics.py:205`。
- 受信処理 `backend/app/services/google_webhook.py:194-259` `handle_webhook_notification`:
  - `sync` は無視（:206-208）。`exists` / `not_exists` を区別せず同じ処理（コメント :202-204）。
  - channel_id → tenant_id は `google_webhook_subscriptions` を引く（:166-186）。無ければ警告して終了（:210-213）。
  - `set_tenant_context`（:218）→ `_get_service`（:224）→ 直近 30 分の `updatedMin` で `events().list(calendarId="primary", singleEvents=True, showDeleted=True)`（:229-241）。**syncToken・pageToken は使っていない**（ページング無し）。
  - 取得した各件を `upsert_from_google`（:246-254）。`reset_tenant_context` は呼んでいない（この関数内に見当たらない）。
- 登録 `register_webhook`（:54-119）: `events().watch(calendarId="primary", ... expiration=今+7日)`（:76-86）。`google_webhook_subscriptions` に `ON CONFLICT (tenant_id) DO UPDATE`（:95-112）。**既存チャンネルの stop は呼んでいない**（docstring :57-58 は「stop → 新規登録」と書くが本文に stop 呼び出し無し）。
- 停止 `stop_webhook`（:127-158）。
- 通知先 URL: `API_BASE_URL`（既定 `https://api.salesanchor.jp`）+ `/api/v1/google-calendar/webhook`（:37,44-46）。
- 表 `public.google_webhook_subscriptions`: `migrations/077_calendar_sync_mode_and_webhook_subscriptions.sql:25-41`（tenant_id UNIQUE・channel_id UNIQUE インデックス・expiration・calendar_id 既定 'primary'）。**RLS の設定は見つからない**（`migrations/20261016_010000_add_google_config_rls.sql` は ADR-1018 の「Google 接続設定 2 表」と書くが、確認できたのは :2-6 の `tenant_google_calendar_config` のみ。2 表目が何かは未確認）。

## 2. update_sync_mode と 422 の理由
- `backend/app/routers/calendar.py:466-505` `PATCH /calendar/sync-mode`（`require_tenant_admin` :470）。
- 422 は 2 種: ① 値が `_VALID_SYNC_MODES = ("bidirectional","read_only","write_only","none")`（:42）に無い（:475-479）。② 値が `_ACCEPTED_SYNC_MODES = ("write_only","none")`（:44）に無い＝bidirectional・read_only（:480-484）。②のメッセージは「Google の予定をアプリへ取り込む設定は使えません（ADR-1057）」。②の理由はコメント :43「取り込むと、つないだ人の Google の予定が会社の予定として全員に見える」。
- 保存後、`bidirectional`/`read_only` なら `register_webhook`、それ以外は `stop_webhook`（:500-503）。②で先に弾くので、現状 `register_webhook` はこの口から呼ばれない。
- `register_webhook` を呼ぶのはこの口だけ（`git grep` 相当で backend/app 内を確認: calendar.py:501 のみ。ほかは `renew_expiring_webhooks` 内 google_webhook.py:286）。
- `GET /calendar/sync-mode`（:450-463）は認証だけで誰でも読める（`require_tenant_admin` 無し）。行が無ければ `"none"`。
- 列 `sync_mode`: `migrations/077_calendar_sync_mode_and_webhook_subscriptions.sql:19-22`（既定 `'bidirectional'`）。つないだ直後の既定値は bidirectional のまま（callback は sync_mode を書かない: `backend/app/routers/google_calendar.py:126-144`）。
- 試験: `backend/tests/test_calendar_owner_api.py:123-133`（bidirectional・read_only が 422 で register を呼ばない）、`:139-165`（write_only・none は通る）。管理者専用の確認: `backend/tests/test_tenant_admin_ssot.py:185`。

## 3. 取り込み処理（Google → calendar_events）
- `backend/app/services/calendar_service.py:367-449` `upsert_from_google`:
  - id 無しは無視（:378-380）。アプリ起源（`sync_origin_id LIKE 'app:<tenant>:%'`）は無視＝ループ防止（:382-385, `_is_app_origin` :76-89）。
  - `status=="cancelled"` は `DELETE FROM calendar_events WHERE google_event_id = :gid`（:388-396）。
  - title は `summary`（無ければ空文字 :398）。`start.dateTime` または `start.date`、end も同様。無ければ警告して無視（:408-410）。終日判定は `"date" in start`（:401）。
  - INSERT は `calendar_type='shared'`・`source='google'`・`sync_status='synced'`・`sync_origin_id='google:<tenant>:<id>'`・`google_calendar_id='primary'`固定（:414-447）。`user_id`・`created_by_user_id`・`category` は入れない（列に無い＝NULL／category は既定値に従う。category の既定値は未確認）。
  - `ON CONFLICT (google_event_id) DO UPDATE`（:426）。UNIQUE の有無は §6。
  - 例外は呼び元で握りつぶしてログのみ（google_webhook.py:246-254）。
- 繰り返し予定: `singleEvents=True`（:238）で展開された個々の実体が来る。展開後 id の扱いは**未確認**（試験無し）。
- 時刻の扱い: 取り込みは `start_dt` の文字列をそのまま渡す（:441）。`date` のみの終日は日付文字列。タイムゾーンの変換は無い（`_parse_dt` を通していない）。実 DB での動作は**未確認**。
- Google への送り側（参考）: `create_event` :172-243（つないだ本人の予定だけ送る :214）、`update_event` :251-325・`delete_event` :333-359（`google_event_id` がある予定だけ）。`_to_google_event_body` :457-478（タイムゾーンは Asia/Tokyo 固定 :470-471）。

## 4. Celery の定期作業
- `backend/app/celery_app.py` に calendar / google / gcal / webhook を含む記述は**見つからない**（`grep -n calendar backend/app/celery_app.py` が 0 件）。
- Google カレンダー関連の backend/app/tasks/ 配下の .py は**見つからない**（tasks 配下で google_webhook・calendar_service を呼ぶ箇所が無い）。
- よって Google の通知に頼らない定期 polling（コメントが推奨 google_webhook.py:13）も、期限更新の定期実行（§5）も、**現状は存在しない**。ほかの beat 登録の書き方の手本: `backend/app/tasks/tcg_mirror.py:7`、`backend/app/tasks/avatar.py:82-84`、`backend/app/tasks/tcg_extraction_recovery.py:562-576`（実際の beat 定義位置の詳細は未確認）。

## 5. Google push 通知の期限更新
- 関数はある: `backend/app/services/google_webhook.py:267-292` `renew_expiring_webhooks(db)`。`expiration < 今+48時間`（`_RENEW_THRESHOLD_HOURS=48` :41, :275-281）の行ごとに `register_webhook`。
- **呼び出し元は試験だけ**: `backend/tests/test_calendar_service.py:614-644`。`backend/app` 内に呼び出しは無い（`grep -rn renew_expiring_webhooks` で google_webhook.py の定義と tests のみ）。
- 最大有効期限 7 日（:38-39）。更新が動かなければ 7 日で通知が止まる。
- `renew_expiring_webhooks` は引数の `db` に tenant 文脈を張らずに全テナントの行を読む（:276-282）。`google_webhook_subscriptions` に RLS が無ければ通るが、RLS の有無は未確認（§1）。
- 更新時の旧チャンネルの停止は無い（§1）。旧チャンネルは期限まで通知を送り続けうる（Google の仕様の挙動は未確認。コード上は旧 channel_id の行が `ON CONFLICT` で上書きされるため、旧 channel_id の通知は「不明な channel_id」で無視される: google_webhook.py:210-213）。

## 6. calendar_events の列と索引
- 作成: `migrations/078_create_calendar_events_tenant.sql:44-66`（tenant_NNN スキーマごと）。列: id, user_id, calendar_type('shared'|'personal'), title, description, location, start_datetime, end_datetime, is_all_day, **google_event_id VARCHAR(255)**, **google_calendar_id VARCHAR(255)**, source('app'|'google'), sync_status('synced'|'pending'|'failed')、**sync_origin_id VARCHAR(500)**, last_synced_at, created_by_user_id, created_at, updated_at。
- 追加列: `category`（`migrations/20260621_020000_add_schedule_calendar_category_and_owner_settings.sql:33-47`）。
- 索引: `idx_calendar_events_google_id`（`(google_event_id) WHERE google_event_id IS NOT NULL`・**UNIQUE ではない**: 078:77-81）、`idx_calendar_events_sync_origin`（:84-88）、range（:70-74）、user_type（:91-95）。
- `migrations/` 内に `calendar_events` を含むファイルは 3 つのみ（078・20260621_020000・20261024_100300）。google_event_id に UNIQUE を足す migration は**見つからない**。→ `ON CONFLICT (google_event_id)`（calendar_service.py:426）は、ON CONFLICT の対象に一致する UNIQUE 制約／部分 UNIQUE インデックスが無ければ PostgreSQL がエラーにする（PostgreSQL の仕様）。本番にその制約があるかは**未確認**（本番を見ていない）。試験は DB をモックしている（`backend/tests/test_calendar_service.py:48` `_make_db`）ため、この点は試験で捕まらない。
- AI 用ビュー: `migrations/20261024_100300_create_ai_cloud_views.sql:338` が `calendar_events` の `google_calendar_id, google_event_id, location, source, sync_origin_id` 等を mask。
- calendar_events 自体の RLS: migrations 内に見つからない（ADR にも言及無し）。テナント分離はスキーマ（tenant_NNN）。
- 接続側の列: `public.tenant_google_calendar_config`（`migrations/076_add_google_calendar_config.sql:14-24`）= tenant_id UNIQUE・access/refresh token（暗号化）・token_expiry・calendar_id 既定 'primary'・connected_by_user_id・connected_at・updated_at。`sync_mode` は 077。RLS は `migrations/20261016_010000_add_google_config_rls.sql:2-6`。
- 取り込みは常に `calendar_id='primary'` 固定（calendar_service.py:445, google_webhook.py:236）で、接続行の `calendar_id` 列は使っていない（`get_calendar_id` が google_calendar.py:334 にあるが、webhook からは呼ばれていない）。

## 7. 誰の予定が誰に見えるか（可視性）
- 一覧 `GET /calendar/events`: `backend/app/routers/calendar.py:132-150`。`get_current_user` のみで権限判定なし。`type` 未指定なら**期間内の全件**（共有・個人・全員分）を返す（`backend/app/services/calendar_service.py:110-121`。type が 'shared' なら共有、'personal' なら本人の個人だけ。None は絞りなし）。
- 画面は type を付けずに呼ぶ: `frontend/src/pages/schedule/SchedulePageImpl.tsx:928`。担当者での絞りは画面側のみ: `eventMatchesFilters`（:148-151。`ownerUserId == null` は常に表示）。
  - 帰結（コードから読める事実）: 取り込んだ予定は `user_id` が NULL（§3）なので、画面の担当者フィルタに関係なく**常に表示される**。API を直接呼べば、他人の個人予定（`calendar_type='personal'`）も返る（:110-121 に絞りが無い）。
- 担当者名簿 `GET /calendar/owners`（calendar.py:158-215）: `staff.view` を持つ人は全員、持たない人は自分だけ（:164-165, 185-189）。`calendar_owner_settings` の `share_mode`（self|view|edit）・color・is_visible を返す（:176-179）。**share_mode を使って一覧 API の中身を絞る処理は calendar_service.list_events に見当たらない**（share_mode が効く場所の詳細は未確認）。
- 更新・削除: 作った本人か tenant admin（owner/admin）のみ（calendar.py:388-399, 439-440）。取り込んだ予定は created_by_user_id が NULL のため、admin 以外は編集・削除できない（:398,439 の条件から）。
- 作成: ログイン者なら誰でも（:338-364）。`calendar_type` は shared/personal。
- Google の予定を直接読み書きする 4 つの口（`/google-calendar/events` GET/POST/PATCH/DELETE）は、つないだ本人だけ（`require_calendar_owner` :155-178, 各口 :280, :308, :335, :369）。未接続・他人は 403。
- 接続操作: start・disconnect は `require_tenant_admin`（:194, :222）。`GET /google-calendar/status` は認証のみ（:238-264）。
- 接続は会社で 1 つ（`tenant_id UNIQUE` 076:15）。callback の upsert は上書き（:134-141）。

## 8. ADR-1057 と schedule-gcal-connect の決定・対象外
ADR-1057（`docs/adr/ADR-1057-google-calendar-owner-only-sync.md`）
- 決定（:15-19）: 接続は会社で 1 つ／アプリ→Google はつないだ本人の予定だけ／直接口 4 つは本人だけ／**Google→アプリの取り込みを始める同期方式（bidirectional・read_only）は 422**／ボタンはオーナー・システム管理者のみ。
- 理由（:23-26）: 取り込みは `calendar_type='shared'` で入り、誰が始めても、つないだ人の Google の中身が会社の全員に見える。今の目的（アプリの予定を PO の Google で見る）には要らない。
- 受け入れた点（:30-31）: ほかの管理者が直す・消すと Google に反映される／本人以外の管理者が「つなぐ」を押すと接続が入れ替わる。
- **見直す条件（:38-40）**: 「Google→アプリの取り込みが要るとき、または PO 以外の人が自分の Google をつなぎたいとき（人ごとの接続が要る）」。→ 今回の取り込み設計はこの条件に当たる。ADR-1057 の更新（または新 ADR）が要るかは設計担当の判断（未確認事項ではなく、要否は設計の論点）。
- 戻し方（:33-36）: 実装 PR の revert。DB の形は変えない。

`docs/handoff/schedule-gcal-connect/design.md`
- 対象外（:28-31）: Google→アプリの取り込みを作ること／既存 9 件を後から Google に送ること／接続を外すボタン・`GoogleCalendarStatusBar` の作り直し。
- 取り込みを止める理由（:26, :39, :51）: PO の Google の予定が「会社の予定」として全員に見える。「呼び手を本人に絞るだけでは足りない。PO 本人が始めても全員に見える」（:51）。
- リスク（:66）: 取り込み登録は 0 件（2026-11-03 読み取り）。`renew_expiring_webhooks` は登録済みを更新するだけで新規取り込みは始まらない。
- 追補 §13（:100-114）: PKCE の code_verifier 不具合の修正（`autogenerate_code_verifier = False`）。同期方式の既定値は変えない。

`docs/handoff/schedule-gcal-connect/recon.md`
- 取り込みの道は同期方式の口だけ（:39-44）。取り込み時に `calendar_type='shared'` で入る（:42）。本番 `google_webhook_subscriptions` 0 件（:44）。本番 `tenant_google_calendar_config` 0 行（:25-28, :68）。
- 追補 §4（:61-68）: 本番でつなぐと「Missing code verifier」で失敗した事実。部品は google-auth-oauthlib 1.5.0。
- 未確認（:58-59）: Google 側の戻り先 URL の登録。
- **注意**: 上の本番の件数（接続 0 行・購読 0 件）は 2026-11-03 の記述。その後に PO がつなぎ直したかは**未確認**（今回本番を見ていない）。

## 9. OAuth の範囲・トークン（取り込みの前提）
- スコープ: `https://www.googleapis.com/auth/calendar`（フル。読み書き）`backend/app/services/google_calendar.py:41`。
- アクセストークン失効 5 分前に更新（:241-249）。更新は `_refresh_if_needed`（:252-）、サービス生成は `_get_service`（:303-331）。
- 取り込みで使うのは接続 1 つ分のトークンだけ＝つないだ人の Google の `primary`。他の人の Google を取り込む仕組みは無い（接続が tenant 1 行のため）。

## 10. 試験（取り込み関連・既存）
- `backend/tests/test_calendar_service.py`: `TestIsAppOrigin` :157、`TestUpsertFromGoogle` :392-495（id 無し・cancelled 削除・アプリ起源スキップ・正常 upsert・start/end 不正・終日）、`TestGetWebhookAddress` :497、`TestGetTenantByChannel` :518、`TestHandleWebhookNotification` :537-554（sync 無視・不明 channel）、`TestRegisterWebhook` :556、`TestStopWebhook` :582、`TestRenewExpiringWebhooks` :614-644、`TestHandleWebhookNotificationExists` :646-。DB はモック（:48 `_make_db`）で、実 PostgreSQL に対する ON CONFLICT の試験は**見当たらない**。
- `backend/tests/test_calendar_owner_api.py`: sync-mode の 422 と通る方式（§2）。
- `backend/tests/test_google_calendar.py`: 直接口の本人確認、認可 URL など。`backend/tests/test_google_config_rls.py`、`backend/tests/test_viewer_isolation.py:33,53`（webhook・callback の許可リスト）、`backend/tests/test_event_loop_nonblocking.py`、`backend/tests/test_tenant_admin_ssot.py:185`。
- 一覧 API の可視性（type 無しで全件返す）を確かめる試験: **見つからない**（未確認）。
- 画面側: 取り込んだ予定の表示の試験は未確認。

## 11. 設計担当が決めるべき論点（事実から見える穴。推測は含めない）
1. 取り込んだ予定の見え方: `user_id` NULL・`shared` で入る → 全員に常時表示（§7）。ADR-1057 の懸念そのもの。可視性を決めずに口を開けると同じ問題が再発する。
2. `google_event_id` の UNIQUE が無い（§6）: `ON CONFLICT` がそのままでは動かない可能性。本番の実際の制約は要確認。
3. 期限更新の呼び出し元と定期作業が無い（§4・§5）。通知は 7 日で止まる。
4. webhook の真正性確認が無い（§1）。
5. 差分取得が「直近 30 分」固定で syncToken・ページング無し（§1）。通知が落ちたり 30 分以上遅れると取りこぼす。Google の仕様として通知は保証されない（コメント google_webhook.py:12-13）。
6. 接続が会社で 1 つ・`primary` 固定（§6, §9）。他の人の Google は取り込めない。
7. ADR-1057 の「見直す条件」に当たるため、ADR の更新または新 ADR が要る（要否は PO／設計担当の判断）。
