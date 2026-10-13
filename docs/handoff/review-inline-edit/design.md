# design: 要確認の一覧で、件を開かずに各行で直す

- 状態: 設計案（Opus 作成・自己審査。コード審査は Fable）
- PO の決定（原文）:
  - 2026-10-13「非エンジニアが触るのでIDではなくテキストでプルダウンを選択して修正することは可能？アプリ上でやったほうが良い」
  - 一覧の各行で直す形：「y」
  - 新しい型の登録：「y」（「名前を入れると候補が出て選べる部品」を新しい型として登録してよいか）
- 現在地: [recon.md](recon.md)（docs/handoff/review-inline-edit/recon.md）
- 対象ADR: ADR-144（金型）、ADR-027（i18n）、ADR-067（デザイントークン）

## 1. 目的（利用者に見える変化）
要確認の一覧（本番の確認待ちのタブ）の各行に、次の2つが付く。
- 「商品」の欄：名前の一部を入れると候補が出る。選ぶと、その場で保存される。
- 「このままで良い」ボタン：押すと、その場で保存される。

保存の結果（保存中・保存済み・エラー）は、その行に出る。件を開いて直す今までの画面は、そのまま残す。

## 2. 対象と対象外
- 対象：v102 の件（is_v102=true）の行だけ。v102 でない行には、操作を出さない。
- 対象外：
  - 状態の確定
  - 書き写しの直し
  - 商品の新規登録
  - 件を開いた画面の作り直し（ProductMasterDrawer の手作りの部品の置き換えは、別の課題）

## 3. 置き場と配線（SSOT）
- 保存先と API は、今の画面と同じ：
  - 商品：POST /tcg/items/{id}/corrections（field_name='product_id'・system_value=今の product_uuid・human_value=選んだ product_uuid）
  - このままで良い：POST /tcg/items/{id}/review-ack
- API を呼ぶ処理を、新しい小さなファイル `reviewActions.ts`（frontend/src/features/tcg-analysis-review/）にまとめる。行の操作と、件を開いた画面（ReviewItemDrawer の「このままで良い」、ProductMasterDrawer の ProductAssignSection の保存）の両方から使う。送る中身の正本を1か所にする。
- 商品の候補は GET /tcg/products/search?query=（有効な商品・名前の部分一致・最大10件）を使う。新しい API は作らない。

## 4. 変更（PR 1つ。frontend のみ）
1. 新しい金型 `AsyncCombobox`（frontend/src/components/）
   - 作るもの：`AsyncCombobox.tsx` と `AsyncCombobox.css`（色・余白・重なりは var() のトークンだけ）と `AsyncCombobox.stories.tsx`。
   - 作りは CountryCombobox と同じ：TextFieldControl の入力、role="listbox" の一覧、role="option" のボタン、矢印キー・Enter・Esc の操作。
   - props：id、ariaLabel、value（表示する文字）、placeholder、disabled、loadOptions(query) => Promise<{value,label}[]>、onSelect(option)、minChars（既定1）、debounceMs（既定300）、noResultsText、loadingText。
   - 文字は呼ぶ側が t() で渡す。部品の中に文字を直書きしない。
   - 表のセルに置いたとき、一覧が表の枠で切れないことを確かめる。DataTable.css の overflow を読んで判断する。切れる場合は、推測で直さずに止めて報告する。
2. `reviewActions.ts`：postProductCorrection(item, productUuid) と postReviewAck(item, codes)。
   - 送る中身は、今の ProductMasterDrawer と ReviewItemDrawer と同じ。
   - 今の2つの画面も、これを使う形に変える。画面の動きは変えない。
3. `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx`（本番の確認待ちのタブ）に「直す」の列を足す。
   - 「商品」：AsyncCombobox を置く。候補は「商品名」で表示し、値は product_uuid。選んだら postProductCorrection を呼ぶ。
   - 「このままで良い」：Button（size="sm"）を置く。その行の review_reason_details のうち ackable が false でない理由を全部まとめて、postReviewAck で送る。外せる理由が無い行には出さない。
   - 行の操作は、行のクリック（件を開く）に伝えない。
   - 行の結果は Badge で出す（成功＝保存済み、失敗＝エラーとその理由）。保存中は、ボタンの loading と、入力の disabled で表す。文字はすべて t()。
   - 保存のあとの読み直しでは、表を消さない。今の行を出したまま取り直す（今は setData(null) で一度消えている）。
4. i18n：ja.json と en.json に同じ鍵を足す。
5. 試験（vitest）
   - AsyncCombobox：入力から候補、選択、キー操作、0件、読み込み中、文字が props からだけ出ること。
   - 行の操作：送る中身、行のクリックが起きないこと、外せる理由が無い行にボタンが無いこと、v102 でない行に操作が無いこと、結果の Badge。
   - reviewActions：2つの画面の今の試験が、変えずに通ること。
6. frontend/CLAUDE.md の決まり：UI の文字を変えたら tests-e2e を同じ PR で直す。該当の e2e があるかを確かめ、あれば直す。

## 5. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| 1. 新しい型が決まりどおり（tsx・css・stories、css は var() のみ、文字の直書きなし） | CI（stories の数・ダークモード・UI governance・i18n） |
| 2. 行で商品を選ぶと、今の画面と同じ中身で保存される | vitest（送る中身の一致） |
| 3. 「このままで良い」は外せる理由だけを送る | vitest |
| 4. 今の2つの画面の動きが変わらない | 今の試験が変えずに通る |
| 5. 本番に反映される | 本番の画面の bundle に新しい鍵がある |
| 6. 本番で実際に1件を直せる | PO の操作で確かめる（画面はログインと二段階認証が要るため、Opus は操作できない） |

## 6. 危険と対処
- 誤って押す：商品は候補から選んだときだけ保存する。打っている途中の文字では保存しない。
- 一覧が表の枠で切れる：作る前に確かめ、切れるなら止めて相談する。
- 戻し方：この PR を revert。保存済みの記録は、今の画面で直した記録と同じ扱い。

## 7. 維持の仕組み
- 守り手: AsyncCombobox の試験と stories（stories の数の検査）、reviewActions の試験。

## 8. 外部・過去事例の参照と我々への応用
- 社内の前例：CountryCombobox・ChannelTypeCombobox（同じ作り）。DataTable のセルに Button を置いた前例（BotsPage・CompaniesPage・TeamsPage）。
- 外部事例：WAI-ARIA の combobox の作り（role=listbox・option・キー操作）。前例の部品が、すでにこれに沿っている。

## 9. 審査（Opus 自己審査）
- 判定: APPROVE。
- 根拠：
  - 保存の中身の正本を1か所に寄せる。
  - 新しい型は PO 許可済みで、決まりの作法どおり。
  - API・DB は変えない。
- 未解決：表の枠で一覧が切れるか（実装の最初に確かめる）。

## 10. 実装で決めた点

設計 §4-1 は「作りは CountryCombobox と同じ」としていた。実装では、候補の一覧の描き方だけがそこから外れる。

- 事実（実測）: `frontend/src/components/DataTable.css:12-18` の `.comp-table` は `overflow-x: auto`。CSS の仕様では、片方が `auto` のとき、もう片方の `visible` も `auto` になるので overflow-y も `auto` になる。実際の Chromium で、`.comp-table` と同じ CSS の表の一番下の行に position:absolute の一覧（高さ 240px）を置くと、枠の `clientHeight` 144 に対して `scrollHeight` 371 となり、枠の外には出ずに枠の中のスクロールになる（枠の下端より下を調べると一覧ではなく枠の外の要素が取れる）。つまり CountryCombobox の作り（`frontend/src/components/CountryCombobox.tsx:145-161` の position:absolute）のままでは、表の下の行で一覧が切れる。
- 判断: 一覧を `document.body` 直下に Portal で描き、`position: fixed` で入力欄の位置に合わせる。スクロール（capture）とリサイズで位置を取り直し、下に収まらなければ上に開き、画面の左右からははみ出さない。
- 既存の金型の再利用: `frontend/src/components/Popover.tsx` は Portal を持つが、次の理由で使えなかった。位置は開いたときの 1 回だけ計算しスクロール・リサイズに追従しない（`Popover.tsx:97-107`）。`position:fixed` なのに `window.scrollY` を足している（`Popover.tsx:50-67`）。トリガーのクリックで開閉が切り替わる（`Popover.tsx:125`）ため入力欄のフォーカスと合わない。パネルが入力欄の幅に合わない（中央寄せ）。Popover 自体は変えていない。
- 設計との違い: 一覧の描き方（Portal＋fixed）だけ。入力欄・role="listbox"・role="option"・キー操作・文字を props で受ける点は設計どおり。
- 設計に足した点（props）: 候補の取得に失敗したときの文字 `errorText`（省略可・省略時は noResultsText）。黙って捨てないため。
- 行の「このままで良い」ボタンには、行ごとの読み上げ名（`needsReview.inline.ackAria`）を付けた。件を開いた画面の同名のボタンと、読み上げ名が重ならない（既存の試験を変えずに通すためでもある）。
- 保存のあとの読み直しは、`reloadKey` だけが変わったときに表を消さない（ページ送り・タブ切替のときは今までどおり消す）。
