# 実装カード schedule-settings 便2a — 予定の種類を DB の表 1 つへ（色・共有の初期値）

> この文書は何か：スケジュール設定ページ整備の便2a（DB 変更あり）の作業指示書です。

- 設計: `docs/handoff/schedule-settings/design-bin2a.md` 第3版（設計審査 第2回 APPROVE。§1〜§6 が正。このカードは設計の範囲を変えない）
- 状態: 要件は PO 承認済み（2026-11-25「1」）。実装・マージ・本番反映までの委任も同日。設計審査の記録は `review-architect-bin2a-*.md`
- 危険便: はい（`migrations/` と `scripts/run_all_migrations.sh` を触る。ADR-135/136 の GO は Opus が PR で記録する）
- 担当: 実装 Sonnet（クラウド）は push まで／PR 作成・審査・マージ Opus
- 枝: 既存の `release/schedule-settings-bin2a`（設計文書が入っている枝）。`bash scripts/new-worktree.sh release/schedule-settings-bin2a` で場所を作る。clone のまま commit しない
- 触るファイル（これ以外は触らない）:
  1. `migrations/20261126_100000_create_calendar_categories.sql`（新規）
  2. `scripts/run_all_migrations.sh`（登録 1 行）
  3. `backend/tests/rls_bootstrap.py`・`backend/tests/test_calendar_sync_tenant_reset_pg.py`・`backend/tests/test_tenant_loop_migration_guard.py`（登録。F10 の 5 行に倣う）
  4. `backend/app/services/tenant.py`（新しい会社の形）
  5. `backend/app/services/calendar_categories.py`（新規）
  6. `backend/app/services/calendar_service.py`（種類を通す 5 か所だけ）
  7. `backend/app/routers/calendar.py`
  8. `backend/tests/test_calendar_categories.py`（新規）・`backend/tests/test_calendar_service.py`・`backend/tests/test_calendar_recurrence.py`・`backend/tests/test_calendar_sync_tenant_reset_pg.py`（移行の試験を足す場合）
  9. `migrations/20261024_100300_create_ai_cloud_views.sql`（分類 3 行と `:3` の注記）・`scripts/migration-guard/reference-allowlist.tsv`（`:7` の sha256 と理由）・`docs/handoff/cloud-case-ai/stage1-column-class.tsv`（4 行）・`backend/tests/ops/test_ai_cloud_views.py`（件数 1169 と分類の試験 1 つ）
  10. `frontend/src/features/schedule/calendars.config.ts`・`calendars.config.test.ts`（消す）
  11. `frontend/src/features/schedule/useCalendarCategories.ts`（新規）・`useCalendarCategories.test.ts`（新規・任意）
  12. `frontend/src/pages/schedule/ScheduleDraftFields.tsx`・`SchedulePageImpl.tsx`・`schedule-utils.ts`・`ScheduleSettingsPage.tsx`
  13. `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`・`ScheduleSettingsPage.test.tsx`・`SchedulePageCache.test.tsx`（`/calendar/categories` の擬似が要るときだけ）・`schedule-utils.test.ts`（型が変わるときだけ）
  14. `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`
  15. `frontend/api-contract/openapi.json`（自動生成。手で書かない）
  16. `.claude-pipeline/active-work.d/release-schedule-settings-bin2a.md`（台帳・新規）

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・03-file.md・04-worktree.md・05-pr.md・10-executor.md。照合: 場所は new-worktree.sh で作る（04）・PR は担当が作らない（05）・プレースホルダなし（00）・push は `git push -u origin HEAD`（04）・各段で `git log` を確かめる（00）。

## 発行前の点検（Opus）

| 点検 | 結果 |
|---|---|
| 設計と同じ範囲か | design-bin2a.md §3〜§5 の項目だけを変更1〜8 に割り当てた |
| 実物の行 | §1 F1〜F14 は第1回審査と Opus の読み直し（2026-11-25）で照合済み |
| 本番の前提 | 5 社とも `calendar_events_category_check`（F9・読むだけの鍵） |
| 設計審査 | 第1回 REVISE → 第2回 APPROVE（`review-architect-bin2a-2.md`）。第2回の推奨は設計 第3版に入れた |
| 見え方を変えない | 変更3 は `calendar_service.py:238-250` に触れない（A9） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード schedule-settings 便2a の実行結果である」と書くこと。

## 変更1 移行と新しい会社の形

design §3-1・§3-2 のとおり。
- 移行は `migrations/20261119_120000_add_calendar_events_color_key.sql` の形に倣い、部屋ごとに 1〜5 の順。7 行は `ON CONFLICT (key) DO NOTHING`。外部キーは `pg_constraint` に無いときだけ `NOT VALID` で足して `VALIDATE`。最後に「`category` を使う CHECK が残れば `RAISE EXCEPTION`」。
- 24 色の並びは `tenant.py` の `calendar_events_color_key_check` と同じ文字の並びを写す（`event_colors.py` と一致すること）。
- `tenant.py`: `calendar_categories` と 7 行を `calendar_events` より前、CHECK の行を外部キーへ、関数 `set_updated_at_calendar_categories()` とトリガ `trg_calendar_categories_updated_at` を `:2139`・`:2241` と同じ形で。`:1577` のコメントを直す。
- 登録 5 行（run_all_migrations.sh は今の末尾 `20261122_100000` の後・`mr_report_summary` の前）。

## 変更2 AI 用の分類

design §3-2 の「AI 用の写しの分類」のとおり。sha256 は `shasum -a 256 migrations/20261024_100300_create_ai_cloud_views.sql` の値を写す。分類の試験は `test_t10_calendar_color_key_is_classified_on_bootstrapped_db`（`test_ai_cloud_views.py:1017-`）と同じ形。

## 変更3 裏側

design §3-3・§3-4 のとおり。サービスの 5 か所（F5）以外の `calendar_service.py` の行を変えない。書いたあとは `await db.commit()` の直後に `await reset_tenant_context(db, tenant_id)`（ADR-072）。

## 変更4 画面の種類の正本

design §4-1 のとおり。`useApiQuery`・`useInvalidateApi`（`frontend/src/lib/query/apiQuery.ts`）を使い、react-query の鍵を手で書かない。

## 変更5 種類を選ぶと初期値

design §4-2 のとおり。色と共有は作るときだけ入れる。

## 変更6 設定ページの区画

design §4-3 のとおり。金型は `SubMenu`・`SectionCard`・`TextFieldControl`・`ColorSwatchPicker`・`SelectControl`・`Toggle`・`Button` と、便1 の帯の部品だけ。生の button/select/input・色の直書き・新しい CSS の色を足さない（ADR-144・ADR-067）。

## 変更7 文字

design §4-4。ja/en の `schedule` に同じキー。使わないキーは足さない。

## 変更8 openapi と台帳

- `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`。差分は `/calendar/categories` の 3 つの道と、予定の作る・直すの入力の `category` だけであることを `git diff frontend/api-contract/openapi.json` で確かめる。
- 台帳 `release-schedule-settings-bin2a.md` を `release-schedule-settings-google.md` と同じ形で、状態 `IN_PROGRESS`・PR# 空で作る。

## 試験

design §5 のとおり。直す道は 5 通り（単発・この予定だけ・これ以降・すべて・単発→繰り返し）を 1 つずつ。加えて（審査 第2回の推奨）:
- `custom_9` がある状態で足すと `custom_10` になる
- 鍵がぶつかったとき（`IntegrityError` を起こす）409 `category_conflict` になり、その後の要求が普通に通る
- 元の行の種類が使わなくした種類でも、「この予定だけ」を種類を変えずに直すと通る

## 確かめ

- `cd backend && python -m pytest tests/test_calendar_categories.py tests/test_calendar_service.py tests/test_calendar_recurrence.py tests/test_calendar_owner_api.py tests/test_google_calendar.py -q` の生の出力をファイルに残す。DB の要る試験（`test_calendar_sync_tenant_reset_pg.py`・`tests/ops/test_ai_cloud_views.py`）が手元で流せなければ「CI で確かめる」と書く。
- `cd frontend && npx vitest run src/pages/schedule src/features/schedule src/components/ToggleMigration.test.tsx src/lib/query/batch3bPages.test.tsx` の生の出力。
- `cd frontend && npx tsc --noEmit` と `npx eslint src/pages/schedule src/features/schedule`。
- i18n の自己点検（`frontend/CLAUDE.md`）。
- A10 の 3 つの `git grep`（design §2）の結果を生のまま残す。
- `git diff origin/main...HEAD -- backend/app/services/calendar_service.py` を残す（`:238-250` に差が無いこと）。
- 提出前: `bash scripts/dev/check-before-submit.sh`。
- commit（`--no-verify` は使わない。分けてよい）→ `git log -1 --oneline`。
- `git push -u origin HEAD` → `git log origin/release/schedule-settings-bin2a -1 --oneline`。

## 停止する条件（BLOCKED: で返す）

- 触るファイル以外を変える必要が出た。
- `calendar_service.py` の見え方の条件（`:238-250`）を変えないと書けない。
- 既存の試験が、この変更と関係なく落ちる。
- 金型に無い部品が要る。
- openapi の差分が上の範囲を超えた。
- 移行の確かめ（古い CHECK が残る）が手元の DB で失敗した。

## 報告

- 冒頭に受領文。1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 本文に: 試験・型・lint・grep の生の出力のファイルの場所と末尾・push した commit・判断を要した点（事実のみ）
- 停止したときは: 停止した手順／最後に実行したコマンド／停止した理由の原文

## 委任の定型

- sleep は使わない。CI は待たない
- PR は作らない。main にマージしない。本番と倉庫の設定に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

END OF CARD
