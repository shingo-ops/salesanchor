# recon: CI の試験どうしが共有 DB でぶつかって main が赤になる件

状態: 調査済み（Opus・2026-11-26〜27）。基準: `origin/main` 24354620e。
KGI の承認: PO 2026-11-26「1」（5種類すべてを直す設計にする）。

## 1. 観測事実（main の Backend Tests 直近60回）
- 期間 2026-11-16〜11-26。`gh run list --workflow "Backend Tests" --branch main --limit 60` の結果は success 48・failure 9・cancelled 3（最後の試行だけを数えた）。
- 落ちた9回の `--log-failed` を全部保存して読んだ（/tmp/CC報告ファイル/collisions/f_<run>.log・counts.txt）。9回とも、落ちた理由は試験どうしのぶつかりだった。

| 種類 | 落ちた回（run） | 落ちた試験 | 相手（DB の記録の `Process N:` 行） |
|---|---|---|---|
| A 調べたが無い | 45823366830・45346102865 | `backend/tests/test_product_blank_confirmations_pg.py::test_write_requires_operator_flag` | migration `migrations/20261016_190000_create_product_blank_confirmations.sql` を丸ごと流す処理 |
| B 請求書の表 | 44096043994・44203948916・44849233250・44854143246 | `backend/tests/test_tenant_issuer_tables_pg.py::test_new_tenant_shape_equals_migration_and_rules_hold` | ADR-1061 便2-2a の public 9表の migration と、`tenant_963.tenant_issuer_profiles` を消す文 |
| C カルテ | 44024988826・44686062120・44854143246 | `backend/tests/test_assistant_karte_pg.py::test_read_meet_available_failed_sql_keeps_transaction_usable` | `DELETE FROM public.users` と「Phase 1 再設計: スタッフ・bot」の migration |
| D 役割 | 44024988826・44343066606（PR の run 45752817882 の1回目でも） | `backend/tests/test_ops_case_router.py`・`backend/tests/ops/test_ops_case_report_kind_migration.py` | 共通の役割（`ai_reader_cloud` など）が途中で消える |
| E テナント998 | 44686062120 | `backend/tests/test_rls_tenant_meta_config.py::test_rls_visible_when_app_tenant_id_matches` | テナント998の schema を消す文 |

- CI は `-n auto --dist=loadfile` で動く。1つのファイルは1つの係が順に流す。別のファイルは同時に流れる。
- 根拠の DB は、多くの試験が同じ `jarvis_test_db`（database 16384）を使う。

## 2. 種類 D（役割が消える）— 仕組みは確定
1つのクラスタの中では、役割（ROLE）はデータベースをまたいで共通である。次の6ファイルは、どれも「始めたときに役割が無ければ、終わったときに消す」という後片付けをしている。

| ファイル:行 | 始めに確かめる | 終わりに消す |
|---|---|---|
| `backend/tests/ops/test_ai_cloud_views.py:84-96` | `ai_reader`・`ai_reader_cloud`・`aic_owner` | `DROP ROLE IF EXISTS {r}`（:96） |
| `backend/tests/ops/test_ai_job_assignments_db.py:70-82` | `ai_reader`・`ai_reader_cloud` | :82 |
| `backend/tests/ops/test_ops_case_db.py:53-60,87-105` | `_ROLES`（7つ） | :102 |
| `backend/tests/ops/test_ops_case_report_kind_migration.py:43,66-69,104-108` | `_ROLES`（6つ） | :106 |
| `backend/tests/test_ops_case_router.py:39,129-132,187-192` | `_ROLES`（6つ） | :190 |
| `backend/tests/ops/test_ai_ro_views.py:68-69,98-99` | `ai_reader` | :99 |

- 起きる順番: 係1のファイルが始まる（役割が無いので「消す」と記録）→係2のファイルが役割を作って使い始める→係1が終わって役割を消す→係2が「役割が無い」で落ちる。
- 実例: PR の run 45752817882 の1回目で、`backend/tests/ops/test_ops_case_report_kind_migration.py:83` で作った直後の :96 で `role "ai_reader_cloud" does not exist`。
- 役割を作る migration はどれも冪等である（例 `migrations/20261024_100100_create_ai_reader_cloud_role.sql:7-20`。無ければ作る。あれば属性を確かめるだけ）。
- `backend/tests/test_tenant_isolation_daily_check.py:217,254` も `DROP ROLE` を流すが、自分で作った名前の役割だけを消す。共通の役割ではないので対象外。
- 未観測の近い危険: 共通の役割の属性を一時的に変える試験が2か所ある（`backend/tests/ops/test_ai_cloud_views.py:460-468` BYPASSRLS、`backend/tests/ops/test_ops_case_db.py:621-627`）。その間に別の係が役割の migration を流すと、属性違いで止まる。直近60回の記録には出ていない。

## 3. 種類 A（調べたが無い）— 相手は確定・直し方は追加の調べが要る
- 相手の確定: run 45823366830 の2回目の DB の記録（/tmp/CC報告ファイル/main45823366830-try2-full.log:16438-16460）に、次の2行がある。
  - `Process 7031: INSERT INTO public.product_blank_confirmations ...`
  - `Process 7030: -- ADR-1020 便1: ...`（migration のファイルを丸ごと流している）
- この migration を共有 DB に流すのは3か所ある: `backend/tests/test_product_blank_confirmations_pg.py:28`、`backend/tests/test_tcg_product_list_pg.py:88-92`、`backend/tests/test_tcg_work_matching_integration.py:373`。
  - work_matching は使い捨ての別 DB で流している（同ファイル :393-400）。
  - blank 自身は同じ係で順に流れる。
  - 残る相手は `backend/tests/test_tcg_product_list_pg.py` だけである。
- `backend/tests/test_tcg_product_list_pg.py` の `product_db`（:96-118）は、1つのトランザクションの中で public の表の DDL を流し続け、最後に巻き戻す。
  - 手順: `:76` で `ALTER TABLE public.products` を流す。`:88-92` で blank の migration を流す。
  - このトランザクションが取る順番待ちの札は「共有」である（`pg_advisory_xact_lock_shared`・:108-111）。
  - PostgreSQL 16 では、ALTER TABLE は「明記が無ければ ACCESS EXCLUSIVE」を取る（公式 sql-altertable.html、Context7 で確認）。
- 起きる順番:
  1. list_pg が products を押さえる（7030）。
  2. blank が `product_blank_confirmations` に書く（7031）。外部キーを確かめるため、products の RowShareLock を待つ。
  3. list_pg が blank の表の AccessExclusiveLock を待つ。
  4. 互いに待ち合いになる。
- 未確認（直し方を決めるのに要る）:
  - list_pg の DDL を巻き戻さない形（1回だけ確定させる形）にしたとき、`:64-92` の migration がすべて2回流しても壊れないか。
  - 他の DML 試験に同じ危険があるか。

## 4. 種類 B・C・E — 仕組みは未確定
- B: 請求書の試験（`backend/tests/test_tenant_issuer_tables_pg.py:297-340`）は、表を消して流し直す部分を排他の札 `public_bootstrap_lock`（`backend/tests/rls_bootstrap.py:60-80`）の中で行う。
  - 相手の ADR-1061 の migration を共有 DB に流すのは、`backend/tests/rls_bootstrap.py:383` の `bootstrap_tenant_schema` だけである（同ファイル :41-49）。こちらも同じ札の中で流す。
  - 同じ排他の札を2つが同時に持つことはできないはずである。それでも待ち合いが起きた理由は、まだ確かめていない。
- C: 「Phase 1 再設計: スタッフ・bot」の migration を流すのがどこか、まだ確かめていない。`DELETE FROM public.users` を流す側は `backend/tests/test_assistant_karte_pg.py` と見られる。どちらが札を持つかも、まだ確かめていない。
- E: テナント998の重なりは、以前から残っている件である。覚え書き test_lock_collisions「次の便」に「test_rls_tenant_meta_config.py と test_countries_master.py の 998/999 の重なり（札なしで作り・消す）」とある。

## 5. 既存 ADR の検索結果
- `git grep -il "xdist|bootstrap_lock|advisory_lock|DROP ROLE" docs/adr` → `docs/adr/ADR-1024-ai-readonly-db-path.md` だけが当たった。:80 は本番の戻し方（`DROP ROLE ai_reader`）であり、試験の決まりではない。
- 試験の並列・共有 DB の決まりを定める ADR は見つからなかった。決まりは覚え書き test_lock_collisions にある（札の順番は tenant → public。DROP は `public_bootstrap_lock` の中）。

## 6. 追記（2026-11-27・便2〜5の調べ。Opus が origin/main 33f2112f9 と失敗の記録で確かめた）
起点の記録: クラウドの調べ `release/ci-test-shared-collisions-recon2`（04b5cc9ba）の調べの記録（recon-bin2-5）。そこで説明できなかった B は、下の 6-1 で決着した。

### 6-1. B と C は PR 5669 で既に直っている
- PR 5669（`release/ci-test-lock-fix-1121`）は 2026-11-21 14:50 UTC に合流した（bb6c4d63c）。その中の cc649a9dc が次の2つを `public_bootstrap_lock` の中へ入れた。
  - B: `backend/tests/test_tenant_issuer_tables_pg.py` の DROP・ALTER・migration の塊（変更前は札の外の `admin_engine.begin()`）。
  - C: `backend/tests/test_assistant_karte_pg.py` の `_cleanup`（`public.users` などの DELETE）と `_setup` の INSERT。
- 失敗の記録（`/tmp/CC報告ファイル/collisions/f_<run>.log`）の起きた時刻:

| run | 種類 | 起きた時刻（UTC） |
|---|---|---|
| 44096043994 | B | 11-17 13:46 |
| 44203948916 | B | 11-17 23:58 |
| 44849233250 | B | 11-21 01:17 |
| 44854143246 | B | 11-21 02:07 |
| 44024988826 | C | 11-17 05:33 |
| 44686062120 | C と E | 11-20 06:11 |
| 44343066606 | D | 11-18 |
| 45346102865 | A | 11-24 07:11 |
| 45823366830 | A | 11-26 12:50 |

- 合流後（11-21 15:00 UTC 以降に作られた main の回）は25回: 成功21・失敗2・取り消し2。失敗2回はどちらも A。B と C は0回。
- B の相手（記録から）: `tenant_963.tenant_issuer_profiles` を消す文が ACCESS EXCLUSIVE を待ち、相手は準備の migration `migrations/20261112_150000_create_viewer_contract_public_tables.sql` の後で `public.tenant_settings` に INSERT していた（`create_tenant_schema` の段）。
- C の相手: カルテの `public.users` の DELETE と、「Phase 1 再設計: スタッフ・bot」の段（`create_tenant_schema`）。

### 6-2. C と同じ形で、まだ札の外にあるもの（落ちたのはまだ見ていない）
- `backend/tests/test_calendar_sync_tenant_reset_pg.py`（テナント978）
  - `_cleanup`（:72-84）: `calendar_events`・`public.tenant_google_calendar_config`・`public.users` の DELETE を、札なしの `admin_engine.begin()` で流す。直す前のカルテと同じ形。呼び元は `_teardown`（:136-138）だけ。
  - `_setup`（:87-）: migration は札の中（:95）。その後の `public.users` と `public.tenant_google_calendar_config` の INSERT・DELETE（:100-127）は札の外。
- `backend/tests/test_staff_join_discord.py`（テナント973・psycopg2・autocommit）
  - `_cleanup_pg`（:582-594）: tenant_973 のスキーマを CASCADE で消す文と、`public.users`・`public.tenants`・`public.permissions` の DELETE を札なしで流す。呼び元は `shared_pg` の後片付け（:615）と `_prep_pg`（:634）。
  - `_prep_pg` の `public.permissions` と `public.users` の INSERT（:635-646）も札の外。
- 2回の C の失敗の相手はカルテだった。カルテが札の中に入ったので、今はこの2つが同じ相手とぶつかる形が残る。

### 6-3. A の仕組み（今も起きている）
- run 45346102865: `test_product_blank_confirmations_pg::test_write_requires_operator_flag` の `INSERT INTO public.product_blank_confirmations` が products の RowShare を待つ。相手は `test_tcg_product_list_pg` の `product_db` で、`migrations/20261016_190000_create_product_blank_confirmations.sql` の ACCESS EXCLUSIVE を待っていた。
- `backend/tests/test_tcg_product_list_pg.py`:
  - `product_db`（:95-120）は、巻き戻す transaction（:106 で始め :118 で rollback）の中で `create_product_schema`（:47-92）を毎回流す。札は共有の xact 札（:110-113）。
  - `create_product_schema` は使い捨てスキーマ（`product_csv_test_<uuid>`）の表に加えて、public の DDL も毎回流す: `_PUBLIC_PRODUCTS_DDL`（:50-54）、085・086（:63-64）、`20260921_060000`（:65）と product_kinds の行（:67-72）、`20260921_120000`（`ALTER TABLE public.products`・:74）、`20260921_070000`（:75）、type_master の行（:77）、`20260919_020000`（:79）、phase3 `20260920_010000`（:82-84）、`20260922_030000` と `20261016_190000`（:86-92）。
  - 巻き戻すまで、これらの ACCESS EXCLUSIVE を持ち続ける。そのあいだにほかの worker が子の表を書いて products を待つと、互いに待ち合う。
- public の DDL は、使い捨てスキーマの名前を受け取らない（`.replace("tenant_004", schema)` は :56-62 の3本と `_rewire_keyword_fks(schema)`（:78）だけ）。そのため public の分を transaction の外へ出しても、使い捨てスキーマの中身は変わらない。
- phase3 は `nspname LIKE 'tenant_%'` のスキーマだけを回す（`migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql:23-30`）。使い捨てスキーマは `product_csv_test_` で始まるので、この試験の表には何もしない。今は、ほかの worker の tenant_* の表を巻き戻す前提で書き換え、札を持ち続けている。
- 見張り `backend/tests/test_tenant_loop_migration_guard.py:284-287` は、この試験を `own_database`（使い捨て DB）に分類している。実際は共有 DB `jarvis_test_db`（:97 の assert）なので、分類が実物と違う。
- 手本: `backend/tests/rls_bootstrap.py:111-150` の `ensure_product_packagings`。DDL を transaction の外の別接続で、札の中で1回だけ確定させる。docstring（:112-124）に「巻き戻す transaction の中で DDL を流すと deadlock する」とある。
- 共有 DB に確定させても困らないか:
  - 085・086・`20260921_060000`・`20260921_070000`・type_master の行は、準備（`backend/tests/rls_bootstrap.py:19-38`・:293-295）が既に確定させている。
  - `_PUBLIC_PRODUCTS_DDL`・`20260919_020000`・`20261016_190000` は、`backend/tests/test_product_blank_confirmations_pg.py:229-236` が札の中で確定させている。`20260922_030000` は `backend/tests/test_product_format_game_links_pg.py:27` が流す。
  - product_kinds の行（TCG・FIGURE・GOODS）を数える試験は無い（`git grep "count(\*) FROM public.product_kinds" -- backend/tests` が0件）。

### 6-4. E の仕組み
- `backend/tests/test_rls_tenant_meta_config.py` の `setup_schemas`（:78-157）は、札なしの `admin_engine.begin()` で tenant_998・tenant_999 のスキーマと表・RLS・GRANT を作る（:87-150）。`tenant_meta_config` は `public.users` を外部キーで指す（:111）。後片付けで2つのスキーマを札なしで消す（:155-157）。
- run 44686062120 で「ERROR at teardown of test_rls_visible_when_app_tenant_id_matches」として落ちた。相手は、当時札の外だったカルテの `public.users` の DELETE。
- `backend/tests/test_countries_master.py`（:146-176）も同じ tenant_998・tenant_999 を札なしで作り、消さない。
- 空いている番号: 946・947 は、`git grep -w -E "946|947"` で試験・migration・scripts・.github のどこにも出てこない。

### 6-5. 見張りを作るかの見積もり
- 共有 DB の後片付けを札の外で流す関数を機械で探す試し（関数の中にスキーマを消す文か `public.` の DELETE があり、札の語が無いもの）: 53ファイル・76関数が当たった（使い捨て DB や SQLite を含む）。1つずつ分類が要るため、本テーマでは作らない（design §10）。
