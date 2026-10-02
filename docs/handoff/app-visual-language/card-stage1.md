# 実装カード 段階1: 3幅の画面検査（測るだけ）

> この文書は何か（専門用語なしの1行）: 受信箱をスマホ・タブレット・PCの3つの幅で自動撮影し、はみ出しと押しにくい部品を数えるだけの仕組みを作る指示書。

親: [design.md](../../specs/design-system/visual-language/design.md)（§6 段階1） / 合格条件: [kgi.md](../../specs/design-system/visual-language/kgi.md)（K6・K7・K8）

- 状態: カード作成済み。**PO実装承認待ち**（承認前は着手禁止）
- 担当: Sonnet（実装役）。設計・判断: Opus
- PO決定（2026-10-02）: CIの画面検査（`.github/workflows/e2e.yml` の playwright ジョブは105行目 `if: false` で停止中）は止めたままにする。UIを変えるPRのたびに、担当が手元で実行して結果をPRに貼る。

## 目的
- K6（3幅の画面検査 0→1）を満たす。
- K7（受信箱がスマホ幅ではみ出さないか）と K8（押す場所が44px以上か）の**現在値を測る**。直すことはしない。

## 作業場所
- origin/main から新しいブランチ `release/app-visual-language-stage1` を `bash scripts/new-worktree.sh release/app-visual-language-stage1 --claude` で作る。
- 設計文書のPR #3927 とは別の便にする（1便1目的）。

## 触るファイル（これ以外は触らない）
1. frontend/playwright.config.ts（`projects` の変更だけ）
2. frontend/tests-e2e/visual-language/inbox-baseline.spec.ts（新規）
3. docs/handoff/app-visual-language/stage1-baseline.md（新規。測定結果の生データ）
4. docs/handoff/app-visual-language/stage1/*.png（新規。撮影画像。モックデータのみで、顧客情報は含まない）
5. .claude-pipeline/active-work.d/release-app-visual-language-stage1.md（台帳）

## 触らない範囲
- `frontend/src/` 配下はすべて触らない。見つけた不具合も直さない。
- `.github/workflows/` は触らない（e2e.yml の停止は維持する）。
- 既存の spec ファイルは修正しない。他の spec から関数を import することもしない（spec を import するとテストが二重に登録されるため）。
- `toHaveScreenshot`（見本画像との比較）は使わない。撮影は `page.screenshot` と `testInfo.attach` で行う。
- backend・API・DB・fixture の中身は変えない。

## 手順0: 着手前の確認（どれか1つでも合わなければ止めて報告）
1. Context7 MCP で Playwright 1.59 の仕様を確認し、引用と出典を報告する。
   - projects 単位の `testMatch` / `testIgnore`
   - `use` での `viewport` の上書き（devices の展開の後に書く）
   - chromium で `isMobile: true` と `hasTouch: true` が使えるか
   - Context7 が使えない場合は、その事実を報告して止める。
2. 次の2つを読み、行番号付きで報告する。
   - `frontend/tests-e2e/inbox-header-ui-screenshots.spec.ts` の `baseMocks` と `openInbox`（49-56行）
   - `frontend/tests-e2e/utils/` の `api-mock.ts`・`common-mocks.ts`・`fixtures.ts`・`auth.ts`
3. 開いている次の2つのPRが、`frontend/playwright.config.ts` を変更していないか確認する。変更していたら止める。
   - #2667 release/morimoto/manual-record-to-meta-messages
   - #2663 release/morimoto/inbox-image-proxy
   - 確認コマンド: `gh pr view <番号> --json files --jq '.files[].path'`

## 変更1: frontend/playwright.config.ts（55-60行の projects）
変更前（実物。recon R13）:
```ts
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
```
変更後:
```ts
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
      // 3幅検査（visual-language）は専用 project でのみ実行する
      testIgnore: /visual-language\/.*\.spec\.ts/,
    },
    {
      name: "vl-mobile-390",
      testMatch: /visual-language\/.*\.spec\.ts/,
      use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
    },
    {
      name: "vl-tablet-768",
      testMatch: /visual-language\/.*\.spec\.ts/,
      use: { ...devices["Desktop Chrome"], viewport: { width: 768, height: 1024 } },
    },
    {
      name: "vl-desktop-1280",
      testMatch: /visual-language\/.*\.spec\.ts/,
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } },
    },
  ],
```
- 幅の根拠: 390 は既存テスト（mobile-shell.spec.ts:78、tcg-import-workflow.spec.ts:201）と同じ幅。768 と 1280 は tokens.css:114 と tokens.css:116 の境目の値。
- 手順0の Context7 確認で `isMobile` が chromium で使えないとわかった場合は、`isMobile` を外さずに止めて報告する。

## 変更2: frontend/tests-e2e/visual-language/inbox-baseline.spec.ts（新規）
動きの仕様（コードは担当が書く。書き終えたら全文を報告する）:
- 開き方は `inbox-header-ui-screenshots.spec.ts` の `openInbox` と同じにする。
  - `installAuthBypass` → `mockApi`（baseMocks と同じ経路・同じ fixture。ライト表示）→ `goto("/lead-chat")`
  - 必要なモックは、このファイル内に書く。既存のものと経路や fixture が食い違ったら止めて報告する。
- 測る状態は2つ。
  - (A) 一覧: 会話一覧の最初の項目が見えたところ。
  - (B) 会話を開いたところ: "Taro Sender" の会話を押し、メッセージが見えたところ。
  - 待ち方は、既存 spec と同じ要素を待つ。スマホ幅で同じ要素が表示されない場合は、止めて報告する。
- それぞれの状態で、次の2つを記録する（記録のみ。この結果で失敗にはしない）。
  1. はみ出し: `document.documentElement.scrollWidth` と `window.innerWidth`。horizontal-overflow.spec.ts と同じ測り方。
  2. 押しにくい部品: 表示中の `button, a[href], [role="button"], input, select, textarea` のうち、幅または高さが44px未満のもの。記録する項目は、要素名・class・aria-label（なければ文字の先頭30字）・幅・高さ。
- 記録の方法:
  - JSON は `testInfo.attach("metrics", { body: JSON.stringify(...), contentType: "application/json" })` で付ける。
  - 画面全体の写真は `testInfo.attach("screenshot", { body: await page.screenshot({ fullPage: true }), contentType: "image/png" })` で付ける。
- 失敗にする条件は、画面が開かないこと（待っている要素が出ないこと）だけにする。
- 文言の直書きについて: テストの中で画面の文字（"Taro Sender" など）を待つのは、既存 spec と同じなので許可する。

## 実行と記録
1. 作業場所で `cd frontend && npm ci && npm run test:e2e:install` を実行する（初回のみ）。
2. `npx playwright test --list` の全文を貼る。chromium project に visual-language が含まれず、vl-* の3つにだけ含まれていることを確認する。
3. `npx playwright test --project=vl-mobile-390 --project=vl-tablet-768 --project=vl-desktop-1280` の全文を貼る。
4. 設定変更で既存の検査が壊れていないことを確認する。`npx playwright test --project=chromium horizontal-overflow.spec.ts mobile-shell.spec.ts` の全文を貼る。
   - 失敗が出た場合は、変更前の main でも同じ失敗が出るかを確かめて報告する（直さない）。
5. 付けた JSON 6件（3幅×2状態）を、stage1-baseline.md に生のまま貼る。
6. 写真6枚を `docs/handoff/app-visual-language/stage1/<project>-<A|B>.png` に保存する。
7. `cd frontend && npm run check:all` の全文を貼る。
8. stage1-baseline.md の冒頭に、次の集計を書く。集計はコマンドで出し、手で数えない。
   - 「幅ごと・状態ごとの scrollWidth − innerWidth」
   - 「44px未満の件数」

## PR
- `gh pr create --base main --draft`。本文はテンプレートに沿って書く。
  - 対象ADR: ADR-144
  - recon: docs/handoff/app-visual-language/recon.md
  - 設計: docs/specs/design-system/visual-language/design.md
- 本文に、手順2〜4・7の結果と、集計の表を貼る。
- マージしない。CIを待たない。

## 止める条件（止めたら BLOCKED または NEEDS_DECISION で報告する）
- 手順0の確認結果がカードと食い違う。
- 「触るファイル」以外を変える必要が出る。
- 受信箱がモックで開かない。
- フックに止められる（言い換えて再試行しない）。
- 数字や結果が想定と説明できない形で違う。

## 合格条件（Opusが確認する）
| 基準 | 検証方法 |
|---|---|
| 3幅の project が存在し、visual-language だけを実行する | 手順2の `--list` の出力 |
| 6件の測定値と写真がそろっている | stage1-baseline.md と stage1/ の6ファイル |
| 既存の検査が設定変更で壊れていない | 手順4の出力（失敗した場合は、main でも同じ失敗が出ることの確認） |
| 製品コードを変えていない | `git diff --name-only origin/main...HEAD` が「触るファイル」と一致する |
| 値の直書きの検査が緑 | 手順7の出力 |
