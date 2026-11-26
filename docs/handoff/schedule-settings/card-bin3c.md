# 実装カード schedule-settings 便3c — 小さい月カレンダーの週の始まり・初期値の読み込み失敗の文

> この文書は何か：便3c（画面だけ）の作業指示書です。

- 設計: `docs/handoff/schedule-settings/design-bin3c.md`（§1〜§9 が正。このカードは設計の範囲を変えない）
- 状態: PO 2026-11-26「1」（この 2 点を設計から本番まで）。実装・マージ・本番反映の委任は同じ流れ
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を触らない）
- 担当: 実装 Sonnet（クラウド）は push まで／PR 作成・審査・マージ Opus
- 枝: 既存の `release/schedule-settings-bin3c`（設計とこのカードが入っている）。`bash scripts/new-worktree.sh release/schedule-settings-bin3c` で場所を作り、`git switch -C release/schedule-settings-bin3c origin/release/schedule-settings-bin3c`。clone のまま commit しない。その後 `git rev-list --count HEAD..origin/main` を流す。0 でなければ main は取り込まず `BLOCKED: main が先に進んだ` で返す（`scripts/agent-hooks/cloud/rules.md:15`）
- 触るファイル（これ以外は触らない）:
  1. `frontend/src/pages/schedule/schedule-utils.ts`
  2. `frontend/src/pages/schedule/SchedulePageImpl.tsx`
  3. `frontend/src/pages/schedule/ScheduleSettingsPage.tsx`
  4. `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`
  5. `frontend/src/pages/schedule/schedule-utils.test.ts`・`frontend/src/pages/schedule/SchedulePageImpl.test.tsx`・`frontend/src/pages/schedule/ScheduleSettingsPage.test.tsx`
  6. `frontend/src/pages/schedule/SchedulePageCache.test.tsx`（擬似応答に初期値の 1 行を足すだけ。変更3）

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・03-file.md・04-worktree.md・05-pr.md・10-executor.md。照合: 場所は new-worktree.sh で作る（04）・PR は担当が作らない（05）・プレースホルダなし（00）・push は `git push -u origin HEAD`（04）・各段で `git log` を確かめる（00）。

## 発行前の点検（Opus）

| 点検 | 結果 |
|---|---|
| 設計と同じ範囲か | design-bin3c.md §4-1・§4-2 だけを変更1・変更2 に割り当てた |
| 実物の行 | §2 F1〜F13 は origin/main 331c18613 で Opus が読んだ |
| 今の動きを変えない | `getMonthCells` の既定は 0（日曜）。初期値が行無しの人は今と同じ日曜始まり |
| 設計審査 | design-bin3c.md §10（第1回 REVISE の R1・R2 を変更3に入れた。第2回 APPROVE、軽い指摘 L1〜L3 も変更3に入れた） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード schedule-settings 便3c の実行結果である」と書くこと。

## 変更1 週の始まり

design §4-1 の 1〜4 のとおり。

- `getMonthCells(anchor: Date, weekStart: 0 | 1 = 0)`。始まりは `addDays(first, -((first.getDay() - weekStart + 7) % 7))`。42 個のまま。
- `ScheduleSidebar` の引数と型に `weekStart: 0 | 1`。`getMonthCells(currentMonth, weekStart)`。曜日の見出しは `new Date(2024, 0, 7 + weekStart + index)`。
- 呼び出しに `weekStart={prefs.week_start}`。月の形の `viewDays` も `getMonthCells(anchorDate, prefs.week_start)`。

## 変更2 読み込み失敗の文

design §4-2 の 1〜3 のとおり。

- ja/en の `schedule` に `prefsLoadError`・`prefsLoadErrorSchedule`（文は design §4-2 の 1 の字面のまま）。`prefsSaveError` の次に置く。
- 設定ページ: 初期値の区画の `{prefsError && ...}`（今の `:519`）の上に `{prefsQ.isError && !prefsReady && <div className="error-message" role="alert">{t("schedule.prefsLoadError")}</div>}`。
- 予定ページ: `const { prefs, isLoaded: prefsLoaded, query: prefsQuery } = useCalendarPreferences({ enabled: live });`。`prefsFailed = live && prefsQuery.isError && !prefsLoaded`。`shownError` は design §4-2 の 3 の式。
- 新しい部品・CSS・色は足さない。
- ja の文に `frontend/scripts/check-error-text-next-action.js:28` の `FAILURE` に当たる語を入れない（`check:error-text-next-action` が赤になる）。文は design の字面のまま。

## 変更3 試験

design §5 の K1〜K4。

- `schedule-utils.test.ts`: K1（2026-11-15 を基に、`weekStart` 1 → 1 つ目 2026-10-26、0 と引数なし → 2026-11-01、どれも 42 個）。
- 失敗の切替え: `SchedulePageImpl.test.tsx` と `ScheduleSettingsPage.test.tsx` の `answers`（今の `prefs` の次）に `prefsFail: false as boolean` を足す。`/calendar/preferences` の枝（`SchedulePageImpl.test.tsx:80-83`・`ScheduleSettingsPage.test.tsx:57-60`）の先頭で `if (answers.prefsFail) throw new Error("prefs failed");`。各ファイルの `beforeEach`（`SchedulePageImpl.test.tsx:119` 付近・`ScheduleSettingsPage.test.tsx:88` 付近）で `answers.prefsFail = false;` に戻す。
- `SchedulePageImpl.test.tsx`: K2。初期値 `{ ...DEFAULT_PREFS, week_start: 1 }` の人と、既定（`prefs: null`）の人の 2 つ。見出しは `container.querySelectorAll(".schedule-mini-calendar__weekdays span")[0].textContent`、マスは `container.querySelectorAll(".schedule-mini-calendar__day")[0].textContent`。見出しの期待値は日本語の曜日名（「月」「日」。`Intl` の `"ja-JP"` で作るため画面の言語によらない）。時計は固定しない。マスの期待値は試験の中で今日から作る: 今月 1 日 `first = new Date(y, m, 1)` から `weekStart` 1 なら `(first.getDay() + 6) % 7` 日、0 なら `first.getDay()` 日戻した日の `getDate()` の文字。月曜の人は初期値が後から届くので `waitFor` で待つ（`SchedulePageImpl.test.tsx:2110-2113` の B1 と同じ形）。既定の人は待たなくてよい。
- `SchedulePageImpl.test.tsx`: K4。`prefsFail = true` で `prefsLoadErrorSchedule` の文が出る・予定（今ある試験と同じ 1 件）は出る。`prefsFail = false` では文が出ない。
- `ScheduleSettingsPage.test.tsx`: K3。`prefsFail = true` で `prefsLoadError` の文が出る（`screen.findByText(i18n.t("schedule.prefsLoadError"))`。`:476` と同じ書き方）。その要素が `role="alert"`。保存ボタンは既存の `saveButton()`（`:485`）で取り、disabled。
- `SchedulePageCache.test.tsx`: `:73` の `/calendar/owners` の行の前に `if (path === "/calendar/preferences") return { default_view: "week", week_start: 0, event_minutes: 60, auto_meet: false, open_owners: "self", open_team_id: null };` を 1 行足す（今は `:76` の想定外の GET で投げ、この便の後は失敗の文が出るため）。ほかは触らない。
- 文の確かめは、試験が今使っている i18n のやり方（実際の文か キー名か）に合わせる。
- `SchedulePageCache.test.tsx` の試験が、足した 1 行のせいで落ちたら、ほかを直さずに `BLOCKED:` でその試験名を返す。
- 上のほかの試験ファイルが、初期値の擬似応答が無いため新しい文で落ちたら、触らずに `BLOCKED:` でファイル名と落ちた試験名を返す。

## 確かめ

- `cd frontend && npx vitest run src/pages/schedule` の生の出力。
- `cd frontend && npx tsc --noEmit` と `npx eslint src/pages/schedule`。
- i18n の自己点検（`frontend/CLAUDE.md`）と `npm run check:i18n-missing-keys`。
- 提出前: `bash scripts/dev/check-before-submit.sh`。
- commit（`--no-verify` は使わない）→ `git log -1 --oneline`。
- `git push -u origin HEAD` → `git log origin/release/schedule-settings-bin3c -1 --oneline`。

## 停止する条件（BLOCKED: で返す）

- 触るファイル以外を変える必要が出た。
- 金型に無い部品が要る。
- 既存の試験が、この変更と関係なく落ちる。
- main が先に進んでいた（上の件数が 0 でない）。

## 報告

- 冒頭に受領文。1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 本文に: 試験・型・lint の生の出力のファイルの場所と末尾・push した commit・判断を要した点（事実のみ）
- 停止したときは: 停止した手順／最後に実行したコマンド／停止した理由の原文

## 委任の定型

- sleep は使わない。CI は待たない
- PR は作らない。main にマージしない。本番と倉庫の設定に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

END OF CARD
