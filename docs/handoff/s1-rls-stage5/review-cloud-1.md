# 設計審査（クラウド 1 回目）— S1 段階⑤ design.md・recon.md・ADR-1069

- 審査役: Claude（クラウドの定期実行・Architect 役）。設計を書いた本人ではない立場で、設計書の主張を実物のコードと照らした。
- 対象: `origin/release/s1-rls-stage5-design` HEAD `21acb5f0fffc95a7a60602cbc1de70069a7dac88`（基準 origin/main `44a6ccce1`。設計の枝は docs だけの 2 コミットなので、コードの行番号は recon の基準と同じ版）。
- 読んだもの: docs/handoff/s1-rls-stage5/design.md・recon.md、docs/adr/ADR-1069-shared-master-tables-rls.md、docs/specs/tenant-rls/kgi.md 段階⑤、手本 docs/handoff/s1-rls-stage4/design.md。
- 測定: (k) だけ、サンドボックスで立てた使い捨ての PostgreSQL 16.15（localhost の UNIX ソケット、DB 名 kmeasure）で行った。本番・secret には触っていない。(g) の文法は使い捨て DB で流さず、読んで判断した（指示の範囲が (k) だけのため）。
- 探し方: 書く箇所は SQL の動詞でなく表の名前（line_conditions・line_units・tcg_note_master・tcg_status_master・tcg_product_categories・payment_fee_settings・public.conditions・public.units・修飾なしの conditions・units）で grep -rn し、前後をファイルで読んだ。

## (a) 6 表とビュー 2 つへ書く箇所

- 方法: `grep -rnE "line_conditions|line_units|tcg_note_master|tcg_status_master|tcg_product_categories|payment_fee_settings" backend/app scripts --include=*.py --include=*.sh` で 32 ファイル。会社の画面・運営画面・schemas・run_all を除いた全行を読んだ。ビューは `(INTO|UPDATE|FROM|JOIN|TABLE)\s+(public\.)?(conditions|units)\b` で探した。表名を f 文字列で組み立てる書込（`INSERT INTO {table}`・`UPDATE {table}`）も別に探した。SQLAlchemy のモデル（`__tablename__`）も探した。
- 結果:
  - 解析・定期の処理・起動時の処理は読むだけ。例: /root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/app/services/tcg_analyzer_svc.py:1116・:1224・:1323（tcg_note_master・tcg_status_master の SELECT）、/root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/app/services/gemini_raw_copy_v102_product_first.py:157-165、/root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/app/services/v102_buyback_unit_svc.py:84、/root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/app/tasks/rule_test.py:44（Celery。読むだけ）、/root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/app/tasks/bundle_bulk_monitor.py:33（JOIN で読むだけ）、/root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/app/services/tcg_product_import_svc.py:249（取込は区分を SELECT で引くだけ）、/root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/app/services/tcg_work_comparison_svc.py:141（`SELECT to_jsonb(t)` で読むだけ）。
  - ビュー経由の書込は会社の画面（conditions.py・units.py）と運営画面だけ。他は FROM・JOIN で読むだけ（tcg_analyzer_svc.py:73・:697、tcg_condition_review_svc.py:360・:399・:420・:441（UPDATE の中の副問い合わせで読むだけ）、line_analysis_v102_svc.py:879・:889、v102_human_decisions_svc.py:76、tcg_unit_recovery_svc.py:1113・:1134、tcg_parallel_report_svc.py:48・:64、tcg_result_order.py:31）。
  - 表名を組み立てる書込の 9 か所（tcg_product_roundtrip_svc.py:527、tcg_product_detail_svc.py:302、discord_webhook_sender.py:161、tenant_profile.py:133、archives.py:146（対象は orders・leads・quotes・invoices だけ、archives.py:31）、super_admin_dex.py:101・:108・:148、tools/reextract_v6_with_v102.py:727）は 6 表に当たらない。
  - モデルの `__tablename__` は 0 件。main.py の該当行（:88・:117・:459・:611）は router の登録だけ。
  - scripts 側: /root/worktrees/salesanchor/release-s1-rls-stage5-review/scripts/migrate-pipeline-data-to-public.sh:130 は注記だけ。scripts/migration-guard/* は一覧。scripts/run_all_migrations.sh は移行の登録。
- 判定: ○。design §3 の 23 本と会社の画面（recon §4-1）以外に、文脈なしで 6 表・ビュー 2 つに書く箇所は backend/app・scripts に見つからなかった（Celery・起動時・取込を含む）。

## (b) 23 本がすべて引数 db を持ち、operator_writes で包めるか

- 方法: 6 ファイルの `@router.(post|patch|delete)`・`async def`・`db: AsyncSession = Depends(get_db)` の行を grep し、Python の ast で関数ごとの commit の位置と、その後の execute を数えた。
- 結果: 23 本すべて、design の行番号どおりに `async def` があり、2 行下前後に `db: AsyncSession = Depends(get_db)` がある。
  - super_admin_conditions.py :167/:169・:239/:242・:275/:277・:377/:380、super_admin_units.py :146/:148・:178/:181・:213/:215・:382/:385、super_admin_note_master.py :164/:166・:197/:200・:232/:234・:334/:337、super_admin_status_master.py :161/:163・:206/:209・:259/:261・:360/:363、super_admin_product_categories.py :135/:137・:235/:238・:293/:296・:328/:330、super_admin_payment_fee_settings.py :88/:90・:121/:124・:156/:158（左が関数・右が db の行。いずれも /root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/app/routers/ の下）。
  - 包み方の手本 /root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/app/routers/super_admin_suppliers.py:58-75 は `sig.bind(*args, **kwargs).arguments["db"]` で名前の db を取る。23 本とも名前は `db`。
  - 6 ファイルに別の接続（AsyncSessionLocal・get_admin_db・AdminSessionLocal・BackgroundTasks）を使う所は 0 件。取込の確定（例 super_admin_conditions.py:386-430）は同じ db の 1 つの取引で書き、:424 で commit。
  - 6 ファイルの他の書込（別名の表の入口 super_admin_conditions.py:462・:499、super_admin_units.py:257・:294）は 6 表でなく別名の表に書く（recon §4-2 の対象外の記載と一致）。
- 判定: ○（包める）。カードで「`@router.*` を外側、`@operator_writes` を内側」の順を明記すること（手本 super_admin_suppliers.py:140-144 の順）。

## (c) 行の鍵の全数

- 方法: `grep -rnE "FOR (UPDATE|SHARE|NO KEY UPDATE|KEY SHARE)|NOWAIT|SKIP LOCKED|with_for_update|LOCK TABLE" backend/app scripts --include=*.py`。
- 結果: 49 行。注記・docstring の 8 行（ai_assignment.py:158、v102_human_decisions_svc.py:380、leads.py:3238、contacts.py:714・:715・:737、invoices.py:248、staff_join.py:286）を除くと 41 件で、recon §5 の 41 件と一致。
  - 6 表・ビューに行の鍵が当たるのは /root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/app/services/tcg_condition_review_svc.py:399（public.conditions）と /root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/app/services/tcg_product_detail_svc.py:210（`public.{table}`。:39 で tcg_product_categories を含む）の 2 か所だけ。
  - 似ていて当たらないもの: tcg_analyzer_svc.py:1549 と tcg_condition_review_svc.py:390 の `FOR SHARE OF ei, ej, sm`（sm は source_messages）、tcg_product_detail_svc.py:180（type_master）・:196（tcg_manufacturers。LOOKUPS は :33-35）、tcg_line_import_svc.py:378（`FOR UPDATE OF sc`＝supplier_channels）、tcg_product_master_svc.py:694・:764（products）。
  - 表ごとの鍵 tcg_product_roundtrip_svc.py:427 の `LOCK TABLE` は RLS が効かない（recon §5 と同じ判断）。
- 判定: ○。

## (d) _operator_writes を dependencies.py に移すと循環 import が起きるか

- 方法: /root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/app/auth/dependencies.py の import 行（:1-30）と、/root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/app/database.py の import を読んだ。
- 結果: dependencies.py は app.auth.self_tokens・app.auth.system_roles・app.cache・app.client_ip・app.database・app.models だけを読み、routers を読まない。database.py は dependencies を関数の中で遅れて読む（database.py:60）。移す関数が要るのは標準の functools・inspect と、同じファイルの set_operator_context（:454）・reset_operator_context（:471）だけ。super_admin_suppliers.py は既に dependencies から import している（:34）。`operator_writes` の名は backend/app に未使用（grep 0 件）。
- 判定: ○（循環は起きない。dependencies.py に `import functools`・`import inspect` を足す必要がある）。
- 付記: 仕入先の `@_operator_writes` は 5 本（super_admin_suppliers.py:143・:194・:230・:444・:772）。依頼文の「6 本」とは数が違う。

## (e) 状態の確定の SET LOCAL

- 方法: /root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/app/services/tcg_condition_review_svc.py:373-459 と呼び出し元 /root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/app/routers/item_corrections.py:145-162、試験 /root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/tests/test_tcg_condition_review.py:404-432 を読んだ。
- 結果:
  - 関数の最初の文 :386 の SELECT で AsyncSession が自動で取引を始める。:386〜:399 の間に commit は無い。commit は :415（同じ要求の再送）と :457（保存）、失敗は :460 の rollback。→ :399 の直前の `SET LOCAL` は :386 から続く同じ取引の中で流れ、:402・:434 以降の書込まで効き、commit・rollback で消える。
  - 呼び出し元は get_db と require_super_admin だけ（item_corrections.py:148-149）。保存後の `_after_condition_review_saved`（item_corrections.py:162）は commit 後の新しい取引なので、SET LOCAL の効き目は無い（6 表に書かない）。
  - 試験 :414 は `'FOR SHARE OF ei, ej, sm' in str(statement)` で特定の文だけを待つ。新しい `SET LOCAL` の文にはこの文字列が無いので、確かめは崩れない。この試験の接続は RLS_ADMIN_DATABASE_URL（superuser。:49）。test_item_corrections.py:190・:206 と test_v102_value_overrides.py:283 は save_condition_review を丸ごと差し替えるので影響しない。
- 判定: ○。

## (f) 商品詳細の保存の SET LOCAL を :156 の直後へ移す影響

- 方法: /root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/app/services/tcg_product_detail_svc.py:150-258 で、:156〜:258 の間に読む表を列挙し、各表のポリシーを migrations で読んだ。
- 結果:
  - 間で読む表: products（:158・`_snapshot` :82）、product_search_keywords・product_exclude_keywords・product_blank_confirmations・product_packagings・quantity_units（`_snapshot`）、type_master（:180）、tcg_manufacturers（:196）、tcg_product_categories・product_kinds（:210）。
  - products の SELECT ポリシーは `tenant_id IS NULL OR tenant_id = app.tenant_id` で、運営の印を見ない（/root/worktrees/salesanchor/release-s1-rls-stage5-review/migrations/20260626_130000_force_rls_public_products.sql:9-13）。UPDATE は `CASE WHEN tenant_id IS NULL THEN is_operator ELSE tenant_id = app.tenant_id END`（:23-27）。→ 運営の印を早く張っても、会社の商品は見えるようにも鍵が掛かるようにもならない。変わるのは「共用の商品に :158 の FOR UPDATE が実際に掛かる」ことだけ（関数の docstring :155「商品ごとに書込を直列にする」の意図どおり）。
  - product_blank_confirmations・product_packagings の読取は `USING (true)`（20261016_190000:24-26、20261018_100000:73-75）、書込は FOR ALL の運営だけ（:29-32、:78-81）。読める範囲は変わらない。
  - 残りの表（product_search_keywords・product_exclude_keywords・quantity_units・type_master・tcg_manufacturers・product_kinds）は `POLICY … ON public.<表>` が migrations に 0 件。
  - 入口は運営専用の 1 か所だけ（tcg_product_import.py:338、依存は :330-331）。
- 判定: ○（運営として見える範囲が広がって困る所は見つからなかった）。

## (g) 古い移行 3 本と WITH の追加

- 方法: 4 ファイルのビューの行を grep で読んだ。使い捨て DB では流していない（読んで判断）。
- 結果:
  - 行番号は recon §3 と一致: /root/worktrees/salesanchor/release-s1-rls-stage5-review/migrations/20260925_010000_conditions_add_match_type.sql:52（DO の `IF EXISTS (information_schema.views …)` の中、:48-53）、/root/worktrees/salesanchor/release-s1-rls-stage5-review/migrations/20260925_020000_conditions_add_def_unit_note.sql:42（条件なし）、/root/worktrees/salesanchor/release-s1-rls-stage5-review/migrations/20261017_120000_line_conditions_value_rank.sql:47（DO の中、:43-48）。20260922_080000 は :32（units）・:83（conditions）の `CREATE VIEW`（無いときだけ）。
  - 3 本とも作り直すのは public.conditions だけ。public.units を作り直す移行は migrations・scripts・backend/app に 0 件（`VIEW … units` の grep は 080000:32 だけ）。→ units は ⑤-1 の新しい移行で一度付ければ、デプロイで消えない。design §2-1 の「古い移行 3 本」は conditions だけに当たる。
  - 文法: `CREATE OR REPLACE VIEW public.conditions WITH (security_invoker = true) AS TABLE public.line_conditions;` は PostgreSQL 16 の CREATE VIEW の書式（名前・WITH・AS 問い合わせの順。`TABLE x` は問い合わせ）に合う（読んで判断。未実測）。
  - 冪等: `CREATE OR REPLACE` は何度流しても同じ。:52・:47 の DO の中の条件も変わらない。列の順は `TABLE line_conditions` の展開で、列の追加は表の末尾なので、置き換えの「既存の列の前に入れない」制約を今と同じく満たす（今の文と同じ条件）。
  - 値の書込の見張り（/root/worktrees/salesanchor/release-s1-rls-stage5-review/scripts/check-migration-value-writes.py:122 は変更されたファイルの追加された行を見る）: 足す行は `CREATE OR REPLACE VIEW` で、許す型（:39-46。VIEW は :43）に当たる。4 ファイルとも reference-allowlist.tsv・value-write-allowlist.tsv・dryrun-exclusions.tsv に載っていない（grep 0 件）ので、sha256 の一致の確かめにも当たらない。
- 判定: ○（文法・冪等は読んで判断。実測は ⑤-1 の CI で確かめる、design §6 のとおり）。

## (h) migration-test.yml の PUBLIC_SQL と変更 SQL のジョブ

- 方法: `sed -n` で /root/worktrees/salesanchor/release-s1-rls-stage5-review/.github/workflows/migration-test.yml の該当行を読んだ。
- 結果:
  - 行番号は recon §6 と一致: PUBLIC_SQL の始まり :480、tcg_status_master :510、units（表）:528、line_units :543、tcg_note_master :556、line_conditions :697、`CREATE OR REPLACE VIEW public.conditions` :713、tcg_product_categories :718、payment_fee_settings :862（tenant_id は :864）、PUBLIC_SQL の終わり :1041。5 表の定義（:510-523・:528-536・:543-551・:556-570・:697-710・:718-726）に tenant_id 列は無い（awk で列の行を抜いた）。
  - 古い移行が流れる条件: 検出 :1194-1245 で `git diff --name-only --diff-filter=d BASE HEAD` の `^migrations/[0-9][0-9][0-9].*\.sql$`（`{schema}` を含まないもの）を `sort` して一覧にする（:1230-1232）。:1362-1370 で 1 回目、:1372-1380 で 2 回目を流す。→ ⑤-1 で古い移行 3 本を直すと、3 本は名前の順（20260925_010000 → 20260925_020000 → 20261017_120000 → 新しい移行）で、PUBLIC_SQL の状態の上に 2 回ずつ流れる。ジョブ自体は paths-filter（:44-53）で migrations/** の変更があるときだけ動く。
  - PUBLIC_SQL の注記（:541・:654・:695）は 20260925_020000 がこのジョブで流れる前提で書かれている。20260925_010000・20261017_120000 がいまの PUBLIC_SQL の上で通るかは流していない（未確認）。
- 判定: ○（design §3-2・§6 の記述と一致。通るかは ⑤-1 の CI で確かめる、という design の扱いで足りる）。

## (i) check_public_tenant_rls.py の拡張の位置

- 方法: /root/worktrees/salesanchor/release-s1-rls-stage5-review/scripts/check_public_tenant_rls.py（87 行）と migration-test.yml:2105-2126 を読んだ。
- 結果: 全件ドライランは :2115（`--rounds 2`、DB は jarvis_report）、点検は次の step の :2125（同じ jarvis_report）。全件ドライランは失敗で job を落とす（:2108 の注記）。6 表とビューを作る移行（20260919_020000・20260920_0X0000・20260922_080000・20260925_0X0000・20261002_1X0000・20261017_120000）は dryrun-exclusions.tsv に 0 件。点検の道具は許可一覧を :20 で import し、`run()`（:46-71）で落とす。許可一覧を読むのはこの道具だけ（grep で .py・.yml・.sh に他 0 件）。
- 判定: ○（2 周の後のビューの状態を見る位置にある）。
- 付記: 今の道具は「許可一覧にあるが見つからない表」を参考に出すだけで落とさない（:56・:63-64）。便ごとに許可一覧から 2 行消すのを忘れても CI は緑のまま。K9-3 は件数を目で数える判定なので足りるが、気付きにくい（軽微-3）。

## (j) design §5 の受入条件が○×で判定できるか

- 結果:
  - K7-1・K7-2・K7-3・K8-1・K9-2・K9-3: 読む物と数え方が決まっていて○×で判定できる。
  - K8-3「解析の結果件数が減らない」: 反映前の同じ長さの時間帯との比較で、投稿の数が違えば結果件数も変わる。「投稿の数の差も一緒に書く」とあるが、どこまでの差なら○かが無い（要修正-1）。
  - K9-1「PostgreSQL のログに 6 表それぞれ violates row-level security policy が 1 件以上」: CI の Backend Tests の PostgreSQL（services のコンテナ）のサーバーのログを誰がどう読むかが書かれていない。試験の側で 42501 を確かめているなら、試験の名前（6 表・ビュー経由）が緑であることで判定する方が○×にしやすい（要修正-2）。
  - K8-2: 会社の画面の保存が「0 回なら使われず未観測」は○でも×でもない状態を認める書き方。kgi.md KGI-8 は「運営画面と会社画面の 6 つのマスタの保存が 200」と書いていて、design K8-2（会社の画面はログの 4xx・5xx で見る）と食い違う（軽微-1）。
- 判定: △（2 か所を直せば○）。

## (k) 運営の印が接続に残るか（実測）

- 方法: サンドボックスで PostgreSQL 16 を起動し（`pg_ctlcluster 16 main start`）、Python 3.12 の venv に本番と同じ版の SQLAlchemy 2.0.38・asyncpg 0.31.0 を入れた（/root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/requirements.txt と同じ版）。get_db（database.py:46-61）・clear_tenant_context（dependencies.py:386-405 の 3 文）・_operator_writes（super_admin_suppliers.py:58-75）と同じ形の関数を書き、`pool_size=1, max_overflow=0` で同じ接続を使い回させて、終わった後に新しい session で `pg_backend_pid()` と `current_setting('app.is_operator', true)` を読んだ。台本は /tmp/claude-0/-home-user-salesanchor/89a0339b-9421-5764-afe4-84994a56abfe/scratchpad/measure_k.py（リポジトリには入れていない）。
- 結果（生の出力）:

```
sqlalchemy 2.0.38 asyncpg 0.31.0
PostgreSQL 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1) on x86_64-pc-linux-gnu, compiled by gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0, 64-bit
0 baseline: pid=1358 is_operator=None tenant_id=None search_path='"$user", public'
1 set true->commit->reset->clear->close: pid=1358 is_operator='true' tenant_id='' search_path='"$user", public'
1b after manual clear+commit: pid=1358 is_operator='' tenant_id='' search_path='public'
2 set true->(no commit)->reset->clear->close: pid=1358 is_operator='' tenant_id='' search_path='public'
3 set true->rollback->raise->reset->clear->close: pid=1358 is_operator='' tenant_id='' search_path='public'
4 tenant_id=5->commit->clear->close: pid=1358 is_operator='' tenant_id='5' search_path='public'
```

  - 1 行目（set true → handler の commit → finally の reset → get_db の clear → close）の後、同じ接続（pid 1358）で `app.is_operator='true'` が残った。commit の後の `SET app.is_operator = ''` と clear の 3 文は新しく自動で始まった取引の中で流れ、close のときの rollback で 3 文とも取り消される（search_path も `public` に戻らず残っている）。
  - commit しない終わり方（2・3 行目）では残らない。
  - 参考（4 行目）: 会社の文脈（`SET app.tenant_id`）も commit の後は同じ仕組みで接続に残る。段階⑤より前からある形。
- 数え: design §3 の 23 本と仕入先の `@_operator_writes` 5 本の計 28 本で、最初の commit の後に流す文（execute・add・flush・merge）は 0 本（ast で数えた。commit の行: conditions :230・:266・:290・:424、units :169・:204・:227・:424、note_master :188・:223・:245・:382、status_master :197・:250・:273・:407、product_categories :158・:279・:319・:342、payment_fee_settings :112・:147・:169、suppliers :185・:221・:246・:542・:803）。→ 28 本とも、成功して commit すると、その接続は `app.is_operator='true'` のままプールに戻る。
- 判定: ×（design §6「運営の文脈がつなぎの使い回しで残る」の対処「operator_writes は finally で reset。get_db の終わりの clear_tenant_context が二重の守り」は、commit した後には効かないことを実測した）→ 重大-1。

## 指摘

### 重大

- **重大-1 運営の印が接続に残る（(k) の実測）**。design §6 の対処は成り立たない。⑤-2〜⑤-4 で 23 本を `@operator_writes` で包むと、運営画面のマスタを保存するたびに、その接続が `app.is_operator='true'` のままプールに戻る。次にその接続を使う要求のうち、get_current_tenant を通るもの（dependencies.py:281 で毎回空にする）は困らないが、get_db だけを使う入口・定期の処理は運営として共用の行（6 表・suppliers・products の共用行など）を書ける状態になる。
  - さらに design §4「運営画面: … 終わった後に `app.is_operator` が空に戻る（段階④ ④-5 の試験の型）」の試験の型は、同じ session の中で close の前に読むので（例 /root/worktrees/salesanchor/release-s1-rls-stage5-review/backend/tests/test_suppliers_rls.py:343・:381）、取り消される前の '' を読んで緑になる。今の型では残りを見つけられない。
  - 直し方の案（設計担当が選ぶ）: (ア) `operator_writes` を `SET LOCAL`（または `set_config('app.is_operator','true', true)`）で張る形にする。28 本とも commit の後に文が 0 本なので、取引の終わりで自動で消える形にしても書込は変わらない。(イ) get_db の finally で clear の後に commit する（ADR-131 の直し。全要求に効くが影響が広い）。(ウ) プールに返すときに接続の上で `RESET app.is_operator` 等を取引の外で流す。いずれにしても、試験は「get_db と同じ順で終えた後、同じ接続（pool_size=1）を取り直して読む」形に変える。
  - 同じ形は段階②b・④の既存の入口（super_admin_suppliers.py の 5 本、super_admin_llm_budget.py:151・:173、super_admin_phase_switch.py:128、services の set_operator_context の利用 line_source_names.py:125、analysis_error_report_svc.py:159・:190、tcg_line_import_svc.py:671、routers/tcg_line_import.py:459）にもある。直しを本段階に入れるか、別の段にするかを design に書くこと。

### 要修正

- **要修正-1 K8-3 の○×の線が無い**。投稿の数で割った比（結果件数／投稿の数）で比べる、または「解析の失敗（エラー）件数が増えない」に置き換えるなど、判定の線を決める。
- **要修正-2 K9-1 の判定の場所**。CI の services の PostgreSQL のサーバーのログは今の流れで読まれていない（未確認：test.yml にログを出す step があるかは確かめていない）。試験の名前（6 表それぞれ・ビュー経由）が緑、で判定する形に直すか、ログを出す step を足すことを書く。
- **要修正-3 design §6 と ADR-1069 の文言**。重大-1 の結論に合わせ、§6 の「二重の守り」の行と §4 の運営画面の試験の型を直す。

### 軽微

- **軽微-1** kgi.md KGI-8 の「会社画面の 6 つのマスタの保存が 200」と design K8-2（会社の画面はログの 4xx・5xx で見る・0 回なら未観測）が食い違う。どちらかに揃える。
- **軽微-2** design §2-1 の「古い移行 3 本」は 3 本とも public.conditions の作り直しで、public.units を作り直す移行は無い（(g)）。units は「新しい移行で一度付ければ消えない」と一言足すと、カードを書く人が units の古い移行を探さずに済む。
- **軽微-3** check_public_tenant_rls.py は許可一覧にあって見つからない表を落とさない（:56・:63-64）。便ごとの許可一覧の 2 行の消し忘れは CI で止まらない。カードの合格条件に「点検の出力に『許可一覧にあるが見つからない』が 0 行」を足すとよい。
- **軽微-4** (b) カードで、デコレータの順（`@router.*` が外、`@operator_writes` が内）と、dependencies.py に `functools`・`inspect` の import を足すことを明記する。
- **軽微-5** 依頼文の「仕入先の _operator_writes 6 本」は実物では 5 本（:143・:194・:230・:444・:772）。

## 未確認

- (g) の文法・冪等、(h) の 20260925_010000・20261017_120000 がいまの PUBLIC_SQL の上で通るか: 使い捨て DB で流していない（指示の範囲が (k) だけのため）。design §6 どおり ⑤-1 の CI で確かめる。
- 重大-1 で、get_db だけを使う入口のうち、残った運営の印で実際に共用の行を書けてしまう道がどれだけあるか（全数は数えていない）。
- 要修正-2 の CI の PostgreSQL のログの扱い（.github/workflows/test.yml を読んでいない）。

VERDICT: REVISE
