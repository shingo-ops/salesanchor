# 設計 — 添付ファイル保管テーマの正本起票

> この文書は何か（専門用語なしの1行）:
> 顧客から届いた画像を自分たちのサーバーに保管するという方針を、正式な決まりとして文書に残すための手順を書いたもの。

対象ADR: ADR-091
recon: docs/handoff/discord-attachment-refetch/recon.md
親テーマ: docs/specs/attachment-storage/README.md

## 1. あるべき姿

顧客が送った画像やファイルが、いつ見返しても受信箱に残っている。
Meta以外のどのチャネルで受けても同じように扱われる。
顧客との関係が終われば、その画像も消える。
サーバーを圧迫しない上限がある。

## 2. recon（実測）

docs/handoff/discord-attachment-refetch/recon.md に記録した実測に加え、
2026-09-01 に次を実測した。

- Discord CDN URL はサーバーから 200、ブラウザから 503（同一URL・同時刻）。
- 署名の有効期限 ex は翌日で、期限切れではない。
- 既存の自社保存の仕組みは存在しない（StaticFiles / mount が0件）。
- prod1 の空き容量 28GB、prod2 の空き容量 166GB。
- 既存の添付は全テナント合計3件（tenant_006 のみ）。
- 索引にファイル保管の類似テーマは0件。

## 3. design（技術How）

本便では実装を行わず、正本3ファイルと索引1行のみを作成する。

作成:
- docs/specs/attachment-storage/README.md（表紙）
- docs/specs/attachment-storage/ideal-state.md（PO自筆のあるべき姿）
- docs/specs/attachment-storage/kgi.md（KGI 7項目・上限8GB）

変更:
- docs/specs/README.md（索引に1行追加）

触らない範囲: backend / frontend / migrations / scripts / .github。

## 4. 外部・過去事例の参照と我々への応用

Discord 公式は、添付CDN URLに ex / is / hm の3パラメータを付け、
署名は有効期限まで有効、期限後はアプリ側が新しいCDN URLを取得し直す必要があると説明している。
目的はCDNを恒久的なファイル置き場として使わせないことである。

LINE 公式ドキュメントも、ユーザーが送信したコンテンツは一定期間後に自動削除されると明記している。

あるOSS実装では、Telegram / Feishu / DingTalk / iMessage は添付をローカルへ保存しているのに
Discord だけがCDN URLを直接使っており、チャンネル間の挙動が一貫しないとして不具合起票されている。

我々への応用: プラットフォーム側は添付を恒久保持しない。
CRMとして履歴を残すには自社保存が必要であり、これは特殊な選択ではなく他実装でも標準の対処である。

## 5. 弊害・トレードオフ

- 弊害: 保存容量が積み上がる。上限8GBと古い順削除で歯止めをかける。
- 弊害: Meta と Discord で方式が分かれ、受信箱の中に2系統が併存する。
  Meta は規約上の理由から自社保存できないため許容する（PO決定）。
- トレードオフ: 本便は文書のみで実装を含まないため、KGI 7項目はいずれも未達である。
  実装は後続便で行う。

## 6. 受入基準

| 基準 | 検証方法 |
|---|---|
| 正本3ファイルが origin/main に存在する | git show refs/remotes/origin/main:docs/specs/attachment-storage/kgi.md が非空 |
| 索引に1行登録されている | git show refs/remotes/origin/main:docs/specs/README.md を grep 'attachment-storage' で1件 |
| あるべき姿がPO自筆のまま記録されている | ideal-state.md の原文節がPO発話と逐語一致 |
| 上限値が数値で確定している | kgi.md に 8GB の記載が存在する |
| 実装コードを含まない | git diff --numstat に backend / frontend / migrations が現れない |

## 7. 維持の仕組み

- 守り手: 人手で守る
- 理由: 本便は文書のみで、機械検査できる振る舞いを持たない。
  正本の書き換えは process-artifacts gate がPR経由を強制するため、
  無断変更は防がれる。
- 対象: あるべき姿がPO以外の手で書き換えられること。
