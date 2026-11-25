# 実装カード schedule-settings 便3a — 人の色を金型へ・使っていない列を消す・止めたチームを外す・区切りを t() へ

> この文書は何か：スケジュール設定ページ整備の便3a（DB 変更あり）の作業指示書です。

- 設計: `docs/handoff/schedule-settings/design-bin3a.md`（設計審査の結果は §12。§1〜§10 が正。このカードは設計の範囲を変えない）
- 状態: 要件は PO 承認済み（2026-11-25「1」・G4〜G7。便3a は G6 の後片付けと人の色）。実装・マージ・本番反映までの委任も同日
- 危険便: はい（`migrations/` と `scripts/run_all_migrations.sh` を触る。ADR-135/136 の GO は Opus が PR で記録する）
- 担当: 実装 Sonnet（クラウド）は push まで／PR 作成・審査・マージ Opus
- 枝: 既存の `release/schedule-settings-bin3`（設計文書が入っている枝）。`bash scripts/new-worktree.sh release/schedule-settings-bin3` で場所を作り、`git switch -C release/schedule-settings-bin3 origin/release/schedule-settings-bin3`。clone のまま commit しない。始める前に `git merge --no-edit origin/main` で main を取り込む
- 触るファイル（これ以外は触らない）:
  1. `migrations/20261128_100000_owner_color_key_drop_dead_columns.sql`（新規）
  2. `scripts/run_all_migrations.sh`（登録 1 行。`20261127_100000_add_calendar_team_share.sql` の次・`mr_report_summary` の前）
  3. `backend/tests/rls_bootstrap.py`（`:190` の対応表）・`backend/tests/test_calendar_sync_tenant_reset_pg.py`（`:56` の流す順の末尾）・`backend/tests/test_tenant_loop_migration_guard.py`（`_REVIEWED` の `rls_bootstrap.py`（`:53` の隣）と `test_calendar_sync_tenant_reset_pg.py`（`:74` の隣）の集合に新しい移行名を足す。新しい試験ファイルの項を足す。`:83` の項は触らない）
  4. `backend/app/services/tenant.py`（`:1632` の登録コメント・`:1649-1660` の `calendar_owner_settings` の形）
  5. `backend/app/routers/calendar.py`
  6. `backend/app/services/calendar_service.py`（`:226-232`・`:381-383` だけ）
  7. `migrations/20261024_100300_create_ai_cloud_views.sql`（分類 2 行を消し 1 行足す・`:3` のコメントの件数）・`scripts/migration-guard/reference-allowlist.tsv`（`:7` の sha256 と理由）・`docs/handoff/cloud-case-ai/stage1-column-class.tsv`（`:579-580` を消し `color_key` の 1 行）・`backend/tests/ops/test_ai_cloud_views.py`（`:486` を 1169・新しい試験 1 本）
  8. `backend/tests/test_calendar_owner_api.py`・`backend/tests/test_calendar_owner_color_key.py`（新規・本物の PostgreSQL・移行と A6/A8）・`backend/tests/test_owner_color_key_map.py`（新規・24 組の照合。DB 不要）
  9. `frontend/src/pages/schedule/schedule-owner.ts`・`ScheduleSettingsPage.tsx`・`SchedulePageImpl.tsx`
  10. `frontend/src/pages/schedule/ScheduleSettingsPage.test.tsx`・`SchedulePageImpl.test.tsx`・`SchedulePageCache.test.tsx`・`frontend/src/lib/query/batch3bPages.test.tsx`
  11. `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`
  12. `frontend/api-contract/openapi.json`（自動生成。手で書かない）
  13. `.claude-pipeline/active-work.d/release-schedule-settings-bin3.md`（台帳・新規）

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・03-file.md・04-worktree.md・05-pr.md・10-executor.md。照合: 場所は new-worktree.sh で作る（04）・PR は担当が作らない（05）・プレースホルダなし（00）・push は `git push -u origin HEAD`（04）・各段で `git log` を確かめる（00）。

## 発行前の点検（Opus）

| 点検 | 結果 |
|---|---|
| 設計と同じ範囲か | design-bin3a.md §3〜§5 の項目だけを変更1〜8 に割り当てた |
| 実物の行 | §1 F1〜F11 は第1回審査で照合済み（行番号の誤りは L1 で直した） |
| 本番の前提 | `calendar_owner_settings` は 5 社とも 0 行（F2） |
| 設計審査 | §12 の記録のとおり |
| 見え方を変えない | 予定の件数は A8 の試験で前後同じ |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード schedule-settings 便3a の実行結果である」と書くこと。

## 変更1 移行と新しい会社の形

design §3-1 のとおり。
- 形は `migrations/20261127_100000_add_calendar_team_share.sql` に倣う。全部屋 1 つの `DO`・`calendar_owner_settings` が無い部屋は飛ばす。
- 会社を選ぶのは 1 か所だけ。1 行で `FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' LOOP` と書き、`WHERE` の直後に別の条件を挟まない。手順 5 の確かめも同じループの中で行う（`rls_bootstrap.py:171-172`・`:200-207` がこの数を 1 と数える）。
- 手順 1〜5（`color_key text` を足す → 名前で確かめて CHECK `calendar_owner_settings_color_key_check` を足す → `color` 列があるときだけ 24 組の `CASE lower(btrim(color))` で写す → 3 列を `DROP COLUMN IF EXISTS`（CASCADE なし）→ 最後の確かめで外れたら `RAISE EXCEPTION`）。
- 24 組は `backend/app/services/event_colors.py:8-17` から一字一句写す。CHECK の鍵の並びは `tenant.py:1607` と同じ。
- `information_schema` は `table_schema` と `table_name` の両方で絞る。
- 戻し方をコメントで書く（design §3-1）。
- `tenant.py`: 3 列を `color_key text` と `CONSTRAINT calendar_owner_settings_color_key_check CHECK (color_key IN (…24 鍵…))` に変える。移行と同じ字面。
- 登録 4 か所（上の 2・3・4）。

## 変更2 受け口

design §3-2 のとおり。
- `OwnerSettingsBody` は `color_key: Optional[str] = None` だけ。`"color_key" not in body.model_fields_set` なら 422 `no_fields_to_update`。null は標準の色へ戻す。それ以外で `EVENT_COLOR_KEYS` に無い値（空文字も）は受け口の中で `HTTPException(422, detail="invalid_color_key")`。
- `OwnerRosterItem` は `color_key: Optional[str]`。`color`・`is_visible`・`share_mode` を消す。
- 名簿と保存後の読み直しは `cos.color_key`。`_DEFAULT_OWNER_COLOR`・`_VALID_OWNER_SHARE_MODES`・`default_color` を消す。
- 保存は `color_key` だけの upsert。`await db.commit()` の直後に `await reset_tenant_context(db, tenant_id)`（ADR-072）。
- `invalid_color_key` を理由の表（`backend/tests/test_api_error_reason_sync.py`・`frontend/src/lib/apiErrorReason.ts`）に足す必要があるかを試験で確かめる。要るなら止めて報告する（触るファイルに無いため）。

## 変更3 止めたチームを外す

design §3-3 のとおり。`calendar_service.py:381-383` と `:226-232` の副問い合わせに `JOIN teams t ON t.id = cet.team_id AND t.is_active` を足すだけ。書き手と確かめ役は触らない。

## 変更4 AI 用の分類

design §3-4 のとおり。
- `20261024_100300_create_ai_cloud_views.sql:381-382` の 2 行を消し、`('tenant_*','calendar_owner_settings',ARRAY['color_key'],'allow','値の決まり calendar_owner_settings_color_key_check で値が限られる')` を足す（既存の `calendar_categories` の `color_key` 行の言い回しに倣う）。`:3` のコメントの件数を 1169 に。
- `stage1-column-class.tsv:579-580` を消し、`color_key` の 1 行を同じ形で足す（型の欄は `text`）。
- `test_ai_cloud_views.py:486` を 1169。新しい試験は `:1061` に倣う。
- sha256 は SQL を直した後の `shasum -a 256 migrations/20261024_100300_create_ai_cloud_views.sql` の値を `reference-allowlist.tsv:7` に写し、理由欄の末尾に `/ schedule-settings 便3a（分類の入れ替え）`。

## 変更5 画面

design §4-1〜§4-3 のとおり。
- `schedule-owner.ts`: `colorKey` を足し、`color` は `eventColorVar(colorKey)` か `DEFAULT_OWNER_COLOR`。`visible`・`shareMode`・`CalendarShareMode` を消す。`DEFAULT_OWNER_COLOR` のコメントに `_DEFAULT_OWNER_COLOR` の名前を書かない。
- `ScheduleSettingsPage.tsx`: `<input type="color">` を `ColorSwatchPicker`（種類の色と同じ金型）に。選択肢の先頭は `{ value: null, label: t("schedule.ownerColorDefault"), color: DEFAULT_OWNER_COLOR }`。保存は `{ color_key: owner.colorKey }`。Google の接続日時は `t("schedule.settingsConnectedAtValue", { date })`。
- `SchedulePageImpl.tsx:346`: `t("schedule.shareTeamWithNames", { names: names.join(t("schedule.nameListSeparator")) })`、名前が無ければ `t("schedule.shareTeam")`。
- 金型以外の部品・色の直書き・新しい CSS の色を足さない（ADR-144・ADR-067）。

## 変更6 文字

design §4-4。ja/en に同じキー（`ownerColorDefault`・`shareTeamWithNames`・`nameListSeparator`・`settingsConnectedAtValue`）。`settingsConnectedAt` は両方から消す。`shareTeam` は残す。en の `nameListSeparator` は `", "`（末尾に空白）。JSON の整形や i18n の検査が値の空白を削るなら止めて報告する。

## 変更7 openapi と台帳

- `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`。差分が `OwnerRosterItem`・`OwnerSettingsBody` だけであることを `git diff frontend/api-contract/openapi.json` で確かめる。
- 台帳 `release-schedule-settings-bin3.md` を main にある `release-schedule-settings-bin2b.md` と同じ形で、状態 `IN_PROGRESS`・PR# 空で作る。

## 変更8 試験

design §5 のとおり。
- `test_calendar_owner_api.py`: 本体は `OwnerSettingsBody(color_key=None)`・`OwnerSettingsBody()` の本物で呼ぶ（`SimpleNamespace` をやめる）。保存・null・範囲外 422・空文字 422・未送 422・応答に `is_visible`/`share_mode` が無いこと。
- `test_calendar_owner_color_key.py`（本物の PostgreSQL）: 土台で作った部屋を `ALTER TABLE … ADD COLUMN color varchar(32) DEFAULT '#1a73e8' NOT NULL, ADD COLUMN is_visible boolean DEFAULT false NOT NULL, ADD COLUMN share_mode varchar(16) DEFAULT 'self' NOT NULL, DROP COLUMN color_key` で古い形に戻し、合う hex（大文字・前後の空白つき）と合わない hex の行を入れ、`_apply_migration_on_conn(..., schema_name=...)` で 2 回流す。写した鍵・NULL・3 列が無い・CHECK が範囲外を拒む・2 回目で変わらないことを見る。A6/A8: チームの予定を 1 件作り、チームを `is_active = false` にして、一覧の `team_ids` と `event_team_ids` からそのチームが消え、一覧の件数が変わらないこと。`CREATE TABLE` は書かない。`test_tenant_loop_migration_guard.py` の `_REVIEWED` に `scoped` で登録。移行の後、`color_key` の `format_type` が `text`、`calendar_owner_settings_color_key_check` の `pg_get_constraintdef` の鍵の並びが同じ部屋の `calendar_events_color_key_check` と同じであることを見る。先に `public.users` に行を入れる（`rls_bootstrap.py:236` の `_ensure_public_users`）。会社番号は他の試験と重ならない番号にする（前例 `test_calendar_team_share.py:37`）。
- `test_owner_color_key_map.py`: 移行ファイルの `WHEN '#…' THEN '…'` を読み、`EVENT_COLORS` と同じ 24 組・移行とひな形の `calendar_owner_settings` の CHECK の鍵が `tenant.py:1607` と同じ並びであること（前例 `backend/tests/test_event_colors_tokens.py`）。移行ファイルの名前を文字に出すので `_REVIEWED` に `text_only` と理由で登録する。
- 画面の試験には `is_visible`・`share_mode` の文字を書かない（A5 が 0 件にならない）。応答のキーは完全一致で確かめる。
- 画面の試験: 擬似データから `is_visible`・`share_mode` を消し `color_key` に。`type="color"` が無い・色を選ぶと `color_key` を送る・標準の色は `null` を送る・人の色が `var(--event-color-…)` で描かれる。`SchedulePageImpl.test.tsx:1939` を新しい文面に、`ScheduleSettingsPage.test.tsx:348` を `color_key` に直す。

## 確かめ

- `cd backend && python -m pytest tests/test_calendar_owner_api.py tests/test_calendar_owner_color_key.py tests/test_owner_color_key_map.py tests/test_calendar_team_share.py tests/test_calendar_service.py tests/test_tenant_loop_migration_guard.py tests/ops/test_ai_cloud_views.py tests/test_api_error_reason_sync.py -q` の生の出力をファイルに残す。DB の要る試験が手元で流せなければ「CI で確かめる」と書く。
- `cd frontend && npx vitest run src/pages/schedule src/lib/query/batch3bPages.test.tsx` の生の出力。
- `cd frontend && npx tsc --noEmit` と `npx eslint src/pages/schedule`。
- i18n の自己点検（`frontend/CLAUDE.md`）。
- design §2 の A1・A5・A7 の `git grep` の結果を生のまま残す（どれも 0 件）。
- 提出前: `bash scripts/dev/check-before-submit.sh`。
- commit（`--no-verify` は使わない。分けてよい）→ `git log -1 --oneline`。
- `git push -u origin HEAD` → `git log origin/release/schedule-settings-bin3 -1 --oneline`。

## 停止する条件（BLOCKED: で返す）

- 触るファイル以外を変える必要が出た。
- `ColorSwatchPicker` で null の選択肢が作れない（金型に無い部品が要る）。
- 既存の試験が、この変更と関係なく落ちる。
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
