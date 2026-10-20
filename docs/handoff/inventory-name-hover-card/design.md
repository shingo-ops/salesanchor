# 設計: 在庫表の商品名が切れているときだけ、名前の上にカードを浮かせて全文を見せる（第1版）

- PO 決定（2026-10-20）
  - 「1」: 吹き出し案で入れる。
  - 「省略されているときだけ」出す。
  - 「吹き出しじゃなくてカード」にする。
  - 「カード版でこの仕様で決定」。
  - A/B の確認に「1」で、A（名前の上に浮く四角いカード）に決定。
- 見本: https://claude.ai/artifact/2exG5Mcd8izucWpGhDwyM3（上の表 A が決定版）。
- recon: docs/handoff/inventory-name-hover-card/recon.md
- 対象 ADR: ADR-1014（在庫表の見え方）、ADR-067（トークン）、ADR-144（金型の先確認）。

## 1. 目的・利用者に見える変化
- 変更前: 商品名が「…」で切れているとき、全文はブラウザ標準の小さな黄色い帯（title）で出る。出るまでに約1秒かかり、PO の評価は「昔のパソコンぽい」。
- 変更後: パソコン幅（768px 以上）で、切れている商品名にマウスを乗せると、150ms 後に名前の上へ角の丸いカードが出る。
  - カードは後ろが少し透けるすりガラスで、少し拡大しながらふわっと現れる。
  - 日本語名は太字で1行、英語名は小さく薄く1行。どちらも折り返さない。
  - 隣の行の名前へ移ると、カードは消えずにそのまま滑って移る。
  - 切れていない名前（全部見えている名前）では、何も出ない。
- 対象は、アプリの在庫表・閲覧ページと、スプレッドシートの在庫一覧（GAS）。
- スマホ幅（767px 以下）は、名前が折り返されて切れないので、カードは出ない（今と同じ）。

## 2. 根拠（recon: docs/handoff/inventory-name-hover-card/recon.md）
- 既存の Tooltip 金型は、文字列1つ・黒い帯・2段表示不可（recon §2）。Popover はクリック式（recon §2）。どちらもそのままでは使えない。
- ADR-144 に従い、在庫表専用の部品ではなく、使い回せる金型 `HoverCard` を components/ に新設する。
- 色・影・角丸・動きは既存トークンで足りる（recon §4）。新しく作るトークンは2つだけ。
  - easing の行き過ぎ（overshoot）用: 既存に無い。
  - ぼかしの強さ: 既存に無い。値 12px は schedule.css:1167 の前例と同じ。

## 3. 変更内容

### 3-1 トークン
frontend/src/tokens.css に、色ではない値を2つ足す。ダーク版は不要。
```css
/* :153 --ease-exit の直後 */
--ease-pop: cubic-bezier(0.2, 0.9, 0.3, 1.15);   /* 少し行き過ぎて戻る。浮くカードが出るとき */
/* :436-438 --comp-inventory-* の直後 */
--comp-hover-card-blur: 12px;   /* 浮くカードのすりガラスの強さ（schedule.css の前例と同じ値） */
```
docs/adr/ADR-067-design-token-enforcement.md のトークン表に、この2行を足す。

### 3-2 金型 HoverCard（新規）
新しく作るファイル:
- frontend/src/components/HoverCard.tsx
- frontend/src/components/HoverCard.css
- frontend/src/components/HoverCard.test.tsx
- frontend/src/components/HoverCard.stories.tsx

公開するもの:
```ts
export interface HoverCardProps {
  title: string;               // 1行目（太字）
  subtitle?: string | null;    // 2行目（小さく薄く）。空なら出さない
  onlyWhenClipped?: boolean;   // 既定 true。子孫の [data-hover-card-clip] のどれかで scrollWidth > clientWidth のときだけ出す
  delay?: number;              // 既定 150（Tooltip と同じ）
  className?: string;
  children: ReactNode;
}
export function HoverCard(props: HoverCardProps): JSX.Element  // トリガー。<div class="comp-hover-card-trigger"> で children を包む
export function HoverCardHost(): JSX.Element | null            // 1画面に1つだけ置く。共有のカードを createPortal で document.body に描く
```

仕組み:
- 共有の状態は、HoverCard.tsx の中のモジュール変数と useSyncExternalStore で持つ。新しいライブラリは入れない。
- 状態の中身は「今の基準要素の位置」「title」「subtitle」「open」「glide」の5つ。

トリガー（HoverCard）の動き:
1. mouseenter:
   - onlyWhenClipped が真で、どの `[data-hover-card-clip]` も切れていなければ何もしない。
   - カードが開いている間、または閉じてから 300ms 以内なら、待たずに表示する。このときは glide=true にする。
   - それ以外は delay 後に表示する（glide=false）。
2. mouseleave: タイマーを止めて閉じる。閉じた時刻を記録する（300ms の判定に使う）。
3. タイマーは ref で持ち、unmount のときに必ず止める（Tooltip.tsx:83-88 の、片付けられないタイマーの形は真似しない）。
4. トリガーが unmount するとき、自分が今の基準なら閉じる。在庫表は即時反映（ADR-1016）で行が描き直されるので、mouseleave が来ないままカードが残らないようにするため。
5. HoverCardHost が無い画面（列の単体試験など）でも、トリガーはエラーなく描ける（カードが出ないだけ）。
6. クリックでは開閉しない。在庫表は行をクリックすると引き出しが開くので、ぶつからないようにするため。
7. title 属性は付けない。全文は DOM に残っているので、読み上げではそのまま読まれる。

Host（HoverCardHost）の動き:
- カードの中身を描いたあと、useLayoutEffect で大きさを測り、位置を決める。
  - x = 基準の左端 + 4px。ただし 8px 〜 (画面幅 − カード幅 − 8px) の範囲に収める。
  - y = 基準の上端 − カード高さ − 8px。8px 未満になるときは、基準の下端 + 8px に置き、`--below` を付ける。
- position は fixed。scrollX/scrollY は足さない（recon §2 の Tooltip の不整合を持ち込まない）。
- 位置は Tooltip.tsx:124-134 と同じ方法で、style として渡す。
- open になった次のフレーム（requestAnimationFrame）で `--open` を付ける。拡大しながらのフェードインを効かせるため。
- スクロール（capture）と画面幅の変更で閉じる。
- role="tooltip"。

HoverCard.css（値はすべてトークン。opacity 0/1 と scale は Popover.css:15-31 と同じ書き方）:
```css
.comp-hover-card-trigger { display: block; min-width: 0; }
.comp-hover-card {
  position: fixed; left: 0; top: 0; z-index: var(--z-dropdown); pointer-events: none;
  max-width: calc(100vw - var(--space-2) * 2);
  padding: var(--space-2) var(--space-3);     /* --space-3 が無ければ --space-2 だけを使い、報告する */
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  background: color-mix(in srgb, var(--bg-surface) 90%, transparent);
  backdrop-filter: blur(var(--comp-hover-card-blur));
  box-shadow: var(--shadow-xl);
  color: var(--text-primary);
  white-space: nowrap;
  opacity: 0;
  transform: scale(0.96);
  transform-origin: left bottom;
  transition: opacity var(--transition-fast), transform var(--duration-base) var(--ease-pop), top var(--transition-slow), left var(--transition-slow);
}
.comp-hover-card--below { transform-origin: left top; }
.comp-hover-card--open { opacity: 1; transform: scale(1); }
.comp-hover-card:not(.comp-hover-card--glide) { transition-property: opacity, transform; }  /* 初めて出るときは位置を滑らせない */
.comp-hover-card__title, .comp-hover-card__subtitle { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.comp-hover-card__title { font-size: var(--font-base); font-weight: var(--font-weight-semi); line-height: var(--line-height-base); }
.comp-hover-card__subtitle { margin-top: var(--space-1); font-size: var(--font-xs); line-height: var(--line-height-base); color: var(--text-secondary); }
@media (prefers-reduced-motion: reduce) {
  .comp-hover-card, .comp-hover-card--open { transform: none; transition: opacity var(--transition-fast); }
}
```
- 行を移るときは、位置（top/left）を --transition-slow で滑らせる。glide のときだけ top/left にも transition を効かせる。
- stylelint や css 検査が `calc(100vw - var(--space-2) * 2)` や `0.96` を拒んだら、迂回せず止めて報告する。

### 3-3 列（inventoryColumns.tsx と viewerColumns.tsx。同じ形）
- frontend/src/features/inventory/inventoryColumns.tsx:100-114:
  - 日本語と英語の2つの div を `<HoverCard title={it.product_name ?? \`#${it.product_id}\`} subtitle={it.name_en}>` で包む。
  - 2つの div の `title` 属性を消し、代わりに `data-hover-card-clip` を付ける。
  - クラス（inventory-cell__title / __sub / __clip）と、英語を出す条件（:108）は変えない。
- frontend/src/pages/viewer/viewerColumns.tsx:57-68:
  - 同じ形にする。title は it.japanese_title、subtitle は it.english_title。
- inventoryColumns.css は変えない。「…」で切る仕組みは前の便のまま。

### 3-4 Host の置き場所
- frontend/src/pages/inventory/InventoryPage.tsx と frontend/src/pages/viewer/InventoryView.tsx に、`<HoverCardHost />` を1つずつ置く。
- 置く場所は、返す JSX の一番外側の要素の最後の子。
- どちらの画面でも、Host は1つだけにする。

### 3-5 試験
- HoverCard.test.tsx に4つ:
  - (1) 切れている（scrollWidth > clientWidth を mock）とき、mouseenter から150ms後に role=tooltip が出て、title と subtitle が入っている。
  - (2) 切れていないときは出ない。
  - (3) mouseleave で閉じる。
  - (4) subtitle が空なら2行目の要素が無い。
  - (5) 開いているカードは、トリガーが消える（unmount）と閉じる（§3-2 の4。コード審査で追加）。
- inventoryColumns.test.tsx:125-133 と viewerColumns.cells.test.tsx:101-109 を書き換える:
  - title 属性が無いこと。
  - data-hover-card-clip が付いていること。
  - `.comp-hover-card-trigger` の中にあること。
  - これまでの「product_name 空なら #product_id」「英語が無ければ2段目なし」の試験はそのまま通ること。
- HoverCard.stories.tsx に Default（切れる長い名前）と Short（切れない名前）の2つ。

### 3-6 GAS（index.html。テスト版28 = test_stage を元に、新しい stage を作る）
- 作業場所: ~/CC報告ファイル-keep/inventory-name-hover-card/gas/stage/（test_stage を複写して作る）。clasp は担当（Sonnet）は実行しない。反映は PO が `!` で実行する。
- :1582-1583 の title 属性を消す。
- 1画面に1つの `<div class="hover-card" id="hoverCard" role="tooltip">` を、`<script>` より前（`#content` の後）に置く。中身は `__title` と `__subtitle`。（第1版は「body の最後」としていたが、script がその場で `getElementById('hoverCard')` を読むため null になる。コード審査で訂正）
- 表に委譲のイベントを付ける（見本ページの wire と同じ動き）:
  - 対象は `.title-cell`。
  - 150ms 待ち。開いている間と閉じて 300ms 以内は待たずに出し、滑らせる。
  - `.title-cell__ja` / `.title-cell__en` のどちらかが切れているときだけ出す。
  - スクロールで閉じる。
  - クリックでは開閉しない。
- CSS は 3-2 と同じ形で書き、GAS の `:root` の変数を使う。
  - 無い変数（--radius-xl・--shadow-xl・--ease-pop・--comp-hover-card-blur など）は、アプリの正本と同じ値で `:root` に写す。写した行には「正本 frontend/src/tokens.css（または index.css）と同じ値」とコメントを付ける。
  - GAS はライトのみ（recon §5）。
- 商品名以外の title（:1604-1606 の印）は変えない。

### 3-7 記録
- ADR-1014 に「改訂 2026-10-20（2）」を追記する。内容は次のとおり。
  - 商品名の全文は、切れているときだけ HoverCard で出す。
  - 反映欄: アプリは本 PR、GAS はテスト版・本番版の番号を後で追記。
  - 前回の改訂 2026-10-20 の反映欄「GAS: テスト・本番とも反映待ち」を、「GAS テスト版28（本番は本改訂の版で反映）」に直す。
- docs/CC_UI_GOVERNANCE.md に金型の一覧があれば HoverCard を1行足す。無ければ足さず、その旨を報告する。
- active-work.d に台帳1件を追加する。

### 3-8 閲覧ページの JS 上限（300KB）に収める（CI 失敗を受けた追補 2026-10-20）
- 事実（生出力 /tmp/CC報告ファイル/inventory-name-card/bundle/・bundle2/）:
  - CI「Viewer bundle check」が失敗した。上限は frontend/scripts/check-viewer-bundle.js:21 の 300KB で、根拠は docs/handoff/gas-viewer-fresh-fast/design.md:163。
  - origin/main は 298.8KB で、余裕は 1.2KB だった。HoverCard の分（+2.6KB）で 301.4KB になった。
  - 閲覧ページが使うアイコンは4つだけ（DataTable.tsx:379-382 の並べ替え矢印2つ、Drawer.tsx:150・161 の X と外部リンク）。それでも、frontend/src/constants/icons.tsx が丸ごと本体との共有 chunk に入り、heroicons が72個・52.9KB 載っていた。
- 方針: 上限は変えない（先例 design.md:509 と同じ。部品の側を直す）。表示は変えない。
- 変更:
  - 新規 frontend/src/constants/icons-base.tsx を作り、icons.tsx から次のものをそのまま移す。型（Icon・IconProps・LucideIcon）、`hi()`、ArrowUp・ArrowDown・X・ArrowTopRight、TABLE_ICONS。
  - icons.tsx は、それらを icons-base から import して同じ名前で再 export する。既存の import 先は、どれも変えずに動く。
  - アイコンの定義は icons-base の1か所だけに置く。二重定義はしない。
  - DataTable.tsx・Drawer.tsx・Modal.tsx・Sheet.tsx の import 先だけを `../constants/icons-base` に変える。
- 試算（一時 worktree、bundle2/try.diff）:
  - viewer は 248.0KB（−53.4KB）で合格。
  - 本体の入口 JS は +54.8KB になるが、共有 chunk が同じだけ減る。本体が読む合計は同じ。
- 守り:
  - アイコンを icons.tsx 以外から読むことを禁じる lint や ADR に反しないかを、実装の前に担当が確かめる。反するなら止めて報告する。
  - tsc・vitest・check-viewer-bundle を流す。

## 4. 代替案
- Tooltip を拡張する案: 文字列1つの API・黒い帯の見た目・既存の利用先（MessageReactionBadges）を変えることになる。影響が広がるので採らない。
- Popover を使う案: クリック式で遅延・ホバーの仕組みがない。足すと制御式の API が崩れるので採らない。
- B（名前の場所で浮き上がる）: PO が A を選んだので採らない。

## 5. リスクと対処
- 行クリックの引き出しとぶつかる → カードは pointer-events:none で、クリックは扱わない。
- 表のセルが多くて重くなる → 状態は画面で1つ、描くカードも1枚。セルごとの追加は div 1つとイベント2つだけ。
- 切れているかを読むたびに配置計算が走る → mouseenter のときだけ読む。
- backdrop-filter 非対応のブラウザ → 背景は 90% の不透明色なので、ぼかしが無くても読める。
- 暗い画面設定 → 使うトークンは --bg-surface・--border・--text-*・--shadow-xl だけで、どれもダーク版が index.css にある（recon §4）。
- 新しい UI 文字列は無い（商品名はデータ）ので、i18n の変更はない。

## 6. 受入条件
| 基準 | 検証方法 |
|---|---|
| K1 切れている名前だけカードが出る、切れていない名前では出ない | HoverCard.test.tsx (1)(2) |
| K2 カードに日本語名と英語名が1行ずつ、英語が無ければ1行 | HoverCard.test.tsx (1)(4) |
| K3 商品名セルに title 属性が無く、data-hover-card-clip と trigger がある（在庫表・閲覧） | 列の試験2本 |
| K4 CSS とトークンに直書きなし。ADR-067 の検査とダーク対応の照合が通る | CI 全緑 |
| K5 本番の配信 CSS に `comp-hover-card` と `--comp-hover-card-blur` がある | 本番の配信物を取得して grep（反映後） |
| K6 PO 目視: アプリの在庫表で、切れた名前に乗せるとカードが出て、隣の行へ滑る。切れていない名前では出ない | PO が ○× |
| K7 PO 目視: GAS 在庫一覧（テスト版）で K6 と同じ | PO が ○× |

## 7. 戻し方
- アプリ: 本 PR を revert する（前の便の「…」＋ title に戻る）。
- GAS:
  - テストは版28に戻す。
  - 本番は版18（「…」が入る前）に戻す。または、テスト版28と同じ中身の deploy_prod.sh（前の便）を使う。

## 8. 外部・過去事例の参照と我々への応用
- 外部事例: 名前が切れたときにだけ全文を出し、隣へ移るとカードが滑る見せ方は、よくある UI の作法。ただし、数値で効果を示した出典は今回は確かめていない。採否は PO の見本での目視（見本ページ）で決めており、成功の証明には外部事例を使わない。
- 過去事例:
  - 前の便（docs/handoff/inventory-title-ellipsis/design.md、PR #4552）と同じく、アプリと GAS を同じ設計で揃える。GAS は stage を差0で照合してから反映する。
  - すりガラスの前例は frontend/src/pages/schedule.css:1166-1168。

## 9. 維持の仕組み
- 守り手: frontend/scripts/check-css-hardcoded-values.js（CSS の数値直書きを CI と commit 前に止める）と、frontend/src/components/HoverCard.test.tsx（切れているときだけ出る挙動を守る）。
- GAS の :root にある写しは、正本トークンを変えたときに一緒に直す（ADR-1014 改訂 2026-10-20（2）に記載）。
