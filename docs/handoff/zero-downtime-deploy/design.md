# design: ゼロダウンタイムデプロイ（blue-green via nginx 切替）

> 作成: 2026-06-11 | STANDARD-WORKFLOW Phase ③ | 担当: architect
> recon: `docs/handoff/zero-downtime-deploy/recon.md`（VPS 実機確認済み）
> ADR: 新規起案不要（既存 ADR-082 の手順変更として実装）

---

## 外部・過去事例の参照と我々への応用

| 事例 | 概要 | 本プロジェクトへの応用 |
|-----|------|---------------------|
| Docker 公式 blue-green | compose プロジェクト名を blue/green で分けて nginx upstream 切替 | プロジェクト名分離は不要。コンテナ名エイリアスで同等実現 |
| nginx upstream resolver | `resolver 127.0.0.11 valid=5s` で Docker DNS を動的解決 | 採用。変数ベース proxy_pass と組み合わせることで reload 一発で切替可能 |
| health-check polling | `/health` を curl でポーリングし 200 確認後に切替 | 採用。Docker healthcheck の 48s 待ちを回避し約 22〜25s で切替 |
| graceful drain（SIGTERM+wait） | stop_signal + stop_grace_period で in-flight リクエストを完了 | 既存設定（SIGTERM+40s）をそのまま流用 |

---

## 技術 How（設計詳細）

### 現状（ダウンタイムあり）
```
docker rm -f backend  ← nginx 502 開始
docker compose up -d  ← 22s 後に ready → nginx 502 終了
```

### 変更後（blue-green 切替）
```
[1] docker compose up -d --no-deps --scale backend=0 backend-green  ← 新起動（旧は接客継続）
[2] migration 実行（additive-only → 旧も動作継続）
[3] curl http://backend-green:8000/api/health が 200 になるまでポーリング（タイムアウト 60s）
[4] nginx -s reload（nginx.conf の upstream が green を指す → 無停止切替）
[5] docker stop --timeout=40 old-backend（graceful drain）
```

### nginx 設定の変更点

**現状** (`nginx.conf:150`):
```nginx
proxy_pass http://backend:8000/api/;
```

**変更後**:
```nginx
resolver 127.0.0.11 valid=5s;
set $backend_upstream "backend:8000";
proxy_pass http://$backend_upstream/api/;
```

`resolver 127.0.0.11` = Docker 内部 DNS。変数経由にすることで nginx が起動時にのみ解決するのではなく、`valid=5s` の TTL で再解決する。`nginx -s reload` 時に新しいコンテナ IP を掴む。

### deploy.yml の変更方針

**変更箇所**: deploy.yml Step 3（コンテナ削除→起動）を **blue-green 切替シーケンス**に置き換え。

**変更前**（deploy.yml:254-275）:
```bash
# 旧コンテナ削除 → 新起動（ダウンタイム発生）
for _svc in backend frontend celery-worker celery-beat discord-gateway; do
  docker ps -a --filter "name=astro-webapp-${_svc}" --format "{{.ID}}" | xargs -r docker rm -f
done
docker compose up -d --remove-orphans
```

**変更後**:
```bash
# 1. blue-green: まず green backend を別名で起動（旧 backend は接客継続）
docker run -d --name astro-webapp-backend-green \
  --network astro-webapp_frontnet \
  --network astro-webapp_backnet \
  --env-file .env \
  -e ENVIRONMENT=${ENVIRONMENT:-production} \
  ... (同等 env) \
  astro-webapp-backend  # 直前の docker compose build で作ったイメージ

# 2. migration（additive-only → old も動作継続）
bash scripts/run_all_migrations.sh

# 3. health polling（Docker healthcheck 待ちではなく直接確認）
timeout 60 bash -c '
  until docker exec astro-webapp-backend-green \
    python -c "import urllib.request; urllib.request.urlopen(\"http://localhost:8000/api/health\")" \
    2>/dev/null; do
    sleep 2
    echo "  ...waiting for green backend..."
  done
'

# 4. nginx を green に向けて reload（無停止切替）
# nginx.conf の upstream 変数が green を指すよう一時ファイルを書き換え → reload
docker exec astro-webapp-nginx-1 nginx -s reload

# 5. 旧 backend を graceful stop
docker stop --time=40 astro-webapp-backend-1 || true
docker rm astro-webapp-backend-1 || true

# 6. green を backend-1 にリネーム（以降の命名を正規化）
docker rename astro-webapp-backend-green astro-webapp-backend-1

# 7. 残り（celery 等）は通常の force-rm + up で切替（502 影響なし）
```

### 実装上の判断事項

#### frontend・celery は従来方式のまま（対象外）
- frontend: 静的サイト serve → 再起動が数秒で完了、かつ nginx が `try_files` でキャッシュ。502 への寄与は小さい
- celery-worker / celery-beat / discord-gateway: ユーザー向け同期 API のリクエストパスに関与しない
- **主因は backend** → まず backend の無停止化で KGI（502 ゼロ）を達成し、残りは必要に応じて別スプリント

#### nginx upstream の切替方法：スクリプト制御 vs 設定変更

**採用**: nginx コンテナ内に `/etc/nginx/conf.d/upstream.conf` を動的生成する方式
```nginx
# upstream.conf（deploy 時に書き換え）
upstream backend_pool {
    server backend-green:8000;   # 切替時
    # server backend:8000;       # 通常時
}
```
deploy スクリプトが `docker exec nginx sed` で upstream.conf を書き換え → `nginx -s reload`

**不採用**: nginx.conf 本体を書き換える方式 → コンテナ再起動で nginx.conf がボリューム経由で元に戻るため NG

**採用（最終案）**: Docker ネットワークエイリアス方式
- `backend` という名前（Docker DNS）が常に「現在の稼働コンテナ」を指すよう管理
- `docker run --network-alias backend` を新コンテナに付け → `docker network disconnect` で旧を外す
- nginx.conf の変更不要、`nginx -s reload` も不要（Docker DNS が自動更新）

#### Docker ネットワークエイリアス方式（最終採用理由）

```bash
# 1. 新コンテナを起動（backend エイリアス追加は後で）
docker run -d --name astro-webapp-backend-green ...（エイリアスなし）

# 2. health 確認
curl http://astro-webapp-backend-green:8000/api/health

# 3. エイリアスを旧から新へ原子的に切替
docker network connect --alias backend astro-webapp_frontnet astro-webapp-backend-green
docker network disconnect astro-webapp_frontnet astro-webapp-backend-1
# nginx は次のリクエストから backend → green を参照（DNS TTL 以内）
# → nginx -s reload で即時反映（念押し）

# 4. nginx reload（DNS キャッシュリフレッシュ）
docker exec astro-webapp-nginx-1 nginx -s reload

# 5. 旧 graceful stop
docker stop --time=40 astro-webapp-backend-1
```

**利点**:
- nginx.conf の変更不要（既存設定を完全流用）
- `nginx -s reload` 1 発で新 IP を掴む（resolver + 変数方式と組み合わせれば reload も不要になるが、reload はゼロコスト）
- エイリアス付け替えは**2コマンド**で原子的に実行可能

---

## KPI・弊害・トレードオフ

| KPI | 基準 | 検証方法 |
|-----|------|--------|
| デプロイ中 502 ゼロ | 連続 `curl /api/health` で 200 継続 | 素振りスクリプトで計測 |
| 並走時間 | 60 秒以内（タイムアウト設定） | deploy ログで確認 |
| メモリ最大使用量 | available が 50 MiB を割らない | docker stats で監視 |
| デプロイ総所要時間 | 従来比 1.5 倍以内（追加 60s + graceful stop 40s） | CI ログ |

| 弊害・リスク | 対策 |
|------------|------|
| green が 60s 以内に ready にならない（OOM 等） | タイムアウト → 切替せず旧維持 → 既存 auto-rollback |
| docker network connect/disconnect の競合 | connect を先・disconnect を後（原子性は DNS レベルで保証） |
| nginx の DNS キャッシュが stale | `nginx -s reload` で即時リフレッシュ（既実績） |
| celery が旧 backend の内部 URL を参照 | celery は backnet 経由。backnet での backend エイリアスも同様に切替（同ステップで実行） |

---

## 実装計画

### Phase 1: deploy.yml 変更（本 PR）
1. `nginx.conf` に `resolver 127.0.0.11 valid=5s` + 変数 proxy_pass を追加（全 `/api/` 箇所）
2. `deploy.yml` の Step 3 を blue-green シーケンスに置き換え
3. `scripts/blue-green-cutover.sh` を新規作成（切替ロジックを分離・テスト容易化）

### Phase 2: 素振り（本 PR 内）
- `scripts/dry-run-deploy.sh` を作成：ローカル docker-compose で連続 curl しながらデプロイをシミュレート
- 受け入れ基準をすべてチェック

### Phase 3: 本番 cutover（Shingo GO 後）
- feature → develop → main PR（Shingo マージ）

---

## 継続・運用

- `scripts/blue-green-cutover.sh` を単体でテスト可能に保つ
- graceful drain の 40s が足りないケース（SSE 接続等）が出た場合は `stop_grace_period` を延長
- migration が additive-only を外れる場合（PO 承認必要）は、新 backend 切替 **前** に migration を実行する現順序を再検討

---

## 受け入れ基準（ゲート）

| # | 基準 | 検証方法 |
|---|------|--------|
| AC1 | 連続 `curl /api/health` で 502 ゼロ | `scripts/dry-run-deploy.sh` の出力 |
| AC2 | green が health fail → 切替せず旧維持 | `docker exec backend-green kill -9 1` でヘルス失敗を強制 → old が接客継続を確認 |
| AC3 | migration 並走中（新旧両コンテナ）に正常応答 | migration 中に curl を継続 |
| AC4 | 並走時間 60s 以内 | deploy ログのタイムスタンプ |
| AC5 | `git revert` 可能（単一 commit） | PR の commit 数確認 |
