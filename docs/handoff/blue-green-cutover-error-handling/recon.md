# recon: blue-green cutover Steps 4-6 エラーハンドリング修正

## 障害概要

- **発生日時**: 2026-09-20 01:12 〜 03:50 JST
- **Deploy Run**: #35480784894
- **症状**: 502 Bad Gateway（nginx → backend 接続不能）

## 根本原因

`scripts/blue-green-cutover.sh:134` の `trap - ERR` 後、`set -e` が有効なままで Steps 4-6 が実行される。

Step 4b（`docker network disconnect`）が "No such container" で失敗 → `set -e` によりスクリプト即座終了 → green コンテナが frontnet に `backend` エイリアスで接続されたまま残存 → その後の nginx restart で DNS が green を向くが green は正常なはずなのに…実際は old が消えていないケースで DNS 混乱 → 502。

## 現状ファイル調査

### scripts/blue-green-cutover.sh

- `scripts/blue-green-cutover.sh:20` — `set -e`（スクリプト全体）
- `scripts/blue-green-cutover.sh:49` — `trap cleanup_green_on_error ERR`（Step 3 まで有効）
- `scripts/blue-green-cutover.sh:134` — `trap - ERR`（ERR trap 解除）← 問題箇所: `set -e` は解除されない
- `scripts/blue-green-cutover.sh:142` — `docker network disconnect "${FRONTNET}" "${OLD_BACKEND}"` ← Step 4b: 旧コンテナが存在しなければ失敗
- `scripts/blue-green-cutover.sh:155` — `docker rename "${GREEN_BACKEND}" "${OLD_BACKEND}"` ← Step 6: rename 失敗時も exit

## 既存 ADR 検索結果

`git grep -i "blue-green\|zero-downtime\|cutover" docs/adr/` → 該当 ADR なし。

運用スクリプト修正のため ADR 不要と判断。

## 影響範囲

- 変更対象: `scripts/blue-green-cutover.sh` のみ
- 呼び出し元: `.github/workflows/deploy.yml`（`bash scripts/blue-green-cutover.sh` として呼び出し）
- 変更の性質: Steps 4-6 のエラーハンドリング追加（正常フローの動作変更なし）
