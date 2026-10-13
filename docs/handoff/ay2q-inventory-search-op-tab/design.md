# design: 在庫検索バー AND/OR 切替の金型化（AY-2q）

recon 相互参照: docs/handoff/ay2q-inventory-search-op-tab/recon.md
設計書 /tmp/CC報告ファイル/ssot-ay2q/ay2q-design.md（Fable 設計審査 r1 REVISE → r2 APPROVE、2026-10-14）の内容を転記する。実装結果は docs/specs/design-system/design.md の「AY-2q 実装結果」、実測の前後表は docs/handoff/design-system-recon/evidence-20260910/ay2q-before-after.md に記録。

PO 決定: 2026-10-14「y」（AND/OR を金型のタブ型ボタンに置き換え、前後の見た目を記録）。GO は ADR-1003 の委任に基づき Claude Opus が発行する。

## 1. 目的
InventorySearchBar（見積作成・請求書作成で共用）の AND/OR は className なしの生 `<button>` 2個＋inline style（frontend/src/components/InventorySearchBar.tsx:302, :318）。金型 Button に variant="tab" がある（frontend/src/components/buttonAppearance.ts:1,10,32、frontend/src/components/Button.tsx:64）ので、ADR-144 に従い金型へ寄せ、見た目の正本を Button.css に一本化する。

## 2. 変更契約
触るのは frontend/src/components/InventorySearchBar.tsx のみ（製品コード）。docs は docs/specs/design-system/design.md、docs/handoff/ay2q-inventory-search-op-tab/、evidence docs/handoff/design-system-recon/evidence-20260910/ay2q-*。

触らない: Button.tsx / Button.css / buttonAppearance.ts（金型は無改変）、i18n キー、API 呼出（:175）、状態（:104）、e2e。

| 箇所 | 変更前 | 変更後 |
|---|---|---|
| import | — | `import { Button } from "./Button";`（既存の ./TextField の import と同じ形） |
| :272 行 div | gap・alignItems:center | `flexWrap: "wrap"` を追加 |
| :289 群 div の role | `radiogroup` | `group`（子が aria-pressed トグルボタンのため。radiogroup は子に role=radio を要求する。WAI-ARIA APG の toggle button 群と一致） |
| :289 群 div の style | inline-flex・gap 0・border・borderRadius・opacity | opacity を削除（B1）、`flexWrap: "wrap"` を追加（B2）。title・aria-label・testid・border・borderRadius・inline-flex・gap は維持 |
| :302 AND / :318 OR | 生 `<button>`＋inline style・明示 aria-pressed | `<Button variant="tab" active={op === "…"} disabled={opToggleDisabled} onClick data-testid>`。inline style 全廃。aria-pressed は Button.tsx:64 が active から付与 |

実装時の追加1点（設計外・記録）: `type="button"` を Button に付けた。Button に type の既定が無く、両ページとも InventorySearchBar は `<form>` の中（frontend/src/pages/quote-create/QuoteCreatePage.tsx:145、frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:290）。元の生 button は type="button" を持っていたため、付けないと AND/OR の押下でフォームが送信される。

### 想定分岐と結果
- B1（確定）: 群 div の opacity を削除。Button.css:120-123 が各ボタンを減光する。実測: 無効時にボタン 0.6・群 1（二重減光なし）。
- B2（確定）: 行 div と群 div に flexWrap:"wrap"。実測: 1280/1440 は1行のまま、375 は群が検索欄の下の行へ落ち AND と OR が縦2段。scrollWidth==clientWidth、群 right ≤ 行 right を満たす。
- B3（分岐不要）: Button.tsx:40 は className/style のみ Omit。disabled は :52、data-testid は :54,:67 の rest で通る。tsc exit 0。
- B4: `title` は群 div に残す（disabled button はホバーを出さないため子に移さない）。
- B5（解消済み・r3、Opus 判断 2026-10-14）: 幅375 で候補一覧が AND/OR 群に重なっていた。行 div に `rowRef` を付け、recalcDropdownPosition の top だけを `行の bottom + 2` にした（left・width は input のまま。行が取れない場合は input の bottom にフォールバック）。実測: 幅375 で候補 top（quote 752.84 / invoice 824.84）≥ 群 bottom、AND 中心の elementFromPoint は AND 自身。幅1280/1440 は候補 top が変更前と一致（差 0）。

## 3. 見た目の変化
| 項目 | 変更前（実測） | 変更後（実測） |
|---|---|---|
| 選択中 | 紺ベタ rgb(30,58,138)・白文字・weight 400 | 薄青 rgb(235,239,248)・紺文字 rgb(30,58,138)・weight 600 |
| 未選択 | 透明・rgb(26,32,44)・400 | 透明・rgb(74,85,104)・500 |
| hover | 変化なし | rgb(247,250,252)（1280・1440） |
| 高さ | 29px（375 は折返しで 71px） | 36px（375 は 44px、縦2段で群 90px） |
| padding | 4px 10px | 8px 20px |
| focus | ブラウザ既定 `rgb(0,95,204) auto 1px` | 金型 `rgb(26,32,44) solid 2px`・offset 2px |
| 幅375 | ボタン内で文言が2〜3行に折返し（群 73px、検索欄の右隣） | 文言は1行、群は検索欄の下の行、AND と OR が縦2段（各 44px）。枠は行幅いっぱい（279px）、ボタンは左寄せ |
| 無効時 | 枠線ごと 0.6 で減光 | ボタンだけ 0.6、枠線は減光しない |
| ボタン自身の枠 | なし（角 0） | border 1px 透明・角 6px |
| 文字 | 13.33px・ブラウザ既定フォント | 14.4px・継承フォント |
| 群の幅（1280） | 276.4px（検索欄 355.6px） | 323.7px（検索欄 308.3px） |

注記: frontend/src/components/Button.tsx:12 と docs/specs/page-header-v2/design.md:15,50 は tab を「ネイビー」と書くが、CSS 実体の選択色は薄青背景＋紺文字。本表は CSS 実体に従う。

## 受入基準
|基準|検証方法|
|---|---|
| AND/OR 2個が `comp-btn comp-btn--tab` で描画、選択側に `comp-btn--active` | after 実測 JSON（evidence ay2q-after.json）の class |
| aria-pressed: 初期 OR=true/AND=false、2語入力後に AND 押下で反転 | preview 実測を正とする。e2e quote-create-inventory-search.spec.ts:106-117 は無改変。CI の e2e は e2e.yml:207 `if: false` で動かないため、手元で実行できれば実行し、できなければ理由を記録 |
| 1語以下で両方 disabled、2語以上で押せる | after 実測 |
| API の op が切替に追従（op=and / op=or） | after 実測の page.route 記録 |
| AND/OR 部に inline style・色直値 0 | git grep と差分（evidence ay2q-grep.txt、ay2q-diff.txt）、コード審査 |
| 幅1280/1440/375 で scrollWidth==clientWidth、かつ群の right ≤ 行の right | after 実測 |
| 見積作成・請求書作成の前後スクショ（初期・選択後・hover・focus・無効） | before/after 各30枚（/tmp/CC報告ファイル/ssot-ay2q/）、代表16枚を evidence ay2q-* |
| 品質: generate / tsc / lint / check:all / test:coverage(maxWorkers=1) / build / build-storybook | 実行ログ（evidence ay2q-chk-*） |
| 幅375 で候補一覧の top ≥ 群の bottom、かつ AND 中心の elementFromPoint が AND 自身（r3） | after-r3 実測（ay2q-after-r3.json の listbox） |
| 幅1280/1440 で候補一覧の top が変更前と ±1px 以内（r3） | 変更前は input.bottom+2（変更前コード :129、input.bottom は ay2q-before.json）、after-r3 の listbox top と比較 |
| 1語ヒント表示中も候補一覧は行の直下（ヒントに重なるのは変更前と同じ。記録のみ）（r3） | 記録のみ（本便では専用の再測定をしていない） |
| 本番: 反映後の JS チャンク（assets/index-*.js）に、生 button の op style 文字列 `var(--space-1) var(--space-10px)` が 0（CSS は InboxPage.css:154,1022 に同じ文字列があるので対象外） | prod bundle grep |

## 外部・過去事例の参照と我々への応用
- 外部事例: WAI-ARIA APG「Button（toggle button）」。aria-pressed トグルは role=button のまま、まとまりは role=group。radiogroup は role=radio 子要素が前提（APG Radio Group）。応用: 群 div の role を radiogroup から group に変えた。
- 過去事例: frontend/src/pages/company-detail/CompanyDetailPage.tsx:104-119、frontend/src/features/tcg-import-review/ReviewSection.tsx:252 が同じ tab 金型の既存利用。AY-2n（#4223）で同コンポーネントの検索欄を金型化済み。応用: 金型は無改変で使い、見た目の正本を Button.css に一本化した。
- 外部事例の追加調査: 不要（新しい仕組みを入れず、既存の金型を前例と同じ型で使う）。

## 代替案
- A 金型 tab（採用。PO 決定。金型無改変）。
- B 新しい segmented 金型の新設: 金型増殖。ADR-144 は既存金型優先のため不採用。
- C 現状維持＋ui-allow: PO が置換を選択済みのため不採用。

## リスクと戻し方
- 選択中の目立ち方が「紺ベタ」から「薄青」に弱まる。金型の正本色であり CompanyDetailPage 等と統一される。戻し方は本 PR の revert（1ファイル）。
- 用途: page-header-v2 の記述では tab は表示切替・ソート用。AND/OR は検索条件の2択切替として同種に扱う（PO が tab を選択済み）。
- 幅375 の縦2段。候補一覧が AND/OR に重なる件は B5（r3 で解消済み）。

## 維持の仕組み
- 守り手: frontend/src/components/Button.tsx（tab の aria-pressed 自動付与）、frontend/src/components/Button.test.tsx:103（tab・active・aria-pressed の試験）、frontend/tests-e2e/quote-create-inventory-search.spec.ts（AND/OR の aria-pressed 動作。CI では停止中）。
- 守っていないもの: frontend/scripts/check-ui-governance.js は生 `<button>` を検出しない（別テーマ。本便では拡張しない）。e2e は CI で停止中（e2e.yml:207）。
- 切戻し: 本 PR の merge commit を revert（DB 影響なし）。

## 関係する ADR
- ADR-144（UI ガバナンス・金型優先）: 生 button を金型へ移す根拠。docs/adr/ADR-144-ui-component-governance.md、docs/CC_UI_GOVERNANCE.md。
- ADR-067（デザイントークン）: 色・px 直値の追加なし。docs/adr/ADR-067-design-token-enforcement.md。
- ADR-027（UI 国際化）: 既存キーのみ。docs/adr/ADR-027-ui-internationalization.md。
- ADR-1003（GO の委任）: GO は Claude Opus が発行。docs/adr/ADR-1003-go-delegation-to-opus.md。
- 相互参照: recon は docs/handoff/ay2q-inventory-search-op-tab/recon.md。

Architect 審査（AY-2q）: Fable 設計審査 r1 REVISE（HIGH 1・MEDIUM 1・LOW 4）→ r2 APPROVE（LOW 2 は記録のみ）、2026-10-14。Fable は AI の審査で、PO 承認や人のレビューではない。
