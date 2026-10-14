# design: 検索フォームの CSS 整理（AY-2r）

recon 相互参照: docs/handoff/ay2r-search-bar-css/recon.md
本書は設計書原本（Fable 設計審査 r1 APPROVE、MEDIUM-1/LOW-1〜3 を改訂1で反映）の内容を転記する。対象 ADR: ADR-027 / ADR-067 / ADR-144。実装結果と前後表は docs/specs/design-system/design.md の「AY-2r」節、実測は docs/handoff/design-system-recon/evidence-20260910/ay2r-*。

PO 決定: 2026-10-13「一覧の検索欄は普通の入力欄の型（金型標準 md）」（AY-2p）、2026-10-14「金型への登録を全権限委譲」。

## 1. 目的
components.css の `.search-bar input` が金型の外観（角丸 6px）を上書きしているのを撤去し、検索欄を金型標準に揃える。死にクラス `search-input` と効果のない `field-h-md` も除く。

## 2. 変更契約
| ファイル | 変更前 | 変更後 |
|---|---|---|
| frontend/src/components.css:50-66 | `.search-bar, .filter-bar {margin-bottom}` ＋ disable ＋ `.search-bar input, .filter-bar select {…}` ＋ enable | `.search-bar { margin-bottom: var(--space-4); }` のみ |
| Conditions / ProductCategories / StatusMaster / Suppliers / Units の TextField | className なし | `className="field-w-md"`（他の props は逐語） |
| frontend/src/pages/contacts/ContactsPage.tsx:287 | `className="search-input field-h-md field-w-sm"` | `className="field-w-sm"` |
| frontend/src/pages/companies/CompaniesPage.tsx:389 | `className="search-input field-h-md field-w-md"` | `className="field-w-md"` |
| docs | — | design.md に AY-2q 本番反映記録と AY-2r 節。recon.md・design.md・evidence |

触らない: field-size.css、tokens.css、TextField.tsx、FormField.css、Button、i18n、API、e2e、5 画面の form の style と onSubmit、検索ボタン。

## 3. 基準（受入）
|基準|検証方法|
|---|---|
| 5 画面の検索欄 width=280・radius 6px・height/padding/border/font 差 0 | before/after 実測（幅 1280/1440/375） |
| 5 画面の縦中心差 ≤0.5px | after 実測 |
| Contacts/Companies の検索欄 rect 差 0（computed は min-height のみ変化＝field-h-md 除去の帰結） | before/after 実測 |
| scrollWidth==clientWidth（全画面・全幅） | after 実測 |
| 検索の動作（入力→送信で一覧 API の search パラメータ）が前後一致 | page.route の記録 |
| `filter-bar`・`search-input`（クラスとして）の参照 0、`.search-bar input` 規則 0 | git grep |
| generate・tsc・lint・check:all・test:coverage(maxWorkers=1)・build・build-storybook 成功 | ログ |
| 本番 CSS に `.search-bar input` 0 件、`.content-toolbar .field-w-md` 規則あり | 本番 bundle の grep（反映後） |

## 外部・過去事例の参照と我々への応用
- 過去事例: AY-2p（#4238）で一覧の検索欄を金型標準 md ＋ field-w-md に統一した。今回は同じ型を `.search-bar` の 5 画面と死にクラスに広げる。
- 先行規則: field-size.css:26-28 の `.content-toolbar .field-w-*{margin-bottom:0}` が余白を消すので、新しい規則は足さない。
- 外部事例: 社内金型の適用のみのため不要。

## 維持の仕組み
- 最初の守り手: frontend/src/components/field-size.css（幅・余白の正本。検索欄の幅は `field-w-*` だけで決まる）。
- 補助: scripts/check-ui-governance.js（pages の生 input 検出）、scripts/check-design-token-ratchet.sh。
- 再発の見張り: `.search-bar input` のような要素セレクタ規則は stylelint の no-descending-specificity で目立つ。新設時は金型を上書きしない。

## リスク
- 角丸 4→6px の見た目変化（金型標準に統一、AY-2p と同じ）。戻し方: revert。
- computed の min-width（280px→auto）は規則削除の帰結。描画幅は field-w-md で 280 のまま（rect 差 0）。
- 縦中心差 8→0 は、form が ContentToolbar 内にあり既存の `.content-toolbar .field-w-md{margin-bottom:0}` が効くことで成立する。

## 残件
- `--input-select-min-w`（tokens.css:355）は参照元 0 で孤児化。tokens.css は触らず、別便で削除を判断する。
