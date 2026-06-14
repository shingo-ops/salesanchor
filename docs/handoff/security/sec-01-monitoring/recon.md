# SEC-01 PR-B 監視画面保護 recon

> Issue: #2173  
> Parent: #2170 / ADR-140 SEC-MASTER  
> 作成日: 2026-06-14  
> 対象: `/grafana/` / `/status/` / `monitor.salesanchor.jp` / `/design/` Basic認証 / `/metrics` IP制限  
> 方針: 実装変更なし。`file:line` 付きで現在地を固定する。

---

## 0. KGI

Grafana / Uptime Kuma / status 系の監視画面を、外部から無防備に見えない状態にする。

---

## 1. 参照ADR / 正本確認

| 対象 | file:line | recon結果 |
|---|---|---|
| 標準ワークフロー | `docs/STANDARD-WORKFLOW.md:20-37` | KGI→recon→設計の順。reconはfile:line引用必須。 |
| 不明点プロトコル | `docs/STANDARD-WORKFLOW.md:41-45` | GitHubから見えない実サーバー設定は「不明」と明示する。 |
| 危険変更 | `docs/STANDARD-WORKFLOW.md:57-68` | `nginx/nginx.conf` は本番入口変更。`deploy.yml`や本番scriptsを触る場合はPO GO必須。 |
| SEC-MASTER | `docs/security/SEC-MASTER.md` | SEC-01の成功条件に監視画面認証/IP制限が含まれる。 |
| SEC-01 recon | `docs/handoff/security/sec-01-entry/recon.md` | `/grafana/`, `/status/`, `monitor.salesanchor.jp` はNginx側追加保護が見えないためPR-B対象。 |
| SEC-01 design | `docs/handoff/security/sec-01-entry/design.md` | PR-BはBasic認証 + 将来IP allowlistを初期推奨。 |

---

## 2. 現在のNginx公開状態

### 2.1 `/grafana/`

| 事実 | file:line | 評価 |
|---|---|---|
| `location /grafana/` が存在する | `nginx/nginx.conf:168-183` | app.salesanchor.jp配下でGrafanaへ到達可能。 |
| proxy先は `http://49.212.160.98:3000/grafana/` | `nginx/nginx.conf:168-169` | 外部向けappドメインから別ホスト/別ポートへproxy。 |
| WebSocket/upgrade headerを渡している | `nginx/nginx.conf:174-176` | Grafana用として妥当。 |
| CSPはGrafana用に `unsafe-eval` / `unsafe-inline` を許容 | `nginx/nginx.conf:177-180` | Grafana要件として理解可能。ただし公開面としては強めの例外。 |
| Nginx側に `auth_basic` / `allow` / `deny` がない | `nginx/nginx.conf:168-183` | 追加保護なし。Grafana自身のログイン設定はGitHubから不明。 |

### 2.2 `/status/`

| 事実 | file:line | 評価 |
|---|---|---|
| `location /status/` が存在する | `nginx/nginx.conf:185-194` | app.salesanchor.jp配下でUptime Kuma系へ到達可能。 |
| proxy先は `http://49.212.160.98:3001/` | `nginx/nginx.conf:185-186` | 外部向けappドメインから監視サービスへproxy。 |
| WebSocket/upgrade headerを渡している | `nginx/nginx.conf:191-193` | Uptime Kuma用として妥当。 |
| Nginx側に `auth_basic` / `allow` / `deny` がない | `nginx/nginx.conf:185-194` | 追加保護なし。Uptime Kuma自身のログイン設定はGitHubから不明。 |

### 2.3 `monitor.salesanchor.jp`

| 事実 | file:line | 評価 |
|---|---|---|
| HTTPはHTTPSへリダイレクト | `nginx/nginx.conf:110-123` | 良い。 |
| HTTPS server blockが存在 | `nginx/nginx.conf:125-155` | monitor専用サブドメインで公開。 |
| proxy先は `http://49.212.160.98:3001/` | `nginx/nginx.conf:143-145` | Uptime Kumaへproxy。 |
| WebSocket/upgrade headerと長時間timeoutあり | `nginx/nginx.conf:150-154` | Uptime Kuma用として妥当。 |
| Nginx側に `auth_basic` / `allow` / `deny` がない | `nginx/nginx.conf:125-155` | 追加保護なし。 |

---

## 3. 既存の保護パターン

### 3.1 `/design/` Basic認証

| 事実 | file:line | 評価 |
|---|---|---|
| `/design` は `/design/` へ301 | `nginx/nginx.conf:201-205` | SPA catch-allへ落ちないようにしている。 |
| `/design/` は `alias /var/www/design-site/` | `nginx/nginx.conf:207-208` | 静的配信。 |
| `auth_basic "SA Design Site"` を使用 | `nginx/nginx.conf:207-211` | 監視画面保護にも流用可能。 |
| htpasswdは `/etc/nginx/htpasswd.d/design-site` | `nginx/nginx.conf:209-210` | composeで `/etc/nginx/htpasswd.d` がro mount済み。 |
| Cache-Control no-store/no-cache | `nginx/nginx.conf:213-216` | 設計サイト向け。監視画面では必須ではないが参考になる。 |

### 3.2 `/metrics` IP制限

| 事実 | file:line | 評価 |
|---|---|---|
| `/metrics` は `allow 49.212.160.98; deny all` | `nginx/nginx.conf:218-220` | IP allowlist実装例。 |
| backend `/metrics` へproxy | `nginx/nginx.conf:221-227` | Prometheus等の内部監視向け。 |

### 3.3 htpasswd volume

| 事実 | file:line | 評価 |
|---|---|---|
| `./nginx/htpasswd.d:/etc/nginx/htpasswd.d:ro` をNginxへmount | `docker-compose.yml:19-20` | 監視用htpasswdを同ディレクトリに追加可能。 |

### 3.4 design-site htpasswd作成処理

| 事実 | file:line | 評価 |
|---|---|---|
| deploy.ymlにdesign-site htpasswd setupがある | `.github/workflows/deploy.yml:94-114` | GitHub SecretsからhtpasswdをVPSへ作る既存パターン。 |
| `DESIGN_SITE_VIEWER_CRED` / `DESIGN_SITE_SMOKE_CRED` を使用 | `.github/workflows/deploy.yml:94-104` | 監視用credentialも同様にSecret化可能。 |
| `openssl passwd -apr1` でhtpasswd生成 | `.github/workflows/deploy.yml:110-112` | apache2-utils不要。流用可能。 |

---

## 4. docker-compose上の関連事実

| 事実 | file:line | 評価 |
|---|---|---|
| Nginxは `80:80` / `443:443` を公開 | `docker-compose.yml:7-11` | 外部入口はNginx。 |
| design-site用htpasswd directoryをro mount | `docker-compose.yml:19-20` | 監視用htpasswdを追加する場合も同mountを利用可能。 |
| Nginxは `no-new-privileges:true` | `docker-compose.yml:38-39` | 良い。 |
| GHA exporterは `expose: 8080` でbacknetのみ | `docker-compose.yml:100-131` | これは外部公開ではない。 |

---

## 5. ADR関連

| ADR | recon結果 |
|---|---|
| ADR-069 Uptime Kuma | monitor.salesanchor.jp / Uptime Kuma有効化の背景ADR。詳細確認が必要。 |
| ADR-070 Grafana | Grafana統合の背景ADR。詳細確認が必要。 |
| ADR-134 design-site | Basic認証 + 静的配信の実装パターンとして参考になる。 |

注: ADR本文の詳細確認はPR-B設計で補完する。現時点ではNginx実装の現物から保護状態を判定した。

---

## 6. GitHubからは不明な点

| 不明点 | 理由 | 次の取得手段 |
|---|---|---|
| Grafana自身のログイン設定 | Grafana設定/DB/envはGitHub上のNginx設定からは見えない | 実機 / Grafana admin設定確認 |
| Uptime Kuma自身のログイン設定 | 同上 | 実機 / Uptime Kuma設定確認 |
| `monitor.salesanchor.jp` を顧客公開ステータスページとして使う意図の有無 | GitHub上のコメントだけでは運用意図が不明 | PO確認 |
| 固定IP allowlistが使えるか | Shingo/開発者の接続元IP運用が不明 | PO確認 |
| 監視用Basic認証credentialの管理場所 | GitHub SecretsかVPS localか未決 | PO確認 |

---

## 7. リスク判定

| ID | 危険度 | 項目 | 根拠 | 対応方針 |
|---|---|---|---|---|
| MON-R1 | Medium-High | GrafanaがNginx側追加認証なしでapp配下に出ている | `nginx/nginx.conf:168-183` | Basic認証を追加。必要に応じてIP allowlist。 |
| MON-R2 | Medium-High | Uptime Kuma/statusがNginx側追加認証なしでapp配下に出ている | `nginx/nginx.conf:185-194` | Basic認証を追加。公開status用途があるなら分離設計。 |
| MON-R3 | Medium-High | monitor.salesanchor.jpがNginx側追加認証なしでUptime Kumaへproxy | `nginx/nginx.conf:125-155` | Basic認証を追加。公開用途があるかPO確認。 |
| MON-R4 | Medium | Grafana用CSPが `unsafe-eval` / `unsafe-inline` を許容 | `nginx/nginx.conf:177-180` | Grafana path限定なので許容。ただし無防備公開は避ける。 |
| MON-R5 | Low-Medium | htpasswd運用を増やすとSecret/運用負荷が増える | deploy.yml既存パターン | 既存design-site方式を流用し、credentialを明示管理。 |

---

## 8. KPI / 受け入れ基準

| KPI | 内容 | 測定方法 |
|---|---|---|
| KPI-B1 | 認証なしで `/grafana/` が 401 または 403 になる | `curl -i https://app.salesanchor.jp/grafana/` |
| KPI-B2 | 認証なしで `/status/` が 401 または 403 になる | `curl -i https://app.salesanchor.jp/status/` |
| KPI-B3 | 認証なしで `monitor.salesanchor.jp` が 401 または 403 になる | `curl -i https://monitor.salesanchor.jp/` |
| KPI-B4 | 正しいBasic認証情報では監視画面へ到達できる | `curl -u "$USER:$PASS" ...` / ブラウザ |
| KPI-B5 | htpasswd欠落時にfail-openしない | stagingまたは一時検証でnginx挙動確認。少なくとも設定上は `auth_basic_user_file` 必須。 |
| KPI-B6 | `/metrics` の既存IP制限を壊さない | `curl` from allowed/disallowed context or config review |
| KPI-B7 | `/design/` の既存Basic認証を壊さない | design-site smoke |

---

## 9. recon結論

監視画面保護の現状は以下。

- `/design/` にはBasic認証があり、流用可能な実装パターンが存在する。
- `/metrics` にはIP allowlistがあり、流用可能な保護パターンが存在する。
- 一方で `/grafana/`, `/status/`, `monitor.salesanchor.jp` にはNginx側のBasic認証/IP制限が見えない。
- Grafana/Uptime Kuma自身のログイン設定はGitHubから不明であり、Nginx側の追加保護を入れる方が堅い。

次のdesignでは、初期実装として **Basic認証を `/grafana/`, `/status/`, `monitor.salesanchor.jp` に追加** する案を第一候補にする。固定IP運用が可能なら、将来IP allowlistを重ねる。
