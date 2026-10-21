# recon: 画面ファイルの圧縮配信（在庫表の高速化 便1）

- 基準: origin/main 222f07098（git fetch 後）
- 生出力: /tmp/CC報告ファイル/inventory-speed/recon/、recon3/、bin1/recon/（01〜09）
- 親: 在庫表の高速化（PO 2026-10-18「在庫表だが表示速度を挙げられる？…瞬時に開かせる方法はある？」）。全体の実現可能性と審査: /tmp/CC報告ファイル/inventory-speed/feasibility.md、review-fable/review.md、review-reviewer/review.md

## 既存 ADR の検索
- `git grep -n -i nginx docs/adr` 94件（bin1/recon/07-adr-nginx.txt）。圧縮（gzip/brotli）を決めた ADR は 0 件
- ADR-137: 外側 nginx の再作成は nginx/** と docker-compose.yml の変更時のみ。frontend/nginx.conf は対象外
- `docs/adr/ADR-1016-realtime-change-signal-standard.md:9`・`docs/adr/ADR-1016-realtime-change-signal-standard.md:48`: SSE 用の外側 nginx の location 追加を危険 PR（GO 必須）とした。frontend/nginx.conf の区分は明記なし → 本件は危険 PR と同じ GO 手順で扱う（ADR-136）

## 現状【事実】
- 本番 https://app.salesanchor.jp/assets/main-DEpSbW8N.js: HTTP/2 200、content-length 2363610、`Accept-Encoding: gzip, br` を付けても content-encoding なし、cf-ray なし（recon3/curl_headers.txt）。gzip にすると 587,194 byte（recon/ の手元計測）
- DNS app.salesanchor.jp = 49.212.137.46、Cloudflare の範囲外（recon3/cf_check.txt）。VPS 直で配信
- 経路: ブラウザ → 外側 nginx（nginx:1.31.1、`docker-compose.yml:6`、`nginx/nginx.conf:303-309` `location /` が `proxy_pass http://$frontend:8080`）→ frontend コンテナ（`frontend/Dockerfile:25` `FROM nginx:alpine`、`frontend/Dockerfile:31` `COPY nginx.conf /etc/nginx/conf.d/default.conf`）
- `frontend/nginx.conf`（41行）: server 1ブロック（listen 8080）。`frontend/nginx.conf:31-35` `location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$` に expires 1y・immutable。gzip の記述なし（bin1/recon/03-nginx.conf.txt）
- nginx:alpine（1.31.7）の既定 /etc/nginx/nginx.conf:29 は `#gzip  on;`（コメント）、:31 `include /etc/nginx/conf.d/*.conf;`。gzip_static・gunzip モジュールあり（bin1/recon/08-nginx-alpine-image.txt）
- 外側 nginx: nginx/ 配下に gzip・gunzip・Accept-Encoding の記述 0 件（06-outer-gzip.txt）。proxy_set_header は Host・X-Real-IP・X-Forwarded-For・X-Forwarded-Proto 等のみで Accept-Encoding は上書きしない
- nginx 公式（nginx.org ngx_http_gzip_module）: gzip 既定 off／gzip_types 既定 text/html のみ／gzip_vary 既定 off／gzip_min_length 既定 20／gzip_comp_level 既定 1／gzip_proxied 既定 off（Via ヘッダのある要求に効く）／gzip_http_version 既定 1.1。proxy_pass_request_headers 既定 on、proxy_http_version は 1.29.7 以降既定 1.1
- 反映: `.github/workflows/deploy.yml:415` で毎回 `docker compose build`、`.github/workflows/deploy.yml:449-453` で frontend を毎回作り直す（パスフィルタなし）。frontend/nginx.conf の変更は main への push ごとに確実に反映される。外側 nginx の再作成（`.github/workflows/deploy.yml:479-490`）は不要
- 検査: frontend/nginx.conf を検査する CI・テストは 0 件（05-grep-nginxconf.txt）。vite に事前圧縮プラグインなし

## 未確認
- 外側 nginx が frontend への要求に Via を付けるか（gzip_proxied の要否）→ 設計で gzip_proxied any を指定して依存をなくす
