# ロールバック実証ドリル手順書（ADR-116）

## 目的

本番に触れずに「安全網（自動ロールバック）が本当に効くか」を実証する。

**重要**: ドリルは `scripts/deploy_rollback.sh` を本番と同じ経路で呼ぶ。
`run-drill.sh` はテストシナリオのセットアップのみを担当し、ロールバックロジック自体は
本番と同一の `deploy_rollback.sh` が実行する（「ドリルで通った＝本番でも同じ動き」を保証）。

---

## 合格条件（7 点・全部緑で Phase2 切替可）

| # | 条件 | 確認方法 |
|---|------|---------|
| 1 | good デプロイ → health 200 → **last-good SHA が記録される** | `.deploy_last_good_sha` ファイルが存在 |
| 2 | bad デプロイ（DB 接続不可）→ **health が 503** | `urllib.urlopen` が例外 |
| 3 | 健康ゲートが 503 を検知して **失敗経路が発火** | `deploy_rollback.sh` が exit 1 |
| 4 | **保全**: `deploy-failures/<ts>-<sha>.log` に backend ログ・health 応答・`compose ps`・`pg_stat_activity` が記録 + 通知 | ファイル内容確認 |
| 5 | **ロールバック**: good SHA へ `git reset --hard` + `.env` 復元 | `git log -1` + `cat .env` |
| 6 | **復旧確認**: 復帰後 health 200 | `urllib.urlopen` が成功 |
| 7 | **初回エッジ**: last-good 記録なし → 黙って進まず **明示失敗** | exit 1 + エラーメッセージ確認 |

---

## 前提条件

- Docker Desktop が起動していること（`docker ps` が通ること）
- プロジェクトルート（`salesanchor/`）から実行すること
- `bash`, `git`, `python3` が使えること

---

## 自動実行（推奨）

```bash
bash scripts/run-drill.sh
```

スクリプトが 7 点すべてを自動検証し、結果を出力する。

- 全 PASS → `exit 0`
- 1 点でも FAIL → `exit 1`（Phase2 切替は HOLD）

---

## 手動実行手順（自動スクリプトが動かない場合）

### Step 1: ドリル環境を起動（good 状態）

```bash
# ドリル用コンテナを起動
docker compose -f docker-compose.drill.yml -p drill up -d --build

# backend が healthy になるまで待つ
docker compose -f docker-compose.drill.yml -p drill ps
# backend の Health が "healthy" になるまで繰り返す（最大 60s）
```

### Step 2: 合格条件 1 を確認

```bash
# good 状態で deploy_rollback.sh を実行
BACKEND_CONTAINER=drill-backend-1 \
DB_CONTAINER=drill-postgres-1 \
COMPOSE_CMD="docker compose -f docker-compose.drill.yml -p drill" \
DEPLOY_FAILURES_DIR="deploy-failures" \
  bash scripts/deploy_rollback.sh

# ✅ exit 0 かつ .deploy_last_good_sha が作成されること
cat .deploy_last_good_sha
```

### Step 3: bad 状態に切り替える（合格条件 2）

```bash
# .env バックアップ（復元用）
cp .env .deploy_prev_env

# DATABASE_URL を壊す（前回の localhost 誤指定相当）
sed -i.bak '/^DATABASE_URL=/d' .env
echo "DATABASE_URL=postgresql+asyncpg://nobody:wrong@nonexistent:9999/nodb" >> .env

# backend だけ再起動（DATABASE_URL を反映）
docker compose -f docker-compose.drill.yml -p drill up -d --force-recreate backend
sleep 15

# ✅ health が 503 になっていること
docker exec drill-backend-1 python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
# → urllib.error.HTTPError: HTTP Error 503 が出れば OK
```

### Step 4: ロールバックスクリプトを実行（合格条件 3-6）

```bash
# deploy-failures/ をクリア（今回の保全ファイルだけ確認するため）
rm -rf deploy-failures

BACKEND_CONTAINER=drill-backend-1 \
DB_CONTAINER=drill-postgres-1 \
COMPOSE_CMD="docker compose -f docker-compose.drill.yml -p drill" \
DEPLOY_FAILURES_DIR="deploy-failures" \
ROLLBACK_BUILD_RETRIES="2" \
  bash scripts/deploy_rollback.sh

# ✅ exit 1 であること（ロールバック成功でも deploy は失敗扱い）
echo "Exit: $?"
```

### Step 5: 合格条件 4-6 を手動確認

```bash
# 条件 4: 保全ファイルの内容確認
ls deploy-failures/
cat deploy-failures/*.log  # backend ログ・health・compose ps・pg_stat_activity が含まれること

# 条件 5: good SHA に戻っているか
git log -1 --oneline
cat .deploy_last_good_sha  # 一致すること

# .env が復元されているか
grep DATABASE_URL .env  # drilluser で接続する URL であること

# 条件 6: health が 200 に戻っているか
docker exec drill-backend-1 python -c "import urllib.request; r=urllib.request.urlopen('http://localhost:8000/api/health'); print(r.status)"
# → 200
```

### Step 6: 初回エッジを確認（合格条件 7）

```bash
# last-good SHA をクリア
rm -f .deploy_last_good_sha .deploy_prev_sha

# コンテナなしでスクリプトを実行
BACKEND_CONTAINER=drill-backend-notexist \
COMPOSE_CMD="docker compose -f docker-compose.drill.yml -p drill" \
DEPLOY_FAILURES_DIR="deploy-failures" \
  bash scripts/deploy_rollback.sh

# ✅ exit 1 かつ "ロールバック先不明（初回デプロイ）" が出力されること
```

---

## A → C 切り替え条件

ローカルで以下の状況が発生した場合は、専用ステージング（案 C）へ切り替えること:

- `docker-compose.drill.yml` がバックエンドの起動に必要な依存（migrate, init.sql 等）を再現できず、`/api/health` の挙動が本番と異なる
- `deploy_rollback.sh` の `COMPOSE_CMD` 変数が VPS 固有のパス/SSH に強く依存しており、ローカルでは `scripts/deploy_rollback.sh` を呼んでも別物の挙動になる

「別物をテストして緑」が最も危険。迷ったら C。

---

## クリーンアップ

```bash
docker compose -f docker-compose.drill.yml -p drill down -v
rm -f .deploy_last_good_sha .deploy_prev_sha .deploy_prev_env
rm -rf deploy-failures drill-workspace
```

---

## 参照

- ADR-116: `docs/adr/ADR-116-deploy-rollback-preservation.md`
- 共有スクリプト: `scripts/deploy_rollback.sh`
- ドリル自動実行: `scripts/run-drill.sh`
