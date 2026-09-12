# recon — 受信箱のドラッグ&ドロップ添付

> この文書は何か（専門用語なしの1行）:
> 画像を画面に落として添付できるようにする前に、いまの作りを見て記録したもの。

対象ADR: ADR-091
親テーマ: docs/specs/attachment-storage/README.md

## 実測（2026-09-04）

### 既存のファイル選択

frontend/src/pages/inbox/InboxMessageThread.tsx:81 の handleFileChange が
選んだファイルを保持し、プレビュー用のURLを作る。

同ファイル:77 の handleAttachClick が隠しの入力要素をクリックする。

ドラッグ&ドロップの処理は存在しない。

### スレッドのルート要素

frontend/src/pages/inbox/InboxMessageThread.tsx:277 が
main 要素でスレッド全体を包んでいる。

同ファイル:374 がメッセージ一覧の領域である。

### CSS の状態

frontend/src/pages/inbox/InboxPage.css:425 の inbox-center に
position の指定が無い。

オーバーレイを内側に重ねるには position: relative が必要である。

同ファイル:1474 に position: fixed と inset: 0 を使ったモーダルの前例がある。
z-index は CSS変数で指定されている。

### 翻訳キー

frontend/src/locales/ja.json:972 に attachImage がある。
その並びに新しいキーを追加できる。

### ライトボックス

frontend/src/pages/inbox/InboxMessageThread.tsx:669 に画像の拡大表示がある。
クラス名を使わずインラインの指定で書かれている。

本便では別のクラス名を使い、CSS に定義を置く。

## 本便で変更する箇所

frontend/src/pages/inbox/InboxMessageThread.tsx に
ドラッグ&ドロップの処理とオーバーレイを追加する。

frontend/src/pages/inbox/InboxPage.css に
position: relative とオーバーレイの定義を追加する。

frontend/src/locales/ja.json と
frontend/src/locales/en.json に翻訳キーを追加する。

frontend/src/pages/inbox/useInboxState.ts は変更しない。
