# DIST-01: tcg-sheets-sa.json マウント漏れ修正 — 設計書

参照 recon: docs/handoff/dist-sa-key-mount/recon.md

## 対象 ADR
ADR-154（DIST-01: TCG 在庫配信 SA 鍵管理）

---

## 前提：なぜ docker-compose.yml の設定が効かないか

**backend は本番では `blue-green-cutover.sh` の `docker run` で起動される。**
`docker-compose.yml` の `volumes` / `environment` セクションは `docker compose up` 専用の設定であり、
`docker run` コマンドには**一切引き継がれない**。

これは IMP-29（TCG_AUTO_ANALYZE）で既に発生した同一の根本原因であり、
`docker-compose.yml` にのみ変更を加えても本番コンテナには反映されないことが確認されている。

---

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| 次回 cutover 後、backend コンテナに `tcg-sheets-sa.json` がマウントされる | `docker inspect astro-webapp-backend-1 --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'` で該当パスが出力される |
| DEV 環境（`TCG_SHEETS_SA_KEY_FILE` 未設定）で `docker run` が失敗しない | ローカルで `TCG_SHEETS_SA_KEY_FILE=` として cutover.sh を dry-run、exit code 0 を確認 |
| DIST-01 配信 API が 503 を返さない | 次回配信実行後に `docker compose logs backend --tail=50` で 503/SA key エラーが出ないことを確認 |

---

## 変更内容

### `scripts/blue-green-cutover.sh`

**変更前（89-90行付近）:**
```bash
  --volume "${REPO_DIR}/firebase-credentials.json:/app/firebase-credentials.json:ro" \
  --volume "${COMPOSE_PROJECT}_attachments_data:/data/attachments" \
```

**変更後:**
```bash
  --volume "${REPO_DIR}/firebase-credentials.json:/app/firebase-credentials.json:ro" \
  --volume "${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:ro" \
  --volume "${COMPOSE_PROJECT}_attachments_data:/data/attachments" \
```

### なぜ同じ `${VAR:-/dev/null}` パターンを使うか

`docker-compose.yml:117` が採用している方式と揃えることで一貫性を保つ:
```yaml
- ${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:ro
```

- `TCG_SHEETS_SA_KEY_FILE` が未設定 → `/dev/null:/dev/null:ro` がマウントされる（`/dev/null` は常に存在・DEV 安全）
- `TCG_SHEETS_SA_KEY_FILE=/home/ubuntu/salesanchor/tcg-sheets-sa.json` → 実ファイルがマウントされる

`blue-green-cutover.sh` はスクリプト先頭（35-40行）で `.env` を `set -a; source; set +a` しており、
`docker run` 実行時点で `TCG_SHEETS_SA_KEY_FILE` はシェル変数として展開可能。
また `--env-file "${REPO_DIR}/.env"` によりコンテナ内の環境変数としても渡される（追加変更不要）。

### DEV 環境での安全性

`firebase-credentials.json` には既存のガードがない（ファイル不在で `docker run` が失敗する設計）。
`TCG_SHEETS_SA_KEY_FILE` には `:-/dev/null` フォールバックを設けているため、
DEV 環境で変数未設定でも `/dev/null:/dev/null:ro` がマウントされ起動は成功する。
これは `docker-compose.yml` の既存の動作と同一。

---

## 外部・過去事例の参照と我々への応用

**IMP-29（TCG_AUTO_ANALYZE 有効化、2026年）:**
- `docker-compose.yml` の `environment` に追加したが、`blue-green-cutover.sh` の `docker run` には反映されなかった
- 解決策: cutover スクリプト側に明示的に環境変数を追加
- 今回の教訓への応用: 鍵ファイルも同様に `--volume` を明示追加することで同一の根本原因を修正

**Firebase credentials の既存パターン:**
- `blue-green-cutover.sh:89` の `firebase-credentials.json` マウントが手本
- 同じ位置・同じ書式で `TCG_SHEETS_SA_KEY_FILE` を追加することで一貫性を確保

---

## 維持の仕組み

今後 `docker-compose.yml` に新しい `volumes` を追加する際は、`blue-green-cutover.sh` への対応追加も同時に行う必要がある。

守り手: `scripts/blue-green-cutover.sh` を変更するPRのレビュー時に `docker-compose.yml` の volumes との差分を確認すること（PR テンプレートの「触るファイル」欄で両ファイルを列挙することで検出可能）

---

## ロールバック

次回 cutover 実行前であれば `--volume` 行を削除してコミット・デプロイすれば戻る。
既に cutover 済みなら、コンテナを `docker run` し直すか `docker-compose.yml` 経由で再起動することで対応可能。
