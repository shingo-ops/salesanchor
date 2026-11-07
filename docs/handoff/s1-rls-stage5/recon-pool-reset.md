# 接続プールの返却時リセット 調査（recon-pool-reset）

- 役割: 調査役（読む＋使い捨て DB での測定のみ）。製品コード・本番・secret には触っていない。PR は作らない。
- 起点: origin/main（9cf750f29）から `release/s1-rls-pool-reset-recon`。背景は 未合流のブランチ release/s1-rls-stage5-review（594737ba8）にあるクラウド審査1回目の記録 review-cloud-1 の (k)（commit の後の SET が close の rollback で消え、接続に前の値が残る）。
- 測定環境: クラウドのサンドボックスで `pg_ctlcluster 16 main start`。PostgreSQL 16.15（localhost・使い捨て DB `kmeasure`）。Python 3.12 の venv に backend/requirements.txt と同じ版（backend/requirements.txt:4-6 `sqlalchemy==2.0.38`・`asyncpg==0.31.0`・`psycopg2-binary==2.9.10`）を入れた。
- 台本: `docs/handoff/s1-rls-stage5/pool_reset_measure.py`（m1〜m7）・`docs/handoff/s1-rls-stage5/m8_scan.py`・`docs/handoff/s1-rls-stage5/m8_scan2.py`（m8 の構文木走査）。製品コードではない。
- **未確認の宣言**: 候補 A/B/Bx の「公式の例どおり」は https://docs.sqlalchemy.org/en/20/dialects/postgresql.html を開いて確かめていない（この実行では外部ページを読んでいない）。B・Bx の形は SQLAlchemy 2.0.38 の pool 実装（下記）を読んで組んだ。

## 候補の定義（台本 pool_reset_measure.py:50-66・:68-100）

| 名前 | engine の設定 | reset ハンドラ |
|---|---|---|
| なし | 既定（pool_reset_on_return = rollback） | なし |
| A | 既定のまま | `event.listens_for(pool, "reset")`。`reset_state.terminate_only` でなければ `RESET ALL` を流す |
| B | `pool_reset_on_return=None` | ハンドラ内で rollback → `RESET ALL` |
| Bx | `pool_reset_on_return=None` | ハンドラ内で rollback → `RESET ALL` → commit |

SQLAlchemy 2.0.38 の返却処理（/opt/kvenv/lib/python3.12/site-packages/sqlalchemy/pool/base.py:1405-1432）: `pool.dispatch.reset(...)`（=ハンドラ）が**先**に走り、その後に `pool._reset_on_return is reset_rollback` のときだけ pool 自身の rollback が走る（`transaction_was_reset` が真なら省く）。

## 結論（先に）

1. **どちらが正しいか（前の 2 回の食い違いの決着）**: 今回の生の値では A は `idle` で効かない・B は効くが `idle in transaction`・Bx は `idle` で効く。→ **2 回目の結果が正しい**。1 回目（「A は idle in transaction・B は効かない」）は A と B の取り違えと推定される（1 回目の台本は未確認）。根拠は m1 の返却直後 pg_stat_activity の生の値。
2. A は効かない。ハンドラの `RESET ALL` が pool の rollback より前に走り、同じ取引の中で rollback されて消えるため（返却直後の last_query が `ROLLBACK;`）。
3. B は値は戻るが、返却直後に **idle in transaction**（last_query = `RESET ALL`）で残る。同期（psycopg2）では `pool_pre_ping=True` の次の checkout が `ProgrammingError: set_session cannot be used inside a transaction` で落ちた（m6）。**B は採用不可**。
4. Bx は 値が戻り・idle・エラー無し。ただし**文脈を入れ直さずに commit の後も同じ session を使う箇所は、プール 2 本以上で文脈が空になる**（m7: 文脈が空 20/20）。いま（候補なし）は同じ箇所が「別テナントの文脈が見える」（m7: pool_size=2・20 で 20/20）。つまり Bx は漏れを「空（フェイルクローズ）」に変えるが、m8 で見つけた「文脈を入れ直さず commit の後に tenant 表を schema 名なしで触る」箇所（calendar_service.py:306、customer_priority.py:180-190、priority_scoring.py:389-415 ほか）は先に直さないと動かなくなる。
5. 速度（m5）: 中央値 なし 0.997ms／A 1.133ms／B 1.118ms／Bx 1.441ms（+0.44ms）。p95 は 1.565／1.996／1.804／1.840 ms。

---

## r1 エンジン一覧

**方法**: `grep -rnE "create_engine|create_async_engine|sessionmaker|asyncpg\.(connect|create_pool)|psycopg2\.connect" --include=*.py backend`（テスト除く。107 行）を読み、engine ごとに前後を開いた。結果は backend/app 外（backend/scripts・backend/tcg_migration/scripts）も 1 行ずつ末尾に記す。

**結果**（フルパス:行番号は /home/user/salesanchor 相対）:

| # | 場所 | 種別・ドライバ | pool 設定 | connect_args / server_settings | 用途 | app.tenant_id・app.is_operator・search_path をこの接続で設定するか |
|---|---|---|---|---|---|---|
| 1 | backend/app/database.py:33 `engine` | 非同期 asyncpg | pool_size=20・max_overflow=10・pool_recycle=3600・pool_pre_ping=True・pool_timeout=30（database.py:26-31） | `prepared_statement_cache_size: 0`・`server_settings.application_name = salesanchor_backend`（database.py:13-16） | API 本体。`get_db`（database.py:46-61） | する: get_current_tenant（backend/app/auth/dependencies.py:274・277・281）が 3 つとも SET。返却前に get_db の finally が `clear_tenant_context`（dependencies.py:403-405）で 3 つを戻す |
| 2 | backend/app/database.py:84 `admin_engine` | 非同期 asyncpg | pool_size=5・max_overflow=2・pool_recycle=1800・pool_pre_ping=True（database.py:78-82） | cache 0・`application_name = salesanchor_admin_ops`（database.py:68-71） | 管理者用 `get_admin_db`（DDL・テナント横断） | このファイル内では設定しない。未確認: 呼び出し側（super_admin_tenants.py:166 は schema 名つきで DROP している） |
| 3 | backend/app/tasks/viewer_inventory_cache.py:110 | 非同期 asyncpg・ワンショット | pool_size=2・max_overflow=0・pool_pre_ping=True（viewer_inventory_cache.py:110-119） | cache 0・`application_name = salesanchor_celery_viewer_cache`（:115-118） | Celery。終わりに `engine.dispose()`（:131） | このファイルでは設定しない（`refresh_once` の中は未確認） |
| 4 | backend/app/tasks/tcg_extraction_recovery.py:172 | 非同期 asyncpg・ワンショット | pool_size=2・max_overflow=0・pre_ping | cache 0・`application_name = salesanchor_celery_extraction_recovery`（:168-171） | Celery。`_engine.dispose()`（:207） | しない |
| 5 | backend/app/tasks/tcg_extraction.py:792 | 非同期 asyncpg・ワンショット | pool_size=2・max_overflow=0・pre_ping | cache 0・`application_name = salesanchor_celery_distribute`（:788-791） | Celery。`_engine.dispose()`（:804） | しない |
| 6 | backend/app/tasks/buyback_scraper.py:29 | 非同期 asyncpg | pool_size=5・max_overflow=2・pool_recycle=1800・pre_ping（:29-37） | **指定なし**（application_name 無し・asyncpg の文キャッシュは既定） | 買取価格スクレイパー。`engine.dispose()`（:76 近辺の `asyncio.run(engine.dispose())`） | 取引内だけ（`SET LOCAL app.is_operator`: backend/app/services/buyback_scraper/base.py:65 ほか） |
| 7 | backend/app/tasks/translation.py:41・:127、google_calendar_sync.py:91・:101・:111、tcg_mirror.py:310 ほか 11 ファイル | #1 の `app.database.engine` を借りる | #1 と同じ | #1 と同じ | Celery。各タスクの終わりに `asyncio.run(engine.dispose())`（translation.py:56 ほか）→ **プールの接続を全部閉じる**ので、前の値は次のタスクへ残らない | タスクごと（translation.py は table_ref を引数で渡す。他は未確認） |
| 8 | backend/app/services/email_sender.py:38 `_engine` | 同期 psycopg2（`postgresql+asyncpg://` を `postgresql://` に置換: email_sender.py:32-34） | pool_pre_ping=True・その他は SQLAlchemy 既定（pool_size=5・max_overflow=10。既定値は台本では未測定） | なし | モジュール singleton（:37-39）。メール送信 | 設定しない |
| 9 | backend/app/tasks/data_deletion.py:59 `_engine` | 同期 psycopg2（ADMIN_DATABASE_URL: :45-56） | pre_ping=True・既定 | なし | モジュール singleton。データ削除（全テナント横断） | しない（schema 名つきで操作） |
| 10 | backend/app/tasks/tcg_extraction.py:94 `_engine` | 同期 psycopg2 | 既定 | なし | モジュール singleton。TCG 抽出 | しない（TCG_SCHEMA = "public": backend/app/services/tcg_analyzer_svc.py:58） |
| 11 | backend/app/services/tcg_product_master_svc.py:828 | 同期 psycopg2 | pre_ping=True・既定 | なし | 呼び出しごとに作成。`engine.dispose()`（:981） | しない |
| 12 | backend/app/services/gemini_extraction_svc.py:105・:154 | 同期 psycopg2 | pre_ping=True・既定 | なし | 呼び出しごとに作成し `engine.connect()`。dispose は未確認 | しない（public.extraction_prompt_config を読むだけ） |
| 13 | 同期 psycopg2・`_get_sync_engine()` 形（呼び出しごと作成・既定 pool・pre_ping なし）: backend/app/tasks/maintenance.py:47、avatar.py:90、verify_meta_subscriptions.py:84、refresh_meta_tokens.py:99、dashboard.py:40、reports.py:178、fx_rate_updater.py:39、tcg_import_discard.py:27、gemini_route_watch.py:37（dispose は :171）、tcg_extraction_recovery.py:51（:518 で dispose）、rule_test.py:29 | 同期 psycopg2 | 既定 | なし | Celery の定期処理 | `set_tenant_context_sync`（dependencies.py:341-343）を使うのは avatar・dashboard・maintenance・refresh_meta_tokens・reports・verify_meta_subscriptions。fx_rate_updater は `SET app.is_operator = 'true'`（fx_rate_updater.py:70）。dispose は多くが未確認 |
| 14 | backend/app/tasks/priority_scoring_check.py:83 | 生 psycopg2 | `autocommit = True`（:84） | なし | 定期。`set_tenant_context_cursor`（dependencies.py:359-361）を使い `conn.close()`（:123）で閉じる | する（接続は専用で閉じるので持ち越さない） |
| 15 | backend/app/ops/readonly_query.py:282・ops/unmask_http.py:61 | 生 psycopg2（読み取り専用の鍵） | `connect_timeout=5`（unmask_http.py:61） | なし | 運用の読み取り窓 | `SET LOCAL statement_timeout`（readonly_query.py:292）だけ |
| 16 | backend/app/discord_gateway/reaction_writer.py:35 | asyncpg の `create_pool` | min_size=1・max_size=5（:35-39） | なし | Discord Gateway（別プロセス） | 取引内で `set_config('app.tenant_id', $1, true)`（:108-111）のみ |
| 17 | backend/scripts/issue_initial_passwords.py:94・backend/scripts/check_keyword_quality.py:72・backend/tcg_migration/scripts/*.py（psycopg2.connect・create_engine） | 手動実行の道具 | — | — | 常駐ではない。対象外 | 未確認（本調査の範囲外） |

**判定**: 常駐で**長く生きて接続を使い回す** engine は #1（本番 API・pool 20）・#2・#6・#8・#9・#10 と、Celery の `app.database.engine`（#7: ただしタスクごとに dispose で接続を閉じる）。`application_name`／`server_settings` を持つのは #1〜#5 のみ（m2 で RESET ALL 後も残ることを確認）。

---

## r2 取引をまたいで残す設定（LOCAL の無い SET・set_config 第 3 引数 false）

**方法**: backend/app 全体（テスト除く）を大文字小文字無視で `SET (SESSION)? (app\.|search_path|statement_timeout|lock_timeout|idle|application_name|role|time zone|work_mem…)`・`set_config`・`SET LOCAL`・`statement_timeout|lock_timeout|application_name|options=` で grep し、`UPDATE … SET` 等を除いて全件読んだ。

**結果の件数**: LOCAL の無い SET = backend/app/auth/dependencies.py（7 関数・計 18 文）と backend/app/tasks/fx_rate_updater.py:70 の 1 文だけ。`set_config` の第 3 引数 false = **0 件**。statement_timeout・lock_timeout は**全部 LOCAL**（下の最後の表）。

### 判定（1 件ずつ）

| # | 場所 | 設定 | 次の要求へ持ち越す前提があるか | 判定 |
|---|---|---|---|---|
| 1 | backend/app/auth/dependencies.py:274 | `SET search_path = tenant_NNN, public`（get_current_tenant） | 無い。持ち越したいのは**同じ要求の中**（commit の後も）だけ。次の要求は get_current_tenant がまた SET する（:274-281） | 次要求への持ち越し前提: なし。要求内で commit を越える前提: **あり**（m7・m8） |
| 2 | :277 | `SET app.tenant_id = '<id>'` | 同上 | 同上 |
| 3 | :281 | `SET app.is_operator = ''`（前の要求が operator だった場合の上書き） | **前の接続の値が残る前提を逆手に取った防御**。残る値を上書きするため、get_current_tenant を通らない入口（get_db だけ）では効かない | 持ち越し前提なし。防御としては部分的（review-cloud-1 の重大-1 と同じ） |
| 4 | :322-324（set_tenant_context） | 上と同じ 3 文 | 同上。reset_tenant_context（:383）も同じ関数に委譲 | 持ち越し前提なし |
| 5 | :341-343（set_tenant_context_sync） | 同じ 3 文。Celery の同期 Session 用（avatar・dashboard・maintenance・refresh_meta_tokens・reports・verify_meta_subscriptions） | 無い。ただし refresh_meta_tokens.py・verify_meta_subscriptions.py は 1 テナントの中で `session.commit()` を何度も挟み、その後も `{schema_name}.audit_logs` 等を触る（m8 の表）。schema 名つきなので表は合うが、`app.tenant_id`（RLS）は commit 後に**同じ接続が再利用される場合にだけ**残る。pool 既定の同期 engine で 1 本ずつ使うので実際は同じ接続（m6 の none 行: 同じ pid・値が残る）。**偶然に頼っている** | 持ち越し前提: 要求内（タスク内）で commit を越える前提あり・偶然 |
| 6 | :359-361（set_tenant_context_cursor） | 生 psycopg2 カーソルで同じ 3 文 | 無い。`autocommit = True`（priority_scoring_check.py:84）なので SET は即時有効・接続は `conn.close()`（:123）で閉じる | 持ち越し前提なし・安全 |
| 7 | :403-405（clear_tenant_context） | `SET search_path = public` / `SET app.tenant_id = ''` / `SET app.is_operator = ''` | これは**持ち越さないための**3 文。commit の後の取引で流れると close の rollback で消えて**効かない**（m1: なし・A とも step1 で `is_operator='true'` が残る） | 意図は「持ち越さない」。実効は commit 後に無効（m1） |
| 8 | :468（set_operator_context） | `SET app.is_operator = 'true'` | 無い。呼び出し元（admin.py:64・fx_rate_admin.py:135・ops_error_reports.py:108・:136・:169・analysis_error_report_svc.py:159・:190・line_source_names.py:125・super_admin_llm_budget.py:151・super_admin_phase_switch.py:128・super_admin_suppliers.py:69・super_admin_tenants.py:50・:176・ops.py 8 箇所・ops_case.py 7 箇所）は同じ要求内で使い終わる | 持ち越し前提なし。**commit の後に reset だけを流す形は 'true' が残る**（m1 step1）。該当: admin.py:90→95、fx_rate_admin.py:147→149、ops_error_reports.py:149→154・:189→194、analysis_error_report_svc.py:179→184・:201→206、tcg_line_import.py:420→422、line_source_names.py:87→89、tcg_line_import_svc.py:552→563（m8 の表）。super_admin_llm_budget.py:173・super_admin_phase_switch.py:156・super_admin_suppliers.py:73 は commit との前後関係を**未確認** |
| 9 | :485（reset_operator_context） | `SET app.is_operator = ''` | 同上（commit の後に使うのが前提の関数。docstring :471-482） | 取引内に流れると rollback で消える。ops.py:70-75・ops_case.py:107-112 の `_clear_operator` は `rollback → reset → commit` で**確定させている**（これだけは (k) を避けている） |
| 10 | backend/app/tasks/fx_rate_updater.py:70 | `SET app.is_operator = 'true'`（同期 Session・非 LOCAL） | 無い。同じ関数で `session.commit()`（:81）の後に戻す文が**無い**ので、その接続には 'true' が残る。ただし engine は呼び出しごとに作成（:39・:65）・dispose 無し（grep で :39 以外に dispose 無し）で、接続は engine が回収されるまでで他の処理は使わない | 持ち越し前提なし。接続の寿命は engine 次第（dispose 無しのため回収待ち・未実測） |
| 11 | application_name: backend/app/database.py:15・:70、tasks/viewer_inventory_cache.py:117、tasks/tcg_extraction_recovery.py:170、tasks/tcg_extraction.py:790 | 接続開始時の `server_settings`（開始パケット） | **ある**（接続の一生の印としてスモークテスト[7]判別: database.py:10-11・:70）。RESET ALL の後も残る（m2: B・Bx で `salesanchor_backend` のまま） | 持ち越し前提あり・RESET ALL と衝突しない |
| 12 | statement_timeout・lock_timeout・jit | `SET LOCAL`／`set_config(..., true)` のみ: backend/app/ops/readonly_query.py:292（`SET LOCAL statement_timeout`）、services/tcg_product_roundtrip_svc.py:416-417（`lock_timeout='5s'`・`statement_timeout='30s'`）、services/tcg_extraction_record_svc.py:49-50（`lock_timeout='1s'`・`statement_timeout='5s'`）、services/tcg_analysis_review_svc.py:302・:304（jit）。LOCAL の無い statement_timeout・lock_timeout は **0 件** | 無い（取引で消える） | 持ち越し前提なし |
| 13 | `SET LOCAL app.is_operator = 'true'` / `set_config('app.is_operator','true',true)` / `set_config('app.tenant_id', …, true)` | backend/app/services/buyback_scraper/base.py:65・alert_checker.py:21・product_matcher.py:96、tcg_product_detail_svc.py:258、tcg_product_master_svc.py:562、tcg_product_roundtrip_svc.py:471・:481、routers/buyback_prices.py:392・:864、routers/buyback_alerts.py:60・:88・:121・:157、analysis_error_report_verify.py:25、tenant.py:1739、discord_gateway/reaction_writer.py:109 | 無い（取引で消える。commit・rollback で自動的に戻る） | 持ち越し前提なし。**この形が RESET ALL・返却時リセットの影響を受けない安全な形** |
| 14 | backend/app/services/tenant.py:1495 | `SET search_path = pg_catalog, public`（SECURITY DEFINER の関数定義の SET 節） | 関数の属性。セッション設定ではない | 対象外 |

---

## m1 (k) 1〜4 を 候補なし・A・B・Bx で再現（非同期 asyncpg・pool_size=1・max_overflow=0）

**方法**: pool_reset_measure.py:102-187。get_db（database.py:46-61）・clear_tenant_context（dependencies.py:403-405）・reset_operator_context（:485）と同じ形の関数で、各手順の**返却直後**に pg_stat_activity を読み（`mon()`・:34-45）、次の checkout で `is_operator`・`tenant_id`・`search_path` を読む。手順: 0 baseline ／ 1 set true→commit→reset→clear→close ／ 1b 手で clear＋commit ／ 2 set true→commit 無し→reset→clear→close ／ 3 set true→rollback→raise→clear→close ／ 4 tenant_id=5→commit→clear→close。

**結果（生の出力）**: `python pool_reset_measure.py m1`

```
--- m1 async cand=none
   0 baseline
     read   : {'pid': 2580, 'is_operator': None, 'tenant_id': None, 'search_path': '"$user", public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
   1 set true->commit->reset->clear->close
     read   : {'pid': 2580, 'is_operator': 'true', 'tenant_id': '', 'search_path': '"$user", public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
   1b after manual clear+commit
     read   : {'pid': 2580, 'is_operator': '', 'tenant_id': '', 'search_path': 'public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
   2 set true->(no commit)->reset->clear->close
     read   : {'pid': 2580, 'is_operator': '', 'tenant_id': '', 'search_path': 'public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
   3 set true->rollback->raise->clear->close
     read   : {'pid': 2580, 'is_operator': '', 'tenant_id': '', 'search_path': 'public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
   4 tenant_id=5->commit->clear->close
     read   : {'pid': 2580, 'is_operator': '', 'tenant_id': '5', 'search_path': 'public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
--- m1 async cand=A
   0 baseline
     read   : {'pid': 2581, 'is_operator': None, 'tenant_id': None, 'search_path': '"$user", public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
   1 set true->commit->reset->clear->close
     read   : {'pid': 2581, 'is_operator': 'true', 'tenant_id': '', 'search_path': '"$user", public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
   1b after manual clear+commit
     read   : {'pid': 2581, 'is_operator': '', 'tenant_id': '', 'search_path': 'public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
   2 set true->(no commit)->reset->clear->close
     read   : {'pid': 2581, 'is_operator': '', 'tenant_id': '', 'search_path': 'public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
   3 set true->rollback->raise->clear->close
     read   : {'pid': 2581, 'is_operator': '', 'tenant_id': '', 'search_path': 'public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
   4 tenant_id=5->commit->clear->close
     read   : {'pid': 2581, 'is_operator': '', 'tenant_id': '5', 'search_path': 'public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'ROLLBACK;'}
--- m1 async cand=B
   0 baseline
     read   : {'pid': 2582, 'is_operator': None, 'tenant_id': None, 'search_path': '"$user", public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle in transaction', 'xact_open': True, 'app': 'salesanchor_backend', 'last_query': 'RESET ALL'}
   1 set true->commit->reset->clear->close
     read   : {'pid': 2582, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle in transaction', 'xact_open': True, 'app': 'salesanchor_backend', 'last_query': 'RESET ALL'}
     読後    : {'state': 'idle in transaction', 'xact_open': True, 'app': 'salesanchor_backend', 'last_query': 'RESET ALL'}
   1b after manual clear+commit
     read   : {'pid': 2582, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle in transaction', 'xact_open': True, 'app': 'salesanchor_backend', 'last_query': 'RESET ALL'}
     読後    : {'state': 'idle in transaction', 'xact_open': True, 'app': 'salesanchor_backend', 'last_query': 'RESET ALL'}
   2 set true->(no commit)->reset->clear->close
     read   : {'pid': 2582, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle in transaction', 'xact_open': True, 'app': 'salesanchor_backend', 'last_query': 'RESET ALL'}
     読後    : {'state': 'idle in transaction', 'xact_open': True, 'app': 'salesanchor_backend', 'last_query': 'RESET ALL'}
   3 set true->rollback->raise->clear->close
     read   : {'pid': 2582, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle in transaction', 'xact_open': True, 'app': 'salesanchor_backend', 'last_query': 'RESET ALL'}
     読後    : {'state': 'idle in transaction', 'xact_open': True, 'app': 'salesanchor_backend', 'last_query': 'RESET ALL'}
   4 tenant_id=5->commit->clear->close
     read   : {'pid': 2582, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle in transaction', 'xact_open': True, 'app': 'salesanchor_backend', 'last_query': 'RESET ALL'}
     読後    : {'state': 'idle in transaction', 'xact_open': True, 'app': 'salesanchor_backend', 'last_query': 'RESET ALL'}
--- m1 async cand=Bx
   0 baseline
     read   : {'pid': 2583, 'is_operator': None, 'tenant_id': None, 'search_path': '"$user", public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'COMMIT;'}
   1 set true->commit->reset->clear->close
     read   : {'pid': 2583, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'COMMIT;'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'COMMIT;'}
   1b after manual clear+commit
     read   : {'pid': 2583, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'COMMIT;'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'COMMIT;'}
   2 set true->(no commit)->reset->clear->close
     read   : {'pid': 2583, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'COMMIT;'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'COMMIT;'}
   3 set true->rollback->raise->clear->close
     read   : {'pid': 2583, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'COMMIT;'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'COMMIT;'}
   4 tenant_id=5->commit->clear->close
     read   : {'pid': 2583, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': 'salesanchor_backend'}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'COMMIT;'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'COMMIT;'}
```

**判定**:

| 候補 | step1 後の is_operator | step4 後の tenant_id | 返却直後の state | 判定 |
|---|---|---|---|---|
| なし | `'true'` | `'5'` | idle | 前の値が残る（(k) の再現） |
| A | `'true'` | `'5'` | idle（last_query `ROLLBACK;`） | **効かない** |
| B | `''` | `''` | **idle in transaction**（last_query `RESET ALL`・xact_open=True） | 効くが取引を開けたまま |
| Bx | `''` | `''` | idle（last_query `COMMIT;`） | **効く** |

前の 2 回の食い違いの決着: 今回は 4 候補とも 1 回の台本で同じ接続形（pool_size=1）・返却直後の生の state を取った。A=idle・効かない、B=idle in transaction・効く、が正しい。A が効かない理由は SQLAlchemy 2.0.38 の pool/base.py（1405〜1432 行）の順序（ハンドラ → pool の rollback）と、返却直後の last_query `ROLLBACK;` から「`RESET ALL` が rollback される取引の中で流れた」と推定（取引の内側かどうかは台本では直接測っていない）。

---

## m2 RESET の後も application_name と server_settings が残るか

**方法**: pool_reset_measure.py:189-203。`SET application_name = 'hacked'` と `SET app.is_operator='true'` を commit し、返却後に `show application_name` と pg_stat_activity を読む。接続は database.py:13-16 と同じ `server_settings.application_name = salesanchor_backend`。

**結果（生の出力）**: `python pool_reset_measure.py m2`

```
--- m2 cand=none read={'pid': 2587, 'is_operator': 'true', 'tenant_id': '', 'search_path': '"$user", public', 'app': 'hacked'} show_application_name='hacked' pg_stat={'state': 'idle', 'xact_open': False, 'app': 'hacked', 'last_query': 'ROLLBACK;'}
--- m2 cand=A read={'pid': 2588, 'is_operator': 'true', 'tenant_id': '', 'search_path': '"$user", public', 'app': 'hacked'} show_application_name='hacked' pg_stat={'state': 'idle', 'xact_open': False, 'app': 'hacked', 'last_query': 'ROLLBACK;'}
--- m2 cand=B read={'pid': 2589, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': 'salesanchor_backend'} show_application_name='salesanchor_backend' pg_stat={'state': 'idle in transaction', 'xact_open': True, 'app': 'salesanchor_backend', 'last_query': 'RESET ALL'}
--- m2 cand=Bx read={'pid': 2590, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': 'salesanchor_backend'} show_application_name='salesanchor_backend' pg_stat={'state': 'idle', 'xact_open': False, 'app': 'salesanchor_backend', 'last_query': 'COMMIT;'}
```

**判定**: B・Bx は `RESET ALL` で `application_name` が接続開始時の `salesanchor_backend` に戻る（`server_settings` は開始パケットの値なので残る）。なし・A は 'hacked' のまま。→ RESET ALL を入れても database.py:15 の印（`salesanchor_backend`）は失われない。

---

## m3 RESET の後に引数つきの同じ問い合わせが 3 回以上通るか

**方法**: pool_reset_measure.py:205-221。`select cast(:x as int) + cast(:y as int)` を 6 回（毎回 checkout し直し、`SET app.is_operator='true'` を commit してから）。`prepared_statement_cache_size=0`（本番 database.py:14）と既定の文キャッシュの両方。

**結果（生の出力）**: `python pool_reset_measure.py m3`

```
--- m3 prod(cache=0) cand=none results=[1, 2, 3, 4, 5, 6]
--- m3 prod(cache=0) cand=A results=[1, 2, 3, 4, 5, 6]
--- m3 prod(cache=0) cand=B results=[1, 2, 3, 4, 5, 6]
--- m3 prod(cache=0) cand=Bx results=[1, 2, 3, 4, 5, 6]
--- m3 default-cache cand=none results=[1, 2, 3, 4, 5, 6]
--- m3 default-cache cand=A results=[1, 2, 3, 4, 5, 6]
--- m3 default-cache cand=B results=[1, 2, 3, 4, 5, 6]
--- m3 default-cache cand=Bx results=[1, 2, 3, 4, 5, 6]
```

**判定**: 8 通り（2 設定 × 4 候補）すべて 6 回とも通る（1〜6）。RESET ALL は準備済み文を消さない（DISCARD ALL とは違う）ことと矛盾しない結果。ADR-065 の InvalidCachedStatementError は本測定では出ていない（コンテナ再起動の再現は未実施）。

---

## m4 例外で rollback した場合と invalidate した場合にエラーや警告が出ないか

**方法**: pool_reset_measure.py:223-266。3 つの場合 × 4 候補: (a) `select 1/0` で失敗→`session.rollback()`→close ／ (b) 失敗→rollback せず close ／ (c) `connection.invalidate()` してから close。close で出た例外・warnings・`sqlalchemy` ロガー（WARNING 以上）・次の checkout で `select 1` が通るかを記録。

**結果（生の出力）**: `python pool_reset_measure.py m4`

```
--- m4 cand=none case=rollback_after_error close_exc=None warnings=[] logs=[] next_checkout_select1=1
--- m4 cand=none case=close_without_rollback_after_error close_exc=None warnings=[] logs=[] next_checkout_select1=1
--- m4 cand=none case=invalidate close_exc=None warnings=[] logs=[] next_checkout_select1=1
--- m4 cand=A case=rollback_after_error close_exc=None warnings=[] logs=[] next_checkout_select1=1
--- m4 cand=A case=close_without_rollback_after_error close_exc=None warnings=[] logs=[] next_checkout_select1=1
--- m4 cand=A case=invalidate close_exc=None warnings=[] logs=[] next_checkout_select1=1
--- m4 cand=B case=rollback_after_error close_exc=None warnings=[] logs=[] next_checkout_select1=1
--- m4 cand=B case=close_without_rollback_after_error close_exc=None warnings=[] logs=[] next_checkout_select1=1
--- m4 cand=B case=invalidate close_exc=None warnings=[] logs=[] next_checkout_select1=1
--- m4 cand=Bx case=rollback_after_error close_exc=None warnings=[] logs=[] next_checkout_select1=1
--- m4 cand=Bx case=close_without_rollback_after_error close_exc=None warnings=[] logs=[] next_checkout_select1=1
--- m4 cand=Bx case=invalidate close_exc=None warnings=[] logs=[] next_checkout_select1=1
```

**判定**: 12 通りすべて close 時の例外なし・warnings 空・ログ空・次の checkout 成功。invalidate は `terminate_only=True` でハンドラが何もしない形（台本 pool_reset_measure.py:50-53）。**限界**: (b) は `Session.close()` が先に接続の rollback を流す（推定・未測定）ので、「失敗した取引の中でハンドラの RESET ALL が流れて落ちる」経路は直接測っていない。ハンドラが例外を投げた場合の SQLAlchemy の扱いは未測定。

---

## m5 checkout→SELECT 1→checkin を 1000 回

**方法**: pool_reset_measure.py:268-284。pool_size=1・max_overflow=0・pool_pre_ping=True（本番 database.py:29 と同じ）・warm 50 回のあと 1000 回。ローカル接続（127.0.0.1）なのでネットワーク遅延は含まない。

**結果（生の出力）**: `python pool_reset_measure.py m5`

```
--- m5 cand=none n=1000 median_ms=0.997 p95_ms=1.565 mean_ms=1.095
--- m5 cand=A n=1000 median_ms=1.133 p95_ms=1.996 mean_ms=1.240
--- m5 cand=B n=1000 median_ms=1.118 p95_ms=1.804 mean_ms=1.210
--- m5 cand=Bx n=1000 median_ms=1.441 p95_ms=1.840 mean_ms=1.519
```

**判定**: Bx は なし より中央値 +0.44ms（0.997→1.441）、p95 +0.28ms（1.565→1.840）。B は中央値 1.118ms。1 リクエスト 1 checkout とすれば 1ms 台の増加。本番（遠隔 DB・負荷あり）での値は未測定。

---

## m6 同期エンジン（psycopg2）で同じ (m1)

**方法**: pool_reset_measure.py:286-341。r1 の #8〜#13 と同じ同期 engine（`postgresql+psycopg2`・pool_size=1・max_overflow=0）。pool_pre_ping は False と True の両方（#8・#9・#11・#12 は True）。手順は m1 の 1〜4（同期は 1b 無し）。各行は前の手順の続き（同じ接続）なので、step2 以降の `is_operator='true'` は step1 の残り。

**結果（生の出力）**: `python pool_reset_measure.py m6`

```
--- m6 sync(psycopg2) cand=none pool_pre_ping=False
   0 baseline: {'pid': 2631, 'is_operator': None, 'tenant_id': None, 'search_path': '"$user", public', 'app': ''} {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
   1 set true->commit->reset->clear->close
     read   : {'pid': 2631, 'is_operator': 'true', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
   2 set true->(no commit)->reset->clear->close
     read   : {'pid': 2631, 'is_operator': 'true', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
   3 set true->rollback->raise->clear->close
     read   : {'pid': 2631, 'is_operator': 'true', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
   4 tenant_id=5->commit->clear->close
     read   : {'pid': 2631, 'is_operator': 'true', 'tenant_id': '5', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
--- m6 sync(psycopg2) cand=A pool_pre_ping=False
   0 baseline: {'pid': 2632, 'is_operator': None, 'tenant_id': None, 'search_path': '"$user", public', 'app': ''} {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
   1 set true->commit->reset->clear->close
     read   : {'pid': 2632, 'is_operator': 'true', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
   2 set true->(no commit)->reset->clear->close
     read   : {'pid': 2632, 'is_operator': 'true', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
   3 set true->rollback->raise->clear->close
     read   : {'pid': 2632, 'is_operator': 'true', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
   4 tenant_id=5->commit->clear->close
     read   : {'pid': 2632, 'is_operator': 'true', 'tenant_id': '5', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
--- m6 sync(psycopg2) cand=B pool_pre_ping=False
   0 baseline: {'pid': 2633, 'is_operator': None, 'tenant_id': None, 'search_path': '"$user", public', 'app': ''} {'state': 'idle in transaction', 'xact_open': True, 'app': '', 'last_query': 'RESET ALL'}
   1 set true->commit->reset->clear->close
     read   : {'pid': 2633, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle in transaction', 'xact_open': True, 'app': '', 'last_query': 'RESET ALL'}
     読後    : {'state': 'idle in transaction', 'xact_open': True, 'app': '', 'last_query': 'RESET ALL'}
   2 set true->(no commit)->reset->clear->close
     read   : {'pid': 2633, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle in transaction', 'xact_open': True, 'app': '', 'last_query': 'RESET ALL'}
     読後    : {'state': 'idle in transaction', 'xact_open': True, 'app': '', 'last_query': 'RESET ALL'}
   3 set true->rollback->raise->clear->close
     read   : {'pid': 2633, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle in transaction', 'xact_open': True, 'app': '', 'last_query': 'RESET ALL'}
     読後    : {'state': 'idle in transaction', 'xact_open': True, 'app': '', 'last_query': 'RESET ALL'}
   4 tenant_id=5->commit->clear->close
     read   : {'pid': 2633, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle in transaction', 'xact_open': True, 'app': '', 'last_query': 'RESET ALL'}
     読後    : {'state': 'idle in transaction', 'xact_open': True, 'app': '', 'last_query': 'RESET ALL'}
--- m6 sync(psycopg2) cand=Bx pool_pre_ping=False
   0 baseline: {'pid': 2634, 'is_operator': None, 'tenant_id': None, 'search_path': '"$user", public', 'app': ''} {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
   1 set true->commit->reset->clear->close
     read   : {'pid': 2634, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
   2 set true->(no commit)->reset->clear->close
     read   : {'pid': 2634, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
   3 set true->rollback->raise->clear->close
     read   : {'pid': 2634, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
   4 tenant_id=5->commit->clear->close
     read   : {'pid': 2634, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
--- m6 sync(psycopg2) cand=none pool_pre_ping=True
   0 baseline: {'pid': 2635, 'is_operator': None, 'tenant_id': None, 'search_path': '"$user", public', 'app': ''} {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
   1 set true->commit->reset->clear->close
     read   : {'pid': 2635, 'is_operator': 'true', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
   2 set true->(no commit)->reset->clear->close
     read   : {'pid': 2635, 'is_operator': 'true', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
   3 set true->rollback->raise->clear->close
     read   : {'pid': 2635, 'is_operator': 'true', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
   4 tenant_id=5->commit->clear->close
     read   : {'pid': 2635, 'is_operator': 'true', 'tenant_id': '5', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
--- m6 sync(psycopg2) cand=A pool_pre_ping=True
   0 baseline: {'pid': 2636, 'is_operator': None, 'tenant_id': None, 'search_path': '"$user", public', 'app': ''} {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
   1 set true->commit->reset->clear->close
     read   : {'pid': 2636, 'is_operator': 'true', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
   2 set true->(no commit)->reset->clear->close
     read   : {'pid': 2636, 'is_operator': 'true', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
   3 set true->rollback->raise->clear->close
     read   : {'pid': 2636, 'is_operator': 'true', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
   4 tenant_id=5->commit->clear->close
     read   : {'pid': 2636, 'is_operator': 'true', 'tenant_id': '5', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'ROLLBACK'}
--- m6 sync(psycopg2) cand=B pool_pre_ping=True
   0 baseline: {'pid': 2637, 'is_operator': None, 'tenant_id': None, 'search_path': '"$user", public', 'app': ''} {'state': 'idle in transaction', 'xact_open': True, 'app': '', 'last_query': 'RESET ALL'}
   1 set true->commit->reset->clear->close ERR ProgrammingError (psycopg2.ProgrammingError) set_session cannot be used inside a transaction (Background on this error at: https://sqlalche.me/e/20/f405) | 返却直後: None
--- m6 sync(psycopg2) cand=Bx pool_pre_ping=True
   0 baseline: {'pid': 2639, 'is_operator': None, 'tenant_id': None, 'search_path': '"$user", public', 'app': ''} {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
   1 set true->commit->reset->clear->close
     read   : {'pid': 2639, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
   2 set true->(no commit)->reset->clear->close
     read   : {'pid': 2639, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
   3 set true->rollback->raise->clear->close
     read   : {'pid': 2639, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
   4 tenant_id=5->commit->clear->close
     read   : {'pid': 2639, 'is_operator': '', 'tenant_id': '', 'search_path': '"$user", public', 'app': ''}
     返却直後: {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
     読後    : {'state': 'idle', 'xact_open': False, 'app': '', 'last_query': 'COMMIT'}
```

**判定**: 同期でも なし・A は 'true'・tenant_id '5' が残る（A は効かない）。B は値は戻るが idle in transaction で、`pool_pre_ping=True` だと**次の checkout が `ProgrammingError: set_session cannot be used inside a transaction`** で落ちる（pre_ping=True の B 行の ERR）。Bx は pre_ping の有無にかかわらず値が戻り idle。→ 同期・非同期の両方で候補は Bx だけが成り立つ。

---

## m7 commit の後に同じ session で文脈を読む（dependencies.py:274-281 と同形）

**方法**: pool_reset_measure.py:343-376。1 つの AsyncSession で `SET search_path = tenant_005, public`／`SET app.tenant_id = '5'`／`SET app.is_operator = ''`（dependencies.py:274-281 と同じ 3 文）→ `pg_backend_pid()`（pid_set）→ `commit()` → **文脈を入れ直さず同じ session で** `pg_backend_pid()`・`current_setting(...)` を読む。毎回の前に「別の要求役」が別テナント 777 の文脈（search_path・tenant_id）を commit して接続に残す（5 本を同時に握って温める。pool_size=1・2 のときは 1・2 本）。pool_size=1・2・20（20 は本番 database.py:26-27 と同じ pool_size=20・max_overflow=10）× 候補なし・Bx。各 20 回。

**結果（生の出力）**: `python pool_reset_measure.py m7`

```
--- m7 pool_size=1 max_overflow=0 cand=none warm=1 trials=20
    pid同じ=20/20  tenant_id=5が残る=20/20  別テナント777が見えた=0/20  文脈が空=0/20  search_path=tenant_005=20/20
    1回目の生の値: {'pid_set': 2643, 'pid_after': 2643, 'op': '', 'tid': '5', 'sp': 'tenant_005, public'}
    全回の tenant_id: ['5', '5', '5', '5', '5', '5', '5', '5', '5', '5', '5', '5', '5', '5', '5', '5', '5', '5', '5', '5']
--- m7 pool_size=1 max_overflow=0 cand=Bx warm=1 trials=20
    pid同じ=20/20  tenant_id=5が残る=0/20  別テナント777が見えた=0/20  文脈が空=20/20  search_path=tenant_005=0/20
    1回目の生の値: {'pid_set': 2644, 'pid_after': 2644, 'op': '', 'tid': '', 'sp': '"$user", public'}
    全回の tenant_id: ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
--- m7 pool_size=2 max_overflow=0 cand=none warm=2 trials=20
    pid同じ=0/20  tenant_id=5が残る=0/20  別テナント777が見えた=20/20  文脈が空=0/20  search_path=tenant_005=0/20
    1回目の生の値: {'pid_set': 2645, 'pid_after': 2646, 'op': None, 'tid': '777', 'sp': 'tenant_777, public'}
    全回の tenant_id: ['777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777']
--- m7 pool_size=2 max_overflow=0 cand=Bx warm=2 trials=20
    pid同じ=0/20  tenant_id=5が残る=0/20  別テナント777が見えた=0/20  文脈が空=20/20  search_path=tenant_005=0/20
    1回目の生の値: {'pid_set': 2647, 'pid_after': 2648, 'op': None, 'tid': '', 'sp': '"$user", public'}
    全回の tenant_id: ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
--- m7 pool_size=20 max_overflow=10 cand=none warm=5 trials=20
    pid同じ=0/20  tenant_id=5が残る=0/20  別テナント777が見えた=20/20  文脈が空=0/20  search_path=tenant_005=0/20
    1回目の生の値: {'pid_set': 2649, 'pid_after': 2650, 'op': None, 'tid': '777', 'sp': 'tenant_777, public'}
    全回の tenant_id: ['777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777', '777']
--- m7 pool_size=20 max_overflow=10 cand=Bx warm=5 trials=20
    pid同じ=0/20  tenant_id=5が残る=0/20  別テナント777が見えた=0/20  文脈が空=20/20  search_path=tenant_005=0/20
    1回目の生の値: {'pid_set': 2654, 'pid_after': 2655, 'op': None, 'tid': '', 'sp': '"$user", public'}
    全回の tenant_id: ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
```

**表（20 回中の回数）**:

| pool_size | 候補 | commit 後も同じ pid | 文脈（tenant_id=5）が残る | 別テナント 777 が見えた | 文脈が空 |
|---|---|---|---|---|---|
| 1 | なし | 20 | 20 | 0 | 0 |
| 1 | Bx | 20 | 0 | 0 | 20 |
| 2 | なし | 0 | 0 | **20** | 0 |
| 2 | Bx | 0 | 0 | 0 | 20 |
| 20（max_overflow=10） | なし | 0 | 0 | **20** | 0 |
| 20（max_overflow=10） | Bx | 0 | 0 | 0 | 20 |

**判定**:
- いまの実装（候補なし）は pool_size=1 なら commit の後も同じ接続なので文脈が残って**偶然動く**。pool_size=2 以上だと commit で接続を返し次の文が別の接続を取り、**別の要求が残した別テナントの search_path・tenant_id が見えた**（20/20）。本番は pool_size=20。QueuePool は既定で FIFO（database.py:24-32 に use_lifo の指定なし）。
- この測定は「温めた接続の全部に 777 が残っている」作った状態で、実際の本番の確率は未測定。
- Bx は同じ箇所で文脈が**空**になる（20/20）。別テナントは見えないが、文脈を前提にする文は失敗する（search_path が `"$user", public`・tenant_id が空 → RLS で 0 件／schema 名なしの tenant 表は relation does not exist のはず。この「はず」の部分は m7 では文脈を読んだだけで、tenant 表への実際の SELECT は測っていない）。

---

## m8 commit の後に文脈を入れ直さず同じ session を使う箇所

**方法**: 2 本の構文木走査を台本にした。
- `docs/handoff/s1-rls-stage5/m8_scan.py backend/app`: 関数ごとに `<db|session|…>.commit()` の後、次の commit か `set_tenant_context`・`reset_tenant_context`・`set_tenant_context_sync` 呼び出しまでの間に、同じ session への操作（execute・add・flush・refresh 等）または session を引数に渡す呼び出しがあるものを拾う（分岐・ループは見ず行番号順。拾い過ぎ寄り）。出力: 74 件。
- `docs/handoff/s1-rls-stage5/m8_scan2.py backend/app`: 中で commit する補助関数（session を引数に取る・名前で突き合わせ・395 個）を呼んだ後に同じ session を使う箇所。名前の取り違えがあり得る近似。出力: 51 件。

各件は commit 行から後続の行を開いて、触る表を読んだ。記号: **Q** = schema 名つき（変数 `{schema}`・`tenant_table_ref`）／**P** = `public.` つき（TCG_SCHEMA は `"public"`: backend/app/services/tcg_analyzer_svc.py:58 ほか）／**T** = tenant 表を schema 名なしで触る（別テナントの search_path で読み書きしうる）／**R** = 後続は文脈の SET だけ（表は触らない）／**N** = 誤検出（commit が分岐の終端で後続は別の経路）／**未確認** = 本文を読んでいない。

### 第 1 走査（74 件）

| 場所（commit 行 → 後続） | 関数 | 後続が触る表 | 判定 |
|---|---|---|---|
| backend/app/discord_gateway/ticket_channel_writer.py:249 → :280・:311 | process_ticket_channel_message | `{schema}.lead_attachments`・`{schema}.meta_messages`（:282・:313） | Q |
| backend/app/routers/admin.py:90 → :95 | register_tenant | なし（reset_operator_context） | R。commit の後に reset だけ（m1 step1 と同形: 'true' が残りうる） |
| backend/app/routers/auth.py:1418 → :1430・:1442 | login_request_poll | `public.auth_login_requests`（:1432） | P（:1422 で return するので別経路: N 寄り） |
| auth.py:1448 → :1451・:1454 | login_request_poll | register_device・_complete_pending_login → `public.user_trusted_devices`・`public.users` | P |
| auth.py:1166 → :1170 | passkey_login_verify | `public.webauthn_credentials`（:1172）。:1167 で raise するので別経路 | P（N 寄り） |
| auth.py:172 → :173 | register_user | `db.refresh(user)`。ORM `User` は `__tablename__ = "users"` で schema 指定なし（backend/app/models.py:23） | **未確認**（schema 指定なしの ORM 表。tenant の search_path に `users` があるかは未確認） |
| auth.py:457 → :458 | self_login | _notify_new_request → web_push.list_targets → `public.user_push_subscriptions`・`public.user_trusted_devices`（backend/app/services/web_push.py:124-125） | P |
| auth.py:528 → :535・:542〜:544 | self_refresh | `public.users`・devices.*（`public.user_trusted_devices`・`public.auth_refresh_tokens`） | P |
| auth.py:545 → :551〜:563 | self_refresh | 同上（auth/devices.py:227-364 すべて `public.`） | P |
| backend/app/routers/fx_rate_admin.py:147 → :149・:157 | refresh_fx_rate | :149 は R。:157 は `public.app_fx_rate_history`（:158-159） | P。:149 は commit の後に reset だけ |
| backend/app/routers/inventory_offers.py:641 → :652 | create_offer | _load_offer（:94-101）→ `_BASE_SELECT`: `public.inventory` ほか | P（JOIN 先の schema 指定は :60-74 の先頭 15 行のみ確認。以降は未確認） |
| inventory_offers.py:738 → :740 | update_offer | 同上 | P（同上） |
| backend/app/routers/leads.py:1643 → :1645〜:1704 | get_message_attachment_url | commit 直後に `_reset_ctx(db, tenant_id)`（:1645）で入れ直し済み。後は `tenant_table_ref(...)`（:1650） | Q（入れ直しあり。走査は別名 `_reset_ctx` を拾えず） |
| leads.py:2666 → :2668〜 | send_lead_image_message | commit 直後に `_reset_ctx`（:2668）。後は tenant_table_ref 系 | Q（同上） |
| backend/app/routers/ops.py:681 → :684・:481 → :483・:633 → :637・:281 → :283・:566 → :568 | _set_control・annotate_incident・close_incident・ingest_alertmanager・report_human_incident | `_clear_operator`（ops.py:70-75: `rollback → reset → commit`） | R。**確定させる形**で (k) を避けている |
| backend/app/routers/ops_case.py:295・:379・:405・:532・:651 → `_safe_clear`/`_clear_operator` | create_ticket・decide_request・post_audit・post_report・post_unmask_request | 同上（ops_case.py:107-112・:177-182） | R（同上） |
| ops_case.py:638 → :640・:642 | post_unmask_request | :639 で raise する分岐。後続は `ai_cloud_meta.build_columns`・`pg_catalog.*`（:543 の関数）と `ops_case.unmask_requests`（:644） | N 寄り。表は Q |
| backend/app/routers/ops_error_reports.py:149 → :154・:189 → :194 | post_error_report_event・post_error_report_reanalyze | なし（reset_operator_context） | R。commit の後に reset だけ（'true' が残りうる） |
| backend/app/routers/super_admin_ai_jobs.py:234 → :236・:238 | put_ai_job | `public.ai_job_choices`（backend/app/services/ai_assignment.py:56-60）・`public.llm_usage_events` | P |
| backend/app/routers/super_admin_llm_budget.py:174 → :180 | upsert_budget | `public.tenant_llm_budgets`・`public.tenants` | P |
| super_admin_product_formats.py:201 → :202、:142 → :143 | replace_product_format_games・update_product_format | `public.product_format_game_links`（:40-41） | P |
| super_admin_quantity_units.py:141 → :143・:147 | update_quantity_unit | `public.unit_condition_links`・`public.product_line_available_units` | P |
| super_admin_suppliers.py:983 → :990 | create_supplier_knowledge_link | `public.supplier_knowledge_links`・`public.knowledge_rules` | P |
| backend/app/routers/super_admin_tenants.py:161 → :173〜:188 | delete_tenant_physical | テナント schema の DROP（名前つき）・`public.tenants` の行削除・`db.begin()` 内で set→削除→reset（:176-181: 取引内で確定する） | P・Q。reset は begin ブロック内で commit されるので残らない |
| super_admin_viewers.py:400 → :401・:402、:275 → :284 | reissue_signup_code_endpoint・update_viewer_template_endpoint | `public.viewer_accounts`・`public.viewer_message_templates`・`public.users`（viewer_admin.py:50-98・viewer_message_templates.py） | P |
| backend/app/routers/viewer.py:565・:193・:201・:205・:392・:475 | viewer_billing_form_submit・viewer_login・viewer_password_reset_confirm・viewer_signup | `public.viewer_login_events`・`public.viewer_billing_profiles` 他（routers/viewer.py:107 `_record_event`・services/viewer_billing_form.py:170） | P |
| backend/app/services/analysis_error_report_svc.py:179 → :184・:201 → :206 | create_report・_record_notify_result | なし（reset_operator_context） | R。commit の後に reset だけ |
| **backend/app/services/calendar_service.py:303 → :306** | create_event | `UPDATE calendar_events SET sync_status = 'failed' ...`（:308）。tenant 表を schema 名なし | **T**（except 側の経路。:272 で commit 後に reset_tenant_context 済みだが、:303 の commit が失敗した後の :306 は入れ直しなし） |
| backend/app/services/line_analysis_v102_svc.py:1572 → :1576・:1577、:1578 → :1580 | run_v102_analysis | `{analyzer.TCG_SCHEMA}.extraction_jobs`（:834-860）・_merge_supplier_products（TCG_SCHEMA） | P |
| backend/app/services/tcg_analyzer_svc.py:1923・:1938・:1949 | analyze_extraction_job | `{tenant_schema}.analysis_results`・`.extraction_items`・`public.products`・`public.conditions`・`public.units`（backend/app/services/tcg_unit_recovery_svc.py:757・:1034・:1093。引数は TCG_SCHEMA = "public"） | P |
| backend/app/services/tcg_condition_review_svc.py:415 → :417〜:451 | save_condition_review | `public.conditions`（:420）・`{TCG_SCHEMA}.item_corrections`（:434）。:416 で return する分岐 | P（N 寄り） |
| backend/app/services/tcg_distribution_svc.py:792・:823 | create_target・update_target | `{TCG_SCHEMA}.tcg_distribution_targets`・`public.viewer_accounts`（:739-740） | P |
| backend/app/services/tcg_product_import_svc.py:621 → :628 | commit_import | `{TCG_SCHEMA}.tcg_product_import_jobs`（:546 finish_job） | P |
| backend/app/services/tcg_product_master_svc.py:845・:907 → :849・:910〜:954 | _run_reanalyze_sync | `{TCG_SCHEMA}.analysis_runs`・`.analysis_results`・`.extraction_items`（:836・:918-919） | P |
| tcg_product_master_svc.py:642 → :645・:655 | create_product | `public.products`（:647）・find_code_collisions（表は未確認） | P（find_code_collisions は未確認） |
| backend/app/tasks/data_deletion.py:166 → :177〜:186・:191 → :207 | process_data_deletion | schema 名を引数で渡す `_delete_*_in_tenant(session, schema, …)`・`public.data_deletion_logs`（:209） | Q・P |
| backend/app/tasks/refresh_meta_tokens.py:283・:296・:313・:323・:334・:343 | _refresh_one_row | `{schema_name}.audit_logs`・`{schema_name}.tenant_meta_config`（:139-238）。`app.tenant_id` は commit 後に同じ接続が再利用されるときだけ残る | Q（RLS 文脈は偶然・上の r2 #5） |
| backend/app/tasks/verify_meta_subscriptions.py:190・:199・:214・:223・:234 | _verify_one_row | `{schema_name}.audit_logs`（:107） | Q（同上） |
| backend/app/tasks/tcg_extraction.py:381・:402・:615 | _run_extraction・_run_recorded_extraction | `{TCG_SCHEMA}.extraction_jobs`・analysis_* | P |
| backend/app/tools/prompt_ab.py:601 → :602 | run_ab | `public.llm_usage_events`（:131-135） | P |

第 1 走査の合計: 74 件のうち **T 確定 = 1 件（calendar_service.py:303→306）**。R（commit の後に reset だけで 'true' が残りうる）= admin.py:90・fx_rate_admin.py:147・ops_error_reports.py:149・:189・analysis_error_report_svc.py:179・:201 の 6 件。`_clear_operator` 経由（確定させる形）= ops.py 5 件・ops_case.py 5 件。残りは P または Q または N。ORM 表で schema 指定なしの **auth.py:172 は未確認**。

### 第 2 走査（51 件・近似。補助関数の中の commit）

読んで確かめた分と、未読の分を分ける。

| 場所 | 後続が触る表 | 判定 |
|---|---|---|
| **backend/app/routers/customer_priority.py:178 → :180〜190** | label_lead_messages（backend/app/services/priority_scoring.py:254-314）が :313 で commit し、入れ直しなし。後続の `SELECT … FROM message_labels`（customer_priority.py:185）は tenant 表を schema 名なし | **T 確定**（priority_scoring.py:281・:296 も schema 名なし） |
| **backend/app/services/priority_scoring.py:389 → :391・:392・:408** | 同じ label_lead_messages の commit（:313）の後に `get_label_counts_for_lead`・`get_tenant_calibration`（`FROM tenant_calibrations`: priority_scoring.py:142）・`INSERT INTO customer_scores`（:411） | **T 確定** |
| backend/app/routers/tenant_commission_settings.py:148 → :157 | `_create_default` の中で commit 直後に `reset_tenant_context`（同ファイル :105-106）。後続は schema 名なしの `tenant_commission_settings`（:152） | N（入れ直し済み） |
| backend/app/services/calendar_service.py:450 → :457・:461 | `cal_svc.update_event`（backend/app/services/google_calendar.py:410）は commit しない（名前の取り違え）。後続 `UPDATE calendar_events`（:421）は schema 名なし | N（commit 無し） |
| backend/app/services/discord_notifier.py:182 → :190・:208 | `public.tenant_llm_budgets`・`public.tenants`（:222・:254・:274） | P |
| backend/app/routers/auth.py:422・:762・:1615 | `_count_login_failure` の後の `devices.*`・`public.*` | P |
| backend/app/routers/ops_case.py:169 | `_safe_clear` | R |
| backend/app/routers/tcg_line_import.py:420・backend/app/services/line_source_names.py:87・backend/app/services/tcg_line_import_svc.py:552 | `reset_operator_context` だけ | R（commit の後に reset だけ。commit は補助関数の中） |
| backend/app/routers/tcg_product_import.py:244・backend/app/services/tcg_product_import_svc.py:579・:591・:606・:620・backend/app/services/tcg_review_csv_svc.py:252・backend/app/services/tcg_distribution_svc.py:1127・:1139・backend/app/services/tcg_analyzer_svc.py:1425・backend/app/tasks/tcg_extraction.py:470・:476・:626・:746・backend/app/services/line_analysis_v102_svc.py:546・:556 | `{TCG_SCHEMA}`（= "public"）つきの表 | P（走査に出た行を個別には開いていないものを含む。TCG_SCHEMA が "public" の前提で P と置いた） |
| backend/app/routers/webhook.py:825・:855・:939 | :855 の `_persist_meta_message` は commit 後に `reset_tenant_context`（webhook.py:638-639）。:939 の後は `clear_tenant_context`（:956）。write_conversation_log の表は未確認 | 一部入れ直しあり。write_conversation_log は**未確認** |
| backend/app/services/message_translator.py:541・:553・:562・:573 | `table_ref` 引数（呼び出し側が schema 名つきで渡す） | Q（translate_inbound の中身は未確認） |
| backend/app/discord_gateway/outside_ticket_notice.py:175、backend/app/line_device_admin.py:34、backend/app/line_import_admin.py:158、backend/app/routers/analysis_error_reports.py:36、backend/app/routers/calendar.py:559、backend/app/routers/integrations.py:901、backend/app/routers/item_corrections.py:157、backend/app/services/analysis_error_report_verify.py:167・:182、backend/app/services/google_webhook.py:405、backend/app/tasks/google_calendar_sync.py:26・:62・:63、backend/app/tasks/tcg_extraction_recovery.py:512-515 | 本文を開いていない | **未確認**（近似走査の候補のみ。google_webhook.py:405・google_calendar_sync.py:26・:73 の後続は `clear_tenant_context`） |

**限界**: (1) 走査は commit が直接見える関数と、名前で突き合わせた補助関数だけ。クラス内のメソッド経由・デコレータ経由（例: `@operator_writes` 系）・別ファイルで commit する呼び出し連鎖は拾えない。(2) 分岐を見ないので拾い過ぎ（N）と、ループ末尾の commit を取りこぼす可能性がある。(3) 第 2 走査の「未確認」行は本文を読んでいない。

**判定（m8 全体）**: 別テナントの search_path で tenant 表を schema 名なしで読み書きしうる箇所は、**確定 3 箇所**（calendar_service.py:306、customer_priority.py:180-190、priority_scoring.py:389-415）と、**未確認**（auth.py:172 の ORM `users`、webhook.py の write_conversation_log、第 2 走査の未読行）。他の大多数は `public.` 明示か schema 名つきなので、別テナントの search_path では取り違えない。ただし `public.` 表でも RLS が `app.tenant_id`・`app.is_operator` で判定する表は、返却時リセット（Bx）で commit 後に文脈が空になると結果が変わりうる（どの表が RLS かは本調査では未確認）。
