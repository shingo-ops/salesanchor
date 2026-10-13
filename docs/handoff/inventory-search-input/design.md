# design: 在庫検索バー（InventorySearchBar）の入力欄の標準化（AY-2n）

recon 相互参照: docs/handoff/inventory-search-input/recon.md
以下は設計書 ay2n-design.md の内容をそのまま転記する。実装結果は docs/specs/design-system/design.md の「AY-2n 実装結果」に記録。

#### AY-2n 在庫検索バー（InventorySearchBar）の入力欄の標準化（2026-10-13）

mode: handoff。§AY の一行入力を金型へ移す便の続き。PO 原文（2026-10-13、本セッション）「後で反映させるので並行して進めている金型の部品に置き換える作業を進めてくれ」。GO は ADR-1003 の委任に基づき Claude Opus が発行する。

現在地（origin/main 5cb680d05。調査全文は /tmp/CC報告ファイル/ssot-ay2n/recon-raw.md）:
- 対象は frontend/src/components/InventorySearchBar.tsx:272-287 の生 `<input type="text">` 1件。請求書作成（InvoiceCreatePage.tsx:410-414、testIdPrefix="invoice-add-search"）と見積作成（QuoteCreatePage.tsx:259-263、"quote-add-search"）の2画面に出る共有部品。2画面とも外側の div で幅 `min(100%, 40rem)`。
- input の style は :285 `{ flex: 1, minWidth: "var(--min-width-input-sm)", padding: "var(--space-6px) var(--space-2)" }`（px 直書き0、トークンのみ）。className なし。
- ref: inputRef（:119）を :126-127 で getBoundingClientRect（候補一覧の位置と幅）、:152 で contains（外側クリック判定）に使う。
- 金型: TextFieldControl（frontend/src/components/TextField.tsx:41-54）は forwardRef で ref を input に渡せる。ラベル付きの TextField（:57）は ref を受けないため使えない。
- variant: "search"（FormField.css:359-377）は左に虫眼鏡アイコンを重ねる前提の左余白（約 36px）を持つ。InventorySearchBar にはアイコンが無い。既存の search 利用は InboxConversationList.tsx:75 だけで、アイコンを `.inbox-search-icon` で重ねている。
- 試験: 単体試験の参照0。e2e tests-e2e/quote-create-inventory-search.spec.ts:94-133 が testid（-input・-op-and・-op-or・-result-N）、placeholder 属性、aria-pressed、fill に依存。stories 3件は testid 非依存。
- 横の AND/OR の切り替え（:288-330、生 `<button>` 2つ）は、2択切り替えの金型が無く、check-ui-governance.js も `<button` を検出しない（:332 は select・input・tab）。

設計判断（設計者、2026-10-13）:
- 金型は TextFieldControl の standard・md（size 指定なし）。理由: 一般フォームは標準の見た目（PO 方針、AY-2m と同じ）。search 変種はアイコン前提の左余白を持つため、アイコンの無いこの欄では余白だけが広がる。アイコンを足すのは見た目の追加になるので本便ではしない。
- inline style は配置の `flex: 1` と `minWidth: "var(--min-width-input-sm)"` だけ残し、外観の `padding` は消す（金型の余白に任せる）。
- AND/OR の切り替えは本便の対象外（2択切り替えの金型の新設は PO 許可が要る＝docs/CC_UI_GOVERNANCE.md:14。CI の検出対象でもない）。残件として記録する。
- 候補一覧（portal）・ドロップダウンの位置計算・JS 内の px 計算（:363-368）も対象外。

AY-2n 変更契約:
1. InventorySearchBar.tsx:272 の `<input` を `<TextFieldControl` に置換（自己終了の形はそのまま）。ref・type・value・onChange・onFocus・onKeyDown・disabled・placeholder・data-testid・aria-label は逐語で保持し、属性の順も変えない。style は `{{ flex: 1, minWidth: "var(--min-width-input-sm)" }}` にする（padding を削除）。
2. import に `import { TextFieldControl } from "./TextField";` を追加（既存の並びに合わせる）。
3. 変えないもの: AND/OR の切り替え、候補一覧、位置計算、InvoiceCreatePage・QuoteCreatePage、金型本体、CSS、トークン、i18n、試験・e2e、backend。既存の試験が落ちたら試験を直さず止まって報告。
4. design.md に AY-2m の本番反映の記録、本節、実装結果を追記。

前後表（予定。実画面で確定）:
| 対象 | 変わる項目 |
|---|---|
| 検索欄 | 余白 var(--space-6px) var(--space-2) → var(--space-2) var(--space-3)、文字 → var(--font-base)、枠 1px var(--border)・角 var(--comp-input-radius)・背景 var(--bg-surface)・フォーカス時の枠色（金型の standard） |
| 欄の幅・並び・候補一覧の幅 | 変化なし（実測で確認） |
| AND/OR の切り替え・候補一覧 | 変化0 |

受入:
| 基準 | 検証方法 |
|---|---|
| 金型に変わる | 開発モードの build と preview（偽ログイン・API モック）で /quotes/new と /invoices/new を幅1280・1440で開き、検索欄に class comp-field__input があることを DOM で記録。変更前と変更後のスクリーンショット（DPR2、検索欄と AND/OR と候補一覧が見える状態） |
| 並び・幅 | 検索欄と AND/OR の切り替えの getBoundingClientRect（top・left・width・height）を前後で JSON に記録。検索欄の幅の差が ±2px 以内、AND/OR の位置の差が ±2px 以内（高さは金型の余白で変わってよい。値を記録） |
| 候補一覧 | 「ポケモン」等の2語を入力して候補一覧を開き、一覧の left・top・width を前後で記録。left と width の差 ±2px 以内、top は検索欄の下端+2px のまま（:126-127 の計算どおり） |
| 外側クリック | 候補一覧を開いた状態で検索欄の外を押すと閉じ、検索欄の中を押しても閉じないこと（前後で同じ） |
| 試験 | 単体試験の全件成功。e2e quote-create-inventory-search.spec.ts を実行（実行できない場合は理由を記録）し成功。testid・placeholder・aria-pressed の保持を grep で確認 |
| 品質 | generate 後の tsc、lint、check:all、test:coverage（maxWorkers=1）、build、build-storybook、CI 必須がすべて成功 |
| 本番 | Deploy 成功。本番 JS の該当チャンクに comp-field__input と testIdPrefix の "-input" がある。app と /api/health が 200 |

外部事例: 不要（既存の金型 TextFieldControl を前例 AY-2k・AY-2m と同じ型で使う）。

維持の仕組み:
- 守り手: tests-e2e/quote-create-inventory-search.spec.ts、TextField.test.tsx、scripts/check-ui-governance.js、frontend-check。
- 守っていないもの: AND/OR の生 button 2つ（2択切り替えの金型が無い）、InventoryPicker.tsx:218 の同じ型の生 input（別の便）、FedExRateModal の API エラー以降の px 直書き。
- 切戻し: 本 PR の merge commit を revert（DB 影響なし）。

改訂 1（2026-10-13、Fable 設計審査 REVISE への対応。上の記述より優先）:
- HIGH（受入の AND/OR の位置）: 金型の余白で検索欄の高さが約 29→約 39.6px に変わり、親が alignItems:center のため AND/OR の top は下がる（設計どおり）。受入の「並び・幅」を次に書き換える: 検索欄の left・width と AND/OR の left・width の差が ±2px 以内。AND/OR の縦の中心と検索欄の縦の中心の差が前後とも ±2px 以内（中心がそろったまま）。top と height は値を記録するだけ。
- MEDIUM（AND/OR を対象外にする理由）: 「2択切り替えの金型が無い」は不正確。Button の variant="tab"（Button.tsx:7,30,55,65、active で aria-pressed。用途は表示切替・ソート＝page-header-v2/design.md:15,50）がある。AND/OR に使うと切り替えの見た目が変わる（枠で囲んだ2つ並びから tab の見た目へ）ため、前後表と PO の確認が要る別の便とする。本便では触らない。
- MEDIUM（e2e が CI で動かない）: .github/workflows/e2e.yml:207 で Playwright のジョブは `if: false`、:104-105 に arm64 で chromium が動かない記載。受入に preview での代替の観測を足す: 2語を入力して AND を押すと and の aria-pressed=true・or=false、候補を1つ選ぶと見積の明細（quote-item-row-1-name）に値が入る（請求書は invoice-item-row-1-name 相当の testid を実物で確認して同じ観測）。e2e は手元で実行できれば実行し、できなければ理由を記録する。
- LOW（方針との対応）: design.md:2391「一般フォームは標準・検索バーは種類登録」は、AY-2a（:2411-2412）で search 変種を受信箱の検索（G32 .search-input-field）に限ったもの。InventorySearchBar はその組に無く、アイコンも無いので standard にする。
- LOW（前後表）: 前後表に font-family（ブラウザ既定→inherit）、line-height（normal→var(--line-height-base)）、高さ（約29→約39.6px、実測で確定）を足す。
- 受入の前提（再審査 r2 の注記）: /invoices/new は既定 mode="quote"（InvoiceCreatePage.tsx:75）で検索欄が出ない（:252）。`data-testid="invoice-mode-inventory"`（:239）を押してから観測する。候補選択の観測は引き継ぎなし（空行1件）で開く前提で、選んだ候補は見積は `quote-item-row-1-name`、請求書は `invoice-item-row-1-name`（InvoiceCreatePage.tsx:355）に入る。

Architect 審査（AY-2n）: 1回目 REVISE（Fable、HIGH 1・MEDIUM 2・LOW 2）→ 改訂1 → 2回目 APPROVE（2026-10-13）。Fable は AI の審査で、PO 承認や人のレビューではない。
