# recon.md — nginx resolver + proxy_pass 変数化（ADR-133）

> 作成: 2026-06-11 | STANDARD-WORKFLOW Phase ② 現在地把握  
> PO 承認: KGI 承認済み（TTL=5s・案A先行）  
> 次工程: 本ドキュメントを設計ドキュメント (design.md) で相互参照すること

---

## 0. 調査対象ファイル

| ファイル | 用途 |
|---------|------|
| `nginx/nginx.conf` | nginx 全設定（447行） |
| `docker-compose.yml` | コンテナ構成・ネットワーク定義 |
| `docs/handoff/zero-downtime-deploy/recon.md` | 隣接案件との重複確認 |

---

## 1. 全 proxy_pass 箇所の完全リスト（推測なし）

### 1-A. backend:8000 へ転送する 9 箇所（変数化対象）

| # | file:line | server_name | location 型 | location パターン | proxy_pass 現行値 | location前缀 = URI後缀 | 変換判定 |
|---|-----------|------------|------------|-----------------|---------------------|----------------------|---------|
| 1 | `nginx/nginx.conf:95` | app.salesanchor.jp | prefix | `/api/v1/auth/` | `http://backend:8000/api/v1/auth/` | ✓ 一致 | **変換そのまま可** |
| 2 | `nginx/nginx.conf:108` | app.salesanchor.jp | exact (`=`) | `/api/v1/conversations/stream` | `http://backend:8000/api/v1/conversations/stream` | ✓ 一致 | **変換そのまま可** [SSE] |
| 3 | `nginx/nginx.conf:128` | app.salesanchor.jp | exact (`=`) | `/api/v1/leads/stream` | `http://backend:8000/api/v1/leads/stream` | ✓ 一致 | **変換そのまま可** [SSE] |
| 4 | `nginx/nginx.conf:150` | app.salesanchor.jp | prefix | `/api/` | `http://backend:8000/api/` | ✓ 一致 | **変換そのまま可** |
| 5 | `nginx/nginx.conf:192` | app.salesanchor.jp | exact (`=`) | `/metrics` | `http://backend:8000/metrics` | ✓ 一致 | **変換そのまま可** |
| 6 | `nginx/nginx.conf:255` | api.salesanchor.jp | prefix | `/api/v1/auth/` | `http://backend:8000/api/v1/auth/` | ✓ 一致 | **変換そのまま可** |
| 7 | `nginx/nginx.conf:268` | api.salesanchor.jp | exact (`=`) | `/api/v1/conversations/stream` | `http://backend:8000/api/v1/conversations/stream` | ✓ 一致 | **変換そのまま可** [SSE] |
| 8 | `nginx/nginx.conf:288` | api.salesanchor.jp | exact (`=`) | `/api/v1/leads/stream` | `http://backend:8000/api/v1/leads/stream` | ✓ 一致 | **変換そのまま可** [SSE] |
| 9 | `nginx/nginx.conf:310` | api.salesanchor.jp | prefix | `/api/` | `http://backend:8000/api/` | ✓ 一致 | **変換そのまま可** |

#### 変換そのまま可の根拠（URI転送等価性）

nginx の動作原則:

- **静的 proxy_pass（URI 付き）**: `location /api/` + `proxy_pass http://backend:8000/api/;`  
  → リクエスト `/api/foo` をバックエンドへ: location prefix `/api/` を URI suffix `/api/` で置換 → `/api/foo`

- **変数 proxy_pass（URI なし）**: `set $backend backend; proxy_pass http://$backend:8000;`  
  → nginx は変数を含む場合 URI 置換を行わず、`$request_uri` をそのままフォワード → `/api/foo`

**9 箇所すべてで location prefix == proxy_pass URI suffix** のため、URI の末尾を除いた変数形式（http://$backend:8000 形式）にしても転送先パスは変わらない。`rewrite` / `break` の追加は不要。

### 1-B. backend 以外への proxy_pass（変数化スコープ外）

| file:line | server_name | location | proxy_pass 現行値 | 対応 |
|-----------|------------|---------|-----------------|-----|
| `nginx/nginx.conf:162` | app.salesanchor.jp | `/grafana/` | `http://49.212.160.98:3000/grafana/` | 外部 IP 直指定・DNS 不要 → **対象外** |
| `nginx/nginx.conf:179` | app.salesanchor.jp | `/status/` | `http://49.212.160.98:3001/` | 外部 IP 直指定 → **対象外**（注: location `/status/` を `/` URI に strip する挙動あり） |
| `nginx/nginx.conf:201` | app.salesanchor.jp | `/` | `http://frontend:8080/` | frontend コンテナ（Docker DNS 問題は原理上同一）→ **本件スコープ外・別途検討** |
| `nginx/nginx.conf:368` | monitor.salesanchor.jp | `/` | `http://49.212.160.98:3001/` | 外部 IP 直指定 → **対象外** |

> **注**: frontend:8080 も backend と同じ DNS 固着問題を持つ。本 ADR のスコープは backend のみだが、将来同様の変数化を適用する際の参考として記録する。

---

## 2. SSE location の特殊設定（全 4 箇所）

SSE 専用設定を持つ location: `nginx/nginx.conf:107`（行107-124）、`nginx/nginx.conf:127`（行127-144）、`nginx/nginx.conf:266`（行266-284）、`nginx/nginx.conf:286`（行286-304）

各 SSE location が持つ設定（4 箇所すべて同一）:

| 設定 | 値 | 目的 |
|-----|---|-----|
| `proxy_buffering off` | `nginx/nginx.conf:116` | バッファリング無効（SSE イベント即時転送） |
| `proxy_cache off` | `nginx/nginx.conf:117` | キャッシュ無効 |
| `proxy_read_timeout 3600s` | `nginx/nginx.conf:118` | 長時間接続維持（1時間） |
| `proxy_send_timeout 3600s` | `nginx/nginx.conf:119` | 同上 |
| `proxy_connect_timeout 10s` | `nginx/nginx.conf:120` | 接続タイムアウト（通常と同値） |
| `proxy_http_version 1.1` | `nginx/nginx.conf:121` | HTTP/1.1 keep-alive（SSE 必須） |
| `chunked_transfer_encoding on` | `nginx/nginx.conf:122` | チャンク転送エンコーディング |

**変数化との干渉なし**: これらの設定はすべて `proxy_pass` とは独立した location ブロック内ディレクティブであり、`set $backend` / `proxy_pass http://$backend:8000` への変換後も同一 location 内に残るため、挙動は変わらない。

`Connection ''` ヘッダーの上書きは現行設定に存在しない（行107-124 全行確認済み）。`proxy_http_version 1.1` が keep-alive を確保しているため SSE 動作に問題はない。

---

## 3. 変数宣言スコープ方針

### 前提: nginx `set` ディレクティブの有効スコープ

- `set` は `http`、`server`、`location` コンテキストで使用可能
- `conf.d/default.conf` としてマウントされているため（`docker-compose.yml:11`）、本ファイルは `http` ブロック内に include される → ファイル内に `http {}` ブロックを書けない
- `resolver` ディレクティブは `http`、`server`、`location` コンテキストで有効

### 採用方針: **server ブロック単位に 1 回宣言**

```nginx
server {
    # ... ssl/security ヘッダー ...
    resolver 127.0.0.11 valid=5s;
    set $backend backend;

    location /api/v1/auth/ {
        proxy_pass http://$backend:8000;
        # ... 他の設定はそのまま維持 ...
    }

    location = /api/v1/conversations/stream {
        proxy_pass http://$backend:8000;
        # ... SSE 設定はそのまま維持 ...
    }
    # ...
}
```

根拠:
1. **宣言 1 回で全 location に適用**: `app.salesanchor.jp` サーバーブロック（`nginx/nginx.conf:67`）と `api.salesanchor.jp` サーバーブロック（`nginx/nginx.conf:228`）それぞれで 1 回宣言すれば、配下の全 location が `$backend` を使用できる
2. **可読性**: location 毎に `set` を繰り返す必要がなく、変更点が server ブロック先頭に集約される
3. **resolver スコープ**: `server` レベルの `resolver` は同サーバーブロック内の全 `proxy_pass` 変数解決に適用される（nginx 公式ドキュメント準拠）

変更が必要なサーバーブロック:
- `nginx/nginx.conf:67`（app.salesanchor.jp HTTPS、行67-207）
- `nginx/nginx.conf:228`（api.salesanchor.jp HTTPS、行228-325）

変更不要（proxy_pass なしまたは外部 IP 直指定のみ）:
- 行11-24（jarvis-claude.uk HTTP → return 301 のみ）
- 行29-47（jarvis-claude.uk HTTPS → return 301 のみ）
- 行53-65（app.salesanchor.jp HTTP → return 301 のみ）
- 行333-378（monitor.salesanchor.jp → 外部 IP 直指定）
- 行386-446（salesanchor.jp → 静的ファイル、proxy_pass なし）

---

## 4. resolver 前提の確認

### Docker 埋め込み DNS アドレス

`127.0.0.11` は Docker の bridge ネットワーク内コンテナに固定で提供される埋め込み DNS リゾルバのアドレス（Docker 公式仕様）。

### ネットワーク構成の確認

```
docker-compose.yml:379
networks:
  frontnet:
  backnet:
```

両ネットワークとも `driver`・`ipam` の明示設定なし → Docker デフォルト bridge ドライバ・IPAM 自動割り当て。

nginx コンテナのネットワーク: `frontnet` のみ（`docker-compose.yml:34`）  
backend コンテナのネットワーク: `frontnet` + `backnet`（`docker-compose.yml:130`）

→ nginx と backend は同一 `frontnet` ネットワーク上に存在。Docker 埋め込み DNS は bridge ネットワーク内で常に `127.0.0.11` で到達可能。

**`backend` 名の解決確認手順**（本番相当環境での実機確認手順）:

```bash
# nginx コンテナ内から backend DNS 解決確認
docker compose exec nginx sh -c "nslookup backend 127.0.0.11"
# または
docker compose exec nginx sh -c "getent hosts backend"
```

コンテナ外部からの検証:
```bash
docker compose exec nginx sh -c "wget -q -O- http://backend:8000/api/health && echo OK"
```

### TTL=5s の根拠

- `valid=5s`: PO 承認済み（recon brief §0）
- zero-downtime-deploy/recon.md §8「nginx upstream がコンテナ名固定」の改善策と整合（零停止デプロイ案件 recon.md 245行目）
- backend 起動完了まで約 22 秒（零停止デプロイ案件 recon.md 209-211行目）のうち、DNS 解決は TTL（5s）後に自動再試行 → restart 後の自動復帰: **≤ 5s + nginx 再接続オーバーヘッド ≒ ≤15s**（KGI #2 の目安と整合）

---

## 5. 隣接案件（zero-downtime-deploy）との重複確認

zero-downtime-deploy/recon.md 245行目に以下の記述あり:

> `resolver 127.0.0.11 valid=5s` を追加すれば Docker 内部 DNS を動的解決できる

`docs/handoff/zero-downtime-deploy/` に `design.md` は現時点で**存在しない**（`ls` 確認済み）。

**PO 承認済み方針（recon brief §4）**: 本件（ADR-133）を先行し、zero-downtime-deploy の design.md 作成時に「nginx.conf 改修部分は ADR-133 完了を前提とする」旨を明記する。本 PR マージ後、zero-downtime-deploy 案件の設計ドキュメント作成者が本 ADR を参照すること。

---

## 6. ADR 番号確認

リポジトリ内 ADR ファイル（最終確認）:

- コミット済み最新: `ADR-125-fedex-rates-stage1.md`
- 未コミット（untracked）: `ADR-126`、`ADR-127`、`ADR-128`
- recon brief 記載「現行最新 ADR-132 の次」→ ADR-129〜132 は他ブランチ or 計画中

ADR-133 の番号はブリーフ指定通り（recon brief §3）。ファイル名: `ADR-133-nginx-resolver-proxy-pass-variable.md`（設計フェーズで確定）。

---

## 7. 変換前後の等価性まとめ（設計フェーズへの引き渡し）

### 9 箇所すべて: rewrite 不要・特殊対応不要

| 変換前 | 変換後 | 等価性 |
|-------|-------|-------|
| `proxy_pass http://backend:8000/api/v1/auth/;` | `proxy_pass http://$backend:8000;` | ✓ URI = location prefix |
| `proxy_pass http://backend:8000/api/v1/conversations/stream;` | `proxy_pass http://$backend:8000;` | ✓ exact match → URI そのまま |
| `proxy_pass http://backend:8000/api/v1/leads/stream;` | `proxy_pass http://$backend:8000;` | ✓ exact match → URI そのまま |
| `proxy_pass http://backend:8000/api/;` | `proxy_pass http://$backend:8000;` | ✓ URI = location prefix |
| `proxy_pass http://backend:8000/metrics;` | `proxy_pass http://$backend:8000;` | ✓ exact match → URI そのまま |
| （api ドメイン側も同様 5 箇所は同一パターン） | | |

**SSE 設定の維持**: 変換後も `proxy_buffering off`・`proxy_cache off`・`proxy_read_timeout 3600s`・`proxy_http_version 1.1`・`chunked_transfer_encoding on` はすべて location ブロック内に残置するため KGI #4（SSE 再確立）を満たす。

---

## 8. 未解決事項（設計フェーズへの持ち越し）

| # | 事項 | 理由 |
|---|-----|------|
| 1 | frontend:8080 の DNS 固着問題 | 本件スコープ外だが原理的に同一の問題。別案件で対処するか今回含めるかを設計フェーズで判断 |
| 2 | chaos smoke スクリプトの置き場 | `nginx/` 配下か `scripts/` 配下かは設計フェーズで決定 |
| 3 | ADR-129〜132 の空き番号 | 他ブランチに存在する可能性。ADR-133 起案前に PO 確認推奨 |
