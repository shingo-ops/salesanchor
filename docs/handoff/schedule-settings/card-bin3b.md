# 実装カード schedule-settings 便3b — ひとりひとりの初期値（開いたときの形・週の始まり・予定の長さ・Meet・誰の予定を出すか）

> この文書は何か：スケジュール設定ページ整備の便3b（DB 変更あり）の作業指示書です。

- 設計: `docs/handoff/schedule-settings/design-bin3b.md`（設計審査の結果は §12。§1〜§10 が正。このカードは設計の範囲を変えない）
- 状態: 要件は PO 承認済み（2026-11-25「1」・G7）。実装・マージ・本番反映までの委任も同日
- 危険便: はい（`migrations/` と `scripts/run_all_migrations.sh` を触る。ADR-135/136 の GO は Opus が PR で記録する）
- 担当: 実装 Sonnet（クラウド）は push まで／PR 作成・審査・マージ Opus
- 前提: 便3a（`calendar_owner_settings` を `staff_id, color_key, updated_at` にする）が main に入っていること。設計の行番号は origin/main 314eeef1e 基準。便3a の後に行がずれていれば、同じ中身の行を探して使い、ずれを報告に書く
- 枝: 既存の `release/schedule-settings-bin3b`（設計文書とこのカードが入っている枝。便3a の合流後の main を Opus が merge で取り込んである。便3a は 2026-11-26 01:35Z に main へ合流・01:44Z に本番反映済み）。`bash scripts/new-worktree.sh release/schedule-settings-bin3b` で場所を作り、`git switch -C release/schedule-settings-bin3b origin/release/schedule-settings-bin3b`。clone のまま commit しない。その後 `git rev-list --count HEAD..origin/main` を流す。0 でなければ main は取り込まず `BLOCKED: main が先に進んだ` で返す（クラウドの決まり `scripts/agent-hooks/cloud/rules.md:15`。Opus が枝を取り直す）
- 触るファイル（これ以外は触らない）:
  1. `migrations/20261129_100000_owner_settings_preferences.sql`（新規）
  2. `scripts/run_all_migrations.sh`（登録 1 行。便3a の `20261128_100000_owner_color_key_drop_dead_columns.sql` の行の次）
  3. `backend/tests/rls_bootstrap.py`・`backend/tests/test_calendar_sync_tenant_reset_pg.py`・`backend/tests/test_tenant_loop_migration_guard.py`（便3a の commit 6a9b8fd15 が足したのと同じ場所に足す）
  4. `backend/app/services/tenant.py`（`calendar_owner_settings` の形と、その上の登録コメント）
  5. `backend/app/routers/calendar.py`
  6. `migrations/20261024_100300_create_ai_cloud_views.sql`・`scripts/migration-guard/reference-allowlist.tsv`・`docs/handoff/cloud-case-ai/stage1-column-class.tsv`・`backend/tests/ops/test_ai_cloud_views.py`
  7. `backend/tests/test_calendar_preferences_api.py`（新規）・`backend/tests/test_calendar_owner_preferences_pg.py`（新規・本物の PostgreSQL）・`backend/tests/test_calendar_owner_api.py`（名簿の `team_ids`）・`backend/tests/test_api_error_reason_sync.py`
  8. `frontend/src/features/schedule/useCalendarPreferences.ts`（新規）
  9. `frontend/src/pages/schedule/SchedulePageImpl.tsx`・`frontend/src/pages/schedule/ScheduleSettingsPage.tsx`・`frontend/src/pages/schedule/schedule-owner.ts`
  10. `frontend/src/components/CalendarView.tsx`・`frontend/src/components/calendarView.utils.ts`（`clickMinutes` だけ）
  11. `frontend/src/lib/apiErrorReason.ts`
  12. `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`・`frontend/src/pages/schedule/ScheduleSettingsPage.test.tsx`・`frontend/src/components/CalendarView.test.tsx`。名簿の擬似データの形が変わって落ちる既存の試験（例 `frontend/src/pages/schedule/SchedulePageCache.test.tsx`・`frontend/src/lib/query/batch3bPages.test.tsx`）は、擬似データに `team_ids` を足す直しだけしてよい。足したファイルは報告に全部書く
  13. `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`
  14. `frontend/api-contract/openapi.json`（自動生成。手で書かない）

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・03-file.md・04-worktree.md・05-pr.md・10-executor.md。照合: 場所は new-worktree.sh で作る（04）・PR は担当が作らない（05）・プレースホルダなし（00）・push は `git push -u origin HEAD`（04）・各段で `git log` を確かめる（00）。

## 発行前の点検（Opus）

| 点検 | 結果 |
|---|---|
| 設計と同じ範囲か | design-bin3b.md §3〜§5 の項目だけを変更1〜8 に割り当てた |
| 実物の行 | §1 F1〜F11 は第1回・第2回審査で origin/main 314eeef1e と照合済み |
| 本番の前提 | `calendar_owner_settings` は 5 社とも 0 行（便3a 反映前の読み取り 2026-11-25T18:14Z） |
| 設計審査 | §12 の記録のとおり（第2回 APPROVE） |
| 今の動きを変えない | 行が無い人は今と同じ（週・日曜・60 分・Meet なし・自分だけ）。B2 の試験 |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード schedule-settings 便3b の実行結果である」と書くこと。

## 変更1 移行と新しい会社の形

design §3-1・§3-2 のとおり。
- 形は便3a の `migrations/20261128_100000_owner_color_key_drop_dead_columns.sql` に倣う。全部屋 1 つの `DO`。`calendar_owner_settings` か `teams` が無い部屋は飛ばす。
- 会社を選ぶのは 1 か所だけ。1 行で `FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' LOOP` と書き、`WHERE` の直後に別の条件を挟まない。最後の確かめも同じループの中で行う。
- 6 列を `ADD COLUMN IF NOT EXISTS`（型・既定値は design §3-1 の表のとおり）。CHECK 4 つと FK `fk_calendar_owner_settings_open_team`（`teams(id) ON DELETE SET NULL`）は、`pg_constraint` で `conname` と `conrelid` を見て無いときだけ足す。
- 最後の確かめ: 6 列の型・CHECK 4 つ・FK が揃っていなければ `RAISE EXCEPTION`。
- 戻し方をコメントで書く（6 列を `DROP COLUMN IF EXISTS`。color_key には触れない）。
- `tenant.py`: `calendar_owner_settings` の形に 6 列と CHECK 4 つと FK を足す。移行と同じ字面。上の登録コメントにこの移行の名前。
- 登録 4 か所（上の 2・3）。`_REVIEWED` には新しい項 `test_calendar_owner_preferences_pg.py` を `scoped` で足す。

## 変更2 受け口

design §3-3 のとおり。
- `GET /calendar/preferences`・`PUT /calendar/preferences`。本体は `CalendarPreferences`（`Literal` で値を限る）。利用者の番号は `current_user.id` だけ。本体に利用者の欄を作らない。
- `open_owners == "team"` のとき `open_team_id` が使っているチームでなければ 422 `invalid_team`。team 以外なら `open_team_id` は NULL で保存。
- upsert の SET は 6 列と `updated_at` だけ。`color_key` を入れない。`await db.commit()` の直後に `await reset_tenant_context(db, tenant_id)`（ADR-072）。
- 便3a の `PATCH /calendar/owners/{user_id}` の upsert が 6 列に触れていないことを確かめる（触れていたら止めて報告）。
- `OwnerRosterItem` に `team_ids: list[int]`（使っているチームだけ・番号順）。
- `invalid_team` を `frontend/src/lib/apiErrorReason.ts`（`invalid_team_ids` の次）と `backend/tests/test_api_error_reason_sync.py` の一覧に足す。ja/en に `apiError.invalidTeam`。

## 変更3 AI 用の分類

design §3-4 のとおり。
- `migrations/20261024_100300_create_ai_cloud_views.sql` に 6 列を `allow` で足す（便3a が足した `color_key` の行の言い回しに倣う）。`:3` のコメントの件数と `backend/tests/ops/test_ai_cloud_views.py` の件数は、取り直した main の数 + 6（便3a の後なら 1175）。
- sha256 は `shasum -a 256 migrations/20261024_100300_create_ai_cloud_views.sql` の値を `scripts/migration-guard/reference-allowlist.tsv` の同じ行に写し、理由欄の末尾に `/ schedule-settings 便3b（個人の初期値）`。
- `docs/handoff/cloud-case-ai/stage1-column-class.tsv` に 6 行。

## 変更4 画面

design §4-1〜§4-3 のとおり。
- `useCalendarPreferences.ts`: `DEFAULT_CALENDAR_PREFERENCES` と `normalizePreferences`。画面側の既定値はここだけ。
- `SchedulePageImpl.tsx`: 開いたときの形（`changeViewByHand` で手の変更を 1 つにまとめる）・`weekStart={prefs.week_start}`・誰の予定（権限・名簿・初期値・team のときはチーム一覧が揃ってから 1 回だけ。手で変えた後は当てない）・`addMinutes`・`clickMinutes`・Meet は `meetAvailable && prefs.auto_meet`・歯車はいつも出す。
- `schedule-owner.ts`: `teamIds: number[]`（無ければ `[]`）。
- `CalendarView.tsx`: 新しい任意の値 `clickMinutes`（既定 60）を `normalizeSelectedRange` に渡す。ほかの使い手の動きは変えない。
- `ScheduleSettingsPage.tsx`: 断りの画面（`:306-314`）を外す。`personal` 節を先頭・最初に開く節にする。`useCalendarTeams()` を全員に。`GoogleStatus` に `meet_available?: boolean`。Meet の行は `meet_available` のときだけ。隠れているときは読んだ `auto_meet` をそのまま送る。保存ボタンは初期値を読めるまで押せない。保存後は `useInvalidateApi()(["calendar","preferences"])` を待ってから成功の文字。
- 部品は `components/` の金型だけ（`SectionCard`・`SelectControl`・`Toggle` など、すでに読み込まれているもの）。生の `select`/`input`・色の直書き・新しい CSS の色を足さない（ADR-144・ADR-067）。
- `settingsPermissionRequired` がどこからも使われなくなったら ja/en から消す。使われていれば残す。

## 変更5 文字

design §4-4。ja/en に同じキー。同じ言葉の既存キー（画面の形の名前・保存）は使い回し、使い回したキーを報告に書く。

## 変更6 openapi と台帳

- `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`。差分が新しい 2 つの道・`CalendarPreferences`・`team_ids` だけであることを `git diff frontend/api-contract/openapi.json` で確かめる。
- 台帳（`.claude-pipeline/active-work.d/`）は作らない・commit しない。台帳は Opus が PR の時に足す。

## 変更7 試験

design §5 のとおり。
- `test_calendar_preferences_api.py`: 行が無いときの既定値 5 つ・保存して返す・B5 は `CalendarPreferences(...)` を作って `ValidationError`・使っていないチームは 422 `invalid_team`・team 以外は `open_team_id` を NULL に・SQL は `current_user.id`・commit の後に `reset_tenant_context`。
- `test_calendar_owner_preferences_pg.py`（本物の PostgreSQL）: 便3a の形の部屋から 6 列を消して古い形に戻し、移行を 2 回流す。既存の行に既定値・CHECK が範囲外を拒む・チームを消すと `open_team_id` が NULL・A の保存で B が変わらない（B3）・色と初期値が互いに変えない（B4）。`CREATE TABLE` は書かない。先に `_ensure_public_users`。会社番号は `git grep -n "^_TENANT = " backend/tests` で使われていない番号。
- 名簿の `team_ids` は使っているチームだけ。
- 画面: design §5 の一覧（B1・B2・B6 (a)(b)(c)・B7・B8・設定ページの各点）。消える前提の既存試験 `ScheduleSettingsPage.test.tsx:128-131` と歯車の試験（`SchedulePageImpl.test.tsx:149` 付近）を新しい動きに書き直す。
- `CalendarView.test.tsx`: `clickMinutes` 30 で 30 分・無ければ 60 分。

## 確かめ

- `cd backend && python -m pytest tests/test_calendar_preferences_api.py tests/test_calendar_owner_preferences_pg.py tests/test_calendar_owner_api.py tests/test_calendar_owner_color_key.py tests/test_tenant_loop_migration_guard.py tests/ops/test_ai_cloud_views.py tests/test_api_error_reason_sync.py -q` の生の出力をファイルに残す。DB の要る試験が手元で流せなければ「CI で確かめる」と書く。
- `cd frontend && npx vitest run src/pages/schedule src/components/CalendarView.test.tsx src/lib/query/batch3bPages.test.tsx` の生の出力。
- `cd frontend && npx tsc --noEmit` と `npx eslint src/pages/schedule src/features/schedule src/components/CalendarView.tsx`。
- i18n の自己点検（`frontend/CLAUDE.md`）と `npm run check:i18n-missing-keys`。
- `git grep -n 'type="color"\|<select\|<input' frontend/src/pages/schedule/ScheduleSettingsPage.tsx` の結果を生のまま残す（0 件）。
- 提出前: `bash scripts/dev/check-before-submit.sh`。
- commit（`--no-verify` は使わない。分けてよい）→ `git log -1 --oneline`。
- `git push -u origin HEAD` → `git log origin/release/schedule-settings-bin3b -1 --oneline`。

## 停止する条件（BLOCKED: で返す）

- 触るファイル以外を変える必要が出た（上の 12 の擬似データの直しは除く）。
- 金型に無い部品が要る。
- 便3a の PATCH の upsert が 6 列に触れていた。
- 既存の試験が、この変更と関係なく落ちる。
- openapi の差分が上の範囲を超えた。
- main が先に進んでいた（上の件数が 0 でない）。

## 報告

- 冒頭に受領文。1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 本文に: 試験・型・lint・grep の生の出力のファイルの場所と末尾・push した commit・判断を要した点（事実のみ）
- 停止したときは: 停止した手順／最後に実行したコマンド／停止した理由の原文

## 委任の定型

- sleep は使わない。CI は待たない
- PR は作らない。main にマージしない。本番と倉庫の設定に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

END OF CARD
