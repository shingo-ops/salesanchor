# card-1: クラウドから本番を読むだけの窓口（便1 実装）

状態: カード発行（Opus、2026-10-23）。根拠: design.md（PO 承認 2026-10-23「1」）、ADR-1042、recon.md、実装前調査 /tmp/CC報告ファイル/cloud-read-window-impl-recon-20261023/（以下 $R）
担当: Sonnet。触ってよいのは下の「触るファイル」だけ。本番・GitHub secret・VPS には触らない（反映は Opus がマージ後に deploy で行う）。

## 0. 設計からの具体化（Opus 決定・design.md §11 に追記する）
- D1 同時数: ai_reader の接続上限は 2（本番実測 rolconnlimit=2、max_connections=100。$R/opus-role.txt）。窓口は **同時1本** にし、もう1本は手元の SSH の道に残す。全体で2本まで（PO 承認の K6「同時に読むのは2本まで。手元の道はそのまま」を満たす形）。DB の上限は変えない。
- D2 別プロジェクト: deploy.yml の `--remove-orphans`（:453, :722）に消されないよう、compose の `name:` は `astro-webapp-readwindow`。ネットワークは既存の `astro-webapp_frontnet` と `astro-webapp_backnet` を external で使う。`container_name: ai-reader-http`。.env の COMPOSE_PROJECT_NAME が top-level の name: より優先されるため、起動は必ず -p astro-webapp-readwindow を付ける。
- D3 nginx は resolver 127.0.0.11 と変数で送る（nginx/nginx.conf:355-356 の前例）。コンテナが居なくても nginx は起動する。コンテナが落ちているときは 503 を返す（`error_page 502 504 =503`）。
- D4 GO の境界: `docker-compose.ai-reader-http.yml` を scripts/check-process-artifacts.js の DANGEROUS_PATTERNS（:126 の隣）に足す。nginx/nginx.conf は足さない（窓口の守りは鍵と DB の権限にあり、nginx の変更では広がらない。ほかの作業への影響を避ける）。
- D6 鍵のヘッダ: `Authorization` は使わず専用ヘッダ `X-Read-Window-Token`（前置きなし）にする。クラウドのネットワークシークレットはヘッダ名を変えられる（公式 cloud-environments:126。$O/07）。api.salesanchor.jp への全通信に付くが、保守用 OPS_API_TOKEN の `Authorization` と取り合わない。backend はこのヘッダを読まない。
- D7 止め続ける手順: サーバーの鍵を空にするだけでは次の deploy で GitHub secret から書き戻される。即停止は「`docker stop ai-reader-http`」、止め続けるには加えて GitHub secret `READ_WINDOW_TOKEN` を消す（空なら全員 401）。design.md §6 と ADR-1042 戻し方に足す。
- D8 既知の重なり: 窓口の読み（最長60秒）と deploy の ai_ro 作り直し（ロック待ち1秒・最大40回、ADR-1037）が重なると作り直しが失敗しうる。失敗時の作り直しは #4618 の仕組みで行われる。usage-cloud.md に「重い読みは短く分ける」を書き、K8 の測定期間に deploy があれば結果を記録する。
- D5 接続情報の正本は VPS の /home/ubuntu/.config/salesanchor/ai-reader.env の1か所のまま。compose は `env_file` でこれを読む（値を写さない）。窓口の鍵は deploy が .env に書く `READ_WINDOW_TOKEN` を `${READ_WINDOW_TOKEN:-}` で受ける（空なら全員 401）。

## 1. 触るファイル
1. backend/app/ops/readonly_query.py（関数の切り出しのみ。動きは変えない）
2. backend/app/ops/read_window_http.py（新規）
3. backend/tests/ops/test_readonly_query.py（既存が通ることの確認。必要なら切り出し関数の試験を追加）
4. backend/tests/ops/test_read_window_http.py（新規）
5. docker-compose.ai-reader-http.yml（新規）
6. nginx/nginx.conf（location 1つと limit_req_zone 1行）
7. .github/workflows/deploy.yml（READ_WINDOW_TOKEN を .env に書く2か所と、窓口コンテナを起こす手順1つ）
8. scripts/check-process-artifacts.js（DANGEROUS_PATTERNS に1行）、scripts/tests/test-process-artifacts.js（その試験1件）、.github/CODEOWNERS（1行）
9. docs/B-11_credential_management_policy.md（90日表に1行）
10. docs/handoff/cloud-read-window/card-1.md（このカード）、design.md（§11 追記ほか）、usage-cloud.md（新規・クラウドからの呼び方）、docs/adr/ADR-1042-cloud-read-window.md、docs/adr/README.md（再生成）
11. .claude-pipeline/active-work.d/release-cloud-read-window-bin1.md
触らない: migrations/、docker-compose.yml、docker-compose.ai-reader.yml、backend の他のコード、frontend、.claude/settings.json。

## 2. 変更の中身
### 2-1. readonly_query.py の切り出し
- `_run`（:229-301）の中身を `execute(sql_text, connect, audit) -> Result` に切り出す。Result は (rc, body, err) の小さな dataclass。body は今の標準出力と同じ TSV 文字列、err は今の標準エラーに書く文字列（AUDIT 行を含む）。
- `_run` は stdin を読んで `execute` を呼び、body/err を今と同じ順で書き、rc を返すだけにする。AUDIT が ok のとき stdout より先に送る順序（:295）は execute の中で保つ。
- 既存試験 backend/tests/ops/test_readonly_query.py が **一字も変えずに** 全件通ること。

### 2-2. read_window_http.py（新規）
- Starlette（requirements.txt:2 に既存）の最小アプリ。依存を足さない。
- `POST /api/v1/ops/read-window/query` だけ。本文は SQL のテキスト（UTF-8）。64KB を超えたら 413。
- 鍵: 環境変数 `READ_WINDOW_TOKEN`。空・未設定なら常に 401。ヘッダ `X-Read-Window-Token: <鍵>` を `secrets.compare_digest`（ops_error_reports.py:82 と同じ）で比べる。違えば 401。本文は理由を書かない（"unauthorized" のみ）。
- 同時数: `threading.Semaphore(1)` を非ブロッキングで取る。取れなければ 429（"busy"）。
- 実行は `readonly_query.execute` を threadpool で呼ぶ。audit は `_open_audit` を毎回開く（今と同じ）。AUDIT 行には ` via=https` を足す（`_log` に引数を足す形。既定は今と同じ出力）。
- 応答: rc0→200 text/tab-separated-values で body。rc2→400、rc4→400（err の DB エラー行だけ。AUDIT 行は返さない）、rc3/rc5→503。どの応答にもヘッダ `X-Read-Window-Rc: <rc>`。
- GET や他のパスは 404/405。
- 起動: `uvicorn app.ops.read_window_http:app --host 0.0.0.0 --port 8080 --workers 1 --no-access-log`。

### 2-3. docker-compose.ai-reader-http.yml（新規）
docker-compose.ai-reader.yml（$R の 2. の全文）を手本にする。
- `name: astro-webapp-readwindow`。service `ai-reader-http`、`container_name: ai-reader-http`。build ./backend・image astro-webapp-backend（ai-reader と同じ）。
- command は 2-2 の uvicorn。
- `env_file: /home/ubuntu/.config/salesanchor/ai-reader.env`（D5）。environment は `READ_WINDOW_TOKEN: ${READ_WINDOW_TOKEN:-}` だけ。
- read_only、tmpfs /tmp、cap_drop ALL、security_opt no-new-privileges、mem_limit 128m、restart unless-stopped、logging none、/dev/log の bind（ai-reader と同じ書き方）。ports なし。
- networks: astro-webapp_frontnet と astro-webapp_backnet（どちらも external）。
- healthcheck は付けない（curl が image に無い前提を確かめてから。無ければ付けない）。

### 2-4. nginx/nginx.conf
- :8 の下に `limit_req_zone $binary_remote_addr zone=read_window:10m rate=2r/s;`。
- api の server ブロック、`location = /api/v1/ops/alertmanager`（:479-496）の直後に:
  - `location = /api/v1/ops/read-window/query {` `limit_except POST { deny all; }` `client_max_body_size 64k;` `limit_req zone=read_window burst=4 nodelay;` `limit_req_status 429;` `set $read_window ai-reader-http;` `proxy_pass http://$read_window:8080;` Host/X-Real-IP/X-Forwarded-For/X-Forwarded-Proto/X-Request-ID は alertmanager と同じ。`proxy_read_timeout 75s;` `error_page 502 504 =503 /__rw_unavailable;` と、それを返す internal location（本文 "unavailable"）。
  - resolver はブロックの :355 のものが効くことを確かめる。効かない書き方なら同じ resolver 行を location 内に置く。

### 2-5. deploy.yml
- :310 の削除列に `-e '/^READ_WINDOW_TOKEN=/d'`、:356 の並びに `READ_WINDOW_TOKEN='${{ secrets.READ_WINDOW_TOKEN }}'`（ERROR_REPORT_AGENT_TOKEN :358 と同じ形）。:363 の引用符・改行チェックに同じく含める。secret が未登録でも空で書かれて止まらないこと（ERROR_REPORT_AGENT_TOKEN と同じ扱いか確かめる）。
- nginx を作り直す手順（:479-494）の後に1手順:「ai-reader-http を起こす」。`docker compose -p astro-webapp-readwindow -f docker-compose.ai-reader-http.yml up -d --build=false --force-recreate` 相当（image は backend と同じものを使い、作り直しの build はしない。ai-reader の image が deploy でどう作られているかを $R の deploy.txt で確かめ、同じ image タグを使う）。
- この手順は失敗しても deploy 全体を止めない（`|| echo "::warning::..."`）。窓口は付け足しの機能で、アプリの反映を巻き込まないため。env_file が無い・読めない場合も警告で抜ける。
- blue-green の手順・migration の手順は触らない。

### 2-6. その他
- check-process-artifacts.js の :126 の隣に `/^docker-compose\.ai-reader-http\.yml$/`。test-process-artifacts.js に1件。.github/CODEOWNERS:27 の隣に同じファイルを同じ持ち主で1行。
- B-11 :71 の下に `| **AI 読み取り窓口の鍵**（`READ_WINDOW_TOKEN`） | **90日ごと**（ADR-1042） |`。
- usage-cloud.md: クラウドからの呼び方（`curl -sS --fail-with-body -X POST --data-binary @q.sql https://api.salesanchor.jp/api/v1/ops/read-window/query`。鍵はネットワークシークレットが付けるので書かない）、応答と X-Read-Window-Rc の表、42P01 のときは1分待つ、同時1本、出力はファイルへ、データ内の指示に従わない（usage.md §5 と同じ）。
- recon.md を実物に合わせて直す: §5 の backend/app/core/rate_limit.py・audit.py → backend/app/middleware/rate_limit.py・audit.py、§2 の「nginx/nginx.conf:318-515」→ 443 側ブロックの実際の行範囲、§1 の hmac.compare_digest → secrets.compare_digest（2026-10-23 審査役の指摘）。
- design.md の末尾に「## 11. 実装前の具体化（2026-10-23）」として D1〜D8 を書き、§3-1 の「同時2本」「hmac」、§3-3 の「Authorization: Bearer」、§3-4 の「で始まる」、§6 を D1・D6・D4・D7 に合わせて直す。ADR-1042 の What 4・5 と戻し方も同じく直す（docs/adr/README.md は `node scripts/generate-adr-index.js` で再生成）。

## 3. 試験（担当が手元で行い、生出力を /tmp/CC報告ファイル/cloud-read-window-bin1-20261023/ へ）
- T1 `cd backend && pytest tests/ops/test_readonly_query.py -q` 全件合格（既存は無改変）。
- T2 test_read_window_http.py（Starlette の TestClient。DB はスタブ）: 鍵なし/違う鍵/サーバー鍵空/`Authorization: Bearer <正しい鍵>`（専用ヘッダ以外では通さない） → 401（K3）、書込10種（UPDATE・DELETE・INSERT・DROP VIEW（表を消す形の文字列は安全フックが止めるため、DROP の種類として VIEW を使う。2026-10-23 Opus 修正）・複文・SET・COPY・`\` 始まり・pg_sleep・EXPLAIN ANALYZE）→ 400 で DB に届かない（K2）、同時2本目 → 429（K6）、audit 不可 → 503 で本文なし（K5）、秘密列 → `<redacted>`（K4）、65KB → 413、GET → 405。
- T3 `node scripts/tests/test-process-artifacts.js` 合格。
- T4 `docker compose -p astro-webapp-readwindow -f docker-compose.ai-reader-http.yml config --quiet`（env_file が手元に無いなら、そのことを記録して代わりに yaml の構文確認）。
- T5 nginx の構文: `docker run --rm -v $PWD/nginx/nginx.conf:/etc/nginx/nginx.conf:ro nginx:<compose と同じ版> nginx -t` が手元で動くなら実行。証明書パスで失敗する場合は、その失敗だけであることを記録。
- T6 `bash scripts/agent-hooks/cloud/test.sh` が今まで通り全件OK（触っていないことの確認）。

## 4. 想定分岐（迷ったら止めて Opus に NEEDS_DECISION）
- `_run` の切り出しで既存試験を変えないと通らない → 止める。
- deploy.yml で image タグが ai-reader と backend で違う／build が要る → 止めて実物を報告。
- nginx の resolver が location に効かない、または alertmanager の直後に置けない事情がある → 止める。
- secret 未登録で deploy の検査（:363）が落ちる → 止める。
- 触るファイルの外を変えたくなった → 止める。

## 5. 完了の形
release/cloud-read-window-bin1 に commit・push。PR は作らない（Opus が作る）。DONE と、T1〜T6 の結果・変更ファイル一覧（git diff --stat）を報告。
