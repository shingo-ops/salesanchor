# SEC-01 入口セキュリティ design

> Issue: #2170  
> Parent: #2166 / PR #2169 / ADR-140 SEC-MASTER  
> Recon: `docs/handoff/security/sec-01-entry/recon.md`  
> 作成日: 2026-06-14  
> 対象: Nginx / TLS / proxy headers / rate limit / monitoring exposure

---

## 0. KGI

外部から到達できる入口を最小化し、IP偽装・過剰公開・TLS/CSP不備による攻撃面を潰す。

---

## 1. recon要約

SEC-01 reconで確認した現在地は以下。

| ID | 状態 | 根拠 | design判断 |
|---|---|---|---|
| R1 | Nginxが外部入口を集約し、80/443のみ公開 | `docker-compose.yml:7-11` | 維持 |
| R2 | backend/frontend/postgres/redisはports公開なし | `docker-compose.yml:63-177`, `docker-compose.yml:31-91` | 維持 |
| R3 | HTTP→HTTPS強制、TLSv1.2/1.3、基本セキュリティヘッダーあり | `nginx/nginx.conf` | 維持。静的LPは別途強化候補 |
| R4 | Nginxは `$proxy_add_x_forwarded_for` をbackendへ渡し、backendはXFF先頭を信用 | `nginx/nginx.conf`, `backend/app/auth/dependencies.py`, middleware各種 | 最優先で修正 |
| R5 | `/grafana/`, `/status/`, `monitor.salesanchor.jp` にNginx側Basic認証/IP制限が見えない | `nginx/nginx.conf` | 保護を追加 |
| R6 | backend rate limit / session guard はRedis不通時fail-open | `backend/app/middleware/rate_limit.py`, `backend/app/middleware/session_guard.py` | 即fail-closeではなく検知強化 |
| R7 | RateLimitMiddlewareが未検証JWT payload emailをuser bucketに使う | `backend/app/middleware/rate_limit.py` | 見直し |

---

## 2. 実装方針

SEC-01実装は4 PRに分ける。

| PR | 内容 | 危険変更 | 理由 |
|---|---|---|---|
| PR-A | proxy header正規化 + backend IP取得helper統一 | Nginx変更あり。PO GO推奨 | 最重要。ログ/RateLimit/SessionGuardの土台。 |
| PR-B | Grafana / Uptime Kuma / status のNginx側保護 | Nginx変更あり。PO GO推奨 | 監視画面の過剰公開防止。 |
| PR-C | Redis fail-open検知強化 | backend変更のみ | 防御停止を検知可能にする。 |
| PR-D | RateLimitMiddlewareの未検証JWT user bucket扱い修正 | backend変更のみ | 偽JWTでbucket分散される余地を減らす。 |

このdesign PR自体はdocsのみ。実装変更はしない。

---

## 3. PR-A: proxy header正規化

### 目的

外部から持ち込まれた `X-Forwarded-For` をbackendが信用しないようにし、IPベースの防御・監査ログ・セッション検知の信頼性を上げる。

### 変更対象候補

- `nginx/nginx.conf`
- `backend/app/auth/dependencies.py`
- `backend/app/middleware/rate_limit.py`
- `backend/app/middleware/session_guard.py`
- `backend/app/middleware/audit.py`
- 必要なら `backend/app/middleware/client_ip.py` または `backend/app/security/client_ip.py` 新設
- backend tests

### 技術How

1. Nginx側で外部入力XFFを引き継がない。

候補:

```nginx
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $remote_addr;
```

または、backendが `X-Real-IP` だけを信頼する方針に寄せる。

2. backend側に共通helperを作る。

例:

```python
def get_trusted_client_ip(request: Request) -> str:
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"
```

3. 以下の重複 `_get_client_ip` / `_get_client_ip_from_request` を共通helperへ置換する。

- `backend/app/auth/dependencies.py`
- `backend/app/middleware/rate_limit.py`
- `backend/app/middleware/session_guard.py`
- `backend/app/middleware/audit.py`

### 受け入れ基準

| ID | 基準 | 検証方法 |
|---|---|---|
| A-G1 | 外部リクエストが `X-Forwarded-For: 1.2.3.4` を送っても、backendのclient_ipがその値にならない | integration test または curl + audit log確認 |
| A-G2 | auth/rate_limit/session_guard/audit が同じIP helperを使う | grep / unit test |
| A-G3 | Nginxの全backend proxy locationで同じheader方針 | `nginx -t` / grep |
| A-G4 | 既存のhealth/API動作が壊れない | backend tests / smoke |

### テスト候補

```bash
python -m pytest backend/tests -q
```

```bash
nginx -t
```

実機/検証環境で:

```bash
curl -H 'X-Forwarded-For: 1.2.3.4' https://api.salesanchor.jp/api/health -i
```

監査ログ確認は値を貼らず、期待IPが偽装値でないことのみ記録する。

### リスク

- 既存監査ログのIP表記が変わる。
- Cloudflare等の上位proxyを将来入れる場合は、信頼proxy chain設計が必要。

### PO確認

- 現在Cloudflare等の上位proxyは使っていない前提でよいか。
- 使っている場合、信頼するproxy CIDRを別設計にする。

---

## 4. PR-B: 監視画面保護

### 目的

Grafana / Uptime Kuma / status 系を、外部から無防備に見えない状態にする。

### 変更対象候補

- `nginx/nginx.conf`
- `docker-compose.yml` は原則触らない
- 必要なら `nginx/htpasswd.d` の運用手順
- docs/operations

### 技術How

#### 案B-1: Basic認証

`/design/` と同じ方式を参考にする。

対象:

- `location /grafana/`
- `location /status/`
- `server_name monitor.salesanchor.jp`

例:

```nginx
auth_basic "SA Monitoring";
auth_basic_user_file /etc/nginx/htpasswd.d/monitoring;
```

#### 案B-2: IP allowlist

固定IP運用が可能なら、`allow <trusted_ip>; deny all;` を使う。

#### 案B-3: VPN/内部化

最も堅いが運用負荷が高い。

### 推奨

初期は **Basic認証 + 将来IP allowlist**。理由:

- 既に `/design/` でBasic認証構造がある。
- 固定IPがない環境でも運用できる。
- 監視画面の認証をGrafana/Uptime Kuma自身にだけ依存しない。

### 受け入れ基準

| ID | 基準 | 検証方法 |
|---|---|---|
| B-G1 | `/grafana/` が認証なしで 401 になる | curl |
| B-G2 | `/status/` が認証なしで 401 になる | curl |
| B-G3 | `monitor.salesanchor.jp` が認証なしで 401 になる | curl |
| B-G4 | 正しいBasic認証では表示できる | curl / ブラウザ |
| B-G5 | htpasswd欠落時にfail-openしない | nginx behavior確認 |

### リスク

- 監視URLを外部サービスが叩いている場合、Basic認証で失敗する可能性。
- Uptime Kuma自身の公開ステータスページを意図している場合、公開範囲の再定義が必要。

### PO確認

- 監視画面はShingo/開発者のみ閲覧でよいか。
- 公開ステータスページとして顧客に見せる予定があるか。
- Basic認証の認証情報はGitHub Secrets経由で注入するか、VPS local管理にするか。

---

## 5. PR-C: Redis fail-open検知強化

### 目的

Redis不通時にRateLimit/SessionGuardがfail-openする状態を、運用上見逃さない。

### 変更対象候補

- `backend/app/middleware/rate_limit.py`
- `backend/app/middleware/session_guard.py`
- `backend/app/metrics.py` または既存metrics定義
- Discord通知系サービスがあれば流用

### 技術How

1. Redis不通/例外時に構造化ログを出す。
2. Prometheus counterを追加する。
   - `security_rate_limit_fail_open_total`
   - `security_session_guard_fail_open_total`
3. 重要度は最初はwarning。即リクエスト拒否にはしない。
4. SEC-08で通知/ダッシュボード化する。

### 受け入れ基準

| ID | 基準 | 検証方法 |
|---|---|---|
| C-G1 | Redis不通時にfail-open counterが増える | unit test / metrics test |
| C-G2 | ログに対象middleware名が出る | pytest caplog |
| C-G3 | 正常時のリクエスト挙動は変えない | backend tests |

### リスク

- Redis障害時にログが大量化する可能性。
- counterだけでは即時通知にならないため、SEC-08で継続設計が必要。

---

## 6. PR-D: 未検証JWT rate bucket見直し

### 目的

署名未検証JWT payloadのemailだけで、認証済みuser bucketに入る挙動をやめる。

### 変更対象候補

- `backend/app/middleware/rate_limit.py`
- tests

### 技術How

現状はAuthorizationヘッダーにBearerがあり、payloadからemailが取れれば `user:<email>` bucketを使う。

修正案:

1. middleware段階では未検証JWTを認証済み扱いにしない。
2. 署名検証前のリクエストはIP bucketに寄せる。
3. どうしてもuser bucketが必要なら、認証Dependency後に別レイヤーで行う。

初期推奨:

- RateLimitMiddlewareでは **常にIP bucket**。
- 認証済みユーザー単位の細かい制限は後続SEC-02/SEC-08で検討。

ただし、正規ユーザーの多い画面でIP単位制限が厳しくなりすぎる可能性があるため、Nginx一般API制限とのバランスを確認する。

### 受け入れ基準

| ID | 基準 | 検証方法 |
|---|---|---|
| D-G1 | 偽JWT emailを変えてもrate bucketを分散できない | unit test |
| D-G2 | Authorizationなしと偽JWTの扱いが同一 | unit test |
| D-G3 | 正規ユーザーの通常操作が429にならない | E2E / smoke |

### リスク

- NAT配下の複数ユーザーが同一IP bucketになり429を受けやすくなる。
- 既存の「認証済み300回/分」緩和が効かなくなる。

### 代替案

- middlewareではIP bucketを使い、認証成功後にRedisへ token hash → user email のverified cacheを作り、次回以降はverified tokenのみuser bucketにする。
- 実装量が増えるため、初期PRでは避ける。

---

## 7. 実装順

推奨順:

1. PR-A proxy header正規化
2. PR-B 監視画面保護
3. PR-C Redis fail-open検知
4. PR-D rate bucket見直し

理由:

- PR-Aが全てのIPベース防御の土台。
- PR-Bは過剰公開面を直接減らす。
- PR-Cは可視化改善で副作用が小さい。
- PR-Dは正規ユーザーの429副作用があり、最後に慎重に実施。

---

## 8. 外部・過去事例の参照と我々への応用

### 事例1: reverse proxy配下のIP信頼境界

一般に、アプリが `X-Forwarded-For` を無条件に信用すると、クライアントがヘッダーを偽装できる。信頼できるreverse proxyで上書きした値、または信頼proxyチェーンだけを読む必要がある。

Sales Anchorへの応用:

- Nginxを信頼境界にする。
- 外部から持ち込まれたXFFは破棄する。
- backendは共通helperでNginxが上書きしたヘッダーのみ参照する。

### 事例2: 監視画面は攻撃者に内部構造を与える

Grafana/Uptime Kuma等は、ログインがあっても、公開範囲・バージョン・稼働状況・内部URLのヒントを与えうる。

Sales Anchorへの応用:

- アプリドメイン配下に出す場合はNginxで追加認証を置く。
- 将来、公開ステータスページが必要なら、管理画面と公開ステータスを分離する。

### 事例3: fail-openは可用性と安全性のトレードオフ

Rate limit/Session guardをRedis依存にすると、Redis障害時に止めるか通すかの選択が必要になる。

Sales Anchorへの応用:

- いきなりfail-closeにせず、まずfail-openの発生を測定・通知する。
- SEC-08で監視とアラートに昇格する。

---

## 9. 検証計画

### docs PR検証

```bash
git diff --name-only origin/develop...HEAD
```

期待:

- docs/handoff/security/sec-01-entry/recon.md
- docs/handoff/security/sec-01-entry/design.md

### PR-A実装時検証

```bash
python -m pytest backend/tests -q
nginx -t
```

追加テスト候補:

- 偽装XFFがclient_ipにならないunit test
- auth/rate_limit/session_guard/auditが共通helperを使うgrep/AST test

### PR-B実装時検証

```bash
curl -i https://app.salesanchor.jp/grafana/
curl -i https://app.salesanchor.jp/status/
curl -i https://monitor.salesanchor.jp/
```

期待:

- 認証なし: 401
- 認証あり: 200またはアプリ側正常応答

### PR-C実装時検証

- Redis接続失敗をmockし、counter/logが出ること。
- 正常時の挙動が変わらないこと。

### PR-D実装時検証

- 偽JWTでemailを変えてもbucket分散できないこと。
- 通常画面操作で429が増えすぎないこと。

---

## 10. PO確認事項

| ID | 確認事項 | 推奨回答 |
|---|---|---|
| Q1 | Cloudflare等の上位proxyを現在使っているか | 使っていない前提ならNginxを唯一の信頼proxyにする |
| Q2 | Grafana/Uptime Kuma/monitorは社内限定でよいか | はい。Basic認証を追加 |
| Q3 | 監視画面の認証情報はどこで管理するか | VPS local htpasswd + GitHub Secrets同期のどちらかを選ぶ |
| Q4 | Redis fail-openを即fail-closeにするか | まずはfail-open維持＋検知強化 |
| Q5 | RateLimitのuser bucketを廃止してIP bucket中心にしてよいか | 影響確認後。初期は慎重にPR-Dで実施 |

---

## 11. Claude Code / Generator への実装ハンドオフ

### 目的

SEC-01入口セキュリティのrecon/designをもとに、まずPR-Aから実装する。

### PR-A実装指示

1. `nginx/nginx.conf` のbackend向けproxy locationで、外部入力XFFを引き継がないようにする。
2. backendに信頼済みclient IP helperを作る。
3. `auth/dependencies.py`, `rate_limit.py`, `session_guard.py`, `audit.py` のIP取得をhelperへ統一する。
4. 偽装XFFがclient_ipにならないテストを追加する。
5. Nginx変更を含むため、PR本文にPO GO欄を作る。
6. `deploy.yml`, `migrations`, 本番`scripts` は触らない。

### 受け入れ基準

- 偽装XFFがrate limit / audit / session guardのclient_ipに使われない。
- 既存API smokeが通る。
- Nginx設定が構文的に正しい。
- 変更ファイルがPR-A範囲に限定されている。

### 注意

GeneratorはHowを再設計しない。このdesignのPR分割・順序に従う。疑義がある場合は実装せず、PO/Plannerに戻す。
