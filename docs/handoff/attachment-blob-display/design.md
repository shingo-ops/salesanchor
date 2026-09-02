# 設計 — 自社配信APIの画像表示（便4b）

> この文書は何か（専門用語なしの1行）:
> 保管した画像を受信箱に映すための、画面側の作り方。

対象ADR: ADR-091
recon: docs/handoff/attachment-blob-display/recon.md
親テーマ: docs/specs/attachment-storage/README.md

## 1. あるべき姿

顧客が送った画像やファイルが、いつ見返しても受信箱に残っている。

## 2. recon（実測）

docs/handoff/attachment-blob-display/recon.md を参照。要点は次の3つ。

- 便4までは動作しており、保存とURL設定は成功している。
- img タグは Authorization ヘッダーを送れず、サーバーは Cookie を見ていない。
- 画面には Blob 取得の既存部品と使用例がある。

## 3. design（技術How）

frontend/src/pages/inbox/InboxMessageThread.tsx に次を追加する。

- attachment_url が /api/ で始まる場合、api.getBlob で取得して
  URL.createObjectURL に変換したものを img の src に渡す。
- 取得済みの画像は再取得しない。取得中はプレースホルダを表示する。
- アンマウント時に objectURL を解放する。
- Meta 経路（外部CDNのURL）は従来どおり src に直接入れる。

frontend/src/lib/api.ts と backend は変更しない。

## 4. 外部・過去事例の参照と我々への応用

HTML の img 要素はブラウザが直接リクエストを発行するため、
JavaScript から任意のリクエストヘッダーを付けられない。
これは仕様上の制約であり、回避策として広く採られているのは次の3つである。

1. Cookie 認証にする
2. 署名付きURLを発行する
3. fetch で取得して Blob URL に変換する

本リポジトリは Firebase の ID トークンを Authorization ヘッダーで送る方式であり、
Cookie 認証を実装していない。1は新たな認証経路の追加になる。

2は認証を経ない配信経路を1つ増やすことになり、
URLが漏れた場合の露出面が広がる。

3は既存の認証方式をそのまま使い、新しい経路を作らない。
本設計は3を採る。

## 5. 弊害・トレードオフ

- 弊害: 画像の表示までに1往復の通信が増える。
  取得中はプレースホルダが表示される。
- 弊害: 画像をメモリ上に保持するため、多数の画像を開くと消費が増える。
  アンマウント時に objectURL を解放して抑える。
- 弊害: 便4で画面を変更しないと設計したが、それが誤りだった。
  img タグの制約を確認していなかった。
- トレードオフ: Meta 経路と自社経路で表示の仕組みが分かれる。
  Meta は規約上の理由から自社保存できないため、統一できない。

## 6. 受入基準

| 基準 | 検証方法 |
|---|---|
| Blob取得を使っている | grep で getBlob が1件ヒットする |
| Meta経路を壊していない | grep で handleAttachmentError が2件ヒットする |
| メモリを解放している | grep で revokeObjectURL が1件以上ヒットする |
| api.ts を変更していない | git diff に frontend/src/lib/api.ts が現れない |
| 型検査が通る | CI の Lint and Dark Mode Check が success |
| ビルドが通る | CI の Frontend E2E が success |
| 実環境で表示される | デプロイ後、Discord へ画像を送り受信箱で表示を確認する |

## 7. 維持の仕組み

- 守り手: 人手で守る
- 理由: 画像の表示は実ブラウザでの描画を伴い、
  現在のテスト基盤では Discord からの実受信を伴う経路を再現できない。
- 対象: 自社配信APIの画像が表示されなくなること。
- 検知方法: PO による実機確認。Discord へ画像を送り受信箱で表示されるかを見る。
