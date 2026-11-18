# 予定ごとの色 — 現状の調べ（recon）

基準: `origin/main` fba2172b8（2026-11-19）。読み取りのみ。行番号はこの版のもの。
設計: [design.md](design.md)・決まりの記録: `docs/adr/ADR-1081-event-color-labels.md`（Proposed）

## 1. 既存 ADR の検索

- 検索語: `color`・`色`・`colorId`・`eventLabel`・`label`・`calendar_events`（`git grep -i` を `docs/adr/` に対して実行・`docs/adr/FEATURE-INDEX.md` も確認）。
- 関係する ADR:
  - ADR-1057（自分の予定だけ Google と同期）・ADR-1059（Google からの取り込み）: Google との行き来の決まり。
  - ADR-1065（予定の画面の金型）・ADR-1074（編集の画面の金型。`--gcal-*` のトークンの持ち主）・ADR-1075（繰り返しの予定と 3 択）。
  - ADR-067（デザイントークン）・ADR-144（部品の金型）・ADR-027（画面の文字は `t()`）。
- 予定ごとの色を決めた ADR は 0 件。Google の `colorId`・`eventLabelId` を扱う決まりも 0 件。

## 2. 予定の記録（DB）

- 予定の表は各社の部屋の `calendar_events`（`migrations/078_create_calendar_events_tenant.sql:44`〜`migrations/078_create_calendar_events_tenant.sql:66`）。色の欄は無い。
- 新しい会社を作るときの表の形: `backend/app/services/tenant.py:1549`〜`backend/app/services/tenant.py:1596`。値の決まりの書き方の手本は `backend/app/services/tenant.py:1575`（`calendar_events_category_check`）。
- 後から足した欄の手本（全社の部屋を回す DO の繰り返し・`ADD COLUMN IF NOT EXISTS`）:
  - `migrations/20261104_161223_add_calendar_events_meet_url.sql`
  - `migrations/20261112_170000_add_calendar_events_recurrence.sql`（値の決まりを `NOT VALID` で足してから `VALIDATE`）
- 移行の登録先:
  - `scripts/run_all_migrations.sh:1452`〜`scripts/run_all_migrations.sh:1453`
  - `backend/tests/rls_bootstrap.py:187`
  - `backend/tests/test_calendar_sync_tenant_reset_pg.py:53`・`backend/tests/test_calendar_sync_tenant_reset_pg.py:301`
  - `backend/tests/test_tenant_loop_migration_guard.py:50`・`backend/tests/test_tenant_loop_migration_guard.py:67`
- AI 用の写しの欄の分類表（このファイルが正本・`migrations/20261024_100300_create_ai_cloud_views.sql:3`）:
  - `calendar_events` の行は `migrations/20261024_100300_create_ai_cloud_views.sql:371`〜`migrations/20261024_100300_create_ai_cloud_views.sql:375`。
  - 値の決まりで値が限られる欄は `allow`（`:371`・`:374`）。
  - 欄を足したときに分類表の行も足した例は f0df9074a（meet_url）と c770f6483（繰り返し）。
  - 欄ごとの見張りの試験の型は `backend/tests/ops/test_ai_cloud_views.py:587` 以降の `test_t10_*_classified`。

## 3. 裏側（backend）

- Google の鍵の許可範囲はカレンダー全体（`backend/app/services/google_calendar.py:42` `_SCOPES = ["https://www.googleapis.com/auth/calendar"]`）。
- Google の道具は `build("calendar","v3", ...)` で作る（`backend/app/services/google_calendar.py:331`）。
- 書き込み:
  - `create_event` は `events().insert`（`backend/app/services/google_calendar.py:391`〜`backend/app/services/google_calendar.py:406`）。
  - `update_event` は `events().patch`（`backend/app/services/google_calendar.py:411`〜`backend/app/services/google_calendar.py:426`）。
  - どちらも Meet のときだけ `conferenceDataVersion=1` を足す（`:403`・`:423`）。手本になる。
- つなぐカレンダーは会社の設定の `calendar_id`、無ければ `primary`（`backend/app/services/google_calendar.py:335`）。
- 予定の欄の流れの手本は `location`。通る場所:
  - `backend/app/services/calendar_service.py:151`（`EVENT_COLUMNS`）
  - `:174`（`_google_body_for`）
  - `:279`（一覧の返し）
  - `:418`（作成の INSERT）
  - `:495`（更新の欄の表）
  - `:661`（`_TEXT_FIELDS`・繰り返しの差の判定）
  - `:955`（`_row_values`）・`:1030`・`:1098`・`:1188`（繰り返しの 3 択）
  - `:1384`（Google からの取り込み）・`:1483`（Google の本文）
- Google の本文を作るのは `_to_google_event_body`（`backend/app/services/calendar_service.py:1446`）。呼び元:
  - 作成 `:436`・更新 `:539`・`_google_body_for` 経由 `:179`。
  - `_google_body_for` の呼び元は `:1062`・`:1121`・`:1138`・`:1177`・`:1200`（繰り返しの 3 択）。
- 画面からの更新では、`_to_google_event_body(payload)` を `patch` で送る（`backend/app/services/calendar_service.py:539`〜`backend/app/services/calendar_service.py:551`）。
- Google からの取り込みは `upsert_from_google`（`backend/app/services/calendar_service.py:1342`）。
  - アプリで作った予定（`sync_origin_id` が `app:` で始まる）は取り込まない（`:1364`〜`:1366`・`:130`〜`:143`）。
  - 上書きは `WHERE calendar_events.source = 'google'` の行だけ（`:1395`〜`:1420`）。
  - つまり、アプリで作った予定を Google で直しても、今はどの欄もアプリに戻らない。
  - 呼び元は `backend/app/services/google_webhook.py:332` の 1 か所だけ。その前の `events().list` は `backend/app/services/google_webhook.py:300`〜`backend/app/services/google_webhook.py:314`。
- 画面からの受け口:
  - `CreateEventBody`（`backend/app/routers/calendar.py:114`）・`UpdateEventBody`（`backend/app/routers/calendar.py:126`）。
  - 中身は `model_dump(exclude_none=True)` で渡す（`backend/app/routers/calendar.py:440`・`backend/app/routers/calendar.py:465`）。`None` は落ちるので、「色を外す」は `None` では伝わらない。
- 裏側に `colorId`・`eventLabelId` の扱いは無い（`git grep -n -i "colorId\|eventLabel" -- backend` が 0 件）。

## 4. 画面（frontend）

- 予定の箱の色は持ち主の色:
  - `frontend/src/pages/schedule/SchedulePageImpl.tsx:1272`（`getOwnerMeta(...).color`）
  - `frontend/src/components/CalendarView.tsx:338`（`--comp-calendar-owner-color` を付ける）
  - `frontend/src/components/calendarView.utils.ts:43`・`frontend/src/components/calendarView.utils.ts:180`
  - `frontend/src/components/CalendarView.css:146`〜`frontend/src/components/CalendarView.css:150`（地と枠に使う・文字は `--on-solid`）
- 持ち主の色の正本は `calendar_owner_settings.color`（`backend/app/routers/calendar.py:50` 既定 `#1a73e8`）。
- 下書きの欄:
  - `frontend/src/pages/schedule/SchedulePageImpl.tsx:99`・`:156`・`:974`・`:1019`・`:1210`・`:1302`
  - `frontend/src/pages/schedule/schedule-utils.ts:21`・`:66`・`:372`
- 種類の欄（色の欄を並べる場所の手本）:
  - `frontend/src/pages/schedule/ScheduleDraftFields.tsx:278`（`DraftCategoryField`）
  - 使う場所は `frontend/src/pages/schedule/ScheduleDraftFields.tsx:508`（小さな窓）と `frontend/src/pages/schedule/ScheduleFullEditor.tsx:88`（全体の編集の画面）
- 繰り返しの予定を直して保存すると 3 択を出す:
  - `frontend/src/pages/schedule/SchedulePageImpl.tsx:1045`〜`frontend/src/pages/schedule/SchedulePageImpl.tsx:1070`
  - 裏側は `_TEXT_FIELDS` に入った欄の差で「どこを直したか」を決める（`backend/app/services/calendar_service.py:720`〜`backend/app/services/calendar_service.py:722`）。
- 色を選ぶ部品は無い（`frontend/src/components/` に color・swatch・picker の名の部品 0 件）。土台に使える部品は `Popover`・`ContextMenu`・`SubMenu`。
- Google の色のトークン `--gcal-*`:
  - 明るい画面 `frontend/src/index.css:194`〜`frontend/src/index.css:206`・暗い画面 `frontend/src/index.css:410` 以降。
  - 書いてよい場所は `index.css`・`tokens.css` だけ（`frontend/src/components/gcalColorsUsage.test.ts:26`）。

## 5. Google の色（2026-11-19 実測）

- Google の画面の色は「予定のラベル」24 色＋デフォルト。
  - 予定の編集の画面で色の印を押し、出た一覧を読んだ。保存はしていない。
  - 英語の名と日本語の名、色の値の対応は design.md §4-1 の表。
- PO の会社のカレンダー（primary）の `calendars.get` の `labelProperties.eventLabels` は 24 件。
  - 各件は id（UUID）と `backgroundColor` だけ。名は無い。
  - 24 件の色は画面の 24 色と 24/24 一致。
  - デフォルトの色（rgb 221,227,234）は名札に無い＝「名札なし」。
  - id の一覧は写さない。カレンダーごとに違うかは【未確認】。
- Google の公式文書（Context7 `/websites/developers_google_workspace_calendar_api`・2026-11-19）:
  - `eventLabelId` はカレンダーの `labelProperties.eventLabels` の id を指す。`colorId` に取って代わる。
  - 書くには `insert`・`import`・`update`・`patch` に `eventLabelVersion=1` が要る。そのとき `colorId` は無視される。
  - `eventLabelVersion=1` のとき、`eventLabelId` が空か無いと、付いていた名札が外れる。
  - 名札を付けるには、そのカレンダーの `writerWithoutPrivateAccess` 以上の権限が要る。
  - 2026-07-07 に正式公開。
- Google の公開の API 説明（discovery・revision 20261115・2026-11-19 取得）:
  - `eventLabelVersion` を受けるのは `insert`・`patch`・`update`・`import`。
  - `list`・`get`・`instances` は受けない。
  - `Event.eventLabelId`・`Calendar.labelProperties` がある。
- 道具の部品 `google-api-python-client`:
  - 求める版は `>=2.100.0,<3.0.0`（`backend/requirements.txt:43`）。backend の入れ物は組み立てのたびに入れ直す（`backend/Dockerfile:21`）。
  - 最新の 2.202.0 に入っている API 説明（revision 20261030）は `insert`・`patch` で `eventLabelVersion` を受ける。`eventLabelId`・`labelProperties` もある。
  - 本番の入れ物に入っている版は【未確認】。

## 6. 未確認（設計で扱いを決め、便の中で確かめる）

- U1: 本番の入れ物の道具の版が、`eventLabelVersion` を受けるか。→ design.md §4-4 の試験で毎回確かめる。
- U2: `events.list` の返事に `eventLabelId` が入るか。版の指定の無い読み取りで入るかは、公式文書に書いていない。→ 本番の K4 で確かめる。入らなければ止める（design.md §13）。
- U3: Google の画面で古いやり方（`colorId`）の色が付いた予定の扱い。→ 色なしとして取り込み、数をログに出す（design.md §6）。
- U4: 名札の id がカレンダーごとに違うか。→ 色の値で照らすので、違っても動く（design.md §5）。
