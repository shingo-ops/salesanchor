# recon: 予定の画面を Google カレンダーに寄せる 段1（2026-11-04）

基準: `origin/main` 7d56ab771（worktree `release/schedule-gcal-alignment`）。行番号はこの時点。
PO の依頼（原文）:
- 「ある程度形にはなってきているのだがGoogle カレンダーに比べるとUI/UXは劣っているのでクローンに出来る？」
- 「画面から予定を作成するときのポップアップも見きれないようにしたい」
- 「googleカレンダーみたいにアプリからもgooglemeetの設定できるように出来る？」
- 「まず私だけで動作確認を行い、その後は全ユーザーが自分のGoogleアカウントを連携できるようにしたい」→ 2 段に分ける案に「1」
- 完成予定の見本（canvas: 週・月・一覧・操作と近道の 4 枚）に「1」

## 0. ADR の検索結果

`git grep -n -i -E "calendar|schedule|予定" docs/adr/FEATURE-INDEX.md` →
`docs/adr/FEATURE-INDEX.md:34` カレンダー / 予定 / Google カレンダー → **ADR-1057** ／ ADR-1018。

| ADR | 関係 |
|---|---|
| `docs/adr/ADR-1057-google-calendar-owner-only-sync.md` | 接続は会社で1つ。Google へ送るのはつないだ本人の予定だけ。段1の Meet もこの線の内側（本人の予定だけ）で作る。見直す条件「PO 以外の人が自分の Google をつなぎたいとき」＝段2 |
| `docs/adr/ADR-1059-google-calendar-import-owner-private.md` | 持ち主の Google の予定を `calendar_type='personal'` で取り込む。Meet の参加 URL を取り込みでも読むかに関係 |
| `docs/adr/ADR-1018-public-sensitive-tables-rls-staged.md` | `tenant_google_calendar_config` の RLS。段1では表の形を変えない |
| `docs/adr/ADR-027-ui-internationalization.md` | 画面の文字は全部 `t()` |
| `docs/adr/ADR-067-design-token-enforcement.md` | 色・大きさはトークン |
| `docs/adr/ADR-144-ui-component-governance.md` | 部品は `frontend/src/components/` の金型を先に使う |
| `docs/adr/ADR-135-release-stowaway-prevention.md`・`docs/adr/ADR-136-cc-bot-github-identity.md` | `migrations/` を含む便は PO の「GO #番号」まで main に入れない |

## 1. 小窓（作る・詳しく・直す）が画面から切れる

- `frontend/src/pages/schedule/SchedulePageImpl.tsx:122-144` `buildPopoverPosition`
  - `:123` `const width = 320;` `:124` `const height = 420;` `:125` `const margin = 12;`
  - `:142` `const top = clamp(anchor.top, margin, Math.max(margin, viewportH - height - margin));`
  - 高さを 420px と決め打ちして上下の位置を決める。実際の高さは測っていない。
- `frontend/src/pages/schedule.css:679-693` `.schedule-popover`
  - `:683` `max-height: min(var(--schedule-popover-max-h), calc(100vh - var(--space-6)));`
  - `:692` `overflow: auto;`（小窓全体が 1 つの箱として中で動く。見出しと保存ボタンも一緒に動く）
- `frontend/src/tokens.css:407` `--schedule-popover-max-h: 34rem;`（16px 換算で 544px）
- 作る小窓の欄（`SchedulePageImpl.tsx:285-410`）: 題名・種類・終日・社員にも見せる・開始日・開始時刻・終了日・終了時刻・場所・説明（4 行）。保存と取消は `:413-435` の下の帯。
- 事実から言えること: 決め打ち 420px より実物が高いと、置き場所の計算は 420px 分しか下を空けないため、下（保存ボタン側）が画面の外に出る。
- 【未確認】PO の画面で実際に何 px 切れているか。PO の画面の大きさは測っていない。

### 既にある金型

- `frontend/src/components/Popover.tsx:47-92` `calcPosition`: 出したあとの `offsetWidth`・`offsetHeight` で測り、画面の中に押し戻す（`:80-87`）。向きの反転はしない（`:79` のコメント）。測る前は見えなくする（`:110` `visible`）。押す相手（trigger）を子に持つ作りで、予定の小窓のように「押した場所の四角」だけを渡す使い方はできない（`:26-45` の props）。
- `frontend/src/components/Toggle.tsx:21`（全 41 行。中身は `<input type="checkbox">` `:27-31`）切替スイッチ（終日・社員にも見せるで使用済み `SchedulePageImpl.tsx:321`・`:336`）。
- `frontend/src/components/Modal.tsx`・`Drawer.tsx`・`ListRow.tsx`・`ContextMenu.tsx` がある。

## 2. 月の表示

- `SchedulePageImpl.tsx:755-` `ScheduleMonthGrid`。1 日に `dayEvents.slice(0, 3)` の 3 件まで（`:801`）。
- 予定の札（`:805-823`）: 背景が担当者の色（`:808` `style={{ background: ownerMeta.color ...}}`）、中に題名と種類の札（`:815-821`）。
- `frontend/src/pages/schedule.css:647-665` `.schedule-month__event`: 最後の span だけ `white-space: nowrap`（`:661-665`）。題名の span は折り返せる。
- 「+N件」（`:826-828`）は `<span className="schedule-month__more">`。押せない。文字は `frontend/src/locales/ja.json:3195` `"moreCount": "+{{count}}件"`。
- 色の意味: 週も月も、予定の箱の色は担当者の色（週 `:724`〜 `background: ownerMeta.color`）。種類は札で出す。見本の月表示は丸印の色を種類の色で描いたが、今の画面の意味（色＝担当者）と違う。→ design で「丸印＝担当者の色」に合わせる。

## 3. 表示の切り替えと期間

- `SchedulePageImpl.tsx:1179-1188` 日・週・月の 3 つ。`frontend/src/pages/schedule/schedule-utils.ts:1` `export type ScheduleView = "day" | "week" | "month";`
- 期間: `schedule-utils.ts:147-157` `toRangeStart`・`toRangeEnd`。一覧の表示は無い。
- 前後の移動: `SchedulePageImpl.tsx:1090-1096`（月は 1 か月、日は 1 日、週は 7 日）。

## 4. 操作（引っぱる・動かす・長さを変える・キーボード）

- 週・日の表: 空いた 1 時間の枠を押すと作る小窓（`SchedulePageImpl.tsx:703-709` `onSelectSlot`）。予定を押すと詳しく（`:726-729`）。
- 引っぱる・つかんで動かす・下の端で長さを変える・キーボードの近道は、どれも無い（`onPointerDown`・`onMouseDown`・`onKeyDown`・`addEventListener` は 0 件。`grep -n -E "onKeyDown|addEventListener|onMouseDown|onPointerDown|draggable"` の結果）。
- `frontend/package.json` に引っぱり用・近道用の外部部品は無い（`grep -n -E "floating-ui|popper|dnd|react-dnd|hotkeys"` 0 件）。
- 予定を直せる人: `SchedulePageImpl.tsx:1123-1125` `canEditSelected`（持ち主、または担当者を管理できる人）。シフトから来た予定は `source === "shift"`（`schedule-utils.ts:54`）。
- 予定を直す口: `PATCH /calendar/events/{id}`（`SchedulePageImpl.tsx:1053`）→ `backend/app/services/calendar_service.py:259-` `update_event`。Google に送ってある予定は Google も直す（`:309-318`）。
- 上の帯の虫めがねボタン（`SchedulePageImpl.tsx:1160-1167`）は `onClick` が無く、押しても何も起きない。

## 5. Google Meet

- 公式（Context7・Google Calendar API）: 予定を作る・直すときに `conferenceDataVersion=1` を付け、`conferenceData.createRequest = {requestId: 毎回ちがう文字, conferenceSolutionKey: {type: "hangoutsMeet"}}` を送ると Meet が付く。作成直後は `createRequest.status.statusCode` が `pending` のことがある。参加 URL は返ってきた予定の `hangoutLink`（と `conferenceData.entryPoints`）。予定を作るだけでは Meet は自動で付かない。そのカレンダーで Meet が使えるかは `calendars.get` の `conferenceProperties.allowedConferenceSolutionTypes`。
- `backend/app/services/google_calendar.py:41` `_SCOPES = ["https://www.googleapis.com/auth/calendar"]`（今の許可の範囲で Meet 付きの予定を作れる。新しい許可は要らない）。
- `google_calendar.py:377-389` `create_event` は `.insert(calendarId=calendar_id, body=event_body)`（`:385`）。`conferenceDataVersion` を渡していない。
- `google_calendar.py:392-404` `update_event` は `.patch(...)`（`:400`）。同じく渡していない。
- `backend/app/services/calendar_service.py:180-253` `create_event`: 先にアプリの表へ入れ（`:192-218`）、`sync_mode in ("bidirectional","write_only") and connected_by == user_id`（`:222`）のときだけ Google へ送る（`:224-240`）。返事から使うのは `id` だけ（`:228`）。
- `calendar_service.py:509-530` `_to_google_event_body`: 題名・開始・終了（Asia/Tokyo）・説明・場所だけ。
- `calendar_service.py:410-501` 取り込み（`upsert_from_google` は `:410` から）: 題名・説明・場所・時刻を入れる（`:449` `location = google_event.get("location")`）。`hangoutLink` は読まない。アプリで作った予定は取り込みで飛ばす（`:432` `_is_app_origin`）。
- 予定の表（会社ごと）`migrations/078_create_calendar_events_tenant.sql` に Meet の URL を入れる列は無い。`git grep -n -E "meet|hangout|conferenceData" backend/app frontend/src/pages/schedule` で Meet 関係は 0 件（`meeting_memo` などの別物だけ）。
- 接続状態の口 `backend/app/routers/google_calendar.py:238-264` `GET /google-calendar/status` は `connected`・`configured`・`calendar_id`・`connected_at` だけ。見ている人がつないだ本人かは返さない。本人判定は `backend/app/routers/google_calendar.py:155-178` `require_calendar_owner`（`connected_by_user_id` と `user.id` の比較）。
- 画面は管理者だけ接続状態を読む（`SchedulePageImpl.tsx:891` `useApiQuery<{ connected: boolean }>("/google-calendar/status", { enabled: isTenantAdmin })`）。
- 【未確認】本番の同期方式（`sync_mode`）の今の値。`write_only` 以外なら今でも Google へ送られない。
- 【未確認】つないだ Google アカウントで Meet を作れるか（無料アカウント・Workspace のどちらか、管理者が Meet を止めていないか）。

## 6. 色とトークン

- `frontend/src/tokens.css:393-417` 予定の画面のトークン（`--schedule-row-height: 48px` など）。
- `frontend/src/features/schedule/calendars.config.ts` 種類の色が直書き（既知の残件。今回は触らない）。

## 7. 試験の置き場所

- `frontend/src/pages/schedule/schedule-utils.test.ts`・`frontend/src/pages/schedule/SchedulePageImpl.test.tsx`・`frontend/src/pages/schedule/SchedulePageCache.test.tsx`
- 裏側: `git grep -l -E "ADR-1057|connected_by" backend/tests` は 10 件ヒットしたが、予定の作成と Google 送信を直接試す試験の名前はこの検索では特定できていない。【未確認】→ 便3 の実装カードで担当に探させ、無ければ新しく作る。
