# 段1 実装カード（設計第4.6版の追補・第4版）

- 対象: docs/handoff/cloud-case-ai/design.md 第4.6版 §4-1・§7・§9 の段1。ADR-1052（Accepted）。
- 根拠の写し: S=origin/main 45b70588400a75df91cf359171bb9455e790eddc。行番号はすべてこの sha。実装の前に最新の origin/main で行を合わせ直す（§3(d)）。
- 状態: 第4版（1回目・2回目の審査の指摘と、3回目の審査の HIGH 1・MEDIUM 2・LOW 8、4回目の審査の MEDIUM 1・LOW 2 を反映）。5回目の審査で APPROVE。PO の実装承認あり（2026-10-31 01:00 ごろ、PO「1」＝作り始める）。

## 0. 第4.3版からの変更（V4.4）
- V4.4-1 受けるヘッダ: §4-1 の READ_WINDOW_TOKEN_HEADER・READ_WINDOW_TOKEN_PREFIX・READ_WINDOW_AUDIT_VIA。読むのは要求ごと（今の S backend/app/ops/read_window_http.py:62 と同じ）。
- V4.4-2 段1での測り方: 段1では case-api の nginx が無い（段2）。
  - T14 の相談係の窓口側と T10b の via=https-case は、段1では試験で測る（Starlette の TestClient に 3 つの環境変数を入れる）。本番での通しの確認は段2の nginx の後（段2の T7 と同じ回）。
  - T14 の今の窓口側は、段1の後に本番で測る（api.salesanchor.jp に Authorization: Bearer だけで送ると 401）。
  - T13 の「相談係から ai_ro が読めない」は、段1では DB の権限で測る（§5）。窓口越しの確認は段2。
  - T10b のロールの属性は pg_roles（rolconfig を含む）で測る。pg_db_role_setting は ai_reader で読めるか未確認のため使わない。
- V4.4-3 段2の前の条件:
  - 証明書は名前ごとの Let's Encrypt（S nginx/nginx.conf:35,75,339,575,629・S docker-compose.yml:42-47 の certbot）。
  - case-api の 443 ブロックを証明書より先に入れると nginx が起動できず、全部の入口が止まる。
  - よって「case-api の DNS（グレー雲）と証明書の取得」を段3から「段2の nginx のマージの前」に移す。DNS は PO の画面操作。証明書は PO の `!`（certbot の webroot。今の名前と同じ手順）。段2の nginx の PR は、証明書のファイルがあることを確かめてからマージする。
  - 段2までは、case-api への要求は jarvis の既定のブロックに当たる（app への 301）。段1では外から届かない。
- V4.4-4 写しの表を外す: 元の表が次に当たるものは ai_cloud に載せない。public の表で名前が `__backup` で始まるもの（LIKE '\_\_backup%'）、名前が正規表現 `(_bak_|_backup|baseline_)` に当たるもの。写しは元の表と同じ中身で、相談に要らない。
- V4.4-5 分類表の初期値: 1035 行（allow 169・mask 859・mask_bare 7）。
  - 伏せる型の列 994 個すべてに行を置く。加えて、正規表現に当たる「そのまま」の型の列 41 個に allow の行を置く（§4-1 の CI の見張りが型を問わず行を求めるため。V4.4 H1）。
  - allow の根拠は次の 3 つだけ。どれにも当たらない列は mask にした（初期は最小）。
    - (a) 本番の値の決まり（CHECK 制約）で値が限られる: 61 行。reason に制約の名前を書く。条件は、1 列だけの CHECK で、形が `= ANY (ARRAY[...])`・`= ANY ((ARRAY[...])::text[])`（varchar の列）か `= '<1つの値>'`（NULL を許す形を含む）で、convalidated=t。文字の形だけを決める正規表現の CHECK は当てない（accuracy_gold_versions.gold_version は mask、review_reason_codes.code は (b) に移した）。
    - (b) 共用マスタ（運営だけが入れる一覧の表 27 個）: 67 行。表の一覧は §4-A。
    - (b) の表に利用者が書く道: 本線の backend/app/routers では、super_admin 以外の口に書き込みは無い（3回目の審査で確認）。ORM・services・celery からの書き込みは未確認 → §3(i)。
    - テナントの利用者が画面から書ける public の表 6 個（products・tcg_note_master・tcg_status_master・tcg_product_categories・payment_fee_settings・translation_glossary。S backend/app/routers/products.py:342-346・note_master.py:155-173・status_master.py:154-226・product_categories.py:130-295・payment_fee_settings.py:86-108・translation.py:100-112,257-297）の文字の列 55 個はすべて mask（うち 32 個は第2版の allow から移した）。商品名も初期は伏せる（相談係は申請で読む。開けるかは後で PO が決める）。
    - (c) そのままの型（数・日付・uuid・真偽）: 41 行。
  - tenant の自由入力の列（支払い方法・梱包・発送方法・シフトの種類・送料の地域など）は、すべて mask にした（V4.4 M1）。
- V4.4-6 分類表の正本: 分類は trap で流す #4 の SQL の中に全行で書く。流すたびに表を空にして入れ直す（ファイルが正本。V4.4 M3）。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 今（S） | 変える形 |
|---|---|---|---|
| 1 | 新 migrations/<日時>_create_ai_cloud_meta.sql（一覧に載せる） | 無し | §4-A の表 2 つと関数 1 つを作る（冪等: IF NOT EXISTS・CREATE OR REPLACE）。PUBLIC から全部 REVOKE。ai_reader にだけ USAGE と 3 表（column_class・build_log・build_columns）の SELECT（§4-A 権限）。ai_reader_cloud には何も付けない。関数 build_views の EXECUTE はだれにも付けない |
| 2 | 新 migrations/<日時>_create_ai_reader_cloud_role.sql（一覧に載せる） | 無し | S migrations/20261017_130000_create_ai_reader_role.sql を写し、名前を ai_reader_cloud に。:12 の属性・CONNECTION LIMIT 2・:16 の止め方・log_statement='all'・読み取り専用・2 つの timeout は同じ値。パスワードは付けない（§4 の PO の `!`） |
| 3 | 新 migrations/<日時>_drop_ai_cloud_views.sql（一覧の先頭） | 無し | `DROP SCHEMA IF EXISTS ai_cloud CASCADE;` だけ |
| 4 | 新 migrations/<日時>_create_ai_cloud_views.sql（一覧に載せず trap から流す） | 無し | §4-B の 1 トランザクション |
| 5 | S scripts/run_all_migrations.sh | :219 で ai_ro を外す。:226-249 の _ai_ro_create_on_exit は ai_ro の作成に失敗すると :238・:245 で exit する | §4-C |
| 6 | S backend/app/ops/read_window_http.py | :28 TOKEN_HEADER 固定。:53 via="https" 固定。:62-64 で比べる | §4-D |
| 7 | 新 docker-compose.ai-reader-cloud-http.yml | 無し | S docker-compose.ai-reader-http.yml の写し。name と -p は astro-webapp-casewindow、container_name ai-reader-cloud-http、env_file は /home/ubuntu/.config/salesanchor/ai-reader-cloud.env、environment は `READ_WINDOW_TOKEN: ${CASE_AGENT_TOKEN:-}`・`READ_WINDOW_TOKEN_HEADER: Authorization`・`READ_WINDOW_TOKEN_PREFIX: "Bearer "`・`READ_WINDOW_AUDIT_VIA: https-case`。ほかは同じ |
| 8 | S .github/workflows/deploy.yml | :324 で READ_WINDOW_TOKEN 行を消す。:376 で書く。:514-530 で ai-reader-http を起こす | :324 の sed に `-e '/^CASE_AGENT_TOKEN=/d'` を足す。:376 の次に `CASE_AGENT_TOKEN='${{ secrets.CASE_AGENT_TOKEN }}'`。:530 の後に同じ形の手順「Start ai-reader-cloud-http」（ai-reader-cloud.env が読めなければ警告して起こさない・失敗してもアプリの反映は止めない） |
| 9 | 新 backend/tests/ops/test_ai_cloud_views.py | 無し | §4-E |
| 10 | S backend/tests/ops/test_read_window_http.py | 今の窓口の試験 | T14 と via の切り替え（§4-D の場合分けを全部） |
| 11 | S tests/sandbox/ai-ro-restore-on-failure.sh・S tests/sandbox/migration-read-probe.sh・S scripts/tests/test-deploy-orphan-cleanup.sh | trap を目印で切り出す（:39・:57・C8 :175-240） | §4-C の目印を守る。T12 の場合分けを ai-ro-restore-on-failure.sh に足す（§4-F）。C8 の眠る回を直し、C10 を足す（§4-C） |

## 2. 触らない範囲
- ai_ro の作成 SQL・ai_reader・ai-reader-http・docker-compose.ai-reader-http.yml・api.salesanchor.jp の nginx。
- nginx の case-api（段2）。ops_case（段2）。クラウドの設定（段3）。
- 分類表の行の中身（下書きの 1035 行のまま。足し引きは申請と別の PR）。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) migration の登録検査（S scripts/check-migration-registration-exists.sh と CI）が、一覧に載せない #4 をどう扱うか。ai_ro の作成 SQL（20261017_130100）と同じ逃がし方があれば合わせる。無ければ止めて Opus へ。
- (c) ai_ro は持ち主 jarvis・security_invoker なしで tenant の RLS を越えている（S migrations/20261017_130100_create_ai_ro_views.sql:2）。jarvis が RLS の対象外（表の持ち主で FORCE なし）かを試験 DB で確かめる。ai_cloud も同じにする。違えば止めて Opus へ。
- (d) 一覧の本当の末尾（S では :1173 の 20261023_180000_create_accuracy_gold.sql）。ほかの PR が足していれば、その後ろに #1・#2 を足す。
- (e) CI で S backend/tests/ops/test_ai_ro_views.py がどの手順で流れているか。同じ手順に #9 を載せる。
- (f) ai-reader.env と ai_reader のパスワードを最初にどう置いたか（ADR-1024 の記録・runbook）。§4 の PO の `!` の台本はそれと同じ形にする。見つからなければ止めて Opus へ。
- (g) 値の決まりの揃い: 本番で、テナントのスキーマごとに分類表 (a) の tenant の 23 個の制約があり convalidated=t かを数える（ai_reader で pg_constraint。制約名は `regexp_replace(conname,'^tenant_[0-9a-z]+_','')` で頭を外して照合）。public の 38 個も同じ条件で確かめる。形は (a) の 3 つのどれか。足りない・形が違うものがあれば止めて Opus へ。
- (i) (b) の 27 表に、router 以外（ORM の session.add・services・celery）から利用者の入力が書かれる道が無いかを探す。有れば止めて Opus へ（その表の文字の列は mask に移す候補）。
- (h) 試験 DB の列と分類表の差: T10 の対象の列のうち分類表に無いものを数える。0 でなければ本番との差の理由を調べ、止めて Opus へ（分類表の行は勝手に足さない）。
- (済) readonly_query の check_sql はスキーマを絞らず、via の値も検査しない（S backend/app/ops/readonly_query.py:142-162,197-210）。https-case はそのまま通る。

## 4-A. #1 の中身
- スキーマ ai_cloud_meta。
- 表 column_class: schema_pattern text（CHECK IN ('public','tenant_*')）・table_name text・column_name text・class text（CHECK IN ('allow','mask','mask_bare')）・reason text NOT NULL DEFAULT ''・主キー (schema_pattern, table_name, column_name)・CHECK (class <> 'allow' OR reason <> '')。
- 表 build_log: built_at timestamptz NOT NULL DEFAULT now()・ok boolean NOT NULL・view_count integer・failed_count integer・error_class text。
- 関数 ai_cloud_meta.build_views() RETURNS TABLE(view_count int, failed_count int)。SECURITY INVOKER（呼ぶのは jarvis）。中身は §4-1 の型の表と下の式。
  - 範囲: S migrations/20261017_130100_create_ai_ro_views.sql:25-31 と同じ（public と tenant\_%、relkind r・p）。V4.4-4 の写しの表を外す（LIKE は `_` を \ で逃がす）。
  - 秘密列: 同じ SQL の :23 の deny を同じ文字のまま使い、列ごと外す。全部外れた表はビューを作らない（:44-47 と同じ）。
  - ビューの名前: 同じ SQL の :49-59 と同じ（`<スキーマ>__<表>`、63 バイトを超えたら先頭 54 バイト以内＋`_`＋md5 先頭 8 桁）。
  - 失敗の単位: 表ごと（:61-71 と同じ。1 本の失敗は failed_count に数え、その表だけ載せない）。
  - 持ち主: 作る人（jarvis）。security_invoker は付けない（ai_ro と同じ）。security_barrier は付けない（ビューに WHERE が無く、行を絞らないため。値の漏れは列の式で防ぐ）。
- 列の出し方（上から順に最初に当たったもの）:
  1. deny に当たる → 列ごと外す。
  2. 分類が mask_bare → `CASE WHEN c IS NULL THEN NULL ELSE 'masked' END`（型を問わない）。
  3. 分類が mask → 下の「伏せる式」（型を問わない。数の型でも伏せる）。
  4. 分類が allow → そのまま。
  5. 分類が無い → 型が「そのまま」の一覧（§4-1。enum は pg_type.typtype='e'。ドメインは typtype='d' なので伏せる側）ならそのまま、ほかは「伏せる式」。
  - 分類の引き当て: public の表は (public, 表, 列)。tenant_* の表は (tenant_*, 表, 列)。
- 伏せる式（c は列。t は c::text）:
  - 配列（pg_type.typcategory='A'）: `CASE WHEN c IS NULL THEN NULL ELSE 'masked:array:n=' || coalesce(cardinality(c),0) END`（多次元でも全要素の数。array_length は 1 次元だけなので使わない）。
  - json・jsonb: `CASE WHEN c IS NULL THEN NULL ELSE 'masked:json:len=' || char_length(t) || ':keys=' || CASE WHEN jsonb_typeof(c::jsonb)='object' THEN (SELECT count(*) FROM jsonb_object_keys(c::jsonb))::text ELSE '0' END END`（`'masked` の文字は式の中に 1 か所だけ。object 以外で jsonb_object_keys を呼ぶとエラーになるため先に型を見る。配列・文字・数・null の json の値で落ちないことを T1 に足す）。
  - どの式も `'masked` の文字は 1 か所だけにする（§5 の受入②で数えるため）。
  - ほか: `CASE WHEN c IS NULL THEN NULL WHEN t = '' THEN '' ELSE 'masked:len=' || char_length(t) || ':' || CASE WHEN t ~ '^[0-9]+$' THEN 'digits' WHEN t ~ '^[\x01-\x7f]+$' THEN 'ascii' WHEN t !~ '[\x01-\x7f]' THEN 'multibyte' ELSE 'mixed' END END`。
  - 出る型はどれも text。
- V4.4-5 (b) の共用マスタの表（public。27 個）: permissions・tcg_series_master・tcg_series・tcg_manufacturers・tcg_unit_evidence_rules・tcg_normalization_rules・line_units・line_conditions・line_unit_aliases・line_condition_aliases・weight_classes・type_master・trainer_dex・pokemon_dex・quantity_units・product_lines・product_kinds・product_formats・product_attribute_masters・condition_definitions・countries・knowledge_rules・inventory_aggregation_rules・extraction_prompt_config・app_fx_rates・app_fx_rate_history・review_reason_codes。
- 表 build_columns（受入用）: view_name・column_name・source（スキーマ.表）・source_type・class（無ければ NULL）・mode（pass・mask・mask_bare・excluded）。build_views() が作るたびに中を空にして書き直す。作成に失敗した表（表ごとの EXCEPTION で捕まえた表）の行は書かない（失敗は build_log の failed_count で数える）。
- 権限: ai_reader に ai_cloud_meta の USAGE と column_class・build_log・build_columns の SELECT を付ける（中身は表と列の名前と件数だけで、値は入らない。受入と週次点検で読む）。ai_reader_cloud には何も付けない。

## 4-B. #4 の中身（1 トランザクション）
1. `TRUNCATE ai_cloud_meta.column_class;` と、下書き 1035 行の INSERT（ファイルが正本。行の足し引きはこの SQL の変更で行う）。
2. `DROP SCHEMA IF EXISTS ai_cloud CASCADE; CREATE SCHEMA ai_cloud;`
3. `DO $$ … $$` の中で `ai_cloud_meta.build_views()` を呼び、結果で build_log に 1 行（ok = failed_count=0、view_count・failed_count）を書き、`RAISE NOTICE 'ai_cloud views created: %, failed: %'` を出す（RAISE は plpgsql の中でしか書けないため）。
4. `GRANT USAGE ON SCHEMA ai_cloud TO ai_reader_cloud; GRANT SELECT ON ALL TABLES IN SCHEMA ai_cloud TO ai_reader_cloud;`
5. COMMIT。
- 途中でエラーや打ち切り（57014。WHEN others に捕まらない）が出ると全体が戻る。このときは ai_cloud が「外れたまま」（デプロイ最初の #3 で外れているため）になり、build_log に書けない。§4-C の shell がその後に失敗の 1 行を書く。

## 4-C. #5 の中身（S scripts/run_all_migrations.sh）
- :219 の「前」の行に `run_sql migrations/<日時>_drop_ai_cloud_views.sql`（ai_ro を外す前に置く。ここで失敗しても ai_ro は外れていないので、trap が無くても今の読む窓口は止まらない。この行はずっと残す。戻すときも消さない。§6）。
- :226 の次に `AI_CLOUD_CREATE_SQL="migrations/<日時>_create_ai_cloud_views.sql"` と `AI_CLOUD_CREATE_TIMEOUT="${AI_CLOUD_CREATE_TIMEOUT:-30s}"`。
- 関数 _ai_ro_create_on_exit の中:
  - ai_ro が失敗しても ai_cloud を試すため、:236-245 を次の形にする: `if [ ! -f "${REPO_DIR}/${AI_RO_CREATE_SQL}" ]; then`（今の :236 の文字のまま）（今の警告）`elif ! docker exec …（今の :243 のまま）; then`（今の警告「ai_ro views の作成に失敗」）`fi`。:238 と :245 の `exit "${rc}"` は無くなる。ファイルが無いときは作成を飛ばし、2 つ目の警告は出さない。既存の試験の grep（'ai_ro views の作成に失敗' など）の当たる数が変わらないことを試験で示す。
  - ai_ro の部分の後、:247 の `exit "${rc}"` の前に ai_cloud の部分を足す: 「>>> [final] psql < ${AI_CLOUD_CREATE_SQL}」を出す → ファイルが無ければ警告 → `docker exec -e PGOPTIONS="-c statement_timeout=${AI_CLOUD_CREATE_TIMEOUT}" -i "${POSTGRES}" ${PSQL} -v VERBOSITY=terse < …` → 失敗なら警告「⚠️ ai_cloud views の作成に失敗（ai_cloud は外れたまま＝相談係は読めない）」と、build_log への失敗の 1 行（`INSERT INTO ai_cloud_meta.build_log(ok, error_class) VALUES (false, 'psql_failed')` を同じ timeout・VERBOSITY=terse で。これも失敗したら警告だけ）。
  - 最後は今と同じ `exit "${rc}"`（終了コードは変えない）。
- 変えない文字（既存の試験の目印）:
  - 始まりの `AI_RO_CREATE_SQL=` の行・終わりの `trap _ai_ro_create_on_exit EXIT` の行・関数名。
  - `>>> [final] psql < ${AI_RO_CREATE_SQL}`・'recreating ai_ro views anyway'・'ai_ro views の作成に失敗'。'ai_ro views created:' は SQL 側の文で、変えない。
  - 切り出す範囲に read_probe の行はちょうど 1 つ（:231 の read_probe_stop）。増やさない（S tests/sandbox/migration-read-probe.sh:233-243）。
- C8（S scripts/tests/test-deploy-orphan-cleanup.sh:186-195）は、PGAPPNAME=salesanchor_migration と ` -i ` を含む 2 回目の呼び出しで眠る。ai_cloud の外しが 1 回目に入るので、眠る回を 3 回目に直す（必須）。直した後の C8 の合格を生出力で示す。
- C10（新。S scripts/tests/test-deploy-orphan-cleanup.sh の偽 docker の形。本物の run_all_migrations.sh を流す）: 偽 docker が PGAPPNAME=salesanchor_migration と ` -i ` を持つ 1 回目の呼び出し（ai_cloud の外し）で exit 1 する。合格: ①スクリプトの終了コードが 0 以外 ②スクリプトの標準出力に `psql < migrations/<日時>_drop_ai_cloud_views.sql` の行があり、`psql < ` と `125900_drop_ai_ro_views.sql` を含む行が無い（S scripts/run_all_migrations.sh:113 の `>>> [N/M] psql < ${file}` の行で判定する。偽の docker の記録は引数だけで、ファイル名は標準入力から渡るため記録では判定しない。ai_ro を外していない）③記録に `VERBOSITY=terse` を含む START が無い（trap の前で止まった）。（ai-ro-restore-on-failure.sh は trap の範囲だけを切り出すため、この試しは置けない）
- 時間: trap の中の作成は ai_ro 最大 30 秒＋ai_cloud 最大 30 秒（1 文ごと）＋失敗の 1 行。

## 4-D. #6 の中身（S backend/app/ops/read_window_http.py）
- :28 の TOKEN_HEADER を既定値の定数にする。要求ごとに `READ_WINDOW_TOKEN_HEADER`（空なら X-Read-Window-Token）と `READ_WINDOW_TOKEN_PREFIX`（既定は空）を読む。
- 受けた値の頭が PREFIX と合わなければ 401。合えば頭を外し、今と同じ compare_digest（:62-64）。
- :53 の via を `READ_WINDOW_AUDIT_VIA`（空なら https）にする。:9 の説明を直す。
- 試験（#10）: 既定のまま＝今と同じ（X-Read-Window-Token で通る・Authorization: Bearer だけは 401）。相談係の形＝`Authorization: Bearer <鍵>` だけ通る・Bearer なしは 401・X-Read-Window-Token だけは 401・鍵が空なら全部 401。via が https-case で記録される。

## 4-E. #9 の中身（試験。T1・T1b・T10・T10b・M8）
- 試験 DB に tenant_* のスキーマが無ければ、試験の中でテナントの作り方（既存の試験と同じ関数）で 1 つ作る。作れなければ skip でなく落とす。
- T10（CI の見張り）: 試験 DB の public と tenant_* の全部の表（V4.4-4 の写しの表を除く）の全列のうち、秘密列の deny（S migrations/20261017_130100_create_ai_ro_views.sql:23 と同じ文字。小文字にした列名に当てる）に当たらない列について、
  - 「そのまま」の型でない列に column_class の行が無ければ落とす。
  - 正規表現に当たる列は型を問わず行が要る。allow で reason が空なら落とす。
  - 足した場合の試し: 分類の無い text 列・理由なしの allow・`phone_number bigint` を足すと落ちる。deny に当たる text 列（例 `x_token_encrypted`）を分類なしで足しても落ちない。
- T1・T1b: ai_reader_cloud で ai_cloud を、別名・式・連結・substring・md5・length・to_json・UNION・型変換のエラーで読む。pg_stats・pg_stats_ext・pg_stats_ext_exprs・EXPLAIN (VERBOSE)。mask の列の元の値が出ない。
- T10b: 属性違いの同名ロールがある状態で #2 を流すと止まる。

## 4-F. T12（sandbox-test。#11）
- 次の 4 つの回を流す: ①ふつう ②途中に「ai_cloud に載っている列を消す migration」と「型を変える migration」を入れる ③ai_ro の作成を失敗させる ④ai_cloud の作成を失敗させる。
- 合格: ②で migration が止まらず、最後に ai_cloud が伏せた形で残る。③で ai_cloud はでき、④で ai_ro はでき、どの回も終了コードは今と同じ。build_log に回ごとに 1 行（④は ok=false・psql_failed）。既存の試験 3 本が通る。

## 4. GO と承認・PO の操作
- #1〜#8 は危険パス（migrations・本番 scripts・deploy.yml・backend/app/ops）→ ADR-136 の委任 GO。release ブランチで待ち、GO の前にマージしない。
- secrets 変更 → PO 本人の GO・置くのは PO の `!`（値は画面に出さない）:
  - GitHub secret CASE_AGENT_TOKEN。
  - ai_reader_cloud のパスワード（VPS の上で作り、ALTER ROLE と ai-reader-cloud.env の書き込みを 1 本の台本で。§3(f) の形に合わせる）。
  - ai-reader-cloud.env（今の ai-reader.env と同じ場所・権限 600）。接続の変数名は AI_READER_DATABASE_URL（S backend/app/ops/readonly_query.py:273 が読む名前）。
- 反映の順: PR マージ→デプロイ（ai_cloud と ロールができる。容器は env が無いので起きない）→ PO の `!` で secret・パスワード・env → 次のデプロイで容器が起きる。
- 段2との順（L5）: 段2の権限の追加は #4 の後（trap の後）に効くよう、段2の設計で決める。段1では ai_cloud に触る GRANT は #4 の中だけ。

## 5. 受入（○×）
| 基準 | 検証方法 |
|---|---|
| T1・T1b・T10・T10b・T14（試験側） | CI の新しい試験が緑 |
| T12 | sandbox-test で §4-F の 4 回が合格 |
| 外しの失敗・C8 | test-deploy-orphan-cleanup.sh の C8（眠る回を 3 回目に直した後）と C10 の ①②③ が合格（生出力で示す） |
| 今の窓口が変わらない（T13・T14 の本番側） | 段1の後、fetch_gold.py・fetch_groups.py・fetch_snapshot.py と fetch_corpus.py が今と同じに動く。今の窓口に Authorization: Bearer だけで送ると 401 |
| ai_cloud ができる | ai_reader で数える（カタログはだれでも読める）: `ai_cloud の relkind='v' の数` ＝ `元の表（public と tenant\_%、relkind r・p、V4.4-4 の写しの表を元の表の名前で除く）のうち、deny に当たらない列が 1 つ以上ある表の数`。build_log の最新の行が ok=t・failed_count=0。デプロイのログに `ai_cloud views created: N, failed: 0` |
| 伏せてある | ai_reader で build_columns を読む: ①分類が mask・mask_bare、または分類が無く型が「そのまま」の一覧に無い列で、mode='pass' の数が 0。②ビューごとに、pg_get_viewdef の中の `'masked` の出てくる数 ＝ build_columns の mode が mask・mask_bare の数（全ビューで食い違い 0）。③mode='pass' の列は、分類が allow か、型が「そのまま」の一覧にある |
| ロール | pg_roles の ai_reader_cloud の rolsuper・rolcreatedb・rolcreaterole・rolreplication・rolbypassrls・rolconnlimit が ai_reader と同じ。rolconfig に log_statement=all・同じ timeout と読み取り専用 |
| 権限（M5） | `has_schema_privilege('ai_reader_cloud','ai_ro','USAGE')`・`('ai_reader_cloud','ai_cloud_meta','USAGE')` が f。public と tenant_* の全部の表で `has_table_privilege('ai_reader_cloud', 表, 'SELECT')` が t の数が 0。`('ai_reader_cloud','ai_cloud','USAGE')` が t。`has_schema_privilege('ai_reader','ai_cloud_meta','USAGE')` が t。`has_function_privilege('ai_reader','ai_cloud_meta.build_views()','EXECUTE')` と `('ai_reader_cloud','ai_cloud_meta.build_views()','EXECUTE')` が f |

## 6. 戻し方（H2）
- 容器を止める: #8 の「Start ai-reader-cloud-http」の手順を外してデプロイし、PO の `!` で容器を止める。GitHub secret を消せば窓口は全部 401（§9 戻し方（３））。
- ロールを使えなくする: PO の `!` で `ALTER ROLE ai_reader_cloud NOLOGIN`。
- ai_cloud を無くす: #5 のうち trap の ai_cloud の部分だけを戻す。デプロイ最初の外しの行（#3）は残す（消すと残ったビューが後の列の削除を止める）。次のデプロイで ai_cloud は外れたまま作られない。
- ai_cloud_meta とロールは残っても読む人がいない。消すのは PO の判断。
