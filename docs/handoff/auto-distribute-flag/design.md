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
