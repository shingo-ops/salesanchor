# TCG_AUTO_DISTRIBUTE 有効化 設計

- recon: docs/handoff/auto-distribute-flag/recon.md
- 対象ADR: ADR-100

## 変更内容
docker-compose.yml の backend と celery_worker の environment セクションに
`TCG_AUTO_DISTRIBUTE=${TCG_AUTO_DISTRIBUTE:-0}` を追加する。

## デフォルト値
`0`（OFF）。本番で有効化する場合は .env に `TCG_AUTO_DISTRIBUTE=1` を追加して再起動。

## 安全性
- 配信フィルタが needs_review=FALSE のみを通すため、要確認の在庫は配信されない
- pending/running ジョブが残っている場合は配信が自動中止される
- デフォルトOFFのため既存環境に影響なし

## 受け入れ基準

| 基準 | 検証方法 |
|------|----------|
| celery_worker に TCG_AUTO_DISTRIBUTE が渡る | `docker compose exec -T celery_worker env \| grep TCG_AUTO_DISTRIBUTE` で `1` を確認 |
| デフォルト値が 0（OFF） | .env 未設定状態で `env` 出力が `0` であること |
| 解析成功後に配信が自動実行される | celery_worker ログに `auto_distribute_after_analysis` タスク実行を確認 |

## 外部・過去事例の参照と我々への応用

TCG_AUTO_ANALYZE（同リポジトリ docker-compose.yml:96,206）で同一パターン `${VAR:-default}` を運用中。デフォルト値を `1`（ON）で2026-09-07から本番稼働しており、問題なし。今回はデフォルト `0`（OFF）でより安全側に設定。

## 維持の仕組み

- docker-compose.yml の environment セクションで管理。.env による上書きが可能
- OFF に戻す場合: .env の `TCG_AUTO_DISTRIBUTE=1` を削除して `docker compose restart celery_worker`
- 配信フィルタ（needs_review=FALSE 等）はコード側に組み込み済みのため、フラグON/OFFに関わらず安全
