# design: ゼロダウンタイムデプロイ 仕上げ（二重切替・504・監視穴）

> 作成: 2026-06-11 | STANDARD-WORKFLOW Phase ③ | 担当: architect  
> recon: `docs/handoff/zero-downtime-polish/recon.md`  
> ADR: ADR-082（ゼロダウンタイムデプロイ手順変更として実装）

---

## 外部・過去事例の参照と我々への応用

| 事例 | 概要 | 本プロジェクトへの応用 |
|-----|------|---------------------|
| nginx resolver + 変数 proxy_pass（Shopify, Cloudflare 事例） | Docker/Consul DNS を動的解決し worker キャッシュ排除 | Docker 内部 DNS (127.0.0.11) + `valid=5s` で5秒以内に新 IP へ追従。reload 不要で 504 排除 |
| Kubernetes rolling update の冪等チェックパターン | Deployment の image hash が変わらなければ Pod 再起動しない | SA-18 bootstrap の DATABASE_URL 比較前後 → URL 同一なら blue-green スキップ |
| nginx variable proxy_pass の URI rewriting 挙動 | host が変数でも path が静的なら location prefix 置換が適用される | `proxy_pass http://$backend_upstream/api/;` は既存の path rewriting と同一動作 |

---

## 技術 How（設計詳細）

### Fix 1: 二重 blue-green を1回に（`.github/workflows/deploy.yml:310-326`）

**変更前の問題**:
```bash
# SA-18 bootstrap（毎回実行）
sed -i '/^DATABASE_URL=/d' .env
echo "DATABASE_URL=${_sa_url}" >> .env
BG_HEALTH_TIMEOUT=90 bash scripts/blue-green-cutover.sh  # ← URL が変わらなくても実行
```

**変更後**:
```bash
_old_url=$(grep '^DATABASE_URL=' .env | head -1 | cut -d= -f2-)
sed -i '/^DATABASE_URL=/d' .env
echo "DATABASE_URL=${_sa_url}" >> .env
_url_changed="false"
[ "${_old_url}" != "${_sa_url}" ] && _url_changed="true"
unset _sa_url _old_url          # パスワード含む URL を即削除
if [ "${_url_changed}" = "true" ]; then
  BG_HEALTH_TIMEOUT=90 bash scripts/blue-green-cutover.sh
  docker compose up -d --force-recreate celery-worker celery-beat discord-gateway
else
  echo "ℹ️  DATABASE_URL 変更なし → SA18 blue-green をスキップ"
fi
```

**安全性**:
- パスワードローテーション時: `_sa_url` が変わる → `_url_changed=true` → 従来どおり2回目実行
- 未ローテーション時: `_old_url == _sa_url` → スキップ → cutover 1回のみ
- `celery/discord --force-recreate` も "URL が変わった場合のみ" に収めて整合

### Fix 2: nginx resolver + 変数 proxy_pass（`nginx/nginx.conf`）

**変更前の問題**:
```nginx
proxy_pass http://backend:8000/api/;  # worker 起動時の IP をキャッシュ → 切替後120s 504
```

**変更後**（app.salesanchor.jp `nginx.conf:67` および api.salesanchor.jp `nginx.conf:228` 各 server ブロックに追加）:
```nginx
resolver 127.0.0.11 valid=5s;        # Docker 内部 DNS、TTL=5s
set $backend_upstream "backend:8000"; # 変数化 → リクエストごとに解決

proxy_pass http://$backend_upstream/api/;  # 各 location を変数経由に
```

**URI rewriting の保全**:
- `proxy_pass http://$backend_upstream/api/;` は host 部分のみ変数。path `/api/` は静的
- nginx は設定パース時に「URI コンポーネントあり」と判定 → location prefix 置換が適用される
- 動作: `location /api/` + request `/api/health` → backend 受信: `/api/health`（変更なし）
- 変更対象9箇所すべて、location prefix = proxy_pass path の "no-op 置換" パターン → `$request_uri` 補正不要

**SSE（3600s タイムアウト箇所）への影響**:
- `proxy_buffering off` / `proxy_read_timeout 3600s` 等の設定は変更しない
- 既存 SSE 接続はコンテナ断で切断される（blue-green の本質的制約、変更なし）
- 新規 SSE 接続は切替後5秒以内に green に向く → 改善

**対象外（変更しない）**:
- `nginx.conf:162` `/grafana/` → `http://49.212.160.98:3000/grafana/`（IP 直指定）
- `nginx.conf:179` `/status/` → `http://49.212.160.98:3001/`（IP 直指定）
- `nginx.conf:201` `/` → `http://frontend:8080/`（blue-green 対象外）

### Fix 3: 監視スクリプトの `--max-time` 追加（`scripts/dry-run-blue-green.sh:81`）

**変更前**:
```bash
curl -s -o /dev/null -w "%{http_code}" "http://backend:8000/api/health"
```

**変更後**:
```bash
curl -s --max-time 5 -o /dev/null -w "%{http_code}" "http://backend:8000/api/health"
```

- backend 不達時に最大5秒で `err` ログ → 監視ループのブロックを排除
- Fix 2 適用後は 5s に引っかかるケースほぼゼロ

---

## KPI・弊害・トレードオフ

| KPI | 基準 | 検証方法 |
|-----|------|--------|
| 502 ゼロ | 連続 `curl /api/health` で 200 継続 | `scripts/dry-run-blue-green.sh` の出力 |
| 504 ゼロ | 同上 | 同上（resolver 適用後） |
| blue-green 回数 | 1回（URL 変更なし） | デプロイログ "SA18: DATABASE_URL 変更なし → blue-green をスキップ" |
| 監視ブラインドスポット | 5s 以内 | `dry-run-blue-green.sh` の FAIL ログで確認 |
| デプロイ総時間 | 初回比 ≤ 同等（2回目 cutover 削減で短縮） | CI ログ |

| 弊害・リスク | 対策 |
|------------|------|
| nginx variable proxy_pass の URI 挙動が想定外 | `nginx -t` で構文確認後、素振り時に9エンドポイント全疎通テスト |
| SSE 既存接続の断 | blue-green の既存制約。クライアント reconnect は変更なし |
| パスワードローテーション時に URL 比較が誤判定 | `_old_url` は sed 削除前に取得するため、rotatied password の場合は確実に異なる文字列になる |

---

## 実装計画

1. `docs/handoff/zero-downtime-polish/design.md`（本ファイル）
2. `.github/workflows/deploy.yml:310-326` — SA-18 URL 比較 + スキップロジック
3. `nginx/nginx.conf` — resolver + set（2 server block）+ 9箇所 proxy_pass 変数化
4. `scripts/dry-run-blue-green.sh:81` — `--max-time 5` 追加

---

## 受け入れ基準（素振りゲート）

| # | 基準 | 検証方法 |
|---|------|--------|
| AC1 | 通常デプロイで blue-green が1回のみ | デプロイログに "SA18: DATABASE_URL 変更なし → blue-green をスキップ" |
| AC2 | URL 変更時は2回目 cutover が走る | VPS .env の DATABASE_URL を手動で jarvis に戻して1デプロイ → 2回目確認 |
| AC3 | 切替中 502/504 ゼロ | `dry-run-blue-green.sh` FAIL=0 |
| AC4 | 9エンドポイント疎通 | `curl` で各 location を確認（200/401/404 等の正常応答） |
| AC5 | SSE ストリーミング継続 | `curl -N` で SSE 接続中に cutover → 接続断後 reconnect を確認 |
| AC6 | 監視空白 ≤ 5s | `dry-run-blue-green.sh` のログに5s超の gap なし |
| AC7 | `git revert` 可能 | PR commit 数確認（単一 commit） |
