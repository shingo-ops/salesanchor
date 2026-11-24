# 実装報告: 受信箱のカルテを段階で切り替える（ADR-1089）

- 枝: `release/inbox-karte-stage-tabs-impl`（origin/main 起点・`origin/release/inbox-karte-stage-tabs` の 11ed12803 を 1 回だけ取り込み・衝突なし）
- 受領確認: カード §2 の触るファイル 5 つと §3 の想定分岐を読んだ。

## §1 の点検結果（すべてカードどおり）

- `InboxKartePanel.tsx` 1 行目: `import { useEffect, useId, useRef, useState } from "react";` → 一致
- 同 124 行目: `const stagePresentation = leadDetail ? getStatusPresentation("lead", leadDetail.status) : null;` → 一致
- 同 229-238 行目: タブの並び `(["deal", "company", "contact"] as KarteTabKey[]).map((tab) => (` と `karteTab === tab` → 一致
- 同 242 行目: `tab={karteTab}` → 一致
- 同 554 行目: `// === COMPANY TAB — ADR-110: ...` → 一致
- 同 718-720 行目: `</div>` `);` `}` → 一致
- `useInboxState.ts` 655-663 行目: `// ADR-108: set default karte tab based on lead_status` から `setKarteTab("deal");` `}` → 一致
- `karte-visual-gate.spec.ts` 126・167・178・231(→差し替え C の範囲内)・270・349 行目: 各 test / describe の始まり → 一致（写す前に境界の行を assert で確認）

## 変えたもの（§2 の 1〜5）

1. 新規 `karteLayout.ts`（.txt を cp）
2. 新規 `karteLayout.test.ts`（.txt を cp）
3. `InboxKartePanel.tsx`: (a)〜(f) のとおり
4. `useInboxState.ts`: import 1 行と 655-663 の差し替え
5. `karte-visual-gate.spec.ts`: 差し替え A〜E
6. 基準画像 2 枚は触っていない（§4 の 4 で GitHub に作らせる）

## 流した命令と結果（生出力はクラウドの一時ファイルに保存して全文を読んだ）

| 命令 | 結果 |
|---|---|
| `npm ci && npm run generate:icon-sizes && npm run generate:api-types`（frontend で 1 回） | exit 0 |
| `npx tsc --noEmit`（§4-1） | exit 0・出力 0 行 |
| `npx eslint --max-warnings=0` 4 ファイル（§4-2） | exit 0・出力 0 行 |
| `npx vitest run src/pages/inbox/`（§4-3） | `|unit|` の 70 件すべて通過（`karteLayout.test.ts`・`InboxKartePanel.discordButtons.test.tsx` を含む）。ただし全体は exit 1: ブラウザ試験の 2 ファイルがこのクラウドに Chromium（版 1223）が無く起動できず `Test Files 10 passed (12)`・`Errors 1 error`（`browserType.launch: Executable doesn't exist`）。`npx playwright install chromium` はダウンロード失敗（`Download failure, code=1`）。この 2 ファイルは CI に任せる |
| §4-5 の grep 1 | 0 件（`useInboxState.ts`・`InboxKartePanel.tsx` に `follow_up_short` なし） |
| §4-5 の grep 2 | `karteLayout.ts`・`inbox.types.ts` と、試験ファイル `karteLayout.test.ts` の 3 つ。製品のファイルはカードの想定どおり 2 つ |
| 画面試験 `karte-visual-gate.spec.ts`（chromium project） | このクラウドにある別の版の Chromium（1243）を、作業場所の外に置いた一時の設定（`executablePath` だけ指定・リポジトリには入れていない）で動かした。**25 件通過・2 件失敗**。失敗は `[visual] karte-lead-deal` と `[visual] karte-customer-company` の基準画像 2 枚だけ（カード §3 の想定どおり）。他の落ちなし |

## 確かめられていないこと

- 基準画像 2 枚の作り直し（§4-4）: Opus が `gh workflow run karte-gate.yml --ref release/inbox-karte-stage-tabs-impl` で依頼する。
- vitest のブラウザ試験 2 ファイル: このクラウドでは動かなかった。CI で確認が要る。

## `git diff --stat origin/main`（commit 前・設計の取り込み分を含む）

```
 .../release-inbox-karte-stage-tabs.md              |   5 +
 docs/adr/ADR-1089-inbox-karte-stage-layout.md      |  77 ++++
 docs/adr/README.md                                 |   3 +-
 .../code/KarteTabContent-body.tsx.txt              | 229 ++++++++++++
 .../code/karte-visual-gate-replacements.ts.txt     | 185 ++++++++++
 .../code/karteLayout.test.ts.txt                   |  94 +++++
 .../inbox-karte-stage-tabs/code/karteLayout.ts.txt | 127 +++++++
 docs/handoff/inbox-karte-stage-tabs/design.md      |  79 +++++
 docs/handoff/inbox-karte-stage-tabs/impl-card.md   | 103 ++++++
 docs/handoff/inbox-karte-stage-tabs/recon.md       |  51 +++
 .../inbox-karte-stage-tabs/review-architect-1.md   | 104 ++++++
 docs/specs/inbox/README.md                         |   4 +-
 frontend/src/pages/inbox/InboxKartePanel.tsx       | 387 ++++++++++++---------
 frontend/src/pages/inbox/useInboxState.ts          |  11 +-
 frontend/tests-e2e/karte-visual-gate.spec.ts       | 239 +++++++------
 15 files changed, 1406 insertions(+), 292 deletions(-)
```

（上に `karteLayout.ts`・`karteLayout.test.ts` の新規 2 つは未追跡のため stat に出ない。commit に入れる。）
