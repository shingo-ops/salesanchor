# 設計 — blue-green への添付ボリューム追加（便4d）

> この文書は何か（専門用語なしの1行）:
> backend を切り替えるときにも、保管庫を持たせるための1行を足す設計。

対象ADR: ADR-091
recon: docs/handoff/bluegreen-attachment-volume/recon.md
親テーマ: docs/specs/attachment-storage/README.md

## 1. あるべき姿

顧客が送った画像やファイルが、いつ見返しても受信箱に残っている。

## 2. recon（実測）

docs/handoff/bluegreen-attachment-volume/recon.md を参照。要点は次の3つ。

- backend は docker compose ではなく docker run で起動している。
- そのため docker-compose.yml の volume 定義が反映されない。
- gateway は compose 経由のため反映されている。

## 3. design（技術How）

scripts/blue-green-cutover.sh の docker run に
添付ボリュームの volume 指定を1行追加する。

ボリューム名は COMPOSE_PROJECT 変数を使って組み立てる。
同スクリプト内で既に定義されている値であり、compose が作る名前と一致する。

既存行は1行も変更しない。追加のみとする。

## 4. 外部・過去事例の参照と我々への応用

同一のサービスを compose と docker run の両方から起動する構成では、
片方にのみ設定を追加すると、起動経路によって挙動が変わる。
これは設定の二重管理であり、片側の更新漏れが起きやすい。

本リポジトリでは、ゼロダウンタイム切替のために backend だけが
docker run 経路を持つ。今回はその二重管理が顕在化した。

我々への応用: backend のコンテナ設定を変えるときは、
docker-compose.yml と scripts/blue-green-cutover.sh の両方を見る。
片方だけの変更は、デプロイ後に静かに失われる。

## 5. 弊害・トレードオフ

- 弊害: 設定が2箇所に分かれたままである。
  本便は追従させるだけで、二重管理そのものは解消しない。
- 弊害: 本番のデプロイ経路を変更する。誤るとデプロイが停止する。
  変更は1行の追加のみとし、既存行を触らないことで影響を抑える。
- トレードオフ: blue-green を compose 経由に戻す案もあるが、
  ゼロダウンタイム切替の仕組みを作り直すことになり範囲が大きい。
  今回は最小の追従を選ぶ。

## 6. 受入基準

| 基準 | 検証方法 |
|---|---|
| 構文が妥当である | bash -n の終了コードが0 |
| 添付ボリュームが1件ある | grep で attachments_data が1件 |
| volume 指定が2件になる | grep で volume が2件 |
| 既存行を変更していない | git diff の削除行が0 |
| 実環境で反映される | デプロイ後 docker inspect の Mounts に現れる |
| 画像が表示される | Discord へ画像を送り受信箱で表示を確認する |

## 7. 維持の仕組み

- 守り手: 人手で守る
- 理由: docker-compose.yml と blue-green-cutover.sh の整合を
  機械的に検査する仕組みが現時点で無い。
  両者の volume 定義を突き合わせる関所は存在しない。
- 対象: backend のコンテナ設定が片方だけ更新されること。
- 検知方法: デプロイ後に docker inspect で Mounts を確認する。
