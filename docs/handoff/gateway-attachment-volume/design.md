# 設計 — discord-gateway への添付ボリューム追加

> この文書は何か（専門用語なしの1行）:
> 画像を保存する処理が動いているコンテナに、保管場所をつなぐための設計。

対象ADR: docs/adr/ADR-091-discord-bot-scope-definition.md
recon: docs/handoff/gateway-attachment-volume/recon.md
親テーマ: docs/specs/attachment-storage/README.md

## 1. あるべき姿

顧客が送った画像やファイルが、いつ見返しても受信箱に残っている。

## 2. recon（実測）

docs/handoff/gateway-attachment-volume/recon.md を参照。要点は次の2つ。

- 添付の保存処理は discord-gateway コンテナで実行される
  （client.py:230 → ticket_channel_writer.py:145）。
- discord-gateway サービス定義に volumes セクションが存在しない。

## 3. design（技術How）

`docker-compose.yml` の discord-gateway に volumes セクションを新設し、
`- attachments_data:/data/attachments` を追加する。

インデントは既存の backend と同じく、セクション名が半角4つ、
子要素が半角6つ + `- ` とする。

触らない範囲: トップレベル volumes / backend の volumes /
他のサービス定義 / backend / frontend / migrations / scripts / .github。

## 4. 外部・過去事例の参照と我々への応用

Docker Compose では、named volume は使用する各サービスの volumes に
個別に記述する必要がある。トップレベルの volumes 定義は
「そのボリュームが存在すること」を宣言するだけで、
自動的に全サービスへマウントされるわけではない。

本リポジトリでも postgres_data は postgres サービスのみ、
redis_data は redis サービスのみに記述されている。

我々への応用: 複数のコンテナが同じデータを扱う場合、
それぞれのサービス定義に明示的に記述する。
便1でこれを怠り、実際に保存を行うコンテナが漏れた。

## 5. 弊害・トレードオフ

- 弊害: docker-compose.yml の記述を誤ると全コンテナが起動しなくなる。
  対処として、PR作成前に yaml.safe_load による構文検証を必須とする。
- 弊害: 本PRのマージだけでは反映されない。デプロイ後に初めて効く。
  加えて、直近のデプロイは FedEx smoke の失敗で完走していない。
  反映確認は docker inspect で行う。
- 弊害: backend と discord-gateway が同じボリュームを共有する。
  同一ファイルへの同時書き込みは想定していないが、
  message_id 単位でパスが分かれるため衝突は起きない。
- トレードオフ: backend 側のマウントも残す。
  便4（配信API）が backend で動くため、読み取りに必要である。

## 6. 受入基準

| 基準 | 検証方法 |
|---|---|
| docker-compose.yml が YAML として妥当である | python3 で yaml.safe_load が例外を出さない |
| discord-gateway に attachments_data がある | yaml.safe_load の services.discord-gateway.volumes に含まれる |
| backend の設定を壊していない | yaml.safe_load の services.backend.volumes に attachments_data が含まれる |
| 他サービスに影響していない | services.celery-worker.volumes に attachments_data が含まれない |
| 既存行を変更していない | git diff の削除行が0行である |
| 追加が2行のみである | git diff の追加行が2行である |
| デプロイ後に反映されている | docker inspect astro-webapp-discord-gateway-1 の Mounts に attachments_data が現れる |

## 7. 維持の仕組み

- 守り手: 本PRの受入基準に含めた yaml.safe_load による構文検証
- 理由: docker-compose.yml の構文誤りは機械検査できる
- 人手で守る部分: デプロイ後の docker inspect による反映確認は
  デプロイ完了を待つ必要があるため、PO または実装役の実測とする。
  加えて、実際に画像が保存されることの確認も人手で行う。
