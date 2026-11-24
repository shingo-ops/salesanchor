# 設計審査（architect 1回目）: 受信箱のカルテを段階で切り替える（ADR-1089）

- 審査した物: `origin/release/inbox-karte-stage-tabs`（`cae9b4b21`）の `docs/adr/ADR-1089-inbox-karte-stage-layout.md`、`docs/handoff/inbox-karte-stage-tabs/` の `recon.md`・`design.md`（本審査では読んでいない）・`impl-card.md`・`code/` の 4 ファイル
- 照らした実物: `origin/main`（`71cae5cb7`）の `frontend/src/pages/inbox/InboxKartePanel.tsx`・`useInboxState.ts`・`inbox.types.ts`、`frontend/tests-e2e/karte-visual-gate.spec.ts`・`karte-screenshot-compare.spec.ts`・fixtures、`frontend/eslint.config.js`・`frontend/tsconfig.json`
- 製品コード・DB・本番・secrets には触れていない（読むだけ）。

## 判定: REVISE（直す点は R1 の 1 つだけ。設計の中身は合格）

1. 設計の中身（表・renderField・e2e 差し替え）は、元の実物と項目ごとに一致した。入力欄の JSX・保存・選択肢・金型の落ちは見つからなかった。
2. ただし impl-card §4(5) の確かめ命令は、書かれた期待（1 行だけ）どおりには決して出ない（実際は 2 行）。実装役が「落ちた」と見て止まる罠なので、直す。
3. 他は軽い指摘（L1〜L4）のみ。R1 を直せば APPROVE できる。

## R（直さないと正しく進めない物）

### R1. `impl-card.md` §4 の (5) の期待が合わない

- 場所: `docs/handoff/inbox-karte-stage-tabs/impl-card.md` §4 の項目 5（`grep -rn "follow_up_short" frontend/src/pages/inbox/ --include=*.ts --include=*.tsx | grep -v test` が `karteLayout.ts` の 1 行だけ）。
- 事実: `origin/main` の `frontend/src/pages/inbox/inbox.types.ts:25` に `{ key: "followup", labelKey: "inbox.tabFollowUp", statuses: ["follow_up_short", "follow_up_long"] }` がある（受信箱の左の一覧の絞り込み。今回は触らない）。`grep -v test` は行の中身で除くので、このパスの行は除かれない。実装後は `inbox.types.ts:25` と `karteLayout.ts:114` の 2 行が出る。
- 直し方: §4(5) を「`useInboxState.ts` に `follow_up_short` が残っていない（`grep -n "follow_up_short" frontend/src/pages/inbox/useInboxState.ts` が 0 件）。出るのは `inbox.types.ts`（一覧の絞り込み・対象外）と `karteLayout.ts` の 2 か所だけ」に書き換える。ADR-1089 受入条件の「置き場所の表が書かれているのは `karteLayout.ts` の 1 か所」は「カルテの置き場所の表」の意味で、一覧の絞り込みとは別。ADR 本文は直さなくてよい。

## 見る点ごとの結果

### (1) impl-card §1 の行番号と origin/main

| §1 の行 | 実物 | 結果 |
|---|---|---|
| InboxKartePanel.tsx:1 | `import { useEffect, useId, useRef, useState } from "react";` | 一致 |
| :8（足す位置） | `import type { LeadDetail, KarteTabKey, ... } from "./inbox.types";` | 一致（9 行目の前に足す） |
| :124 | `const stagePresentation = leadDetail ? getStatusPresentation(...)` | 一致 |
| :228-238 | 228 コメント〜238 `</div>` | 一致（カード本文は 229-238 と 228-238 が混在。実害なし） |
| :242 | `tab={karteTab}` | 一致 |
| :554 | `// === COMPANY TAB — ADR-110 ...` | 一致 |
| :717-720 | 717 は `onBlur={handleCardFieldBlur} placeholder=...`（textarea の途中）。`</div>`・`);`・`}` は 718-720 | 1 行ずれ（L1） |
| useInboxState.ts:655-663 | 655 コメント〜663 `}` | 一致 |
| useInboxState.ts:43（import の次） | 43 は `import type { ConvertAssigneeOption, ... } from "./inbox.types";` | 一致 |
| karte-visual-gate.spec.ts:126/167/178/231/270/349 | 各 test・describe の始まり | 全部一致 |

差し替えの範囲も一致: A=126-138・B=167-175・C=178-268・D=272-287 の 273-274 行・E=349-382（全部 `origin/main` の行と照合済み）。

### (2) renderField が元 554-720 の JSX を落とさず写しているか

項目ごとに `KarteTabContent-body.tsx.txt` と元の行を照らした。

| 項目 | 元の行 | 写し | 結果 |
|---|---|---|---|
| nickname | 560-565 | body 38-45 | 一致（値・onChange・onBlur・placeholder） |
| country | 566-571 | 47-54 | 一致 |
| customer_type | 572-580 | 56-66 | 一致（option 2 つの日本語の値と t() キー） |
| target_titles | 584-589 | 68-75 | 一致（placeholder は `leads.targetTitlesPlaceholder`） |
| sales_form | 590-598 | 77-87 | 一致（`right-panel-row--multiselect`・`sales_form_options`・`sales_form_selections`） |
| next_action + 日付 | 628-639 | 90-103 | 一致（`karte-field-empty`・`type="date"`・`|| null`） |
| response_speed | 640-649 | 106-117 | 一致（3 つの option） |
| temperature | 653-662 | 119-130 | 一致 |
| challenge | 663-666 | 133-139 | 一致 |
| competitor_check | 667-679 | 141-155 | 一致（`competitorValue`・`setTimeout(handleCardFieldBlur, 0)`・onBlur 無しも元と同じ） |
| estimated_scale | 683-692 | 157-168 | 一致 |
| amounts（3 欄） | 693-710 | 171-191 | 一致（`type="number" min="0"`・`|| null`） |
| meeting_memo | 713-717 | 194-200 | 一致 |
| performance | 600-605 | 24-29（見出し）・202 | 一致（鍵の印・`karte-lock-icon`・`karte-section-ro-heading`） |
| cs_memo | 607-612 | 205-210 | 一致 |

- 見出し 8 つの `t()` キーは元と同じ。新しく付けた `data-testid`（`karte-field-*`・`karte-section-next-action/analysis/scale/memo-heading`）は元に無く、足すだけ（既存の試験を壊さない）。
- 型: `KarteSectionKey`（8 語）・`KarteFieldKey`（15 語）の switch は全部の語に case がある。`tsconfig.json` に `noImplicitReturns` は無く、`strict` の範囲で通る見込み（未確認: tsc は実行していない）。連絡先タブは `if (tab === "contact") return` の後で型が絞られるため `fields[tab]` は `"company" | "deal"` で引ける。`InboxKartePanel.discordButtons.test.tsx:27-45` は `tab="contact"` だけで、連絡先は変えないため影響しない（`getKarteLayout(leadDetail.status)` は contact の早い return より後）。

### (3) karteLayout.ts と ADR-1089 What 1・What 3

- リード（`karteLayout.ts:60-69`）: 呼び名・国・取り扱いタイトル・販売形態・次回アクション・返信速度・温度感・想定規模 ＝ 表の「リード＝商談」に一致。顧客タイプ・課題・競合・金額・商談メモ・実績・CS は無い ＝ 表の「出さない」に一致。
- 商談中（:71-81）: 表の「商談中＝商談」の項目すべて・実績サマリーと CS は無い。一致。
- 成約後（:83-96）: 顧客タブ＝呼び名・国・顧客タイプ・タイトル・販売形態・次回アクション・実績サマリー・CS、商談タブ＝返信速度・温度感・想定規模・課題・競合・金額・商談メモ。表の「顧客」と「商談（記録）」に一致。タブ順 `company, contact, deal`・最初は `company`（`tabs[0]`）。
- その他（:99-112）: 元の置き場所（元 `InboxKartePanel.tsx:554-615` が顧客タブ、`:617-720` が商談タブ）と一致。タブ順 `deal, company, contact`。ADR What 3 と同じ。
- 段階の対応（:114-121）: `lead`・`negotiating`・`existing_customer`/`follow_up_short`/`follow_up_long`、他は `OTHER`（`lost`・`out_of_scope`・null・空）。ADR What 2 と一致。
- 見出しの並び（:39-48）: ADR What 7 の 8 つ・順序と一致。返信速度は `analysis` の先頭（:43）で What 7 のとおり。
- 懸念: `useInboxState` の既定タブは会話一覧の `lead_status`、`InboxKartePanel` の見せ方は `leadDetail.status`（別の元）。食い違う一瞬は `resolveKarteTab` が受ける（ADR What 6）ので問題なし。

### (4) e2e の差し替え A〜E

- fixtures の `status`（`frontend/tests-e2e/fixtures/karte-lead-*-with-deal.json:4`）: shinki=`lead`、shoudanchuu=`negotiating`、kisonkosaku=`existing_customer`、oikomi=`follow_up_short`（no-deal も同じ）。想定どおり。`karte-visual-gate.spec.ts:73-75` のコメントの「新規」は古い書き方で、実際の値は内部の名前。
- A: 元の「3 つ・deal/company/contact」を、段階ごとの 3 本（2・2・3 のタブ）に分けた。弱めていない（個数と順序を data-testid で見る点は同じ）。
- B: 元はリードで顧客タブを押していたが、リードに顧客タブが無くなるので成約後の見本に替えた。意味（鍵の印が見える）は同じ。
- C: 元の「商談タブに顧客の項目が出ない」（ADR-108-1・5 本）は、リードでは出るようになる決定（ADR-1089 What 1）に反するので置き換えが正しい。新しい試験は 17 項目 × 段階 4 つ（リード・商談中・成約後の 顧客タブ/商談タブ・追い込み）で、「出る」と「無い（`toHaveCount(0)`）」の両方を確かめるので、元より強い。元の 4 つの見出しの試験は 5 つの見出しを回す 1 本にまとまり、見出しの数が増えた（`karte-section-next-action-heading` を含む）。`[ADR-1089-7]` で成約後の商談タブに「次のアクション」見出しが無いことも確かめる。意味は弱まっていない。
- D: 2 行を 1 行（`leadKisonkosakuNoDeal`・最初から顧客タブ）に替えるだけ。`leadShinkiNoDeal` は未使用になるが、`tsconfig.json` は `include: ["src"]`・`noUnusedLocals: false` で、元から `leadShoudanchuuNoDeal`・`leadOikomiNoDeal` も未使用なので問題なし。
- E: 元の 3 タブを順に押す形を、出ているタブを全部押す関数にし、リードと成約後の 2 見本に広げた。弱めていない（広げた）。日本語の直書きには `eslint-disable-next-line` が付いている。
- 変えない試験（Default tab・Contact tab・visual regression）: `[ADR-108-4]`（shinki/shoudanchuu=deal、kisonkosaku/oikomi=company が active）は新しい配置でも通る。視覚の 2 本は `karte-tab-deal`（リード）・`karte-tab-company`（成約後）を押す先がそれぞれ存在する。
- `karte-screenshot-compare.spec.ts:90-114` も、リードは deal・成約後は company を押すので通る（手動実行のみ）。

### (5) tsc・eslint で落ちる書き方

- `no-japanese-literal`（`frontend/eslint.config.js:31` は `warn`、`--max-warnings=0` なので警告も落ちる）: 新しい `.tsx` の日本語は `<option value="信頼重視">` など `<option value>` だけで、ルールは `<option value>` を除外する（`frontend/scripts/eslint-rules/no-japanese-literal.cjs:61-66`）。`karteLayout.ts` の日本語はコメントだけ。`karteLayout.test.ts.txt:1` はファイル全体で disable 済み。落ちる書き方は見つからなかった。
- `Fragment` を import（カード §2 (a)）し、`KarteTabKey` は `InboxKartePanel.tsx:8,58` でまだ使われるので「未使用 import」は出ない。
- `tests-e2e` は `tsconfig.json` の `include: ["src"]` の外。

## L（軽い指摘・直さなくても進められる）

- L1. `impl-card.md` §1 の「717-720」は、`</div>`・`);`・`}` が 718-720。717 は textarea の途中の行。「718-720」に直すと正確。§2 (f) の置き換え範囲「554〜720」は正しい。
- L2. 失注・対象外（OTHER）の e2e は無い（fixtures に失注の見本が無い）。vitest（`karteLayout.test.ts.txt:55-70`）が表を固定しているので受入条件「失注・対象外は今と同じ」は守られるが、画面側は未確認。次の工事で fixtures を足すのがよい。
- L3. `impl-card.md` §4 の命令に e2e（`npx playwright test karte-visual-gate.spec.ts`）が無い。基準画像 2 枚は GitHub で作り直す設計（§4(4)）で、それ以外の試験は CI が走らせる。実装役の手元の確かめに足すなら、クラウドで playwright を回す 1 行を足すとよい（なくても CI で落ちる）。
- L4. `ADR-1089` の「Amends」行は ADR-108 の受入条件を「103〜106 行目」と書く。`docs/adr/ADR-108-inbox-karte-panel-redesign.md` の行は今回は照らしていない（未確認）。

## Opus の対応（2026-11-24）

- R1: `impl-card.md` §4(5) と `design.md` K7 を直した。実物の照合: `git grep -n "follow_up_short" origin/main -- frontend/src/pages/inbox/ ':!*.test.*'` が `inbox.types.ts:25` と `useInboxState.ts:658` の 2 行。実装後は `useInboxState.ts:658` が消え `karteLayout.ts` が増えるので、直した期待（2 ファイル・`useInboxState.ts` と `InboxKartePanel.tsx` は 0 件）と合う。直しは期待の文だけで、設計の中身は変えていないため、審査の残りは本審査の結果（設計の中身は合格）をそのまま使う。
- L1: §1 を 718-720 に直した。L4: ADR-108 の受入条件は 102〜105 行目（実物で照合）に直した。
- L2・L3: 今回は直さない。L2（失注の画面試験）は次の工事の候補。L3 は CI の Karte Visual Gate が流す。
- 判定: R1 を直したので設計合格（APPROVE）として実装に進む。
