# 設計 — 添付保存用ボリュームの追加（便1）

> この文書は何か（専門用語なしの1行）:
> 顧客から届いた画像を置くための保管場所を、サーバーに1つ用意するための設計。

対象ADR: ADR-091
recon: docs/handoff/attachment-volume/recon.md
親テーマ: docs/specs/attachment-storage/README.md

## 1. あるべき姿

顧客が送った画像やファイルが、いつ見返しても受信箱に残っている。

## 2. recon（実測）

docs/handoff/attachment-volume/recon.md を参照。
要点は次の3つ。
- backend コンテナの Mounts が空配列であり、書いたファイルがデプロイで消える。
- backend の volumes セクションとトップレベル volumes はいずれも既存で、追加のみで済む。
- celery-worker が backend と同一の firebase マウント行を持つため、
  アンカーには `SMOKE_SERVICE_EMAIL` を含めて一意化する。

## 3. design（技術How）

docker-compose.yml に2行を追加する。

- backend サービスの volumes に `- attachments_data:/data/attachments` を追加
- トップレベル volumes に `attachments_data:` を追加

命名は PR #3192 でマージ済みの docs/specs/attachment-storage/to-be.md に従う。

触らない範囲: backend / frontend / migrations / scripts / .github / docs/specs /
docker-compose.yml の celery-worker 定義。

## 4. 外部・過去事例の参照と我々への応用

Docker 公式の設計では、コンテナのファイルシステムはコンテナの寿命と一致し、
再作成で失われる。永続化が必要なデータは named volume に置くのが標準である。
本リポジトリでも postgres_data / redis_data が同じ方式で永続化されている。

我々への応用: 既存の postgres_data と同じ named volume 方式を踏襲する。
新しい方式を持ち込まないことで、運用とバックアップの手順を揃えられる。

## 5. 弊害・トレードオフ

- 弊害: docker-compose.yml の記述を誤ると全コンテナが起動しなくなる。
  対処として、PR作成前に yaml.safe_load による構文検証を必須とする。
- 弊害: 同一のマウント行が backend と celery-worker の2箇所にあり、
  アンカーを誤ると別サービスを書き換える危険がある。
  対処として、1箇所にしか存在しない `SMOKE_SERVICE_EMAIL` を含めて一意化する。
- 弊害: 本PRのマージだけでは反映されない。デプロイ後に初めて効く。
  対処として、受入基準に docker inspect による確認を含める。
- トレードオフ: ボリュームは prod1 のディスクを消費する。
  上限8GBの管理は便5（削除）で実装する。本便では制限しない。

## 6. 受入基準

| 基準 | 検証方法 |
|---|---|
| docker-compose.yml が YAML として妥当である | python3 で yaml.safe_load が例外を出さない |
| トップレベル volumes に attachments_data がある | yaml.safe_load の volumes キーに含まれる |
| backend の volumes に attachments_data:/data/attachments がある | yaml.safe_load の services.backend.volumes に含まれる |
| celery-worker を書き換えていない | yaml.safe_load の services.celery-worker.volumes に attachments_data が含まれない |
| 既存行を変更していない | git diff の削除行が0行である |
| 追加が2行のみである | git diff の追加行が2行である |
| デプロイ後に反映されている | docker inspect astro-webapp-backend-1 の Mounts に attachments_data が現れる |

## 7. 維持の仕組み

- 守り手: CI の YAML 構文検査と、本PRの受入基準に含めた yaml.safe_load
- 理由: docker-compose.yml の構文誤りは機械検査できる
- 人手で守る部分: デプロイ後の docker inspect による反映確認は
  デプロイ完了を待つ必要があるため、PO または実装役の実測とする
