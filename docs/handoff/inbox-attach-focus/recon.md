# recon — 添付後の Enter でファイル選択が開く

> この文書は何か（専門用語なしの1行）:
> 画像を付けたあと Enter を押すと送信されない理由を、実際の作りを見て突き止めた記録。

対象ADR: ADR-091
親テーマ: docs/specs/attachment-storage/README.md

## 実測（2026-09-04）

### Enter の処理は入力欄にしか付いていない

frontend/src/pages/inbox/InboxMessageThread.tsx:646 で
onKeyDown が textarea に付いている。

同ファイル内で onKeyDown を持つ要素は他に無い。

### クリップボタンは通常のボタンである

frontend/src/pages/inbox/InboxMessageThread.tsx:670 の
クリップボタンは type が button である。

同ファイル:672 で handleAttachClick を呼び、
隠しの入力要素をクリックする。

### フォーカスを制御していない

frontend/src/pages/inbox/InboxMessageThread.tsx 内に
focus の呼び出しは0件である。

form 要素も0件である。

### 起きていること

クリップボタンを押すとフォーカスがボタンに移る。
ファイルを選んだ後もフォーカスはボタンに残る。

その状態で Enter を押すと、ボタンの押下として扱われ、
handleAttachClick が再び走ってファイル選択が開く。

入力欄にフォーカスが無いため、
frontend/src/pages/inbox/useInboxState.ts:660 の handleKeyDown は呼ばれない。

## 本便で変更する箇所

frontend/src/pages/inbox/InboxMessageThread.tsx に
入力欄への参照を作り、添付の直後にフォーカスを戻す。

ドラッグ&ドロップで添付した場合も同様に戻す。

frontend/src/pages/inbox/useInboxState.ts は変更しない。
