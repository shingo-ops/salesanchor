# 設計の審査（architect）便3b 第2回

- 審査した物: `origin/release/schedule-settings-bin3b`（bc929f930）の `docs/handoff/schedule-settings/design-bin3b.md`（204行）
- 第1回の結果: `origin/release/schedule-settings-bin3b-review1` の `docs/handoff/schedule-settings/review-architect-bin3b-1.md`
- 前提: `origin/release/schedule-settings-bin3` の `design-bin3a.md`。実物: `origin/main` 314eeef1e
- 読むだけ。製品のコード・DB・本番・secrets には触れていない。

## 判定: APPROVE

1. 第1回の R1・R2 と L1〜L10 は、設計に正しく入っている（下の表。12件すべて○）。実物の行・部品名・ファイルと照らして食い違いはなかった。
2. 直しで生まれた書き方（§4-2「全部読めたら1回・手で変えたら適用しない」、§4-3 のチーム一覧、Meet の値を保つ PUT）は、実物の上で実装できる形で、他の区画の挙動も変えない（下の「見る点 (2)」）。
3. 直さないと作れない・壊れる物（R）は無い。軽い指摘 L1〜L7 は実装役が迷わないための補足で、実装中に拾える。

## (1) 第1回の指摘が設計に入ったか

| 第1回 | 設計での入り方 | 実物との照合 | 判定 |
|---|---|---|---|
| R1 最初の1回の条件 | §4-2「Whose events」: permissions・owners・preferences、`team` のときは teams が揃うまで何もしない。手で変えたら適用しない。B6 (b)(c) | 権限の `loading` は `frontend/src/hooks/usePermissions.ts:27`、`SchedulePageImpl.tsx:874` は今 `loading` を受けていない（設計が「今は読んでいない」と書くとおり）。チーム一覧は `SchedulePageImpl.tsx:338` の `useCalendarTeams()` が返す `isLoaded`（`frontend/src/features/schedule/useCalendarTeams.ts:34-39`）で判断できる。手で変える入口は選択の `toggleOwner`（`SchedulePageImpl.tsx:1222-1228`）の1つだけで、印を立てられる | ○ |
| R2 チーム一覧 | §4-3 `useCalendarTeams()` を引数なしに | `SchedulePageImpl.tsx:338` が既に引数なしで全員に読ませている。`ScheduleSettingsPage.tsx:145` の `enabled: isTenantAdmin === true` を外すだけ。バックエンドは `calendar.py:282-293` で誰でも読める | ○ |
| R2 Meet | §4-2・§4-3・B7 で「`/google-calendar/status` は管理者だけの読み取りのまま」「隠れているとき PUT は読み込んだ `auto_meet` をそのまま送る」 | `SchedulePageImpl.tsx:877`、`ScheduleSettingsPage.tsx:120-122` ともに `isTenantAdmin` 条件 | ○ |
| L1 部品名 | `SelectControl`・`Toggle` | `ScheduleSettingsPage.tsx` が読み込み済み | ○ |
| L2 契約ファイル | `frontend/api-contract/openapi.json` と再生成の命令 | 便3a設計と同じ | ○ |
| L3 `invalid_team` | `apiErrorReason.ts` と `test_api_error_reason_sync.py` の両方、`apiError.invalidTeam` | 設計 §3-3・§4-4 で食い違いなし | ○ |
| L4 commit→reset | §3-3 PUT に明記 | 便3a設計 §3-3 の PATCH と同じ形 | ○ |
| L5 B5 | `CalendarPreferences(...)` の `ValidationError` を見る | ハンドラ直呼びでは本体検証が走らない点に合う | ○ |
| L6 登録先 | §3-2 に `run_all_migrations.sh`・`rls_bootstrap.py`・`test_calendar_sync_tenant_reset_pg.py`・`test_tenant_loop_migration_guard.py`（辞書の1キー＋2つの集合）・雛形 | 第1回の実物と一致。`_TENANT` は実装役が `git grep` で選ぶ旨も入っている | ○ |
| L7 `addMinutes` | §4-2 で新設と明記 | `SchedulePageImpl.tsx:186` は `addHours` のみ | ○ |
| L8 `normalizeSelectedRange` の試験 | `CalendarView.test.tsx` に足す（§5） | 実物の使用は `CalendarView.tsx:390` のみ、`clickMinutes` 既定 60 で他を変えない | ○ |
| L9 区画の初期位置 | §4-3 `SectionKey` に `personal`、先頭、初期値 | `ScheduleSettingsPage.tsx:91,129,316-323` | ○ |
| L10 ちらつき | §8 と §4-3「保存の後に `useInvalidateApi()(["calendar","preferences"])` を `await`」 | 写しの名前は `["api", uid, "calendar", "preferences", {query}]`（`frontend/src/lib/query/apiQuery.ts:42-45`）。前の言葉が同じ物を取り直す（`:105-110`）。設定画面が同じ `useApiQuery` を持っていれば「使っている写し」なので取り直される | ○ |

## (2) 直しで新しい食い違い・作れない所はないか

- **§4-2 の「全部読めたら1回だけ・手で変えたら適用しない」**: 実装できる。選択を変える所は `SchedulePageImpl.tsx:989`（空のときだけ自分を入れる効果）と `:1224`（`toggleOwner`）の2つだけ。`:989` は「空のときだけ」なので、適用後の選択を壊さない。適用は「すべて揃った・まだ適用していない・手で触っていない」の3つを見る効果1つで書ける。
- **§4-3 のチーム一覧を全員に**: `SchedulePageImpl.tsx:338` が既に全員で読んでいるので、実際の通信は増えない。設定画面で他に `teamOptions` を使うのは種類の区画（管理者だけ）。既存の試験は、書いていない道を `[]` で返す（`ScheduleSettingsPage.test.tsx:42-43,66`）ので、`/calendar/teams` と `/calendar/preferences` が増えても落ちない。`/calendar/preferences` の応答が `[]` のときは §4-1 の `normalizePreferences` が既定値に直す（設計どおり）。
- **Meet の値を保つ PUT**: 設定画面の形が読み込んだ6つの値を持っていれば、隠れた欄の値もそのまま送れる。実装できる。
- **設定画面の他の動き**: 戻りの帯（`?connected=`、`ScheduleSettingsPage.tsx:228-244`）は区画に依らず出るので、初期区画を `personal` にしても壊れない。`jumpToSection` は `scrollIntoView` で各区画は縦に並ぶ形。`personal` に `schedule-settings-personal` の id を付ける。
- **便3a との整合**: `color_key` は NULL 可（便3a設計 §3-1。`color_key text`）なので、PUT preferences が新しい行を作っても通る。移行名 `20261129_…` は 3a の `20261128_…` の後で、実物の最新は `migrations/20261127_100000_add_calendar_team_share.sql`。件数 1169→1175 も 3a設計 `:141` と合う。

## (3) B1〜B9 が試験で確かめられるか

B1〜B9 はいずれも、書かれた試験（§5）で確かめられる。B3・B4・B5 の DB 側は実 PostgreSQL 試験、B5 の API 側は本体モデルの `ValidationError`、B6 (a)(b)(c) と B7・B8 は `SchedulePageImpl.test.tsx`・`ScheduleSettingsPage.test.tsx` の模擬の差し替え（`perms.loading` など既存の仕組み）で作れる。B9 は CI の検査。

## L（軽い指摘。作る途中で拾える）

- L1. 既存の試験を直す指示が §5 に無い。便3bで落ちるもの: `frontend/src/pages/schedule/ScheduleSettingsPage.test.tsx:124-130`（管理者でも `staff.view` でもない人に拒否文を出す試験。拒否を無くすので「個人の区画だけ出る」へ書き換える）。`SchedulePageImpl.test.tsx:149` 付近の歯車の試験も、一般の人に歯車が出ない試験があれば反転する。設計 §5 に「拒否文の試験を書き換える」と一行足すとよい。
- L2. 設定画面の `GoogleStatus` 型（`ScheduleSettingsPage.tsx:93-96`）に `meet_available` が無い。Meet の欄を `meet_available` で出すには、型に足す（`SchedulePageImpl.tsx:877` の型と同じ形）。
- L3. `team_ids` を画面の持ち主型に通す道が書かれていない。`ApiCalendarOwnersResponse` と `CalendarOwner`（`buildSchedule`／`normalizeOwner`）に `teamIds` を足し、未知なら空の配列にする。§4-2 の `team` の規則はこれを読む。
- L4. 保存ボタンは「読み込み完了」まで押せなくする（`/calendar/preferences` が取れる前や失敗時に押すと、既定値で保存済みの値を上書きする）。設計 §4-3 に一行。
- L5. 最初の1回の適用は、写し（古い取得）が「読めた」ことになるので、チームの所属が変わった直後に古い `team_ids` で適用する可能性がある。1回きりの設計の範囲内（次に開けば直る）。§8 に一行書いてあれば足りる。
- L6. 見を変える入口は `setView` が複数ある（`SchedulePageImpl.tsx:1421-1425` のキー、`:1576`、`:1650`）。§4-2 の「手で変えた印」は、`setView` を包む関数1つにまとめてから使うと取りこぼさない。
- L7. 件数の「1175」は 3a が先に main に入った後の数。3a の合流が遅れて数が変わったら、実装役が `test_ai_cloud_views.py:486` の実数から 6 を足して書く（設計 §3-4 は「after 3a」と書いていて矛盾はない）。
