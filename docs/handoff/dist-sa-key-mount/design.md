# DIST-01: tcg-sheets-sa.json マウント漏れ修正 — 設計書

参照 recon: `docs/handoff/dist-sa-key-mount/recon.md`
対象 ADR: `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md`

---

## 前提：backend は docker run で起動する

**backend は `scripts/blue-green-cutover.sh` の `docker run` で起動される。**
`docker-compose.yml` の `volumes` / `environment` セクションは `docker compose up` 専用の設定であり、
**backend コンテナには一切引き継がれない。**

今後 backend に環境変数・ファイルを渡す場合は、`docker-compose.yml` だけでなく
`scripts/blue-green-cutover.sh` の `docker run` にも必ず追加すること。
これは IMP-29（TCG_AUTO_ANALYZE）で既に同一の根本原因が確認されており、
`docs/handoff/tcg-auto-analyze-enable/design.md` に記録されている。

---

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| 次回 cutover 後、backend コンテナに tcg-sheets-sa.json がマウントされる | `docker inspect astro-webapp-backend-1 --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'` で /home/ubuntu/salesanchor/tcg-sheets-sa.json が出力される |
| DIST-01 配信 API が SA キーエラーを返さない | 次回配信実行後のログに認証エラーが出ないことを確認 |

---

## 変更内容

### `scripts/blue-green-cutover.sh`

**変更前（89-91行）:**
```bash
  --volume "${REPO_DIR}/firebase-credentials.json:/app/firebase-credentials.json:ro" \
  --volume "${COMPOSE_PROJECT}_attachments_data:/data/attachments" \
```

**変更後:**
```bash
  --volume "${REPO_DIR}/firebase-credentials.json:/app/firebase-credentials.json:ro" \
  --volume "${REPO_DIR}/tcg-sheets-sa.json:${REPO_DIR}/tcg-sheets-sa.json:ro" \
  --volume "${COMPOSE_PROJECT}_attachments_data:/data/attachments" \
```

### パス設計の理由

- `REPO_DIR` は `scripts/blue-green-cutover.sh:22` で `/home/ubuntu/salesanchor` に解決される
- `TCG_SHEETS_SA_KEY_FILE=/home/ubuntu/salesanchor/tcg-sheets-sa.json`（.env.example:129）
- コンテナ内アプリが `os.environ["TCG_SHEETS_SA_KEY_FILE"]` で読む**ホストと同じパス**にマウントする必要がある
- `docker-compose.yml` が `${TCG_SHEETS_SA_KEY_FILE}:${TCG_SHEETS_SA_KEY_FILE}:ro` でホスト = コンテナ同一パスにマウントしているのと同じ設計
- `/app` ではない（`TCG_SHEETS_SA_KEY_FILE` が `/home/ubuntu/salesanchor/tcg-sheets-sa.json` を指しているため）

### DEV 環境での動作

`firebase-credentials.json` に存在確認ガードがないのと同じ扱い。
`scripts/blue-green-cutover.sh` は本番 VPS 専用スクリプトであり、
DEV 環境での `docker run` 実行は想定外。ガードは追加しない。

---

## 外部・過去事例の参照と我々への応用

IMP-29（TCG_AUTO_ANALYZE 有効化）: `docs/handoff/tcg-auto-analyze-enable/design.md` に記録。
compose の environment に追加しただけでは backend コンテナに反映されなかった。
今回の SA キーも同一パターン。cutover スクリプト側への明示追加が唯一の解決策。

---

## 維持の仕組み

守り手: `scripts/blue-green-cutover.sh` を変更する PR のレビュー時、`docker-compose.yml` の volumes との差分を確認する