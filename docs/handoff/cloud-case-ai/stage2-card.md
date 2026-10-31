# 段2 実装カード（設計第4.6版の追補・第6版）

- 対象: docs/handoff/cloud-case-ai/design.md 第4.6版 §4-2・§4-3・§7（T2〜T6c・T7）・§9 の段2。ADR-1052（Accepted）。
- 根拠の写し: S=origin/main 8c6f52813（Merge #4942）。行番号はすべてこの sha。実装の前に最新の origin/main で行を合わせ直す（§3(a)）。
- 前提（済み）: 段1 本番反映・受入合格（#4932・#4940）。case-api.salesanchor.jp はさくらの DNS に登録済み、証明書は 2026-10-31 16:46 に取得（期限 2027-01-29。PO の `!`）。
- 状態: 第6版（第1版〜第5版の審査 REVISE を受けた直し。§0-2〜§0-6）。第6版の審査は APPROVE（LOW 1 件＝「good が無いのは初回だけ」の書き方。この版で直し済み）。

## 0. 設計からの直し（V5。どれも事実に合わせる直しで、守りの強さは変えない）
- V5-1 DNS: 設計 §4-3（design.md:179）・§4-4（:210）の「Cloudflare・グレー雲」は事実と違う。case-api の名前はさくらの DNS（ns1/ns2.dns.ne.jp）にあり、プロキシは無い。SNI はそのまま nginx に届く（守りの前提は満たす）。design.md の 2 行をこのカードと同じ PR で直す。プロキシを入れる場合に守りを作り直す約束は残す。
- V5-2 421 の守りの書き方: 設計 §4-3（:176）の `include snippets/case-api-sni-guard.conf` は採れない。nginx の容器は S nginx/nginx.conf 1 つだけを /etc/nginx/conf.d/default.conf として読む（S docker-compose.yml:11。VPS の実物でも同じ）。nginx/snippets/ は無い。include のために本体の compose を変えると、ほかの名前の入口まで巻き込む。
  - 代わり: S nginx/nginx.conf の先頭（http の段。S :6-10 の limit_req_zone と同じ段）に `map $ssl_server_name $is_case_api_sni` を 1 つ置く（§4-F）。今の 443 のブロック 5 つそれぞれに `if ($is_case_api_sni) { return 421; }` を 1 行置く。
  - 判定の正本は map の 1 か所（名前を書くのはそこだけ。case-api のブロックの中の SNI の判定も同じ変数を使う）。
- V5-3 CI の検査: CI に nginx の検査の仕事は無い（S .github/workflows/ に nginx -t を走らせる仕事が無い）。
  - 新しい仕事 nginx-config-check.yml を 1 つ作り、文法の検査（nginx -t）・数え合わせ（#13）・本物の nginx を起こした守りの試験（421・404・400）をそこで行う（§4-F）。paths で絞らず毎回走らせる（§4-F の #11）。test.yml は触らない。
- V5-4 鍵の持たせ方: 設計 §4-3（:146）の「CASE_AGENT_TOKEN（の照合用ハッシュ）」は採らない。ai-unmask-http には ai-reader-cloud-http（S docker-compose.ai-reader-cloud-http.yml:31）と同じく値そのものを渡し、hmac.compare_digest で比べる。
  - 理由: 値はすでに VPS の .env に書かれている（S .github/workflows/deploy.yml:378）。容器だけハッシュにしても、同じ機械の .env に値が残るので守りは増えない。ハッシュを作る手順を deploy に足すと、手順が 1 つ増えて壊れる所が増える。
- V5-5 秘密列と拒否表の正本: 設計の「列が DENY_COLUMN_RE に当たらない」は、正規表現を写さず、段1の ai_cloud_meta.build_columns の mode を正本にする。
  - mode='excluded' は「deny に当たって外した列」（段1 カード §4-A）。同じ正規表現を backend と関数に写すと、正本が 3 か所に分かれる。
  - 拒否表は新しい表 ops_case.deny_tables の 1 か所に書く（§4-A）。加えて、build_columns に mode='excluded' の列を 1 つでも持つ表（＝秘密列を持つ表）は、表ごと拒否する。
  - 同じ判定を関数 ops_case.is_denied_source(source text) 1 つにまとめる。backend の申請の受付・unmask_fetch・持ち主の権限付け（grant_unmask_owner）の 3 か所はこの関数だけを呼ぶ。
- V5-6 ai_unmask の記録の設定: 段1のロールは log_statement='all'。ai_unmask は文を DB の記録に一切残さない設定にする（§4-A のロール。log_statement='none'・log_min_error_statement='panic'・log_min_duration_statement=-1 の 3 つ）。
  - 理由: 呼び出しの文に件の札がそのまま入る。log_statement だけでは、関数が断った（エラーの）回に log_min_error_statement の既定 ERROR で文が記録に出る（PostgreSQL 16 公式文書 runtime-config-logging）。読んだ記録は同じ取引で unmask_reads に残る（§4-A）。返した値は、どの設定でも DB の記録に出ない。
- V5-7 3回目の申請: 「自動で断り、PO に知らせる」は、段2では status='denied'・decided_by='auto:limit' の行を残し、409 を返すところまで。知らせるのは段4（agent-console が GET /ops/case/pending の auto_denied を読む）。

## 0-2. 第1版の審査（REVISE・HIGH 1・MEDIUM 4・LOW 15）への対応
| 指摘 | 対応（場所） |
|---|---|
| HIGH-1 証明書の道があいまい・nginx の作り直しの前に本番の取り付けで nginx -t が無い | 道をホスト側の絶対パスに直す（§3(済)）。deploy の nginx の作り直しの前に本番と同じ取り付けで nginx -t、通らなければ作り直さずデプロイを失敗に。作り直しの後に起きているかと 443 の応答を確かめ、だめなら直前の nginx.conf に自動で戻す（#9・§4-E）。§5・§6 に入れる |
| MEDIUM-1 断った回に札入りの文が記録に出る | ai_unmask に log_min_error_statement='panic'・log_min_duration_statement=-1 を足し、試験で rolconfig を確かめる（V5-6・§4-A・§4-G） |
| MEDIUM-2 SNI の末尾の点 | map のキーを `~*^case-api\.salesanchor\.jp\.?$` にする。case-api のブロックの SNI の判定も同じ変数。末尾に点を付けた SNI の試験を CI の本物の nginx で行う（§4-F） |
| MEDIUM-3 42501 以外の失敗の扱いが無い | 行のキーの形は backend が主キーの型ごとに先に確かめる（受ける型は 3 種）。関数の中の読み出しのエラーは全部 42501 'read_failed' に変える。42501 以外の DB の失敗は、中身なしの 503 で返し、記録には SQLSTATE だけ（§4-A・§4-C・§4-D・§4-G） |
| MEDIUM-4 毎回の権限の付け直しのロックと時間 | 今の権限と比べて違う表だけ GRANT・REVOKE。関数に lock_timeout='2s'。CI で所要時間を測り 5 秒以内、trap は所要時間を出す（§4-A・§4-B・§5） |
| L1〜L4 | 申請と件の結び付け・source の解き方・backend の UPDATE の列・数え方の取り合い（§4-A・§4-C） |
| L5 | 2 つの鍵が同じ値なら両方の口を 401（§4-C） |
| L6・L7 | tenant_carrier_credentials は public（§3(d)）。read-window の location は S :502-519・`__rw_unavailable` は :521（§4-F） |
| L8 | 数え合わせは `listen 443` と `listen [::]:443` の両方、server のブロックだけ（§4-F） |
| L9 | case-api のブロックで $request_uri に `%2e`・`%2f`・`..`・`//` があれば 400（§4-F） |
| L10・L11 | #13 は nginx-config-check.yml で走らせる。paths で絞らない（V5-3） |
| L12 | 「同じ応答」は応答コードと Location の一致。IPv4 と IPv6 は CI の本物の nginx で両方試す（§4-F・§5） |
| L13 | 本物のクラウドからの T7 は段3（§5 の下） |
| L14 | #12 の前提と後片付け（§4-G） |
| L15 | trap を切り出す既存の試験 3 本の合格を受入に入れる（§5） |

## 0-3. 第2版の審査（REVISE・MEDIUM 2・LOW 9）への対応
| 指摘 | 対応（場所） |
|---|---|
| N1 前の点検で `exit 1` すると後ろの Bootstrap・移行・smoke が飛び、新しい backend と古い DB のまま残る | 審査の案 (a) を採る。nginx の手順に `continue-on-error: true` を付け、点検に通らなければ作り直さずに失敗で終える（後ろの手順はそのまま流れる）。Finalize の後に「nginx の手順が失敗なら止める」手順を 1 つ足し、デプロイ全体を失敗の表示にする（§4-E・§6・§5） |
| N2 戻す手順そのものが失敗すると nginx が止まったままになる | 作り直しの前に、戻り先の nginx.conf を git から別のファイルに書き出し、空でないことを確かめる。書き出せなければ作り直さない。戻す部分は `set +e` で囲み、どこで失敗しても作り直しと確認まで進む（§4-E・§6） |
| L-N1 has_table_privilege は PUBLIC への付与も数える | 今付いている表は `aclexplode(relacl)` で grantee が ai_unmask_owner のものだけ数える。本番の受入でも PUBLIC の SELECT が無いことを見る（§4-A・§5） |
| L-N2 is_denied_source の EXECUTE | PUBLIC から REVOKE し、salesanchor_app と ai_unmask_owner に GRANT する（§4-A） |
| L-N3 statement_timeout（57014）は WHEN OTHERS で捕まらない | 書き方を事実に合わせ、57014 は 503 になる試験を足す（§4-A・§4-G） |
| L-N4 users は migrations に CREATE が無い | migrations と backend/app/models.py の両方を数える。0 件でも行は残す（§3(d)） |
| L-N5 GitHub のランナーで ::1 が使えるか | §3(l) の分かれ道にする |
| L-N6 openssl が末尾の点をそのまま送るか | CI で、送られた SNI をそのまま返す試験専用の nginx を別に起こし、届いた名前を確かめてから本番の設定に当てる（§4-F） |
| L-N7 design.md:366 の CI の置き場 | このカードの PR で design.md を直す（§1 の #15） |
| L-N8 CI の「同じ応答」は中継する名前では意味が薄い | 書き添える（§4-F） |
| L-N9 戻すのは nginx.conf だけ | §6 に 1 行足す |

## 0-4. 第3版の審査（REVISE・HIGH 1・MEDIUM 2・LOW 4）への対応
| 指摘 | 対応（場所） |
|---|---|
| H1 点検で止まって失敗の表示になると、S :1106「Emergency block /design/」が点検に落ちた設定で nginx を作り直し、全部の入口が止まる | 両側で守る。(b) nginx の手順で点検に落ちたら、作業の写しを戻り先の設定に替えてから止める。(a) Emergency の手順を変え、作り直しの前に nginx -t を通し、通らなければ作り直さない（§1 #9・§4-E の 1 の 3 と 1c・§3(k)・§5） |
| M1 `set -e` のため、作り直しや確認の途中の失敗で戻す部分まで届かない | 作り直し・後の確認・戻すをまとめて `set +e` で囲む（Finalize の health check と同じ形）。compose up が 0 でない回・curl が 000 の回を受入に足す（§4-E の 1 の 4〜6・§5 ④） |
| M2 戻り先がひとつ前の記録の設定なので、前の回に点検で落ちた壊れた設定に戻ることがある | 後の確認まで通った設定を `.deploy_nginx_good.conf` に残し、それを戻り先にする。無いときだけひとつ前の記録から書き出す。作り直しの前に戻り先も nginx -t を通す（§4-E の 1 の 1・2・5・§3(m)(n)・§5 ⑤⑥・§6） |
| L1 salesanchor_app に ops_case のスキーマの USAGE が無い | 付ける。#11 に SELECT と is_denied_source の試験を足す（§4-A・§5） |
| L2 S :1124 は失敗の知らせを送らない（記録に出すだけ） | 書き方を事実に合わせる。PO と Opus への知らせは段4（§4-E の 1b） |
| L3 `.deploy_prev_sha` が無いと `cat` が 0 でなく `set -e` で理由を出さずに止まる | `|| true` を付け、空なら理由の印を出して止める（§4-E の 1 の 1） |
| L4 題と状態の行が古い | 第4版に直す（冒頭） |

## 0-5. 第4版の審査（REVISE・MEDIUM 1・LOW 2）への対応
| 指摘 | 対応（場所） |
|---|---|
| M1 1c は作業の写しの設定で作り直すが、その設定は nginx -t しか通っていない回がある | 審査の案 (a) を採る。1c は good があれば作業の写しを good に替えてから点検し、作り直す。good が無いのは、この形の初回と、good の書き出しに失敗して消した後（第6版の審査 L1）。受入の ② を点検に落ちる回と通る回に分け、⑦ を足す（§4-E の 1c・§5） |
| L1' salesanchor_app の権限の試験が #11 の中身に無い | §4-G の #11 に足す |
| L2 good の書き出しの失敗が黙って通り、切れた good が残りうる | tmp に書いてから mv し、失敗したら警告を出す。受入に ⑧ を足す（§4-E の 1 の 5・§5） |

## 0-6. 第5版の審査（REVISE・MEDIUM 1・LOW 2）への対応
| 指摘 | 対応（場所） |
|---|---|
| M1 受入 ⑦ の前提（good があって手順 1・2 で止める）は起こせず、直しが効く本当の回が受入に無い | ⑦ を「nginx の手順が飛んだ回」と「Finalize の自動ロールバックの後」の 2 つに替え、1c の説明も直す（§4-E の 1c・§5） |
| L1 good の書き出しに失敗すると、動いている設定より古い good が残り、後で 1c がそれで作り直す | 失敗したら good と tmp を消す。⑧ の期待を「good が無い」に直す（§4-E の 1 の 5・§5） |
| L2 §1 の #9 の行が 1c の新しい形を書いていない | 書き足す（§1 #9） |

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 今（S） | 変える形 |
|---|---|---|---|
| 1 | 新 migrations/<日時>_create_ops_case.sql（一覧に載せる） | 無し | §4-A。スキーマ ops_case・表 6 つ・ロール 2 つ・関数 3 つ。冪等 |
| 2 | S scripts/run_all_migrations.sh | 一覧の末尾は :1193 の 20261024_100100_create_ai_reader_cloud_role.sql。trap の ai_cloud の作成は :252-262、`exit "${rc}"` は :263 | :1193 の後に #1 を足す。trap の ai_cloud の作成の後（:262 の後、:263 の前）に持ち主の権限の付け直しを足す（§4-B） |
| 3 | 新 backend/app/routers/ops_case.py | 無し | §4-C の口 8 つ |
| 4 | S backend/app/main.py | :74-75 で import、:777・:780 で include_router(prefix="/api/v1") | ops_case を同じ形で import と include_router |
| 5 | 新 backend/app/ops/unmask_http.py | 無し | §4-D。S backend/app/ops/read_window_http.py の形（app.* の import は最小） |
| 6 | 新 docker-compose.ai-unmask-http.yml | 無し | S docker-compose.ai-reader-cloud-http.yml の写し（§4-E） |
| 7 | S docker-compose.yml | backend の environment :135-144 に OPS_API_TOKEN・OPS_INGEST_TOKEN・ERROR_REPORT_AGENT_TOKEN | 同じ所に `CASE_AGENT_TOKEN=${CASE_AGENT_TOKEN:-}`・`CASE_ADMIN_TOKEN=${CASE_ADMIN_TOKEN:-}` の 2 行 |
| 8 | S nginx/nginx.conf | 667 行。443 のブロックは jarvis :32-33・app :70-73・api :334-337・monitor :570-573・salesanchor.jp :624-627 | §4-F（map 1 つ・limit_req_zone 1 つ・421 の行 5 つ・case-api のブロック 1 つ） |
| 9 | S .github/workflows/deploy.yml | :325 の sed で CASE_AGENT_TOKEN 行を消す。:378 で書く。:499-514「Recreate nginx」は作り直して状態を出すだけ。:534-550 で ai-reader-cloud-http を起こす | :325 の sed に `-e '/^CASE_ADMIN_TOKEN=/d'`。:378 の次に `CASE_ADMIN_TOKEN='${{ secrets.CASE_ADMIN_TOKEN }}'`。:499-514 を §4-E の形（id と continue-on-error・前の点検・後の確認・自動で戻す）に。Finalize（:723）の後・Verify（:870）の前に「nginx の手順が失敗なら止める」手順を足す。:1106-1122「Emergency block /design/」を、good があれば作業の写しを good に替える → nginx -t → 通れば作り直して確認の結果を記録に出す、通らなければ作り直さず警告、の形にする（§4-E の 1c）。:550 の後に「Start ai-unmask-http」（§4-E） |
| 10 | 新 .github/workflows/nginx-config-check.yml | 無し | §4-F の #11 |
| 11 | 新 backend/tests/ops/test_ops_case_db.py | 無し | T2〜T6c の DB 側（§4-G） |
| 12 | 新 backend/tests/ops/test_nginx_case_api_guard.py | 無し | §4-F の #13 の数え合わせ（#10 の仕事から走らせる） |
| 13 | 新 backend/tests/ops/test_unmask_http.py・新 backend/tests/test_ops_case_router.py | 無し | §4-G |
| 14 | 新 scripts/tests/nginx-case-api-guard.sh | 無し | §4-F。#10 の仕事が本物の nginx に curl と openssl で当てる台本 |
| 15 | docs/handoff/cloud-case-ai/design.md | :176-177・:179・:210・:146・:366 | V5-1〜V5-4 と V5-3（:366 の CI の置き場）に合わせる（このカードの PR で直す。実装の PR では触らない） |

## 2. 触らない範囲
- 段1の部品（ai_cloud・ai_cloud_meta の表と build_views・ai_reader_cloud・ai-reader-cloud-http・read_window_http.py）。build_columns の中身の作り方も変えない。
- 今の窓口（ai_ro・ai_reader・ai-reader-http）と、api.salesanchor.jp の今の location。
- 既存の POST /ops/incidents/human（S backend/app/routers/ops.py:524-569。件を作る口はこのまま使う）。
- .github/workflows/test.yml（V5-3）。
- クラウドの設定（段3）・agent-console（段4）。
- nginx の 80 番のブロック（case-api の 80 番は今の jarvis の既定のブロックに当たり、証明書の更新の道 /.well-known/acme-challenge/ はそこで通る。S nginx/nginx.conf:13-26）。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 行の合わせ直し: §1 の行番号を最新の origin/main で引き直す。migration の一覧の末尾が :1193 より後ろに伸びていれば、その後ろに #1 を足す。trap の形・「Recreate nginx」の形が S と違えば止めて Opus へ。
- (b) 試験 DB の jarvis: CI の試験 DB で migration を流すロールが superuser か（CREATE ROLE … BYPASSRLS・ALTER FUNCTION … OWNER・ALTER ROLE … SET log_min_error_statement に要る。本番の jarvis は rolsuper=t・rolbypassrls=t。ADR-1024:18）。違えば止めて Opus へ。
- (c) 登録の検査: S scripts/check-migration-registration-exists.sh と S .github/workflows/migration-guard.yml:119-132 が #1 を通すか（一覧に載せるので逃がしは要らない見込み）。落ちたら止めて Opus へ。
- (d) 拒否表の名前: 次の表が origin/main の migration か backend/app/models.py（`__tablename__`）に実在するかを数える（users は migrations に CREATE が無く、models.py:23 にある）。0 件の名前があっても一覧から外さず、数を報告に書く。users・viewer_accounts・auth_events・auth_refresh_tokens・password_reset_tokens・registration_tokens・viewer_login_events・viewer_login_tokens・webauthn_credentials・tenant_carrier_credentials（どれも public。tenant_carrier_credentials は S migrations/20260608_080000_add_carrier_credentials.sql:14 でスキーマ無しの CREATE）。ほかに認証・合言葉・鍵の表（名前に auth・login・session・passkey・webauthn・credential・otp・totp・mfa・reset・token・password を含む表）があれば一覧に足す候補として止めて Opus へ（勝手に足さない・勝手に減らさない）。
- (e) 主キー: ai_cloud に載る表のうち、主キーが 1 列でない表・主キーが無い表・主キーの型が integer・bigint・smallint・uuid・text・character varying のどれでもない表を数える。それらは申請を受けない（申請の受付で 422。関数でも断る）。数を報告に書く。
- (f) 鍵の口の前例: S backend/app/routers/ops_error_reports.py:65-87 の専用鍵の Bearer の作り（空の鍵なら全員 401・compare_digest）を CASE_AGENT_TOKEN と CASE_ADMIN_TOKEN の 2 つに写す。形が違えば止めて Opus へ。
- (g) 操作の記録の文脈: ops_case の表の RLS は ops_incidents と同じ形にする（S migrations/20261016_100000_create_ops_incident_tables.sql の ENABLE＋FORCE・`current_setting('app.is_operator', true) = 'true'` の方針・salesanchor_app の権限の付け方と DELETE・TRUNCATE の REVOKE）。router は S backend/app/auth/dependencies.py:482 の set_operator_context と ops.py の _clear_operator を使う。
- (h) nginx の材料: S nginx/nginx.conf の変数を通さない proxy_pass の宛先は IP だけ（:235・:252・:265・:589 の 49.212.160.98）で、名前の解決は要らない。ssl_certificate の道は 5 つ（:35-36・:75-76・:339-340・:575-576・:629-630）＋ case-api の 1 つ。最新の origin/main でこの数が違えば、#11 の偽の証明書の数を合わせる。読む物（htpasswd.d・/var/www の各所）を全部数える。
- (i) 容器のイメージ: ai-unmask-http も astro-webapp-backend を使う（S docker-compose.ai-reader-cloud-http.yml:15）。psycopg2 がイメージに入っているか（S backend/app/ops/readonly_query.py:280-289 が使っている）。
- (j) nginx の前の点検の形: `docker compose run --rm --no-deps -T nginx nginx -t` が、compose の nginx の取り付け（S docker-compose.yml:11-19）と networks（frontnet）をそのまま使い、ports を開かないこと（docker compose の公式文書 `run` の項。--service-ports を付けない限り ports は開かない）。Context7 か公式文書で確かめ、違えば止めて Opus へ。
- (k) 失敗を後ろへ送る形: GitHub Actions で `continue-on-error: true` の手順が失敗したとき、`steps.<id>.outcome` が failure・`conclusion` が success になり、後ろの `success()` の手順が動くこと（公式文書の steps の文脈の項）。違えば止めて Opus へ。あわせて、`continue-on-error` で落ちた手順の後でも、後ろの `failure()` の手順（S :1106・:1124）が動かず、1b が `exit 1` してから動くことを確かめる（公式文書の expressions の項には continue-on-error との関係が書かれていない。偽の流れで 1 回試して生出力を出す）。
- (l) CI の IPv6: GitHub のランナーで `--network host` の nginx が [::]:443 で待ち受け、::1 に届くか。最初に 1 回だけ試し、届かなければ止めて Opus へ（IPv6 の試験を外すかは Opus が決める）。
- (m) 戻り先の点検の形: `docker compose run --rm --no-deps -T -v /home/ubuntu/salesanchor/.deploy_prev_nginx.conf:/etc/nginx/conf.d/default.conf:ro nginx nginx -t` で、サービスの取り付け（S docker-compose.yml:11）が同じ道の -v で置き換わるかを docker compose の公式文書と sandbox で確かめる。置き換わらない・重なりでエラーなら、`-v …:/tmp/candidate.conf:ro` と `--entrypoint sh` で、`/etc/nginx/nginx.conf` の `include /etc/nginx/conf.d/*.conf;` を `/tmp/candidate.conf` に替えた写しを /tmp に作り `nginx -t -c` で試す形にする。どちらも動かなければ止めて Opus へ。
- (n) 置くファイル: `.deploy_nginx_good.conf` と `.deploy_prev_nginx.conf` が、S deploy.yml の `git reset --hard`（:258・:765）で消えないこと（追跡していないファイルは reset で消えない）。deploy.yml に `git clean` が無いことを数える。あれば止めて Opus へ。
- (済) 証明書: 2026-10-31 16:46 に PO の `!` で取得済み（certbot の webroot・今の名前と同じ形）。ホスト側の道は /home/ubuntu/salesanchor/certbot/conf/live/case-api.salesanchor.jp/（容器の中では S docker-compose.yml:19 の取り付けで /etc/letsencrypt/live/case-api.salesanchor.jp/。S docs/PHASE5_DOMAIN_CUTOVER_RUNBOOK.md:29）。マージの直前に Opus が PO の `!` の確認台本で、ホスト側の fullchain.pem と privkey.pem があることを ls でもう一度確かめる（中身は読まない。§4）。

## 4-A. #1 の中身（migrations/<日時>_create_ops_case.sql）
- `CREATE SCHEMA IF NOT EXISTS ops_case;` `REVOKE ALL ON SCHEMA ops_case FROM PUBLIC;`
- 表（どれも `CREATE TABLE IF NOT EXISTS`）:
  - cases: incident_id uuid PRIMARY KEY REFERENCES public.ops_incidents(id)・ticket_hash text・ticket_expires_at timestamptz・created_at timestamptz NOT NULL DEFAULT now()。ticket_hash は `^[0-9a-f]{64}$`。
  - reports: id uuid PK DEFAULT gen_random_uuid()・incident_id uuid NOT NULL UNIQUE REFERENCES ops_case.cases(incident_id)（2 回目は一意制約で 409）・status text CHECK IN ('investigating','reported')・summary text・cause text・evidence jsonb・proposal jsonb・risk text・needs_decision text・received_at timestamptz NOT NULL DEFAULT now()。本文の 32KB の上限は backend で測る（§4-C）。
  - unmask_requests: id uuid PK DEFAULT gen_random_uuid()・incident_id uuid NOT NULL REFERENCES ops_case.cases(incident_id)・view_name text NOT NULL・column_names text[] NOT NULL CHECK (cardinality BETWEEN 1 AND 5)・row_keys text[] NOT NULL CHECK (cardinality BETWEEN 1 AND 20)・reason text NOT NULL CHECK (char_length BETWEEN 20 AND 1000)・status text NOT NULL DEFAULT 'pending' CHECK IN ('pending','approved','denied','expired')・decided_by text・decision_reason text・approved_minutes integer CHECK (approved_minutes BETWEEN 1 AND 15)・expires_at timestamptz・max_reads integer NOT NULL DEFAULT 1 CHECK (max_reads = 1)・read_count integer NOT NULL DEFAULT 0 CHECK (read_count >= 0 AND read_count <= max_reads)・created_at timestamptz NOT NULL DEFAULT now()。CHECK (status <> 'approved' OR (approved_minutes IS NOT NULL AND expires_at IS NOT NULL))。
  - unmask_reads: id bigserial PK・request_id uuid NOT NULL REFERENCES ops_case.unmask_requests(id)・read_at timestamptz NOT NULL DEFAULT now()・row_count integer NOT NULL・column_names text[] NOT NULL。値の列は持たない。
  - audits: id bigserial PK・ran_at timestamptz NOT NULL DEFAULT now()・findings jsonb NOT NULL・finding_count integer NOT NULL。
  - deny_tables: table_name text PRIMARY KEY・reason text NOT NULL。中身は §3(d) の 10 行（表の名前だけ。スキーマは問わず、public でも tenant_* でも同じ名前なら拒否）。`TRUNCATE` してから `INSERT`（ファイルが正本。段1の column_class と同じ）。
- RLS と backend の権限: cases・reports・unmask_requests・unmask_reads・audits は ops_incidents と同じ形（§3(g)）。salesanchor_app には次だけ。DELETE・TRUNCATE は REVOKE。
  - ops_case のスキーマの USAGE（前例の ops_incidents は public にあるので写せる前例が無い。付けないと backend の口がどれも表と is_denied_source に届かない）。
  - cases: SELECT・INSERT・UPDATE。reports: SELECT・INSERT。unmask_reads: SELECT。audits: SELECT・INSERT。deny_tables: SELECT。
  - unmask_requests: SELECT・INSERT と、列を絞った `UPDATE (status, decided_by, decision_reason, approved_minutes, expires_at)`（read_count は backend から変えられない。FOR UPDATE は 1 列以上の UPDATE 権限で足りる。PostgreSQL 16 公式文書 SELECT の「The Locking Clause」）。
  - ai_cloud_meta の USAGE と build_columns の SELECT（申請の受付で列を確かめるため。中身は名前だけで値は無い）。is_denied_source の EXECUTE（is_denied_source は PUBLIC から REVOKE し、salesanchor_app と ai_unmask_owner にだけ GRANT する。unmask_fetch の中から呼ぶため持ち主にも要る）。
- ロール（段1の S migrations/20261024_100100_create_ai_reader_cloud_role.sql の DO の形。属性が違えば RAISE EXCEPTION）:
  - ai_unmask_owner: NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION BYPASSRLS。
  - ai_unmask: LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2。パスワードは付けない（§4 の PO の `!`）。
    - `ALTER ROLE ai_unmask SET` で log_statement='none'・log_min_error_statement='panic'・log_min_duration_statement=-1（V5-6）・statement_timeout='10s'・idle_in_transaction_session_timeout='30s'。
    - default_transaction_read_only は付けない（書ける取引が要る）。
- 関数 ops_case.is_denied_source(p_source text) RETURNS boolean（SECURITY INVOKER・STABLE・`SET search_path = pg_catalog, pg_temp`）:
  - p_source は build_columns.source の文字（段1 の作り方 `sch || '.' || rel`、引用符なし。S migrations/20261024_100000_create_ai_cloud_meta.sql）。
  - 文字を割って名前を取り出さない。`pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname || '.' || c.relname = p_source AND c.relkind IN ('r','p')` で 1 つの表に解く。解けない・2 つ以上なら true（断る側）。
  - 表の名前（c.relname）が deny_tables にある、または build_columns に source=p_source かつ mode='excluded' の行がある、なら true。
- 関数 ops_case.unmask_fetch(p_request_id uuid, p_ticket text) RETURNS jsonb:
  - SECURITY DEFINER・`SET search_path = pg_catalog, pg_temp`・`SET lock_timeout = '2s'`・持ち主 ai_unmask_owner（`ALTER FUNCTION … OWNER TO ai_unmask_owner`）・`REVOKE ALL ON FUNCTION … FROM PUBLIC`・`GRANT EXECUTE … TO ai_unmask`。
  - 中の名前はすべてスキーマ付きで書く（search_path に頼らない）。
  - 確かめる順（どれかが合わなければ `RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = <理由の短い印>` で値を返さない。印は not_found・ticket・status・expired・used・view・source・column・key・read_failed の 10 種だけ。値・名前・札を印に入れない）:
    1. `SELECT r.*, c.ticket_hash, c.ticket_expires_at FROM ops_case.unmask_requests r JOIN ops_case.cases c ON c.incident_id = r.incident_id WHERE r.id = p_request_id FOR UPDATE OF r`。無ければ not_found。
    2. 件の札: `encode(sha256(convert_to(p_ticket,'UTF8')),'hex')` が 1 の c.ticket_hash と一致し、now() < c.ticket_expires_at（＝申請の件の札だけが通る）。
    3. status='approved'。
    4. now() < expires_at。
    5. read_count < max_reads。
    6. view_name が ai_cloud に実在する（pg_class と pg_namespace。nspname='ai_cloud'・relkind='v'）。
    7. build_columns から view_name の source を 1 つに決め、is_denied_source(source) と同じ解き方で表の oid を得る。is_denied_source(source) が false。
    8. column_names の全部が、build_columns のその view_name の列にあり、mode が 'excluded' でない。
    9. 元の表の主キーが 1 列（pg_index の indisprimary・indnatts=1）で、型が §3(e) の 6 種のどれか。
  - 読み方: `format('SELECT to_jsonb(t) FROM (SELECT %I AS __key, %s FROM %I.%I WHERE %I = ANY ($1::%s[])) t', pk, <列ごとの %I をつなげたもの>, n.nspname, c.relname, pk, format_type(pk の型))` を `EXECUTE … USING p_row_keys` で回し、jsonb の配列にまとめる。表と列の名前は 7 で得たカタログの名前を %I で、型は format_type の結果だけを %s に入れる（どれもカタログ由来）。
  - 読み出しは `BEGIN … EXCEPTION WHEN OTHERS THEN RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'read_failed'; END` で包む（型の変換の失敗・ロック待ちの時間切れ 55P03 を含め、元の文や値をエラーの文に出さない）。statement_timeout の時間切れ 57014 は OTHERS で捕まらない（PostgreSQL 16 公式文書 plpgsql-control-structures「OTHERS matches every error type except QUERY_CANCELED and ASSERT_FAILURE」）。57014 はそのまま外に出て、unmask_http は 503 を返す（値は USING で渡すので、エラーの文に値は入らない）。
  - 同じ取引で `UPDATE ops_case.unmask_requests SET read_count = read_count + 1` と `INSERT INTO ops_case.unmask_reads(request_id, row_count, column_names)`。
  - 返す形: `{"request_id":…, "rows":[…], "row_count":n}`。
- 関数 ops_case.grant_unmask_owner() RETURNS integer（SECURITY INVOKER・`SET lock_timeout = '2s'`。呼ぶのは trap の jarvis。EXECUTE は PUBLIC から REVOKE し、だれにも付けない）:
  1. 付けるべき表の一覧を作る: build_columns の source（重複を除く）のうち、is_denied_source が false のもの（is_denied_source と同じ解き方で oid に解く）。
  2. 今付いている表の一覧を作る: public と tenant\_% のスキーマの表で `aclexplode(c.relacl)` の grantee が ai_unmask_owner の oid で privilege_type='SELECT' のもの（has_table_privilege は PUBLIC への付与も t にするので使わない）。
  3. 2 にあって 1 に無い表だけ REVOKE SELECT。1 にあって 2 に無い表だけ GRANT SELECT。付けるべき表のスキーマに USAGE（無いときだけ）。同じなら何もしない。
  4. ai_cloud_meta の USAGE と build_columns・ops_case.deny_tables の SELECT。ops_case の USAGE、cases と unmask_requests の SELECT、unmask_requests の UPDATE(read_count)、unmask_reads の INSERT と bigserial の列の USAGE（無いときだけ）。
  5. 付けた数と外した数の合計を返す。
  - ai_unmask には ops_case の USAGE と unmask_fetch の EXECUTE だけ（表には何も付けない）。
- #1 の最後で `SELECT ops_case.grant_unmask_owner();` を 1 回呼ぶ（初回のデプロイでも効くように。build_columns が前のデプロイのまま残っている前提）。

## 4-B. #2 の中身（S scripts/run_all_migrations.sh）
- :1193 の後に `run_sql migrations/<日時>_create_ops_case.sql`（上に `# ADR-1052 段2: …` の 1 行の説明）。
- trap の関数の中、ai_cloud の作成の部分（:252-262）の後、`exit "${rc}"`（:263）の前に:
  - 「>>> [final] grant ai_unmask_owner」を出す → `docker exec -e PGOPTIONS="-c statement_timeout=${AI_CLOUD_CREATE_TIMEOUT}" -i "${POSTGRES}" ${PSQL} -v VERBOSITY=terse -c 'SELECT ops_case.grant_unmask_owner();'` → 所要の秒を出す → 失敗したら警告「⚠️ ai_unmask_owner の権限の付け直しに失敗（値を返す口は前の権限のまま）」だけ。終了コードは変えない。
  - ai_cloud の作成が失敗した回も呼ぶ（build_columns は前のまま残るので、前と同じ表に付く。ai_cloud が無ければ unmask_fetch の 6 で断る）。
- 段1の目印（段1 カード §4-C の「変えない文字」）は全部そのまま。read_probe の行は増やさない。
- trap を切り出す既存の試験 3 本が、新しい行が入っても通ることを生出力で示す: S tests/sandbox/ai-ro-restore-on-failure.sh:39 と S tests/sandbox/migration-read-probe.sh:57（awk で `^AI_RO_CREATE_SQL=` から `^trap _ai_ro_create_on_exit EXIT` までを切り出す）、S scripts/tests/test-deploy-orphan-cleanup.sh の C8（:176-232。偽の docker で [final] の行の順を確かめる）。C8 の数え方が変わるなら直し、直した後の合格を示す。

## 4-C. #3 の中身（backend/app/routers/ops_case.py）
- router は `APIRouter(tags=["ops-case"])`。main.py で prefix="/api/v1"。
- 鍵: CASE_AGENT_TOKEN の口と CASE_ADMIN_TOKEN の口を別の依存関数にする（§3(f) の形）。
  - 鍵が空なら全員 401。どちらの口も、もう片方の鍵では 401。
  - 2 つの鍵が同じ値なら、両方の口を全員 401 にし、記録に「keys identical」の印だけ出す（値は出さない。比べるのは compare_digest）。
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
  - 先に `SELECT … FROM ops_case.cases WHERE incident_id = :id FOR UPDATE` で件の行をロックしてから、件の申請の数を数える（同時に送られても 3 本目が通らない）。すでに 2 つあれば、status='denied'・decided_by='auto:limit'・decision_reason='limit' の行を残して 409。
  - 理由 20〜1000 字・列 1〜5・行 1〜20（重複は 1 つに数える）。
  - view_name が build_columns にあり、source が 1 つに決まる。`ops_case.is_denied_source(source)` が false（関数を呼ぶ。backend に一覧を写さない）。
  - 列が全部そのビューの build_columns にあり、mode が excluded でない。
  - 元の表の主キーが 1 列で、型が §3(e) の 6 種のどれか（カタログを読む）。行のキーを型ごとに確かめる: integer・bigint・smallint は `^-?[0-9]{1,19}$` で、さらに型の範囲内。uuid は `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`。text・character varying は 1〜200 字。合わなければ 422。
- どの口も set_operator_context の後に DB を触り、最後に _clear_operator（S ops.py:534・:568 の形）。
- 一意制約（reports の 2 回目）は 409。ほかの DB の失敗（sqlalchemy の DBAPIError）は、503 と `{"detail": "OPS_CASE_UNAVAILABLE"}` だけを返し、記録には口の名前と SQLSTATE だけ（エラーの文・表の名前・値は出さない）。
- 応答と記録（ログ）に札・鍵・申請の理由の全文を書かない。

## 4-D. #5 の中身（backend/app/ops/unmask_http.py）
- Starlette の小さな app（S read_window_http.py と同じ作り）。口は POST /ops/unmask/read {request_id} だけ。ほかの道は 404。
- 鍵: `Authorization: Bearer <CASE_AGENT_TOKEN>`（V5-4。環境変数の値と compare_digest。空なら全員 401）。件の札は X-Case-Ticket。どちらも無ければ 401。request_id が uuid の形でなければ 400。
- DB: psycopg2 で AI_UNMASK_DATABASE_URL に繋ぐ（`_connect` の差し替えの入口は S read_window_http.py:35-36 の形）。readonly_query.execute は使わない（読み取り専用の取引のため）。
  - autocommit を切り、`SELECT ops_case.unmask_fetch(%s, %s)` を 1 回 → `conn.commit()` → 成功してから値を返す。
  - 関数が SQLSTATE 42501 なら 403 と `{"error": <印>}`（印は §4-A の 10 種だけ。それ以外の文は返さない）。
  - 42501 以外の失敗（接続・時間切れ・COMMIT の失敗を含む）は 503 と `{"error": "unavailable"}` で値を返さない。
- 記録: S read_window_http.py と同じ /dev/log の印に、request_id・row_count・結果の種類・失敗のときは SQLSTATE だけ。値・札・鍵・エラーの文は書かない。via は 'https-case-unmask'。
- 体の大きさは 4KB まで。

## 4-E. #6・#9 の中身（容器と deploy）
- #6: S docker-compose.ai-reader-cloud-http.yml の写し。name と -p は astro-webapp-unmask、container_name ai-unmask-http、command は `uvicorn app.ops.unmask_http:app --host 0.0.0.0 --port 8080 --workers 1 --no-access-log`、env_file は /home/ubuntu/.config/salesanchor/ai-unmask.env、environment は `CASE_AGENT_TOKEN: ${CASE_AGENT_TOKEN:-}` だけ。read_only・tmpfs /tmp・cap_drop ALL・no-new-privileges・mem_limit 128m・logging none・/dev/log・frontnet と backnet は同じ。ports は無し。上の説明の行も同じ形で書く。
- #9 の 1（S :499-514「Recreate nginx」を次の形に。if の条件は今のまま）:
  0. 手順に `id: nginx_recreate` と `continue-on-error: true` を付ける（§3(k)。この手順が失敗しても、後ろの Bootstrap・移行・smoke・Finalize は今と同じに流れる）。
  - 置くファイル（どれも /home/ubuntu/salesanchor の直下。git に入れない。.deploy_prev_sha と同じ扱い。§3(n)）: `.deploy_nginx_good.conf`＝最後に後の確認まで通った設定。`.deploy_prev_nginx.conf`＝今回の戻り先。
  1. 戻り先の用意（`PREV=$(cat .deploy_prev_sha 2>/dev/null || true)`）:
     - `.deploy_nginx_good.conf` があって空でなければ、それを `.deploy_prev_nginx.conf` に写す（最後に起きた設定を正とする。PREV の設定は、前のデプロイで点検に落ちていれば壊れている）。
     - 無ければ（この形の初回か、good の書き出しに失敗して消した後）、PREV が空でなく `git cat-file -e "${PREV}:nginx/nginx.conf"` が通るときだけ `git show "${PREV}:nginx/nginx.conf" > .deploy_prev_nginx.conf`。
     - どちらもできない・結果が空なら、理由の印（`::error::戻り先の nginx.conf を用意できません`）を出し、作り直さずに `exit 1`（作業の写しの nginx.conf は新しいまま残る。この回の Emergency の手順は #9 の 1c が守る）。
  2. 戻り先の点検: `.deploy_prev_nginx.conf` を本番と同じ取り付けで `nginx -t`（形は §3(m)）。通らなければ作り直さずに `exit 1`。
  3. 新しい設定の点検: `docker compose run --rm --no-deps -T nginx nginx -t`（本番の取り付け＝証明書・htpasswd.d・/var/www をそのまま使う。§3(j)）。通らなければ、作業の写しを戻り先に替えてから（`cp .deploy_prev_nginx.conf nginx/nginx.conf`。後ろで nginx を作り直す手順が起きても壊れた設定を読まないため）、作り直さずに `exit 1`（今の nginx は前の設定のまま動き続ける）。
  4. 4〜6 はまとめて `set +e` で囲む（S deploy.yml:743-752 の Finalize の health check と同じ形）。作り直し: 今と同じ `docker compose up -d --no-deps --force-recreate nginx`。
  5. 後の確認: 最大 15 秒、1 秒ごとに `docker inspect --format='{{.State.Running}}' astro-webapp-nginx-1` が true、かつホストから `curl -sk -o /dev/null -w '%{http_code}' --resolve app.salesanchor.jp:443:127.0.0.1 https://app.salesanchor.jp/` が 000 でない（curl の終了コードが 0 でなくても止まらずに次の秒へ）。通ったら `cp nginx/nginx.conf .deploy_nginx_good.conf.tmp && mv .deploy_nginx_good.conf.tmp .deploy_nginx_good.conf` で書き出し（途中で切れた good を残さない）、失敗したら `rm -f .deploy_nginx_good.conf .deploy_nginx_good.conf.tmp` で古い good も消し（動いている設定より古い good で 1c が作り直さないため。第5版の審査 L1）、`::warning::最後に起きた nginx の設定を残せませんでした` を出して、手順を成功で終える（第4版の審査 L2）。
  6. 4 が 0 でない、または 5 が 15 秒の間に通らなければ自動で戻す: `cp .deploy_prev_nginx.conf nginx/nginx.conf` → もう一度作り直し → 5 と同じ確認の結果を出して `exit 1`（`.deploy_nginx_good.conf` は書き換えない）。作業の写しは次のデプロイの `git reset --hard origin/main` で戻る。
- #9 の 1b（Finalize（S :723）の後・Verify deployment（S :870）の前に新しい手順）: 「Fail if nginx recreate failed」。`if: ${{ always() && steps.nginx_recreate.outcome == 'failure' }}`。`echo "::error::nginx の作り直しの手順が失敗しました（戻り先の用意・点検・後の確認のどれか）"` と `exit 1`。これでデプロイ全体が失敗の表示になり、Verify は動かない。S :1124 の手順は記録に出すだけで、どこにも送らない（届くのは GitHub の既定の失敗の知らせだけ）。PO と Opus への知らせは段4（agent-console）で扱い、段2では足さない。
- #9 の 1c（S :1106-1122「Emergency block /design/ on smoke FAIL」を変える。`if: failure()` のまま）: htpasswd を消した後、作り直しの前に次の順で進める（第4版の審査 M1。作業の写しの設定は nginx -t しか通っていない、または点検もしていない回がある＝Recreate が飛んだ回（S :500 の success() が偽）・Finalize の自動ロールバックの後（S :765 で作業の写しが PREV の設定になる）・good が無い回（初回・書き出しに失敗して消した後）に手順 1・2 で止めた回）:
  1. `.deploy_nginx_good.conf` があって空でなければ、`cp .deploy_nginx_good.conf nginx/nginx.conf`（最後に後の確認まで通った設定で作り直す。作業の写しは次のデプロイの `git reset --hard origin/main` で戻る）。無ければ（この形の初回か、good の書き出しに失敗して消した後）作業の写しのまま。点検だけ通った設定で作り直すことになるので、確認の結果を必ず記録に出す。
  2. `docker compose run --rm --no-deps -T nginx nginx -t` を通す。通らなければ作り直さず、`::warning::nginx の設定が点検に通らないため作り直しません` を出す（全部の入口を止めないことを優先する）。
  3. 通れば今と同じに作り直し、#9 の 1 の 5 と同じ確認の結果を記録に出す（この手順は `if: failure()` の中なので、確認に落ちても戻す先はもう無い。結果は記録に残すだけ）。今の手順は、どの失敗の回でも作業の写しの設定で nginx を作り直すので、点検に落ちた設定でも作り直してしまう（第3版の審査 H1）。
- 失敗の表示になった回は、1c が /design/ を閉じる（htpasswd を消す）。次に成功したデプロイで htpasswd が作り直され、元に戻る（S deploy.yml:1104 の説明と :125「Setup design-site htpasswd (idempotent)」）。
- 点検で止まった回の本番の状態: backend・DB の移行・smoke は新しい形で済み、nginx だけが前の設定のまま。新しい設定にしか無い入口（case-api）だけが使えない。次にすることは直す PR を出すこと（次のデプロイは S deploy.yml:63-79 の gate で nginx の手順も流れる。戻り先は `.deploy_nginx_good.conf` なので、壊れた設定には戻らない）。
- #9 の 2: :550 の後に「Start ai-unmask-http (case agent unmask read)」。S :534-550 と同じ形で、ai-unmask.env が読めなければ警告して起こさない、起こせなくても警告だけ（アプリの反映は止めない）。`docker compose -p astro-webapp-unmask -f docker-compose.ai-unmask-http.yml up -d --build=false --force-recreate`。

## 4-F. #8・#10・#12・#14 の中身（nginx と CI）
- #8 の 1: http の段（S :10 の後）に
  - `limit_req_zone $binary_remote_addr zone=case_api:10m rate=1r/s;`
  - `map $ssl_server_name $is_case_api_sni { default 0; "~*^case-api\.salesanchor\.jp\.?$" 1; }`（大文字小文字と末尾の点を同じに扱う。ここが名前の判定の正本）
- #8 の 2: 今の 443 のブロック 5 つそれぞれの server_name の直後に `if ($is_case_api_sni) { return 421; }`（上に `# ADR-1052: TLS の名前が case-api なら 421` の 1 行）。
- #8 の 3: case-api のブロック（api のブロックの後に置く）:
  - listen と TLS は S :334-344 と同じ形（listen 443 ssl・[::]:443 ssl・http2 on・ssl_protocols・ssl_ciphers・ssl_prefer_server_ciphers）。証明書は容器の中の /etc/letsencrypt/live/case-api.salesanchor.jp/fullchain.pem と privkey.pem。add_header は S :348-352 と同じ 5 つ。
  - `if ($is_case_api_sni = 0) { return 421; }` と `if ($host != "case-api.salesanchor.jp") { return 421; }`（api の TLS で Host を case-api にした場合と、case-api の TLS で Host を替えた場合の両方を止める）。
  - `if ($request_uri ~* "(%2e|%2f|\.\.|//)") { return 400; }`。
  - `resolver 127.0.0.11 valid=5s;`（S の api のブロックと同じ）。
  - `location = /api/v1/ops/read-window/query`: S :502-519 と同じ中身で、`set $case_window ai-reader-cloud-http;`。
  - `location ~ "^/api/v1/ops/case/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/(report|unmask-requests)$"`: limit_except POST・client_max_body_size 40k・limit_req zone=case_api burst=4 nodelay・`set $case_backend backend;` で :8000 へ。
  - `location ~ "^/api/v1/ops/case/unmask-requests/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"`: limit_except GET・同じ制限で backend へ。
  - `location = /ops/unmask/read`: limit_except POST・client_max_body_size 4k・同じ制限・`set $case_unmask ai-unmask-http;` で :8080 へ。
  - どの location も proxy_set_header の 5 行と timeout は S :502-519 と同じ。落ちているときは `error_page 502 504 =503 /__case_unavailable;`（S :521 の `__rw_unavailable` と同じ形。internal・503 "unavailable"）。
  - `location / { return 404; }`。
  - uuid は小文字だけ受ける（相談係は backend が返した形のまま使う）。
- #12 test_nginx_case_api_guard.py（ファイルを読むだけ。DB も docker も要らない）:
  - nginx.conf を `server {` のブロックに分ける（波かっこの数で。コメントの行は外す）。
  - `listen 443` か `listen [::]:443` を持つ server のブロックのうち、server_name が case-api でないものの数 ＝ `if ($is_case_api_sni) { return 421; }` を持つブロックの数。食い違えば落とす。
  - map の行がちょうど 1 つ・case-api のブロックがちょうど 1 つで、SNI と host の 421 の 2 行と 400 の 1 行を持つ。
  - case-api のブロックの location が上の 5 つ（read-window・case の 2 つ・unmask・`/`）と内部の 1 つだけ。pending・ticket・decision・audits・audit-inputs の文字を含む location が無い。
  - 数え合わせの関数に、421 の行を 1 つ消した文字列を渡すと落ちることを試験に入れる（T7 の CI 側）。
- #10 nginx-config-check.yml（pull_request と push(main)。paths で絞らず毎回走る。必須の Check にするかは PO の判断。段2では GO の条件に入れる）:
  1. `python -m pytest backend/tests/ops/test_nginx_case_api_guard.py`（標準の python と pytest だけで動く形にする）。
  2. docker-compose.yml の nginx のイメージ（S :6 の nginx:1.31.1）を `--network host` で起こす。nginx.conf の ssl_certificate の名前ごとに、その名前の自己署名の証明書を一時の場所に作り /etc/letsencrypt に取り付ける。htpasswd.d・/var/www の各所は空の物を取り付ける。`nginx -t` が通る。
  3. #14 nginx-case-api-guard.sh を走らせる（IPv4 の 127.0.0.1 と IPv6 の ::1 の両方。どれか 1 つでも期待と違えば落とす）:
     - case-api の SNI で Host を 5 つの名前（jarvis-claude.uk・app・api・monitor・salesanchor.jp）にそれぞれ替える → 5 つとも 421。
     - 5 つの名前の SNI で Host を case-api → 5 つとも 421。
     - 先に送り方の確かめ: 試験専用の小さな nginx（本番の nginx.conf とは別のファイル。`return 200 "$ssl_server_name";` だけを返す）を別の番号で起こし、openssl s_client -servername `case-api.salesanchor.jp.` で届いた名前に末尾の点が残ることを確かめる。残らなければ止めて Opus へ（末尾の点の試験が何も試さずに通るのを防ぐ）。
     - SNI に末尾の点を付けた `case-api.salesanchor.jp.` と大文字の `CASE-API.salesanchor.jp`（openssl s_client -servername で送り、手で HTTP の 1 行を書く）で、Host を app → 421。Host を case-api・道を `/` → 404。
     - case-api の `/`・`/api/v1/auth/login`・`/api/v1/ops/case/pending`・ticket・decision・audits・audit-inputs・uuid でない {id}・大文字の uuid → 404。`/api/v1/ops/case/%2e%2e/pending`・`//ops/unmask/read` → 400。
     - 5 つの名前それぞれ、SNI と Host を揃えた `/` の応答コードと Location が、同じ台本を今の S の nginx.conf に当てた結果と同じ（「同じ応答」の定義。前と後の両方を CI で取って比べる）。CI は host ネットワークで docker の名前解決が無いので、変数で中継する app・api などの `/` は前も後も中継の失敗の応答になる。CI の比べが効くのは 421 の守りと jarvis・salesanchor.jp などの直接の応答で、中継する名前は §5 の本番の比べで見る。
- 本物のクラウドからの T7（外への中継が CONNECT の先の名前を SNI に入れるか）は段3で測る。

## 4-G. 試験（#11・#13）
- #11（S backend/tests/ops/test_ai_cloud_views.py と同じ作り。使い捨ての DB に本物の migration を流し、SET ROLE で測る）:
  - 前提: ops_incidents（S migrations/20261016_100000_create_ops_incident_tables.sql）と salesanchor_app のロールが要る。試験 DB に tenant_* が無ければ作る。作れなければ skip でなく落とす。
  - 後片付け: 作ったロール（ai_unmask_owner・ai_unmask）はクラスタ全体に残るので、S test_ai_cloud_views.py の _Cluster の形で消す。
  - T2: 申請が pending・denied のまま unmask_fetch → 42501（status）。unmask_reads が増えない。
  - T3: 別の件の札・期限を過ぎた札 → 42501（ticket）。
  - T4: expires_at を過去にした approved（status を expired に変える処理を止めた形のまま）→ 42501（expired）。
  - T5: 許可にない列（申請の列に無い列を直接 view_name に足した行を作る）・mode='excluded' の列・deny_tables の表・主キーが 2 列の表 → 42501。許可済みの行でも同じ。
  - T5b: 型に合わない行のキー（uuid の主キーに 'abc'）を直接入れた許可済みの行 → 42501（read_failed）。エラーの文に 'abc' が入っていない。
  - T6: ai_unmask で public の表・tenant の表・ops_case の 5 表・ai_cloud_meta.build_columns を直接 SELECT → 42501。ai_reader・ai_reader_cloud・salesanchor_app・PUBLIC から unmask_fetch と grant_unmask_owner を実行 → 42501。ai_unmask_owner の SELECT が deny_tables の表に付いていない（has_table_privilege が f）。salesanchor_app で unmask_requests の read_count を UPDATE → 42501。
  - T6c: tenant の表の行を許可して unmask_fetch → 行が返る（0 件でない）。COMMIT の後、別の接続で unmask_reads が 1 増え、read_count=1。
  - T6b: 2 回目 → 42501（used）。同時に 2 本（2 つの接続で、1 本目の COMMIT の前に 2 本目を始める）→ 1 本だけ値が返り、read_count=1・unmask_reads 1 行。
  - ロール: ai_unmask_owner と ai_unmask の属性。属性違いの同名ロールがある状態で #1 を流すと止まる。ai_unmask の rolconfig（pg_db_role_setting）に log_statement=none・log_min_error_statement=panic・log_min_duration_statement=-1 があり、default_transaction_read_only が無い。
  - is_denied_source: deny_tables の名前・excluded の列を持つ表で true、ふつうの表で false、解けない名前で true。
  - salesanchor_app の権限: SET ROLE salesanchor_app で ops_case.cases を SELECT できる（42501 にならない）。is_denied_source を呼べる（第3版の審査 L1・第4版の審査 L1'）。
  - grant_unmask_owner: 2 回続けて呼ぶと 2 回目の戻りは 0（違う表だけ変える）。表を deny_tables に足して呼ぶと、その表の SELECT が外れる。試験 DB での 1 回目の所要が 5 秒以内（測った秒を出す）。
- #13:
  - test_unmask_http.py（Starlette の TestClient。`_connect` を差し替える）: 鍵なし・Bearer なし・違う鍵・札なしは 401。鍵が空なら全部 401。request_id が uuid でなければ 400。ほかの道は 404。関数が 42501 なら 403 で印だけ・値なし。42501 以外の失敗（57014 の時間切れを含む）と COMMIT の失敗は 503 で値なし。成功したら値を返し、/dev/log の印に値・札・鍵・エラーの文が入らない。
  - test_ops_case_router.py: 2 つの鍵の取り違えで 401。2 つの鍵が同じ値なら両方の口が 401。札の違い・件の違い・期限切れで 403。報告の 2 回目は 409、32KB を超えたら 413。申請の 3 回目は 409 で auto:limit の行が残る。理由 19 字・列 6・行 21・excluded の列・拒否表・主キー 2 列・型に合わない行のキー（uuid に 'abc'、integer に '1x'、範囲を超える数）は 422。decision の minutes 16 は 422、pending 以外は 409、expires_at は backend の時刻から決まる。DB の失敗を起こすと 503 で `OPS_CASE_UNAVAILABLE` だけ。

## 4. GO と承認・PO の操作
- #1〜#10・#14 は危険パス（migrations・本番 scripts・deploy.yml・backend/app/ops・nginx・workflows）→ ADR-136 の委任 GO（POの委任に基づくClaude Opus発行）。release ブランチで待ち、GO の前にマージしない。GO の条件: CI 緑（#10 を含む）・reviewer（opus）APPROVE・PR 本文の相乗り確認・証明書のファイルの再確認（§3(済)）。
- secrets 変更 → PO 本人の GO・置くのは PO の `!`（値は画面に出さない）。台本は Opus が書き、/security-review を通す:
  - GitHub secret CASE_ADMIN_TOKEN（段1の CASE_AGENT_TOKEN の台本と同じ形。値は手元で作り、agent-console の Keychain にも同じ値を入れる。CASE_AGENT_TOKEN と同じ値にしない）。
  - ai_unmask のパスワードと ai-unmask.env（段1の ai_reader_cloud の台本と同じ形。VPS の上で作り、ALTER ROLE と env の書き込みを 1 本で。接続の変数名は AI_UNMASK_DATABASE_URL。権限 600）。
- 反映の順: PR マージ → デプロイ（ops_case・ロール・nginx の case-api。容器は env が無いので起きない）→ PO の `!` で secret・パスワード・env → 次のデプロイで容器が起きる。

## 5. 受入（○×）
| 基準 | 検証方法 |
|---|---|
| T2〜T6c・ロール・is_denied_source・権限の付け直し | CI の #11 が緑。grant_unmask_owner の 1 回目が 5 秒以内（出した秒） |
| 口の決まり | CI の #13 が緑 |
| T7（CI 側）・文法・末尾の点・IPv4 と IPv6 | #10 が緑（#12 の数え合わせ・nginx -t・#14 の台本）。421 の行を 1 つ消すと #12 が落ちる試験がある |
| trap を切り出す既存の試験 | S tests/sandbox/ai-ro-restore-on-failure.sh・S tests/sandbox/migration-read-probe.sh・S scripts/tests/test-deploy-orphan-cleanup.sh の C8 が合格（生出力） |
| nginx の作り直しの守り | #9 の 1・1b・1c を偽の docker か sandbox で、次の回を生出力で示す: ① 新しい設定の点検が通らない → 作り直しをせず、作業の写しが戻り先に替わり、nginx の手順が失敗。後ろの手順（Bootstrap・移行・smoke の代わりの印）は動き、1b でデプロイが失敗の表示。1c は good があれば good の設定で、無ければ戻り先の設定で点検を通して作り直す ② .deploy_prev_sha が空で good も無い → 作り直しをせず失敗。1c は 2 つに分けて示す: ②-1 作業の写しが nginx -t に落ちる回 → 作り直さず警告 ②-2 nginx -t に通る回 → 作り直して確認の結果が記録に出る ⑦ good がある状態で 1c が動く 2 つの回: ⑦-1 nginx の手順が飛んだ回（偽の流れで success() を偽にする） ⑦-2 Finalize の自動ロールバックで作業の写しが PREV の設定になった回 → どちらも 1c が作業の写しを good に替えてから点検し、good の設定で作り直す（作業の写しの設定で作り直さない。容器の中の設定が good と同じことを diff で示す） ⑧ good の書き出しを失敗させた回 → 警告が出て、good も tmp も無い ③ 戻り先の点検に落ちる → 作り直さず失敗 ④ 作り直した後に起きない（curl が 000 と終了コード 7 を返す回・compose up が 0 でない回の 2 つ）→ 戻り先に戻して作り直し、失敗の表示 ⑤ 前の回で点検に落ちた後の次の回で、戻り先が `.deploy_nginx_good.conf`（PREV の壊れた設定ではない） ⑥ 成功の回で `.deploy_nginx_good.conf` が新しい設定になる |
| backend の DB の権限 | #11 に、salesanchor_app で ops_case.cases を SELECT でき、is_denied_source を呼べる試験がある |
| nginx が止まらない（本番） | デプロイの「Recreate nginx」で前の点検・後の確認が通った記録がある。その後、app・api・monitor・salesanchor.jp・jarvis-claude.uk の 5 つの入口の `/` の応答コードと Location がデプロイ前と同じ（デプロイ前に同じ curl で基準値を取る） |
| T7（本番の通し） | 手元の curl で（IPv4）: case-api の TLS で Host を 5 つの名前にそれぞれ替える → 5 つとも 421。api の TLS（`--connect-to`）で Host を case-api → 421。case-api の `/`・`/api/v1/auth/login`・`/api/v1/ops/case/pending`・ticket・decision・audits・audit-inputs・uuid でない {id} → 404。case-api の 3 つの道に鍵なしで送る → 401（容器が起きる前の /ops/unmask/read は 503） |
| 管理の口は api だけ | api.salesanchor.jp の /api/v1/ops/case/pending に鍵なし → 401（404 でない＝届いている） |
| DB の権限（本番） | ai_reader で: `has_function_privilege('ai_unmask','ops_case.unmask_fetch(uuid,text)','EXECUTE')` が t、ai_reader・ai_reader_cloud・salesanchor_app は f。pg_roles の 2 つのロールの属性と ai_unmask の rolconfig が §4-A のとおり。pg_proc の unmask_fetch の持ち主が ai_unmask_owner・prosecdef=t・proconfig に search_path と lock_timeout。deny_tables の 10 表で `has_table_privilege('ai_unmask_owner', 表, 'SELECT')` が f、かつ同じ 10 表で `has_table_privilege('public', 表, 'SELECT')` が f（PUBLIC への付与が無い）。デプロイの記録に grant ai_unmask_owner の所要の秒がある |
| 相談係の窓口の通し（段1の残り。T10b・T13・T14） | 容器が起きた後、PO の `!` の台本（VPS の .env の値を画面に出さずに使う）で、case-api の read-window に Bearer 付き → 200 で 1 文読める・Bearer なし → 401・ai_ro を読む文 → 400 か 42501。記録の印が via=https-case |
| ai-unmask-http が起きる | env を置いた後のデプロイで、ai-unmask-http が running。case-api の /ops/unmask/read に鍵だけ・札なし → 401 |

- 段2では本番で値を 1 件も読まない（許可の行を作る道は段4の agent-console）。値を返す通しは CI の T6c・T6b で測る。

## 6. 戻し方
- 値を返す口を止める: GitHub secret CASE_AGENT_TOKEN を消してデプロイ（相談係の 3 つの道が全部 401。設計 §9（３））。PO の `!` で `ALTER ROLE ai_unmask NOLOGIN`。
- 容器を止める: #9 の 2 の手順を外してデプロイし、PO の `!` で容器を止める。
- case-api の入口を外す: #8 の case-api のブロックを外す PR（421 の行と map は残してよい。外しても他の名前の応答は変わらない）。
- ops_case の表・ロール・関数は残っても届く人がいない。消すのは PO の判断。
- nginx が起きない場合:
  - 前の点検・戻り先の用意で止まった回: 今の nginx は前の設定のまま動いている。backend と DB の移行は済んでいる（#9 の 1 の「点検で止まった回の本番の状態」）。直す PR を出す。
  - 作り直した後に起きない回: #9 の 1 の 6 が戻り先に自動で戻して作り直す。それでも起きなければ、PO の `!` で `cd /home/ubuntu/salesanchor && cp .deploy_nginx_good.conf nginx/nginx.conf; docker compose up -d --no-deps --force-recreate nginx`（台本は Opus が先に用意する。最後に起きた設定に戻す。.deploy_nginx_good.conf が無いときだけ .deploy_prev_nginx.conf を使い、どちらも先に #9 の 1 の 2 と同じ形で nginx -t を通す）。あわせて直前のマージを戻す PR を EMERGENCY の手順（S docs/BRANCH_PROTECTION_SETUP.md §4）で出す。
  - 戻すのは nginx.conf だけ。compose の nginx の部分（取り付け・イメージ）を変えた PR では、戻すものに docker-compose.yml を含める（この PR は backend の env しか変えないので当たらない）。
