# recon — S5 接続元 IP の偽装対策（client-ip）

**日付**: 2026-10-16　**基準**: origin/main（b4f00fa67 以降）　**仕様書**: [docs/specs/client-ip/README.md](../../specs/client-ip/README.md)
**生出力**: /tmp/CC報告ファイル/s5-ip/（recon-raw.md、prod-uvicorn.txt、recon2/）、/tmp/CC報告ファイル/sec-next/（s5-prod-facts.txt、s5-prod-ports.txt）

## 既存 ADR の検索結果

- `git grep -niE "rate limit|回数制限|client_ip|接続元|X-Real-IP|forwarded" docs/adr` の該当 13 行のうち、接続元 IP に関係するのは ADR-127 のみ（docs/adr/ADR-127-auth-lockout-bystander-fix.md:16,18,41-43。回数制限の本体と nginx 層は変えないと記載）。
- docs/adr/FEATURE-INDEX.md に rate limit・接続元・client_ip・監査ログ・session_guard の行は無い。
- 既に指摘あり: docs/handoff/gas-viewer-fresh-fast/security-recon.md:135、review-fable.md:429-430。

## 1. 接続元 IP を決める関数（5 つ）

【事実】次の 4 つは同じ本文（X-Forwarded-For があれば先頭、無ければ request.client.host、client 無しは "unknown"）:
- backend/app/auth/dependencies.py:70-75 `_get_client_ip`
- backend/app/middleware/rate_limit.py:53-57 `_get_client_ip`
- backend/app/middleware/audit.py:64-69 `_get_client_ip_from_request`
- backend/app/middleware/session_guard.py:58-62 `_get_client_ip`

【事実】5 つ目 backend/app/routers/viewer.py:53-60 `_client_ip` は X-Real-IP → request.client.host → "unknown"（X-Forwarded-For は読まない）。

## 2. 呼び出し元と使い道

【事実】
- backend/app/auth/dependencies.py:152（get_current_user）→ :208 `check_auth_rate_limit`、:216 自社トークン認証、:222 `record_auth_failure`。
- backend/app/routers/auth.py:17 で import。:248 自社ログイン（:249 check→429、:266・:289 record）、:431 パスワード再設定確定（:432 check、:451 record）。
- backend/app/middleware/rate_limit.py:104 未認証要求の 60 回/分の計数キー `ip:{client_ip}`。
- backend/app/middleware/audit.py:151 public.auth_events.client_ip、:194 public.data_access_events.client_ip。
- backend/app/middleware/session_guard.py:161 セッションの /8 プレフィックス変化検知（5 分以内に変われば 401 SESSION_COMPROMISED）。
- 回数制限本体 backend/app/cache.py:288-318（10 回で 900 秒ロック、キーは IP の sha256 先頭 16 文字）。

## 3. 本番の入口（2026-10-16 実測）

【事実】
- DNS は api・app とも 49.212.137.46 直、応答 `server: nginx`（Cloudflare 等の前段なし）。外から 8000 番は届かない。公開は nginx の 80/443 のみ（sec-next/s5-prod-facts.txt、s5-prod-ports.txt）。
- nginx/nginx.conf の backend 向け 12 location すべてに `proxy_set_header X-Real-IP $remote_addr;`（app :96,:112,:132,:152,:171,:246、api :312,:328,:348,:368,:388,:406）。X-Forwarded-For は `$proxy_add_x_forwarded_for`（利用者が送った値の後ろに追記）。`set_real_ip_from` は 0 件。本番 `nginx -T` も同じ。
- 本番 backend（2026-10-16 17:11 JST、prod-uvicorn.txt）: uvicorn 0.34.0、起動コマンド `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1`、環境変数 FORWARDED_ALLOW_IPS は未設定。uvicorn/config.py:205 `proxy_headers: bool = True`、:334 既定の信頼先 `"127.0.0.1"`、:470-471 ProxyHeadersMiddleware。nginx コンテナの IP は 172.20.0.2 で信頼先ではないため、uvicorn は X-Forwarded-For を書き換えず、request.client.host は nginx の IP になる。
- コンテナ内ヘルスチェックは localhost:8000 を直接叩く（docker-compose.yml:152、.github/workflows/deploy.yml:639,:691、scripts/smoke_test_post_deploy.sh:102）。X-Real-IP は付かない → 関数は request.client.host に戻る必要がある。
- backend へ X-Forwarded-For を付ける内部の呼び出しは 0 件（frontend・gas・scripts・workflows・monitoring の git grep）。

## 4. 試験

【事実】
- X-Forwarded-For を送る: backend/tests/test_security_hardening.py:555,:584,:613（session_guard）、backend/tests/test_real_redis_lockout.py:137（当初「手動実行用」と書いたが誤り。CI の pytest-run-internal で実 Redis を使って走る。2026-10-16 CI 失敗で判明し X-Real-IP へ修正）。
- X-Real-IP を送る: backend/tests/test_viewer_api.py:140,:288,:405-409（XFF を無視する試験あり）。
- 関数名に依存する patch: backend/tests/test_event_loop_nonblocking.py:171、backend/tests/test_smoke_auth_least_privilege.py:31（`app.auth.dependencies._get_client_ip`）。
- X-Forwarded-For を毎回変えてログイン失敗を回す試験は無い。

## 5. 監査記録（K3 の測り方）

【事実】public.auth_events（migrations/001_create_auth_events.sql:6-16、client_ip VARCHAR(45)）。記録条件は backend/app/middleware/audit.py:119-130（/api/v1/auth/ 配下、または 401/403）。45 文字を超える偽値は INSERT に失敗し、audit.py:181-182 で握りつぶされる。

## 6. K4 の基準値

【事実】本番 nginx 記録（起動 2026-10-16T04:58:45Z〜08:11Z、3591 行）: 401 が 41、403 が 1、502 が 1、429 が 0（prod-uvicorn.txt）。

## 7. 追加調査（recon2、生出力 /tmp/CC報告ファイル/s5-ip/recon2/）

【事実】
- 名前の参照は §1・§2 の箇所だけ。tests の patch 文字列は "app.auth.dependencies._get_client_ip" の 2 件のみ（backend/tests/test_event_loop_nonblocking.py:171、backend/tests/test_smoke_auth_least_privilege.py:31）。middleware 側の関数名を patch する試験は無い。
- backend/app/auth/__init__.py と backend/app/middleware/__init__.py は空。middleware は app.auth を import せず、app.auth も middleware を import しない。
- backend/app/routers/auth.py のルートはすべて POST（register :43、logout :157、login :238、refresh :319、password-reset/request :381、password-reset/confirm :423）。トークン無しの POST /api/v1/auth/logout は HTTPBearer（backend/app/auth/dependencies.py:35）が依存解決で 401 を返し、本体も record_auth_failure も動かない。AuditMiddleware は auth_failure・401 として auth_events に 1 行書く（backend/app/middleware/audit.py:124-130,153-154）。
- AuditMiddleware を試験する箇所は backend/tests に無い。RateLimitMiddleware・SessionGuardMiddleware は backend/tests/test_security_hardening.py:288・:486 で最小アプリに装着して試験。FakeRedis は backend/tests/test_viewer_api.py:66（get/exists/incr/expire/delete/pipeline）。check_auth_rate_limit は r.get、record_auth_failure は r.incr と r.expire だけを使う（backend/app/cache.py:296-318）。
- backend/tests/test_security_hardening.py は DB 不要（SQLite）。ローカルで 33 passed。CI は .github/workflows/test.yml:207-242 で `pytest -q --tb=short` 全件。
- backend/app で ipaddress を使う箇所は 0 件。

## 8. 本番で偽装を再現（K3 の反映前値）

【事実】2026-10-16 18:24 JST、偽の `X-Forwarded-For: 203.0.113.77` を付けてトークン無し POST /api/v1/auth/logout を 1 回送った（/tmp/CC報告ファイル/s5-ip/k3-before.txt）。応答 401。public.auth_events の client_ip は **203.0.113.77**（偽の値）、同じ要求の nginx 記録の接続元は **49.128.148.145**。＝監査記録の IP は利用者が自由に書き換えられる。
