# 設計: 受信箱の本文の面を画面の下端まで届かせる（地の一本化の仕上げ）

対象 ADR: ADR-144（UI共通部品のガバナンス・金型所有のCSS）／ADR-067（デザイントークン強制）／ADR-137（MobileShell の独立 DOM）
recon: [recon.md](./recon.md)（`docs/handoff/inbox-mobile-fill-height/recon.md`）
経緯: PR #4184 で配色を直したが**地の一本化だけ未達**（投入後の実機測定）。PO 選択「(A) 受信箱のスマホ幅だけで伸ばす」。

## 1. なぜ直すのか（事実のみ）

- お手本は**一覧の面が画面の上端から下端まで1色**（白 79.76%・全幅を占める範囲 y=111〜2129）。会話が少なくても最後の行より下は同じ色（recon A）。
- 当方は白 45.73% で、面が届くのは y=1429 まで。**y=1431〜2125（231dp）にページの地が出ている**（recon B）。
- `.inbox-wrapper` に色を敷く前便の方法では、**wrapper 自身の箱が内容の高さで終わる**ため届かない（配信CSSに指定は入っている）。

## 2. 変更するファイルと、変更前後

### 2-1. `frontend/src/components/PageLayout.css`（金型所有）

既存の `@media (max-width: 767px)` の中に1つ足す。

```css
.page-layout.page-layout--slim-header .page-layout-content {
  background: var(--bg-surface);
}
```

`.page-layout-content` は `flex: 1`（recon C2）で**本文の高さを持つ段**。`slimHeaderOnMobile` を渡しているのは受信箱だけ（`frontend/src/pages/inbox/InboxPage.tsx`）なので、対象は受信箱に限られる。2クラスで書くのは、単一クラスだと他の指定に負ける可能性があるため（前便の `.icon-btn` の教訓）。

### 2-1b. 本文の高さを実寸で出す（CI の実測で判明した真因への対応）

```css
.page-layout.page-layout--slim-header {
  min-height: calc(100dvh - var(--tabbar-height));
}
```

**なぜ必要か**: 色を敷くだけでは届かなかった。CI の `height-chain` 実測で `.mobile-content` が 844px（全高）なのに `.page-layout` が 287px で切れていることが判明（recon C-2）。`.mobile-shell` が `height` ではなく `min-height: 100dvh` のため、`.page-layout` の `height: 100%` が中身の高さに落ちる。**パーセントでは解決できないので実寸で与える。**

あわせて `frontend/src/tokens.css` に `--tabbar-height: 56px` を登録する（従来 `frontend/src/mobile-shell.css` の2箇所が代替値付きで参照していた値。非色トークンなので `:root` のみ・`force-dark` 不要）。

### 2-2. `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`

**高さの鎖の各段を記録に残す**（`height-chain` 添付）。`.mobile-content` / `.page-layout` / `.page-layout-content` / `.inbox-wrapper` / `.inbox-left-panel` の top・bottom・height・背景色を取る。あわせて「**面の色を敷いた要素のうち最も下まで届くものが画面の7割より下**」を基準にする。

**なぜ記録を残すのか**: 鎖はコード上は繋がって見えるのに実測では切れている（recon C）。どの段で切れているかを**推測せずに次の便へ引き継ぐ**ため。

## 3. 触らない範囲（明示）

- **PC・タブレット**: `@media (max-width: 767px)` の内側のみ。
- **`frontend/src/pages-layout.css` / `MobileShell` / `.mobile-content`**: 触らない（recon E）。
- **トークン**: 追加・変更しない（`--tabbar-height` の登録も本便では行わない）。
- **他の全画面型ページ（8枚）**: 触らない。各ページを作る/直すときに同じ尺度で判断する（recon D）。
- **API・DB・migrations**: 触らない。

## 4. 守る決まり（CI が検査する）

`check:all`（25項目）／`Lint & Dark Mode Check (ADR-067)`／`画面検査（受信箱 3幅 Playwright）`／`Frontend lint & custom checks`（単体テスト）。

## 5. 検証方法（受け入れ基準）

| # | 基準 | 検証方法 |
|---|---|---|
| 1 | 390px で**面の色が画面の7割より下まで届く** | `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` で、面の色を敷いた要素の `bottom` の最大値 > `innerHeight * 0.7` |
| 2 | **高さの鎖の各段が記録される** | 同検査の `height-chain` 添付に5段の top/bottom/height/背景色が入る |
| 3 | **1280px / 768px が不変** | 同検査の PC・タブレット側が緑のまま |
| 4 | 既存の基準（左右対称・12px のコントラスト・地の色の一致・1画面1ページの往復・操作行の出し分け）が緑のまま | 同ファイルの既存4件 |
| 5 | `npm run check:all` 25/25 ／ 単体テスト全件合格 | 実行して出力を PR に貼る |
| 6 | **投入後の実機で地が 70% 以上**（お手本は 79.76%） | デプロイ後に画素を数えて PR に追記 |

## 6. 戻し方

このPRの revert のみ。トークン・共有部品・API・DB を変更しないため波及はない。

## 7. 残るリスク（正直に）

1. ~~`.page-layout-content` 自身が画面の高さを持っていない場合、この方法でも届かない~~ → **実際に起きた。** CI の1回目で `.page-layout` が 287px で切れていることが判明し、§2-1b で実寸の高さを与える対応を追加した（recon C-2）。記録を残す設計にしていたため、**推測せず1回で原因を特定できた。**
2. **`min-height` を実寸（`calc(100dvh - var(--tabbar-height))`）で与えるため、将来タブバーの高さが変わると値がずれる。** トークン参照にしてあるので、タブバー側の高さもこのトークンを使う限りずれない（`frontend/src/mobile-shell.css` は現在 `var(--tabbar-height, 56px)` の形で同じトークンを参照している）。
2. **本文の領域が白くなるため、受信箱のスマホで「カードが浮いている」見え方は無くなる。** これは意図（お手本は面が1枚）。
3. **`slimHeaderOnMobile` を他のページが使い始めると、そのページも白くなる。** 現在の利用は受信箱のみ。金型のコメントに対象と理由を明記した。
4. 他の全画面型ページ（8枚）は未対応のまま（recon D の判断）。

## 8. 相互参照

- **recon**: [recon.md](./recon.md)（`docs/handoff/inbox-mobile-fill-height/recon.md`）— A のお手本実測・B の当方実測・C の高さの鎖・D の他画面の判断・E の手段の選択を前提とする。
- **ADR-144**（UI共通部品のガバナンス）: 本便の指定は**金型所有のCSS**（`frontend/src/components/PageLayout.css`）に置く。ページ側のCSSに書くと金型の見た目がページごとにばらけるため。
- **ADR-067**（デザイントークン強制）: 既存トークン `--bg-surface` の `var()` 参照のみ。新規追加・値の変更なし。
- **ADR-137**（MobileShell の独立 DOM）: `.mobile-content` には触らない（全ページに効くため）。
- **前便**: [../inbox-mobile-polish/design.md](../inbox-mobile-polish/design.md) §2-1（色で覆う方針）と §7-1（根因が残ることの明記）。本便はその続きで、未達だった地の一本化を仕上げる。
- **お手本の実測**: [../../specs/design-system/visual-language/benchmark/whatsapp-color-structure.md](../../specs/design-system/visual-language/benchmark/whatsapp-color-structure.md)（地79.6% / 面2段 / 強調色1.7%）。本便の目標値（地70%以上）はここから取っている。

## 9. 外部・過去事例の参照と我々への応用

| 事例 | 何を参照したか | 我々への応用 |
|---|---|---|
| **WhatsApp（Android・ライト）の実測** | 一覧の面が**画面の上端から下端まで1色**。最後の行より下も同じ色（y=1600・2000 がどちらも白） | 本便の目標そのもの。空き領域を「背景」ではなく「一覧の続き」として扱う |
| **Meta Business Suite の実測** | 受信箱の一覧も面が画面を埋める | 同じ方向の裏付け |
| **PR 4184（直前の自分の便）** | `.inbox-wrapper` に色を敷いたが**箱の高さで終わり届かなかった**（投入後の実測で判明） | **色を敷く段を1つ上げる**（本文の領域）。同じ失敗を繰り返さないため、届いたかを検査の基準にした |
| **PR 4179（直前の社内事例）** | `.icon-btn` との詳細度争いで単一クラスの指定が負けた | 本便も**2クラス**（`.page-layout.page-layout--slim-header .page-layout-content`）で書く |

**採用しなかったもの**: `min-height: calc(100dvh - ...)` で伸ばす案（未登録トークンが必要・`overflow-y: hidden` で溢れが切れる）。高さの鎖を整理する案（共有部品に波及・PO 選択は (A)）。`.mobile-content` に色を敷く案（全84ページに効く）。

## 10. 維持の仕組み

- 守り手: `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`（基準 #1〜#4 を3幅で検査。`height-chain` 添付で鎖の各段を記録）、`.github/workflows/e2e.yml` のジョブ `visual-language`、`frontend/package.json` の `check:all`（25項目）。
- 対象: 面の色が届かなくなること（高さの鎖が将来崩れた場合）、PC・タブレットへの波及、色コードの直書き、明暗の対の欠落。
- 関所が無い部分: **面積比（地が70%以上）そのものは機械で検査していない。** CI でスクリーンショットの色統計を取る仕組みが無いため、**投入後に実機で測って PR に記録する**運用で守る（基準 #6）。「面が画面の7割より下まで届く」は**その代理指標**であり、面積比と完全に同じではない（代理であることを明記しておく）。
