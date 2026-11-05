# 段D 実装報告（ログインの依頼 → 鈴 → 詳しい画面）

- 作業場所: `/root/worktrees/salesanchor/release-auth-login-notice-detail`
- 開始時の `git rev-parse HEAD`: `3ee820adebc97a1bda9875f4d8c2718478d9fe7d`（3ee820ade で始まる・一致）
- カード v1.1。§2 の行番号は実物と一致（`LoginApprovalWatcher.tsx` 171行・`.test.tsx` 79行・`App.tsx:297`・`DesktopShell.tsx:209/39`・`MobileShell.tsx:211/44`・ja.json の `watcher.*`/`notices.*` ほか）。違いは無かった
- executor-preflight は GitHub API / gh の FAIL（指示どおり無視）。PR は作っていない

## §4-4 削除前の `git grep -n LoginApprovalWatcher` 生出力

```
src/components/DesktopShell.test.tsx:11:vi.mock("../features/auth/LoginApprovalWatcher", () => ({ default: () => null }));
src/components/DesktopShell.tsx:39:import LoginApprovalWatcher from "../features/auth/LoginApprovalWatcher";
src/components/DesktopShell.tsx:209:    <LoginApprovalWatcher />
src/components/MobileShell.test.tsx:36:vi.mock("../features/auth/LoginApprovalWatcher", () => ({ default: () => null }));
src/components/MobileShell.tsx:44:import LoginApprovalWatcher from "../features/auth/LoginApprovalWatcher";
src/components/MobileShell.tsx:211:    <LoginApprovalWatcher />
src/features/auth/LoginApprovalWatcher.test.tsx:13:import LoginApprovalWatcher from "./LoginApprovalWatcher";
src/features/auth/LoginApprovalWatcher.test.tsx:31:        <LoginApprovalWatcher />
src/features/auth/LoginApprovalWatcher.test.tsx:46:describe("LoginApprovalWatcher", () => {
src/features/auth/LoginApprovalWatcher.tsx:33:export default function LoginApprovalWatcher() {
```

カードの想定の範囲（2 shell・2 試験・本体・本体の試験）だけ。他の使用なし。削除後は frontend 内で0件。

## 変えたファイル（`git diff --stat origin/release/auth-login-notice-detail` 生出力）

```
 frontend/src/App.tsx                               |   2 +
 frontend/src/components/DesktopShell.test.tsx      |   1 -
 frontend/src/components/DesktopShell.tsx           |   2 -
 frontend/src/components/MobileShell.test.tsx       |   1 -
 frontend/src/components/MobileShell.tsx            |   2 -
 frontend/src/components/NoticeBell.test.tsx        | 116 ++++++++++++++
 frontend/src/components/NoticeBell.tsx             |  93 ++++++++++-
 .../features/auth/LoginApprovalWatcher.test.tsx    |  79 ----------
 .../src/features/auth/LoginApprovalWatcher.tsx     | 171 ---------------------
 .../features/auth/LoginRequestDetailPage.test.tsx  |  97 ++++++++++++
 .../src/features/auth/LoginRequestDetailPage.tsx   | 152 ++++++++++++++++++
 frontend/src/locales/en.json                       |  15 +-
 frontend/src/locales/ja.json                       |  15 +-
 tests/prod-check/device-accept.spec.ts             |  66 ++++++--
 14 files changed, 527 insertions(+), 285 deletions(-)
```
（この報告ファイル自体は上の diff の後に足した）

## 実装の補足
- `PendingLoginRequest` 型は新画面から export。鈴は型だけ import
- `PENDING_FETCH_MIN_INTERVAL_MS` は鈴（`NoticeBell.tsx`）へ移し export
- 「私です」の後の「戻る」は `common.back`（ja「戻る」）
- 使わなくなったキー `login.deviceApproval.watcher.title` は、`device-accept.spec.ts` の旧版が読んでいたが新版は `detail.title` を読む。コード上の参照は無くなったが、「迷えば残す」で**消していない**
- 新しい CSS は作っていない。色・余白は `Stack`・`Button`・`EmptyState`・`PageLayout`・`NoticeRow` の金型のみ。生の button/select は新規に書いていない（鈴の既存の button は元のまま）
- `frontend/src/api/generated/schema.d.ts` は `npm run generate:api-types` で手元に作った（commit 対象外・未追跡にならない設定）。これが無いと tsc が既存ファイルで落ちる

## 受入条件 D-a〜D-i（自分で確かめたこと / 確かめられなかったこと）

| 基準 | 確かめた | 確かめられなかった |
|---|---|---|
| D-a 鈴に依頼が出る | `NoticeBell.test.tsx`「counts the request with unread notices and puts its row first」: 依頼1件＋未読2件で数字 3・依頼の行が先頭、が緑 | 本番 K2 の新しい形（流していない・指示） |
| D-b 行にボタンが無い | 同試験で、依頼の行（`NoticeRow` の button）の中に button が0個。行そのものが1つの button | — |
| D-c 押すと詳しい画面 | 「navigates to the detail page…」: `/account/login-requests/req-1` へ移動、`api.post` 呼ばれない（`/notices/{id}/read` なし）が緑。詳しい画面の試験で機械・場所・時刻（dd 3つ）と2ボタンが緑 | PO の本番目視 |
| D-d 私です→番号→許可 | `LoginRequestDetailPage.test.tsx`: 「私です」前は番号なし→後に3つ→`/auth/login-requests/req-1/approve` に `{number:"34"}`→`approvedTitle`、違う番号（rejected）で `wrongNumberBody`、が緑 | 本番 K3 の新しい形（流していない） |
| D-e 私ではありません→拒否 | 同試験: `/reject` に `{}`→`rejectedTitle`、id が一覧に無いと `closed`、が緑 | 本番 K4 の新しい形（流していない） |
| D-f 小窓が出ない | frontend 内で `LoginApprovalWatcher` の参照0件（下に生出力）。docs のカードの記述を除く | `git grep ... origin/main` は main にこの変更が入ってから。本番の目視は未 |
| D-g t() 経由・ja/en 同じキー | 追加・変更したキーは ja.json と en.json の両方（9キー＋値変更3）。JSON 構文は読み込みで確認。新規コードに日本語リテラル無し。lint 0 エラー（新ファイルに警告無し） | CI の i18n の確かめ |
| D-h 金型とトークン | `check-before-submit.sh` の UI governance gate（○）・ADR-067 の commit 時チェック（○）・lint 0 エラー | CI の Lint & Dark Mode Check |
| D-i CI | — | PR を作っていないので未確認 |

`device-accept.spec.ts` は書き換えただけで流していない。型確認: `npx tsc --noEmit` は frontend の tsconfig の対象外のファイルのため、この spec 自体の型は**確かめられていない**（`tests/` は別の Playwright 設定）。構文は commit 時の prettier/eslint の対象外。

## 【3/4】確かめの生出力

### (1) `npx tsc --noEmit`
最初（`schema.d.ts` 未生成）:
```
src/features/tcg-sold-out/soldOutApi.ts(3,45): error TS2307: Cannot find module '../../api/generated/schema' or its corresponding type declarations.
src/pages/inventory/OwnInventoryPage.tsx(11,33): error TS2307: Cannot find module '../../api/generated/schema' or its corresponding type declarations.
src/pages/super-admin/components/SoldOutResultsPanel.tsx(34,27): error TS7006: Parameter 'line' implicitly has an 'any' type.
src/pages/super-admin/components/SoldOutResultsPanel.tsx(34,33): error TS7006: Parameter 'index' implicitly has an 'any' type.
tsc exit=2
```
（この4件は今回触っていないファイル。生成物が無いことが原因）
`npm run generate:api-types` の後:
```
===TSC
tsc exit=0
```

### (2) `npm run lint`
```
✖ 59 problems (0 errors, 59 warnings)
  0 errors and 1 warning potentially fixable with the `--fix` option.

lint exit=0
```
（警告は既存ファイル: FedExRateModal.test・PriorityScoreBadge.test・i18n.ts・api.no-double-prefix.test・funnelFixtures・OAuthCallbackPage ほか。今回触ったファイルの警告は 0）

### (3) 指定4ファイルの vitest
```
 RUN  v4.1.7 /root/worktrees/salesanchor/release-auth-login-notice-detail/frontend

 Test Files  4 passed (4)
      Tests  30 passed (30)
   Start at  17:52:03
   Duration  3.59s (transform 1.62s, setup 132ms, import 2.93s, tests 1.65s, environment 2.96s)
```

### (4) `npx vitest run`（全部）
```
 Test Files  198 passed (273)
      Tests  2217 passed (2217)
     Errors  1 error
   Start at  17:52:18
   Duration  127.95s (transform 12.42s, setup 5.10s, import 68.62s, tests 118.22s, environment 153.45s)
```
- 落ちた試験: 0（2217 件すべて緑）。`Errors 1` と、273 − 198 = 75 ファイルが数えられていない件は、Storybook 用のブラウザ試験が `browserType.launch: Executable doesn't exist at /opt/pw-browsers/chromium_headless_shell-1223/chrome-headless-shell-linux64/chrome-headless-shell`（Playwright のブラウザがこの実行環境に無い）で起動できないため。今回の変更と無関係な環境の問題。**変更前の HEAD で同じ落ち方をするかは流して確かめていない**（原因が実行ファイルの欠如で明らか、と判断。未検証）

### (5) `bash scripts/dev/check-before-submit.sh`（commit 878d555f5 の後）
```
合計 10.6 秒 / 必須 16 件を表示 / 流した検査 18 件 / 落ちた検査 0 件
注意: この枝は main より遅れている。main を取り込んでから流すと CI と同じ結果になる
結果: ○ 流した検査は全部通りました（終了コード 0）
```
（main は取り込んでいない・指示どおり）

## 残り・注意
- 本番の受入試験（K2〜K4 の新しい形）は未実行。鈴は PC では hover で開く前提で `openRequestFromBell` を書いた（hover → 行が4秒出なければ開き直す、を60秒まで）。スマホ幅で流す場合は「tab」変種（クリックで開く）になるため、そのとき hover で開かない可能性がある（未確認）
- 依頼の行を押した直後の詳しい画面は、鈴の一覧の読み込みとは別に `/login-approvals/pending` を読む。5秒の間隔制限は鈴側だけに入れた（カードどおり）

## main 取り込み（2回目）

- 作業前 HEAD: f26d3b695（origin と一致）。origin/main (df6725761) を git merge --no-edit で1回取り込み
- 衝突は LoginApprovalWatcher.tsx と同 .test.tsx の「こちら削除・main 変更」の2件のみ。両方 git rm で削除を維持
- merge commit: 33ad8fc36 / 直し: f16b3686e（NoticeBell.tsx を isDevSession() に、NoticeBell.test.tsx を registerDevSession(null)・registerTestDevSession() に）
- ja.json / en.json のキー数: ja 5231 / en 5231（一致）

### (d) git grep -n "lib/auth/provider\|isSelfAuth" -- frontend
```
（出力なし・0件・終了コード1）
```

### (e)(1) npx tsc --noEmit
```
tsc exit=0
```

### (e)(2) npm run lint
```

> salesanchor-frontend@1.0.0 lint
> eslint src


/root/worktrees/salesanchor/release-auth-login-notice-detail/frontend/src/components/FedExRateModal.test.tsx
  151:19  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal

/root/worktrees/salesanchor/release-auth-login-notice-detail/frontend/src/components/PriorityScoreBadge.test.tsx
  15:28   warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  16:33   warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  17:9    warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  17:30   warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  18:9    warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  18:29   warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  19:9    warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  19:30   warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  20:38   warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  21:35   warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  22:35   warning  i18n: テンプレートリテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  22:54   warning  i18n: テンプレートリテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  22:82   warning  i18n: テンプレートリテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  22:105  warning  i18n: テンプレートリテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  30:9    warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  45:6    warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  47:29   warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  50:6    warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  52:29   warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  55:6    warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  56:61   warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  57:36   warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  61:6    warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  63:36   warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  67:6    warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  68:61   warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  69:36   warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal
  73:6    warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）     local/no-japanese-literal

/root/worktrees/salesanchor/release-auth-login-notice-detail/frontend/src/i18n.ts
  43:7  warning  Unused eslint-disable directive (no problems were reported from 'no-console')

/root/worktrees/salesanchor/release-auth-login-notice-detail/frontend/src/lib/api.no-double-prefix.test.ts
  29:10  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  30:6   warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal

/root/worktrees/salesanchor/release-auth-login-notice-detail/frontend/src/mocks/funnelFixtures.ts
   33:17  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
   42:17  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
   51:17  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
   60:17  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
   69:17  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
   78:17  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
   87:17  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  135:14  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  136:14  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  137:14  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  138:14  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  143:22  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  144:13  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  149:22  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  150:13  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  158:14  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  159:14  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  160:14  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  165:22  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  166:13  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  183:25  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  223:18  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  241:25  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  281:18  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  299:25  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal
  339:18  warning  i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）  local/no-japanese-literal

/root/worktrees/salesanchor/release-auth-login-notice-detail/frontend/src/pages/oauth-callback/OAuthCallbackPage.tsx
  130:6  warning  React Hook useEffect has a missing dependency: 't'. Either include it or remove the dependency array  react-hooks/exhaustive-deps

✖ 59 problems (0 errors, 59 warnings)
  0 errors and 1 warning potentially fixable with the `--fix` option.

lint exit=0
```

### (e)(3) 指定4ファイルの vitest
```
|
!  No story files found for the specified pattern: src/**/*.mdx

 RUN  v4.1.7 /root/worktrees/salesanchor/release-auth-login-notice-detail/frontend

|
•  Storybook collects completely anonymous usage telemetry. We use it to
|  shape Storybook's roadmap and prioritize features. You can learn more,
|  including how to opt out, at ]8;;https://storybook.js.org/telemetryhttps://storybook.js.org/telemetry]8;;

 Test Files  4 passed (4)
      Tests  30 passed (30)
   Start at  18:09:18
   Duration  3.91s (transform 1.66s, setup 276ms, import 2.93s, tests 1.86s, environment 3.23s)

exit=0
```

### (e)(4) npx vitest run（全部）末尾
```
⎯⎯⎯⎯⎯⎯ Unhandled Errors ⎯⎯⎯⎯⎯⎯

Vitest caught 1 unhandled error during the test run.
This might cause false positive tests. Resolve unhandled errors to make sure your tests are not affected.

⎯⎯⎯⎯⎯⎯ Unhandled Error ⎯⎯⎯⎯⎯⎯⎯
Error: browserType.launch: Executable doesn't exist at /opt/pw-browsers/chromium_headless_shell-1223/chrome-headless-shell-linux64/chrome-headless-shell
╔════════════════════════════════════════════════════════════╗
║ Looks like Playwright was just installed or updated.       ║
║ Please run the following command to download new browsers: ║
║                                                            ║
║     npx playwright install                                 ║
║                                                            ║
║ <3 Playwright Team                                         ║
╚════════════════════════════════════════════════════════════╝
 ❯ node_modules/@vitest/browser-playwright/dist/index.js:929:55

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯


 Test Files  196 passed (271)
      Tests  2191 passed (2191)
     Errors  1 error
   Start at  18:09:35
   Duration  150.64s (transform 14.00s, setup 6.85s, import 78.55s, tests 136.08s, environment 183.38s)

error during close browserType.launch: Executable doesn't exist at /opt/pw-browsers/chromium_headless_shell-1223/chrome-headless-shell-linux64/chrome-headless-shell
╔════════════════════════════════════════════════════════════╗
║ Looks like Playwright was just installed or updated.       ║
║ Please run the following command to download new browsers: ║
║                                                            ║
║     npx playwright install                                 ║
║                                                            ║
║ <3 Playwright Team                                         ║
╚════════════════════════════════════════════════════════════╝
    at /root/worktrees/salesanchor/release-auth-login-notice-detail/frontend/node_modules/@vitest/browser-playwright/dist/index.js:929:55 {
  name: 'Error',
  type: 'Unhandled Error',
  stacks: [
```
- 落ちた試験: 0 件（2191 件通過）。ただし 271 ファイル中 75 ファイルは Storybook のブラウザ試験で、この実行機に Playwright の Chromium (chromium_headless_shell-1223) が無く起動できず未実行（環境の問題・コードの失敗ではない。CI で確認）

### (e)(5) bash scripts/dev/check-before-submit.sh 末尾
```
  - test-guard-evaluations (node --test)             流していない: CI で確かめる（約 120 秒。--full で流せます）
  - run_rule_fixtures（全件）                    流していない: CI で確かめる（約 375 秒。--full で流せます）

== 版の違い（手元と CI）==
  手元: Python 3.11.18 / node v22.23.4
  CI  : Python 3.12 / node 22（guard-authoring だけ 24）
  版が違うので、最後の判定は CI です（この入口は提出前の補助）

合計 11.5 秒 / 必須 16 件を表示 / 流した検査 18 件 / 落ちた検査 0 件 / ログ /tmp/check-before-submit.gCKfgr（消さずに残します）
結果: ○ 流した検査は全部通りました（終了コード 0）
流した印を書きました: /home/user/salesanchor/.git/worktrees/release-auth-login-notice-detail/check-before-submit.ok
exit=0
```

### git diff --stat f26d3b695
```
 .github/workflows/e2e.yml                          |   7 -
 .github/workflows/frontend-check.yml               |  10 +
 .github/workflows/karte-gate.yml                   |   9 -
 .../doc-library-one-tree/card-weekly-k9-line.md    |  56 ++
 .../impl-report-weekly-k9-line.md                  |  78 ++
 .../handoff/doc-library-one-tree/k12-fix-design.md |  19 +
 docs/handoff/firebase-removal/design.md            |   9 +-
 docs/handoff/firebase-removal/recon.md             |  15 +-
 frontend/.storybook/main.ts                        |  25 -
 frontend/.storybook/preview.tsx                    |   7 +-
 frontend/package-lock.json                         | 890 +--------------------
 frontend/package.json                              |   1 -
 frontend/playwright.config.ts                      |   6 +-
 .../components/LeadFormButtonMigration.test.tsx    |   3 +-
 frontend/src/components/NoticeBell.test.tsx        |   8 +-
 frontend/src/components/NoticeBell.tsx             |   4 +-
 .../PurchaseAdminEditorButtonMigration.test.tsx    |   3 +-
 .../src/components/SharedButtonMigration.test.tsx  |   3 +-
 frontend/src/contexts/AuthContext.tsx              | 119 +--
 frontend/src/contexts/UiPrefsContext.tsx           |   2 +-
 .../src/features/auth/RecoveryCodePrompt.test.tsx  |   4 +-
 frontend/src/features/auth/RecoveryCodePrompt.tsx  |   4 +-
 .../src/lib/__storybook-mocks__/firebase-app.ts    |   6 -
 .../src/lib/__storybook-mocks__/firebase-auth.ts   |  34 -
 frontend/src/lib/api.httpError.test.ts             |   7 +-
 frontend/src/lib/api.ts                            |  10 +-
 frontend/src/lib/auth/apiReauth.test.ts            |   5 +-
 frontend/src/lib/auth/authErrorMessage.ts          |   1 -
 frontend/src/lib/auth/devSession.ts                | 104 +++
 frontend/src/lib/auth/devSessionSlot.ts            |  35 +
 frontend/src/lib/auth/passkey.test.ts              |   9 +-
 frontend/src/lib/auth/passkey.ts                   |   4 +-
 frontend/src/lib/auth/provider.test.ts             |  15 -
 frontend/src/lib/auth/provider.ts                  |  21 -
 frontend/src/lib/auth/selfAuth.test.ts             |   5 +-
 frontend/src/lib/auth/selfAuth.ts                  |  19 +-
 frontend/src/lib/firebase-auth.ts                  | 189 -----
 frontend/src/lib/firebase.ts                       |  68 --
 frontend/src/lib/firebaseErrorMessage.test.ts      |  87 --
 frontend/src/lib/firebaseErrorMessage.ts           |  60 --
 frontend/src/lib/query/QueryAuthSync.tsx           |   2 +-
 frontend/src/lib/query/apiQuery.test.tsx           |   1 -
 frontend/src/lib/query/batch3aPages.test.tsx       |   1 -
 frontend/src/lib/query/batch3bPages.test.tsx       |   1 -
 frontend/src/lib/query/batch3cPages.test.tsx       |   1 -
 frontend/src/lib/query/batch3dPages.test.tsx       |   1 -
 frontend/src/lib/query/batch3ePages.test.tsx       |   1 -
 frontend/src/lib/query/batch3fPages.test.tsx       |   1 -
 frontend/src/lib/query/dashboardPage.test.tsx      |   1 -
 frontend/src/lib/query/stage2Pages.test.tsx        |   1 -
 .../src/lib/realtime/RealtimeProvider.test.tsx     |   6 +-
 frontend/src/locales/en.json                       |  13 -
 frontend/src/locales/ja.json                       |  13 -
 frontend/src/main.tsx                              |  20 +-
 .../account-settings/SecuritySection.test.tsx      |  32 +-
 .../src/pages/account-settings/SecuritySection.tsx |  61 +-
 frontend/src/pages/login/LoginPage.test.tsx        |  52 +-
 frontend/src/pages/login/LoginPage.tsx             |  14 +-
 .../reset-password/ResetPasswordPage.test.tsx      |   1 -
 frontend/src/test-setup.ts                         |  20 +-
 frontend/src/test-utils/devSession.ts              |  30 +
 frontend/tests-e2e/login.spec.ts                   |   6 +-
 frontend/tests-e2e/scene1-dashboard.spec.ts        |   2 +-
 frontend/tests-e2e/utils/auth.ts                   |  10 +-
 .../visual-language/viewer-focus-trap.spec.ts      |   2 +-
 .../tests-e2e/visual-language/viewer-helpers.ts    |   2 +-
 frontend/vite.config.ts                            |   2 +-
 scripts/dev/doc-entry-weekly-check.sh              |   4 +-
 68 files changed, 538 insertions(+), 1724 deletions(-)
```
