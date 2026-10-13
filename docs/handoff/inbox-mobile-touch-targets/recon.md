# recon: 押す場所を44px以上にする（現状把握）

調査日 2026-10-13 / ブランチ `release/inbox-mobile-touch-targets`（`origin/main` 起点）

PO 指示: 並べた「次にできること」を順番に進める。その2番目＝**押す場所を44px以上にする**（第2便）。

## A. 44px 未満の対象（CSS とトークンの実値で確定）

| クラス | 参照トークン | 実値 | 位置 |
|---|---|---|---|
| `.send-attach-btn` | `--size-icon-btn-sm` | **28px** | **送信ピルの内側**（`.send-input-wrap` の中） |
| `.send-preview-remove` | `--size-icon-btn-sm` | **28px** | 添付プレビューの行（`.send-attachment-preview` の中） |
| ~~`.inbox-thread-action-btn`~~ | `--size-icon-btn` | 36px | **スマホでは非表示**（`frontend/src/pages/inbox/InboxPage.css` の `@media` 内 `.inbox-thread-actions { display: none; }`）＝**対象外**。画面検査で「見つからない」となって判明した |
| `.inbox-mobile-filter-toggle` | `.icon-btn` 経由 → `--size-icon-btn` | **36px** | 検索欄（`.inbox-search-row` の中） |
| `.inbox-send-btn` | スマホで `--size-avatar-sm` に上書き | **32px** | 送信行の右端（ピルの外） |

出典: `frontend/src/pages/inbox/InboxPage.css` の各規則 ／ `frontend/src/tokens.css` の `--size-icon-btn-sm: 28px`・`--size-icon-btn: 36px`・`--size-avatar-sm: 32px`。

## B. 使うべきトークンは既に登録されている

| トークン | 実値 | コメント |
|---|---|---|
| `--size-icon-btn-lg` | **44px** | 「lg アイコンボタン（モバイルタッチターゲット基準 WCAG 2.5.5）」 |

出典: `frontend/src/tokens.css`。**新しいトークンは不要**。

## C. 送信エリアの構造（ピルが膨らむ理由）

```
.inbox-send-area
  .send-card（白い角丸ボックス）
    .send-top-row（横並び・align-items: flex-end）
      [アバター]
      .send-input-wrap（ピル。bg-subtle・radius-pill・padding: --space-2 --space-14px）
        .inbox-textarea
        .send-attach-btn  ← 28px・ピルの内側
      .inbox-send-btn     ← 32px・ピルの外側
```

出典: `frontend/src/pages/inbox/InboxPage.css` の該当規則。

| # | 事実 | 根拠 |
|---|---|---|
| C1 | ピルの縦余白は `--space-2`（**8px**）×2 | `.send-input-wrap` の `padding` ／ `frontend/src/tokens.css` の `--space-2: 8px` |
| C2 | ピル内の 28px を 44px にすると、ピルの高さは最低 **44 + 8×2 = 60px** になる＝入力1行に対して膨らむ | C1 と `.send-attach-btn` の寸法から |
| C3 | 当たり判定だけ広げる方法（`::before` で `inset: calc(-1 * var(--space-2))`）なら **28 + 8×2 = ちょうど44px** になるが、**左隣の入力欄に 8px 重なる** | C1・C2 から。重なった領域のタップがどちらに入るかは重ね順で決まる |
| C4 | お手本は**入力欄の操作ボタンが全て 48x48dp**＝行自体が高い作り | `docs/specs/design-system/visual-language/benchmark/README.md` の要点 |

**判断**: ピルの内側の2つ（`.send-attach-btn` / `.send-preview-remove`）は、**膨らませる（お手本の作り）か、入力欄に重なるのを許すか**のどちらかになる。**見た目と操作の両方に影響するため本便では触らず、PO 判断を仰ぐ**。ピルの外側の3つは副作用が小さいので本便で直す。

## D. 既存の計測との関係

`frontend/tests-e2e/visual-language/inbox-baseline.spec.ts` は 44px 未満の押せる要素を**記録するだけ**（合否を出さない）。本便で3つを 44px にすると、その記録に残るのはピル内の2つに縮む見込み。合否は `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` 側に追加する。

## E. 詳細度の注意

`.inbox-mobile-filter-toggle` は `icon-btn` も併せ持つ。`frontend/src/components.css` の `.icon-btn { width/height: var(--size-icon-btn) }` が後に読み込まれるため、**単一クラスの指定では負ける**（PR 4179 で同じ原因で PC 側の非表示が効いていなかった）。**2クラス（`.icon-btn.inbox-mobile-filter-toggle`）で指定する。**

## F. 実機で測り直した会話ヘッダ（当初の机上の想定を訂正）

画面検査が `.inbox-thread-action-btn` を「見つからない」と報告したため、実機の構造データで会話ヘッダを測り直した（1080x2340 @480dpi）。

| 要素 | 実寸（device px / dp） | 44dp 以上か |
|---|---|---|
| 一覧へ戻る | 144x144 = **48x48dp** | ✅ |
| 言語（自動） | 219x108 = 73x**36dp** | ❌ |
| **顧客情報（カルテ切替）** | 270x84 = 90x**28dp** | ❌ → **本便で高さを44pxに** |
| **三点メニュー** | 45x114 = **15x38dp** | ❌ **幅が足りないのは画面右端で切れているため** |
| 受信箱の設定（ヘッダー操作行） | 108x108 = 36x36dp | ❌ |

**三点メニューは x=1035〜1080 で画面の右端に達している**＝ヘッダの中身が 360dp に収まっていない。これは**寸法の問題ではなく中身の量の問題**で、直すには「言語セレクトをメニューへ移す」「顧客情報の文言を隠す」などヘッダの構成を変える判断が必要。**本便では触らず、値を記録に残して PO 判断を仰ぐ。**

`.karte-toggle-btn` は幅は中身（アイコン＋文言）に任せ、**高さだけ 44px を下限**にする。会話ヘッダの行は「一覧へ戻る」の 48dp で既に決まっているため**行は高くならない**。
