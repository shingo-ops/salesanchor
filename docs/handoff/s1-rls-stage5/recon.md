# recon — S1 段階⑤（会社の行も足せる public の 6 表と別名の入口 2 つの RLS）

> この文書は何か：運営の共用行に加えて会社の画面から会社の行も足せる 6 表について、今どこから読み書きされ、そのとき会社や運営の文脈が張られているか、別名の入口（ビュー）がどの権限で読まれているかを、実物の行番号で並べたものです。

- 基準: origin/main `44a6ccce1`（2026-11-07 15:00 JST に fetch して一致を確認）。行番号はこの版。
- 調べた人: Claude Opus（設計担当）。生の抜き出しは本 PR に載せず、要点だけを下に引用する。
- 発端: ADR-1063 便5 の許可一覧（backend/app/ops/tenant_rls_allowlist.py:17-41）に、この 6 表を理由「RLS は次の段で付ける」で載せた（PO 2026-11-07「ｃ1」）。ADR-1067 の「触らない範囲」に、次の段でビューの読み方も設計に入れると書いた。

## 1. 既存 ADR・仕様の検索結果

| 文書 | 関係 |
|---|---|
| docs/adr/ADR-1067-public-tenant-config-tables-rls.md | 段階④（8 表）。型A／型C の選び方、移行の 3 点の決まり（NULLIF・DROP POLICY IF EXISTS・BEGIN〜COMMIT）、戻し方の順番。本段階もこれに従う。「触らない範囲」に本段階の 6 表とビュー 2 つを名指し |
| docs/adr/ADR-1018-public-sensitive-tables-rls-staged.md | 型C（読取は全行・書込は自社か運営）の前例（段階③便C users） |
| docs/adr/ADR-1063 系（便5・tenant_rls_allowlist.py） | RLS の無い会社の列付きの表を CI で止める。許可一覧が唯一の正本（tenant_rls_allowlist.py:1-4） |
| docs/handoff/s1-rls-stage4/design.md | 型C のポリシー文（§2-2）、試験の項目（§4）、戻し方（§7）の手本 |
| docs/specs/tenant-rls/kgi.md | 段階⑤の KGI-7〜9（PO 承認済み 2026-11-07「1」） |

## 2. 本番の状態（reader 鍵の道・ADR-1024）

### 2-1. 行数（2026-11-07T04:18:44Z、AUDIT sha=b376a44f1d7b）

| 表 | 全行 | 共用（tenant_id 空） | 会社の数 |
|---|---|---|---|
| line_conditions | 28 | 28 | 0 |
| line_units | 10 | 10 | 0 |
| payment_fee_settings | 7 | 7 | 0 |
| tcg_note_master | 99 | 99 | 0 |
| tcg_status_master | 21 | 21 | 0 |
| tcg_product_categories | 6 | 6 | 0 |

- 計 171 行、会社の行は 0。

### 2-2. 持ち主・RLS・ビューの設定（2026-11-07 13:55 JST の読取）

- 6 表とビュー 4 つ（conditions・units・condition_aliases・unit_aliases）の持ち主はすべて `jarvis`（superuser・BYPASSRLS）。6 表とも `relrowsecurity`・`relforcerowsecurity` は False。ビュー `conditions`・`units` の `reloptions` は空（`security_invoker` なし）。
- 権限（AUDIT sha=a26bad3add6c）: 6 表は `jarvis=arwdDxt`・`salesanchor_app=arwd`・`ai_unmask_owner=r`。ビュー `conditions`・`units` は `jarvis=arwdDxt`・`salesanchor_app=arwd` だけ。
  - 意味: アプリの接続役 salesanchor_app は、ビューにも元の表にも読み書きの権限がある。ビューを「読む人の権限で読む」に変えても、権限不足で止まらない。
  - ai_unmask_owner は BYPASSRLS（migrations/20261031_210000_create_ops_case.sql:170）。reader 鍵の窓口はこの役で元の表を読むので、RLS を付けても数え方は変わらない。

## 3. ビュー（別名の入口）の作られ方

- 表の名前の付け替え: migrations/20260922_080000_rename_line_analysis_tables.sql:20（units → line_units）・:72（conditions → line_conditions）。付け替えた後に旧名でビューを作る: :32 `CREATE VIEW public.units AS TABLE public.line_units;`・:83 `CREATE VIEW public.conditions AS TABLE public.line_conditions;`（ビューが無いときだけ。:30・:81）。
- ビューの作り直し（デプロイで移行が流れるたびに毎回走る）:
  - migrations/20260925_010000_conditions_add_match_type.sql:52 `CREATE OR REPLACE VIEW public.conditions AS TABLE public.line_conditions;`（DO の IF EXISTS の中）
  - migrations/20260925_020000_conditions_add_def_unit_note.sql:42（条件なし）
  - migrations/20261017_120000_line_conditions_value_rank.sql:47（DO の IF EXISTS の中）
- PostgreSQL 16 公式文書「CREATE VIEW」: `CREATE OR REPLACE VIEW` は WITH の設定を置き換える（指定しなければ設定は外れる）。根拠の実物は PostgreSQL のソース src/backend/commands/view.c:191-200（作り直しで `reloptions` を新しい指定で上書き）。→ 新しい移行で `ALTER VIEW … SET (security_invoker = true)` を付けても、上の 3 つの古い移行が次のデプロイで設定を消す。
- 同じ公式文書: ビューは既定で持ち主の権限で元の表を読み、持ち主には RLS が効かない（持ち主 jarvis は superuser）。`security_invoker = true` にすると、元の表の権限と RLS が「読む人」に対して効く。

## 4. 書込の入口

### 4-1. 会社の画面（会社の文脈あり。変更不要）

| ファイル | 文脈 | 書く行 |
|---|---|---|
| backend/app/routers/conditions.py | `Depends(get_current_tenant)`（:138・:167・:191） | 自社の行だけ（:142 `tenant_id = :tenant_id`）。書込はビュー public.conditions 経由（:232・:302・:346・:491・:503） |
| backend/app/routers/units.py | 同（:103・:132・:158） | 自社だけ（:4・:107）。ビュー public.units 経由（:137・:170・:196・:320・:330） |
| backend/app/routers/note_master.py | 同（:146・:169・:205） | 自社だけ（:218 `WHERE id = :id AND tenant_id = :tenant_id`） |
| backend/app/routers/status_master.py | 同（:130・:159・:188） | 自社だけ（:4・:134） |
| backend/app/routers/product_categories.py | 同（:103・:135・:160） | 自社だけ（:4・:107） |
| backend/app/routers/payment_fee_settings.py | 同（:66・:95・:132） | 自社だけ（:8） |

- `get_current_tenant`（backend/app/auth/dependencies.py:235）は `app.tenant_id` を自社に張り、`app.is_operator` を空にする（同ファイル :277・:281）。型C の書込条件を満たす。
- 例外: backend/app/routers/conditions.py:615 は別名の表（aliases）を消すときに public.conditions を USING で読むだけで、状態の表には書かない。

### 4-2. 運営画面（文脈なし。RLS の後は止まる）

- 運営画面は `get_db`（backend/app/database.py）と `require_super_admin`（dependencies.py:488）だけを使い、会社の文脈も運営の文脈も張らない。型C の後は、INSERT が 42501、UPDATE・DELETE が静かに 0 行になる（段階②b の教訓）。
- 書込の入口 23 本（関数の行。生の一覧: 道と関数名を `@router.post/patch/delete` から抜き出した）:

| ファイル | 作る | 変える | 消す | 取込の確定 |
|---|---|---|---|---|
| backend/app/routers/super_admin_conditions.py | :167 create_condition | :239 update_condition | :275 delete_condition | :377 import_conditions_commit |
| backend/app/routers/super_admin_units.py | :146 create_unit | :178 update_unit | :213 delete_unit | :382 import_units_commit |
| backend/app/routers/super_admin_note_master.py | :164 | :197 | :232 | :334 |
| backend/app/routers/super_admin_status_master.py | :161 | :206 | :259 | :360 |
| backend/app/routers/super_admin_product_categories.py | :135 | :293 | :328 | :235 |
| backend/app/routers/super_admin_payment_fee_settings.py | :88 | :121 | :156 | — |

- 対象外（6 表に書かない）: 取込の下見（super_admin_conditions.py:341・super_admin_units.py:346・super_admin_note_master.py:298・super_admin_status_master.py:324・super_admin_product_categories.py:199）、照合の下見（super_admin_status_master.py:467）、別名の表の入口（super_admin_conditions.py:462・:499、super_admin_units.py:257・:294）。別名の表は本段階の対象外（tenant_id の有無と型は別の段で調べる）。
- 運営の文脈を張る手本: backend/app/routers/super_admin_suppliers.py:58 の `_operator_writes`（書く関数を包み、`set_operator_context`（dependencies.py:454）→ 本体 → finally で `reset_operator_context`（:471））。:143 で使用中。段階④の運営画面 2 本も同じ道具（super_admin_llm_budget.py:151・:173、super_admin_phase_switch.py:128）。

### 4-3. 解析・定期の処理

- 6 表を読むだけで書かない（six_writes の抜き出しで、書く文はすべて 4-1・4-2 のファイルにある）。型C の読取は全行なので影響しない。解析が会社で絞らずに読むこと（tenant_rls_allowlist.py:19-20 の理由）も変わらない。

## 5. 行に鍵を掛ける箇所（RLS で静かに外れる穴）

- PostgreSQL 16 公式文書「CREATE POLICY」: `SELECT … FOR UPDATE / FOR SHARE` は UPDATE のポリシーの USING を「黙って行を絞る条件」として当てる。→ 型C では、会社の文脈・文脈なしの接続から共用行（tenant_id 空）に鍵を掛けると、エラーにならず鍵が 0 行になる。
- backend 全体の鍵を掛ける箇所 41 件を全部読み、6 表に触るのは 2 件だけ（他は import_jobs・supplier_channels・suppliers・ai_job_*・companies・contacts・staff_join_invites・products など）:
  1. backend/app/services/tcg_condition_review_svc.py:399 `SELECT id FROM public.conditions ORDER BY id FOR SHARE`（:397-398 の注記「使う定義をすべて鍵で止める。穴は認めない」）。呼び出し元 backend/app/routers/item_corrections.py:157 は `get_db`＋`require_super_admin`（:149-150）で文脈なし → RLS の後は鍵が 0 行になる。この関数は状態の表を読むだけで書かない（書込は :434 の item_corrections と :439・:452 の analysis_results だけ）。
  2. backend/app/services/tcg_product_detail_svc.py:210 `SELECT {name_col} FROM public.{table} WHERE id=:id AND is_active=TRUE FOR SHARE`（:201 の PUBLIC_INTEGER_LOOKUPS。:39 で tcg_product_categories を含む）。運営の文脈 `SET LOCAL app.is_operator = 'true'` は :258 で、鍵の後に張られる。呼び出し元 backend/app/routers/tcg_product_import.py:338 は `get_db`＋`require_super_admin`（:330-331）→ RLS の後は共用の区分が見つからず 422 PRODUCT_DETAIL_INVALID_CLASSIFICATION になる。
- PostgreSQL 16 公式文書「LOCK」: 表に UPDATE・DELETE・TRUNCATE の権限があればどの強さの鍵も掛けられる。RLS は LOCK に効かない。salesanchor_app は line_conditions に arwd を持つ（§2-2）。
- 既存の表ごとの鍵 backend/app/services/tcg_product_roundtrip_svc.py:427（LOCK TABLE … IN SHARE MODE）は RLS の影響を受けない。
- 既存の穴（本段階の対象外）: tcg_condition_review_svc.py:402 の `FOR SHARE OF p`（products。運営の文脈なしで共用の商品に鍵が掛からない。ADR-145 のポリシー）。

## 6. CI

- 確かめの道具: scripts/check_public_tenant_rls.py（87 行）。:22-31 の FIND_SQL で public の relkind r/p・tenant_id 列あり・RLS なしの表を探し、許可一覧（:20 で import）に無ければ落とす。試験は backend/tests/test_check_public_tenant_rls.py。ビューの設定は確かめていない。
- 全件ドライラン（.github/workflows/migration-test.yml:1385 のジョブ）: :2115 で全移行を 2 回流し（`--rounds 2`）、:2125 で check_public_tenant_rls.py を流す。6 表とビューを作る移行は除外一覧（scripts/migration-guard/dryrun-exclusions.tsv）に無い（grep 0 件）＝全件ドライランで実物の移行から作られる。
- 変更 SQL のジョブ（:91）は前提の表を `PUBLIC_SQL`（:480）で作る: tcg_status_master :510、units を「表」として :528、line_units :543、tcg_note_master :556、line_conditions :697、`CREATE OR REPLACE VIEW public.conditions` :713、tcg_product_categories :718、payment_fee_settings :862。→ このジョブでは public.units はビューでなく表。ビューに触る移行は「ビューのときだけ」の条件が要る。
- 同じ `PUBLIC_SQL` の 6 表の定義のうち、tenant_id 列があるのは payment_fee_settings（:864）だけ。tcg_status_master（:510）・line_units（:543）・tcg_note_master（:556）・line_conditions（:697）・tcg_product_categories（:718）には無い（各定義の行を読んで確かめた）。→ このジョブで RLS の移行（`tenant_id = …` を書くポリシー）を流すと、列が無くて落ちる。本番では §7 の 20260920_0X0000 の 5 本が列を足している。
- 試験の DB: .github/workflows/test.yml:234 で `RLS_TEST_DATABASE_URL` は salesanchor_app。段階④の試験の型 backend/tests/test_tenant_budget_settings_rls.py（使い捨て DB・本物の移行・会社番号 966/967）。下準備 backend/tests/rls_bootstrap.py（`_apply_migration`、`bootstrap_public_products`）。
- 既存の試験でこの 6 表に触るもの 40 本（backend/tests を表の名で git grep。例 test_tcg_condition_review.py・test_tcg_product_detail_pg.py・test_line_analysis_v102_pg.py）。*_pg の多くは superuser でつなぐ。test_tcg_condition_review.py:414 は `FOR SHARE OF ei, ej, sm` の文字だけを確かめる。

## 7. 移行の順番（scripts/run_all_migrations.sh）

| 行 | 移行 | 6 表に関すること |
|---|---|---|
| :898 | 20260919_020000_master_ssot_public_tables.sql | units :62・conditions :145・tcg_note_master :234・tcg_status_master :259・tcg_product_categories :283 を作る。public.products を参照する表も作る（:305・:321） |
| :913・:916・:919・:922・:925 | 20260920_040000_conditions_ssot_phase1.sql（:57）・20260920_030000_units_add_tenant_id.sql（:11）・20260920_050000_status_master_add_tenant_id.sql（:2）・20260920_060000_note_master_tenant_id.sql・20260920_070000_product_categories_tenant_id.sql | 5 表に tenant_id 列を足す（括弧は ADD COLUMN の行） |
| :940 | 20260921_090000_create_condition_definitions.sql | product_lines・condition_definitions |
| :980 | 20260922_080000_rename_line_analysis_tables.sql | 名前の付け替えとビュー |
| :1020・:1023 | 20260925_010000・20260925_020000 | 列の追加とビューの作り直し |
| :1071・:1074 | 20261002_160000_create_payment_fee_settings.sql・20261002_180000 | payment_fee_settings（tenants を参照） |
| :1170 | 20261017_120000_line_conditions_value_rank.sql | 列の追加とビューの作り直し |
| 末尾 | 20261107_160000_add_tenant_budget_settings_rls.sql | 段階④の最後。本段階の移行はこの後ろに足す |

## 8. 外の資料

- PostgreSQL 16 公式文書（2026-11-07 取得）: CREATE VIEW（security_invoker）・CREATE POLICY（FOR UPDATE/SHARE と USING）・LOCK（権限）・5.8 Row Security Policies。Context7 は月の上限に達して使えなかったため、起動指示の許可に従い公式文書とソース（view.c）を直接読んだ。
