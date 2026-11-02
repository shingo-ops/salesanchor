# recon — 予定の画面に Google カレンダーのつなぐボタンを戻す

基準: origin/main c60ea6eb3（2026-11-03 fetch 後）。本番は読み取りのみ（BEGIN READ ONLY … ROLLBACK）。
生出力: セッションの作業メモ（gc/check9〜17・check10〜12-prod）。

## 0. 既存 ADR の検索
- `git grep -i -l "google.calendar" docs/adr/` → ADR-1018 のみ。`docs/adr/FEATURE-INDEX.md` にカレンダーの行は無い。
- ADR-1018:15,24 — `tenant_google_calendar_config` は RLS 段階②（会社別の型）。OAuth callback は文脈を張ってから書く（下の 1-1）。今回この表の書き方は変えない。
- Google カレンダー同期の方針を決めた ADR は無い（今回 ADR-1057 を起こす）。

## 1. 裏側（事実）
### 1-1 接続の口
- `backend/app/routers/google_calendar.py` connect_callback: `set_tenant_context` の後に `tenant_google_calendar_config` へ upsert する。保存するのは `connected_by_user_id = user_id`（state から取り出す）。その後 `/schedule?connected=true|false` へ戻す。
- `GET /google-calendar/connect/start` は `require_tenant_admin` が要る。返すのは `{auth_url}`。
- `GET /google-calendar/status` は行が無ければ `{connected:false, configured:false}`、行があれば `{connected:true, configured:true, ...}`。「configured=true かつ connected=false」を返す道は無い。
- `backend/app/auth/dependencies.py`（origin/main の require_tenant_admin）: 判定の正本は user_roles の system_key（owner / admin）。

### 1-2 予定を Google に送るところ
- `backend/app/services/calendar_service.py:45-54` `_get_sync_mode`: 行が無ければ `'none'` を返す。
- `backend/app/services/calendar_service.py:159` `create_event`。:199-200 で `sync_mode in ("bidirectional","write_only")` なら、作った人を見ずに Google へ送る。
- `backend/app/services/calendar_service.py:285` update / :338 delete: `google_event_id` がある予定だけ Google に送る。送っていない予定は変えても消しても Google に行かない。
- `backend/app/routers/calendar.py:350-355`: 作成の口は `user_id=user.id`（ログインしている人）を渡す。秘書が作る予定も、PO のログインでこの口を呼ぶ。
- Google→アプリの通知の登録は `PATCH /calendar/sync-mode`（`backend/app/routers/calendar.py:491-496`）からだけ行われる。この口を呼ぶ画面は無い。今回の範囲外。

### 1-3 本番（2026-11-03 読み取り）
- `public.tenant_google_calendar_config`: 0 行。列の既定値は calendar_id='primary'、sync_mode='bidirectional'。
- tenant_004 の役割: user 3 = オーナー（owner）、6・83 = 営業、84 = スモーク専用。`channels.manage` を持つ役割は「システム管理者(admin)」と「オーナー(owner)」だけ。
- `tenant_004.calendar_events` 9 件。作った人（created_by_user_id）は全件 user 3。google_event_id は 0 件。
- user 3 のメールのドメインは treasureislandjp.com。2026-11-02 に PO が秘書で作った予定もこの 9 件に入る。よって PO = user 3。

### 1-4 Google の予定を直接読む・書く口（見つかった穴）
- `backend/app/routers/google_calendar.py:245-345` に 4 つの口がある: `GET /google-calendar/events`（:249）・`POST`（:276）・`PATCH /{event_id}`（:302）・`DELETE /{event_id}`（:335）。
- どれも `tenant_id = Depends(get_current_tenant)` と `db` だけを受け取る。管理者や本人の確かめは無い。`backend/app/main.py:674-677` も `get_current_tenant` だけを付ける。
- `GET` はつないだ人の Google カレンダー（既定 primary）の予定一覧を返す。`POST`/`PATCH`/`DELETE` はそこへ直接書く。
- つまり、PO がつないだ後は、同じ会社でログインできる人（営業の 6・83 など）が、画面を通さず口を直接呼べば、PO の Google の予定を読めて書けて消せる。
- 画面からこの 4 つの口を呼ぶところは無い（`git grep "google-calendar/events" -- frontend/src secretary-agent` で 0 件）。
- 試験の手本: `backend/tests/test_google_calendar.py:310-317` は、口の `user` 引数の既定値が `require_tenant_admin` かを `inspect` で確かめている。

### 1-5 Google→アプリの取り込みの道（審査役の指摘で追加）
- `backend/app/routers/calendar.py:464-498` `PATCH /calendar/sync-mode` は `require_tenant_admin`。受け付ける方式は `_VALID_SYNC_MODES = ("bidirectional","read_only","write_only","none")`（:42）。:493-494 で bidirectional・read_only のとき `register_webhook` を呼ぶ。
- 取り込みの登録を始めるのはこの口だけ。ほかは `renew_expiring_webhooks`（`backend/app/services/google_webhook.py:267-286`）で、登録済み（`google_webhook_subscriptions` に行がある）ものを更新するだけ（git grep で確かめた）。
- 通知が来ると `google_webhook.py:230-249` が primary の直近 30 分の変更を読み、`calendar_service.py:400-433` `upsert_from_google` が `calendar_type='shared'` で入れる。会社の予定として全員に見える。
- この口が管理者専用であることは `backend/tests/test_tenant_admin_ssot.py:184-185` が確かめている。
- 本番 `public.google_webhook_subscriptions`: 0 件（2026-11-03 読み取り）。

## 2. 画面（事実）
- つなぐボタンは 2026-06-21 の 1e4c4e7fb「fix schedule parity」で消えた。旧コードは `hasPermission("channels.manage")` で表示し、生の `<button className="gcal-connect-btn">` を使っていた（今の決まりでは使えない）。
- `frontend/src/pages/schedule/SchedulePageImpl.tsx:829,831` `usePermissions()` / `canManageOwners = hasPermission("staff.view")`。
- `frontend/src/pages/schedule/SchedulePageImpl.tsx:864-874` `?connected=true|false` を見て知らせの帯（banner）を出す処理は残っている。
- `frontend/src/pages/schedule/SchedulePageImpl.tsx:1118-1150` ヘッダー右（headerAction）には検索・設定・表示切替がある。つなぐボタンは無い。
- `frontend/src/hooks/usePermissions.ts:13-46`: `/me/permissions` から `permissions` だけを読む。`is_tenant_admin` は返さない。
- `backend/app/routers/roles.py:132-162` `/me/permissions` は `is_tenant_admin` も返す。`frontend/src/pages/goal-setting/GoalSettingPage.tsx:515-519` は同じ口を `useApiQuery` で読み、`is_tenant_admin` を使っている。
- `frontend/src/lib/query/apiQuery.ts:52-54` `useApiQuery(path, { enabled?, keepPrevious? })`。
- 文言キー（ja / en 両方にある）: `schedule.connectBtn`「Googleカレンダー連携」、`schedule.connectBtnConnected`「✔︎連携済」、`schedule.connectSuccess`、`schedule.connectError`。
- `frontend/src/components/GoogleCalendarStatusBar.tsx`: どの画面でも使われていない。手書きの style（`minHeight: "36px"` など）を持つ。状態「切断中」は 1-1 のとおり起きない。今回は使わない。
- ボタンの決まり（`docs/specs/design-system/component-ssot/page-header-v2/design.md` §2）: ヘッダーでは ghost（設定系）を使ってよい。primary は使えない。生 button と手書き style は禁止。

## 3. 未確認
- Google の画面で、本番のつなぎ先の戻り先 URL が登録済みか。鍵 3 つは本番に設定済み（値は見ていない）。これは PO がボタンを押したときに分かる。
