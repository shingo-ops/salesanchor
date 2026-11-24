# 実装報告: Google カレンダーの許可を狭める（実装役・クラウド・3回目）

DONE: 706714970ed99f09adf41d76fd1a87eb5c5a703b

## 状況

- 枝: `release/google-calendar-narrow-scope`（origin/main = 19c2f249c 起点、commit 1つ、push 済み・force なし）。PR は作っていない。マージしていない。
- `git config user.name` = shingo-cc。`git rev-parse --verify origin/main` = 19c2f249c3a4202ab30b02df43ca4473f02b4009。
- `git diff origin/main --name-only` はカードの7ファイルだけ（生成物なし）:
  backend/app/routers/google_calendar.py・backend/app/services/google_calendar.py・backend/tests/test_google_calendar.py・frontend/src/locales/ja.json・en.json・frontend/src/pages/schedule/SchedulePageImpl.tsx・SchedulePageImpl.test.tsx
- 変更1〜6と試験 S1・S2・S3a（list/str × new_scope 有無の4通り＋別の範囲だけ）・S3a'・S3b・S3c・S5（2件）を実装。
- 本番・DB・secrets には触っていない。

## 流した命令と出力

1. 変更3の事前確認（`/tmp/narrow-precheck.txt`）。設計どおり:
```
Warning ['https://www.googleapis.com/auth/calendar.events.owned'] str
no exception
no exception
4.0.1
```
2. `cd backend && /tmp/venv312/bin/python -m pytest tests/test_google_calendar.py -q`（`/tmp/narrow-check-1.txt` の最後）:
```
FAIL Required test coverage of 60% not reached. Total coverage: 1.50%
66 passed, 5 warnings in 8.36s
4.0.1   <- oauthlib の版
```
   被覆率の門は1ファイルだけ流したためで無関係。passed = 66、failed 無し。
3. frontend: `npm ci` exit 0、`npm run generate:api-types` exit 0（生成物は gitignore で commit されない）。
4. `npx vitest run src/pages/schedule/SchedulePageImpl.test.tsx`（`/tmp/narrow-check-2.txt`）exit 0:
```
 Test Files  1 passed (1)
      Tests  121 passed (121)
```
5. `npx eslint --max-warnings=0`（触った tsx 2つ。`/tmp/narrow-check-3.txt`）exit 0・出力なし。
6. `npx tsc --noEmit -p .`（`/tmp/narrow-check-4.txt`）exit 0・出力なし（生成型を作ったので前回の4件は消えた）。
7. ja/en の `locales` キー数: ja 5841 / en 5841（同数）。
8. commit の pre-commit（ruff・ADR-067・ADR-072 ほか）全部通過。push の pre-push（check-before-submit）: 流した検査 18 件・落ちた 0 件。

## 止められた命令と見張りの文面

なし。

## 注意（事実）

- 手元の pre-push は Python 3.11 / node 22 で動き、最後の判定は CI（書かれた文面どおり）。
- `bash scripts/new-worktree.sh … --claude` の末尾の起動失敗（`Input must be provided…`）は指示どおり無視した。
- 次: 手元で shingo-cc 名義の PR（`--base main`、本文に「### 標準ワークフロー確認」）。
