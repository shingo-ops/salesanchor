# impl-report-2: 予定の画面の表示崩れ 3 件の直し（実装・2 回目）

## 結果

手順 2〜10 を実施。4 ファイル（ja.json・en.json・schedule.css・新規 calendars.config.test.ts）だけを変えた。

## 作業場所と先頭

- `git fetch origin` → `bash scripts/new-worktree.sh release/schedule-labels-week-layout` → `git switch -C release/schedule-labels-week-layout origin/release/schedule-labels-week-layout`
- `git rev-parse HEAD` = `705cdcf63ee8cbb4cf2e38b69bb2378c51fa7908`（先頭 705cdcf63 で一致。`origin/release/schedule-labels-week-layout` も同じ）

## 手順 1 の免除

`executor-preflight.sh` は流していない。クラウドでは GitHub API と gh 切替が使えないため、Opus が手順 1 を免除した（今回の指示による）。

## 依存

`cd frontend && npm ci`（終了コード 0）

## 手順 2: 言葉を足す前の試験（14 件落ちる）

コマンド: `cd frontend && npx vitest run --config vitest.unit.config.ts --project unit src/features/schedule/calendars.config.test.ts`（終了コード 1）

```
 Test Files  1 failed (1)
      Tests  14 failed (14)
   Start at  03:36:45
   Duration  1.48s (transform 413ms, setup 60ms, import 427ms, tests 24ms, environment 754ms)
```

## 手順 3: ja/en に calendarLabels を足した後（14 件通る）

同じコマンド（終了コード 0）

```
 Test Files  1 passed (1)
      Tests  14 passed (14)
   Start at  03:37:01
   Duration  1.34s (transform 418ms, setup 38ms, import 453ms, tests 9ms, environment 672ms)
```

## 手順 4: CSS

`schedule.css` に §4-3 (a) `flex-shrink: 0`、(b) `grid-auto-flow: column` + `grid-auto-columns: minmax(0, 1fr)`、(c) 1023px 以下・767px 以下の 2 か所に `grid-auto-flow: row` を足した。行番号は設計通りで食い違いなし。

## 手順 5: 全体の点検

`cd frontend && npm run check:all`（終了コード 0。stylelint も終了コード 0）

```
[1] ✖ 60 problems (0 errors, 60 warnings)
[1] npm run lint exited with code 0
[22] npm run check:stylelint exited with code 0
```

（警告 60 件は既存の i18n 日本語リテラル等の警告。エラー 0）

`npx vitest run --config vitest.unit.config.ts --project unit src/pages/schedule src/features/schedule`（終了コード 0）

```
 Test Files  4 passed (4)
      Tests  28 passed (28)
   Start at  03:37:27
   Duration  4.61s (transform 1.69s, setup 147ms, import 3.28s, tests 3.81s, environment 3.46s)
```

## 手順 6: ja.json の meeting を Edit で消す → 落ちる → Edit で戻す → 通る

消した直後（終了コード 1）:

```
 FAIL  |unit| src/features/schedule/calendars.config.test.ts > CALENDARS labelKey は ja/en の両方に空でない文字がある > 'meeting' ('ja'): 'schedule.calendarLabels.meeting'
 Test Files  1 failed (1)
      Tests  1 failed | 13 passed (14)
```

戻した後（終了コード 0）:

```
 Test Files  1 passed (1)
      Tests  14 passed (14)
   Start at  03:37:41
   Duration  1.25s (transform 397ms, setup 45ms, import 418ms, tests 6ms, environment 671ms)
```

戻し忘れなし（ja.json の差分に meeting の行が personal の次にある）。

## git diff --stat origin/main（コード側、報告書を足す前）

```
 frontend/src/features/schedule/calendars.config.test.ts (新規)
 frontend/src/locales/en.json    | 11 ++++++++++-
 frontend/src/locales/ja.json    | 11 ++++++++++-
 frontend/src/pages/schedule.css |  6 +++++-
 3 files changed, 25 insertions(+), 3 deletions(-)  ※新規ファイルは未追跡のため上に含まれず
```

（設計・調査書類と impl-report-1 は先頭 commit 由来）

## 最終 HEAD

実装 commit（push 済み）: `8759a43f0`（先頭 705cdcf63 の次）。この追記 commit の後の HEAD は `git log -1` を参照。

補足: 最初の commit は pre-commit の lint（警告 0 件が条件）が、試験ファイルの日本語 describe 題名で止めた。題名を英語に直して再実行し、14 件通ることを確認してから commit した。pre-push の検査は 18 件流して落ち 0 件。

DONE
