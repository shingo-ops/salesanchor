# recon.md — ゼロダウンタイムデプロイ 仕上げ

> 作成: 2026-06-11 | STANDARD-WORKFLOW Phase ① recon | 担当: architect  
> 前提: `docs/handoff/zero-downtime-deploy/recon.md` + `design.md`（初回 blue-green 実装）  
> 初回本番デプロイ結果: 502=0件、504=1件、監視2分ブラインドスポット

---

## 1. 二重 blue-green 切替（最重要）

### 問題の構造

毎デプロイで blue-green が **2回**走る。

| 回 | 実行箇所 | タイムスタンプ（2026-06-11 本番） |
|----|---------|-------------------------------|
| 1回目 | Step 3b `bash scripts/blue-green-cutover.sh` | `03:33:50Z`〜`03:34:35Z`（45s） |
| 2回目 | SA-18 bootstrap `BG_HEALTH_TIMEOUT=90 bash scripts/blue-green-cutover.sh` | `03:34:46Z`〜`03:35:50Z`（64s） |

### SA-18 bootstrap の実行フロー（`.github/workflows/deploy.yml:285-332`）

```
deploy.yml:290  if: ${{ success() }}  ← 毎回実行（migration 条件なし）
deploy.yml:301-304  ALTER ROLE salesanchor_app PASSWORD（冪等）
deploy.yml:310  if grep -q '^SA18_PHASE2_ENABLED=1' .env
                  ← 本番 .env に SA18_PHASE2_ENABLED=1 が設定済み → **常に true**
deploy.yml:311-314  _pgdb / _sa_url を組み立て
deploy.yml:315  sed -i '/^DATABASE_URL=/d' .env
deploy.yml:316  echo "DATABASE_URL=${_sa_url}" >> .env
                  ← パスワード未ローテーション時は Step2 の値と同一
deploy.yml:323  BG_HEALTH_TIMEOUT=90 bash scripts/blue-green-cutover.sh
                  ← DATABASE_URL が変わっていなくても blue-green が走る（冪等チェックなし）
```

### Step 2 との関係（`.github/workflows/deploy.yml:217-233`）

```
deploy.yml:218  if grep -q '^SA18_PHASE2_ENABLED=1' .env
deploy.yml:219    → "salesanchor_app URL を保持します" ← DATABASE_URL は変更しない
```

Step 2 がすでに salesanchor_app URL を保持するため、Step 3b（1回目 blue-green）は正しい DATABASE_URL でコンテナを起動済み。SA-18 bootstrap がパスワード未ローテーション時に同一 URL で上書きしても意味がない。

### 二重になる根本原因

`deploy.yml:323` の blue-green 実行前に **「DATABASE_URL が実際に変わったか」の確認がない**。

### 安全なスキップ条件（設計フェーズで実装）

```bash
# deploy.yml:314 あたりに挿入（sed の前）
_old_url=$(grep '^DATABASE_URL=' .env | head -1 | cut -d= -f2-)

# [URL 再構築: deploy.yml:315-316 の既存 sed/echo]
sed -i '/^DATABASE_URL=/d' .env
echo "DATABASE_URL=${_sa_url}" >> .env

# 変更がなければ blue-green スキップ
_new_url=$(grep '^DATABASE_URL=' .env | head -1 | cut -d= -f2-)
if [ "$_old_url" != "$_new_url" ]; then
  BG_HEALTH_TIMEOUT=90 bash scripts/blue-green-cutover.sh
  ...
else
  echo "DATABASE_URL 変更なし: SA18 blue-green スキップ"
fi
```

**安全性の根拠**:
- 純粋な文字列比較のみ（データ変更なし）
- パスワードローテーション時は URL が変わるため blue-green は確実に実行される
- Step 2 の保持ロジックと矛盾しない

---

## 2. nginx 504 の根本原因

### 現状の nginx proxy_pass（`resolver` なし）

`nginx/nginx.conf` に `resolver` ディレクティブは**存在しない**。

nginx worker プロセスが起動時に `backend` を DNS 解決し、その IP をキャッシュする。  
`nginx -s reload` で新 worker が起動すると新 IP を解決するが、旧 worker は古い IP を保持したまま in-flight リクエストを処理し続ける。

| 切替ステップ | 経過時間 | nginx の状態 |
|------------|---------|-------------|
| `docker network connect --alias backend frontnet green` | t+0 | 旧/新 worker 共存（旧=old IP, 新=green IP） |
| `docker network disconnect frontnet old` | t+0.5s | 旧 worker の old IP → frontnet から削除 → 到達不能 |
| `docker exec nginx nginx -s reload` | t+0.75s | 新 worker 起動、green IP を解決 |
| 旧 worker の timeout | t+0.75s〜+120s | `proxy_read_timeout 120s` 待ち → **504 を返す** |

### proxy_read_timeout の実測値

```
nginx/nginx.conf:103   proxy_read_timeout    120s;  ← /api/v1/auth/
nginx/nginx.conf:118   proxy_read_timeout        3600s;  ← /conversations/stream（SSE）
nginx/nginx.conf:138   proxy_read_timeout        3600s;  ← /leads/stream（SSE）
nginx/nginx.conf:158   proxy_read_timeout    120s;  ← /api/（汎用）
nginx/nginx.conf:197   proxy_read_timeout 30s;      ← /metrics
nginx/nginx.conf:263   proxy_read_timeout    120s;  ← HTTPS /api/v1/auth/
nginx/nginx.conf:278   proxy_read_timeout        3600s;  ← HTTPS /conversations/stream（SSE）
nginx/nginx.conf:298   proxy_read_timeout        3600s;  ← HTTPS /leads/stream（SSE）
nginx/nginx.conf:318   proxy_read_timeout    120s;  ← HTTPS /api/（汎用）
```

`proxy_read_timeout 120s` が 2分間の監視ブラインドスポットの原因（監視 curl が 120s ブロック）。

### `resolver 127.0.0.11 valid=5s` + 変数 proxy_pass の適用対象

`backend` ホスト名を proxy_pass している全箇所（9か所）：

**app.salesanchor.jp（HTTP + HTTPS、`nginx/nginx.conf:67` / `nginx/nginx.conf:228` server block）:**

| 行番号 | location | proxy_pass |
|-------|---------|------------|
| `nginx.conf:95` | `/api/v1/auth/` | `http://backend:8000/api/v1/auth/` |
| `nginx.conf:108` | `= /api/v1/conversations/stream` | `http://backend:8000/api/v1/conversations/stream` |
| `nginx.conf:128` | `= /api/v1/leads/stream` | `http://backend:8000/api/v1/leads/stream` |
| `nginx.conf:150` | `/api/` | `http://backend:8000/api/` |
| `nginx.conf:192` | `= /metrics` | `http://backend:8000/metrics` |

**api.salesanchor.jp（HTTPS、`nginx/nginx.conf:228` server block）:**

| 行番号 | location | proxy_pass |
|-------|---------|------------|
| `nginx.conf:255` | `/api/v1/auth/` | `http://backend:8000/api/v1/auth/` |
| `nginx.conf:268` | `= /api/v1/conversations/stream` | `http://backend:8000/api/v1/conversations/stream` |
| `nginx.conf:288` | `= /api/v1/leads/stream` | `http://backend:8000/api/v1/leads/stream` |
| `nginx.conf:310` | `/api/` | `http://backend:8000/api/` |

**対象外（IP アドレス直指定 / frontend）:**
- `nginx.conf:162`: `http://49.212.160.98:3000/grafana/` — DNS 不使用・変更不要
- `nginx.conf:179`: `http://49.212.160.98:3001/` — DNS 不使用・変更不要
- `nginx.conf:201`: `http://frontend:8080/` — blue-green 対象外・変更不要

### 変更方針

`resolver` は `server` ブロックに1箇所置くと配下の全 `location` に適用される。

**app.salesanchor.jp（`nginx.conf:67-213`）**: 1つ追加  
**api.salesanchor.jp（`nginx.conf:228-325`）**: 1つ追加

各 `proxy_pass http://backend:8000/...` を変数経由に変更：
```nginx
# server ブロック冒頭（nginx.conf:67 直後 または nginx.conf:228 直後）に追加
resolver 127.0.0.11 valid=5s;
set $backend_upstream "backend:8000";
```
```nginx
# 各 location 内: http://backend:8000/... → http://$backend_upstream/...
proxy_pass http://$backend_upstream/api/v1/auth/;
proxy_pass http://$backend_upstream/api/v1/conversations/stream;
...
```

**SSE（3600s タイムアウト）への影響**:  
SSE は長時間接続。切替後の **新規** SSE 接続は即座に green に向く（DNS 再解決）。  
切替時点で **既存** の SSE 接続はコンテナ断で切断されるが、これは blue-green の本質的な制約であり resolver 変更で変わらない。

### `nginx -s reload` の要否

変数 proxy_pass + resolver により nginx は各リクエスト時に Docker DNS を参照（TTL=5s）。  
エイリアス切替後 **最大 5s** で全リクエストが green に向く。理論上は `nginx -s reload` 不要になるが、  
`blue-green-cutover.sh:144` の reload は念押しとして残して問題なし（ゼロコスト）。

---

## 3. 監視スクリプトのブラインドスポット

### 対象ファイル

`scripts/dry-run-blue-green.sh:80-82`（バックグラウンドモニター内の curl）:

```bash
_status=$(docker exec "${COMPOSE_PROJECT}-nginx-1" \
  curl -s -o /dev/null -w "%{http_code}" \
  "http://backend:8000/api/health" 2>/dev/null || echo "err")
```

`--max-time` なし → backend が到達不能のとき curl がブロック → 監視ループが停止。

### 初回本番デプロイでの実測

- `proxy_read_timeout 120s` のため 1リクエストが 120s ブロック
- その間 SA-18 の第2回 cutover（12:35:27）の状況が記録不能
- 結果: 12:34:27〜12:36:29 の 122s がブラインドスポット

### 修正方針

`scripts/dry-run-blue-green.sh:81` に `--max-time 5` を追加：

```bash
_status=$(docker exec "${COMPOSE_PROJECT}-nginx-1" \
  curl -s --max-time 5 -o /dev/null -w "%{http_code}" \
  "http://backend:8000/api/health" 2>/dev/null || echo "err")
```

- 5s 以内に応答がなければ `err` として FAIL ログに記録 → ブラインドスポット解消
- 通常リクエスト（< 1s）への影響なし
- resolver 修正後は 5s 制限に引っかかるケースほぼゼロ

---

## 4. 制約・リスクのまとめ（設計フェーズへの引き継ぎ）

| 項目 | 詳細 | 関連 file:line |
|-----|------|--------------|
| SA-18 blue-green スキップ条件 | URL 比較は `_sa_url` 組み立て後に実施（組み立て前と比較すると unset 変数で失敗） | `.github/workflows/deploy.yml:315` |
| resolver ディレクティブのスコープ | `server` ブロック内に1回置けば全 `location` に適用 | `nginx/nginx.conf:67`、`nginx/nginx.conf:228` |
| 変数 proxy_pass と path rewriting | パス付き `proxy_pass http://$var/api/` は通常の path rewriting と同じ動作（nginx 公式仕様） | `nginx/nginx.conf:150` |
| SSE 既存接続の断 | resolver 変更後も blue-green 切替時に既存 SSE は切断される。クライアント側 reconnect 必須（現状変わらず） | `nginx/nginx.conf:108`、`nginx/nginx.conf:268` |
| dry-run 本番反映不要 | `--max-time 5` は dry-run スクリプト内のみの変更。本番 nginx.conf とは無関係 | `scripts/dry-run-blue-green.sh:81` |

---

## 5. 設計フェーズへの示唆

1. **優先度高**: `deploy.yml:314`〜`deploy.yml:323` の URL 比較 + スキップ（デプロイ時間半減、監視ブラインド解消）
2. **優先度中**: `nginx.conf` 全9箇所の resolver + 変数 proxy_pass（504 完全排除）
3. **優先度低**: `dry-run-blue-green.sh:81` の `--max-time 5`（素振り監視の精度向上）

変更順序の推奨: (1) → (3) → (2) の順に PR 分割。nginx.conf 変更は本番反映に `nginx -t` + VPS 素振り必須。
