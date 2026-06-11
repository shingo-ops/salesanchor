# design.md — nginx resolver + proxy_pass 変数化（ADR-133）

> 作成: 2026-06-11 | STANDARD-WORKFLOW Phase ③ 実現方法の設計  
> recon 参照: `docs/handoff/nginx-resolver-adr133/recon.md`（突合済み・全9箇所「変換そのまま可」）  
> ADR: `docs/adr/ADR-133-nginx-resolver-proxy-pass-variable.md`  
> PO 承認: KGI 承認済み（TTL=5s・案A先行・frontend 含む最終スコープ）

---

## 1. KGI（PO 承認済み・転記）

| # | 成功条件 | 検証方法 |
|---|---------|---------|
| KGI#1 | 4種の再起動（デプロイ／手動 restart／クラッシュ自動再起動／VPS 再起動）で backend/frontend が healthy 後に**人手の nginx 操作ゼロ**で全 API＋画面＋SSE が 200 へ自動復帰 | chaos smoke（本番相当 compose 環境） |
| KGI#2 | 旧 IP 固着による**永続 502 ゼロ**。自動復帰は TTL+マージン以内（valid=5s → 目安 ≤15 秒） | 同上の復帰秒数計測 |
| KGI#3 | **回帰ゼロ**: 全 10 箇所で変換前後の転送先パス・挙動が同一 | ルート等価テスト（全 10 ルートで変換前後レスポンス比較）＋既存 smoke 全 PASS |
| KGI#4 | 再起動後に SSE 接続が再確立し、ストリーミングが再開する | SSE 専用疎通確認 |

KGI 対象外（明記）: backend 自体が落ちている数秒間の一時 502 は本件範囲外。

---

## 2. 変更対象と設計

### 2-A. 対象ファイル

- `nginx/nginx.conf` のみ

### 2-B. 変更サマリー

| server ブロック | file:line | 追加・変更内容 |
|---------------|-----------|--------------|
| app.salesanchor.jp HTTPS | `nginx.conf:67-207` | resolver 追加 + set $backend + set $frontend + 5箇所 backend 変数化 + 1箇所 frontend 変数化 |
| api.salesanchor.jp HTTPS | `nginx.conf:228-325` | resolver 追加 + set $backend + 4箇所 backend 変数化 |
| その他サーバーブロック | — | 変更なし（外部 IP 直指定・静的ファイル・return 301 のみ） |

### 2-C. 具体的変更内容

#### app.salesanchor.jp（`nginx.conf:67-207`）

**追加（`client_max_body_size 10m;` の直後）:**
```nginx
    resolver 127.0.0.11 valid=5s;
    set $backend backend;
    set $frontend frontend;
```

**proxy_pass 変換（6 箇所）:**

| file:line | 変換前 | 変換後 |
|-----------|-------|-------|
| `nginx.conf:95` | `proxy_pass http://backend:8000/api/v1/auth/;` | `proxy_pass http://$backend:8000;` |
| `nginx.conf:108` | `proxy_pass http://backend:8000/api/v1/conversations/stream;` | `proxy_pass http://$backend:8000;` |
| `nginx.conf:128` | `proxy_pass http://backend:8000/api/v1/leads/stream;` | `proxy_pass http://$backend:8000;` |
| `nginx.conf:150` | `proxy_pass http://backend:8000/api/;` | `proxy_pass http://$backend:8000;` |
| `nginx.conf:192` | `proxy_pass http://backend:8000/metrics;` | `proxy_pass http://$backend:8000;` |
| `nginx.conf:201` | `proxy_pass http://frontend:8080/;` | `proxy_pass http://$frontend:8080;` |

#### api.salesanchor.jp（`nginx.conf:228-325`）

**追加（`client_max_body_size 10m;` の直後）:**
```nginx
    resolver 127.0.0.11 valid=5s;
    set $backend backend;
```

**proxy_pass 変換（4 箇所）:**

| file:line | 変換前 | 変換後 |
|-----------|-------|-------|
| `nginx.conf:255` | `proxy_pass http://backend:8000/api/v1/auth/;` | `proxy_pass http://$backend:8000;` |
| `nginx.conf:268` | `proxy_pass http://backend:8000/api/v1/conversations/stream;` | `proxy_pass http://$backend:8000;` |
| `nginx.conf:288` | `proxy_pass http://backend:8000/api/v1/leads/stream;` | `proxy_pass http://$backend:8000;` |
| `nginx.conf:310` | `proxy_pass http://backend:8000/api/;` | `proxy_pass http://$backend:8000;` |

### 2-D. 変換等価性の根拠（recon.md §7 参照）

変数化後の nginx 動作:
- `set $backend backend; proxy_pass http://$backend:8000;` → nginx は変数を含む場合 URI 置換を行わず、`$request_uri` をそのままフォワード
- 全 10 箇所で location prefix == proxy_pass URI suffix が成立しているため、URI 部除去後も転送先パスが等価
- **rewrite 不要・特殊対応不要**（recon.md §1-A 全箇所「変換そのまま可」）

### 2-E. SSE 設定の維持（recon.md §2 参照）

SSE 専用 location 4 箇所（`nginx.conf:108, 128, 268, 288`）の `proxy_buffering off / proxy_cache off / proxy_read_timeout 3600s / proxy_http_version 1.1 / chunked_transfer_encoding on` は**一切変更しない**。proxy_pass 行のみを差し替える。

---

## 3. 外部・過去事例の参照と我々への応用

### OSS nginx + Docker 動的 IP の定石: resolver + 変数化

- nginx は起動時に DNS を解決し以降キャッシュする（NGINX OSS 仕様）
- `resolver 127.0.0.11 valid=5s;` + `set $var hostname; proxy_pass http://$var;` パターンが Docker 環境での標準的解法
- `127.0.0.11` は Docker 埋め込み DNS (Docker Engine 1.10+) で全 bridge ネットワークコンテナに固定提供される
- nginx-plus の `resolve` フラグと同等の効果を OSS で実現する唯一の手段
- 参考: [nginx 公式ドキュメント: proxy_pass + variables](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass)

### 静的 IP 固定が不採用の理由

- Docker IPAM はコンテナ再生成ごとに IP を動的割り当てする設計
- `docker-compose.yml:379-381` で frontnet/backnet とも IPAM 明示設定なし（デフォルト自動割り当て）
- IP 固定は Docker の設計に逆行し、将来的に IP 衝突・管理コスト増加のリスクを持つ

---

## 4. KPI・弊害・計画

### KPI

| 指標 | 目標値 | 計測方法 |
|------|--------|---------|
| backend 再生成後の自動復帰時間 | ≤15 秒 | chaos smoke 計測 |
| 永続 502 発生件数 | 0 件 | chaos smoke 後に 502 継続しないこと |
| ルート等価テスト | 10/10 PASS | 変換前後レスポンス比較スクリプト |

### 弊害と対策

| 弊害 | 発生条件 | 対策 |
|-----|---------|-----|
| `127.0.0.11` が到達不能 | Docker 環境でない場合（本番環境では発生しない） | 本番は Docker Compose 構成のため非該当 |
| TTL 期間中（≤5s）の一時 502 | コンテナ再起動直後 + TTL 未期限切れ + 新旧 IP 変化 | KGI 対象外として明記（本件の許容範囲） |
| `$backend` 変数が空の場合 | set ディレクティブが欠落した場合（設定ミス） | nginx -t で設定検証必須（CI に組み込む） |

### 実装計画（1 PR・1 コミット）

1. `nginx/nginx.conf` 修正（2 server ブロック計 12 行差し替え）
2. `docs/adr/ADR-133-nginx-resolver-proxy-pass-variable.md` 作成
3. `node scripts/generate-adr-index.js` で `docs/adr/README.md` 再生成
4. `docs/handoff/nginx-resolver-adr133/recon.md` + `design.md` を git add
5. PR 作成（develop ← feature/morimoto/nginx-resolver-adr133）

---

## 5. 継続（本番投入後の確認計画）

1. 全 API スモーク 200
2. SSE 疎通確認
3. 画面表示確認（frontend 変数化の回帰チェック）
4. 実地 chaos: backend 手動 `docker compose restart backend` → ≤15 秒で自動復帰確認  
   ※ 実施タイミングは Shingo と調整（低トラフィック帯）

---

## 6. process-artifacts gate チェック

- [x] recon.md: フルパス:行番号引用（`nginx.conf:95` 等、推測なし）
- [x] design.md: recon/ADR 相互参照 + `|基準|検証方法|` テーブル + 外部事例欄 記入済み
- [ ] PR 本文: `### 標準ワークフロー確認` セクション（PR 作成時に記載）
