# ADR-133: nginx resolver + proxy_pass 変数化による IP 固着 502 恒久解

- **ステータス**: Accepted
- **決定者**: Shingo（PO）
- **日付**: 2026-06-11
- **関連 Issue**: #1951（約10時間の永続502障害）
- **References**: ADR-130（案B: CI/CD nginx reload）、`docs/handoff/nginx-resolver-adr133/recon.md`、`docs/handoff/nginx-resolver-adr133/design.md`

---

## コンテキスト

nginx worker は**起動時に一度だけ**プロキシ先ホスト名を DNS 解決し、以後キャッシュし続ける（nginx OSS 仕様）。  
Docker Compose 環境では backend/frontend コンテナの再起動ごとに内部 IP が変化するため、旧 IP を指し続けた nginx が永続 502 を引き起こす。

### ADR-130（案B）との関係

ADR-130 は CI/CD デプロイフロー（`deploy.yml`）に `nginx -s reload` を追加し、**デプロイ経由の再起動**については対処済み。  
しかし以下のケースが未カバーのまま残っており、本 ADR（案A）がそれを解消する:

| ケース | ADR-130 | ADR-133（本件） |
|--------|---------|----------------|
| CI/CD デプロイ | ✓ reload あり | ✓ resolver 自動再解決 |
| 手動 `docker compose restart` | ✗ | ✓ |
| クラッシュ自動再起動（`restart: unless-stopped`） | ✗ | ✓ |
| VPS 再起動 | ✗ | ✓ |

ADR-130 の設計文書に「案Aは別ADRで後日」と明記されており、本 ADR がその正式な受け。

---

## 決定

`nginx/nginx.conf` の 2 つの server ブロック（app.salesanchor.jp / api.salesanchor.jp）に対して:

1. **`resolver 127.0.0.11 valid=5s;`** を各 server ブロック先頭に追加する  
   （`127.0.0.11` は Docker 埋め込み DNS の固定アドレス）

2. **`set $backend backend;`**（および app ブロックに `set $frontend frontend;`）を宣言する

3. backend 向け **9 箇所**・frontend 向け **1 箇所**、合計 **10 箇所**の `proxy_pass` を  
   `http://backend:8000/path` → `http://$backend:8000`（URI 部除去）形式に変換する

### 変換対象一覧

| # | file:line | location | 変換前 proxy_pass | 変換後 |
|---|-----------|---------|-----------------|-------|
| 1 | `nginx.conf:95` | `/api/v1/auth/`（app） | `http://backend:8000/api/v1/auth/` | `http://$backend:8000` |
| 2 | `nginx.conf:108` | `= /api/v1/conversations/stream`（app）[SSE] | `http://backend:8000/api/v1/conversations/stream` | `http://$backend:8000` |
| 3 | `nginx.conf:128` | `= /api/v1/leads/stream`（app）[SSE] | `http://backend:8000/api/v1/leads/stream` | `http://$backend:8000` |
| 4 | `nginx.conf:150` | `/api/`（app） | `http://backend:8000/api/` | `http://$backend:8000` |
| 5 | `nginx.conf:192` | `= /metrics`（app） | `http://backend:8000/metrics` | `http://$backend:8000` |
| 6 | `nginx.conf:201` | `/`（app・frontend） | `http://frontend:8080/` | `http://$frontend:8080` |
| 7 | `nginx.conf:255` | `/api/v1/auth/`（api） | `http://backend:8000/api/v1/auth/` | `http://$backend:8000` |
| 8 | `nginx.conf:268` | `= /api/v1/conversations/stream`（api）[SSE] | `http://backend:8000/api/v1/conversations/stream` | `http://$backend:8000` |
| 9 | `nginx.conf:288` | `= /api/v1/leads/stream`（api）[SSE] | `http://backend:8000/api/v1/leads/stream` | `http://$backend:8000` |
| 10 | `nginx.conf:310` | `/api/`（api） | `http://backend:8000/api/` | `http://$backend:8000` |

### 変換等価性の根拠

nginx は `proxy_pass` に変数を含む場合、location prefix → URI suffix の置換を行わず `$request_uri` をそのまま転送する。全 10 箇所で `location prefix == proxy_pass URI suffix` が成立しているため、URI 部を除去しても転送先パスは等価（recon.md §1-A 参照）。

---

## 対象外

- 外部 IP 直指定の proxy_pass（`49.212.160.98:3000` grafana / `49.212.160.98:3001` status/monitor）: IP は DNS 解決しないため本件の問題を持たない。変更なし。
- `jarvis-claude.uk` / `salesanchor.jp` / `monitor.salesanchor.jp` サーバーブロック: proxy_pass なし or 外部 IP のみ。変更なし。

---

## 検証ゲート（全 PASS がマージ条件）

| 検証 | 内容 | 対応 KGI |
|------|------|---------|
| ルート等価テスト | 全 10 ルートで変換前後のレスポンス比較 | KGI#3 |
| chaos smoke | 本番相当 compose 環境で backend を強制再生成（新 IP 付与）→ reload なしで ≤15 秒以内に 200 自動復帰 | KGI#1, #2 |
| SSE 疎通 | 再起動後に SSE 接続が再確立・ストリーミング再開 | KGI#4 |
| 既存 smoke | 全 PASS | KGI#3 |
| CI | GitHub Actions 全チェック緑 | — |

---

## 外部事例

**OSS nginx + Docker 動的 IP の定石**:  
`resolver 127.0.0.11 valid=5s` + `set $var hostname; proxy_pass http://$var;` は Docker ブリッジネットワーク上での nginx 動的 DNS 解決の業界標準手法。nginx-plus の `resolve` フラグ相当の効果を OSS で実現する唯一の方法として広く採用されている。

**静的 IP 固定が不採用の理由**:  
Docker IPAM はコンテナ再生成ごとに IP を動的割り当てする設計であり、静的 IP 固定は Docker の設計原則に逆行する。IP 衝突・管理コスト増加のリスクがあるため不採用。

---

## 影響

- **nginx 設定**: `nginx/nginx.conf` のみ変更。Docker イメージ・スクリプト・CI/CD 設定には変更なし。
- **ダウンタイム**: nginx 設定変更のみのため、`nginx -s reload`（無停止）で反映可能。本番適用時は `nginx -t` で設定検証後に Shingo の明示 GO を得てから実施する。
- **zero-downtime-deploy 案件**: `docs/handoff/zero-downtime-deploy/` の将来の設計ドキュメントは「nginx.conf 改修は ADR-133 完了済み」を前提として起案すること（recon.md §5 参照）。
