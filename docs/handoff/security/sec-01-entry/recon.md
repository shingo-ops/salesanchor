# SEC-01 入口セキュリティ recon

> Issue: #2170  
> Parent: #2166 / PR #2169 / ADR-140 SEC-MASTER  
> 作成日: 2026-06-14  
> 対象: Nginx / TLS / proxy headers / rate limit / monitoring exposure  
> 方針: 実装変更なし。`file:line` 付きで現在地を固定する。

---

## 0. KGI

外部から到達できる入口を最小化し、IP偽装・過剰公開・TLS/CSP不備による攻撃面を潰す。

---

## 1. 参照ADR / 正本確認

| 対象 | file:line | recon結果 |
|---|---|---|
| 標準ワークフロー | `docs/STANDARD-WORKFLOW.md:20-37` | KGI→recon→設計の順。reconは実コードへのfile:line引用必須。 |
| 不明点プロトコル | `docs/STANDARD-WORKFLOW.md:41-45` | 推測で埋めず、不明は明示してPO相談。 |
| 危険変更 | `docs/STANDARD-WORKFLOW.md:57-68` | `migrations/`・`deploy.yml`・本番`scripts/`はPO GO対象。SEC-01実装でNginx/deployを触る場合は別PRでGO確認。 |
| SEC-MASTER | `docs/adr/ADR-140-security-hardening-master-plan.md` | SEC-01を最初の実装対象とする。 |
| FEATURE-INDEX | `docs/adr/FEATURE-INDEX.md` | security / hardening / SEC-MASTER は ADR-140 が正準。 |

---

## 2. 構成サマリー

### 2.1 外部公開入口

| 事実 | file:line | 評価 |
|---|---|---|
| `nginx` サービスのみ `80:80` / `443:443` を公開している | `docker-compose.yml:7-11` | 良い。公開入口はNginxに集約されている。 |
| backend は `build: ./backend` で、ports公開はなく、`frontnet` と `backnet` に接続 | `docker-compose.yml:63-142` | 良い。外部からbackendへ直接到達しない前提。 |
| frontend はports公開なし、`frontnet` のみ | `docker-compose.yml:144-177` | 良い。外部公開はNginx経由。 |
| Redis はports公開なし、`backnet` のみ | `docker-compose.yml:31-59` | 良い。ただしパスワード既定値は別リスク。 |
| PostgreSQL はports公開なし、`backnet` のみ | `docker-compose.yml:61-91` | 良い。DBは外部公開されていない。 |

### 2.2 HTTP/HTTPS/TLS

| 事実 | file:line | 評価 |
|---|---|---|
| `app.salesanchor.jp` のHTTPはHTTPSへ301 | `nginx/nginx.conf:55-67` | 良い。HTTP平文利用を防ぐ。 |
| `api.salesanchor.jp` のHTTPはHTTPSへ301 | `nginx/nginx.conf:243-254` | 良い。 |
| `monitor.salesanchor.jp` のHTTPはHTTPSへ301 | `nginx/nginx.conf:110-123` | 良い。 |
| app/API/monitorでTLSv1.2/TLSv1.3を使用 | `nginx/nginx.conf:78-80`, `nginx/nginx.conf:257-261`, `nginx/nginx.conf:134-136` | 良い。古いTLSを避けている。 |
| HSTS が app/API/monitor に設定されている | `nginx/nginx.conf:82-90`, `nginx/nginx.conf:14-20`, `nginx/nginx.conf:138-142` | 良い。 |

### 2.3 セキュリティヘッダー

| 事実 | file:line | 評価 |
|---|---|---|
| `server_tokens off` でNginxバージョン非表示 | `nginx/nginx.conf:3-4` | 良い。攻撃者へのヒントを減らす。 |
| appドメインにCSP / X-Frame-Options / nosniff / Referrer-Policy / Permissions-Policy | `nginx/nginx.conf:82-90` | 良い。ただしCSPは今後フロント実挙動と照合が必要。 |
| APIドメインは `default-src 'none'; frame-ancestors 'none'` | `nginx/nginx.conf:14-20` | 良い。API error pageの防御として適切。 |
| salesanchor.jp静的サイトにもX-Frame-Options等あり | `nginx/nginx.conf:218-223` | 良い。ただしHSTS/CSPはapp/APIより弱い。SEC-01またはLP側で要判断。 |

---

## 3. proxy header / IP取得

### 3.1 Nginxからbackendへのヘッダー

| location | file:line | 事実 |
|---|---|---|
| app `/api/v1/auth/` | `nginx/nginx.conf:98-111` | `X-Real-IP $remote_addr` と `X-Forwarded-For $proxy_add_x_forwarded_for` を渡す。 |
| app `/api/` | `nginx/nginx.conf:153-166` | 同上。 |
| api `/api/v1/auth/` | `nginx/nginx.conf:28-41` | 同上。 |
| api `/api/` | `nginx/nginx.conf:83-96` | 同上。 |

### 3.2 backend側のIP取得

| 対象 | file:line | 事実 |
|---|---|---|
| 認証Dependency | `backend/app/auth/dependencies.py:64-69` | `X-Forwarded-For` があれば先頭要素をクライアントIPとして採用。 |
| RateLimitMiddleware | `backend/app/middleware/rate_limit.py:55-59` | 同じく `X-Forwarded-For` 先頭を採用。 |
| SessionGuardMiddleware | `backend/app/middleware/session_guard.py:60-64` | 同じく `X-Forwarded-For` 先頭を採用。 |
| AuditMiddleware | `backend/app/middleware/audit.py:66-71` | 同じく `X-Forwarded-For` 先頭を採用。 |

### 3.3 判定

**穴あり（High相当候補）**。

Nginxが `$proxy_add_x_forwarded_for` を使っているため、外部リクエストが持ち込んだ `X-Forwarded-For` が残る可能性がある。backend側はその先頭を信用するため、攻撃者が任意IPを先頭に置いた場合、以下へ影響しうる。

- 認証失敗のIPロック / ブルートフォース対策
- RateLimitMiddlewareの未認証IP制限
- SessionGuardMiddlewareのIP変化検知
- AuditMiddlewareの監査ログIP

**SEC-01 designで必ず対策対象にする。**

---

## 4. レート制限

### 4.1 Nginxレート制限

| 対象 | file:line | 事実 |
|---|---|---|
| login zone | `nginx/nginx.conf:6-10` | ログインAPIは `10r/m`。一般APIは `30r/s`。 |
| app auth | `nginx/nginx.conf:98-111` | `/api/v1/auth/` に `limit_req zone=login burst=5 nodelay`。 |
| app api | `nginx/nginx.conf:153-166` | `/api/` に `limit_req zone=api burst=50`。 |
| api auth | `nginx/nginx.conf:28-41` | APIドメイン側もauthにlogin limit。 |
| api api | `nginx/nginx.conf:83-96` | APIドメイン側も一般APIにapi limit。 |

### 4.2 backendレート制限

| 対象 | file:line | 事実 |
|---|---|---|
| Authenticated | `backend/app/middleware/rate_limit.py:26-35` | 認証済みは300回/分、未認証IPは60回/分。 |
| Skip paths | `backend/app/middleware/rate_limit.py:37-39` | `/health`, `/metrics`, `/docs`, `/openapi`, `/static`, `/api/health` は除外。 |
| Redis不通 | `backend/app/middleware/rate_limit.py:62-84` | Redis不通/例外時はfail-openで通過。 |
| JWT email抽出 | `backend/app/middleware/rate_limit.py:41-52` | 署名検証なしでemailを抽出し、認証済み扱いの識別子に使う。 |

### 4.3 判定

- Nginx側にもbackend側にもレート制限がある点は良い。
- ただしbackend側はIP取得が `X-Forwarded-For` 依存のため、3章のproxy header問題に引きずられる。
- Redis不通時 fail-open は可用性優先として理解できるが、攻撃時に防御が弱くなるため、SEC-08監視・SEC-01設計でアラート/補助制限を検討する。
- `RateLimitMiddleware` はJWT署名未検証のpayload emailを識別子に使う。認証本体ではないが、攻撃者が任意emailを入れた偽JWTで識別子を分散できる可能性がある。未検証JWTを「認証済みレート枠」とみなすのは見直し候補。

---

## 5. 監視画面 / 管理画面露出

| 対象 | file:line | 事実 | 評価 |
|---|---|---|---|
| `/grafana/` | `nginx/nginx.conf:168-183` | `http://49.212.160.98:3000/grafana/` へproxy。Nginx側Basic認証/IP制限は見えない。 | 穴あり候補。Grafana自身の認証設定はGitHubから不明。 |
| `/status/` | `nginx/nginx.conf:185-194` | `http://49.212.160.98:3001/` へproxy。Nginx側Basic認証/IP制限は見えない。 | 穴あり候補。 |
| `monitor.salesanchor.jp` | `nginx/nginx.conf:125-155` | Uptime Kumaへproxy。Nginx側Basic認証/IP制限は見えない。 | 穴あり候補。 |
| `/design/` | `nginx/nginx.conf:196-216` | Basic認証付き。htpasswd欠落時はfail-closed想定。 | 良い。監視画面保護の参考実装。 |
| `/metrics` | `nginx/nginx.conf:218-227` | `allow 49.212.160.98; deny all`。 | 良い。IP制限あり。 |

### 判定

**Grafana / Uptime Kuma / status 系は、Nginx設定上は追加認証が見えないため要対策候補。**

ただし、Grafana / Uptime Kuma 自体のログイン設定はGitHubからは不明。SEC-01 designでは以下のどれかを選ぶ必要がある。

1. Nginx Basic認証を追加。
2. 固定IP allowlist を追加。
3. VPN/管理ネットワーク経由のみにする。
4. アプリドメイン配下から外し、内部運用に寄せる。

---

## 6. API専用ドメイン

| 事実 | file:line | 評価 |
|---|---|---|
| `api.salesanchor.jp` は `/api/` 系だけbackendへproxy | `nginx/nginx.conf:28-96` | 良い。 |
| API以外は `return 404` | `nginx/nginx.conf:98-101` | 良い。フロント/管理画面をAPIドメインで出さない。 |

---

## 7. app / frontend 経路

| 事実 | file:line | 評価 |
|---|---|---|
| app `/` は frontend:8080 へproxy | `nginx/nginx.conf:229-235` | 想定通り。 |
| frontend Nginx は `index.html` no-cache、hash assetは1年cache | `frontend/nginx.conf:9-22` | 良い。セキュリティというよりデプロイ整合性。 |
| SPA fallback は全パスを `index.html` へ | `frontend/nginx.conf:24-27` | 想定通り。Nginx app側のAPI prefix分離が前提。 |

---

## 8. container / network hardening

| 事実 | file:line | 評価 |
|---|---|---|
| nginxに `no-new-privileges:true` | `docker-compose.yml:38-40` | 良い。 |
| backendに `no-new-privileges:true` と `/tmp` tmpfs | `docker-compose.yml:136-140` | 良い。 |
| frontendに `no-new-privileges:true` と `/tmp` tmpfs | `docker-compose.yml:172-176` | 良い。 |
| backend Dockerfileは非rootユーザーへ切替 | `backend/Dockerfile:28-39` | 良い。 |
| frontend Dockerfileは非rootユーザーへ切替 | `frontend/Dockerfile:33-45` | 良い。 |

---

## 9. 不明点

| 不明点 | 理由 | 次の取得手段 |
|---|---|---|
| VPS firewall実設定 | GitHub上に実サーバー設定がない | 実機 `ufw status` / cloud firewall確認 |
| SSH hardening実設定 | GitHub上に `/etc/ssh/sshd_config` がない | 実機確認 |
| Grafana自身の認証設定 | Nginx proxy先アプリの設定がGitHubから見えない | 実機 / Grafana env確認 |
| Uptime Kuma自身の認証設定 | 同上 | 実機 / Uptime Kuma設定確認 |
| 実TLS証明書の期限/発行状態 | GitHubから証明書実体は見えない | `certbot certificates` / SSL外部検査 |
| 実 `.env` の `ENVIRONMENT`, `REDIS_PASSWORD`, enforce flags | GitHub Secrets/VPS envは見えない | 実機 `.env` 確認。ただし値は貼らず有無のみ記録 |

---

## 10. 穴・改善候補一覧

| ID | 危険度 | 項目 | 根拠 | 対応方針 |
|---|---|---|---|---|
| SEC01-R1 | High | `X-Forwarded-For` 偽装でIPベース防御/監査が揺らぐ | Nginxが `$proxy_add_x_forwarded_for`、backendが先頭XFF採用 | NginxでXFFを上書き、backendは信頼済みproxyヘッダーだけを見る設計へ |
| SEC01-R2 | Medium-High | Grafana / Uptime Kuma / statusのNginx側保護が見えない | `/grafana/`, `/status/`, `monitor.salesanchor.jp` にauth_basic/allowlistなし | Basic認証/IP制限/VPN化のいずれかをPO確認 |
| SEC01-R3 | Medium | Redis不通時にbackend rate limit / session guardがfail-open | `rate_limit.py`, `session_guard.py` | Redis不通アラートとNginx側補助制限を設計 |
| SEC01-R4 | Medium | 未検証JWT payload emailで認証済みrate bucket扱い | `rate_limit.py:41-52`, `97-103` | 未検証JWTはIP bucket扱い、または検証済みuserのみuser bucketへ |
| SEC01-R5 | Low-Medium | salesanchor.jp静的サイトはapp/APIよりセキュリティヘッダーが弱い | `nginx/nginx.conf:218-223` | Meta申請ページ等への影響を見てCSP/HSTS追加を検討 |

---

## 11. SEC-01 designへの引き継ぎ

### 必須対応候補

1. proxy header 正規化
   - Nginxで外部入力のXFFを信用しない。
   - backend共通IP取得helperを作り、auth/rate_limit/session_guard/auditで統一する。

2. monitoring exposure保護
   - `/grafana/`, `/status/`, `monitor.salesanchor.jp` にBasic認証またはIP制限を追加。
   - `/design/` のBasic認証実装を参考にする。

3. Redis fail-open監視
   - fail-open自体を即fail-closeにはしない。
   - まずはログ/Discord/Grafana等で検知可能にする。

4. rate bucket判定修正
   - JWT未検証payloadだけで「認証済みuser bucket」にしない。

### 危険変更判定

- `nginx/nginx.conf` 変更: 本番入口変更。PO GO推奨。
- backend middleware変更: 実コード変更。通常PRでテスト必須。
- `.github/workflows/deploy.yml` や本番`scripts/` を触る場合: STANDARD-WORKFLOW上の危険変更。PO GO必須。

---

## 12. recon結論

現状の入口セキュリティは、Nginx集約・HTTPS強制・基本セキュリティヘッダー・Dockerネットワーク分離・Nginx/backend二層rate limitがあり、土台は良い。

一方で、SEC-01として最初に直すべき穴は明確。

1. `X-Forwarded-For` 偽装対策。
2. Grafana / Uptime Kuma / status のNginx側保護。
3. Redis fail-open時の検知。
4. 未検証JWT payloadをrate limit user bucketに使う挙動の見直し。

次は `docs/handoff/security/sec-01-entry/design.md` を作成し、上記4点の実装順・受け入れ基準・テストコマンド・PO確認事項を確定する。
