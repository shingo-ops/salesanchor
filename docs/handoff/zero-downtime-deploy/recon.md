# recon.md — ゼロダウンタイムデプロイ調査

> 作成: 2026-06-11 | STANDARD-WORKFLOW Phase ① recon | 担当: architect

---

## 1. デプロイ全体フロー

### GitHub Actions トリガー

`.github/workflows/deploy.yml:3`  
`main` ブランチへの push で起動。`concurrency: group: deploy-production, cancel-in-progress: false` により直列実行保証（`.github/workflows/deploy.yml:14`）。

### ステップ順序

| # | ステップ名 | file:line | 内容 |
|---|-----------|-----------|------|
| 0 | PREV_SHA 保存 | `.github/workflows/deploy.yml:130` | ロールバック用に現 HEAD を `.deploy_prev_sha` に保存 |
| 1 | git pull | `.github/workflows/deploy.yml:137` | `git fetch origin main && git reset --hard origin/main` |
| 2 | .env 更新 | `.github/workflows/deploy.yml:141` | GitHub Secrets を sed 削除 → append で注入 |
| 3a | `docker compose build` | `.github/workflows/deploy.yml:241` | 最大3リトライ。**旧コンテナは生存したまま新イメージをビルド** |
| 3b | コンテナ force-rm | `.github/workflows/deploy.yml:260` | `docker rm -f` で backend/frontend/celery系を削除 ← **ダウン開始点** |
| 3c | `docker compose up -d` | `.github/workflows/deploy.yml:263` | 新コンテナ起動 |
| 4 | backend healthy 待ち | `.github/workflows/deploy.yml:265` | `docker inspect Health.Status == "healthy"` を最大120s |
| 4b | `nginx -s reload` | `.github/workflows/deploy.yml:273` | Docker 内部 DNS キャッシュリフレッシュ |
| 5 | SA-18 bootstrap | `.github/workflows/deploy.yml:283` | salesanchor_app ロール設定（冪等） |
| 6 | migrations | `.github/workflows/deploy.yml:341` | `bash scripts/run_all_migrations.sh`（backend/migration変更時のみ） |
| 7 | smoke tests | `.github/workflows/deploy.yml:362` | migration があった場合のみ |
| 8 | health check + auto-rollback | `.github/workflows/deploy.yml:449` | `/api/health` 失敗時 PREV_SHA に戻す |

---

## 2. 29秒ダウン窓の中身

### タイムライン

```
[3b] docker rm -f backend/frontend  ← ダウン開始（nginx が 502 を返し始める）
  ↓ 0-2秒
[3c] docker compose up -d           ← 新コンテナ起動 (uvicorn 起動: ~3-5秒)
  ↓ start_period 15秒（docker-compose.yml:115）
[4]  healthcheck 初回チェック        ← PASS でようやく "healthy"
  ↓
[4b] nginx -s reload                ← DNS キャッシュリフレッシュ
     ← ダウン終了（nginx が backend に転送できる状態に）
```

### ダウン時間を生む構造的原因

1. **コンテナ削除から起動まで連続的に空白が生まれる**（`.github/workflows/deploy.yml:260`）  
   force-rm → `up -d` の間、`backend` という名前のコンテナが存在しない。

2. **nginx は Docker 内部 DNS でプロキシ解決する**（`nginx/nginx.conf:150`）  
   `proxy_pass http://backend:8000/api/` — コンテナ不在 = DNS NXDOMAIN → 502。

3. **healthcheck の start_period が15秒**（`docker-compose.yml:115`）  
   `start_period: 15s, interval: 30s, retries: 3` → 最短15秒後に初回チェック。  
   nginx reload はその後（`.github/workflows/deploy.yml:274`）→ 合計15〜45秒の窓。

4. **migration は `up -d` の後に走る**（`.github/workflows/deploy.yml:355`）  
   起動済み新コンテナ1台のみの状態で migration を実行 → 並走コンテナへの双方向互換が必要な構造。

---

## 3. リバースプロキシ / Web 前段

### 構成

```
Internet (443/80)
    ↓
[nginx コンテナ]（docker-compose.yml:4-35, ports: 80:80/443:443）
    ├─ /api/       → proxy_pass http://backend:8000  (nginx.conf:146-159)
    ├─ /api/v1/auth/ → proxy_pass http://backend:8000  (nginx.conf:91-104)
    ├─ /api/v1/conversations/stream → backend SSE (nginx.conf:107-124)
    └─ /           → proxy_pass http://frontend:8080  (nginx.conf:200-206)
```

### nginx 設定の重要点

- **プロキシはホスト名ベース**（http://backend:8000）— コンテナ名が Docker DNS で解決される
- nginx は `restart: unless-stopped`（`docker-compose.yml:16`）— 常時稼働、コンテナ再作成不要
- `proxy_connect_timeout 10s`（`nginx/nginx.conf:102`）— コンテナ不在時は10秒後にタイムアウト → 502
- nginx ネットワーク: `frontnet` のみ（`docker-compose.yml:35`）— backend も frontnet に属す（`docker-compose.yml:131`）

### blue-green 可能性への影響

- nginx がコンテナ名でプロキシするため、**nginx upstream 設定の切り替え** か **コンテナ名エイリアス変更**がゼロダウンタイムの鍵。
- nginx コンテナ自身は常時生存 → `nginx -s reload` で設定変更を無停止で反映可能。

---

## 4. ヘルスチェック

### アプリエンドポイント

`backend/app/routers/health.py:16`  
`GET /api/health`

| チェック項目 | 結果 | HTTP ステータス |
|------------|------|----------------|
| DB 接続（必須） | 失敗 | 503 |
| DB 接続（必須） | 正常 | 200 |
| Redis / Celery | 失敗 | 200 degraded |

DB 接続チェック: `SELECT 1`（`backend/app/routers/health.py:29`）

### Docker healthcheck 設定

| サービス | 設定 | file:line |
|--------|------|-----------|
| backend | `python -c "urllib.request.urlopen('http://localhost:8000/api/health')"` | `docker-compose.yml:111` |
|  | `start_period: 15s, interval: 30s, timeout: 10s, retries: 3` | `docker-compose.yml:112` |
| frontend | `wget --spider http://127.0.0.1:8080/` | `docker-compose.yml:147` |
|  | `start_period: 15s, interval: 30s` | `docker-compose.yml:149` |
| nginx | `curl -f http://localhost:80/nginx_status` | `docker-compose.yml:18` |
| postgres | `pg_isready -U ${POSTGRES_USER}` | `docker-compose.yml:315` |

### deploy.yml でのヘルス確認箇所

- Step 4: `docker inspect Health.Status == "healthy"` 最大120s待ち（`.github/workflows/deploy.yml:265`）
- Finalize: `urllib.request.urlopen('http://localhost:8000/api/health')` で最終確認（`.github/workflows/deploy.yml:450`）

---

## 5. コンテナ / ポート構成

### サービス一覧

| サービス | ポートマッピング | ネットワーク | リソース上限 |
|--------|--------------|-------------|------------|
| nginx | 80:80, 443:443 | frontnet | 256M / 0.5cpu |
| backend | なし（frontnet 内部のみ） | frontnet + backnet | 512M / 1.0cpu |
| frontend | なし | frontnet | 128M / 0.25cpu |
| celery-worker | なし | backnet | 512M / 1.0cpu |
| celery-beat | なし | backnet | 128M / 0.25cpu |
| discord-gateway | なし | backnet | 256M / 0.5cpu |
| redis | なし | backnet | 320M（maxmemory 256mb） / 0.5cpu |
| postgres | なし | backnet | 1G / 1.0cpu |

`docker-compose.yml:116`（backend）、`docker-compose.yml:4`（nginx）

### 第2インスタンス並走の余地

- **backend/frontend にはポートマッピングなし** → blue インスタンスと green インスタンスを異なるコンテナ名で起動しても、ポート競合は起きない
- **nginx が upstream をコンテナ名で直指定** → `backend-blue` / `backend-green` を nginx.conf に追記し reload すれば切り替え可能
- **VPS リソース制約**: backend が512M/1cpu × 2台 = 計1024M/2cpu。VPS 総メモリ次第（現状未確認 → 設計フェーズで要確認）
- postgres / redis は状態を持つため再作成対象外（`.github/workflows/deploy.yml:259` でも除外済み）

---

## 6. migration とデプロイの関係

### 実行タイミング

`.github/workflows/deploy.yml:341`: `steps.changes.outputs.migrations == 'true'` の場合のみ実行。  
`backend/**`, `migrations/**`, `scripts/**`, `docker-compose.yml`, `deploy.yml` のいずれかが変更された場合に該当（`.github/workflows/deploy.yml:37`）。

### run_all_migrations.sh の動作

`scripts/run_all_migrations.sh:1`  
- `docker cp scripts ${BACKEND}:/app/` と `docker cp migrations ${BACKEND}:/app/` でファイルをコンテナにコピー
- `run_py` ヘルパー: `docker exec -e DATABASE_URL="${ADMIN_DATABASE_URL:-$DATABASE_URL}" ${BACKEND} python <script>`
- `run_sql` ヘルパー: `docker exec -i ${POSTGRES} psql -U jarvis -d jarvis_db < <file>`
- TOTAL=120 ステップ（`scripts/run_all_migrations.sh:63`）

### migration 実行時の状態

- `docker compose up -d` 後（`.github/workflows/deploy.yml:263`）に migration が実行される
- 実行時点では **新コンテナ1台のみ**稼働している（旧コンテナは force-rm 済み）
- migration は **新コンテナ上で実行** されるため、新旧コンテナ並走中のスキーマ変更は現構成では発生しない
- **後方互換（backward-compatible）スキーマ変更**は `backend/CLAUDE.md` で強制：`additive-only`（カラム追加のみ許可、削除禁止）

### blue-green 並走時の migration 考慮点

blue コンテナ（旧コード）が稼働中に migration（スキーマ変更）を流す場合、  
**roaming columns**（新カラムに旧コードがアクセスしない）であれば後方互換が成立する。  
`additive-only` 原則（`backend/CLAUDE.md`）により、カラム削除・型変更は行われないため、  
新カラム追加のみなら旧コードは無視するだけで問題なし。

---

## 7. VPS 実機確認結果（2026-06-11）

### メモリ状況（`docker stats --no-stream` + `free -h`）

| 項目 | 値 |
|-----|----|
| 総メモリ | 1.9 GiB |
| 使用中 | 1.6 GiB |
| 空き（free） | 90 MiB |
| 利用可能（available、buff/cache含む） | **330 MiB** |
| Swap 総量 | 2.0 GiB |
| Swap 使用中 | **1.1 GiB（55%使用）** |

**現在の backend 実使用量**: 117 MiB / 512 MiB limit（22.85%）

**第2インスタンス並走の判定**:
- available 330 MiB に対して実際の backend 使用量は 117 MiB → **起動自体は可能**
- ただし Swap が既に 1.1 GiB 使用中 → 追加インスタンス起動でスワップ圧力が増加
- blue-green 切替時間（30〜60 秒）の一時的並走ならリスク許容範囲

### backend 起動時間の実測（デプロイログ 2026-06-10 23:53〜）

```
23:53:47.350  Uvicorn running on http://0.0.0.0:8000 (Started parent process [1])
              ← コンテナ起動直後: listen ソケット open だが worker プロセスなし
              ← この時点で nginx が接続しても 502 またはコネクションキューに積まれる
  ↓ 22秒
23:54:09.699  Started server process [9] / Application startup complete
              ← worker 起動完了・リクエスト処理可能になる（Python import + DB pool init で 22 秒）
  ↓ 26秒
23:54:35.979  GET /api/health 200 OK
              ← Docker healthcheck 初回 PASS（start_period 15s 経過後の最初の interval）
```

**ダウンタイムの実測根拠**:
- コンテナ削除 → 新コンテナ起動（~1s）+ worker 起動完了（22s）= **約 23 秒がサービス不能**
- 報告された 29 秒との差（~6 秒）= `docker rm -f` の処理時間 + Docker compose up のオーバーヘッド
- Docker healthcheck の PASS は 48 秒後 → deploy.yml step 4b の `nginx -s reload` もそれ以降
- **nginx の IP キャッシュ**: Docker 内部 DNS が旧コンテナ削除時に更新されるため、新コンテナが同 IP を取得すれば nginx reload 不要。同 IP が割り当てられない場合は reload まで 502 継続

---

## 8. 制約・リスクのまとめ（設計フェーズへの引き継ぎ）

| 制約 | 詳細 | file:line |
|-----|------|-----------|
| nginx upstream がコンテナ名固定 | http://backend:8000 — blue/green切替には設定変更が必要 | `nginx/nginx.conf:150` |
| healthcheck start_period が15s | 最短でも15秒後まで healthy 判定が出ない | `docker-compose.yml:115` |
| VPS リソース | backend×2台並走は512M×2=1024M必要。VPS 総メモリ要確認 | — |
| migration タイミング | 現在は `up -d` 後・単一コンテナで実行。blue-green 並走中の実行順序設計が必要 | `.github/workflows/deploy.yml:355` |
| nginx `proxy_pass` DNS解決 | nginx は起動時に名前解決し、コンテナ再起動でDNSが変わっても古いIPをキャッシュする可能性あり。`resolver` 設定 or `nginx -s reload` で対処可能 | `nginx/nginx.conf:95` |
| `stop_grace_period: 40s` | backend コンテナは SIGTERM 後40秒間は応答を試みる | `docker-compose.yml:109` |

---

## 8. 設計フェーズへの示唆（推測なし・事実ベース）

以下は事実から読み取れる設計オプションの素材。**選択は設計フェーズで行う**。

1. **nginx upstream 切替方式が現実的**:  
   - nginx は常時稼働（コンテナ再作成不要）
   - `nginx -s reload` で設定変更が無停止で反映される（`.github/workflows/deploy.yml:274` に実績あり）
   - `resolver 127.0.0.11 valid=5s` を追加すれば Docker 内部 DNS を動的解決できる

2. **healthcheck 完了後に切替**:  
   - `docker inspect Health.Status` で healthy 確認済みのインスタンスへ切替（`.github/workflows/deploy.yml:266` に実績あり）

3. **migration の実行タイミング**:  
   - additive-only 原則により、新コンテナ起動 → migration → 旧コンテナ停止 の順序でも旧コードは動作可能
   - ただし migration が失敗した場合のロールバック（新コンテナ削除 → 旧コンテナ復帰）が必要
