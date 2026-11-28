# recon: 予定の中身を Google とアプリの両方向でそろえる

- 調べた日: 2026-11-20（JST）
- 基準: origin/main `c70ad7bd6`（worktree `release/calendar-two-way-sync` 作成時の HEAD）
- きっかけ: PO が Google カレンダーで、アプリで作った予定の色を変えた。アプリの予定の画面は変わらなかった。PO の選択（2026-11-20「1,」）:「予定の中身を全部、両方向にそろえる → 題名・時間・場所・色を、どちらで直してももう片方にそろえます。画面も開き直さずに変わります。」

## 1. 既存 ADR の検索

- `docs/adr/FEATURE-INDEX.md:34`（カレンダー / 予定 / Google カレンダー / 取り込みの行）→ ADR-1057・ADR-1059・ADR-1060・ADR-1018・ADR-1075
- 予定の色: ADR-1081（K3・K4 は PO 目視合格・K8 は #5634 で本番反映し PO 目視合格）
- 即時反映: ADR-1016（決定5「裏の処理がデータを書き換えたときは、終わったところで publish_change を明示的に呼ぶ」・決定6 会社ごとのチャンネル `rt:t:{tenant_id}`）
- ADR-1059 What: 接続の持ち主の Google `primary` の予定を `calendar_events` に取り込む。Google 側で中身が変わってもアプリで選んだ見せ方（`calendar_type`）は変えない。syncToken 方式・知らせ（push）＋15 分おき。
- ADR-1075 決定6: 取り込みでは、アプリ起源の元の予定の回（`recurringEventId` が一致）を飛ばす。
- アプリ起源の予定を Google で直したときに取り込むかを決めた ADR は無い（ADR-1059 は Google 起源の予定だけを書いている。実装はアプリ起源を飛ばす）。

## 2. Google → アプリ（取り込み）の今の動き

- 呼ばれ方: `backend/app/tasks/google_calendar_sync.py:26`（知らせの受け口から 1 社分）と `backend/app/tasks/google_calendar_sync.py:63`（15 分おきの全社）が、どちらも `backend/app/services/google_webhook.py:234` `sync_tenant_from_google` を呼ぶ。
- 読み方: `backend/app/services/google_webhook.py:299`〜`:300` `calendarId: "primary"`・`singleEvents: True`（繰り返しは回ごとに返る。元の予定そのものは返らない）。
- 1 件ずつ `backend/app/services/google_webhook.py:339` で `upsert_from_google` を呼ぶ。全部終えて `:371` で commit、`:372` で `reset_tenant_context`、`:377` で件数を返す。
- **画面への合図は出していない**: `git grep -n "publish_change" origin/main -- backend/app/services/google_webhook.py backend/app/services/calendar_service.py backend/app/tasks/google_calendar_sync.py` は 0 件（ADR-1016 決定5 の合図が無い）。
- `backend/app/services/calendar_service.py:1382` `upsert_from_google`:
  - `:1408` `_is_app_origin(google_event_id)` が真なら `"skipped"`（アプリで作った予定は Google で直しても取り込まない）。**PO の色の件の原因はここ**。
  - `:1412` `recurringEventId` がアプリ起源なら `"skipped"`（ADR-1075 決定6）。
  - `:1420` 消された予定は `source = 'google'` の行だけ消す。
  - `:1491` 上書きは `WHERE calendar_events.source = 'google'` の行だけ。
- `backend/app/services/calendar_service.py:131` `_is_app_origin`: `sync_origin_id LIKE 'app:{tenant}:%'` の行があるかを見る。`:124` `_build_sync_origin_id` の説明:「Webhook 受信時にこの値が存在するイベントはスキップして無限ループを防止する」。
- 取り込みは DB だけに書く。Google への書き込み（`backend/app/services/google_calendar.py` の `events().insert` / `events().patch`）は、アプリの作る・直す・消すの関数からだけ呼ばれる（`upsert_from_google` と `sync_tenant_from_google` の中に Google へ書く呼び出しは無い。上の 2 関数の全文を読んで確認）。

## 3. アプリ → Google の今の動き

- `backend/app/services/calendar_service.py:490` `update_event`: DB を直すとき `:537` で `sync_status = 'pending'` を入れて commit → Google へ patch → 成功で `:577` `sync_status = 'synced'`、失敗で `'failed'`。
- 送る条件は「`google_event_id` がある」かつ同期方式が `bidirectional` か `write_only`。Google 起源の行もアプリで直せば Google へ送られる（`source` を見ていない）。
- 作るときの色: `:445` `send_color=payload.get("color_key") is not None`（色を選んで作れば Google にも送る）。
- 繰り返しの直し（`:992`〜`:993`・`:1104`）も `sync_status = 'pending'` を入れる。
- `updated_at` は表の仕掛け（`migrations/078_create_calendar_events_tenant.sql:113` `trg_calendar_events_updated_at`）で更新される。

## 4. 即時反映（ADR-1016）の今の形

- 合図の名前の表: `backend/app/realtime/topics.py`。人宛て `USER_TOPICS`（`:23`）・裏の処理用 `TASK_TOPICS`（`:37`・今は `tcg.inventory: shared` だけ）。
- 予定の書き込みの口（`backend/app/realtime/topics.py:190`〜`:192`）は `NO_SIGNAL_ROUTES` に `_PENDING`（`:92`「段階2で画面に当てるときに決める」）で載っている。
- 試験 `backend/tests/test_realtime_topics.py:138` `test_task_topics_are_shared_or_global`: 理由のコメント「会社 ID の無い裏の処理から tenant 範囲の合図は出せない」。`:129` で画面側の名前（`frontend/src/lib/realtime/topics.ts`）と裏の名前の集合（`:132`）が同じかを照合する。
- 送り口: `backend/app/realtime/publisher.py:69` `publish_change(topic, scope, tenant_id, origin)`（Redis 障害時はログだけで例外を出さない）。
- 画面側の受け口: `frontend/src/hooks/useRealtimeRefresh.ts:15`。使っている画面は通知の鈴・在庫表など 5 か所。**予定の画面（`frontend/src/pages/schedule/SchedulePageImpl.tsx`）は使っていない**。
- 予定の画面の読み方: `frontend/src/pages/schedule/SchedulePageImpl.tsx:886` `eventsQ = useApiQuery(... "/calendar/events?start=…&end=…")`。保存の後は `:908` `useInvalidateApi()` で `invalidate(["calendar", "events"])`（`:1073`・`:1112`・`:1322`）。

## 5. 本番の事実（読み取り専用の鍵・ADR-1024・2026-11-20 23:11 JST）

`google_event_id` がある行を、会社・起源・同期の状態・繰り返し・色の有無で数えた（生の結果: 作業メモ prod-sync-status.txt）:

| 会社 | 起源 | 同期の状態 | 繰り返しの元 | 例外の回 | 色あり | 件数 |
|---|---|---|---|---|---|---|
| 001 | app | synced | なし | なし | なし | 1 |
| 004 | app | synced | なし | なし | なし | 1 |
| 004 | app | synced | なし | なし | あり | 2 |
| 004 | google | synced | なし | なし | なし | 19 |

- アプリ起源で Google にもある予定は 4 件。すべて `synced`。`pending`・`failed` は 0 件。繰り返しは 0 件。
- 003・005・006 には Google にある予定が無い。

## 6. 分かっていないこと

- Google の知らせが届くまでの秒数（Google は到着を保証しない。ADR-1059 Why）。本番で直してから DB が変わるまでの時刻を K で測る。

## 便2（2026-11-22・Google で色を「なし」に戻したとき）

- 既存 ADR の確認: `git grep -il "eventLabelId\|color_key" origin/main -- docs/adr/` で ADR-1059・ADR-1081 を確かめた。色の取り込みの決めは ADR-1059 改訂 2026-11-20 と ADR-1081。
- 実物の行番号と本番の記録の数は design.md §10-2 に書いた（origin/main 2560f963f・Loki 7 日分: 取り込み 481 回（2026-11-19〜21 の記録）・古い色の番号だけの予定 0 件・`event_label_missing` 0 件・`event_label_colors_unavailable` 0 件）。

## 便3（2026-11-23・アプリで説明・場所を空にしたとき）

- 既存 ADR の確認: `git grep -il "description\|説明" origin/main -- docs/adr/ | grep -i calendar` で ADR-1059・ADR-1060 が出た。説明・場所の送り方の決めは ADR-1059 改訂 2026-11-20（「空 "" でも送る。None は送らない」）。ADR-1060 は Meet の件で、説明・場所の扱いは決めていない。
- 実物の行番号は design.md §11-2 に書いた（origin/main 3763e55c7 で読んだ）。

## 便4（2026-11-25・Google で消したとき・繰り返しの 1 回だけを直した・消したとき）

- 既存 ADR の確認: `git grep -il "is_cancelled\|recurringEventId\|cancelled" origin/main -- docs/adr/` で ADR-1059・ADR-1075 を確かめた。「Google で消しても消さない」は ADR-1059 改訂 2026-11-20（`docs/adr/ADR-1059-google-calendar-import-owner-private.md:30`）。「アプリで作った繰り返しの回は取り込まない」は ADR-1075 決定6（`docs/adr/ADR-1075-schedule-recurrence.md:20`）と Why（`:26`）。
- 実物の行番号は design.md §12-2 に書いた（origin/main 88c3fccd1 で読んだ）。
- 本番の数（読むだけの鍵・2026-11-25）: Google とつないだ会社は 2 社（tenant_001・tenant_004、どちらも両方向）。アプリで作って Google にもある予定は tenant_001 が 1 件（会社の予定・送り終えた）、tenant_004 が 4 件（自分だけ 3・会社 1・すべて送り終えた）。繰り返しの元の行と例外の行は全社で 0 件。
- 予定の表を読む所: `calendar_events` を読むのは `backend/app/services/calendar_service.py`・`backend/app/services/google_webhook.py`・`backend/app/services/calendar_recurrence.py`・`backend/app/services/tenant.py`（表の作り）と予定の画面だけ。画面へ返す一覧は `backend/app/services/calendar_service.py:247` で `NOT ce.is_cancelled` を付ける。繰り返しの回は例外の行（消した印も含む）があれば広げた回から外す（`:337-366`）。
- Google の公式の資料（Context7 `/websites/developers_google_workspace_calendar_api`・2026-11-25）:
  - 差分の取り込みでは消した予定が `status: "cancelled"` で必ず届く。消した単発の予定は `id` だけが保証される。消した回は `id`・`recurringEventId`・`originalStartTime` が保証される。
  - 予定を別のカレンダーへ移すと、元のカレンダーには「消した」と同じ形（`cancelled`・`id` だけ）が届く。消したのと見分けられない。
  - `originalStartTime` は回を一意に決め、回を動かしても変わらない。`singleEvents=true` の回には `recurrence` が付かない。
  - 1 回だけの直し・消しは例外の予定として持つ（取り消しは `status` に出る）。元の予定の `recurrence[]` は RRULE・EXRULE・RDATE・EXDATE の行の並び。
  - 「すべて」「これ以降」を回ごとの直しで済ませないよう公式が注意している（回ごとに直すと例外が大量にできる）。
- 分かっていないこと: Google の画面で「すべて」を消したとき、差分に元の予定 1 件が届くか、回ごとに届くか。どちらでも便4 は「アプリは今のまま」になるように作る（design.md §12-3）。

## 便4 改め（2026-11-25・DB の決まりと書き込みの照らし合わせ）

- 【事実】表の決まり: `backend/app/services/tenant.py:1579-1590`。`calendar_events_cancelled_exception_check` は `CHECK (((NOT is_cancelled) OR (recurring_event_id IS NOT NULL)))`（`:1583`）。消した印は繰り返しの例外の行だけに付けられる。
- 【事実】ほかに exception_pair（`:1585`）・recurrence_role（`:1586`）・recurring_event_id の参照 ON DELETE CASCADE（`:1587`）・source（`:1588`）・sync_status（`:1589`）・category（`:1579`）・color_key（`:1581`）・calendar_type（`:1582`）。
- 【事実】実装コミット 70451bf3c の単発の消しは `UPDATE calendar_events SET is_cancelled = true ... AND recurring_event_id IS NULL`（`backend/app/services/calendar_service.py:1466-1478`）。通る行は必ず決まりに外れる。
- 【事実】同じコミットの単発の戻し（`backend/app/services/calendar_service.py:1485`・`:1497`・`:1500-1502`）は、単発の行に印が付かないので通る行が無い。
- 【事実】回の例外の行の作り（`backend/app/services/calendar_service.py:1648`・`:1689` の `_insert_row` と `_adopt_google_instance` `:1566-1574`）は、例外の行の重なり禁止を前の読み（`:1636-1641`）で避けている。Google の id の重なり禁止（`uq_calendar_events_google_event_id`）は読んでいない。
- 【事実】取り込みの繰り返し（`backend/app/services/google_webhook.py:339-347`）に 1 件ずつの try は無い。1 件の DB の失敗で、その回の取り込み全体が止まる。sync_token も進まない。
- 【事実】アプリで単発の予定を消すとき（`delete_event` `backend/app/services/calendar_service.py:648-683`）は行を消してから Google を消す。
- 【事実】CI は本物の PostgreSQL の試験を回す（`.github/workflows/test.yml:238-245` で `RLS_TEST_DATABASE_URL`・`RLS_ADMIN_DATABASE_URL`）。`backend/tests/test_calendar_sync_tenant_reset_pg.py` が使う。70451bf3c の試験は偽の DB だけで、決まりは通していない。
- 【事実】`calendar_events` を指すほかの表は無い（参照は自分の表の recurring_event_id だけ）。行を消しても他の表は壊れない。（2026-11-27 追記: いまはチームとの対応表も指す。便5 の項を見る）

## 便5（2026-11-27・Google で繰り返しの「すべての予定」を消したとき）

- PO の依頼: 2026-11-27「1」（Google で毎週の予定を全部消したときに、アプリからも消えるようにする設計を作る）。
- 既存 ADR の確認: `git grep -il "recurringEventId\|すべて" origin/main -- docs/adr/` と `docs/adr/FEATURE-INDEX.md` で ADR-1075・ADR-1059 を確かめた。「Google で『すべて』を直した・消したらアプリは今のまま」は ADR-1075 改訂 2026-11-25（`docs/adr/ADR-1075-schedule-recurrence.md:27`）。「これ以降は UNTIL で切る」「すべては元の行を直す」は決定5（`:19`）。
- 【事実】実物（origin/main 65934286b）:
  - 取り込みの入口 `backend/app/services/calendar_service.py:1876-1923` の `upsert_from_google`。`:1904-1906` で `recurringEventId` がアプリで作った元の予定を指せば `_apply_app_instance_from_google` へ回す。`:1909-1912` でアプリで作った予定の id そのものなら `_update_app_origin_from_google` へ回す。
  - `_apply_app_instance_from_google`（`:1738-1873`）: `:1759-1772` で送り終えた繰り返しの元の行を読む。`:1778-1783` で Google の元の予定を `get_event` で 1 回だけ読む（読めなければ警告「Google の繰り返しの元の予定を読めませんでした」を残して None）。`:1784-1785` で `_same_series` が偽なら飛ばす。
  - `_same_series`（`:1692-1715`）: `:1698` で Google の元の予定が無い・`status` が `cancelled`・時間が無いときは偽。
  - `_update_app_origin_from_google`（`:1603-1679`）: `:1619-1633` の消した知らせは、送り終えた・繰り返しでない行（`recurrence_rule IS NULL AND recurring_event_id IS NULL`）だけを消す。元の予定の id そのものが消した形で届いても、元の行は消さない。
  - アプリで「すべての予定」を消すとき（`delete_recurring_event` `:1400`、`# all` は `:1487-1497`）: 例外の行の Google の id を先に読み、元の行を id で消して commit し、そのあと Google の例外の回と元の予定を消す。例外の行は外部キーで一緒に消える。
  - Google の元の予定を読む `backend/app/services/google_calendar.py:403-411` の `get_event`（`events().get`、失敗は RuntimeError）。
  - 取り込みの回し方 `backend/app/services/google_webhook.py:291-347`: 差分は `singleEvents: True`・`calendarId: "primary"`・`timeMax` なし（`:298-307`）。1 回の取り込みに 1 つの `series_cache`（`:336`）。結果は「Google 取り込み完了 (tenant, upserted, deleted, full)」（`:382`）。
  - Google で作った予定の消した知らせ（`backend/app/services/calendar_service.py:1915-1923`）は、`source='google'` の行だけを消し、行が無くても "deleted" を返す。
- 【事実】表のつながり（`backend/app/services/tenant.py`）: `calendar_events.recurring_event_id` は自分の表の `id` を ON DELETE CASCADE で指す（`:1613`）。チームとの対応表 `calendar_event_teams.event_id` も ON DELETE CASCADE（`:1635`、移行 `migrations/20261127_100000_add_calendar_team_share.sql:32`）。元の行を消すと、例外の行とチームの対応も一緒に消える。アプリで「すべて」を消すときと同じ。
- 【事実】本番の記録（Grafana の Loki、job=containerlogs、2026-11-26 15:10〜15:25 UTC、133 行）: 15:16:28 Google からの知らせ（webhook POST 200）→ 15:16:31 「Google 取り込み完了 (tenant=1, upserted=0, deleted=0, full=False)」。同じ時間に「繰り返しの元の予定」の警告は 0 行。だから `get_event` は失敗せずに返り、`_same_series` が偽になって飛ばした。
- 【事実】Google の公式の資料（Context7 `/websites/developers_google_workspace_calendar_api`・2026-11-26 に読んだ）: `get` は消した予定（`status: "cancelled"`）も返す。差分の取り込みでは消した予定が必ず届く。`showDeleted` と `singleEvents` が両方 true のときは、消した回だけが届き、元の繰り返しの予定は届かない。消した例外の回は `id`・`recurringEventId`・`originalStartTime` だけが保証される。
- 【推測】15:16 の `get_event` は `status: "cancelled"` の元の予定を返した。根拠は上の資料と、警告が 0 行で、元の予定はほかに変えていないこと。Google が返した中身は記録に出ないので見ていない。受け入れの基準 K-s1（本番）で確かめる。
- 【未確認】15:16 の差分に回が何件届いたか。取り込みは件数を記録しない。
- 【事実】本番の数（読むだけの鍵・2026-11-26 15:43Z の片付け後）: tenant_001 の予定の行は元からの 3 行だけ。繰り返しの元の行・例外の行は 0 行。
- 【事実】既存の試験 `backend/tests/test_calendar_service.py:2289-2304` の `test_series_changed_in_google_is_skipped` は、Google の元の予定が `cancelled` で回が「消していない」形（題名を直した回）のときに飛ばすことを確かめている。便5 は回も消した形のときだけ消すので、この試験はそのまま通る。
- 【事実】本物の PostgreSQL の試験 `backend/tests/test_calendar_sync_tenant_reset_pg.py` に、取り込みの書き込みの試験がある（`:560` 単発の消し、`:578` 回の消し・直し、`:612` Google の id の重なり）。

## 便6（2026-11-27・取り込みの「消した数」が膨らむ件）

- PO の依頼: 2026-11-27「1」（実際に消した行だけを数えるように直す。設計を出して承認をもらう）。
- 既存 ADR の確認: 取り込みの数え方を決めた ADR は無い（`git grep -il "upserted\|deleted=" origin/main -- docs/adr/` は 0 件・2026-11-27）。消す動きの決めは ADR-1059・ADR-1075 で、便6 は動きを変えない。
- 【事実】本番の記録（Loki・2026-11-27 06:31:33 UTC）: 便5 の本番の確かめで「Google 取り込み完了 (tenant=1, upserted=0, deleted=730, full=False)」。本番の読むだけの鍵で、消えた行はテストの元の行 id 10 と例外の行 id 11 の 2 行（06:31:51 UTC に 0 行）。tenant_001 に残る 3 行（id 1・2・3、11/3〜11/5 作成）は更新時刻が変わっていない。
- 【事実】実物（origin/main 218e4fc7c）:
  - `backend/app/services/calendar_service.py:1983-1992`: Google で作った予定の消した知らせは `source='google'` の行を消し、消した行が 0 でも "deleted" を返す。
  - ほかの "deleted" を返す所（`:1635`・`:1798`・`:1903`）は、行を消した・印を付けたときだけ返す。`:1893` は消した印の例外の行を 1 行作ったときに返す。
  - `backend/app/services/google_webhook.py:346-347`: "deleted" を 1 つ 1 つ数える。`:376` で upserted と deleted の和が 0 より大きければ予定の画面へ合図を出す。`:382` で記録に出す。
  - `:300` の差分は `singleEvents: True`。繰り返しを消すと、回が 1 つずつ消した形で届く。元の行を消した後の回は、`_is_app_origin` が偽になって `:1983-1992` へ落ちる。
- 【推測】730 は Google が消した形で送った回の数。Google が何回分まで送るかは確かめていない。数がどうであれ、消した行は 0 行。
- 【事実】`backend/tests/test_calendar_service.py:803-819` の `test_deletes_cancelled_event_only_google_rows` は、消した行の数を決めずに "deleted" を期待している。便6 で行の数を決めた試験へ直す。

## 便7（2026-11-28・アプリで消した繰り返しの 1 回が、Google への送りの失敗で戻る件）

- PO の依頼: 2026-11-28「３：…直したい」。成功条件 K1〜K5 と本番反映までの完走は 2026-11-28「1」で承認。
- 既存 ADR の確認: ADR-1075（繰り返し）・ADR-1059（取り込み）。送りの失敗のときの決めは無い。design.md §12-11 ① に「次の候補」として書かれている（`git grep -n "送り中にする" origin/main -- docs/handoff/calendar-two-way-sync/design.md`）。
- 【事実】実物（origin/main 702e1767f）:
  - `backend/app/services/calendar_service.py:1421-1424`: 前からある例外の行は `is_cancelled = true` だけ。sync_status は変えない。
  - `:1426-1440`: 新しい行は `_insert_row`（`:1090`）で source='app'・sync_status='pending'。送れても `:1451-1456` は id だけ書き、送り終えた印を付けない。
  - `:1458-1459`: 送りの失敗は警告「Google の回の取り消しに失敗」だけ。
  - `:1873`: 取り込みは、送り終えていない例外の行に触らず "skipped"。
  - `:1930-1938`: 送り終えた例外の行は、消していない形の回が届くと `is_cancelled = False` に戻す。
  - `:1774`: Google で「すべて」を消したとき、送り終えていない例外の行があると消さない。
  - `backend/app/services/google_calendar.py:492-511` `update_event` は失敗を `RuntimeError(...) from e` で包む（元の HttpError は `__cause__`）。`:527-573` `get_instance` は `showDeleted` を付けず、見つからなければ `RuntimeError("繰り返しの回が見つかりません")`。
  - `backend/app/services/google_webhook.py:234-278`: 取り込みは会社ごとの鍵（advisory lock 1059）の中で、接続を確かめ文脈を張り直してから Google を読む（`:300` 以降）。
  - DB の決まり: `migrations/078_create_calendar_events_tenant.sql:59-60` で sync_status は synced・pending・failed の 3 つ。
- 【事実】本番（2026-11-28）: Loki で 2026-11-07〜11-28 の「回の取り消しに失敗」は 0 行（取り込みの完了の記録は週に約 1,150〜1,225 行）。tenant_001 の例外の行は 0 行（ai_ro の窓・2026-11-28T04:53:08Z）。今は戻った回は無い。
- 【事実】Google の公式の資料（Context7・2026-11-28）: 410 "deleted" は「それ以上の動きは要らない」。`events.instances` の `showDeleted` は初期値が偽。
