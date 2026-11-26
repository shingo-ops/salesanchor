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
