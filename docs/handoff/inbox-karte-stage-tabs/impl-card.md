# 実装カード: 受信箱のカルテの見せ方を段階で切り替える（ADR-1089）

- 枝: `release/inbox-karte-stage-tabs`（origin/main `1ac87e46b` 起点）
- 設計: `design.md`・調査: `recon.md`・決定: `docs/adr/ADR-1089-inbox-karte-stage-layout.md`
- 書く人: クラウドの Sonnet。設計に無いことはしない。迷ったら止まって `NEEDS_DECISION:` で返す。

## 0. 読んだ節

- このカードを作るとき Opus が引いた決まり: `docs/handoff/design-partner-card-ops/guards/00-common.md`・`guards/03-file.md`（新規は丸ごと書く・長い本文はファイルで渡す）・`guards/04-worktree.md`（作業場所は new-worktree.sh・push は `git push -u origin HEAD`）
- `docs/ai-agents/executor-checklist.md`（作業前・commit 前・PR 前）
- ADR-1089 What 1〜7・ADR-027（t() 経由）・ADR-144（金型）

## 受領確認

- 始める前に、このカードの §2 の触るファイル 5 つと §3 の想定分岐を読んだことを、最初の報告で 1 行で返す（受領確認）。
- 作業場所: `git fetch origin` → `bash scripts/new-worktree.sh release/inbox-karte-stage-tabs` → その場所へ移る → `git merge --no-edit origin/release/inbox-karte-stage-tabs`（設計書を取り込む）。

## 1. 先に確かめる実物（違っていたら止まる）

| ファイル | 行 | 中身 |
|---|---|---|
| `frontend/src/pages/inbox/InboxKartePanel.tsx` | 1 | `import { useEffect, useId, useRef, useState } from "react";` |
| 同 | 124 | `const stagePresentation = leadDetail ? getStatusPresentation("lead", leadDetail.status) : null;` |
| 同 | 229-238 | タブの並び `(["deal", "company", "contact"] as KarteTabKey[]).map((tab) => (` と `karteTab === tab` |
| 同 | 242 | `tab={karteTab}` |
| 同 | 554 | `// === COMPANY TAB — ADR-110: 基本 / 取引プロフィール / 実績サマリー / 引き継ぎ ===` |
| 同 | 717-720 | 商談タブの終わり（`</div>` `);` `}`） |
| `frontend/src/pages/inbox/useInboxState.ts` | 655-663 | `// ADR-108: set default karte tab based on lead_status` から `setKarteTab("deal");` `}` まで |
| `frontend/tests-e2e/karte-visual-gate.spec.ts` | 126, 167, 178, 231, 270, 349 | 各 test / describe の始まり（recon §2） |

## 2. 触るファイル（これだけ）

1. 新規 `frontend/src/pages/inbox/karteLayout.ts` ← `docs/handoff/inbox-karte-stage-tabs/code/karteLayout.ts.txt` の中身をそのまま。
2. 新規 `frontend/src/pages/inbox/karteLayout.test.ts` ← `code/karteLayout.test.ts.txt` の中身をそのまま。
3. `frontend/src/pages/inbox/InboxKartePanel.tsx`:
   - (a) 1 行目を `import { Fragment, useEffect, useId, useRef, useState } from "react";` にする。
   - (b) 8 行目の次に 1 行足す: `import { KARTE_SECTIONS, getKarteLayout, resolveKarteTab, type KarteFieldKey, type KarteSectionKey } from "./karteLayout";`
   - (c) 124 行目の次に 2 行足す:
     ```tsx
     const karteLayout = getKarteLayout(leadDetail?.status);
     const activeKarteTab = resolveKarteTab(karteLayout, karteTab);
     ```
   - (d) 228-238 のタブの並びの部分を次にする（コメント 1 行・map の配列・active の比べる相手だけ変わる）:
     ```tsx
     {/* Tab bar — ADR-1089: tabs and order come from karteLayout.ts (per stage) */}
     <div className="right-panel-tabs" data-testid="karte-tab-bar">
       {karteLayout.tabs.map((tab) => (
         <button key={tab} type="button"
           className={`right-panel-tab${activeKarteTab === tab ? " active" : ""}`}
           data-testid={`karte-tab-${tab}`}
           onClick={() => setKarteTab(tab)}>
           {t(`inbox.karte${tab.charAt(0).toUpperCase()}${tab.slice(1)}`)}
         </button>
       ))}
     </div>
     ```
   - (e) 242 行目 `tab={karteTab}` を `tab={activeKarteTab}` にする。
   - (f) 554 行目（`// === COMPANY TAB` の行）から 720 行目（`KarteTabContent` の閉じ `}`）までを、`code/KarteTabContent-body.tsx.txt` の中身で置き換える。477-552 の連絡先タブは 1 文字も変えない。
4. `frontend/src/pages/inbox/useInboxState.ts`:
   - import に 1 行足す（43 行目の次）: `import { getKarteLayout } from "./karteLayout";`
   - 655-663 を次にする:
     ```ts
     // ADR-1089: 最初に開くタブは段階ごとの見せ方（karteLayout.ts）の最初のタブ
     const conv = conversations.find((c) => c.lead_id === leadId);
     setKarteTab(getKarteLayout(conv?.lead_status).tabs[0]);
     ```
5. `frontend/tests-e2e/karte-visual-gate.spec.ts`: `code/karte-visual-gate-replacements.ts.txt` の差し替え A〜E のとおり。他の行は変えない。
6. 基準画像 2 枚（`frontend/tests-e2e/karte-visual-gate.spec.ts-snapshots/karte-lead-deal-chromium-linux.png`・`karte-customer-company-chromium-linux.png`）: 手で作らない。§4 の (4) で GitHub に作らせる。

触らない: CSS・`ja.json`/`en.json`・backend・migrations・scripts・`.github/`・連絡先タブ・ActionBar・`PerformanceSummary` の中身・`inbox.types.ts`・`karte-screenshot-compare.spec.ts`。

## 3. 想定分岐

| 起きたこと | すること |
|---|---|
| §1 の行が違う（main が進んだ） | 中身が同じ場所を探して合わせる。中身が違えば止まって `NEEDS_DECISION:` |
| `tsc` で `conv?.lead_status` の型が `string` 以外（例: 決まった語の並び）で `getKarteLayout` に渡せない | `getKarteLayout` の引数の型は `string \| null \| undefined` のまま。渡す側で型を変えない。通らなければ止まる |
| `renderHeading`・`renderField` の switch で「全部の場合を返していない」と型の見張りが言う | `KarteSectionKey`・`KarteFieldKey` の全部の語に case があるか見る。足りなければ code の .txt と照らす。.txt と違う書き方はしない |
| eslint が `option value="信頼重視"` などを日本語の直書きと言う | 元の行と同じなので除外されるはず。言われたら止まる（直さない） |
| 画面試験（Karte Visual Gate）が基準画像 2 枚だけで落ちる | 想定どおり。§4 の (4) へ |
| 画面試験が基準画像以外で落ちる | その試験の名前と出力を持って止まる。試験を弱めない |
| vitest の別の試験（`InboxKartePanel.discordButtons.test.tsx` 等）が落ちる | 止まる（連絡先タブは変えていないので落ちないはず） |

## 4. 確かめの命令（手元の Mac では回さない・GitHub とクラウドで）

1. `cd frontend && npm ci && npm run generate:icon-sizes && npm run generate:api-types && npx tsc --noEmit` → 0 件。
2. `cd frontend && npx eslint --max-warnings=0 src/pages/inbox/karteLayout.ts src/pages/inbox/karteLayout.test.ts src/pages/inbox/InboxKartePanel.tsx src/pages/inbox/useInboxState.ts` → 0 件。
3. `cd frontend && npx vitest run src/pages/inbox/` → 全部通る。
4. commit・push のあと、Opus が基準画像の作り直しを GitHub に頼む: `gh workflow run karte-gate.yml --ref release/inbox-karte-stage-tabs`。ボットが枝へ画像を commit する。Sonnet はここまでで `DONE` を返す。
5. 確かめ後の残し方: `grep -rn "follow_up_short" frontend/src/pages/inbox/ --include=*.ts --include=*.tsx | grep -v test` が `karteLayout.ts` の 1 行だけ（成約後の段階の一覧が 1 か所だけ）。

## 5. commit

- 1 つの commit で 1〜5 を入れる。文は `feat(inbox): show karte tabs and fields per stage (ADR-1089)`。
- 文は Write でファイルに書き、`git commit -F <file>`。git は 1 回に 1 つ。
- push は `git push -u origin HEAD`。

## 6. 停止したときの報告

- 停止したら、その時点の `git status --short` と止まった命令の生の出力をそのまま添え、`BLOCKED:` の後に理由を1行、または `NEEDS_DECISION:` の後に決めてほしいことを1行で返す。直したつもりで先へ進めない。
- 全部終わったら `DONE:` の後に commit の番号と push した枝を書いて返す。

END OF CARD
