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
