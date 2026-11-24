# 実装報告: Google カレンダーの許可を狭める（実装役・クラウド）

BLOCKED: `npx tsc --noEmit -p .` が、カードに無い理由（gitignore された生成型 `frontend/src/api/generated/schema` が無い環境）で exit 2。期待を書き換えず止まった。実装は作業場所 `/root/worktrees/salesanchor/release-google-calendar-narrow-scope` に未 commit で残してある（枝は origin/main の 19c2f249c のまま。push していない）。

## 状況

- 作業場所: `release/google-calendar-narrow-scope`（origin/main = 19c2f249c 起点。審査時の ed9a9f158 より進んでいる）。`git config user.name` = shingo-cc。
- 変更3の【実装の前に確かめる】: 設計どおり（片方だけ → `Warning`・`new_scope` はリスト／2つ（順不同とも）→ 例外なし）。oauthlib 4.0.1。
- 触ったのはカードの7ファイルだけ（`git diff origin/main --name-only` で確認）。
- 変更1〜6と試験 S1・S2・S3a・S3a'・S3b・S3c・S5 を実装した。
- `ja.json`・`en.json` のキー数は同じ（各 5841）。

## 流した命令と結果

1. 前提の依存: `pip` は見張り（py312-guard）に止められたため、文面どおり `python3.12 -m venv /tmp/venv312` を作ってその pip を使った（`requirements.txt` と `requirements-dev.txt`）。
2. 事前確認（`/tmp/narrow-precheck.txt`）:
```
one: Warning new_scope=['https://www.googleapis.com/auth/calendar.events.owned'] tokscope_type=str
both: no exception
both rev: no exception
4.0.1
```
3. `cd backend && python -m pytest tests/test_google_calendar.py -q`（`/tmp/narrow-check-1.txt`。最後の部分）:
```
TOTAL                                                52230  51448     1%
FAIL Required test coverage of 60% not reached. Total coverage: 1.50%
65 passed, 5 warnings in 8.23s
oauthlib 4.0.1
```
   試験は 65 件すべて通過。「FAIL Required test coverage」は 1 ファイルだけ流したときの全体の被覆率の門で、この変更とは関係しない（未確認: 全試験を流したときの値）。
4. `npx vitest run src/pages/schedule/SchedulePageImpl.test.tsx`（`/tmp/narrow-check-2.txt`）: `Test Files 1 passed (1)` / `Tests 120 passed (120)` / exit 0。
5. `npx eslint --max-warnings=0 …`（`/tmp/narrow-check-3.txt`）: exit 0（出力なし）。
6. `npx tsc --noEmit -p .`（`/tmp/narrow-check-4.txt`、全文）: exit 2
```
src/features/tcg-sold-out/soldOutApi.ts(3,45): error TS2307: Cannot find module '../../api/generated/schema' or its corresponding type declarations.
src/pages/inventory/OwnInventoryPage.tsx(11,33): error TS2307: Cannot find module '../../api/generated/schema' or its corresponding type declarations.
src/pages/super-admin/components/SoldOutResultsPanel.tsx(34,27): error TS7006: Parameter 'line' implicitly has an 'any' type.
src/pages/super-admin/components/SoldOutResultsPanel.tsx(34,33): error TS7006: Parameter 'index' implicitly has an 'any' type.
```

## 落ちた理由（事実と推測）

- 事実: 4件とも触っていないファイル。`SchedulePage` に関する型エラーは 0 件。
- 事実: `frontend/src/api/generated/` は `.gitignore:128` で除外。`package.json` に `generate:api-types`（`openapi-typescript api-contract/openapi.json -o src/api/generated/schema.d.ts`）がある。
- 推測（未確認）: 生成型を作ってから流せば通る（`npm ci` だけでは作られない）。生成はカードの範囲外なので、指示（カードに無い理由で落ちたら止まる）に従い流していない。

## 止められた命令と見張りの文面

- `pip install -r backend/requirements.txt`: 「本番は Python 3.12 です。python3.12 -m venv <場所>（または uv venv --python 3.12 <場所>）で作り、その venv の pip を使ってください（py312-guard）」。文面が指す道（venv）で作り直した。

## 次の判断（PO / 設計役）

- 選択肢: 実装役に「`npm run generate:api-types` を流してから tsc を流す」を許可して続きをさせる。許可があれば、残りは tsc の再確認 → commit 1つ → push。
- 実装そのものは完了済み・未 commit。

BLOCKED: tsc がカードに無い理由で失敗（生成型 frontend/src/api/generated/schema が無い環境。触ったファイルの型エラーは 0 件）
