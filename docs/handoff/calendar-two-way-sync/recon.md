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
