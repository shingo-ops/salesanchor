# recon: クラウドから本番を「読むだけ」できる窓口（段階2）

状態: 調査済み（2026-10-23、Sonnet 調査・Opus 照合）
基準: origin/main 19eb6921659e7e94cb06c00b6abbf5b1d016af13
生出力: /tmp/CC報告ファイル/cloud-read-window-recon-20261023/（以下 $O。社外秘を含むためリポジトリには入れない）

## 1. 既存ADR・仕様の検索
`git grep -i` で `https|窓口|read.?only|ai_reader|ai_ro|network secret|cloud` を docs/adr/ と docs/adr/FEATURE-INDEX.md に当てた（$O/01-adr-grep.txt）。
- HTTPS で本番 DB を読ませる窓口を扱う ADR は無い。
- ADR-1024（AI の本番 DB 読み取りの道）: 読む人 `ai_reader`・秘密列を外したビュー群 `ai_ro`・専用コンテナ `ai-reader`・台本 `backend/app/ops/readonly_query.py`・SSH 鍵 `salesanchor-reader`。
  - docs/adr/ADR-1024*.md:32「専用コンテナ ai-reader。環境変数は AI_READER_DATABASE_URL だけ。volumes なし、read_only、cap_drop: [ALL]、no-new-privileges、backnet のみ。backend コンテナでは動かさない。」
  - 同:46「境界は二重にする。権限の境界は DB の GRANT、コードの境界は process-artifacts gate の GO 記録。」
  - 同:59 不採用「backend コンテナでの実行: 台本の隣に DATABASE_URL・ADMIN_DATABASE_URL・METADATA_FERNET_KEY などがあり、暗号文と復号鍵が同じ場所に揃う。blue-green の切替でコンテナ名が一時的に消える可用性の問題もある」
- ADR-1025（Discord 不具合報告の受け口）: 専用の鍵でだけ通す口の前例。backend/app/routers/ops_error_reports.py:1-10, :66-92。鍵 `ERROR_REPORT_AGENT_TOKEN` が未設定なら全員 401、比較は `secrets.compare_digest`。
- ADR-1017（smoke の最小権限）: 未設定時は拒否に倒す（fail-closed）の前例。
- ADR-1012:45: トークンを本番 secrets に登録する作業が要ると明記。

## 2. 公開経路（$O/02-*）
- api.salesanchor.jp は 49.212.137.46。Cloudflare を通っていない（$O/02-dig-cf.txt）。
- TLS は nginx コンテナで終端（docker-compose.yml:7-9、nginx/nginx.conf:337-338）。
- api の server ブロックは nginx/nginx.conf:331-517（443 側ブロック。:317-329 は 80 番のリダイレクト用）。`location /api/`（:498）から backend:8000。
- 速度制限 `limit_req_zone ... zone=api:10m rate=30r/s`（nginx/nginx.conf:8）、burst=50（:499-500）。
- IP 許可の前例: `/api/v1/ops/alertmanager` は `allow 49.212.160.98` のみ（nginx/nginx.conf:480-482）。
- nginx は frontnet（docker-compose.yml:39）。backend は frontnet と backnet の両方（docker-compose.yml:174-176）。
- nginx の access_log は設定されていない（$O/02-nginx.conf を grep、該当なし）。

## 3. ADR-1024 の実物（$O/03-*）
- docker-compose.ai-reader.yml（40行）: 環境変数は `AI_READER_DATABASE_URL` だけ（:17）。ネットワークは `astro-webapp_backnet`（:37-40）。/dev/log だけマウント。
- backend には `AI_READER_DATABASE_URL` が渡っていない。値は VPS の /home/ubuntu/.config/salesanchor/ai-reader.env。
- readonly_query.py の上限: SQL 64KB、行は既定200・上限5000、1値10KB で切る、60秒で打ち切り。
- 拒否: 先頭語 select/with/show/explain 以外、EXPLAIN ANALYZE、複文、`\` 始まり、set_config/SET/COPY/pg_read_file/pg_sleep/lo_、書込語。秘密列は `<redacted>`（readonly_query.py:40）。
- AUDIT 行は stderr と /dev/log へ。/dev/log に送れなければ rc=5 で結果を出さない。
- k-results（$O/03-k-results.md）: K11 のみ △。K18 で同時3本のうち1本が失敗（同時は2本まで）。
- デプロイのたびに ai_ro が約70秒外れ、その間は 42P01（ビューが無い）になる。

## 4. 鍵の前例（$O/04-*）
- `OPS_API_TOKEN`: backend/app/routers/ops.py:89-90, :102-117。GitHub secret → .github/workflows/deploy.yml:356 で .env に書く → docker-compose.yml:138 で backend へ。
- 生成手順: docs/handoff/ai-ops-247/card-stage2-bin-b.md:357（PO が `!` で実行）。
- docs/B-11_credential_management_policy.md:62-71 の90日更新表に OPS 系の鍵は無い。

## 5. 速度制限・監査（$O/05-*）
- backend/app/middleware/rate_limit.py は Redis 方式。JWT でない固定トークンは IP 単位 60回/分。Redis が落ちると通す（fail-open）。
- backend/app/middleware/audit.py は通常の GET を記録しない。
- → HTTPS 窓口の「誰が何を読んだか」の記録は新しく作る必要がある。

## 6. 手元での使われ方（$O/06-*、AUDIT 行 3450 本）
- 成功 3360。select 2902 / with 532 / explain 12。
- 行数: 中央値16・p90 300・最大5000。所要: 中央値62ms・p90 11.2秒・最大57.9秒。
- よく読むビュー: ai_ro.public__extraction_jobs / source_messages / extraction_items / analysis_results / item_corrections / products ほか（$O/06-views.txt）。

## 7. クラウドの公式仕様（2026-10-23T05:00:36Z 取得。Context7 は月次上限で使えず、公式文書を直接確認）
出典: https://code.claude.com/docs/en/cloud-environments（$O/07-cloud-environments.md）
- 外向き通信は None / Trusted（既定）/ Full / Custom（:216-223）。
- 環境変数は、その環境を使う人なら誰でも読める（:90）。
- ネットワークシークレット（:92-146）: 登録したホストへのリクエストに、中継がヘッダで鍵を付ける。鍵は VM の環境変数にもファイルにも出ない（:134）。値は再表示・編集できず、消して作り直す（:112, :132）。登録ホストは Trusted でも届く（:146, :229）。その環境の全セッションで効く（:146）。
- 外向き IP が固定だという記載は無い（全文を確認）。

## 8. 未確認
- クラウドの会話記録に鍵の文字列が出ないこと（実地未測定）。
- routine（定期実行）でネットワークシークレットが効くこと（実地未確認）。
- 本番機 prod1 の空きメモリに、常駐コンテナ1つを足す余裕があるか（未測定。実装カードの最初で測る）。
