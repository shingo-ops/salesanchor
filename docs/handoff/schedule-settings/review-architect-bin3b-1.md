# 設計の審査（architect）便3b 第1回

- 審査した物: `origin/release/schedule-settings-bin3b`（69967ed10）の `docs/handoff/schedule-settings/design-bin3b.md`
- 前提の設計: `origin/release/schedule-settings-bin3` の `docs/handoff/schedule-settings/design-bin3a.md`（便3a。実装中・未合流）
- 実物: `origin/main` 314eeef1e。親設計 `docs/handoff/schedule-settings/design.md` §7、要件 `docs/handoff/schedule-settings/requirements.md`
- 読むだけ。製品のコード・DB・本番・secrets には触れていない。

## 判定: REVISE

1. §1 の事実と行番号はほぼ実物と合い、列を既存の `calendar_owner_settings` に足す判断と、CHECK・FK・既定値の組み立ても書き込みの道と矛盾しない。
2. ただし画面側に、直さないと「チームを選ぶ」と「全員を開いた形」が正しく動かない所が2つある（R1・R2）。
3. 登録先の説明の取り違え・存在しない部品名・存在しない関数名（L1〜L6）は軽いが、実装役が迷うので直すとよい。

## 確認できた事実（合っていたもの）

| 設計の記述 | 実物 | 判定 |
|---|---|---|
| F1 `SchedulePageImpl.tsx:881` `useState<ScheduleView>("week")` | 同じ。`schedule-utils.ts:4` に5つの形 | 合う |
| F2 `SchedulePageImpl.tsx:1636` `weekStart={0}`、`CalendarView.tsx:68` 既定1、`calendarView.utils.ts:74` `0 \| 1` | 同じ | 合う |
| F3 `:970` と効果 `:986-990` | `:970` は `useState` の初期値（自分の鍵）、`:986-990` は空なら自分を選ぶ効果 | 合う |
| F4 `:1008` `addHours(start, 1)`、`calendarView.utils.ts:254-265` | 同じ。呼び出しは `CalendarView.tsx:390` のみ（他の使用は `CalendarView.test.tsx`） | 合う |
| F5 `:1019` `:1271` `addMeet: false`、`:1072`、`:876-879` | 同じ。ただし `:877` は `enabled: isTenantAdmin`（R2 参照） | 行は合う・事実が足りない |
| F6 `:1538` 歯車 | `(canManageOwners \|\| isTenantAdmin) &&` が `SchedulePageImpl.tsx:1538` 付近 | 合う |
| F7 `ScheduleSettingsPage.tsx:306-314` | 同じ | 合う |
| F8 `tenant.py:1649-1659` | `:1649-1660`（インデックス行が `:1661`）。ずれは1行 | ほぼ合う |
| F9 `tenant.py:530-548`、`calendar.py:282-293` | 同じ。`team_members.user_id` は `users.id`（`calendar_service.py:210-211` の `tm.user_id = :me`） | 合う |
| F10 `calendar.py:384-443`、`canManageOthers` `:629` | 同じ（ロスターの表を `s.user_id` で `cos` に結ぶ。`team_members` も `user_id` で結べる） | 合う |
| F11 `tenant.py:638-648`、`staff.py:574-610` | 未照合の範囲（論点に影響しない） | 未確認 |
| 件数 1169→1175 | main は `test_ai_cloud_views.py:486` で `== 1170`。便3aで 1170−2+1 = 1169。便3bで +6 = 1175 | 合う |
| 登録先 `run_all_migrations.sh:1495`、`rls_bootstrap.py:190`、`reference-allowlist.tsv:7` | 同じ（allowlist の行7が `20261024_100300_create_ai_cloud_views.sql`） | 合う |
| `stage1-column-class.tsv` の `calendar_owner_settings` 行 | `:579-580`（便3aが入れ替える行）。6列の形 | 合う |

## 見る点ごとの結果

### (2) 列を既存の表に足す判断
妥当。持ち主の鍵は `users.id`（`tenant.py:1649-1660` の `staff_id`→`public.users(id)`）で、`staff_ui_preferences` の `staff.id` とは違う（設計 §3-1・§7 の理由どおり）。書き手は列ごとに分かれる。PATCH 側の UPSERT は便3aの設計 §3-2 で `color_key` だけを SET する形なので、6列を触らない。新しい行ができるときは NOT NULL の既定値で全列が埋まる。

### (3) CHECK・FK・既定値と書き込みの道
- PUT preferences: 6列を全部書く。`open_owners` が `team` 以外なら `open_team_id=NULL`。矛盾なし。
- PATCH owners（便3a後）: `INSERT (staff_id, color_key)` のみ。他の列は既定値。矛盾なし。
- 移行: `ADD COLUMN IF NOT EXISTS … NOT NULL DEFAULT` は既存行に既定値が入る。CHECK と FK は名前で有無を見る。冪等。
- 雛形: `teams` は `tenant.py:530` で先に作られ、`calendar_owner_settings` は `:1649` なので FK を先に張れる。
- `team` と NULL の組を CHECK で縛らない理由（`ON DELETE SET NULL` と衝突する）は正しい。使っていないチームを後から選び続ける場合は画面側で `self` に戻す（B6）。
- 書き込み後の `commit` → `reset_tenant_context`（ADR-072）が §3-3 に書かれていない（L4）。

### (4) 受入 B1〜B9
試験で確かめられる。B5 の「API 422」は、ハンドラ直呼び（db を模擬）の試験では pydantic の検証が走らないので、本体モデルを作って `ValidationError` を見るか、TestClient で呼ぶかを指定したほうがよい（L5）。B6 の「画面の試験」は R1 の直しが入って初めて決まった結果になる。

### (5) 画面の金型
`SectionCard`・`SubMenu`・`SelectControl`・`TextFieldControl`・`Toggle`・`MultiSelect`・`ColorSwatchPicker` は `frontend/src/components/` にあり、`ScheduleSettingsPage.tsx:4-13` で読み込み済み。`SelectField`・`Switch` は `components/` に無い（L1）。`SegmentedToggle`・`Radio` もある。文字は `t()`、キーは `frontend/src/locales/ja.json`・`en.json`。

### (6) openapi・AI 分類・allowlist・`_REVIEWED`
- 契約ファイルは `frontend/api-contract/openapi.json`。設計の `frontend/src/lib/api/openapi.json` は実在しない（L2）。
- 理由の対: 表は `frontend/src/lib/apiErrorReason.ts:39`（`invalid_team_ids` まで）と `backend/tests/test_api_error_reason_sync.py` の一覧（`"invalid_team_ids"` が末尾）の両方。新しい `invalid_team` は両方に足す。文言キーは `apiError.*`（設計 §4-4 は `schedule` 配下と書いていて食い違う）（L3）。
- `_REVIEWED` は `backend/tests/test_tenant_loop_migration_guard.py` の1つの辞書で、キーが試験ファイル名（`rls_bootstrap.py`・`test_calendar_sync_tenant_reset_pg.py`・新しい試験）。設計 §3-2 の「2つの `_REVIEWED` の集合」は取り違え（L6）。

## R（直さないと作れない・壊れる）

### R1. 「全員／チーム」を開く最初の1回の条件が足りない（§4-2、§8）
設計 §4-2 は「owners と preferences が両方読めたとき最初の1回だけ `visibleOwnerIds` を決める」と書く。しかし:
- `team` の判断には `/calendar/teams`（`SchedulePageImpl.tsx:338` `useCalendarTeams()`）の読み込み完了が要る。teams が owners より後に来ると、1回きりの印が先に立ち、`self` に落ちて二度と直らない。B6 の試験が時機で割れる。
- `all`／`team` の判断は `canManageOwners = hasPermission("staff.view")`（`SchedulePageImpl.tsx:876`）を使うが、権限の読み込み中（`usePermissions().loading`、`frontend/src/hooks/usePermissions.ts:27`）は false になる。`SchedulePageImpl.tsx:874` は `loading` を受け取っていない。読み込み前に判断すると staff.view の人でも `self` に落ちる。`ScheduleSettingsPage.tsx:102` は `!permsLoading &&` で待っている。
- 一度適用した後に人が手で人の選択を変えた場合に上書きしない旨が、view だけ書かれていて owners に無い（owners は初期値が `[selfKey]` で、先に人が触れた場合の扱いが未定）。

直し方: `design-bin3b.md` §4-2「Whose events」に、「適用は permissions・owners・preferences、`team` のときは `/calendar/teams` も、すべて読み込めた時に1回。読み込み前は何もしない（今の自分だけの形のまま）。人が先に選択を変えていたら適用しない（view と同じ印を使う）」と書き足す。B6 に「teams が後から届いても `team` が効く」試験を1つ足す。

### R2. 設定ページで、チーム一覧と Meet の状態が管理者以外から読めない（§4-3、F5）
- `ScheduleSettingsPage.tsx:145` `useCalendarTeams({ enabled: isTenantAdmin === true })`。設計 §4-3 は「staff.view の人に『一つのチーム』の選択欄（`/calendar/teams`）を出す」と書くが、管理者でない staff.view の人は一覧が読み込まれず、選択欄が空になる。バックエンドは `calendar.py:282-293` でログイン済みなら誰でも読める。直し: 条件を「ログイン済み（`enabled` を渡さない、または権限の読み込み完了後は常に true）」にする、と設計に書く。
- `ScheduleSettingsPage.tsx:120-122` と `SchedulePageImpl.tsx:877` は `/google-calendar/status` を `enabled: isTenantAdmin` で読む。つまり `meet_available` が true になりうるのは今は管理者だけで、管理者でない人にはMeetの欄が出ない（F5 の「Google をつないだ本人だけ」に、この条件が抜けている）。設計 §4-3「Meet は `meet_available` が true のときだけ」は成り立つが、B7「管理者でない人は個人の区画だけ」の中に Meet が出ないことを明記し、`/google-calendar/status` の読み取り条件は変えない（変える場合は別の便）と書く。Meet が見えない人の PUT は、読み込んだ `auto_meet` の値をそのまま送る（欠けさせない）ことも書く。

## L（軽い指摘）

- L1. §4-3 の部品名: `SelectField`・`Switch` は `frontend/src/components/` に無い。実在するのは `SelectControl`（`components/Select.tsx`）と `Toggle`（`components/Toggle.tsx`）で、`ScheduleSettingsPage.tsx:11,13` が読み込み済み。そのまま書き換える。
- L2. §3-3 の契約ファイル: `frontend/src/lib/api/openapi.json` ではなく `frontend/api-contract/openapi.json`（便3a設計 §3-2 と同じ）。再生成の命令は便3aの `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`。
- L3. §3-3・§4-4 の `invalid_team` の文言: 画面の表 `frontend/src/lib/apiErrorReason.ts` と `backend/tests/test_api_error_reason_sync.py` の一覧の両方に足す。文言キーは `apiError.invalidTeam`（ja/en）で、§4-4 の「`schedule` 配下」は直す。既存の `invalid_team_ids`（`apiError.invalidTeamIds`）と別名なので名前の取り違えに注意。
- L4. §3-3 PUT: 書いた後は `commit` の後に `reset_tenant_context`（ADR-072）。便3aの PATCH と同じ形、と一行書く。
- L5. §5 B5: ハンドラ直呼びの試験では 422 にならない。`CalendarPreferences(...)` の `ValidationError` を見る形か TestClient の形かを指定する。DB の CHECK の拒否は実 PostgreSQL 試験（設計どおり）。
- L6. §3-2 の登録先の書き方を正す。実物:
  - `scripts/run_all_migrations.sh`（便3aの行の後）。
  - `backend/app/services/tenant.py` の雛形の列と、移行名のコメント（便3a設計 F10 の `:1632`）。
  - `backend/tests/rls_bootstrap.py:190` の対応表（件数1）。
  - `backend/tests/test_calendar_sync_tenant_reset_pg.py:56` の `_MIGRATIONS` の並び（`True`）。
  - `backend/tests/test_tenant_loop_migration_guard.py` の `_REVIEWED` は辞書。`rls_bootstrap.py` の集合（`:53` 付近）と `test_calendar_sync_tenant_reset_pg.py` の集合（`:74` 付近）に移行名を足し、新しい試験 `test_calendar_owner_preferences_pg.py` を `scoped` で1つ足す。「2つの `_REVIEWED`」は誤り。
  - `_TENANT = 981`（`test_calendar_team_share.py:37`）、979、978、989 は使用済み。未使用の番号を `rg '^_TENANT'` で確かめて選ぶ。
- L7. §4-2 `addMinutes`: `SchedulePageImpl.tsx:186` にあるのは非公開の `addHours(date, amount)` だけで、`addMinutes` は無い。足す（または `new Date(start.getTime() + minutes * 60000)`）と書く。
- L8. §5 の「`calendarView.utils` の試験」: そのファイルの試験は無く、`normalizeSelectedRange` は `frontend/src/components/CalendarView.test.tsx` で動く。新規ファイルか `CalendarView.test.tsx` に足すかを決める。`clickMinutes` の既定は 60（他の使用者を変えない）で正しい。
- L9. §4-3 の区画の初期位置: `ScheduleSettingsPage.tsx:129` の `useState<SectionKey>("google")`、`:91` の `SectionKey`、`:316-323` の `menuItems`。管理者でない人は「google」が無いので、最初の区画（`personal`）を初期値にし、`SectionKey` に `"personal"` を足す。拒否文（`:306-314`、`settingsPermissionRequired`）を消すとキーが未使用になる場合は ja/en から消すか判断する。
- L10. §8「画面が週から保存した形にちらつく」: 画面を開き直すたびに出る可能性がある（印が1回きりなので）。保存後に設定ページで `/calendar/preferences` を入れ替える（PUT の返りで `setQueryData` する）か、戻ったときに最新が先に使えることを B1 の試験に含める。`useApiQuery` の入れ替えの挙動は未確認。
