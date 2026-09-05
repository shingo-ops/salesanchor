# DIST-01: tcg-sheets-sa.json マウント漏れ — recon

## 対象 ADR
ADR-154（DIST-01: TCG 在庫配信 SA 鍵管理）

## 調査日時
2026-09-05

---

## 1. 本番環境の実測値

### ホスト側（VPS: /home/ubuntu/salesanchor）
```
-rw-r--r-- 1 ubuntu ubuntu 2391 Sep  4 06:32 /home/ubuntu/salesanchor/tcg-sheets-sa.json
```
→ ファイルは存在する（2391 bytes）

### 実行中 backend コンテナのマウント一覧
```
/var/lib/docker/volumes/astro-webapp_attachments_data/_data -> /data/attachments
/home/ubuntu/salesanchor/firebase-credentials.json -> /app/firebase-credentials.json
```
→ `tcg-sheets-sa.json` は**コンテナに未マウント**

---

## 2. 設定ファイル間の乖離

| 項目 | `docker-compose.yml` | `scripts/blue-green-cutover.sh`（修正前） |
|------|---------------------|------------------------------------------|
| firebase-credentials.json | マウントあり | マウントあり |
| attachments volume | マウントあり | マウントあり |
| tcg-sheets-sa.json | `${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:…:ro` でマウントあり | **マウント記述なし** ← ここが欠落 |

- `docker-compose.yml:117`: `- ${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:ro`
- `scripts/blue-green-cutover.sh:89`（修正前）: `--volume "${REPO_DIR}/firebase-credentials.json:/app/firebase-credentials.json:ro" \`
  → 次行に `TCG_SHEETS_SA_KEY_FILE` の `-v` 行がない

### .env.example の定義
```
# .env.example:126-129
# VPS 手動配置: /home/ubuntu/salesanchor/tcg-sheets-sa.json
# docker-compose がホスト側の絶対パスをコンテナ内同一パスでマウントする。
# 未設定の場合は配信実行時に 503 エラーを返す（起動自体は止まらない）。
TCG_SHEETS_SA_KEY_FILE=/home/ubuntu/salesanchor/tcg-sheets-sa.json
```

---

## 3. .env 読み込みの有無

`blue-green-cutover.sh:35-40` にて `.env` を `set -a; source "${REPO_DIR}/.env"; set +a` で読み込んでいる。
→ `TCG_SHEETS_SA_KEY_FILE` は `docker run` 実行時に**シェル変数として利用可能**。
→ `--env-file "${REPO_DIR}/.env"` でコンテナ内の環境変数としても渡される。
→ **欠けているのはボリュームマウントの `-v` 行のみ**。

---

## 4. 同種の問題が TCG_AUTO_ANALYZE でも発生（IMP-29 教訓）

IMP-29（TCG_AUTO_ANALYZE 有効化）では `docker-compose.yml` の `environment` に追記したが、
`blue-green-cutover.sh` は `docker run` で起動するため compose の設定は**一切適用されない**。
→ 今回の SA キーマウント漏れと同一の根本原因。

---

## 5. 影響範囲

変更対象ファイル:
- `scripts/blue-green-cutover.sh:89` 付近（`firebase-credentials.json` の `-v` 行直後に追加）

触らないファイル:
- `docker-compose.yml`（compose 側はすでに正しい）
- `.env` / `.env.example`（変数定義はすでに存在）
- 鍵ファイル本体（参照のみ）
