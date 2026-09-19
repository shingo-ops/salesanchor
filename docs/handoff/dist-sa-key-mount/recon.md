# DIST-01: tcg-sheets-sa.json マウント漏れ — recon

## 対象 ADR
`docs/adr/ADR-154-tcg-parity02-gas-python-migration.md`

## 調査日時
2026-09-05

---

## 1. 本番環境の実測値

### ホスト側（VPS: /home/ubuntu/salesanchor）
```
-rw-r--r-- 1 ubuntu ubuntu 2391 Sep  4 06:32 /home/ubuntu/salesanchor/tcg-sheets-sa.json
```
→ ファイルはホストに存在する（2391 bytes）

### 実行中 backend コンテナのマウント一覧
```
/var/lib/docker/volumes/astro-webapp_attachments_data/_data -> /data/attachments
/home/ubuntu/salesanchor/firebase-credentials.json -> /app/firebase-credentials.json
```
→ tcg-sheets-sa.json はコンテナに未マウント

### ENV の値（.env.example:129 の本番デフォルト）
```
TCG_SHEETS_SA_KEY_FILE=/home/ubuntu/salesanchor/tcg-sheets-sa.json
```
→ コンテナ内アプリはこのパスでファイルを読もうとするが、マウントされていないため失敗する

---

## 2. docker-compose.yml と blue-green-cutover.sh の乖離

`docker-compose.yml:117`（以下、**マウント記述あり**）:
```
- ${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:ro
```

`scripts/blue-green-cutover.sh:89` 付近（修正前、**マウント記述なし**）:
```bash
  --volume "${REPO_DIR}/firebase-credentials.json:/app/firebase-credentials.json:ro" \
  # tcg-sheets-sa.json の --volume 行が存在しない ← 欠落
  --volume "${COMPOSE_PROJECT}_attachments_data:/data/attachments" \
```

---

## 3. 同種の欠落が IMP-29 でも発生（TCG_AUTO_ANALYZE）

`docs/handoff/tcg-auto-analyze-enable/design.md` に記録済み。

`docker-compose.yml` の `environment` セクションに `TCG_AUTO_ANALYZE` を追加したが、
backend は `scripts/blue-green-cutover.sh` の `docker run` で起動するため compose 設定は適用されなかった。
同一の根本原因（「compose には書いた、cutover には書いていない」）により今回の SA キーマウント漏れが発生。

---

## 4. 影響範囲

変更対象:
- `scripts/blue-green-cutover.sh`（`firebase-credentials.json` の `--volume` 行直後に1行追加）
- `docs/handoff/dist-sa-key-mount/recon.md`（本ファイル）
- `docs/handoff/dist-sa-key-mount/design.md`

触らないファイル:
- `docker-compose.yml`（compose 側はすでに正しい）
- `.env` / `.env.example`（変数定義はすでに存在）
- 鍵ファイル本体（パス名参照のみ。中身は参照しない）
