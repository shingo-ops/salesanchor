# 値を書く移行 52本の分け方（段5 5-1・§5-5）

- 状態: 設計案（Opus 作成・2026-11-15・第3版）。PO の承認待ち。承認の前に 5-1 の実装カードは出さない。
- 事実の出どころ: `docs/handoff/migration-runner-redesign/recon-5-1a/p11-detail.md`（52本の中身・commit `a6d59cc36`）、`docs/handoff/migration-runner-redesign/recon-5-0a/p12.md`（依存する試験）、登録の順番 `scripts/run_all_migrations.sh`、本番の構造の読み取り（reader 鍵・表と列の有無だけ。行の中身は読まない。生出力 `/tmp/CC報告ファイル/deploy-lock-1113/p11-prod-tables.txt`・`p11-prod-recheck.txt`・`p11-prod-recheck-cols.txt`。後の2つは問い合わせの文を AUDIT 行に残した。2026-11-15 16:02-16:03 JST）、番号と登録行の対応 `/tmp/CC報告ファイル/deploy-lock-1113/p11-midrun.txt`。
- 固める判断は、5-3 の記録を始めた後は取り消せない（記録の後は流し終えたファイルの書き換えを CI で止める。§5-7）。無効にする書き換えは 5-3 より前にしかできない。

## 1. 分け方の決まり

5-3 の記録が始まれば、本番ではどのファイルも二度と流れない。そのため、毎回流れて行が戻る害は、どちらに分けても 5-3 で止まる。分け方で変わるのは次の2つ。
- 5-1 から 5-3 までの間（と 5-3 の起点の回）に、本番で戻る・上書きが続くか。
- 新しい環境（CI の使い捨て DB・新しい会社・稽古の環境）に、その値が入るか。

そこで、次の3つが全部そろう物だけを「無効にする」とし、残りは「固めてよい」とする。
1. 本番で、毎回の反映が今も、反映の後まで残る表の行を戻す・値を上書きする。
2. 値の出どころが昔のデータの写し・一度きりの直しで、新しい環境では入れる意味が無い（または、その表をアプリがどこからも名指ししない）。
3. そのファイルを読んで流す試験が無い（p12.md の当たりが「なし」）。

判断は、反映が終わった後の本番の形ではなく、そのファイルが流れる時点の形で行う。tenant_004 では、毎回の反映の途中で古い表が作り直されるため（下の §1-1）。

### 1-1. tenant_004 の古い表は、毎回の反映の途中で作り直されて消える

- `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:40-44` は「tenant_004.audit_log が有り、かつ tcg_products が無い」ときだけ飛ばす。
- tenant_004.audit_log は毎回 `migrations/20260921_050000_drop_tenant004_pipeline_tables.sql:51`（登録 `scripts/run_all_migrations.sh:947`）で消える。反映の後の本番にも無い（p11-prod-recheck.txt に tenant_004.audit_log の行が無い）。
- そのため、毎回 :733 で飛ばされず、次の18表を作る（IF NOT EXISTS。行番号は `20260831_110000` の中）: audit_log :55・conditions :79・tcg_products :92・tcg_suppliers :111・units :123・condition_aliases :140・product_exclude_keywords :157・product_search_keywords :173・products_logistics :189・supplier_channels :199・unit_aliases :212・source_messages :233・extraction_jobs :253・extraction_items :271・analysis_results :293・item_notes :341・unparsed_lines :358・import_jobs :373。
- その後、同じ反映の中で次の3本が消す: :868（`migrations/20260915_010000_drop_tcg_products_phase2c.sql:86`、tcg_products）、:947（`20260921_050000` :18・:30・:42・:50・:51・:56・:57）、:959（`migrations/20260921_130000_drop_tenant004_master_copies.sql` :27・:28・:33・:35・:36・:41・:42）。
- どれも消さない表がある: tcg_suppliers・item_notes・unparsed_lines・products_logistics など。これらは反映の後も残る（tcg_suppliers は p11-prod-recheck.txt で確かめた）。この18表のうち残る表を書く先に挙げるのは、p11-detail の書く先の列では #24・#25（tcg_suppliers）と #38（products_logistics。§4 のとおり値は書かない）だけ。
- 【未確認】本番の反映ログで、:47 の NOTICE（creating TCG analysis tables in schema tenant_004）が毎回出ているかは見ていない。上は本文と登録の順番から読んだ事実。分け方の答えは、この NOTICE が出ていなくても変わらない（出ていなければ C の物は書く先が無く飛ばすだけ）。#24・#25 は、tcg_suppliers と supplier_channels が両方ある回に行を戻す。

## 2. 結果の数

| 分け方 | 本数 | 番号 |
|---|---|---|
| 無効にする | 8 | 1・3・5・12・17・24・25・43 |
| 固めてよい（A 本文のガードで2回目は何も変わらない） | 16 | 2・4・7・8・9・10・13・14・37・38・40・41・44・47・48・52 |
| 固めてよい（B 本番の構造を読んで、2回目は何も変わらないと確かめた） | 2 | 6・26 |
| 固めてよい（C 反映の途中で作り直され、同じ反映の中で消える表にだけ書く） | 18 | 15・18・19・20・21・22・23・27・28・29・30・31・32・33・34・35・36・39 |
| 固めてよい（D 新しい環境の初期値の出どころで、試験も値を使う） | 8 | 11・16・42・45・46・49・50・51 |
| 合計 | 52 | |

設計 §5-5 が「無効にする」の例に挙げた2本のうち、`migrations/20260903_120000_tcg_unit_evidence_rules_t004.sql`（#17）は無効にする。`migrations/20260902_110000_tcg_classification_masters.sql`（#16）は D に変えた。理由: 試験 `backend/tests/test_tcg_product_list_pg.py:60` がこのファイルを流して値を使う。書く4表のうち2表は同じ反映の中で消え（`migrations/20260921_130000_drop_tenant004_master_copies.sql:35-36`、登録 `scripts/run_all_migrations.sh:959`）、残る2表（tenant_004 の tcg_series・tcg_manufacturers）はアプリが名指ししない（`backend/app` で `tenant_004` と表名が同じ行に出る所 0件。アプリは TCG の表を `public` で直書きする: `backend/app/routers/tcg_line_import.py:60`・`backend/app/routers/tcg_product_import.py:54`・`backend/app/line_import_admin.py:26` の `TCG_SCHEMA = "public"`。`backend/app/tcg_config.py` は `backend/app` のどこからも読まれていない）。例は P11 の詳細を読む前に書いた物で、事実に合わせて直した。

## 3. 無効にする 8本

無効にするのは値を書く文だけ。表・列を作る文は残す（§5-5）。値の文は NOTICE を1行出すだけにする。

ただし #17 は、値の文と一緒に件数の確かめ（`migrations/20260903_120000_tcg_unit_evidence_rules_t004.sql:128-132`、4件でなければ RAISE）も外す。値の文だけ外すと、表が空の環境では件数が0になり反映が止まる。CI（`.github/workflows/migration-test.yml`）は tenant_004 を作らないので、CI ではこの止まりを見つけられない。5-1 のカードにこの2か所を書く。

| # | ファイル | 本番で毎回起きていること | 新しい環境での意味 | 試験 |
|---|---|---|---|---|
| 1 | 027_backfill_customer_contact_channels.sql | 顧客側に連絡手段が残っていれば、消した連絡手段の行が戻る（p11-detail #1、:46-49・:68-71） | 無し（昔の顧客の表からの写し） | なし |
| 3 | 054_add_users_theme.sql | 審査用の利用者1人の画面の色を、毎回「明るい」に戻す（:10-12） | 無し（列の既定値で足りる） | なし |
| 5 | 098_migrate_customer_discord_to_company_discord.sql | 古い顧客の Discord の行が残っていれば、消した会社の Discord の行が戻る（:117）。会社の名前が合わない行があると :87 で反映が止まる | 無し（昔の表からの写し） | なし |
| 12 | 20260622_020000_migrate_conv_only_into_meta_messages.sql | 消したメッセージの行が、昔の会話の表から戻る（:94-99） | 無し（昔の表からの写し） | なし |
| 17 | 20260903_120000_tcg_unit_evidence_rules_t004.sql | 消した4行が戻る（:62 ほか）。行を足すと毎回の反映が止まる（:128-132）。本番に表が残っている（tenant_004.tcg_unit_evidence_rules） | 無し（アプリがこの表を名指ししない。`backend/app` で表名の当たり 0件。移行用の台本 `backend/tcg_migration/scripts/dry_run_parity02_phase_e.py:284` が読むが、アプリではない） | なし |
| 24 | 20260905_120000_register_15_suppliers_t004.sql | 消した仕入れ先の行が tenant_004.tcg_suppliers に戻る（:37-55 の INSERT、:54 の ON CONFLICT DO NOTHING）。:733 が作り直した supplier_channels があるので :27-29 では飛ばない（§1-1）。tcg_suppliers は反映の後も残る | 無し（tenant_004 の昔の仕入れ先の写し。アプリは tcg_suppliers を名指ししない。`backend/app` で 0件。`recon-5-1a/apps.md:176` が ×） | なし（`backend`・`.github` でファイル名の当たり 0件） |
| 25 | 20260905_150000_record_manual_supplier_fixes_t004.sql | #24 と同じ表に、手で直した仕入れ先2件を戻す（:57-59・:80-82 の INSERT ... ON CONFLICT DO NOTHING） | 無し（一度きりの手直しの記録。`recon-5-1a/apps.md:178` が ×） | なし（同上） |
| 43 | 20260929_120000_fix_source_messages_received_at.sql | 新しく届いたメッセージの受け取り時刻を、毎回 LINE の投稿時刻に書き換える（:6-9） | 無し（一度きりの直し） | なし |

## 4. 固めてよい 44本（ファイルごとの理由）

「:733」「:868」「:947」「:959」は §1-1 の作り直しと消す移行の登録行（`scripts/run_all_migrations.sh`）。

| # | 区分 | 固めてよい理由（根拠は p11-detail の同じ番号の行） |
|---|---|---|
| 2 | A | 会社の欄が空の行だけ埋める（:78 ほか）。2回目は0行 |
| 4 | A | 列を消した後は書く文に入らない（:23-31・:60） |
| 6 | B | public.products.work_id が NOT NULL なので :68-79 で飛ばす（p11-prod-recheck-cols.txt: work_id の attnotnull が True）。この列の NOT NULL を外す移行は無い（`migrations/20260919_010000_master_ssot_work_id_recast.sql:78` が外すのは work_id_old_uuid で、登録も :892 と後）。tenant_006.products は本番に有る（p11-prod-recheck.txt。第1版の「無い」は誤り） |
| 7 | A | 表が空のときだけ入れる（:61） |
| 8 | A | 環境の欄が空の行だけ（:15-17） |
| 9 | A | 日時が空の行だけ（:39・:49。:9 に再実行で0件） |
| 10 | A | 元の列を消した後は飛ばす（:48）。種類が空の行だけ（:94-96） |
| 11 | D | 販売フォームの選択肢5件の出どころ。アプリが読む（`backend/app/routers/leads.py:312`）。試験の前準備が流す（`backend/tests/rls_bootstrap.py:52`）。アプリから消す道は無い（書き込み ×） |
| 13 | A | 単位が空の行だけ（:20） |
| 14 | A | lead が空の会社だけ。空の会社はもう作れない（:42） |
| 15 | C | 書く先の tenant_004.conditions は :733 が作り直し（登録 :736 はその後）、:959 で消える（`20260921_130000:33`） |
| 16 | D | 上の §2 のとおり |
| 18 | C | tenant_004.tcg_note_master は :959 で消える（`20260921_130000:41`）。試験が流す（`backend/tests/test_tcg_work_matching_integration.py:618`） |
| 19 | C | tenant_004.tcg_status_master は :959 で消える（同 :42）。毎回作り直した表なので件数照合（:139-146）では止まらない。試験が値を使う（`backend/tests/test_tcg_completion_safety.py:92-98`） |
| 20 | C | 表は :947 で消える（`20260921_050000:42`）。試験が値を使う（`backend/tests/test_tcg_work_comparison_pg.py:61-64`） |
| 21 | C | 書く先の tenant_004.tcg_products は :733 が作り直し、:868 で消える（`20260915_010000:86`） |
| 22 | C | #20 と同じ表。:947 で消える。試験が流す（`test_tcg_work_matching_integration.py:621`） |
| 23 | C | 表は :947 で消える（`20260921_050000:50`）。試験が流す（`backend/tests/test_tcg_distribution_pg.py:88`） |
| 26 | B | tenant_001.tcg_products が本番に無く、tenant_001.audit_log は有る（p11-prod-tables.txt・p11-prod-recheck.txt）。tenant_001.audit_log を消す移行は無いので :40-44 で毎回全部飛ばす。試験が流す（`test_tcg_work_matching_integration.py:53`） |
| 27 | C | 書く先の tenant_004.extraction_jobs は :733 が作り直した空の表で、:947 で消える（`20260921_050000:30`） |
| 28 | C | #18 と同じ表。:959 で消える。試験が流す（`test_tcg_work_matching_integration.py:619`） |
| 29 | C | #27 と同じ（extraction_jobs・:947） |
| 30 | C | #27 と同じ（extraction_jobs・:947）。:16-18 に2回目以降は更新しないと明記 |
| 31 | C | 書く先の tenant_004.source_messages は :733 が作り直し、:947 で消える（`20260921_050000:56`） |
| 32 | C | 書く2表は :947 と :959 で消える。試験が流す（`test_tcg_work_matching_integration.py:622`） |
| 33 | C | #27 と同じ（extraction_jobs・:947） |
| 34 | C | :841 の時点で tenant_004.conditions（:733）と tcg_note_master（#18）が両方あるので :12-19 を通って書くが、tcg_note_master は :959 で消える（`20260921_130000:41`）。試験が流す（`test_tcg_work_matching_integration.py:612`）。第1版の B の理由は誤り |
| 35 | C | 書く先の tenant_004.conditions は :733 が作り直し、:959 で消える（`20260921_130000:33`）。第1版の A の理由は誤り |
| 36 | C | 書く先の tenant_004.product_exclude_keywords は :733 が作り直し、:851 で書いた後 :959 で消える（`20260921_130000:28`）。試験が流す（`test_tcg_work_matching_integration.py:1216`） |
| 37 | A | tcg_uuid が UUID でなければ全体を飛ばす（:106-123） |
| 38 | A | 列が既に整数なら飛ばす（:53-55 ほか）。整数でない表（tenant_004 で作り直された表）に当たったときは、public.products.tcg_uuid が本番に無いので（`/tmp/CC報告ファイル/deploy-lock-1113/p11-prod-tcguuid.txt`、0行、2026-11-15 07:20:47Z）書く道（:62-68 ほか）に入らず、件数を数える道（:69-76 ほか）に入る。行があれば RAISE、0行なら NOTICE だけで、値は書かない。作り直された表は空なので通る |
| 39 | C | tenant_001.analysis_policies は :934 で消える（`migrations/20260921_010000_drop_analysis_rule_tables.sql:55`）。本番に無い（p11-prod-tables.txt） |
| 40 | A | 列が既に整数なら飛ばす（:49-50・:144-145）。tenant_004.analysis_results に当たっても :947 で消える |
| 41 | A | 古い値の行だけ（:23） |
| 42 | D | 抽出の指示文の初期値の出どころ。画面で直した行は上書きしない（:81・:97）。試験が流す（`backend/tests/test_suppliers_rls.py:56`） |
| 44 | A | 古い既定の文の行だけ（:15） |
| 45 | D | 試験がこの埋め直しそのものを確かめる（`backend/tests/test_llm_usage_events_backfill_migration_pg.py:30`）。無効にすると試験が落ちる |
| 46 | D | 為替の履歴の初期値。試験が流す（`backend/tests/test_llm_usage_outcome_filter_pg.py:45`） |
| 47 | A | 値の文は関数の本文の中だけ。移行を流した時には書かない |
| 48 | A | 毎回、表を空にして同じ16行を入れ直す（TRUNCATE :90・INSERT :91-109、1つの取引）。:88 に「拒否表は migration が正本」と明記。アプリから足す・消す道は無い（書き込み ×）ので、毎回の結果は同じ16行で、戻る行は無い。:369-370 は関数の本文 |
| 49 | D | 秘書チャットの使用可の初期値。止めた設定は上書きしない（:11）。試験が流す（`backend/tests/test_rls_secretary_resolve.py:29`） |
| 50 | D | AI の担当の選択肢と割り当ての初期値の出どころ。画面で切り替えた担当は上書きしない（:124）。試験が期待値を持つ（`backend/tests/ops/test_ai_job_assignments_db.py:46-52`） |
| 51 | D | 同上の選択肢3件（`ops/test_ai_job_assignments_db.py:37`） |
| 52 | A | 値の文はトリガ関数の本文の中だけ（:37-73）。埋め直しは外してある（:81-85） |

## 5. この分け方で残ること（5-3 までの間）

- D の8本と #16 の残る2表は、5-3 までの間、消した行が戻る形のまま。D の8本は、既にある行を上書きしない形（ON CONFLICT DO NOTHING、#45 は NOT EXISTS `migrations/20260930_160000_backfill_llm_usage_events.sql:28`）で、PO やアプリが消したときだけ戻る。
- C の18本は、毎回の反映で作り直して消す表に書いている（構造の出し入れ）。値の始末ではなく、5-3（流し終えた物は流さない）で止まる。
- 無効にする8本を書き換えた後、依存する試験（なし）と CI の全件のドライラン（`.github/workflows/migration-test.yml`）が通ることを K5-1b で確かめる。
- 試験との当たりの確かめ（2026-11-15、`backend` 配下の .py と `.github` 配下でファイル名を探した。生出力 `/tmp/CC報告ファイル/deploy-lock-1113/p11-cls-check.txt`）: 無効にする8本を名指しする試験は0件（#24・#25 は同じ日に `backend`・`.github` を grep して0件）。`backend/tests/test_inventory_aggregated.py:244` は同じ番号で始まる別のファイル（`20260622_020000_add_inventory_raw_condition.sql`）。`.github/workflows/migration-test.yml:179`・`:181`・`:797`・`:805` は #43 のために最小の表を用意するだけで、値の文を NOTICE にしても困らない（表を作る文は残る）。

## 6. 審査

- 第1版（HEAD `8ea69e0f3`）: 合流前の審査役（Opus・新規起動、2026-11-15）REVISE。指摘: (1) tenant_004 の表が反映の途中で作り直される点を見ていない (2) そのため #24・#25 は「無効にする」に当たる (3) #34・#35・#36 と #27・#29・#30・#31・#33 の理由が仕組みと合わない (4) #6 の「tenant_006.products が無い」の根拠を生出力からたどれない (5) #17 を読む移行用の台本がある (6) design.md §5-6 の1行の変更は頼まれた範囲の外。
- 第2版での直し: (1) §1 に判断の時点と §1-1 を足した (2) #24・#25 を無効にするへ（6本→8本） (3) C に移して理由を書き直した（C 9本→18本、A 26本→16本、B 3本→2本） (4) 問い合わせの文を残して読み直した。tenant_006.products は本番に有った。#6 は work_id の NOT NULL で飛ばす、に直した（答えは固めてよいのまま） (5) #17 の行に一言足した (6) §5-6 の1行は、PO の言葉と設計の根拠を分けるための直しで、意図して入れた（PR 本文に書く）。
- 第2版（HEAD `9e9b9d63f`）: 合流前の審査役（Opus・新規起動、2026-11-15）REVISE。分け方そのものは妥当。直す3点: (1) #17 の件数の確かめは値の文ではないが、一緒に外さないと空の環境で止まる (2) design.md §5-5 の決まりが古いまま (3) §1-1 の「tcg_suppliers だけは、どれも消さない」は誤り（item_notes ほかも残る）、#38 の理由が tcg_uuid の有無に触れていない。細かい点: #45 は NOT EXISTS、#48 は TRUNCATE＋入れ直し、tcg_config.py はアプリから読まれていない。
- 第3版での直し: (1) §3 の頭に #17 の件数の確かめも外すと書いた (2) design.md §5-5 に「決まりはこの文書 §1 で細かくした（PO 承認待ち）」の1行を足した (3) §1-1 に作る18表を全部並べ、残る表を直した。#38 は本番で tcg_uuid が無いこと（0行）を読んで理由を書き直した。細かい点も直した。分け方の本数は変わらない（無効8・固め44）。
