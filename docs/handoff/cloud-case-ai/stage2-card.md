# 段2 実装カード（設計第4.6版の追補・第1版）

- 対象: docs/handoff/cloud-case-ai/design.md 第4.6版 §4-2・§4-3・§7（T2〜T6c・T7）・§9 の段2。ADR-1052（Accepted）。
- 根拠の写し: S=origin/main 8c6f52813（Merge #4942）。行番号はすべてこの sha。実装の前に最新の origin/main で行を合わせ直す（§3(a)）。
- 前提（済み）: 段1 本番反映・受入合格（#4932・#4940）。case-api.salesanchor.jp はさくらの DNS に登録済み、証明書は 2026-10-31 16:46 に取得（期限 2027-01-29。PO の `!`）。
- 状態: 第1版（審査前）。

## 0. 設計からの直し（V5。どれも事実に合わせる直しで、守りの強さは変えない）
- V5-1 DNS: 設計 §4-3（design.md:179）・§4-4（:210）の「Cloudflare・グレー雲」は事実と違う。case-api の名前はさくらの DNS（ns1/ns2.dns.ne.jp）にあり、プロキシは無い。SNI はそのまま nginx に届く（守りの前提は満たす）。design.md の 2 行をこのカードと同じ PR で直す。プロキシを入れる場合に守りを作り直す約束は残す。
- V5-2 421 の守りの書き方: 設計 §4-3（:176）の `include snippets/case-api-sni-guard.conf` は採れない。nginx の容器は S nginx/nginx.conf 1 つだけを /etc/nginx/conf.d/default.conf として読む（S docker-compose.yml:11。VPS の実物でも同じ）。nginx/snippets/ は無い。include のために本体の compose を変えると、ほかの名前の入口まで巻き込む。
  - 代わり: S nginx/nginx.conf の先頭（http の段。S :6-10 の limit_req_zone と同じ段）に `map $ssl_server_name $is_case_api_sni { default 0; case-api.salesanchor.jp 1; }` を 1 つ置く。今の 443 のブロック 5 つそれぞれに `if ($is_case_api_sni) { return 421; }` を 1 行置く。
  - 判定の正本は map の 1 か所（名前を書くのはそこだけ）。
- V5-3 CI の数え合わせ: CI に nginx の検査の仕事は無く、S .github/workflows/test.yml の detect-changes の対象に nginx/** が無い。
  - 数え合わせは pytest で行う（§4-F の #13）。test.yml の detect-changes と push の paths に `nginx/**` を足し、nginx だけの変更でも試験が流れるようにする。
  - nginx の文法の検査（nginx -t）も CI に足す（§4-F の #14）。今は文法の誤りがデプロイの nginx の作り直しまで見つからず、そこで全部の入口が止まる。
- V5-4 鍵の持たせ方: 設計 §4-3（:146）の「CASE_AGENT_TOKEN（の照合用ハッシュ）」は採らない。ai-unmask-http には ai-reader-cloud-http（S docker-compose.ai-reader-cloud-http.yml:31）と同じく値そのものを渡し、hmac.compare_digest で比べる。
  - 理由: 値はすでに VPS の .env に書かれている（S .github/workflows/deploy.yml:378）。容器だけハッシュにしても、同じ機械の .env に値が残るので守りは増えない。ハッシュを作る手順を deploy に足すと、手順が 1 つ増えて壊れる所が増える。
- V5-5 秘密列と拒否表の正本: 設計の「列が DENY_COLUMN_RE に当たらない」は、正規表現を写さず、段1の ai_cloud_meta.build_columns の mode を正本にする。
  - mode='excluded' は「deny に当たって外した列」（段1 カード §4-A）。同じ正規表現を backend と関数に写すと、正本が 3 か所に分かれる。
  - 拒否表は新しい表 ops_case.deny_tables の 1 か所に書く（§4-A）。加えて、build_columns に mode='excluded' の列を 1 つでも持つ表（＝秘密列を持つ表）は、表ごと拒否する。
  - 同じ判定を関数 ops_case.is_denied_source(source text) 1 つにまとめる。backend の申請の受付・unmask_fetch・持ち主の権限付け（grant_unmask_owner）の 3 か所はこの関数だけを呼ぶ。
- V5-6 ai_unmask の記録の設定: 段1のロールは log_statement='all'。ai_unmask は 'none' にする。
  - 理由: 呼び出しの文に件の札がそのまま入り、DB の記録に残る。読んだ記録は同じ取引で unmask_reads に残る（§4-A）。返した値は、どちらの設定でも DB の記録に出ない。
- V5-7 3回目の申請: 「自動で断り、PO に知らせる」は、段2では status='denied'・decided_by='auto:limit' の行を残し、409 を返すところまで。知らせるのは段4（agent-console が GET /ops/case/pending の auto_denied を読む）。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 今（S） | 変える形 |
|---|---|---|---|
| 1 | 新 migrations/<日時>_create_ops_case.sql（一覧に載せる） | 無し | §4-A。スキーマ ops_case・表 6 つ・ロール 2 つ・関数 3 つ。冪等 |
| 2 | S scripts/run_all_migrations.sh | 一覧の末尾は :1193 の 20261024_100100_create_ai_reader_cloud_role.sql。trap の ai_cloud の作成は :252-262 | :1193 の後に #1 を足す。trap の ai_cloud の作成の後（:262 の後、`exit "${rc}"` の前）に持ち主の権限の付け直しを足す（§4-B） |
| 3 | 新 backend/app/routers/ops_case.py | 無し | §4-C の口 8 つ |
| 4 | S backend/app/main.py | :74-75 で import、:777・:780 で include_router(prefix="/api/v1") | ops_case を同じ形で import と include_router |
| 5 | 新 backend/app/ops/unmask_http.py | 無し | §4-D。S backend/app/ops/read_window_http.py の形（app.* の import は最小） |
| 6 | 新 docker-compose.ai-unmask-http.yml | 無し | S docker-compose.ai-reader-cloud-http.yml の写し（§4-E） |
| 7 | S docker-compose.yml | backend の environment :135-144 に OPS_API_TOKEN・OPS_INGEST_TOKEN・ERROR_REPORT_AGENT_TOKEN | 同じ所に `CASE_AGENT_TOKEN=${CASE_AGENT_TOKEN:-}`・`CASE_ADMIN_TOKEN=${CASE_ADMIN_TOKEN:-}` の 2 行 |
| 8 | S nginx/nginx.conf | 667 行。443 のブロックは jarvis :32-33・app :70-73・api :334-337・monitor :570-573・salesanchor.jp :624-627 | §4-F（map 1 つ・limit_req_zone 1 つ・421 の行 5 つ・case-api のブロック 1 つ） |
| 9 | S .github/workflows/deploy.yml | :325 の sed で CASE_AGENT_TOKEN 行を消す。:378 で書く。:534-550 で ai-reader-cloud-http を起こす | :325 の sed に `-e '/^CASE_ADMIN_TOKEN=/d'`。:378 の次に `CASE_ADMIN_TOKEN='${{ secrets.CASE_ADMIN_TOKEN }}'`。:550 の後に同じ形の手順「Start ai-unmask-http」（§4-E） |
| 10 | S .github/workflows/test.yml | detect-changes の対象に nginx/** が無い | detect-changes の filter と push の paths に `nginx/**` |
| 11 | 新 .github/workflows/nginx-config-check.yml | 無し | §4-F の #14 |
| 12 | 新 backend/tests/ops/test_ops_case_db.py | 無し | T2〜T6c の DB 側（§4-G） |
| 13 | 新 backend/tests/ops/test_nginx_case_api_guard.py | 無し | §4-F の数え合わせ |
| 14 | 新 backend/tests/ops/test_unmask_http.py・新 backend/tests/test_ops_case_router.py | 無し | §4-G |
| 15 | docs/handoff/cloud-case-ai/design.md | :176-177・:179・:210・:146 | V5-1〜V5-4 に合わせる（このカードの PR で直す。実装の PR では触らない） |

## 2. 触らない範囲
- 段1の部品（ai_cloud・ai_cloud_meta の表と build_views・ai_reader_cloud・ai-reader-cloud-http・read_window_http.py）。build_columns の中身の作り方も変えない。
- 今の窓口（ai_ro・ai_reader・ai-reader-http）と、api.salesanchor.jp の今の location。
- 既存の POST /ops/incidents/human（S backend/app/routers/ops.py:524-569。件を作る口はこのまま使う）。
- クラウドの設定（段3）・agent-console（段4）。
- nginx の 80 番のブロック（case-api の 80 番は今の jarvis の既定のブロックに当たり、証明書の更新の道 /.well-known/acme-challenge/ はそこで通る。S nginx/nginx.conf:13-26）。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 行の合わせ直し: §1 の行番号を最新の origin/main で引き直す。migration の一覧の末尾が :1193 より後ろに伸びていれば、その後ろに #1 を足す。trap の形が S と違えば止めて Opus へ。
- (b) 試験 DB の jarvis: CI の試験 DB で migration を流すロールが superuser か（CREATE ROLE … BYPASSRLS と ALTER FUNCTION … OWNER に要る。本番の jarvis は rolsuper=t・rolbypassrls=t。ADR-1024:18）。違えば止めて Opus へ。
- (c) 登録の検査: S scripts/check-migration-registration-exists.sh が #1 を通すか（一覧に載せるので逃がしは要らない見込み）。落ちたら止めて Opus へ。
- (d) 拒否表の名前: 次の表が origin/main の migration に実在するかを数える。public.users・public.viewer_accounts・public.auth_events・public.auth_refresh_tokens・public.password_reset_tokens・public.registration_tokens・public.viewer_login_events・public.viewer_login_tokens・public.webauthn_credentials・（tenant の）tenant_carrier_credentials。ほかに認証・合言葉・鍵の表（名前に auth・login・session・passkey・webauthn・credential・otp・totp・mfa・reset・token・password を含む表）があれば一覧に足す候補として止めて Opus へ（勝手に足さない・勝手に減らさない）。
- (e) 主キー: ai_cloud に載る表のうち、主キーが 1 列でない表・主キーが無い表を数える。それらは申請を受けない（§4-A の is_denied_source とは別に、申請の受付で 422）。数を報告に書く。
- (f) 鍵の口の前例: S backend/app/routers/ops_error_reports.py:69-87 の専用鍵の Bearer の作り（空の鍵なら全員 401・compare_digest）を CASE_AGENT_TOKEN と CASE_ADMIN_TOKEN の 2 つに写す。形が違えば止めて Opus へ。
- (g) 操作の記録の文脈: ops_case の表の RLS は ops_incidents と同じ形にする（S migrations/20261016_100000_create_ops_incident_tables.sql の ENABLE＋FORCE・`current_setting('app.is_operator', true) = 'true'` の方針・salesanchor_app の権限の付け方と DELETE・TRUNCATE の REVOKE）。router は S backend/app/auth/dependencies.py:482 の set_operator_context と ops.py の _clear_operator を使う。
- (h) nginx の文法の検査の材料: S nginx/nginx.conf の中で、変数を通さずに proxy_pass する宛先の名前と、ssl_certificate の道を全部数える。#14 で偽の証明書と --add-host を用意する数と合わせる。
- (i) 容器のイメージ: ai-unmask-http も astro-webapp-backend を使う（S docker-compose.ai-reader-cloud-http.yml:15）。psycopg2 がイメージに入っているか（S backend/app/ops/readonly_query.py:280-289 が使っている）。
- (済) 証明書: 2026-10-31 16:46 に PO の `!` で取得済み（certbot の webroot・今の名前と同じ形。道は /etc/letsencrypt/live/case-api.salesanchor.jp/）。マージの直前に Opus が PO の `!` の確認台本で、fullchain.pem と privkey.pem があることをもう一度確かめる（§4）。

## 4-A. #1 の中身（migrations/<日時>_create_ops_case.sql）
- `CREATE SCHEMA IF NOT EXISTS ops_case;` `REVOKE ALL ON SCHEMA ops_case FROM PUBLIC;`
- 表（どれも `CREATE TABLE IF NOT EXISTS`）:
  - cases: incident_id uuid PRIMARY KEY REFERENCES public.ops_incidents(id)・ticket_hash text・ticket_expires_at timestamptz・created_at timestamptz NOT NULL DEFAULT now()。ticket_hash は `^[0-9a-f]{64}$`。
  - reports: id uuid PK DEFAULT gen_random_uuid()・incident_id uuid NOT NULL UNIQUE REFERENCES ops_case.cases(incident_id)（2 回目は一意制約で 409）・status text CHECK IN ('investigating','reported')・summary text・cause text・evidence jsonb・proposal jsonb・risk text・needs_decision text・received_at timestamptz NOT NULL DEFAULT now()。本文の 32KB の上限は backend で測る（§4-C）。
  - unmask_requests: id uuid PK DEFAULT gen_random_uuid()・incident_id uuid NOT NULL REFERENCES ops_case.cases(incident_id)・view_name text NOT NULL・column_names text[] NOT NULL CHECK (cardinality BETWEEN 1 AND 5)・row_keys text[] NOT NULL CHECK (cardinality BETWEEN 1 AND 20)・reason text NOT NULL CHECK (char_length BETWEEN 20 AND 1000)・status text NOT NULL DEFAULT 'pending' CHECK IN ('pending','approved','denied','expired')・decided_by text・decision_reason text・approved_minutes integer CHECK (approved_minutes BETWEEN 1 AND 15)・expires_at timestamptz・max_reads integer NOT NULL DEFAULT 1 CHECK (max_reads = 1)・read_count integer NOT NULL DEFAULT 0 CHECK (read_count >= 0 AND read_count <= max_reads)・created_at timestamptz NOT NULL DEFAULT now()。CHECK (status <> 'approved' OR (approved_minutes IS NOT NULL AND expires_at IS NOT NULL))。
  - unmask_reads: id bigserial PK・request_id uuid NOT NULL REFERENCES ops_case.unmask_requests(id)・read_at timestamptz NOT NULL DEFAULT now()・row_count integer NOT NULL・column_names text[] NOT NULL。値の列は持たない。
  - audits: id bigserial PK・ran_at timestamptz NOT NULL DEFAULT now()・findings jsonb NOT NULL・finding_count integer NOT NULL。
  - deny_tables: table_name text PRIMARY KEY・reason text NOT NULL。中身は §3(d) の 10 行（表の名前だけ。スキーマは問わず、public でも tenant_* でも同じ名前なら拒否）。`TRUNCATE` してから `INSERT`（ファイルが正本。段1の column_class と同じ）。
- RLS と backend の権限: cases・reports・unmask_requests・unmask_reads・audits は ops_incidents と同じ形（§3(g)）。salesanchor_app には、cases の SELECT・INSERT・UPDATE、reports の SELECT・INSERT、unmask_requests の SELECT・INSERT・UPDATE、unmask_reads の SELECT、audits の SELECT・INSERT、deny_tables の SELECT。DELETE・TRUNCATE は REVOKE。salesanchor_app に ai_cloud_meta の USAGE と build_columns の SELECT（申請の受付で列を確かめるため。中身は名前だけで値は無い）。
- ロール（段1の S migrations/20261024_100100_create_ai_reader_cloud_role.sql の DO の形。属性が違えば RAISE EXCEPTION）:
  - ai_unmask_owner: NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION BYPASSRLS。
  - ai_unmask: LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2。パスワードは付けない（§4 の PO の `!`）。`ALTER ROLE ai_unmask SET log_statement='none'`（V5-6）・statement_timeout='10s'・idle_in_transaction_session_timeout='30s'。default_transaction_read_only は付けない（書ける取引が要る）。
- 関数 ops_case.is_denied_source(p_source text) RETURNS boolean（SECURITY INVOKER・STABLE・`SET search_path = pg_catalog, pg_temp`）: p_source は 'スキーマ.表'。表の名前が deny_tables にある、または ai_cloud_meta.build_columns に source=p_source かつ mode='excluded' の行がある、なら true。
- 関数 ops_case.unmask_fetch(p_request_id uuid, p_ticket text) RETURNS jsonb:
  - SECURITY DEFINER・`SET search_path = pg_catalog, pg_temp`・持ち主 ai_unmask_owner（`ALTER FUNCTION … OWNER TO ai_unmask_owner`）・`REVOKE ALL ON FUNCTION … FROM PUBLIC`・`GRANT EXECUTE … TO ai_unmask`。
  - 中の名前はすべてスキーマ付きで書く（search_path に頼らない）。
  - 確かめる順（どれかが合わなければ RAISE EXCEPTION（SQLSTATE '42501'・文は理由の短い印だけ）で値を返さない）:
    1. 申請の行を `SELECT … FROM ops_case.unmask_requests WHERE id = p_request_id FOR UPDATE`。無ければ断る。
    2. 件の札: `encode(sha256(convert_to(p_ticket,'UTF8')),'hex')` が cases.ticket_hash と一致し、now() < cases.ticket_expires_at。
    3. status='approved'。
    4. now() < expires_at。
    5. read_count < max_reads。
    6. view_name が ai_cloud に実在する（pg_class と pg_namespace。relkind='v'）。
    7. build_columns から view_name の source を 1 つに決める。is_denied_source(source) が false。
    8. column_names の全部が、build_columns のその view_name の列にあり、mode が 'excluded' でない。
    9. 元の表の主キーが 1 列（pg_index の indisprimary・indnatts=1）。
  - 読み方: `format('SELECT to_jsonb(t) FROM (SELECT %I AS __key, %s FROM %I.%I WHERE %I = ANY ($1::%s[])) t', pk, <列ごとの %I をつなげたもの>, schema, table, pk, format_type(pk の型))` を `EXECUTE … USING p_row_keys` で回し、jsonb の配列にまとめる。列と表の名前は %I、型は format_type の結果だけを %s に入れる（カタログ由来）。
  - 同じ取引で `UPDATE ops_case.unmask_requests SET read_count = read_count + 1` と `INSERT INTO ops_case.unmask_reads(request_id, row_count, column_names)`。
  - 返す形: `{"request_id":…, "rows":[…], "row_count":n}`。
- 関数 ops_case.grant_unmask_owner() RETURNS integer（SECURITY INVOKER。呼ぶのは trap の jarvis。EXECUTE は PUBLIC から REVOKE し、だれにも付けない）:
  1. public と tenant\_% の全部の表について、ai_unmask_owner の SELECT を REVOKE（前の回に付けた表が拒否側に移った場合に外すため）。
  2. build_columns の source（重複を除く）のうち、is_denied_source が false の表に SELECT を GRANT し、そのスキーマに USAGE。
  3. ai_cloud_meta の USAGE と build_columns・ops_case.deny_tables の SELECT。ops_case の USAGE、cases と unmask_requests の SELECT、unmask_requests の UPDATE(read_count)、unmask_reads の INSERT と bigserial の列の USAGE。
  4. 付けた表の数を返す。
  - ai_unmask には ops_case の USAGE と unmask_fetch の EXECUTE だけ（表には何も付けない）。
- #1 の最後で `SELECT ops_case.grant_unmask_owner();` を 1 回呼ぶ（初回のデプロイでも効くように。build_columns が前のデプロイのまま残っている前提）。

## 4-B. #2 の中身（S scripts/run_all_migrations.sh）
- :1193 の後に `run_sql migrations/<日時>_create_ops_case.sql`（上に `# ADR-1052 段2: …` の 1 行の説明）。
- trap の関数の中、ai_cloud の作成の部分（:252-262）の後、`exit "${rc}"` の前に:
  - 「>>> [final] grant ai_unmask_owner」を出す → `docker exec -e PGOPTIONS="-c statement_timeout=${AI_CLOUD_CREATE_TIMEOUT}" -i "${POSTGRES}" ${PSQL} -v VERBOSITY=terse -c 'SELECT ops_case.grant_unmask_owner();'` → 失敗したら警告「⚠️ ai_unmask_owner の権限の付け直しに失敗（値を返す口は前の権限のまま）」だけ。終了コードは変えない。
  - ai_cloud の作成が失敗した回も呼ぶ（build_columns は前のまま残るので、前と同じ表に付く。ai_cloud が無ければ unmask_fetch の 6 で断る）。
- 段1の目印（段1 カード §4-C の「変えない文字」）は全部そのまま。trap を切り出す既存の試験 3 本（S tests/sandbox/ai-ro-restore-on-failure.sh・S tests/sandbox/migration-read-probe.sh・S scripts/tests/test-deploy-orphan-cleanup.sh）が通ることを生出力で示す。read_probe の行は増やさない。C8 の眠る回の数え方が変わるなら直し、直した後の合格を示す。

## 4-C. #3 の中身（backend/app/routers/ops_case.py）
- router は `APIRouter(tags=["ops-case"])`。main.py で prefix="/api/v1"。
- 鍵: CASE_AGENT_TOKEN の口と CASE_ADMIN_TOKEN の口を別の依存関数にする（§3(f) の形）。鍵が空なら全員 401。どちらの口も、もう片方の鍵では 401。
- 件の札（相談係の口だけ）: ヘッダ X-Case-Ticket。sha256 の hex を cases.ticket_hash と compare_digest で比べ、期限内か。合わなければ 403（件が無い場合も 403。件の有無を漏らさない）。
- 口:
  | 口 | 鍵 | 中身 |
  |---|---|---|
  | POST /ops/case/{incident_id}/ticket | ADMIN | ops_incidents に件が無ければ 404。secrets.token_urlsafe(32) の札を作り、ハッシュと now()+24h を cases に入れる（あれば上書き＝前の札は使えなくなる）。札は応答で 1 回だけ返す |
  | GET /ops/case/pending | ADMIN | status='pending' の申請（理由・列・行の数・作った時刻）と、24 時間以内の decided_by='auto:limit' の行（auto_denied）。値は無い |
  | POST /ops/case/unmask-requests/{id}/decision | ADMIN | {decision: approved|denied, reason (1〜1000 字), minutes (1〜15。approved のときだけ要る)}。pending 以外は 409。approved なら expires_at = now() + minutes 分（backend が決める）。decided_by は 'agent-console' |
  | POST /ops/case/audits | ADMIN | {findings: [...]}（64KB まで）。audits に 1 行 |
  | GET /ops/case/audit-inputs | ADMIN | 期間（既定 7 日）の申請・判断・読み出しの数、ai_cloud_meta.build_log の最新の行の ok・失敗の数。数だけ |
  | POST /ops/case/{incident_id}/report | AGENT＋札 | 本文 32KB まで（超えたら 413）。reports に 1 行。2 回目は 409 |
  | POST /ops/case/{incident_id}/unmask-requests | AGENT＋札 | 下の検査を通ったら pending で 1 行。応答は id と status |
  | GET /ops/case/unmask-requests/{id} | AGENT＋札 | その件の申請だけ（別の件の札なら 403）。status・expires_at・read_count・decision_reason。値は無い |
- 申請の検査（backend が先に止める。どれも 422、上限は 409）:
  - 件の申請がすでに 2 つあれば、status='denied'・decided_by='auto:limit'・decision_reason='limit' の行を残して 409。
  - 理由 20〜1000 字・列 1〜5・行 1〜20（重複は 1 つに数える）。
  - view_name が build_columns にあり、source が 1 つに決まる。`ops_case.is_denied_source(source)` が false（関数を呼ぶ。backend に一覧を写さない）。
  - 列が全部そのビューの build_columns にあり、mode が excluded でない。
  - 元の表の主キーが 1 列（§3(e)）。
- どの口も set_operator_context の後に DB を触り、最後に _clear_operator（S ops.py:534・:568 の形）。
- 応答と記録（ログ）に札・鍵・申請の理由の全文を書かない。

## 4-D. #5 の中身（backend/app/ops/unmask_http.py）
- Starlette の小さな app（S read_window_http.py と同じ作り）。口は POST /ops/unmask/read {request_id} だけ。ほかの道は 404。
- 鍵: `Authorization: Bearer <CASE_AGENT_TOKEN>`（V5-4。環境変数の値と compare_digest。空なら全員 401）。件の札は X-Case-Ticket。どちらも無ければ 401。request_id が uuid の形でなければ 400。
- DB: psycopg2 で AI_UNMASK_DATABASE_URL に繋ぐ（`_connect` の差し替えの入口は S read_window_http.py:35-36 の形）。readonly_query.execute は使わない（読み取り専用の取引のため）。
  - autocommit を切り、`SELECT ops_case.unmask_fetch(%s, %s)` を 1 回 → `conn.commit()` → 成功してから値を返す。COMMIT が失敗したら 503 で値を返さない。関数が 42501 なら 403（理由の印だけ返す）。
- 記録: S read_window_http.py と同じ /dev/log の印に、request_id・row_count・結果の種類だけ。値・札・鍵は書かない。via は 'https-case-unmask'。
- 体の大きさは 4KB まで。

## 4-E. #6・#9 の中身（容器と deploy）
- #6: S docker-compose.ai-reader-cloud-http.yml の写し。name と -p は astro-webapp-unmask、container_name ai-unmask-http、command は `uvicorn app.ops.unmask_http:app --host 0.0.0.0 --port 8080 --workers 1 --no-access-log`、env_file は /home/ubuntu/.config/salesanchor/ai-unmask.env、environment は `CASE_AGENT_TOKEN: ${CASE_AGENT_TOKEN:-}` だけ。read_only・tmpfs /tmp・cap_drop ALL・no-new-privileges・mem_limit 128m・logging none・/dev/log・frontnet と backnet は同じ。ports は無し。上の説明の行も同じ形で書く。
- #9: :550 の後に「Start ai-unmask-http (case agent unmask read)」。S :534-550 と同じ形で、ai-unmask.env が読めなければ警告して起こさない、起こせなくても警告だけ（アプリの反映は止めない）。`docker compose -p astro-webapp-unmask -f docker-compose.ai-unmask-http.yml up -d --build=false --force-recreate`。

## 4-F. #8・#10・#11・#13 の中身（nginx と CI）
- #8 の 1: http の段（S :10 の後）に
  - `limit_req_zone $binary_remote_addr zone=case_api:10m rate=1r/s;`
  - `map $ssl_server_name $is_case_api_sni { default 0; case-api.salesanchor.jp 1; }`
- #8 の 2: 今の 443 のブロック 5 つそれぞれの server_name の直後に `if ($is_case_api_sni) { return 421; }`（上に `# ADR-1052: TLS の名前が case-api なら 421` の 1 行）。
- #8 の 3: case-api のブロック（api のブロックの後に置く）:
  - listen と TLS は S :334-344 と同じ形（listen 443 ssl・[::]:443 ssl・http2 on・ssl_protocols・ssl_ciphers・ssl_prefer_server_ciphers）。証明書は /etc/letsencrypt/live/case-api.salesanchor.jp/fullchain.pem と privkey.pem。add_header は S :348-352 と同じ 5 つ。
  - `if ($ssl_server_name != "case-api.salesanchor.jp") { return 421; }` と `if ($host != "case-api.salesanchor.jp") { return 421; }`（api の TLS で Host を case-api にした場合と、case-api の TLS で Host を替えた場合の両方を止める）。
  - `resolver 127.0.0.11 valid=5s;`（S の api のブロックと同じ）。
  - `location = /api/v1/ops/read-window/query`: S :503-520 と同じ中身で、`set $case_window ai-reader-cloud-http;`。
  - `location ~ "^/api/v1/ops/case/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/(report|unmask-requests)$"`: limit_except POST・client_max_body_size 40k・limit_req zone=case_api burst=4 nodelay・`set $case_backend backend;` で :8000 へ。
  - `location ~ "^/api/v1/ops/case/unmask-requests/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"`: limit_except GET・同じ制限で backend へ。
  - `location = /ops/unmask/read`: limit_except POST・client_max_body_size 4k・同じ制限・`set $case_unmask ai-unmask-http;` で :8080 へ。
  - どの location も proxy_set_header の 5 行と timeout は S :503-520 と同じ。落ちているときは `error_page 502 504 =503 /__case_unavailable;`（internal・503 "unavailable"）。
  - `location / { return 404; }`。
  - uuid は小文字だけ受ける（相談係は backend が返した形のまま使う）。
- #10: test.yml の detect-changes の filter と on.push.paths に `nginx/**`。
- #13 test_nginx_case_api_guard.py（ファイルを読むだけ。DB も docker も要らない）:
  - nginx.conf を server のブロックに分ける（波かっこの数で。コメントの行は外す）。
  - `listen 443` を持つブロックのうち server_name が case-api でないものの数 ＝ `if ($is_case_api_sni) { return 421; }` を持つブロックの数。食い違えば落とす。
  - map の行がちょうど 1 つ・case-api のブロックがちょうど 1 つで、ssl_server_name と host の 421 の 2 行を持つ。
  - case-api のブロックの location が上の 5 つ（read-window・case の 2 つ・unmask・`/`）と内部の 1 つだけ。pending・ticket・decision・audits・audit-inputs の文字を含む location が無い。
  - 数え合わせの関数に、421 の行を 1 つ消した文字列を渡すと落ちることを試験に入れる（T7 の CI 側）。
- #11 nginx-config-check.yml（pull_request と push。paths は nginx/**・docker-compose.yml・自分自身）:
  - docker-compose.yml の nginx のイメージ（S :6 の nginx:1.31.1）で `nginx -t`。
  - S nginx/nginx.conf の ssl_certificate の名前ごとに自己署名の証明書を一時の場所に作り、/etc/letsencrypt に読み込ませる。変数を通さない proxy_pass の宛先は --add-host で 127.0.0.1 にする（§3(h) で数えた数と合わせる）。htpasswd.d など読む物は空の物を置く。
  - 落ちたら PR が赤くなる（必須の Check にするかは PO の判断。段2では GO の条件に入れる）。

## 4-G. 試験（#12・#14）
- #12（S backend/tests/ops/test_ai_cloud_views.py と同じ作り。使い捨ての DB に本物の migration を流し、SET ROLE で測る。試験 DB に tenant_* が無ければ作る。作れなければ skip でなく落とす）:
  - T2: 申請が pending・denied のまま unmask_fetch → 42501。unmask_reads が増えない。
  - T3: 別の件の札・期限を過ぎた札 → 42501。
  - T4: expires_at を過去にした approved（status を expired に変える処理を止めた形のまま）→ 42501。
  - T5: 許可にない列（申請の列に無い列を直接 view_name に足した行を作る）・mode='excluded' の列・deny_tables の表・主キーが 2 列の表 → 42501。許可済みの行でも同じ。
  - T6: ai_unmask で public の表・tenant の表・ops_case の 5 表・ai_cloud_meta.build_columns を直接 SELECT → 42501。ai_reader・ai_reader_cloud・salesanchor_app・PUBLIC から unmask_fetch と grant_unmask_owner を実行 → 42501。ai_unmask_owner の SELECT が deny_tables の表に付いていない（has_table_privilege が f）。
  - T6c: tenant の表の行を許可して unmask_fetch → 行が返る（0 件でない）。COMMIT の後、別の接続で unmask_reads が 1 増え、read_count=1。
  - T6b: 2 回目 → 42501。同時に 2 本（2 つの接続で、1 本目の COMMIT の前に 2 本目を始める）→ 1 本だけ値が返り、read_count=1・unmask_reads 1 行。
  - ロール: ai_unmask_owner と ai_unmask の属性。属性違いの同名ロールがある状態で #1 を流すと止まる。ai_unmask の rolconfig に log_statement=none があり、default_transaction_read_only が無い。
  - is_denied_source: deny_tables の名前・excluded の列を持つ表で true、ふつうの表で false。
- #14:
  - test_unmask_http.py（Starlette の TestClient。`_connect` を差し替える）: 鍵なし・Bearer なし・違う鍵・札なしは 401。鍵が空なら全部 401。request_id が uuid でなければ 400。ほかの道は 404。関数が 42501 なら 403 で値なし。COMMIT を失敗させると 503 で値なし（T6c の COMMIT 失敗の回）。成功したら値を返し、/dev/log の印に値・札・鍵が入らない。
  - test_ops_case_router.py: 2 つの鍵の取り違えで 401。札の違い・件の違い・期限切れで 403。報告の 2 回目は 409、32KB を超えたら 413。申請の 3 回目は 409 で auto:limit の行が残る。理由 19 字・列 6・行 21・excluded の列・拒否表・主キー 2 列は 422。decision の minutes 16 は 422、pending 以外は 409、expires_at は backend の時刻から決まる。

## 4. GO と承認・PO の操作
- #1〜#11 は危険パス（migrations・本番 scripts・deploy.yml・backend/app/ops・nginx）→ ADR-136 の委任 GO（POの委任に基づくClaude Opus発行）。release ブランチで待ち、GO の前にマージしない。GO の条件: CI 緑（#11 を含む）・reviewer（opus）APPROVE・PR 本文の相乗り確認・証明書のファイルの再確認（§3(済)）。
- secrets 変更 → PO 本人の GO・置くのは PO の `!`（値は画面に出さない）。台本は Opus が書き、/security-review を通す:
  - GitHub secret CASE_ADMIN_TOKEN（段1の CASE_AGENT_TOKEN の台本と同じ形。値は手元で作り、agent-console の Keychain にも同じ値を入れる）。
  - ai_unmask のパスワードと ai-unmask.env（段1の ai_reader_cloud の台本と同じ形。VPS の上で作り、ALTER ROLE と env の書き込みを 1 本で。接続の変数名は AI_UNMASK_DATABASE_URL。権限 600）。
- 反映の順: PR マージ → デプロイ（ops_case・ロール・nginx の case-api。容器は env が無いので起きない）→ PO の `!` で secret・パスワード・env → 次のデプロイで容器が起きる。

## 5. 受入（○×）
| 基準 | 検証方法 |
|---|---|
| T2〜T6c・ロール・is_denied_source | CI の #12 が緑 |
| 口の決まり | CI の #14 が緑 |
| T7（CI 側）・文法 | #13 と #11 が緑。421 の行を 1 つ消すと #13 が落ちる試験がある |
| nginx が止まらない | デプロイの「Recreate nginx」の後、app・api・monitor・salesanchor.jp・jarvis-claude.uk の 5 つの入口が今と同じ応答（デプロイ前に同じ curl で基準値を取る） |
| T7（本番の通し） | 手元の curl で: case-api の TLS で Host を 5 つの名前にそれぞれ替える → 5 つとも 421。api の TLS（`--connect-to`）で Host を case-api → 421。case-api の `/`・`/api/v1/auth/login`・`/api/v1/ops/case/pending`・ticket・decision・audits・audit-inputs・uuid でない {id} → 404。case-api の 3 つの道に鍵なしで送る → 401（容器が起きる前の /ops/unmask/read は 503） |
| 管理の口は api だけ | api.salesanchor.jp の /api/v1/ops/case/pending に鍵なし → 401（404 でない＝届いている） |
| DB の権限（本番） | ai_reader で: `has_function_privilege('ai_unmask','ops_case.unmask_fetch(uuid,text)','EXECUTE')` が t、ai_reader・ai_reader_cloud・salesanchor_app は f。pg_roles の 2 つのロールの属性が §4-A のとおり。pg_proc の unmask_fetch の持ち主が ai_unmask_owner・prosecdef=t・proconfig に search_path。deny_tables の 10 表で `has_table_privilege('ai_unmask_owner', 表, 'SELECT')` が f |
| 相談係の窓口の通し（段1の残り。T10b・T13・T14） | 容器が起きた後、PO の `!` の台本（VPS の .env の値を画面に出さずに使う）で、case-api の read-window に Bearer 付き → 200 で 1 文読める・Bearer なし → 401・ai_ro を読む文 → 400 か 42501。記録の印が via=https-case |
| ai-unmask-http が起きる | env を置いた後のデプロイで、ai-unmask-http が running。case-api の /ops/unmask/read に鍵だけ・札なし → 401 |

- 段2では本番で値を 1 件も読まない（許可の行を作る道は段4の agent-console）。値を返す通しは CI の T6c・T6b で測る。

## 6. 戻し方
- 値を返す口を止める: GitHub secret CASE_AGENT_TOKEN を消してデプロイ（相談係の 3 つの道が全部 401。設計 §9（３））。PO の `!` で `ALTER ROLE ai_unmask NOLOGIN`。
- 容器を止める: #9 の手順を外してデプロイし、PO の `!` で容器を止める。
- case-api の入口を外す: #8 の case-api のブロックを外す PR（421 の行と map は残してよい。外しても他の名前の応答は変わらない）。
- ops_case の表・ロール・関数は残っても届く人がいない。消すのは PO の判断。
- nginx の作り直しで入口が止まった場合: 直前のマージを戻す PR を EMERGENCY の手順（S docs/BRANCH_PROTECTION_SETUP.md §4）で出す。
