# stage W recon round 2 raw facts

基準: origin/main

## Q1 git rev-parse origin/main

```
d97928fa7bd91639b3880f882c46babff22ee548
```

## Q2 frontend/src/components/Toggle.tsx 1-80 (cat -n)

```
     1	/**
     2	 * Toggle — 切替スイッチ金型（design.md §AY-3b）
     3	 *
     4	 * ネイティブ checkbox に role="switch" を付けた型。状態は持たない（controlled）。
     5	 * className・style は受けない（見た目はこの部品が決める）。
     6	 * 名前は id＋外側の label、または aria-label／aria-labelledby で与える。
     7	 */
     8	
     9	import { forwardRef } from "react";
    10	import "./Toggle.css";
    11	
    12	export interface ToggleProps {
    13	  checked: boolean;
    14	  onCheckedChange: (next: boolean) => void;
    15	  disabled?: boolean;
    16	  id?: string;
    17	  "aria-label"?: string;
    18	  "aria-labelledby"?: string;
    19	}
    20	
    21	export const Toggle = forwardRef<HTMLInputElement, ToggleProps>(function Toggle(
    22	  { checked, onCheckedChange, disabled, id, ...aria },
    23	  ref,
    24	) {
    25	  return (
    26	    <label className={`comp-toggle${disabled ? " comp-toggle--disabled" : ""}`}>
    27	      <input
    28	        ref={ref}
    29	        id={id}
    30	        type="checkbox"
    31	        role="switch"
    32	        className="comp-toggle__input"
    33	        checked={checked}
    34	        disabled={disabled}
    35	        onChange={(e) => onCheckedChange(e.target.checked)}
    36	        {...aria}
    37	      />
    38	      <span className="comp-toggle__track" aria-hidden="true" />
    39	    </label>
    40	  );
    41	});
```

## Q3 .github/workflows/deploy.yml 270-400 (cat -n)

```
   270	            #     (`META_APP_ID_OLD=...`) を誤って削除しない
   271	            #   - .env 内の他のキー（DB_PASSWORD 等 VPS で手動設定したもの）には触れない
   272	            #   - 冪等: 同じ値で再実行しても最終状態は同じ
   273	            #   - quoted heredoc (`<<'ENV_EOF'`) でシェル変数展開を抑止し、
   274	            #     Secret 値をそのまま literal text として書き込む。
   275	            #     `${{ secrets.X }}` 自体は GitHub Actions が SSH 送信前に展開する。
   276	            #   - 値は単一引用符で囲む（compose も source も文字どおり読む。件1 design）
   277	            #   - Phase 1-D Sprint 1: METADATA_FERNET_KEY 紛失は DB token を永久に
   278	            #     復号不能化するリスクが極めて高い。GitHub Secrets と別の安全な
   279	            #     バックアップの二重保管必須。ローテーション手順は
   280	            #     docs/operations/meta_encryption_key_rotation.md 参照。
   281	            touch .env
   282	            sed -i.bak \
   283	              -e '/^META_VERIFY_TOKEN=/d' \
   284	              -e '/^META_APP_SECRET=/d' \
   285	              -e '/^META_APP_ID=/d' \
   286	              -e '/^META_OAUTH_REDIRECT_URI=/d' \
   287	              -e '/^METADATA_FERNET_KEY=/d' \
   288	              -e '/^GEMINI_API_KEY=/d' \
   289	              -e '/^ADMIN_NOTIFICATION_DISCORD_WEBHOOK=/d' \
   290	              -e '/^ANALYSIS_ERROR_REPORT_DISCORD_WEBHOOK=/d' \
   291	              -e '/^GOOGLE_CALENDAR_CLIENT_ID=/d' \
   292	              -e '/^GOOGLE_CALENDAR_CLIENT_SECRET=/d' \
   293	              -e '/^GOOGLE_CALENDAR_REDIRECT_URI=/d' \
   294	              -e '/^DISCORD_BOT_TOKEN=/d' \
   295	              -e '/^GOOGLE_DRIVE_CLIENT_ID=/d' \
   296	              -e '/^GOOGLE_DRIVE_CLIENT_SECRET=/d' \
   297	              -e '/^GOOGLE_DRIVE_REDIRECT_URI=/d' \
   298	              -e '/^SMOKE_SERVICE_TOKEN=/d' \
   299	              -e '/^SMOKE_SERVICE_EMAIL=/d' \
   300	              -e '/^REVIEW_MAIL_IMAP_HOST=/d' \
   301	              -e '/^REVIEW_MAIL_IMAP_PORT=/d' \
   302	              -e '/^REVIEW_MAIL_IMAP_USER=/d' \
   303	              -e '/^REVIEW_MAIL_IMAP_PASSWORD=/d' \
   304	              -e '/^REVIEW_MAIL_WEBMAIL_URL=/d' \
   305	              -e '/^REVIEW_MAIL_DISCORD_WEBHOOK=/d' \
   306	              -e '/^OPS_MAIL_IMAP_USER=/d' \
   307	              -e '/^OPS_MAIL_IMAP_PASSWORD=/d' \
   308	              -e '/^OPS_MAIL_DISCORD_WEBHOOK=/d' \
   309	              -e '/^VITE_FUNNEL_DASHBOARD=/d' \
   310	              -e '/^SMTP_HOST=/d' \
   311	              -e '/^SMTP_PORT=/d' \
   312	              -e '/^SMTP_USER=/d' \
   313	              -e '/^SMTP_PASSWORD=/d' \
   314	              -e '/^MAIL_FROM=/d' \
   315	              -e '/^CONTACT_NOTIFY_EMAIL=/d' \
   316	              -e '/^AUTH_PASSWORD_RESET_ALLOWLIST=/d' \
   317	              -e '/^AUTH_VIEWER_JWT_SECRET=/d' \
   318	              -e '/^AUTH_PROVIDER=/d' \
   319	              -e '/^AUTH_JWT_SECRET=/d' \
   320	              -e '/^VITE_AUTH_PROVIDER=/d' \
   321	              -e '/^OPS_API_TOKEN=/d' \
   322	              -e '/^OPS_INGEST_TOKEN=/d' \
   323	              -e '/^ERROR_REPORT_AGENT_TOKEN=/d' \
   324	              -e '/^READ_WINDOW_TOKEN=/d' \
   325	              -e '/^CASE_AGENT_TOKEN=/d' \
   326	              -e '/^CASE_ADMIN_TOKEN=/d' \
   327	              -e '/^COMPOSE_FILE=/d' \
   328	              .env
   329	            # YAML `|` ブロックの共通インデント (12 スペース) はパース時に自動除去される。
   330	            # したがって heredoc 本文の各行は実行時に行頭スペースなしで届く。
   331	            # Sprint 4 (F4): GEMINI_API_KEY / ADMIN_NOTIFICATION_DISCORD_WEBHOOK は
   332	            #   ADR-025 trap 回避のため同じ「sed 削除 → append」パターンに合流。
   333	            #   secret 未設定でも空値で append される（後段 LLM サービスは空判定して
   334	            #   parsed_rule_only に graceful degrade、AC4.5）。
   335	            # ADR-1013 便3: メール送信（mail_config.py が読む）と再設定の送信許可。未登録の Secret は空文字＝送らない
   336	            # ADR-1019 段2: 閲覧者のトークンの鍵（viewer_tokens.py が読む）。アプリの鍵 AUTH_JWT_SECRET とは別の値
   337	            cat > .env.secrets.new <<'ENV_EOF'
   338	            META_VERIFY_TOKEN='${{ secrets.META_VERIFY_TOKEN }}'
   339	            META_APP_SECRET='${{ secrets.META_APP_SECRET }}'
   340	            META_APP_ID='${{ secrets.META_APP_ID }}'
   341	            META_OAUTH_REDIRECT_URI='${{ secrets.META_OAUTH_REDIRECT_URI }}'
   342	            METADATA_FERNET_KEY='${{ secrets.METADATA_FERNET_KEY }}'
   343	            GEMINI_API_KEY='${{ secrets.GEMINI_API_KEY }}'
   344	            ADMIN_NOTIFICATION_DISCORD_WEBHOOK='${{ secrets.ADMIN_NOTIFICATION_DISCORD_WEBHOOK }}'
   345	            ANALYSIS_ERROR_REPORT_DISCORD_WEBHOOK='${{ secrets.ANALYSIS_ERROR_REPORT_DISCORD_WEBHOOK }}'
   346	            GOOGLE_CALENDAR_CLIENT_ID='${{ secrets.GOOGLE_CALENDAR_CLIENT_ID }}'
   347	            GOOGLE_CALENDAR_CLIENT_SECRET='${{ secrets.GOOGLE_CALENDAR_CLIENT_SECRET }}'
   348	            GOOGLE_CALENDAR_REDIRECT_URI='${{ secrets.GOOGLE_CALENDAR_REDIRECT_URI }}'
   349	            DISCORD_BOT_TOKEN='${{ secrets.DISCORD_BOT_TOKEN }}'
   350	            GOOGLE_DRIVE_CLIENT_ID='${{ secrets.GOOGLE_DRIVE_CLIENT_ID }}'
   351	            GOOGLE_DRIVE_CLIENT_SECRET='${{ secrets.GOOGLE_DRIVE_CLIENT_SECRET }}'
   352	            GOOGLE_DRIVE_REDIRECT_URI='${{ secrets.GOOGLE_DRIVE_REDIRECT_URI }}'
   353	            SMOKE_SERVICE_TOKEN='${{ secrets.FEDEX_SMOKE_API_TOKEN }}'
   354	            SMOKE_SERVICE_EMAIL='${{ secrets.FEDEX_SMOKE_USER_EMAIL }}'
   355	            REVIEW_MAIL_IMAP_HOST='${{ secrets.REVIEW_MAIL_IMAP_HOST }}'
   356	            REVIEW_MAIL_IMAP_PORT='${{ secrets.REVIEW_MAIL_IMAP_PORT }}'
   357	            REVIEW_MAIL_IMAP_USER='${{ secrets.REVIEW_MAIL_IMAP_USER }}'
   358	            REVIEW_MAIL_IMAP_PASSWORD='${{ secrets.REVIEW_MAIL_IMAP_PASSWORD }}'
   359	            REVIEW_MAIL_WEBMAIL_URL='${{ secrets.REVIEW_MAIL_WEBMAIL_URL }}'
   360	            REVIEW_MAIL_DISCORD_WEBHOOK='${{ secrets.REVIEW_MAIL_DISCORD_WEBHOOK }}'
   361	            OPS_MAIL_IMAP_USER='${{ secrets.OPS_MAIL_IMAP_USER }}'
   362	            OPS_MAIL_IMAP_PASSWORD='${{ secrets.OPS_MAIL_IMAP_PASSWORD }}'
   363	            OPS_MAIL_DISCORD_WEBHOOK='${{ secrets.OPS_MAIL_DISCORD_WEBHOOK }}'
   364	            VITE_FUNNEL_DASHBOARD='${{ secrets.VITE_FUNNEL_DASHBOARD }}'
   365	            SMTP_HOST='${{ secrets.SMTP_HOST }}'
   366	            SMTP_PORT='${{ secrets.SMTP_PORT }}'
   367	            SMTP_USER='${{ secrets.SMTP_USER }}'
   368	            SMTP_PASSWORD='${{ secrets.SMTP_PASSWORD }}'
   369	            MAIL_FROM='${{ secrets.MAIL_FROM }}'
   370	            CONTACT_NOTIFY_EMAIL='${{ secrets.CONTACT_NOTIFY_EMAIL }}'
   371	            AUTH_VIEWER_JWT_SECRET='${{ secrets.AUTH_VIEWER_JWT_SECRET }}'
   372	            AUTH_PROVIDER='self'
   373	            AUTH_JWT_SECRET='${{ secrets.AUTH_JWT_SECRET }}'
   374	            VITE_AUTH_PROVIDER='self'
   375	            OPS_API_TOKEN='${{ secrets.OPS_API_TOKEN }}'
   376	            OPS_INGEST_TOKEN='${{ secrets.OPS_INGEST_TOKEN }}'
   377	            ERROR_REPORT_AGENT_TOKEN='${{ secrets.ERROR_REPORT_AGENT_TOKEN }}'
   378	            READ_WINDOW_TOKEN='${{ secrets.READ_WINDOW_TOKEN }}'
   379	            CASE_AGENT_TOKEN='${{ secrets.CASE_AGENT_TOKEN }}'
   380	            CASE_ADMIN_TOKEN='${{ secrets.CASE_ADMIN_TOKEN }}'
   381	            COMPOSE_FILE=docker-compose.yml:docker-compose.exporters.yml
   382	            ENV_EOF
   383	            # 件1（docs/handoff/deploy-secrets-dollar-quote/design.md）: 値に ' か改行があると単一引用符が壊れる。
   384	            # 壊れた行があれば .env を書き換える前の状態に戻して止める。出すのは heredoc 内の行番号だけ（値は出さない）。
   385	            _bad_lines=$(grep -nvE "^[A-Z0-9_]+='[^']*'$|^COMPOSE_FILE=" .env.secrets.new | cut -d: -f1 | tr '\n' ' ')
   386	            if [ -n "${_bad_lines}" ]; then
   387	              echo "❌ secrets の値に単一引用符か改行がある（heredoc の行: ${_bad_lines}）。.env は変更前に戻した"
   388	              mv .env.bak .env
   389	              rm -f .env.secrets.new
   390	              exit 1
   391	            fi
   392	            cat .env.secrets.new >> .env
   393	            rm -f .env.secrets.new .env.bak
   394	
   395	            echo "Step 2b: DATABASE_URL ホスト修正 + Phase2 フラグ確認..."
   396	            # SA-18: localhost:5432 は必ずコンテナ内到達可能な postgres:5432 に修正する。
   397	            # Phase2 フラグ（SA18_PHASE2_ENABLED=1）が .env に立っている場合は
   398	            # salesanchor_app URL を保持する（ユーザー意図を尊重）。
   399	            # フラグがない場合は jarvis@postgres:5432 に戻す（従来動作・冪等）。
   400	
```

## Q4 grep -n -E 'server_name|Content-Security-Policy|location|listen' nginx/nginx.conf

```
15:map $ssl_server_name $is_case_api_sni {
22:    listen 80;
23:    server_name jarvis-claude.uk;
26:    location /.well-known/acme-challenge/ {
31:    location / {
40:    listen 443 ssl;
41:    server_name jarvis-claude.uk;
56:    location / {
66:    listen 80;
67:    listen [::]:80;
68:    server_name app.salesanchor.jp;
70:    location /.well-known/acme-challenge/ {
74:    location / {
80:    listen 443 ssl;
81:    listen [::]:443 ssl;
83:    server_name app.salesanchor.jp;
96:    add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://www.gstatic.com; connect-src 'self' https://*.googleapis.com https://*.firebaseio.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:" always;
100:    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
111:    location = /api/v1/viewer/login {
126:    location = /api/v1/viewer/password-reset/request {
141:    location = /api/v1/viewer/password-reset/confirm {
156:    location /api/v1/auth/ {
172:    location = /api/v1/conversations/stream {
192:    location = /api/v1/leads/stream {
212:    location = /api/v1/events/stream {
231:    location /api/ {
246:    location /grafana/ {
257:        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; connect-src 'self' ws: wss:; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:;" always;
260:        add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
263:    location /status/ {
275:    location /pushgateway/metrics/job/sop-health-reporter/ {
290:    # location /（SPA catch-all）に落ちてアプリ画面を返す挙動を防止する
291:    location = /design {
295:    location /design/ {
306:    location = /metrics {
317:    location / {
332:    listen 80;
333:    listen [::]:80;
334:    server_name api.salesanchor.jp;
336:    location /.well-known/acme-challenge/ {
340:    location / {
346:    listen 443 ssl;
347:    listen [::]:443 ssl;
349:    server_name api.salesanchor.jp;
363:    add_header Content-Security-Policy "default-src 'none'; frame-ancestors 'none'" always;
375:    location = /api/v1/viewer/login {
390:    location = /api/v1/viewer/password-reset/request {
405:    location = /api/v1/viewer/password-reset/confirm {
420:    location /api/v1/auth/ {
436:    location = /api/v1/conversations/stream {
456:    location = /api/v1/leads/stream {
476:    location = /api/v1/events/stream {
496:    location = /api/v1/ops/alertmanager {
516:    location = /api/v1/ops/read-window/query {
535:    location = /__rw_unavailable {
541:    location /api/ {
557:    location / {
569:    listen 443 ssl;
570:    listen [::]:443 ssl;
572:    server_name case-api.salesanchor.jp;
582:    add_header Content-Security-Policy "default-src 'none'; frame-ancestors 'none'" always;
599:    location = /api/v1/ops/read-window/query {
619:    location ~ "^/api/v1/ops/case/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/(report|unmask-requests)$" {
639:    location ~ "^/api/v1/ops/case/unmask-requests/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$" {
659:    location = /ops/unmask/read {
678:    location = /__case_unavailable {
685:    location / {
697:    listen 80;
698:    listen [::]:80;
699:    server_name monitor.salesanchor.jp;
702:    location /.well-known/acme-challenge/ {
706:    location / {
712:    listen 443 ssl;
713:    listen [::]:443 ssl;
715:    server_name monitor.salesanchor.jp;
732:    location / {
752:    listen 80;
753:    listen [::]:80;
754:    server_name salesanchor.jp www.salesanchor.jp;
757:    location /.well-known/acme-challenge/ {
762:    location / {
768:    listen 443 ssl;
769:    listen [::]:443 ssl;
771:    server_name salesanchor.jp www.salesanchor.jp;
787:    location /privacy {
791:    location /terms {
795:    location /data-deletion {
799:    location / {
```

## Q5 nginx/nginx.conf 80-120 (cat -n)

```
    80	    listen 443 ssl;
    81	    listen [::]:443 ssl;
    82	    http2 on;
    83	    server_name app.salesanchor.jp;
    84	    # ADR-1052: TLS の名前が case-api なら 421
    85	    if ($is_case_api_sni) { return 421; }
    86	
    87	    ssl_certificate     /etc/letsencrypt/live/app.salesanchor.jp/fullchain.pem;
    88	    ssl_certificate_key /etc/letsencrypt/live/app.salesanchor.jp/privkey.pem;
    89	
    90	    ssl_protocols TLSv1.2 TLSv1.3;
    91	    ssl_ciphers HIGH:!aNULL:!MD5;
    92	    ssl_prefer_server_ciphers on;
    93	
    94	    # セキュリティヘッダー（jarvis-claude.uk と同一）
    95	    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    96	    add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://www.gstatic.com; connect-src 'self' https://*.googleapis.com https://*.firebaseio.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:" always;
    97	    add_header X-Frame-Options "DENY" always;
    98	    add_header X-Content-Type-Options "nosniff" always;
    99	    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
   100	    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
   101	    add_header X-XSS-Protection "1; mode=block" always;
   102	
   103	    client_max_body_size 10m;
   104	    # ADR-133: Docker 内部 DNS（127.0.0.11）を valid=5s で動的再解決
   105	    # → backend/frontend 再起動後に nginx 操作なしで自動復帰する恒久解
   106	    resolver 127.0.0.11 valid=5s;
   107	    set $backend backend;
   108	    set $frontend frontend;
   109	
   110	    # ADR-1019 段4a-1: 閲覧ページの login・パスワード再発行は auth と同じ厳しい回数制限（完全一致）
   111	    location = /api/v1/viewer/login {
   112	        limit_req zone=login burst=5 nodelay;
   113	        limit_req_status 429;
   114	
   115	        proxy_pass http://$backend:8000;
   116	        proxy_set_header Host $host;
   117	        proxy_set_header X-Real-IP $remote_addr;
   118	        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   119	        proxy_set_header X-Forwarded-Proto $scheme;
   120	        proxy_set_header X-Request-ID $request_id;
```

## Q5 nginx/nginx.conf 240-320 (cat -n)

```
   240	        proxy_set_header X-Request-ID $request_id;
   241	        proxy_connect_timeout 10s;
   242	        proxy_send_timeout    60s;
   243	        proxy_read_timeout    120s;
   244	    }
   245	
   246	    location /grafana/ {
   247	        proxy_pass http://49.212.160.98:3000/grafana/;
   248	        proxy_set_header Host $host;
   249	        proxy_set_header X-Real-IP $remote_addr;
   250	        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   251	        proxy_set_header X-Forwarded-Proto $scheme;
   252	        proxy_http_version 1.1;
   253	        proxy_set_header Upgrade $http_upgrade;
   254	        proxy_set_header Connection "upgrade";
   255	        # GrafanaはReact/Angularバンドルに'unsafe-eval'が必要（グローバルCSPを上書き）
   256	        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
   257	        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; connect-src 'self' ws: wss:; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:;" always;
   258	        add_header X-Content-Type-Options "nosniff" always;
   259	        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
   260	        add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
   261	    }
   262	
   263	    location /status/ {
   264	        proxy_pass http://49.212.160.98:3001/;
   265	        proxy_set_header Host $host;
   266	        proxy_set_header X-Real-IP $remote_addr;
   267	        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   268	        proxy_set_header X-Forwarded-Proto $scheme;
   269	        proxy_http_version 1.1;
   270	        proxy_set_header Upgrade $http_upgrade;
   271	        proxy_set_header Connection "upgrade";
   272	    }
   273	
   274	    # ADR-124: sop-health-reporter（GitHub Actions）→ prod2 Pushgateway。記録係の送信1経路だけ通す（読み取り・削除・他 job は通さない）
   275	    location /pushgateway/metrics/job/sop-health-reporter/ {
   276	        limit_except POST PUT { deny all; }
   277	        proxy_pass http://49.212.160.98:9091/metrics/job/sop-health-reporter/;
   278	        proxy_set_header Host $host;
   279	        proxy_set_header X-Real-IP $remote_addr;
   280	        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   281	        proxy_set_header X-Forwarded-Proto $scheme;
   282	    }
   283	
   284	    # ================================================================
   285	    # SA設計図書サイト（ADR-134）— Basic認証付き静的配信
   286	    # デフォルトdeny: htpasswdファイルが読めない/消えた場合nginxは500を返す
   287	    # （htpasswdが消えた場合に401ではなく500になる = fail-closed 構造）
   288	    # ================================================================
   289	    # /design（末尾スラッシュなし）→ /design/ へ 301 リダイレクト（ADR-134）
   290	    # location /（SPA catch-all）に落ちてアプリ画面を返す挙動を防止する
   291	    location = /design {
   292	        return 301 /design/;
   293	    }
   294	
   295	    location /design/ {
   296	        alias /var/www/design-site/;
   297	        auth_basic "SA Design Site";
   298	        auth_basic_user_file /etc/nginx/htpasswd.d/design-site;
   299	        try_files $uri $uri/ =404;
   300	
   301	        add_header X-Frame-Options "DENY" always;
   302	        add_header X-Content-Type-Options "nosniff" always;
   303	        add_header Cache-Control "no-store, no-cache" always;
   304	    }
   305	
   306	    location = /metrics {
   307	        allow 49.212.160.98;
   308	        deny all;
   309	        proxy_pass http://$backend:8000;
   310	        proxy_set_header Host $host;
   311	        proxy_set_header X-Real-IP $remote_addr;
   312	        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   313	        proxy_set_header X-Forwarded-Proto $scheme;
   314	        proxy_read_timeout 30s;
   315	    }
   316	
   317	    location / {
   318	        proxy_pass http://$frontend:8080;
   319	        proxy_set_header Host $host;
   320	        proxy_set_header X-Real-IP $remote_addr;
```

## Q6 frontend/nginx.conf (cat -n)

```
     1	server {
     2	    listen 8080;
     3	    server_name localhost;
     4	    root /usr/share/nginx/html;
     5	    index index.html;
     6	
     7	    # 画面ファイルを圧縮して返す（在庫表の高速化 便1・docs/handoff/frontend-gzip/design.md）
     8	    gzip on;
     9	    gzip_vary on;
    10	    gzip_proxied any;
    11	    gzip_comp_level 5;
    12	    gzip_min_length 1024;
    13	    gzip_types text/css application/javascript text/javascript application/json image/svg+xml text/plain application/manifest+json;
    14	
    15	    # index.html: 毎回サーバーに確認させる（キャッシュ無効）
    16	    # → デプロイ後にブラウザが必ず新しいアセットURLを参照できる
    17	    location = /index.html {
    18	        add_header Cache-Control "no-cache, must-revalidate";
    19	        try_files $uri =404;
    20	    }
    21	
    22	    # 閲覧ページ(/viewer/): 本体と同じ理由で index を毎回確認させる。
    23	    # /viewer の転送は、この location の中だけでポート(8080)を混ぜない（server 全体には置かない）。
    24	    location = /viewer {
    25	        absolute_redirect off;
    26	        return 301 /viewer/;
    27	    }
    28	    location = /viewer/index.html {
    29	        add_header Cache-Control "no-cache, must-revalidate";
    30	        try_files $uri =404;
    31	    }
    32	    location = /viewer/ {
    33	        add_header Cache-Control "no-cache, must-revalidate";
    34	        try_files /viewer/index.html =404;
    35	    }
    36	
    37	    # JS/CSS/画像 等のハッシュ付きアセット: 1年間キャッシュ
    38	    # → Vite がビルドごとにファイル名を変えるため、古いファイルが返ることはない
    39	    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    40	        expires 1y;
    41	        add_header Cache-Control "public, max-age=31536000, immutable";
    42	        try_files $uri =404;
    43	    }
    44	
    45	    # SPA ルーティング（全パスを index.html にフォールバック）
    46	    location / {
    47	        try_files $uri $uri/ /index.html;
    48	    }
    49	}
```

## Q7 frontend/Dockerfile (cat -n)

```
     1	# Stage 1: Build
     2	FROM node:20-slim AS builder
     3	
     4	WORKDIR /app
     5	
     6	# Vite がビルド時に埋め込む VITE_ 環境変数を受け取る
     7	ARG VITE_FIREBASE_API_KEY
     8	ARG VITE_FIREBASE_AUTH_DOMAIN
     9	ARG VITE_GCP_PROJECT_ID
    10	ARG VITE_FUNNEL_DASHBOARD
    11	ARG VITE_AUTH_PROVIDER
    12	ENV VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY
    13	ENV VITE_FIREBASE_AUTH_DOMAIN=$VITE_FIREBASE_AUTH_DOMAIN
    14	ENV VITE_GCP_PROJECT_ID=$VITE_GCP_PROJECT_ID
    15	ENV VITE_FUNNEL_DASHBOARD=$VITE_FUNNEL_DASHBOARD
    16	ENV VITE_AUTH_PROVIDER=$VITE_AUTH_PROVIDER
    17	
    18	# 依存関係をコピーしてインストール
    19	COPY package*.json ./
    20	RUN npm install
    21	
    22	# ソースコードをコピーしてビルド
    23	COPY . .
    24	RUN npm run build
    25	
    26	# Stage 2: Production
    27	FROM nginx:alpine
    28	
    29	# ビルド成果物をNginxの公開ディレクトリにコピー
    30	COPY --from=builder /app/dist /usr/share/nginx/html
    31	
    32	# カスタムNginx設定（キャッシュヘッダー付き・非rootユーザー用ポート8080）
    33	COPY nginx.conf /etc/nginx/conf.d/default.conf
    34	
    35	# 非rootユーザーの作成とファイル権限設定
    36	RUN addgroup -S appgroup && adduser -S appuser -G appgroup \
    37	    && chown -R appuser:appgroup /usr/share/nginx/html \
    38	    && chown -R appuser:appgroup /var/cache/nginx \
    39	    && chown -R appuser:appgroup /var/log/nginx \
    40	    && touch /var/run/nginx.pid \
    41	    && chown appuser:appgroup /var/run/nginx.pid
    42	
    43	USER appuser
    44	
    45	EXPOSE 8080
    46	
    47	CMD ["nginx", "-g", "daemon off;"]
```

## Q8 grep -n devices frontend/src/locales/en.json, then 40 lines from the first hit

```
3326:    "devices": {
--- 40 lines from line 3326 (cat -n) ---
  3326	    "devices": {
  3327	      "title": "Signed-in devices",
  3328	      "description": "Devices signed in to your account. Sign out any device you do not recognize.",
  3329	      "colLabel": "Device",
  3330	      "colLocation": "Approximate location",
  3331	      "colLastUsed": "Last used",
  3332	      "current": "This device",
  3333	      "unknown": "Unknown",
  3334	      "remove": "Sign out",
  3335	      "removeTitle": "Sign out this device?",
  3336	      "removeMessage": "This device will need approval again the next time it is used.",
  3337	      "empty": "No devices.",
  3338	      "geoipCredit": "Locations are estimated by IP Geolocation by DB-IP."
  3339	    },
  3340	    "recoveryCodes": {
  3341	      "title": "Recovery codes",
  3342	      "description": "Codes for signing in on a new device when your usual device is not at hand.",
  3343	      "remaining": "{{count}} left",
  3344	      "regenerate": "Create new codes",
  3345	      "regenerateTitle": "Create new recovery codes?",
  3346	      "regenerateMessage": "Your unused codes will stop working. The new 10 codes are shown only once, when created.",
  3347	      "shownTitle": "Recovery codes",
  3348	      "shownBody": "These 10 codes are shown only now. Keep them somewhere safe.",
  3349	      "copy": "Copy",
  3350	      "copied": "Copied",
  3351	      "promptTitle": "Create recovery codes?",
  3352	      "promptBody": "We recommend creating recovery codes in case your usual device becomes unavailable.",
  3353	      "promptCreate": "Create",
  3354	      "promptLater": "Later"
  3355	    }
  3356	  },
  3357	  "badges": {
  3358	    "userFallback": "User #{{id}}",
  3359	    "subtitle": "Manage badges and achievement conditions.",
  3360	    "badgeCount": "Badges",
  3361	    "badgeList": "Badge list",
  3362	    "badgeName": "Badge name",
  3363	    "criteria": "Criteria",
  3364	    "icon": "Icon",
  3365	    "leaderboard": "Leaderboard",
```

## Q9 git grep -n -E '_notify_new_request|send_new_device_mail' origin/main -- backend/app

```
origin/main:backend/app/routers/auth.py:52:from app.services.auth_mail import send_invite_email, send_new_device_mail, send_password_reset_email
origin/main:backend/app/routers/auth.py:336:async def _notify_new_request(
origin/main:backend/app/routers/auth.py:342:        send_new_device_mail,
origin/main:backend/app/routers/auth.py:419:                send_new_device_mail,
origin/main:backend/app/routers/auth.py:432:            await _notify_new_request(background_tasks, user_row.email, new, user_row.id)
origin/main:backend/app/routers/auth.py:1181:                send_new_device_mail,
origin/main:backend/app/services/auth_mail.py:164:def send_new_device_mail(
```

## Q10 backend/app/routers/auth.py +-15 lines around each Q9 hit (cat -n)

```
--- around line 52 (37-67) ---
    37	from app.auth.schemas import UserRegister, UserResponse
    38	from app.cache import (
    39	    PASSWORD_RESET_REQUEST_MAX,
    40	    blacklist_token,
    41	    check_auth_rate_limit,
    42	    count_password_reset_request,
    43	    invalidate_user_permissions,
    44	    record_auth_failure,
    45	)
    46	from app.database import get_db
    47	from app.models import Tenant, User
    48	from app.realtime.publisher import publish_user_change
    49	from app.realtime.topics import TOPIC_AUTH_LOGIN_REQUEST
    50	from app.schemas.auth import PasswordChange
    51	from app.services.audit import record_audit_log
    52	from app.services.auth_mail import send_invite_email, send_new_device_mail, send_password_reset_email
    53	from app.services.invite import create_invite_token, invite_enabled, invite_url
    54	
    55	router = APIRouter()
    56	security = HTTPBearer()
    57	
    58	
    59	@router.post("/register", response_model=UserResponse, status_code=201)
    60	async def register_user(
    61	    data: UserRegister,
    62	    request: Request,
    63	    background_tasks: BackgroundTasks,
    64	    db: AsyncSession = Depends(get_db),
    65	    current_user: User = Depends(require_super_admin),
    66	):
    67	    """
--- around line 336 (321-351) ---
   321	    await clear_tenant_context(db)
   322	    await db.commit()
   323	    await record_auth_failure(ip)
   324	
   325	
   326	class LoginApprovalRequired(BaseModel):
   327	    """知らない機械からのログイン（202）。トークンは出さない。いつもの機械で許可するまで待つ（ADR-1055）。"""
   328	
   329	    status: str = Field(default="device_approval_required", description="許可待ち")
   330	    match_number: str = Field(description="待つ機械に出す2けたの番号")
   331	    expires_in: int = Field(description="依頼の有効秒数")
   332	    has_trusted_device: bool = Field(description="いつもの機械があるか")
   333	    has_recovery_codes: bool = Field(description="予備の合言葉が残っているか")
   334	
   335	
   336	async def _notify_new_request(
   337	    background_tasks: BackgroundTasks, email: str, new: devices.NewRequest, user_id: int
   338	) -> None:
   339	    """許可依頼を、いつもの機械の画面（SSE）とメールで知らせる。失敗しても依頼は作ってある。"""
   340	    await publish_user_change(user_id, TOPIC_AUTH_LOGIN_REQUEST)
   341	    background_tasks.add_task(
   342	        send_new_device_mail,
   343	        email,
   344	        when=devices.jst_text(),
   345	        device=new.label,
   346	        location=new.location,
   347	    )
   348	
   349	
   350	@router.post(
   351	    "/login",
--- around line 342 (327-357) ---
   327	    """知らない機械からのログイン（202）。トークンは出さない。いつもの機械で許可するまで待つ（ADR-1055）。"""
   328	
   329	    status: str = Field(default="device_approval_required", description="許可待ち")
   330	    match_number: str = Field(description="待つ機械に出す2けたの番号")
   331	    expires_in: int = Field(description="依頼の有効秒数")
   332	    has_trusted_device: bool = Field(description="いつもの機械があるか")
   333	    has_recovery_codes: bool = Field(description="予備の合言葉が残っているか")
   334	
   335	
   336	async def _notify_new_request(
   337	    background_tasks: BackgroundTasks, email: str, new: devices.NewRequest, user_id: int
   338	) -> None:
   339	    """許可依頼を、いつもの機械の画面（SSE）とメールで知らせる。失敗しても依頼は作ってある。"""
   340	    await publish_user_change(user_id, TOPIC_AUTH_LOGIN_REQUEST)
   341	    background_tasks.add_task(
   342	        send_new_device_mail,
   343	        email,
   344	        when=devices.jst_text(),
   345	        device=new.label,
   346	        location=new.location,
   347	    )
   348	
   349	
   350	@router.post(
   351	    "/login",
   352	    response_model=SelfTokenResponse,
   353	    responses={202: {"model": LoginApprovalRequired, "description": "知らない機械。いつもの機械で許可するまで待つ"}},
   354	)
   355	async def self_login(
   356	    data: SelfLoginRequest,
   357	    request: Request,
--- around line 419 (404-434) ---
   404	        cookie_raw = request.cookies.get(devices.DEVICE_COOKIE_NAME)
   405	        found = await devices.find_trusted_device(db, user_row.id, cookie_raw)
   406	        if found is not None:
   407	            # いつもの機械: 使った時刻を更新し、印の期限を延ばす
   408	            await devices.touch_device(db, found.id, request)
   409	            trusted_device_id = found.id
   410	            device_cookie_raw = devices.clean_cookie_value(cookie_raw)
   411	            audit_new_device = False
   412	        elif user_row.last_login is None and await devices.count_all_devices(db, user_row.id) == 0:
   413	            # D5: 一度もログインしていない人の最初のログイン。この機械を最初のいつもの機械にする
   414	            trusted_device_id, device_cookie_raw = await devices.register_device(
   415	                db, user_row.id, cookie_raw, "first_login", request
   416	            )
   417	            audit_reason, audit_new_device = "first_login", True
   418	            background_tasks.add_task(
   419	                send_new_device_mail,
   420	                user_row.email,
   421	                when=devices.jst_text(),
   422	                device=devices.describe_user_agent(request.headers.get("user-agent")),
   423	                location=geo.lookup(ip),
   424	                note="この機械を最初のいつもの機械として登録しました。 / This device was registered as your first trusted device.",
   425	            )
   426	        else:
   427	            # 知らない機械: 許可依頼を作って 202（トークンは出さない）
   428	            new = await devices.create_login_request(db, user_row.id, request, cookie_raw)
   429	            has_trusted = await devices.has_any_trusted_device(db, user_row.id)
   430	            has_codes = (await recovery_codes.remaining(db, user_row.id)) > 0
   431	            await db.commit()
   432	            await _notify_new_request(background_tasks, user_row.email, new, user_row.id)
   433	            pending = JSONResponse(
   434	                status_code=status.HTTP_202_ACCEPTED,
--- around line 432 (417-447) ---
   417	            audit_reason, audit_new_device = "first_login", True
   418	            background_tasks.add_task(
   419	                send_new_device_mail,
   420	                user_row.email,
   421	                when=devices.jst_text(),
   422	                device=devices.describe_user_agent(request.headers.get("user-agent")),
   423	                location=geo.lookup(ip),
   424	                note="この機械を最初のいつもの機械として登録しました。 / This device was registered as your first trusted device.",
   425	            )
   426	        else:
   427	            # 知らない機械: 許可依頼を作って 202（トークンは出さない）
   428	            new = await devices.create_login_request(db, user_row.id, request, cookie_raw)
   429	            has_trusted = await devices.has_any_trusted_device(db, user_row.id)
   430	            has_codes = (await recovery_codes.remaining(db, user_row.id)) > 0
   431	            await db.commit()
   432	            await _notify_new_request(background_tasks, user_row.email, new, user_row.id)
   433	            pending = JSONResponse(
   434	                status_code=status.HTTP_202_ACCEPTED,
   435	                content=LoginApprovalRequired(
   436	                    match_number=new.match_number,
   437	                    expires_in=int(devices.REQUEST_TTL.total_seconds()),
   438	                    has_trusted_device=has_trusted,
   439	                    has_recovery_codes=has_codes,
   440	                ).model_dump(),
   441	            )
   442	            devices.set_pending_cookie(pending, new.pending_raw)
   443	            _audit(
   444	                request,
   445	                user_id=user_row.id,
   446	                reason="device_approval_required",
   447	                is_new_device=True,
--- around line 1181 (1166-1196) ---
  1166	    audit_reason, audit_new_device = "ok", None
  1167	    if devices.is_enforced():
  1168	        cookie_raw = request.cookies.get(devices.DEVICE_COOKIE_NAME)
  1169	        found = await devices.find_trusted_device(db, cred.user_id, cookie_raw)
  1170	        if found is not None:
  1171	            await devices.touch_device(db, found.id, request)
  1172	            trusted_device_id = found.id
  1173	            device_cookie_raw = devices.clean_cookie_value(cookie_raw)
  1174	            audit_new_device = False
  1175	        else:
  1176	            trusted_device_id, device_cookie_raw = await devices.register_device(
  1177	                db, cred.user_id, cookie_raw, "passkey", request
  1178	            )
  1179	            audit_reason, audit_new_device = "passkey_new_device", True
  1180	            background_tasks.add_task(
  1181	                send_new_device_mail,
  1182	                cred.email,
  1183	                when=devices.jst_text(),
  1184	                device=devices.describe_user_agent(request.headers.get("user-agent")),
  1185	                location=geo.lookup(ip),
  1186	                note="パスキーでログインし、この機械をいつもの機械に加えました。 / Signed in with a passkey; this device was added as a trusted device.",
  1187	            )
  1188	    family_id = str(uuid.uuid4())
  1189	    raw, expires_at = await self_tokens.issue_refresh_token(
  1190	        db,
  1191	        cred.user_id,
  1192	        request.headers.get("user-agent"),
  1193	        family_id=family_id,
  1194	        trusted_device_id=trusted_device_id,
  1195	    )
  1196	    await db.commit()
```

## Q11 git grep -n -E 'serviceWorker|manifest' origin/main -- frontend/src frontend/index.html frontend/vite.config.ts

```
origin/main:frontend/vite.config.ts:19:    // 閲覧ページ(/viewer/)は本体と別の入口。manifest はここに書かない（CI のビルドでだけ --manifest を付ける）。
```

## Q12 venv

```
python3.12 -m venv /tmp/pv -> OK (python3.12 使用。python3 代替は不要だった)
```

## Q12(a) /tmp/pv/bin/pip install --dry-run --report /tmp/rep.json -c backend/requirements.txt pywebpush==2.5.0 (末尾60行、原文のまま)

```
DEPRECATION: Constraints are only allowed to take the form of a package name and a version specifier. Other forms were originally permitted as an accident of the implementation, but were undocumented. The new implementation of the resolver no longer supports these forms. A possible replacement is replacing the constraint with a requirement. Discussion can be found at https://github.com/pypa/pip/issues/8210
ERROR: Constraints cannot have extras
```

## Q12(a2) 上の(a)が extras で失敗したため、backend/requirements.txt から [extras] 部分だけ sed で除いた制約ファイル(/tmp/constraints-noextras.txt)で同じ pip を再実行した結果（末尾60行、exit=0）

```
Collecting idna<4,>=2.5 (from requests>=2.21.0->pywebpush==2.5.0)
  Downloading idna-3.20-py3-none-any.whl.metadata (7.2 kB)
Collecting urllib3<3,>=1.26 (from requests>=2.21.0->pywebpush==2.5.0)
  Downloading urllib3-2.8.0-py3-none-any.whl.metadata (7.4 kB)
Collecting certifi>=2023.5.7 (from requests>=2.21.0->pywebpush==2.5.0)
  Downloading certifi-2026.10.23-py3-none-any.whl.metadata (2.5 kB)
Collecting aiohappyeyeballs>=2.5.0 (from aiohttp->pywebpush==2.5.0)
  Downloading aiohappyeyeballs-2.7.1-py3-none-any.whl.metadata (5.9 kB)
Collecting aiosignal>=1.4.0 (from aiohttp->pywebpush==2.5.0)
  Downloading aiosignal-1.4.0-py3-none-any.whl.metadata (3.7 kB)
Collecting attrs>=17.3.0 (from aiohttp->pywebpush==2.5.0)
  Downloading attrs-26.1.0-py3-none-any.whl.metadata (8.8 kB)
Collecting frozenlist>=1.1.1 (from aiohttp->pywebpush==2.5.0)
  Downloading frozenlist-1.8.0-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (20 kB)
Collecting multidict<8.0,>=4.5 (from aiohttp->pywebpush==2.5.0)
  Downloading multidict-7.2.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (6.1 kB)
Collecting propcache>=0.2.0 (from aiohttp->pywebpush==2.5.0)
  Downloading propcache-0.5.4-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (25 kB)
Collecting typing_extensions>=4.4 (from aiohttp->pywebpush==2.5.0)
  Downloading typing_extensions-4.16.0-py3-none-any.whl.metadata (3.3 kB)
Collecting yarl<2.0,>=1.25.1 (from aiohttp->pywebpush==2.5.0)
  Downloading yarl-1.25.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (111 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 111.6/111.6 kB 25.4 MB/s eta 0:00:00
Collecting pycparser (from cffi>=2.0.0->cryptography>=47.0.0->pywebpush==2.5.0)
  Downloading pycparser-3.12-py3-none-any.whl.metadata (9.7 kB)
Downloading pywebpush-2.5.0-py3-none-any.whl (22 kB)
Downloading cryptography-48.0.1-cp311-abi3-manylinux_2_34_x86_64.whl (4.7 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.7/4.7 MB 42.0 MB/s eta 0:00:00
Downloading py_vapid-1.9.6-py2.py3-none-any.whl (19 kB)
Downloading requests-2.34.2-py3-none-any.whl (73 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 73.1/73.1 kB 17.5 MB/s eta 0:00:00
Downloading aiohttp-3.14.5-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (1.9 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.9/1.9 MB 52.6 MB/s eta 0:00:00
Downloading aiohappyeyeballs-2.7.1-py3-none-any.whl (15 kB)
Downloading aiosignal-1.4.0-py3-none-any.whl (7.5 kB)
Downloading attrs-26.1.0-py3-none-any.whl (67 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.5/67.5 kB 14.2 MB/s eta 0:00:00
Downloading certifi-2026.10.23-py3-none-any.whl (135 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 135.1/135.1 kB 37.9 MB/s eta 0:00:00
Downloading cffi-2.1.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (221 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 221.8/221.8 kB 46.0 MB/s eta 0:00:00
Downloading charset_normalizer-3.5.2-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (257 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 257.6/257.6 kB 50.5 MB/s eta 0:00:00
Downloading frozenlist-1.8.0-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (242 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 242.4/242.4 kB 45.9 MB/s eta 0:00:00
Downloading idna-3.20-py3-none-any.whl (69 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 69.6/69.6 kB 18.1 MB/s eta 0:00:00
Downloading multidict-7.2.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (516 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 516.8/516.8 kB 48.5 MB/s eta 0:00:00
Downloading propcache-0.5.4-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (250 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 250.4/250.4 kB 32.1 MB/s eta 0:00:00
Downloading typing_extensions-4.16.0-py3-none-any.whl (45 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.6/45.6 kB 11.7 MB/s eta 0:00:00
Downloading urllib3-2.8.0-py3-none-any.whl (135 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 135.7/135.7 kB 34.4 MB/s eta 0:00:00
Downloading yarl-1.25.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (117 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 117.0/117.0 kB 26.6 MB/s eta 0:00:00
Downloading pycparser-3.12-py3-none-any.whl (62 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 62.6/62.6 kB 17.5 MB/s eta 0:00:00
Would install aiohappyeyeballs-2.7.1 aiohttp-3.14.5 aiosignal-1.4.0 attrs-26.1.0 certifi-2026.10.23 cffi-2.1.1 charset-normalizer-3.5.2 cryptography-48.0.1 frozenlist-1.8.0 http_ece-1.2.1 idna-3.20 multidict-7.2.1 propcache-0.5.4 py-vapid-1.9.6 pycparser-3.12 pywebpush-2.5.0 requests-2.34.2 typing_extensions-4.16.0 urllib3-2.8.0 yarl-1.25.1
```

## Q12(b)(c) python3 で /tmp/rep.json を集計した出力（(b)(c)は(a2)の rep.json が元）

```
--- (b) install list (name version) ---
pywebpush 2.5.0
cryptography 48.0.1
http_ece 1.2.1
py-vapid 1.9.6
requests 2.34.2
aiohttp 3.14.5
aiohappyeyeballs 2.7.1
aiosignal 1.4.0
attrs 26.1.0
certifi 2026.10.23
cffi 2.1.1
charset-normalizer 3.5.2
frozenlist 1.8.0
idna 3.20
multidict 7.2.1
propcache 0.5.4
typing_extensions 4.16.0
urllib3 2.8.0
yarl 1.25.1
pycparser 3.12
--- (b) not named in backend/requirements.txt ---
pywebpush 2.5.0
http_ece 1.2.1
py-vapid 1.9.6
requests 2.34.2
aiohttp 3.14.5
aiohappyeyeballs 2.7.1
aiosignal 1.4.0
attrs 26.1.0
certifi 2026.10.23
cffi 2.1.1
charset-normalizer 3.5.2
frozenlist 1.8.0
idna 3.20
multidict 7.2.1
propcache 0.5.4
typing_extensions 4.16.0
urllib3 2.8.0
yarl 1.25.1
pycparser 3.12
--- (b) version differs from requirements.txt (name, resolved, requirements.txt spec) ---
--- (c) requires_dist ---
pywebpush 2.5.0
   aiohttp
   cryptography>=47.0.0
   http-ece>=1.1.0
   requests>=2.21.0
   py-vapid>=1.7.0
   isort; extra == "dev"
   bandit; extra == "dev"
   black; extra == "dev"
   mock; extra == "dev"
   pytest; extra == "dev"
http_ece 1.2.1
   cryptography>=2.5
py-vapid 1.9.6
   cryptography>=46
   coverage; extra == 'test'
   flake8; extra == 'test'
   mock>=1.0; extra == 'test'
   pytest; extra == 'test'
requests 2.34.2
   charset_normalizer<4,>=2
   idna<4,>=2.5
   urllib3<3,>=1.26
   certifi>=2023.5.7
   PySocks!=1.5.7,>=1.5.6; extra == "socks"
   chardet<8,>=3.0.2; extra == "use-chardet-on-py3"
aiohttp 3.14.5
   aiohappyeyeballs>=2.5.0
   aiosignal>=1.4.0
   async-timeout<6.0,>=4.0; python_version < "3.11"
   attrs>=17.3.0
   frozenlist>=1.1.1
   multidict<8.0,>=4.5
   propcache>=0.2.0
   typing_extensions>=4.4; python_version < "3.13"
   yarl<2.0,>=1.25.1
   aiodns>=3.3.0; (sys_platform != "android" and sys_platform != "ios") and extra == "speedups"
   Brotli>=1.2; (platform_python_implementation == "CPython" and sys_platform != "android" and sys_platform != "ios") and extra == "speedups"
   brotlicffi>=1.2; platform_python_implementation != "CPython" and extra == "speedups"
   backports.zstd; (platform_python_implementation == "CPython" and python_version < "3.14" and sys_platform != "android" and sys_platform != "ios") and extra == "speedups"
```

## 参考 grep -n -i cryptography backend/requirements.txt

```
14:python-jose[cryptography]==3.5.0
23:# python-jose[cryptography] が transitive に持ち込むが、用途が異なるため直接依存として明示
24:cryptography==48.0.1
25:# ADR-1013 便5: パスキー。pyOpenSSL 26.2.0 は cryptography 48 と両立する唯一の版（26.3.0 以降と webauthn 3.x は cryptography>=49）
```
