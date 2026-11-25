# 実装カード schedule-settings 便2b — 予定の共有に「チーム」を足す

> この文書は何か：スケジュール設定ページ整備の便2b（DB 変更あり）の作業指示書です。

- 設計: `docs/handoff/schedule-settings/design-bin2b.md` 第3版（設計審査 第3回 APPROVE。§1〜§8 が正。このカードは設計の範囲を変えない）
- 状態: 要件は PO 承認済み（2026-11-25「1」・G4〜G6）。実装・マージ・本番反映までの委任も同日。設計審査の記録は `review-architect-bin2b-*.md`
- 危険便: はい（`migrations/` と `scripts/run_all_migrations.sh` を触る。ADR-135/136 の GO は Opus が PR で記録する）
- 担当: 実装 Sonnet（クラウド）は push まで／PR 作成・審査・マージ Opus
- 枝: 既存の `release/schedule-settings-bin2b`（設計文書が入っている枝）。`bash scripts/new-worktree.sh release/schedule-settings-bin2b` で場所を作り、`git switch -C release/schedule-settings-bin2b origin/release/schedule-settings-bin2b`。clone のまま commit しない。始める前に `git merge --no-edit origin/main` で main を取り込む（便2a の合流 56419ebfa より後の main が要る）
- 触るファイル（これ以外は触らない）:
  1. `migrations/20261127_100000_add_calendar_team_share.sql`（新規）
  2. `scripts/run_all_migrations.sh`（登録 1 行。`20261126_100000_create_calendar_categories.sql` の次）
  3. `backend/tests/rls_bootstrap.py`・`backend/tests/test_calendar_sync_tenant_reset_pg.py`・`backend/tests/test_tenant_loop_migration_guard.py`（登録。便2a の `20261126_100000` の行に倣う）
  4. `backend/app/services/tenant.py`（新しい会社の形: 2 つの表・CHECK の名前を明示）
  5. `backend/app/services/calendar_service.py`
  6. `backend/app/services/calendar_categories.py`
  7. `backend/app/routers/calendar.py`
  8. `backend/app/realtime/topics.py`（試験が要るときだけ）
  9. `backend/tests/test_calendar_team_share.py`（新規）・`backend/tests/test_calendar_categories.py`・`backend/tests/test_calendar_service.py`・`backend/tests/test_calendar_recurrence.py`・`backend/tests/test_calendar_owner_api.py`（既存の試験が新しい形で落ちるときだけ）
  10. `backend/tests/test_api_error_reason_sync.py`・`frontend/src/lib/apiErrorReason.ts`（`invalid_team_ids` だけ）
  11. `migrations/20261024_100300_create_ai_cloud_views.sql`（分類 1 行）・`scripts/migration-guard/reference-allowlist.tsv`（sha256 と理由）・`docs/handoff/cloud-case-ai/stage1-column-class.tsv`（1 行）・`backend/tests/ops/test_ai_cloud_views.py`（件数を main の今の値＋1）
  12. `frontend/src/features/schedule/useCalendarCategories.ts`・`useCalendarTeams.ts`（新規）・それぞれの試験（任意）
  13. `frontend/src/pages/schedule/schedule-utils.ts`・`SchedulePageImpl.tsx`・`ScheduleDraftFields.tsx`・`ScheduleSettingsPage.tsx`
  14. `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`・`ScheduleSettingsPage.test.tsx`・`SchedulePageCache.test.tsx`（擬似が要るときだけ）・`schedule-utils.test.ts`（型が変わるときだけ）
  15. `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`
  16. `frontend/api-contract/openapi.json`（自動生成。手で書かない）
  17. `.claude-pipeline/active-work.d/release-schedule-settings-bin2b.md`（台帳・新規）

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・03-file.md・04-worktree.md・05-pr.md・10-executor.md。照合: 場所は new-worktree.sh で作る（04）・PR は担当が作らない（05）・プレースホルダなし（00）・push は `git push -u origin HEAD`（04）・各段で `git log` を確かめる（00）。

## 発行前の点検（Opus）

| 点検 | 結果 |
|---|---|
| 設計と同じ範囲か | design-bin2b.md §3〜§5 の項目だけを変更1〜8 に割り当てた |
| 実物の行 | §1 F1〜F21 は第1〜3回審査で照合済み |
| 本番の前提 | 5 社とも CHECK の名前は `calendar_events_calendar_type_check`・`calendar_categories_default_share_check`（F15）。`personal` で `user_id` が NULL は 0 件（F21） |
| 設計審査 | 第1回 REVISE → 第2回 REVISE → 第3回（`review-architect-bin2b-3.md`） |
| 見え方を変えない | 今ある予定の見え方は B7 の試験で前後同じ |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード schedule-settings 便2b の実行結果である」と書くこと。

## 変更1 移行と新しい会社の形

design §3-1・§3-2 のとおり。
- 移行は `migrations/20261126_100000_create_calendar_categories.sql` の形に倣う。全部屋 1 つの `DO`・`calendar_events` か `teams` が無い部屋は飛ばす。
- CHECK の入れ替えは §3-2 の 1〜4 の順（仮の名前 `_v2` → `VALIDATE` → 古いものを `pg_get_constraintdef` で探して全部消す → 名前を戻す）。最後の確かめで外れたら `RAISE EXCEPTION`。
- `tenant.py`: 2 つの表を `calendar_events`・`calendar_categories`・`teams` より後に。CHECK は `CONSTRAINT <名前> CHECK (...)` で名前を明示。RLS は付けない（§3-1）。
- 登録 4 か所（`run_all_migrations.sh`・`rls_bootstrap.py`・`test_calendar_sync_tenant_reset_pg.py`・`test_tenant_loop_migration_guard.py`）。

## 変更2 AI 用の分類

design §3-2 の最後の項のとおり。`calendar_category_teams.category_key` だけ `mask`（`calendar_categories.key` と同じ理由の文）。件数は `git show origin/main:backend/tests/ops/test_ai_cloud_views.py` の今の値＋1。sha256 は `shasum -a 256 migrations/20261024_100300_create_ai_cloud_views.sql` の値を写す。

## 変更3 見え方の正本

design §3-3 のとおり。
- `SHARE_VALUES`・`visibility_sql()`・`can_see_event()`・`set_event_teams()`・`validate_team_ids()` を `calendar_service.py` に置く。
- 呼ぶ場所は §3-3 の 5 つ（作る・単発の直す・「すべて」・単発→繰り返し・「これ以降」）。どれも「早く返る所の前・commit の前」。「この予定だけ」は書かず、違うときだけ 422。
- `team_ids` の扱いは §3-3「直すときの決まりの表」の 6 行のとおり。
- `list_events` の変数 `visibility_sql` は `vis_where` に名前を変える（`:240-246`・`:344-347`）。説明文 `:207-209` を直す。
- 書いたあとは `await db.commit()` の直後に `await reset_tenant_context(db, tenant_id)`（ADR-072）。

## 変更4 受け口

design §3-4 のとおり。`GET /calendar/teams` は名前と番号だけ。種類の `CATEGORY_SHARE_VALUES` と `default_team_ids`・`set_category_teams`。`invalid_team_ids` を理由の表へ。

## 変更5 画面

design §4-1〜§4-3 のとおり。金型は `SelectControl`（`variant="editor-filled"`）・`MultiSelect`（予定の画面 `layout="inline"`・設定ページ `layout="popover"`）と既存の部品だけ。生の button/select/input・色の直書き・新しい CSS の色を足さない（ADR-144・ADR-067）。`useApiQuery`・`useInvalidateApi`（`frontend/src/lib/query/apiQuery.ts`）を使い、react-query の鍵を手で書かない。「この予定だけ」のときは `team_ids` を送らない。

## 変更6 文字

design §4-4。ja/en に同じキー。使わなくなるキーは両方から消す。

## 変更7 openapi と台帳

- `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`。差分は `/calendar/teams`・予定の作る・直すの `team_ids`・予定の返す `team_ids`・種類の `default_team_ids` と `default_share` の値だけであることを `git diff frontend/api-contract/openapi.json` で確かめる。
- 台帳 `release-schedule-settings-bin2b.md` を `release-schedule-settings-bin2a.md`（main にあるもの）と同じ形で、状態 `IN_PROGRESS`・PR# 空で作る。

## 変更8 試験

design §5 のとおり（本物の PostgreSQL の試験は `backend/tests/test_calendar_team_share.py`）。既存の `switch` を使う画面の試験（`SchedulePageImpl.test.tsx:171`・`:1047`・`:1403`・`:1433`）は `combobox` に直す。

## 確かめ

- `cd backend && python -m pytest tests/test_calendar_team_share.py tests/test_calendar_categories.py tests/test_calendar_service.py tests/test_calendar_recurrence.py tests/test_calendar_owner_api.py tests/test_google_calendar.py tests/test_api_error_reason_sync.py -q` の生の出力をファイルに残す。DB の要る試験が手元で流せなければ「CI で確かめる」と書く。
- `cd frontend && npx vitest run src/pages/schedule src/features/schedule src/components/ToggleMigration.test.tsx src/lib/query/batch3bPages.test.tsx` の生の出力。
- `cd frontend && npx tsc --noEmit` と `npx eslint src/pages/schedule src/features/schedule`。
- i18n の自己点検（`frontend/CLAUDE.md`）。
- B8 の 4 つの `git grep`（design §2）の結果を生のまま残す。
- 提出前: `bash scripts/dev/check-before-submit.sh`。
- commit（`--no-verify` は使わない。分けてよい）→ `git log -1 --oneline`。
- `git push -u origin HEAD` → `git log origin/release/schedule-settings-bin2b -1 --oneline`。

## 停止する条件（BLOCKED: で返す）

- 触るファイル以外を変える必要が出た。
- 「直すときの決まりの表」どおりに書けない道がある。
- 既存の試験が、この変更と関係なく落ちる。
- 金型に無い部品が要る。
- openapi の差分が上の範囲を超えた。
- main の取り込みで衝突した。

## 報告

- 冒頭に受領文。1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 本文に: 試験・型・lint・grep の生の出力のファイルの場所と末尾・push した commit・判断を要した点（事実のみ）
- 停止したときは: 停止した手順／最後に実行したコマンド／停止した理由の原文

## 委任の定型

- sleep は使わない。CI は待たない
- PR は作らない。main にマージしない。本番と倉庫の設定に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

END OF CARD
